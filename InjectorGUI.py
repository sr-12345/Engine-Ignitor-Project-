
import json
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import numpy as np
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from IPA import SPI, Coaxial_IPA_Size, Impinging_IPA_Size
from N2O import (
    ChokedNitrousAreaRequired,
    Coaxial_Drill_Diameter_Nitrous,
    Impinging_Nitrous_Size,
    ChokedFlowCriteria,
)

APP_NAME = "Injector Sizing Input Interface"
APP_VERSION = "1.1.0"

CHAMBER_FIELDS = [
    ("P_c", "Chamber Pressure", "Pa", "2000000"),
    ("P_feedsystem", "IPA Feed System Pressure", "Pa", "3500000"),
    ("P_feedsystem_N2O", "N2O Feed System Pressure", "Pa", "4500000"),
]

IPA_FIELDS = [
    ("Cd_IPA", "Discharge Coefficient (Cd)", "-", "0.65"),
    ("m_dot_IPA", "IPA Mass Flow Rate", "kg/s", "0.030"),
    ("Rho_IPA", "IPA Density", "kg/m^3", "786"),
]

N2O_FIELDS = [
    ("Cd_N2O", "Discharge Coefficient (Cd)", "-", "0.65"),
    ("m_dot_N2O", "N2O Mass Flow Rate", "kg/s", "0.060"),
    ("Gamma_N2O", "Specific Heat Ratio (gamma)", "-", "1.3"),
    ("R_N2O", "Specific Gas Constant", "J/(kg K)", "188.9"),
    ("N2O_Temp", "Temperature", "K", "298"),
]

GEOMETRY_FIELDS = [
    ("IPA_needle_OD_mm", "IPA Needle Outer Diameter", "mm", "3.0"),
    ("IPA_orifices", "Number of IPA Orifices", "-", "4"),
    ("N2O_orifices", "Number of N2O Orifices", "-", "4"),
]

ALL_FIELDS = CHAMBER_FIELDS + IPA_FIELDS + N2O_FIELDS + GEOMETRY_FIELDS


INT_FIELDS = {"IPA_orifices", "N2O_orifices"} #integers


PRESSURE_KEYS = {"P_c", "P_feedsystem", "P_feedsystem_N2O"}

PA_PER_BAR = 1e5 #conversion factor


class InjectorSizingApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.minsize(1000, 650)
        self.root.geometry("1200x750")

        self.vars = {}
        self.bar_vars = {}
        self._last_inputs = None
        self._last_results = None

        self._build_style()
        self._build_menu()
        self._build_layout()


    def _build_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Sub.TLabel", font=("Segoe UI", 9), foreground="#555555")
        style.configure("Unit.TLabel", font=("Segoe UI", 9), foreground="#777777")
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6)
        style.configure("Section.TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        style.configure("Result.TLabel", font=("Segoe UI", 12, "bold"))
        style.configure("ResultCaption.TLabel", font=("Segoe UI", 9), foreground="#555555")
        style.configure("ColHeader.TLabel", font=("Segoe UI", 9, "bold"), foreground="#333333")

    def _build_menu(self):
        menu_bar = tk.Menu(self.root)

        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Calculate", command=self.on_generate, accelerator="Enter")
        file_menu.add_command(label="Export Results...", command=self.on_export, accelerator="Ctrl+E")
        file_menu.add_command(label="Reset Defaults", command=self.on_reset)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menu_bar.add_cascade(label="File", menu=file_menu)

        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="About", command=self.on_about)
        menu_bar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menu_bar)
        self.root.bind("<Control-e>", lambda e: self.on_export())


    def _build_layout(self):
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        #scrollable input/results panel
        left_container = ttk.Frame(self.root)
        left_container.grid(row=0, column=0, sticky="nsew")
        left_container.rowconfigure(0, weight=1)
        left_container.columnconfigure(0, weight=1)

        canvas = tk.Canvas(left_container, borderwidth=0, highlightthickness=0, width=500)
        vscroll = ttk.Scrollbar(left_container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        vscroll.grid(row=0, column=1, sticky="ns")

        left = ttk.Frame(canvas, padding=16)
        left_window = canvas.create_window((0, 0), window=left, anchor="nw")
        left.columnconfigure(0, weight=1)

        def _on_left_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            canvas.itemconfig(left_window, width=event.width)

        left.bind("<Configure>", _on_left_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        def _on_mousewheel(event):
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")
            else:
                canvas.yview_scroll(int(-event.delta / 120), "units")

        def _bind_wheel(_event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            canvas.bind_all("<Button-4>", _on_mousewheel)
            canvas.bind_all("<Button-5>", _on_mousewheel)

        def _unbind_wheel(_event):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        canvas.bind("<Enter>", _bind_wheel)
        canvas.bind("<Leave>", _unbind_wheel)

        # docked plots
        right = ttk.Frame(self.root, padding=(0, 16, 16, 16))
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        ttk.Label(left, text="Injector Sizing", style="Header.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 2)
        )
        ttk.Label(
            left,
            text="Enter IPA and N2O flow parameters to size each drill-hole orifice.",
            style="Sub.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(0, 12))

        self._build_section(left, "Chamber & Feed System", CHAMBER_FIELDS, row=2, bar_keys=PRESSURE_KEYS)
        self._build_section(left, "IPA Injector", IPA_FIELDS, row=3)
        self._build_section(left, "N2O Injector", N2O_FIELDS, row=4)
        self._build_section(left, "Injector Geometry", GEOMETRY_FIELDS, row=5)

        self.status_var = tk.StringVar(value="")
        ttk.Label(left, textvariable=self.status_var, foreground="#b00020", wraplength=420).grid(
            row=6, column=0, sticky="w", pady=(8, 0)
        )
        self.warning_var = tk.StringVar(value="")
        ttk.Label(left, textvariable=self.warning_var, foreground="#b06000", wraplength=420).grid(
            row=7, column=0, sticky="w", pady=(2, 0)
        )

        btn_frame = ttk.Frame(left)
        btn_frame.grid(row=8, column=0, sticky="ew", pady=(12, 12))
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        ttk.Button(btn_frame, text="Calculate", command=self.on_generate).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(btn_frame, text="Reset Defaults", command=self.on_reset).grid(
            row=0, column=1, sticky="ew", padx=(6, 0)
        )

        #results panel
        results = ttk.Labelframe(left, text="Results", padding=12, style="Section.TLabelframe")
        results.grid(row=9, column=0, sticky="ew", pady=(0, 20))
        results.columnconfigure(0, weight=1)
        results.columnconfigure(1, weight=1)

        ttk.Label(results, text="Coaxial Injector", style="ColHeader.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(results, text="Impinging Injector", style="ColHeader.TLabel").grid(
            row=0, column=1, sticky="w"
        )

        ttk.Label(results, text="IPA orifice diameter", style="ResultCaption.TLabel", wraplength=190).grid(
            row=1, column=0, sticky="w", pady=(6, 0)
        )
        ttk.Label(
            results, text="IPA orifice diameter (per hole)", style="ResultCaption.TLabel", wraplength=190
        ).grid(row=1, column=1, sticky="w", pady=(6, 0))

        self.ipa_coax_var = tk.StringVar(value="--")
        self.ipa_impinge_var = tk.StringVar(value="--")
        ttk.Label(results, textvariable=self.ipa_coax_var, style="Result.TLabel").grid(
            row=2, column=0, sticky="w"
        )
        ttk.Label(results, textvariable=self.ipa_impinge_var, style="Result.TLabel").grid(
            row=2, column=1, sticky="w"
        )

        ttk.Separator(results, orient="horizontal").grid(row=3, column=0, columnspan=2, sticky="ew", pady=8)

        ttk.Label(
            results, text="N2O drill diameter (incl. IPA needle)", style="ResultCaption.TLabel", wraplength=190
        ).grid(row=4, column=0, sticky="w")
        ttk.Label(
            results, text="N2O orifice diameter (per hole)", style="ResultCaption.TLabel", wraplength=190
        ).grid(row=4, column=1, sticky="w")

        self.n2o_coax_var = tk.StringVar(value="--")
        self.n2o_impinge_var = tk.StringVar(value="--")
        ttk.Label(results, textvariable=self.n2o_coax_var, style="Result.TLabel").grid(
            row=5, column=0, sticky="w"
        )
        ttk.Label(results, textvariable=self.n2o_impinge_var, style="Result.TLabel").grid(
            row=5, column=1, sticky="w"
        )

        
        self._init_plot_area(right)

        self.root.bind("<Return>", lambda event: self.on_generate())

    def _build_section(self, parent, title, field_specs, row, bar_keys=None):
        bar_keys = bar_keys or set()
        frame = ttk.Labelframe(parent, text=title, padding=(12, 8), style="Section.TLabelframe")
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        frame.columnconfigure(1, weight=1)

        for i, (key, label, unit, default) in enumerate(field_specs):
            var = tk.StringVar(value=default)
            self.vars[key] = var

            ttk.Label(frame, text=label).grid(row=i, column=0, sticky="w", padx=(0, 8), pady=3)
            entry = ttk.Entry(frame, textvariable=var, width=13, justify="right")
            entry.grid(row=i, column=1, sticky="ew", pady=3)
            ttk.Label(frame, text=unit, style="Unit.TLabel").grid(
                row=i, column=2, sticky="w", padx=(8, 0), pady=3
            )

            if key in bar_keys:
                bar_var = tk.StringVar(value="")
                self.bar_vars[key] = bar_var
                ttk.Label(frame, textvariable=bar_var, style="Unit.TLabel").grid(
                    row=i, column=3, sticky="w", padx=(10, 0), pady=3
                )
                var.trace_add("write", lambda *args, k=key: self._update_bar_label(k))
                self._update_bar_label(key)

    def _update_bar_label(self, key):
        raw = self.vars[key].get().strip()
        try:
            pa = float(raw)
            self.bar_vars[key].set(f"\u2248 {pa / PA_PER_BAR:.2f} bar")
        except ValueError:
            self.bar_vars[key].set("")


    def on_reset(self):
        for key, _, _, default in ALL_FIELDS:
            self.vars[key].set(default)
        self.status_var.set("")
        self.warning_var.set("")
        self.ipa_coax_var.set("--")
        self.ipa_impinge_var.set("--")
        self.n2o_coax_var.set("--")
        self.n2o_impinge_var.set("--")
        self._last_inputs = None
        self._last_results = None
        self._draw_placeholder()
        self.fig.tight_layout()
        self.canvas.draw()

    def _read_inputs(self):
        values = {}
        for key, label, _, _ in ALL_FIELDS:
            raw = self.vars[key].get().strip()
            try:
                values[key] = int(float(raw)) if key in INT_FIELDS else float(raw)
            except ValueError:
                raise ValueError(f"'{label}' must be a number (got '{raw}').")

        if not (0 < values["Cd_IPA"] <= 1):
            raise ValueError("IPA Discharge Coefficient (Cd) must be between 0 and 1.")
        if not (0 < values["Cd_N2O"] <= 1):
            raise ValueError("N2O Discharge Coefficient (Cd) must be between 0 and 1.")
        if values["m_dot_IPA"] <= 0:
            raise ValueError("IPA Mass Flow Rate must be greater than 0.")
        if values["m_dot_N2O"] <= 0:
            raise ValueError("N2O Mass Flow Rate must be greater than 0.")
        if values["P_c"] <= 0:
            raise ValueError("Chamber Pressure must be greater than 0.")
        if values["P_feedsystem"] <= 0:
            raise ValueError("IPA Feed System Pressure must be greater than 0.")
        if values["P_feedsystem"] <= values["P_c"]:
            raise ValueError("IPA Feed System Pressure must be greater than Chamber Pressure.")
        if values["P_feedsystem_N2O"] <= 0:
            raise ValueError("N2O Feed System Pressure must be greater than 0.")
        if values["P_feedsystem_N2O"] <= values["P_c"]:
            raise ValueError("N2O Feed System Pressure must be greater than Chamber Pressure.")
        if values["Rho_IPA"] <= 0:
            raise ValueError("IPA Density must be greater than 0.")
        if values["Gamma_N2O"] <= 1:
            raise ValueError("N2O Specific Heat Ratio (gamma) must be greater than 1.")
        if values["R_N2O"] <= 0:
            raise ValueError("N2O Specific Gas Constant must be greater than 0.")
        if values["N2O_Temp"] <= 0:
            raise ValueError("N2O Temperature must be greater than 0.")
        if values["IPA_needle_OD_mm"] < 0:
            raise ValueError("IPA Needle Outer Diameter cannot be negative.")
        if values["IPA_orifices"] <= 0:
            raise ValueError("Number of IPA Orifices must be a positive whole number.")
        if values["N2O_orifices"] <= 0:
            raise ValueError("Number of N2O Orifices must be a positive whole number.")

        return values

    @staticmethod
    def _cd_sweep(cd_value, n=100):
        """Sweep range for the sensitivity plot, guaranteed to include cd_value."""
        lo = min(0.1, cd_value * 0.5)
        hi = max(1.0, cd_value * 1.1)
        return np.linspace(lo, hi, n)

    def on_generate(self):
        self.status_var.set("")
        self.warning_var.set("")
        try:
            v = self._read_inputs()
        except ValueError as e:
            self.status_var.set(str(e))
            messagebox.showerror("Input Error", str(e))
            return

        try:
            needle_od_m = v["IPA_needle_OD_mm"] / 1000.0

            ipa_area_point = SPI(v["Cd_IPA"], v["m_dot_IPA"], v["Rho_IPA"], v["P_c"], v["P_feedsystem"])
            ipa_coax_point = Coaxial_IPA_Size(ipa_area_point)
            ipa_impinge_point = Impinging_IPA_Size(ipa_area_point, v["IPA_orifices"])


            n2o_area_point = ChokedNitrousAreaRequired(
                v["m_dot_N2O"], v["Cd_N2O"], v["P_feedsystem_N2O"], v["Gamma_N2O"], v["R_N2O"], v["N2O_Temp"]
            )
            n2o_coax_point = Coaxial_Drill_Diameter_Nitrous(n2o_area_point, needle_od_m)
            n2o_impinge_point = Impinging_Nitrous_Size(n2o_area_point, v["N2O_orifices"])

            choke_status = ChokedFlowCriteria(v["Gamma_N2O"], v["P_feedsystem_N2O"], v["P_c"])
            if choke_status != "Choked Flow Applies":
                self.warning_var.set(
                    "Warning: N2O flow is NOT choked at these conditions (chamber pressure "
                    "too close to feed pressure) - the choked-flow sizing model may not apply."
                )


            ipa_cd_range = self._cd_sweep(v["Cd_IPA"])
            ipa_areas = SPI(ipa_cd_range, v["m_dot_IPA"], v["Rho_IPA"], v["P_c"], v["P_feedsystem"])
            ipa_coax_curve = Coaxial_IPA_Size(ipa_areas)

            n2o_cd_range = self._cd_sweep(v["Cd_N2O"])
            n2o_areas = ChokedNitrousAreaRequired(
                v["m_dot_N2O"], n2o_cd_range, v["P_feedsystem_N2O"], v["Gamma_N2O"], v["R_N2O"], v["N2O_Temp"]
            )
            n2o_coax_curve = Coaxial_Drill_Diameter_Nitrous(n2o_areas, needle_od_m)
        except Exception as e:
            messagebox.showerror("Calculation Error", f"Sizing calculation failed:\n{e}")
            return

        self.ipa_coax_var.set(f"{ipa_coax_point:.3f} mm")
        self.ipa_impinge_var.set(f"{ipa_impinge_point:.3f} mm  (x{v['IPA_orifices']})")
        self.n2o_coax_var.set(f"{n2o_coax_point:.3f} mm")
        self.n2o_impinge_var.set(f"{n2o_impinge_point:.3f} mm  (x{v['N2O_orifices']})")

        self._last_inputs = dict(v)
        self._last_results = {
            "ipa_coaxial_diameter_mm": ipa_coax_point,
            "ipa_impinging_diameter_per_hole_mm": ipa_impinge_point,
            "ipa_impinging_orifice_count": v["IPA_orifices"],
            "n2o_coaxial_drill_diameter_incl_needle_mm": n2o_coax_point,
            "n2o_impinging_diameter_per_hole_mm": n2o_impinge_point,
            "n2o_impinging_orifice_count": v["N2O_orifices"],
            "n2o_choked_flow_status": choke_status,
        }

        self._update_plots(
            ipa_cd_range, ipa_coax_curve, v["Cd_IPA"], ipa_coax_point,
            n2o_cd_range, n2o_coax_curve, v["Cd_N2O"], n2o_coax_point,
        )

    def on_export(self):
        if self._last_results is None:
            messagebox.showinfo("Nothing to Export", "Click Calculate first, then export the results.")
            return

        path = filedialog.asksaveasfilename(
            title="Export Results",
            defaultextension=".json",
            filetypes=[("JSON file", "*.json"), ("All files", "*.*")],
            initialfile="injector_sizing_results.json",
        )
        if not path:
            return

        payload = {
            "app": APP_NAME,
            "version": APP_VERSION,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "inputs": self._last_inputs,
            "results": self._last_results,
        }
        try:
            with open(path, "w") as f:
                json.dump(payload, f, indent=2)
        except OSError as e:
            messagebox.showerror("Export Failed", f"Could not write file:\n{e}")
            return

        self.status_var.set(f"Results exported to {path}")

    def on_about(self):
        messagebox.showinfo(
            "About",
            f"{APP_NAME}\nVersion {APP_VERSION}\n\n"
            "Sizes coaxial and impinging injector orifices for an IPA/N2O "
            "bipropellant rocket engine from user-supplied flow parameters.",
        )


    def _init_plot_area(self, parent):
        self.fig = Figure(figsize=(6, 7), dpi=100)
        self.ax1 = self.fig.add_subplot(2, 1, 1)
        self.ax2 = self.fig.add_subplot(2, 1, 2)
        self._draw_placeholder()
        self.fig.tight_layout()

        canvas = FigureCanvasTkAgg(self.fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        self.canvas = canvas

        toolbar_frame = ttk.Frame(parent)
        toolbar_frame.grid(row=1, column=0, sticky="ew")
        toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
        toolbar.update()

    def _draw_placeholder(self):
        for ax, title in (
            (self.ax1, "IPA Coaxial Drill Diameter vs Cd"),
            (self.ax2, "N2O Coaxial Drill Diameter vs Cd"),
        ):
            ax.clear()
            ax.set_title(title)
            ax.set_xlabel("Discharge Coefficient (Cd)")
            ax.set_ylabel("Drill Hole Diameter (mm)")
            ax.text(
                0.5, 0.5, "Click Calculate to view results",
                ha="center", va="center", transform=ax.transAxes, color="#999999",
            )
            ax.grid(True, alpha=0.3)

    def _update_plots(
        self,
        ipa_cd_range, ipa_curve, ipa_cd_point, ipa_point,
        n2o_cd_range, n2o_curve, n2o_cd_point, n2o_point,
    ):
        self.ax1.clear()
        self.ax1.plot(ipa_cd_range, ipa_curve, color="#1f77b4")
        self.ax1.scatter([ipa_cd_point], [ipa_point], color="#1f77b4", zorder=5)
        self.ax1.annotate(
            f"{ipa_point:.3f} mm",
            (ipa_cd_point, ipa_point),
            textcoords="offset points", xytext=(8, 8),
        )
        self.ax1.set_title("IPA Coaxial Drill Diameter vs Cd")
        self.ax1.set_xlabel("Discharge Coefficient (Cd)")
        self.ax1.set_ylabel("Drill Hole Diameter (mm)")
        self.ax1.grid(True, alpha=0.3)

        self.ax2.clear()
        self.ax2.plot(n2o_cd_range, n2o_curve, color="#d62728")
        self.ax2.scatter([n2o_cd_point], [n2o_point], color="#d62728", zorder=5)
        self.ax2.annotate(
            f"{n2o_point:.3f} mm",
            (n2o_cd_point, n2o_point),
            textcoords="offset points", xytext=(8, 8),
        )
        self.ax2.set_title("N2O Coaxial Drill Diameter vs Cd (incl. IPA needle)")
        self.ax2.set_xlabel("Discharge Coefficient (Cd)")
        self.ax2.set_ylabel("Drill Hole Diameter (mm)")
        self.ax2.grid(True, alpha=0.3)

        self.fig.tight_layout()
        self.canvas.draw()


if __name__ == "__main__":
    root = tk.Tk()
    app = InjectorSizingApp(root)
    root.mainloop()

#need to update GUI such that the thickness of the IPA needle is taken into account when calculating the 
#total drill size for the N2O injector. The total drill size should be the sum of the outer diameter of the 
#IPA needle and the required area for the N2O injector. This will ensure that the N2O injection hole is properly 
#sized to fit around the IPA needle. The GUI should also include results for the impinging injector model for both IPA and N2O

import tkinter as tk
from tkinter import ttk, messagebox

import numpy as np
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from IPA import SPI, Coaxial_IPA_Size
from N2O import ChokedNitrousAreaRequired, Coaxial_Nitrous_Size


# Each section is a list of (key, label, unit, default) tuples.
CHAMBER_FIELDS = [
    ("P_c", "Chamber Pressure", "Pa", "2000000"),
    ("P_feedsystem", "IPA Feed System Pressure", "Pa", "3500000"),
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

ALL_FIELDS = CHAMBER_FIELDS + IPA_FIELDS + N2O_FIELDS


class InjectorSizingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Injector Sizing Input Interface")
        self.root.minsize(520, 620)

        self.vars = {}

        self._build_style()
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

    def _build_layout(self):
        outer = ttk.Frame(self.root, padding=16)
        outer.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)

        ttk.Label(outer, text="Injector Sizing", style="Header.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 2)
        )
        ttk.Label(
            outer,
            text="Enter IPA and N2O flow parameters to size each drill-hole orifice.",
            style="Sub.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(0, 12))

        # Chamber / shared section
        self._build_section(outer, "Chamber & Feed System", CHAMBER_FIELDS, row=2)
        # IPA section
        self._build_section(outer, "IPA Injector", IPA_FIELDS, row=3)
        # N2O section
        self._build_section(outer, "N2O Injector", N2O_FIELDS, row=4)

        self.status_var = tk.StringVar(value="")
        ttk.Label(outer, textvariable=self.status_var, foreground="#b00020", wraplength=460).grid(
            row=5, column=0, sticky="w", pady=(8, 0)
        )

        btn_frame = ttk.Frame(outer)
        btn_frame.grid(row=6, column=0, sticky="ew", pady=(12, 12))
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        ttk.Button(btn_frame, text="Calculate", command=self.on_generate).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(btn_frame, text="Reset Defaults", command=self.on_reset).grid(
            row=0, column=1, sticky="ew", padx=(6, 0)
        )

        # Results panel
        results = ttk.Labelframe(outer, text="Results", padding=12, style="Section.TLabelframe")
        results.grid(row=7, column=0, sticky="ew")
        results.columnconfigure(0, weight=1)
        results.columnconfigure(1, weight=1)

        ttk.Label(results, text="IPA orifice diameter", style="ResultCaption.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(results, text="N2O orifice diameter", style="ResultCaption.TLabel").grid(
            row=0, column=1, sticky="w"
        )

        self.ipa_result_var = tk.StringVar(value="--")
        self.n2o_result_var = tk.StringVar(value="--")
        ttk.Label(results, textvariable=self.ipa_result_var, style="Result.TLabel").grid(
            row=1, column=0, sticky="w"
        )
        ttk.Label(results, textvariable=self.n2o_result_var, style="Result.TLabel").grid(
            row=1, column=1, sticky="w"
        )

        self.root.bind("<Return>", lambda event: self.on_generate())

    def _build_section(self, parent, title, field_specs, row):
        frame = ttk.Labelframe(parent, text=title, padding=(12, 8), style="Section.TLabelframe")
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        frame.columnconfigure(1, weight=1)

        for i, (key, label, unit, default) in enumerate(field_specs):
            var = tk.StringVar(value=default)
            self.vars[key] = var

            ttk.Label(frame, text=label).grid(row=i, column=0, sticky="w", padx=(0, 8), pady=3)
            entry = ttk.Entry(frame, textvariable=var, width=14, justify="right")
            entry.grid(row=i, column=1, sticky="ew", pady=3)
            ttk.Label(frame, text=unit, style="Unit.TLabel").grid(
                row=i, column=2, sticky="w", padx=(8, 0), pady=3
            )

    def on_reset(self):
        for key, _, _, default in ALL_FIELDS:
            self.vars[key].set(default)
        self.status_var.set("")
        self.ipa_result_var.set("--")
        self.n2o_result_var.set("--")

    def _read_inputs(self):
        values = {}
        for key, label, _, _ in ALL_FIELDS:
            raw = self.vars[key].get().strip()
            try:
                values[key] = float(raw)
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
        if values["Rho_IPA"] <= 0:
            raise ValueError("IPA Density must be greater than 0.")
        if values["Gamma_N2O"] <= 1:
            raise ValueError("N2O Specific Heat Ratio (gamma) must be greater than 1.")
        if values["R_N2O"] <= 0:
            raise ValueError("N2O Specific Gas Constant must be greater than 0.")
        if values["N2O_Temp"] <= 0:
            raise ValueError("N2O Temperature must be greater than 0.")

        return values

    @staticmethod
    def _cd_sweep(cd_value, n=100):
        """Sweep range for the sensitivity plot, guaranteed to include cd_value."""
        lo = min(0.1, cd_value * 0.5)
        hi = max(1.0, cd_value * 1.1)
        return np.linspace(lo, hi, n)

    def on_generate(self):
        self.status_var.set("")
        try:
            v = self._read_inputs()
        except ValueError as e:
            self.status_var.set(str(e))
            messagebox.showerror("Input Error", str(e))
            return

        try:
            # Exact design-point results, at the user's actual Cd values.
            ipa_diam_point = Coaxial_IPA_Size(
                SPI(np.array([v["Cd_IPA"]]), v["m_dot_IPA"], v["Rho_IPA"], v["P_c"], v["P_feedsystem"])
            )[0]
            n2o_diam_point = Coaxial_Nitrous_Size(
                ChokedNitrousAreaRequired(
                    v["m_dot_N2O"], np.array([v["Cd_N2O"]]), v["P_c"], v["Gamma_N2O"], v["R_N2O"], v["N2O_Temp"]
                )
            )[0]

            # Sensitivity curves vs Cd, for context.
            ipa_cd_range = self._cd_sweep(v["Cd_IPA"])
            ipa_diameters = Coaxial_IPA_Size(
                SPI(ipa_cd_range, v["m_dot_IPA"], v["Rho_IPA"], v["P_c"], v["P_feedsystem"])
            )

            n2o_cd_range = self._cd_sweep(v["Cd_N2O"])
            n2o_diameters = Coaxial_Nitrous_Size(
                ChokedNitrousAreaRequired(
                    v["m_dot_N2O"], n2o_cd_range, v["P_c"], v["Gamma_N2O"], v["R_N2O"], v["N2O_Temp"]
                )
            )
        except Exception as e:
            messagebox.showerror("Calculation Error", f"Sizing calculation failed:\n{e}")
            return

        self.ipa_result_var.set(f"{ipa_diam_point:.3f} mm")
        self.n2o_result_var.set(f"{n2o_diam_point:.3f} mm")

        self._show_plot_window(
            ipa_cd_range, ipa_diameters, v["Cd_IPA"], ipa_diam_point,
            n2o_cd_range, n2o_diameters, v["Cd_N2O"], n2o_diam_point,
        )

    def _show_plot_window(
        self,
        ipa_cd_range, ipa_diameters, ipa_cd_point, ipa_diam_point,
        n2o_cd_range, n2o_diameters, n2o_cd_point, n2o_diam_point,
    ):
        win = tk.Toplevel(self.root)
        win.title("Injector Sizing Results")
        win.geometry("900x480")

        fig = Figure(figsize=(9, 4.5), dpi=100)
        ax1 = fig.add_subplot(1, 2, 1)
        ax2 = fig.add_subplot(1, 2, 2)

        ax1.plot(ipa_cd_range, ipa_diameters, color="#1f77b4")
        ax1.scatter([ipa_cd_point], [ipa_diam_point], color="#1f77b4", zorder=5)
        ax1.annotate(
            f"{ipa_diam_point:.3f} mm",
            (ipa_cd_point, ipa_diam_point),
            textcoords="offset points", xytext=(8, 8),
        )
        ax1.set_title("IPA Drill Hole Diameter vs Cd")
        ax1.set_xlabel("Discharge Coefficient (Cd)")
        ax1.set_ylabel("Drill Hole Diameter (mm)")
        ax1.grid(True, alpha=0.3)

        ax2.plot(n2o_cd_range, n2o_diameters, color="#d62728")
        ax2.scatter([n2o_cd_point], [n2o_diam_point], color="#d62728", zorder=5)
        ax2.annotate(
            f"{n2o_diam_point:.3f} mm",
            (n2o_cd_point, n2o_diam_point),
            textcoords="offset points", xytext=(8, 8),
        )
        ax2.set_title("N2O Drill Hole Diameter vs Cd")
        ax2.set_xlabel("Discharge Coefficient (Cd)")
        ax2.set_ylabel("Drill Hole Diameter (mm)")
        ax2.grid(True, alpha=0.3)

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        toolbar = NavigationToolbar2Tk(canvas, win)
        toolbar.update()
        toolbar.pack(side=tk.BOTTOM, fill=tk.X)


if __name__ == "__main__":
    root = tk.Tk()
    app = InjectorSizingApp(root)
    root.mainloop()
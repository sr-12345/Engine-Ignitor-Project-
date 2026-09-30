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
from Engine import SizeEngine, SplitMassFlow, StayTime
from Chamber import SizeChamber, SizeNozzle

APP_NAME = "Engine & Injector Sizing Input Interface"
APP_VERSION = "1.2.0"

#Each section is a list of (key, label, unit, default) tuples

#Engine performance targets -> feeds Engine.py (SizeEngine)
ENGINE_FIELDS = [
    ("F_target", "Target Thrust", "N", "50"),
    ("P_a", "Ambient Pressure", "Pa", "101325"),
    ("OF_ratio", "O/F Ratio (N2O / IPA)", "-", "2.5"),
    ("Tc", "Chamber Temperature", "K", "2500"),
    ("Gamma_gas", "Combustion Gamma", "-", "1.2"),
    ("MW_gas", "Combustion Molecular Weight", "g/mol", "22.0"),
    ("eta_cstar", "c* Efficiency", "-", "0.95"),
    ("eta_cf", "CF Efficiency", "-", "0.95"),
]

#Chamber/nozzle geometry -> feeds Chamber.py (SizeChamber, SizeNozzle)
CHAMBER_GEOM_FIELDS = [
    ("L_star", "Characteristic Length L*", "m", "1.0"),
    ("contraction_ratio", "Contraction Ratio (blank = auto)", "-", ""),
    ("conv_half_angle_deg", "Convergent Half-Angle", "deg", "45"),
    ("nozzle_half_angle_deg", "Divergent Half-Angle", "deg", "15"),
]

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

#Engine/chamber fields are validated and read separately (they're optional,
#and contraction_ratio can be left blank), so they are not part of ALL_FIELDS.
ENGINE_ALL_FIELDS = ENGINE_FIELDS + CHAMBER_GEOM_FIELDS

#Mass-flow fields that get overwritten automatically when engine sizing is on.
AUTO_FILLED_BY_ENGINE = {"m_dot_IPA", "m_dot_N2O"}

#Fields that must be whole numbers.
INT_FIELDS = {"IPA_orifices", "N2O_orifices"}

#Pressure fields that also get a live "≈ X bar" readout.
PRESSURE_KEYS = {"P_c", "P_feedsystem", "P_feedsystem_N2O", "P_a"}

PA_PER_BAR = 1e5 #For pressure conversion


class InjectorSizingApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.minsize(1050, 700)
        self.root.geometry("1300x820")

        self.vars = {}
        self.widgets = {}
        self.bar_vars = {}
        self.engine_mode_var = tk.BooleanVar(value=False)
        self.engine_mode_note_var = tk.StringVar(value="")
        self._last_inputs = None
        self._last_results = None

        self._build_style()
        self._build_menu()
        self._build_layout()

    
    #Styling/menu
    
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

    
    #Layout
    
    def _build_layout(self):
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        #Left side: scrollable input/results panel

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

        #Right side: docked plots 
        
        right = ttk.Frame(self.root, padding=(0, 16, 16, 16))
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        ttk.Label(left, text="Engine & Injector Sizing", style="Header.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 2)
        )
        ttk.Label(
            left,
            text="Optionally size the engine from a target thrust, then size each "
                 "drill-hole orifice.",
            style="Sub.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(0, 12))

        #Engine sizing toggle
        
        toggle_frame = ttk.Frame(left)
        toggle_frame.grid(row=2, column=0, sticky="ew", pady=(0, 4))
        ttk.Checkbutton(
            toggle_frame, text="Design engine from target thrust",
            variable=self.engine_mode_var,
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(toggle_frame, textvariable=self.engine_mode_note_var, style="Sub.TLabel").grid(
            row=1, column=0, sticky="w", pady=(2, 8)
        )
        self.engine_mode_var.trace_add("write", lambda *a: self._set_engine_mode())

        self._build_section(left, "Engine Performance Targets", ENGINE_FIELDS, row=3,
                            bar_keys=PRESSURE_KEYS)
        self._build_section(left, "Chamber & Nozzle Geometry", CHAMBER_GEOM_FIELDS, row=4)

        self._build_section(left, "Chamber & Feed System", CHAMBER_FIELDS, row=5, bar_keys=PRESSURE_KEYS)
        self._build_section(left, "IPA Injector", IPA_FIELDS, row=6)
        self._build_section(left, "N2O Injector", N2O_FIELDS, row=7)
        self._build_section(left, "Injector Geometry", GEOMETRY_FIELDS, row=8)

        self.status_var = tk.StringVar(value="")
        ttk.Label(left, textvariable=self.status_var, foreground="#b00020", wraplength=420).grid(
            row=9, column=0, sticky="w", pady=(8, 0)
        )
        self.warning_var = tk.StringVar(value="")
        ttk.Label(left, textvariable=self.warning_var, foreground="#b06000", wraplength=420).grid(
            row=10, column=0, sticky="w", pady=(2, 0)
        )

        btn_frame = ttk.Frame(left)
        btn_frame.grid(row=11, column=0, sticky="ew", pady=(12, 12))
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        ttk.Button(btn_frame, text="Calculate", command=self.on_generate).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(btn_frame, text="Reset Defaults", command=self.on_reset).grid(
            row=0, column=1, sticky="ew", padx=(6, 0)
        )

        #Engine & Chamber results panel

        eng_results = ttk.Labelframe(left, text="Engine & Chamber Results", padding=12,
                                     style="Section.TLabelframe")
        eng_results.grid(row=12, column=0, sticky="ew", pady=(0, 10))
        eng_results.columnconfigure(0, weight=1)
        eng_results.columnconfigure(1, weight=1)

        eng_labels = [
            ("Thrust", "thrust_var"), ("Isp", "isp_var"),
            ("c* (real)", "cstar_var"), ("CF (real)", "cf_var"),
            ("Throat diameter", "dt_var"), ("Exit diameter", "de_var"),
            ("Expansion ratio", "eps_var"), ("Chamber diameter", "dc_var"),
            ("Contraction ratio", "cr_var"), ("Cylinder length", "lcyl_var"),
            ("N2O / IPA mass flow", "split_var"), ("Stay time", "stay_var"),
        ]
        for i, (caption, attr) in enumerate(eng_labels):
            r, c = divmod(i, 2)
            ttk.Label(eng_results, text=caption, style="ResultCaption.TLabel").grid(
                row=2 * r, column=c, sticky="w", pady=(6 if r else 0, 0)
            )
            var = tk.StringVar(value="--")
            setattr(self, attr, var)
            ttk.Label(eng_results, textvariable=var, style="Result.TLabel").grid(
                row=2 * r + 1, column=c, sticky="w"
            )

        #Injector results panel

        results = ttk.Labelframe(left, text="Injector Results", padding=12, style="Section.TLabelframe")
        results.grid(row=13, column=0, sticky="ew", pady=(0, 20))
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

        #Plot panel, docked permanently on the right, updated in place

        self._init_plot_area(right)

        self._set_engine_mode()  # apply the initial (off) enabled/disabled state
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
            self.widgets[key] = entry
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

    def _set_engine_mode(self):
        """Grey the engine/chamber fields in or out, and grey the mass-flow
        fields the other way (they're computed automatically when engine
        sizing is on)."""
        enabled = self.engine_mode_var.get()

        for key, _, _, _ in ENGINE_ALL_FIELDS:
            w = self.widgets.get(key)
            if w is not None:
                w.configure(state="normal" if enabled else "disabled")

        for key in AUTO_FILLED_BY_ENGINE:
            w = self.widgets.get(key)
            if w is not None:
                w.configure(state="disabled" if enabled else "normal")

        self.engine_mode_note_var.set(
            "IPA / N2O mass flow rates below are computed automatically from the "
            "target thrust and O/F ratio."
            if enabled else
            "Off: enter IPA / N2O mass flow rates manually below."
        )

    
    #Actions
    
    def on_reset(self):
        for key, _, _, default in ALL_FIELDS + ENGINE_ALL_FIELDS:
            self.vars[key].set(default)
        self.engine_mode_var.set(False)
        self._set_engine_mode()
        self.status_var.set("")
        self.warning_var.set("")
        self.ipa_coax_var.set("--")
        self.ipa_impinge_var.set("--")
        self.n2o_coax_var.set("--")
        self.n2o_impinge_var.set("--")
        self._update_engine_results_display(None, None)
        self._last_inputs = None
        self._last_results = None
        self._draw_placeholder()
        self.fig.tight_layout()
        self.canvas.draw()

    def _update_engine_results_display(self, engine, chamber):
        """Refresh the Engine & Chamber Results panel. Pass None, None to clear it."""
        if engine is None or chamber is None:
            for attr in ("thrust_var", "isp_var", "cstar_var", "cf_var", "dt_var", "de_var",
                        "eps_var", "dc_var", "cr_var", "lcyl_var", "split_var", "stay_var"):
                getattr(self, attr).set("--")
            return

        self.thrust_var.set(f"{engine['F_target']:.1f} N")
        self.isp_var.set(f"{engine['Isp']:.1f} s")
        self.cstar_var.set(f"{engine['cstar']:.0f} m/s")
        self.cf_var.set(f"{engine['CF']:.3f}")
        self.dt_var.set(f"{engine['Dt_mm']:.2f} mm")
        self.de_var.set(f"{engine['De_mm']:.2f} mm")
        self.eps_var.set(f"{engine['epsilon']:.2f}")
        self.dc_var.set(f"{chamber['Dc_mm']:.2f} mm")
        self.cr_var.set(f"{chamber['contraction_ratio']:.2f} ({chamber['contraction_ratio_source']})")
        self.lcyl_var.set(f"{chamber['L_cyl_mm']:.1f} mm  (L/D {chamber['L_over_D']:.2f})")
        self.split_var.set(f"{engine['mdot_ox']*1000:.2f} / {engine['mdot_fuel']*1000:.2f} g/s")
        self.stay_var.set(f"{engine['stay_time_s']*1000:.2f} ms")

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

    def _read_engine_inputs(self):
        """Read + validate the Engine Performance Targets / Chamber & Nozzle
        Geometry fields. Only called when engine sizing is switched on."""
        values = {}
        for key, label, _, _ in ENGINE_ALL_FIELDS:
            raw = self.vars[key].get().strip()
            if key == "contraction_ratio" and raw == "":
                values[key] = None   #blank -> Chamber.py estimates it automatically
                continue
            try:
                values[key] = float(raw)
            except ValueError:
                raise ValueError(f"'{label}' must be a number (got '{raw}').")

        if values["F_target"] <= 0:
            raise ValueError("Target Thrust must be greater than 0.")
        if values["P_a"] < 0:
            raise ValueError("Ambient Pressure cannot be negative.")
        if values["OF_ratio"] <= 0:
            raise ValueError("O/F Ratio must be greater than 0.")
        if values["Tc"] <= 0:
            raise ValueError("Chamber Temperature must be greater than 0.")
        if values["Gamma_gas"] <= 1:
            raise ValueError("Combustion Gamma must be greater than 1.")
        if values["MW_gas"] <= 0:
            raise ValueError("Combustion Molecular Weight must be greater than 0.")
        if not (0 < values["eta_cstar"] <= 1):
            raise ValueError("c* Efficiency must be between 0 and 1.")
        if not (0 < values["eta_cf"] <= 1):
            raise ValueError("CF Efficiency must be between 0 and 1.")
        if values["L_star"] <= 0:
            raise ValueError("Characteristic Length L* must be greater than 0.")
        if values["contraction_ratio"] is not None and values["contraction_ratio"] <= 1:
            raise ValueError(
                "Contraction Ratio must be greater than 1 (or left blank for an estimate)."
            )
        if not (5 <= values["conv_half_angle_deg"] <= 85):
            raise ValueError("Convergent Half-Angle must be between 5 and 85 degrees.")
        if not (5 <= values["nozzle_half_angle_deg"] <= 45):
            raise ValueError("Divergent Half-Angle must be between 5 and 45 degrees.")

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
        warnings = []
        try:
            v = self._read_inputs()
            engine_v = self._read_engine_inputs() if self.engine_mode_var.get() else None
        except ValueError as e:
            self.status_var.set(str(e))
            messagebox.showerror("Input Error", str(e))
            return

        engine_results = chamber_results = nozzle_results = None
        try:
            if engine_v is not None:
                #Engine.py: size the throat/exit for the target thrust
                engine_results = SizeEngine(
                    engine_v["F_target"], v["P_c"], engine_v["P_a"], engine_v["Tc"],
                    engine_v["Gamma_gas"], engine_v["MW_gas"],
                    engine_v["eta_cstar"], engine_v["eta_cf"],
                )
                mdot_ox, mdot_fuel = SplitMassFlow(engine_results["mdot"], engine_v["OF_ratio"])
                engine_results["F_target"] = engine_v["F_target"]
                engine_results["mdot_ox"] = mdot_ox
                engine_results["mdot_fuel"] = mdot_fuel

                #Overwrite the manual mass-flow inputs with the engine-derived
                #values, and reflect that back into the (disabled) entry fields
                #so it's clear where the numbers came from.
                v["m_dot_IPA"] = mdot_fuel
                v["m_dot_N2O"] = mdot_ox
                self.vars["m_dot_IPA"].set(f"{mdot_fuel:.6f}")
                self.vars["m_dot_N2O"].set(f"{mdot_ox:.6f}")

                #Chamber.py: size the chamber and nozzle from At
                chamber_results = SizeChamber(
                    engine_results["At"], engine_v["L_star"],
                    engine_v["contraction_ratio"], engine_v["conv_half_angle_deg"],
                )
                nozzle_results = SizeNozzle(
                    engine_results["At"], engine_results["epsilon"],
                    engine_v["nozzle_half_angle_deg"],
                )
                engine_results["stay_time_s"] = StayTime(
                    engine_v["L_star"], engine_results["cstar"], engine_results["R_gas"], engine_v["Tc"]
                )
                if chamber_results["L_over_D"] > 4.0 or chamber_results["L_over_D"] < 0.5:
                    warnings.append(
                        f"Chamber cylinder L/D is {chamber_results['L_over_D']:.1f}; typical "
                        "designs are roughly 1-3. Consider adjusting L* or the contraction ratio."
                    )
        except ValueError as e:
            self.status_var.set(str(e))
            messagebox.showerror("Engine Sizing Error", str(e))
            return
        except Exception as e:
            messagebox.showerror("Engine Sizing Error", f"Engine/chamber sizing failed:\n{e}")
            return

        try:
            needle_od_m = v["IPA_needle_OD_mm"] / 1000.0

            #IPA: exact design-point results

            ipa_area_point = SPI(v["Cd_IPA"], v["m_dot_IPA"], v["Rho_IPA"], v["P_c"], v["P_feedsystem"])
            ipa_coax_point = Coaxial_IPA_Size(ipa_area_point)
            ipa_impinge_point = Impinging_IPA_Size(ipa_area_point, v["IPA_orifices"])

            #N2O: exact design-point results
            #Uses the N2O feed system pressure (not chamber pressure) as the
            #upstream pressure for the choked-flow relation.
            n2o_area_point = ChokedNitrousAreaRequired(
                v["m_dot_N2O"], v["Cd_N2O"], v["P_feedsystem_N2O"], v["Gamma_N2O"], v["R_N2O"], v["N2O_Temp"]
            )
            n2o_coax_point = Coaxial_Drill_Diameter_Nitrous(n2o_area_point, needle_od_m)
            n2o_impinge_point = Impinging_Nitrous_Size(n2o_area_point, v["N2O_orifices"])

            choke_status = ChokedFlowCriteria(v["Gamma_N2O"], v["P_feedsystem_N2O"], v["P_c"])
            if choke_status != "Choked Flow Applies":
                warnings.append(
                    "N2O flow is NOT choked at these conditions (chamber pressure too close "
                    "to feed pressure) - the choked-flow sizing model may not apply."
                )

            #Sensitivity curves vs Cd, for context
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
        if engine_v is not None:
            self._last_inputs["engine"] = dict(engine_v)
        self._last_results = {
            "ipa_coaxial_diameter_mm": ipa_coax_point,
            "ipa_impinging_diameter_per_hole_mm": ipa_impinge_point,
            "ipa_impinging_orifice_count": v["IPA_orifices"],
            "n2o_coaxial_drill_diameter_incl_needle_mm": n2o_coax_point,
            "n2o_impinging_diameter_per_hole_mm": n2o_impinge_point,
            "n2o_impinging_orifice_count": v["N2O_orifices"],
            "n2o_choked_flow_status": choke_status,
            "engine": engine_results,
            "chamber": chamber_results,
            "nozzle": nozzle_results,
        }

        self._update_engine_results_display(engine_results, chamber_results)

        if warnings:
            self.warning_var.set("  |  ".join(warnings))

        self._update_plots(
            ipa_cd_range, ipa_coax_curve, v["Cd_IPA"], ipa_coax_point,
            n2o_cd_range, n2o_coax_curve, v["Cd_N2O"], n2o_coax_point,
            chamber_results, nozzle_results,
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
            "Optionally sizes the engine (throat, exit, chamber, nozzle) from a "
            "target thrust using Engine.py / Chamber.py, then sizes coaxial and "
            "impinging IPA / N2O injector orifices from the resulting (or "
            "manually entered) mass flow rates.",
        )

    
    #Plotting
    
    def _init_plot_area(self, parent):
        self.fig = Figure(figsize=(6, 10), dpi=100)
        self.ax1 = self.fig.add_subplot(3, 1, 1)
        self.ax2 = self.fig.add_subplot(3, 1, 2)
        self.ax3 = self.fig.add_subplot(3, 1, 3)
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

        self.ax3.clear()
        self.ax3.set_title("Engine / Chamber Profile")
        self.ax3.text(
            0.5, 0.5,
            "Enable 'Design engine from target thrust' above\nand click Calculate "
            "to view the chamber/nozzle profile",
            ha="center", va="center", transform=self.ax3.transAxes, color="#999999",
        )
        self.ax3.set_xticks([])
        self.ax3.set_yticks([])

    def _update_plots(
        self,
        ipa_cd_range, ipa_curve, ipa_cd_point, ipa_point,
        n2o_cd_range, n2o_curve, n2o_cd_point, n2o_point,
        chamber_results=None, nozzle_results=None,
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

        self.ax3.clear()
        if chamber_results is not None and nozzle_results is not None:
            self._draw_chamber_profile(chamber_results, nozzle_results)
        else:
            self.ax3.set_title("Engine / Chamber Profile")
            self.ax3.text(
                0.5, 0.5,
                "Enable 'Design engine from target thrust' above to view this profile",
                ha="center", va="center", transform=self.ax3.transAxes, color="#999999",
            )
            self.ax3.set_xticks([])
            self.ax3.set_yticks([])

        self.fig.tight_layout()
        self.canvas.draw()

    def _draw_chamber_profile(self, chamber, nozzle):
        """Draw a simple axisymmetric wall profile: cylinder -> convergent cone
        -> throat -> divergent cone, mirrored about the centerline."""
        Rc_mm = chamber["Rc_m"] * 1000
        Rt_mm = chamber["Rt_m"] * 1000
        Re_mm = nozzle["Re_m"] * 1000
        L_cyl = chamber["L_cyl_mm"]
        L_conv = chamber["L_conv_mm"]
        L_cone = nozzle["L_cone_mm"]

        x = [0.0, L_cyl, L_cyl + L_conv, L_cyl + L_conv + L_cone]
        r = [Rc_mm, Rc_mm, Rt_mm, Re_mm]
        r_neg = [-v for v in r]

        ax = self.ax3
        ax.fill_between(x, r, r_neg, color="#dfe6ee")
        ax.plot(x, r, color="black", lw=1.5)
        ax.plot(x, r_neg, color="black", lw=1.5)
        ax.axvline(0, color="#1f77b4", lw=2.5)
        ax.text(0, Rc_mm * 1.1, "injector face", color="#1f77b4", ha="left", va="bottom", fontsize=8)
        x_throat = L_cyl + L_conv
        ax.axvline(x_throat, color="#888888", ls="--", lw=1)
        ax.text(x_throat, -Rc_mm * 1.05, "throat", ha="center", va="top", color="#555555", fontsize=8)

        span = x[-1] - x[0]
        rmax = max(r)
        ax.set_xlim(-0.06 * span, 1.06 * span)
        ax.set_ylim(-1.3 * rmax, 1.3 * rmax)
        ax.set_title(
            f"Chamber Dc {2*Rc_mm:.1f} mm x {L_cyl:.0f} mm  |  throat Dt {2*Rt_mm:.2f} mm  |  "
            f"exit De {2*Re_mm:.1f} mm"
        )
        ax.set_xlabel("Axial position (mm)")
        ax.set_ylabel("Radius (mm)")
        ax.set_aspect("equal", adjustable="box")
        ax.grid(True, alpha=0.25)


if __name__ == "__main__":
    root = tk.Tk()
    app = InjectorSizingApp(root)
    root.mainloop()
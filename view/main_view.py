"""
MainView – tkinter/ttk GUI for the ACSR Transmission Line Calculator.

New in v2.0:
  • Line configuration selector: Transpuesta / No Transpuesta / Doble Circuito
  • Double-circuit: extra input for inter-circuit separation
  • Results panel expanded: capacitance C, reactance Xc, per-phase L/C for untransposed
"""

import tkinter as tk
from tkinter import ttk, messagebox

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
_C_TITLE   = "#1a3a5c"
_C_VALUE   = "#005a9c"
_C_RESULT  = "#006633"
_C_SUBTLE  = "#666666"
_C_PHASE   = "#7a3000"   # per-phase results (untransposed)

CFG_TRANSPOSED   = "transposed"
CFG_UNTRANSPOSED = "untransposed"
CFG_DOUBLE       = "double"


class MainView(tk.Tk):
    APP_TITLE   = "Calculadora de Líneas de Transmisión ACSR"
    APP_VERSION = "v2.0"

    def __init__(self):
        super().__init__()
        self.title(f"{self.APP_TITLE}  {self.APP_VERSION}")
        self.resizable(False, False)

        self._controller = None
        self._init_variables()
        self._apply_style()
        self._build_ui()

    # ------------------------------------------------------------------
    # Public API used by the controller
    # ------------------------------------------------------------------

    def set_controller(self, controller):
        self._controller = controller

    def populate_calibre_list(self, calibres):
        self._combo_calibre["values"] = calibres

    def populate_ratio_list(self, ratios, auto_select=None):
        self._combo_ratio["values"] = ratios
        self._combo_ratio.config(state="readonly")
        if auto_select is not None:
            self._ratio_var.set(auto_select)

    def populate_conductor_list(self, codes, auto_select=None):
        self._combo_conductor["values"] = codes
        self._combo_conductor.config(state="readonly")
        if auto_select is not None:
            self._conductor_var.set(auto_select)

    def display_conductor_info(self, name, rmg, r_base):
        self._info_name_var.set(name)
        self._info_rmg_var.set(rmg)
        self._info_r_var.set(r_base)
        self._btn_confirm.config(state="normal")

    def display_results(self, results: dict):
        """Push all result fields to the GUI. Handles all configurations."""
        self._res_config_var.set(results.get("config", "---"))
        self._res_dmg_var.set(results.get("dmg",      "---"))
        self._res_rmg_haz_var.set(results.get("rmg_haz",  "---"))
        self._res_r_bundle_var.set(results.get("r_bundle", "---"))
        self._res_L_var.set(results.get("L_mH_km",  "---"))
        self._res_XL_km_var.set(results.get("XL_km",    "---"))
        self._res_R_corr_var.set(results.get("R_corr",   "---"))
        self._res_XL_tot_var.set(results.get("XL_total", "---"))
        self._res_C_var.set(results.get("C_nF_km",  "---"))
        self._res_Xc_km_var.set(results.get("Xc_km",    "---"))
        self._res_Xc_tot_var.set(results.get("Xc_total", "---"))

        # Per-phase results (only for untransposed)
        has_per_phase = results.get("La") is not None
        self._per_phase_frame.grid() if has_per_phase else self._per_phase_frame.grid_remove()

        if has_per_phase:
            self._res_La_var.set(results.get("La",  "---"))
            self._res_Lb_var.set(results.get("Lb",  "---"))
            self._res_Lc_var.set(results.get("Lc",  "---"))
            self._res_XLa_var.set(results.get("XLa", "---"))
            self._res_XLb_var.set(results.get("XLb", "---"))
            self._res_XLc_var.set(results.get("XLc", "---"))
            self._res_Ca_var.set(results.get("Ca",  "---"))
            self._res_Cb_var.set(results.get("Cb",  "---"))
            self._res_Cc_var.set(results.get("Cc",  "---"))
            self._res_Xca_var.set(results.get("Xca", "---"))
            self._res_Xcb_var.set(results.get("Xcb", "---"))
            self._res_Xcc_var.set(results.get("Xcc", "---"))

    def get_line_params(self) -> dict:
        return {
            "config":    self._config_var.get(),
            "freq":      self._freq_var.get(),
            "length":    self._length_var.get(),
            "temp":      self._temp_var.get(),
            "n_cond":    self._n_cond_var.get(),
            "spacing":   self._spacing_var.get(),
            "D12":       self._d12_var.get(),
            "D23":       self._d23_var.get(),
            "D31":       self._d31_var.get(),
            "D_between": self._d_between_var.get(),
        }

    def get_search_code(self):
        return self._search_code_var.get()

    def get_selected_ratio(self):
        return self._ratio_var.get()

    def get_selected_calibre(self):
        return self._calibre_var.get()

    def get_selected_conductor(self):
        return self._conductor_var.get()

    def show_error(self, title, message):
        messagebox.showerror(title, message, parent=self)

    def show_info(self, title, message):
        messagebox.showinfo(title, message, parent=self)

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------

    def _init_variables(self):
        self._method_var     = tk.IntVar(value=2)
        self._search_code_var = tk.StringVar()
        self._calibre_var    = tk.StringVar()
        self._ratio_var      = tk.StringVar()
        self._conductor_var  = tk.StringVar()

        self._info_name_var  = tk.StringVar(value="---")
        self._info_rmg_var   = tk.StringVar(value="---")
        self._info_r_var     = tk.StringVar(value="---")

        # Line configuration
        self._config_var     = tk.StringVar(value=CFG_TRANSPOSED)

        # Line parameters
        self._freq_var       = tk.StringVar(value="60")
        self._length_var     = tk.StringVar(value="100")
        self._temp_var       = tk.StringVar(value="75")
        self._n_cond_var     = tk.IntVar(value=1)
        self._spacing_var    = tk.StringVar(value="0.40")
        self._d12_var        = tk.StringVar(value="6.0")
        self._d23_var        = tk.StringVar(value="6.0")
        self._d31_var        = tk.StringVar(value="6.0")
        self._d_between_var  = tk.StringVar(value="8.0")

        # Results – averaged / equivalent
        self._res_config_var  = tk.StringVar(value="---")
        self._res_dmg_var     = tk.StringVar(value="---")
        self._res_rmg_haz_var = tk.StringVar(value="---")
        self._res_r_bundle_var = tk.StringVar(value="---")
        self._res_L_var       = tk.StringVar(value="---")
        self._res_XL_km_var   = tk.StringVar(value="---")
        self._res_R_corr_var  = tk.StringVar(value="---")
        self._res_XL_tot_var  = tk.StringVar(value="---")
        self._res_C_var       = tk.StringVar(value="---")
        self._res_Xc_km_var   = tk.StringVar(value="---")
        self._res_Xc_tot_var  = tk.StringVar(value="---")

        # Per-phase results (untransposed only)
        self._res_La_var  = tk.StringVar(value="---")
        self._res_Lb_var  = tk.StringVar(value="---")
        self._res_Lc_var  = tk.StringVar(value="---")
        self._res_XLa_var = tk.StringVar(value="---")
        self._res_XLb_var = tk.StringVar(value="---")
        self._res_XLc_var = tk.StringVar(value="---")
        self._res_Ca_var  = tk.StringVar(value="---")
        self._res_Cb_var  = tk.StringVar(value="---")
        self._res_Cc_var  = tk.StringVar(value="---")
        self._res_Xca_var = tk.StringVar(value="---")
        self._res_Xcb_var = tk.StringVar(value="---")
        self._res_Xcc_var = tk.StringVar(value="---")

    def _apply_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TLabelframe.Label",
                        font=("Helvetica", 10, "bold"), foreground=_C_TITLE)
        style.configure("Calc.TButton",
                        font=("Helvetica", 11, "bold"), foreground="white",
                        background="#005a9c", padding=6)
        style.map("Calc.TButton",
                  background=[("active", "#003f7a"), ("pressed", "#002f5a")])
        style.configure("Confirm.TButton",
                        font=("Helvetica", 9, "bold"), foreground="white",
                        background="#006633", padding=4)
        style.map("Confirm.TButton",
                  background=[("active", "#004d26"), ("disabled", "#aaaaaa")])

    def _build_ui(self):
        outer = ttk.Frame(self, padding=12)
        outer.grid(row=0, column=0, sticky="nsew")

        ttk.Label(outer, text=self.APP_TITLE,
                  font=("Helvetica", 14, "bold"),
                  foreground=_C_TITLE).grid(row=0, column=0, pady=(0, 10))

        self._build_catalog_section(outer, row=1)
        self._build_params_section(outer, row=2)

        ttk.Button(outer, text="▶   CALCULAR PARÁMETROS",
                   style="Calc.TButton",
                   command=self._evt_calculate
                   ).grid(row=3, column=0, sticky="ew", pady=10, ipady=4)

        self._build_results_section(outer, row=4)

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _build_catalog_section(self, parent, row):
        frame = ttk.LabelFrame(parent, text="Catálogo ACSR", padding=8)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 6))

        radio_frame = ttk.Frame(frame)
        radio_frame.grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(radio_frame, text="Método 1: Búsqueda Directa",
                        variable=self._method_var, value=1,
                        command=self._evt_toggle_method).grid(row=0, column=0, padx=(0, 24))
        ttk.Radiobutton(radio_frame, text="Método 2: Filtrado en Cascada",
                        variable=self._method_var, value=2,
                        command=self._evt_toggle_method).grid(row=0, column=1)

        ttk.Separator(frame, orient="horizontal").grid(row=1, column=0, sticky="ew", pady=6)

        # Method 1
        self._m1_frame = ttk.Frame(frame)
        self._m1_frame.grid(row=2, column=0, sticky="w")
        ttk.Label(self._m1_frame, text="Código del conductor:").grid(row=0, column=0, padx=(0, 6))
        self._entry_code = ttk.Entry(self._m1_frame,
                                     textvariable=self._search_code_var, width=22)
        self._entry_code.grid(row=0, column=1, padx=(0, 6))
        self._entry_code.bind("<Return>", lambda _e: self._evt_search())
        ttk.Button(self._m1_frame, text="Buscar",
                   command=self._evt_search).grid(row=0, column=2)

        # Method 2
        self._m2_frame = ttk.Frame(frame)
        self._m2_frame.grid(row=3, column=0, sticky="w")
        ttk.Label(self._m2_frame, text="Calibre (AWG/kcmil):").grid(row=0, column=0, padx=(0, 4))
        self._combo_calibre = ttk.Combobox(self._m2_frame,
                                            textvariable=self._calibre_var,
                                            width=10, state="readonly")
        self._combo_calibre.grid(row=0, column=1, padx=(0, 16))
        self._combo_calibre.bind("<<ComboboxSelected>>", self._evt_calibre_selected)

        ttk.Label(self._m2_frame, text="Hilos Al/Ac:").grid(row=0, column=2, padx=(0, 4))
        self._combo_ratio = ttk.Combobox(self._m2_frame,
                                          textvariable=self._ratio_var,
                                          width=8, state="disabled")
        self._combo_ratio.grid(row=0, column=3, padx=(0, 16))
        self._combo_ratio.bind("<<ComboboxSelected>>", self._evt_ratio_selected)

        ttk.Label(self._m2_frame, text="Conductor:").grid(row=0, column=4, padx=(0, 4))
        self._combo_conductor = ttk.Combobox(self._m2_frame,
                                              textvariable=self._conductor_var,
                                              width=16, state="disabled")
        self._combo_conductor.grid(row=0, column=5)
        self._combo_conductor.bind("<<ComboboxSelected>>",
                                   self._evt_conductor_cascade_selected)

        ttk.Separator(frame, orient="horizontal").grid(row=4, column=0, sticky="ew", pady=6)

        # Conductor info
        info_frame = ttk.Frame(frame)
        info_frame.grid(row=5, column=0, sticky="ew")
        ttk.Label(info_frame, text="Seleccionado:").grid(row=0, column=0, padx=(0, 4))
        ttk.Label(info_frame, textvariable=self._info_name_var,
                  font=("Helvetica", 10, "bold"), foreground=_C_VALUE,
                  width=16).grid(row=0, column=1, padx=(0, 20))
        ttk.Label(info_frame, text="RMG:").grid(row=0, column=2, padx=(0, 4))
        ttk.Label(info_frame, textvariable=self._info_rmg_var,
                  foreground=_C_VALUE, width=8).grid(row=0, column=3)
        ttk.Label(info_frame, text="mm", foreground=_C_SUBTLE).grid(
            row=0, column=4, padx=(2, 20))
        ttk.Label(info_frame, text="R₀ (20 °C):").grid(row=0, column=5, padx=(0, 4))
        ttk.Label(info_frame, textvariable=self._info_r_var,
                  foreground=_C_VALUE, width=8).grid(row=0, column=6)
        ttk.Label(info_frame, text="Ω/km", foreground=_C_SUBTLE).grid(
            row=0, column=7, padx=(2, 20))
        self._btn_confirm = ttk.Button(info_frame, text="✓  Confirmar Conductor",
                                       style="Confirm.TButton",
                                       command=self._evt_confirm_conductor,
                                       state="disabled")
        self._btn_confirm.grid(row=0, column=8)

        self._evt_toggle_method()

    def _build_params_section(self, parent, row):
        frame = ttk.LabelFrame(parent, text="Parámetros de la Línea", padding=8)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 6))

        # Row 0: Configuration selector
        rCfg = ttk.Frame(frame)
        rCfg.grid(row=0, column=0, sticky="w", pady=3)
        ttk.Label(rCfg, text="Configuración de la línea:").grid(
            row=0, column=0, padx=(0, 12))
        for col_idx, (lbl, val) in enumerate([
            ("Transpuesta (simétrica/asimétrica)", CFG_TRANSPOSED),
            ("No Transpuesta",                     CFG_UNTRANSPOSED),
            ("Doble Circuito",                     CFG_DOUBLE),
        ]):
            ttk.Radiobutton(rCfg, text=lbl, variable=self._config_var, value=val,
                            command=self._evt_toggle_config).grid(
                row=0, column=col_idx + 1, padx=8)

        ttk.Separator(frame, orient="horizontal").grid(
            row=1, column=0, sticky="ew", pady=4)

        # Row 2: frequency, length, temperature
        rA = ttk.Frame(frame)
        rA.grid(row=2, column=0, sticky="w", pady=3)
        for col_idx, (lbl, var, width, hint) in enumerate([
            ("Frecuencia (Hz):", self._freq_var,  6, None),
            ("Longitud (km):",   self._length_var, 7, None),
            ("Temp. Op. (°C):",  self._temp_var,   6, "Tc Al = 228 °C"),
        ]):
            base = col_idx * 4
            ttk.Label(rA, text=lbl).grid(row=0, column=base, padx=(0, 4))
            ttk.Entry(rA, textvariable=var, width=width).grid(
                row=0, column=base + 1, padx=(0, 16))
            if hint:
                ttk.Label(rA, text=f"({hint})",
                          foreground=_C_SUBTLE).grid(row=0, column=base + 2, padx=(0, 8))

        # Row 3: bundle
        rB = ttk.Frame(frame)
        rB.grid(row=3, column=0, sticky="w", pady=3)
        ttk.Label(rB, text="Conductores/fase:").grid(row=0, column=0, padx=(0, 6))
        for i, n in enumerate([1, 2, 3, 4]):
            ttk.Radiobutton(rB, text=str(n), variable=self._n_cond_var, value=n,
                            command=self._evt_toggle_spacing).grid(
                row=0, column=i + 1, padx=4)
        ttk.Label(rB, text="Separación haz (m):").grid(
            row=0, column=6, padx=(20, 4))
        self._entry_spacing = ttk.Entry(rB, textvariable=self._spacing_var,
                                        width=7, state="disabled")
        self._entry_spacing.grid(row=0, column=7)

        # Row 4: phase distances
        rC = ttk.Frame(frame)
        rC.grid(row=4, column=0, sticky="w", pady=3)
        ttk.Label(rC, text="Distancias entre fases:").grid(
            row=0, column=0, padx=(0, 12))
        for col_idx, (lbl, var) in enumerate([
            ("D₁₂ (m):", self._d12_var),
            ("D₂₃ (m):", self._d23_var),
            ("D₃₁ (m):", self._d31_var),
        ]):
            base = col_idx * 3 + 1
            ttk.Label(rC, text=lbl).grid(row=0, column=base, padx=(0, 4))
            ttk.Entry(rC, textvariable=var, width=7).grid(
                row=0, column=base + 1, padx=(0, 16))

        # Row 5: double-circuit extra input (hidden unless CFG_DOUBLE)
        self._rDC = ttk.Frame(frame)
        self._rDC.grid(row=5, column=0, sticky="w", pady=3)
        ttk.Label(self._rDC,
                  text="Separación entre circuitos D_entre (m):").grid(
            row=0, column=0, padx=(0, 8))
        ttk.Entry(self._rDC, textvariable=self._d_between_var, width=7).grid(
            row=0, column=1)
        ttk.Label(self._rDC,
                  text="(distancia entre conductores homólogos de ambos circuitos)",
                  foreground=_C_SUBTLE).grid(row=0, column=2, padx=(8, 0))

        self._evt_toggle_config()  # Set initial visibility

    def _build_results_section(self, parent, row):
        frame = ttk.LabelFrame(parent, text="Resultados", padding=8)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 4))

        # Configuration label
        cfg_row = ttk.Frame(frame)
        cfg_row.grid(row=0, column=0, columnspan=12, sticky="w", pady=(0, 6))
        ttk.Label(cfg_row, text="Configuración calculada:").grid(
            row=0, column=0, padx=(0, 8))
        ttk.Label(cfg_row, textvariable=self._res_config_var,
                  font=("Helvetica", 10, "bold"),
                  foreground=_C_VALUE).grid(row=0, column=1)

        # ── Averaged / equivalent results ──────────────────────────────
        avg_frame = ttk.LabelFrame(frame, text="Parámetros equivalentes (promedio)", padding=6)
        avg_frame.grid(row=1, column=0, sticky="ew", pady=(0, 4))

        fields_row1 = [
            ("DMG:",           self._res_dmg_var,     "m"),
            ("RMG Haz (L):",   self._res_rmg_haz_var, "mm"),
            ("Radio Haz (C):", self._res_r_bundle_var, "mm"),
        ]
        fields_row2 = [
            ("Inductancia L:",  self._res_L_var,      "mH/km"),
            ("Reactancia XL:",  self._res_XL_km_var,  "Ω/km"),
            ("XL total:",       self._res_XL_tot_var, "Ω"),
        ]
        fields_row3 = [
            ("Capacitancia C:", self._res_C_var,      "nF/km"),
            ("Reactancia Xc:",  self._res_Xc_km_var,  "Ω·km"),
            ("Xc total:",       self._res_Xc_tot_var, "Ω"),
        ]
        fields_row4 = [
            ("R corregida:",    self._res_R_corr_var, "Ω/km"),
        ]

        for r_idx, row_fields in enumerate([fields_row1, fields_row2, fields_row3, fields_row4]):
            for c_idx, (lbl, var, unit) in enumerate(row_fields):
                gc = c_idx * 4
                ttk.Label(avg_frame, text=lbl, anchor="e", width=16).grid(
                    row=r_idx, column=gc, padx=(6, 4), pady=3, sticky="e")
                ttk.Label(avg_frame, textvariable=var,
                          font=("Courier New", 11, "bold"),
                          foreground=_C_RESULT, width=11, anchor="w").grid(
                    row=r_idx, column=gc + 1, sticky="w")
                ttk.Label(avg_frame, text=unit,
                          foreground=_C_SUBTLE).grid(
                    row=r_idx, column=gc + 2, padx=(2, 14), sticky="w")

        # ── Per-phase results (untransposed only) ──────────────────────
        self._per_phase_frame = ttk.LabelFrame(
            frame, text="Parámetros por fase (línea No Transpuesta)", padding=6)
        self._per_phase_frame.grid(row=2, column=0, sticky="ew", pady=(4, 0))
        self._per_phase_frame.grid_remove()   # hidden until untransposed is selected

        # Headers
        for col, txt in enumerate(["", "Fase A", "Fase B", "Fase C"]):
            ttk.Label(self._per_phase_frame, text=txt,
                      font=("Helvetica", 9, "bold"),
                      foreground=_C_TITLE, width=14, anchor="center").grid(
                row=0, column=col, padx=4)

        per_phase_rows = [
            ("L (mH/km):",    self._res_La_var,  self._res_Lb_var,  self._res_Lc_var),
            ("XL (Ω/km):",    self._res_XLa_var, self._res_XLb_var, self._res_XLc_var),
            ("C (nF/km):",    self._res_Ca_var,  self._res_Cb_var,  self._res_Cc_var),
            ("Xc (Ω·km):",    self._res_Xca_var, self._res_Xcb_var, self._res_Xcc_var),
        ]
        for r_idx, (lbl, va, vb, vc) in enumerate(per_phase_rows):
            ttk.Label(self._per_phase_frame, text=lbl,
                      anchor="e", width=14).grid(
                row=r_idx + 1, column=0, padx=(6, 4), pady=3, sticky="e")
            for c_idx, var in enumerate([va, vb, vc]):
                ttk.Label(self._per_phase_frame, textvariable=var,
                          font=("Courier New", 10, "bold"),
                          foreground=_C_PHASE, width=12, anchor="center").grid(
                    row=r_idx + 1, column=c_idx + 1, pady=3)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _evt_toggle_method(self):
        if self._method_var.get() == 1:
            self._m1_frame.grid()
            self._m2_frame.grid_remove()
        else:
            self._m1_frame.grid_remove()
            self._m2_frame.grid()

    def _evt_toggle_spacing(self):
        state = "normal" if self._n_cond_var.get() > 1 else "disabled"
        self._entry_spacing.config(state=state)

    def _evt_toggle_config(self):
        """Show/hide double-circuit distance row."""
        if self._config_var.get() == CFG_DOUBLE:
            self._rDC.grid()
        else:
            self._rDC.grid_remove()

    def _evt_search(self):
        if self._controller:
            self._controller.handle_search_by_code(self._search_code_var.get())

    def _evt_calibre_selected(self, _event=None):
        if self._controller:
            self._ratio_var.set("")
            self._combo_ratio.config(state="disabled", values=[])
            self._conductor_var.set("")
            self._combo_conductor.config(state="disabled", values=[])
            self._controller.handle_calibre_selected(self._calibre_var.get())

    def _evt_ratio_selected(self, _event=None):
        if self._controller:
            self._conductor_var.set("")
            self._combo_conductor.config(state="disabled", values=[])
            self._controller.handle_ratio_selected(
                self._calibre_var.get(), self._ratio_var.get())

    def _evt_conductor_cascade_selected(self, _event=None):
        if self._controller:
            self._controller.handle_conductor_selected(self._conductor_var.get())

    def _evt_confirm_conductor(self):
        if self._controller:
            self._controller.handle_confirm_conductor()

    def _evt_calculate(self):
        if self._controller:
            self._controller.handle_calculate()

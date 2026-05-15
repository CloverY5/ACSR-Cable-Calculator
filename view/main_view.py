"""
MainView – tkinter/ttk GUI for the ACSR Transmission Line Calculator.

Sections:
  1. Catálogo ACSR (conductor del circuito A / principal)
  2. Parámetros de la Línea
     - Configuración (transpuesta / no transpuesta / doble circuito)
     - Para doble circuito → botón "Configurar Doble Circuito" abre diálogo modal
  3. Resultados:
     ① Corrección de Resistencia por Temperatura
     ② Inductancia y Reactancia Inductiva
     ③ Capacitancia y Reactancia Capacitiva
     ④ Parámetros por fase (No Transpuesta)
     ⑤ Detalle de Doble Circuito (cuando aplica)
"""

import tkinter as tk
from tkinter import ttk, messagebox

# ── Colour palette ──────────────────────────────────────────────────────────
_C_TITLE   = "#1a3a5c"
_C_VALUE   = "#005a9c"
_C_RESULT  = "#006633"
_C_RES_R   = "#a04000"
_C_RES_L   = "#005a9c"
_C_RES_C   = "#6a1b9a"
_C_RES_D   = "#0d4f3c"   # double-circuit (dark green)
_C_SUBTLE  = "#666666"
_C_PHASE   = "#7a3000"

CFG_TRANSPOSED   = "transposed"
CFG_UNTRANSPOSED = "untransposed"
CFG_DOUBLE       = "double"


class MainView(tk.Tk):
    APP_TITLE   = "Calculadora de Líneas de Transmisión ACSR"
    APP_VERSION = "v4.0"

    def __init__(self):
        super().__init__()
        self.title(f"{self.APP_TITLE}  {self.APP_VERSION}")
        self.resizable(False, False)

        self._controller = None
        # Persistent storage for the double-circuit dialog state
        self._double_circuit_data = {
            "coords_A": [(0.0, 8.0), (0.0, 4.0), (0.0, 0.0)],   # default 3 conds
            "coords_B": [(8.0, 6.0), (8.0, 2.0)],                # default 2 conds
            "same_conductors": True,
            "side_A_type": "acsr",   # 'acsr' or 'solid'
            "side_A_radius_mm": "10.0",
            "side_B_type": "acsr",
            "side_B_radius_mm": "10.0",
        }
        self._init_variables()
        self._apply_style()
        self._build_ui()

    # ==================================================================
    # Public API used by the controller
    # ==================================================================

    def set_controller(self, controller):
        self._controller = controller

    def populate_calibre_list(self, calibres):
        self._combo_calibre["values"] = calibres

    def populate_calibre_list_b(self, calibres):
        # Stored for the dialog; the dialog populates from this when opened
        self._calibres_for_b = calibres

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

    def populate_ratio_list_b(self, ratios, auto_select=None):
        if hasattr(self, "_combo_ratio_b") and self._combo_ratio_b.winfo_exists():
            self._combo_ratio_b["values"] = ratios
            self._combo_ratio_b.config(state="readonly")
            if auto_select is not None:
                self._ratio_var_b.set(auto_select)

    def populate_conductor_list_b(self, codes, auto_select=None):
        if hasattr(self, "_combo_conductor_b") and self._combo_conductor_b.winfo_exists():
            self._combo_conductor_b["values"] = codes
            self._combo_conductor_b.config(state="readonly")
            if auto_select is not None:
                self._conductor_var_b.set(auto_select)

    def display_conductor_info(self, name, rmg, r_base):
        self._info_name_var.set(name)
        self._info_rmg_var.set(rmg)
        self._info_r_var.set(r_base)
        self._btn_confirm.config(state="normal")

    def display_conductor_info_b(self, name, rmg):
        if hasattr(self, "_info_name_b_var"):
            self._info_name_b_var.set(name)
            self._info_rmg_b_var.set(rmg)
            if hasattr(self, "_btn_confirm_b") and self._btn_confirm_b.winfo_exists():
                self._btn_confirm_b.config(state="normal")

    def display_results(self, results: dict):
        self._res_config_var.set(results.get("config", "---"))

        # Resistance
        res = results.get("res_data", {})
        self._r_n_al_var.set(str(res.get("n_al", "---")))
        self._r_d_al_var.set(f"{res.get('d_al_mm', 0):.3f}" if res else "---")
        self._r_A_al_var.set(f"{res.get('A_Al', 0):.4f}" if res else "---")
        self._r_f_al_var.set(f"×{res.get('factor_al', 0):.2f}" if res else "---")
        self._r_R20_al_var.set(f"{res.get('R20_Al', 0):.6f}" if res else "---")
        self._r_RT_al_var.set(f"{res.get('R_Al_T', 0):.6f}" if res else "---")

        self._r_n_ac_var.set(str(res.get("n_ac", "---")))
        self._r_d_ac_var.set(f"{res.get('d_ac_mm', 0):.3f}" if res else "---")
        self._r_A_ac_var.set(f"{res.get('A_Ac', 0):.4f}" if res else "---")
        self._r_f_ac_var.set(f"×{res.get('factor_ac', 0):.2f}" if res else "---")
        self._r_R20_ac_var.set(f"{res.get('R20_Ac', 0):.6f}" if res else "---")
        self._r_RT_ac_var.set(f"{res.get('R_Ac_T', 0):.6f}" if res else "---")

        self._r_Tfinal_var.set(f"{res.get('T_final', 0):.1f}" if res else "---")
        self._r_Rtot_var.set(results.get("R_TOT", "---"))
        self._r_Rline_var.set(results.get("R_total_line", "---"))

        # Inductance
        self._res_dmg_var.set(results.get("dmg", "---"))
        self._res_rmg_haz_var.set(results.get("rmg_haz", "---"))
        self._res_L_var.set(results.get("L_mH_km", "---"))
        self._res_XL_km_var.set(results.get("XL_km", "---"))
        self._res_XL_tot_var.set(results.get("XL_total", "---"))

        # Capacitance
        self._res_r_bundle_var.set(results.get("r_bundle", "---"))
        self._res_C_var.set(results.get("C_nF_km", "---"))
        self._res_Xc_km_var.set(results.get("Xc_km", "---"))
        self._res_Xc_tot_var.set(results.get("Xc_total", "---"))

        # Per-phase
        has_pp = results.get("La") is not None
        self._per_phase_frame.grid() if has_pp else self._per_phase_frame.grid_remove()
        if has_pp:
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

        # Double-circuit details
        d_info = results.get("double_info")
        if d_info:
            self._double_frame.grid()
            self._dc_name_a_var.set(d_info["name_A"])
            self._dc_name_b_var.set(d_info["name_B"])
            self._dc_same_var.set("Iguales" if d_info["same"] else "Distintos")
            self._dc_n_a_var.set(str(d_info["n_A"]))
            self._dc_n_b_var.set(str(d_info["n_B"]))
            self._dc_rmg_a_var.set(d_info["RMG_A"])
            self._dc_rmg_b_var.set(d_info["RMG_B"])
            self._dc_dmg_var.set(d_info["DMG"])
            self._dc_la_var.set(d_info["L_A"])
            self._dc_lb_var.set(d_info["L_B"])
            self._dc_ca_var.set(d_info["C_A"])
            self._dc_cb_var.set(d_info["C_B"])
        else:
            self._double_frame.grid_remove()

    def get_line_params(self):
        base = {
            "config":    self._config_var.get(),
            "freq":      self._freq_var.get(),
            "length":    self._length_var.get(),
            "temp":      self._temp_var.get(),
            "n_cond":    self._n_cond_var.get(),
            "spacing":   self._spacing_var.get(),
            "D12":       self._d12_var.get(),
            "D23":       self._d23_var.get(),
            "D31":       self._d31_var.get(),
        }
        # Pass dialog state for double circuit
        base.update({
            "coords_A":         list(self._double_circuit_data["coords_A"]),
            "coords_B":         list(self._double_circuit_data["coords_B"]),
            "same_conductors":  self._double_circuit_data["same_conductors"],
            "side_A_type":      self._double_circuit_data["side_A_type"],
            "side_A_radius_mm": self._double_circuit_data["side_A_radius_mm"],
            "side_B_type":      self._double_circuit_data["side_B_type"],
            "side_B_radius_mm": self._double_circuit_data["side_B_radius_mm"],
        })
        return base

    def show_error(self, title, message):
        messagebox.showerror(title, message, parent=self)

    def show_info(self, title, message):
        messagebox.showinfo(title, message, parent=self)

    # ==================================================================
    # Initialisation
    # ==================================================================

    def _init_variables(self):
        self._method_var      = tk.IntVar(value=2)
        self._search_code_var = tk.StringVar()
        self._calibre_var     = tk.StringVar()
        self._ratio_var       = tk.StringVar()
        self._conductor_var   = tk.StringVar()

        self._info_name_var = tk.StringVar(value="---")
        self._info_rmg_var  = tk.StringVar(value="---")
        self._info_r_var    = tk.StringVar(value="---")

        self._config_var    = tk.StringVar(value=CFG_TRANSPOSED)

        self._freq_var      = tk.StringVar(value="60")
        self._length_var    = tk.StringVar(value="100")
        self._temp_var      = tk.StringVar(value="75")
        self._n_cond_var    = tk.IntVar(value=1)
        self._spacing_var   = tk.StringVar(value="0.40")
        self._d12_var       = tk.StringVar(value="6.0")
        self._d23_var       = tk.StringVar(value="6.0")
        self._d31_var       = tk.StringVar(value="6.0")

        self._dc_status_var = tk.StringVar(value="(usar valores por defecto)")

        # Result variables
        self._res_config_var = tk.StringVar(value="---")

        self._r_n_al_var   = tk.StringVar(value="---")
        self._r_d_al_var   = tk.StringVar(value="---")
        self._r_A_al_var   = tk.StringVar(value="---")
        self._r_f_al_var   = tk.StringVar(value="---")
        self._r_R20_al_var = tk.StringVar(value="---")
        self._r_RT_al_var  = tk.StringVar(value="---")
        self._r_n_ac_var   = tk.StringVar(value="---")
        self._r_d_ac_var   = tk.StringVar(value="---")
        self._r_A_ac_var   = tk.StringVar(value="---")
        self._r_f_ac_var   = tk.StringVar(value="---")
        self._r_R20_ac_var = tk.StringVar(value="---")
        self._r_RT_ac_var  = tk.StringVar(value="---")
        self._r_Tfinal_var = tk.StringVar(value="---")
        self._r_Rtot_var   = tk.StringVar(value="---")
        self._r_Rline_var  = tk.StringVar(value="---")

        self._res_dmg_var     = tk.StringVar(value="---")
        self._res_rmg_haz_var = tk.StringVar(value="---")
        self._res_L_var       = tk.StringVar(value="---")
        self._res_XL_km_var   = tk.StringVar(value="---")
        self._res_XL_tot_var  = tk.StringVar(value="---")

        self._res_r_bundle_var = tk.StringVar(value="---")
        self._res_C_var        = tk.StringVar(value="---")
        self._res_Xc_km_var    = tk.StringVar(value="---")
        self._res_Xc_tot_var   = tk.StringVar(value="---")

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

        # Double-circuit details panel
        self._dc_name_a_var = tk.StringVar(value="---")
        self._dc_name_b_var = tk.StringVar(value="---")
        self._dc_same_var   = tk.StringVar(value="---")
        self._dc_n_a_var    = tk.StringVar(value="---")
        self._dc_n_b_var    = tk.StringVar(value="---")
        self._dc_rmg_a_var  = tk.StringVar(value="---")
        self._dc_rmg_b_var  = tk.StringVar(value="---")
        self._dc_dmg_var    = tk.StringVar(value="---")
        self._dc_la_var     = tk.StringVar(value="---")
        self._dc_lb_var     = tk.StringVar(value="---")
        self._dc_ca_var     = tk.StringVar(value="---")
        self._dc_cb_var     = tk.StringVar(value="---")

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
        style.configure("Dialog.TButton",
                        font=("Helvetica", 9, "bold"), foreground="white",
                        background="#0d4f3c", padding=4)
        style.map("Dialog.TButton",
                  background=[("active", "#093526")])

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

    # ==================================================================
    # Catalog section
    # ==================================================================

    def _build_catalog_section(self, parent, row):
        frame = ttk.LabelFrame(parent, text="Catálogo ACSR — Conductor principal (Circuito A)", padding=8)
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

        self._m1_frame = ttk.Frame(frame)
        self._m1_frame.grid(row=2, column=0, sticky="w")
        ttk.Label(self._m1_frame, text="Código del conductor:").grid(row=0, column=0, padx=(0, 6))
        self._entry_code = ttk.Entry(self._m1_frame,
                                     textvariable=self._search_code_var, width=22)
        self._entry_code.grid(row=0, column=1, padx=(0, 6))
        self._entry_code.bind("<Return>", lambda _e: self._evt_search())
        ttk.Button(self._m1_frame, text="Buscar",
                   command=self._evt_search).grid(row=0, column=2)

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
        ttk.Label(info_frame, text="R₀ (cat., 20 °C):").grid(row=0, column=5, padx=(0, 4))
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

    # ==================================================================
    # Parameters section
    # ==================================================================

    def _build_params_section(self, parent, row):
        frame = ttk.LabelFrame(parent, text="Parámetros de la Línea", padding=8)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 6))

        rCfg = ttk.Frame(frame)
        rCfg.grid(row=0, column=0, sticky="w", pady=3)
        ttk.Label(rCfg, text="Configuración:").grid(row=0, column=0, padx=(0, 12))
        for col_idx, (lbl, val) in enumerate([
            ("Transpuesta (simétrica/asimétrica)", CFG_TRANSPOSED),
            ("No Transpuesta",                     CFG_UNTRANSPOSED),
            ("Doble Circuito / Paralelo",          CFG_DOUBLE),
        ]):
            ttk.Radiobutton(rCfg, text=lbl, variable=self._config_var, value=val,
                            command=self._evt_toggle_config).grid(
                row=0, column=col_idx + 1, padx=8)

        ttk.Separator(frame, orient="horizontal").grid(
            row=1, column=0, sticky="ew", pady=4)

        rA = ttk.Frame(frame)
        rA.grid(row=2, column=0, sticky="w", pady=3)
        for col_idx, (lbl, var, width, hint) in enumerate([
            ("Frecuencia (Hz):", self._freq_var,  6, None),
            ("Longitud (km):",   self._length_var, 7, None),
            ("Temp. Op. (°C):",  self._temp_var,   6, "T base = 20 °C"),
        ]):
            base = col_idx * 4
            ttk.Label(rA, text=lbl).grid(row=0, column=base, padx=(0, 4))
            ttk.Entry(rA, textvariable=var, width=width).grid(
                row=0, column=base + 1, padx=(0, 16))
            if hint:
                ttk.Label(rA, text=f"({hint})",
                          foreground=_C_SUBTLE).grid(row=0, column=base + 2, padx=(0, 8))

        # ── Single-circuit-only parameters ──
        self._single_frame = ttk.Frame(frame)
        self._single_frame.grid(row=3, column=0, sticky="w", pady=3)

        rB = ttk.Frame(self._single_frame)
        rB.grid(row=0, column=0, sticky="w", pady=3)
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

        rC = ttk.Frame(self._single_frame)
        rC.grid(row=1, column=0, sticky="w", pady=3)
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

        # ── Double-circuit area (button + status) ──
        self._double_setup_frame = ttk.Frame(frame)
        self._double_setup_frame.grid(row=4, column=0, sticky="w", pady=3)
        ttk.Label(self._double_setup_frame,
                  text="Configuración del Doble Circuito:",
                  font=("Helvetica", 9, "bold"),
                  foreground=_C_TITLE).grid(row=0, column=0, padx=(0, 12))
        ttk.Button(self._double_setup_frame,
                   text="⚙  Configurar Doble Circuito",
                   style="Dialog.TButton",
                   command=self._evt_open_double_dialog).grid(row=0, column=1, padx=(0, 12))
        ttk.Label(self._double_setup_frame,
                  textvariable=self._dc_status_var,
                  foreground=_C_SUBTLE,
                  font=("Helvetica", 9, "italic")).grid(row=0, column=2)

        self._evt_toggle_config()
        self._update_dc_status()

    # ==================================================================
    # Results section
    # ==================================================================

    def _build_results_section(self, parent, row):
        wrapper = ttk.Frame(parent)
        wrapper.grid(row=row, column=0, sticky="ew")

        cfg_row = ttk.Frame(wrapper)
        cfg_row.grid(row=0, column=0, sticky="w", pady=(0, 6))
        ttk.Label(cfg_row, text="Configuración calculada:",
                  font=("Helvetica", 10, "bold")).grid(row=0, column=0, padx=(0, 8))
        ttk.Label(cfg_row, textvariable=self._res_config_var,
                  font=("Helvetica", 10, "bold"),
                  foreground=_C_VALUE).grid(row=0, column=1)

        self._build_resistance_section(wrapper, row=1)
        self._build_inductance_section(wrapper, row=2)
        self._build_capacitance_section(wrapper, row=3)
        self._build_per_phase_section(wrapper, row=4)
        self._build_double_circuit_section(wrapper, row=5)

    def _build_resistance_section(self, parent, row):
        frame = ttk.LabelFrame(
            parent,
            text="① Corrección de Resistencia por Temperatura (ACSR)",
            padding=8,
        )
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 4))

        headers = ["", "Hilos", "Ø (mm)", "Área (mm²)", "Factor",
                   "R₂₀ (Ω/km)", "R(T) (Ω/km)"]
        for c, h in enumerate(headers):
            ttk.Label(frame, text=h,
                      font=("Helvetica", 9, "bold"),
                      foreground=_C_TITLE, anchor="center", width=12).grid(
                row=0, column=c, padx=3, pady=(0, 4))

        ttk.Label(frame, text="Aluminio (Al):",
                  anchor="e", width=14,
                  font=("Helvetica", 9, "bold"),
                  foreground=_C_RES_R).grid(
            row=1, column=0, sticky="e", padx=(4, 4), pady=2)
        for c, var in enumerate([self._r_n_al_var, self._r_d_al_var,
                                 self._r_A_al_var, self._r_f_al_var,
                                 self._r_R20_al_var, self._r_RT_al_var]):
            ttk.Label(frame, textvariable=var,
                      font=("Courier New", 10, "bold"),
                      foreground=_C_RES_R, anchor="center", width=12).grid(
                row=1, column=c + 1, pady=2)

        ttk.Label(frame, text="Acero (Ac):",
                  anchor="e", width=14,
                  font=("Helvetica", 9, "bold"),
                  foreground=_C_RES_R).grid(
            row=2, column=0, sticky="e", padx=(4, 4), pady=2)
        for c, var in enumerate([self._r_n_ac_var, self._r_d_ac_var,
                                 self._r_A_ac_var, self._r_f_ac_var,
                                 self._r_R20_ac_var, self._r_RT_ac_var]):
            ttk.Label(frame, textvariable=var,
                      font=("Courier New", 10, "bold"),
                      foreground=_C_RES_R, anchor="center", width=12).grid(
                row=2, column=c + 1, pady=2)

        ttk.Separator(frame, orient="horizontal").grid(
            row=3, column=0, columnspan=7, sticky="ew", pady=6)

        totals = ttk.Frame(frame)
        totals.grid(row=4, column=0, columnspan=7, sticky="w")
        ttk.Label(totals, text="T final:",
                  foreground=_C_SUBTLE).grid(row=0, column=0, padx=(0, 4))
        ttk.Label(totals, textvariable=self._r_Tfinal_var,
                  font=("Courier New", 10, "bold"),
                  foreground=_C_RES_R).grid(row=0, column=1, padx=(0, 4))
        ttk.Label(totals, text="°C", foreground=_C_SUBTLE).grid(
            row=0, column=2, padx=(0, 18))

        ttk.Label(totals, text="R_TOT:",
                  font=("Helvetica", 9, "bold"),
                  foreground=_C_TITLE).grid(row=0, column=3, padx=(0, 4))
        ttk.Label(totals, textvariable=self._r_Rtot_var,
                  font=("Courier New", 11, "bold"),
                  foreground=_C_RES_R, width=12).grid(row=0, column=4)
        ttk.Label(totals, text="Ω/km", foreground=_C_SUBTLE).grid(
            row=0, column=5, padx=(2, 18))

        ttk.Label(totals, text="R total línea:",
                  font=("Helvetica", 9, "bold"),
                  foreground=_C_TITLE).grid(row=0, column=6, padx=(0, 4))
        ttk.Label(totals, textvariable=self._r_Rline_var,
                  font=("Courier New", 11, "bold"),
                  foreground=_C_RES_R, width=12).grid(row=0, column=7)
        ttk.Label(totals, text="Ω", foreground=_C_SUBTLE).grid(
            row=0, column=8, padx=(2, 0))

    def _build_inductance_section(self, parent, row):
        frame = ttk.LabelFrame(
            parent, text="② Inductancia y Reactancia Inductiva", padding=8,
        )
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 4))

        fields = [
            ("DMG:",           self._res_dmg_var,    "m"),
            ("RMG Haz (L):",   self._res_rmg_haz_var, "mm"),
            ("Inductancia L:", self._res_L_var,      "mH/km"),
            ("Reactancia XL:", self._res_XL_km_var,  "Ω/km"),
            ("XL total:",      self._res_XL_tot_var, "Ω"),
        ]
        for idx, (lbl, var, unit) in enumerate(fields):
            r = idx // 3
            c = (idx % 3) * 4
            ttk.Label(frame, text=lbl, anchor="e", width=14).grid(
                row=r, column=c, padx=(6, 4), pady=3, sticky="e")
            ttk.Label(frame, textvariable=var,
                      font=("Courier New", 11, "bold"),
                      foreground=_C_RES_L, width=12, anchor="w").grid(
                row=r, column=c + 1, sticky="w")
            ttk.Label(frame, text=unit,
                      foreground=_C_SUBTLE).grid(row=r, column=c + 2, padx=(2, 14), sticky="w")

    def _build_capacitance_section(self, parent, row):
        frame = ttk.LabelFrame(
            parent, text="③ Capacitancia y Reactancia Capacitiva", padding=8,
        )
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 4))

        fields = [
            ("Radio Haz (C):",  self._res_r_bundle_var, "mm"),
            ("Capacitancia C:", self._res_C_var,        "nF/km"),
            ("Reactancia Xc:",  self._res_Xc_km_var,    "Ω·km"),
            ("Xc total:",       self._res_Xc_tot_var,   "Ω"),
        ]
        for idx, (lbl, var, unit) in enumerate(fields):
            r = idx // 3
            c = (idx % 3) * 4
            ttk.Label(frame, text=lbl, anchor="e", width=14).grid(
                row=r, column=c, padx=(6, 4), pady=3, sticky="e")
            ttk.Label(frame, textvariable=var,
                      font=("Courier New", 11, "bold"),
                      foreground=_C_RES_C, width=12, anchor="w").grid(
                row=r, column=c + 1, sticky="w")
            ttk.Label(frame, text=unit,
                      foreground=_C_SUBTLE).grid(row=r, column=c + 2, padx=(2, 14), sticky="w")

    def _build_per_phase_section(self, parent, row):
        self._per_phase_frame = ttk.LabelFrame(
            parent,
            text="④ Parámetros por fase (sólo para línea No Transpuesta)",
            padding=8,
        )
        self._per_phase_frame.grid(row=row, column=0, sticky="ew", pady=(0, 4))
        self._per_phase_frame.grid_remove()

        for col, txt in enumerate(["", "Fase A", "Fase B", "Fase C"]):
            ttk.Label(self._per_phase_frame, text=txt,
                      font=("Helvetica", 9, "bold"),
                      foreground=_C_TITLE, width=14, anchor="center").grid(
                row=0, column=col, padx=4)

        rows = [
            ("L (mH/km):", self._res_La_var,  self._res_Lb_var,  self._res_Lc_var),
            ("XL (Ω/km):", self._res_XLa_var, self._res_XLb_var, self._res_XLc_var),
            ("C (nF/km):", self._res_Ca_var,  self._res_Cb_var,  self._res_Cc_var),
            ("Xc (Ω·km):", self._res_Xca_var, self._res_Xcb_var, self._res_Xcc_var),
        ]
        for r_idx, (lbl, va, vb, vc) in enumerate(rows):
            ttk.Label(self._per_phase_frame, text=lbl,
                      anchor="e", width=14).grid(
                row=r_idx + 1, column=0, padx=(6, 4), pady=3, sticky="e")
            for c_idx, var in enumerate([va, vb, vc]):
                ttk.Label(self._per_phase_frame, textvariable=var,
                          font=("Courier New", 10, "bold"),
                          foreground=_C_PHASE, width=12, anchor="center").grid(
                    row=r_idx + 1, column=c_idx + 1, pady=3)

    def _build_double_circuit_section(self, parent, row):
        self._double_frame = ttk.LabelFrame(
            parent,
            text="⑤ Detalle de Doble Circuito (sólo para configuración Doble Circuito)",
            padding=8,
        )
        self._double_frame.grid(row=row, column=0, sticky="ew", pady=(0, 4))
        self._double_frame.grid_remove()

        # Headers
        for col, txt in enumerate(["", "Lado A", "Lado B"]):
            ttk.Label(self._double_frame, text=txt,
                      font=("Helvetica", 9, "bold"),
                      foreground=_C_TITLE, width=16, anchor="center").grid(
                row=0, column=col, padx=4, pady=(0, 4))

        rows = [
            ("Conductor:",        self._dc_name_a_var, self._dc_name_b_var),
            ("Nº conductores:",   self._dc_n_a_var,    self._dc_n_b_var),
            ("RMG del lado (m):", self._dc_rmg_a_var,  self._dc_rmg_b_var),
            ("L por lado (mH/km):", self._dc_la_var,   self._dc_lb_var),
            ("C por lado (nF/km):", self._dc_ca_var,   self._dc_cb_var),
        ]
        for r_idx, (lbl, va, vb) in enumerate(rows):
            ttk.Label(self._double_frame, text=lbl,
                      anchor="e", width=20).grid(
                row=r_idx + 1, column=0, padx=(6, 4), pady=2, sticky="e")
            for c_idx, var in enumerate([va, vb]):
                ttk.Label(self._double_frame, textvariable=var,
                          font=("Courier New", 10, "bold"),
                          foreground=_C_RES_D, width=16, anchor="center").grid(
                    row=r_idx + 1, column=c_idx + 1, pady=2)

        ttk.Separator(self._double_frame, orient="horizontal").grid(
            row=99, column=0, columnspan=3, sticky="ew", pady=6)

        totals = ttk.Frame(self._double_frame)
        totals.grid(row=100, column=0, columnspan=3, sticky="w")
        ttk.Label(totals, text="DMG entre lados:",
                  font=("Helvetica", 9, "bold"),
                  foreground=_C_TITLE).grid(row=0, column=0, padx=(0, 4))
        ttk.Label(totals, textvariable=self._dc_dmg_var,
                  font=("Courier New", 11, "bold"),
                  foreground=_C_RES_D).grid(row=0, column=1, padx=(0, 4))
        ttk.Label(totals, text="m", foreground=_C_SUBTLE).grid(
            row=0, column=2, padx=(0, 18))
        ttk.Label(totals, text="Tipo:",
                  foreground=_C_SUBTLE).grid(row=0, column=3, padx=(0, 4))
        ttk.Label(totals, textvariable=self._dc_same_var,
                  font=("Helvetica", 9, "bold"),
                  foreground=_C_RES_D).grid(row=0, column=4)

    # ==================================================================
    # Double-circuit configuration dialog
    # ==================================================================

    def _evt_open_double_dialog(self):
        DoubleCircuitDialog(self, self._double_circuit_data,
                            self._calibres_for_b,
                            self._controller,
                            on_save=self._on_double_saved)

    def _on_double_saved(self, new_data: dict):
        self._double_circuit_data.update(new_data)
        self._update_dc_status()

    def _update_dc_status(self):
        d = self._double_circuit_data
        nA = len(d["coords_A"])
        nB = len(d["coords_B"])
        same = "iguales" if d["same_conductors"] else "distintos"
        self._dc_status_var.set(
            f"Lado A: {nA} cond., Lado B: {nB} cond., conductores {same}"
        )

    # ==================================================================
    # Event handlers
    # ==================================================================

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
        cfg = self._config_var.get()
        if cfg == CFG_DOUBLE:
            self._single_frame.grid_remove()
            self._double_setup_frame.grid()
        else:
            self._single_frame.grid()
            self._double_setup_frame.grid_remove()

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


# ===========================================================================
# DoubleCircuitDialog
# ===========================================================================

class DoubleCircuitDialog(tk.Toplevel):
    """Modal dialog to configure the double-circuit geometry."""

    def __init__(self, parent, current_data, calibres_for_b, controller, on_save):
        super().__init__(parent)
        self.title("Configuración del Doble Circuito")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._on_save = on_save
        self._controller = controller
        self._calibres = calibres_for_b

        # Copy current state (so cancel discards)
        self._data = {
            "coords_A": list(current_data["coords_A"]),
            "coords_B": list(current_data["coords_B"]),
            "same_conductors": current_data["same_conductors"],
            "side_A_type": current_data["side_A_type"],
            "side_A_radius_mm": current_data["side_A_radius_mm"],
            "side_B_type": current_data["side_B_type"],
            "side_B_radius_mm": current_data["side_B_radius_mm"],
        }

        self._same_var       = tk.BooleanVar(value=self._data["same_conductors"])
        self._sideA_type_var = tk.StringVar(value=self._data["side_A_type"])
        self._sideB_type_var = tk.StringVar(value=self._data["side_B_type"])
        self._sideA_r_var    = tk.StringVar(value=self._data["side_A_radius_mm"])
        self._sideB_r_var    = tk.StringVar(value=self._data["side_B_radius_mm"])

        self._calibre_b_var   = tk.StringVar()
        self._ratio_var_b     = tk.StringVar()
        self._conductor_var_b = tk.StringVar()

        self._build_ui()

        # Centre over parent
        self.update_idletasks()
        self.geometry(f"+{parent.winfo_rootx() + 50}+{parent.winfo_rooty() + 50}")

    def _build_ui(self):
        outer = ttk.Frame(self, padding=12)
        outer.grid(row=0, column=0)

        ttk.Label(outer, text="Configurar Doble Circuito / Conductores en Paralelo",
                  font=("Helvetica", 12, "bold"),
                  foreground=_C_TITLE).grid(row=0, column=0, columnspan=2, pady=(0, 10))

        # ── Same/different toggle ──
        toggle_frame = ttk.LabelFrame(outer, text="Tipo de conductores", padding=8)
        toggle_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        ttk.Checkbutton(toggle_frame,
                        text="Mismo conductor en ambos circuitos",
                        variable=self._same_var,
                        command=self._evt_same_toggle).grid(row=0, column=0, sticky="w")
        ttk.Label(toggle_frame,
                  text="(Si está marcado, el lado B usará el mismo conductor que el lado A)",
                  foreground=_C_SUBTLE,
                  font=("Helvetica", 8, "italic")).grid(
            row=1, column=0, sticky="w", padx=(20, 0))

        # ── Side A conductor type ──
        sideA_frame = ttk.LabelFrame(outer, text="Lado A (Circuito 1)", padding=8)
        sideA_frame.grid(row=2, column=0, sticky="nsew", padx=(0, 6), pady=(0, 6))

        ttk.Radiobutton(sideA_frame, text="ACSR (usar conductor principal del catálogo)",
                        variable=self._sideA_type_var, value="acsr",
                        command=self._evt_sideA_type).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Radiobutton(sideA_frame, text="Sólido (cobre u otro) - ingresar radio:",
                        variable=self._sideA_type_var, value="solid",
                        command=self._evt_sideA_type).grid(row=1, column=0, columnspan=2, sticky="w")

        rA_frame = ttk.Frame(sideA_frame)
        rA_frame.grid(row=2, column=0, sticky="w", padx=(20, 0))
        ttk.Label(rA_frame, text="Radio (mm):").grid(row=0, column=0)
        self._entry_rA = ttk.Entry(rA_frame, textvariable=self._sideA_r_var, width=8)
        self._entry_rA.grid(row=0, column=1, padx=(4, 0))

        # ── Side B conductor type ──
        self._sideB_frame = ttk.LabelFrame(outer, text="Lado B (Circuito 2)", padding=8)
        self._sideB_frame.grid(row=2, column=1, sticky="nsew", pady=(0, 6))

        ttk.Radiobutton(self._sideB_frame, text="ACSR (seleccionar del catálogo):",
                        variable=self._sideB_type_var, value="acsr",
                        command=self._evt_sideB_type).grid(row=0, column=0, columnspan=4, sticky="w")

        catB_frame = ttk.Frame(self._sideB_frame)
        catB_frame.grid(row=1, column=0, columnspan=4, sticky="w", padx=(20, 0))
        ttk.Label(catB_frame, text="Calibre:").grid(row=0, column=0, padx=(0, 4))
        self._combo_calibre_b = ttk.Combobox(catB_frame,
                                              textvariable=self._calibre_b_var,
                                              width=10, state="readonly",
                                              values=self._calibres or [])
        self._combo_calibre_b.grid(row=0, column=1, padx=(0, 8))
        self._combo_calibre_b.bind("<<ComboboxSelected>>", self._evt_calibre_b)

        ttk.Label(catB_frame, text="Cableado:").grid(row=0, column=2, padx=(0, 4))
        self._combo_ratio_b = ttk.Combobox(catB_frame,
                                            textvariable=self._ratio_var_b,
                                            width=7, state="disabled")
        self._combo_ratio_b.grid(row=0, column=3, padx=(0, 8))
        self._combo_ratio_b.bind("<<ComboboxSelected>>", self._evt_ratio_b)

        ttk.Label(catB_frame, text="Conductor:").grid(row=0, column=4, padx=(0, 4))
        self._combo_conductor_b = ttk.Combobox(catB_frame,
                                                textvariable=self._conductor_var_b,
                                                width=14, state="disabled")
        self._combo_conductor_b.grid(row=0, column=5)
        self._combo_conductor_b.bind("<<ComboboxSelected>>", self._evt_conductor_b)

        infoB = ttk.Frame(self._sideB_frame)
        infoB.grid(row=2, column=0, columnspan=4, sticky="w", padx=(20, 0), pady=4)
        self.master._info_name_b_var = tk.StringVar(value="---")
        self.master._info_rmg_b_var  = tk.StringVar(value="---")
        ttk.Label(infoB, text="Selección:",
                  foreground=_C_SUBTLE).grid(row=0, column=0, padx=(0, 4))
        ttk.Label(infoB, textvariable=self.master._info_name_b_var,
                  font=("Helvetica", 9, "bold"),
                  foreground=_C_VALUE, width=14).grid(row=0, column=1, padx=(0, 12))
        ttk.Label(infoB, text="RMG:",
                  foreground=_C_SUBTLE).grid(row=0, column=2, padx=(0, 4))
        ttk.Label(infoB, textvariable=self.master._info_rmg_b_var,
                  foreground=_C_VALUE, width=8).grid(row=0, column=3)
        ttk.Label(infoB, text="mm",
                  foreground=_C_SUBTLE).grid(row=0, column=4, padx=(2, 12))
        self.master._btn_confirm_b = ttk.Button(infoB,
            text="✓ Confirmar B",
            style="Confirm.TButton",
            command=lambda: self._controller.handle_confirm_conductor_b() if self._controller else None,
            state="disabled")
        self.master._btn_confirm_b.grid(row=0, column=5)

        ttk.Radiobutton(self._sideB_frame, text="Sólido - ingresar radio:",
                        variable=self._sideB_type_var, value="solid",
                        command=self._evt_sideB_type).grid(row=3, column=0, columnspan=4, sticky="w", pady=(6, 0))

        rB_frame = ttk.Frame(self._sideB_frame)
        rB_frame.grid(row=4, column=0, sticky="w", padx=(20, 0))
        ttk.Label(rB_frame, text="Radio (mm):").grid(row=0, column=0)
        self._entry_rB = ttk.Entry(rB_frame, textvariable=self._sideB_r_var, width=8)
        self._entry_rB.grid(row=0, column=1, padx=(4, 0))

        # ── Coordinates tables ──
        coords_label = ttk.Label(outer,
                                  text="Coordenadas (x, y) en metros — origen arbitrario",
                                  font=("Helvetica", 10, "bold"),
                                  foreground=_C_TITLE)
        coords_label.grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 4))

        self._coords_A_frame = self._build_coords_table(outer, "Lado A (Circuito 1)",
                                                        "A", self._data["coords_A"])
        self._coords_A_frame.grid(row=4, column=0, sticky="nsew", padx=(0, 6))

        self._coords_B_frame = self._build_coords_table(outer, "Lado B (Circuito 2)",
                                                        "B", self._data["coords_B"])
        self._coords_B_frame.grid(row=4, column=1, sticky="nsew")

        # ── Buttons ──
        btn_frame = ttk.Frame(outer)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=(12, 0))
        ttk.Button(btn_frame, text="Aceptar",
                   style="Calc.TButton",
                   command=self._evt_accept).grid(row=0, column=0, padx=4, ipadx=20)
        ttk.Button(btn_frame, text="Cancelar",
                   command=self.destroy).grid(row=0, column=1, padx=4, ipadx=12)

        # Initial state
        self._evt_same_toggle()
        self._evt_sideA_type()
        self._evt_sideB_type()

    def _build_coords_table(self, parent, label, side_id, initial_coords):
        frame = ttk.LabelFrame(parent, text=label, padding=6)

        headers = ["#", "x (m)", "y (m)"]
        for c, h in enumerate(headers):
            ttk.Label(frame, text=h, font=("Helvetica", 9, "bold"),
                      foreground=_C_TITLE, anchor="center", width=8).grid(
                row=0, column=c, padx=2, pady=(0, 4))

        # Store entry variables per row
        var_list = []   # list of (x_var, y_var)

        for row_idx, (x, y) in enumerate(initial_coords):
            xv = tk.StringVar(value=f"{x:g}")
            yv = tk.StringVar(value=f"{y:g}")
            var_list.append((xv, yv))
            ttk.Label(frame, text=str(row_idx + 1),
                      font=("Helvetica", 9, "bold"),
                      foreground=_C_VALUE).grid(row=row_idx + 1, column=0, pady=1)
            ttk.Entry(frame, textvariable=xv, width=8).grid(
                row=row_idx + 1, column=1, padx=2, pady=1)
            ttk.Entry(frame, textvariable=yv, width=8).grid(
                row=row_idx + 1, column=2, padx=2, pady=1)

        if side_id == "A":
            self._coords_A_vars = var_list
        else:
            self._coords_B_vars = var_list

        # Add/Remove buttons
        btn_row = ttk.Frame(frame)
        btn_row.grid(row=99, column=0, columnspan=3, pady=(6, 0))
        ttk.Button(btn_row, text="+ Agregar",
                   command=lambda: self._add_row(side_id),
                   width=10).grid(row=0, column=0, padx=2)
        ttk.Button(btn_row, text="− Quitar",
                   command=lambda: self._remove_row(side_id),
                   width=10).grid(row=0, column=1, padx=2)

        return frame

    def _add_row(self, side_id):
        var_list = self._coords_A_vars if side_id == "A" else self._coords_B_vars
        frame = self._coords_A_frame if side_id == "A" else self._coords_B_frame
        new_idx = len(var_list)
        xv = tk.StringVar(value="0")
        yv = tk.StringVar(value="0")
        var_list.append((xv, yv))
        ttk.Label(frame, text=str(new_idx + 1),
                  font=("Helvetica", 9, "bold"),
                  foreground=_C_VALUE).grid(row=new_idx + 1, column=0, pady=1)
        ttk.Entry(frame, textvariable=xv, width=8).grid(
            row=new_idx + 1, column=1, padx=2, pady=1)
        ttk.Entry(frame, textvariable=yv, width=8).grid(
            row=new_idx + 1, column=2, padx=2, pady=1)

    def _remove_row(self, side_id):
        var_list = self._coords_A_vars if side_id == "A" else self._coords_B_vars
        frame = self._coords_A_frame if side_id == "A" else self._coords_B_frame
        if len(var_list) <= 1:
            messagebox.showwarning("Aviso",
                                    "Cada lado debe tener al menos un conductor.",
                                    parent=self)
            return
        var_list.pop()
        # Reach into frame and remove last row of widgets
        # Identify the widgets to delete (row = len(var_list)+1 in grid)
        idx = len(var_list) + 1
        for w in list(frame.grid_slaves(row=idx)):
            w.destroy()

    def _evt_same_toggle(self):
        if self._same_var.get():
            for child in self._sideB_frame.winfo_children():
                self._set_widget_state(child, "disabled")
        else:
            for child in self._sideB_frame.winfo_children():
                self._set_widget_state(child, "normal")
            # Then re-apply current radio selection
            self._evt_sideB_type()

    def _set_widget_state(self, widget, state):
        try:
            widget.configure(state=state)
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self._set_widget_state(child, state)

    def _evt_sideA_type(self):
        if self._sideA_type_var.get() == "solid":
            self._entry_rA.config(state="normal")
        else:
            self._entry_rA.config(state="disabled")

    def _evt_sideB_type(self):
        if self._same_var.get():
            return  # Side B is fully disabled
        is_solid = self._sideB_type_var.get() == "solid"
        self._combo_calibre_b.config(state="disabled" if is_solid else "readonly")
        self._combo_ratio_b.config(state="disabled" if is_solid
                                   else ("readonly" if self._ratio_var_b.get() else "disabled"))
        self._combo_conductor_b.config(state="disabled" if is_solid
                                       else ("readonly" if self._conductor_var_b.get() else "disabled"))
        self._entry_rB.config(state="normal" if is_solid else "disabled")

    def _evt_calibre_b(self, _event=None):
        if self._controller:
            self._ratio_var_b.set("")
            self._combo_ratio_b.config(state="disabled", values=[])
            self._conductor_var_b.set("")
            self._combo_conductor_b.config(state="disabled", values=[])
            self._controller.handle_calibre_selected_b(self._calibre_b_var.get())

    def _evt_ratio_b(self, _event=None):
        if self._controller:
            self._conductor_var_b.set("")
            self._combo_conductor_b.config(state="disabled", values=[])
            self._controller.handle_ratio_selected_b(
                self._calibre_b_var.get(), self._ratio_var_b.get())

    def _evt_conductor_b(self, _event=None):
        if self._controller:
            self._controller.handle_conductor_selected_b(self._conductor_var_b.get())

    def _evt_accept(self):
        # Validate coordinates
        try:
            coords_A = [(float(xv.get()), float(yv.get()))
                        for xv, yv in self._coords_A_vars]
            coords_B = [(float(xv.get()), float(yv.get()))
                        for xv, yv in self._coords_B_vars]
        except ValueError:
            messagebox.showerror("Error", "Todas las coordenadas deben ser numéricas.",
                                  parent=self)
            return

        if len(coords_A) == 0 or len(coords_B) == 0:
            messagebox.showerror("Error", "Ambos lados deben tener al menos un conductor.",
                                  parent=self)
            return

        new_data = {
            "coords_A": coords_A,
            "coords_B": coords_B,
            "same_conductors": self._same_var.get(),
            "side_A_type": self._sideA_type_var.get(),
            "side_A_radius_mm": self._sideA_r_var.get(),
            "side_B_type": self._sideB_type_var.get(),
            "side_B_radius_mm": self._sideB_r_var.get(),
        }
        if self._on_save:
            self._on_save(new_data)
        self.destroy()

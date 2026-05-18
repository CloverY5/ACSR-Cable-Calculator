"""
MainView – tkinter/ttk GUI for the ACSR Transmission Line Calculator (v5.0).

Configuraciones soportadas:
  • Monofásica (2 conductores) — nuevo en v5
  • Trifásica Transpuesta (simétrica/asimétrica)
  • Trifásica No Transpuesta
  • Doble Circuito Trifásico (fórmula rigurosa por fase) — actualizado en v5
"""

import tkinter as tk
from tkinter import ttk, messagebox

_C_TITLE   = "#1a3a5c"
_C_VALUE   = "#005a9c"
_C_RESULT  = "#006633"
_C_RES_R   = "#a04000"
_C_RES_L   = "#005a9c"
_C_RES_C   = "#6a1b9a"
_C_RES_D   = "#0d4f3c"
_C_RES_M   = "#7a3000"  # monophasic results
_C_SUBTLE  = "#666666"
_C_PHASE   = "#7a3000"

CFG_TRANSPOSED   = "transposed"
CFG_UNTRANSPOSED = "untransposed"
CFG_DOUBLE       = "double"
CFG_MONOPHASIC   = "monophasic"


class MainView(tk.Tk):
    APP_TITLE   = "Calculadora de Líneas de Transmisión ACSR"
    APP_VERSION = "v6.0"

    def __init__(self):
        super().__init__()
        self.title(f"{self.APP_TITLE}  {self.APP_VERSION}")
        self.resizable(True, True)

        self._controller = None
        self._calibres_for_b = []

        # Persistent state for Monophasic dialog
        self._mono_data = {
            "D_m": "4.0",
            "same_conductors": True,
            "side_A_type": "acsr",
            "side_A_radius_mm": "10.0",
            "side_B_type": "acsr",
            "side_B_radius_mm": "10.0",
        }

        # Persistent state for Double-Circuit dialog (phase-aware)
        # Each phase has 2 conductors: [circuito_A, circuito_B]
        self._dc_data = {
            "phase_a": [(0.0, 10.0), (5.0, 10.0)],   # a, a'
            "phase_b": [(0.0,  5.0), (5.0,  5.0)],   # b, b'
            "phase_c": [(0.0,  0.0), (5.0,  0.0)],   # c, c'
            "same_conductors": True,
            "side_A_type": "acsr",
            "side_A_radius_mm": "10.0",
            "side_B_type": "acsr",
            "side_B_radius_mm": "10.0",
        }

        self._init_variables()
        self._apply_style()
        self._build_ui()

    # ==================================================================
    # Public API
    # ==================================================================

    def set_controller(self, controller):
        self._controller = controller

    def populate_calibre_list(self, calibres):
        self._combo_calibre["values"] = calibres

    def populate_calibre_list_b(self, calibres):
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

        # Per-phase (untransposed)
        has_pp = results.get("La") is not None
        self._per_phase_frame.grid() if has_pp else self._per_phase_frame.grid_remove()
        if has_pp:
            for var, key in [
                (self._res_La_var, "La"), (self._res_Lb_var, "Lb"), (self._res_Lc_var, "Lc"),
                (self._res_XLa_var, "XLa"), (self._res_XLb_var, "XLb"), (self._res_XLc_var, "XLc"),
                (self._res_Ca_var, "Ca"), (self._res_Cb_var, "Cb"), (self._res_Cc_var, "Cc"),
                (self._res_Xca_var, "Xca"), (self._res_Xcb_var, "Xcb"), (self._res_Xcc_var, "Xcc"),
            ]:
                var.set(results.get(key, "---"))

        # Monophasic details
        m_info = results.get("mono_info")
        if m_info:
            self._mono_frame.grid()
            self._mono_name_a_var.set(m_info["name_A"])
            self._mono_name_b_var.set(m_info["name_B"])
            self._mono_same_var.set("Iguales" if m_info["same"] else "Distintos")
            self._mono_rA_var.set(m_info["r_A_mm"])
            self._mono_rB_var.set(m_info["r_B_mm"])
            self._mono_D_var.set(m_info["D_m"])
            self._mono_Can_var.set(m_info["C_an"])
            self._mono_Cab_var.set(m_info["C_ab"])
        else:
            self._mono_frame.grid_remove()

        # Double-circuit details (rigorous)
        d_info = results.get("double_info")
        if d_info:
            self._double_frame.grid()
            self._dc_name_a_var.set(d_info["name_A"])
            self._dc_name_b_var.set(d_info["name_B"])
            self._dc_same_var.set("Iguales" if d_info["same"] else "Distintos")
            self._dc_DMG_ab_var.set(d_info["DMG_ab"])
            self._dc_DMG_bc_var.set(d_info["DMG_bc"])
            self._dc_DMG_ac_var.set(d_info["DMG_ac"])
            self._dc_DMG_e_var.set(d_info["DMG_e"])
            self._dc_D_aa_var.set(d_info["D_aa"])
            self._dc_D_bb_var.set(d_info["D_bb"])
            self._dc_D_cc_var.set(d_info["D_cc"])
            self._dc_RMG_aL_var.set(d_info["RMG_a_L"])
            self._dc_RMG_bL_var.set(d_info["RMG_b_L"])
            self._dc_RMG_cL_var.set(d_info["RMG_c_L"])
            self._dc_RMG_eL_var.set(d_info["RMG_e_L"])
            self._dc_RMG_aC_var.set(d_info["RMG_a_C"])
            self._dc_RMG_bC_var.set(d_info["RMG_b_C"])
            self._dc_RMG_cC_var.set(d_info["RMG_c_C"])
            self._dc_RMG_eC_var.set(d_info["RMG_e_C"])
        else:
            self._double_frame.grid_remove()

    def get_line_params(self):
        base = {
            "config":  self._config_var.get(),
            "freq":    self._freq_var.get(),
            "length":  self._length_var.get(),
            "temp":    self._temp_var.get(),
            "n_cond":  self._n_cond_var.get(),
            "spacing": self._spacing_var.get(),
            "D12":     self._d12_var.get(),
            "D23":     self._d23_var.get(),
            "D31":     self._d31_var.get(),
        }
        # Pass the dialog data
        base["mono"] = dict(self._mono_data)
        base["dc"]   = dict(self._dc_data)
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

        self._mono_status_var = tk.StringVar(value="(usar valores por defecto)")
        self._dc_status_var   = tk.StringVar(value="(usar valores por defecto)")

        # Result variables
        self._res_config_var = tk.StringVar(value="---")

        for name in [
            "_r_n_al_var", "_r_d_al_var", "_r_A_al_var", "_r_f_al_var",
            "_r_R20_al_var", "_r_RT_al_var",
            "_r_n_ac_var", "_r_d_ac_var", "_r_A_ac_var", "_r_f_ac_var",
            "_r_R20_ac_var", "_r_RT_ac_var",
            "_r_Tfinal_var", "_r_Rtot_var", "_r_Rline_var",
            "_res_dmg_var", "_res_rmg_haz_var",
            "_res_L_var", "_res_XL_km_var", "_res_XL_tot_var",
            "_res_r_bundle_var", "_res_C_var",
            "_res_Xc_km_var", "_res_Xc_tot_var",
            "_res_La_var", "_res_Lb_var", "_res_Lc_var",
            "_res_XLa_var", "_res_XLb_var", "_res_XLc_var",
            "_res_Ca_var", "_res_Cb_var", "_res_Cc_var",
            "_res_Xca_var", "_res_Xcb_var", "_res_Xcc_var",
            # Monophasic
            "_mono_name_a_var", "_mono_name_b_var", "_mono_same_var",
            "_mono_rA_var", "_mono_rB_var", "_mono_D_var",
            "_mono_Can_var", "_mono_Cab_var",
            # Double-circuit
            "_dc_name_a_var", "_dc_name_b_var", "_dc_same_var",
            "_dc_DMG_ab_var", "_dc_DMG_bc_var", "_dc_DMG_ac_var", "_dc_DMG_e_var",
            "_dc_D_aa_var", "_dc_D_bb_var", "_dc_D_cc_var",
            "_dc_RMG_aL_var", "_dc_RMG_bL_var", "_dc_RMG_cL_var", "_dc_RMG_eL_var",
            "_dc_RMG_aC_var", "_dc_RMG_bC_var", "_dc_RMG_cC_var", "_dc_RMG_eC_var",
        ]:
            setattr(self, name, tk.StringVar(value="---"))

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
        # Scrollable container
        container = ttk.Frame(self)
        container.grid(row=0, column=0, sticky="nsew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._canvas = tk.Canvas(container, highlightthickness=0, borderwidth=0)
        vsb = ttk.Scrollbar(container, orient="vertical",
                            command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vsb.set)

        self._canvas.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        outer = ttk.Frame(self._canvas, padding=12)
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=outer, anchor="nw"
        )

        outer.bind("<Configure>", self._on_inner_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self.bind_all("<MouseWheel>", self._on_mousewheel)
        self.bind_all("<Button-4>",   self._on_mousewheel_lin)
        self.bind_all("<Button-5>",   self._on_mousewheel_lin)

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

        self.after(50, self._set_initial_geometry)

    def _on_inner_configure(self, _event=None):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        delta = -1 * int(event.delta / 120) if abs(event.delta) >= 120 else -event.delta
        self._canvas.yview_scroll(delta, "units")

    def _on_mousewheel_lin(self, event):
        if event.num == 4:   self._canvas.yview_scroll(-1, "units")
        elif event.num == 5: self._canvas.yview_scroll(1, "units")

    def _set_initial_geometry(self):
        self.update_idletasks()
        screen_h = self.winfo_screenheight()
        screen_w = self.winfo_screenwidth()
        bbox = self._canvas.bbox("all")
        content_w = bbox[2] if bbox else 1000
        content_h = bbox[3] if bbox else 700
        max_h = int(screen_h * 0.88)
        win_h = min(content_h + 20, max_h)
        win_w = min(content_w + 60, screen_w - 40)
        self.geometry(f"{win_w}x{win_h}")
        self.minsize(win_w, 400)

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

        # Configuration
        rCfg = ttk.Frame(frame)
        rCfg.grid(row=0, column=0, sticky="w", pady=3)
        ttk.Label(rCfg, text="Configuración:").grid(row=0, column=0, padx=(0, 12))
        for col_idx, (lbl, val) in enumerate([
            ("Monofásica (2 conductores)",        CFG_MONOPHASIC),
            ("Trifásica Transpuesta",             CFG_TRANSPOSED),
            ("Trifásica No Transpuesta",          CFG_UNTRANSPOSED),
            ("Doble Circuito Trifásico",          CFG_DOUBLE),
        ]):
            ttk.Radiobutton(rCfg, text=lbl, variable=self._config_var, value=val,
                            command=self._evt_toggle_config).grid(
                row=0, column=col_idx + 1, padx=8)

        ttk.Separator(frame, orient="horizontal").grid(
            row=1, column=0, sticky="ew", pady=4)

        # Common params: f, length, T
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

        # Bundle (shared across configurations)
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

        # Single-circuit-only block (transposed / untransposed)
        self._single_frame = ttk.Frame(frame)
        self._single_frame.grid(row=4, column=0, sticky="w", pady=3)
        ttk.Label(self._single_frame, text="Distancias entre fases:").grid(
            row=0, column=0, padx=(0, 12))
        for col_idx, (lbl, var) in enumerate([
            ("D₁₂ (m):", self._d12_var),
            ("D₂₃ (m):", self._d23_var),
            ("D₃₁ (m):", self._d31_var),
        ]):
            base = col_idx * 3 + 1
            ttk.Label(self._single_frame, text=lbl).grid(row=0, column=base, padx=(0, 4))
            ttk.Entry(self._single_frame, textvariable=var, width=7).grid(
                row=0, column=base + 1, padx=(0, 16))

        # Monophasic config row
        self._mono_setup_frame = ttk.Frame(frame)
        self._mono_setup_frame.grid(row=5, column=0, sticky="w", pady=3)
        ttk.Label(self._mono_setup_frame,
                  text="Configuración Monofásica:",
                  font=("Helvetica", 9, "bold"),
                  foreground=_C_TITLE).grid(row=0, column=0, padx=(0, 12))
        ttk.Button(self._mono_setup_frame,
                   text="⚙  Configurar Línea Monofásica",
                   style="Dialog.TButton",
                   command=self._evt_open_mono_dialog).grid(row=0, column=1, padx=(0, 12))
        ttk.Label(self._mono_setup_frame, textvariable=self._mono_status_var,
                  foreground=_C_SUBTLE,
                  font=("Helvetica", 9, "italic")).grid(row=0, column=2)

        # Double-circuit config row
        self._double_setup_frame = ttk.Frame(frame)
        self._double_setup_frame.grid(row=6, column=0, sticky="w", pady=3)
        ttk.Label(self._double_setup_frame,
                  text="Configuración del Doble Circuito:",
                  font=("Helvetica", 9, "bold"),
                  foreground=_C_TITLE).grid(row=0, column=0, padx=(0, 12))
        ttk.Button(self._double_setup_frame,
                   text="⚙  Configurar Doble Circuito",
                   style="Dialog.TButton",
                   command=self._evt_open_double_dialog).grid(row=0, column=1, padx=(0, 12))
        ttk.Label(self._double_setup_frame, textvariable=self._dc_status_var,
                  foreground=_C_SUBTLE,
                  font=("Helvetica", 9, "italic")).grid(row=0, column=2)

        self._evt_toggle_config()
        self._update_mono_status()
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
        self._build_monophasic_section(wrapper, row=5)
        self._build_double_circuit_section(wrapper, row=6)

    def _build_resistance_section(self, parent, row):
        frame = ttk.LabelFrame(
            parent, text="① Corrección de Resistencia por Temperatura (ACSR)", padding=8)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 4))

        headers = ["", "Hilos", "Ø (mm)", "Área (mm²)", "Factor",
                   "R₂₀ (Ω/km)", "R(T) (Ω/km)"]
        for c, h in enumerate(headers):
            ttk.Label(frame, text=h, font=("Helvetica", 9, "bold"),
                      foreground=_C_TITLE, anchor="center", width=12).grid(
                row=0, column=c, padx=3, pady=(0, 4))

        ttk.Label(frame, text="Aluminio (Al):", anchor="e", width=14,
                  font=("Helvetica", 9, "bold"), foreground=_C_RES_R).grid(
            row=1, column=0, sticky="e", padx=(4, 4), pady=2)
        for c, var in enumerate([self._r_n_al_var, self._r_d_al_var,
                                 self._r_A_al_var, self._r_f_al_var,
                                 self._r_R20_al_var, self._r_RT_al_var]):
            ttk.Label(frame, textvariable=var, font=("Courier New", 10, "bold"),
                      foreground=_C_RES_R, anchor="center", width=12).grid(
                row=1, column=c + 1, pady=2)

        ttk.Label(frame, text="Acero (Ac):", anchor="e", width=14,
                  font=("Helvetica", 9, "bold"), foreground=_C_RES_R).grid(
            row=2, column=0, sticky="e", padx=(4, 4), pady=2)
        for c, var in enumerate([self._r_n_ac_var, self._r_d_ac_var,
                                 self._r_A_ac_var, self._r_f_ac_var,
                                 self._r_R20_ac_var, self._r_RT_ac_var]):
            ttk.Label(frame, textvariable=var, font=("Courier New", 10, "bold"),
                      foreground=_C_RES_R, anchor="center", width=12).grid(
                row=2, column=c + 1, pady=2)

        ttk.Separator(frame, orient="horizontal").grid(
            row=3, column=0, columnspan=7, sticky="ew", pady=6)

        totals = ttk.Frame(frame)
        totals.grid(row=4, column=0, columnspan=7, sticky="w")
        ttk.Label(totals, text="T final:", foreground=_C_SUBTLE).grid(
            row=0, column=0, padx=(0, 4))
        ttk.Label(totals, textvariable=self._r_Tfinal_var,
                  font=("Courier New", 10, "bold"), foreground=_C_RES_R).grid(
            row=0, column=1, padx=(0, 4))
        ttk.Label(totals, text="°C", foreground=_C_SUBTLE).grid(
            row=0, column=2, padx=(0, 18))

        ttk.Label(totals, text="R_TOT:", font=("Helvetica", 9, "bold"),
                  foreground=_C_TITLE).grid(row=0, column=3, padx=(0, 4))
        ttk.Label(totals, textvariable=self._r_Rtot_var,
                  font=("Courier New", 11, "bold"), foreground=_C_RES_R, width=12).grid(
            row=0, column=4)
        ttk.Label(totals, text="Ω/km", foreground=_C_SUBTLE).grid(
            row=0, column=5, padx=(2, 18))

        ttk.Label(totals, text="R total línea:", font=("Helvetica", 9, "bold"),
                  foreground=_C_TITLE).grid(row=0, column=6, padx=(0, 4))
        ttk.Label(totals, textvariable=self._r_Rline_var,
                  font=("Courier New", 11, "bold"), foreground=_C_RES_R, width=12).grid(
            row=0, column=7)
        ttk.Label(totals, text="Ω", foreground=_C_SUBTLE).grid(
            row=0, column=8, padx=(2, 0))

    def _build_inductance_section(self, parent, row):
        frame = ttk.LabelFrame(parent, text="② Inductancia y Reactancia Inductiva", padding=8)
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
            ttk.Label(frame, textvariable=var, font=("Courier New", 11, "bold"),
                      foreground=_C_RES_L, width=12, anchor="w").grid(
                row=r, column=c + 1, sticky="w")
            ttk.Label(frame, text=unit, foreground=_C_SUBTLE).grid(
                row=r, column=c + 2, padx=(2, 14), sticky="w")

    def _build_capacitance_section(self, parent, row):
        frame = ttk.LabelFrame(parent, text="③ Capacitancia y Reactancia Capacitiva", padding=8)
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
            ttk.Label(frame, textvariable=var, font=("Courier New", 11, "bold"),
                      foreground=_C_RES_C, width=12, anchor="w").grid(
                row=r, column=c + 1, sticky="w")
            ttk.Label(frame, text=unit, foreground=_C_SUBTLE).grid(
                row=r, column=c + 2, padx=(2, 14), sticky="w")

    def _build_per_phase_section(self, parent, row):
        self._per_phase_frame = ttk.LabelFrame(
            parent, text="④ Parámetros por fase (sólo para línea No Transpuesta)", padding=8)
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
            ttk.Label(self._per_phase_frame, text=lbl, anchor="e", width=14).grid(
                row=r_idx + 1, column=0, padx=(6, 4), pady=3, sticky="e")
            for c_idx, var in enumerate([va, vb, vc]):
                ttk.Label(self._per_phase_frame, textvariable=var,
                          font=("Courier New", 10, "bold"),
                          foreground=_C_PHASE, width=12, anchor="center").grid(
                    row=r_idx + 1, column=c_idx + 1, pady=3)

    def _build_monophasic_section(self, parent, row):
        self._mono_frame = ttk.LabelFrame(
            parent, text="⑤ Detalle Monofásica (línea de 2 conductores)", padding=8)
        self._mono_frame.grid(row=row, column=0, sticky="ew", pady=(0, 4))
        self._mono_frame.grid_remove()

        for col, txt in enumerate(["", "Conductor A", "Conductor B"]):
            ttk.Label(self._mono_frame, text=txt,
                      font=("Helvetica", 9, "bold"), foreground=_C_TITLE,
                      width=18, anchor="center").grid(row=0, column=col, padx=4, pady=(0, 4))

        rows = [
            ("Conductor:",            self._mono_name_a_var, self._mono_name_b_var),
            ("Radio efectivo (mm):",  self._mono_rA_var,     self._mono_rB_var),
        ]
        for r_idx, (lbl, va, vb) in enumerate(rows):
            ttk.Label(self._mono_frame, text=lbl, anchor="e", width=20).grid(
                row=r_idx + 1, column=0, padx=(6, 4), pady=2, sticky="e")
            for c_idx, var in enumerate([va, vb]):
                ttk.Label(self._mono_frame, textvariable=var,
                          font=("Courier New", 10, "bold"),
                          foreground=_C_RES_M, width=18, anchor="center").grid(
                    row=r_idx + 1, column=c_idx + 1, pady=2)

        ttk.Separator(self._mono_frame, orient="horizontal").grid(
            row=99, column=0, columnspan=3, sticky="ew", pady=6)

        # Distance + capacitances
        totals = ttk.Frame(self._mono_frame)
        totals.grid(row=100, column=0, columnspan=3, sticky="w")
        ttk.Label(totals, text="Distancia D:", font=("Helvetica", 9, "bold"),
                  foreground=_C_TITLE).grid(row=0, column=0, padx=(0, 4))
        ttk.Label(totals, textvariable=self._mono_D_var,
                  font=("Courier New", 11, "bold"), foreground=_C_RES_M).grid(
            row=0, column=1, padx=(0, 4))
        ttk.Label(totals, text="m", foreground=_C_SUBTLE).grid(
            row=0, column=2, padx=(0, 18))
        ttk.Label(totals, text="Tipo:", foreground=_C_SUBTLE).grid(
            row=0, column=3, padx=(0, 4))
        ttk.Label(totals, textvariable=self._mono_same_var,
                  font=("Helvetica", 9, "bold"), foreground=_C_RES_M).grid(
            row=0, column=4)

        # Capacitances row
        ttk.Label(totals, text="C al neutro (C_an):",
                  font=("Helvetica", 9, "bold"), foreground=_C_TITLE).grid(
            row=1, column=0, padx=(0, 4), pady=(6, 0))
        ttk.Label(totals, textvariable=self._mono_Can_var,
                  font=("Courier New", 11, "bold"), foreground=_C_RES_M).grid(
            row=1, column=1, padx=(0, 4), pady=(6, 0))
        ttk.Label(totals, text="nF/km", foreground=_C_SUBTLE).grid(
            row=1, column=2, padx=(0, 18), pady=(6, 0))

        ttk.Label(totals, text="C línea-línea (C_ab):",
                  font=("Helvetica", 9, "bold"), foreground=_C_TITLE).grid(
            row=1, column=3, padx=(0, 4), pady=(6, 0))
        ttk.Label(totals, textvariable=self._mono_Cab_var,
                  font=("Courier New", 11, "bold"), foreground=_C_RES_M).grid(
            row=1, column=4, padx=(0, 4), pady=(6, 0))
        ttk.Label(totals, text="nF/km", foreground=_C_SUBTLE).grid(
            row=1, column=5, padx=(0, 0), pady=(6, 0))

    def _build_double_circuit_section(self, parent, row):
        self._double_frame = ttk.LabelFrame(
            parent, text="⑥ Detalle de Doble Circuito (fórmula rigurosa)", padding=8)
        self._double_frame.grid(row=row, column=0, sticky="ew", pady=(0, 4))
        self._double_frame.grid_remove()

        # Conductor info
        info = ttk.Frame(self._double_frame)
        info.grid(row=0, column=0, sticky="w", pady=(0, 6))
        ttk.Label(info, text="Conductor Circuito A:",
                  font=("Helvetica", 9, "bold"), foreground=_C_TITLE).grid(
            row=0, column=0, padx=(0, 4))
        ttk.Label(info, textvariable=self._dc_name_a_var,
                  foreground=_C_RES_D, width=16).grid(row=0, column=1, padx=(0, 16))
        ttk.Label(info, text="Conductor Circuito B:",
                  font=("Helvetica", 9, "bold"), foreground=_C_TITLE).grid(
            row=0, column=2, padx=(0, 4))
        ttk.Label(info, textvariable=self._dc_name_b_var,
                  foreground=_C_RES_D, width=16).grid(row=0, column=3, padx=(0, 16))
        ttk.Label(info, text="Tipo:", foreground=_C_SUBTLE).grid(
            row=0, column=4, padx=(0, 4))
        ttk.Label(info, textvariable=self._dc_same_var,
                  font=("Helvetica", 9, "bold"), foreground=_C_RES_D).grid(row=0, column=5)

        # DMGs per pair
        dmg_frame = ttk.LabelFrame(
            self._double_frame, text="DMG entre fases", padding=4)
        dmg_frame.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        dmgs = [
            ("DMG_ab:", self._dc_DMG_ab_var, "m"),
            ("DMG_bc:", self._dc_DMG_bc_var, "m"),
            ("DMG_ac:", self._dc_DMG_ac_var, "m"),
            ("DMG_e:",  self._dc_DMG_e_var,  "m  (equivalente)"),
        ]
        for c, (lbl, var, unit) in enumerate(dmgs):
            ttk.Label(dmg_frame, text=lbl, anchor="e").grid(
                row=0, column=c * 3, padx=(6, 4), pady=2, sticky="e")
            ttk.Label(dmg_frame, textvariable=var,
                      font=("Courier New", 10, "bold"),
                      foreground=_C_RES_D, width=10, anchor="w").grid(
                row=0, column=c * 3 + 1, sticky="w")
            ttk.Label(dmg_frame, text=unit, foreground=_C_SUBTLE).grid(
                row=0, column=c * 3 + 2, padx=(2, 10), sticky="w")

        # Same-phase distances
        d_frame = ttk.LabelFrame(
            self._double_frame, text="Distancias D_aa', D_bb', D_cc'", padding=4)
        d_frame.grid(row=2, column=0, sticky="ew", pady=(0, 4))
        ds = [
            ("D_aa':", self._dc_D_aa_var),
            ("D_bb':", self._dc_D_bb_var),
            ("D_cc':", self._dc_D_cc_var),
        ]
        for c, (lbl, var) in enumerate(ds):
            ttk.Label(d_frame, text=lbl, anchor="e").grid(
                row=0, column=c * 3, padx=(6, 4), pady=2, sticky="e")
            ttk.Label(d_frame, textvariable=var,
                      font=("Courier New", 10, "bold"),
                      foreground=_C_RES_D, width=10, anchor="w").grid(
                row=0, column=c * 3 + 1, sticky="w")
            ttk.Label(d_frame, text="m", foreground=_C_SUBTLE).grid(
                row=0, column=c * 3 + 2, padx=(2, 10), sticky="w")

        # RMGs per phase
        rmg_L_frame = ttk.LabelFrame(
            self._double_frame, text="RMG por fase (para inductancia, usa GMR del conductor)",
            padding=4)
        rmg_L_frame.grid(row=3, column=0, sticky="ew", pady=(0, 4))
        rmgs_L = [
            ("RMG_a:", self._dc_RMG_aL_var),
            ("RMG_b:", self._dc_RMG_bL_var),
            ("RMG_c:", self._dc_RMG_cL_var),
            ("RMG_e:", self._dc_RMG_eL_var),
        ]
        for c, (lbl, var) in enumerate(rmgs_L):
            ttk.Label(rmg_L_frame, text=lbl, anchor="e").grid(
                row=0, column=c * 3, padx=(6, 4), pady=2, sticky="e")
            ttk.Label(rmg_L_frame, textvariable=var,
                      font=("Courier New", 10, "bold"),
                      foreground=_C_RES_D, width=10, anchor="w").grid(
                row=0, column=c * 3 + 1, sticky="w")
            ttk.Label(rmg_L_frame, text="m", foreground=_C_SUBTLE).grid(
                row=0, column=c * 3 + 2, padx=(2, 10), sticky="w")

        rmg_C_frame = ttk.LabelFrame(
            self._double_frame, text="RMG por fase (para capacitancia, usa radio físico)",
            padding=4)
        rmg_C_frame.grid(row=4, column=0, sticky="ew", pady=(0, 4))
        rmgs_C = [
            ("RMG_a:", self._dc_RMG_aC_var),
            ("RMG_b:", self._dc_RMG_bC_var),
            ("RMG_c:", self._dc_RMG_cC_var),
            ("RMG_e:", self._dc_RMG_eC_var),
        ]
        for c, (lbl, var) in enumerate(rmgs_C):
            ttk.Label(rmg_C_frame, text=lbl, anchor="e").grid(
                row=0, column=c * 3, padx=(6, 4), pady=2, sticky="e")
            ttk.Label(rmg_C_frame, textvariable=var,
                      font=("Courier New", 10, "bold"),
                      foreground=_C_RES_D, width=10, anchor="w").grid(
                row=0, column=c * 3 + 1, sticky="w")
            ttk.Label(rmg_C_frame, text="m", foreground=_C_SUBTLE).grid(
                row=0, column=c * 3 + 2, padx=(2, 10), sticky="w")

    # ==================================================================
    # Dialogs
    # ==================================================================

    def _evt_open_mono_dialog(self):
        MonophasicDialog(self, self._mono_data,
                          self._calibres_for_b, self._controller,
                          on_save=self._on_mono_saved)

    def _on_mono_saved(self, new_data):
        self._mono_data.update(new_data)
        self._update_mono_status()

    def _update_mono_status(self):
        d = self._mono_data
        same = "iguales" if d["same_conductors"] else "distintos"
        self._mono_status_var.set(
            f"D = {d['D_m']} m, conductores {same}"
        )

    def _evt_open_double_dialog(self):
        DoubleCircuitDialog(self, self._dc_data,
                            self._calibres_for_b, self._controller,
                            on_save=self._on_double_saved)

    def _on_double_saved(self, new_data):
        self._dc_data.update(new_data)
        self._update_dc_status()

    def _update_dc_status(self):
        d = self._dc_data
        same = "iguales" if d["same_conductors"] else "distintos"
        self._dc_status_var.set(f"Fases a, b, c configuradas — conductores {same}")

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
        # Hide everything first
        self._single_frame.grid_remove()
        self._mono_setup_frame.grid_remove()
        self._double_setup_frame.grid_remove()

        if cfg in (CFG_TRANSPOSED, CFG_UNTRANSPOSED):
            self._single_frame.grid()
        elif cfg == CFG_MONOPHASIC:
            self._mono_setup_frame.grid()
        elif cfg == CFG_DOUBLE:
            self._double_setup_frame.grid()

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
# Helpers shared by both dialogs
# ===========================================================================

def _build_side_b_selector(parent, master_view, calibres, controller, dialog):
    """
    Build the 'Side B' selector (ACSR or Solid). Used by both Mono and DC dialogs.
    Returns: dict of variables and the parent frame for show/hide control.
    """
    frame = ttk.LabelFrame(parent, text="Lado B / Circuito 2", padding=8)

    sideB_type_var = tk.StringVar(value=dialog._data["side_B_type"])
    sideB_r_var    = tk.StringVar(value=dialog._data["side_B_radius_mm"])

    ttk.Radiobutton(frame, text="ACSR (seleccionar del catálogo):",
                    variable=sideB_type_var, value="acsr",
                    command=lambda: dialog._evt_sideB_type_change()
                    ).grid(row=0, column=0, columnspan=4, sticky="w")

    catB_frame = ttk.Frame(frame)
    catB_frame.grid(row=1, column=0, columnspan=4, sticky="w", padx=(20, 0))
    ttk.Label(catB_frame, text="Calibre:").grid(row=0, column=0, padx=(0, 4))
    combo_calibre_b = ttk.Combobox(catB_frame, width=10, state="readonly",
                                    values=calibres or [])
    combo_calibre_b.grid(row=0, column=1, padx=(0, 8))

    ttk.Label(catB_frame, text="Cableado:").grid(row=0, column=2, padx=(0, 4))
    combo_ratio_b = ttk.Combobox(catB_frame, width=7, state="disabled")
    combo_ratio_b.grid(row=0, column=3, padx=(0, 8))

    ttk.Label(catB_frame, text="Conductor:").grid(row=0, column=4, padx=(0, 4))
    combo_conductor_b = ttk.Combobox(catB_frame, width=14, state="disabled")
    combo_conductor_b.grid(row=0, column=5)

    # Wire into the parent MainView for the controller callbacks
    master_view._combo_ratio_b = combo_ratio_b
    master_view._combo_conductor_b = combo_conductor_b
    master_view._ratio_var_b = tk.StringVar()
    master_view._conductor_var_b = tk.StringVar()
    combo_ratio_b.configure(textvariable=master_view._ratio_var_b)
    combo_conductor_b.configure(textvariable=master_view._conductor_var_b)

    calibre_b_var = tk.StringVar()
    combo_calibre_b.configure(textvariable=calibre_b_var)

    def _on_calibre(_e=None):
        if controller:
            master_view._ratio_var_b.set("")
            combo_ratio_b.config(state="disabled", values=[])
            master_view._conductor_var_b.set("")
            combo_conductor_b.config(state="disabled", values=[])
            controller.handle_calibre_selected_b(calibre_b_var.get())

    def _on_ratio(_e=None):
        if controller:
            master_view._conductor_var_b.set("")
            combo_conductor_b.config(state="disabled", values=[])
            controller.handle_ratio_selected_b(
                calibre_b_var.get(), master_view._ratio_var_b.get())

    def _on_conductor(_e=None):
        if controller:
            controller.handle_conductor_selected_b(master_view._conductor_var_b.get())

    combo_calibre_b.bind("<<ComboboxSelected>>", _on_calibre)
    combo_ratio_b.bind("<<ComboboxSelected>>", _on_ratio)
    combo_conductor_b.bind("<<ComboboxSelected>>", _on_conductor)

    infoB = ttk.Frame(frame)
    infoB.grid(row=2, column=0, columnspan=4, sticky="w", padx=(20, 0), pady=4)
    master_view._info_name_b_var = tk.StringVar(value="---")
    master_view._info_rmg_b_var  = tk.StringVar(value="---")
    ttk.Label(infoB, text="Selección:", foreground=_C_SUBTLE).grid(
        row=0, column=0, padx=(0, 4))
    ttk.Label(infoB, textvariable=master_view._info_name_b_var,
              font=("Helvetica", 9, "bold"), foreground=_C_VALUE, width=14).grid(
        row=0, column=1, padx=(0, 12))
    ttk.Label(infoB, text="RMG:", foreground=_C_SUBTLE).grid(
        row=0, column=2, padx=(0, 4))
    ttk.Label(infoB, textvariable=master_view._info_rmg_b_var,
              foreground=_C_VALUE, width=8).grid(row=0, column=3)
    ttk.Label(infoB, text="mm", foreground=_C_SUBTLE).grid(
        row=0, column=4, padx=(2, 12))
    master_view._btn_confirm_b = ttk.Button(
        infoB, text="✓ Confirmar B", style="Confirm.TButton",
        command=lambda: controller.handle_confirm_conductor_b() if controller else None,
        state="disabled")
    master_view._btn_confirm_b.grid(row=0, column=5)

    ttk.Radiobutton(frame, text="Sólido - ingresar radio:",
                    variable=sideB_type_var, value="solid",
                    command=lambda: dialog._evt_sideB_type_change()
                    ).grid(row=3, column=0, columnspan=4, sticky="w", pady=(6, 0))

    rB_inner = ttk.Frame(frame)
    rB_inner.grid(row=4, column=0, sticky="w", padx=(20, 0))
    ttk.Label(rB_inner, text="Radio (mm):").grid(row=0, column=0)
    entry_rB = ttk.Entry(rB_inner, textvariable=sideB_r_var, width=8)
    entry_rB.grid(row=0, column=1, padx=(4, 0))

    return {
        "frame":           frame,
        "type_var":        sideB_type_var,
        "radius_var":      sideB_r_var,
        "combo_calibre":   combo_calibre_b,
        "combo_ratio":     combo_ratio_b,
        "combo_conductor": combo_conductor_b,
        "entry_radius":    entry_rB,
    }


# ===========================================================================
# Monophasic Dialog
# ===========================================================================

class MonophasicDialog(tk.Toplevel):
    def __init__(self, parent, current_data, calibres, controller, on_save):
        super().__init__(parent)
        self.title("Configuración Línea Monofásica")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._on_save = on_save
        self._controller = controller
        self._calibres = calibres
        self._master_view = parent

        self._data = dict(current_data)

        self._same_var       = tk.BooleanVar(value=self._data["same_conductors"])
        self._sideA_type_var = tk.StringVar(value=self._data["side_A_type"])
        self._sideA_r_var    = tk.StringVar(value=self._data["side_A_radius_mm"])
        self._D_var          = tk.StringVar(value=self._data["D_m"])

        self._build_ui()
        self.update_idletasks()
        self.geometry(f"+{parent.winfo_rootx() + 50}+{parent.winfo_rooty() + 50}")

    def _build_ui(self):
        outer = ttk.Frame(self, padding=12)
        outer.grid(row=0, column=0)

        ttk.Label(outer, text="Configurar Línea Monofásica (2 conductores)",
                  font=("Helvetica", 12, "bold"),
                  foreground=_C_TITLE).grid(row=0, column=0, columnspan=2, pady=(0, 10))

        # Distance
        dist_frame = ttk.LabelFrame(outer, text="Geometría", padding=8)
        dist_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        ttk.Label(dist_frame, text="Distancia entre conductores D (m):").grid(
            row=0, column=0, padx=(0, 4))
        ttk.Entry(dist_frame, textvariable=self._D_var, width=10).grid(
            row=0, column=1)

        # Same/different toggle
        toggle_frame = ttk.LabelFrame(outer, text="Tipo de conductores", padding=8)
        toggle_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        ttk.Checkbutton(toggle_frame,
                        text="Mismo conductor en ambos lados",
                        variable=self._same_var,
                        command=self._evt_same_toggle).grid(row=0, column=0, sticky="w")

        # Side A
        sideA_frame = ttk.LabelFrame(outer, text="Conductor A", padding=8)
        sideA_frame.grid(row=3, column=0, sticky="nsew", padx=(0, 6), pady=(0, 6))
        ttk.Radiobutton(sideA_frame, text="ACSR (conductor principal)",
                        variable=self._sideA_type_var, value="acsr",
                        command=self._evt_sideA_type).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(sideA_frame, text="Sólido - radio:",
                        variable=self._sideA_type_var, value="solid",
                        command=self._evt_sideA_type).grid(row=1, column=0, sticky="w")
        rA = ttk.Frame(sideA_frame)
        rA.grid(row=2, column=0, sticky="w", padx=(20, 0))
        ttk.Label(rA, text="Radio (mm):").grid(row=0, column=0)
        self._entry_rA = ttk.Entry(rA, textvariable=self._sideA_r_var, width=8)
        self._entry_rA.grid(row=0, column=1, padx=(4, 0))

        # Side B (using shared helper)
        sideB = _build_side_b_selector(
            outer, self._master_view, self._calibres, self._controller, self)
        self._sideB = sideB
        sideB["frame"].grid(row=3, column=1, sticky="nsew", pady=(0, 6))

        # Buttons
        btn_frame = ttk.Frame(outer)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=(12, 0))
        ttk.Button(btn_frame, text="Aceptar", style="Calc.TButton",
                   command=self._evt_accept).grid(row=0, column=0, padx=4, ipadx=20)
        ttk.Button(btn_frame, text="Cancelar",
                   command=self.destroy).grid(row=0, column=1, padx=4, ipadx=12)

        self._evt_same_toggle()
        self._evt_sideA_type()
        self._evt_sideB_type_change()

    def _evt_same_toggle(self):
        state = "disabled" if self._same_var.get() else "normal"
        for child in self._sideB["frame"].winfo_children():
            self._set_widget_state(child, state)
        if not self._same_var.get():
            self._evt_sideB_type_change()

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

    def _evt_sideB_type_change(self):
        if self._same_var.get():
            return
        is_solid = self._sideB["type_var"].get() == "solid"
        self._sideB["combo_calibre"].config(state="disabled" if is_solid else "readonly")
        self._sideB["combo_ratio"].config(state="disabled")
        self._sideB["combo_conductor"].config(state="disabled")
        self._sideB["entry_radius"].config(state="normal" if is_solid else "disabled")

    def _evt_accept(self):
        try:
            float(self._D_var.get())
        except ValueError:
            messagebox.showerror("Error", "La distancia D debe ser numérica.", parent=self)
            return
        new_data = {
            "D_m":              self._D_var.get(),
            "same_conductors":  self._same_var.get(),
            "side_A_type":      self._sideA_type_var.get(),
            "side_A_radius_mm": self._sideA_r_var.get(),
            "side_B_type":      self._sideB["type_var"].get(),
            "side_B_radius_mm": self._sideB["radius_var"].get(),
        }
        if self._on_save:
            self._on_save(new_data)
        self.destroy()


# ===========================================================================
# DoubleCircuitDialog (phase-aware, rigorous)
# ===========================================================================

class DoubleCircuitDialog(tk.Toplevel):
    def __init__(self, parent, current_data, calibres, controller, on_save):
        super().__init__(parent)
        self.title("Configuración del Doble Circuito (3+3 conductores)")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._on_save = on_save
        self._controller = controller
        self._calibres = calibres
        self._master_view = parent

        self._data = dict(current_data)

        self._same_var       = tk.BooleanVar(value=self._data["same_conductors"])
        self._sideA_type_var = tk.StringVar(value=self._data["side_A_type"])
        self._sideA_r_var    = tk.StringVar(value=self._data["side_A_radius_mm"])

        # Coordinate StringVars per phase, per conductor
        # phase_a = [(x_a, y_a), (x_a', y_a')]
        self._phase_vars = {"a": [], "b": [], "c": []}
        for ph in ("a", "b", "c"):
            for (x, y) in self._data[f"phase_{ph}"]:
                self._phase_vars[ph].append(
                    (tk.StringVar(value=f"{x:g}"), tk.StringVar(value=f"{y:g}"))
                )

        self._build_ui()
        self.update_idletasks()
        self.geometry(f"+{parent.winfo_rootx() + 50}+{parent.winfo_rooty() + 50}")

    def _build_ui(self):
        outer = ttk.Frame(self, padding=12)
        outer.grid(row=0, column=0)

        ttk.Label(outer, text="Doble Circuito Trifásico — Fórmula Rigurosa",
                  font=("Helvetica", 12, "bold"),
                  foreground=_C_TITLE).grid(row=0, column=0, columnspan=2, pady=(0, 4))
        ttk.Label(outer, text=("Cada fase tiene 2 conductores: uno por circuito.\n"
                                "Ingrese las coordenadas (x, y) en metros."),
                  foreground=_C_SUBTLE, font=("Helvetica", 9, "italic")).grid(
            row=1, column=0, columnspan=2, pady=(0, 8))

        # Same/different toggle
        toggle_frame = ttk.LabelFrame(outer, text="Tipo de conductores", padding=8)
        toggle_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        ttk.Checkbutton(toggle_frame,
                        text="Mismo conductor en ambos circuitos",
                        variable=self._same_var,
                        command=self._evt_same_toggle).grid(row=0, column=0, sticky="w")

        # Side A
        sideA_frame = ttk.LabelFrame(outer, text="Conductor Circuito A", padding=8)
        sideA_frame.grid(row=3, column=0, sticky="nsew", padx=(0, 6), pady=(0, 6))
        ttk.Radiobutton(sideA_frame, text="ACSR (conductor principal)",
                        variable=self._sideA_type_var, value="acsr",
                        command=self._evt_sideA_type).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(sideA_frame, text="Sólido - radio:",
                        variable=self._sideA_type_var, value="solid",
                        command=self._evt_sideA_type).grid(row=1, column=0, sticky="w")
        rA = ttk.Frame(sideA_frame)
        rA.grid(row=2, column=0, sticky="w", padx=(20, 0))
        ttk.Label(rA, text="Radio (mm):").grid(row=0, column=0)
        self._entry_rA = ttk.Entry(rA, textvariable=self._sideA_r_var, width=8)
        self._entry_rA.grid(row=0, column=1, padx=(4, 0))

        # Side B (shared helper)
        sideB = _build_side_b_selector(
            outer, self._master_view, self._calibres, self._controller, self)
        self._sideB = sideB
        sideB["frame"].grid(row=3, column=1, sticky="nsew", pady=(0, 6))

        # Coordinate input by phase
        coords_label = ttk.Label(outer,
                                  text="Coordenadas (x, y) por fase, en metros",
                                  font=("Helvetica", 10, "bold"),
                                  foreground=_C_TITLE)
        coords_label.grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 4))

        phases_frame = ttk.Frame(outer)
        phases_frame.grid(row=5, column=0, columnspan=2, sticky="w")
        for c_idx, phase in enumerate(("a", "b", "c")):
            self._build_phase_table(phases_frame, phase, c_idx)

        # Buttons
        btn_frame = ttk.Frame(outer)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=(12, 0))
        ttk.Button(btn_frame, text="Aceptar", style="Calc.TButton",
                   command=self._evt_accept).grid(row=0, column=0, padx=4, ipadx=20)
        ttk.Button(btn_frame, text="Cancelar",
                   command=self.destroy).grid(row=0, column=1, padx=4, ipadx=12)

        self._evt_same_toggle()
        self._evt_sideA_type()
        self._evt_sideB_type_change()

    def _build_phase_table(self, parent, phase_letter, col_idx):
        title = {"a": "Fase a", "b": "Fase b", "c": "Fase c"}[phase_letter]
        frame = ttk.LabelFrame(parent, text=title, padding=6)
        frame.grid(row=0, column=col_idx, padx=4, sticky="n")

        for c, h in enumerate(["", "x (m)", "y (m)"]):
            ttk.Label(frame, text=h, font=("Helvetica", 9, "bold"),
                      foreground=_C_TITLE, anchor="center", width=8).grid(
                row=0, column=c, padx=2, pady=(0, 4))

        # Row 0 → Circuit A;  Row 1 → Circuit B
        labels = [f"Cir. A ({phase_letter}):", f"Cir. B ({phase_letter}'):"]
        for r_idx, lbl in enumerate(labels):
            xv, yv = self._phase_vars[phase_letter][r_idx]
            ttk.Label(frame, text=lbl,
                      font=("Helvetica", 9, "bold"),
                      foreground=_C_VALUE, anchor="e").grid(
                row=r_idx + 1, column=0, padx=2, pady=2, sticky="e")
            ttk.Entry(frame, textvariable=xv, width=8).grid(
                row=r_idx + 1, column=1, padx=2, pady=2)
            ttk.Entry(frame, textvariable=yv, width=8).grid(
                row=r_idx + 1, column=2, padx=2, pady=2)

    def _evt_same_toggle(self):
        state = "disabled" if self._same_var.get() else "normal"
        for child in self._sideB["frame"].winfo_children():
            self._set_widget_state(child, state)
        if not self._same_var.get():
            self._evt_sideB_type_change()

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

    def _evt_sideB_type_change(self):
        if self._same_var.get():
            return
        is_solid = self._sideB["type_var"].get() == "solid"
        self._sideB["combo_calibre"].config(state="disabled" if is_solid else "readonly")
        self._sideB["combo_ratio"].config(state="disabled")
        self._sideB["combo_conductor"].config(state="disabled")
        self._sideB["entry_radius"].config(state="normal" if is_solid else "disabled")

    def _evt_accept(self):
        try:
            phase_a = [(float(self._phase_vars["a"][i][0].get()),
                        float(self._phase_vars["a"][i][1].get())) for i in range(2)]
            phase_b = [(float(self._phase_vars["b"][i][0].get()),
                        float(self._phase_vars["b"][i][1].get())) for i in range(2)]
            phase_c = [(float(self._phase_vars["c"][i][0].get()),
                        float(self._phase_vars["c"][i][1].get())) for i in range(2)]
        except ValueError:
            messagebox.showerror("Error", "Todas las coordenadas deben ser numéricas.",
                                  parent=self)
            return

        new_data = {
            "phase_a": phase_a,
            "phase_b": phase_b,
            "phase_c": phase_c,
            "same_conductors": self._same_var.get(),
            "side_A_type": self._sideA_type_var.get(),
            "side_A_radius_mm": self._sideA_r_var.get(),
            "side_B_type": self._sideB["type_var"].get(),
            "side_B_radius_mm": self._sideB["radius_var"].get(),
        }
        if self._on_save:
            self._on_save(new_data)
        self.destroy()

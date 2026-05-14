"""
AppController – mediates between ConductorDatabase (Model) and MainView (View).

Supports:
  • Transposed symmetric/asymmetric line  (D12=D23=D31 or different)
  • Untransposed asymmetric line          (per-phase L and C)
  • Double-circuit line                   (equivalent GMR/GMD)
  • Bundle of 1–4 sub-conductors per phase
  • Inductance, capacitance and all derived reactances
"""

from model.conductor_db import (
    ConductorDatabase,
    COL_CODE, COL_RMG, COL_R_DC20, COL_D_TOTAL,
)
from model.calculations import (
    correct_resistance,
    bundle_gmr,
    bundle_radius,
    geometric_mean_distance,
    inductance_per_meter,
    inductance_untransposed,
    double_circuit_gmr,
    capacitance_per_meter,
    capacitance_untransposed,
    reactance_per_km,
    capacitive_reactance_per_km,
    total_reactance,
    total_capacitive_reactance,
    to_mH_per_km,
    to_nF_per_km,
)

# Line configuration identifiers (must match values used in MainView)
CFG_TRANSPOSED    = "transposed"
CFG_UNTRANSPOSED  = "untransposed"
CFG_DOUBLE        = "double"


class AppController:
    """Wires the View to the Model."""

    def __init__(self, view, db: ConductorDatabase):
        self._view = view
        self._db   = db

        self._previewed_conductor: dict | None = None
        self._confirmed_conductor: dict | None = None

        view.set_controller(self)
        calibres = self._db.get_unique_calibres()
        self._view.populate_calibre_list(calibres)

    # ------------------------------------------------------------------
    # Method 1 – direct search by code name
    # ------------------------------------------------------------------

    def handle_search_by_code(self, code: str):
        if not code.strip():
            self._view.show_error("Campo vacío", "Ingrese el código del conductor.")
            return
        conductor = self._db.search_by_code(code)
        if conductor is None:
            self._view.show_error(
                "No encontrado",
                f"El conductor '{code}' no existe en el catálogo.\n"
                "Verifique el nombre (ej. Drake, Hawk, Tern)."
            )
            return
        self._previewed_conductor = conductor
        self._push_conductor_info(conductor)

    # ------------------------------------------------------------------
    # Method 2 – cascading filter
    # ------------------------------------------------------------------

    def handle_calibre_selected(self, calibre: str):
        ratios = self._db.get_ratios_for_calibre(calibre)
        if not ratios:
            return
        auto = ratios[0] if len(ratios) == 1 else None
        self._view.populate_ratio_list(ratios, auto_select=auto)
        if auto is not None:
            self.handle_ratio_selected(calibre, auto)

    def handle_ratio_selected(self, calibre: str, ratio: str):
        codes = self._db.get_codes_by_filter(calibre, ratio)
        if not codes:
            return
        auto = codes[0] if len(codes) == 1 else None
        self._view.populate_conductor_list(codes, auto_select=auto)
        if auto is not None:
            self.handle_conductor_selected(auto)

    def handle_conductor_selected(self, code: str):
        conductor = self._db.search_by_code(code)
        if conductor is None:
            return
        self._previewed_conductor = conductor
        self._push_conductor_info(conductor)

    # ------------------------------------------------------------------
    # Conductor confirmation
    # ------------------------------------------------------------------

    def handle_confirm_conductor(self):
        if self._previewed_conductor is None:
            self._view.show_error("Sin selección", "Seleccione un conductor primero.")
            return
        self._confirmed_conductor = self._previewed_conductor
        name = self._confirmed_conductor[COL_CODE]
        self._view.show_info(
            "Conductor confirmado",
            f"'{name}' ha sido confirmado.\n"
            "Ya puede ingresar los parámetros de línea y calcular."
        )

    # ------------------------------------------------------------------
    # Calculation – dispatcher
    # ------------------------------------------------------------------

    def handle_calculate(self):
        if self._confirmed_conductor is None:
            self._view.show_error(
                "Sin conductor",
                "Confirme primero un conductor ACSR antes de calcular."
            )
            return

        params = self._view.get_line_params()
        config = params.get("config", CFG_TRANSPOSED)

        try:
            freq   = _parse_pos("Frecuencia", params["freq"])
            length = _parse_pos("Longitud",   params["length"])
            temp   = float(params["temp"])
            n_cond = int(params["n_cond"])
            D12    = _parse_pos("D₁₂", params["D12"])
            D23    = _parse_pos("D₂₃", params["D23"])
            D31    = _parse_pos("D₃₁", params["D31"])

            rmg_mm    = float(self._confirmed_conductor[COL_RMG])
            r_base    = float(self._confirmed_conductor[COL_R_DC20])
            d_total_mm = float(self._confirmed_conductor[COL_D_TOTAL])

            # Physical radius from total diameter [m]
            r_cond_m = (d_total_mm / 2.0) / 1000.0

            if n_cond > 1:
                spacing = _parse_pos("Separación del haz", params["spacing"])
            else:
                spacing = 0.0

            if config == CFG_DOUBLE:
                D_between = _parse_pos("Separación entre circuitos", params["D_between"])

        except (ValueError, TypeError) as exc:
            self._view.show_error("Error de entrada", str(exc))
            return

        try:
            R_corr = correct_resistance(r_base, T2=temp)

            # ── Bundle GMR (inductance) and bundle radius (capacitance) ──
            rmg_haz_m  = bundle_gmr(rmg_mm, spacing, n_cond)
            r_bundle_m = bundle_radius(r_cond_m, spacing, n_cond)

            rmg_haz_mm  = rmg_haz_m  * 1000.0
            r_bundle_mm = r_bundle_m * 1000.0

            # ── Dispatch by configuration ─────────────────────────────────
            if config == CFG_TRANSPOSED:
                results = self._calc_transposed(
                    freq, length, D12, D23, D31,
                    rmg_haz_m, r_bundle_m, rmg_haz_mm, r_bundle_mm, R_corr
                )

            elif config == CFG_UNTRANSPOSED:
                results = self._calc_untransposed(
                    freq, length, D12, D23, D31,
                    rmg_mm / 1000.0, r_cond_m, rmg_haz_mm, R_corr
                )

            elif config == CFG_DOUBLE:
                results = self._calc_double_circuit(
                    freq, length, D12, D23, D31, D_between,
                    rmg_mm / 1000.0, r_cond_m, rmg_haz_mm, r_bundle_mm, R_corr
                )
            else:
                self._view.show_error("Configuración", f"Configuración desconocida: {config}")
                return

        except (ValueError, ZeroDivisionError) as exc:
            self._view.show_error("Error de cálculo", str(exc))
            return

        self._view.display_results(results)

    # ------------------------------------------------------------------
    # Private calculation methods
    # ------------------------------------------------------------------

    def _calc_transposed(self, freq, length, D12, D23, D31,
                         rmg_haz_m, r_bundle_m,
                         rmg_haz_mm, r_bundle_mm, R_corr):
        """Transposed symmetric or asymmetric line."""
        dmg = geometric_mean_distance(D12, D23, D31)

        # Inductance
        L_H_m   = inductance_per_meter(dmg, rmg_haz_m)
        L_mH_km = to_mH_per_km(L_H_m)
        XL_km   = reactance_per_km(freq, L_H_m)
        XL_tot  = total_reactance(XL_km, length)

        # Capacitance
        C_F_m   = capacitance_per_meter(dmg, r_bundle_m)
        C_nF_km = to_nF_per_km(C_F_m)
        Xc_km   = capacitive_reactance_per_km(freq, C_F_m)
        Xc_tot  = total_capacitive_reactance(Xc_km, length)

        return {
            "config":    "Transpuesta",
            "dmg":       f"{dmg:.4f}",
            "rmg_haz":   f"{rmg_haz_mm:.4f}",
            "r_bundle":  f"{r_bundle_mm:.4f}",
            "L_mH_km":   f"{L_mH_km:.4f}",
            "XL_km":     f"{XL_km:.4f}",
            "R_corr":    f"{R_corr:.4f}",
            "XL_total":  f"{XL_tot:.4f}",
            "C_nF_km":   f"{C_nF_km:.4f}",
            "Xc_km":     f"{Xc_km:.4f}",
            "Xc_total":  f"{Xc_tot:.4f}",
            # Per-phase fields (N/A for transposed)
            "La": None, "Lb": None, "Lc": None,
            "Ca": None, "Cb": None, "Cc": None,
        }

    def _calc_untransposed(self, freq, length, D12, D23, D31,
                           rmg_m, r_m, rmg_haz_mm, R_corr):
        """Untransposed asymmetric line – per-phase L and C."""
        dmg = geometric_mean_distance(D12, D23, D31)

        # Per-phase inductance
        La, Lb, Lc = inductance_untransposed(rmg_m, D12, D23, D31)
        L_avg = (La + Lb + Lc) / 3.0

        XLa = reactance_per_km(freq, La)
        XLb = reactance_per_km(freq, Lb)
        XLc = reactance_per_km(freq, Lc)

        # Per-phase capacitance
        Ca, Cb, Cc = capacitance_untransposed(r_m, D12, D23, D31)
        C_avg = (Ca + Cb + Cc) / 3.0

        Xca = capacitive_reactance_per_km(freq, Ca)
        Xcb = capacitive_reactance_per_km(freq, Cb)
        Xcc = capacitive_reactance_per_km(freq, Cc)

        return {
            "config":   "No Transpuesta",
            "dmg":      f"{dmg:.4f}",
            "rmg_haz":  f"{rmg_haz_mm:.4f}",
            "r_bundle": f"{r_m*1000:.4f}",
            "L_mH_km":  f"{to_mH_per_km(L_avg):.4f}",
            "XL_km":    f"{reactance_per_km(freq, L_avg):.4f}",
            "R_corr":   f"{R_corr:.4f}",
            "XL_total": f"{total_reactance(reactance_per_km(freq, L_avg), length):.4f}",
            "C_nF_km":  f"{to_nF_per_km(C_avg):.4f}",
            "Xc_km":    f"{capacitive_reactance_per_km(freq, C_avg):.4f}",
            "Xc_total": f"{total_capacitive_reactance(capacitive_reactance_per_km(freq, C_avg), length):.4f}",
            # Per-phase
            "La": f"{to_mH_per_km(La):.4f}",
            "Lb": f"{to_mH_per_km(Lb):.4f}",
            "Lc": f"{to_mH_per_km(Lc):.4f}",
            "XLa": f"{XLa:.4f}", "XLb": f"{XLb:.4f}", "XLc": f"{XLc:.4f}",
            "Ca": f"{to_nF_per_km(Ca):.4f}",
            "Cb": f"{to_nF_per_km(Cb):.4f}",
            "Cc": f"{to_nF_per_km(Cc):.4f}",
            "Xca": f"{Xca:.4f}", "Xcb": f"{Xcb:.4f}", "Xcc": f"{Xcc:.4f}",
        }

    def _calc_double_circuit(self, freq, length, D12, D23, D31, D_between,
                             rmg_m, r_m, rmg_haz_mm, r_bundle_mm, R_corr):
        """Double-circuit line – equivalent parallel combination."""
        dmg_eq, rmg_eq = double_circuit_gmr(rmg_m, D12, D23, D31, D_between)

        # Capacitance equivalent radius (same structure, using physical r)
        import math
        r_eq_cap = math.sqrt(r_m * D_between)

        # Inductance
        L_H_m   = inductance_per_meter(dmg_eq, rmg_eq)
        L_mH_km = to_mH_per_km(L_H_m)
        XL_km   = reactance_per_km(freq, L_H_m)
        XL_tot  = total_reactance(XL_km, length)

        # Capacitance
        C_F_m   = capacitance_per_meter(dmg_eq, r_eq_cap)
        C_nF_km = to_nF_per_km(C_F_m)
        Xc_km   = capacitive_reactance_per_km(freq, C_F_m)
        Xc_tot  = total_capacitive_reactance(Xc_km, length)

        return {
            "config":   "Doble Circuito",
            "dmg":      f"{dmg_eq:.4f}",
            "rmg_haz":  f"{rmg_eq*1000:.4f}",
            "r_bundle": f"{r_bundle_mm:.4f}",
            "L_mH_km":  f"{L_mH_km:.4f}",
            "XL_km":    f"{XL_km:.4f}",
            "R_corr":   f"{R_corr:.4f}",
            "XL_total": f"{XL_tot:.4f}",
            "C_nF_km":  f"{C_nF_km:.4f}",
            "Xc_km":    f"{Xc_km:.4f}",
            "Xc_total": f"{Xc_tot:.4f}",
            "La": None, "Lb": None, "Lc": None,
            "Ca": None, "Cb": None, "Cc": None,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _push_conductor_info(self, conductor: dict):
        self._view.display_conductor_info(
            name   = conductor[COL_CODE],
            rmg    = f"{float(conductor[COL_RMG]):.4f}",
            r_base = f"{float(conductor[COL_R_DC20]):.4f}",
        )


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _parse_pos(label: str, value: str) -> float:
    try:
        v = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"'{label}': valor no numérico → '{value}'.")
    if v <= 0:
        raise ValueError(f"'{label}': debe ser un número positivo (ingresado: {v}).")
    return v

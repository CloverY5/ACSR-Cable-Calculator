"""
AppController – mediates between ConductorDatabase (Model) and MainView (View).
"""

import math
from model.conductor_db import (
    ConductorDatabase,
    COL_CODE, COL_RMG, COL_R_DC20, COL_D_TOTAL, COL_RATIO,
)
from model.calculations import (
    acsr_resistance,
    bundle_gmr,
    bundle_radius,
    geometric_mean_distance,
    inductance_per_meter,
    inductance_untransposed,
    conductor_gmr_m,
    rmg_side,
    dmg_between_sides,
    inductance_double_circuit,
    capacitance_double_circuit,
    capacitance_per_meter,
    capacitance_untransposed,
    reactance_per_km,
    capacitive_reactance_per_km,
    total_reactance,
    total_capacitive_reactance,
    total_resistance,
    to_mH_per_km,
    to_nF_per_km,
)

COL_D_AL = "D. Alambre Al (mm)"
COL_D_AC = "D. Alambre Acero (mm)"

CFG_TRANSPOSED   = "transposed"
CFG_UNTRANSPOSED = "untransposed"
CFG_DOUBLE       = "double"


class AppController:
    """Wires the View to the Model."""

    def __init__(self, view, db: ConductorDatabase):
        self._view = view
        self._db   = db

        self._previewed_conductor: dict | None = None
        self._confirmed_conductor: dict | None = None
        # Second conductor for double-circuit when sides are different
        self._previewed_conductor_b: dict | None = None
        self._confirmed_conductor_b: dict | None = None

        view.set_controller(self)
        calibres = self._db.get_unique_calibres()
        self._view.populate_calibre_list(calibres)
        self._view.populate_calibre_list_b(calibres)

    # ------------------------------------------------------------------
    # Catalog – side A (default)
    # ------------------------------------------------------------------

    def handle_search_by_code(self, code: str):
        if not code.strip():
            self._view.show_error("Campo vacío", "Ingrese el código del conductor.")
            return
        conductor = self._db.search_by_code(code)
        if conductor is None:
            self._view.show_error(
                "No encontrado",
                f"El conductor '{code}' no existe en el catálogo."
            )
            return
        self._previewed_conductor = conductor
        self._push_conductor_info(conductor)

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
    # Catalog – side B (for different-conductor double circuit)
    # ------------------------------------------------------------------

    def handle_calibre_selected_b(self, calibre: str):
        ratios = self._db.get_ratios_for_calibre(calibre)
        if not ratios:
            return
        auto = ratios[0] if len(ratios) == 1 else None
        self._view.populate_ratio_list_b(ratios, auto_select=auto)
        if auto is not None:
            self.handle_ratio_selected_b(calibre, auto)

    def handle_ratio_selected_b(self, calibre: str, ratio: str):
        codes = self._db.get_codes_by_filter(calibre, ratio)
        if not codes:
            return
        auto = codes[0] if len(codes) == 1 else None
        self._view.populate_conductor_list_b(codes, auto_select=auto)
        if auto is not None:
            self.handle_conductor_selected_b(auto)

    def handle_conductor_selected_b(self, code: str):
        conductor = self._db.search_by_code(code)
        if conductor is None:
            return
        self._previewed_conductor_b = conductor
        self._view.display_conductor_info_b(
            name = conductor[COL_CODE],
            rmg  = f"{float(conductor[COL_RMG]):.4f}",
        )

    def handle_confirm_conductor_b(self):
        if self._previewed_conductor_b is None:
            self._view.show_error("Sin selección",
                                  "Seleccione un conductor para el circuito B.")
            return
        self._confirmed_conductor_b = self._previewed_conductor_b
        name = self._confirmed_conductor_b[COL_CODE]
        self._view.show_info(
            "Conductor circuito B confirmado",
            f"'{name}' será usado para el lado B de la línea."
        )

    # ------------------------------------------------------------------
    # Calculation dispatcher
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

            rmg_mm     = float(self._confirmed_conductor[COL_RMG])
            d_total_mm = float(self._confirmed_conductor[COL_D_TOTAL])
            r_cond_m   = (d_total_mm / 2.0) / 1000.0

            n_al, n_ac = _parse_stranding(self._confirmed_conductor[COL_RATIO])
            d_al_mm = float(self._confirmed_conductor[COL_D_AL])
            d_ac_mm = float(self._confirmed_conductor[COL_D_AC])

            if n_cond > 1:
                spacing = _parse_pos("Separación del haz", params["spacing"])
            else:
                spacing = 0.0

        except (ValueError, TypeError) as exc:
            self._view.show_error("Error de entrada", str(exc))
            return

        try:
            # ── ACSR resistance correction (always computed for side A) ──
            res_dict = acsr_resistance(n_al, d_al_mm, n_ac, d_ac_mm, temp)
            R_TOT = res_dict["R_TOT"]
            R_total_line = total_resistance(R_TOT, length)

            rmg_haz_m  = bundle_gmr(rmg_mm, spacing, n_cond)
            r_bundle_m = bundle_radius(r_cond_m, spacing, n_cond)
            rmg_haz_mm  = rmg_haz_m  * 1000.0
            r_bundle_mm = r_bundle_m * 1000.0

            if config == CFG_TRANSPOSED:
                results = self._calc_transposed(
                    freq, length, D12, D23, D31,
                    rmg_haz_m, r_bundle_m, rmg_haz_mm, r_bundle_mm
                )
            elif config == CFG_UNTRANSPOSED:
                results = self._calc_untransposed(
                    freq, length, D12, D23, D31,
                    rmg_mm / 1000.0, r_cond_m, rmg_haz_mm
                )
            elif config == CFG_DOUBLE:
                results = self._calc_double_general(
                    freq, length, temp,
                    rmg_mm, r_cond_m, params
                )
                # Override resistance for double-circuit:
                #   if different conductors → parallel of R_TOT_A and R_TOT_B
                if results.get("R_TOT_override") is not None:
                    R_TOT = results["R_TOT_override"]
                    R_total_line = total_resistance(R_TOT, length)
                    # Also override res_dict with composite info
                    res_dict = results.get("res_dict_override", res_dict)
            else:
                self._view.show_error("Configuración",
                                      f"Configuración desconocida: {config}")
                return

            results["res_data"]     = res_dict
            results["R_TOT"]        = f"{R_TOT:.6f}"
            results["R_total_line"] = f"{R_total_line:.4f}"

        except (ValueError, ZeroDivisionError) as exc:
            self._view.show_error("Error de cálculo", str(exc))
            return

        self._view.display_results(results)

    # ------------------------------------------------------------------
    # Per-configuration calculations
    # ------------------------------------------------------------------

    def _calc_transposed(self, freq, length, D12, D23, D31,
                         rmg_haz_m, r_bundle_m, rmg_haz_mm, r_bundle_mm):
        dmg = geometric_mean_distance(D12, D23, D31)

        L_H_m   = inductance_per_meter(dmg, rmg_haz_m)
        L_mH_km = to_mH_per_km(L_H_m)
        XL_km   = reactance_per_km(freq, L_H_m)
        XL_tot  = total_reactance(XL_km, length)

        C_F_m   = capacitance_per_meter(dmg, r_bundle_m)
        C_nF_km = to_nF_per_km(C_F_m)
        Xc_km   = capacitive_reactance_per_km(freq, C_F_m)
        Xc_tot  = total_capacitive_reactance(Xc_km, length)

        return {
            "config":   "Transpuesta",
            "dmg":      f"{dmg:.4f}",
            "rmg_haz":  f"{rmg_haz_mm:.4f}",
            "r_bundle": f"{r_bundle_mm:.4f}",
            "L_mH_km":  f"{L_mH_km:.4f}",
            "XL_km":    f"{XL_km:.4f}",
            "XL_total": f"{XL_tot:.4f}",
            "C_nF_km":  f"{C_nF_km:.4f}",
            "Xc_km":    f"{Xc_km:.4f}",
            "Xc_total": f"{Xc_tot:.4f}",
            "La": None, "Lb": None, "Lc": None,
            "Ca": None, "Cb": None, "Cc": None,
            "double_info": None,
        }

    def _calc_untransposed(self, freq, length, D12, D23, D31,
                           rmg_m, r_m, rmg_haz_mm):
        dmg = geometric_mean_distance(D12, D23, D31)

        La, Lb, Lc = inductance_untransposed(rmg_m, D12, D23, D31)
        L_avg = (La + Lb + Lc) / 3.0

        XLa = reactance_per_km(freq, La)
        XLb = reactance_per_km(freq, Lb)
        XLc = reactance_per_km(freq, Lc)

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
            "XL_total": f"{total_reactance(reactance_per_km(freq, L_avg), length):.4f}",
            "C_nF_km":  f"{to_nF_per_km(C_avg):.4f}",
            "Xc_km":    f"{capacitive_reactance_per_km(freq, C_avg):.4f}",
            "Xc_total": f"{total_capacitive_reactance(capacitive_reactance_per_km(freq, C_avg), length):.4f}",
            "La":  f"{to_mH_per_km(La):.4f}",
            "Lb":  f"{to_mH_per_km(Lb):.4f}",
            "Lc":  f"{to_mH_per_km(Lc):.4f}",
            "XLa": f"{XLa:.4f}", "XLb": f"{XLb:.4f}", "XLc": f"{XLc:.4f}",
            "Ca":  f"{to_nF_per_km(Ca):.4f}",
            "Cb":  f"{to_nF_per_km(Cb):.4f}",
            "Cc":  f"{to_nF_per_km(Cc):.4f}",
            "Xca": f"{Xca:.4f}", "Xcb": f"{Xcb:.4f}", "Xcc": f"{Xcc:.4f}",
            "double_info": None,
        }

    def _calc_double_general(self, freq, length, temp,
                             rmg_mm_A, r_cond_m_A, params):
        """
        Double-circuit / parallel circuits computed from (x, y) coordinates.

        Reads from params:
          coords_A          – list of (x, y) for side A
          coords_B          – list of (x, y) for side B
          same_conductors   – bool
          side_A_type       – 'acsr' or 'solid'
          side_A_radius_mm  – if solid (radius in mm)
          side_B_type       – 'acsr' or 'solid'
          side_B_radius_mm  – if solid
        """
        coords_A = params["coords_A"]
        coords_B = params["coords_B"]
        same     = params["same_conductors"]

        if len(coords_A) == 0:
            raise ValueError("El lado A no tiene conductores definidos.")
        if len(coords_B) == 0:
            raise ValueError("El lado B no tiene conductores definidos.")

        side_A_type      = params.get("side_A_type", "acsr")
        side_A_radius_mm = params.get("side_A_radius_mm", None)
        side_B_type      = params.get("side_B_type", "acsr")
        side_B_radius_mm = params.get("side_B_radius_mm", None)

        # ── Side A: determine GMR (inductance) and physical radius (capacitance)
        if side_A_type == "acsr":
            gmr_A_m = conductor_gmr_m(rmg_mm=rmg_mm_A, is_acsr=True)
            r_A_m   = r_cond_m_A
            name_A  = self._confirmed_conductor[COL_CODE]
        else:
            r_A_m = _parse_pos("Radio del conductor A", side_A_radius_mm) / 1000.0
            gmr_A_m = conductor_gmr_m(r_m=r_A_m, is_acsr=False)
            name_A  = f"Sólido r={r_A_m*1000:.2f} mm"

        # ── Side B
        if same:
            gmr_B_m = gmr_A_m
            r_B_m   = r_A_m
            name_B  = name_A
            conductor_b_for_res = None
        else:
            if side_B_type == "acsr":
                if self._confirmed_conductor_b is None:
                    raise ValueError("Confirme primero un conductor para el circuito B.")
                rmg_mm_B = float(self._confirmed_conductor_b[COL_RMG])
                d_tot_B  = float(self._confirmed_conductor_b[COL_D_TOTAL])
                gmr_B_m  = conductor_gmr_m(rmg_mm=rmg_mm_B, is_acsr=True)
                r_B_m    = (d_tot_B / 2.0) / 1000.0
                name_B   = self._confirmed_conductor_b[COL_CODE]
                conductor_b_for_res = self._confirmed_conductor_b
            else:
                r_B_m = _parse_pos("Radio del conductor B", side_B_radius_mm) / 1000.0
                gmr_B_m = conductor_gmr_m(r_m=r_B_m, is_acsr=False)
                name_B  = f"Sólido r={r_B_m*1000:.2f} mm"
                conductor_b_for_res = None

        # ── RMG of each side and mutual DMG (general formulas)
        RMG_A = rmg_side(coords_A, gmr_A_m)
        RMG_B = rmg_side(coords_B, gmr_B_m)
        DMG   = dmg_between_sides(coords_A, coords_B)

        # ── Inductance
        ind = inductance_double_circuit(RMG_A, RMG_B, DMG, same_conductors=same)
        L_total = ind["L_total"]
        XL_km   = reactance_per_km(freq, L_total)
        XL_tot  = total_reactance(XL_km, length)

        # ── Capacitance
        cap = capacitance_double_circuit(r_A_m, r_B_m, DMG, same_conductors=same)
        C_total = cap["C_total"]
        Xc_km   = capacitive_reactance_per_km(freq, C_total)
        Xc_tot  = total_capacitive_reactance(Xc_km, length)

        # ── Per-side L (and C) for the "different conductors" case
        if same:
            LA_disp = LB_disp = "—"
            CA_disp = CB_disp = "—"
        else:
            LA_disp = f"{to_mH_per_km(ind['L_A']):.4f}"
            LB_disp = f"{to_mH_per_km(ind['L_B']):.4f}"
            CA_disp = f"{to_nF_per_km(cap['C_A']):.4f}"
            CB_disp = f"{to_nF_per_km(cap['C_B']):.4f}"

        # ── Resistance handling for double circuit
        R_TOT_override = None
        res_dict_override = None
        if same:
            # use the normal acsr_resistance of side A; nothing to override
            pass
        else:
            # If both sides have a known ACSR, compute R for each and combine
            # in parallel (both circuits carry current in parallel).
            if side_A_type == "acsr" and side_B_type == "acsr" \
               and conductor_b_for_res is not None:
                # Side A resistance already computed in the caller
                n_al_A, n_ac_A = _parse_stranding(self._confirmed_conductor[COL_RATIO])
                d_al_A = float(self._confirmed_conductor[COL_D_AL])
                d_ac_A = float(self._confirmed_conductor[COL_D_AC])
                resA = acsr_resistance(n_al_A, d_al_A, n_ac_A, d_ac_A, temp)

                n_al_B, n_ac_B = _parse_stranding(conductor_b_for_res[COL_RATIO])
                d_al_B = float(conductor_b_for_res[COL_D_AL])
                d_ac_B = float(conductor_b_for_res[COL_D_AC])
                resB = acsr_resistance(n_al_B, d_al_B, n_ac_B, d_ac_B, temp)

                R_TOT_override = (resA["R_TOT"] * resB["R_TOT"]) / \
                                 (resA["R_TOT"] + resB["R_TOT"])
                # Use side-A dict but flag combined R_TOT
                res_dict_override = resA
            # If any side is solid, skip resistance override (user uses side A)

        return {
            "config":   "Doble Circuito" + (" (iguales)" if same else " (distintos)"),
            "dmg":      f"{DMG:.4f}",
            "rmg_haz":  f"{RMG_A*1000:.4f}",
            "r_bundle": f"{r_A_m*1000:.4f}",
            "L_mH_km":  f"{to_mH_per_km(L_total):.4f}",
            "XL_km":    f"{XL_km:.4f}",
            "XL_total": f"{XL_tot:.4f}",
            "C_nF_km":  f"{to_nF_per_km(C_total):.4f}",
            "Xc_km":    f"{Xc_km:.4f}",
            "Xc_total": f"{Xc_tot:.4f}",
            "La": None, "Lb": None, "Lc": None,
            "Ca": None, "Cb": None, "Cc": None,
            # Extra info for double-circuit details panel
            "double_info": {
                "name_A":  name_A,
                "name_B":  name_B,
                "same":    same,
                "n_A":     len(coords_A),
                "n_B":     len(coords_B),
                "RMG_A":   f"{RMG_A:.4f}",
                "RMG_B":   f"{RMG_B:.4f}",
                "DMG":     f"{DMG:.4f}",
                "L_A":     LA_disp,
                "L_B":     LB_disp,
                "C_A":     CA_disp,
                "C_B":     CB_disp,
            },
            "R_TOT_override": R_TOT_override,
            "res_dict_override": res_dict_override,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _push_conductor_info(self, conductor: dict):
        self._view.display_conductor_info(
            name   = conductor[COL_CODE],
            rmg    = f"{float(conductor[COL_RMG]):.4f}",
            r_base = f"{float(conductor[COL_R_DC20]):.4f}",
        )


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _parse_pos(label: str, value) -> float:
    try:
        v = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"'{label}': valor no numérico → '{value}'.")
    if v <= 0:
        raise ValueError(f"'{label}': debe ser un número positivo (ingresado: {v}).")
    return v


def _parse_stranding(ratio: str) -> tuple[int, int]:
    try:
        parts = ratio.replace(" ", "").split("/")
        n_al = int(parts[0])
        n_ac = int(parts[1])
        if n_al <= 0 or n_ac <= 0:
            raise ValueError
        return n_al, n_ac
    except (ValueError, IndexError, AttributeError):
        raise ValueError(f"Formato de cableado no reconocido: '{ratio}' (esperado 'NN/NN').")

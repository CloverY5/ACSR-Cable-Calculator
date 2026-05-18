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
    inductance_monophasic,
    capacitance_per_meter,
    capacitance_untransposed,
    capacitance_monophasic,
    conductor_gmr_m,
    rigorous_double_circuit_params,
    reactance_per_km,
    capacitive_reactance_per_km,
    total_reactance,
    total_capacitive_reactance,
    total_resistance,
    to_mH_per_km,
    to_nF_per_km,
    to_uF_per_km,
)

COL_D_AL = "D. Alambre Al (mm)"
COL_D_AC = "D. Alambre Acero (mm)"

CFG_TRANSPOSED   = "transposed"
CFG_UNTRANSPOSED = "untransposed"
CFG_DOUBLE       = "double"
CFG_MONOPHASIC   = "monophasic"


class AppController:
    """Wires the View to the Model."""

    def __init__(self, view, db: ConductorDatabase):
        self._view = view
        self._db   = db

        self._previewed_conductor: dict | None = None
        self._confirmed_conductor: dict | None = None
        # Conductor for side/circuit B (monophasic with different conductors,
        # or double circuit with different conductors)
        self._previewed_conductor_b: dict | None = None
        self._confirmed_conductor_b: dict | None = None

        view.set_controller(self)
        calibres = self._db.get_unique_calibres()
        self._view.populate_calibre_list(calibres)
        self._view.populate_calibre_list_b(calibres)

    # ------------------------------------------------------------------
    # Catalog – conductor A (main)
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
    # Catalog – conductor B (for double-circuit with different conductors)
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
            f"'{name}' será usado para el lado B/circuito 2."
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

            # Single-circuit distances (only used by transposed/untransposed)
            if config in (CFG_TRANSPOSED, CFG_UNTRANSPOSED):
                D12 = _parse_pos("D₁₂", params["D12"])
                D23 = _parse_pos("D₂₃", params["D23"])
                D31 = _parse_pos("D₃₁", params["D31"])
            else:
                D12 = D23 = D31 = None

        except (ValueError, TypeError) as exc:
            self._view.show_error("Error de entrada", str(exc))
            return

        try:
            # ── Resistance (always for side A) ────────────────────────────
            res_dict = acsr_resistance(n_al, d_al_mm, n_ac, d_ac_mm, temp)
            R_TOT = res_dict["R_TOT"]
            R_total_line = total_resistance(R_TOT, length)

            # ── Bundle helpers ────────────────────────────────────────────
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
            elif config == CFG_MONOPHASIC:
                results = self._calc_monophasic(
                    freq, length, temp, params,
                    rmg_mm, r_cond_m, n_cond, spacing
                )
                if results.get("R_TOT_override") is not None:
                    R_TOT = results["R_TOT_override"]
                    R_total_line = total_resistance(R_TOT, length)
            elif config == CFG_DOUBLE:
                results = self._calc_double_rigorous(
                    freq, length, temp, params,
                    rmg_mm, r_cond_m, n_cond, spacing
                )
                if results.get("R_TOT_override") is not None:
                    R_TOT = results["R_TOT_override"]
                    R_total_line = total_resistance(R_TOT, length)
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
    # Calculations per configuration
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

        return self._common_result_dict(
            config="Transpuesta", dmg=dmg, rmg_haz=rmg_haz_mm, r_bundle=r_bundle_mm,
            L=L_mH_km, XL=XL_km, XL_tot=XL_tot,
            C=C_nF_km, Xc=Xc_km, Xc_tot=Xc_tot,
        )

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

        result = self._common_result_dict(
            config="No Transpuesta", dmg=dmg, rmg_haz=rmg_haz_mm, r_bundle=r_m*1000,
            L=to_mH_per_km(L_avg), XL=reactance_per_km(freq, L_avg),
            XL_tot=total_reactance(reactance_per_km(freq, L_avg), length),
            C=to_nF_per_km(C_avg),
            Xc=capacitive_reactance_per_km(freq, C_avg),
            Xc_tot=total_capacitive_reactance(capacitive_reactance_per_km(freq, C_avg), length),
        )
        result.update({
            "La":  f"{to_mH_per_km(La):.4f}",
            "Lb":  f"{to_mH_per_km(Lb):.4f}",
            "Lc":  f"{to_mH_per_km(Lc):.4f}",
            "XLa": f"{XLa:.4f}", "XLb": f"{XLb:.4f}", "XLc": f"{XLc:.4f}",
            "Ca":  f"{to_nF_per_km(Ca):.4f}",
            "Cb":  f"{to_nF_per_km(Cb):.4f}",
            "Cc":  f"{to_nF_per_km(Cc):.4f}",
            "Xca": f"{Xca:.4f}", "Xcb": f"{Xcb:.4f}", "Xcc": f"{Xcc:.4f}",
        })
        return result

    def _calc_monophasic(self, freq, length, temp, params,
                         rmg_mm_A, r_cond_m_A, n_cond, spacing):
        """Monophasic line: 2 conductors with possibly different radii."""
        mono = params.get("mono", {})
        same_cond = mono.get("same_conductors", True)
        side_A_type = mono.get("side_A_type", "acsr")
        side_B_type = mono.get("side_B_type", "acsr")
        D_m = _parse_pos("Distancia D entre conductores", mono.get("D_m", "4.0"))

        # ── Side A ─────────────────────────────────────────────────────
        if side_A_type == "acsr":
            r_A_m   = r_cond_m_A
            gmr_A_m = conductor_gmr_m(rmg_mm=rmg_mm_A, is_acsr=True)
            name_A  = self._confirmed_conductor[COL_CODE]
        else:
            r_A_m   = _parse_pos("Radio A", mono.get("side_A_radius_mm", 10)) / 1000.0
            gmr_A_m = conductor_gmr_m(r_m=r_A_m, is_acsr=False)
            name_A  = f"Sólido r={r_A_m*1000:.2f} mm"

        # ── Side B ─────────────────────────────────────────────────────
        if same_cond:
            r_B_m = r_A_m
            gmr_B_m = gmr_A_m
            name_B = name_A
            conductor_b_for_res = None
        else:
            if side_B_type == "acsr":
                if self._confirmed_conductor_b is None:
                    raise ValueError("Confirme primero un conductor para el lado B.")
                rmg_mm_B = float(self._confirmed_conductor_b[COL_RMG])
                d_tot_B  = float(self._confirmed_conductor_b[COL_D_TOTAL])
                r_B_m    = (d_tot_B / 2.0) / 1000.0
                gmr_B_m  = conductor_gmr_m(rmg_mm=rmg_mm_B, is_acsr=True)
                name_B   = self._confirmed_conductor_b[COL_CODE]
                conductor_b_for_res = self._confirmed_conductor_b
            else:
                r_B_m   = _parse_pos("Radio B", mono.get("side_B_radius_mm", 10)) / 1000.0
                gmr_B_m = conductor_gmr_m(r_m=r_B_m, is_acsr=False)
                name_B  = f"Sólido r={r_B_m*1000:.2f} mm"
                conductor_b_for_res = None

        # ── Apply bundle r_e if there is a bundle ──────────────────────
        if n_cond > 1:
            r_A_eff = bundle_radius(r_A_m, spacing, n_cond)
            r_B_eff = bundle_radius(r_B_m, spacing, n_cond)
            gmr_A_eff = bundle_gmr(gmr_A_m * 1000.0, spacing, n_cond)
            gmr_B_eff = bundle_gmr(gmr_B_m * 1000.0, spacing, n_cond)
        else:
            r_A_eff, r_B_eff = r_A_m, r_B_m
            gmr_A_eff, gmr_B_eff = gmr_A_m, gmr_B_m

        # ── Capacitance ────────────────────────────────────────────────
        cap = capacitance_monophasic(r_A_eff, r_B_eff, D_m)
        C_F_m = cap["C_an"]
        C_ab_F_m = cap["C_ab"]
        C_nF_km = to_nF_per_km(C_F_m)
        C_ab_nF_km = to_nF_per_km(C_ab_F_m)
        Xc_km   = capacitive_reactance_per_km(freq, C_F_m)
        Xc_tot  = total_capacitive_reactance(Xc_km, length)

        # ── Inductance (loop) ──────────────────────────────────────────
        L_H_m = inductance_monophasic(gmr_A_eff, gmr_B_eff, D_m)
        L_mH_km = to_mH_per_km(L_H_m)
        XL_km = reactance_per_km(freq, L_H_m)
        XL_tot = total_reactance(XL_km, length)

        # ── Combined ACSR resistance if B is also ACSR (parallel) ──────
        R_TOT_override = None
        if not same_cond and side_A_type == "acsr" and side_B_type == "acsr" \
                and conductor_b_for_res is not None:
            n_al_A, n_ac_A = _parse_stranding(self._confirmed_conductor[COL_RATIO])
            d_al_A = float(self._confirmed_conductor[COL_D_AL])
            d_ac_A = float(self._confirmed_conductor[COL_D_AC])
            resA = acsr_resistance(n_al_A, d_al_A, n_ac_A, d_ac_A, temp)

            n_al_B, n_ac_B = _parse_stranding(conductor_b_for_res[COL_RATIO])
            d_al_B = float(conductor_b_for_res[COL_D_AL])
            d_ac_B = float(conductor_b_for_res[COL_D_AC])
            resB = acsr_resistance(n_al_B, d_al_B, n_ac_B, d_ac_B, temp)

            # In monophasic loop, R_loop = R_A + R_B  (series)
            R_TOT_override = resA["R_TOT"] + resB["R_TOT"]

        result = self._common_result_dict(
            config=f"Monofásica ({'iguales' if same_cond else 'distintos'})",
            dmg=D_m, rmg_haz=gmr_A_eff*1000, r_bundle=r_A_eff*1000,
            L=L_mH_km, XL=XL_km, XL_tot=XL_tot,
            C=C_nF_km, Xc=Xc_km, Xc_tot=Xc_tot,
        )
        result.update({
            "mono_info": {
                "name_A":  name_A,
                "name_B":  name_B,
                "same":    same_cond,
                "r_A_mm":  f"{r_A_eff*1000:.4f}",
                "r_B_mm":  f"{r_B_eff*1000:.4f}",
                "D_m":     f"{D_m:.4f}",
                "C_an":    f"{C_nF_km:.4f}",
                "C_ab":    f"{C_ab_nF_km:.4f}",
            },
            "R_TOT_override": R_TOT_override,
        })
        return result

    def _calc_double_rigorous(self, freq, length, temp, params,
                              rmg_mm_A, r_cond_m_A, n_cond, spacing):
        """Rigorous double-circuit with phase identification (PDF formulas)."""
        dc = params.get("dc", {})
        same_cond = dc.get("same_conductors", True)
        side_A_type = dc.get("side_A_type", "acsr")
        side_B_type = dc.get("side_B_type", "acsr")

        # Phase coordinates (each phase has 2 conductors: one per circuit)
        phase_a = dc.get("phase_a", [])
        phase_b = dc.get("phase_b", [])
        phase_c = dc.get("phase_c", [])

        for label, coords in [("a", phase_a), ("b", phase_b), ("c", phase_c)]:
            if len(coords) != 2:
                raise ValueError(
                    f"La fase '{label}' debe tener exactamente 2 coordenadas "
                    f"(una para circuito A y otra para circuito B)."
                )

        # ── Determine GMR and r for side A ─────────────────────────────
        if side_A_type == "acsr":
            gmr_A_m = conductor_gmr_m(rmg_mm=rmg_mm_A, is_acsr=True)
            r_A_m   = r_cond_m_A
            name_A  = self._confirmed_conductor[COL_CODE]
        else:
            r_A_m = _parse_pos("Radio A", dc.get("side_A_radius_mm", 10)) / 1000.0
            gmr_A_m = conductor_gmr_m(r_m=r_A_m, is_acsr=False)
            name_A = f"Sólido r={r_A_m*1000:.2f} mm"

        # ── Apply bundle r_e if there are bundles ──────────────────────
        if n_cond > 1:
            gmr_self_L = bundle_gmr(gmr_A_m * 1000.0, spacing, n_cond)
            r_self_C   = bundle_radius(r_A_m, spacing, n_cond)
        else:
            gmr_self_L = gmr_A_m
            r_self_C   = r_A_m

        # For "different conductors", the rigorous PDF formula assumes
        # symmetry side-A = side-B (the formula uses a single gmr/r).
        # If users actually have different conductors per circuit, we still
        # honour their choice by averaging the per-side gmr/r.
        if not same_cond:
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
                r_B_m = _parse_pos("Radio B", dc.get("side_B_radius_mm", 10)) / 1000.0
                gmr_B_m = conductor_gmr_m(r_m=r_B_m, is_acsr=False)
                name_B = f"Sólido r={r_B_m*1000:.2f} mm"
                conductor_b_for_res = None
            if n_cond > 1:
                gmr_self_L = math.sqrt(
                    bundle_gmr(gmr_A_m * 1000.0, spacing, n_cond) *
                    bundle_gmr(gmr_B_m * 1000.0, spacing, n_cond)
                )
                r_self_C = math.sqrt(
                    bundle_radius(r_A_m, spacing, n_cond) *
                    bundle_radius(r_B_m, spacing, n_cond)
                )
            else:
                gmr_self_L = math.sqrt(gmr_A_m * gmr_B_m)
                r_self_C   = math.sqrt(r_A_m * r_B_m)
        else:
            name_B = name_A
            conductor_b_for_res = None

        # ── Apply rigorous formula ─────────────────────────────────────
        res = rigorous_double_circuit_params(
            phase_a_coords=phase_a,
            phase_b_coords=phase_b,
            phase_c_coords=phase_c,
            gmr_self_m=gmr_self_L,
            r_self_m=r_self_C,
        )

        L_H_m = res["L"]
        C_F_m = res["C"]
        L_mH_km = to_mH_per_km(L_H_m)
        XL_km   = reactance_per_km(freq, L_H_m)
        XL_tot  = total_reactance(XL_km, length)
        C_nF_km = to_nF_per_km(C_F_m)
        Xc_km   = capacitive_reactance_per_km(freq, C_F_m)
        Xc_tot  = total_capacitive_reactance(Xc_km, length)

        # ── Combined ACSR resistance if both are ACSR ──────────────────
        R_TOT_override = None
        if not same_cond and side_A_type == "acsr" and side_B_type == "acsr" \
                and conductor_b_for_res is not None:
            n_al_A, n_ac_A = _parse_stranding(self._confirmed_conductor[COL_RATIO])
            d_al_A = float(self._confirmed_conductor[COL_D_AL])
            d_ac_A = float(self._confirmed_conductor[COL_D_AC])
            resA = acsr_resistance(n_al_A, d_al_A, n_ac_A, d_ac_A, temp)

            n_al_B, n_ac_B = _parse_stranding(conductor_b_for_res[COL_RATIO])
            d_al_B = float(conductor_b_for_res[COL_D_AL])
            d_ac_B = float(conductor_b_for_res[COL_D_AC])
            resB = acsr_resistance(n_al_B, d_al_B, n_ac_B, d_ac_B, temp)

            # Double circuit → two circuits in parallel
            R_TOT_override = (resA["R_TOT"] * resB["R_TOT"]) / \
                             (resA["R_TOT"] + resB["R_TOT"])

        result = self._common_result_dict(
            config=f"Doble Circuito ({'iguales' if same_cond else 'distintos'})",
            dmg=res["DMG_e"], rmg_haz=res["RMG_e_L"]*1000, r_bundle=res["RMG_e_C"]*1000,
            L=L_mH_km, XL=XL_km, XL_tot=XL_tot,
            C=C_nF_km, Xc=Xc_km, Xc_tot=Xc_tot,
        )
        result.update({
            "double_info": {
                "name_A":  name_A,
                "name_B":  name_B,
                "same":    same_cond,
                "DMG_ab":  f"{res['DMG_ab']:.4f}",
                "DMG_bc":  f"{res['DMG_bc']:.4f}",
                "DMG_ac":  f"{res['DMG_ac']:.4f}",
                "DMG_e":   f"{res['DMG_e']:.4f}",
                "D_aa":    f"{res['D_aa']:.4f}",
                "D_bb":    f"{res['D_bb']:.4f}",
                "D_cc":    f"{res['D_cc']:.4f}",
                "RMG_a_L": f"{res['RMG_a_L']:.4f}",
                "RMG_b_L": f"{res['RMG_b_L']:.4f}",
                "RMG_c_L": f"{res['RMG_c_L']:.4f}",
                "RMG_e_L": f"{res['RMG_e_L']:.4f}",
                "RMG_a_C": f"{res['RMG_a_C']:.4f}",
                "RMG_b_C": f"{res['RMG_b_C']:.4f}",
                "RMG_c_C": f"{res['RMG_c_C']:.4f}",
                "RMG_e_C": f"{res['RMG_e_C']:.4f}",
            },
            "R_TOT_override": R_TOT_override,
        })
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _common_result_dict(self, config, dmg, rmg_haz, r_bundle,
                            L, XL, XL_tot, C, Xc, Xc_tot):
        """Build the base result dict with the standard fields."""
        return {
            "config":   config,
            "dmg":      f"{dmg:.4f}",
            "rmg_haz":  f"{rmg_haz:.4f}",
            "r_bundle": f"{r_bundle:.4f}",
            "L_mH_km":  f"{L:.4f}",
            "XL_km":    f"{XL:.4f}",
            "XL_total": f"{XL_tot:.4f}",
            "C_nF_km":  f"{C:.4f}",
            "Xc_km":    f"{Xc:.4f}",
            "Xc_total": f"{Xc_tot:.4f}",
            "La": None, "Lb": None, "Lc": None,
            "Ca": None, "Cb": None, "Cc": None,
            "double_info": None,
            "mono_info":   None,
        }

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

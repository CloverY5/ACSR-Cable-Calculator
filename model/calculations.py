"""
Electrical calculation engine for overhead transmission lines.
All formulas operate in SI base units internally (metres, ohms, henries, farads, seconds).

Supported configurations:
  - Monophasic line (2 conductors)             → C_an and C_ab
  - Transposed line (symmetric or asymmetric)  → DMG = (D12·D23·D31)^(1/3)
  - Untransposed asymmetric line               → L_a, L_b, L_c individually
  - Double-circuit / parallel circuits         → rigorous DMG_ab, DMG_bc, DMG_ac
                                                 and RMG_a, RMG_b, RMG_c per phase
  - Bundle of 1–4 sub-conductors per phase     → r_e for both single and double
  - ACSR resistance correction by individual material (Al ∥ Ac)
"""

import math
from itertools import product

# ── Material constants ──────────────────────────────────────────────────────
RHO_AL: float = 0.02781   # Aluminium  [Ω·mm²/m]
RHO_AC: float = 0.14017   # Steel core [Ω·mm²/m]

ALPHA_AL: float = 0.004027  # [1/°C]
ALPHA_AC: float = 0.004305  # [1/°C]

T_BASE:    float = 20.0      # °C
EPSILON_0: float = 8.85e-12  # F/m

# Factor for solid round conductors:  r' = r · e^(-1/4) ≈ r · 0.7788
SOLID_GMR_FACTOR: float = 0.7788


# ===========================================================================
# 1. RESISTANCE — ACSR
# ===========================================================================

def stranding_factor(n_strands: int) -> float:
    if n_strands <= 3:
        return 1.01
    elif n_strands <= 11:
        return 1.02
    else:
        return 1.03


def wire_area(n_strands: int, diameter_mm: float) -> float:
    if n_strands <= 0 or diameter_mm <= 0:
        raise ValueError("Número de hilos y diámetro deben ser > 0.")
    return n_strands * (math.pi / 4.0) * diameter_mm ** 2


def resistance_dc_20(rho: float, area_mm2: float, n_strands: int) -> float:
    if area_mm2 <= 0:
        raise ValueError("Área de la sección transversal debe ser > 0.")
    return rho * 1000.0 * stranding_factor(n_strands) / area_mm2


def correct_resistance_linear(R_20: float, alpha: float,
                              T_final: float, T_base: float = T_BASE) -> float:
    return R_20 * (1.0 + alpha * (T_final - T_base))


def parallel_resistance(R_a: float, R_b: float) -> float:
    if R_a <= 0 or R_b <= 0:
        raise ValueError("Ambas resistencias deben ser > 0.")
    return (R_a * R_b) / (R_a + R_b)


def acsr_resistance(n_al: int, d_al_mm: float,
                    n_ac: int, d_ac_mm: float,
                    T_final: float) -> dict:
    A_Al = wire_area(n_al, d_al_mm)
    A_Ac = wire_area(n_ac, d_ac_mm)
    R20_Al = resistance_dc_20(RHO_AL, A_Al, n_al)
    R20_Ac = resistance_dc_20(RHO_AC, A_Ac, n_ac)
    R_Al_T = correct_resistance_linear(R20_Al, ALPHA_AL, T_final)
    R_Ac_T = correct_resistance_linear(R20_Ac, ALPHA_AC, T_final)
    R_TOT  = parallel_resistance(R_Al_T, R_Ac_T)
    return {
        "n_al": n_al, "d_al_mm": d_al_mm, "A_Al": A_Al,
        "factor_al": stranding_factor(n_al),
        "n_ac": n_ac, "d_ac_mm": d_ac_mm, "A_Ac": A_Ac,
        "factor_ac": stranding_factor(n_ac),
        "R20_Al": R20_Al, "R20_Ac": R20_Ac,
        "T_final": T_final, "R_Al_T": R_Al_T, "R_Ac_T": R_Ac_T,
        "R_TOT": R_TOT,
    }


# ===========================================================================
# 2. GMR / GMD / r_e HELPERS
# ===========================================================================

def bundle_gmr(rmg_cond_mm: float, d_m: float, n: int) -> float:
    """Bundle GMR for inductance (uses RMG of individual conductor)."""
    r = rmg_cond_mm / 1000.0
    if n == 1:   return r
    elif n == 2: return (r * d_m) ** 0.5
    elif n == 3: return (r * d_m ** 2) ** (1.0 / 3.0)
    elif n == 4: return 1.09 * (r * d_m ** 3) ** 0.25
    else:
        raise ValueError(f"Número de conductores por fase no soportado: {n} (rango 1–4).")


def bundle_radius(r_cond_m: float, d_m: float, n: int) -> float:
    """
    Equivalent radius r_e of a bundle for CAPACITANCE.
    Same structure as bundle_gmr but uses physical radius r:
        n=1: r
        n=2: √(r·s)
        n=3: ∛(r·s²)
        n=4: 1.09·⁴√(r·s³)
    """
    r = r_cond_m
    if n == 1:   return r
    elif n == 2: return (r * d_m) ** 0.5
    elif n == 3: return (r * d_m ** 2) ** (1.0 / 3.0)
    elif n == 4: return 1.09 * (r * d_m ** 3) ** 0.25
    else:
        raise ValueError(f"Número de conductores por fase no soportado: {n} (rango 1–4).")


def geometric_mean_distance(D12: float, D23: float, D31: float) -> float:
    if D12 <= 0 or D23 <= 0 or D31 <= 0:
        raise ValueError("D₁₂, D₂₃ y D₃₁ deben ser > 0.")
    return (D12 * D23 * D31) ** (1.0 / 3.0)


def distance(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    """Euclidean distance between two points (x, y) in metres."""
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def conductor_gmr_m(rmg_mm: float | None = None,
                    r_m: float | None = None,
                    is_acsr: bool = True) -> float:
    """GMR of a single conductor in metres."""
    if is_acsr:
        if rmg_mm is None or rmg_mm <= 0:
            raise ValueError("ACSR: el RMG del conductor debe ser > 0.")
        return rmg_mm / 1000.0
    else:
        if r_m is None or r_m <= 0:
            raise ValueError("Conductor sólido: el radio debe ser > 0.")
        return r_m * SOLID_GMR_FACTOR


# ===========================================================================
# 3. INDUCTANCE — TRANSPOSED / UNTRANSPOSED single-circuit
# ===========================================================================

def inductance_per_meter(DMG_m: float, RMG_haz_m: float) -> float:
    """L = 2×10⁻⁷ · ln(DMG / RMG_haz)   [H/m]"""
    if RMG_haz_m <= 0:
        raise ValueError("RMG_haz debe ser positivo.")
    ratio = DMG_m / RMG_haz_m
    if ratio <= 1.0:
        raise ValueError(
            f"DMG ({DMG_m:.4f} m) debe ser mayor que RMG_haz ({RMG_haz_m*1000:.4f} mm)."
        )
    return 2e-7 * math.log(ratio)


def inductance_untransposed(rmg_m: float,
                            D12: float, D23: float, D31: float
                            ) -> tuple[float, float, float]:
    """Per-phase inductance of an untransposed asymmetric line."""
    if rmg_m <= 0 or D12 <= 0 or D23 <= 0 or D31 <= 0:
        raise ValueError("RMG y todas las distancias deben ser > 0.")
    La = 2e-7 * math.log(math.sqrt(D12 * D31) / rmg_m)
    Lb = 2e-7 * math.log(math.sqrt(D12 * D23) / rmg_m)
    Lc = 2e-7 * math.log(math.sqrt(D23 * D31) / rmg_m)
    return La, Lb, Lc


# ===========================================================================
# 4. CAPACITANCE — single-circuit
# ===========================================================================

def capacitance_per_meter(DMG_m: float, r_eq_m: float) -> float:
    """C_an = 2πε₀ / ln(DMG / r_eq)   [F/m]"""
    if r_eq_m <= 0:
        raise ValueError("Radio equivalente del conductor debe ser > 0.")
    ratio = DMG_m / r_eq_m
    if ratio <= 1.0:
        raise ValueError(
            f"DMG ({DMG_m:.4f} m) debe ser mayor que r_eq ({r_eq_m*1000:.4f} mm)."
        )
    return (2.0 * math.pi * EPSILON_0) / math.log(ratio)


def capacitance_untransposed(r_m: float,
                             D12: float, D23: float, D31: float
                             ) -> tuple[float, float, float]:
    """Per-phase capacitance to neutral of an untransposed asymmetric line."""
    if r_m <= 0 or D12 <= 0 or D23 <= 0 or D31 <= 0:
        raise ValueError("Radio y todas las distancias deben ser > 0.")
    Ca = (2.0 * math.pi * EPSILON_0) / math.log(math.sqrt(D12 * D31) / r_m)
    Cb = (2.0 * math.pi * EPSILON_0) / math.log(math.sqrt(D12 * D23) / r_m)
    Cc = (2.0 * math.pi * EPSILON_0) / math.log(math.sqrt(D23 * D31) / r_m)
    return Ca, Cb, Cc


# ===========================================================================
# 5. CAPACITANCE — MONOPHASIC LINE (2 conductors)
# ===========================================================================

def capacitance_monophasic(r_a_m: float, r_b_m: float, D_m: float) -> dict:
    """
    Capacitance of a monophasic line (2 conductors), per the project PDF.

        C_an  =  2πε₀ / ln(D / √(r_a · r_b))     [F/m]
        C_ab  =  C_an / 2                         [F/m]

    For equal radii (r_a = r_b = r):
        C_an  =  2πε₀ / ln(D / r)
        C_ab  =  πε₀  / ln(D / r)

    Args:
        r_a_m, r_b_m: physical radius of each conductor [m]
        D_m:          centre-to-centre distance between conductors [m]

    Returns:
        Dict with C_an and C_ab in F/m, plus the geometric ratio used.
    """
    if r_a_m <= 0 or r_b_m <= 0 or D_m <= 0:
        raise ValueError("Radios y distancia deben ser > 0.")

    r_eq = math.sqrt(r_a_m * r_b_m)
    ratio = D_m / r_eq
    if ratio <= 1.0:
        raise ValueError(
            f"La distancia D ({D_m:.4f} m) debe ser mayor que √(r_a·r_b) "
            f"({r_eq*1000:.4f} mm)."
        )
    C_an = (2.0 * math.pi * EPSILON_0) / math.log(ratio)
    C_ab = C_an / 2.0
    return {
        "C_an":    C_an,
        "C_ab":    C_ab,
        "r_eq_m":  r_eq,
        "ratio":   ratio,
    }


# ===========================================================================
# 6. INDUCTANCE — MONOPHASIC LINE (2 conductors)
# ===========================================================================

def inductance_monophasic(gmr_a_m: float, gmr_b_m: float, D_m: float) -> float:
    """
    Total inductance of a monophasic line (loop):
        L_loop = 4×10⁻⁷ · ln(D / √(GMR_a · GMR_b))   [H/m]
    Reference: Stevenson, eq. for monophasic line with two parallel conductors.
    """
    if gmr_a_m <= 0 or gmr_b_m <= 0 or D_m <= 0:
        raise ValueError("GMRs y distancia deben ser > 0.")
    gmr_eq = math.sqrt(gmr_a_m * gmr_b_m)
    ratio = D_m / gmr_eq
    if ratio <= 1.0:
        raise ValueError(
            f"La distancia D ({D_m:.4f} m) debe ser mayor que √(GMR_a·GMR_b) "
            f"({gmr_eq*1000:.4f} mm)."
        )
    return 4e-7 * math.log(ratio)


# ===========================================================================
# 7. DOUBLE-CIRCUIT — RIGOROUS PER-PHASE FORMULAS
# ===========================================================================

def rigorous_double_circuit_params(
        phase_a_coords: list[tuple[float, float]],
        phase_b_coords: list[tuple[float, float]],
        phase_c_coords: list[tuple[float, float]],
        gmr_self_m: float,
        r_self_m:  float,
        ) -> dict:
    """
    Rigorous double-circuit calculation following the project PDF:

        DMG_ab = ⁴√(D_ab · D_ab' · D_a'b · D_a'b')      (between phases a and b)
        DMG_bc = ⁴√(D_bc · D_bc' · D_b'c · D_b'c')      (between phases b and c)
        DMG_ac = ⁴√(D_ac · D_ac' · D_a'c · D_a'c')      (between phases a and c)
        DMG_e  = ∛(DMG_ab · DMG_bc · DMG_ac)

        RMG_a  = √(gmr · D_aa')      (GMR of phase a, two conductors in parallel)
        RMG_b  = √(gmr · D_bb')      (idem for b)
        RMG_c  = √(gmr · D_cc')      (idem for c)
        RMG_e  = ∛(RMG_a · RMG_b · RMG_c)

    Then:
        L = 2×10⁻⁷ · ln(DMG_e / RMG_e_gmr)        [H/m]   (uses gmr-based RMG)
        C = 2πε₀  / ln(DMG_e / RMG_e_r)           [F/m]   (uses radius-based RMG)

    Args:
        phase_a_coords: list of (x, y) for phase a (2 conductors: [a, a'])
        phase_b_coords: same for phase b
        phase_c_coords: same for phase c
        gmr_self_m:     GMR of a single conductor (for inductance) [m]
        r_self_m:       physical radius (for capacitance) [m]

    Returns:
        Dict with all DMGs, RMGs, the equivalent values and L, C.
    """
    # Validate that each phase has exactly two conductors
    for label, coords in (("a", phase_a_coords),
                          ("b", phase_b_coords),
                          ("c", phase_c_coords)):
        if len(coords) != 2:
            raise ValueError(
                f"La fase '{label}' debe tener exactamente 2 conductores "
                f"(tiene {len(coords)})."
            )

    a, a_p = phase_a_coords
    b, b_p = phase_b_coords
    c, c_p = phase_c_coords

    # ── DMG between phase pairs (4-th root of 4 distances) ─────────────────
    DMG_ab = (distance(a, b) * distance(a, b_p) *
              distance(a_p, b) * distance(a_p, b_p)) ** 0.25
    DMG_bc = (distance(b, c) * distance(b, c_p) *
              distance(b_p, c) * distance(b_p, c_p)) ** 0.25
    DMG_ac = (distance(a, c) * distance(a, c_p) *
              distance(a_p, c) * distance(a_p, c_p)) ** 0.25
    DMG_e  = (DMG_ab * DMG_bc * DMG_ac) ** (1.0 / 3.0)

    # ── RMG per phase (square root of 2 distances) ─────────────────────────
    D_aa = distance(a, a_p)
    D_bb = distance(b, b_p)
    D_cc = distance(c, c_p)

    if D_aa <= 0 or D_bb <= 0 or D_cc <= 0:
        raise ValueError("Los dos conductores de una misma fase no pueden coincidir.")

    # For inductance, the "self distance" is gmr_self_m (RMG of the conductor).
    # For capacitance, it is r_self_m (the physical radius).
    RMG_a_L = math.sqrt(gmr_self_m * D_aa)
    RMG_b_L = math.sqrt(gmr_self_m * D_bb)
    RMG_c_L = math.sqrt(gmr_self_m * D_cc)
    RMG_e_L = (RMG_a_L * RMG_b_L * RMG_c_L) ** (1.0 / 3.0)

    RMG_a_C = math.sqrt(r_self_m * D_aa)
    RMG_b_C = math.sqrt(r_self_m * D_bb)
    RMG_c_C = math.sqrt(r_self_m * D_cc)
    RMG_e_C = (RMG_a_C * RMG_b_C * RMG_c_C) ** (1.0 / 3.0)

    # ── Final L and C ──────────────────────────────────────────────────────
    if DMG_e / RMG_e_L <= 1.0:
        raise ValueError("DMG_e debe ser mayor que RMG_e (inductancia).")
    if DMG_e / RMG_e_C <= 1.0:
        raise ValueError("DMG_e debe ser mayor que RMG_e (capacitancia).")

    L_H_m = 2e-7 * math.log(DMG_e / RMG_e_L)
    C_F_m = (2.0 * math.pi * EPSILON_0) / math.log(DMG_e / RMG_e_C)

    return {
        # Distances between same-phase conductors
        "D_aa":   D_aa,
        "D_bb":   D_bb,
        "D_cc":   D_cc,
        # Per-pair DMGs
        "DMG_ab": DMG_ab,
        "DMG_bc": DMG_bc,
        "DMG_ac": DMG_ac,
        # Equivalent DMG
        "DMG_e":  DMG_e,
        # Per-phase RMGs (inductance)
        "RMG_a_L": RMG_a_L,
        "RMG_b_L": RMG_b_L,
        "RMG_c_L": RMG_c_L,
        "RMG_e_L": RMG_e_L,
        # Per-phase RMGs (capacitance)
        "RMG_a_C": RMG_a_C,
        "RMG_b_C": RMG_b_C,
        "RMG_c_C": RMG_c_C,
        "RMG_e_C": RMG_e_C,
        # Final results
        "L":      L_H_m,
        "C":      C_F_m,
    }


# ===========================================================================
# 8. REACTANCES & TOTALS
# ===========================================================================

def reactance_per_km(f: float, L_H_per_m: float) -> float:
    return 2.0 * math.pi * f * L_H_per_m * 1000.0


def capacitive_reactance_per_km(f: float, C_F_per_m: float) -> float:
    if C_F_per_m <= 0:
        raise ValueError("Capacitancia debe ser positiva.")
    return 1.0 / (2.0 * math.pi * f * C_F_per_m * 1000.0)


def total_reactance(XL_km: float, length_km: float) -> float:
    return XL_km * length_km


def total_capacitive_reactance(Xc_km: float, length_km: float) -> float:
    if length_km <= 0:
        raise ValueError("Longitud debe ser positiva.")
    return Xc_km / length_km


def total_resistance(R_km: float, length_km: float) -> float:
    return R_km * length_km


# ===========================================================================
# 9. UNIT CONVERSIONS
# ===========================================================================

def to_mH_per_km(L_H_per_m: float) -> float:
    return L_H_per_m * 1e6


def to_nF_per_km(C_F_per_m: float) -> float:
    return C_F_per_m * 1e12


def to_uF_per_km(C_F_per_m: float) -> float:
    """F/m → µF/km  (×10⁹)"""
    return C_F_per_m * 1e9

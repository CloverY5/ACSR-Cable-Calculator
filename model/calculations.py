"""
Electrical calculation engine for overhead transmission lines.
All formulas operate in SI base units internally (metres, ohms, henries, farads, seconds).

Supported configurations:
  - Transposed line (symmetric or asymmetric)  → DMG = (D12·D23·D31)^(1/3)
  - Untransposed asymmetric line               → L_a, L_b, L_c individually
  - Double-circuit / parallel circuits         → general RMG and DMG from (x,y) coords
  - Bundle of 1–4 sub-conductors per phase
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

# Factor that converts physical radius to GMR for a solid round conductor.
# r' = r · e^(-1/4) ≈ r · 0.7788
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
    """Full ACSR resistance correction (per project methodology)."""
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
# 2. GMR / GMD HELPERS
# ===========================================================================

def bundle_gmr(rmg_cond_mm: float, d_m: float, n: int) -> float:
    r = rmg_cond_mm / 1000.0
    if n == 1:   return r
    elif n == 2: return (r * d_m) ** 0.5
    elif n == 3: return (r * d_m ** 2) ** (1.0 / 3.0)
    elif n == 4: return 1.09 * (r * d_m ** 3) ** 0.25
    else:
        raise ValueError(f"Número de conductores por fase no soportado: {n} (rango 1–4).")


def bundle_radius(r_cond_m: float, d_m: float, n: int) -> float:
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


# ===========================================================================
# 3. INDUCTANCE – TRANSPOSED LINE
# ===========================================================================

def inductance_per_meter(DMG_m: float, RMG_haz_m: float) -> float:
    if RMG_haz_m <= 0:
        raise ValueError("RMG_haz debe ser positivo.")
    ratio = DMG_m / RMG_haz_m
    if ratio <= 1.0:
        raise ValueError(
            f"DMG ({DMG_m:.4f} m) debe ser mayor que RMG_haz ({RMG_haz_m*1000:.4f} mm)."
        )
    return 2e-7 * math.log(ratio)


# ===========================================================================
# 4. INDUCTANCE – UNTRANSPOSED ASYMMETRIC LINE
# ===========================================================================

def inductance_untransposed(rmg_m: float,
                            D12: float, D23: float, D31: float
                            ) -> tuple[float, float, float]:
    if rmg_m <= 0 or D12 <= 0 or D23 <= 0 or D31 <= 0:
        raise ValueError("RMG y todas las distancias deben ser > 0.")
    La = 2e-7 * math.log(math.sqrt(D12 * D31) / rmg_m)
    Lb = 2e-7 * math.log(math.sqrt(D12 * D23) / rmg_m)
    Lc = 2e-7 * math.log(math.sqrt(D23 * D31) / rmg_m)
    return La, Lb, Lc


# ===========================================================================
# 5. GENERAL DOUBLE-CIRCUIT / PARALLEL CIRCUITS (from (x, y) coordinates)
# ===========================================================================

def distance(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    """Euclidean distance between two points (x, y) in metres."""
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def conductor_gmr_m(rmg_mm: float | None = None,
                    r_m: float | None = None,
                    is_acsr: bool = True) -> float:
    """
    Returns the GMR (in metres) of a single conductor:
      - For ACSR  → rmg_mm / 1000 (the catalogue RMG)
      - For solid → r · 0.7788
    """
    if is_acsr:
        if rmg_mm is None or rmg_mm <= 0:
            raise ValueError("ACSR: el RMG del conductor debe ser > 0.")
        return rmg_mm / 1000.0
    else:
        if r_m is None or r_m <= 0:
            raise ValueError("Conductor sólido: el radio debe ser > 0.")
        return r_m * SOLID_GMR_FACTOR


def rmg_side(coords: list[tuple[float, float]], gmr_self_m: float) -> float:
    """
    Self GMR (RMG) of a group of n conductors on the same side
    (eq. 4.3 PDF, generalised):

        RMG = (n²)√[ ∏_{i,j} D_{ij} ]

    Diagonal terms D_ii are replaced by the individual conductor GMR
    (catalogue RMG for ACSR, r·0.7788 for solid).

    Args:
        coords      – list of (x, y) for each conductor on this side [m]
        gmr_self_m  – GMR of each individual conductor in this side  [m]

    Returns:
        RMG of the group [m]
    """
    n = len(coords)
    if n == 0:
        raise ValueError("El lado no puede tener cero conductores.")
    if n == 1:
        return gmr_self_m

    product_of_distances = 1.0
    for i in range(n):
        for j in range(n):
            if i == j:
                d_ij = gmr_self_m
            else:
                d_ij = distance(coords[i], coords[j])
                if d_ij <= 0:
                    raise ValueError(
                        f"Conductores {i+1} y {j+1} del mismo lado están en la misma posición."
                    )
            product_of_distances *= d_ij

    return product_of_distances ** (1.0 / (n * n))


def dmg_between_sides(coords_A: list[tuple[float, float]],
                      coords_B: list[tuple[float, float]]) -> float:
    """
    Mutual GMD between two groups of conductors (eq. 4.5 PDF, generalised):

        DMG = (m·n)√[ ∏_{i∈A, j∈B} D_{ij} ]

    Computed once even if conductors are different (only geometry matters).

    Args:
        coords_A – list of (x, y) on side 1 [m]
        coords_B – list of (x, y) on side 2 [m]

    Returns:
        DMG between the two groups [m]
    """
    m = len(coords_A)
    n = len(coords_B)
    if m == 0 or n == 0:
        raise ValueError("Ambos lados deben tener al menos un conductor.")

    product_of_distances = 1.0
    for pa, pb in product(coords_A, coords_B):
        d_ij = distance(pa, pb)
        if d_ij <= 0:
            raise ValueError(
                f"Conductores en posiciones idénticas entre los dos lados."
            )
        product_of_distances *= d_ij

    return product_of_distances ** (1.0 / (m * n))


def inductance_double_circuit(rmg_A_m: float,
                              rmg_B_m: float,
                              dmg_m: float,
                              same_conductors: bool) -> dict:
    """
    Inductance of a double-circuit / parallel-circuits line, per the project
    methodology (PDF "Cálculo de inductancia para conductores en paralelo o
    doble circuito"):

      • Equal conductors on both sides:
            L = 4×10⁻⁷ · ln(DMG / RMG)     [H/m]
        (a single inductance per metre of line for the whole parallel set)

      • Different conductors per side:
            L_A = 2×10⁻⁷ · ln(DMG / RMG_A)  [H/m]
            L_B = 2×10⁻⁷ · ln(DMG / RMG_B)  [H/m]
            L_T = L_A + L_B                  [H/m]

    Args:
        rmg_A_m         – RMG of the group on side A [m]
        rmg_B_m         – RMG of the group on side B [m]
        dmg_m           – mutual DMG between both sides [m]
        same_conductors – True if both circuits use the same conductor type

    Returns:
        Dict with keys: L_total, L_A, L_B (the per-side values are None when
        same_conductors=True), and DMG / RMG ratios for reference.
    """
    if dmg_m <= 0 or rmg_A_m <= 0 or rmg_B_m <= 0:
        raise ValueError("DMG y RMG deben ser positivos.")

    if same_conductors:
        rmg = rmg_A_m   # both equal
        ratio = dmg_m / rmg
        if ratio <= 1.0:
            raise ValueError(
                f"DMG ({dmg_m:.4f} m) debe ser mayor que RMG ({rmg*1000:.4f} mm)."
            )
        L_total = 4e-7 * math.log(ratio)
        return {
            "L_total": L_total,
            "L_A":     None,
            "L_B":     None,
            "rmg_A":   rmg_A_m,
            "rmg_B":   rmg_B_m,
            "dmg":     dmg_m,
        }
    else:
        if (dmg_m / rmg_A_m) <= 1.0 or (dmg_m / rmg_B_m) <= 1.0:
            raise ValueError(
                "DMG debe ser mayor que ambos RMG (lado A y lado B)."
            )
        L_A = 2e-7 * math.log(dmg_m / rmg_A_m)
        L_B = 2e-7 * math.log(dmg_m / rmg_B_m)
        return {
            "L_total": L_A + L_B,
            "L_A":     L_A,
            "L_B":     L_B,
            "rmg_A":   rmg_A_m,
            "rmg_B":   rmg_B_m,
            "dmg":     dmg_m,
        }


def capacitance_double_circuit(r_A_m: float, r_B_m: float,
                               dmg_m: float, same_conductors: bool) -> dict:
    """
    Capacitance to neutral for a double-circuit line, parallel of identical
    formulas to the inductance case but using the physical radius r:

      • Equal conductors:  C = 2πε₀ / [½·ln(DMG/r)]  =  4πε₀ / ln(DMG/r)
      • Different:         C_A = 2πε₀/ln(DMG/r_A),   C_B = 2πε₀/ln(DMG/r_B)
                            (combined as parallel capacitors)

    For the user-facing per-side display we keep them separate; total
    capacitance is the parallel sum.

    Args:
        r_A_m, r_B_m   – physical radius of the conductor on each side [m]
        dmg_m          – mutual DMG between both sides [m]
        same_conductors

    Returns:
        Dict with C_total, C_A, C_B (per-side None if same).
    """
    if dmg_m <= 0 or r_A_m <= 0 or r_B_m <= 0:
        raise ValueError("DMG y radios deben ser positivos.")

    if same_conductors:
        ratio = dmg_m / r_A_m
        if ratio <= 1.0:
            raise ValueError(
                f"DMG ({dmg_m:.4f} m) debe ser mayor que r ({r_A_m*1000:.4f} mm)."
            )
        C_total = (4.0 * math.pi * EPSILON_0) / math.log(ratio)
        return {
            "C_total": C_total,
            "C_A":     None,
            "C_B":     None,
        }
    else:
        if (dmg_m / r_A_m) <= 1.0 or (dmg_m / r_B_m) <= 1.0:
            raise ValueError(
                "DMG debe ser mayor que ambos radios (lado A y lado B)."
            )
        C_A = (2.0 * math.pi * EPSILON_0) / math.log(dmg_m / r_A_m)
        C_B = (2.0 * math.pi * EPSILON_0) / math.log(dmg_m / r_B_m)
        return {
            "C_total": C_A + C_B,
            "C_A":     C_A,
            "C_B":     C_B,
        }


# ===========================================================================
# 6. CAPACITANCE — single-circuit (transposed / untransposed)
# ===========================================================================

def capacitance_per_meter(DMG_m: float, r_eq_m: float) -> float:
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
    if r_m <= 0 or D12 <= 0 or D23 <= 0 or D31 <= 0:
        raise ValueError("Radio y todas las distancias deben ser > 0.")
    Ca = (2.0 * math.pi * EPSILON_0) / math.log(math.sqrt(D12 * D31) / r_m)
    Cb = (2.0 * math.pi * EPSILON_0) / math.log(math.sqrt(D12 * D23) / r_m)
    Cc = (2.0 * math.pi * EPSILON_0) / math.log(math.sqrt(D23 * D31) / r_m)
    return Ca, Cb, Cc


# ===========================================================================
# 7. REACTANCES & TOTALS
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
# 8. UNIT CONVERSIONS
# ===========================================================================

def to_mH_per_km(L_H_per_m: float) -> float:
    return L_H_per_m * 1e6


def to_nF_per_km(C_F_per_m: float) -> float:
    return C_F_per_m * 1e12

"""
Electrical calculation engine for overhead transmission lines.
All formulas operate in SI base units internally (metres, ohms, henries, farads, seconds).

Supported configurations:
  - Transposed line (symmetric or asymmetric)  → DMG = (D12·D23·D31)^(1/3)
  - Untransposed asymmetric line               → L_a, L_b, L_c individually
  - Double-circuit line (two 3-phase circuits) → equivalent RMG/DMG
  - Bundle of 1–4 sub-conductors per phase
  - ACSR resistance correction by individual material (Al ∥ Ac)
"""

import math

# ── Material constants ──────────────────────────────────────────────────────
# Resistivities in Ω·mm²/m so that R[Ω/km] = ρ · 1000 · Factor / A[mm²]
RHO_AL: float = 0.02781   # Aluminium  [Ω·mm²/m]
RHO_AC: float = 0.14017   # Steel core [Ω·mm²/m]

# Temperature coefficients α₁ at 20 °C [1/°C]
ALPHA_AL: float = 0.004027
ALPHA_AC: float = 0.004305

T_BASE:    float = 20.0      # Reference temperature [°C]
EPSILON_0: float = 8.85e-12  # Permittivity of free space [F/m]


# ===========================================================================
# 1. RESISTANCE — ACSR rigorous correction (per-material, in parallel)
# ===========================================================================

def stranding_factor(n_strands: int) -> float:
    """
    Stranding factor that accounts for the helical lay of strands in a cable.
        ≤  3 strands  → ×1.01  (+1%)
        ≤ 11 strands  → ×1.02  (+2%)
        > 11 strands  → ×1.03  (+3%)
    """
    if n_strands <= 3:
        return 1.01
    elif n_strands <= 11:
        return 1.02
    else:
        return 1.03


def wire_area(n_strands: int, diameter_mm: float) -> float:
    """Total cross-sectional area of a strand group:  A = n·(π/4)·D²   [mm²]"""
    if n_strands <= 0 or diameter_mm <= 0:
        raise ValueError("Número de hilos y diámetro deben ser > 0.")
    return n_strands * (math.pi / 4.0) * diameter_mm ** 2


def resistance_dc_20(rho: float, area_mm2: float, n_strands: int) -> float:
    """
    DC resistance per kilometre at 20 °C, including the stranding factor.
        R₂₀ = ρ · 1000 · Factor(n) / A   [Ω/km]
    """
    if area_mm2 <= 0:
        raise ValueError("Área de la sección transversal debe ser > 0.")
    return rho * 1000.0 * stranding_factor(n_strands) / area_mm2


def correct_resistance_linear(R_20: float, alpha: float,
                              T_final: float, T_base: float = T_BASE) -> float:
    """Linear temperature correction:  R_T = R₂₀ · [1 + α·(T_final − T_base)]"""
    return R_20 * (1.0 + alpha * (T_final - T_base))


def parallel_resistance(R_a: float, R_b: float) -> float:
    """Two resistances in parallel:  R = (R_a · R_b) / (R_a + R_b)."""
    if R_a <= 0 or R_b <= 0:
        raise ValueError("Ambas resistencias deben ser > 0.")
    return (R_a * R_b) / (R_a + R_b)


def acsr_resistance(n_al: int, d_al_mm: float,
                    n_ac: int, d_ac_mm: float,
                    T_final: float) -> dict:
    """
    Full ACSR resistance correction at T_final °C
    (per project methodology – Formulario-CRT).

    Steps:
        1. A_Al = n_Al · π/4 · D_Al²        (and same for steel)
        2. R₂₀_Al = ρ_Al · 1000 · Factor(n_Al) / A_Al
           R₂₀_Ac = ρ_Ac · 1000 · Factor(n_Ac) / A_Ac
        3. R_Al(T) = R₂₀_Al · [1 + α_Al · (T − 20)]
           R_Ac(T) = R₂₀_Ac · [1 + α_Ac · (T − 20)]
        4. R_TOT = (R_Al · R_Ac) / (R_Al + R_Ac)

    Returns dict with every intermediate result for the GUI.
    """
    A_Al = wire_area(n_al, d_al_mm)
    A_Ac = wire_area(n_ac, d_ac_mm)

    R20_Al = resistance_dc_20(RHO_AL, A_Al, n_al)
    R20_Ac = resistance_dc_20(RHO_AC, A_Ac, n_ac)

    R_Al_T = correct_resistance_linear(R20_Al, ALPHA_AL, T_final)
    R_Ac_T = correct_resistance_linear(R20_Ac, ALPHA_AC, T_final)

    R_TOT = parallel_resistance(R_Al_T, R_Ac_T)

    return {
        "n_al":      n_al,
        "d_al_mm":   d_al_mm,
        "A_Al":      A_Al,
        "factor_al": stranding_factor(n_al),
        "n_ac":      n_ac,
        "d_ac_mm":   d_ac_mm,
        "A_Ac":      A_Ac,
        "factor_ac": stranding_factor(n_ac),
        "R20_Al":    R20_Al,
        "R20_Ac":    R20_Ac,
        "T_final":   T_final,
        "R_Al_T":    R_Al_T,
        "R_Ac_T":    R_Ac_T,
        "R_TOT":     R_TOT,
    }


# ===========================================================================
# 2. GMR / GMD HELPERS
# ===========================================================================

def bundle_gmr(rmg_cond_mm: float, d_m: float, n: int) -> float:
    """
    GMR of a symmetrical bundle of n sub-conductors (inductance calculation).
        n=1 : r ; n=2 : (r·d)^½ ; n=3 : (r·d²)^⅓ ; n=4 : 1.09·(r·d³)^¼
    Returns GMR_bundle [m].
    """
    r = rmg_cond_mm / 1000.0
    if n == 1:   return r
    elif n == 2: return (r * d_m) ** 0.5
    elif n == 3: return (r * d_m ** 2) ** (1.0 / 3.0)
    elif n == 4: return 1.09 * (r * d_m ** 3) ** 0.25
    else:
        raise ValueError(f"Número de conductores por fase no soportado: {n} (rango 1–4).")


def bundle_radius(r_cond_m: float, d_m: float, n: int) -> float:
    """Equivalent radius of a bundle for CAPACITANCE calculation (uses physical r)."""
    r = r_cond_m
    if n == 1:   return r
    elif n == 2: return (r * d_m) ** 0.5
    elif n == 3: return (r * d_m ** 2) ** (1.0 / 3.0)
    elif n == 4: return 1.09 * (r * d_m ** 3) ** 0.25
    else:
        raise ValueError(f"Número de conductores por fase no soportado: {n} (rango 1–4).")


def geometric_mean_distance(D12: float, D23: float, D31: float) -> float:
    """DMG = (D12·D23·D31)^(1/3)   [m]"""
    if D12 <= 0 or D23 <= 0 or D31 <= 0:
        raise ValueError("D₁₂, D₂₃ y D₃₁ deben ser > 0.")
    return (D12 * D23 * D31) ** (1.0 / 3.0)


# ===========================================================================
# 3. INDUCTANCE – TRANSPOSED LINE
# ===========================================================================

def inductance_per_meter(DMG_m: float, RMG_haz_m: float) -> float:
    """L = 2×10⁻⁷ · ln(DMG / RMG_haz)   [H/m]  (eq. 4.47/4.52 PDF)"""
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
    """Per-phase inductance of an untransposed asymmetric line (eq. 4.41-4.43 PDF)."""
    if rmg_m <= 0 or D12 <= 0 or D23 <= 0 or D31 <= 0:
        raise ValueError("RMG y todas las distancias deben ser > 0.")
    La = 2e-7 * math.log(math.sqrt(D12 * D31) / rmg_m)
    Lb = 2e-7 * math.log(math.sqrt(D12 * D23) / rmg_m)
    Lc = 2e-7 * math.log(math.sqrt(D23 * D31) / rmg_m)
    return La, Lb, Lc


# ===========================================================================
# 5. INDUCTANCE – DOUBLE-CIRCUIT LINE
# ===========================================================================

def double_circuit_gmr(rmg_m: float,
                       D12: float, D23: float, D31: float,
                       D_between: float):
    """Equivalent (DMG_eq, RMG_eq) for a double-circuit 3-phase line."""
    if D_between <= 0:
        raise ValueError("Separación entre circuitos D_entre debe ser > 0.")
    DMG_single = geometric_mean_distance(D12, D23, D31)
    RMG_phase = math.sqrt(rmg_m * D_between)
    RMG_eq = RMG_phase           # geometric mean of three equal groups
    DMG_eq = DMG_single
    return DMG_eq, RMG_eq


# ===========================================================================
# 6. CAPACITANCE
# ===========================================================================

def capacitance_per_meter(DMG_m: float, r_eq_m: float) -> float:
    """C = 2πε₀ / ln(DMG / r_eq)   [F/m]  (eq. 4.76 PDF)"""
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
# 7. REACTANCES & TOTALS
# ===========================================================================

def reactance_per_km(f: float, L_H_per_m: float) -> float:
    """XL = 2π·f·L·1000   [Ω/km]"""
    return 2.0 * math.pi * f * L_H_per_m * 1000.0


def capacitive_reactance_per_km(f: float, C_F_per_m: float) -> float:
    """Xc = 1/(2π·f·C·1000)   [Ω·km]"""
    if C_F_per_m <= 0:
        raise ValueError("Capacitancia debe ser positiva.")
    return 1.0 / (2.0 * math.pi * f * C_F_per_m * 1000.0)


def total_reactance(XL_km: float, length_km: float) -> float:
    """XL_total = XL · length   [Ω]"""
    return XL_km * length_km


def total_capacitive_reactance(Xc_km: float, length_km: float) -> float:
    """Xc_total = Xc / length   [Ω]"""
    if length_km <= 0:
        raise ValueError("Longitud debe ser positiva.")
    return Xc_km / length_km


def total_resistance(R_km: float, length_km: float) -> float:
    """R_total = R · length   [Ω]"""
    return R_km * length_km


# ===========================================================================
# 8. UNIT CONVERSIONS
# ===========================================================================

def to_mH_per_km(L_H_per_m: float) -> float:
    """H/m → mH/km  (×10⁶)"""
    return L_H_per_m * 1e6


def to_nF_per_km(C_F_per_m: float) -> float:
    """F/m → nF/km  (×10¹²)"""
    return C_F_per_m * 1e12

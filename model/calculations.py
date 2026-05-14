"""
Electrical calculation engine for overhead transmission lines.
All formulas operate in SI base units internally (metres, ohms, henries, farads, seconds).

Supported configurations:
  - Transposed line (symmetric or asymmetric)  → DMG = (D12·D23·D31)^(1/3)
  - Untransposed asymmetric line               → L_a, L_b, L_c individually
  - Double-circuit line (two 3-phase circuits) → equivalent RMG/DMG
  - Bundle of 1–4 sub-conductors per phase
  - Inductance and capacitance (+ reactances) for all cases
"""

import math

# ── Material constants ──────────────────────────────────────────────────────
TC_ALUMINUM: float = 228.0   # Temperature constant for aluminium [°C]
T_BASE:      float = 20.0    # Base temperature matching R_CD_20C column [°C]
EPSILON_0:   float = 8.85e-12  # Permittivity of free space [F/m]


# ===========================================================================
# 1. RESISTANCE
# ===========================================================================

def correct_resistance(R1: float, T2: float,
                       T1: float = T_BASE,
                       Tc: float = TC_ALUMINUM) -> float:
    """
    Temperature-corrected resistance.
        R2 = R1 · (Tc + T2) / (Tc + T1)   [Ω/km]
    """
    return R1 * (Tc + T2) / (Tc + T1)


# ===========================================================================
# 2. GMR / GMD HELPERS
# ===========================================================================

def bundle_gmr(rmg_cond_mm: float, d_m: float, n: int) -> float:
    """
    GMR of a symmetrical bundle of n sub-conductors (inductance calculation).
        n=1 : r
        n=2 : (r·d)^½
        n=3 : (r·d²)^⅓
        n=4 : 1.09·(r·d³)^¼
    Returns GMR_bundle [m].
    """
    r = rmg_cond_mm / 1000.0
    if n == 1:
        return r
    elif n == 2:
        return (r * d_m) ** 0.5
    elif n == 3:
        return (r * d_m ** 2) ** (1.0 / 3.0)
    elif n == 4:
        return 1.09 * (r * d_m ** 3) ** 0.25
    else:
        raise ValueError(f"Número de conductores por fase no soportado: {n} (rango 1–4).")


def bundle_radius(r_cond_m: float, d_m: float, n: int) -> float:
    """
    Equivalent radius of a bundle for CAPACITANCE calculation.
    Same formulas as bundle_gmr but using the physical radius r instead of RMG.
    Returns RMG_C [m].
    """
    r = r_cond_m
    if n == 1:
        return r
    elif n == 2:
        return (r * d_m) ** 0.5
    elif n == 3:
        return (r * d_m ** 2) ** (1.0 / 3.0)
    elif n == 4:
        return 1.09 * (r * d_m ** 3) ** 0.25
    else:
        raise ValueError(f"Número de conductores por fase no soportado: {n} (rango 1–4).")


def geometric_mean_distance(D12: float, D23: float, D31: float) -> float:
    """
    GMD for a transposed asymmetric 3-phase line.
        DMG = (D12·D23·D31)^(1/3)   [m]
    """
    if D12 <= 0 or D23 <= 0 or D31 <= 0:
        raise ValueError("D₁₂, D₂₃ y D₃₁ deben ser > 0.")
    return (D12 * D23 * D31) ** (1.0 / 3.0)


# ===========================================================================
# 3. INDUCTANCE – TRANSPOSED LINE (symmetric or asymmetric)
# ===========================================================================

def inductance_per_meter(DMG_m: float, RMG_haz_m: float) -> float:
    """
    L = 2×10⁻⁷ · ln(DMG / RMG_haz)   [H/m]
    Valid for transposed symmetric and asymmetric lines (eq. 4.47/4.52 PDF).
    """
    if RMG_haz_m <= 0:
        raise ValueError("RMG_haz debe ser positivo.")
    ratio = DMG_m / RMG_haz_m
    if ratio <= 1.0:
        raise ValueError(
            f"DMG ({DMG_m:.4f} m) debe ser mayor que RMG_haz ({RMG_haz_m*1000:.4f} mm)."
        )
    return 2e-7 * math.log(ratio)


# ===========================================================================
# 4. INDUCTANCE – UNTRANSPOSED ASYMMETRIC LINE (one conductor per phase)
# ===========================================================================

def inductance_untransposed(rmg_m: float,
                            D12: float, D23: float, D31: float
                            ) -> tuple[float, float, float]:
    """
    Per-phase inductance of an untransposed asymmetric line (eq. 4.41-4.43 PDF).
    The three phases occupy fixed positions; inductance differs per phase.

    Args:
        rmg_m          – single-conductor GMR [m]
        D12, D23, D31  – phase-to-phase distances [m]

    Returns:
        (La, Lb, Lc) each in [H/m]

    Note: this assumes balanced currents Ia + Ib + Ic = 0.
    La uses D12 and D31 (distances from phase-a to the other phases).
    Lb uses D12 and D23.
    Lc uses D23 and D31.
    """
    if rmg_m <= 0 or D12 <= 0 or D23 <= 0 or D31 <= 0:
        raise ValueError("RMG y todas las distancias deben ser > 0.")

    # λ_a = 2e-7·[Ia·ln(1/r') + Ib·ln(1/D12) + Ic·ln(1/D31)]
    # With Ia = -(Ib+Ic) and assuming balanced → La = 2e-7·ln(√(D12·D31)/r')
    # More precisely from (4.41): positions 1=a, 2=b, 3=c
    La = 2e-7 * math.log(math.sqrt(D12 * D31) / rmg_m)
    Lb = 2e-7 * math.log(math.sqrt(D12 * D23) / rmg_m)
    Lc = 2e-7 * math.log(math.sqrt(D23 * D31) / rmg_m)
    return La, Lb, Lc


# ===========================================================================
# 5. INDUCTANCE – DOUBLE-CIRCUIT LINE
# ===========================================================================

def double_circuit_gmr(rmg_m: float,
                       D12: float, D23: float, D31: float,
                       D_between: float) -> float:
    """
    Equivalent GMR for a double-circuit 3-phase line (two circuits in parallel,
    sharing the same tower).

    Simplified model: both circuits have identical geometry; the second circuit
    is a mirror image displaced D_between [m] horizontally from the first.

    The equivalent GMR of each phase group (two conductors in parallel) is:
        RMG_eq = (RMG_single · D_aa')^½
    where D_aa' is the distance between the conductor of phase A in circuit 1
    and the conductor of phase A in circuit 2.

    The equivalent GMD is recalculated from the combined geometry using the
    GMD between phase groups (see Glover/Sarma eq. for double circuit).

    For a simple estimate with D_between >> D_phase:
        DMG_eq ≈ GMD_single  (phases see same average separation)
        RMG_eq = (RMG · D_between)^½   per phase

    Returns:
        (DMG_eq [m], RMG_eq [m])
    """
    if D_between <= 0:
        raise ValueError("Separación entre circuitos D_entre debe ser > 0.")

    DMG_single = geometric_mean_distance(D12, D23, D31)

    # Distance between same-phase conductors across circuits
    # For a vertical tower, approximate D_aa' ≈ D_between
    D_aa_prime = D_between
    D_bb_prime = D_between
    D_cc_prime = D_between

    # RMG of each phase group (two conductors in parallel)
    RMG_a = math.sqrt(rmg_m * D_aa_prime)
    RMG_b = math.sqrt(rmg_m * D_bb_prime)
    RMG_c = math.sqrt(rmg_m * D_cc_prime)
    RMG_eq = (RMG_a * RMG_b * RMG_c) ** (1.0 / 3.0)

    # GMD between phase groups (approximate: same as single circuit DMG
    # when D_between is much larger than phase spacing)
    DMG_eq = DMG_single

    return DMG_eq, RMG_eq


# ===========================================================================
# 6. CAPACITANCE – TRANSPOSED LINE
# ===========================================================================

def capacitance_per_meter(DMG_m: float, r_eq_m: float) -> float:
    """
    Positive-sequence capacitance to neutral for a transposed line.
        C = 2πε₀ / ln(DMG / r_eq)   [F/m]
    (eq. 4.76 PDF)

    Args:
        DMG_m  – geometric mean distance [m]
        r_eq_m – equivalent conductor radius (or bundle RMG_C) [m]

    Returns:
        C [F/m]
    """
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
    """
    Per-phase capacitance to neutral of an untransposed asymmetric line.
    Analogous to inductance_untransposed but using physical radius r.
    (Derived from eq. 4.70–4.72 PDF, same position-fixed approach.)

    Returns:
        (Ca, Cb, Cc) each in [F/m]
    """
    if r_m <= 0 or D12 <= 0 or D23 <= 0 or D31 <= 0:
        raise ValueError("Radio y todas las distancias deben ser > 0.")
    Ca = (2.0 * math.pi * EPSILON_0) / math.log(math.sqrt(D12 * D31) / r_m)
    Cb = (2.0 * math.pi * EPSILON_0) / math.log(math.sqrt(D12 * D23) / r_m)
    Cc = (2.0 * math.pi * EPSILON_0) / math.log(math.sqrt(D23 * D31) / r_m)
    return Ca, Cb, Cc


# ===========================================================================
# 7. REACTANCES
# ===========================================================================

def reactance_per_km(f: float, L_H_per_m: float) -> float:
    """XL = 2π·f·L·1000   [Ω/km]"""
    return 2.0 * math.pi * f * L_H_per_m * 1000.0


def capacitive_reactance_per_km(f: float, C_F_per_m: float) -> float:
    """
    Capacitive reactance to neutral per kilometre.
        Xc = 1 / (2π·f·C·1000)   [Ω·km]  (MΩ·km convention, returned as Ω·km)
    """
    if C_F_per_m <= 0:
        raise ValueError("Capacitancia debe ser positiva.")
    return 1.0 / (2.0 * math.pi * f * C_F_per_m * 1000.0)


def total_reactance(XL_km: float, length_km: float) -> float:
    """XL_total = XL · length   [Ω]"""
    return XL_km * length_km


def total_capacitive_reactance(Xc_km: float, length_km: float) -> float:
    """Xc_total = Xc / length   [Ω]  (capacitive reactances divide with length)"""
    if length_km <= 0:
        raise ValueError("Longitud debe ser positiva.")
    return Xc_km / length_km


# ===========================================================================
# 8. UNIT CONVERSIONS
# ===========================================================================

def to_mH_per_km(L_H_per_m: float) -> float:
    """H/m  →  mH/km  (×10⁶)"""
    return L_H_per_m * 1e6


def to_nF_per_km(C_F_per_m: float) -> float:
    """F/m  →  nF/km  (×10¹²)"""
    return C_F_per_m * 1e12

"""
ConductorDatabase: reads the ACSR catalogue from a CSV file using pandas.
Falls back to the built-in csv module if pandas is unavailable.
"""

import os
import csv as _csv

# Column constants — mapped to the actual CSV headers.
COL_RATIO    = "Cableado (Al/Ac)"              # Al/Ac stranding (e.g. "26/7")
COL_CODE     = "Código"                         # Conductor name  (e.g. "Drake")
COL_CALIBRE  = "Calibre (AWG/Kcmil)"           # AWG or kcmil    (e.g. "795")
COL_D_TOTAL  = "D. Total (mm)"                 # Overall diameter [mm]
COL_RMG      = "RMG (mm)"                      # Geometric mean radius [mm]
COL_R_DC20   = "R. Elec. CD a 20°C (Ohm/km)"  # DC resistance at 20 °C [Ω/km]
COL_R_AC75   = "R. Elec. CA a 75°C (Ohm/km)"  # AC resistance at 75 °C [Ω/km]
COL_CAP_IN   = "Capacidad In (A)"              # Rated current capacity [A]

_NUMERIC_COLS = [
    "D. Alambre Acero (mm)", "D. Alambre Al (mm)", "D. Núcleo (mm)", COL_D_TOTAL,
    COL_RMG, "Peso Al (kg/km)", "Peso Acero (kg/km)", "Peso Total (kg/km)",
    "Carga de Rotura (kg-f)", COL_R_DC20, COL_R_AC75, COL_CAP_IN, "Capacidad Icc (kA)",
]


class ConductorDatabase:
    """
    Loads and queries the ACSR conductor catalogue from 'ACSR-Tabla-RMG.csv'.
    """

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self._records: list[dict] = []
        self._load()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load(self):
        """Load the CSV, preferring pandas for robustness."""
        if not os.path.isfile(self.csv_path):
            raise FileNotFoundError(
                f"No se encontró el archivo de catálogo:\n{self.csv_path}"
            )
        try:
            import pandas as pd
            self._load_with_pandas(pd)
        except ImportError:
            self._load_with_csv()

    def _load_with_pandas(self, pd):
        df = pd.read_csv(self.csv_path, encoding="latin-1", skipinitialspace=True)
        # Strip whitespace from string columns
        for col in [COL_RATIO, COL_CODE, COL_CALIBRE]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
        # Cast numeric columns safely
        for col in _NUMERIC_COLS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        self._records = df.to_dict(orient="records")

    def _load_with_csv(self):
        """Fallback reader using the built-in csv module."""
        with open(self.csv_path, encoding="latin-1", newline="") as f:
            reader = _csv.DictReader(f)
            for row in reader:
                rec = {}
                for k, v in row.items():
                    v = v.strip() if isinstance(v, str) else v
                    if k in _NUMERIC_COLS:
                        try:
                            rec[k] = float(v)
                        except (ValueError, TypeError):
                            rec[k] = None
                    else:
                        rec[k] = v
                self._records.append(rec)

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_unique_calibres(self) -> list[str]:
        """Return the distinct calibre values in CSV order."""
        seen = []
        for r in self._records:
            c = r[COL_CALIBRE]
            if c not in seen:
                seen.append(c)
        return seen

    def get_ratios_for_calibre(self, calibre: str) -> list[str]:
        """Return unique Al/Ac ratios available for a given calibre."""
        seen = []
        for r in self._records:
            if r[COL_CALIBRE] == calibre and r[COL_RATIO] not in seen:
                seen.append(r[COL_RATIO])
        return seen

    def get_codes_by_filter(self, calibre: str, ratio: str) -> list[str]:
        """Return conductor code names that match both calibre and Al/Ac ratio."""
        return [
            r[COL_CODE]
            for r in self._records
            if r[COL_CALIBRE] == calibre and r[COL_RATIO] == ratio
        ]

    def search_by_code(self, code: str) -> dict | None:
        """Case-insensitive lookup by conductor code name. Returns the first match."""
        needle = code.strip().lower()
        for r in self._records:
            if r[COL_CODE].lower() == needle:
                return dict(r)
        return None
"""Central configuration: paths, random seeds, and dataset scale/demo constants.

Every other module reads paths and constants from here instead of hardcoding
them, so the whole pipeline can be reconfigured from one place.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# ml/src/common/config.py -> parents[3] is the repo root (OpAssure/).
PROJECT_ROOT = Path(__file__).resolve().parents[3]
ML_ROOT = PROJECT_ROOT / "ml"

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
SYNTHETIC_DIR = DATA_DIR / "synthetic"
GROUND_TRUTH_DIR = DATA_DIR / "ground_truth"

for _dir in (RAW_DIR, PROCESSED_DIR, SYNTHETIC_DIR, GROUND_TRUTH_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------

SEED = 42

# ---------------------------------------------------------------------------
# Dataset scale (per CLAUDE.md §6)
# ---------------------------------------------------------------------------

N_OPERATORS = 20
N_MACHINES = 8
N_DAYS = 60
SIM_START_DATE = "2026-06-01"  # arbitrary deterministic anchor date

SHIFT_START_HOUR = 7
SHIFT_END_HOUR = 17

TELEMETRY_INTERVAL_MIN = 5
WORKER_POSITION_INTERVAL_MIN = 10
N_SITE_WORKERS = 6

# ---------------------------------------------------------------------------
# Deterministic demo identifiers (per CLAUDE.md §7)
# ---------------------------------------------------------------------------

DEMO_OPERATOR_ID = "OP1001"
DEMO_MACHINE_ID = "EXC001"
DEMO_TASK_ID = "T001"

# ---------------------------------------------------------------------------
# Deterministic planted-anomaly identifiers (per CLAUDE.md §6)
# ---------------------------------------------------------------------------

SEATBELT_HABIT_OPERATOR_ID = "OP1005"
INEFFICIENT_OPERATOR_ID = "OP1010"
DEGRADING_MACHINE_ID = "EXC002"

SWING_ZONE_RADIUS_M = 8.0

# ---------------------------------------------------------------------------
# Time-aware split fractions (chronological, never shuffled — see evaluation/splits.py)
# ---------------------------------------------------------------------------

TRAIN_FRAC = 0.70
VAL_FRAC = 0.15
# remaining 0.15 is the test fraction

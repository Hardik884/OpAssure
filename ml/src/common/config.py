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

MODELS_DIR = ML_ROOT / "models"
ETA_MODEL_DIR = MODELS_DIR / "eta"

for _dir in (RAW_DIR, PROCESSED_DIR, SYNTHETIC_DIR, GROUND_TRUTH_DIR, ETA_MODEL_DIR):
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

# ---------------------------------------------------------------------------
# ETA model / uncertainty
# ---------------------------------------------------------------------------

# Residual-quantile interval (see src/eta/train.py): eta_min/eta_max are the
# point prediction plus the (q_low, q_high) empirical quantiles of the
# validation-set residuals. Simple, defensible, no separate quantile model.
ETA_RESIDUAL_QUANTILES = (0.10, 0.90)

# Recent-telemetry window used by dynamic ETA to detect a cycle-time change.
RECENT_TELEMETRY_ROWS = 3

# ---------------------------------------------------------------------------
# Operator Twin
# ---------------------------------------------------------------------------

# Empirical-Bayes-style shrinkage strength: an operator's estimate is blended
# with the fleet average as `n / (n + k)` operator-weight. Small k = trust
# operator data sooner; large k = need more history before trusting it.
OPERATOR_TWIN_SHRINKAGE_K = 5

# Fallback afternoon-hour threshold when an operator's own fatigue_start_hour
# isn't available for some reason (it normally is — operators.csv has it).
DEFAULT_AFTERNOON_HOUR = 13
HEAT_TEMP_THRESHOLD_C = 30.0

# ---------------------------------------------------------------------------
# Habit Radar
# ---------------------------------------------------------------------------

LEGITIMATE_IDLE_REASONS = {"waiting_for_truck", "waiting_for_instruction", "break"}
AVOIDABLE_IDLE_REASONS = {"unnecessary", "unnecessary_engine_running"}

# "A single unsafe event is NOT a habit" — all three thresholds must be met
# before detect_habits() flags something as an actual habit. The frequency
# bar is relative (z-score vs. the fleet), not a fixed absolute rate — see
# src/anomaly/habit_radar.py's docstring for why.
HABIT_MIN_OPPORTUNITIES = 3
HABIT_MIN_COUNT = 2
HABIT_Z_THRESHOLD = 2.0

# ---------------------------------------------------------------------------
# Focus Battery
# ---------------------------------------------------------------------------

FOCUS_BREAK_GAP_MIN = 20  # a gap this long between tasks counts as a break
FOCUS_REPETITIVE_TASK_THRESHOLD = 5  # tasks completed today before workload counts as repetitive

# ---------------------------------------------------------------------------
# Risk intelligence
# ---------------------------------------------------------------------------

RISK_PROXIMITY_ELEVATED_MULTIPLIER = 2.0  # within N x swing-zone radius = elevated (not yet critical)
RISK_LEVEL_BANDS = (("critical", 85), ("high", 60), ("medium", 30))  # else "low"

# ---------------------------------------------------------------------------
# Machine vs. operator fuel diagnosis
# ---------------------------------------------------------------------------

DIAGNOSIS_MIN_DISTINCT_ENTITIES = 3  # need evidence across >= this many operators/machines
DIAGNOSIS_ELEVATED_RATIO = 1.15  # 15% above fleet average fuel/moving-min to flag

# ---------------------------------------------------------------------------
# Just-in-Time Micro Training
# ---------------------------------------------------------------------------

# Evidence floors before a "repeated" pattern (not a single anomaly) can
# trigger a training recommendation.
TRAINING_MIN_PROXIMITY_EVENTS = 3  # near-misses for this operator before flagging proximity
TRAINING_MIN_TASKS_FOR_SENSITIVITY = 10  # operator needs this many tasks before a Twin sensitivity counts as evidence
TRAINING_SENSITIVITY_THRESHOLD = 0.15  # rain/heat sensitivity above this is "meaningful"
TRAINING_AFTERNOON_EFFECT_THRESHOLD = -0.10  # afternoonEffect below this is "meaningful"

# Training effectiveness observation window (the spec's "next FIVE relevant
# tasks/events") and the bar for calling an observed change "meaningful".
TRAINING_OBSERVATION_WINDOW = 5
TRAINING_MEANINGFUL_IMPROVEMENT = 0.15  # before-after drop >= this counts as "improving"
TRAINING_WORSENING_THRESHOLD = -0.05  # before-after drop <= this counts as "worsening"

# Instructor escalation
ESCALATION_SESSION_MINUTES = 20

# ---------------------------------------------------------------------------
# Pre-Task Threat Briefing
# ---------------------------------------------------------------------------

THREAT_BRIEFING_TOP_N = 3
THREAT_BRIEFING_SITE_LOOKBACK_DAYS = 14  # recent near-misses at this machine, within this window

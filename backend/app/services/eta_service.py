"""Deterministic ETA fallback (until the ML ETA model exists).

    estimate_eta(...) -> {"min", "max", "original", "reason", "bucketsRemaining"}

Pure function of what has been observed so far in the task:

    remaining work = buckets remaining x recent cycle time
    min = elapsed + remaining work                    (no more interruptions)
    max = elapsed + remaining work x (1 + PLAN_OVERHEAD)  (same allowance for waits
                                                           the plan itself uses)

Before there is enough data it returns the plan estimate. To swap in the ML
model, replace the body of `estimate_eta` — the eta_update contract stays the same.
"""

import math

PLAN_OVERHEAD = 0.15  # tasks.estimated_time_min = standard cycles + 15% (simulator/generate_data.py)
MIN_WORKING_SAMPLES = 3  # working telemetry rows needed before trusting the observed pace
SLOWDOWN_RATIO = 1.10  # recent cycles this much slower than the task's opening pace -> "slowed" reason
BEHIND_PLAN_MIN = 3  # max ETA this many minutes over plan -> "Behind plan" (avoids flapping on jitter)


def plan_eta(estimated_time_min: float, estimated_buckets: int) -> dict:
    original = round(estimated_time_min)
    return {"min": original, "max": original, "original": original, "reason": "Plan estimate",
            "bucketsRemaining": int(estimated_buckets)}


def estimate_eta(*, estimated_time_min: float, estimated_buckets: int, elapsed_min: float, cycles_done: float,
                 recent_cycle_s: float | None, baseline_cycle_s: float | None, working_samples: int,
                 idle_min: float, rain_mm: float | None = None) -> dict:
    """ETA range in minutes from task start. See module docstring."""
    original = round(estimated_time_min)
    remaining_buckets = max(0.0, estimated_buckets - cycles_done)
    if remaining_buckets == 0:
        done = round(elapsed_min)
        return {"min": done, "max": done, "original": original, "reason": "Task complete", "bucketsRemaining": 0}
    if working_samples < MIN_WORKING_SAMPLES or not recent_cycle_s:
        eta = plan_eta(estimated_time_min, estimated_buckets)
        eta["bucketsRemaining"] = math.ceil(remaining_buckets)
        return eta

    work_min = remaining_buckets * recent_cycle_s / 60
    eta_min = round(elapsed_min + work_min)
    eta_max = max(eta_min, round(elapsed_min + work_min * (1 + PLAN_OVERHEAD)))

    reasons = []
    if baseline_cycle_s and recent_cycle_s >= baseline_cycle_s * SLOWDOWN_RATIO:
        cause = f"Rain ({rain_mm:g} mm/h) slowed" if rain_mm else "Slower"
        reasons.append(f"{cause} cycles from {baseline_cycle_s:.1f} s to {recent_cycle_s:.1f} s")
    if idle_min >= 5:
        reasons.append(f"{idle_min:.0f} min of waiting so far")
    if not reasons:
        reasons.append("Behind plan" if eta_max >= original + BEHIND_PLAN_MIN else "On pace")
    return {"min": eta_min, "max": eta_max, "original": original, "reason": "; ".join(reasons),
            "bucketsRemaining": math.ceil(remaining_buckets)}

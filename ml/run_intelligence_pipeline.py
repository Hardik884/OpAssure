#!/usr/bin/env python
"""OpAssure Unified Operator Intelligence — single entry point.

Usage (from the repo root or from `ml/`):

    python ml/run_intelligence_pipeline.py

Runs `generate_operator_state()` for the deterministic demo scenario
(OP1001 / EXC001 / T001), then feeds one simulated realtime telemetry
update through `update_operator_state()` to show the live-update path. All
values come from the real generated data and the already-built/tested
modules — nothing here is fabricated.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd  # noqa: E402

from src.common import config  # noqa: E402
from src.intelligence.operator_state import generate_operator_state  # noqa: E402
from src.intelligence.realtime import update_operator_state  # noqa: E402


def _print_section(title: str, body: dict | list) -> None:
    print(f"\n{'-' * 29}\n{title}\n{'-' * 29}")
    if isinstance(body, list):
        if not body:
            print("  (none)")
        for item in body:
            print(f"  {item}")
    else:
        for k, v in body.items():
            print(f"  {k:<20} {v}")


def print_report(state: dict) -> None:
    _print_section("OPERATOR TWIN", state["operator_twin"])
    _print_section("CURRENT ETA", state["eta"])
    _print_section("DYNAMIC ETA", state["dynamic_eta"])
    _print_section("REMAINING WORK", state["remaining_work"])
    _print_section("SAFETY / RISK", state["risk"])
    _print_section("HABITS", state["habits"])
    _print_section("IDLE ANALYSIS", state["idle_analysis"])
    _print_section("FOCUS", state["focus"])
    _print_section("TRAINING", state["training"])
    _print_section("PRE-TASK THREAT BRIEF", state["threat_briefing"])
    _print_section("EXPLANATIONS", state["explanations"])


def main() -> None:
    print("=" * 70)
    print(f"UNIFIED OPERATOR INTELLIGENCE: {config.DEMO_OPERATOR_ID} / {config.DEMO_MACHINE_ID} / {config.DEMO_TASK_ID}")
    print("=" * 70)

    state = generate_operator_state(config.DEMO_OPERATOR_ID, config.DEMO_MACHINE_ID, config.DEMO_TASK_ID)
    print_report(state)

    # --- Realtime update demonstration --------------------------------------
    telemetry_df = state["_context"]["tables"]["telemetry"]
    task_telemetry = telemetry_df[telemetry_df["task_id"] == config.DEMO_TASK_ID].sort_values("timestamp")

    if len(task_telemetry) == 0:
        print("\n(No telemetry available for T001 to demonstrate a realtime update.)")
    else:
        print("\n" + "=" * 70)
        print("REALTIME UPDATE — telemetry rows applied one at a time (no model retraining)")
        print("=" * 70)
        current_state = state
        n_steps = min(4, len(task_telemetry))
        for i in range(n_steps):
            row = task_telemetry.iloc[i].to_dict()
            updated_state = update_operator_state(current_state, row)
            print(
                f"  step {i + 1}: dynamic_eta.eta_point={updated_state['dynamic_eta']['eta_point']}  "
                f"buckets_remaining={updated_state['remaining_work']['buckets_remaining']}  "
                f"risk_level={updated_state['risk']['risk_level']}"
            )
            current_state = updated_state

    print("\nIntelligence pipeline completed with no errors.\n")


if __name__ == "__main__":
    main()

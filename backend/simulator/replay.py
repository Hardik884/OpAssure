"""Run the shared demo replay against a running backend and print the live events.

    python -m simulator.replay                      # default interval (REPLAY_INTERVAL_SECONDS, 3 s)
    python -m simulator.replay --interval 0.5       # faster
    python -m simulator.replay --quiet              # hide telemetry_update lines
    python -m simulator.replay --no-start           # just listen (replay started elsewhere)

Connects to WS /ws, calls POST /demo/start, and prints every event until the
replay finishes. The replay itself runs inside the backend (app/services/replay_service.py).
"""

import argparse
import json
import sys
import urllib.request

from websockets.sync.client import connect


def _post(url: str) -> dict:
    req = urllib.request.Request(url, method="POST", data=b"")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.load(resp)


def _describe(message: dict) -> str:
    event, d = message["event"], message["data"]
    if event == "telemetry_update":
        return (f"{d['timestamp'][11:16]} cycle={d['cycleTime']} idle={d['idle']} fuel={d['fuel']} "
                f"belt={d['belt']} moving={d['movement']}")
    keep = {k: v for k, v in d.items() if k not in ("machineId", "operatorId", "taskId")}
    return json.dumps(keep)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://localhost:8000", help="backend base URL")
    parser.add_argument("--interval", type=float, default=None, help="seconds between rows")
    parser.add_argument("--quiet", action="store_true", help="do not print telemetry_update events")
    parser.add_argument("--no-start", action="store_true", help="only listen")
    args = parser.parse_args()

    ws_url = args.url.replace("http", "ws", 1).rstrip("/") + "/ws"
    with connect(ws_url, open_timeout=10) as ws:
        print(f"connected to {ws_url}")
        if not args.no_start:
            query = f"?interval={args.interval}" if args.interval is not None else ""
            result = _post(f"{args.url.rstrip('/')}/demo/start{query}")
            print(result["message"])
        for raw in ws:
            message = json.loads(raw)
            if args.quiet and message["event"] == "telemetry_update":
                continue
            print(f"{message['event']:<24} {_describe(message)}", flush=True)
            if message["event"] == "replay_status" and message["data"]["state"] in ("finished", "stopped", "error"):
                return 0 if message["data"]["state"] != "error" else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

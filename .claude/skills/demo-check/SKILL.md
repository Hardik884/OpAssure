---
name: demo-check
description: Run the OpAssure demo readiness checklist — verifies services, database, synthetic data, APIs, ML artifacts, WebSocket, frontend, and the core demo scenario (OP1001/EXC001/T001) all work end to end. Use before a demo run, before a milestone review, or whenever asked "is the demo working?" / "are we demo-ready?".
---

# Demo Check

Verifies the OpAssure demo path described in `CLAUDE.md` §7 is currently
reproducible. Refer to `CLAUDE.md` for the demo story, priority levels, and
demo identifiers — this skill only checks that they currently work.

## Steps

Run each check in order. Stop noting granular sub-steps once a whole area fails —
just record the failure and move to the next area so the report is complete.

1. **Services start**
   - `docker compose up -d` succeeds (or is already running).
   - Backend process starts without error (`uvicorn app.main:app`).
   - Frontend dev server starts without error (`npm run dev` in `frontend/`).

2. **Database reachable**
   - Can connect to PostgreSQL using `DATABASE_URL` from `.env`.
   - Expected core tables exist (operators, machines, weather, tasks, telemetry,
     worker_positions, incidents, near_misses, ground_truth_labels,
     training_events).

3. **Synthetic data exists**
   - `data/synthetic/` is non-empty.
   - Row counts roughly match the expected scale (20 operators, 8 machines, 60
     days) — if wildly off, flag it (delegate deep validation to
     `/data-validation`).

4. **Demo identifiers exist**
   - Operator `OP1001` exists.
   - Machine `EXC001` exists.
   - Task `T001` exists and references OP1001 and EXC001.

5. **APIs work**
   - Health endpoint responds (`GET /health`).
   - Core endpoints used by the demo story respond with 2xx and shapes matching
     `docs/api/`.

6. **ML artifacts load**
   - Any trained model artifacts referenced by the backend load without error.
   - If a model artifact is missing, note it — do not silently fall back without
     reporting it.

7. **WebSocket works**
   - Can open a WebSocket connection to the backend.
   - A telemetry replay event round-trips as expected.

8. **Frontend loads**
   - The app loads in a browser without console errors.
   - Mission Board renders and Task T001 is selectable.

9. **Telemetry replay works**
   - Replaying the demo scenario produces live telemetry updates visible in the
     backend logs or WebSocket stream.

10. **Safety event works**
    - A seatbelt or proximity event in the replay triggers the expected alert.

11. **ETA works**
    - ETA is computed and displayed for Task T001, and updates when conditions
      change during replay.

## Report format

End with a summary in this exact form:

```
DEMO CHECK: PASS
```

or

```
DEMO CHECK: FAIL
Failed:
- <area>: <specific reason>
- <area>: <specific reason>
```

Be specific about what failed (which endpoint, which table, which ID) — "APIs
broken" is not acceptable, "GET /api/tasks/T001 returned 404" is.

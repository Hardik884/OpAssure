---
name: integration-check
description: Check frontend/backend/ML integration contracts in OpAssure — API shapes, WebSocket events, ML input/output payloads, field names, demo identifiers, CORS and environment configuration. Use before merging a change that touches an API, WebSocket message, or ML interface, or when frontend/backend/ML seem out of sync.
---

# Integration Check

Checks the contract boundaries described in `CLAUDE.md` §10 (Integration Rules)
are actually consistent across `frontend/`, `backend/`, and `ml/`.

## Steps

1. **API shapes**
   - For each REST endpoint the frontend calls, confirm the backend's actual
     response shape matches what the frontend expects (field names, types,
     nullability) — compare frontend `src/types/` (or equivalent) against backend
     `app/schemas/`.
   - Confirm shapes match what's documented in `docs/api/`; if the code and docs
     disagree, say which one looks authoritative and flag the mismatch rather than
     silently trusting one.

2. **WebSocket events**
   - Confirm every WebSocket message `type` the backend emits has a
     corresponding handler on the frontend, and vice versa (no frontend handler
     listening for a type the backend never sends).
   - Confirm payload shapes match on both ends.

3. **ML input/output payloads**
   - Confirm the fields the backend sends into ML services match what the ML
     code expects (names, units, types — e.g. minutes vs seconds).
   - Confirm ML output fields match what the backend expects to receive and pass
     to the frontend.

4. **Field-name consistency**
   - Cross-check field names against the data model in `CLAUDE.md` §6. Flag any
     silent rename at a layer boundary (e.g. `estimated_time_min` becoming
     `etaMinutes` without a documented mapping).

5. **Demo identifiers**
   - Confirm `OP1001`, `EXC001`, `T001` resolve correctly through every layer
     touched by the change (DB → backend API → frontend render).

6. **CORS / local URLs / environment configuration**
   - Confirm frontend API/WebSocket URLs come from `.env`
     (`NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_WS_URL`) and not hardcoded values.
   - Confirm backend CORS config allows the frontend's local origin.
   - Confirm nothing depends on a `.env` value that isn't documented in
     `.env.example`.

## Output

Report incompatibilities as a specific, actionable list: which layer, which
field/endpoint/event, expected vs actual. Group by severity — a contract break
that would crash the demo path (see `CLAUDE.md` §7) is higher priority than an
unused/dead field mismatch. Do not fix the mismatches automatically — report them
unless explicitly asked to fix.

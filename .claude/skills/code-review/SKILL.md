---
name: code-review
description: Review the current OpAssure diff for bugs, broken contracts, unnecessary complexity, security problems, missing tests, hardcoded secrets, hackathon-risky changes, and regressions to the five mandatory outcomes. Use before committing or opening a pull request.
---

# Code Review

Reviews the current diff against the engineering rules and mandatory outcomes in
`CLAUDE.md` (§2, §9, §14). This is a review skill — report findings, don't
auto-rewrite the code unless explicitly asked to apply fixes.

## What to check

1. **Bugs** — logic errors, off-by-one, incorrect null/undefined handling, race
   conditions in WebSocket/async code, incorrect unit conversions (minutes vs
   seconds, m³ vs L, etc.).

2. **Broken contracts** — does this diff change an API shape, WebSocket event, or
   ML payload that another layer depends on? If so, is the other layer updated to
   match, or is this now a job for `/integration-check`?

3. **Unnecessary complexity** — new abstraction layers, config systems, or
   generalized solutions for a problem that only has one caller. Per `CLAUDE.md`
   §14, prefer the simple version during the hackathon window.

4. **Security problems** — injection risks (raw SQL string interpolation instead
   of parameterized queries), unsafe deserialization, missing auth checks on an
   endpoint that should have one, unsafe use of eval/exec-like constructs.

5. **Missing tests** — does this diff touch logic that drives a mandatory outcome
   (ETA calc, safety rules, seatbelt/proximity detection) without a corresponding
   test? Flag it; don't necessarily block on it unless it's core-path logic.

6. **Hardcoded secrets** — API keys, passwords, tokens, connection strings with
   credentials embedded. Check `.env`-shaped values weren't pasted directly into
   source. Confirm `.env` itself isn't part of the diff.

7. **Hackathon-risky changes** — anything that could break the demo path
   (`CLAUDE.md` §7) or a Level 1 feature (`CLAUDE.md` §8) for the sake of a Level
   2/3 feature. Anything that makes the project harder to run locally
   (`CLAUDE.md` §9).

8. **Regressions to mandatory outcomes** — re-check the five outcomes in
   `CLAUDE.md` §2 are all still intact after this diff, not just the area the
   diff directly touches.

## Output

List findings ranked most-severe first. For each: what's wrong, where (file/line
if available), and the concrete failure scenario (not just "this could be
better"). If nothing significant is found, say so plainly — don't invent
findings to seem thorough. Do not rewrite the code as part of this skill unless
explicitly asked to apply the fixes.

---
name: feature-priority
description: Classify a proposed OpAssure feature as Level 1 (must work), Level 2 (important), or Level 3 (optional/last) per the project priority system. Use whenever asked "should we build X?", "is this worth doing?", or before starting any feature not already on the priority lists in CLAUDE.md.
---

# Feature Priority

Classifies a proposed feature against the priority system in `CLAUDE.md` §8, so
the team doesn't spend hackathon time on low-value work before the core demo
works.

## Steps

1. **Check if it's already classified.** Compare the proposed feature against the
   Level 1/2/3 lists in `CLAUDE.md` §8 and the feature mapping in §2. If it's
   already named there, just state its level and move on.

2. **If it's new, classify it by asking:**
   - Does the demo story in `CLAUDE.md` §7 break without it? → **Level 1.**
   - Does it directly implement one of the five mandatory outcomes (§2) in a way
     not yet covered? → **Level 1**, unless a simpler Level-1 version already
     satisfies the outcome — in that case this is an enhancement, likely
     **Level 2**.
   - Does it materially strengthen the Operator Twin, ETA accuracy, or
     safety/anomaly detection in a way the demo story showcases? → **Level 2.**
   - Is it polish, a nice-to-have visualization, or something outside the five
     mandatory outcomes entirely? → **Level 3.**

3. **Flag conflicts explicitly.** If the feature would require reworking Level 1
   code to build, say so — per `CLAUDE.md` §14, that's usually a sign to defer it
   regardless of how good the idea is.

4. **State the tradeoff, not just the label.** Say what would need to be
   deprioritized or delayed if the team builds this now, given current known
   progress (ask, or check recent commits/`docs/` if unsure what's already done).

## Output

Respond concisely:

```
LEVEL: <1|2|3>
Why: <one or two sentences>
Tradeoff: <what this costs if built now, or "none — fits current priorities">
```

Do not start implementing the feature as part of this skill — classification
only, unless the user explicitly asks you to proceed after seeing the
classification.

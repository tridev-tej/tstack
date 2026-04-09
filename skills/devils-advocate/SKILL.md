---
name: devils-advocate
description: Adversarial argument loop - steelman then demolish any piece of writing until it's bulletproof. Argue for, argue against, synthesize. Repeat until no new weaknesses found.
trigger: when user says "/devils-advocate", "argue against this", "steelman", "demolish my argument", "stress test this writing", "make this bulletproof"
---

# Devil's Advocate Loop

Iterative adversarial refinement for any piece of writing - blog posts, essays, arguments, proposals.

## How it works

You run 3 parallel agents per round, then synthesize. Loop until convergence (no new substantive weaknesses found).

## Procedure

### Input

The user provides either:
- A file path to the writing
- The writing inline in their message
- A reference to something already in context

Save the current draft to `/tmp/devils-advocate-draft.md` at the start. All rounds read from and write to this file.

### Each Round

Spawn 3 agents in parallel:

**Agent 1: Steelman** (subagent_type: general-purpose)
- Read the draft
- Make the STRONGEST possible case for every claim
- Find where the argument is already strong and why
- Identify which points would convince a skeptic
- Output: bullet list of strengths + suggestions to make strong points even stronger

**Agent 2: Demolisher** (subagent_type: general-purpose)
- Read the draft
- DESTROY every argument. Argue the opposite is true.
- Find logical gaps, unsupported claims, cherry-picked evidence
- Find where the author is being sycophantic to their sources (just agreeing with the talk without questioning)
- Find where the writing assumes its conclusion
- Be ruthless. No mercy. The goal is to find every weakness.
- Output: numbered list of weaknesses with severity (critical/major/minor)

**Agent 3: Reader** (subagent_type: general-purpose)
- Read the draft as a first-time reader with no context
- Where do you get bored? Where are you confused?
- What's missing that you expected to find?
- What feels like filler vs what feels like insight?
- Where does the author lose their own voice and start sounding generic?
- Output: section-by-section reader experience notes

### Synthesis

After all 3 agents return:

1. Read all three reports
2. Categorize findings:
   - **Must fix**: critical weaknesses from Demolisher that the Steelman couldn't defend
   - **Should fix**: major weaknesses + reader confusion points
   - **Consider**: minor issues, style suggestions
3. For each "must fix" and "should fix" - determine the right fix:
   - Sometimes it means strengthening the argument
   - Sometimes it means ACKNOWLEDGING the counterargument (the strongest writing doesn't hide weaknesses, it addresses them)
   - Sometimes it means cutting a section that can't be defended
   - Sometimes it means adding a "to be fair" or "the counterargument is..." section
4. Rewrite the draft incorporating fixes
5. Save updated draft to `/tmp/devils-advocate-draft.md`
6. Print a round summary:

```
=== ROUND N ===
Critical issues found: X
Major issues found: X
Minor issues found: X
Issues fixed: X
Remaining: X
```

### Convergence Check

After each round, evaluate:
- Did the Demolisher find any NEW critical or major issues not found in previous rounds?
- If yes: run another round
- If no: the draft is converged. Done.

Max 4 rounds to prevent infinite loops. If still finding critical issues after 4 rounds, present the remaining issues to the user and let them decide.

### Output

When converged, present:
1. The final improved draft
2. A changelog of what changed from original to final
3. Any remaining minor issues the user might want to address manually

## Key Principles

- The Demolisher must NOT be sycophantic. It must genuinely try to destroy the argument. Prompt it to imagine it's a smart contrarian who thinks the author is wrong.
- The Steelman must NOT be defensive. It should honestly assess which parts hold up and which don't.
- The Reader must NOT be an expert. It should read as someone encountering these ideas fresh.
- Fixes should make the writing MORE honest, not just more persuasive. The best writing acknowledges its own limits.
- Preserve the author's voice. Fixes should sound like the same person wrote them.
- Do NOT add hedging everywhere. Confidence is fine when earned. Only hedge where the Demolisher found a genuine weakness.

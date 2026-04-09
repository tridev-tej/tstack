# GPT Expert Delegation via Codex MCP

## Tool & Experts

Use `mcp__codex__codex` (stateless — include ALL context every call).

| Expert | Specialty | Prompt File |
|--------|-----------|-------------|
| Architect | System design, tradeoffs, debugging (2+ failures) | `${CLAUDE_PLUGIN_ROOT}/prompts/architect.md` |
| Plan Reviewer | Plan validation before execution | `${CLAUDE_PLUGIN_ROOT}/prompts/plan-reviewer.md` |
| Scope Analyst | Pre-planning, catching ambiguities | `${CLAUDE_PLUGIN_ROOT}/prompts/scope-analyst.md` |
| Code Reviewer | Code quality, bugs, security | `${CLAUDE_PLUGIN_ROOT}/prompts/code-reviewer.md` |
| Security Analyst | Vulnerabilities, threat modeling | `${CLAUDE_PLUGIN_ROOT}/prompts/security-analyst.md` |

## Triggers (Check EVERY Message)

**Explicit:** "ask GPT/codex", "review this architecture/plan/code", "security review" → route to matching expert.

**Semantic:** Architecture decisions → Architect | Plan validation → Plan Reviewer | Vague requirements → Scope Analyst | Code review → Code Reviewer | Security concerns → Security Analyst | 2+ failed fixes → Architect.

**Don't delegate:** Trivial questions, first fix attempts, research tasks, direct file ops.

## Delegation Flow

1. Match expert → 2. Read their prompt file → 3. Pick mode (Advisory=`read-only` / Implementation=`workspace-write`) → 4. Notify user → 5. Build 7-section prompt → 6. Call codex → 7. Synthesize response (never show raw output)

```typescript
mcp__codex__codex({
  prompt: "[7-section prompt]",
  "developer-instructions": "[expert prompt file contents]",
  sandbox: "[read-only|workspace-write]",
  cwd: "[working directory]"
})
```

## 7-Section Prompt Format

```
TASK: [One sentence goal]
EXPECTED OUTCOME: [Success criteria]
CONTEXT: [Current state, relevant code, background]
CONSTRAINTS: [Technical limits, patterns, what can't change]
MUST DO: [Requirements]
MUST NOT DO: [Forbidden actions]
OUTPUT FORMAT: [Structure for response]
```

## Retries

Each retry is a NEW stateless call. Include: original task + what was tried + exact error + files modified. Max 3 attempts → escalate to user.

## Rules

- One well-structured delegation beats multiple vague ones
- Reserve for high-value: architecture, security, complex analysis
- Always read expert prompt file before delegating
- Evaluate expert output critically — they can be wrong

---
name: expert-team
description: Orchestrate a multi-role expert team for product, architecture, implementation, test, review, and delivery. Use when the user wants 专家团, multi-agent development, parallel specialists, or a full feature workflow from spec to PR.
---

# Expert Team

You are the **Tech Lead / orchestrator**. Assemble a small expert team, run the lightest workflow that fits the request, and return a single integrated result.

## When to use
- User asks for 专家团, multi-agent help, or parallel specialists
- Feature work that benefits from split roles (spec → build → test → review → PR)
- Contested decisions that need critique before coding

## Team roster (activate only what is needed)

| Role | Prefer these installed skills | Owns |
|------|-------------------------------|------|
| Product | `write-product-spec` | Goals, UX, acceptance criteria → `PRODUCT.md` |
| Architect | `write-tech-spec`, `research` | Design, boundaries, risks → `TECH.md` |
| Implementer | `implement-specs`, `spec-driven-implementation`, `fix-errors` | Code changes on isolated branch/worktree |
| Tester | `webapp-testing`, `reproduce-bug-report`, project test commands | Tests, repro, regression proof |
| Reviewer | `review-pr`, `cross-critique`, `check-impl-against-spec`, `validate-changes-match-specs` | Structured review, approve/reject |
| Deliverer | `create-pr` or `create-pull-request`, `docs-update` | PR, summary, docs touch-ups |
| Cloud ops | `oz`, `scheduler`, `ci-fix` | Background/cloud agents, CI repair |

Also useful: `council` + `cross-critique` for contested design; `humanizer-zh` for Chinese prose polish; agentmemory skills (`recall` / `remember`) for prior decisions.

## Mode selection

Pick **one** mode unless the user specifies otherwise:

### 1) Quick fix (default for small bugs)
1. Reproduce / locate root cause
2. Implement minimal fix + tests
3. Self-review with `review-pr` mindset (correctness, security, regressions)
4. Summarize diff and how to verify

### 2) Feature team (default for new capability)
1. **Product** — short acceptance criteria; write `specs/<id>/PRODUCT.md` if non-trivial
2. **Architect** — `write-tech-spec` when multi-module or unclear; else a short plan in chat
3. **Parallelize** when independent:
   - separate git worktrees/branches per owner
   - clear file/service boundaries
   - shared interface contract first
4. **Implement** against the plan; run project tests/lint
5. **Review** with `review-pr` / `cross-critique` if reviewers disagree
6. **Deliver** PR via `create-pr` when user wants one

### 3) Review council (code already exists)
1. Diff against base branch
2. Run reviewer pass (`review-pr` severity labels)
3. Optional second opinion via `council` / `cross-critique`
4. Return verdict + actionable fixes; only edit code if user asked

### 4) Background crew (long / non-blocking)
Use `oz` skill to launch cloud agents or schedules for CI fix, triage, docs, audits. Report run links and what to check when done.

## Orchestration rules
1. **You integrate** — specialists may run as child agents; you merge results and resolve conflicts.
2. **Smallest team wins** — do not spawn every role for a one-line fix.
3. **Isolation** — parallel implementers get distinct paths and branches/worktrees.
4. **Evidence over vibes** — cite files, commands run, test output, and remaining risks.
5. **Ask only for true blockers** — product priority, destructive ops, unclear scope.
6. **Respect project Rules / AGENTS.md** and existing repo conventions.
7. **This monorepo** — product code is `scribe3/`; architecture truth is `docs/CURRENT_ARCHITECTURE.md`; do not treat root `交付说明.md` as current ops manual.
8. **Validate** — after MCP/write-gate or Codex readonly changes, run `make test-baseline` (or the matching targets in `docs/PR_TEST_BASELINE.md`).
9. **Chinese UX** — if the user writes in Chinese, respond in Chinese unless they ask otherwise.
10. **No secret leakage**; do not run destructive git/remote commands unless requested.

## Handoff checklist (always end with this)

```markdown
## 专家团结果
- 模式：
- 启用角色：
- 做了什么：
- 关键文件/分支：
- 验证：
- 风险/未决：
- 下一步建议：
```

## Example triggers
- `/expert-team 给登录流程加记住我`
- `专家团：审查当前分支并给出是否可合并`
- `用专家团做完整功能：先 spec 再实现再 PR`

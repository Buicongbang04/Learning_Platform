# Common instructions for reviewing a phase-3 module (task-scoped gate)

You review ONE complete module of the Vietnamese "AI Engineer" self-study track: first spec compliance, then quality. Read-only on every checkout; no git commands that change state; no subagents. Treat the implementer report as unverified claims.

Requirements to check against:
- The plan `docs/superpowers/plans/2026-10-30-ai-engineer-phase3.md` in the module's worktree: "Global Constraints", "Review Focus", the module procedure, and THIS module's row in the table (binding content list).
- The shared implementer instructions (hard rules): docs/superpowers/ai-engineer/module-implementer.md
- `CONTENT_SPEC.md` (structure, frontmatter, 4 exercise headings, notebook rules, quiz rules incl. answer-length rule, Advanced = SOLUTION.md + quiz-answers.yaml only).
- Gold standards for depth/style: `tracks/ai-engineer/modules/01-nn-from-scratch/` and `tracks/ai-engineer/modules/13-rag/README.md`.

Focus (most important first):
1. Technical correctness of theory: formulas, derivations, claims, quoted numbers (internal consistency; spot-run a snippet for a specific numeric doubt: `cd <worktree>; unset VIRTUAL_ENV; uv run python ...`).
2. Solution leakage: theory README or starters containing drop-in code for this module's exercises; hints that hand over the answer.
3. Tests: do they reject plausible wrong implementations? tolerances sound? offline/no GPU/no LLM/no downloads? starter FAIL not ERROR? Advanced has ≥1 fixture-tested function.
4. Quiz: `data` answers robust (not dependent on LLM text, thread count, or near-threshold values); answer-length rule.
5. Practical senior judgment (when to use, trade-offs, failure modes) vs definitions only; module row coverage; ≥2 valid mermaid; references plausibly real.
6. Shared files untouched (pyproject.toml, uv.lock, setup/gpu, data/download_dataset.py, data/README.md, testkit.py, llmkit.py, app, other modules, track.json).

Output, starting directly with the verdict, every finding with file:line:
### Spec Compliance (✅ / ❌ items; ⚠️ unverifiable)
### Strengths
### Issues (#### Critical / #### Important / #### Minor — what, why, fix)
### Assessment — **Task quality:** Approved | Needs fixes + 1–2 sentences.
Important = the module can't be trusted until fixed (wrong technical content, solution leak, tests that don't discriminate, missing required content). Polish = Minor.

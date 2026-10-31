# Common instructions for every phase-3 module task (read fully)

You are writing one complete learning module of the Vietnamese "AI Engineer" self-study track. The learner wants to become a senior ("lão luyện") AI Engineer who understands models from the inside and ships real products.

## Read first
1. The shared module procedure + plan Global Constraints + Review Focus: `docs/superpowers/plans/2026-10-30-ai-engineer-phase3.md` (sections "Global Constraints", "Review Focus", "Task 1–21: Mỗi module một task" incl. the procedure Steps 1–5 and YOUR module's row in the table). Your module row is binding.
2. `CONTENT_SPEC.md` (structure, frontmatter, 4 exercise headings, notebook rules, quiz.yaml + quiz-answers.yaml, answer-length rule, LaTeX `$$`).
3. Gold-standard modules — match their depth, voice, exercise design, SOLUTION.md, quiz, tests: part A `tracks/ai-engineer/modules/01-nn-from-scratch/`, part B `tracks/ai-engineer/modules/13-rag/` (theory + interview only in your branch). Also `tracks/ai-engineer/track.json` (your module's summary/topics), `tracks/ai-engineer/README.md`.
4. `testkit.py` (`ex.module`, `ex.notebook`, `ex.dataset`), `llmkit.py` (`chat`, `embed`, `FakeLLM`, `use`), `data/README.md` (provisioned datasets + libraries for phase 3 — use them; registry names via `ex.dataset("<name>")` / `ensure("<name>")`).

## Hard rules (lessons from the sample modules' reviews)
- Theory README and starters must NOT contain code that solves this module's exercises. Explain with formulas, diagrams, measured results, small illustrative snippets that are not drop-in solutions.
- Every number in theory, quiz `data` answers and test thresholds comes from your actual runs with pinned seeds. Quiz answers that depend on LLM-generated text or BLAS thread count must be robust (ranges/qualitative) or `knowledge`.
- `**Phần cứng:** <CPU | GPU 4GB | GPU 12GB (PC)> · ~<N> phút` is the first line of `## Đề bài`; N = learner WORKING time; mention run time separately.
- Tests: offline, no GPU (pass with `CUDA_VISIBLE_DEVICES=""`), no real LLM, no model downloads, < 30 s each, discriminate plausible wrong implementations (try mutants). Starter: FAIL/SKIP, never ERROR. `SOLUTION=1`: Basic/Intermediate PASS. Advanced: only SOLUTION.md (approach + scored rubric) + quiz-answers.yaml in solutions/, ≥1 function tested on a fixture; verify Advanced with a reference implementation kept outside the repo in `<your worktree>/.superpowers/scratch/` (gitignored).
- Notebooks: first cell may set `os.environ.setdefault("OMP_NUM_THREADS", "4")` before numpy/torch; graded cells only def/class/imports/env config; `explore`-tagged cells start with `# explore: ...`; commit without outputs; every solution notebook must run with `uv run jupyter nbconvert --to notebook --execute --stdout <nb> > /dev/null`.
- Hardware is SHARED with the other module agent running in parallel (at most 2 module agents at a time: one GPU, one Ollama server). On the PC (RTX 3060 12GB, 128GB RAM) you may use up to ~5 GB VRAM while another agent runs; set OMP_NUM_THREADS to roughly half the cores; retry if CUDA OOM due to the other agent. Never kill other processes. Learner-facing Basic/Intermediate must still run on a 4GB laptop GPU / CPU (state the laptop fallback); 12GB-only work goes in Advanced or ungraded "mở rộng" cells, and numbers measured on the 12GB PC must say so.
- Do NOT modify shared files: `pyproject.toml`, `uv.lock`, `setup/gpu/*`, `data/download_dataset.py`, `data/README.md`, `testkit.py`, `llmkit.py`, app, other modules, track.json. If you truly need a missing dependency/dataset, stop and report NEEDS_CONTEXT with exactly what and why.
- If something only the learner can provide is needed (PC access, API key, registration), use the laptop-scale fallback and say so in the report.
- Vietnamese prose with English technical terms; LaTeX `$$`; valid mermaid (≥2 per README).
- `data/raw` is a shared symlink: never delete/modify existing data; never git add it. Stage by path only; commit messages Vietnamese, NO Co-Authored-By. Commit in a few logical commits (theory+interview; exercises), ending with the module commit per the plan.
- Final checks: `uv run pytest tracks/ai-engineer/modules/<id> -q` (FAIL/SKIP only, 0 errors), `SOLUTION=1 uv run pytest tracks/ai-engineer/modules/<id> -q` (PASS/advanced SKIP), nbconvert all solution notebooks, `UV_NO_SYNC=1 uv run pytest tests/test_quiz_files.py -q`, `cd app && pnpm install --frozen-lockfile && pnpm build`.
- `unset VIRTUAL_ENV` before uv commands. Work only inside your worktree. Do not dispatch subagents. Escalate with BLOCKED/NEEDS_CONTEXT if stuck.

## Report
Write the full report to the report path given in your dispatch: what you built (sections, exercises with slugs/levels/hardware), measured numbers and their sources, test outputs (starter, SOLUTION=1), nbconvert results, quiz test, app build, Advanced reference results, deviations from the module row and why, files, self-review, concerns.
Reply with ONLY (under 15 lines): Status (DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT), commits (short SHA + subject), one-line test summary, concerns, report path.

# Guide for FDE module tasks (dùng cho mọi phase) — read after the brief

Track: Forward Deployed Engineer (`tracks/fde`), Vietnamese text with English technical terms. Learner is a DA/DS moving toward engineering, has done (or is doing) the DE, DA, DS, AI Engineer, MLOps, DevOps tracks in this repo. Senior-level goal: practical field decisions, trade-offs, common failures — not definitions.

Read before writing:
- CONTENT_SPEC.md: the whole file, especially exercise layout/frontmatter (`files`, `run`, `level`), exactly 4 `## ` headings in exercise READMEs (Mục tiêu / Đề bài / Tiêu chí đạt / Gợi ý), quiz.yaml format (quote every `text` value), solutions tree mirrors exercises, `SOLUTION.md` at every level, and the `## Track FDE` section at the end (helpers, VM budget, rules).
- tests/test_fde_track.py — the validator your module must pass.
- Sibling examples for tone/structure: tracks/mlops/modules/01-engineering-foundations/ (README, interview.md, an exercise with starter/tests/solution). Look at one exercise's conftest/tests to see how `testkit.Exercise` and SOLUTION=1 switching work.
- fdekit.py public API + setup/fde/README.md (profiles, quirks "Tật của khách", golden prep) + setup/fde/profiles/*.yaml (facts). Product: tracks/fde/product/README.md, REQUIREMENTS.yaml, release.py.

Rules (from the plan's Global Constraints — all binding):
- Every VM install/deploy exercise has ≥1 real breakage caused by the customer profile (proxy, untrusted CA, egress none, small disk, no sudo, SELinux, missing compose plugin, HTTP registry not in insecure-registries…), not a bug planted in code. README describes context + symptom only; cause only in solutions/; starter names don't hint the cause.
- Tests: only via fdekit (`customer_site`, `vm`, `VM.ssh/put/get/port`) or testkit.DockerLab / run_sandboxed — never bare `docker`/`qemu-system`. Skip cleanly (with the command to fix) when KVM/golden/image/data is missing. Each exercise ≤300 s incl. boot; ≤2 VMs; VM RAM budget (aux ≤2048, product ≤5120, total ≤8192).
- Starter: tests FAIL or SKIP, never ERROR. SOLUTION=1: PASS, no skips on this machine (goldens prepared, data downloaded).
- Every rule a test grades must be stated in the exercise README.
- Repeated knowledge from other tracks: at most one `## ` per module, linking the source module (paths under tracks/devops, tracks/ai-engineer, tracks/mlops, tracks/data-engineer — link to existing files only).
- Module README: first line `# Title`, 5–8 `## ` sections (not counting `## 0. Cài đặt`), ≥2 mermaid blocks, last `## N. Tài liệu tham khảo` with real links (official docs, roadmap.sh FDE page). interview.md ≥12 `## ` questions incl. field scenarios ("khách nói X, bạn làm gì") with model answers.
- ~7 exercises (3 basic, 2–3 intermediate, 2 advanced); module 00 may have 4–6. Advanced: README + SOLUTION.md (approach + rubric), no tests required.
- Code: Python 3.12 / POSIX sh as specified; no inline comments; docstrings only if needed. Commit without Co-Authored-By.
- Heavy runs with `nice -n 15`; other agents share the machine; after verification `uv run python -m fdekit leftovers` must print nothing left.

Lessons from module 00 review (apply):
- Reference solutions (SOLUTION.md samples) must obey every constraint of their own exercise and score full marks on their own rubric — reviewers check this.
- Judgement fields (who decides, what it looks like, severity…) are graded against per-item ACCEPTED SETS of every defensible answer, with definitions/mapping in the README and reasoning in SOLUTION.md; a correct learner must never fail.
- Hints must not give away the answer; avoid exercises solvable by keyword matching.
- Tests that run learner scripts over SSH must fail with a clear message on timeout, and should defeat hardcoded output (e.g. vary the environment between two runs, compare to ground truth measured in the same VM).
- Learner-visible files (theory README, interview.md, exercise READMEs, hints, starters) must not reveal the specific causes of field exercises — keep interview answers generic (method, not this exercise's causes).
- Anything that collects data from a customer machine (survey, support bundle, logs) must never carry secrets: strip URL userinfo, mask password=/token= values, no env dumps/shell history/business data — teach it and grade it with a random planted secret.
- Reference installers/scripts are teaching artifacts: trace every failure path (first install, upgrade, same-version re-run, partial state) and make the end state match what the README claims; never exit via `set -e` after a state change without rollback/logging.

# FDE Phase 1 — việc để sau (follow-ups)

Các phát hiện mức Minor được review đánh giá là không chặn merge, giữ lại để xử lý ở Phase 2+. Nguồn: ledger SDD của plan docs/superpowers/plans/2026-11-03-fde-phase1.md.

- Task 1: minor (deferred): no host-key pinning for lab SSH (single-user laptop threat model); dated image URLs will rot — consider fallback mirror URLs; -pidfile unused; Task 2 must wire profile→restrict.
- Task 1: minor (deferred): forked (non-exec) children inherit lifeline write end; stale fds after fork; redundant sleep(3) in worker-thread test; guard SIGKILL leaves run dir until clean().
- Task 1: minor (deferred): `except RuntimeError` in _ubuntu() broad; no tests for log truncation/QMP ValueError/exit code mapping.
- Task 2: minor (deferred→carried into Task 3): guard halt branch should delete qemu.start; purge() should kill run's guestfwd relays; move _GUARDS run-id check above prereqs in vm().
- Task 2: minor (deferred): SIGTERM handler reentrancy (Popen waitpid lock) bounded by SIGKILL escalation; empty run dir if SIGKILL between _new_run_dir and _spawn_guard; prepare pulls images every time, failed pull exit 0; cloud-init degraded rc 2 treated as failure.
- Task 3: minor (deferred): CUAD zip has no checksum verification (Dataset has no sha field; consumers in Task 4/11 could verify Zenodo md5).
- Task 4: minor (deferred): iterdir OSError wipes retries/stuck (idempotent re-embed); dead 22/23 prefixes in OperationalError branch; README limitation should mention 57014/53200 also hold queue; ProgrammingError 42P01 (missing schema) sends every file to failed/ — worker should check schema at startup.
- Task 5: minor (deferred→Task 6): CONTENT_SPEC FDE section must state milestones attach to main modules only; trackStats not directly unit-tested.
- Task 7: minor (deferred): first-week plan Monday row "kiểm bundle theo manifest" add "trên máy bạn"; why-justification only length-checked; mermaid flowcharts need visual check in app (Task 12).
- Task 8: minor (deferred): basic SOLUTION.md cpus row omits getconf fallback; proxy strip can't handle unencoded '/' in password (invalid URL anyway — document); support bundle env.txt redaction not graded.
- Task 9: minor (deferred): rollback path "previous dir deleted by hand" leaves failed B unit/current (could restore unit backup); same-version re-run with changed manifest overwrites release; health() InvalidURL traceback (catch http.client.InvalidURL); restore_same doesn't wait for health.
- Task 10: minor (deferred): adv-02 SOLUTION.md:11 still mentions intermediate 01; int-02 install.sh restart failure doesn't auto-restore daemon.json; publish.sh restore cp not atomic; old-layout hosts would see site files as "thừa".
- Task 11: review Approved. minor (deferred→final fix wave): m00 /DataScience substring false positive; m03 untouched-machine check lacks filesystem snapshot (/opt,/etc); reference verify.sh accepts Restarting containers; per-test worst-case > 300 s (shrink 2nd install timeout); fdekit leftovers should list /var/tmp/fde-capstone-*; README license line for docker compose (Apache-2.0); m03 doc example path unify; note host git outside sandbox in CONTENT_SPEC; comment for /tmp visibility in test_m00_layout; spec §7 "lab in private repo" vs brief (fdekit stays in learning repo) — update spec.
- Task 12: final fix wave re-review APPROVE (12 addressed). minor (follow-up): infra steps outside Budget; verify.sh set -u on failed inspect; legacy pid-less tmp dirs manual rm; host_online uses host proxy env; module 03 fde-usb-* leak not in leftovers.

# W1–W4 本機交付與驗證紀錄

日期：2026-10-08。Base `c9f109b`，branch `codex/android-workflow-registry`；功能提交4630057、717b05d、d5482e6、38bb375，審查修正f4e76a3。本機交付完成，尚未合併main或推送。

交付：固定ref登錄、自有0.1.0文件包／0.2.0技能包與immutable hash lock、Android/私有company profiles、TaskContract與ready-set、八個待binding任務、JUnit runner／evidence／comparison、公開指南／流程圖／下载与採納scope。

雲端設定時序見 [cloud-account-timing](cloud-account-timing.md)，實測綁定與封存見 [evaluation-runbook](evaluation-runbook.md)。尚無Android測試repo；candidate保持候選，不能據此聲稱效率／品質提升。沒有付費呼叫、帳號設定、shared push或公開部署。

一次Sol6.1新上下文整體審查找出四項Important；下面記錄作者各項RED→GREEN與整體測試，不是reviewer二次核准。固定hash：0.1.0 `4f2322e9be952869f21cf87951fe91cd62eb9650eef9eafcbfb522d9ee8467c7`；0.2.0 `ed9649b990da98b2f425806806ab00a12040405973ff83eaf62bdde80ebeb230`。

## 任務、裁定與驗證原始紀錄

# SDD ledger — plan: docs/superpowers/plans/2026-10-08-android-workflow-registry.md
Base: c9f109b; clean existing managed worktree reused; baseline 103/103.
Pre-flight W1→W2: initial bundle references only files already supplied; skill belongs to next task.
Pre-flight W2→W3: immutable task head/spec/base binding; evidence never unlocks an unintegrated dependency.
Pre-flight W1/W3→W4→K4: only approved public own files; catalog adoption distinct from content publication review.
Ruling: A/W task IDs use manual ledger as prior runs — cost manual bookkeeping.
Ruling: W1 produces immutable0.1.0 document bundle; W2 adds skill in0.2.0 instead of referencing missing future files — cost two retained versions.
Ruling: Link to pinned MIT upstream, embed only owned adapter — avoids full upstream/cache redistribution; cost separate installation.

W1: RED missing module; GREEN full suite110; commit4630057.
Skill baseline: safety gates respected, but invented C→B dependency and omitted attempt/budget/checkpoint slots; skill adds declared-edge rule and explicit handoff fields.

Task W1: complete (c9f109b..4630057, pytest110/110).
Task W2: complete (4630057..717b05d, pytest119/119).
Skill forward-test: declared dependencies preserved, blocked handoff includes checkpoint/remaining budgets; ambiguity on attempt/deadline semantics repaired in reference. Skill validator pass; synthetic read/behavior only.
Task W3: complete (717b05d..d5482e6, pytest129/129; fresh/stale JUnit actual local process fixture).
Ruling: No target Android repo supplied; deliver eight pending bindings and private runner observations, real effectiveness evaluation remains blocked — cost if wrong: cannot justify company adoption yet.
Ruling: Maestro has no supplied compatible report; standard JUnit or explicit manual acceptance only — cost if wrong: extra report binding/reviewer work.
Ruling: Historical package manifest remains immutable; adoption overlays validated separately — cost if wrong: users must consult catalog for latest status.
Ruling: Use Sol6.1 final reviewer per user model preference — cost if wrong: reviewer judgment may differ from another model.
Task W4: pytest135/135; Astro check zeroerrors/zerowarnings/10 existing hints; root/subpath build10 pages and browser5/5 each.

Task W4: complete (d5482e6..38bb375, pytest135/135; browser root5/5 and subpath5/5).
Live restore:145 release events; public dist excludes private sentinels and company profile path; no paid calls.

Final review: Sol6.1 fresh-context, range c9f109b..38bb375; four Important, no Critical or Minor. Reviewer independently ran31 targeted tests; initial verdict No. One author fix pass, no re-review.
Final: fixed artifact presence/hash/report observations — test_real_evidence_requires_existing_matching_report RED→GREEN, suite136/136.
Final: fixed fresh export regenerating historical packages — test_historical_package_cannot_change_on_fresh_export RED→GREEN, suite137/137; committed release ZIP hash locks; prior export survives rejection.
Final: fixed reference-style missing/private links — test_reference_definition_must_be_in_public_bundle RED→GREEN, suite139/139.
Final: fixed lost subset adoption scope — test_catalog_retains_subset_adoption_scope RED→GREEN, suite140/140; supported and adopted profiles displayed separately.
Final: Ruling: Actual Android quality/efficiency — no target repo, effectiveness stays blocked and candidate — cost if wrong: real project outcomes remain unknown.
Final: Ruling: Native non-JUnit Maestro parsing — accept verified compatible JUnit or explicit manual observations and saved artifacts — cost if wrong: custom format integration requires additional work.
Final: Ruling: Full dispatcher/persistent checkpoint engine/automatic integration — upstream/team orchestration remains external; this adapter supplies contracts/readiness — cost if wrong: team must bind orchestration and persistence before sustained parallel runs.
Final: Ruling: Cryptographic human identity — trust repo-reviewed human attestation; verify actual artifact integrity — cost if wrong: forged authorized metadata needs a stronger approval/authentication service.
Final: Ruling: Complete upstream embedding — separate pinned official installation, own adapter only — cost if wrong: users must install upstream separately and verify ref.
Final: Ruling: Cloud creation/paid calls/push/publication — not performed in this delivery; GitHub/AI wizards ready, GCP/DB only after actual service need — cost if wrong: schedules and remote permissions remain unverified until provisioning.
Final verification: pytest140/140; root/subpath browser5/5 each; Astro check0errors/0warnings/10 existing hints; static build10 pages; skill validator and pip check pass; actionlint, bash -n, shellcheck pass (SC2034 existing template exclusion only). Live restore145events,2candidate packages; dist excludes private fixture/company profile path. Known pre-existing Zod deprecation hints and404 route precedence warning remain. Deferred minors: none reported by this review.

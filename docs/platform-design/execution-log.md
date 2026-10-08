# K1–K7 執行紀錄

日期：2026-10-08。base：`e2058b7`；分支：`codex/knowledge-radar-mvp`。

本機實作與驗收完成；獨立整體審查提出三項 Important，均完成重現測試與單次修正驗證。遠端Actions、Pages、YouTube live API尚未設定／驗證；沒有付費模型呼叫或對共享遠端push。

## 任務證據與設計裁定

Base: e2058b7. Managed worktree created; baseline is documentation-only, no existing test suite.
Pre-flight K1→K2→K3: dataclasses and config shared; constructors get conservative defaults.
Pre-flight K3→K4→K5: source public approval must travel with snapshot; add public_metadata/trust/topics to health so export never guesses visibility.
Pre-flight K5→K6→K7: SITE_URL/SITE_BASE and PUBLIC_EXPORT_TOKEN consistent; publish disabled by default.
Ruling: ledger helpers expect numeric Task headers but plan IDs are K1–K7; use same ledger format directly — preserves exact task identity and verification evidence.
Ruling: initial commit contains only seven reviewed design/research documents, not all original company docs — enables isolated worktree without exposing company files.

Task K1: complete — RED missing radar; GREEN 4 tests; pip check clean. Shared dataclasses/config validated.

Task K2: complete — RED missing adapter; GREEN 11 tests. Ten release endpoints returned HTTP200; records can be empty (skills repo). RSS and YouTube fixture-only.

Task K3: complete — RED missing normalize/store/pipeline; GREEN 20 tests including interrupted save and partial source failure.

Task K4: complete — RED missing export; GREEN 30 tests. Public DTO strips excerpt/inbox/error; private links and symlinks rejected; old output survives rejection.
Ruling: MVP attachments reject by default rather than copy arbitrary assets — no reviewed assets yet; future bundles add explicit attachment approval.

Task K5: complete — RED missing homepage/guide; GREEN 4 browser tests at root and /ai-workflow/, 30 Python tests, typecheck zero errors, npm audit zero vulnerabilities.
Ruling: Astro 7 auto-backgrounds agent dev processes; browser tests use static preview --ignore-lock — verifies built output instead of daemon behavior.
Ruling: install patched PostCSS nested/selector transitive versions via overrides rather than npm forced Starlight downgrade — builds and audit pass; compatibility validated by static build.
Final: minor (deferred): Astro/Starlight emits a 404 dynamic/static route precedence warning; correct 404 output renders, no duplicate user route.

Task K6: complete — RED missing CLI/state/publisher; GREEN 36 tests, actionlint clean, live collect 145 events twice with no duplicate revisions; source failures preserve state. Remote Actions not run; publication remains disabled.
Ruling: checkout v6 moves credentials out of local config; use gh credential helper with short-lived GH_TOKEN environment and persist-credentials:false — avoids relying on checkout internals.

Task K7: complete — RED missing wizard; GREEN 40 tests, bash -n clean. Five-stage repeatable wizard; --check/cancel no writes, secrets via stdin only, custom-domain root supported. Live setup intentionally not run. shellcheck subsequently installed and passed, excluding SC2034 for the unchanged wizard-template RED styling variable only.

## 使用方式

見根目錄README與setup-github.md。工作在Codex managed worktree，原始repo的其他公司文件仍未追蹤且未修改。

## 整體審查與最終驗證

審查範圍：e2058b7..376b723。使用 Sol 6.1 新上下文審查。初始 verdict 為 changes requested；三個 Important 全數修正，依執行技能不進行第二次審查，以下為作者的測試驗證，並非聲稱 reviewer 重新核准。

Final: fixed A→B→A content reversion retaining B — test_reverted_content_becomes_current_again RED→GREEN, suite 43/43. Historical revisions remain deduplicated; current event membership and last observation select A.
Final: fixed missing snapshot in existing pipeline-state branch silently resetting history — test_existing_branch_missing_snapshot_is_not_empty_initialization RED→GREEN, suite 43/43. Existing branch must contain a regular non-symlink valid snapshot; only an absent branch permits initialization.
Final: fixed daily publication deleting managed CNAME — test_managed_custom_domain_survives_daily_publication RED→GREEN, suite 43/43. Preserve validated DNS hostname from managed export repository; reject unsafe CNAME before publication.
Final: Ruling: paid AI/enrichment/budget governance — deferred to A1–A5 as agreed; K never calls a model — cost if wrong: this MVP provides raw signals without AI synthesis or paid-call safeguards.
Final: Ruling: versioned workflow bundles and arbitrary attachments — deferred to W1–W4; current download contains approved Markdown only — cost if wrong: no installable skill bundle until W is delivered.
Final: Ruling: authenticated hosting/SSO — public static Pages only; no private material exported — cost if wrong: internal-only access needs a different deployment architecture.
Final: Ruling: release-feed coverage — ten configured GitHub release sources, not complete author articles or social posts — cost if wrong: useful updates may be missed until sources expand.
Final: Ruling: live Actions/Pages/DNS/YouTube permissions — unconfigured and unverified externally; local wizard and fixtures only — cost if wrong: account permissions, DNS, quotas and schedule reliability may fail at provisioning.
Final: minor (deferred): date/search/download/private-index checks are manual end-to-end evidence, not added to repeatable browser CI coverage; automated suite currently covers navigation, escaping, stale state, topic filtering and mobile layout.

Final verification after fixes:
- Python 3.12: pytest 43/43; pip check clean.
- Browser smoke: 4/4 at / and 4/4 at /ai-workflow/.
- Astro check: 0 errors / warnings / hints. Root and subpath static builds: five pages. npm audit: 0 vulnerabilities.
- actionlint v1.7.12 clean; bash -n clean; shellcheck v0.11.0 clean with only SC2034 excluded for template library's unused RED variable. Template library not modified.
- Live state: 145 events and 145 historical revisions, collected twice with same counts; no paid model invocation.
- Final live site manual checks: 145 cards; 14-day filter 29 visible equals 29 expected; public search “來源” returns 1 result; private sentinel search returns 0; approved index.md download HTTP200; entire dist including binary search index excludes temporary PRIVATE_QA_K7_4d919fe2 sentinel. Temporary private fixture removed after validation.
- No live wizard, shared remote push, repository creation or Pages deployment performed. Source and export account settings remain user configuration work.

Previously recorded rulings retain these costs if wrong: manual K-number ledger requires manual bookkeeping; documentation-only baseline means original untracked company docs remain outside worktree; no attachments limits guide assets; static-preview tests do not exercise dev-daemon behavior; dependency overrides may need revisiting on upgrades; gh credential helper requires available authenticated gh in CI. Source approval metadata travels in snapshots to prevent guessed visibility; export still verifies explicit current approval.

官方 CNAME requirement: [GitHub Pages custom domain troubleshooting](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/troubleshooting-custom-domains-and-github-pages). Domain must still be set in Pages and DNS; preserving CNAME alone does not configure them.

## 後續 A 階段

A1–A5 本機交付完成，見 [雙週整理執行紀錄](enrichment-execution-log.md)。目前未啟用付費或建立遠端PR。

## 後續 W 階段

W1–W4本機交付與審查修正完成，見 [工作流執行紀錄](workflow-execution-log.md)。版本保持candidate，Android實測待binding；雲端設定見 [帳號時序](cloud-account-timing.md)。

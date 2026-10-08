# K1–K7 執行紀錄

日期：2026-10-08。base：`e2058b7`；分支：`codex/knowledge-radar-mvp`。

本機實作與驗收完成，整體審查進行中。遠端Actions、Pages、YouTube live API尚未設定／驗證；沒有付費模型呼叫或對共享遠端push。

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

Task K7: complete — RED missing wizard; GREEN 40 tests, bash -n clean. Five-stage repeatable wizard; --check/cancel no writes, secrets via stdin only, custom-domain root supported. Live setup intentionally not run. shellcheck unavailable locally.

## 使用方式

見根目錄README與setup-github.md。工作在Codex managed worktree，原始repo的其他公司文件仍未追蹤且未修改。

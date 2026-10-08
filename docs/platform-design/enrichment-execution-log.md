# A1–A5 執行紀錄

日期：2026-10-08；base 330b73c；分支 codex/fortnightly-enrichment。

Base: 330b73c. Baseline 43/43. Existing clean managed worktree reused on codex/fortnightly-enrichment.
Pre-flight A1→A2→A3: policy/reservation/usage and request persisted with result; explicit caps version.
Pre-flight A3→A4→A5: durable state precedes provider; private result plus repeatable draft/PR recovery.
Pre-flight K6→A3→A5: same pipeline-state CAS and concurrency; collection must preserve enrichment files.
Ruling: A-number task headers use manual matching ledger rather than numeric helper — costs manual bookkeeping.
Ruling: Reserve against official full 1M context ceiling instead of an unverified tokenizer or byte estimate — proven upper bound on accepted input; costs conservative budget utilization.
Task A1: complete — tests/test_enrichment_gate.py missing module RED→GREEN, whole suite 56/56. Disabled/empty/pending, exact UTC 14 days, cross-month unresolved reservation, expired prices and Decimal budget verified.
Task A2: complete — missing input/provider modules RED→GREEN; suite 66/66. Stable priority, public-only bounded input, versioned cache, single no-tools nonthinking HTTP request, usage/cap/model failures verified with MockTransport. Official pricing/API/thinking/token docs verified 2026-10-08. No real API calls.
Task A3: complete — missing runner/store RED→GREEN; suite 72/72. CAS temp Git remote persists ledger+result and collection preserves enrichment; persist failure calls=0; calling crash/timeout never retry; saved result reused; unknown usage retains reservation. First version performs zero retries.
Task A4: complete — missing evidence modules and missing digest page RED→GREEN; Python suite 83/83; Astro check 0 errors/warnings, 10 z deprecation hints; six-page build and browser 5/5. Quote/ID/schema/executable/fake-evaluation refusal; private drafts excluded; approved digest metadata sets both dates. Empty JSON array inferred never[], corrected by explicit Digest interface as in existing Radar DTO.
Task A5: complete — missing enrich CLI/PR/wizard/dispatch RED→GREEN; suite 92/92; actionlint clean; bash -n and shellcheck (only template SC2034 excluded) clean. Fixture roundtrip and private synthetic sample/report delivered; gh is fake/local bare remote in tests, no live paid/API/PR/wizard. Optional gate input_hash added to distinguish new revision batches from pending event IDs.

Final review: independent Sol 6.1 review of 330b73c..fb161b0, initial verdict With fixes. Three Important accepted, no Critical. No second review.
Final: fixed bounded overflow starvation — test_bounded_overflow_eventually_consumed_without_duplicates RED→GREEN, suite 103/103; unseen revision/hash pairs advance until all 60 consumed.
Final: fixed human-edited draft blocking recovery — test_human_edited_draft_does_not_block_recovery RED→GREEN; additional PR failure→human edit→MERGED integration passes with real Git CAS and fake gh; suite 103/103.
Final: fixed incomplete financial state resetting safeguards — four test_existing_state_required_fields_not_defaulted cases and test_inconsistent_settled_ledger_refused RED→GREEN; required JSON schema, ledger reconstruction consistency, completed batch due date checks; suite 103/103.
Final: fixed quoted false weakening explicit enabled gate — test_quoted_false_config_refuses_paid RED→GREEN; suite 103/103.
Final: fixed completed charge crossing calendar month — test_cross_month_completion_counts_in_both_uncertain_billing_months RED→GREEN; suite 103/103.
Ruling: For a request spanning UTC months, conservatively charge actual usage against both reservation and completion months — provider billing boundary not live-verified; cost if wrong: one boundary batch reduces available budget in both months.
Final: minor (deferred): latest approved digest timestamps use textual max; mixed timezone offsets can show the wrong latest update time, without changing financial UTC gates.
Final: minor (deferred): Astro z export has ten deprecation hints; check has no errors/warnings. Existing 404 route precedence warning also remains from K stage.
Final: Ruling: reviewer declined current pricing/model availability — executor checked official pricing/API on 2026-10-08 with 14-day expiry — cost if wrong: an in-window provider change still needs updated policy before payment.
Final: Ruling: actual billing/timeout semantics — no live paid authorization; preserve ambiguous reservation and no retries — cost if wrong: manual billing reconciliation remains necessary.
Final: Ruling: real GitHub permissions/dispatch/PR — no real account mutations; fake gh/local Git only — cost if wrong: account or organization policy may block provisioning.
Final: Ruling: semantic/factual correctness — human review remains mandatory — cost if wrong: traceable quotes can still support incorrect inference.
Final: Ruling: company approval/Android evaluation — W stage, no claims of evaluation — cost if wrong: workflow effectiveness not established.
Final: Ruling: video transcripts/Threads crawling — metadata/manual links only as spec — cost if wrong: some source knowledge omitted.
Final: Ruling: automatic price refresh — manual official verification every policy period — cost if wrong: stale policy postpones enrichment.
Final: Ruling: automatic ambiguous-charge recovery — manual confirmation only — cost if wrong: paused batches require operator intervention.
Final: Ruling: approved frontmatter authentication — trust repository human review, no cryptographic ledger attestation — cost if wrong: a trusted writer can mark content approved without a real review.
Final: Ruling: alternate default branches — main contract retained from K — cost if wrong: other branch names require adaptation.
Final: Ruling: multi-host scheduling/DB migration — deferred platform evolution — cost if wrong: Git state serialization is the scalability limit.
Final: Ruling: independent full-suite rerun — reviewer did targeted reproductions; executor reran full 103 tests after fixes — cost if wrong: broader behavior is evidenced by author-run coverage, not a second independent suite run.

## 最終驗證與外部狀態

Python 3.12：103/103 tests；包含真實 temp Git remote 的 ledger/result CAS，以及 fake gh 的 PR恢復。未付費、未跑 live wizard、未建立實際PR或push共享repo。
瀏覽器：根路徑5/5、/ai-workflow/子路徑5/5。另用 synthetic approved fixture 檢查兩個日期、指南跳轉、Markdown下載HTTP200與390px無橫向溢出。此fixture不會留在公開內容。
Astro：0 errors/0 warnings/10 deprecation hints；六頁靜態建置；npm audit 0 vulnerabilities。
actionlint clean；兩個wizard shellcheck clean（只排除未改模板RED未使用變數SC2034）；bash -n clean；pip check clean。
範例與報告在examples/；AI_ENABLED預設false。真實provider billing、GitHub permissions、Actions和PR均unconfigured/unverified。
初始 reviewer verdict With fixes，三個Important與兩個額外financial/config缺陷由作者RED→GREEN修正；沒有重新審查或聲稱reviewer已再次核准。

# Fortnightly AI Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在到期且預算足夠時整理公開新資訊，產生可追溯、可恢復的雙週草稿。

**Architecture:** 讀取 K3 的 Snapshot，由 deterministic gate 選事件；先持久化費用預留，再呼叫可替換 provider。结果先進私有草稿，通過來源檢查與人類 review 後才進 K4 export。

**Tech Stack:** 延用 Python/pytest/httpx/jsonschema、Git state、GitHub PR；DeepSeek HTTP adapter、fixture provider。不新增向量 DB 或 browser 即時 AI。

**Spec:** [架構提案](../../platform-design/2026-10-08-android-ai-workflow-platform-design.md)，§6–7、11–12。依賴 [MVP K1–K3；發布銜接 K6](2026-10-08-knowledge-radar-mvp.md)。

## Global Constraints

- `AI_ENABLED=false` 是預設；首次付費是明確操作，不因設定 token 自動啟用。
- interval_days=14；持久化 `next_ai_due_at`，不用 `*/14`。
- max_events_per_batch=20，允許設定至30；先排序與限制片段，再送 provider。
- 預算預設每批 US$0.50、每月 US$2；未審核價目／模型或無法約束可計費輸出時拒絕付費。
- 只讀公開來源片段，不讀公司 docs；付費結果不自動成為 company-approved。
- ambiguous timeout 不盲目重試；provider/schema/cache key 必須版本化。
- scope 是可審閱草稿，不保證模型的推論完全正確。

## Review Focus

1. 月底＋時區造成提前到期或預算重置 → A1 跨月／UTC測試。
2. provider timeout 或 process kill 導致重複收費 → A3 reservation/crash recovery 測試。
3. prompt 注入或未知來源 ID 進入核准摘要 → A2/A4 來源 allowlist 與 quote 測試。
4. review PR 尚未 merge 又重做同批 → A3/A5 批次去重與審閱狀態測試。
5. 模型／價格／輸出規則改變導致低估費用 → A1/A2 過期與不支援 cap 測試。

## File Structure / Contracts

`src/radar/enrich/` 只負責整理與台帳，不重寫 collectors。state branch 新增 `enrichment-state.json` 與 `batches/<batch_id>/result.json`，schema_version 獨立於 Snapshot；review草稿落 source repo 的 `content/drafts/` 分支，不進 public export。

A1 定義 `PricePolicy(model,input_usd_per_million,output_usd_per_million,checked_at,expires_at,max_output_tokens)`、`EnrichmentState(next_ai_due_at,batches,monthly_ledger)`、`Batch(id,input_hash,event_ids,status,reserved_usd,actual_usd,result_hash,review_pr_url)`、`GateDecision(allowed,reason)`；money 用 Decimal 字串，不用 binary float。狀態 reserved/calling/succeeded/ambiguous/failed/pending_review/reviewed/rejected。

A2 定義 `EnrichRequest(batch_id,model,prompt_version,schema_version,event_inputs,max_output_tokens)`；`ProviderResult(payload,input_tokens,output_tokens,reasoning_tokens,request_id)`。ProviderResult 的 token 語意要明確防止重複加計 reasoning；無 usage 結果不得自動釋放預留。

## Task A1: 到期與預算 gate

**Files:** Create `src/radar/enrich/{__init__,models,gate,budget}.py`, `schemas/enrichment-state.schema.json`, `config/model-pricing.yaml`, `tests/test_enrichment_gate.py`；Modify `config/pipeline.yaml`。

**Interfaces:** `decide_run(state: EnrichmentState, now: datetime, enabled: bool, eligible_event_ids: list[str], policy: PricePolicy) -> GateDecision`；`estimate_reservation(input_upper_bound: int, policy: PricePolicy) -> Decimal`；`reserve(state, batch: Batch, now: datetime) -> EnrichmentState`。

- [ ] Step 1：寫 `test_disabled_no_call`、`test_empty_no_call`、`test_due_is_exact_14_days_across_month`（Oct25→Nov8）、`test_pending_same_input_no_call`；`test_budget_counts_ambiguous_reservation` 與 `test_expired_price_rejected`。Gate reason 明確使用 disabled/no_new_data/not_due/pending_review/budget_exceeded/invalid_price。
- [ ] Step 2：`python -m pytest tests/test_enrichment_gate.py -q`，確認 FAIL。
- [ ] Step 3：實作 UTC 月度 ledger；紀錄跨月未解決 reservation，不能因月切換忘記可能付費項目。台帳允許其他新批次，但同 input hash 的 pending_review 阻擋重做。成功時間決定 next_ai_due_at=completed_at+14days；無新資料不推延 due。
- [ ] Step 4：同測試 PASS；Sol 審查 conservative estimate、金額語意。pricing expires_at 預設 checked_at+14days，過期保留每日收集並提示查核，不自行相信模型回傳的新價格。
- [ ] Step 5：精確 commit `feat: gate enrichment by interval and reserved budget`。

## Task A2: 有界輸入與 provider 契約

**Files:** Create `src/radar/enrich/{select,prompt,provider,deepseek}.py`, `prompts/enrichment-v1.md`, `schemas/enrichment-result.schema.json`, `tests/{test_enrichment_input,test_provider}.py`, `tests/fixtures/enrichment-result.json`。

**Interfaces:** `select_events(snapshot: Snapshot, done_ids: set[str], limit: int) -> list[Event]`；`build_request(events: list[Event], snapshot: Snapshot, policy: PricePolicy) -> EnrichRequest`；`EnrichmentProvider.generate(request: EnrichRequest) -> ProviderResult`；fake provider 与 DeepSeekProvider implements same interface。

- [ ] Step 1：測選取順序 trust A→B→C、release/能力變更優先、同分按事件 ID 穩定排序；private revision 不進 prompt；超过20事件截斷；每 revision excerpt≤600字元、每 batch 最多40 revision、輸入 UTF-8≤50KB。惡意片段要求改配置／洩漏 token 時仍只是資料，provider request 不含 tool calls。
- [ ] Step 2：`python -m pytest tests/test_enrichment_input.py tests/test_provider.py -q`，確認 FAIL。
- [ ] Step 3：實作 prompt 只請輸出繁體中文 why/usage/limitations/case_evidence/source_ids/claim_evidence；case_evidence enum=author_claim/vendor_case/reproducible/internal_evaluation/unknown。保留原始文摘的固定 ID。max_output_tokens=6000；單批最多一個模型 request，無默默額外修復呼叫。
- [ ] Step 4：實作前讀當時 DeepSeek 官方 API 與參數；model 以配置指定，pricing不自動沿用舊model。選能限制 billable output 的模式，明確設定推理模式及 provider caps；若API不能證明上限，dry-run說明限制且不自動付費。token上界用 provider 官方 tokenizer（可取得時）或查核過的保守 byte 上界加系統訊息／協議餘量；未能建立上界就拒絕自動呼叫。全部測試用 fake/MockTransport，不用真 key。
- [ ] Step 5：同測試 PASS；provider超長／未知usage/model錯誤皆明確返回失败；不記錄Authorization。精確 commit `feat: add bounded enrichment provider contracts`。

## Task A3: 持久化預留與中斷恢復

**Files:** Create `src/radar/enrich/runner.py`, `tests/test_enrichment_recovery.py`；Modify `scripts/state-sync.py`。

**Interfaces:** `run_batch(request: EnrichRequest, state: EnrichmentState, provider: EnrichmentProvider, persist: Callable[[EnrichmentState], None], now: datetime) -> Batch`。persist 必須將當次 batch 的台帳及結果一同完成 CAS push（結果payload由state中的batch引用），不只是寫 local JSON；失敗拋 exception 阻擋 call。batch_id/cache_key=hash(sorted revision hashes＋model＋prompt_version＋schema_version)。

- [ ] Step 1：測預留 persist 失敗 provider calls=0；同 hash succeeded 再跑 calls=0；timeout 後 ambiguous 且預留不釋放；程序在 calling 後中斷，重跑不呼叫；已存 result 但 draft 未建只恢復 draft。
- [ ] Step 2：`python -m pytest tests/test_enrichment_recovery.py -q`，確認 FAIL。
- [ ] Step 3：實作 reserve→durable calling checkpoint→provider once→durable result/usage→pending_review。並行使用 K6 相同 concurrency group `pipeline-state`、cancel false；跨流程一律 CAS。沒有記錄 response 的 calling/reserved 皆視為需確認，保守不自動重送。
- [ ] Step 4：把 actual cost 按 usage 計算並取代 reservation；unknown usage 保留 reservation 與問題狀態。網路模糊失敗不 retry；確定未發送與 provider明確未接受的錯誤只允許一次受预算约束的 retry，且有測試，否則第一版完全不 retry。
- [ ] Step 5：同測試 PASS；用 temp Git remote 重跑持久化 crash scenario；Sol 審查一次性呼叫與恢復。精確 commit `feat: recover enrichment without blind paid retries`。

## Task A4: 引用驗證與摘要草稿

**Files:** Create `src/radar/enrich/{validate,draft}.py`, `tests/test_enrichment_evidence.py`；Modify site 新增雙週精選頁與內容 metadata schema。

**Interfaces:** `validate_result(payload: dict, request: EnrichRequest) -> ValidatedEnrichment`；`write_draft(result: ValidatedEnrichment, output: Path) -> Path`。ValidatedEnrichment 包含 verified_claims/unverified_claims；unknown來源或quote不符為拒絕，不自動改為合理來源。

- [ ] Step 1：測未知 source ID、quote 非原始輸入子字串、schema多餘欄位、HTML/script／假安裝指令被當可執行附件均拒絕；合理來源與推論可寫 draft 但 review_state=draft。來源描述無逐字稿時，必有「未檢視影片全文」標記。
- [ ] Step 2：`python -m pytest tests/test_enrichment_evidence.py -q`，確認 FAIL。
- [ ] Step 3：實作 JSON schema 與 evidence映射；確實可引用的片段與推論分開；模板不得寫經過實測／公司核准除非存在對應 evidence record。輸出 Markdown 保存 batch_id、model、版本、source links、整理時間、人工核准狀態。
- [ ] Step 4：同測試 PASS；K4 export draft exclusion regression PASS；check/build PASS且已核准摘要頁顯示整理與review時間。格式修復不呼叫第二次模型；失敗保存私有診斷與原結果並供人工處理。
- [ ] Step 5：精確 commit `feat: validate evidence before creating enrichment drafts`。

## Task A5: Actions、PR 與 AI wizard

**Files:** Create `.github/workflows/enrich.yml`, `scripts/setup/ai.sh`, `scripts/open-digest-pr.py`, `docs/platform-design/setup-ai.md`, `tests/test_enrichment_cli.py`；Modify `src/radar/cli.py`, `config/pipeline.yaml`。

**Interfaces:** `python -m radar.cli enrich --state-dir PATH --dry-run` 預設無付費；真正呼叫需 `--allow-paid` 且 ai_enabled=true。`open-digest-pr.py --batch-id ID --draft PATH` idempotently 建立／更新固定 digest branch/PR，同 batch 不再開新 PR。

- [ ] Step 1：測 dry-run 沒 token 也成功、default paid denied、同batch PR僅一個、已 rejected 不自动重付費、enrich停用不影響collect。用fake gh與provider。
- [ ] Step 2：pytest FAIL 後，實作手動 enrich入口與 daily due check。collect持久化後明確 dispatch enrich，dispatch workflow取得同 group鎖並重讀state；不能在持有同 group鎖時同步等待子workflow。token secret僅 paid job可讀，PR版checks用fixtures。無權開PR時保留結果、待人工處理，不重呼叫。
- [ ] Step 3：按 wizard skill template 實作 API帳號與hidden token→GitHub Secret `DEEPSEEK_API_KEY`→模型價目确认→interval14/预算設定→dry-run→首次paid明确操作。保存非敏感 resume；取消、無新資料、超預算時provider calls=0。
- [ ] Step 4：Python相關測試＋shell語法／shellcheck＋K6狀態測試 PASS。假資料跑完整draft roundtrip。沒有真token／未啟用時標記 paid live run未驗證；不得為了完成測試自行付費。
- [ ] Step 5：精確 commit `feat: schedule reviewable fortnightly enrichment`。

## Completion / Handoff

交付一份 fake provider 產出的 clearly labeled 示範精選、一份dry-run預算報告、台帳恢復證據與設定說明。真實付費／PR發布另記其狀態。價格與provider行為在實作當下再次查核：[DeepSeek pricing](https://api-docs.deepseek.com/quick_start/pricing/)、[JSON mode](https://api-docs.deepseek.com/guides/json_mode)；不以舊的模型名稱或價格當永久契約。

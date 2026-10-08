# FDE Updates and Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓 FDE 與 Android 共用雙週更新、去重與預算，最後加入可驗證部署配置與統一 wizard。

**Architecture:** 免費 source 收集擴充 topic，付費批次仍只有一個持久 Git CAS 財務 ledger。公開精選 metadata 從可信來源推導 domain。企業 labs 的 DB/API 部署另外建 profile，知識站仍維持靜態。

**Tech Stack:** 現有 radar Python、GitHub Actions、Astro；Bash wizard；GCP Cloud Run／Scheduler 配置（本輪 dry-run）。

**Spec:** [設計規格](../specs/2026-10-08-fde-learning-hub-design.md)

## Global Constraints

- 前置：[F1–F3](2026-10-08-fde-content-and-skills.md)、[F4–F7](2026-10-08-fde-local-labs.md)。本計劃放最後。
- 14 天持久 next_due；AI 停用預設；全站預算每批 USD 0.50／每月 USD 2，保持原財務狀態與 ambiguous 規則。
- 舊 request/prompt 與已產生 payload 可 resume，不因新增 topics 改變歷史付款身份。
- 模型不能自己指定採納、來源權限或生成可執行 skills；roadmap 更新僅人工 reviewed proposal。
- 不建立 cloud resource、不 push/merge/deploy，不呼叫付費 API；wizard 是後續由人操作的入口。

## Review Focus

- Android/FDE 候選量失衡不能使一方持續餓死；F8 測試。
- 同 story 多 topic 只收費一次；舊 saved request resume 不改 batch；F8 測試。
- 精選／時間不能混用全站其他 topic 更新，AI 停用不能假報已更新；F8 測試。
- 部署配置未知 profile、任意 shell、公開未授權 endpoint 必須拒絕；F9 測試。
- wizard --check、取消、失敗不能寫 secrets／啟用付費／呼叫 cloud；F10 測試。

## File Structure

修改 `src/radar/enrich/select.py` 的 bounded fair selection，新增 `src/radar/enrich/topics.py` 負責可信分類；既有 ledger/runner/gate 不另開一套。`config/fde-deployment.yaml` 與 `scripts/fde-deployment.py` 管理可審阅配置；`scripts/setup/fde.sh` 放 human-only 帳號操作。

### Task 8 / F8: 來源差量與共用雙週更新

**Files:** Modify `config/sources.yaml`, `src/radar/enrich/{select,draft,metadata,command}.py`, `src/radar/export.py`, `site/src/pages/fde/updates.astro`; create `src/radar/enrich/topics.py`, `tests/test_fde_updates.py`, `content/public/fde/update-policy.md`。

**Interfaces:** 保留 `select_events(snapshot, done_ids, limit=20)` 舊 consumer；多領域時 deterministic round-robin android/fde 桶，同 event 去重、桶內原 priority。`event_topics(event, snapshot) -> list[str]` 只用 public source health metadata。`write_draft(..., topic_map=None)` 可選來源側 topic mapping；舊 draft recovery topic_map 缺省保持舊內容。

- [ ] Step 1: 寫 `test_fair_topics_without_duplicate_events`：20 Android＋3 FDE、limit=4，兩者入選且 unique ids；`test_single_domain_priority_unchanged` 保留既有 trust/version/id 排序；`test_old_saved_request_recovers_without_model_call_or_new_identity` 讀舊 fixture saved request；`test_private_topic_cannot_classify_public_story`；`test_fde_digest_metadata_excludes_android_only_and_reports_disabled`。
- [ ] Step 2: `.venv312/bin/python -m pytest tests/test_fde_updates.py -q`；Expected: 缺公平選取／domain export 而失敗。
- [ ] Step 3: 逐一查核 Spring AI、Temporal Python SDK、pgvector、Qdrant、Ollama、vLLM、Pydantic AI、TRL 官方 release endpoint，沿用 adapter 記 verified_at／provenance；LangGraph 加 fde topic，不重複 source。無發布 feed 顯示 empty，不造更新。加入 fair selection；對已 bounded request 的實際 included event ids 推導 topics，混合 story 不拆第二付費批次。digest metadata optional topics，歷史精選缺分類標 legacy/unclassified，不冒充 FDE。public radar 合併公開 revisions topics。
- [ ] Step 4: 測試、enrichment 全部回歸、全 pytest；一次免費 live collect／export 查18來源狀態，允許個別 empty/failure 明列；fixture provider 測同 ledger reservation/calling/ambiguous/budget；FDE UI顯示 collected/enriched/reviewed/next_due 分開，未啟用 AI 據實顯示；root/subpath browser PASS。
- [ ] Step 5: commit `feat: share bounded fortnightly updates across domains`；ledger，不執行付費 workflow。

### Task 9 / F9: API/DB/排程部署配置與 dry-run

**Files:** Create `config/fde-deployment.yaml`, `src/radar/fde/deployment.py`, `scripts/fde-deployment.py`, `examples/fde/deploy/{Dockerfile,README.md,postgres.sql}, `examples/fde/python/fde_lab/postgres.py``, `tests/test_fde_deployment.py`; modify `content/public/fde/{cloud,api,data,handover}.md`。

**Interfaces:** `load_deployment(path: Path) -> dict`、`deployment_plan(config: dict) -> list[list[str]]`；CLI `--check`／`--dry-run` 只驗證及列出 argv，不 execute。profiles `local-sqlite|gcp-postgres`；必填 project/region/image_digest/service_account/API audience、secret reference，不能放 secret value。本輪只提供可信命令清單和部署契約，不內建任意 command execution。

- [ ] Step 1: 寫 `test_local_profile_requires_no_cloud_account`、`test_cloud_profile_requires_identity_private_api_and_pinned_image`、`test_unknown_field_or_secret_value_rejected`、`test_dry_run_never_executes_cloud_or_changes_files`；另寫 `test_postgres_tenant_policies_and_idempotency_constraints`，只在明確 opt-in 測試 DB 跑，不在缺 DB 時假 PASS。
- [ ] Step 2: `.venv312/bin/python -m pytest tests/test_fde_deployment.py -q`；Expected: parser/plan 功能不存在失敗。
- [ ] Step 3: 查核 GCP WIF/OIDC/IAM/Secrets 與選定 PostgreSQL 供應商官方 docs，固定版本配置。Dockerfile 可本機 build、不 auto push；API 私有與 least privilege；Jobs/Scheduler argv 綁身分與 schedule timezone。SQL提供 migration、tenant role/RLS、唯一 key、versioned vectors；backup/restore/runbook明列。Python/Java local profile 保持可用；實作 `PostgresJobStore(dsn: str)` 與 `PostgresRagStore(dsn: str)` adapters，沿用 F4/F5 的 public 方法與契約；pgvector index 綁模型/維度版本，connection secrets 僅環境或 secret reference。所有相同 tenant/idempotency/lease tests 對 PostgreSQL 再跑，必須通過真實 opt-in integration 才能標 ready；未配置保留未驗證狀態。
- [ ] Step 4: parser tests＋全 pytest、local container build/health（先檢查 daemon）；dry-run 檢查無 secrets/任意 shell，state 不變。Postgres integration 無 service 時 report 未測，不標雲端 profile ready；不建立任何 remote DB。
- [ ] Step 5: commit `feat: add reviewable FDE deployment profiles`；ledger 記local／cloud驗證界線。

### Task 10 / F10: 最後的統一 wizard 與全分支驗收

**Files:** Create `scripts/setup/fde.sh`, `tests/test_fde_wizard.py`, `content/public/fde/setup.md`; modify `scripts/setup/{github,ai}.sh` 僅必要入口說明，`README.md`, `docs/platform-design/fde-execution-log.md`。

**Interfaces:** Bash `fde.sh --root PATH --check`；人選 `local|github|provider|api-db|gcp|health` 階段。--check 不開瀏覽器／寫檔／需要 cloud login；選配階段在自己的邊界檢查帳號。呼叫既有 GitHub/AI wizard 保留原付費 gate；F9 check/dry-run 用相同 configuration。

- [ ] Step 1: 使用 wizard 技能讀原版 library，不修改 library；寫 `test_check_and_cancel_have_no_side_effects`、`test_local_does_not_require_gh_gcloud_or_token`、`test_secret_never_appears_in_output_env_or_git`、`test_failed_cloud_checks_never_enable_paid_or_apply`；使用可記錄的 fake CLIs 驗證 argv 與未呼叫 mutation。
- [ ] Step 2: `.venv312/bin/python -m pytest tests/test_fde_wizard.py -q`；Expected: wizard 缺失失敗。
- [ ] Step 3: 寫 human-only stages：選模式、GitHub／provider、DB endpoint/secret reference、GCP identity、review配置、dry-run、health/rollback。秘密以隱藏輸入／stdin，不存 state，非秘密配置可重跑。沒有部署需求就 local-only 完成；真正 resource 建立需使用者審閱具體配置後另行執行，wizard 本輪不自動 apply。
- [ ] Step 4: 全 pytest、Maven verify、Astro check/build、browser root/subpath、bash -n、shellcheck、actionlint、技能驗證；檢查公開 dist 無 private data，三套 labs實際結果、舊ZIP SHA不變。免費 live restore；完整記錄未配置選配服務及既有 warnings。
- [ ] Step 5: commit `feat: integrate FDE setup and delivery guidance`；一次 fresh-context 全分支 review（依使用者 Sol 偏好）；Important/Critical 一輪 RED→GREEN 修正並回歸，minor留紀錄；最後使用 finishing-a-development-branch，等使用者選本機合併／push／保留，不自行推送或部署。

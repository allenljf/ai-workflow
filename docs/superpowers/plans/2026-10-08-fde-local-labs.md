# FDE Local Labs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 提供不需要 token/GPU 的 RAG、可恢復任務、資料品質範例與 Spring Boot 對照 API。

**Architecture:** Python labs 是獨立可安裝模組，runtime 在 .build/fde-labs，與 radar 財務 state 分離。SQLite 先驗證契約；Ollama 為選配。Java 模組遵循相同 HTTP/資料契約，固定相容 release，fixture 可測。

**Tech Stack:** Python 3.12、SQLite/FTS5、httpx、Java/Spring Boot、Maven、JUnit。

**Spec:** [設計規格](../specs/2026-10-08-fde-learning-hub-design.md)

## Global Constraints

- 前置：[F1–F3](2026-10-08-fde-content-and-skills.md)；runtime、客戶資料、秘密與 weights 不進 git/公開包。
- 不自動下載 model、不啟動 GPU training、不呼叫付費 API；fixture 成果不得標模型品質。
- tenant 來自可信 caller；schema、資源授權與業務 validation 分層。
- 模型引用僅能來自本次授權 chunks；不足返回 insufficient_evidence。
- 長任務 ambiguous 不自動重付費，不重寫程式／擴權；attempt/deadline/budget 有上限。

## Review Focus

- 跨 tenant、舊版本文件與偽造引用不可輸出；F4 測試。
- 不同 embedding 模型／维度不可混寫；F4 測試。
- 舊 worker 在 lease 被接手後不能覆寫 checkpoint；F5 測試。
- 相同 key 不同 payload、扣費結果不確定不能當成功／重試；F5/F7 測試。
- 同文件／客戶近重複與時間穿越不可進 holdout；F6 測試。

## File Structure

`examples/fde/python/fde_lab/` 分 rag/providers/jobs/data/cli；合成 fixtures 放鄰近 fixtures。`examples/fde/spring-api/` 獨立 Maven 模組。主 repo tests 透過 fixture 安装路徑測試公開邊界，不把 lab state 與 src/radar/enrich 混用。

### Task 4 / F4: 授權 RAG 與選配 Ollama

**Files:** Create `examples/fde/python/pyproject.toml`, `fde_lab/{__init__,rag,providers,cli}.py`, `fixtures/documents.json`, `tests/test_fde_rag.py`; update `content/public/fde/{rag,local,getting-started}.md`。

**Interfaces:** `RagStore(path: Path)`；`ingest(documents: list[dict]) -> dict`；`query(tenant: str, query: str, provider, limit: int=5) -> dict`。Document 包含 id/version/tenant/text/source_url；Answer 包含 status/answer/citations。`FixtureProvider.generate(chunks, query)` 與 `OllamaProvider(base_url, model, embedding_model)`；model/digest/dim 綁 index version。

- [ ] Step 1: 寫 `test_rag_never_returns_other_tenant_or_superseded_version`、`test_no_evidence_and_forged_citation_rejected`，以兩 tenant/兩版本實 SQLite 測；`test_embedding_model_dimension_mismatch_rejected`；`test_ollama_truncation_timeout_and_schema_failure` 用本機 HTTP fixture server，不呼叫外部模型。
- [ ] Step 2: `.venv312/bin/python -m pytest tests/test_fde_rag.py -q`；Expected: 尚無 lab import/功能而失敗。
- [ ] Step 3: 實作 versioned SQLite/FTS、ACL 前置 filter、允許引用集合、長 context comparison 題集與報告 metadata。Ollama embed 明確 truncate=false、timeouts、response schema，固定本機 endpoint；fixture 與真模型報告 evidence_level 不同。
- [ ] Step 4: 以上 tests＋全 pytest；CLI `python -m fde_lab.cli rag-demo --state-dir .build/fde-labs/rag`；Expected: public 合成 tenant 的引用、無證據拒答、fixture 標示。真模型未配置列未測。
- [ ] Step 5: commit `feat: add tenant-scoped local RAG lab`；ledger。

### Task 5 / F5: 持久任務、恢復與失敗路徑

**Files:** Create `fde_lab/jobs.py`, `tests/test_fde_jobs.py`, `examples/fde/python/fixtures/jobs.json`; modify `fde_lab/cli.py`, `content/public/fde/durable.md`。

**Interfaces:** `JobStore(path)`；`submit(tenant, key, payload, now, deadline, max_attempts=3, max_cost_usd='0') -> dict`；`claim(owner, now, lease_seconds=30) -> dict|None`；`checkpoint(job_id, owner, lease_version, step, receipt, now) -> None`；`get(tenant, job_id) -> dict`；`cancel(tenant, job_id) -> dict`。SQLite transaction＋unique(tenant,key)，claim 增 lease_version。terminal states succeeded/failed/ambiguous/cancelled。

- [ ] Step 1: 寫 `test_restart_resumes_without_repeating_receipted_side_effect` 用子程序中斷後新 process 續跑；`test_expired_worker_cannot_checkpoint_after_takeover`；`test_duplicate_payload_conflict_and_tenant_isolation`；`test_ambiguous_timeout_does_not_retry`；`test_attempt_budget_deadline_cancel_stop_work`。
- [ ] Step 2: `.venv312/bin/python -m pytest tests/test_fde_jobs.py -q`；Expected: JobStore 缺失而失敗。
- [ ] Step 3: 實作 schema migration、lease fencing、持久 receipt、有限 backoff 與 terminal transition。合成可恢復讀寫 demo，外部副作用已送出但未知結果轉 ambiguous；worker 重啟不能重置 attempts/cost/deadline。runbook 對照 Temporal，不冒充完整 production engine。
- [ ] Step 4: tests＋全 pytest、CLI jobs-demo 真實中斷/恢復；Expected: 一份副作用 receipt、正確狀態、實際報告保存。
- [ ] Step 5: commit `feat: add recoverable bounded job lab`；ledger。

### Task 6 / F6: 資料品質與訓練準備

**Files:** Create `fde_lab/data.py`, `fixtures/dataset.jsonl`, `tests/test_fde_data.py`; modify CLI、`content/public/fde/{analysis,training,eval}.md`。

**Interfaces:** `analyze_dataset(rows: list[dict]) -> dict`；`prepare_dataset(rows, output: Path, cutoff: str) -> dict`。Row: id/group_id/timestamp/prompt/completion；manifest 有 split counts、hash、lineage、查核結果；training profile dry_run=true，無 model download。

- [ ] Step 1: 寫 `test_duplicate_group_and_time_leakage_refused`、`test_missing_schema_and_invalid_timestamp_rejected`、`test_dataset_hash_and_split_manifest_reproducible`，hand-derived fixture 驗證 train/validation/holdout 無同 group、晚資料不入 train；`test_training_dry_run_has_no_network_or_weights`。
- [ ] Step 2: `.venv312/bin/python -m pytest tests/test_fde_data.py -q`；Expected: 功能不存在而失敗。
- [ ] Step 3: 實作 schema／missingness／正規化文本 hash 去重，group/time split、資料集 hash、eval failure buckets；SFT messages/prompt-completion 轉換只針對授權合成樣本，輸出配置與決策說明，不 train。
- [ ] Step 4: tests＋全 pytest；CLI dataset-demo；Expected: 可重現 manifests、無隱藏 downloads；新增範例資產要 F2 approval hash，已發布包若內容變更建立 0.2.0 並保留 0.1.0 sources。
- [ ] Step 5: commit `feat: add dataset quality and training preparation lab`；ledger。

### Task 7 / F7: Java Spring Boot 對照 API

**Files:** Create `examples/fde/spring-api/pom.xml`, `src/main/java/com/workflowradar/fde/{Application,JobController,JobService,JobRepository,PrincipalFilter,FixtureProvider}.java`, `src/main/resources/db/migration/V1__jobs.sql`, `src/test/java/com/workflowradar/fde/JobApiTest.java`, README；create `examples/fde/contracts/openapi.yaml`, modify公開 API/交接指南。

**Interfaces:** `POST /jobs`（Idempotency-Key）、`GET /jobs/{id}`、`POST /jobs/{id}/cancel`、`POST /rag/query`、`GET /health`。本機 auth profile 的服務端配置 token→tenant 映射，body tenant 拒絕；job HTTP statuses 201/200/409/404/401，JSON error code 不含秘密。資料契約同 F5，Java 獨立 SQLite DB。

- [ ] Step 1: 查核官方 Spring Boot/AI/Maven/SQLite JDBC 相容 release、license、checksum；固定 BOM，先寫 JUnit HTTP contract tests：unauthenticated=401、cross-tenant=404、same key/same payload=同 id、different payload=409、cancel terminal、安全 schema failure。固定 tenant token 只在 test fixture。
- [ ] Step 2: 用官方固定 Maven 在 .build/tools 執行 module tests；Expected: routes/implementation 缺失失敗，非環境下載錯誤。
- [ ] Step 3: 實作 controllers/service/repository，transaction/unique constraints、可信 principal，fixture provider與可選 Spring AI provider分隔。補 OpenAPI、local start、migration與 Spring/Python 對照，無 token 預設僅 health 可用。
- [ ] Step 4: Maven verify、全 pytest、API 真實 local HTTP 冒煙；Expected: compile/test PASS，錯誤/重複/跨 tenant 正確；模型整合只有 fixture，Ollama 未測另列。
- [ ] Step 5: commit `feat: add Spring Boot enterprise API reference`；ledger。下一份整合計劃消费 API 契約，不把「local PASS」稱 cloud 已部署。

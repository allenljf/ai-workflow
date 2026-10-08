# Knowledge Radar MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 建立不呼叫模型的知識網站，具備可恢復每日蒐集、精確去重、核准內容匯出與部署準備。

**Architecture:** Python 批次蒐集、JSON 持久化於 pipeline-state branch；Astro/Starlight 只讀經隔離的 export。開發預設本機與 artifact 預覽，公開內容透過獨立 export repo 發布；不直接發布此 repo。

**Tech Stack:** Python 3.12、pytest、httpx、feedparser、PyYAML、jsonschema；Node 22.12+ 的受支持偶數版本、npm、Astro/Starlight、Playwright。執行時鎖定相容依賴與 Actions commit SHA，不在計劃臆造版本。

**Spec:** [架構提案](../../platform-design/2026-10-08-android-ai-workflow-platform-design.md)，§1–7、9–12。

## Global Constraints

- `AI_ENABLED=false`；網站瀏覽不呼叫模型。
- 每日台北 09:17，UTC `17 1 * * *`；schedule 不是精確 SLA。
- 不把整個 `docs/` 複製到網站或公開 repo；新人工內容預設 private/draft。
- 只有 `visibility: public` 且核准內容可匯出；每日 metadata 使用核准來源與明確欄位 allowlist。
- Actions cache/artifact 不是唯一持久化資料庫；來源失敗保留前次成功資料。
- 本計劃不新增 GCP、DB、向量庫、影片逐字稿與付費搜尋。
- 全部時間以 timezone-aware UTC ISO8601 儲存，顯示 Asia/Taipei；未知 published_at 為 null，不偽造日期。
- 精確 commit scope；不修改既有公司文件，不自動 push 或發布。

## Review Focus

1. 私有文件與附件透過 symlink、路徑跳脫或搜尋索引外洩 → K4 的 export boundary 測試。
2. 來源 HTTP 失敗或 304 導致資料被清空／日期被覆寫 → K2/K3 的保留與健康測試。
3. 追蹤參數清理錯刪影片識別、版本被合併 → K3 的 URL／event 測試。
4. 網站建置成功但 repo 子路徑、惡意來源 HTML／URL 不正確 → K5 的 browser smoke。
5. 重複排程、state push 失敗或權限不足導致遺失資料／發布舊快照 → K6 的狀態 CAS 與發布前檢查。

## File Structure / Contracts

`src/radar/` 是 Python 套件（`pyproject.toml` 的 src layout）；模組可透過 `python -m radar.cli` 執行。`scripts/` 只放操作入口，不複製套件邏輯。site 在 `site/`，唯一內容輸入是 `.build/export/`。

K1 定義 dataclasses：`Source(id,type,url,trust_tier,topics,enabled,public_metadata,options)`、`FetchResult(source_id,status,items,etag,last_modified,error)`、`ItemRevision(id,source_id,external_id,canonical_url,title,published_at,updated_at,fetched_at,content_hash,excerpt,access_scope,entity,version)`、`Event(id,entity,version,item_revision_ids,status,dedup_reason)`、`SourceHealth(last_attempt,last_success,status,error,etag,last_modified)`、`Snapshot(schema_version,revisions,events,health,inbox)`。status 與 type 用明確 enum；註記 optional 欄位，不用自由字典代替核心型別。`Snapshot` 不含模型 token。

資料：`config/sources.yaml`、`config/pipeline.yaml`、`config/publication.yaml`、`schemas/snapshot.schema.json`、`content/public/`、`content/private/`。Git state branch root 使用 `snapshot.json`；網站讀 `radar.json`，是刻意刪除私有欄位的公開 DTO。

## Task K1: 配置與資料契約

**Files:** Create `pyproject.toml`, `src/radar/__init__.py`, `src/radar/models.py`, `src/radar/config.py`, `schemas/snapshot.schema.json`, `config/{sources,pipeline,publication}.yaml`, `.gitignore`, `tests/conftest.py`, `tests/test_contracts.py`。

**Interfaces:** `load_config(root: Path) -> RadarConfig`；`validate_snapshot(value: dict) -> Snapshot`。`PublicationConfig` 含 allowed_content_roots、site_url、site_base、export_repo、publish_enabled；`ExportReport` 在K4定義。`RadarConfig` 含 sources、interval_days=14、ai_enabled=False、publish_enabled=False、max_items_per_source=100、request_timeout_seconds=20、allowed_content_roots=['content/public']、site_url（本機預設 http://localhost:4321）、site_base（本機 '/'）。

- [x] Step 1：建立 fixtures `source()`、`revision(**overrides)`、`snapshot()`、`approved_doc(root, **frontmatter)`；後續測試共用。寫 `test_missing_visibility_is_private`、`test_reject_naive_time`、`test_duplicate_source_ids`，分別斷言預設 private、無時區拒絕、重複 ID 拒絕。
- [x] Step 2：`python -m pytest tests/test_contracts.py -q`，確認先因缺少模組／功能失敗。
- [x] Step 3：實作上述 dataclasses、enum、載入與 schema；來源初期空清單合法，未知 schema_version 拒絕。gitignore 排除 `.build/`、`.venv/`、node_modules、暫存 state、wizard state 與 secrets。
- [x] Step 4：安裝開發依賴後同命令 PASS；Source.public_metadata 預設false、只對人工核准來源設true；不檢查私有 env token；`python -m pip check` 無依賴衝突。
- [x] Step 5：只 stage 本任務檔案並 commit `feat: define radar configuration and data contracts`；有未追蹤 docs 不代表可一起 stage。

## Task K2: 來源蒐集與手動收件匣

**Files:** Create `src/radar/fetch.py`, `src/radar/adapters/{__init__,feeds,github,youtube,manual}.py`, `content/inbox/links.json`, `tests/test_adapters.py`, `tests/fixtures/{feed.xml,release.json,youtube.json}`；Modify `config/sources.yaml`。

**Interfaces:** `fetch_source(source: Source, previous: SourceHealth | None, client: httpx.Client) -> FetchResult`；`read_manual_links(path: Path) -> list[dict]`。`FetchResult.status` 是 updated/not_modified/failed；items 是 normalized item input dictionaries，由 K3 產生 revision。client 可注入，測試不連網。

- [x] Step 1：寫 `test_feed_304_keeps_no_new_items`（not_modified、items=[]）、`test_source_timeout_returns_failed`（不拋出導致其他來源停止）、`test_youtube_no_key_is_disabled`、`test_manual_url_must_be_https`。用 httpx MockTransport 與 fixtures。
- [x] Step 2：`python -m pytest tests/test_adapters.py -q`，確認 FAIL。
- [x] Step 3：實作 RSS/Atom、GitHub release、YouTube uploads metadata 與手動 URL。只允許配置的 HTTPS 來源；拒絕私有／loopback 網路目標、重新驗證 redirect destination，限制 response 2MiB、redirect 3 次、timeout 20秒。無 key 不啟動 YouTube；不下載字幕。陌生手動 URL 只保存連結待核准，不自動擴大抓取範圍。
- [x] Step 4：同測試 PASS；另外測不安全 redirect 拒絕。從既有調研原始來源挑至少 10 個 RSS/release 來源，逐個查核端點，記錄 source id、信任層級、topics、public_metadata=true 與 provenance；不猜官方 RSS 路徑。真正 live smoke 與 fixture 結果分開報告。
- [x] Step 5：精確 stage 並 commit `feat: collect verified feeds and source metadata`。

## Task K3: 去重、revision 與持久化快照

**Files:** Create `src/radar/{normalize,dedup,store,pipeline}.py`, `tests/{test_dedup,test_store,test_pipeline}.py`。

**Interfaces:** `canonicalize_url(url: str) -> str`；`merge_fetch(snapshot: Snapshot, result: FetchResult, now: datetime) -> Snapshot`；`load_snapshot(path: Path) -> Snapshot`；`save_snapshot(path: Path, snapshot: Snapshot) -> None`；`collect(config: RadarConfig, previous: Snapshot, client: httpx.Client, now: datetime) -> Snapshot`。

- [x] Step 1：寫下列明確 assertions：`canonicalize_url('https://www.youtube.com/watch?v=abc&utm_source=x') == 'https://www.youtube.com/watch?v=abc'`；兩次同 stable ID/content hash 抓取 revision 數量不增；原 URL 內容變更產生第二 revision；v1/v2 release 產生兩個 event；failed/304 均保留舊 events 與 published_at；failed 保留 last_success，304 更新 last_success 為本次成功確認時間。
- [x] Step 2：`python -m pytest tests/test_dedup.py tests/test_store.py tests/test_pipeline.py -q`，確認 FAIL。
- [x] Step 3：實作 tracking allowlist（utm_*、fbclid、gclid）；穩定 ID→canonical URL→content hash；可信 repo/version 用 event key 合併，多來源保留 provenance。title similarity 只標疑似，不永久合併。same content 不因 fetched_at 產生 revision；304 可更新 last_success，failed 只更新 last_attempt。內容清理為純文字，excerpt 最大 600 字元。
- [x] Step 4：save 使用同目錄 temp＋replace；讀取壞 JSON 明確失敗，不靜默 reset。加入 `test_corrupt_state_is_not_overwritten`、`test_interrupted_save_keeps_previous_file`；同測試 PASS，結果符合 K1 schema。
- [x] Step 5：精確 commit `feat: persist idempotent collection snapshots`。

## Task K4: 公開 export 隔離

**Files:** Create `src/radar/export.py`, `tests/test_export.py`, `content/public/index.md`, `content/private/README.md`；Modify `config/publication.yaml`。

**Interfaces:** `export_public(snapshot: Snapshot, content_root: Path, output: Path, publication: PublicationConfig) -> ExportReport`；report 有 copied_paths、excluded_paths、errors。輸出 `radar.json`、`docs/`、`manifest.json`；只准在新 staging dir 完成驗證後取代 output，不清空任意路徑。

- [x] Step 1：測試核准公開 frontmatter `{visibility: public, review_state: approved}` 被收錄，缺欄位／draft／private 被排除；`content/public/leak.md` 指向 docs 私有檔的 symlink 應拒絕。加入附件 `../`、Markdown local links 與原始 HTML 包含相對私有路徑的檢查，不依賴掃描關鍵字宣稱安全。
- [x] Step 2：`python -m pytest tests/test_export.py -q`，確認 FAIL。
- [x] Step 3：實作 realpath root allowlist、拒絕所有 symlink、只允許 `.md` 與明確核准附件；不讀 `docs/`。每日 metadata 僅取已核准 public_metadata 來源的 id/title/url/date/trust/topics/health，保留「機器蒐集，未深入整理」狀態，不帶 raw body、inbox 或 error 中憑證。人工指南另需 approved。
- [x] Step 4：同測試 PASS；對 fixture 私有標記檢查 export 全部檔案與 manifest 均無該字串。Sol 審查資料邊界及 static search index 輸入。無 public review 的指南不自動轉 approved。
- [x] Step 5：精確 commit `feat: enforce reviewed public content export`。

## Task K5: 可使用的靜態網站

**Files:** Create `site/package.json`, `site/package-lock.json`, `site/astro.config.mjs`, `site/tsconfig.json`, `site/src/content.config.ts`, `site/src/pages/index.astro`, `site/src/components/{EventCard,SourceHealth}.astro`, `site/src/styles/custom.css`, `scripts/build-site.py`, `site/tests/smoke.spec.ts`, `site/playwright.config.ts`。

**Interfaces:** `scripts/build-site.py --export .build/export --site site` 把 export docs 與 radar.json 複製到明確 generated 輸入；`npm --prefix site run check/build`。site/base 由設定注入，不在 browser 使用 secrets。不允許 glob repo/docs。

- [x] Step 1：建立 Astro/Starlight 相容 scaffold 與 lockfile；先加入 browser smoke：首頁可見原始来源連結與三種時間；來源失敗有 stale 顯示；空資料有說明。測含 `<script>` 標題顯示文字、`javascript:` 來源拒絕。
- [x] Step 2：先跑 `npm --prefix site run test:smoke`，記錄必要頁面未建立的 FAIL。
- [x] Step 3：實作繁體中文導覽「新訊／指南／工作流／來源」，依日期與 topic 篩選；所有事件帶信任與整理狀態。指南用 Starlight，無指南則空狀態。index、下載及搜尋資料只來自 export；不使用 raw HTML render 來源片段。
- [x] Step 4：check/build/smoke PASS；以 `/ai-workflow/` base 再 smoke，內部連結與資產可載入。實際檢視 desktop/mobile、搜尋核准指南與私有 fixture 不可搜尋；避免用未安裝的 Mermaid plugin 誤宣稱圖已 render，需明確安裝相容 integration 或發布預先產出的 SVG。
- [x] Step 5：精確 commit `feat: build a static knowledge radar website`。

## Task K6: CLI、每日 Actions 與部署準備

**Files:** Create `src/radar/cli.py`, `scripts/state-sync.py`, `.github/workflows/{checks,collect,export-preview,publish}.yml`, `tests/{test_cli,test_state_sync}.py`；Modify config 與 `.gitignore`。

**Interfaces:** `python -m radar.cli collect --config config --state PATH`；`validate --state PATH`；`export --state PATH --output PATH`。success=0、配置/schema/state 錯誤=2、全部 enabled sources failed=3；部分來源失敗為0但寫 degraded report。`state-sync.py load/persist --checkout PATH --expected-sha SHA` 使用 Git subprocess argument array。

- [x] Step 1：CLI fixture 測試兩次 collect 一致、全失敗保存健康狀態但 exit3、破損 state 不覆寫。state sync 測本機 temp Git remote：head 改變則 persist 拒絕，不 force push。
- [x] Step 2：pytest 指定兩個測試檔，確認 FAIL。
- [x] Step 3：實作 CLI、專用 orphan `pipeline-state` branch（snapshot/health，不含 source code）、load/persist CAS。collect 設 `concurrency: pipeline-state`、`cancel-in-progress: false`，每日／manual 共用。全部失敗時仍保存健康資訊但不發布新內容；state persist 成功前不發布。PR checks 不用任何外部 secrets，禁止 pull_request_target 執行不可信程式。
- [x] Step 4：publish default disabled，`PUBLISH_ENABLED`、export repo、URL/base 與 `PUBLIC_EXPORT_TOKEN` 未設定就只產 artifact。跨 repo token 只給指定 export repo contents write；export repo 僅提交已驗證靜態輸出 `.nojekyll`，Pages source 由 wizard 設為核准分支/root，不複製 private source history。無 diff 不 commit。與來源 repo 同一 job 明確串接，不靠 GITHUB_TOKEN push 觸發另一 workflow。
- [x] Step 5：Python 全測試＋site checks/build/smoke PASS；Git fixture 恢復測試 PASS；檢查 Actions 權限：collect contents write、checks contents read、publish 無廣泛 org 寫入。Sol 審查 state CAS、發布條件與 secrets。遠端 run 尚未設定時標為未驗證，不能宣稱排程已啟用。
- [x] Step 6：精確 commit `feat: automate durable daily collection and export previews`。

## Task K7: 可重跑的 GitHub 設定 wizard

**Files:** Create `scripts/setup/github.sh`, `docs/platform-design/setup-github.md`, `tests/test_wizard.py`。

**Interfaces:** `bash scripts/setup/github.sh`；支援 `--check`（只讀）與 resume；state 位於 `.build/setup-state.json` 且無 secret。使用 wizard skill 的 template library，從 STAGES 以下定義本專案階段。

- [x] Step 1：用假 gh executable 測「未登入不寫 secret」「取消不啟用 publish」「resume state 無 token」「--check 不建 repo／push／付費」。測試讀假 stdin，不用真 token。
- [x] Step 2：pytest FAIL 後實作：確認 source visibility→選 export repo/網址/base→登入 gh→讀取 repo與Pages設定→顯示 export manifest 預覽→讓人啟用外部發布→hidden read token 並 stdin 寫 `PUBLIC_EXPORT_TOKEN`。初始 commit、repo 建立與 Pages 啟用只在顯示具體變更後操作；不擅自變更 source repo visibility。
- [x] Step 3：`bash -n scripts/setup/github.sh`、shellcheck（可用時）、pytest PASS；無 shellcheck 記錄工具限制。操作說明涵蓋 token 到期、Pages 公開性、schedule延遲與手動補跑。
- [x] Step 4：本機首次 collect→export→build 驗收；外部發布需人類配置及預覽確認。精確 commit `feat: guide GitHub setup without exposing secrets`。

## Execution Status

2026-10-08：K1–K7 本機交付與驗收完成，整體審查三項 Important 已修正並通過 43 個 Python 測試及兩種 base 路徑瀏覽器驗證；遠端帳號設定、排程與公開部署尚未執行，見 [執行紀錄](../../platform-design/execution-log.md)。

## Completion / Handoff

K1–K7 accepted 後，本機可用是第一個交付點；遠端排程／公開部署另記 configured 或 unconfigured。交付來源清單、export manifest、預覽、執行證據與剩餘外部設定。下一計劃只引用此處已固定的 API，不自行重命名。

官方查核（2026-10-08）：[Astro 安裝與 Node 最低版本](https://docs.astro.build/en/install-and-setup/)、[Starlight 入門](https://starlight.astro.build/getting-started/)、[Astro Pages site/base](https://docs.astro.build/en/guides/deploy/github/)。官方部署範例僅參考；本計劃隔離 source/export repo，因此不得直接套用把 source repo 全量公開的範例。

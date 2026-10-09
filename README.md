# AI Workflow Radar

每天收集 AI 開發與 Android 工程的原始更新，去重後生成靜態網站。每日不呼叫模型；AI 雙週整理可產生未核准審閱草稿，預設停用；本 repo 是公開作品集，因此程式碼、Git 歷史及已提交草稿都會公開可見。已提供版本化 Android 技能包與評測契約，仍為候選版本，Android 實測待接。

## 本機啟動

需要 Python 3.12+、Node 22.12+ 的受支持偶數版本。

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m pip install --no-deps -e .
npm --prefix site ci
.venv/bin/python -m radar.cli collect --config config --state .build/live/snapshot.json
.venv/bin/python -m radar.cli export --config config --state .build/live/snapshot.json --output .build/export
.venv/bin/python scripts/build-site.py --export .build/export --site site
npm --prefix site run build
npm --prefix site run preview
```

瀏覽 `http://localhost:4321`。資料已建立後可用 `npm --prefix site run dev` 修改畫面；Astro在agent環境可能自動背景執行，需前景模式時加 `-- --ignore-lock`。沒有完成export，網站不會直接讀公司docs作為fallback。

如果不想連網，可用下面的 synthetic fixture 跑測試網站；它只供測試，不能當真實成功案例。

## 驗證

```bash
.venv/bin/python -m pytest -q
.venv/bin/python tests/site_fixture.py
.venv/bin/python scripts/build-site.py --export .build/smoke-export --site site
npm --prefix site run check
npm --prefix site exec -- playwright install chromium
npm --prefix site run build
npm --prefix site run test:smoke
SITE_BASE=/ai-workflow/ npm --prefix site run build
SITE_BASE=/ai-workflow/ npm --prefix site run test:smoke
bash -n scripts/setup/github.sh
```

Browser smoke預期synthetic fixture，測試後重新export/build可回到live資料。GitHub checks固定相同流程並安裝Linux瀏覽器依賴。`npm audit`檢查前端依賴；目前對PostCSS間接依賴使用已修正版本的override，升版時需一起驗證。

## 設定與發布

先閱讀 [GitHub 設定流程](docs/platform-design/setup-github.md)，再執行：

```bash
bash scripts/setup/github.sh --check
bash scripts/setup/github.sh
```

公開發布預設停用。公開作品集原始 repo 同時承載網站；GitHub Actions 只部署核准 export 產生的靜態輸出，不把原始 `docs/`、`content/private/` 或 pipeline state 複製到網站。repo 本身與 Git 歷史仍對所有人可見。Wizard 不會推送本機分支；設定完成後才由你推送並啟用部署。

## 雙週 AI 整理

設定與恢復見 [AI設定指南](docs/platform-design/setup-ai.md)。先用 enrich --dry-run 看gate與預算；真實付費需要 --allow-paid、AI_ENABLED=true及durable Git checkpoint。公開 repo 中的 AI 草稿 PR、原始結果與 state branch 都可被閱讀。

## 内容與來源

- `config/sources.yaml`：10個已查核GitHub release來源；也支持RSS/Atom、選配YouTube uploads metadata。
- `content/inbox/links.json`：手動加入HTTPS連結，只進待審核收件匣，不自動抓陌生網站。
- `content/public/`：frontmatter同時標 `visibility: public` 和 `review_state: approved` 才匯出；禁止symlink、raw HTML及指向非核准檔案的本機連結。附件只接受 workflow catalog 明列且通過來源／授權／hash驗證的生成ZIP，不匯出任意檔案。
- `content/private/`、`docs/`：不供公開網站讀取；由於作品集 repo 公開，已提交在這些路徑的內容仍可從 GitHub repo 瀏覽。
- `pipeline-state`：遠端專用branch存snapshot；本機snapshot位於忽略的`.build/`。不要以artifact/cache替代它。

資料包含原始發布、最後成功抓取、最近嘗試等不同時間；來源失敗不清空舊資料。GitHub release來源不涵蓋作者所有文章或產品功能，來源廣度需之後持續擴充。

## 設計與進度

[架構設計](docs/platform-design/2026-10-08-android-ai-workflow-platform-design.md) · [執行入口](docs/superpowers/plans/2026-10-08-ai-workflow-execution-index.md) · [執行紀錄](docs/platform-design/execution-log.md)

## Android 工作流與雲端設定時序

[雲端帳號時序](docs/platform-design/cloud-account-timing.md) · [評測 runbook](docs/platform-design/evaluation-runbook.md) · [上游與再散布政策](docs/platform-design/upstream-policy.md)

網站 `/workflows/` 提供0.1.0文件包、0.2.0技能包及SHA-256。公司profile不提供公開下載；真實Android報告與採納決策待接，fixture不會升級candidate。

## AI 應用工程師 / FDE

網站 `/fde/` 提供 12 節點能力樹與 12 週路線、企業交付/RAG/可靠任務/資料分析與訓練準備指南，以及有版本/hash 的自有 skills ZIP；`/fde/updates/` 分開顯示免費原始更新和人工核准精選。18 個官方來源每日免費收集；Android/FDE 共用 14 天付款帳本，AI 預設停用、USD 0.50/批與 USD 2/月，不因新增領域另扣一批。

本機 labs：`python -m pip install -e examples/fde/python` 後用 `python -m fde_lab.cli rag-demo --state-dir .build/fde-labs/rag`、`jobs-demo --state-dir .build/fde-labs/jobs`、`dataset-demo --state-dir .build/fde-labs/data`。全是合成 fixture，不宣稱模型品質或企業成功案例。API/worker 與 PostgreSQL 參考見 [部署 runbook](examples/fde/deploy/README.md)；Java 對照見 [Spring Boot](examples/fde/spring-api/README.md)。PostgreSQL 測試只在明確提供 `FDE_TEST_POSTGRES_DSN` 的獨立測試 DB 執行，會建立/刪除測試 schema，不使用正式 DB。

最後用 `bash scripts/setup/fde.sh --check` 唯讀驗證；互動入口 `bash scripts/setup/fde.sh` 分 local/github/provider/api-db/gcp/health。GCP 階段只保存非敏感 refs 並列出 dry-run 命令，尚未建立雲端資源；真正部署、模型品質、效能與客戶驗收仍需另完成。[執行證據與設計判斷](docs/platform-design/fde-execution-log.md)。

FDE labs 修正版為 0.3.0；0.2.0 已停用但保留原 ZIP/hash。修正 embedding profile 並行、取消與未決外部呼叫、input近重複及validation/holdout時間邊界。跨領域批次至少2筆，低於此值拒絕整理，不會增加付費。

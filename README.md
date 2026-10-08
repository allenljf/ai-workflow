# AI Workflow Radar

每天收集 AI 開發與 Android 工程的原始更新，去重後生成靜態網站。每日不呼叫模型；AI 雙週整理與工作流技能包屬於後續 A／W 階段。

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

公開發布預設停用。原始repo應保留私有；獨立匯出repo只包含靜態輸出，沒有原始docs/history。此階段沒有自動push、部署或使用付費AI。

## 内容與來源

- `config/sources.yaml`：10個已查核GitHub release來源；也支持RSS/Atom、選配YouTube uploads metadata。
- `content/inbox/links.json`：手動加入HTTPS連結，只進待審核收件匣，不自動抓陌生網站。
- `content/public/`：frontmatter同時標 `visibility: public` 和 `review_state: approved` 才匯出；禁止symlink、raw HTML及指向非核准檔案的本機連結。第一版不接受任意附件。
- `content/private/`、`docs/`：不供公開網站讀取。
- `pipeline-state`：遠端專用branch存snapshot；本機snapshot位於忽略的`.build/`。不要以artifact/cache替代它。

資料包含原始發布、最後成功抓取、最近嘗試等不同時間；來源失敗不清空舊資料。GitHub release來源不涵蓋作者所有文章或產品功能，來源廣度需之後持續擴充。

## 設計與進度

[架構設計](docs/platform-design/2026-10-08-android-ai-workflow-platform-design.md) · [執行入口](docs/superpowers/plans/2026-10-08-ai-workflow-execution-index.md) · [執行紀錄](docs/platform-design/execution-log.md)

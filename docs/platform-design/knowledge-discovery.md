# 工作流知識總覽：雙週搜尋、修訂與發布

實作日期：2026-10-09。以既有 Git state、共同模型帳本與核准匯出流程擴充，不部署 GCP／DB。

## 資料流

1. 每週一09:17收集既有 releases；另有每日09:47免費 due check 只讀狀態，不收集、不搜尋、不呼叫模型。避免週排程比上次完成時間早數分鐘而把14天間隔延為21天。探索啟用時不要求有新 release。
2. AI／有效價格／14天到期／預算 gate 通過後，paid enrichment 先執行 Tavily 開放搜尋。`config/knowledge.yaml` 目前4個主題，涵蓋新工具與新觀念；無廠商網域限定。
3. 每個查詢先保存 durable reservation 至 `pipeline-state/knowledge-discovery.json`，basic search、關閉 auto_parameters、最多5個結果，要求 raw_content。每月最多12次預約。無key或不確定失敗不呼叫模型；calling／ambiguous 狀態不自動重試，需要人工核對搜尋帳單後處理。
4. 按 canonical URL 去重，保留文字和片段證據等級。候選與原始更新一起送入現有單次 DeepSeek batch，附上最新核准總覽。共用 US$0.50／批與 US$2／月模型帳本；搜尋 credits 是獨立費用。
5. 回傳 stories 與最多5個 landscape_updates。修改指向既有章節或「新觀念」新章節；quote需匹配輸入文字、連結需指向提供的來源。這是可追溯校驗，不能代替作者身份或事實查核。
6. 同一公開 PR 提供 digest、新來源候選與完整 landscape 草稿。候選不自動加入訂閱，未修改章節原封保留。抓取日不冒充全面查核日。
7. 人工審閱後以核准腳本生成公開版本，baseline hash防止覆寫較新的人工修改。公開內容合併main觸發 `publish-reviewed.yml`，不重新抓來源、不呼叫AI。

## 初次上站

`content/public/knowledge/index.md`整理研究README索引；`landscape.md`沿用2026-10-08報告，原docs日期快照不改。歷史素材連到公開repo，網站只匯出核准內容。`/knowledge/`提供導覽、下載與日期；全文在`/guides/knowledge/landscape/`。

## 設定

先推送程式到main，再設定AI wizard。Secrets：DEEPSEEK_API_KEY、TAVILY_API_KEY；Variables：AI_ENABLED=true、KNOWLEDGE_DISCOVERY_ENABLED=true、有效AI_PRICE_POLICY、模型預算。API key不得放Variables。

```bash
bash scripts/setup/ai.sh
bash scripts/setup/knowledge.sh allenljf/ai-workflow
```

上述設定可能啟用之後的付費；knowledge wizard本身不呼叫API。AI wizard有另行詢問首次付費。價格政策持續有效，直到手動修改；無有效價格不使用搜尋額度。

手動跑週收集（可能在gate通過後dispatch付費）：

```bash
gh workflow run collect.yml --repo allenljf/ai-workflow --ref main
```

只檢查AI gate，不使用搜尋或模型：

```bash
gh workflow run enrich.yml --repo allenljf/ai-workflow --ref main -f allow_paid=false
```

## 審閱並發布

checkout該digest PR，讀取內容、引用與候選來源；沒有證據的段落不要核准。核准總覽：

```bash
.venv312/bin/python scripts/approve-landscape.py --draft content/drafts/landscape-<batch-id>.md --approve
```

再把 `content/public/knowledge/landscape.md` 提交到PR。Digest另外移至content/public/digests，設定visibility: public、review_state: approved、reviewed_at。合併到main後自動建置發布。不合併草稿就當作已核准。

## 限制

搜尋服務可能未取得全文；廣泛搜尋也不保證涵蓋所有新工具。主張的quote吻合不證明真實；模型不得把關注度當市佔。新來源由人查核並納入設定。每週收集後按config/retention.yaml封存180天以前資料，保護待審與未決證據及每個來源最新一筆；網站顯示近90天。Git歷史仍累積；搜尋候選本輪最多30筆，批次證據與費用紀錄保留。

全部排程、頁面用途與更新時機見 [網站運作說明](../../content/public/site/operations.md)。

本輪只使用MockTransport與合成provider驗證，不使用真人API token，不執行付費搜尋或模型，不變更雲端帳號，不推送部署。遠端首次執行、provider最新模型契約與效果仍需實際配置驗收。

[一手API與歷史證據](../agentic-workflow-research/research/2026-10-09-knowledge-discovery-source-notes.md)

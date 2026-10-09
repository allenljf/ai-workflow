---
title: 網站自動排程、頁面用途與更新時機
visibility: public
review_state: approved
---

# 這個網站如何持續運作

網站是 GitHub Pages 靜態網站。GitHub Actions 在雲端按排程執行 Python，將資料保存至 Git 分支，再由 Astro 產生 HTML 與下載檔。訪客瀏覽不呼叫 AI、不即時搜尋，也不需要 GCP 或資料庫。電腦關機不影響 GitHub 上的排程。

本文描述程式部署並完成設定後的行為。API key 已設定，不等於 AI 已啟用；本機改好也不等於遠端已部署。頁面顯示的是最近一次建置時的狀態，可能落後最新一次排程。

## 自動排程與觸發條件

下列時間均為台灣時間 Asia/Taipei。研究間隔預設14天，可用GitHub Variable `AI_INTERVAL_DAYS` 調整；修改方法見repo README。GitHub 排程可能延遲或漏跑；週期是目標，不是準時服務保證。

| 排程／觸發 | 自動行為 | 產物與發布 | 外部 API 費用 |
|---|---|---|---|
| 每週一 09:17：`collect.yml` | 查啟用的來源、比對前次資料、去重、記錄成功／失敗；按保留規則封存舊資料 | 保存 `pipeline-state`，成功後建置網站；`PUBLISH_ENABLED=true` 才部署 Pages | 收集本身不呼叫模型或搜尋服務；若到期可另派發付費研究 |
| 每天 09:47：`enrichment-due.yml` | AI 啟用時讀取帳本，免費檢查到期、有效價格與預算；未啟用直接略過 | 不更新來源、不搜尋、不建置網站；符合條件才派發 `enrich.yml` | 到期檢查沒有搜尋／模型費 |
| 上次成功整理後至少 14 天：`enrich.yml` | 需要 AI 啟用、有效價格、預算與憑證。探索開啟時，先搜尋新觀念／新工具，再與舊總覽及已知來源更新一起分析 | 單次 DeepSeek 批次產生精選、總覽修訂與新來源候選，提交公開 PR；不自動核准 | Tavily credits 與 DeepSeek tokens 分別計算 |
| 核准公開內容或網站程式合併 `main`：`publish-reviewed.yml` | 讀取現有資料、匯出核准文件、建置 | 依發布開關部署；總覽／指南與下載檔一起更新 | 不重新收集、不搜尋、不呼叫模型 |
| push、PR 或手動：`checks.yml` | Python 測試、網站檢查、建置與瀏覽器測試 | CI 結果；不是內容發布 | 不呼叫真實模型／搜尋 API |
| 手動：`export-preview.yml` | 用現有資料建立預覽 | `radar-preview` artifact 保留 7 天，不部署正式網站 | 不呼叫模型／搜尋 API |

資料更新與核准內容建置共用同一排隊鎖，避免同一程式版本匯出不同時刻的資料並互相覆蓋。發布前會比對建置版本與目前 `main`；已過時的網站產物會略過，避免並行發布把較新的核准內容覆蓋。

每日檢查僅避免「上次整理在週一09:20完成，但兩週後09:17仍差三分鐘而多等一週」；原始來源仍每週更新。沒有新 release 也可以做新來源探索。有未決付費結果時停止新研究，不自動重試。

## 每個頁面負責什麼

以下為站內路徑；GitHub Pages 會自動加上 `/ai-workflow/` 前綴。

| 頁面 | 顯示資訊 | 什麼時候內容改變 |
|---|---|---|
| `/` 最新知識 | 已訂閱來源的原始更新、版本、時間、引用、主題篩選；最近90天，每頁24筆 | 每週收集成功並部署後；未經 AI 深入分析，不視為核准建議 |
| `/sources/` 來源狀態 | 每個來源最後嘗試、最後成功、失敗或延遲 | 每週收集並部署後；失敗保留舊資料，不冒充成功 |
| `/knowledge/` 知識總覽入口 | 目前核准版、基準查核與核准日期、研究索引、MD下載、AI／探索狀態 | 總覽核准合併後；狀態隨下次建置更新 |
| `/guides/knowledge/landscape/` | Superpowers、Matt Pocock、SDD、harness、loop、graph、Mods 等總覽，以及核准的新觀念／工具 | 雙週研究先提出草稿；人工核准並合併後才更新 |
| `/guides/knowledge/` | 原研究 README 的主題索引、手冊與歷史來源入口 | 研究索引經修改、核准、合併後；舊研究不自動標成今天查核 |
| `/digests/` 雙週精選 | 人工核准的 AI 精選、整理日期、審閱日期、模型與來源 | 精選移至公開區、補齊核准資訊並合併後 |
| `/workflows/` 工作流 | Android 開發工作流、候選版本、使用指南、版本化 skills ZIP 與 SHA-256 | 工作流與技能包經更新、驗證、核准並合併後；上游新版本不會直接改寫本站套件 |
| `/fde/` AI 應用工程師 | 技能樹、學習路線、企業交付、RAG／Local模型／資料／部署指南與技能下載 | 指南或技能版本經核准並合併後；新工具研究可先提出修訂建議 |
| `/fde/updates/` | FDE 相關原始更新、核准精選及全站研究狀態 | 原始資料每週更新；精選核准後更新；共用模型批次與預算 |
| `/guides/` 使用指南 | Android／FDE／研究與運作說明的全文及搜尋 | 核准文件或網站功能合併並部署後 |
| `/guides/site/operations/` 本頁 | 全部排程、頁面用途、保留與費用規則 | 排程或行為修改後，同步修改說明並部署 |
| `/downloads/…` | 與核准文件對應的 Markdown、版本化技能 ZIP | 同一次網站建置產生；草稿不放進下載區 |

雙週研究不是直接讓網頁上的文字全部自動重寫。研究會提出可檢視的修改；審閱尚未完成時，讀者仍看到最後核准版。

## 如何發現原本不知道的工作流

目前啟用的是18個 GitHub Releases 來源。RSS／Atom 與 YouTube 收集器已提供，但尚未設定訂閱；Threads 目前沒有專用收集器。開放搜尋可發現搜尋引擎收錄的網站與公開貼文，但不能保證涵蓋所有平台，也不代表已觀看影片或讀取登入後內容。新增訂閱仍須先核對來源與取得方式。

固定來源解決「已知工具最近改了什麼」；Tavily 開放搜尋解決「有哪些原本不知道的工具與工程思維」。查詢在 `config/knowledge.yaml`，涵蓋驗證、context、長任務、恢復、規格、task graph、loop、新工具，以及主要模型的官方發布、API能力、基準與價格；搜尋不限制在既有廠商網域。

搜尋要求取得原文文字；無原文時只保留片段標記。候選按 canonical URL 去重；不因多篇文章提到同一概念，就當成多個新工具。搜尋時間、來源日期、實際取得的證據與人工查核日期分開。搜尋日期可能由服務估算，不能直接當成工具發明日期。

同一模型批次讀取目前總覽與新證據，提出最多5個章節修訂或「新觀念」章節。引用需對上提供的來源文字與URL；引用吻合仍不代表主張真實或廣泛採用。候選來源經人工核對才加入永久訂閱，不自動安裝工具或修改公司工作流。

## 沒有資料庫怎麼保存資料

| 資料 | 儲存位置與保留方式 |
|---|---|
| 原始收集與來源健康狀態 | `pipeline-state/snapshot.json`；運作資料保留最近180天 |
| 舊事件／修訂 | `pipeline-state/archives/YYYY-MM.json` 按月封存，日常建置不載入 |
| 待審、未決或尚在處理的批次證據 | 不受180天清理影響；每個來源最新一筆也保留在運作資料中 |
| 網站原始更新列表 | 只匯出最近90天；有來源發布／更新時間時優先採用；缺少日期時才使用抓取時間 |
| AI 結果、費用與去重帳本 | 保留在 state branch，避免重複付費；原始修訂證據不因首頁清理而刪除 |
| 核准指南、總覽與技能包 | `main` 的公開內容與版本紀錄；原日期研究快照保留 |
| CI 預覽與網站 artifact | 預覽／`radar-site` 保留7天；不是持久資料來源 |

保留期限在 `config/retention.yaml`。封存能縮小活躍 JSON 與網站輸出，**不會縮小 Git 的歷史容量**。資料長期變大後再評估物件儲存或資料庫；不會自動重寫 Git 歷史或刪除已發布知識。

## 哪些設定與費用需要注意

| 設定 | 放在哪裡 | 用途 |
|---|---|---|
| `DEEPSEEK_API_KEY` | GitHub Actions Repository Secret | 模型整理 |
| `TAVILY_API_KEY` | GitHub Actions Repository Secret | 開放搜尋 |
| `AI_ENABLED` | Repository Variable | 是否允許模型批次；預設false |
| `KNOWLEDGE_DISCOVERY_ENABLED` | Repository Variable | 是否在批次中進行開放搜尋；預設false |
| `AI_INTERVAL_DAYS` | Repository Variable | 研究／搜尋間隔，預設14天，可設1～365天 |
| `AI_PRICE_POLICY` | Repository Variable | 手動設定的模型與價格；不含token、沒有自動到期 |
| `AI_MAX_BATCH_USD`／`AI_MAX_MONTHLY_USD` | Repository Variables | 模型預算，預設US$0.50／批與US$2／月 |
| `PUBLISH_ENABLED`、`SITE_URL`、`SITE_BASE` | Repository Variables | Pages發布開關與網址 |

目前設定每輪4個 basic 搜尋，每個最多5筆結果；程式最多允許每輪6個查詢、每月12次搜尋預約。搜尋點數與模型美元預算是兩個不同帳本；供應商額度或帳單才是實際費用依據。

價格設定持續有效，直到你手動修改；不定期要求重新輸入，也不由AI自動修改價格。預算估算沿用你設定的單價，供應商實際帳單可能不同。缺少key、預算不足、搜尋不確定或模型不確定時也會暫停研究；不是網站壞掉。

公開 repo 標準 GitHub runner 分鐘與 Pages 通常免費，但儲存、流量與第三方API有額度。額外GCP、DB、搜尋付費方案、自訂網域可能另外收費。網站不需要先部署GCP才可運作。

## 設定與人工發布步驟

DeepSeek Secret 已有時，AI wizard直接沿用；Tavily Secret 已有時也會沿用。互動步驟需要你查核服務方案、價格與是否允許之後付費，腳本不把API key寫入repo。

```bash
bash scripts/setup/ai.sh
bash scripts/setup/knowledge.sh allenljf/ai-workflow
```

先將程式推送至main，遠端才有新排程。修改repo變數不會自動發布本機程式。

研究PR中先查核總覽、引用與候選。總覽核准工具會拒絕覆寫較新的基準；精選另外移至公開目錄，設定核准資訊。核准內容合併後觸發網站建置。公司內部採用與Android真實實測仍需自己的驗收，不能由網站研究代替。

[知識總覽](../knowledge/landscape.md) · [探索與審閱政策](../knowledge/update-policy.md) · [研究入口](../knowledge/index.md)

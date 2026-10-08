# FDE／AI 應用工程師：學習路線與交付技術調研

查核日：2026-10-08，Asia/Taipei。讀者：已有軟體開發經驗，想以 Python、Java Spring Boot、雲端與 AI 解決企業問題的工程師。

本文是第一方資料調研與本平台建議；網站、技能包與 labs 尚待實作。下面的程式流程是設計藍圖，未執行，不是生產範例或模型效果證據。動態文件以查核日為準，沒有發布日期者不推測日期；產品存在、雇主需求、論文結果與業界普及率是不同證據。

## 1. 業界需要什麼能力

OpenAI 的 FDE 職缺要求從原型到穩定 production 的交付、全端程式、客戶合作、範圍取捨與可重用模式。這支持把需求與工程交付放在學習主線。[OpenAI FDE UAE](https://openai.com/careers/forward-deployed-engineer-uae-abu-dhabi-uae/)

Anthropic 的 FDE 職缺強調 Python、正式應用交付、組織間協作、探索客戶問題與溝通；企業 IT／AI 部署與特定產業經驗也是加分項。[Anthropic FDE](https://job-boards.greenhouse.io/anthropic/jobs/5423029008)

Palantir 的 FDSE 從模糊業務問題出發，做系統設計、應用與資料整合，持續接受客戶回饋；其技術列有 Python、Java、資料庫與雲端。這個職缺包含特定政府領域要求，不能當作所有 FDE 的資格清單。[Palantir FDSE](https://jobs.lever.co/palantir/a39bf84c-6648-4871-bd07-9b882d401c4c)

**本平台推論：** FDE 是企業現場的需求、工程與交付角色。上述三個雇主樣本不足以估計市場占比，也沒有要求所有人先自行訓練大模型。建議先練一個可驗收、可恢復、可交接的企業解決方案，再增加新框架。

## 2. 能力樹與參考路線

以下 12 週是本平台建議，依能力門檻調整，不是國際職涯標準。

| 階段 | 技能與前置依賴 | 作品與驗收 |
| --- | --- | --- |
| 1–2 週：需求、API、資料 | stakeholder 訪談、baseline、HTTP/OpenAPI、SQL、transaction、資料權限 | 一頁需求契約；合成資料匯入；API schema、重複請求與權限測試 |
| 3–4 週：模型與檢索 | structured outputs、tool calling、context、chunking、引用；依賴資料/API | 文件助理；相同題集比較長 context 與 RAG；無證據拒答 |
| 5–6 週：評測、本機模型 | golden/holdout、failure taxonomy、local inference、成本與延遲 | retrieval/answer 分別評測；fixture 與真模型結果分開 |
| 7–8 週：可靠任務 | state machine、checkpoint、lease、retry、idempotency、取消；依賴 transaction | 中斷恢復、重複 delivery、timeout、外部結果不確定的測試 |
| 9–10 週：雲端與資料分析 | container、IAM、Secrets、DB migration、排程、資料品質／切分 | 部署契約與 dry-run、backup/restore；資料品質報告；微調準備為選修 |
| 11–12 週：完整交付 | pilot、變更管理、rollback、runbook、support ownership | capstone：企業文件/工單處理、API、eval、故障演練與交接包 |

技能可分 12 節點：需求交付、API/backend、資料/DB、模型整合、RAG、local inference、eval/observability、durable tasks、cloud/scheduling、資料分析、訓練適配、production handoff。每節點需包含前置依賴、用途、第一方來源、查核日、練習與完成門檻。

Python 適合資料、檢索與 worker；Spring Boot 適合既有 Java 企業系統整合。語言依團隊能力選擇，不要求同一功能同時維護兩套正式系統。

## 3. 現代模型的 RAG 與長 context

長 context 與 RAG 的選擇要測資料覆蓋、更新頻率、權限、引用、成本與延遲。2024 年 RAG/long-context 研究提出混合路由；它是當年的模型與資料集證據，不能直接代表 2026 年模型。[EMNLP 2024 論文](https://aclanthology.org/2024.emnlp-industry.66.pdf)

Anthropic 的 Contextual Retrieval 使用 chunk 上下文改善檢索，結合文字與向量檢索及 reranking。文章發布於 2024-09-19，仍可作技術基礎；其中 benchmark 的改善幅度不能直接套到本公司的資料。[Contextual Retrieval](https://www.anthropic.com/engineering/contextual-retrieval)

| 情境 | 建議先測 | 需要驗證 |
| --- | --- | --- |
| 少量文件、需整份推理 | 授權文件的長 context baseline | 超長截斷、不同位置的資訊、成本、更新與引用 |
| 大量且持續更新的企業文件 | metadata/ACL filter＋RAG | 遺漏、版本混用、跨 tenant、查無資料 |
| 專有名詞、料號、精確字串與語意混合 | 文字＋dense retrieval、fusion | 不同 query 類型的 recall；增加成本是否合理 |
| 第一階段召回多且噪音高 | reranking | retrieval 與答案改善、延遲、權限不洩漏 |
| 離線、敏感或成本受限 | local inference＋同一評測題集 | RAM/VRAM、併發、context、模型授權與真實品質 |

pgvector 支援 exact 與近似向量索引，可搭配 PostgreSQL full-text 做 hybrid；原生 full-text 不應直接稱為 BM25。Qdrant 提供 prefetch/query 的多階段 hybrid 機制，選型需按資料與維運需求實測。[pgvector](https://github.com/pgvector/pgvector)、[Qdrant hybrid](https://qdrant.tech/documentation/search/hybrid-queries/)

**建議實作順序：** 合成文件 → SQLite FTS baseline → 授權檢索與引用 → 選配 embedding → 長 context/RAG 對照 → 有失敗證據再加 hybrid/reranking。PostgreSQL＋pgvector 是服務化方向；Qdrant 留作對照，不一開始部署兩個向量 DB。

檢索前就套可信 caller 的 tenant/ACL。資料庫可用 row security，但仍需正確 role/policy 與隔離測試；模型 prompt 的 tenant 描述不能取代授權。[PostgreSQL row security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)

## 4. Local 模型與模型整合

Ollama `/api/embed` 接受文字並回傳向量；`truncate` 預設為 true，因此 lab 應明確選擇截斷策略，不能把截斷後結果當完整文件表示。索引記錄模型識別、digest、維度与資料版本，避免不同 embedding 混寫。[Ollama embed](https://docs.ollama.com/api/embed)

Structured outputs 可用 schema 約束形狀，收到後仍做型別、引用、權限和業務檢查；格式合法不能證明答案正確。[Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs)

vLLM 是服務化候選，需另查固定版本的模型、硬體和 API 相容性。本次其 rolling 文件入口重導後未取得內容，因此不採用未驗證的啟動命令或版本能力；實作前重新查核。[vLLM 官方文件入口](https://docs.vllm.ai/)

工具與 MCP 用來連接企業能力，需對每個工具限制輸入、權限與副作用。MCP transport authorization 與業務資源授權仍分層處理，不能因工具被發現就允許全部操作。[官方 MCP authorization 規格原始資料（2025-06-18 版）](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2025-06-18/basic/authorization.mdx)

## 5. Evals 與可觀測性

Anthropic 2026-01-09 的 agent eval 工程文討論多種 grader 與任務軌跡／結果。依此建議把 deterministic checks、人工判讀與經校準的 model judge 組合；單一評分不能覆蓋全部失敗。[Demystifying evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)

本平台建議分開記錄：

- Retrieval：授權結果、正確文件召回、最新版本、沒有答案的題目。
- Answer：引用可追溯、unsupported claims、schema 與業務正確性。
- Jobs：成功率、中斷恢復、重複副作用、ambiguous cases、取消與期限。
- Delivery：人工修正分鐘數、p95 latency、每成功任務成本、採用率與 rollback。

先記 baseline 與 acceptance criteria，再比較新模型／新 workflow。保留 dataset hash、程式 commit、provider/model、參數、時間與 artifact hash；零執行、fixture-only、stale artifact 都不能標成企業實測。

Spring AI 有 RAG 與 observability 接口，可作 Java 對照；實作時固定相容 Boot/BOM，觀測不得把企業原文與秘密直接公開。[Spring AI RAG](https://docs.spring.io/spring-ai/reference/api/retrieval-augmented-generation.html)、[Observability](https://docs.spring.io/spring-ai/reference/observability/)

## 6. 長任務、自我恢復與排程

Cloud Scheduler 是 at-least-once delivery，可能重複。Cloud Run Jobs 文件要求持久保存中間成果及設計 idempotent 工作；該頁更新日為 2026-10-07 UTC。[Scheduler](https://docs.cloud.google.com/scheduler/docs/overview)、[Run Jobs retries/checkpoints](https://docs.cloud.google.com/run/docs/jobs-retries)

Temporal 提供持久執行的機制與 SDK，適合需要中斷恢復、多步驟與長等待的流程；事件歷史與 replay 是學習重點。外部副作用仍需幂等策略，不可推論任意網路動作都 exactly-once。[Temporal AI](https://docs.temporal.io/ai)、[Event history](https://docs.temporal.io/encyclopedia/event-history)、[Python SDK](https://docs.temporal.io/develop/python)

建議兩層學習：先以 SQLite 小型 worker 看清 checkpoint、lease、attempt/deadline 與 receipts；正式多日／多人 approval 用現成 durable engine。不要把每隔幾分鐘重跑完整 prompt 當作持久執行。

```text
queued → running（租約）→ succeeded
                ├→ retry_wait（暫時性且仍有 budget/deadline）
                ├→ failed（永久性／超過上限）
                ├→ ambiguous（外部是否成功無法確認）
                └→ cancelled（在安全 checkpoint 停止）
```

自我恢復限定為已授權狀態機內的恢復：重試讀取、重啟 worker、續跑完成前的步驟。外部扣費／寫入 timeout 先查 receipt，不確定時轉人工處理；不能無限重試、擴權或自行重寫程式。

Spring `@Scheduled` 可以排程，但多個 schedule／instance 可能並行；它不能代替分散式 lease 與去重。[Spring scheduling](https://docs.spring.io/spring-framework/reference/integration/scheduling.html)

## 7. 資料分析、訓練與適配

先分析資料契約、缺漏、duplicates、類別分布、時間與群組偏差。先切分資料再 fit preprocessing，避免 test 資訊進入訓練；pipeline 有助隔離 preprocessing。[scikit-learn pitfalls](https://scikit-learn.org/1.9/common_pitfalls.html)

本平台另建議對同客戶／同文件系列做 group split、對時間敏感業務做 time split；用 hash/lineage 檢查近重複及同源資料跨 split。保留未用來調 prompt 的 holdout，錯誤分桶後決定改資料、檢索、prompt、工具或模型。

| 問題 | 優先方向 |
| --- | --- |
| 不知道最新企業文件 | 更新資料與 RAG／context |
| tool schema／業務流程錯誤 | 契約、工具與 deterministic validation |
| 穩定格式／風格／特定任務仍不足 | 有足夠授權標註與 holdout 再評估 SFT |
| GPU／資料／評測不足 | 先做資料品質與訓練 dry-run，不啟動訓練 |

TRL `SFTTrainer` 支援 text、prompt/completion 與 conversational 格式，也能整合 PEFT adapters。微調配置要固定 tokenizer/chat template、loss scope、資料版本與驗收，不能只看 training loss。[TRL SFTTrainer](https://huggingface.co/docs/trl/en/sft_trainer)

PEFT 的量化指南介紹量化基座搭配 LoRA 的 QLoRA 方向。實際顯存依模型、序列長度、batch、optimizer 與硬體而變，不保證某一張卡適用所有模型。[PEFT quantization](https://huggingface.co/docs/peft/en/developer_guides/quantization)

第一階段僅做合成 dataset、品質報告、split manifest、訓練格式與 dry-run；取得資料使用權、GPU 與預算後再做受控訓練與獨立評估。未執行模型訓練，不宣稱性能改善。

## 8. 如何用程式組合企業解決方案

以下是自有設計藍圖，函式／repository 尚未實作，不可直接執行。

```python
# API 層先驗證身份，tenant 不是模型或 request body 指定。
principal = authenticate(request)
query = QuerySchema.validate(request.body)
chunks = repository.search_authorized(principal, query.text)
if not chunks:
    return {"status": "insufficient_evidence"}
answer = provider.generate(schema=AnswerSchema, evidence=chunks)
validate_schema_and_citations(answer, allowed_chunks=chunks)
return answer
```

工作 API 建議 `POST /jobs`、`GET /jobs/{id}`、cancel、`POST /rag/query`、`GET /health`。job 的唯一性至少包含 tenant＋idempotency key，且同 key 不同 payload 要拒絕。worker 使用 transaction 原子領取工作與 lease；checkpoint/receipt 在可恢復儲存內，過期 worker 用 fencing/version 檢查防止覆寫新 owner。

Java 版以 Controller 做 schema，可信身份映射 principal，Service 做權限和任務契約，Repository 做 transaction/unique constraints，Provider 做 fixture/local/選配 cloud。Python worker 與 Java API 共享契約與測試案例，不直接共享框架內部物件。

Spring AI 2.0.x 的官方 getting-started 資料列有 Boot 4.0.x／4.1.x 相容方向；實作時再核對固定穩定 release/BOM。當前也有 milestone release，不能把 rolling docs 或 milestone 當公司預設穩定版本。[官方相容性資料](https://github.com/spring-projects/spring-ai/blob/main/spring-ai-docs/src/main/antora/modules/ROOT/pages/getting-started.adoc)、[Spring AI releases](https://github.com/spring-projects/spring-ai/releases)

## 9. 雲端配置與 wizard 最後做

網站仍是公開靜態知識站；企業資料/API 是獨立私有服務。先本機 SQLite，服務化才加 PostgreSQL＋pgvector；使用 versioned migration、least privilege、TLS、backup/restore、資料 retention 與 tenant 隔離驗收。

GCP 選型：持續 HTTP 用 Cloud Run service，批次工作用 Jobs，Scheduler 觸發工作；需要多日等待與協作則 durable engine。Run Jobs 的排程有專門的 service account／IAM 配置。[Jobs on schedule](https://docs.cloud.google.com/run/docs/execute/jobs-on-schedule)

知識站沿用每日 GitHub Actions；它可能延遲／丟失，不能當企業準點 SLA，因此保存 last_success、next_due 與手動補跑入口。[GitHub scheduled events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)

wizard 在本機 labs 與契約完成後，分 local、GitHub schedule、provider、API/DB、GCP identity/secrets/schedule、health/rollback 階段；配置能 dry-run。帳號／token／計費只在選擇對應能力時需要。本輪沒有建立雲端資源、呼叫付費模型或更改帳號。

## 10. 持續取得新知識與雙週更新

| 來源層 | 查什麼 | 本平台使用方式 |
| --- | --- | --- |
| 官方 release/changelog | 版本、breaking changes、相容性 | 每日免費收集、去重；新增 topic 不重抓同 repo |
| 官方工程文與 docs | 設計、限制、可靠性案例 | 人工查看全文、記查核日；提出有依據的技能變更 |
| 官方職缺 | 企業正在要求的交付能力 | 季度比較需求，不當市場統計 |
| 論文原文 | 實驗、資料、限制 | 追模型/資料集版本；做自己的 holdout 重驗 |
| YouTube／Threads | 新議題線索 | 人工或官方 API metadata；回查原始證據，不假裝看過影音全文 |

優先觀察 [Anthropic engineering](https://www.anthropic.com/engineering)、[Spring AI releases](https://github.com/spring-projects/spring-ai/releases)、[Temporal Python releases](https://github.com/temporalio/sdk-python/releases)、[pgvector](https://github.com/pgvector/pgvector)、[Qdrant](https://github.com/qdrant/qdrant)、[Ollama](https://github.com/ollama/ollama)、[vLLM](https://github.com/vllm-project/vllm)、[TRL docs](https://huggingface.co/docs/trl/en/index)。此處是候選 watchlist，正式 feed endpoint 的存在與解析結果在實作時驗證。

可重用的搜尋組合：

```text
site:anthropic.com/engineering evals agent long-running
site:docs.cloud.google.com/run jobs retries checkpoint
site:docs.temporal.io durable workflow idempotency
site:docs.spring.io/spring-ai RAG observability
site:github.com/pgvector/pgvector releases
site:huggingface.co/docs/trl SFT dataset
site:openai.com/careers "forward deployed engineer"
```

加入過去兩週時間篩選只用來找差量，遇到穩定基礎資料仍保留舊來源並標日期。每雙週依序：來源差量 → 同 story 合併 → 第一方全文查核 → 影響／相容性 → 代表任務測試 → 人工 approve → 發新版本與 changelog。

付費摘要仍預設停用；啟用時 FDE／Android 共用既有每批 USD 0.50、每月 USD 2 上限與同一持久財務 ledger，不另開隱藏預算。網站閱覽不即時呼叫 AI。14 天依持久 next_due，不用每月兩固定日期冒充雙週。

skill 先做兩個薄路由：`fde-solution` 與 `fde-knowledge-review`，詳細能力放 references／MD；新版先 candidate 與實測，再由人決定公司採納。热门 release 不直接覆寫已批准工作流。

## 11. 案例與證據界線

目前可支持的是雇主明列需求、官方產品機制與已發表研究。職缺不是客戶成功案例；廠商 benchmark 不是本公司品質證據。网站案例欄位應記問題、限制、baseline、方案、觀察指標、來源、證據種類與可移植限制。

首個 capstone 建議用合成企業工單／文件：資料匯入→授權檢索→有引用建議→人工確認→可恢復處理→報告／交接。它能覆蓋完整生命週期，但在真實企業 pilot 前只能標示教學範例。

## 12. 與本 repo 的落地設計

詳見 [FDE 平台設計規格](../../superpowers/specs/2026-10-08-fde-learning-hub-design.md)。推薦延伸現有靜態站、版本化技能目錄、來源去重、預算與 review；先網站/內容/技能包和本機 labs，再雙週更新，最後 wizard/API/DB/排程整合。

仍待驗證：vLLM 固定版本文件與硬體、本機模型真實品質、Java 固定依賴編譯、所有新 feed、cloud deployment、真實企業成效與 GPU training。本次調研沒有這些執行結果。

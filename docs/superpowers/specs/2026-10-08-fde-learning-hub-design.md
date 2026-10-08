# FDE／AI 應用工程師學習與交付平台：設計規格

日期：2026-10-08（Asia/Taipei）。狀態：**待使用者審閱；尚未開始產品實作**。
基線：W1–W4完成的 `4a91054`；本次分支 `codex/fde-learning-hub`。W分支尚未合併main，本設計延續其成果，不改原始未追蹤的公司docs。

## 1. 使用者目的與成功條件

使用者希望新增不限Android的網站篇章，協助AI應用工程師／Forward Deployed Engineer依企業特殊需求交付解決方案。需要最新且持續更新的學習路線、技能樹、知識來源、程式做法、技能查看／更新／下載；涵蓋雲端、API、資料庫、排程、校驗、長任務恢復、現代模型與Local RAG、資料分析與訓練。先完成本機，再更新wizard並整合API／DB／排程。

設計假設：讀者已有軟體開發經驗；以能解決企業問題為目標。Python是資料與worker主範例，Java Spring Boot提供企業API範例，不把某語言或框架當成FDE的必要資格。學習順序是本平台建議，不宣稱國際統一職涯標準。

完成本機交付後，使用者能：

- 從 `/fde/` 找到能力依賴、分階段路線、第一方依據與每階段可驗收的作品。
- 查看有版本、來源、查核日、適用情境、限制與狀態的skills與MD，下載自有包並核對SHA-256。
- 在無API token、無GPU、無雲端帳號模式跑出本機範例的實際測試，清楚區分fixture、local model觀察與企業實測。
- 以同一去重／持久化／預算／人工review流程處理Android與FDE雙週更新，來源每日免費蒐集，付費整理仍預設關閉。
- 最後使用wizard選擇本機或GCP部署，設定API／DB／排程；配置可dry-run和檢查，秘密不進git，不自動把公開網站變成企業私有資料服務。

## 2. 三種方案與選擇

| 方案 | 取捨 |
| --- | --- |
| **既有靜態網站＋版本化技能目錄＋獨立本機labs（採用）** | 沿用現有review／export，容易本機驗收；雲端worker與資料服務最後才接 |
| 新建全功能LMS／會員／雲端後端 | 有線上進度與多人管理，但增加帳號、維運與資料遷移，超過當前知識網站目的 |
| 只新增MD連結清單 | 變更小，但無技能依賴、可執行驗收、版本更新追溯，不能滿足交付能力培養 |

平台分兩個可獨立驗收的子項目：A「學習網站／技能與知識更新」；B「本機程式labs→API／DB／排程→wizard」。先A與本機B，最後才做雲端配置。雲端架構的操作計劃在本機測試完成後再依此契約展開，避免先建立不必要資源。

## 3. 學習篇章與技能樹

網站提供路線圖、技能樹／前置依賴、情境選型、案例、範例、來源與版本。每個節點的權威資料用MD維護，YAML只存索引與關係，避免同一規則多處複製。

| 模組 | 需掌握 | 驗收作品／門檻 |
| --- | --- | --- |
| 問題探索與交付 | stakeholder訪談、流程盤點、資料權限、baseline、成本／價值、scope、handover | 一頁需求契約：問題、非目標、成功指標、資料owner、風險與驗收 |
| Backend／API | HTTP/OpenAPI、JSON schema、認證授權、限流、webhook、idempotency、測試 | 企業任務API，錯誤與重複request可驗證，不把模型輸出直接當授權 |
| 資料與DB | SQL、transaction、migration、索引、ETL、去重、lineage、tenant scope | 可重跑匯入；斷點恢復／跨tenant隔離／schema變更測試 |
| 模型整合 | 模型選型、structured outputs、tool calling、context、延遲與成本、MCP邊界 | 相同schema的fixture/local/選配cloud provider；未知與拒答路徑 |
| RAG／最新context策略 | long-context與retrieval對比、chunking、hybrid、reranking、metadata/ACL、增量索引、引用 | 有來源、版本與ACL的檢索；無證據拒答；對照BM25／long-context／RAG |
| Local推論 | Ollama起步、vLLM服務化、embedding維度／版本、quantization、RAM/VRAM／並行／context | 使用者已安裝模型後的健康／schema／context檢查；硬體實測另記 |
| Evals與觀測 | golden/holdout、failure taxonomy、retrieval和answer分開、統計、trace、cost、human minutes | 當前版本的報告；零執行／stale／缺acceptance不能成功；模型judge需校準 |
| Durable長任務 | state machine、checkpoint、lease/heartbeat、retry、backoff、timeout、dead-letter、compensation | worker中斷後恢復、不重做已完成副作用；不確定外部結果轉ambiguous |
| 雲端與排程 | container、Cloud Run service/job、Scheduler、IAM、OIDC、Secrets、private network、監控、backup | 本機部署契約與dry-run；實際雲端驗收在帳號配置後進行 |
| 資料分析 | Python/SQL、資料品質、schema、sampling、group/time split、data leakage、可重現報告 | 脫敏合成CSV/JSON的品質／切分／錯誤分析報告 |
| 訓練／適配 | prompt/RAG與fine-tuning的分界、SFT／LoRA／QLoRA、dataset／labels、checkpoint／評估／license | 訓練資料檢查及dry-run配置；有設備／預算才訓練，不自動下載／啟動GPU工作 |
| 企業交付與改善 | PoC→pilot→production、變更管理、rollback、runbook、support ownership | capstone交接包，按觀察和人工決策升級，熱門度不是採納依據 |

路線以能力門檻為主，提供參考12週排程：1–2週問題/API/資料；3–4週模型/RAG；5–6週評測/Local；7–8週durable／觀测；9–10週cloud與資料分析／適配；11–12週capstone及交接。進階或已有能力可跳過基礎，訓練列選修，不要求先訓練大模型才交付。

新增模型／框架時先補來源與查核日，通過代表任務後才更新「建議」。職缺、官方產品能力、vendor case、論文觀察與平台建議分開標示，不能把廠商敘述改寫成業界普及率。

## 4. 三個本機程式labs

所有lab資料為明確合成資料，與知識網站的財務／pipeline state分開；runtime與輸出位於忽略的`.build/fde-labs/`。public bundle包含自有程式與脫敏fixture，不包含runtime DB、tokens、客戶檔案或第三方model weights。

### Lab A：企業文件檢索與RAG

Python實作schema、版本化匯入、tenant/document ACL、檢索、引用與拒答。SQLite/FTS作零雲端baseline；本機embedding/小資料cosine檢索與Ollama provider為選配。PostgreSQL+pgvector是後續服務DB路徑，Qdrant與vLLM放選型與相容profile，不同時部署多套DB／推論服務。

先測檢索正確性，再測生成；fixture不當成模型效果證據。長context、RAG、hybrid與reranking按資料量、更新頻率、ACL、成本及holdout實測選擇，不以「最新模型」名義跳過比較。模型輸出引用必須來自該次授權檢索；不足時返回insufficient_evidence。

### Lab B：可恢復的企業資料處理任務

Python worker＋SQLite任務表，對合成API／文件匯入做持久checkpoint、attempt/deadline、lease與取消。副作用使用idempotency key及交易receipt；任何retry要分類是暫時性、永久性、還是不確定結果。斷點、schema failure、429／timeout、重複delivery、lease過期與預算耗盡都需實際測試。

這是可檢查的小型教學範例，不冒充跨網路exactly-once平台。長時間／多人／human approval的正式編排以Temporal等現成durable engine為參考，避免自建無限agent loop。`ambiguous` 不自動重付費，不自行修改程式或擴權「自癒」。

### Lab C：資料品質與評測／訓練準備

Python CLI做schema/duplicates/missingness、group/time leakage檢查、dataset manifests/hash、train/validation/holdout切分、錯誤分桶和比較報告。提供SFT／LoRA適配決策與可驗證資料格式示例。fine-tune用途、使用權、評測與成本先明確，再由選配訓練profile啟動；當前只要求資料與dry-run的本機可重現驗收。

### Java Spring Boot對照

獨立範例模組提供相同job API、DB migration／idempotency／錯誤契約與provider接口；以fixture provider跑測試，不需模型token。Spring AI/Ollama/RAG整合使用被查核的相容Boot/BOM版本。compile與API測試獨立於網站Python環境；不把查到的snapshot示例混入固定release。

已觀察本機有Java25與Docker CLI，尚無Maven命令；實作期可使用版本固定且checksum驗證的官方Maven工具，不運行任意文章install script。Docker daemon與模型服務須實際檢查；未有的選配外部runtime不宣稱已測。

## 5. 平台契約與既有W相容性

- 新增FDE技能樹索引：id、title、level、prerequisite_ids、guide_path、source_refs、checked_at、practice_ids、evidence_level、visibility、review_state、skill_bundle_ids。唯一id、依賴cycle、缺指南／來源、私有引用與無查核日要拒絕。
- WorkflowManifest新增可選domain；舊版缺省仍是Android。舊manifest序列化不可增加default欄位，以保持W0.1／0.2的ZIP hash完全相同。
- 打包使用枚舉domain policy：Android原allowlist不變；FDE只允許明列的skills/fde-solution、skills/fde-knowledge-review、profiles/fde、bundles/fde及已核准自有lab檔案。禁止把整個skills/或examples/改成可公開root。
- 保留immutable ZIP鎖、private exclusion、inline/reference links完整性、所有檔案明確核准。程式／JSON的核准改由bundle內列明的asset approvals與hash清單，不把YAML frontmatter硬塞進可執行程式；manifest本身不能自行擴大根目錄。
- FDE包含安裝／移除／使用／相容性、LICENSE／來源與完整references。現成upstream仍另外安裝；不複製plugin cache／第三方完整框架。
- 沿用candidate→evaluated→trial→approved→deprecated、真實artifact hash／observations核對、公開採納scope。學習內容可閱讀，不代表公司已採納。
- 最初提供兩個自有薄skill：`fde-solution` 路由需求→資料/API→AI/RAG→evidence→部署交接；`fde-knowledge-review` 路由來源差量→影響評估→有理由的版本提案。各用條件式references，避免每個技能樹節點都變成always-loaded技能。

## 6. 雙週更新與新知識取得

每日資料蒐集沿用config source／Snapshot／去重。初始候選來源：Spring AI、Temporal Python SDK、pgvector、Qdrant、Ollama、vLLM、Pydantic AI、TRL的官方release；既有LangGraph可加fde topic，避免同repo抓兩遍。實作前逐一查核endpoint與實際空feed行為。企業職缺與工程文章／論文作人工策展來源，不假装release涵蓋所有知識。

來源取得分三層：官方docs/release/changelog為能力與變更；第一方工程案例／職缺為實際問題線索；YouTube／Threads為線索，再回查原始依據。無API權限的社群維持手動入口，影音metadata不代表看過內容。來源過期或故障顯示stale，而非清空歷史。

每14日差量更新共用A階段全站費用上限及原有durable Git CAS ledger。FDE沒有第二個隱藏付款帳本。選取新增topic配額避免Android或FDE互相餓死；同一revision仍只計入一次，同一story跨topic只顯示多標籤而非重複付費。失敗／ambiguous的既有規則保持。

track/topic從已核准source metadata推導，不信任模型自稱分類或自行產生skills/scripts。產生的roadmap／skill更新是change proposal，需human review、代表任務與新版本hash，不能把最新release自動覆寫公司規範。

公開頁 `/fde/updates/` 顯示核准精選、raw updates、last_collected/enriched/reviewed/next_due；AI停用或未有核准精選時據實顯示。免費收集與付費整理時間分開。deep研究仍需查看完整官方來源，不宣稱600字release片段能建立完整能力指南。

## 7. API／DB／排程最後整合

先固定本機接口和測試，再更新配置與wizard。網站保持靜態；企業labs/API是獨立服務，網站瀏覽不直接呼叫模型或讀私有DB。

API範例：`POST /jobs`（idempotency key）、`GET /jobs/{id}`、`POST /jobs/{id}/cancel`、`POST /rag/query`、`GET /health`。HTTP caller的tenant／權限由可信authentication映射；模型與request body不能自行升級tenant。Schema＋授權＋業務校驗三層；工具採固定allowlist，不接任意shell command。

DB：本機SQLite先測；後續PostgreSQL＋pgvector有獨立migration／repository adapter、TLS、least-privilege role、backup/export/restore與tenant policy。embedding模型/維度/version不同要重建或版本化index，不混寫。不得將目前Git pipeline／財務state悄悄搬進lab DB。

排程：知識網站每日Actions＋持久next_due決定雙週AI批次，避免用每月兩日期假裝14天。企業長任務可選Cloud Run Jobs＋Cloud Scheduler；持續API用Cloud Run service；多日human wait用durable編排。所有delivery視為可能重複，排程與worker各有idempotency；外部呼叫不確定保留receipt與人工處理。[Scheduler](https://docs.cloud.google.com/scheduler/docs/overview)、[Run checkpoint](https://docs.cloud.google.com/run/docs/jobs-retries)、[Temporal durable AI](https://docs.temporal.io/ai)

wizard放最後，統一入口但維持可單獨重跑階段：local-only → GitHub knowledge schedule → model/provider（DeepSeek既有預算或Ollama本機）→ API/DB profile → GCP account/IAM/Secrets/Scheduler → dry-run與健康／rollback檢查。GCP採短期OIDC/WIF身分方向，決策時查核官方文件／所需角色，沒有需求不建立DB/GPU。cloud選配，未宣稱免費額度或性能。實際建立付費resource／公開remote部署在reviewable配置後由使用者決定。

## 8. 驗收與交付順序

| 階段 | 交付 | 完成門檻 |
| --- | --- | --- |
| A1 調研與路線資料 | 第一方研究、技能樹、MD內容契約 | 每個技術建議有依據／查核日；事實與推薦分開 |
| A2 公開內容與網站 | FDE主頁、路線／技能／來源／更新入口 | 桌機／手機、搜尋、MD下載、根與Pages子路徑可用 |
| A3 通用技能打包 | domain policy、兩個skills、FDE profile與ZIP | 缺references／private／未核准asset拒絕；W包hash不變；新包可重現 |
| B1 本機RAG | Python fixture/local provider與retrieval | ACL、無證據、引用、embedding version、holdout驗收；local模型選配 |
| B2 長任務與資料分析 | SQLite worker、品質／eval／訓練準備CLI | 真實interrupt/resume、duplicate、lease、budget／timeout／leakage失敗路徑 |
| B3 Java對照API | 固定依賴Spring模組、fixture provider | compile、API/schema/idempotency測試；實際未測項另列 |
| A4 雙週更新整合 | 查核source、topic配額、精選分類／change proposals | 不多付費、不改舊帳本、不自動採納；free／AI disabled／ambiguous路徑 |
| C1 最後整合wizard | local/API/DB/cloud/schedule配置檢查 | --check／取消無寫入；secrets不輸出／不進repo；健康與rollback dry-run |

實作採使用者既有偏好的Sol原生逐項執行、TDD與一次整體終審。調研使用research要求的背景代理；不把產品實作派成多個平行代理。各階段可提交本機分支，但不在本輪自行合併main／push／部署。

本文件是待審閱設計，不把上表視為已完成的實作計劃。規格確認後才展開逐項檔案／介面／回歸測試／commit的執行計劃。

## 9. 已查核的架構依據與限制

- Cloud Scheduler可能重複delivery，Run Jobs需要持久checkpoint與idempotent輸出，因此API/worker設計需處理同一工作多次觸發。[Scheduler](https://docs.cloud.google.com/scheduler/docs/overview)、[Run](https://docs.cloud.google.com/run/docs/jobs-retries)
- Spring AI提供modular/Advisor RAG與observability，Java可作企業整合對照；具體版本與實測profile需固定。[RAG](https://docs.spring.io/spring-ai/reference/api/retrieval-augmented-generation.html)、[Observability](https://docs.spring.io/spring-ai/reference/observability/)、[相容性原始docs](https://github.com/spring-projects/spring-ai/blob/main/spring-ai-docs/src/main/antora/modules/ROOT/pages/getting-started.adoc)
- `@Scheduled`可能因多個schedule／instance重複執行；排程註解不取代分散式工作的dedup與persistent ownership。[Spring scheduling](https://docs.spring.io/spring-framework/reference/integration/scheduling.html)
- Actions排程可能延誤／丟失，不提供企業工作準點SLA；本平台可觀察last_success並補跑。[GitHub schedule](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
- PostgreSQL有row security，正式多tenant需要role／policy設計與隔離測試，不能只在prompt寫tenant。[PostgreSQL RLS](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)

職務需求、現代RAG／Local、eval與資料訓練的深入第一方證據見[FDE研究筆記](../../agentic-workflow-research/research/2026-10-08-fde-source-notes.md)。調研不代表已執行真實企業任務，沒有GPU training或cloud deployment結果。

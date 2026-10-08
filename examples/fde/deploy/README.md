# 本機與雲端部署契約

本轮已验证本機 SQLite/PostgreSQL 與合成 HTTP/worker；沒有建立雲端資源，沒有正式客戶資料或模型品質結果。靜態網站與企業 API 分開，瀏覽網站不需 DB/token。

## 本機

安裝 `examples/fde/python` 的 `.[postgres]` extra，執行 `python -m fde_lab.api`（預設 loopback、SQLite、無 token 時只 health）。`FDE_AUTH_TOKENS` 是服務端 JSON token→tenant，透過環境/secret 注入，不寫 repo；所有 body tenant 拒絕。`python -m fde_lab.api --worker` 跑最多 100 個合成步驟/60 秒，不呼叫模型。API 為單程序、小型教學 reference；需企業吞吐量時替換為 ASGI/連線池並保留同契約。Java 模組仍是獨立 SQLite 教學對照，不假稱已接 PostgreSQL。

從 `examples/fde/python` 為 context，以 `../deploy/Dockerfile` build。base Python 3.12.12 與 pgvector/pgvector pg18 的 digest 已固定，runtime 是非 root。SQLite container 的 `/state` 只適合本機，重建前 mount volume/備份；Cloud Run 必須選 postgres，不能把容器暫存檔當持久資料。沒有自動下載 weights。

## PostgreSQL

在新的明確 schema，migration owner 套用 `postgres.sql` 一次。runtime 不做 DDL，schema_version 只接受 1；升版前备份與review新migration。`fde_app`、`fde_worker` 是 NOLOGIN/NOBYPASSRLS 群組角色；由 provider/admin 建立個別 LOGIN 並授予一個群組，runtime 不用 owner/superuser。程式拒絕 owner/BYPASSRLS。API使用 app login，worker 使用另一個 worker login，secret/SA 不共用。應用以可信身分設定 transaction-local tenant；app RLS 只見該租戶，worker 明確允許跨租戶 claim。若讓客戶直接取得 DB login 或任意 SQL，它能設定 session tenant，這個模型不適用，需獨立角色/DB。

DSN 僅 secret/env，遠端 PostgreSQL 連線要求 TLS 與憑證校驗（verify-full + provider CA）；網路allowlist/Cloud Run出站及連線上限需部署前驗證。可選支援 PostgreSQL/pgvector 與 roles/RLS 的供應商；免費方案額度、休眠與角色權限需再查，不承諾零費用。若供應商不允许角色建立或extension，本配置不可直接套用，不退回owner runtime。

模型/digest/dim 綁一個 schema 的 embedding_profile，換模型重建新 schema。pgvector exact cosine 小資料查詢已測，尚未建立 ANN 或中文 tokenizer品質基準。文檔 tenant/id/version immutable，只检索最新授权版本。任務修改用 transaction advisory lock，對齊 SQLite 的串行安全邊界；代價是吞吐量有限，擴大時改 row lock/SKIP LOCKED 並重跑race/lease/effect tests。

## 雲端只列步驟

`config/fde-deployment.yaml` 預設 local-sqlite，不需帳號。`scripts/fde-deployment.py --check` / `--dry-run` 純驗證/輸出 argv，不執行、不寫檔。cloud profile 需 project、region、service、固定 image@sha256、service_account、worker_service_account、scheduler_account、Cloud Run audience、database_secret、worker_database_secret、auth_secret（各 secret 必须指定数字版本）、allow_unauthenticated=false、schedule、timezone。API/worker SA和DB refs必須不同。

生成的命令依序建立私有API與最多5分鐘/零平台重試的worker Job，再用Scheduler每天觸發 Job run。Jobs API 使用 OAuth；服务對服务呼叫 API 使用 audience 對應的 OIDC ID token 與 run.invoker。命令列不含secret值；API客戶端外層可用 X-Serverless-Authorization 傳 IAM token、Authorization 傳應用 tenant token。IAM token證明caller，tenant mapping仍由企業服務控制。生成命令附特定job的 invoker和特定secretAccessor；部署人還需部署權限及受限制的 actAs。CI 用 GitHub OIDC/WIF，限制 repo、ref/environment，不存 SA JSON key。

這份清單依賴人先完成 image build/push、DB migration/backup、roles/login、Secret Manager、IAM、network與實際audience查核，不是完整一鍵provision。雲端到期/重送可能發生；資料任務以idempotency、lease/receipt處理，radar付費更新仍用原Git CAS帳本，不能搬進此DB。

## 備份、恢復、回滾

migration owner `pg_dump --format=custom` 到私有儲存，密碼由安全連線設定注入；復原到新DB/schema，以 `pg_restore` 後重跑 tenant/lease/vector contract，核对 schema_version、counts、current versions 与 receipt。先停 Scheduler/worker，確認未决 external_calls；結果未知保持 ambiguous，不重跑付費。API image回滾到前一digest須先確認DBschema相容；不得用旧image覆盖新schema。备份頻率/RPO/RTO及真的restore演練需企業pilot驗收，本轮未聲稱遠端restore完成。

2026-10-08 官方依據：[Cloud Run 服務身分/OIDC](https://docs.cloud.google.com/run/docs/authenticating/service-to-service)、[WIF deployment pipelines](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines)、[Secret Manager integration](https://docs.cloud.google.com/run/docs/configuring/services/secrets)、[Scheduler/Jobs](https://docs.cloud.google.com/run/docs/execute/jobs-on-schedule)、[PostgreSQL RLS](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)、[pgvector](https://github.com/pgvector/pgvector)。

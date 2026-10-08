---
title: FDE 本機與選配帳號設定
visibility: public
review_state: approved
checked_at: '2026-10-08'
---

## 入口

在 repo 根目錄先安裝平台 Python 依賴，執行 `bash scripts/setup/fde.sh --check` 純驗證配置，不需帳號、不開瀏覽器、不寫檔、不呼叫模型。互動設定用 `bash scripts/setup/fde.sh`，選本次階段；可隨時 cancel/Ctrl-C 重跑。

| 階段 | 需要帳號 | 產生結果 |
| --- | --- | --- |
| local | 無 | 安裝、三套 fixture labs、API/worker 執行說明；不變更設定 |
| github | GitHub | 進入既有 GitHub wizard，分開確認私有來源 repo、公開 export repo、Secret 與發布開關 |
| provider | 選配 DeepSeek/GitHub | 進入既有 AI wizard，隱藏 token 輸入→GitHub Secret；14 天間隔與全站預算，不自動啟用 |
| api-db | SQLite 無／Postgres 選配 | schema、身份與連線說明；秘密只在執行環境/Secret Manager，本入口不收集值 |
| gcp | GCP | 唯讀確認登入，填非敏感 project/region/image digest、不同 API/worker SA、DB/auth Secret name:version；審閱後保存 YAML，只列部署命令 |
| health | 無 | 配置 dry-run、health/授權/worker/DB 驗收與回滾說明 |

## 手動配置來源

GCP Console → Project selector 選專案；Cloud Run/Artifact Registry 查 region、私有 API URL 與 image digest。IAM & Admin → Service Accounts 建/查不同 API、worker、Scheduler 身分。Security → Secret Manager 查 name 與固定數字 version，API DB、worker DB 需不同 references；值不貼進 wizard。WIF 限制來源 repo/ref，API OIDC audience 對應服務 URL，Scheduler→Jobs 使用 OAuth。UI 若變更，以 repo deploy README 的官方文件為準。

`gcp` 只保存 `config/fde-deployment.yaml` 的非敏感配置；API/worker IAM、DB migration、image push、Secrets、網路前置仍由人審閱後另行完成。配置失敗或取消時不寫檔；`--check` 也不登入。不把「dry-run 通過」寫成雲端 ready。

## 本機範例與下載

repo 的 `examples/fde/python` 可安裝為獨立 lab，FDE 0.3.0 ZIP 包含三套不需 token 的固定 Python 快照；API/PostgreSQL/部署整合在 repo 活躍 examples。Java `examples/fde/spring-api` 以 `mvn verify` 驗證。runtime 放 `.build`，公司資料、模型 weights 與秘密不進公開下載。

[能力路線](roadmap.md)、[更新政策](update-policy.md)、[API 契約](api.md)、[雲端指南](cloud.md)。查核 2026-10-08：[Cloud Run Secrets](https://docs.cloud.google.com/run/docs/configuring/services/secrets)、[WIF](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines)。

0.2.0 labs 已停用，歷史 ZIP 原 bytes 留存追溯；請使用 0.3.0 修正版。

---
title: 雲端、部署與排程
visibility: public
review_state: approved
checked_at: '2026-10-08'
---

## 用途

按 HTTP、batch、長等待區分執行服務。

## 做法與程式分工

持續 API 用 Cloud Run service，批次 Jobs＋Scheduler；private identity/IAM/Secrets，部署固定 image digest，先 dry-run。

## 本機練習

完成本機 container health、備份還原與 rollback；帳號只在 cloud 階段設定。

## 驗收

Scheduler 重送仍只有一份副作用；未部署時明列未驗證。

## 限制與證據

GitHub schedule 非準點 SLA；GCP 免費額度與性能需部署時查核。 本指南是第一方調研與本平台建議，尚非企業實測。

## 來源與下一步

[第一方依據](https://docs.cloud.google.com/run/docs/jobs-retries)（查核 2026-10-08）。[完整路線](roadmap.md)。


## 部署範例與驗證界線

repo 的 `config/fde-deployment.yaml` 預設 local-sqlite，`scripts/fde-deployment.py --check`／`--dry-run` 只列可審閱配置，不建立資源。Python API 位於 `examples/fde/python/fde_lab/api.py`，PostgreSQL migration／Dockerfile／備份與回滾 runbook 在 `examples/fde/deploy`。API／worker 需不同 DB 身分與 secret references；遠端連線校驗 TLS，runtime 不用 owner 或 BYPASSRLS。

本機已測合成 HTTP、SQLite、PostgreSQL/pgvector 的 tenant、lease、receipt 與向量版本契約；雲端、正式模型、效能與客戶資料尚未驗收。JobStore 的交易鎖優先維持一致性，需擴大吞吐量時替換鎖策略並重跑併發測試。靜態網站與企業 API 分離，付費知識更新保持原全站帳本。

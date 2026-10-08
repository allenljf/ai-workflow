---
title: 資料與資料庫
visibility: public
review_state: approved
checked_at: '2026-10-08'
---

## 用途

建立可重跑匯入、交易與資料隔離。

## 做法與程式分工

先 SQLite transaction＋unique(tenant,key)＋schema version。服務化再用 PostgreSQL adapter、migration、TLS、least privilege、backup/restore。

## 本機練習

重複匯入兩次並中斷一次，檢查 lineage、去重與恢復。

## 驗收

跨 tenant 不可讀取；schema change 有 migration；restore 後記錄一致。

## 限制與證據

Row security 仍需正確角色，owner／superuser 可能繞過政策。 本指南是第一方調研與本平台建議，尚非企業實測。

## 來源與下一步

[第一方依據](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)（查核 2026-10-08）。[完整路線](roadmap.md)。


## 部署範例與驗證界線

repo 的 `config/fde-deployment.yaml` 預設 local-sqlite，`scripts/fde-deployment.py --check`／`--dry-run` 只列可審閱配置，不建立資源。Python API 位於 `examples/fde/python/fde_lab/api.py`，PostgreSQL migration／Dockerfile／備份與回滾 runbook 在 `examples/fde/deploy`。API／worker 需不同 DB 身分與 secret references；遠端連線校驗 TLS，runtime 不用 owner 或 BYPASSRLS。

本機已測合成 HTTP、SQLite、PostgreSQL/pgvector 的 tenant、lease、receipt 與向量版本契約；雲端、正式模型、效能與客戶資料尚未驗收。JobStore 的交易鎖優先維持一致性，需擴大吞吐量時替換鎖策略並重跑併發測試。靜態網站與企業 API 分離，付費知識更新保持原全站帳本。

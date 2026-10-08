---
title: 上線、交接與持續改善
visibility: public
review_state: approved
checked_at: '2026-10-08'
---

## 用途

把 PoC 變為有人負責、可回退的 enterprise delivery。

## 做法與程式分工

pilot→production，訂定 support owner、runbook、資料 retention、監控、rollback，變更走候選→評測→試用→批准。

## 本機練習

用合成文件工單 capstone，整合 RAG、API、durable worker、eval 與交接。

## 驗收

接受者能重跑、故障恢復、查成本、回退；真實 pilot 前標教學。

## 限制與證據

最新 release 不直接覆寫公司規範；vendor case 不當本公司品質證據。 本指南是第一方調研與本平台建議，尚非企業實測。

## 來源與下一步

[第一方依據](https://openai.com/careers/forward-deployed-engineer-uae-abu-dhabi-uae/)（查核 2026-10-08）。[完整路線](roadmap.md)。

Java 範例的交接要包含 OpenAPI、SQLite schema v1 備份與 worker 啟動方式。`/health` 只表示程序可回應；需另外查 DB、授權、worker 與模型 readiness。測試 token 為本機練習，正式 identity mapping、金鑰輪替與部署需另驗收。


## 部署範例與驗證界線

repo 的 `config/fde-deployment.yaml` 預設 local-sqlite，`scripts/fde-deployment.py --check`／`--dry-run` 只列可審閱配置，不建立資源。Python API 位於 `examples/fde/python/fde_lab/api.py`，PostgreSQL migration／Dockerfile／備份與回滾 runbook 在 `examples/fde/deploy`。API／worker 需不同 DB 身分與 secret references；遠端連線校驗 TLS，runtime 不用 owner 或 BYPASSRLS。

本機已測合成 HTTP、SQLite、PostgreSQL/pgvector 的 tenant、lease、receipt 與向量版本契約；雲端、正式模型、效能與客戶資料尚未驗收。JobStore 的交易鎖優先維持一致性，需擴大吞吐量時替換鎖策略並重跑併發測試。靜態網站與企業 API 分離，付費知識更新保持原全站帳本。

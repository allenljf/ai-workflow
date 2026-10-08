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

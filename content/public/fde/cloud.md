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

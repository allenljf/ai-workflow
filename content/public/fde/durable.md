---
title: 長任務與故障恢復
visibility: public
review_state: approved
checked_at: '2026-10-08'
---

## 用途

讓中斷的企業任務依 checkpoint 恢復。

## 做法與程式分工

用 SQLite state、lease/version fencing、receipt、attempt/deadline/budget；暫時錯誤有限 backoff，外部結果未知轉 ambiguous。

## 本機練習

殺掉 worker、新 process 續跑；模擬 duplicate、lease 過期、429、timeout、取消。

## 驗收

完成副作用不重做；過期 worker 不可覆寫；不確定扣費不可自動再扣。

## 限制與證據

教學 worker 不是跨網路 exactly-once 平台；多日 approval 可用 Temporal。 本指南是第一方調研與本平台建議，尚非企業實測。

## 來源與下一步

[第一方依據](https://docs.temporal.io/ai)（查核 2026-10-08）。[完整路線](roadmap.md)。

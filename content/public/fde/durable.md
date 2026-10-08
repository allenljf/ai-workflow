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

## 本機恢復範例

依[開始使用](getting-started.md)安裝後執行：

```bash
.venv312/bin/python -m fde_lab.cli jobs-demo --state-dir .build/fde-labs/jobs
```

Demo 真實啟動子程序，完成本機 receipt 後以 exit 7 中斷，再由新 worker 續跑；時鐘使用可控制 epoch 值，報告預期副作用計數為 1。SQLite transaction 同時提交 local effect/receipt/checkpoint；這不代表任何遠端系統都 exactly-once。

`JobStore` 提供 submit/claim/checkpoint/heartbeat/cancel；過期 lease/version 拒絕写入。對遠端操作必須先 `begin_external_step` 持久記錄與預算保留，再呼叫外部 API，成功後 checkpoint receipt。中途 crash 或 timeout 而未確認結果轉 ambiguous，人工對帳後另作授權決策；不可自動重送。取消在安全 checkpoint 或 lease 回收時完成，不抹去已送出的未知副作用。

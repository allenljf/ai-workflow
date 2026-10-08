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

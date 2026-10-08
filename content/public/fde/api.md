---
title: API 與後端契約
visibility: public
review_state: approved
checked_at: '2026-10-08'
---

## 用途

把企業操作封裝為有 schema、身份與錯誤契約的 API。

## 做法與程式分工

Python worker 處理資料，Spring Boot Controller→Service→Repository 分別處理 schema、業務與交易。POST /jobs 使用 Idempotency-Key，GET /jobs/id 按可信 tenant 查詢。

## 本機練習

用相同 key 重送相同與不同 payload；驗證 200／409，未登入 401、跨 tenant 404。

## 驗收

不能用 body／模型輸出的 tenant 升級權限；非法 schema 不寫 DB。

## 限制與證據

JSON 合法只證明形狀，還需要授權與業務檢查。 本指南是第一方調研與本平台建議，尚非企業實測。

## 來源與下一步

[第一方依據](https://docs.spring.io/spring-ai/reference/api/retrieval-augmented-generation.html)（查核 2026-10-08）。[完整路線](roadmap.md)。

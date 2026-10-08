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

## 可執行 Java 對照

repo 的 `examples/fde/spring-api` 是獨立 Maven 模組，`mvn verify` 後可本機啟動。Java 21–26，固定 Boot 4.1.1 / AI 2.0.1；兩個服務端測試 token 映射 tenant，未配置時只有 health 可用。OpenAPI 放 `examples/fde/contracts/openapi.yaml`。RAG 預設合成 fixture；選配 Spring AI/Ollama 只允許 loopback，真模型品質未測。任務入列後由 Python JobStore worker 處理，不把 API 回 201 當任務完成。

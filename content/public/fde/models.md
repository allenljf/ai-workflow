---
title: 模型、工具與 context
visibility: public
review_state: approved
checked_at: '2026-10-08'
---

## 用途

用可替換 provider 整合模型，保留型別、成本、延遲與工具邊界。

## 做法與程式分工

先 FixtureProvider，再選配 Ollama/cloud；每個 tool 固定 schema、allowlist 與授權副作用。驗證輸出後才呼叫企業 API。

## 本機練習

加入錯誤 JSON、偽造工具參數、文件中的注入指令。

## 驗收

來源資料不能變成系統指令；未授權操作被拒絕。

## 限制與證據

API 相容不代表所有模型與工具能力等價。 本指南是第一方調研與本平台建議，尚非企業實測。

## 來源與下一步

[第一方依據](https://docs.ollama.com/capabilities/structured-outputs)（查核 2026-10-08）。[完整路線](roadmap.md)。

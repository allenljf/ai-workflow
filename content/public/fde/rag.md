---
title: 現代 RAG 與長 context
visibility: public
review_state: approved
checked_at: '2026-10-08'
---

## 用途

從資料量、更新、權限與品質比較長 context、RAG、hybrid、reranking。

## 做法與程式分工

先 SQLite FTS baseline；檢索前套 tenant/ACL，取最新版本，再生成並驗引用。選配 embedding 記 model/digest/dim/index version。

## 本機練習

相同 holdout 題目比較完整授權 context 與 RAG；按料號、語意、無答案分類。

## 驗收

查無證據返回 insufficient_evidence；不能引用未檢索的文件。

## 限制與證據

2024 contextual retrieval 是方法來源，benchmark 不是目前模型的通用改善保證。 本指南是第一方調研與本平台建議，尚非企業實測。

## 來源與下一步

[第一方依據](https://www.anthropic.com/engineering/contextual-retrieval)（查核 2026-10-08）。[完整路線](roadmap.md)。

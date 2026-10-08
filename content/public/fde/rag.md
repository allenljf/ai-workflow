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

## 可執行範例

依[開始使用](getting-started.md)安裝 `fde-local-labs`。`RagStore.ingest` 寫入不可覆寫的 tenant/id/version；`query` 只取該租戶最新版本，生成後驗證引用集合。`set_embedding`／`search_embeddings` 提供小資料 cosine 對照，需 model/digest/dimension 一致。純本機 baseline 的 FTS5 不提供完整中文斷詞；企業中文資料需獨立召回評測。

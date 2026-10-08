---
title: 評測與可觀測性
visibility: public
review_state: approved
checked_at: '2026-10-08'
---

## 用途

用證據衡量正確率、人工修正與成本。

## 做法與程式分工

固定 golden/holdout、dataset hash、commit、model、參數；retrieval 與 answer 分開，deterministic checks 加人工與校準的 model judge。

## 本機練習

評估引用、無答案、跨 tenant、tool failure、延遲與每成功任務成本。

## 驗收

零執行、stale artifact、缺 acceptance 不能通過；保留原始報告。

## 限制與證據

model judge 要校準，分數不能取代高風險人類決策。 本指南是第一方調研與本平台建議，尚非企業實測。

## 來源與下一步

[第一方依據](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)（查核 2026-10-08）。[完整路線](roadmap.md)。

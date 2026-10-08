---
title: 資料分析與品質
visibility: public
review_state: approved
checked_at: '2026-10-08'
---

## 用途

分析缺漏、重複、分布、時間與群組偏差。

## 做法與程式分工

先切 train/validation/holdout，再 fit preprocessing；用 group/time split、正規化 hash 與 lineage 找資料洩漏。

## 本機練習

對合成 CSV/JSONL 做 quality report、split manifests 與錯誤分桶。

## 驗收

同客戶／同文件系列不跨 split，晚資料不回流 train。

## 限制與證據

少量合成資料只能驗契約，不能證明企業模型泛化。 本指南是第一方調研與本平台建議，尚非企業實測。

## 來源與下一步

[第一方依據](https://scikit-learn.org/1.9/common_pitfalls.html)（查核 2026-10-08）。[完整路線](roadmap.md)。

---
title: Local 模型與服務化
visibility: public
review_state: approved
checked_at: '2026-10-08'
---

## 用途

依資料保密、硬體與成本選本機推論。

## 做法與程式分工

Ollama 起步，明確 embed truncate=false、timeout 與 schema；vLLM 作服務化候選，實作前查固定版本、模型 license 與硬體。

## 本機練習

使用已安裝模型量 RAM/VRAM、context、p95 latency、併發；不要自動下載 weights。

## 驗收

不同 embedding 維度不能混寫；context 太長要報錯或明確切分。

## 限制與證據

fixture 結果不代表真模型品質；本機推論也需要部署與存取控制。 本指南是第一方調研與本平台建議，尚非企業實測。

## 來源與下一步

[第一方依據](https://docs.ollama.com/api/embed)（查核 2026-10-08）。[完整路線](roadmap.md)。

---
title: SFT／LoRA 與訓練準備
visibility: public
review_state: approved
checked_at: '2026-10-08'
---

## 用途

在 prompt/RAG/工具不足且有資料與評测後才考慮適配。

## 做法與程式分工

TRL conversational/prompt-completion 格式、tokenizer/chat template、loss scope；LoRA/QLoRA 固定模型與資料版本。先 dry-run。

## 本機練習

準備授權合成資料、品質報告、獨立 holdout、配置與預算。

## 驗收

沒有資料使用權、GPU/預算或獨立評測不啟動；不能只看 training loss。

## 限制與證據

顯存依模型、seq、batch、optimizer 變動，沒有通用單卡保證。 本指南是第一方調研與本平台建議，尚非企業實測。

## 來源與下一步

[第一方依據](https://huggingface.co/docs/trl/en/sft_trainer)（查核 2026-10-08）。[完整路線](roadmap.md)。

## 已提供訓練準備

[資料 CLI](analysis.md)只產生格式、hash與dry-run配置，不載入weights、不執行trainer。先查看品質、lineage、held-out group與資料授權；真正訓練再固定model/tokenizer/chat template、LoRA設定與獨立eval。合成教學資料沒有企業泛化效果證據。

資料準備的 near-duplicate gate 依正規化 input 與 token 包含度（至少兩 token、>=0.9）判定，不因 completion 改變而視為新問題；這是保守啟發式，仍需人工檢查語義改寫與資料來源 lineage。重複／相似 input 拒絕輸出，需先清理或重新設計群組/context。validation 最晚樣本必須早於 holdout 最早樣本，群組時間範圍重疊時拒絕。

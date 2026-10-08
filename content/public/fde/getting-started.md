---
title: FDE 工作流開始使用
visibility: public
review_state: approved
checked_at: '2026-10-08'
---

目標是解決各業界企業問題，不限 Android。先以零 token、零 GPU 的本機合成練習建立能力，再按需要配置雲端。

1. 閱讀[技能樹與12週路線](roadmap.md)，依前置能力選入口。
2. 完成[需求契約](enterprise-discovery.md)，記錄資料 owner 和验收。
3. 先做[授權RAG](rag.md)、[可恢復任務](durable.md)、[資料品質](analysis.md)。
4. 查看網站候選技能包的版本、檔案與SHA-256；公開核准不代表公司採納。
5. [雲端與排程](cloud.md)放最後。程式labs與wizard按實作階段提供，未發布項目不視為已可執行。

## 使用與更新

Python負責資料/worker，Java Spring Boot作企業API對照；依既有團隊選擇。詳細[來源與更新方法](sources.md)。模型結果必須有當前版本報告，合成fixture不是AI品質證據。

## 已提供的 Python RAG lab

在 repo 本機開發環境執行：

```bash
.venv312/bin/python -m pip install -e examples/fde/python
.venv312/bin/python -m fde_lab.cli rag-demo --state-dir .build/fde-labs/rag
```

合成報告寫入 `rag-report.json`，包含 dataset hash、授權引用、無證據拒答與 fixture context/RAG 對照。此對照只驗證契約，不衡量真模型品質。Runtime DB 在忽略的 `.build/`；目前技能 ZIP 0.1.0 是路由包，不含 labs，程式從本 repo 執行。

---
title: FDE 雙週更新與預算政策
visibility: public
review_state: approved
checked_at: '2026-10-08'
---

每週 GitHub Actions 免費收集 release metadata；AI 預設停用，選配啟用後由同一份持久全站帳本控制 14 天 next_due、每批 USD 0.50、每月 USD 2。FDE 不另外開第二個付費批次，同事件多領域只整理一次。每週排程不保證準時：來源限流或排程延遲時查看來源健康狀態。

候選按來源信任、版本與穩定 id 排序；跨 Android/FDE 輪流選取，同事件不重複。request 仍限制 40 revisions / 50KB，每片段 600 字，多領域時分輪讀取不同事件，避免單一大事件吃滿。這是候選公平性，不代表內容品質或每次各領域一定有新資料。

Spring AI、Temporal Python SDK、pgvector、Qdrant、Ollama、vLLM、Pydantic AI、TRL 以各專案官方 releases 為來源，LangGraph 沿用同一 source 並加 FDE 標記。pgvector 若未發布 GitHub release，保留空來源，不把 tags 假造為 release。來源端 topic 由 reviewed config 提供，不信任模型自稱領域。

AI 輸出先存 private draft，人工確認引用、日期、案例證據與限制後才發布。核准精選分別顯示整理與審閱時間；歷史精選沒 topic 標為 unclassified。模型不能自行改 skill、採納工具或擴大權限；新技能需版本、hash 與 review，保留舊 ZIP 原 bytes。

next_due 屬私人財務狀態，公開頁不推估；頁上 AI 設定反映 checked-in 設定，Actions override 仍以該次 gate/帳本為準。calling 後結果不確定保留 ambiguous 與 reservation，不能自動重扣費。舊 saved request/prompt 保持原付款身份，恢復 draft 不呼叫模型。

查核 2026-10-08：[GitHub 官方排程限制](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)、[Spring AI releases](https://github.com/spring-projects/spring-ai/releases)、[Temporal SDK releases](https://github.com/temporalio/sdk-python/releases)、[pgvector releases](https://github.com/pgvector/pgvector/releases)、[Qdrant releases](https://github.com/qdrant/qdrant/releases)、[Ollama releases](https://github.com/ollama/ollama/releases)、[vLLM releases](https://github.com/vllm-project/vllm/releases)、[Pydantic AI releases](https://github.com/pydantic/pydantic-ai/releases)、[TRL releases](https://github.com/huggingface/trl/releases)。[能力路線](roadmap.md)。

兩領域同時有候選時，max_events_per_batch 至少要 2；設 1 會明確拒絕整理而不扣費。單一跨領域事件本身涵蓋兩領域時仍可用一筆；單領域也可用單筆批次，不以固定第一桶造成另一領域飢餓。

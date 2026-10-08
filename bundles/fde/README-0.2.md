---
title: FDE 0.2 本機 labs 與技能
visibility: public
review_state: approved
---
# FDE 自有包 0.2.0

包含 [solution skill](../../skills/fde-solution/SKILL.md)、[knowledge review skill](../../skills/fde-knowledge-review/SKILL.md)、[general profile](../../profiles/fde/general.yaml)、自有本機 labs 的固定來源快照。MIT，[授權](LICENSE.md)；沒有嵌入upstream框架或model weights。上游ref是開發基線，包內容由manifest/hash標識。

解壓後將兩個skills完整資料夾複製到harness skills目錄，已有版本先備份；移除僅刪本包資料夾。labs安裝：

```bash
python3 -m venv .venv-fde
.venv-fde/bin/python -m pip install -e bundles/fde/labs-0.2
.venv-fde/bin/python -m fde_lab.cli rag-demo --state-dir .build/fde-labs/rag
.venv-fde/bin/python -m fde_lab.cli jobs-demo --state-dir .build/fde-labs/jobs
.venv-fde/bin/python -m fde_lab.cli dataset-demo --state-dir .build/fde-labs/dataset
```

需Python3.12以上及SQLite FTS5。首次安裝httpx需要網路；執行fixture labs不需token/GPU。快照在bundles/fde/labs-0.2，持久runtime另存.build。固定版report不等於後續開發分支版本；回退重裝對應ZIP。

RAG驗證tenant/最新版本/引用與拒答；jobs真子程序中斷後恢復且不重做local effect，external未知結果停止；dataset做群組/時間/duplicates與訓練dry-run。均標synthetic-contract，尚無enterprise pilot。真Ollama、GPU訓練與cloud需另驗收。

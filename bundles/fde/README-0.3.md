---
visibility: public
review_state: approved
---
# FDE skills 與修正版本機 labs 0.3.0

[來源授權](LICENSE.md)。upstream_ref是開發基線，不聲稱此基線已包含本次修正；本ZIP/SHA識別完整內容。自有MIT薄adapter，第三方harness另外安裝，未再散布完整框架。候選，不代表企業已採納。

安裝：複製 `skills/fde-solution` 與 `skills/fde-knowledge-review` 到harness skill目錄；依任務讀references。Codex/Claude Code相容profile在 `profiles/fde/general.yaml`。移除：刪除此兩個目錄；升版先備份自己的修改，不覆寫團隊私有規則。

Python 3.12以上，`bundles/fde/labs-0.3` 執行 `python -m pip install -e .`，再跑 `python -m fde_lab.cli rag-demo --state-dir <私有runtime目錄>`；jobs-demo、dataset-demo同理。只用合成fixtures，不拉模型、不train、不付費。API/PostgreSQL/雲端整合在repo的活躍examples與deploy runbook，此ZIP只交付三套lab快照。資料與秘密不放skill目錄或Git。

0.3修正：embedding profile以SQLite交易串行建立並強制singleton，讀向量拒絕維度損壞；取消時其他外部call未確認保留ambiguous；重複input不依completion判定，詞token包含度達0.9作保守near-duplicate拒絕；validation最晚時間需早於holdout最早時間。相似度是啟發式，不保證語義paraphrase全被找出，需資料來源/group審閱與獨立holdout。

0.2已deprecated，ZIP不改bytes以供追溯，請勿繼續用它的lab驗收安全性。0.1是薄skill契約包，不含舊lab。真實模型/企業吞吐量/雲端與GPU訓練仍未驗證。

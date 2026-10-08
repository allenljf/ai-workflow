# FDE F1–F10 最終審查與交付邊界

2026-10-08。一次 fresh-context Sol reviewer 審查 4a91054..f847baf，讀三份 plan/spec、active labs 與歷史 0.2 快照。無 Critical，5 個 Important；作者以一輪 RED→GREEN 修正，不追加第二輪 reviewer。

## 重要問題與修正證據

| 問題 | 重現測試 | 修正 |
| --- | --- | --- |
| SQLite初次embedding profile並行混入不同模型/維度 | test_concurrent_initial_embedding_profiles_cannot_mix；test_corrupt_stored_vector_dimension_fails_closed | BEGIN IMMEDIATE包住檢查與寫入、singleton index、拒絕損壞向量與已有多profile DB |
| 取消＋其他checkpoint隱藏未決external call | test_cancel_progress_checkpoint_preserves_unresolved_other_call | 確認当前step後仍查全部started，未決保留ambiguous；SQLite及真Postgres同契約 |
| 同input改completion能跨train/holdout | test_repeated_prompt_with_changed_answer_cannot_enter_holdout | 正規化input與token包含度near-duplicate拒絕，不依答案判定 |
| validation group時間延伸到holdout後 | test_validation_group_must_not_extend_into_holdout_time | max(validation時間)必須嚴格早於min(holdout時間) |
| limit=1永遠先Android | test_mixed_domain_one_event_limit_refused_instead_of_starving；test_one_shared_event_can_cover_both_domains_in_one_slot | 沒有一個event同時涵蓋兩域時要求至少2筆，拒絕後不呼叫模型；共享事件仍只計一次 |

以上6個主要回歸在修正前確實失敗；共享event補充情境亦RED→GREEN。新0.3 package缺失RED→GREEN，解壓後實跑修正過的job/data邊界，rag/jobs/data快照bytes與已測active模組一致；新公開停用標示browser RED→GREEN。

0.3.0 SHA-256：`fbef48c08d2b53a91df6a770c647faefd85360f494d43e6f4b3fe275a4edb8ea`。0.2.0以reviewed state overlay標deprecated、replacement=0.3.0，原manifest/ZIP/hash不改。舊Android0.1/0.2與FDE0.1/0.2四份literal SHA仍驗證。重新安裝0.3，不將0.2舊lab當安全驗收基礎。

## 作者對審查保留範圍的裁定

- 真Ollama模型品質、語義grounding、context容量與硬體效能：維持未驗證。fixture及輸出schema不當品質證據；成本是還需獨立模型eval。
- GPU/SFT/LoRA效果：維持資料準備/dry-run，沒有訓練成果；成本是仍需硬體/授權/訓練預算與holdout驗收。
- 真實付費供應商與外部receipt reconciliation：本輪未付費。已測狀態機保守停止，不宣稱供應商exactly-once；成本是實際對帳adapter與人工reconcile未驗收。
- 雲端部署、IAM/WIF、排程、remote networking與backup/restore：僅本機與dry-run，維持未部署；成本是仍需帳號/IAM/實際restore與網路驗證。
- 企業吞吐量/availability、ANN品質與production scaling：教學reference，不宣稱企業ready；成本是負載測試及替換串行鎖/HTTPserver仍需另做。
- Java PostgreSQL與完整文件retrieval：接受既有F7/F9裁定，Java本機SQLite對照、Python實作postgres/版本化RAG；成本是Java企業整合需另接adapter。
- 市場熱門度、企業採納與vendor benchmark推廣：來源/release與職缺只能提供線索；不造市占率/採納排名；成本是選型仍需本公司代表任務驗證。

## 版本及補充設計裁定

- input近重複用保守token包含度（>=0.9且至少2 token），不是語義embedding檢測。成本：可能誤拒相似但不同的題目，也不能保證找出所有paraphrase；公開指南要求lineage/group人工審閱。
- 多領域limit<2無法穩定保障兩桶，明確拒絕而非新增另一付費batch；共享event例外。成本：自訂單筆配置需調整，預設20不受影響。
- 歷史0.2以deprecated保留追溯，不改bytes；最新修正另發0.3。成本：歷史下載仍可取得含已知缺陷的lab，公開警示要求改用0.3。
- 舊adoption測試的全站candidate斷言改為Android scope，另實際驗證FDE0.2 deprecated/替代版本/原因。成本：不同領域採納狀態需分別驗證，不假設全站相同。

## 延後小修

- FDE首頁末段仍有「Java API與wizard依後續階段加入」的舊階段措辭。實際功能與設定連結已可用；依一次review流程列為Minor延後，不把文字誤當尚無本機API。下次內容整理時校正。

所有逐項測試、執行命令結果與實作裁定見 [FDE執行紀錄](fde-execution-log.md)。本文件不代替公司採納、正式模型eval或雲端上線驗收。

## 逐項執行時的裁定與代價

依發生順序保留，不把一次通過測試當沒有設計取捨：

1. F1 adoption fixtures補齊registry所引用的approved content，產品export仍fail closed；成本：fixture範圍增加。
2. F2既有版本數量assert限Android，FDE另測；成本：domain測試需分開维护。
3. F2 adapter的upstream ref標開發基線，完整新內容以ZIP/hash識別；成本：不能只用该基線ref重建新增包，需使用已鎖ZIP及manifest。
4. F5外部步驟先持久保留budget/started，不確定轉ambiguous；成本：中断時需人工/provider receipt對帳，可能保守停止。
5. F6固定歷史snapshot，活躍examples可演進；只明列pyproject/dataset及asset hashes，code不當Markdown；成本：维护多个快照/allowlist，格式新增需review。
6. F7 Java合成policy生成與Python完整版本化retrieval分工；成本：Java正式文件檢索另接adapter。
7. F8泛用workflow保留原開發桶、跨域事件去重並輪讀revisions；單域付款身份/排序保留；成本：多域選擇順序改變，需各域回歸。
8. F8公開next_due不推估，AI狀態只反映checked-in設定；成本：公開頁不能看精確私人帳本或Actions override狀態。
9. F9 PostgreSQL共用JobStore狀態機與連線seam，用advisory lock維持串行安全；成本：吞吐量有限。
10. F9雲端image用PythonAPI/worker、Java留SQLite；成本：Java PostgreSQL企業整合另做。
11. F9 Scheduler→Jobs用OAuth，API→服務用OIDC；API/worker分SA/DB refs、只列argv；成本：IAM/WIF、DB/image與網路前置仍需人完成/驗證。
12. F10不收集DB/API秘密值，GitHub/provider路由既有隱藏stdin與付費gate；成本：人仍需自行注入本機憑證。

最終整套Python（含本機真PostgreSQL）223/223，Java4/4，browser root/Pages各7/7，Astro0errors/0warnings/10既有hints。修正版container build/health200，shellcheck/bash/actionlint/skill validators通過。尚未啟用paid模型/雲端；原四個包hash不变，最新0.3候選不等於企業採納。

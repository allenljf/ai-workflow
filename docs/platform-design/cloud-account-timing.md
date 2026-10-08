# 雲端帳號與資料何時設計、何時設定

**現在先設計帳號責任與資料邊界；本機 W1–W4 驗收後、第一次排程或公開部署前，再設定 GitHub。** 雙週付費整理啟用前才設定 DeepSeek。GCP 與 DB 等實際需求出現再接入，目前每日蒐集與靜態網站可由既有 GitHub Actions 流程承擔。

## 時機與最小資料

| 階段 | 要準備 | 儲存位置與責任 |
| --- | --- | --- |
| 現在：架構與本機驗收 | owner、私有來源repo／公開輸出repo分離、visibility、排程、publish/AI開關、月額度、rollback | 版本化 config 保存非秘密識別；token不進git |
| 首次 GitHub 排程／公開部署前 | repo名稱、Pages site URL/base、公開export授權、最小scope與保管人 | `bash scripts/setup/github.sh` 依wizard設定；repo Actions secrets/variables |
| 首次付費雙週整理前 | DeepSeek token、模型、由官方價格填入的輸入/輸出單價、單批/月預算、失敗處理 | `bash scripts/setup/ai.sh`；預設 AI disabled，dry-run 後才啟用；每次不即時呼叫模型 |
| 首次 Android 真實評測前 | 測試repo、完整SHA、JDK/SDK/Gradle/裝置、命令、核准profile、資源鎖、沙盒帳號 | 私有RunnerBinding與evidence；先有測試環境再跑，正式帳號／簽章不在公開下載包 |
| 需要 GCP 時 | 執行job超出既有CI限制、長工作需cloud runner、或需服務API；project id、region、service account、預算與owner | 優先短期身分聯盟與最小權限；需求定案後再做專用wizard，不預先建立付費資源 |
| 需要 DB 時 | 多人同時編輯審查、跨服務查詢、即時後端；資料模型、留存、可見性、備份／匯出方案 | 評估實際用量與當時服務限制後選DB，再做wizard；現阶段 Git/state與靜態export足夠 |

這是專案設計時序，不是當前雲端方案價格或免費額度承諾；選供應商與開通前再查官方限制。

## 資料流

每日 Actions → 來源metadata與去重state → 人工可讀網站更新；不需每天模型呼叫。

雙週且 AI enabled → 差量批次／硬預算／候選摘要 → 人類review → 核准公開精選。新工作流 → candidate → 固定spec/base的代表與holdout任務 → evaluated → trial → 人類approved。資料來源更新不會自動改公司規範。

公開repo只含核准靜態檔與自有技能包。公司profile、內部案例、原始evidence、inbox、token及正式帳號保持私有。新增雲端服務時，同步設計身分、資料保留、費用、監控與回復；不用為未使用的服務先收集秘密。

## 本輪未做的外部設定

未建立雲端資源、未寫入Secrets、未啟用付費模型、未推送／發布網站，也未綁定Android source。現有wizard可在本機驗收後使用；需要GCP/DB時再依選定服務補wizard，而非把帳號流程塞進每次開發任務。

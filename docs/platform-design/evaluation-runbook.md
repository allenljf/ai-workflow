# Android 工作流評測 runbook

本輪狀態：契約與本機 runner fixture 已測；**Android 真實評測待綁定**。八個任務位於 `evaluations/tasks/`，binding 欄位全為 null，沒有猜測 package、Gradle module 或成功案例。

## 綁定與實際執行

1. 選隔離的 Android 測試 repository、固定 base/head 40 位 SHA，確認乾淨 tracked tree。指定 JDK/SDK/Gradle/裝置與工具版本、profile ID、harness/model 精確版本。對照八個任務 acceptance，保存規格原始位元組 SHA-256。
2. 人類核准 RunnerBinding 的 `profile_review`：owner、decision=approved、profile_id、commands、environment 必須與 binding 完全相符。commands 是參數陣列，包含目標專案已存在的 Gradle/測試命令，不執行文章推薦的任意 script。資源鎖由 dispatcher 保留。憑證使用沙盒，輸出預設私有。
3. 於 platform 已安裝 Python 環境執行：`python scripts/evaluate-workflow.py --binding /private/binding.json --report relative/JUnit.xml --out /private/evidence`。可多次指定 report。runner 有總 timeout、記錄退出碼、驗證執行後 HEAD/乾淨 tracked tree、拒絕未重產生的 report。Gradle 若沿用快取，選專案核准的 rerun 參數；不要拿舊報告補證。
4. runner 的 observations 不是完整 EvaluationRun。人工補 task/spec/base/head、model/harness、workflow id/version、environment 及逐項 acceptance；人工分鐘、成本缺測就 null。Artifact SHA-256 由 runner 計算，檔案由 reviewer 檢查後封存。維持 private，脫敏且核准的摘要才可公開。
5. `validate_evidence(run, expected_head, acceptance_ids)` 的 acceptance_ids 必須來自固定規格，而非報告中自稱的成功清單。零執行、失敗、全部 skip、舊 head、缺 acceptance 或 artifact 都不完整。依賴仍須 reviewer accepted 且 integrator 記錄實際 inclusion。

## Maestro 與手動觀察

此版本只解析標準 JUnit `testcase`，實際計算 skipped/failure/error，不信 testsuite 總數。尚未為不明 Maestro 報告格式建立 parser；Maestro 可使用團隊已驗證的 JUnit 產出，或 reviewer 提供逐 acceptance 的手動結果與版本、錄影/畫面證據。單張畫面、exit0、mock 與未執行 UI 測試不能冒充成功。API登入、支付、發布要另外取得責任人決策。

## 比較設計

先跑 baseline（既有流程）、固定 upstream、company-profile 三組，同一 task/spec/base/environment/model/harness，各保存 head。分配代表任務與 holdout，避免只挑成功任務。每組多次執行，記錄失敗、人工修復時間與 token/金額，品質先於速度。

`compare_runs` 只配對相同 task/spec/base/environment/model/harness/provenance 的唯一 baseline；重複 run 需先按實驗輪次拆組，避免隨意配對。返回 duration/cost/human_minutes 差值，缺值仍 null，不自動推論因果或更新公司採納狀態。

Synthetic 示例：baseline duration10、candidate6 → delta−4；兩組 cost=null → cost_delta=null。這只測比較契約，不是 Android 效率改善案例。

## 待補資料

Android repo與版本、八個任務的專案路徑/命令、真實環境與資源鎖、實驗規格hash、模型/工具版本、報告、acceptance觀察、實測成本/人工時間、公司profile核准人、試用範圍與rollback版本。這些具備前，candidate 不升 evaluated。每兩週資訊更新只產生候選；先實測再 trial，由人類決定 approved。

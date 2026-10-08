---
title: Android 工作流開始使用
visibility: public
review_state: approved
---


1. 在工作流頁選版本，下載 ZIP，核對页面 SHA-256 與包內 manifest 的 id/version/ref。0.1.0 是文件包，0.2.0 加入可讀取的 android-task 技能。兩者都是 candidate。
2. 依 [固定上游 README](https://github.com/obra/superpowers/blob/8ca22dba9a94f28898bbce59f2537ff4d87c747d/README.md) 分別安装支援的 harness 上游。核對固定 ref；marketplace 可能跟隨新版，安裝名稱相同不代表版本相同。
3. 0.2.0 的 `skills/android-task/` 安裝到團隊 harness 的技能目錄，開新對話確認能讀取技能與兩個 references。這是可讀性檢查，不是 Android 效果驗證。薄 adapter 依上游安排任務，不額外引入一套 orchestrator。
4. 在隔離 Android repo 綁定固定 SHA、已核准 profile、路徑、資源鎖、參數陣列命令與環境。先做契約 dry-run，再收集真實 Gradle/JUnit 與 UI acceptance。公司 profile 私下提供，專案例外需附理由；衝突先解決再開始。
5. Reviewer 先驗收，integrator 記錄基線包含依賴，再解鎖下一任務。初期最多兩個實作者，共用 emulator/Gradle cache/port/account 另保留資源鎖。

移除只刪除這次加入的 adapter 目錄；上游由其官方方法管理。Rollback 選保留的上一版 ZIP/hash/profile，重開對話確認載入版本；不要用新版證據證明舊版採納。

[任務流程](task-flow.md) 與 [證據等級](../cases/evidence-levels.md) 說明何時可以交接與採用。簽章、正式支付／登入與 Play 發布另由責任人決定。

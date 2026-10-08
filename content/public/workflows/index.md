---
title: 工作流版本與採納
visibility: public
review_state: approved
---


以一個固定版本的上游指揮流程，搭配自有 Android adapter；公司規範以私有 profile 疊加。新版與熱門技巧先列為候選，再以代表任務驗證。此網站目前只有 **candidate**，沒有 Android 真實成功案例。

| 狀態 | 需要的證據 |
| --- | --- |
| discovered / candidate | 來源、固定 ref、授權及可重現包 |
| evaluated | 固定 spec/base/environment 的真實執行與逐 acceptance 證據 |
| trial | 人類決定試用範圍、owner、日期、理由、rollback |
| approved | 試用證據與人類採納決策；公司範圍可保留私有 |
| deprecated | 可追溯歷史包、替代版本與停用理由 |

閱讀 [開始使用](../android/getting-started.md)、[任務流程](../android/task-flow.md)、[證據等級](../cases/evidence-levels.md)。公開文件 review_state=approved 只表示可以發布；不是公司已採用，也不是 Android 已驗證。

歷史 ZIP 保留建立時的 manifest。目錄頁呈現最新採納狀態，SHA-256 對應原始包；版本內容變更需要新版本，採納決策不改寫歷史包。下載包不含第三方上游技能，須另安裝官方固定版本。

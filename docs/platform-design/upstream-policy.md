# 固定上游與 bundle 政策

2026-10-08查核：[obra/superpowers v6.4.2](https://github.com/obra/superpowers/releases/tag/v6.4.2)，annotated tag 668b16d4d8d4d603fd257567684fbbffccbf2022，peeled commit **8ca22dba9a94f28898bbce59f2537ff4d87c747d**。
[該commit授權](https://github.com/obra/superpowers/blob/8ca22dba9a94f28898bbce59f2537ff4d87c747d/LICENSE)為MIT。僅記錄查核，仍選擇不將上游打包進本repo。

一個主流程為Superpowers；Matt的方法只作選配技巧。自有adapter只補profile/contract/evidence/handoff，不再指揮另一套SDLC。
bundle白名單限自有bundles/android-task、skills/android-task、profiles/android，逐檔要求public+approved。公司profile、原始docs、evaluation原輸出禁止入zip。相對reference必須在同一manifest清單，script缺檔拒絕，不執行未知上游script來測完整性。
重打包固定ZIP路徑排序、時間、權限；同版本內容不同則拒絕覆寫。版本變更另存manifest，歷史評測不跟著current alias更新。
第三方若將來嵌入，必須另查授權、核准redistribution並附完整notice；未知授權拒絕。初版明確用官方固定ref安裝連結，不把本機plugin cache當來源。

公開版本第一次建立 ZIP 後，將 id/version/SHA-256 寫入 `registry/bundle-locks/` 並與版本一起審查提交。每次 export 從全新 staging 重建也必須符合已提交的 lock。既有 lock 不隨內容修改更新；升版時保留歷史 manifest 指向的檔案位元組，新版改動需使用新版本專屬來源路徑。即使共享 LICENSE/references 修改，也不得改變旧版本。

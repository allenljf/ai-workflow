---
title: Android 任務驗收與交接
visibility: public
review_state: approved
---


任務從不可變規格與固定整合基線開始，宣告讀寫範圍、依賴、acceptance、命令、重試／時間／token預算。進行中的任務預留資源；worktree 只能隔離檔案，不能隔離裝置或帳號。

```mermaid
flowchart TD
  S[固定規格與基線] --> D{依賴已驗收且整合?}
  D -->|否| B[blocked / 等待交接]
  D -->|是| R{檔案與資源可用?}
  R -->|否| B
  R -->|是| I[實作與測試]
  I --> V{當前 head 的實際證據完整?}
  V -->|是| Q[ready_for_review]
  Q --> A[人類驗收 accepted]
  A --> M[整合與 inclusion 記錄]
  V -->|否| T{預算尚未耗盡?}
  T -->|是| I
  T -->|否| B
  B --> C[保存 checkpoint 與下一步]
```

圖的 Markdown 原碼可下載；文字門檻與圖一致。未知 token 用量保留 null；重開對話保留原始 deadline／attempt count，不自動重置。Checkpoint 比對 spec/base/head，若不同先修訂契約。

交接包包含 patch、當前 head 的報告、逐 acceptance、改動路徑、重試次數、剩餘預算、checkpoint、阻礙與下一步。ready_for_review 不會解鎖依賴；exit0、零執行、全部skip、舊head、fake/stub 或缺失驗收也不會解鎖。

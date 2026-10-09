# Agentic 開發工作流研究資料

2026-08 調研產物。主題：harness / loop / graph 三種 AI 開發工作流，以 Android 為實例。

## 2026-10 更新

- **[AI 軟體開發工作流最新調研與知識更新指南](workflow-landscape-2026-10-08.md)** — 查核日 2026-10-08；包含 Superpowers、Matt Pocock、SDD、harness／loop／graph、Claude Code Mods、採用證據、導入建議與可重複的搜尋方法。
- **[本次作者與 SDD 一手來源筆記](research/2026-10-08-workflow-source-notes.md)** — 版本快照、原始來源與限制。

以下既有手冊與 12 份研究為 2026-08 快照；此次沒有全面重新查核。

## 檔案

- **`agentic-workflow-handbook.md`** — 主文件（約 1,100 行）。完整實作手冊，含步驟、腳本、流程圖、可貼的設定檔。
  重點章是 Part B（閉環工程）。線上版：https://claude.ai/code/artifact/505795d5-d452-4850-83a9-bd56743b3e54

- **`research/`** — 12 份一手調研原始資料，總量約 750 KB，是手冊的素材。
  資訊量遠大於手冊，含大量沒收進手冊的細節、陷阱（GOTCHAS）與未解問題（OPEN）。
  每份結構相同：`SUMMARY` → `KEY FACTS`（附來源 URL）→ `EXAMPLES`（可貼的程式碼）→ `GOTCHAS` → `OPEN`。

| 檔案 | 主題 | 對應手冊章節 |
|---|---|---|
| `01-loop-engineering-閉環工程.md` | Ralph 迴圈、Stop hook、reward hacking 證據與防線 | Part B |
| `02-android-verification-驗證工具鏈.md` | 每個 oracle 的指令、耗時、機器可讀輸出格式 | Part B2 |
| `03-claude-code-harness-primitives.md` | hook / skill / subagent / plugin / headless 完整契約 | Part A |
| `04-android-architecture-官方架構.md` | 2026 官方分層、Now in Android 現況、工具鏈版本 | 全文 |
| `05-tdd-vs-fast-routing.md` | TDD 對 agent 是否有效的實證、各套件的路由設計 | Part D5 |
| `06-spec-driven-dev-tools.md` | OpenSpec / spec-kit / Kiro / BMAD / Agent OS / Tessl 比較 | Part D1 |
| `07-packaging-distribution-打包發佈.md` | superpowers 架構、跨工具可攜、安裝器設計 | Part D7 |
| `08-codebase-search-知識庫.md` | 檢索三層、Kotlin 工具的實際成熟度 | Part E |
| `09-practitioner-workflows-方法論.md` | Pocock / HumanLayer / Every / Anthropic / 反對派 | Part 1.2 |
| `10-graph-orchestration.md` | LangGraph、多 agent 模式與反方證據 | Part C |
| `11-eval-telemetry-儀表與刪除.md` | OTel 指標、黃金任務集、刪除 scaffolding 的判準 | Part D8 |
| `12-parallel-agents-gradle-底層實測.md` | worktree × Gradle 爭用、cache、sandbox 的實測數字 | Part C3 |

## 注意

調研時間是 2026-08。工具版本、API 契約、套件架構都會變——特別是 Claude Code 的 hook 事件表和各套件的目錄結構，
半年後要重新確認。每則事實都附了來源 URL，可以直接回去查。

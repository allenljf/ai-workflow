# AI 開發工作流：Superpowers、Matt Pocock 與 SDD 一手來源筆記

查核基準：2026-10-08（Asia/Taipei）。這份筆記記錄本次能讀到的官方來源；版本日期依 release/changelog 原樣保留，GitHub 顯示時間未自行轉換為台灣日期。`main` 會變動；導入前應再看實際安裝版本與 tag。功能與作者主張分開記錄，沒有把 GitHub stars、安裝量或行銷文案當成業界普及率或效果證明。

## 1. 版本快照

| 專案 | 本次查到的最新 release | 日期依官方頁面 | 注意 |
| --- | --- | --- | --- |
| Matt Pocock skills | v1.3.1 | 2026-10-04 | 10 月剛加入正式版 `implement-spec`；舊影片流程可能不同。 |
| Superpowers | v6.4.2 | 2026-09-25（release notes） | 計畫不再預寫全部程式。 |
| GitHub Spec Kit | v1.1.2 | 2026-10-07 | README 已拓展為 SDD、bug fixing、idea assessment 三個入口。 |
| OpenSpec | v1.14.1 | 2026-10-06 | artifact-guided OPSX 流程；Stores 仍 beta。 |
| BMAD Method | v6.12.1 | 2026-10-04 | `main` 已混有標為 Unreleased 的 v7 草稿，不能視為已發布。 |
| Tessl | 不以單一方法框架版本概括 | 當前首頁無發布日期 | 2025 的 Framework closed-beta 資訊只作歷史記錄。 |

版本來源：[Matt releases](https://github.com/mattpocock/skills/releases)、[Superpowers release notes](https://github.com/obra/superpowers/blob/main/RELEASE-NOTES.md)、[Spec Kit releases](https://github.com/github/spec-kit/releases)、[OpenSpec releases](https://github.com/Fission-AI/OpenSpec/releases)、[BMAD releases](https://github.com/bmad-code-org/BMAD-METHOD/releases)。

## 2. Matt Pocock：可組合工程紀律，而非只有一套 SDD 模板

**可驗證事實：** 官方 README 將技能分為使用者明確啟動的流程與模型可自動採用的工程紀律。現有入口含 `grill-with-docs`、`to-spec`、`to-tickets`、`implement`、`implement-spec`、`wayfinder`、`retro`；底層含 `domain-modeling`、`codebase-design`、`tdd`、`code-review`。Claude plugin 為受管理 bundle；skills.sh 安裝的是可自行編輯檔案，官方提醒不要兩種都裝以免重複。[官方 README](https://github.com/mattpocock/skills)

**實用流程：** `grill-with-docs → to-spec → to-tickets → implement（逐票）或 implement-spec（整體協調）→ code-review → retro`。`to-tickets` 切的是可展示的垂直 tracer bullet，跨 schema/API/UI/tests，而非先做完所有 DB 再做所有 UI；每票附 blocking edges，應能由新的 context window 獨立理解。小變更可跳過 tickets。[to-tickets 官方說明](https://github.com/mattpocock/skills/blob/main/docs/engineering/to-tickets.md)

**graph 的具體含義：** `implement-spec` 讀取 ticket dependency graph，讓 blockers 已整合的 ready frontier 票同時由 subagents 在各自 worktree 執行，再整合至一個 integration branch。這是工作相依圖，不是強制導入 graph database、GraphRAG 或 LangGraph。它需要背景 subagent、獨立 worktree 與設定好的 tracker；若 harness 只能逐一執行 subagent，官方明言會變成較慢的 `implement`。最後整體 review，相較逐票人工監督，控制點較晚。[implement-spec 官方說明](https://github.com/mattpocock/skills/blob/main/docs/engineering/implement-spec.md)

**loop 的具體含義：** `implement` 在約定 seam 上逐行為 red/green/refactor，過程持續 typecheck，最後完整 tests 與 review 後 commit 至目前 branch。輸入若是切錯的 ticket，流程不會幫你重新設計。[implement 官方說明](https://github.com/mattpocock/skills/blob/main/docs/engineering/implement.md)

**最新增量：** v1.3.0/1.3.1 的正式集成包括 `implement-spec`、`pr`、`retro`。`retro` 聚焦 agent 的環境：導覽、checks、標準、steering files、工具使用；機械性標準優先變成 deterministic checks。這正是把每次失誤轉成下一次的 harness 改善。[官方 changelog](https://github.com/mattpocock/skills/blob/main/CHANGELOG.md)

**作者主張與限制：** 作者偏好小、可讀、可修改 skills，批評大型框架接管流程使 debugging 困難；這是他的設計立場，並非跨專案比較研究。[官方 README](https://github.com/mattpocock/skills)。AIHero 2026-04-27 文章仍使用 `domain-model`、`to-prd`、`to-issues` 等舊名，適合作背景，不應照抄當前指令。[有日期的舊介紹](https://www.aihero.dev/skills-post)

## 3. Superpowers：自動啟動、完整且較強制的開發方法

**可驗證事實：** 官方流程涵蓋 brainstorming/design、worktree、plan、執行、TDD、review、branch 收尾；多個 coding harness 有各自安裝方式。作者明確稱這些是 mandatory workflows。適合希望 agent 預設遵循一致紀律的人；是否適合小改動須考慮流程負擔。[官方 README](https://github.com/obra/superpowers)

**最新變化：** v6.3.0 將任務分成 spike/bounded/architectural 以縮放 ceremony。v6.4.1 重建 Native inline execution：同一 session 執行整個 plan，最後一次新 reviewer；也保留逐 task subagent/review。v6.4.2 的 plan 改記 signature、assertions、spec values 與必要演算法；不以大段 implementation 填滿計畫。作者報告少量 eval 的時間/token 改善，不能外推到你的 repo。[release notes](https://github.com/obra/superpowers/blob/main/RELEASE-NOTES.md)

**來源衝突提示：** 查核時 README Basic Workflow 還有「2–5 分鐘、complete code」措辭，與 v6.4.2 release notes 不完全同步。研究最新行為時，以指定 tag 的 SKILL 與 release notes 優先；勿只讀 README 或舊 fork。[v6.4.2 writing-plans](https://github.com/obra/superpowers/blob/v6.4.2/skills/writing-plans/SKILL.md)

**我的選用判斷：** 想要全套、預設自動遵守可先試 Superpowers；已懂工程流程且要精選、改造某些步驟，可先試 Matt skills。先挑一個作主流程，避免兩套 brainstorming/TDD/review 互相觸發；這是工作流設計建議，沒有聲稱實測優勝者。

## 4. SDD 工具不是同一種東西

| 工具 | 可驗證的核心做法 | 適用判斷與限制 |
| --- | --- | --- |
| Spec Kit | 專案 constitution；每個 feature `specify → plan → tasks → implement → converge`，反覆 implement/converge 至收斂；另有獨立 bug fixing 與 idea assessment extensions。 | 適合要模板、可檢視 artifact 與明確 quality gates。不要沿用「只支援 greenfield」或早期六指令介紹。[README](https://github.com/github/spec-kit) |
| OpenSpec | `explore → propose → apply → archive`；每個 change 有 proposal/specs/design/tasks，archive 將變更納入主 specs；spec 有具體 WHEN/THEN scenario。 | 官方定位 brownfield、迭代、tool agnostic；這是定位而非實測優勢。跨 repo Stores beta 要另評估。[README](https://github.com/Fission-AI/OpenSpec) |
| BMAD | 涵蓋產品、架構、UX、dev/testing 等觀點，依工作大小調整深度；官方 modules 包括 BMad Loop。 | 適合需求/產品/架構協作多的工作；能否簡化到合適負擔應試行。main 的 v7 未發布內容與 stable v6 要分開。[README](https://github.com/bmad-code-org/BMAD-METHOD) |

Spec Kit 的既有專案指引明確建議：從 bounded change 起步，constitution 只寫 repo 已存在或團隊已同意的標準；不要先替整個舊系統補一份大規格。新 spec 定義這次改動，不是所有舊行為的追溯規格。這可避免 SDD 被用成文件工程。[Existing project guide](https://github.github.io/spec-kit/guides/existing-projects.html)

OpenSpec v1.14.1 進一步區分「tasks checked」與「完成可 archive」：apply 完成後仍要 review。spec validate 可檢查規格形式，不能替代實際行為的 tests。[v1.14.1 release](https://github.com/Fission-AI/OpenSpec/releases)

BMAD stable 最近版本：v6.11.0 以 `bmad-build` 取代 quick-dev，v6.12.0 簡單變更採兩段 spec，v6.12.1 修正 merged config/override 一致性。舊 agent 名稱、舊路由與 v7 Toolsmith 宣傳應看版本再採用。[releases](https://github.com/bmad-code-org/BMAD-METHOD/releases)、[main Unreleased changelog](https://github.com/bmad-code-org/BMAD-METHOD/blob/main/CHANGELOG.md)

## 5. Tessl：2025 SDD 歷史與當前 enablement 平台需分開

2025-09-23 官方公告區分 Spec Registry（open beta；library usage specs）與 Tessl Framework（closed beta；以 specs 引導程式產生/演進）。那是歷史發布狀態，不能直接當 2026-10 的可用性結論。[當時的官方公告](https://tessl.io/blog/tessl-launches-spec-driven-framework-and-registry)

目前首頁定位為 agent enablement：build/test/distribute/optimize skills，registry/context activation、before-after eval、review/security/documentation loops、model/harness/cost 評估。官方將 skill 定義為標準、loop 為反覆套用標準做工作、factory 為多個 loop 組合。這個產品層的 loop 與 TDD loop 不同。首頁的 defect precision、success rate、客戶 logo 為廠商呈現，未在本次找到足以獨立驗證成效的完整方法；不應當成普遍績效保證。[當前官方首頁](https://tessl.io/)

## 6. 持續追蹤的做法（研究建議）

1. 先保存你的實際版本/tag/安裝管道；追上游 release，不把 marketplace 已裝版本等同 main。
2. 每月搜尋：`site:github.com/obra/superpowers releases`、`site:github.com/mattpocock/skills CHANGELOG implement-spec`、`site:github.com/github/spec-kit releases converge`、`site:github.com/Fission-AI/OpenSpec releases`、`site:github.com/bmad-code-org/BMAD-METHOD releases`、`site:tessl.io skills loops evaluation`。
3. 看「改了什麼失敗模式」而不只新名詞：plan 過長、tests 漏跑、review 重複、context 汙染、錯分支、gate 誤通過、任務整合。這些項目在上述實際 changelog 能找到具體修正。
4. 看一手 README → release notes → 指定 tag skill → issues/PR 中的 reproducer/eval。遇到矛盾，以 source/version 具體比對，保留不確定性。
5. 拿同一個自己的 feature/bug 測兩種方法；記 elapsed time、tokens/cost、人工介入次數、失敗 cases、可維護性及一次完整測試結果。網路人氣不能代替你 repo 的 baseline。

**本次證據界線：** 沒有執行上述工具、沒有驗證其 eval、沒有市場份額調查；推薦按已讀到的流程設計與導入成本推論。資料足以確認專案活躍與當前功能方向，不足以將任一工具稱為「業界標準」或「公認最好用」。

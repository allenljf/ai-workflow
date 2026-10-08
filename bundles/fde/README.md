---
title: FDE 技能包安裝與使用
visibility: public
review_state: approved
---
# FDE 自有技能包 0.1.0

本包是本 repo 自有路由與 references，MIT。manifest 的 upstream ref 指向開發基線 commit，不宣稱該 commit 包含本次新增技能；ZIP 檔案與 SHA 才是本版本完整內容。沒有嵌入任何第三方框架。

解壓後把 [fde-solution](../../skills/fde-solution/SKILL.md) 與 [fde-knowledge-review](../../skills/fde-knowledge-review/SKILL.md) 兩個完整資料夾複製到 harness 的 skills 目錄，references 同時保留。Codex 使用 `~/.codex/skills/`，其他 harness 依官方安裝文件操作。先檢查已有同名資料夾，備份再覆寫。移除只刪本包兩個資料夾，保留任務資料與已安裝 upstream。

以需求開發任務呼叫 `$fde-solution`；以來源差量与工作流版本提案呼叫 `$fde-knowledge-review`。查看 [general profile](../../profiles/fde/general.yaml)。參數與資料權限應由實際企業 owner 決定，不因安裝取得雲端或付款授權。

這是候選 adapter，尚無企業 pilot，不把文件核准當公司採納。需搭配目標 harness 的原生工具；沒有內建無限 agent loop、runtime DB、雲端 credentials 或 model weights。發布新技能時建立新版本，保留舊包與校驗碼，回退重新安裝先前 ZIP。

[授權](LICENSE.md)。每次採纳保留 acceptance、run artifact/hash 與人類決策；第三方插件另行查核固定版本與安裝。

# 接到你的 AI 工具

本指南不綁定任何 AI 工具。以下是各家的接法，選你在用的那個就好。

**共同原則**：讓工具知道兩件事 —— `android-dev-guide/AGENTS.md` 是入口，動程式碼前要依任務讀對應的 `guides/`。

---

## Claude Code

在專案根目錄的 `CLAUDE.md` 加一段：

```markdown
## 開發準則

Android 程式碼一律遵守 `android-dev-guide/`。動任何程式碼前先讀 `android-dev-guide/AGENTS.md`，
依它的路由表決定本次要讀哪幾份 `guides/`。選型有疑慮時讀對應的判斷樹，不要自行決定。
```

若要更強的保證，可加 hook 在每次編輯後自動稽核（可選，非必要）：

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Edit|Write",
      "hooks": [{
        "type": "command",
        "command": "python3 android-dev-guide/tools/check-rules.py --files \"$CLAUDE_FILE_PATH\" 2>/dev/null || true"
      }]
    }]
  }
}
```

`skills/` 下的顧問可複製到 `.claude/skills/` 直接使用。

---

## Cursor

建立 `.cursor/rules/android-guide.mdc`：

```markdown
---
description: Android 開發準則
alwaysApply: true
---

Android 程式碼一律遵守 @android-dev-guide/AGENTS.md。
動程式碼前依該檔的路由表讀取對應的 android-dev-guide/guides/ 檔案。
```

舊版 Cursor 用 `.cursorrules`，內容同上（不需要 frontmatter）。

---

## Codex 與多數 agent

多數 agent 會自動讀取專案根目錄的 `AGENTS.md`。在根目錄的 `AGENTS.md` 加：

```markdown
## Android 開發準則

見 `android-dev-guide/AGENTS.md`。動程式碼前先讀它的路由表。
```

若你的專案根目錄還沒有 `AGENTS.md`，可以直接把 `android-dev-guide/AGENTS.md` 的內容複製過去，
或建一個只含上述指向的最小檔案。

---

## GitHub Copilot

建立 `.github/copilot-instructions.md`：

```markdown
Android 程式碼遵守 android-dev-guide/AGENTS.md 的規範。
重點：依賴方向 UI → Domain → Data；不得暴露 Mutable 狀態；
不得硬寫 Dispatchers；Compose 用 collectAsStateWithLifecycle；
設計系統 token 不得 hardcode。完整規則見 android-dev-guide/guides/。
```

Copilot 的指令檔有長度限制，所以只放最高頻的紅線，其餘靠 `guides/`。

---

## 不用 AI 工具

指南本身就是給人讀的。建議：

1. 新人到職讀 `guides/00-principles.md`（約 100 行）
2. `tools/check-rules.py` 接進 pre-commit 與 CI
3. code review 時對照 `checklists/` 對應的場景清單

---

## 接進 CI

### GitHub Actions

```yaml
- name: Android 開發準則稽核
  run: |
    pip3 install pyyaml
    python3 android-dev-guide/tools/check-rules.py \
      --diff origin/${{ github.base_ref }} --format github
```

`--format github` 會輸出 annotation，違規直接標在 PR 的對應行上。
腳本在有 MUST/MUST_NOT 違規時回傳 exit 1，PR 會紅。

### pre-commit

```bash
# .git/hooks/pre-commit 或 .githooks/pre-commit
python3 android-dev-guide/tools/check-rules.py --staged || exit 1
```

導入初期建議先不要擋 commit，只印出來看：

```bash
python3 android-dev-guide/tools/check-rules.py --staged || true
```

---

## 委派 subagent 時的注意事項

多數 AI 工具的 subagent **不會繼承**主 agent 的 context。委派實作任務時，
必須把準則路徑寫進 subagent 的指示：

```
實作前先讀完這些，不得略過：
- android-dev-guide/guides/00-principles.md
- android-dev-guide/guides/08-ui-state.md
- android-dev-guide/guides/10-compose-state.md

新增檔案 100% 遵守；修改既有檔案只修你改到的區塊。
選型有疑慮不要自己決定，回報給我。
```

這是實務上準則失效的最大破口 —— 主 agent 讀了準則，但實際寫程式碼的 subagent 沒讀到。

# Android 開發準則

一份可直接複製到任何 Android 專案的開發準則，內容全部以 [Google 官方文件](https://developer.android.com/topic/architecture) 與官方範例 [nowinandroid](https://github.com/android/nowinandroid) 為準。

給 AI agent 的入口是 [AGENTS.md](AGENTS.md)。

---

## 這份管什麼、不管什麼

**管**：程式碼該長什麼樣。

技術選型（Hilt / Compose / Room / Retrofit…）、架構分層、模組化、狀態管理、非同步、
測試策略、效能、安全、設計系統的使用原則。

**不管**：怎麼協作。

需求怎麼分析、規格怎麼寫、任務怎麼拆、PR 怎麼開、要不要 TDD、用不用 spec-driven —— 
這些是團隊工作流的事。你可以搭配 OpenSpec、superpowers、或任何你慣用的方法，
本指南不會與它們衝突，也不依賴它們。

**不綁定任何 AI 工具。** 沒有 Claude Code 專屬的 hook，沒有 Cursor 專屬的設定。
稽核腳本是一支獨立的 Python，能接進任何 CI 或 git hook。

---

## 目錄

```
android-dev-guide/
├── AGENTS.md              AI agent 入口：實作順序、通用紅線、路由表
├── README.md              這份（人類入口）
├── rules.yaml             機器可讀規則索引（唯一真相源）
├── guides/                19 份領域準則
├── checklists/            場景檢查清單
├── skills/                顧問 skill（可載入支援 skill 機制的工具）
├── tools/
│   └── check-rules.py     獨立稽核腳本，零 AI 工具依賴
└── adoption/              導入指引
```

### guides/ 的編號

| 範圍 | 檔案 |
|---|---|
| 原則 | `00-principles` |
| 架構與模組 | `01-architecture` `02-modularization` `03-dependency-injection` |
| 資料 | `04-domain-layer` `05-data-layer` `06-network` `07-persistence` |
| UI 與狀態 | `08-ui-state` `09-compose-api` `10-compose-state` `11-compose-performance` |
| 非同步與導航 | `12-coroutines-flow` `13-navigation` |
| 橫向 | `14-design-system` `15-testing` `16-performance` `17-security` `18-analytics` |

---

## 怎麼開始

### 新專案

複製整個 `android-dev-guide/` 到專案根目錄，然後讀 [adoption/getting-started.md](adoption/getting-started.md)。

### 既有專案

**不要**一次套用全部規則 —— 既有專案一定有大量違規，全開會讓所有 PR 都紅。
讀 [adoption/existing-project.md](adoption/existing-project.md)，它給的是漸進導入的順序。

先跑一次看全貌：

```bash
python3 android-dev-guide/tools/check-rules.py --all
```

### 接到你的 AI 工具

讀 [adoption/integrating-ai-tools.md](adoption/integrating-ai-tools.md)。
簡短版：把 `android-dev-guide/AGENTS.md` 的路徑寫進你的工具設定檔即可。

| 工具 | 設定檔 |
|---|---|
| Claude Code | `CLAUDE.md` |
| Cursor | `.cursorrules` 或 `.cursor/rules/` |
| Codex / 多數 agent | `AGENTS.md`（根目錄） |
| GitHub Copilot | `.github/copilot-instructions.md` |

---

## 規則的兩個標籤

每條規則有 `level`（錯得多嚴重）與 `enforce`（什麼時候必須修）。**兩個都要看。**

| level | 意義 |
|---|---|
| MUST / MUST_NOT | 官方明確要求，或違反會產生 bug、洩漏、無法測試 |
| SHOULD / SHOULD_NOT | 官方建議，例外需在 review 說明 |
| MAY | 可選 |

| enforce | 意義 |
|---|---|
| `new-only` | 新增檔案 100% 符合，既有的不動 |
| `new-only+on-touch` | 加上：你改到的函式／區塊要一併修 |
| `migrate` | 既有違規不阻斷 PR，另案批次處理 |

只看 level 會讓人在既有專案裡不知道該不該動手，這是多數「規範文件沒人遵守」的原因。

完整索引在 [rules.yaml](rules.yaml)，每條含 id / level / enforce / owner / 檢查方式 / 官方出處。

---

## 稽核

```bash
# 看目前工作區的改動
python3 android-dev-guide/tools/check-rules.py

# pre-commit
python3 android-dev-guide/tools/check-rules.py --staged

# CI（GitHub Actions 的 annotation 格式）
python3 android-dev-guide/tools/check-rules.py --diff origin/main --format github

# 檢查指南自身一致性（改了規則後跑）
python3 android-dev-guide/tools/check-rules.py --self-check
```

腳本只實作「單檔就能判定」的規則（約三分之一）。其餘需要理解上下文的（分層是否正確、
UiState 設計、測試強度）交給 code review 或 AI agent 依 `guides/` 判斷 —— 這是誠實的上限，
不是所有規範都能自動化。

誤報時加行內豁免，並在 review 說明理由：

```kotlin
val dispatcher = Dispatchers.IO // guide-ignore: hardcoded-dispatcher
```

---

## 技術基準

穩定版為準，且以 nowinandroid 已採用者優先。**不包含**還在 alpha/beta 的技術。

| 領域 | 採用 |
|---|---|
| DI | Hilt |
| UI | Compose（Material 3） |
| 狀態 | ViewModel + StateFlow，MVVM + UDF |
| 非同步 | Coroutines / Flow |
| 導航 | Navigation Compose 2.8+ type-safe route |
| 網路 | Retrofit + OkHttp + kotlinx.serialization |
| 本地 | Room / DataStore |
| 測試 | JUnit4 + Turbine + Robolectric + Compose UI Test |
| 建置 | Gradle version catalog + convention plugin + KSP |

若你的專案用了不同的選型（例如 DI 用 Koin），多數規則的**原則**仍然適用 —— 
constructor injection、介面與實作分離、scope 對應、DI 圖驗證。
各領域檔會標明哪些是框架無關的原則、哪些是 Hilt 專屬語法。

---

## 修改這份指南

1. 改規則要同步三處：`guides/` 的 md 正文、`rules.yaml` 的條目、必要時 `tools/check-rules.py` 的 pattern
2. 改完跑 `python3 tools/check-rules.py --self-check`
3. 一條規則只有一個 owner 檔案，其他檔案只寫 cross-ref，不要重述 —— 重述必然漂移

規則 id 全域唯一，且是行內豁免用的識別碼，改名要一併搜尋全庫。

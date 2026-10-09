---
name: android-guide
description: Android 開發準則入口。判斷本次任務要讀哪幾份準則、依什麼順序實作、有哪些選型需要先決定。任何新功能、新畫面、串接 API、重構前先跑一次。觸發詞：android-guide、開發準則、要遵守什麼、該讀哪些、怎麼寫才對、實作順序、架構規範。
---

# Android 開發準則入口

準則庫在 `android-dev-guide/`。這個 skill 做三件事：判斷任務類型 → 給必讀清單 → 指出需要先決定的選型。

> 這份只管**程式碼該長什麼樣**。需求分析、規格、任務拆分、PR 流程屬於團隊工作流，不在此範圍。

---

## 守則

1. **不要憑印象回答準則內容**，每次實際讀檔案
2. **不要一次讀完 19 份**，依任務讀 2–4 份
3. **選型有疑慮不要自己決定** —— 去讀對應的判斷樹，或問使用者
4. 委派 subagent 時**必須把準則路徑寫進它的指示**（subagent 不繼承你的 context）

---

## Step 1：判斷任務類型

| 訊號 | 任務類型 |
|---|---|
| 「新功能」「開發 XXX」、有需求文件 | 新功能 |
| 「新增畫面」「做一個頁面」、有設計稿 | 新畫面 |
| 「串接 API」「接後端」、有 API 規格 | 串接 API |
| 「重構」「整理」「技術債」 | 重構 |
| 「修」「壞了」「閃退」 | 修 bug |
| 檔案是既有的 Screen/ViewModel/Repository | 修改既有程式碼 |

判斷不出來就問，不要猜。

## Step 2：讀準則

`android-dev-guide/guides/00-principles.md` **一律必讀**。其餘依任務：

| 任務 | 加讀 |
|---|---|
| 新功能 | `01-architecture` `02-modularization` `03-dependency-injection` |
| 新畫面 | `08-ui-state` `09-compose-api` `10-compose-state` `14-design-system` |
| 串接 API | `06-network` `05-data-layer` `04-domain-layer` |
| 本地儲存 | `07-persistence` |
| 非同步 | `12-coroutines-flow` |
| 導航 | `13-navigation` |
| 效能 | `11-compose-performance` `16-performance` |
| 測試 | `15-testing` |
| 埋點 | `18-analytics` |
| 安全 | `17-security` |
| 重構／修 bug | `01-architecture` + 對應領域 |

**上限 4 份。** 超過就挑最相關的。

用 Read 逐一讀，不要 grep 片段 —— 規則的「例外」欄常常才是關鍵。

## Step 3：查 enforce（改既有程式碼時）

新增檔案不用查（100% 遵守）。修改既有檔案必查：

```bash
grep -A6 "id: <rule-id>" android-dev-guide/rules.yaml
```

| enforce | 遇到既有違規 |
|---|---|
| `new-only` | 既有的不動 |
| `new-only+on-touch` | 你改到的區塊要修，同檔其他地方不動 |
| `migrate` | **不要在這個 PR 修**，記到待辦 |
| `exempt` | 本專案不採用，不用管 |

## Step 4：確認選型

以下問題若沒有明確答案，**先解決再動手**：

| 問題 | 去哪找答案 |
|---|---|
| 這段邏輯放哪一層？要不要開 UseCase？ | `01-architecture` 的判斷表 |
| 該開新模組還是塞現有的？ | `02-modularization` |
| StateFlow / SharedFlow / Channel 選哪個？ | `12-coroutines-flow` 的選型樹 |
| UiState 一個還是多個？事件怎麼傳？ | `08-ui-state` |
| 該用哪個 side effect API？ | `10-compose-state` 的判斷樹 |
| 錯誤怎麼往上傳？ | `05-data-layer` |
| fake 還是 mock？該測什麼？ | `15-testing` |

判斷樹給不出答案時（專案有特殊限制），問使用者，不要自行決定。

## Step 5：實作順序

照 `android-dev-guide/AGENTS.md` 的順序，由內而外：

```
契約 → 資料 → 業務 → 注入 → 狀態 → 畫面 → 測試
```

不要從 UI 開始寫 —— UI 的形狀會反過來決定資料結構，導致 DTO 穿透到畫面。

## Step 6：輸出

```
## 本次任務

**類型**：<判定結果>
**已讀**：guides/00-principles.md、guides/<...>

**本次要注意的**（從讀到的準則挑 3–6 條真正相關的）：
1. [rule-id] <一句話> — <為什麼這次會踩到>

**待確認的選型**（如果有）：
- <問題> → <建議，或需要使用者決定>

**實作順序**：
1. ...

**檢查清單**：android-dev-guide/checklists/<對應場景>.md
```

---

## 委派 subagent

subagent **不會**繼承這段 context。指示必須自帶：

```
實作前先讀完，不得略過：
- android-dev-guide/guides/00-principles.md
- android-dev-guide/guides/<領域檔>

新增檔案 100% 遵守；修改既有檔案只修你改到的區塊，不擴散。
選型有疑慮不要自己決定，回報給我。
```

依 subagent 職責的預設清單：

| 職責 | 準則 |
|---|---|
| 資料層 / API | `05-data-layer` `06-network` `04-domain-layer` `03-dependency-injection` |
| UI / Compose | `08-ui-state` `09-compose-api` `10-compose-state` `14-design-system` |
| 測試 | `15-testing` |

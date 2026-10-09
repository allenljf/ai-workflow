# Android 開發準則 — AI Agent 入口

這份檔案是 AI coding agent 的入口。人類請看 [README.md](README.md)。

本指南只定義**實作程式碼的技術選型、規範、品質與架構**，全部以 Google 官方文件與官方範例 [nowinandroid](https://github.com/android/nowinandroid) 為準。

**它不定義**任何專案管理或協作流程 —— 需求怎麼分析、規格怎麼寫、任務怎麼拆、PR 怎麼開，那是你的團隊工作流的事（OpenSpec、superpowers、任何你慣用的方法都可以）。本指南只管「程式碼該長什麼樣」。

---

## 一、動手前

### 每次都讀

[guides/00-principles.md](guides/00-principles.md) — 不可協商的核心原則，約 100 行。

### 依任務讀

不要一次讀完 19 份。用下表決定這次要讀哪 2–4 份：

| 任務 | 讀 |
|---|---|
| 新功能／新需求 | `01-architecture` `02-modularization` `03-dependency-injection` |
| 新畫面 | `08-ui-state` `09-compose-api` `10-compose-state` `14-design-system` |
| 串接 API | `06-network` `05-data-layer` `04-domain-layer` |
| 本地儲存 | `07-persistence` `05-data-layer` |
| 非同步／資料流 | `12-coroutines-flow` |
| 畫面跳轉 | `13-navigation` |
| 列表卡頓、重組過多 | `11-compose-performance` `16-performance` |
| 寫測試 | `15-testing` |
| 埋點 | `18-analytics` |
| 碰到認證／付款／log | `17-security` |
| 重構既有程式碼 | `01-architecture` + 對應領域 + [checklists/refactor.md](checklists/refactor.md) |

完整規則索引在 [rules.yaml](rules.yaml)（機器可讀，含每條規則的 id / 嚴重度 / 檢查方式）。

### 選型卡住時

不要自己決定，去讀對應的判斷樹：

| 疑問 | 去哪 |
|---|---|
| 這段邏輯放哪一層？要不要開 UseCase？ | `01-architecture` |
| 該開新模組還是塞現有的？ | `02-modularization` |
| StateFlow / SharedFlow / Channel 選哪個？ | `12-coroutines-flow` |
| UiState 要一個還是拆多個？事件怎麼傳？ | `08-ui-state` |
| 該用哪個 side effect API？ | `10-compose-state` |
| 錯誤怎麼往上傳？ | `05-data-layer` |
| fake 還是 mock？該測什麼？ | `15-testing` |

`skills/` 下有對應的 skill 版本，若你的工具支援 skill 機制可直接載入。

---

## 二、實作順序

**由內而外，依賴方向決定順序。** 每一步完成後才進下一步，不要跳著寫。

```
① 契約      domain 層介面（Repository interface、domain model）
              ↓  純 Kotlin，不含任何 Android 型別
② 資料      Retrofit service / DAO → DTO → mapper → Repository 實作
              ↓  DTO 在這一層轉成 domain model，不外流
③ 業務      UseCase（有商業邏輯或跨 ViewModel 重用時才開）
              ↓
④ 注入      DI 綁定：介面 → 實作
              ↓
⑤ 狀態      UiState data class + ViewModel（暴露單一 StateFlow）
              ↓
⑥ 畫面      stateless Composable ← stateful Screen（收 ViewModel）
              ↓
⑦ 測試      UseCase / Repository / ViewModel 的單元測試
```

為什麼是這個順序：每一層只依賴上一步產出的抽象，寫到後面不需要回頭改前面。反過來從 UI 開始寫，會讓 UI 的形狀決定資料結構，導致 DTO 直接穿透到畫面。

**測試不是最後才想**。第 ①③ 步定介面時就要問「這個介面好不好測」——需要注入 dispatcher 嗎？需要 fake 嗎？答案會影響介面設計。

### 修 bug 的順序

```
① 重現      先寫一個會失敗的測試（紅燈）
② 定位      找根因，不是找到能讓症狀消失的那一行
③ 修復      改 production code，讓測試轉綠
④ 檢查      同類問題在別處還有沒有
```

不要跳過第 ①步。沒有失敗測試就修好的 bug，無法證明真的修好了，也擋不住回歸。

---

## 三、通用紅線

以下違反即為實作錯誤，需重做。細節見各領域準則。

**架構**

1. 依賴方向只能是 UI → Domain → Data。data / domain 層不得 import 任何 UI 型別（Compose、ViewModel、Activity、Fragment、View）
2. domain 層不得 import Android framework（`androidx.annotation`、`androidx.paging` 除外）
3. UI 層（含 ViewModel）不得直接持有 DataSource（ApiService、DAO、DataStore、SharedPreferences），一律經 Repository
4. 網路 DTO 與資料庫 Entity 不得外流到 UI 層，必須先 map 成 domain model 或 UI model
5. 跨層公開 API 只能是 `suspend fun` 或 `Flow`，不得用 callback、LiveData、RxJava 型別

**狀態**

6. 不得對外暴露 `MutableStateFlow` / `MutableSharedFlow` / `MutableLiveData`
7. ViewModel 不得持有 `Context` / `Activity` / `View` / `NavController`
8. 新程式碼不得使用 `LiveData`

**協程**

9. 不得硬寫 `Dispatchers.IO` / `Dispatchers.Default`，一律建構子注入 `CoroutineDispatcher`
10. 不得使用 `GlobalScope`；production code 不得使用 `runBlocking`
11. `suspend` 函式必須 main-safe（自己負責切 dispatcher）
12. 不得吞掉 `CancellationException`

**Compose**

13. 收集 Flow 一律 `collectAsStateWithLifecycle()`
14. 不得在 composition 中做 I/O、網路、資料庫存取或重運算
15. `LazyColumn` / `LazyRow` 的 `items` 必須提供穩定的 `key`
16. 可重用 composable 必須提供 `modifier: Modifier = Modifier` 參數

**設計系統**

17. 間距、圓角、字級、顏色一律用專案設計系統的 token，不得 hardcode 數值
18. 使用者可見文案不得硬編碼在程式碼中，一律用字串資源

**測試**

19. 不得寫假綠燈測試：無斷言、恆真斷言、被註解掉的斷言、無 ticket 的 `@Ignore`
20. 測試不得使用 `Thread.sleep`，用 `runTest` 虛擬時間

---

## 四、既有專案的處理原則

在既有專案採用本指南時，用兩級強制：

| 情況 | 要求 |
|---|---|
| **新增檔案** | 100% 符合，無例外 |
| **修改既有檔案** | 你改到的那個函式／區塊要符合；同檔案沒動到的部分不強求 |
| **其他檔案** | 不動。想批次清理就另開專門的 PR |

不要為了「順便重構」把功能 PR 擴散到十幾個檔案。遇到大量既有違規時，記錄下來另案處理，不要在當前 PR 裡修。

每條規則在 [rules.yaml](rules.yaml) 都標了 `enforce`：`new-only`（只管新檔案）、`new-only+on-touch`（改到就要修）、`migrate`（既有違規另案處理）。

---

## 五、你的產出要交代什麼

實作完成後，明確說明：

1. 做了什麼（改了哪些檔案、為什麼）
2. **偏離準則的地方與理由**（有的話）——不要無聲偏離
3. 沒做完的部分（如果有）
4. 驗證結果：編譯、測試、靜態檢查的實際輸出，不要只說「應該沒問題」

如果專案已接上 [tools/check-rules.py](tools/check-rules.py)，跑一次並附上結果。

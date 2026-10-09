# 00 · 不可協商紅線

**每次動程式碼前都讀這一份。** 這裡只有絕對不能違反的規則，全部是 MUST / MUST NOT。細節與理由在各領域準則檔。

違反紅線的程式碼視為實作錯誤，需重做，不接受「這次先這樣」。

---

## A. 流程紅線

| # | 規則 | 來源 |
|---|------|------|
| A1 | **MUST NOT** 未經使用者明確指示就 `git commit` / `git push` | 專案決策 |
| A2 | **MUST NOT** 修改 `libs/app_resource/src/main/res/values*/strings.xml`（PM 維護） | 專案決策 |
| A3 | **MUST NOT** 為了讓建置通過而調整 SDK / 套件版本，需先取得確認 | 專案決策 |
| A4 | **MUST** 所有 AI 產出的文件與說明使用繁體中文（程式碼、API 名稱、技術識別符除外） | 專案決策 |
| A5 | **MUST NOT** 手動在 `docs/ai-guide/` 新增檔案（由 skill 維護） | 專案決策 |

## B. 設計系統紅線

| # | 規則 | 來源 |
|---|------|------|
| B1 | **MUST** 間距、圓角、字型、字級、顏色一律使用 StyleDictionary token | 專案決策 |
| B2 | **MUST NOT** hardcode `16.dp`、`14.sp`、`Color(0xFF…)`、`RoundedCornerShape(8)` 等數值 | 專案決策 |
| B3 | **MUST** 找不到對應 token 時**先詢問使用者**，不可自行決定數值 | 專案決策 |
| B4 | **MUST** 程式碼中的硬編碼字串加 `// TODO: replace with stringResource - <說明>` 並列入待處理 task | 專案決策 |
| B5 | **MUST** 嚴格遵守 Figma 設計稿的 padding / size / color token / layout flow | 專案決策 |

→ 細節：[13-designsystem.md](13-designsystem.md)

## C. 架構紅線

| # | 規則 | 來源 |
|---|------|------|
| C1 | **MUST NOT** 在 domain 層 `import android.*` / `androidx.*`（`androidx.annotation`、`androidx.paging` 除外） | [官方](https://developer.android.com/topic/architecture/domain-layer) |
| C2 | **MUST NOT** 在 domain 層 import data 層實作類別（`*RepositoryImpl`、`*ApiService`、`*Dao`）；只依賴 `:domain:contract` 介面 | [官方](https://developer.android.com/topic/architecture/recommendations) |
| C3 | **MUST NOT** 讓 UI 層直接使用網路 DTO 或 DB Entity，必須先在 data 層 map 成 domain model / UiModel | [官方](https://developer.android.com/topic/architecture/data-layer) |
| C4 | **MUST NOT** 新增 feature 模組之間的直接依賴 | [官方](https://developer.android.com/topic/modularization/patterns) |
| C5 | **MUST NOT** 手動 `new` 實作類別（`XxxRepositoryImpl()`），一律 DI 注入介面 | [官方](https://developer.android.com/training/dependency-injection) |

→ 細節：[01-architecture.md](01-architecture.md)、[02-modularization.md](02-modularization.md)、[04-domain-layer.md](04-domain-layer.md)

## D. UI 狀態紅線

| # | 規則 | 來源 |
|---|------|------|
| D1 | **MUST NOT** 對外暴露 `MutableStateFlow` / `MutableSharedFlow` / `MutableLiveData`；用 `private val _x` + `val x: StateFlow<T> = _x.asStateFlow()` | [官方](https://developer.android.com/topic/architecture/ui-layer) |
| D2 | **MUST NOT** 在 ViewModel 持有 `Context` / `Activity` / `View` / `NavController` | [官方](https://developer.android.com/topic/libraries/architecture/viewmodel) |
| D3 | **MUST NOT** 在新程式碼使用 `LiveData`，一律 `StateFlow` / `SharedFlow` | 專案決策（官方方向） |
| D4 | **MUST NOT** 寫新的 Reductor store / reducer；新畫面一律 MVVM + UDF | 專案決策 |

→ 細節：[08-ui-state.md](08-ui-state.md)

## E. Compose 紅線

| # | 規則 | 來源 |
|---|------|------|
| E1 | **MUST NOT** 新增 `res/layout/*.xml`；新畫面一律 Compose（「新畫面」判定見 [91-decisions.md](91-decisions.md)） | 專案決策（官方方向） |
| E2 | **MUST** 用 `collectAsStateWithLifecycle()`，**MUST NOT** 用 `collectAsState()` | [官方](https://developer.android.com/topic/libraries/architecture/coroutines) |
| E3 | **MUST NOT** 在 composition 中直接做 I/O、網路、資料庫存取或重運算 | [官方](https://developer.android.com/develop/ui/compose/performance/bestpractices) |
| E4 | **MUST** `LazyColumn` / `LazyRow` 的 `items` 提供 `key` | [官方](https://developer.android.com/develop/ui/compose/lists) |

→ 細節：[09a-compose-api.md](09a-compose-api.md)、[09b-compose-state.md](09b-compose-state.md)、[10-compose-performance.md](10-compose-performance.md)

## F. Coroutine 紅線

| # | 規則 | 來源 |
|---|------|------|
| F1 | **MUST NOT** 硬寫 `Dispatchers.IO` / `Dispatchers.Default`；一律建構子注入 `CoroutineDispatcher` | [官方](https://developer.android.com/kotlin/coroutines/coroutines-best-practices) |
| F2 | **MUST NOT** 使用 `GlobalScope` | [官方](https://developer.android.com/kotlin/coroutines/coroutines-best-practices) |
| F3 | **MUST NOT** 在 production code 使用 `runBlocking` | [官方](https://developer.android.com/kotlin/coroutines/coroutines-best-practices) |
| F4 | **MUST** `suspend` 函式必須 main-safe（自己負責切 dispatcher，不要求呼叫端切） | [官方](https://developer.android.com/kotlin/coroutines/coroutines-best-practices) |
| F5 | **MUST NOT** 吞掉 `CancellationException`；`catch (e: Exception)` 必須先 `if (e is CancellationException) throw e`，或改捕捉具體例外 | [官方](https://developer.android.com/kotlin/coroutines/coroutines-best-practices) |
| F6 | **MUST NOT** 空 `catch {}` 吞例外 | 業界共識 |

→ 細節：[11-coroutines-flow.md](11-coroutines-flow.md)

## G. 資料層紅線

| # | 規則 | 來源 |
|---|------|------|
| G1 | **MUST NOT** `Gson()` 直接建立實例；一律 `com.kkday.util.gson.GsonInstance`（pre-push hook 會擋，含測試碼） | 專案決策 |
| G2 | **MUST** Retrofit service 一律 `suspend fun`，**MUST NOT** 回傳 `Call<T>` / RxJava 型別 | [官方 sample](https://github.com/android/nowinandroid) |
| G3 | **MUST NOT** `printStackTrace()`；用統一 logger 並轉成 domain error | 業界共識 |
| G4 | **MUST NOT** 在 release build 輸出敏感資訊（token、個資、完整 request body） | 業界共識 |

→ 細節：[05-data-layer.md](05-data-layer.md)、[06-network.md](06-network.md)

## H. 測試紅線

| # | 規則 | 來源 |
|---|------|------|
| H1 | **MUST NOT** 寫假綠燈測試：沒有斷言、恆真斷言（`assertTrue(true)`）、`catch` 吞掉失敗 | 專案決策 |
| H2 | **MUST NOT** 在測試使用 `Thread.sleep`；用 `runTest` 虛擬時間 / `advanceUntilIdle` / Turbine / Compose `waitUntil` | [官方](https://developer.android.com/kotlin/coroutines/test) |
| H3 | **MUST** 新增的 UseCase 與 Repository 都要有單元測試 | 專案決策 |

→ 細節：[14-testing.md](14-testing.md)

## I. 相容性紅線

| # | 規則 | 來源 |
|---|------|------|
| I1 | **MUST NOT** 使用 `window.statusBarColor` / `window.navigationBarColor`（targetSdk 36 起無效）；用專案的 `SystemBarLegacyCompat` API | 專案決策 |

→ 細節：[15-performance.md](15-performance.md)

---

## 誤報處理

自動稽核（`.claude/hooks/dev-guide-lint.py`）誤報時，加行內豁免並**在回覆或 PR 說明理由**：

```kotlin
val ioDispatcher = Dispatchers.IO // dev-guide-ignore: hardcoded-dispatcher
```

無聲豁免視同違反紅線。

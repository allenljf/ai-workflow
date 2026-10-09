# Checklist · 新功能

依 [AGENTS.md](../AGENTS.md) 的實作順序逐層完成。每一項都要能回答「做了／不適用（原因）」，不是打勾就好。

## 動工前

- [ ] 已讀 `guides/00-principles.md` + `01-architecture.md`
- [ ] 這個功能放哪個模組已確定（新開？既有？）→ `guides/02-modularization.md`
- [ ] 資料流已想清楚：UI ← ViewModel ← UseCase(選用) ← Repository ← DataSource
- [ ] 錯誤情境已列出：網路失敗、空資料、權限不足、逾時，各自 UI 要顯示什麼

## ① 契約（domain）

- [ ] Repository 介面定義在 domain 層，方法是 `suspend fun` 或回傳 `Flow`
- [ ] domain model 是純 Kotlin，沒有 `android.*` / `androidx.*` import（`androidx.annotation`、`androidx.paging` 除外）
- [ ] 沒有序列化註解（`@Serializable` / `@SerializedName`）—— 那是 DTO 的事
- [ ] 介面方法用 domain model，不是 DTO

## ② 資料（data）

- [ ] Retrofit service 是 `suspend fun`，回傳具名 DTO（不是泛型參數）
- [ ] DTO 與 domain model 分開，有 mapper（`toDomain()`）
- [ ] `Repository` 實作命名 `DefaultXxxRepository` 或 `XxxRepositoryImpl`，放 data 層
- [ ] `CoroutineDispatcher` 由建構子注入，沒有硬寫 `Dispatchers.IO`
- [ ] `suspend` 函式自己 `withContext(ioDispatcher)`，呼叫端不需要切
- [ ] 錯誤有轉成 domain error，沒有把 `HttpException` 往上丟
- [ ] `catch` 有處理 `CancellationException`，沒有空 catch
- [ ] Room：DAO 是 `suspend` 或回傳 `Flow`；改到 entity 有寫 migration

## ③ 業務（domain，選用）

- [ ] 有商業邏輯或 ≥2 個 ViewModel 重用 → 開 UseCase；否則可以不開
- [ ] UseCase 用 `operator fun invoke` 單一入口
- [ ] UseCase 沒有持有狀態
- [ ] 只依賴 domain 層的介面

## ④ 注入

- [ ] 介面 → 實作的綁定已註冊（`@Binds` 優於 `@Provides`）
- [ ] `@Module` 有 `@InstallIn`，scope 與 component 對應正確
- [ ] 沒有手動 `new` 實作類別
- [ ] Dispatcher 用 `@Qualifier` 註解區分，不是字串

## ⑤ 狀態

- [ ] `UiState` 是不可變 `data class`，欄位全 `val`，集合用唯讀型別
- [ ] ViewModel 暴露單一 `StateFlow<XxxUiState>`（或有充分理由的少數幾條）
- [ ] 沒有對外暴露 `MutableStateFlow` / `MutableLiveData`
- [ ] ViewModel 沒有持有 `Context` / `Activity` / `View` / `NavController`
- [ ] one-off event 用 state 欄位表達，消費後由 UI 回呼清除
- [ ] 衍生自 repository stream 的狀態用 `stateIn(viewModelScope, WhileSubscribed(5_000), initial)`
- [ ] 需要跨 process death 的狀態有用 `SavedStateHandle`

## ⑥ 畫面

- [ ] 拆成 stateful screen（收 ViewModel）+ stateless content（只收 value 與 lambda）
- [ ] stateless 那層可以獨立 `@Preview`
- [ ] 用 `collectAsStateWithLifecycle()`
- [ ] 可重用 composable 有 `modifier: Modifier = Modifier`，位置在必填參數之後
- [ ] 參數傳值不傳 `State<T>`
- [ ] `LazyColumn` / `LazyRow` 的 `items` 有穩定的 `key`
- [ ] 間距／顏色／圓角／字級用設計系統 token，沒有 hardcode 數值
- [ ] 使用者可見文案來自字串資源，沒有硬編碼
- [ ] composition 內沒有 I/O、網路、重運算
- [ ] side effect 用對 API，`LaunchedEffect` 的 key 正確

## ⑦ 測試

- [ ] Repository 有測試：成功／API 錯誤／網路錯誤／空資料 至少 3 條路徑
- [ ] UseCase 有測試（若有開）
- [ ] ViewModel 有測試：loading → success，以及錯誤路徑
- [ ] 用手寫 fake 而非 mock（自家介面）
- [ ] 用 `runTest` + 注入的 `TestDispatcher`，沒有 `Thread.sleep`
- [ ] 驗證狀態序列時用 Turbine，不是只斷言最終的 `.value`
- [ ] 每個 `@Test` 都有真正驗證行為的斷言
- [ ] content composable 的 `@Preview` 涵蓋 loading / empty / error / success

## 收尾

- [ ] 編譯通過
- [ ] 測試綠燈
- [ ] 靜態檢查（detekt / lint）無新增問題
- [ ] `python3 android-dev-guide/tools/check-rules.py` 無必修項
- [ ] 偏離準則的地方已在 PR 描述說明理由

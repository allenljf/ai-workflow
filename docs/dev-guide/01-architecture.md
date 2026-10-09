# 01 · 架構分層

**這份管**：三層職責邊界、依賴方向、SSOT、UDF、跨層溝通型別、新程式碼該放進哪一層。
**這份不管**：層內部怎麼寫 —— ViewModel / UiState 見 [08-ui-state.md](08-ui-state.md)、UseCase 見 [04-domain-layer.md](04-domain-layer.md)、Repository 與 model 分層見 [05-data-layer.md](05-data-layer.md)、模組切分與 Gradle 依賴邊見 [02-modularization.md](02-modularization.md)、DI 綁定見 [03-di.md](03-di.md)。
本專案是**水平分層**（`:app` / `:shared:*` / `:feature:*` / `:data:*` / `:domain:*`，53 個模組），**沒有** feature 的 `:api` / `:impl` 拆分；假設該結構的官方規則已標 exempt（[91-decisions.md](91-decisions.md) D-17），不要嘗試建立那種模組。

---

## 三層職責

| 層 | 對應模組 | 負責 | 不負責 |
|----|---------|------|-------|
| **UI** | `:app`、`:feature:*`、`:shared:UI:*` | 渲染狀態、把使用者事件交給 ViewModel | 取得資料、商業規則 |
| **Domain**（選用） | `:domain:contract`（介面 + domain model）、`:domain:usecase` | 商業規則、組合多個 Repository | Android 型別、data 層實作 |
| **Data** | `:data:*` | 取得／儲存資料、DTO → domain model 映射、快取策略 | 認識 UI 型別、持有 UI 狀態 |

依賴方向 **UI → Domain → Data**，單向。Domain 是選用層：沒有商業邏輯時 UI 可直接依賴 Repository 介面，但不得跳過 Repository。

---

## 規則

### layer-upward-import · MUST_NOT · new-only+on-touch · lint:layer-upward-import

`:data:*` / `:domain:*` 模組內的檔案不得 import 任何 UI 型別：`androidx.compose.*`、`androidx.lifecycle.ViewModel`、`Activity`、`Fragment`、`View`、`Composable`。

✗ `// :domain:usecase` 內：`import androidx.lifecycle.ViewModel`
✓ UseCase 回傳 domain model，由 UI 層的 ViewModel 自行轉成 UiState

例外：無。domain 層另有 `android.*` / `androidx.*` 白名單，見紅線 C1。

### datasource-in-ui · MUST_NOT · new-only · lint:datasource-in-ui

UI 層檔案（`*Activity.kt` / `*Fragment.kt` / `*Screen.kt` / `*ViewModel.kt`）不得直接持有或呼叫 DataSource：Retrofit ApiService、Room `*Dao`、`PersistentManager` / `PreferencesHelper` / `SharedPreferences`、DataStore、Firebase SDK。一律經 Repository，即使該資料只有單一來源。

✗ `class OrderViewModel(private val api: OrderApiService) : ViewModel()`
✓ `class OrderViewModel(private val orderRepository: OrderRepository) : ViewModel()`

例外：既有 `PersistentManager` / `PreferencesHelper` 呼叫點屬 `migrate`，**不要**在功能 PR 內搬遷（涉及資料搬移風險）。
既有違規：170 檔 → [90-migration-ledger.md#m-22](90-migration-ledger.md)

### ui-calls-repository · MUST_NOT · new-only · lint:ui-calls-repository

Composable / Activity / Fragment 不得注入或呼叫 Repository、UseCase、DataSource。取資料一律經 ViewModel（狀態下行、事件上行）。

✗ `@Composable fun OrderList() { val repo: OrderRepository by inject(); … }`
✓ `@Composable fun OrderRoute(viewModel: OrderViewModel = koinViewModel())`

例外：既有 MVP Presenter 畫面不主動改寫（見遷移帳 M-01）。Composable 內禁止 `by inject()` 的裁決見 [91-decisions.md](91-decisions.md) D-09。
既有違規：29 檔 → [90-migration-ledger.md#m-01](90-migration-ledger.md)

### duplicate-source-of-truth · MUST_NOT · new-only · manual

同一種資料只能有一個可寫來源（通常是該 Repository 或其 local DataSource）。其他元件只能觀察它的 Flow，不得各自維護可寫副本，也不得再寫一份進全域狀態。

✗ ViewModel 取到清單後寫進 `AppState`，另一個畫面改從 `AppState` 讀
✓ 兩個畫面各自 collect `orderRepository.getOrdersStream()`

例外：純畫面暫存（表單輸入、捲動位置）不算資料副本，留在 UiState。
既有違規：`AppState.java` 1859 行 god object → [90-migration-ledger.md#m-01](90-migration-ledger.md)

### cross-layer-callback · MUST_NOT · new-only · lint:cross-layer-callback

層與層之間的公開簽章只能是 `suspend fun`（一次性）或 `Flow`（會隨時間變化）。不得用 callback / listener 介面回傳結果。

✗ `fun loadOrders(onSuccess: (List<Order>) -> Unit, onError: (Throwable) -> Unit)`
✓ `suspend fun getOrders(): List<Order>` ／ `fun getOrdersStream(): Flow<List<Order>>`

例外：Android framework 或第三方 SDK 本身是 callback 時，必須在 **data 層**用 `callbackFlow` / `suspendCancellableCoroutine` 收斂，再以 Flow / suspend 向上傳。
> `LiveData` 見 [08-ui-state.md#livedata-new-code](08-ui-state.md)；`Call<T>` / RxJava 回傳型別見 [06-network.md#retrofit-non-suspend](06-network.md)。

### global-state-holder · MUST_NOT · new-only+on-touch · lint:global-state-holder

不得用 `object` 單例、`companion object` / static 可變欄位、或 `Application` 子類別的可變屬性當資料來源、狀態容器或跨畫面傳值管道。

✗ `object GlobalVar { var isProductionEnv = false }`
✓ 注入 `AppConfigRepository`，狀態以 `Flow` 對外；跨模組共享一律 DI 注入介面

例外：編譯期常數（`const val`）、無狀態工具 `object`、DI 容器本身。
既有違規：`GlobalVar.kt` 等 → [90-migration-ledger.md#m-21](90-migration-ledger.md)

### event-bus-for-state · MUST_NOT · new-only · manual

不得用 `:shared:tool:event_bus` 或任何 event bus 傳遞資料、狀態或跨畫面結果 —— 它沒有型別化的呼叫圖，無法靜態追蹤誰改了資料。

✗ `EventBus.post(OrderUpdatedEvent(order))`，另一畫面訂閱後更新自己的狀態
✓ 更新 `orderRepository`，兩端 collect 同一個 Flow；導航回傳值用 `SavedStateHandle`

例外：既有 96 檔 event bus 用法不主動改寫，觸碰時也不要求一併移除（會動到訂閱端）。

### layer-package-mismatch · MUST · new-only · manual

新檔案必須放進所屬層的模組：Composable / Activity / Fragment / ViewModel → `:feature:*` 或 `:app`；Repository 介面與 domain model → `:domain:contract`；UseCase → `:domain:usecase`；Repository 實作 / DataSource / DTO → `:data:*`。

✗ 在 `:feature:common:order` 內新增 `OrderRepositoryImpl`
✓ 介面放 `:domain:contract`、`OrderRepositoryImpl` 放 `:data:repository`、feature 只注入介面

例外：feature 專屬且不跨模組共用的 mapper 與 UiModel 可留在該 feature 模組。介面歸屬的裁決見 [91-decisions.md](91-decisions.md) D-12。

---

## 其他檔案的規則（只給指向，不在這裡重述）

| 主題 | 去哪查 |
|------|-------|
| domain 層禁 Android 型別、禁 import data 實作 | [04-domain-layer.md#android-in-domain](04-domain-layer.md)、[#domain-imports-impl](04-domain-layer.md) |
| UI 不得直接用 DTO / Entity、model 分層細則 | [05-data-layer.md#dto-in-ui](05-data-layer.md) |
| Repository 是否要抽介面 | [05-data-layer.md#repository-needs-interface](05-data-layer.md) |
| UseCase 何時該開、pass-through 是否允許 | [04-domain-layer.md#usecase-single-invoke](04-domain-layer.md)、[91-decisions.md](91-decisions.md) D-13 |
| 對外暴露 Mutable 狀態、ViewModel 持有 Context、one-off event | [08-ui-state.md#mutable-state-exposed](08-ui-state.md)、[#context-in-viewmodel](08-ui-state.md)、[#one-off-event-as-state](08-ui-state.md) |
| 生命週期感知收集狀態 | [09b-compose-state.md#collect-as-state](09b-compose-state.md) |
| dispatcher 注入、`GlobalScope`、suspend main-safe | [11-coroutines-flow.md#hardcoded-dispatcher](11-coroutines-flow.md)、[#global-scope](11-coroutines-flow.md)、[#suspend-not-main-safe](11-coroutines-flow.md) |
| 手動 new 實作、service locator 取依賴 | [03-di.md#manual-impl-instantiation](03-di.md)、[#service-locator-get](03-di.md) |
| 跨模組導航（`:shared:routing` 的 `XxxRouter` + `XxxRoutingInput`） | [12-navigation.md#cross-module-navigation](12-navigation.md) |
| 模組依賴邊、feature 互依、Gradle 設定 | [02-modularization.md](02-modularization.md) |
| 新畫面一律 Compose、禁新增 XML | [09a-compose-api.md#new-xml-layout](09a-compose-api.md)、紅線 E1 |

# 08 · UI 狀態（MVVM + UDF）

**這份管**：ViewModel 如何產生狀態、如何對外暴露 —— UiState 建模、可變狀態封裝、one-off event、loading/error 表達、`SavedStateHandle`、ViewModel 的型別邊界。
**這份不管**：Compose 端怎麼收狀態與拆 composable（→ 09b）、Flow 運算子／scope／dispatcher（→ 11）、導航機制（→ 12）。

**專案標準樣板**：`app/src/main/java/com/kkday/member/view/login_methods/feature/login_methods/LoginMethodsViewModel.kt`。
新 ViewModel **照這一份抄**，不要照抄其他既有 ViewModel（全庫多數 ViewModel 屬待遷移狀態）。

| 主題 | owner |
|------|-------|
| `collectAsStateWithLifecycle`、screen/content 兩層拆分、可重用 composable 不得收 ViewModel | [09b-compose-state.md](09b-compose-state.md) |
| UiState 內的可變集合與穩定性 | [10-compose-performance.md#mutable-collection-in-state](10-compose-performance.md) |
| dispatcher 注入、`GlobalScope`、`runBlocking`、Channel/Flow 選型與取消 | [11-coroutines-flow.md](11-coroutines-flow.md) |
| 導航決策上拋 UI、跨模組 `XxxRouter` | [12-navigation.md](12-navigation.md) |
| DTO / Entity 不得出現在 UiState 或 Composable 參數 | [05-data-layer.md#dto-in-ui](05-data-layer.md) |
| ViewModel 的 DI 註冊（`@KoinViewModel`） | [03-di.md](03-di.md) |

---

## 一、UiState 建模

### uistate-var-property · MUST_NOT · new-only · manual

UiState 必須是 `data class`，所有欄位為 `val` 且帶預設值（`OrderUiState()` 要能直接當 `initialValue`、`@Preview` 資料與測試起點）。UI 層不得寫入 UiState 任何欄位。

✗ `data class OrderUiState(var isLoading: Boolean)`
✓ `data class OrderUiState(val isLoading: Boolean = false, val orders: List<OrderUiModel> = emptyList())`

例外：無。可變集合欄位另見 [10-compose-performance.md#mutable-collection-in-state](10-compose-performance.md)。

### uistate-naming · SHOULD · new-only · manual

畫面狀態型別一律命名 `<畫面>UiState`；禁止 `XxxViewState` / `XxxScreenState` / `XxxUiModel`（`UiModel` 保留給 UiState 內的單筆資料型別）。

✗ `data class OrderScreenState(...)`
✓ `data class OrderUiState(val orders: List<OrderUiModel> = emptyList())`

例外：`XxxState` 保留給 UI logic state holder（`rememberXxxState()` 的回傳型別）。

### scattered-state-streams · SHOULD_NOT · new-only · manual

一個畫面對外的狀態 stream 上限 3 條。彼此需同時更新、有一致性要求的欄位必須收在同一個 UiState；只有「畫面上互不影響、可獨立顯示 loading、更新頻率明顯不同」的區塊才拆。超過 3 條代表該畫面應拆成多個 destination。

✗ 6 條獨立 `StateFlow`（`sortInfoFlow` / `loadingStateFlow` / `alphaStateFlow` …）
✓ `val uiState: StateFlow<VTagUiState>`，需獨立 loading 的區塊才另開一條

例外：`PagingData` 一律獨立（見 `paging-in-uistate`）。
既有違規：`ProductDetailViewModel` 36 條、`MemberPageViewModel` 16 條 → [90-migration-ledger.md#m-07](90-migration-ledger.md)

### content-state-not-sealed · SHOULD · new-only · manual

新畫面「內容區」的互斥狀態（Loading / Success / Error / Empty）用 sealed interface 讓 `when` 窮盡；只有能與內容並存的暫態（`isRefreshing`、`isSubmitting`、訊息）才放外層 data class 欄位。不得用多個 boolean flag 拼出非法組合。

✗ `data class OrderUiState(val isLoading: Boolean, val error: String?, val orders: List<Order>?)`
✓ `data class OrderUiState(val content: OrderContent = OrderContent.Loading, val isRefreshing: Boolean = false)`
✓ `sealed interface OrderContent { data object Loading : OrderContent; data class Success(val orders: List<OrderUiModel>) : OrderContent }`

例外：既有 flag 風格畫面不為此重寫。新畫面不得沿用專案既有的另外三套 loading 機制（`BaseViewModel.showLoading`、Reductor 全域旗標、`ApiResult.Loading`）。

### uistate-resolved-string · MUST_NOT · new-only · manual

UiState 不得攜帶「ViewModel 自行解析出來」的提示／錯誤文字。訊息用 `@StringRes Int`；需帶參數或需區分重試行為時用 sealed `UiError` 攜帶參數，由 UI 端 `stringResource(id, args)` 組裝。

✗ `state.copy(errorMessage = "訂單建立失敗")`
✓ `state.copy(errorRes = R.string.order_create_failed)`

例外：後端回傳、本身就是使用者可見內容的字串（商品名、客服訊息）。`strings.xml` 由 PM 維護（紅線 A2），沒有對應 key 時先詢問。

### paging-in-uistate · MUST_NOT · new-only · manual

`PagingData` 不得放進 UiState data class，必須由 ViewModel 另開一條 `Flow<PagingData<T>>` 並 `cachedIn(viewModelScope)`。

✗ `data class SearchUiState(val results: PagingData<ProductUiModel>)`
✓ `val results: Flow<PagingData<ProductUiModel>> = repository.searchStream(query).cachedIn(viewModelScope)`

例外：無。

---

## 二、狀態的暴露與更新

### mutable-state-exposed · MUST_NOT · new-only+on-touch · lint:mutable-state-exposed

對外可見的屬性型別不得是 `MutableStateFlow` / `MutableSharedFlow` / `MutableLiveData` / `Channel`。可變狀態一律 `private val _x`，另暴露唯讀型別。

✗ `val uiState: MutableStateFlow<OrderUiState> = MutableStateFlow(OrderUiState())`
✓ `private val _uiState = MutableStateFlow(OrderUiState())`
✓ `val uiState: StateFlow<OrderUiState> = _uiState.asStateFlow()`

例外：測試碼。**不要**為此修改 `libs/base` 的 `BaseViewModel.showLoading`（87 檔引用）。
既有違規：11 處 public Mutable + 22 個 public `Channel` → [90-migration-ledger.md#m-04](90-migration-ledger.md)

### mutable-state-inferred · MUST_NOT · new-only+on-touch · lint:mutable-state-inferred

省略型別標註的 `val x = MutableStateFlow(...)` 推斷出來仍是 Mutable，等同對外暴露可變狀態。private 欄位一律加 `_` 前綴，公開欄位一律顯式標唯讀型別。

✗ `val selectedTab = MutableStateFlow(0)`
✓ `private val _selectedTab = MutableStateFlow(0)` + `val selectedTab: StateFlow<Int> = _selectedTab.asStateFlow()`

例外：測試碼。
既有違規：→ [90-migration-ledger.md#m-04](90-migration-ledger.md)

### state-read-then-write · SHOULD · new-only · manual

更新多欄位 UiState 一律 `update { it.copy(...) }`；不得先讀 `.value` 再寫回（並發更新會互相覆蓋）。

✗ `_uiState.value = _uiState.value.copy(isLoading = true)`
✓ `_uiState.update { it.copy(isLoading = true) }`

例外：無。

### async-in-viewmodel-init · MUST_NOT · new-only · manual

ViewModel 的 `init { }` 與建構子不得啟動 coroutine 或非同步載入（測試無法控制時序、沒有訂閱者時就開始耗資源）。改用 lazy 的 `stateIn` pipeline，或提供 idempotent 的載入方法由 UI 呼叫一次。

✗ `init { viewModelScope.launch { loadOrders() } }`
✓ `fun fetchOrders(mode: FetchMode) { if (mode == FetchMode.INITIALIZE && ordersFlow.value != null) return; ... }`

例外：無。

### statein-while-subscribed · SHOULD · new-only · manual

用 `stateIn` 暴露給 UI 的衍生狀態，一律 `stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000L), <明確初始值>)`；5 秒緩衝讓旋轉螢幕期間上游不必重跑，畫面真正離開後才停。5_000 以外的數值不得使用。

✗ `.stateIn(viewModelScope, SharingStarted.WhileSubscribed(), false)`  // 無參數 = stopTimeoutMillis 0，旋轉螢幕即斷開上游重訂閱
✗ `.stateIn(viewModelScope, SharingStarted.Eagerly, null)`  // 上游不停 + null 塞進非 nullable 狀態
✓ `.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000L), OrderUiState())`

初始值一律給 `OrderUiState()` 這種預設實例，不得用 null 代替。
範圍：只管 `stateIn` 暴露的衍生態；ViewModel 自己 `MutableStateFlow` + `asStateFlow()` 持有的狀態沒有上游可停，不適用。
偏離官方之處：nowinandroid 抽共用常數 `WhileUiSubscribed`，本專案沒有這個常數，故寫字面 `5_000L`；常數化列 [90-migration-ledger.md#m-05](90-migration-ledger.md)。
既有違規：`OtpRegisterViewModel.kt:36,40`、`LoginMethodsViewModel.kt:59` 用無參數寫法，`HomeViewModelV2.kt:94` 寫 `5000` → [90-migration-ledger.md#m-05](90-migration-ledger.md)

### eager-sharing-started · SHOULD_NOT · new-only · manual

有上游成本的 pipeline（DB 查詢、網路訂閱、Socket、感測器）不得用 `SharingStarted.Eagerly`。`Lazily` 只在「使用者可能返回該畫面且 pipeline 必須持續運作」時使用，並在 PR 說明理由。

✗ `repository.ordersStream().stateIn(viewModelScope, SharingStarted.Eagerly, emptyList())`
✓ `repository.ordersStream().stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000L), emptyList())`

例外：無上游成本的純轉換（例如 `savedStateHandle.getStateFlow(...)` 的 `map`）。

### saved-state-missing · SHOULD · new-only · manual

跨 process death 需還原的最小輸入（route 參數、篩選條件、輸入草稿）必須存進 `SavedStateHandle`；優先用 `savedStateHandle.getStateFlow(key, default)` 直接當 pipeline 輸入，不要另外手動同步。

✗ `class OrderViewModel(private val orderId: String) : ViewModel()`
✓ `private val _stateFlow = MutableStateFlow(savedStateHandle[KEY_STATE] ?: State())`  // 照 `LoginMethodsViewModel`

例外：可由 repository 低成本重取的資料不需要存。
既有違規：205 個 ViewModel 只有 6 檔使用 → [90-migration-ledger.md#m-07](90-migration-ledger.md)

---

## 三、one-off event

### one-off-event-as-state · MUST_NOT · new-only · manual

ViewModel 不得用 `Channel` / `MutableSharedFlow` / `SingleLiveEvent` / `Event<T>` wrapper 發一次性事件，一律 reduce 成 UiState 欄位。**唯一白名單**（離開 App 的一次性外部動作）：開啟外部 App／瀏覽器／撥號／系統分享、系統權限請求、音效與觸覺回饋、檔案下載或相機等系統 UI 呼叫 —— 這幾類可用 `Channel(Channel.CONFLATED)`，且 channel 必須 private、對外只暴露 `receiveAsFlow()`。

✗ `private val _navigate = MutableSharedFlow<Unit>()`  // 導航、snackbar、dialog、驗證錯誤、重試提示都不在白名單
✓ `state = state.copy(actions = state.actions + State.Action.ShowBindingError(description))`
✓ `private val _openBrowser = Channel<String>(Channel.CONFLATED)` + `val openBrowser = _openBrowser.receiveAsFlow()`

例外：白名單如上，且必須在 PR 說明屬於哪一類。
既有違規：`MutableSharedFlow` 67 檔、`Channel` 45 檔 → [90-migration-ledger.md#m-05](90-migration-ledger.md)

### event-not-cleared · MUST · new-only · manual

以 UiState 表達的一次性訊息必須有消費回呼把該欄位清為 `null` / `false` / 從清單移除；沒有清除路徑的事件欄位視同 bug（每次重組都會重播）。

✗ `state.copy(actions = state.actions + Action.ShowError)` 而 ViewModel 沒有任何移除 action 的方法
✓ `fun onAction(action: State.Action) { state = state.copy(actions = state.actions - action) }`

例外：無。UI 端的 `LaunchedEffect(message)` 觸發方式見 [09b-compose-state.md](09b-compose-state.md)。

---

## 四、ViewModel 邊界

### context-in-viewmodel · MUST_NOT · new-only+on-touch · lint:context-in-viewmodel

ViewModel 的建構子、欄位、方法簽名都不得出現 `Context` / `Application` / `Activity` / `View` / `Fragment` / `Resources` / `NavController`。需要文字或資源時傳 `@StringRes Int` 給 UI 解析。

✗ `class VTagViewModel(private val app: KKdayApp) : AndroidViewModel(app)`
✓ `class VTagViewModel(private val getVTagsUseCase: GetVTagsUseCase) : ViewModel()`

例外：測試碼。
既有違規：16 檔 `AndroidViewModel` + 35 檔 import `Context` + 11 檔方法收 `Activity` → [90-migration-ledger.md#m-06](90-migration-ledger.md)

### legacy-base-viewmodel · MUST_NOT · new-only · manual

新 ViewModel 一律直接繼承 `androidx.lifecycle.ViewModel`，不得繼承 `AndroidViewModel` 或專案的 `BaseViewModel`（後者帶 public 可變 `showLoading` 與 RxJava2 `CompositeDisposable`，繼承等於被綁進兩項待退場技術）。loading 狀態放自己的 UiState 欄位。

✗ `class OrderViewModel : BaseViewModel()`
✓ `@KoinViewModel class OrderViewModel(private val getOrdersUseCase: GetOrdersUseCase) : ViewModel()`

例外：既有畫面維持現狀；**不要**改 `BaseViewModel` 本身（87 檔引用）。
既有違規：→ [90-migration-ledger.md#m-03](90-migration-ledger.md)

### livedata-new-code · SHOULD_NOT · new-only · lint:livedata-new-code

新程式碼不得宣告 `LiveData` / `MutableLiveData`。同一個 ViewModel 內若已有 Flow，新欄位不得再開 LiveData（新舊混用比純舊寫法更難維護）。

✗ `private val _count = MutableLiveData(0)`
✓ `private val _count = MutableStateFlow(0)`

例外：測試碼；既有純 LiveData 的 ViewModel 不強制重寫。
既有違規：64 檔，其中 21 檔與 Flow 混用 → [90-migration-ledger.md#m-02](90-migration-ledger.md)

### no-new-reductor · MUST_NOT · new-only · manual

不得新增 Reductor store / reducer / action：禁止新增 `@AutoReducer`、`@ActionCreator`、新的 `dispatch(...)` 呼叫點，禁止擴充 `AppState` 欄位。新畫面一律 MVVM + UDF（紅線 D4）。

✗ `@AutoReducer object OrderReducer { ... }` / `store.dispatch(OrderActions.load())`
✓ `@KoinViewModel class OrderViewModel(...) : ViewModel()` + `val uiState: StateFlow<OrderUiState>`

例外：既有 Reductor 畫面**不得**為了合規改寫成 MVVM，除非該畫面本來就要重寫。
既有違規：752 處 `dispatch` / 190 檔 → [90-migration-ledger.md#m-01](90-migration-ledger.md)

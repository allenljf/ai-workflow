# 08 · UI 狀態與 ViewModel

**這份管**：UiState 的形狀與不可變性、ViewModel 的職責邊界、狀態怎麼從 ViewModel 流到 UI、一次性事件（one-off event）的做法、state holder 該用 ViewModel 還是 plain class、process death 的還原。
**這份不管**：composable 的參數長相與拆法、`remember` 與 side effect 的機制、Flow 運算子與 dispatcher 注入。

| 需要什麼 | 去哪 |
|---|---|
| composable 參數順序、Route/Screen 拆兩層、事件 lambda 命名 | `09-compose-api` |
| `remember` / `rememberSaveable` / `collectAsStateWithLifecycle` 的機制 | `10-compose-state` |
| StateFlow vs SharedFlow 選型、dispatcher 注入、scope 選擇 | `12-coroutines-flow` |
| 重組過多、`@Immutable`、`ImmutableList` 要不要用 | `11-compose-performance` |
| 錯誤型別怎麼從 data 層往上傳 | `05-data-layer` |
| route 定義與導航參數 | `13-navigation` |
| ViewModel 單元測試 | `15-testing` |

`MutableStateFlow` 外流、ViewModel 持有 `Context`、新程式碼禁用 `LiveData` 是 AGENTS.md 的通用紅線；以下是它們可判定的細則與其餘規則。

---

### uistate-mutable-field · MUST_NOT · new-only+on-touch · regex

UiState 必須是全 `val` 的 data class，集合欄位型別必須是唯讀的 `List` / `Set` / `Map`，且每個欄位都有預設值（讓 `OrderUiState()` 能直接當 `initialValue`、preview 資料與測試起點）。

✗ `data class OrderUiState(var isLoading: Boolean, val orders: MutableList<Order>)`
✓ `data class OrderUiState(val isLoading: Boolean = true, val orders: List<Order> = emptyList())`

例外：無。

### exposed-mutable-state · MUST_NOT · new-only+on-touch · regex

ViewModel 對外只能是唯讀型別：`StateFlow` 走 `_state.asStateFlow()`，Compose State 走 `by mutableStateOf(...)` 搭配 `private set`。可變容器一律 `private`。

✗ `val uiState = MutableStateFlow(OrderUiState())`
✓ `private val _uiState = MutableStateFlow(OrderUiState())` + `val uiState: StateFlow<OrderUiState> = _uiState.asStateFlow()`

例外：測試用的 fake state holder 可直接持有可變型別。

### uistate-naming · SHOULD · new-only · regex

畫面狀態的類別名一律 `<畫面或元件>UiState`，不用 `XxxViewState` / `XxxScreenState` / `XxxUiModel`。

✗ `data class OrderViewState(...)`
✓ `data class OrderUiState(...)`

例外：plain state holder 承載的 UI logic state 命名為 `XxxState`（如 `OrderListState`），不帶 `Ui`。

### split-related-state-streams · SHOULD_NOT · new-only · manual

同一畫面中「必須同時更新才不會出現矛盾畫面」的狀態，不得拆成多條對外 stream。只有兩塊狀態在畫面上互不影響、可各自獨立顯示 loading、更新頻率明顯不同時才拆，上限 2–3 條；再多代表該畫面應拆成多個 destination。

✗ `val orders: StateFlow<List<Order>>` + `val isLoading: StateFlow<Boolean>` + `val error: StateFlow<Int?>`
✓ `val uiState: StateFlow<OrderUiState>`

例外：`Flow<PagingData<T>>` 一律獨立（見 `pagingdata-in-uistate`）。

### ambiguous-status-flags · SHOULD · new-only · manual

互斥的內容狀態（Loading / Success / Empty / Error）用 `sealed interface` + `data object` 表達，讓 `when` 被編譯器強制窮盡；只有能與內容並存的暫態（`isRefreshing`、`isSubmitting`、`userMessage`）才用外層 data class 的欄位。不得用一組可同時為真的 flag 表達互斥狀態。

✗ `data class OrderUiState(val isLoading: Boolean, val orders: List<Order>, val errorRes: Int?)`（可以同時 loading + 有資料 + 有錯）
✓ `data class OrderUiState(val content: OrderContent = OrderContent.Loading, val isRefreshing: Boolean = false)` 搭配 `sealed interface OrderContent { data object Loading; data object Empty; data class Success(val orders: List<Order>); data class Error(@StringRes val messageRes: Int) }`

例外：畫面只有單一區塊、且結構上不存在 empty / error 分支時，可全用欄位。

### pagingdata-in-uistate · MUST_NOT · new-only+on-touch · regex

`PagingData` 內容會隨時間改變，不是不可變型別，不得放進 UiState；必須由 ViewModel 以獨立的 `Flow<PagingData<T>>` 曝露並 `cachedIn(viewModelScope)`。

✗ `data class OrderUiState(val pages: PagingData<Order>)`
✓ `val orders: Flow<PagingData<Order>> = pager.flow.cachedIn(viewModelScope)`

例外：無。

### stored-derived-state · SHOULD_NOT · new-only · manual

可由其他欄位推導的值不得存成獨立欄位（會出現兩份真實來源、且可能不同步），改用 extension property 或 `get()` 推導。

✗ `data class OrderUiState(val orders: List<Order>, val orderCount: Int, val isEmpty: Boolean)`
✓ `val OrderUiState.isEmpty: Boolean get() = orders.isEmpty()`

例外：推導成本高且來源變動頻繁時，可在 pipeline 內算好再存成欄位。

### android-type-in-uistate · MUST_NOT · new-only+on-touch · regex

UiState 欄位不得出現 `Context` / `Activity` / `View` / `Fragment` / `Drawable` / `Bitmap` / `Intent`。文字用 `@StringRes Int`（需帶參數時用攜帶參數的 sealed error type），圖片用 `@DrawableRes Int` 或 URL 字串。

✗ `data class OrderUiState(val icon: Drawable, val message: String)`
✓ `data class OrderUiState(@DrawableRes val iconRes: Int, @StringRes val messageRes: Int? = null)`

例外：`androidx.annotation` 的資源 id 註解本身可用；UiState 必須能在純 JVM 測試中被建構。

### android-type-in-viewmodel · MUST_NOT · migrate · regex

ViewModel 不得注入或持有 `Context` / `Application` / `Resources` / `Activity` / `View` / `Fragment` / `NavController`，也不得為了取字串而繼承 `AndroidViewModel` 或呼叫 `getString()`（已解析的字串在語言切換後不會更新）。

✗ `class OrderViewModel(app: Application) : AndroidViewModel(app) { fun title() = getApplication<Application>().getString(R.string.title) }`
✓ `@HiltViewModel class OrderViewModel @Inject constructor(private val orderRepository: OrderRepository, savedStateHandle: SavedStateHandle) : ViewModel()`

例外：`@ApplicationContext` 注入到 data 層元件（不是 ViewModel）；ViewModel 需要平台能力時改注入一個 domain 介面。

### one-off-event-channel · MUST_NOT · migrate · regex

ViewModel 不得以 `Channel` / `MutableSharedFlow` / `SingleLiveEvent` / `Event<T>` wrapper 曝露一次性事件。官方立場是 events-as-state：事件必須立即 reduce 成 UiState 欄位，因為 producer 活得比 consumer 久時這些機制不保證送達，使用者會漏掉關鍵資訊。

✗ `private val _events = Channel<OrderEvent>()` + `val events = _events.receiveAsFlow()`
✓ `data class OrderUiState(val submittedOrderId: String? = null)`

例外：僅限下方「無法 reduce 的白名單」兩種情況。

### event-without-consumed-callback · MUST · new-only+on-touch · manual

以 UiState 欄位表達的一次性訊息，UI 消費後必須回呼 ViewModel 把該欄位清為 `null` / `false`，且消費動作要包在以該欄位為 key 的 `LaunchedEffect` 內。欄位用名詞（`userMessageRes`、`submittedOrderId`），回呼命名 `xxxShown()` / `xxxHandled()`。

✗ 在 composable body 直接 `if (uiState.userMessageRes != null) snackbarHostState.showSnackbar(...)`（重組就重播、也永遠清不掉）
✓ `LaunchedEffect(uiState.userMessageRes) { uiState.userMessageRes?.let { snackbarHostState.showSnackbar(context.getString(it)); viewModel.userMessageShown() } }`

例外：無。

### viewmodel-navigates · MUST_NOT · migrate · regex

ViewModel 不得決定或執行導航。使用者操作直接造成的導航由 composable 以 `onXxxClick: () -> Unit` 上拋給 NavHost；需 business logic 判定的導航改為 UiState flag，UI 消費後回呼清除。

✗ `fun onSubmit() { viewModelScope.launch { repository.submit(); navController.navigate(OrderDetailRoute(id)) } }`
✓ `fun onSubmit() { viewModelScope.launch { _uiState.update { it.copy(submittedOrderId = orderRepository.submit()) } } }`

例外：無。

### non-atomic-state-update · SHOULD · new-only+on-touch · regex

更新多欄位 UiState 一律用 `update { it.copy(...) }`。讀後寫不是原子操作，兩個 coroutine 同時更新不同欄位時，後者會無聲覆蓋前者。

✗ `_uiState.value = _uiState.value.copy(isRefreshing = true)`
✓ `_uiState.update { it.copy(isRefreshing = true) }`

例外：建構時的一次性初始賦值。

### eager-ui-state-sharing · MUST · new-only+on-touch · regex

由上游 stream 產生的 UiState 一律以 `stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), initialValue)` 曝露。5_000ms 是「訂閱者短暫歸零」的緩衝：螢幕旋轉或短暫切出 App 時，UI 會在 5 秒內重新訂閱，上游不會被停掉再重跑一次；設 0 會讓每次旋轉都重打一輪資料，用 `Eagerly` 則 pipeline 從 ViewModel 建立起就永不停止，背景持續耗電與流量。timeout 抽成專案共用常數，不要散落魔術數字。

✗ `stateIn(viewModelScope, SharingStarted.Eagerly, OrderUiState())`
✓ `stateIn(viewModelScope, WhileUiSubscribed, OrderUiState())`（`val WhileUiSubscribed = SharingStarted.WhileSubscribed(5_000)`）

例外：使用者很可能返回、且 pipeline 需在 back stack 上持續運作（隱藏的 tab）時可用 `Lazily`，需在 PR 說明理由。

### async-work-in-viewmodel-init · MUST_NOT · new-only+on-touch · regex

不得在 ViewModel 的 `init { }` 或建構子內啟動 coroutine——非同步程式碼可能在物件初始化完成前讀寫它，且會讓 `WhileSubscribed` 的省電效果失效。

✗ `init { viewModelScope.launch { loadOrders() } }`
✓ `val uiState = orderRepository.observeOrders().map(::toUiState).stateIn(viewModelScope, WhileUiSubscribed, OrderUiState())`

例外：真的只能命令式載入時，提供 idempotent 的 `initialize()` 由 UI 呼叫一次。

### dispatcher-switch-in-viewmodel · MUST_NOT · new-only+on-touch · regex

ViewModel 必須是 main-safe，但切換執行緒是 data / domain 層的責任；不得用 `withContext(ioDispatcher)` 包住 repository 呼叫（那會讓 data 層的 main-safety 契約變得不明確）。

✗ `viewModelScope.launch { withContext(ioDispatcher) { orderRepository.refresh() } }`
✓ `viewModelScope.launch { orderRepository.refresh() }`

例外：ViewModel 內確有 CPU 密集的純運算時可切 `Default`，但該運算應優先下移到 domain 層。

### unsaved-restorable-state · SHOULD · new-only · manual

跨 process death 必須還原的最小輸入（route 參數 id、篩選條件、輸入草稿）存進 `SavedStateHandle`，優先用 `getStateFlow(key, default)` 讓它直接成為 pipeline 的輸入，而不是另外手動同步。可由 repository 重新取得的資料不要存。

✗ `private var query: String = ""`（process death 後輸入內容消失）
✓ `val query = savedStateHandle.getStateFlow(KEY_QUERY, "")`

例外：重建成本低且使用者不會察覺的畫面。

### screen-state-outside-viewmodel · MUST · new-only+on-touch · manual

需要存取 data / domain 層、或需跨組態變更與 back stack 存活的畫面狀態，必須由 ViewModel 持有；不得放在 `remember` / `rememberSaveable` / Fragment 欄位 / Activity 欄位。

✗ `var orders by remember { mutableStateOf(emptyList<Order>()) }` 搭配 `LaunchedEffect(Unit) { orders = repository.getOrders() }`
✓ `val uiState by viewModel.uiState.collectAsStateWithLifecycle()`

例外：無。

### ui-element-state-in-viewmodel · SHOULD_NOT · new-only · manual

純呈現用的狀態（捲動位置、展開收合、bottom sheet 開關、依 window size class 的版面判斷）不得放進 ViewModel。簡單情況直接寫在 composable；複雜到影響可讀性時抽成標 `@Stable` 的 plain class 加 `rememberXxxState()` 工廠。

✗ `class OrderViewModel : ViewModel() { val isExpanded = MutableStateFlow(false) }`
✓ `var expanded by rememberSaveable { mutableStateOf(false) }`

例外：該狀態同時是 business logic 的輸入（例如展開才觸發載入）時，由 ViewModel 以事件接收，但仍不持有 UI 型別。

### plain-holder-holds-viewmodel · MUST_NOT · new-only+on-touch · regex

plain state holder 不得持有 ViewModel 實例，只能接收值、`StateFlow` 或函式參考。

✗ `class OrderListState(private val viewModel: OrderViewModel)`
✓ `class OrderListState(val listState: LazyListState, private val onRefresh: () -> Unit)`

例外：無。

---

## 無法 reduce 成 state 的白名單

只有這兩種情況可以不走 UiState 欄位，其餘一律違反 `one-off-event-channel`：

1. **來源本來就在 UI 的即發即忘動作**——點擊後開啟外部 App、系統分享、撥號、播放音效。做法是留在 UI 層的 `onClick` 直接執行，ViewModel 只提供資料（例如分享用的 URL）。這類事件根本不該從 ViewModel 發出。
2. **跨畫面的全域通知**（例如 token 失效導致強制登出）——由 app 層單一 collector 消費，且必須有對應的持久狀態作為 fallback，讓事件遺失時下次進入畫面仍能由狀態重新判定。

「下單成功後跳轉付款頁」不在白名單內：它是 business logic 的結果，必須是 `val pendingPaymentUrl: String? = null` 加 consumed 回呼。用 Channel 而漏掉這個事件，等於使用者已扣款但畫面沒跳轉。

## 狀態該放哪

| 狀態性質 | 放哪 |
|---|---|
| 需要 data / domain 層，且要跨組態變更與 back stack 存活 | `OrderUiState` 欄位（ViewModel 持有） |
| process death 後必須還原的最小輸入 | `SavedStateHandle` |
| 只影響呈現，但要撐過組態變更（展開、tab index、輸入草稿） | `rememberSaveable` |
| 只影響呈現且可重建（捲動位置、動畫進度） | `remember` / `rememberLazyListState()` |

## 尚無定論

- **MVI（單一 `onEvent(intent)` 入口）vs 具名 method**：官方文件未表態，官方 sample 走具名 method（`viewModel::onOrderClick` 可直接當 lambda 參數、型別安全、IDE 可追蹤）。**建議**預設用具名 method，只有流程本身就是明確狀態機且需要記錄事件序列時才引入 Intent；若採 MVI，其慣用的 `Channel<SideEffect>` 仍必須改成 UiState 欄位。這是建議不是規則。
- **ViewModel 輸出型別 `StateFlow` vs Compose `State`**：兩者官方都認可。**建議**統一用 `StateFlow`——狀態來源含任何 repository stream 時官方即要求 `StateFlow`，且它能在純 JVM 測試中直接驗證，不需 Compose 測試環境。Compose `State` 只用在 composable 或 plain state holder 內部。

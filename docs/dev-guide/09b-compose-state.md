# 09b · Compose 狀態與副作用

這份管 **composable 內部的狀態與副作用**：state hoisting、screen/content 兩層拆分、`remember` 家族、side effect API 選擇、composition 內禁止做的事。

這份**不管** composable 的公開 API 形狀（那是 09a），也**不管** ViewModel 內部怎麼設計 UiState（那是 08）。

| 你要找的 | 去哪份 |
|---------|-------|
| `modifier`、參數順序、禁止傳 `State<T>`、`@Preview` | [09a-compose-api.md](09a-compose-api.md) |
| UiState 形狀、one-off event、`stateIn`、ViewModel 禁持 Context | [08-ui-state.md](08-ui-state.md) |
| `LazyColumn` 的 `key`、可變集合、延後讀取、重運算成本 | [10-compose-performance.md](10-compose-performance.md) |
| `Dispatchers` 注入、`GlobalScope`、取消例外 | [11-coroutines-flow.md](11-coroutines-flow.md) |
| 新程式碼禁用 `LiveData`（含 `observeAsState`） | [08-ui-state.md](08-ui-state.md) |
| 埋點曝光怎麼接 `snapshotFlow` | [16-tracking.md](16-tracking.md) |

---

## 一、狀態的來源與提升

### collect-as-state · MUST NOT · new-only+on-touch · lint:collect-as-state

Compose 收集 `Flow` / `StateFlow` 一律 `collectAsStateWithLifecycle()`。禁止 `collectAsState()`，也禁止在 composable 內直接讀 `stateFlow.value`。

✗ `val uiState by viewModel.uiState.collectAsState()`
✓ `val uiState by viewModel.uiState.collectAsStateWithLifecycle()`

例外：KMP 共用碼（本專案目前無）。
既有違規：`collectAsState(` 103 檔 vs `collectAsStateWithLifecycle` 10 檔；反例 `MemberPageFragment.kt:222-242` 連續 12 個 → [90-migration-ledger.md#m-10](90-migration-ledger.md)（批次遷移優先級最高）

### screen-content-split · SHOULD · new-only · manual

畫面級 composable 拆成兩層：**stateful 層**（`XxxRoute`／`XxxScreen(viewModel = koinViewModel())`）只負責取 ViewModel、collect UiState、把事件轉成 lambda；**stateless 層**（`XxxContent(uiState, onXxx)`）只收資料與 lambda，不認識 ViewModel。

✗ `@Composable fun OrderScreen(vm: OrderViewModel = koinViewModel()) { /* 300 行 UI 直接讀 vm */ }`
✓ `@Composable fun OrderRoute(vm: OrderViewModel = koinViewModel()) { val s by vm.uiState.collectAsStateWithLifecycle(); OrderContent(s, vm::onRetry) }`

例外：無 ViewModel 的純展示畫面不需要拆。

### viewmodel-in-reusable-composable · MUST NOT · new-only+on-touch · manual

ViewModel 只能出現在 stateful 層的預設參數位置。不得把 ViewModel 當參數往下傳給子 composable，也不得在子 composable 內呼叫 ViewModel 方法。

✗ `fun SearchResultPage(searchResultVM: SearchResultViewModel) { … searchResultVM.trackFilterMenuPg() … }`
✓ `fun SearchResultContent(filters: List<FilterUiModel>, onFilterShown: () -> Unit)`

例外：無。可重用 composable 持有 ViewModel 等於無法 preview、無法測試。

### duplicated-hoisted-state · MUST NOT · new-only · manual

同一份語意的狀態只能有一個真實來源。兩個以上 composable 要讀寫同一份狀態時，提升到**所有讀寫者的最低共同祖先**；不得各自 `remember` 一份再手動同步。

✗ 父子各 `remember { mutableStateOf(selectedTab) }`，再用 `LaunchedEffect` 互相對齊
✓ 父層 `var selectedTab by rememberSaveable { mutableStateOf(0) }`，子層收 `selectedTab: Int, onTabChange: (Int) -> Unit`

例外：無。

### screen-data-in-remember · MUST NOT · new-only · manual

畫面資料（API 回應、清單內容、分頁結果）不得存在 `remember` / `rememberSaveable`，必須由 ViewModel 持有（跨 process death 用 `SavedStateHandle`）。

✗ `val orders = remember { mutableStateOf(emptyList<Order>()) }` 後在 `LaunchedEffect` 內打 API 塞進去
✓ ViewModel 內 `_uiState.update { it.copy(orders = …) }`，UI 只收 `uiState.orders`

例外：純 UI 元素狀態（展開／收合、選中頁籤）不算畫面資料，見下一條。

### ui-state-not-saveable · SHOULD · new-only · manual

需在設定變更（旋轉、字型縮放）後保留的 UI 元素狀態用 `rememberSaveable`；型別非 Bundle 支援時提供 `mapSaver` / `listSaver`，或改由 ViewModel 保存。

✗ `var expanded by remember { mutableStateOf(false) }`  // 旋轉後收合
✓ `var expanded by rememberSaveable { mutableStateOf(false) }`

例外：只在單次組合內有意義的狀態（動畫進度、拖曳暫態）用 `remember` 即可。

---

## 二、remember 與可觀察狀態

### unremembered-state · MUST · new-only · manual

在 composable 主體建立的狀態物件（`mutableStateOf`、`Animatable`、state holder 實例）必須包在 `remember { }` / `rememberSaveable { }` 內。

✗ `var query by mutableStateOf("")`  // 每次重組都重建，永遠是空字串
✓ `var query by rememberSaveable { mutableStateOf("") }`

例外：ViewModel 內的 `by mutableStateOf(…) private set` 不在此限（不在 composition 中）。

### state-mutated-in-place · MUST NOT · new-only+on-touch · manual

不得就地修改 state 所持有的物件或集合；一律 `copy()` 或建立新集合後重新賦值。`remember { mutableListOf() }` 這類不可觀察容器不得當 UI 狀態，需要可觀察集合時用 `mutableStateListOf`。

✗ `val items = remember { mutableListOf<Product>() }; items.add(p)` ／ `state.value.form.name = "x"`
✓ `var items by remember { mutableStateOf(emptyList<Product>()) }; items = items + p`

例外：無。就地修改不會通知 snapshot 系統，症狀是「資料改了畫面不更新」。
> UiState 欄位不得宣告成 `MutableList` 等可變集合型別 → [10-compose-performance.md](10-compose-performance.md)

### derived-state-misuse · MUST NOT · new-only+on-touch · manual

`derivedStateOf` 必須包在 `remember` 內，且**只能**用在「來源狀態變動頻率明顯高於衍生結果」的情境（如 `listState.firstVisibleItemIndex > 0`）。單純讀取 UiState 欄位或做字串拼接、加總、格式化，一律直接算。

✗ `val title by remember { derivedStateOf { uiState.value.title } }`  // `HomeV2Screen` 連續 18 個
✓ `val showTopBar by remember { derivedStateOf { listState.firstVisibleItemIndex > 0 } }`

例外：無。同頻情況下 `derivedStateOf` 不會減少任何重組，只增加成本。

---

## 三、副作用

**先用這張表選 API，再往下看規則。** 判斷順序由上而下，第一個成立的就是答案。

| 你要做的事 | 用哪個 |
|-----------|-------|
| 使用者點擊／輸入觸發的動作 | 事件 lambda（`onClick`）交給 ViewModel，**不是** effect |
| 進入組合時啟動協程，key 變更時重啟 | `LaunchedEffect(key)` |
| 使用者事件中要啟動協程（捲動、開關 drawer） | `rememberCoroutineScope()` + `scope.launch` |
| 長時間 effect 內要用到會變動的 lambda／值 | `rememberUpdatedState`（**不是**把它加進 key） |
| 需要註冊／反註冊（listener、observer、Socket） | `DisposableEffect` + `onDispose` |
| 把 Compose 狀態同步給非 Compose 物件（analytics property、Window flag） | `SideEffect` |
| 把 callback／listener 來源轉成 `State` | `produceState` + `awaitDispose` |
| 要用 Flow operator 處理 Compose State（debounce、曝光埋點） | `LaunchedEffect` 內 `snapshotFlow { }` |

### side-effect-in-composable-body · MUST NOT · new-only+on-touch · manual

composable 主體不得執行副作用：寫入外層／全域變數、送埋點、更新 ViewModel 狀態、呼叫 `Random()` / `System.currentTimeMillis()` / `Date()` 等非冪等 API。也不得依賴 composable 的執行順序或執行次數。

✗ `@Composable fun ProductCard(p: Product) { tracker.logImpression(p.id); Text(p.name) }`
✓ `LaunchedEffect(p.id) { tracker.logImpression(p.id) }`

例外：無。composable 可能每影格執行一次，也可能被 skip。

### io-in-composition · MUST NOT · new-only+on-touch · manual

composition 中不得做 I/O 或高成本操作：`SharedPreferences` 讀寫、File／Room 同步查詢、JSON 解析、`runBlocking`、Bitmap 解碼、網路呼叫。也不得在 composable 內呼叫 UseCase / Repository / ApiService。（紅線 E3）

✗ `@Composable fun Header() { val name = PersistentManager.getUserName() … }`
✓ ViewModel 在協程內取得後放進 UiState，composable 只讀 `uiState.userName`

例外：`remember(key) { }` 內做**純運算**的快取可接受；I/O 仍不可以。
> 排序／過濾等重運算的處理見 [10-compose-performance.md](10-compose-performance.md)

### effect-key-incomplete · MUST · new-only · manual

`remember` / `LaunchedEffect` / `DisposableEffect` / `produceState` 的 block 內若讀取參數或外部可變值，這些值必須列為 key。唯二例外：以 `rememberUpdatedState` 包裝的值，或由無 key 的 `remember` 產生因此永不變動的值。

✗ `LaunchedEffect(Unit) { viewModel.load(orderId) }`  // orderId 變了不會重載
✓ `LaunchedEffect(orderId) { viewModel.load(orderId) }`

例外：無。key 不完整的症狀是「導到舊目標、送到舊參數的埋點」。

### launched-effect-unit-key · SHOULD NOT · new-only · manual

不應使用 `LaunchedEffect(Unit)` / `LaunchedEffect(true)`。僅當確實需要「跟隨呼叫點生命週期且只執行一次」時可用，且必須在該行加註理由。

✗ `LaunchedEffect(true) { onScreenShown(pinName) }`
✓ `LaunchedEffect(Unit) { onScreenShown() } // 僅需在畫面首次進入時送一次 PV`

例外：見上方註記要求；block 內引用的 lambda 仍須依下一條包裝。

### stale-lambda-in-effect · MUST · new-only · manual

長時間執行的 effect（`delay`、`while`、`collect`、註冊 observer）內若引用外部傳入的 lambda 或頻繁變動的值，必須以 `rememberUpdatedState` 包裝後使用，而不是列入 key（列入 key 會讓 effect 反覆重啟）。

✗ `LaunchedEffect(onTimeout) { delay(3000); onTimeout() }`
✓ `val currentOnTimeout by rememberUpdatedState(onTimeout); LaunchedEffect(Unit) { delay(3000); currentOnTimeout() }`

例外：無。

### empty-on-dispose · MUST · new-only · manual

需要反註冊的資源（`LifecycleEventObserver`、`BroadcastReceiver`、SDK listener、Socket 監聽）必須用 `DisposableEffect` 註冊，`onDispose` 不得為空區塊。

✗ `DisposableEffect(Unit) { socket.addListener(l); onDispose { } }`
✓ `DisposableEffect(socket) { socket.addListener(l); onDispose { socket.removeListener(l) } }`

例外：無。空 `onDispose` 等於宣告洩漏。

### scope-created-in-composable · MUST NOT · new-only · manual

composable 內不得自建 `CoroutineScope(...)`，也不得直接用 `viewModelScope.launch`。啟動協程只能透過 `LaunchedEffect` 或 `rememberCoroutineScope()`。

✗ `val scope = CoroutineScope(Dispatchers.Main)` ／ `Button(onClick = { viewModelScope.launch { … } })`
✓ `val scope = rememberCoroutineScope()`；長時間工作交給 ViewModel 方法

例外：無。
> `GlobalScope`、dispatcher 注入見 [11-coroutines-flow.md](11-coroutines-flow.md)

### ui-anim-in-viewmodel · MUST NOT · new-only · manual

Compose UI 狀態的動畫 suspend 函式（`animateScrollToItem`、`DrawerState.open/close`、`Animatable.animateTo`）不得在 `viewModelScope` 或任何非組合範圍的 scope 中呼叫。

✗ ViewModel 內 `viewModelScope.launch { listState.animateScrollToItem(0) }`
✓ UI 端 `val scope = rememberCoroutineScope()`，由 `scope.launch { listState.animateScrollToItem(0) }` 觸發

例外：無。`LazyListState` 等 UI 狀態不該被 ViewModel 持有。

# 10 · Compose 狀態與副作用

**管**：composable 內狀態的建立、持有、提升，以及副作用 API（`LaunchedEffect` 家族）的選擇與正確寫法。
**不管**：UiState 的欄位設計與一次性事件、composable 的簽名與命名、重組次數與 stability、Flow 的建構與 `stateIn`。
本檔是 AGENTS.md 通用紅線 13、14 的細則；與紅線衝突時以紅線為準。

| 想問的事 | 去 |
|---|---|
| UiState 要一包還是拆多個？一次性事件怎麼傳？ViewModel 對外暴露什麼型別？ | `08-ui-state` |
| composable 命名、`modifier` 參數、參數順序、`@Preview` | `09-compose-api` |
| 這樣會不會重組太多次？`@Immutable` 要不要加？`LazyColumn` 的 key / contentType | `11-compose-performance` |
| Flow 怎麼建、`SharingStarted` 選哪個、dispatcher 怎麼注入 | `12-coroutines-flow` |
| 導航事件往哪送、`NavController` 放哪 | `13-navigation` ／ composable 怎麼測 → `15-testing` |

## 一、狀態放哪一層

依序問，第一個答「是」就停：

1. **來自 Repository／需要跨畫面存活／程序被殺後要復原？** → ViewModel（復原用 `SavedStateHandle`）
2. **兩個以上 composable 要讀寫同一份？** → 提升到它們的**最低共同祖先**
3. **只有這個 composable 用，而且是 UI 元素狀態？** → `remember` / `rememberSaveable`

「UI 元素狀態」＝展開收合、選中頁籤、捲動位置、輸入游標與草稿。API 回應、清單資料、送出結果都**不是**，一律 ViewModel。
`remember` 只擋重組；`rememberSaveable` 還擋配置變更與程序重建，但只能存 Bundle 支援的型別（否則要 `mapSaver` / `listSaver`）。兩者都擋不住「離開畫面再回來」。

```kotlin
@Composable                                     // ① stateful：認識 ViewModel，本身不畫東西
fun OrderRoute(onOrderClick: (String) -> Unit, viewModel: OrderViewModel = hiltViewModel()) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    OrderScreen(uiState = uiState, onRetry = viewModel::retry, onOrderClick = onOrderClick)
}

@Composable                                     // ② stateless：只認識資料與 lambda，可 preview、可測
fun OrderScreen(uiState: OrderUiState, onRetry: () -> Unit, onOrderClick: (String) -> Unit,
                modifier: Modifier = Modifier) { /* ... */ }
```

## 二、副作用 API 選擇

| 你要做的事 | 用 |
|---|---|
| 進入組合時、或 key 變更時跑 suspend 工作 | `LaunchedEffect(key)` |
| 由使用者事件（onClick）觸發 suspend 工作 | `rememberCoroutineScope().launch { }` |
| 註冊需要對稱反註冊的東西（observer、receiver、SDK listener） | `DisposableEffect(key) { … onDispose { } }` |
| 每次成功重組後，把值同步給非 Compose 管理的物件 | `SideEffect { }` |
| 把 callback / suspend 的外部來源轉成 `State` | `produceState(initial, key) { … awaitDispose { } }` |
| 要用 Flow operator 處理 Compose State（debounce、distinctUntilChanged） | `LaunchedEffect` 內 `snapshotFlow { }` |
| effect 內要用到最新的 lambda，但不想因此重啟 effect | `rememberUpdatedState(lambda)` |
| 從高頻 state 推出低頻結果（`index > 0`） | `remember { derivedStateOf { } }` |

```kotlin
val scope = rememberCoroutineScope()                          // 事件觸發：不能用 LaunchedEffect
Button(onClick = { scope.launch { snackbarHostState.showSnackbar(msg) } }) { Text("Send") }
SideEffect { analytics.setUserProperty("tier", user.tier) }   // 同步給非 Compose 物件
LaunchedEffect(listState) {                                   // Compose State → Flow
    snapshotFlow { listState.firstVisibleItemIndex }
        .distinctUntilChanged().collect(tracker::onFirstVisibleChanged)
}
```

推導值的來源在 ViewModel（API、DB、使用者選擇）→ 用 Flow 的 `map` / `combine` + `stateIn`，別搬進 composition；來源是 Compose 自己的 state（`LazyListState`、`ScrollState`）→ 用 `derivedStateOf`，不要用 `LaunchedEffect` 每幀回寫進 ViewModel。

## 三、規則

### unremembered-mutable-state · MUST · new-only+on-touch · regex

在 `@Composable` 主體建立的狀態物件（`mutableStateOf`、`Animatable`、state holder）必須包在 `remember { }` 或 `rememberSaveable { }` 內。

✗ `var name by mutableStateOf("")`
✓ `var name by remember { mutableStateOf("") }`

例外：無 · source: https://developer.android.com/develop/ui/compose/state

### incomplete-keys · MUST · new-only+on-touch · manual

`remember` / `LaunchedEffect` / `DisposableEffect` / `produceState` 的 lambda 內若讀取會變動的參數或變數，該變數必須列為 key；只有 `rememberUpdatedState` 包過的值與無 key `remember` 產生的值可以不列。

✗ `LaunchedEffect(Unit) { viewModel.load(orderId) }`
✓ `LaunchedEffect(orderId) { viewModel.load(orderId) }`

例外：無 · source: https://developer.android.com/develop/ui/compose/side-effects

### invisible-state-mutation · MUST_NOT · new-only+on-touch · regex

不得用非 snapshot 的可變容器當狀態，也不得就地修改 state 持有的物件或集合——兩者都不會通知 snapshot 系統，畫面不會更新。

✗ `val items = remember { mutableListOf<Item>() }` ／ `user.value.name = "Jane"`
✓ `val items = remember { mutableStateListOf<Item>() }` ／ `user = user.copy(name = "Jane")`

例外：無 · source: https://developer.android.com/develop/ui/compose/state

### collect-without-lifecycle · MUST · new-only+on-touch · regex

在 composable 訂閱 `Flow` / `StateFlow` 一律用 `collectAsStateWithLifecycle()`（`androidx.lifecycle:lifecycle-runtime-compose`），也不得在 composable 內直接讀 `stateFlow.value`。

✗ `val uiState by viewModel.uiState.collectAsState()`
✓ `val uiState by viewModel.uiState.collectAsStateWithLifecycle()`

例外：跨平台共用碼無此 API 時可用 `collectAsState()` · source: https://developer.android.com/develop/ui/compose/state

### stateful-stateless-not-split · MUST · new-only · manual

畫面層 composable 必須拆兩層：stateful 層取得 ViewModel、collect state、把事件轉成 lambda；stateless 層只收資料與 lambda，不認識 ViewModel。

✗ `fun OrderScreen(viewModel: OrderViewModel = hiltViewModel()) { /* 直接畫 UI */ }`
✓ `fun OrderRoute(viewModel: OrderViewModel = hiltViewModel())` → `fun OrderScreen(uiState, onRetry)`

例外：無 · source: 官方 sample nowinandroid

### viewmodel-passed-down · MUST_NOT · new-only+on-touch · manual

ViewModel 只能出現在 stateful 畫面層的預設參數位置，不得當參數往下傳給子 composable。

✗ `OrderList(viewModel = viewModel)`
✓ `OrderList(orders = uiState.orders, onOrderClick = viewModel::onOrderClick)`

例外：無 · source: https://developer.android.com/topic/architecture/ui-layer/stateholders

### mutable-state-as-parameter · MUST_NOT · new-only+on-touch · regex

被提升狀態的 composable 參數必須是唯讀值 + 事件 lambda；不得把 `MutableState`、`MutableStateFlow`、setter 物件當參數傳下去。

✗ `fun NameField(name: MutableState<String>)`
✓ `fun NameField(name: String, onNameChange: (String) -> Unit, modifier: Modifier = Modifier)`

例外：無 · source: https://developer.android.com/develop/ui/compose/state-hoisting

### duplicated-state-source · MUST · new-only+on-touch · manual

同一份語意的狀態只能有一個真實來源。兩個以上 composable 要讀寫它時，提升到最低共同祖先，不得各自 `remember` 一份再手動同步。

✗ `MessageList()` 與 `JumpToBottomButton()` 各自 `rememberLazyListState()`
✓ 父層 `val listState = rememberLazyListState()` 後傳給兩者

例外：無 · source: https://developer.android.com/develop/ui/compose/state-hoisting

### screen-data-in-remember · MUST_NOT · new-only+on-touch · manual

畫面資料（API 回應、清單內容、分頁結果）不得放在 `remember` / `rememberSaveable`，必須由 ViewModel 持有。

✗ `var orders by rememberSaveable { mutableStateOf(emptyList<Order>()) }`
✓ `val uiState by viewModel.uiState.collectAsStateWithLifecycle()`

例外：無 · source: https://developer.android.com/develop/ui/compose/state-hoisting

### unsaved-ui-element-state · SHOULD · new-only · manual

要在配置變更或程序重建後保留的 UI 元素狀態（展開收合、選中頁籤、輸入草稿）用 `rememberSaveable`；型別非 Bundle 支援時提供 `mapSaver` / `listSaver`，或改由 ViewModel 保存。

✗ `var expanded by remember { mutableStateOf(false) }`（旋轉後收合）
✓ `var expanded by rememberSaveable { mutableStateOf(false) }`

例外：狀態本來就該隨畫面重建而重置（例如動畫進度） · source: https://developer.android.com/develop/ui/compose/state

### side-effect-in-composition · MUST_NOT · new-only+on-touch · manual

`@Composable` 主體不得執行副作用：寫入外層變數、送埋點、更新 ViewModel 狀態、呼叫 `Random()` / `System.currentTimeMillis()` 等非冪等 API。副作用只能放事件 lambda 或副作用 API。

✗ `analytics.logScreenView(screen)`（直接寫在 body）
✓ `LaunchedEffect(screen) { analytics.logScreenView(screen) }`

例外：無 · source: https://developer.android.com/develop/ui/compose/side-effects

### expensive-work-in-composition · MUST_NOT · new-only+on-touch · manual

`@Composable` 主體不得執行阻塞或高成本工作：檔案／DB 同步查詢、`SharedPreferences` 讀寫、JSON 解析、`runBlocking`、Bitmap 解碼、排序過濾與正則。改由 ViewModel 算好傳入，或以 `remember(key)` 快取。

✗ `val sorted = orders.sortedBy { it.date }`（每次重組都排序）
✓ `val sorted = remember(orders) { orders.sortedBy { it.date } }`（更好：在 ViewModel 算）

例外：無 · source: https://developer.android.com/develop/ui/compose/performance/bestpractices

### composition-order-dependency · MUST_NOT · new-only+on-touch · manual

不得依賴 composable 的執行順序、執行次數或是否被略過。composable 可能被跳過、可能每幀執行、可能平行執行。

✗ `var shownCount = 0` 在子 composable 內累加以計算曝光數
✓ `LaunchedEffect(itemId) { tracker.logImpression(itemId) }`

例外：無 · source: https://developer.android.com/develop/ui/compose/mental-model

### coroutine-outside-effect-api · MUST · new-only+on-touch · regex

composable 內啟動協程只能用 `LaunchedEffect`（進入組合時）或 `rememberCoroutineScope()`（事件觸發）；不得用 `GlobalScope`、自建 `CoroutineScope(...)`，也不得在 composable 內直接呼叫 `viewModelScope.launch`。

✗ `Button(onClick = { GlobalScope.launch { … } })`
✓ `val scope = rememberCoroutineScope()` 後 `scope.launch { … }`

例外：無 · source: https://developer.android.com/develop/ui/compose/side-effects

### unit-key-effect · SHOULD_NOT · new-only · regex

`LaunchedEffect(Unit)` / `LaunchedEffect(true)` 只在「跟隨呼叫點生命週期且只跑一次」時可用，且必須加註理由、block 內的 lambda 要用 `rememberUpdatedState` 包裝。

✗ `LaunchedEffect(Unit) { navigateTo(uiState.nextRoute) }`（state 變更不重啟，導到舊目標）
✓ `LaunchedEffect(uiState.nextRoute) { … }`；真的只跑一次才 `LaunchedEffect(Unit) { // 只在進場倒數一次 }`

例外：無 · source: https://developer.android.com/develop/ui/compose/side-effects

### unwrapped-lambda-in-long-effect · MUST · new-only+on-touch · manual

長時間執行的 effect（`delay`、`while`、`collect`、註冊 observer）內引用的外部 lambda 或高頻值，必須用 `rememberUpdatedState` 包裝，而不是列為 key——列為 key 會讓 effect 每次重組都重啟。

✗ `LaunchedEffect(onTimeout) { delay(5_000); onTimeout() }`
✓ `val current by rememberUpdatedState(onTimeout)` 後 `LaunchedEffect(Unit) { delay(5_000); current() }`

例外：無 · source: https://developer.android.com/develop/ui/compose/side-effects

### missing-ondispose · MUST · new-only+on-touch · regex

需要反註冊的資源（`LifecycleEventObserver`、`BroadcastReceiver`、SDK listener）必須用 `DisposableEffect` 註冊並在 `onDispose` 反註冊；`onDispose` 不得是空區塊。非 suspend 的訂閱若用 `produceState`，必須在 `awaitDispose { }` 取消。

✗ `LaunchedEffect(Unit) { lifecycle.addObserver(observer) }`
✓ `DisposableEffect(lifecycleOwner) { lifecycle.addObserver(observer); onDispose { lifecycle.removeObserver(observer) } }`

例外：無 · source: https://developer.android.com/develop/ui/compose/side-effects

### misused-derived-state-of · MUST · new-only+on-touch · regex

`derivedStateOf` 必須包在 `remember { }` 內，且只用於「來源變更頻率明顯高於結果變更頻率」。由參數直接算得的值（字串拼接、加總、格式化）不得用 `derivedStateOf`，直接算即可。

✗ `val fullName by remember { derivedStateOf { "$first $last" } }` ／ `val show by derivedStateOf { … }`
✓ `val showButton by remember { derivedStateOf { listState.firstVisibleItemIndex > 0 } }`

例外：無 · source: https://developer.android.com/develop/ui/compose/side-effects

### ui-animation-suspend-in-viewmodel · MUST_NOT · new-only+on-touch · manual

不得在 `viewModelScope` 或任何非組合範圍的 scope 呼叫 Compose UI 的動畫 suspend 函式（`animateScrollToItem`、`DrawerState.open/close`、`Animatable.animateTo`）——那裡沒有 `MonotonicFrameClock`。

✗ `viewModelScope.launch { drawerState.close() }`
✓ `val scope = rememberCoroutineScope()` 後 `scope.launch { drawerState.close() }`

例外：無 · source: https://developer.android.com/develop/ui/compose/state-hoisting

## 四、尚無定論

**UI 元素狀態的保存界線**：官方未明說哪些該用 `rememberSaveable`、哪些該進 `SavedStateHandle`。業界主流做法（建議，非規則）：使用者會察覺「App 被殺掉後沒了很奇怪」的狀態（輸入草稿、多步驟表單進度）放 `SavedStateHandle`；純視覺狀態（展開、頁籤、捲動位置）放 `rememberSaveable`。兩邊都說得通時選 ViewModel，它比較好測。

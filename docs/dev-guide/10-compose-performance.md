# 10 · Compose 效能（重組、穩定性、清單）

**這份管**：重組成本、三階段（composition / layout / draw）與延後讀取 state、LazyList 的 key / contentType / item 尺寸、UiState 穩定性策略、Compose 效能結論的成立前提。

**這份不管**：Composable 參數慣例與 `modifier` 參數（[09a-compose-api.md](09a-compose-api.md)）、state hoisting 與 side effect API 選擇（[09b-compose-state.md](09b-compose-state.md)）、UiState 欄位語意與 one-off event（[08-ui-state.md](08-ui-state.md)）、App 啟動與 Baseline Profile（[15-performance.md](15-performance.md)）。

跨檔主題（只在對應檔案定義，這裡不重述）：

> Compose 收集 Flow 用 `collectAsStateWithLifecycle` → [09b-compose-state.md#collect-as-state](09b-compose-state.md)
> `derivedStateOf` 的 remember 與適用條件 → [09b-compose-state.md#derived-state-misuse](09b-compose-state.md)
> composition 內做 I/O → [09b-compose-state.md#io-in-composition](09b-compose-state.md)
> 自訂 modifier 不用 `Modifier.composed` → [09a-compose-api.md#composed-modifier](09a-compose-api.md)
> UiState 欄位一律 `val` → [08-ui-state.md#uistate-var-property](08-ui-state.md)
> 效能結論必須在 release + R8 build 量測 → [15-performance.md#measure-perf-on-release](15-performance.md)
> Baseline Profile → [15-performance.md#baseline-profile-setup](15-performance.md)
> ViewModel 端衍生狀態用 Flow `map` / `combine` + `stateIn` → [11-coroutines-flow.md](11-coroutines-flow.md)

**貫穿全檔的一句話**：state 讀得越晚，重組範圍越小。composition 讀 → 整棵子樹重組；layout 讀（`Modifier.offset { }`）→ 只重跑 layout；draw 讀（`Modifier.graphicsLayer { }`、`drawBehind`）→ 只重畫。下面多條規則都是這句的具體化。

---

## 一、Lazy 清單

### lazy-list-no-key · MUST · new-only+on-touch · lint:lazy-list-no-key

`LazyColumn` / `LazyRow` / `LazyVerticalGrid` 的 `items()` / `itemsIndexed()` 必須傳 `key`，且 key 必須是資料本身的穩定唯一 id（primitive / enum / Parcelable）。禁止用 list index 或含 index 的組合字串當 key。

✗ `items(products) { ProductCard(it) }`
✗ `items(products.size, key = { i -> "waterfall_$i" }) { ... }`  // index 等同沒有身分
✓ `items(products, key = { it.id }) { product -> ProductCard(product) }`

例外：資料真的沒有 id（純靜態、不會增刪排序的固定清單）時可省略，需在 PR 說明。
既有違規：113 檔（142 檔有 LazyColumn，只 29 檔帶 key）→ [90-migration-ledger.md#m-12](90-migration-ledger.md)。既有清單屬批次遷移，不要在功能 PR 內全掃。

### lazy-list-no-content-type · SHOULD · new-only · manual

同一個 lazy layout 內出現兩種以上版型（banner / card / ad / footer）時必須傳 `contentType`，否則不同版型之間無法重用 composition。

✗ `items(feedItems, key = { it.id }) { when (it) { is Banner -> ...; is Card -> ... } }`
✓ `items(feedItems, key = { it.id }, contentType = { it.type }) { ... }`

### paging-index-as-key · MUST · new-only+on-touch · manual

搭配 Paging 3 的 lazy layout 必須用 `LazyPagingItems` 的 `itemKey { }` 與 `itemContentType { }`；禁止只傳 `itemCount` 而以 index 當 key。

✗ `items(count = items.itemCount, key = { index -> "waterfall_$index" }) { ... }`
✓ `items(count = items.itemCount, key = items.itemKey { it.id }, contentType = items.itemContentType()) { ... }`

既有違規：`MemberPageScreen` 等 → [90-migration-ledger.md#m-12](90-migration-ledger.md)

### lazy-item-zero-size · MUST · new-only · manual

lazy item 內載入非同步內容（`AsyncImage`、遠端決定尺寸）時，該元素必須先有確定尺寸（`size()` / `height()` / `aspectRatio()`），不得讓 item 首次量測為 0px。

✗ `AsyncImage(model = product.imageUrl, contentDescription = null)`
✓ `AsyncImage(model = product.imageUrl, contentDescription = null, modifier = Modifier.fillMaxWidth().aspectRatio(16f / 9f))`

### nested-same-direction-scroll · MUST NOT · new-only · manual

純 Compose 容器之間，禁止把 lazy layout 放進同方向的 `Modifier.verticalScroll` / `horizontalScroll` 容器（無限高度量測，直接 throw）。header / 清單 / footer 用單一 lazy layout 的 `item {}` + `items()` 組合。

✗ `Column(Modifier.verticalScroll(rememberScrollState())) { Header(); LazyColumn { ... } }`
✓ `LazyColumn { item { Header() }; items(products, key = { it.id }) { ... }; item { Footer() } }`

例外：方向相反（垂直清單內放 `LazyRow`）不受此限；View ↔ Compose 互通的嵌套見 [17-interop-views-compose.md#nested-same-axis-scroll](17-interop-views-compose.md)。

### column-scroll-for-long-list · SHOULD · new-only · manual

長度未知、來自 API、或可能超過一個畫面高度的清單必須用 `LazyColumn` / `LazyRow`。只有項目數固定且很少（約 10 個以內、不含圖片）才可用 `Column` + `verticalScroll` + `forEach`。

✗ `Column(Modifier.verticalScroll(state)) { products.forEach { ProductCard(it) } }`
✓ `LazyColumn { items(products, key = { it.id }) { ProductCard(it) } }`

---

## 二、重組成本與延後讀取

### composable-heavy-work · MUST NOT · new-only+on-touch · lint:composable-heavy-work

禁止在 composable 函式本體直接做排序、過濾、`groupBy`、字串格式化、正則、日期解析或 JSON 解析。必須包進 `remember(keys) { }` 或上移到 ViewModel。紅線 E3。

✗ `val sorted = products.sortedBy { it.price }`
✓ `val sorted = remember(products) { products.sortedBy { it.price } }`  // 更好：在 ViewModel 排好

例外：`@Preview` 內的假資料組裝。

### remember-missing-key · MUST · new-only · manual

`remember { }` 的 lambda 內若讀到任何外部參數或變數，這些變數必須全部列為 key，否則輸入改變後仍回傳舊值。

✗ `val filtered = remember { products.filter { it.available } }`  // products 變了不會重算
✓ `val filtered = remember(products) { products.filter { it.available } }`

> 高頻來源（`rememberLazyListState()`、`rememberScrollState()`、輸入文字）推導低頻值時用 `remember { derivedStateOf { } }`，判定條件見 [09b-compose-state.md#derived-state-misuse](09b-compose-state.md)。

### animated-modifier-non-lambda · MUST · new-only+on-touch · manual

由滾動或動畫「每幀」驅動的值，必須用 lambda 版 modifier 把讀取延後到 layout / draw phase。禁止用 `Modifier.offset(x =, y =)`、`Modifier.padding(dp)`、`Modifier.alpha()`、`Modifier.scale()`、`Modifier.rotate()`、`Modifier.background(animatedColor)` 承載動畫值。

✗ `Modifier.offset(y = with(LocalDensity.current) { scrollState.value.toDp() })`
✗ `Modifier.alpha(animatedAlpha)`
✓ `Modifier.offset { IntOffset(0, scrollState.value) }`  // layout phase
✓ `Modifier.graphicsLayer { alpha = animatedAlpha }`  // draw phase

例外：一次性、非每幀的靜態位移（用 `StyleDictionary.kkSpacing300` 等 token）不受此限。

### backwards-write · MUST NOT · new-only · manual

禁止在 composable 函式本體（composition 期間）寫入任何已被讀取的 state，包含在 `Modifier.onSizeChanged` / `onGloballyPositioned` / `onPlaced` 的 lambda 內寫入會被 composition 讀取的 state。所有寫入放事件 callback、`LaunchedEffect`、`SideEffect` 或 `rememberCoroutineScope().launch`。

✗ `if (items.isEmpty()) { showEmpty = true }`  // composable 本體直接寫
✓ `LaunchedEffect(items) { showEmpty = items.isEmpty() }`

例外：需要依子元素尺寸排版時改用 `Column` / `Row` / `SubcomposeLayout` / 自訂 `Layout`，不要靠回寫 state。

### boxed-primitive-state · MUST · new-only · manual

原始型別的 state 一律用特化 API，避免每次寫入 autoboxing。

✗ `var count by remember { mutableStateOf(0) }`
✓ `var count by remember { mutableIntStateOf(0) }`  // 另有 mutableLongStateOf / mutableFloatStateOf / mutableDoubleStateOf

既有違規：約 407 處 → [90-migration-ledger.md#m-12](90-migration-ledger.md)（Android Lint 的 `AutoboxingStateCreation` 可偵測）

---

## 三、穩定性（照 D-06 裁決）

### mutable-collection-in-state · MUST NOT · new-only+on-touch · lint:mutable-collection-in-state

UiState 欄位與 composable 參數不得使用 `MutableList` / `ArrayList` / `MutableMap` / `MutableSet` / `HashMap`。

✗ `data class OrderUiState(val items: MutableList<OrderItem>)`
✓ `data class OrderUiState(val items: List<OrderItem>)`

### stability-annotation-lie · MUST NOT · new-only · manual

禁止對「屬性會在 Compose 不知情的情況下變動」的型別標 `@Immutable` / `@Stable`：含 `var` 欄位、內含可變集合、或會被外部程式碼就地修改的物件。標註是承諾，違背會造成畫面不更新。

✗ `@Immutable data class Cart(var count: Int, val items: MutableList<Item>)`
✓ `@Immutable data class Cart(val count: Int, val items: List<Item>)`

### premature-stability-fix · MUST NOT · new-only · manual

不得為了「讓所有 composable 都 skippable」而全面套 `@Immutable` / `ImmutableList` / wrapper class。必須先用 Layout Inspector recomposition count 或 composition tracing 證明該 composable 在熱路徑（滾動、動畫、輸入）上重複重組，才做穩定性修復。新 UiState 的集合欄位就用 `List`。

✗ 開一張「全部 UiState 補 @Immutable」的清票並批次改 100 個 data class
✓ 量到訂單清單滾動時 `OrderCard` 重組次數異常 → 只對該路徑上的型別補標註

例外：量測前提見 [15-performance.md#measure-perf-on-release](15-performance.md)。

### uistate-stability-default · MUST · new-only · manual

新增的 UiState / UiModel 一律用**不帶任何穩定性標註**的形狀：`data class` + 全欄位 `val` + 集合欄位用唯讀 `List` / `Map` / `Set`。Kotlin 2.1 的 strong skipping 已預設開啟，未量測就標 `@Immutable` / `@Stable`、改用 `ImmutableList` 或另包 wrapper class 屬過度優化，reviewer 直接退（裁決 D-06）。

✗ `@Immutable data class OrderUiState(val items: ImmutableList<OrderItem>)`  // 無量測依據
✓ `data class OrderUiState(val items: List<OrderItem> = emptyList(), val isLoading: Boolean = false)`

例外：熱路徑（滾動、動畫、輸入）已量到重複重組時，才對該路徑上的型別補標註，量測依據照 `perf-claim-without-evidence` 附在 PR。
本專案沒有 stability configuration file（官方推薦的集中宣告方式），也沒有 `composeCompiler {}` DSL。**不要在功能 PR 內自建** `compose_compiler_config.conf` —— 該基建與刪除失效的 `kotlinCompilerExtensionVersion = 1.5.15` 併為同一支 build-logic PR → [90-migration-ledger.md#m-25](90-migration-ledger.md)。
欄位 `val` 的完整要求 → [08-ui-state.md#uistate-var-property](08-ui-state.md)；可變集合禁令 → 同檔 `mutable-collection-in-state`。

### perf-claim-without-evidence · SHOULD · new-only · manual

PR 描述與程式碼註解不得出現未附證據的效能主張。本專案**沒有 compose compiler metrics 管道**（無 `composeCompiler {}` DSL、無 reports 產出），因此「已經 skippable」「減少了重組」「strong skipping 會處理」一律是推論，不得當成採用某寫法的理由。

要主張效能改善，必須附下列之一：Layout Inspector 的 recomposition count 前後數字、Macrobenchmark 數據、Perfetto / systrace 區段。反之，**以效能為由增加程式碼複雜度**（撒 `@Immutable`、改 `ImmutableList`、只為減少重組而拆 composable）在量測前一律不做。

✗ 註解 `// 標 @Immutable 讓 OrderCard 變 skippable`
✓ PR 描述：「Layout Inspector：訂單清單滾動時 `OrderCard` 重組 42 → 3 次（附截圖）」

例外：純可讀性或正確性的重構不需要量測，但描述裡同樣不得宣稱效能收益。
量測環境（release + R8）→ [15-performance.md#measure-perf-on-release](15-performance.md)。

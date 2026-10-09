# 11 · Compose 效能

**管**：怎麼讓重組更少、更晚、更便宜——延後讀取 state、lambda 版 modifier、stability 與 strong skipping、lazy layout 的 key / contentType，以及效能該怎麼量。
**不管**：狀態正確性與副作用 API（那是狀態問題，不是效能問題）、UiState 欄位設計、App 冷啟動與記憶體、Baseline Profile 與 Macrobenchmark 的建置設定。
**先確認**：本檔規則全部是「量到才修」。沒有量測數據就套 stability 修復，見 `unmeasured-stability-fix`。

| 想問的事 | 去 |
|---|---|
| `remember` 的 key、`derivedStateOf` 該不該用、composition 內不能做什麼 | `10-compose-state` |
| `collectAsStateWithLifecycle`、副作用 API 選哪個 | `10-compose-state` |
| UiState 要一包還是拆多個 | `08-ui-state` |
| 冷啟動、ANR、記憶體、Baseline Profile、Macrobenchmark、CI 效能防線 | `16-performance` |
| Flow 端的 `distinctUntilChanged` / `stateIn` | `12-coroutines-flow` |
| `modifier` 參數的簽名規範、自訂 modifier 怎麼寫 | `09-compose-api` |

## 一、三階段與延後讀取

每一幀都會經過三個階段，**state 在哪個階段被讀取，就只重跑那一階段之後的部分**：

```
composition（要顯示什麼）→ layout（放哪裡、多大）→ drawing（畫出來）
```

在 composable 本體讀 state = composition 階段讀 = 三階段全跑。把讀取延後到 modifier 的 lambda 內，就只從 layout 或 drawing 開始跑：

| 你在做的事 | 讀在 composition（貴） | 延後讀（便宜） |
|---|---|---|
| 位移 | `Modifier.offset(y = dp)`、`padding(dp)` | `Modifier.offset { IntOffset(0, y) }`（layout） |
| 透明度／縮放／旋轉／位移動畫 | `Modifier.alpha(a)`、`rotate()`、`scale()` | `Modifier.graphicsLayer { alpha = a }`（drawing） |
| 顏色動畫 | `Modifier.background(color)` | `Modifier.drawBehind { drawRect(color) }`（drawing） |

同樣道理套在參數上：高頻值跨 composable 邊界時傳 `() -> T` 而不是 `T`，讓讀取發生在最深的使用點。

「量到才修」的排查順序：① 確認在 minify 的 build 量測 → ② lazy layout 有沒有 key / contentType → ③ item 內非同步圖片是否 0px → ④ 用 Layout Inspector 的 recomposition count 或 composition tracing 找熱點 → ⑤ 看動畫值是不是走了 composition 階段的 modifier。前四步沒做完不要開始改型別。

## 二、規則

### animated-value-in-composition-modifier · MUST · new-only+on-touch · regex

由捲動或動畫每幀驅動的值，不得傳進在 composition 階段讀取的 modifier 多載（`offset(dp)`、`padding(dp)`、`alpha()`、`rotate()`、`scale()`、`background(color)`），必須改用對應的 lambda 版。

✗ `Modifier.offset(y = scrollDp).alpha(animatedAlpha).background(animatedColor)`
✓ `Modifier.offset { IntOffset(0, scrollPx) }.graphicsLayer { alpha = animatedAlpha }.drawBehind { drawRect(color) }`

例外：值只在使用者操作後變更一次（例如展開／收合的兩個固定值） · source: https://developer.android.com/develop/ui/compose/phases

### high-frequency-value-as-plain-param · SHOULD · new-only · manual

高頻變化的值（捲動 offset、動畫值、手勢位置）跨 composable 邊界時，參數型別用 `() -> T` provider，不要用已解出的 `T`，否則呼叫端每幀重組。

✗ `Header(scrollOffset = listState.firstVisibleItemScrollOffset)`
✓ `Header(scrollOffset = { listState.firstVisibleItemScrollOffset })`

例外：值本來就低頻變化 · source: https://developer.android.com/develop/ui/compose/performance/bestpractices

### whole-uistate-passed-to-subtrees · SHOULD · new-only · manual

不得把整包 `uiState` 當單一參數傳給多個子樹；任一欄位變更會讓所有子樹一起重組。每個子樹只收自己要的欄位。

✗ `Header(state); OrderList(state); Footer(state)`
✓ `Header(title = state.title); OrderList(orders = state.orders); Footer(total = state.total)`

例外：子樹確實用到 state 的多數欄位 · source: https://developer.android.com/develop/ui/compose/phases

### backwards-write-in-composition · MUST_NOT · new-only+on-touch · manual

不得在 composable 本體寫入任何已被讀取的 state（backwards write），那會造成無限重組。所有寫入必須發生在事件 callback、`LaunchedEffect`、`SideEffect` 或 `rememberCoroutineScope().launch` 內。

✗ `Text("$count"); count++`（同一個 composable 本體內）
✓ `Button(onClick = { count++ }) { Text("+") }; Text("$count")`

例外：無 · source: https://developer.android.com/develop/ui/compose/performance/bestpractices

### state-write-in-layout-callback · MUST_NOT · new-only+on-touch · regex

不得在 `Modifier.onSizeChanged` / `onGloballyPositioned` / `onPlaced` 的 lambda 內寫入會被 composition 讀取的 state——那是跨階段的 backwards write。需要依子元素尺寸排版時改用 `Column` / `Row` / 自訂 `Layout` / `SubcomposeLayout`。

✗ `Modifier.onSizeChanged { headerHeightPx = it.height }` 後在別處讀 `headerHeightPx` 當 padding
✓ `Column { Header(); Body() }` 讓 layout 系統處理相對位置

例外：寫入的 state 只被 layout 或 drawing 階段讀取（例如只給 `graphicsLayer` 用） · source: https://developer.android.com/develop/ui/compose/phases

### boxed-primitive-state · MUST · new-only+on-touch · regex

原始型別的 state 必須用 `mutableIntStateOf` / `mutableLongStateOf` / `mutableFloatStateOf` / `mutableDoubleStateOf`，不得用會 autoboxing 的 `mutableStateOf(0)`。Android Lint 規則 `AutoboxingStateCreation` 會報。

✗ `var progress by remember { mutableStateOf(0f) }`
✓ `var progress by remember { mutableFloatStateOf(0f) }`

例外：可為 null 的原始型別（`mutableStateOf<Int?>(null)`） · source: https://developer.android.com/develop/ui/compose/performance/bestpractices

### lazy-items-without-key · MUST · new-only+on-touch · regex

`LazyColumn` / `LazyRow` / `LazyVerticalGrid` 的 `items()` 必須帶 `key`（AGENTS 紅線 15 的細則）：key 必須是 Bundle 可存的型別（primitive、enum、Parcelable），不得用 list index，Paging 場景必須用 `itemKey { }`。

✗ `items(orders) { … }` ／ `items(orders.itemCount) { i -> … }`
✓ `items(orders, key = { it.id }) { … }` ／ `items(count = orders.itemCount, key = orders.itemKey { it.id })`

例外：清單內容永不變動且無內部狀態 · source: https://developer.android.com/develop/ui/compose/lists

### lazy-items-without-content-type · SHOULD · new-only · manual

同一個 lazy layout 內出現兩種以上 item 版型（banner / card / ad / footer）時必須傳 `contentType`，讓 Compose 只在同型別間重用 composition。Paging 用 `itemContentType { }`。

✗ `items(feed, key = { it.id }) { FeedItem(it) }`（`FeedItem` 內部 `when` 分三種版型）
✓ `items(feed, key = { it.id }, contentType = { it.type }) { FeedItem(it) }`

例外：只有一種版型 · source: https://developer.android.com/develop/ui/compose/lists

### non-lazy-scrolling-list · MUST_NOT · new-only+on-touch · regex

長度未知或可能超過一個畫面的清單不得用 `Column` + `verticalScroll` + `forEach`（全部一次組合）；也不得把 lazy layout 放進同方向的 scroll 容器（會直接 crash）。header / 清單 / footer 用單一 lazy layout 的 `item {}` + `items()` 組合。

✗ `Column(Modifier.verticalScroll(state)) { Header(); LazyColumn { … } }`
✓ `LazyColumn { item { Header() }; items(photos, key = { it.id }) { … }; item { Footer() } }`

例外：項目數固定且很少（10 個以內、不含圖片） · source: https://developer.android.com/develop/ui/compose/lists

### zero-size-async-item · MUST · new-only+on-touch · manual

lazy layout 內載入非同步內容（遠端圖片）的 item 必須指定 `size()` / `height()` / `aspectRatio()`；首次量測為 0px 會讓整份清單被組合出來。

✗ `AsyncImage(model = url, contentDescription = null)`
✓ `AsyncImage(model = url, contentDescription = null, modifier = Modifier.fillMaxWidth().aspectRatio(16f / 9f))`

例外：尺寸已由父容器固定 · source: https://developer.android.com/develop/ui/compose/lists

### false-stability-annotation · MUST_NOT · new-only+on-touch · regex

不得對「屬性會在 Compose 不知情下變動」的型別標 `@Immutable` / `@Stable`：含 `var` 欄位、內含 `MutableList` / `MutableMap` / `Array`、或會被外部 mutate 的物件。標了等於承諾，違背承諾的結果是畫面不更新。

✗ `@Immutable data class Cart(val items: MutableList<Item>)`
✓ `@Immutable data class Cart(val items: ImmutableList<Item>)`

例外：無 · source: https://developer.android.com/develop/ui/compose/performance/stability/fix

### unannotated-recreated-ui-model · SHOULD · migrate · manual

strong skipping 對 unstable 參數改用 `===` 比較，因此「每次都由 mapper 產生新實例」的 UI model 即使內容相同也會觸發重組。經量測確認在熱路徑上重複重組的 UI model，加 `@Immutable`（或列入 stability configuration file）。

✗ `data class OrderUiModel(val id: String, val title: String)`（mapper 每次回傳新實例）
✓ `@Immutable data class OrderUiModel(val id: String, val title: String)`

例外：未量測到重複重組時不要動——見 `unmeasured-stability-fix` · source: https://developer.android.com/develop/ui/compose/performance/stability/strongskipping

### unstable-collection-in-composable-param · SHOULD · new-only · manual

新寫的 composable 參數與 UI state 內的集合，用 `ImmutableList` / `PersistentList`（kotlinx-collections-immutable），或把該型別所在 package 列入 stability configuration file。不得曝露 `List` / `Map` / `Set` 又期待 skipping 生效。

✗ `fun OrderList(orders: List<Order>)`
✓ `fun OrderList(orders: ImmutableList<Order>)` ／ `data class OrderUiState(val orders: ImmutableList<Order> = persistentListOf())`

例外：既有大量 `List` 簽名改型別成本過高時，改走 stability configuration file · source: https://developer.android.com/develop/ui/compose/performance/stability/fix

### unmeasured-stability-fix · MUST_NOT · new-only · manual

不得為了「讓所有 composable 都 skippable」而全面加 `@Immutable`、換 `ImmutableList` 或包 wrapper class。必須先用 recomposition count 或 composition tracing 證明該 composable 在熱路徑（捲動、動畫、輸入）上重複重組。

✗ PR 說明：「把所有 data class 加上 `@Immutable`」——無任何量測依據
✓ PR 說明：「trace 顯示 `OrderRow` 捲動時每幀重組，因 `tags: List<String>` unstable；改 `ImmutableList` 後降為 0」

例外：無 · source: https://developer.android.com/develop/ui/compose/performance/stability/fix

### redundant-lambda-remember · MAY · new-only · regex

strong skipping 會自動 memoize 捕獲外部變數的 lambda，因此不需要為 `onClick` 之類的 lambda 手動包 `remember`。確實要關掉個別 lambda 的 memoize 才用 `@DontMemoize`。

✗ `val onClick = remember(order.id) { { onOrderClick(order.id) } }`
✓ `Button(onClick = { onOrderClick(order.id) })`

例外：無 · source: https://developer.android.com/develop/ui/compose/performance/stability/strongskipping

### perf-claim-from-debug-build · MUST · new-only · manual

任何 Compose 效能結論（卡頓、捲動流暢度、重組次數）只能在 `isMinifyEnabled = true` 的 build、且未連接 debugger 的情況下量測。debug build 的觀察結果不得作為優化依據或「Compose 比較慢」的證據。

✗ 用 debug build 手動滑一滑就下結論
✓ 在 minify 開啟的 variant 量測，或用 Macrobenchmark 對 release 量測；PR 註明量測 variant

例外：無 · source: https://developer.android.com/develop/ui/compose/performance

### missing-compose-compiler-report-switch · SHOULD · migrate · regex

建置腳本必須提供以 Gradle property 開關的 compose compiler metrics / reports 輸出，並集中管理 `stabilityConfigurationFiles`，否則 stability 假設無從查證。設定放 convention plugin，不要每個模組各寫一份。

✗ 各模組 `build.gradle.kts` 完全沒有 `composeCompiler { }` 區塊
✓ convention plugin 內 `composeCompiler { reportsDestination.set(…); stabilityConfigurationFiles.add(…) }`，由 `-PenableComposeCompilerReports=true` 開啟

例外：無 · source: 官方 sample nowinandroid ／ https://developer.android.com/develop/ui/compose/compiler

## 三、compiler metrics 怎麼讀

開啟後每個模組會產出三份檔案，看兩件事就好：

- `*-composables.txt`：每個 composable 標 `restartable` / `skippable`。**熱路徑上的 composable 不是 `skippable` 才是問題**；一次性的畫面層 composable 不 skippable 沒關係。
- `*-classes.txt`：每個類別標 `stable` / `unstable`，並列出害它 unstable 的欄位。先看熱路徑用到的 UI model。
- `*-module.json`：skippable 比例的總計，適合當「有沒有變糟」的趨勢指標，不適合當目標值。

判讀順序：先從 Layout Inspector 找出重組次數異常的 composable → 回到 `*-composables.txt` 確認它不 skippable → 到 `*-classes.txt` 找出是哪個參數 unstable → 只修那一個型別。不要拿 `*-module.json` 的比例當 KPI 去追。

## 四、尚無定論

**集合穩定性策略**：官方在 stability/fix 頁面並列四種做法（開 strong skipping、immutable collections、stability configuration file、wrapper class），明說視情況選擇。業界主流做法（建議，非規則）：以 **stability configuration file 為主、`ImmutableList` 為輔**——官方 sample nowinandroid 就是這個組合：根目錄一份 `compose_compiler_config.conf` 列自家 data model package 與 `java.time` 型別，由 convention plugin 掛上；新寫的 UI state 才直接用 `ImmutableList`；wrapper class 只用在無法修改的第三方型別。注意 conf 檔不是免費的：列入即等於承諾該型別不會被 mutate，因此那些型別必須同步強制 `val` 且不曝露可變集合。

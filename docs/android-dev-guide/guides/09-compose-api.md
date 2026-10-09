# 09 · Composable 公開 API

**這份管**：composable 的函式簽名長什麼樣——命名、參數順序、`modifier` 參數、slot 設計、`@Preview` 規範、無障礙底線。凡是「別人要怎麼呼叫這個 composable」的問題都在這裡。
**這份不管**：函式內部怎麼寫、狀態從哪裡來、重組成本、顏色與間距的取值方式。

| 需要什麼 | 去哪 |
|---|---|
| UiState 形狀、事件怎麼從 ViewModel 出來、state holder 選型 | `08-ui-state` |
| `remember` / `LaunchedEffect` / 狀態提升機制 / 收集 Flow | `10-compose-state` |
| 穩定性、重組次數、lazy list 的 `key`、延後讀取 | `11-compose-performance` |
| 間距 / 圓角 / 字級 / 顏色 token、字串資源 | `14-design-system` |
| route 定義與導航參數 | `13-navigation` |
| composable 測試與 screenshot test | `15-testing` |

「可重用 composable 必須有 `modifier` 參數」是 AGENTS.md 的通用紅線；以下是它的細則與其餘規則。

---

### composable-naming · MUST · new-only · regex

發出 UI 且回傳 `Unit` 的 `@Composable` 必須用 PascalCase 名詞命名（是「一個東西」不是「一個動作」）；有回傳值的 `@Composable` 依一般 Kotlin 函式慣例用 camelCase。發出 UI 的 composable 不得同時回傳值。

✗ `@Composable fun drawOrderCard(order: Order)`、`@Composable fun OrderCard(order: Order): Boolean`
✓ `@Composable fun OrderCard(order: Order, modifier: Modifier = Modifier)`、`@Composable fun bodyTextColor(): Color`

例外：無。

### remember-factory-naming · MUST · new-only · regex

內部使用 `remember` 並回傳物件的 `@Composable` 工廠函式，必須以 `remember` 前綴命名。

✗ `@Composable fun orderListState(): OrderListState = remember { OrderListState() }`
✓ `@Composable fun rememberOrderListState(): OrderListState = remember { OrderListState() }`

例外：無。

### composable-param-order · MUST · new-only+on-touch · manual

參數順序固定為：必填參數 → `modifier: Modifier = Modifier` → 其他選填參數 → 最後一個 `@Composable` content lambda。`modifier` 必須是第一個可選參數，讓呼叫端能只填必填參數加 modifier。

✗ `fun OrderCard(order: Order, enabled: Boolean = true, modifier: Modifier = Modifier)`
✓ `fun OrderCard(order: Order, modifier: Modifier = Modifier, enabled: Boolean = true, content: @Composable ColumnScope.() -> Unit)`

例外：無。

### missing-modifier-param · MUST · new-only+on-touch · manual

每個發出 UI 的公開 composable 必須有且僅有一個名為 `modifier`、型別 `Modifier`、預設值 `Modifier` 的參數。不得出現第二個 modifier 參數（`contentModifier`、`iconModifier`），需要調整內部元件時改用 slot。

✗ `@Composable fun OrderCard(order: Order, contentModifier: Modifier = Modifier)`
✓ `@Composable fun OrderCard(order: Order, modifier: Modifier = Modifier)`

例外：`@Preview` 函式；不發出 UI 只回傳值的 composable；只被單一父容器使用、不對外的 private 子 composable。

### modifier-not-applied-to-root · MUST · new-only+on-touch · manual

傳入的 `modifier` 必須原封不動套在該 composable 最外層的 layout，且位於 chain 最前面。不得丟棄、不得改套到內部子元件、不得在它之前先接自己的 size / padding（那樣呼叫端就覆寫不掉）。

✗ `Column(modifier = Modifier.fillMaxWidth().then(modifier)) { ... }`、`Column(modifier = Modifier.padding(16.dp)) { ... }`（參數被丟掉）
✓ `Column(modifier = modifier.padding(AppTheme.spacing.medium)) { ... }`

例外：無。

### state-param-in-composable · MUST_NOT · new-only+on-touch · regex

composable 參數不得是 `State<T>` / `MutableState<T>` / `MutableStateFlow<T>` 或任何 setter 容器；一律傳「值 + 事件 lambda」。傳可變容器會讓子元件變成第二個真實來源。

✗ `@Composable fun OrderFilter(query: MutableState<String>)`
✓ `@Composable fun OrderFilter(query: String, onQueryChange: (String) -> Unit, modifier: Modifier = Modifier)`

例外：Compose 官方本身就設計成 hoisted holder 的型別（`LazyListState`、`ScrollState`、`SnackbarHostState`）可直接當參數。

### viewmodel-param-in-composable · MUST_NOT · new-only+on-touch · regex

可重用 composable 與 list item composable 不得接收 ViewModel、ViewModel 的方法容器物件或 `NavController`；只接收顯示所需的資料與事件 lambda。ViewModel 型別只能出現在畫面最外層 route composable 的預設參數位置。

✗ `@Composable fun OrderRow(viewModel: OrderViewModel)`
✓ `@Composable fun OrderRow(order: Order, onOrderClick: (String) -> Unit, modifier: Modifier = Modifier)`

例外：`@Composable fun OrderRoute(viewModel: OrderViewModel = hiltViewModel())` 這一層。

### screen-not-split-stateful-stateless · MUST · new-only · manual

每個畫面拆兩層：對外的 `XxxRoute` 取得 ViewModel、collect state、把 state 與 method reference 往下傳；internal 的 `XxxScreen(uiState, onXxx)` 完全 stateless。`@Preview` 與 UI 測試一律針對 stateless 那層。

✗ 單一 `OrderScreen(viewModel: OrderViewModel = hiltViewModel())` 內同時 collect 狀態與繪製畫面
✓ `OrderRoute` 內 `OrderScreen(uiState = uiState, onOrderClick = viewModel::onOrderClick, modifier = modifier)`

例外：完全沒有 ViewModel 的靜態畫面。

### event-lambda-naming · SHOULD · new-only · regex

事件參數命名為 `on` + 動詞 + 目標，型別用 lambda 而非自訂 interface。

✗ `clickListener: OnOrderClickListener`、`callback: (String) -> Unit`、`handler: () -> Unit`
✓ `onOrderClick: (String) -> Unit`、`onRetryClick: () -> Unit`

例外：Compose 既有慣例名（`onValueChange`、`onDismissRequest`、`onCheckedChange`）照用。

### bloated-composable-param · SHOULD · new-only · manual

composable 只接收它真正用到的資料，不接收整個 domain model，也不接收把全部狀態與 callback 打包的 wrapper 物件——後者會讓元件無法在其他情境重用，且任一欄位變動就觸發重組。

✗ `@Composable fun OrderTitle(order: Order)`（只用到 `order.title`）
✓ `@Composable fun OrderTitle(title: String, modifier: Modifier = Modifier)`

例外：欄位超過 4–5 個且語意成組時，傳該畫面的 UI model 比拆散成一堆參數清楚。

### slot-instead-of-flags · SHOULD · new-only · manual

當元件開始長出「要不要顯示某塊內容」的布林或 enum 開關時，改成 slot（`@Composable () -> Unit` 參數）由呼叫端決定。主要 slot 命名 `content` 並放在最後成為 trailing lambda；需要提供版面資訊時用 scope receiver。

✗ `fun OrderCard(showBadge: Boolean, badgeText: String?, showTrailingIcon: Boolean)`
✓ `fun OrderCard(modifier: Modifier = Modifier, trailing: @Composable () -> Unit = {}, content: @Composable ColumnScope.() -> Unit)`

例外：只有兩種固定樣式且不會再擴充時，enum 參數比 slot 簡單。

### composable-default-values · SHOULD · new-only · manual

選填參數必須給預設值，讓呼叫端能只填必填參數；一組相關的預設值集中在同檔案的 `XxxDefaults` object，不要散在簽名裡。視覺類預設值取自 theme。

✗ `fun OrderCard(order: Order, modifier: Modifier, containerColor: Color)`（呼叫端每次都得重填）
✓ `fun OrderCard(order: Order, modifier: Modifier = Modifier, containerColor: Color = OrderCardDefaults.containerColor)`

例外：無。

### preview-with-viewmodel · MUST_NOT · new-only+on-touch · regex

`@Preview` 不得預覽會取得 ViewModel 或需要 DI / 網路 / 檔案 IO 的 composable；預覽資料一律用假資料常數或 `PreviewParameterProvider`。

✗ `@Preview @Composable fun OrderRoutePreview() { OrderRoute() }`
✓ `@Preview @Composable private fun OrderScreenPreview() { AppTheme { OrderScreen(uiState = OrderUiState(), onOrderClick = {}) } }`

例外：無。

### preview-signature · MUST · new-only · regex

`@Preview` 函式必須同時標 `@Composable`、宣告為 `private`、無參數（`@PreviewParameter` 提供的除外）、以專案 theme 包裹、命名 `XxxPreview`。

✗ `@Preview @Composable fun previewCard(order: Order) { OrderCard(order) }`
✓ `@Preview @Composable private fun OrderCardPreview(@PreviewParameter(OrderPreviewProvider::class) order: Order) { AppTheme { OrderCard(order) } }`

例外：無。

### duplicated-preview-variants · SHOULD · new-only · manual

要驗證深色模式、字型縮放、螢幕尺寸時，用內建或自訂的 multipreview 註解，不要複製多個 `@Preview`。

✗ `@Preview @Preview(uiMode = UI_MODE_NIGHT_YES) @Preview(fontScale = 2f)`
✓ `@PreviewLightDark`、`@PreviewFontScales`、`@PreviewScreenSizes`

例外：無。

### missing-content-description · MUST · new-only+on-touch · regex

傳達資訊的 `Image` / `Icon` 必須提供取自字串資源的 `contentDescription`；純裝飾必須明確傳 `null`，不得省略、不得填空字串或圖檔名。描述講「這是什麼／按了會怎樣」，不要包含「圖示」「按鈕」等由系統補上的字。

✗ `Icon(painterResource(R.drawable.ic_delete), contentDescription = "ic_delete")`
✓ `Icon(painterResource(R.drawable.ic_delete), contentDescription = stringResource(R.string.order_delete))`

例外：外層已用 `Modifier.semantics(mergeDescendants = true)` 或按鈕本身已有可見文字標籤時，內部圖示傳 `null` 以免重複朗讀。

### small-touch-target · MUST · new-only+on-touch · manual

可點擊元件的觸控目標至少 48dp × 48dp。圖示視覺尺寸只有 24dp 時，用 `IconButton` 或 `Modifier.minimumInteractiveComponentSize()` 擴大可點區，不得只靠視覺大小決定。

✗ `Icon(..., modifier = Modifier.size(24.dp).clickable { onDeleteClick() })`
✓ `IconButton(onClick = onDeleteClick) { Icon(..., modifier = Modifier.size(24.dp)) }`

例外：可點區是整列 / 整張卡片時，該列本身即已滿足尺寸。

---

## 尚無定論

- **設計系統元件要不要開放外觀覆寫參數**（`colors`、`textStyle`）：官方 Material3 的做法是把一組顏色收成單一 `colors` 參數，並用 `XxxDefaults.colors(...)` 工廠給預設值。**建議**新元件先不開覆寫參數，等真的出現第二個需要不同外觀的呼叫端再開，並照 `XxxDefaults` 形式加；一次開一堆覆寫參數會讓元件簽名膨脹又沒人用。這是建議不是規則。
- **公開 composable 要不要一律配 screenshot test**：官方工具鏈仍在演進。**建議**設計系統模組的元件配，feature 模組的畫面只在關鍵流程配。細節見 `15-testing`。

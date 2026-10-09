# 09a · Compose API 慣例

這份管 **composable 函式的公開 API 形狀**：`modifier` 參數、參數順序與型別、命名、slot、`@Preview`、Material 版本與 Accompanist。

這份**不管**狀態提升、`remember`、side effect（那是 09b），也不管重組效能與 LazyList（那是 10）。寫任何 `@Composable` 都必須讀這份。

| 你要找的 | 去哪份 |
|---------|-------|
| 收集 Flow、state hoisting、`LaunchedEffect`、`derivedStateOf` | [09b-compose-state.md](09b-compose-state.md) |
| `LazyColumn` key、穩定性、延後讀取、重運算 | [10-compose-performance.md](10-compose-performance.md) |
| 間距／顏色／圓角／字型 token、硬編碼字串 | [13-designsystem.md](13-designsystem.md) |
| Composable 內取依賴（禁 `by inject()`，只允許 `koinViewModel()`） | [03-di.md](03-di.md) |
| 導覽事件、跨模組 `XxxRouter` | [12-navigation.md](12-navigation.md) |
| `ComposeView` / `AndroidView` 互通、`ViewCompositionStrategy` | [17-interop-views-compose.md](17-interop-views-compose.md) |
| 「什麼算新畫面」的判定邊界 | [91-decisions.md](91-decisions.md) |

---

## 一、modifier 與參數

### compose-modifier-missing · MUST · new-only+on-touch · lint:compose-modifier-missing

會發出 UI 的 composable 必須有**且僅有一個** `modifier: Modifier = Modifier` 參數，並把它套在**最外層** layout 上；不得丟棄、不得只套到內層子元件。

✗ `@Composable fun KKButton(text: String, onClick: () -> Unit)`  // 呼叫端無法調整 layout
✗ `@Composable fun KKLabel(text: String, modifier: Modifier = Modifier) { Row { Text(text, modifier) } }`  // 沒套最外層
✓ `@Composable fun KKButton(text: String, onClick: () -> Unit, modifier: Modifier = Modifier) { Row(modifier) { … } }`

例外：`@Preview` 函式、不發出 UI 只回傳值的 composable。
既有違規：3544 個 `@Composable` 只有 406 個宣告（11%），含 `KKButton` / `KKTextField` / `KKSelect` → [90-migration-ledger.md#m-12](90-migration-ledger.md)

### composable-param-order · MUST · new-only · manual

參數順序固定：必填參數 → `modifier` → 其他有預設值的選填參數 → `@Composable` slot lambda 放最後（trailing）。主要 slot 一律命名 `content`。

✗ `fun ProductCard(modifier: Modifier = Modifier, title: String, onClick: () -> Unit)`
✓ `fun ProductCard(title: String, onClick: () -> Unit, modifier: Modifier = Modifier, badge: (@Composable () -> Unit)? = null, content: @Composable ColumnScope.() -> Unit)`

例外：無。

### state-in-composable-param · MUST NOT · new-only+on-touch · manual

composable 參數不得是 `State<T>` / `MutableState<T>` / `StateFlow<T>` / `MutableStateFlow<T>`，也不得傳 setter 物件。一律傳**解出的值 + 事件 lambda**。

✗ `fun HomeV2Screen(keyword: State<String>, …)`  // `HomeV2Screen.kt:135-137`
✓ `fun HomeV2Screen(keyword: String, onKeywordChange: (String) -> Unit, …)`

例外：stateful 層（`XxxRoute`）自己 collect 後把值往下傳，本身不算違規；把 flow 往下傳才是。

### composed-modifier · MUST NOT · new-only · manual

不得新增 `Modifier.composed { }`（有可觀測效能成本，androidx 已改推 `Modifier.Node`）。自訂 modifier 用一般擴充函式，需要 composition 狀態時由呼叫端當參數傳入。

✗ `fun Modifier.highlight() = composed { background(StyleDictionary.kkColorBorderLighter) }`
✓ `fun Modifier.highlight(color: Color) = this.background(color)`

例外：既有 `composed` 不主動改寫。

---

## 二、命名

### composable-naming · MUST · new-only · manual

發出 UI 的 `@Composable` 回傳 `Unit`，用 **PascalCase 名詞**；有回傳值的 `@Composable` 用 camelCase。發出 UI 的 composable 不得同時有回傳值。

✗ `@Composable fun showProductCard(…)` ／ `@Composable fun ProductCard(…): Boolean`
✓ `@Composable fun ProductCard(…)` ／ `@Composable fun priceTextColor(status: OrderStatus): Color`

例外：無。

### remember-prefix-missing · MUST · new-only · manual

內部呼叫 `remember` 並把結果**回傳**的 `@Composable` factory，函式名必須以 `remember` 前綴。

✗ `@Composable fun productListState(items: List<Product>): ProductListState = remember(items) { … }`
✓ `@Composable fun rememberProductListState(items: List<Product>): ProductListState = remember(items) { … }`

例外：無。

---

## 三、Material 與第三方

### no-new-material2 · MUST NOT · new-only · manual

新程式碼不得 `import androidx.compose.material.*`（M2），一律 `material3`。同一個檔案內**禁止**同時 import 兩套。

✗ `import androidx.compose.material.Text`
✓ `import androidx.compose.material3.Text`

例外：M3 確無對應元件時，該 import 需在 PR 說明並記入遷移帳；不得因此在同檔混用兩套元件語意。
既有違規：M2 374 檔、同檔混用 103 檔 → [90-migration-ledger.md#m-13](90-migration-ledger.md)

### no-new-accompanist · MUST NOT · new-only · manual

不得新增任何 `com.google.accompanist.*` import（版本停在 0.28.0，pager / swiperefresh / systemuicontroller 皆已由官方廢止）。

✗ `import com.google.accompanist.pager.HorizontalPager` ／ `rememberSystemUiController()`
✓ `androidx.compose.foundation.pager.HorizontalPager` ／ `androidx.compose.material3.pulltorefresh.PullToRefreshBox`

例外：系統列顏色改用專案 `SystemBarLegacyCompat`（紅線 I1），不是自行 `enableEdgeToEdge`。
既有違規：28 檔（`rememberSystemUiController` 20 檔）→ [90-migration-ledger.md#m-14](90-migration-ledger.md)

---

## 四、Preview

### preview-not-stateless · MUST · new-only · manual

`@Preview` 只能預覽**無狀態**composable。預覽目標不得取 ViewModel（`koinViewModel()` / `viewModel()`）、不得 `by inject()`、不得觸發網路／DB／檔案。假資料用常數或 `@PreviewParameter` 提供。

✗ `@Preview @Composable private fun OrderPreview() { OrderRoute(viewModel = koinViewModel()) }`
✓ `@Preview @Composable private fun OrderScreenPreview() { OrderScreen(uiState = FakeOrderUiState, onRetry = {}) }`

例外：無。stateful 層無法預覽是預期結果 —— 這正是 [09b-compose-state.md](09b-compose-state.md) 要求兩層拆分的用途。

### preview-signature · SHOULD · new-only · manual

`@Preview` 函式必須同時標 `@Composable`、宣告為 `private`、命名 `XxxPreview`，且不得有參數（`@PreviewParameter` 提供者除外）。

✗ `@Preview @Composable fun preview1(title: String) { … }`
✓ `@Preview @Composable private fun ProductCardPreview() { ProductCard(title = "Tokyo Tower", onClick = {}) }`

例外：本專案沒有 Compose Theme（`StyleDictionary` 是編譯期常數、不支援深色模式），因此**不要求**以 Theme 包裹，`@PreviewLightDark` 也不適用；`@PreviewFontScales` / `@PreviewScreenSizes` 可自行斟酌使用。
既有違規：988 個 `@Preview` / 502 檔（58% 覆蓋），`@PreviewParameter` 僅 13 檔 → [90-migration-ledger.md#m-12](90-migration-ledger.md)

### new-xml-layout · MUST NOT · new-only · lint:new-xml-layout

不得新增 `res/layout*/*.xml`。新畫面、新元件一律 Compose。「新畫面」的判定表見 [91-decisions.md](91-decisions.md) D-03。

✗ 新增 `res/layout/fragment_coupon.xml` + `CouponFragment` 用 ViewBinding
✓ `CouponScreen()` composable；要嵌進既有 Fragment 時用 `ComposeView`（見 [17-interop-views-compose.md](17-interop-views-compose.md)）

例外：第三方 View SDK 強制要求、既有 XML 畫面的局部修改。例外必須在 PR 說明並記入遷移帳。
既有違規：1185 個 layout xml → [90-migration-ledger.md#m-11](90-migration-ledger.md)

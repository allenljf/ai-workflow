# 13 · 導航

**管**：route 的定義與型別安全、NavHost 結構與 nested graph、導航事件的流向、參數傳遞、back stack 操作、deep link、跨模組導航的接法。
**不管**：狀態怎麼建模、模組怎麼切、Compose side effect 怎麼寫。基準為 `navigation-compose` 2.8+ 穩定版的 type-safe API。

| 想找 | 去 |
|---|---|
| 導航事件在 UiState 裡怎麼表達、消費後怎麼清除 | `08-ui-state` |
| `LaunchedEffect` / `snapshotFlow` 的正確用法 | `10-compose-state` |
| feature 模組怎麼切 api/impl、依賴方向 | `02-modularization` |
| ViewModel 不得持有 `Context` / `Activity` / `View`；route 參數取回後怎麼查資料 | `08-ui-state` `05-data-layer` |

---

## 一、三原則

官方 [navigation principles](https://developer.android.com/guide/navigation/principles)，所有規則都由此推導：

1. **起始目的地固定**：start destination 是 back stack 的底座，也是使用者按 Back 離開 App 前看到的最後一頁。登入、onboarding 這類條件式畫面不是 start destination。
2. **back stack 反映真實路徑**：以 LIFO 堆疊，使用者去過哪裡就長什麼樣，不可人工偽造順序。
3. **Up 不離開 App、Back 可以**：Up 在 start destination 上不顯示；Back 走到底會離開 App。
4. **deep link 產生合成 back stack**：外部進入時，Navigation 依 graph 結構補上 start destination 與沿路各層 nested graph 的 start destination，取代原有 back stack。

## 二、type-safe route 標準寫法

route 用 `@Serializable` 類別，不用字串。模組需 apply `org.jetbrains.kotlin.plugin.serialization`、依賴 `kotlinx-serialization-json`，且 `androidx.navigation` ≥ 2.8.0。

```kotlin
@Serializable data object Home                             // 無參數 → data object
@Serializable data class OrderDetail(val orderId: String)  // 有參數 → data class
@Serializable data object CheckoutGraph                    // nested graph 的 route

NavHost(navController, startDestination = Home) {
    composable<Home> {
        HomeScreen(onOrderClick = { navController.navigate(OrderDetail(it)) })
    }
    composable<OrderDetail> { entry ->
        OrderDetailScreen(                                  // 畫面只收 lambda，不收 NavController
            orderId = entry.toRoute<OrderDetail>().orderId,
            onBackClick = navController::navigateUp,
        )
    }
    navigation<CheckoutGraph>(startDestination = CheckoutAddress) { /* 子流程 */ }
}
```

ViewModel 端以 `savedStateHandle.toRoute<OrderDetail>().orderId` 取參數，再向 repository 查資料。

**route 形狀**：有參數用 `data class`，無參數用 `data object`。不要為了「未來可能加參數」把無參數 route 寫成全預設值的 data class，也不要用沒有 `equals` 的一般 class——`popUpTo<T>()` 與 `launchSingleTop` 的比對會出現非預期結果。

**nested graph 只用於「有明確進出點的子流程」**（登入、註冊、精靈、結帳）。單畫面 feature 不要硬包一層 base route——只是多一層 back stack 與 `popUpTo` 目標。外部只導航到 graph 的 route（`navigate(CheckoutGraph)`），不直接跳進圖內的中間節點，否則 deep link 合成 back stack 會少一層。

## 三、跨模組導航

feature 之間不得互相依賴實作。route 與導航擴充函式放在該 feature 的 **api 模組**，destination 的註冊由 app 模組組裝。

```kotlin
// :feature:order:api —— 只有 route，沒有 UI
@Serializable data class OrderDetail(val orderId: String)

// :feature:order:impl —— 對外只暴露一個 NavGraphBuilder 擴充函式，去向由參數決定
fun NavGraphBuilder.orderDetailScreen(onCheckoutClick: (String) -> Unit, onBackClick: () -> Unit) =
    composable<OrderDetail> { entry -> OrderDetailScreen(/* ... */) }

// :app —— 唯一知道「誰接誰」的地方
NavHost(navController, startDestination = Home) {
    orderDetailScreen(
        onCheckoutClick = { navController.navigate(CheckoutGraph) },
        onBackClick = navController::navigateUp,
    )
}
```

`:feature:checkout:impl` 若要跳到訂單詳情，只依賴 `:feature:order:api`，永遠不碰 `:feature:order:impl`。

---

## 四、規則

### dynamic-start-destination · MUST_NOT · new-only+on-touch · manual

`NavHost` 的 `startDestination` 必須是編譯期固定的單一值，不得依登入狀態、feature flag、實驗分組動態切換。動態起點會同時搞壞 Up 行為、deep link 合成 back stack 與 process death 還原。

✗ `NavHost(nav, startDestination = if (isLoggedIn) Home else Login)`
✓ `NavHost(nav, startDestination = Home)`，未登入時由 Home 的 state 觸發導向 `Login`

例外：無 · source: https://developer.android.com/guide/navigation/principles

### string-route · MUST_NOT · new-only+on-touch · regex

不得使用字串 route 與字串參數佔位符。route 一律是 `@Serializable` 類別，以 `composable<T>` 註冊、`navigate(T(...))` 呼叫。字串 route 的型別、必填性、預設值全部到 runtime 才會炸。

✗ `composable("order/{orderId}") { ... }` ／ `navController.navigate("order/$id")`
✓ `composable<OrderDetail> { ... }` ／ `navController.navigate(OrderDetail(id))`

例外：尚未 Compose 化、仍使用 XML nav graph 的既有畫面（`migrate` 帳） · source: https://developer.android.com/guide/navigation/design/type-safety

### navcontroller-as-composable-param · MUST_NOT · new-only+on-touch · regex

不得把 `NavController` / `NavHostController` 當參數傳進 screen 或更深層的 composable，也不得改用 `CompositionLocal` 全域提供或就地 `findNavController(view)`——那只是把耦合藏起來。導航一律以 `() -> Unit` / `(Id) -> Unit` lambda 上拋，由 `NavHost` 那一層呼叫 `navigate()`。傳 NavController 會讓畫面與整張導航圖耦合，無法單獨 preview 或測試。

✗ `fun OrderDetailScreen(orderId: String, navController: NavController)`
✓ `fun OrderDetailScreen(orderId: String, onCheckoutClick: (String) -> Unit, onBackClick: () -> Unit)`

例外：無 · source: https://developer.android.com/guide/navigation/design

### navcontroller-in-viewmodel · MUST_NOT · new-only+on-touch · regex

ViewModel 不得持有、注入或接收 `NavController` / `NavHostController` / `NavBackStackEntry`。ViewModel 生命週期長於 composition，持有會 leak，也讓它無法純 JVM 測試。ViewModel 只更新狀態，導航由 UI 觀察狀態後執行（事件建模見 `08-ui-state`）。

✗ `class LoginViewModel(private val navController: NavController) : ViewModel()`
✓ ViewModel 更新 `uiState.isLoggedIn`；UI 端 `LaunchedEffect` 觀察後呼叫 `onLoggedIn()` 並回呼清除

例外：無 · source: https://developer.android.com/topic/architecture/ui-layer/events

### object-as-nav-argument · MUST_NOT · new-only+on-touch · manual

導航參數只能是 id 或原始型別（String / Int / Long / Boolean / Enum）。不得把 domain model、`Parcelable`、`Serializable` 物件或 JSON 字串塞進 route，目標畫面必須用 id 從 data layer 重新取資料。back stack 的 saved state 空間有限，且塞進去的是會過期的快照。

✗ `@Serializable data class OrderDetail(val order: Order)`
✓ `@Serializable data class OrderDetail(val orderId: String)`

例外：跨畫面共享的大量資料改用 scope 到 nested graph 的 ViewModel（`viewModel(navController.getBackStackEntry(CheckoutGraph))`） · source: https://developer.android.com/guide/navigation/use-graph/pass-data

### string-key-argument-access · MUST_NOT · new-only+on-touch · regex

取得導航參數一律用 `NavBackStackEntry.toRoute<T>()` 或 `SavedStateHandle.toRoute<T>()`，不得用字串鍵取值。字串鍵在 route 欄位改名時不會編譯失敗，而是 runtime 拿到 null。

✗ `savedStateHandle.get<String>("orderId")!!` ／ `entry.arguments?.getString("orderId")`
✓ `savedStateHandle.toRoute<OrderDetail>().orderId`

例外：無 · source: https://developer.android.com/guide/navigation/design/type-safety

### navigate-in-composition-body · MUST_NOT · new-only+on-touch · manual

不得在 composable 的 composition body（非 callback、非 `LaunchedEffect`）中呼叫 `navigate()` / `popBackStack()`。composition body 會因任何重組重跑，導致重複 push、back stack 爆量。

✗ `@Composable fun DetailScreen(...) { if (uiState.expired) navController.navigate(Home) }`
✓ `LaunchedEffect(uiState.expired) { if (uiState.expired) onSessionExpired() }`

例外：無 · source: https://developer.android.com/topic/architecture/ui-layer/events

### unguarded-navigation-callback · SHOULD · new-only · manual

導航 callback 應以 `dropUnlessResumed { }` 包裝，避免快速連點或轉場動畫期間重複導航；至少必須設 `launchSingleTop = true`，否則同一個 destination 會被 push 兩次。

✗ `Button(onClick = { onOrderClick(id) })`
✓ `Button(onClick = dropUnlessResumed { onOrderClick(id) })`

例外：無 · source: https://developer.android.com/topic/architecture/ui-layer/events

### multiple-navhost · MUST_NOT · new-only · manual

一個畫面層級只能有一個 `NavHost`（一個 `NavController` 對應一個 `NavHost`）。第二個 NavHost 帶來第二條獨立 back stack，系統 Back 只送到最外層、deep link 也無法穿透。子流程用 `navigation<T>(startDestination = ...)` 巢狀圖表達。

✗ `Column { NavHost(outerNav, ...); NavHost(innerNav, ...) }`
✓ `NavHost(nav, startDestination = Home) { navigation<CheckoutGraph>(startDestination = CheckoutAddress) { ... } }`

例外：無 · source: https://developer.android.com/guide/navigation/design

### oneshot-flow-not-popped · MUST · new-only+on-touch · manual

登入、註冊、onboarding、付款結果等一次性流程結束後導航，必須用 `popUpTo(inclusive = true)` 把該流程的所有畫面移出 back stack，否則 Back 會把使用者送回已完成的流程。

✗ `navController.navigate(Home)`
✓ `navController.navigate(Home) { popUpTo<LoginGraph> { inclusive = true } }`

例外：無 · source: https://developer.android.com/guide/navigation/backstack

### top-level-switch-missing-nav-options · MUST · new-only+on-touch · manual

bottom navigation / navigation rail 的 top-level 切換必須同時設 `popUpTo(startDestination) { saveState = true }`、`launchSingleTop = true`、`restoreState = true`，缺一不可。缺了會分別造成 back stack 無限成長、重複堆疊、tab 內狀態與捲動位置遺失。

✗ `navigate(tabRoute) { popUpTo(nav.graph.findStartDestination().id) }`
✓ `navigate(tabRoute) { launchSingleTop = true; restoreState = true; popUpTo(nav.graph.findStartDestination().id) { saveState = true } }`

例外：無 · source: https://developer.android.com/guide/navigation/backstack/multi-back-stacks

### popbackstack-as-up · MUST · new-only+on-touch · manual

Up（App bar 返回鍵）用 `navigateUp()`，只有真的要 pop 才用 `popBackStack()`，且必須處理它回傳 `false` 的情況——此時 current destination 為 null，使用者會看到空白畫面。

✗ `IconButton(onClick = { navController.popBackStack() })`（在 start destination 上會空白）
✓ `IconButton(onClick = navController::navigateUp)` ／ `if (!navController.popBackStack()) finish()`

例外：無 · source: https://developer.android.com/guide/navigation/backstack

### feature-route-outside-api-module · MUST · new-only · manual

feature 的 route 類別與其導航擴充函式必須放在該 feature 的 api 模組（或共用的 `:core:navigation`）並保持 public；Screen、ViewModel 等實作維持 internal。其他 feature 只能依賴 api，不得依賴 impl。

✗ `:feature:checkout:impl` 依賴 `:feature:order:impl` 才能拿到 route
✓ `:feature:order:api` 放 `@Serializable data class OrderDetail(...)`，`:feature:checkout:impl` 只依賴它

例外：尚未拆 api/impl 的既有 feature（`migrate` 帳，見 `02-modularization`） · source: https://developer.android.com/topic/modularization/patterns

### hardcoded-cross-feature-destination · MUST · new-only+on-touch · manual

feature 模組以 `NavGraphBuilder` 擴充函式對外提供自己的 destination，「離開本 feature 之後要去哪」一律用 lambda 參數表達，不得在函式內寫死其他 feature 的 route，也不得收 `NavController`。組裝由 app 模組負責。

✗ `fun NavGraphBuilder.orderScreen(nav: NavController) { ... nav.navigate(CheckoutGraph) ... }`
✓ `fun NavGraphBuilder.orderScreen(onCheckoutClick: (String) -> Unit, onBackClick: () -> Unit)`

例外：導向同一個 feature 內部的 destination · source: https://developer.android.com/guide/navigation/design/nested-graphs（官方 sample nowinandroid 的 entry provider 模式）

### deeplink-without-synthetic-backstack · MUST · new-only+on-touch · manual

deep link 必須宣告在 destination 上，交由 Navigation 依 graph 結構合成 back stack；不得在 Activity 手動解析 URI 後直接 `navigate()` 到目標畫面（back stack 只剩一層，Up 會直接離開 App）。

✗ `intent.data?.let { navController.navigate(OrderDetail(it.lastPathSegment!!)) }`
✓ `composable<OrderDetail>(deepLinks = listOf(navDeepLink<OrderDetail>(basePath = "https://www.example.com/order")))`

例外：無 · source: https://developer.android.com/guide/navigation/principles

### intra-app-startactivity · SHOULD_NOT · new-only · manual

App 內畫面之間不得用 `startActivity` + Intent extras 導航。Activity destination 只保留給第三方 App 互動、系統元件，或既有架構的遷移過渡期（後者需在 PR 說明保留原因）。

✗ `startActivity(Intent(this, OrderDetailActivity::class.java).putExtra("order", order))`
✓ `navController.navigate(OrderDetail(orderId))`；對外才 `startActivity(Intent(ACTION_VIEW, uri))`

例外：多 Activity 的既有架構（`migrate` 帳） · source: https://developer.android.com/guide/navigation/design

### overridden-onbackpressed · MUST_NOT · new-only+on-touch · regex

不得 override `Activity.onBackPressed()`。攔截返回一律用 `BackHandler(enabled)`（Compose）或 `OnBackPressedDispatcher.addCallback`（Views），並在 manifest 的 `<application>` 設 `android:enableOnBackInvokedCallback="true"`。

✗ `override fun onBackPressed() { if (hasUnsavedChanges) showDialog() else super.onBackPressed() }`
✓ `BackHandler(enabled = hasUnsavedChanges) { showDiscardDialog = true }`

例外：無 · source: https://developer.android.com/guide/navigation

---

## 五、尚無定論

官方未表態，以下是**建議不是規則**：

- **畫面之間回傳結果**（選擇器把選中值帶回上一頁）：優先讓兩邊都讀同一個 repository（單一資料來源），其次用 scope 到 nested graph 的共享 ViewModel。`savedStateHandle` 回傳鍵值是字串、型別不安全、來源頁被 popUpTo 清掉就失效，只在同一 NavHost 內、資料極小、不需持久化時才用。
- **登入牆**：start destination 固定為真正的首頁，登入包成 nested graph，需要登入的動作觸發時 navigate 進去，成功後 `popUpTo<LoginGraph> { inclusive = true }`。判斷放在 UI 層觀察 state，不要放在 graph 的組建期。

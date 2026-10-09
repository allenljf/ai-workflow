# 12 · 導航（Navigation）

這份管**畫面之間怎麼跳**：四套並存機制怎麼選、跨模組導航契約（`:shared:routing` 的 `XxxRouter` + `XxxRoutingInput`）、Compose Navigation 的 route 與 back stack 操作、deep link 入口。

這份**不管**：Gradle 依賴怎麼宣告（→ 02）、Router 注入寫法（→ 03）、導航決策怎麼從 ViewModel 上拋（→ 08）、`NavBackStackEntry` 的 ViewModel scope（→ 17）。

| 你要找的 | 去哪份 |
|---------|-------|
| feature 模組不得互相依賴、`compileOnly(project(...))` | [02-modularization.md](02-modularization.md) |
| `by inject()` 白名單、`object XxxRouterHelper : KoinComponent` 取 Router | [03-di.md#inject-outside-whitelist](03-di.md) |
| 導航要用 state 欄位還是 one-off event | [08-ui-state.md#one-off-event-as-state](08-ui-state.md) |
| ViewModel 不得持有 `NavController` | [08-ui-state.md#context-in-viewmodel](08-ui-state.md)（紅線 D2） |
| ViewModel 不得往下傳給子 composable | [09b-compose-state.md](09b-compose-state.md) |
| `composable { }` 內的 ViewModel owner、巢狀 `NavHost` | [17-interop-views-compose.md#nested-navhost-viewmodel](17-interop-views-compose.md) |
| 新畫面禁新增 `res/layout/*.xml`、什麼算「新畫面」 | [00-red-lines.md](00-red-lines.md) E1、[91-decisions.md](91-decisions.md) D-03 |
| deep link 帶進來的 URL 丟進 WebView | [18-security.md#webview-untrusted-url](18-security.md) |

---

## 一、新畫面該用哪一套：四選一

本專案四套機制並存（Jetpack Navigation XML 13 份 graph / Compose `NavHost` 16 檔 / KRouter `kkday://` 179 檔 / 裸 `startActivity` 195 處）。**不要再自己判斷，照這張表選。**

| 你要導到哪 | 用哪套 |
|-----------|-------|
| 同一 Compose 宿主內的子頁（設定層級、bottom sheet 分頁） | Compose Navigation `NavHost` + route 常數 |
| 同模組內另一個 Activity | 該 Activity 的 `companion object fun launch(context, …)` / `createIntent(...)` |
| **跨模組**畫面 | 注入 `:shared:routing` 的 `XxxRouter` 介面（見下方 `cross-module-navigation`） |
| App 外部進來（`kkday://`、推播、AppsFlyer、web） | KRouter：目標 Activity 標 `@Router(KRouterConst.PAGE_X)`，由 `RouterHelper` 分派 |
| 既有 XML nav graph 內新增子頁 | 沿用該 graph（`findNavController()` + safeargs），不得在同一 graph 內混入 Compose Navigation |

### new-navigation-mechanism · MUST_NOT · new-only · manual

不得引入第五套導航機制（第三方 router library、自建 Intent 分派表、用 EventBus 發導航事件），也不得為單一功能自建 Router 框架。新導航需求一律落到上表四套之一。

✗ `object ProductNavigator { fun go(ctx: Context, page: String) { … } }`
✓ `interface ProductRouter { fun launchProductPage(context: Context, input: ProductRoutingInput) }` 放 `libs/routing`

例外：無。

### krouter-for-internal-nav · SHOULD_NOT · new-only · manual

新增的 App **內部**跳轉不應新增 `KRouterConst` 常數 + `RouterHelper.dispatch(...)`。KRouter 保留給 App 外部進入點（deep link、推播、AppsFlyer）。

✗ `RouterHelper.dispatch(KRouterConst.PAGE_ORDER_DETAIL).withParam("order_id", id).navigator(context)`
✓ `startActivity(orderRouter.createOrderDetailIntent(context, OrderDetailRoutingInput(orderId = id)))`

例外：目標畫面同時是 deep link 入口時 `@Router` 註解保留，App 內部呼叫仍走 Router 介面。
既有違規：179 檔引用 `com.kkday.krouter` / `KRouterConst` —— 遷移帳無專屬條目，不主動遷移。

### new-xml-nav-graph · MUST_NOT · new-only · manual

不得新增 `res/navigation/*.xml` nav graph。既有 13 份 graph 內新增 destination 可接受，但該 destination 的畫面內容仍須是 Compose。

✗ 新增 `libs/feature/hotel/product/src/main/res/navigation/nav_hotel.xml`
✓ 全新畫面用 Compose `NavHost` 或獨立 Activity；既有 `nav_product.xml` 內新增 `<fragment>` 並以 `ComposeView` 承載內容

例外：見上。紅線 E1 的延伸。
既有違規：13 份 nav graph、`findNavController` 20 檔 → [90-migration-ledger.md#m-11](90-migration-ledger.md)

---

## 二、跨模組導航（本專案做對的地方，照抄）

標準樣板三件事：**介面在 `:shared:routing`（`libs/routing`）、實作在 `:app`、使用端 Koin 注入介面**。

```kotlin
// libs/routing/src/main/java/com/kkday/router/OrderRouter.kt
interface OrderRouter {
    fun createOrderDetailIntent(context: Context, input: OrderDetailRoutingInput, flags: Int? = null): Intent
}

// libs/routing/src/main/java/com/kkday/input/OrderDetailRoutingInput.kt
@Parcelize
data class OrderDetailRoutingInput(val orderId: String, val isFromDeepLink: Boolean = false) : Parcelable

// app/src/main/java/com/kkday/member/view/order/detail/qrcode/OrderRouterImpl.kt
@Single
class OrderRouterImpl : OrderRouter { … }

// 使用端（HomeV2Fragment.kt:92）
private val orderRouter: OrderRouter by inject()
```

### cross-module-navigation · MUST · new-only+on-touch · manual

跨模組畫面跳轉必須注入 `:shared:routing` 的 `XxxRouter` 介面。不得 import 目標模組的 Activity / Fragment 類別，也不得為此新增 feature → feature 的 Gradle 依賴。

✗ `:feature:search_page` 內 `startActivity(OrderDetailActivity.createIntent(context, orderId))`
✓ `private val orderRouter: OrderRouter by inject()` → `orderRouter.createOrderDetailIntent(context, input)`

例外：`:app` 是所有 Router 的實作處，可直接 import 目標畫面。
既有違規：11 條 feature 互依邊 → [90-migration-ledger.md#m-24](90-migration-ledger.md)

### router-contract-misplaced · MUST · new-only · manual

新增的 `XxxRouter` 介面放 `libs/routing` 的 `com.kkday.router`；`XxxRoutingInput` 放同模組 `com.kkday.input`，標 `@Parcelize` 並實作 `Parcelable`。不得新增到 `libs/base/.../common/util/routing/` 或任何 feature 模組。

✗ `libs/base/src/main/java/com/kkday/library/common/util/routing/OrderItineraryRouter.kt`
✓ `libs/routing/src/main/java/com/kkday/router/OrderItineraryRouter.kt` + `com/kkday/input/OrderItineraryRoutingInput.kt`

例外：無。
既有違規：契約散落三處，`libs/base/.../util/routing` 6 檔。

### duplicate-router-contract · MUST_NOT · new-only · manual

新增 Router 介面前先搜尋 `libs/routing/src/main/java/com/kkday/router/` 是否已有同名檔案。既有契約缺方法時擴充該介面，不得另開一份同名介面。

✗ `com.kkday.library.common.util.routing.CancelOrderRouter` 與 `com.kkday.router.CancelOrderRouter` 同名並存 —— import 錯就綁到不同實作
✓ 在 `com.kkday.router.CancelOrderRouter` 內補上 `fun launch(context: Context, input: CancelOrderRoutingWithDataInput)` 多載

例外：無。

### router-impl-outside-app · MUST · new-only · manual

`XxxRouterImpl` 放 `:app`，以 Koin `@Single` 註冊。`:shared:routing` 與 feature 模組不得含 Router 實作。

✗ `libs/feature/order_page/.../OrderRouterImpl.kt`
✓ `app/src/main/java/com/kkday/member/view/order/detail/qrcode/OrderRouterImpl.kt` 標 `@Single`

例外：無。

---

## 三、Compose Navigation

### nav-controller-passed-down · MUST_NOT · new-only+on-touch · manual

`NavController` / `NavHostController` 只能存在於建立它的 `NavHost` 宿主層。不得當參數傳給子 composable，子層只收 `onXxxClick: () -> Unit`。

✗ `@Composable fun BundleSheetProductScreen(navController: NavController, …)`
✓ `@Composable fun BundleSheetProductScreen(onSkuClick: (String) -> Unit, onBackClick: () -> Unit, …)`

例外：無。
既有違規：24 檔以 `navController` 當 composable 參數。

### nav-controller-composition-local · MUST_NOT · new-only · lint:nav-controller-composition-local

不得用 `CompositionLocal` 供應 `NavController` / `NavHostController`。

✗ `val LocalNavController = compositionLocalOf<NavHostController> { error("…") }`
✓ 宿主層 `val navController = rememberNavController()`，導航動作逐層以 lambda 下傳

例外：無。
既有違規：`libs/feature/order_page/.../presentation/navigation/LocalNavController.kt` 1 處。

### route-string-literal · MUST · new-only+on-touch · manual

route 一律用 `const val` 常數。帶參數的 route 同時宣告「樣板常數」與「建構函式」；不得在 `composable(...)` / `navigate(...)` 直接寫字面值或就地拼字串。

✗ `navController.navigate("order_detail/$orderId")`
✓ `const val ORDER_DETAIL_ROUTE = "order_detail"` + `const val ORDER_DETAIL_ROUTE_WITH_PARAM = "$ORDER_DETAIL_ROUTE/{orderId}"` + `fun orderDetailRoute(id: String) = "$ORDER_DETAIL_ROUTE/$id"`

例外：無。

### nav-arg-not-id · MUST_NOT · new-only+on-touch · manual

destination 參數只傳識別碼與少量純量（id、type、date）。不得把 domain model / DTO / 清單整包塞進 route 參數或 `savedStateHandle`；目標畫面用 id 自行載入。

✗ `navController.currentBackStackEntry?.savedStateHandle?.set(KEY_ORDER_INFO, order)` → 下一頁 `previousBackStackEntry…get<OrderInfo>(KEY_ORDER_INFO)`
✓ `navController.navigate(groupOrderRoute(order.id))`，`GroupOrderViewModel` 依 `orderId` 取資料

例外：無。

### route-string-convention · MUST · new-only · manual

`navigation = 2.7.7`，type-safe route（`@Serializable` route + `composable<T>` + `toRoute<T>()`）需 2.8+，**現在寫編譯不過**，升版屬紅線 A3。字串 route 是唯一選項，寫法固定四點：

1. route 常數收在該 feature 模組的 `navigation/XxxRoutes.kt` 的 `object XxxRoutes`，不散在 Fragment / Activity 的 `companion object`（呼叫點不得寫字面字串 → 同檔 `route-string-literal`）。
2. 每個參數用 `navArgument` 宣告 `type`；可空或有預設值時一併宣告 `nullable` / `defaultValue`。
3. 目的地取值走 ViewModel 的 `SavedStateHandle`，不在 composable 內 `backStackEntry.arguments?.getString(...)` 直取。
4. 參數只放 id 與少量純量（→ 同檔 `nav-arg-not-id`）；跨模組導航走 `:shared:routing` 的 Router，不得 import 他模組的 Routes 常數（→ 同檔 `cross-module-navigation`）。

```kotlin
object OrderDetailRoutes {                                    // navigation/OrderDetailRoutes.kt
    const val ARG_ORDER_ID = "orderId"
    const val ROUTE = "order_detail"
    const val ROUTE_WITH_ARG = "$ROUTE/{$ARG_ORDER_ID}"
    fun build(orderId: String) = "$ROUTE/$orderId"
}
composable(
    route = OrderDetailRoutes.ROUTE_WITH_ARG,
    arguments = listOf(navArgument(OrderDetailRoutes.ARG_ORDER_ID) { type = NavType.StringType }),
) { OrderDetailScreen() }   // ViewModel：savedStateHandle.get<String>(OrderDetailRoutes.ARG_ORDER_ID)
```

✗ `composable("order_detail/{orderId}") { it.arguments?.getString("orderId") }`
例外：無。升版的完整影響面（四個 navigation artifact、XML nav graph、safe-args、決策 P-02）→ [90-migration-ledger.md#m-25](90-migration-ledger.md)

---

## 四、Back stack 與返回

### conditional-start-destination · MUST · new-only · manual

`NavHost` 的 `startDestination` 必須固定，不得依登入狀態 / 實驗開關動態切換。條件式畫面（登入、引導頁）改由起始畫面導向，並以 `popUpTo(START_ROUTE) { inclusive = true }` 處理。

✗ `NavHost(navController, startDestination = if (isLoggedIn) ROUTE_MEMBER_PAGE else ROUTE_LOGIN)`
✓ `NavHost(navController, startDestination = ROUTE_MEMBER_PAGE)`，未登入時由該畫面導向登入

例外：無。

### navigate-back-instead-of-pop · MUST_NOT · new-only+on-touch · manual

返回一律 `popBackStack()`；不得用 `navigate(上一頁 route)` 當返回。要退到特定畫面用 `popBackStack(route, inclusive = false)`。

✗ `onBackClick = { navController.navigate(ROUTE_MEMBER_PAGE) }`
✓ `onBackClick = { navController.popBackStack() }` ／ `navController.popBackStack(ROUTE_MEMBER_PAGE, inclusive = false)`

例外：無。

### repeated-nav-no-singletop · MUST · new-only · manual

可被重複觸發的導航（底部導航、tab、清單連點、通知）必須加 `launchSingleTop = true`；tab 切換另加 `popUpTo(startDestination) { saveState = true }` + `restoreState = true`。

✗ `navController.navigate(ROUTE_SETTINGS)` 綁在可連點的按鈕
✓ `navController.navigate(ROUTE_SETTINGS) { launchSingleTop = true }`

例外：刻意允許同一 destination 疊多層（如商品頁一路往下鑽）。

### up-back-divergence · SHOULD_NOT · new-only · manual

`BackHandler` 不應讓系統返回與畫面上的 Up（返回箭頭）走不同路徑；兩者共用同一個 `onBack` lambda。

✗ Up 呼叫 `popBackStack(ROUTE_SETTINGS, false)`，`BackHandler` 卻 `navigate(ROUTE_SETTINGS)`
✓ `val onBack = { navController.popBackStack(ROUTE_SETTINGS, inclusive = false) }`，topBar 與 `BackHandler { onBack() }` 共用

例外：需攔截未儲存變更時，兩條路徑都要先跳同一個確認對話框。
既有現況：`BackHandler` 24 檔。

### deeplink-no-synthetic-backstack · MUST · new-only+on-touch · manual

deep link（`kkday://`、推播、web）進入非起始畫面時必須組出合成 back stack，讓返回鍵回到 App 起始畫面而不是直接離開 App。

✗ `@Router(KRouterConst.PAGE_ORDER_DETAIL)` 的 Activity 被 deep link 直接開啟，按返回即離開 App
✓ 照 `OrderRouterImpl.createOrderDetailIntent`：先建 `MainActivity.createLaunchFragmentIntent(...)`，再用 extra 指定要展開的目標

例外：刻意的單畫面外部入口（如付款 3DS 回跳）須在 PR 說明。

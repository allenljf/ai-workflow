# 17 · View ↔ Compose 互通（interop）

**這份管**：在既有 Fragment / Activity 內嵌 Compose（`ComposeView`）、在 Compose 內嵌既有 View（`AndroidView`）、兩邊共用 ViewModel、兩邊樣式對齊、Epoxy / RecyclerView 清單邊界、RxJava 與協程的收斂邊界。

**這份不管**：純 Compose 的寫法與狀態（見 [09a-compose-api.md](09a-compose-api.md)、[09b-compose-state.md](09b-compose-state.md)）、UiState 設計（[08-ui-state.md](08-ui-state.md)）、token 清單與字串資源（[13-designsystem.md](13-designsystem.md)）、dispatcher 與 scope（[11-coroutines-flow.md](11-coroutines-flow.md)）、跨模組導航（[12-navigation.md](12-navigation.md)）。

> **本專案最高頻情境**：860 個含 `@Composable` 的檔案，與 177 個 Fragment / 157 個 Activity / 1185 份 XML layout 長期共存。你大部分的需求不是「開新畫面」，而是「在既有畫面裡塞一塊 Compose」。
>
> 什麼算「新畫面」（決定該不該開 Compose 畫面）→ 見 [91-decisions.md#d-03](91-decisions.md) 的判定表，本檔不重述。
> 新增 XML layout 的禁令 → [00-red-lines.md](00-red-lines.md) E1。

---

## 一、標準骨架：Fragment 內嵌 Compose

四步缺一不可。抄這段，不要自己重組。

```kotlin
override fun onCreateView(
    inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?,
): View = ComposeView(requireContext()).apply {
    // 1. 必設：composition 隨 viewLifecycleOwner 銷毀，不設會洩漏 / 狀態錯亂
    setViewCompositionStrategy(ViewCompositionStrategy.DisposeOnViewTreeLifecycleDestroyed)
    setContent {
        // 2. ViewModel 在 Compose 端取得；預設 owner 已解析到本 Fragment
        val viewModel: ConsultPickerViewModel = koinViewModel()
        // 3. LocalLifecycleOwner 此時已是 viewLifecycleOwner，直接收集即可
        val state by viewModel.state.collectAsStateWithLifecycle()
        // 4. 只往下傳值與 lambda，不傳 ViewModel
        ConsultPickerContent(state = state, onPick = viewModel::onPick)
    }
}
```

真實參考：`libs/feature/presale_chat/.../ui/consult_picker/ConsultPickerDialogFragment.kt:99-111`、`app/src/main/java/com/kkday/member/view/memberpage/MemberPageFragment.kt:141-144`。

XML 內宣告 `<androidx.compose.ui.platform.ComposeView>` 時，在 `onViewCreated` 對 `binding.composeView` 做同樣的第 1、2 步。

---

## 二、ComposeView 嵌入既有 Fragment / Activity

### compose-view-strategy · MUST · new-only+on-touch · lint:compose-view-strategy

每一處 `ComposeView(...)` 建立或取得後，緊接著必須呼叫 `setViewCompositionStrategy(ViewCompositionStrategy.DisposeOnViewTreeLifecycleDestroyed)`，才能 `setContent`。Fragment、RecyclerView / Epoxy item、Dialog 內一律適用。

✗ `return ComposeView(requireContext()).apply { setContent { ... } }`
✓ `ComposeView(requireContext()).apply { setViewCompositionStrategy(DisposeOnViewTreeLifecycleDestroyed); setContent { ... } }`

例外：`ComponentActivity.setContent { }`（不經 `ComposeView`）不需設定。既有 `DisposeOnDetachedFromWindow`（6 處）只在該 View 不掛在 Fragment 或 RecyclerView 上時才可保留。
既有違規：143 檔（165 用 `ComposeView`，僅 22 設定）→ [90-migration-ledger.md#m-12](90-migration-ledger.md)，批次遷移候選第 5 項

### fragment-lifecycle-in-compose · MUST NOT · new-only+on-touch · manual

`ComposeView` 的 `setContent` 內不得顯式改用 Fragment 自身的 lifecycle：不得傳 `lifecycleOwner = this@XxxFragment` / `lifecycle = this.lifecycle`，也不得在 `onViewCreated` 用 `lifecycleScope`（Fragment 自身）把資料推進 Compose。

✗ `viewModel.state.collectAsStateWithLifecycle(lifecycleOwner = this@MemberPageFragment)`
✓ `viewModel.state.collectAsStateWithLifecycle()`  // 預設即 viewLifecycleOwner

例外：無。Fragment view 比 Fragment 早死，綁錯會在 back stack 復原時對已銷毀的 view 發狀態。
> View 端（非 Compose）收集 Flow 的 `viewLifecycleOwner` / `repeatOnLifecycle` 規則見 [11-coroutines-flow.md](11-coroutines-flow.md)。

### activity-cast-in-compose · MUST NOT · new-only+on-touch · lint:activity-cast-in-compose

Composable 內不得把 `LocalContext.current` 強轉成 Activity。本專案的 base class 在 `attachBaseContext()` 做 locale 包裝，`LocalContext.current` 常是 `ContextWrapper`，強轉會 `ClassCastException`。

✗ `val activity = LocalContext.current as ComponentActivity`
✓ `val activity = LocalActivity.current ?: return`  // androidx.activity.compose.LocalActivity

例外：無。已有 `findActivity()` 私有實作的檔案（3 處各自複製）應改用 `LocalActivity`。
既有違規：29 檔（`as ComponentActivity` / `as Activity`）

---

## 三、Fragment 與 Compose 畫面共用 ViewModel

### viewmodel-owner-mismatch · MUST · new-only · manual

Fragment 端與其 `ComposeView` 內容要拿到**同一個** ViewModel 實例時，兩端必須解析到同一個 `ViewModelStoreOwner`，且跨 scope 時必須顯式指定，不得依賴預設值。

✗ Fragment 用 `by activityViewModel<CartViewModel>()`，Compose 內用 `koinViewModel<CartViewModel>()` → 兩個實例
✓ `val host = requireActivity()` 在 `setContent` 外取好，內部 `koinViewModel<CartViewModel>(viewModelStoreOwner = host)`

例外：兩端都要 Fragment scope 時不需指定 —— Compose 的預設 owner 經 `ViewTreeViewModelStoreOwner` 就是該 Fragment。

### nested-navhost-viewmodel · MUST NOT · new-only · manual

Fragment / Activity 內的 Compose `NavHost` 中，`composable { }` 區塊裡的 `koinViewModel()` owner 是該 `NavBackStackEntry`，不是宿主。要用宿主的 ViewModel，必須在 `NavHost` **外層**取得，往下只傳值與 lambda。

✗ `NavHost(...) { composable("settings") { val vm: MemberPageViewModel = koinViewModel() } }`  // 靜默拿到新實例
✓ 外層 `val vm: MemberPageViewModel = koinViewModel()` + `composable("settings") { SettingsContent(state, vm::onToggle) }`

例外：該 destination 本來就該有自己的畫面級 ViewModel 時，在 `composable { }` 內取是正確的。
> 「不得把 ViewModel 當參數往下傳」見 [09b-compose-state.md](09b-compose-state.md)。

---

## 四、AndroidView：Compose 內嵌既有 View

### android-view-as-xml-escape · MUST NOT · new-only · manual

不得以 `AndroidView` 包裝**新寫的** XML layout 或新寫的自訂 View 來規避「新畫面一律 Compose」。`AndroidView` 只允許包**既有**的 View、第三方 SDK View（地圖、播放器、WebView），或 Compose 確實沒有等價能力的元件。

✗ `AndroidView(factory = { LayoutInflater.from(it).inflate(R.layout.item_new_banner, null) })`
✓ `AndroidView(factory = { MapView(it) }, ...)`  // 第三方 SDK，Compose 無等價元件

例外：無。既有 View 若已有 Compose 版設計系統元件（`KK*`），一律改用 Compose 元件。

### android-view-update-heavy · MUST NOT · new-only+on-touch · manual

`update` lambda 每次重組都會執行，只能放「把當前 state 賦值到 View 屬性」。字串解析、清單重建、`requestModelBuild()`、物件配置一律不得放在裡面；昂貴轉換先用 `remember(key)` 算好再賦值。`factory` 只跑一次，不得在其中讀取會變動的 Compose state。

✗ `update = { productController.requestModelBuild() }`  // 每次重組重建整份清單
✓ `val spanned = remember(html) { fromHtml(html) }` + `update = { it.text = spanned }`

例外：無。

### android-view-no-release · MUST · new-only · manual

被包裝的 View 若持有需要釋放的資源（`MapView`、`WebView`、播放器、SDK listener、`RecyclerView` adapter 綁定），必須在 `AndroidView(onRelease = { ... })` 內釋放；只在 `factory` 註冊而不釋放視為洩漏。

✗ `AndroidView(factory = { WebView(it).apply { loadUrl(url) } })`
✓ `AndroidView(factory = { WebView(it) }, update = { it.loadUrl(url) }, onRelease = { it.destroy() })`

例外：無狀態、無註冊的純顯示 View（`TextView`、`ImageView`）不需要。

---

## 五、樣式兩端同源：Compose ↔ XML

兩端的 token 由同一份 style-dictionary 產出，**名稱可機械對應**（已實測驗證）：

| 類型 | Compose | XML |
|------|---------|-----|
| 間距 | `StyleDictionary.kkSpacing100` | `@dimen/kk_spacing_100` |
| 圓角 | `StyleDictionary.kkRadiusMd` | `@dimen/kk_radius_md` |
| 顏色 | `StyleDictionary.kkColorBorderLighter` | `@color/kk_color_border_lighter` |
| 字型 | `com.kkday.design.font.fontBodyMd`（頂層 val） | 無同源對應，沿用該 XML 既有 `textAppearance` |

規則：camelCase ↔ snake_case，數字後綴不變。改動 token 值必須回到 style-dictionary 產生流程（`StyleDictionary.kt` 檔頭已註明 auto-generated，且同一份產出餵給 iOS）。

### token-via-xml-resource · SHOULD NOT · new-only · lint:token-via-xml-resource

Compose 端不得經由 XML resource 取設計系統 token；直接引用 `StyleDictionary` / `font` 頂層 val。嵌入 XML 畫面時，用上表把 XML 端的 token 名對應回 Compose 端，不要重量 Figma 也不要 hardcode。

✗ `color = colorResource(id = R.color.kk_color_text_darker)`
✓ `color = StyleDictionary.kkColorTextDarker`

例外：`android.R.color.*` 等平台資源、以及該值本來就來自非 token 的 XML 資源時。
既有違規：158 檔（`colorResource` / `dimensionResource`），尚未登記於遷移帳
> hardcode 數值與字串資源的紅線見 [13-designsystem.md](13-designsystem.md)。

---

## 六、清單邊界：Epoxy / RecyclerView

### new-epoxy-model · MUST NOT · new-only · lint:new-epoxy-model

不得新增 `EpoxyModel` / `EpoxyModelWithHolder` / `@ModelView` / `EpoxyController` 子類，也不得新增 `RecyclerView.Adapter` / `ListAdapter`。新清單一律 `LazyColumn` / `LazyRow`。既有清單要新增一種 item type 時，評估整段換 `LazyColumn`；評估後決定不換的，寫進 PR 說明。

✗ `class NewBannerEpoxyModel : EpoxyModelWithHolder<Holder>()`
✓ `LazyColumn { items(items = banners, key = { it.id }) { BannerCard(it) } }`

例外：既有 `EpoxyController` 內既有 model 的參數調整不算新增。
既有違規：248 檔 Epoxy + 100 檔 Adapter → [90-migration-ledger.md#m-11](90-migration-ledger.md)（既有清單**不要**主動改寫）

### epoxy-compose-ad-hoc · SHOULD · new-only · manual

既有 Epoxy 清單要嵌入 Compose 區塊時，用共用的 `ComposeViewEpoxyModel`（`libs/feature/shared_core/.../customModules/epoxy/ComposeViewEpoxyModel.kt`），不要在每個 model 內自建 `ComposeView`。它已處理 `doOnLayout`、`findViewTreeLifecycleOwner()` 為 null 的回收期例外與 composition strategy。

✗ 在自訂 EpoxyModel 的 `bind()` 內 `ComposeView(parent.context).setContent { ... }`
✓ `ComposeViewEpoxyModel { ProductCard(item) }.id(item.id).addTo(controller)`

例外：需要自訂 layout params 或 holder 行為時可自建，但 `compose-view-strategy` 與 lifecycle owner 檢查一項都不能少。

### nested-same-axis-scroll · MUST NOT · new-only+on-touch · manual

同方向的捲動容器不得互相嵌套：垂直 RecyclerView / Epoxy item 內的 Compose 不得用 `LazyColumn` 或 `Modifier.verticalScroll`；`AndroidView` 包 `RecyclerView` 放進 Compose 時，該 `RecyclerView` 必須 `isNestedScrollingEnabled = false`，且外層 Compose 不得是同向捲動容器。

✗ Epoxy item 的 ComposeView 內 `LazyColumn { ... }`  // 無限高度量測
✓ Epoxy item 內用 `Column { ... }`；`AndroidView(factory = { RecyclerView(it).apply { isNestedScrollingEnabled = false } })`

例外：方向相反時（垂直清單內放 `LazyRow`）不受此限。

---

## 七、RxJava interop

### no-new-rxjava · MUST NOT · new-only · lint:no-new-rxjava

新程式碼不得引入 `io.reactivex.*` 型別（`Observable` / `Single` / `Completable` / `Flowable` / `Disposable`）。新資料流一律 `suspend fun` 或 `Flow`。

✗ `fun loadOrders(): Observable<List<Order>>`
✓ `suspend fun loadOrders(): List<Order>` / `fun observeOrders(): Flow<List<Order>>`

例外：修改既有 Rx 鏈的內部實作時可沿用該鏈的型別（見下一條的收斂邊界）。
既有違規：194 檔 → [90-migration-ledger.md#m-09](90-migration-ledger.md)（**不要**整段重寫既有 Rx 鏈）
> Retrofit endpoint 不得回傳 Rx 型別，見 [00-red-lines.md](00-red-lines.md) G2 / [06-network.md](06-network.md)。

### rx-type-crosses-boundary · MUST NOT · new-only+on-touch · manual

Rx 型別不得出現在 domain 層或 UI 層的公開簽章（UseCase / Repository 介面 / ViewModel 公開成員 / Composable 參數）。既有 Rx 鏈一律在 **Repository 實作內部**用 `kotlinx.coroutines.rx2` 的 `await()` / `awaitFirst()` / `asFlow()` 收斂後才向上傳。

✗ `class OrderViewModel { val orders: Observable<List<Order>> = repo.orders() }`
✓ `override suspend fun getOrders(): List<Order> = legacyService.fetchOrders().awaitFirst().toDomain()`

例外：`:app` 內既有的 Reductor / Presenter 路徑（由 `Observable<AppState>` 驅動）維持不動。
註：`kotlinx-coroutine-rx2` 已在 version catalog，但只在 `:app` 的 classpath 上；其他模組要用需先在該模組 `build.gradle.kts` 加 `implementation(libs.kotlinx.coroutine.rx2)`。

### rx-disposable-unmanaged · MUST · new-only+on-touch · manual

任何新產生的 `Disposable` 必須立刻掛進生命週期綁定的 `CompositeDisposable`，並在 `onDestroyView()`（View 層）或 `onCleared()`（ViewModel）`dispose()`。裸 `subscribe()` 不接住回傳值視為洩漏。

✗ `repository.orders().subscribe { render(it) }`
✓ `disposables += repository.orders().subscribe({ render(it) }, { logger.error(it) })`  // onDestroyView 內 disposables.clear()

例外：`BaseViewModel.subscribeWithAutoDispose()` 已代管 dispose，沿用即可。
> `BaseViewModel` 本身**不要**改（87 處引用）→ [90-migration-ledger.md#m-03](90-migration-ledger.md)。

### rx-mixed-scope · MUST NOT · new-only · manual

同一條資料流不得同時由 `CompositeDisposable` 與 `viewModelScope` 管理。把某條 Rx 鏈改成協程時，必須整條移除 Rx 端（含 `subscribeWithAutoDispose`），不得留下 Rx 訂閱再在 `viewModelScope` 內轉發。

✗ `disposables += repo.orders().subscribe { viewModelScope.launch { _state.update { s -> s.copy(orders = it) } } }`
✓ `viewModelScope.launch { repo.getOrders().collect { orders -> _state.update { it.copy(orders = orders) } } }`

例外：同一個 ViewModel 內**不同**資料流分別用兩套機制，屬既有混合期現況，不在本條範圍。

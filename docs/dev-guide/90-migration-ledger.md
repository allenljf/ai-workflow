# 90 · 遷移帳（Migration Ledger）

`enforce: migrate` 級規則的既有違規登記處。**這裡的數字是 2026-08 全庫實測，不是估計。**

## 這份文件怎麼用

| 你的情況 | 做法 |
|---------|------|
| 新增檔案 | 不用看這裡，直接 100% 遵守準則 |
| 改到的檔案裡有下列違規 | 查該項的「觸碰時怎麼辦」欄；多數是順手修，少數是**明確不要動** |
| 想開專案級遷移任務 | 從「批次遷移候選」挑，優先級已排好 |
| 本次改不完 | 在對應項目的「本次未修」加一行（檔案路徑 + PR 連結 + 原因） |

**重要**：遷移帳的存在不是拖延的藉口，但也不是要你在功能 PR 裡順手改 100 個檔案。`on-touch` 的邊界是**你本來就要改的那個檔案**。

---

## 一、狀態管理（最大宗）

<a id="m-01"></a>
### M-01 Reductor + MVP Presenter 架構

| 項目 | 數字 |
|------|------|
| `dispatch(` 呼叫點 | 752 處 / 190 檔 |
| `@AutoReducer` reducer | 41 檔 |
| `@ActionCreator` actions | 40 檔 |
| `AppState.java` | 1859 行（AutoValue god object） |
| 由 `Observable<AppState>` 餵狀態的 Presenter | 61 個 |
| 引用 Presenter 的 Activity/Fragment | 68 個 |
| 同時 `setContent` 又持有 Presenter 的混血畫面 | 30 個 |

**根本問題**：Reductor 是 vendored 的第三方 Redux（上游 0.13.1，最後更新 2017-01-12，內嵌 build 檔還寫 Kotlin 1.3.72 / AGP 4.0.1）。它同時綁死了兩件事：`:app` 的 kapt 無法移除（`kapt(project(":shared:tool:reductor:compiller"))`），以及 RxJava2 作為 UI 唯一出口。

**規則**：`no-new-reductor`（MUST NOT · new-only）— 紅線 D4。
**觸碰時怎麼辦**：既有 Reductor 畫面**不要**改成 MVVM，除非該畫面本來就要重寫。新增畫面一律 MVVM + UDF。改既有 reducer 時不要擴大 AppState 欄位。
**已知額外問題**：reducer 不是純函式（`LoginReducer.kt:75-105` 在 reduce 內直接 `trackEvent()`），reducer 用 `KoinComponent + by inject()` 取依賴而非建構子注入 → 無法在不啟動 Koin 的情況下單測。

<a id="m-02"></a>
### M-02 LiveData → StateFlow

| 項目 | 數字 |
|------|------|
| `LiveData` 出現檔案 | 64 |
| `MutableLiveData` | 57 |
| `.observe(` | 45 |
| `observeAsState`（Compose 收 LiveData） | 12 |
| 只用 LiveData 的 ViewModel | 33 |
| LiveData 與 Flow 混用的 ViewModel | 21 ← **真正的痛點** |

**規則**：`livedata-new-code`（SHOULD NOT · new-only）。
**觸碰時怎麼辦**：新增狀態欄位一律 StateFlow。同一個 ViewModel 內若已有 Flow，新欄位不得再開 LiveData（混用比純舊寫法更難維護）。

<a id="m-03"></a>
### M-03 `BaseViewModel.showLoading` 公開可變狀態

`libs/base/.../view/base/BaseViewModel.kt:9` 的 `var showLoading = MutableLiveData(false)` 是 public 可變，**87 個檔案引用**。等於把 loading 狀態開放給整個 App 寫入。同檔還內建 RxJava2 `CompositeDisposable` 與 `Observable.subscribeWithAutoDispose()`，讓所有繼承者被綁進 RxJava2。

**規則**：`mutable-state-exposed`（MUST NOT · new-only）。
**觸碰時怎麼辦**：**不要**改 `BaseViewModel` 本身（87 個引用點會炸）。新 ViewModel 不要繼承它，改繼承 `androidx.lifecycle.ViewModel` 並自行定義 UiState 內的 loading 欄位。
**批次遷移**：需要獨立專案任務，先建替代 base class 再逐畫面搬。

<a id="m-04"></a>
### M-04 對外暴露 Mutable 狀態

| 項目 | 數字 | 位置範例 |
|------|------|---------|
| public `MutableStateFlow` | 9 處 | `VTagViewModel.kt:39,45,55,57`、`CouponProductViewModel.kt:78-85`、`SpecificationSharedViewModel.kt:179` |
| public `MutableLiveData` | 2 處 | `BaseViewModel.kt:9`（見 M-03）、`KhsrSearchResultViewModel.kt:69` |
| public `Channel`（send/receive 兩端全開） | 22 個 ViewModel | `BookingViewModel.kt:72`、`BusListBookingViewModel.kt:78`、`AirportFillOrderScreenViewModel.kt:108` |

**規則**：`mutable-state-exposed`、`mutable-state-inferred`（MUST NOT · new-only+on-touch）。
**觸碰時怎麼辦**：這 33 處數量小、改動局部，**觸碰即修**。加 `_` 前綴 private + `asStateFlow()`。

<a id="m-05"></a>
### M-05 one-off event 三套機制並存

| 機制 | 數字 |
|------|------|
| `MutableSharedFlow`（多為 `_singleEvent`，無 replay 無 buffer → 無 collector 時事件遺失） | 67 檔 |
| `Channel<`（多為 UNLIMITED） | 45 檔 |
| `SingleLiveEvent` / `LiveData<Event<T>>` | 0 ← 這點乾淨 |
| `stateIn(WhileSubscribed)` | 只有 3 個 ViewModel / 4 處，且 4 處寫法全不合規（見下） |

**規則**：`one-off-event-as-state`（見 [08-ui-state.md](08-ui-state.md)）。
**觸碰時怎麼辦**：既有 SharedFlow/Channel 事件**不要**大規模改（會動到 UI 收集端）。新畫面用 events-as-state。
**專案標準樣板**：`app/.../login_methods/feature/login_methods/LoginMethodsViewModel.kt` 是全庫最貼近官方的實作 —— 單一 state 由 `SavedStateHandle` 持久化、事件以 `actions: List<Action>`（sealed interface + Parcelable）掛在 state 上、UI 呼叫 `onAction` 移除已消費事件。**新畫面照這個抄，唯一不要抄的是第 59 行的 `stateIn(WhileSubscribed())`**（無參數 = stopTimeoutMillis 0）。

**`statein-while-subscribed`（SHOULD · new-only）的既有違規**：`OtpRegisterViewModel.kt:36,40`、`LoginMethodsViewModel.kt:59` 無參數 `WhileSubscribed()`；`HomeViewModelV2.kt:94` 寫魔術數字 `5000`。**觸碰該 flow 時順手改成 `WhileSubscribed(5_000L)`**，不必為此專開 PR。
**基建待辦（一行）**：在 `:shared:base`（`libs/base/`）宣告 `const val WhileUiSubscribed = 5_000L`，之後把上述 4 處與新程式碼的字面值改引用；常數就位前一律寫 `5_000L`。詳細步驟見第八節基建項 B。

<a id="m-06"></a>
### M-06 ViewModel 持有 Android 型別

| 項目 | 數字 |
|------|------|
| `AndroidViewModel` | 16 檔（含 app 層 `BaseViewModel` 本身） |
| ViewModel `import android.content.Context` | 35 檔 |
| 方法簽名收 `Activity` / `View` / `Fragment` | 11 檔 |

`VTagViewModel` 甚至在建構子收 `KKdayApp`。`PaymentViewModel.kt:173` 方法收 `activity: Activity`。

**規則**：`context-in-viewmodel`（MUST NOT · on-touch）。量小，設到期目標：2 個 sprint 內清完。

<a id="m-07"></a>
### M-07 UiState 散落

| 項目 | 數字 |
|------|------|
| `data class *UiState` | 65 |
| `sealed *State` | 71 |
| 單一 ViewModel 最多 `MutableStateFlow` 欄位 | **36**（`ProductDetailViewModel`，2503 行） |
| 次高 | 16（`MemberPageViewModel`） |
| `SavedStateHandle` 使用 | 只有 6 檔 → 205 個 ViewModel 幾乎都沒處理 process death |

**觸碰時怎麼辦**：不要求把 36 個 flow 一次收斂成一個 UiState。新增欄位時加進既有 UiState（若有），沒有 UiState 的畫面新增欄位時建立 UiState 並只搬你要動的部分。

---

## 二、Coroutine / Rx

<a id="m-08"></a>
### M-08 硬寫 Dispatchers

| 項目 | 數字 |
|------|------|
| `Dispatchers.IO` 出現檔案 | 139（其中 ViewModel 38） |
| `viewModelScope.launch(Dispatchers.IO)` | 54 處 |
| 有宣告 `CoroutineDispatcher` 參數的檔案 | 只有 24（且多數帶 `= Dispatchers.IO` 預設值） |
| `runBlocking` | 30 檔 |
| `GlobalScope` | 6 檔 |

**規則**：`hardcoded-dispatcher`（MUST NOT · new-only+on-touch）、`run-blocking-prod`、`global-scope`。

> **提供點已存在，規則已啟用**：`CoroutinesScopeModule.kt:17-19` 已註冊 `named("DispatcherMain")` / `named("DispatcherIO")` / `named("DispatcherDefault")`，新程式碼直接注入即可，無須等基建。
> **基建待辦（一個小 PR，零風險）**：`libs/model/src/main/java/com/kkday/data/consts/KoinConstant.kt` 補 `DISPATCHER_MAIN = "DispatcherMain"` / `DISPATCHER_IO = "DispatcherIO"` / `DISPATCHER_DEFAULT = "DispatcherDefault"` 三個常數，並把 `CoroutinesScopeModule.kt:17-19` 與各注入點的字面字串改引用常數（值不變）。完成前字面字串是 `koin-named-string-literal` 的已知例外。詳細步驟見第八節基建項 A。

**正面樣板**：`PaymentViewModel.kt:66-69` 把 `ioDispatcher: CoroutineDispatcher` 當建構子參數注入，並註明是為了測試可控。

<a id="m-09"></a>
### M-09 RxJava2（已 EOL 2021-02-28）

| 項目 | 數字 |
|------|------|
| `import io.reactivex` | 194 檔 |
| 回傳 Rx 型別的 Retrofit endpoint | 209 / 528（40%），其中 `KKdayService.kt` 單檔 199 個 |
| `KKdayService.kt` 行數 | 1451 |
| 由 `Observable<AppState>` 驅動的 Presenter | 61 |

錯誤處理靠 Java 寫的 `RxJava2CallAdapterWithErrorInterceptor.java:53-80` 手動 `new JSONObject` 解析 metadata。

**規則**：`no-new-rxjava`（MUST NOT · new-only）。
**觸碰時怎麼辦**：見 [checklists/touch-legacy-rx.md](checklists/touch-legacy-rx.md)。要點：允許在 **Repository 邊界**用 `.asFlow()` / `.await()` 收斂，**禁止 Rx 型別穿透到 domain 或 UI 簽章**。不要整段重寫 Rx 鏈。

---

## 三、Compose / UI

<a id="m-10"></a>
### M-10 collectAsState → collectAsStateWithLifecycle

`collectAsState(` 103 檔 vs `collectAsStateWithLifecycle` 10 檔（僅 presale_chat、homeV2、chat、order_page 等新模組）。

配合 M-08 的 `stateIn(WhileSubscribed)` 覆蓋率極低（3 個 ViewModel），代表絕大多數 Compose 畫面在 STOPPED 狀態仍持續收集上游、背景資源無法釋放。

**規則**：`collect-as-state`（MUST NOT · new-only+on-touch）。
**批次遷移優先級：最高。** 機械式替換、風險低、收益明確，值得排一次性 PR 掃完。
**反例**：`MemberPageFragment.kt:222-242` 連續 12 個 `collectAsState()`。

<a id="m-11"></a>
### M-11 XML / View 系統

| 項目 | 數字 |
|------|------|
| `res/layout*/*.xml` | 1185 |
| Fragment 子類 | 177 |
| Activity 子類 | 157 |
| Epoxy（`EpoxyModel` / `EpoxyController`） | 248 檔 |
| `findViewById` | 247 檔 |
| `RecyclerView.Adapter` / `ListAdapter` | 100 檔 |
| `notifyDataSetChanged` | 105 檔 |
| ViewBinding | 101 檔 |

**規則**：`new-xml-layout`（MUST NOT · new-only）— 紅線 E1。
**觸碰時怎麼辦**：**不要**把既有 XML 畫面改寫成 Compose（除非該畫面本來就要重寫）。既有 Fragment 內要新增區塊 → 用 `ComposeView` 嵌入（見 [17-interop-views-compose.md](17-interop-views-compose.md)）。
**替代規則（A 級）**：不新增 `RecyclerView.Adapter` / Epoxy model，新清單一律 `LazyColumn`。
**`notifyDataSetChanged` 105 檔**：`migrate` 級，改 DiffUtil 有行為風險（動畫、捲動位置、選取狀態），不在功能 PR 裡順手改。

<a id="m-12"></a>
### M-12 Compose 慣例缺失

| 項目 | 數字 |
|------|------|
| `@Composable` 總數 | 3544 |
| 宣告 `modifier: Modifier = Modifier` | 406（**11%**） |
| 有 `LazyColumn` 的檔案 | 142 |
| `items` 帶 `key =` 的檔案 | 29 |
| `ComposeView` 使用 | 165 檔 |
| 設定 `ViewCompositionStrategy` | 只有 22 檔 |
| `@Preview` | 988 個 / 502 檔（58% 覆蓋） |
| `@PreviewParameter` | 13 檔 |
| multipreview（`@PreviewLightDark` 等） | 0 |
| 截圖測試（Paparazzi / Roborazzi） | 0 |

**最嚴重的一項**：設計系統旗艦元件 `KKButton.kt:51-64` 的公開 API **完全沒有 modifier 參數**，呼叫端無法調整 layout。`KKTextField` / `KKSelect` / `KKLabel` / `KKFormMessage` / `KKRadioButtonGroup` / `KKRadioButtonIcon` 同樣缺。

**規則**：`compose-modifier-missing`、`lazy-list-no-key`、`compose-view-strategy`。
**批次遷移候選**：設計系統元件補 modifier 參數（影響面可控、收益高，優先做）。
**`ViewCompositionStrategy` 未設**是官方明確的洩漏/狀態錯亂來源，143 個檔案有風險。正確範例：`MemberPageFragment.kt:141-144`。

<a id="m-13"></a>
### M-13 Material 2 / Material 3 混用

`androidx.compose.material.*` 374 檔、`material3` 454 檔，**103 檔在同一檔內同時 import 兩者**（如 `HomeScreen.kt:39-46` 混用 `material.pullrefresh` + `material3.Text`）。

**規則**：`no-new-material2`（MUST NOT · new-only）。
**觸碰時怎麼辦**：不要在功能 PR 裡把 M2 元件換成 M3（視覺會變）。新程式碼一律 M3。

<a id="m-14"></a>
### M-14 Accompanist 已廢止

版本停在 `0.28.0`（2023），28 檔使用，其中 `rememberSystemUiController` 20 檔。`accompanist-pager` / `pager-indicators` / `swiperefresh` / `systemuicontroller` 皆已由官方廢止（分別併入 foundation、Material3 `PullToRefresh`、`enableEdgeToEdge`）。

**規則**：`no-new-accompanist`（MUST NOT · new-only）。
**注意**：`rememberSystemUiController` 的替代方案與 targetSdk 36 edge-to-edge 相關，改動前先看 [15-performance.md](15-performance.md) 的 `SystemBarLegacyCompat` 段落。

<a id="m-15"></a>
### M-15 設計系統缺 theme 與深色模式

`StyleDictionary` 是 318 行的扁平 `object`（約 305 個 static val），**沒有任何 Compose Theme / CompositionLocalProvider**。因為 token 是編譯期常數而非 theme-aware，全 App 無法支援深色模式（`isSystemInDarkTheme` 使用次數 **0**，`libs/designsystem/design` 沒有 `values-night`）。

token 名稱中的 `Dark` / `Light` 是**色階**（shade）而非主題模式，不要誤用。

**這是架構級限制，不是可以順手修的項目。** 新程式碼照現有 token API 寫（見 [13-designsystem.md](13-designsystem.md)），不要自己造 theme。

---

## 四、資料層 / 網路層

<a id="m-16"></a>
### M-16 泛型抹除 endpoint 與雙重序列化

198 個 endpoint 宣告為 `suspend fun <T> ...: B2CApiResponse<T>`（佔 suspend endpoint 的 59%）。Gson 先反序列化成 `LinkedTreeMap`，再由 `apiResultData()` / `apiResultList()` 用 `gson.toJson` → `gson.fromJson` **二次轉換**成真型別，全庫 **256 個呼叫點**。

代價：雙倍序列化成本 + 零編譯期型別安全。

**規則**：`api-no-type-erasure`（MUST NOT · new-only）。新 endpoint 必須宣告具名回傳型別。
**正面樣板**：`IPresaleChatApiService.kt:33-50`（13 個 suspend fun，全部具名 DTO）。

<a id="m-17"></a>
### M-17 DTO 直送 UI

**269 個含 `@Composable` 的檔案** import `com.kkday.library.networking.resource.*`（占全庫 Compose 檔案 860 個的 31%）。

具體案例：`WishScreen.kt:104-108` 的 Composable 參數直接是網路 DTO `B2CProductCardData`；`BundleProductItemCard.kt:47-56` 參數是 `ProductInfo`。

DTO→domain mapper 只存在於最新三個功能（presale 16 處、chat 19 處、otpauth 4 處）共 13 檔，相對 457 個 model 檔覆蓋率極低。

**規則**：`dto-in-ui`（MUST NOT · new-only）— 紅線 C3。
**觸碰時怎麼辦**：新畫面必須有 UiModel / domain model。既有畫面**不要**為了合規把 269 個檔案的參數型別全換（會擴散到整條呼叫鏈）。

<a id="m-18"></a>
### M-18 Repository 缺介面

67 個 Repository 類，只有 21 個（31%）實作介面，46 個是直接被注入的具體類。且 repository 契約散落：`:domain:contract` 只有 8 個，另 13 個在各 feature 模組自己的 `domain/repository` 套件。

4 個完全沒有介面的 concrete class（`ProductRepository`、`BundleRepository`、`HotelProductRepository`、`HotelSearchRepository`）被 domain 層 UseCase 直接注入。

**同名衝突**：`com.kkday.data.repository.ProductRepository` 是 class，`com.kkday.product.domain.repository.ProductRepository` 是 interface，分屬兩個模組。

**規則**：`repository-needs-interface`（MUST · new-only）。
**觸碰時怎麼辦**：新 Repository 一律介面在 `:domain:contract` + Impl 在 `:data:repository`。既有 concrete class 不主動抽介面。

<a id="m-19"></a>
### M-19 四套錯誤處理機制

| 機制 | 數字 |
|------|------|
| Rx `onErrorResumeNext` + 手刻 `JSONObject` 解析 | KKdayService 路徑 |
| `sealed ApiResult`（`libs/model` 版，`Success.data`） | 185 檔 import |
| **同名但欄位不同的第二個 `ApiResult`**（`app.network.trans` 版，`Success.result`） | 42 檔 import |
| `kotlin.Result` + 自訂 `ApiException` | 67 檔（新功能） |
| `safeApiCall` | 244 次 / 38 檔 |

**兩個同名 `ApiResult` 是嚴重陷阱**：`Error` 一個帶 `ApiError` 一個帶 `Throwable`，import 錯了編譯過但語意錯。

額外問題：`BaseApiRepository.kt:100-108` 把 UI 狀態塞進 data layer 的 Flow（`onStart` 發 `Loading`、`onCompletion` 無條件發 `Loaded`）→ collector 用 `first()` 只會拿到 `Loading`；`Loaded` 在成功與失敗後都會補發。

**規則**：錯誤模型 owner 在 [05-data-layer.md](05-data-layer.md)。新程式碼用哪一套見該檔定案。

<a id="m-20"></a>
### M-20 Gson / kotlinx.serialization 混用

`com.google.gson` 502 檔、`@SerializedName` 394 檔 vs `kotlinx.serialization` 85 檔、`@Serializable` 69 檔。Retrofit 只註冊一個 converter factory（`KtConverterFactory`，內部包 Gson），kotlinx **沒有接成 converter**，只在程式碼內手動 `decodeFromString` → 形成「Gson 解一次 → kotlinx 再解一次」的混合路徑。

**規則**：`ser-kotlinx-for-new-dto`（MUST · new-only，**以檔案為單位**）+ 既有 Gson DTO 新增欄位維持 Gson（`exempt`，明文豁免）。
> 這條的邊界必須寫清楚：**新建 DTO 檔案**用 kotlinx；**既有 Gson DTO 檔案新增欄位**繼續用 `@SerializedName`，不得同 class 混用兩套註解。

**⚠️ 定時炸彈：48 個檔案同一個 class 混用兩套註解**

```kotlin
// libs/model/.../presale/PresaleOtherFaqsResponse.kt — 實際現況
@Serializable
data class PresaleFaqDto(
    @SerializedName("faq_oid") val faqOid: Int,     // kotlinx 不認得這個註解
)
```

kotlinx.serialization **完全忽略** `@SerializedName`，解析時會用 Kotlin 屬性名（`faqOid`）去對 JSON key（`faq_oid`）→ 對不到就取預設值，**不拋錯**。

這些程式碼現在能跑，只是因為 Retrofit 走的是 `KtConverterFactory`（內部包 Gson），Gson 認 `@SerializedName`，`@Serializable` 形同裝飾。**一旦有人把某個 endpoint 接上 kotlinx converter，該 DTO 的欄位會全部靜默變成預設值。**

- **規則**：`mixed-json-annotations`（MUST NOT · new-only+on-touch · lint，無例外）
- **觸碰時怎麼辦**：改到這類檔案時，把該 class 的註解統一成一套 —— 走 Gson 就拿掉 `@Serializable`，走 kotlinx 就把 `@SerializedName` 全換成 `@SerialName`。**不要只改你新增的那個欄位**（那會讓同一個 class 更混亂）。
- **注意**：`presale` 系列被多份準則列為正面樣板（DI、測試、mapper 分層都值得抄），但**它的 DTO 註解寫法不要抄**。

**其他已知問題**：
- `B2CApiResponse.kt:14-27`（DTO）自己實作 `KoinComponent` + `val gson: Gson by inject()`，還提供 `setDataModel(Class<*>)` 反射轉型 → 每個 response 物件都綁 DI 容器，單測必須起 Koin。
- `ApiService.kt:31-44` 每次呼叫都 `new Json { }`（kotlinx 官方要求重用實例）；`BaseApiRepository.kt:31-38` 做對了。同一 codebase 兩種寫法並存。

<a id="m-21"></a>
### M-21 OkHttp / Interceptor 問題

| 問題 | 位置 |
|------|------|
| 寫死 `.protocols(listOf(Protocol.HTTP_1_1))` 關閉 HTTP/2 multiplexing | `networkCoreModule.kt:127`、`RetrofitUtil.kt:69` |
| `ApiLogInterceptor`（落地完整 request/response 到 SQLite）開關是 **runtime 可變全域變數** `var isProductionEnv = false`，只在 `AppConfigManager.getAppConfig()` 首次呼叫時才設 true | `GlobalVar.kt:9`、`networkCoreModule.kt:183-185` |
| `B2CInterceptor` 與 network interceptor 把 exception catch 住回傳 `code(0)` 假 Response，body 是 `e.stackTraceToString()` → Retrofit 拿 stacktrace 文字去跑 Gson 解析 | `B2CInterceptor.kt:62-72`、`networkCoreModule.kt:163-174` |
| `libs/networking/app/MainApp.kt:38-47` 有 hardcode 的 auth token / x-auth-token / mixpanel id | 違反紅線「嚴禁硬編碼敏感資訊」 |

`ApiLogInterceptor` 的安全邊界依賴初始化順序而非編譯期隔離 —— **正解是移到 debug/staging sourceSet**。列為安全類遷移項，見 [18-security.md](18-security.md)。

**HTTP/1.1 寫死：不清償，只圍堵。** 規則 [`force-http1`](06-network.md#force-http1)（SHOULD NOT · new-only）只禁止新 client 指定 `protocols`、禁止從這兩處複製；**既有兩處在下列解鎖動作完成前不得移除，即使 `on-touch` 也不改**。

| 解鎖動作 | 負責 | 產出 |
|---------|------|------|
| 確認 B2C API gateway 的 HTTP/2（h2 over TLS）支援與已知行為 | 後端 / SRE | 書面結論（哪些 host 支援、有無 stream reset / 連線復用問題） |
| 確認 CDN 與圖片網域的 HTTP/2 支援 | SRE | 同上 |
| 依結論在 stage 環境拿掉 `.protocols(...)` 實測一輪（含長連線、上傳、3DS 導頁） | Android | 實測報告 |

三項齊備後，才把 `force-http1` 的 `enforce` 改為 `new-only+on-touch` 並移除既有兩處。**在此之前不得以「現代化清理」為由動它** —— 拿掉後的連線異常在線上難以歸因。

**HTTP/1.1 這兩處：現在是「圍堵」，不是「清理」。** 規則 `force-http1`（SHOULD NOT · new-only，owner [06-network.md](06-network.md)）只禁止**新的** `OkHttpClient` 複製這行；**既有兩處在解鎖動作完成前不得移除**，`on-touch` 也不改 —— 這兩行的原因未留紀錄，貿然拿掉可能造成線上連線異常且難以歸因（跨 CDN / gateway，症狀可能是偶發而非全面失敗）。

| 解鎖動作 | 誰做 | 完成後 |
|---------|------|-------|
| 由後端／SRE 確認 B2C API gateway 與 CDN 的 HTTP/2 支援狀態（含 ALPN 協商、既有 client 憑證鏈），並回報結論 | 後端／SRE | 結論為「支援」→ 把 `force-http1` 改為 `on-touch`，並排一支獨立 PR 拿掉這兩行 + stage 實測；結論為「不支援」→ 在這兩行加註解寫明原因，本項結案 |

<a id="m-22"></a>
### M-22 Room 與持久化

| 項目 | 現況 |
|------|------|
| Room version / exportSchema | `version = 1`, `exportSchema = false` |
| Migration / AutoMigration | **0 個** |
| Entity / DAO | 2 / 2（只涵蓋通知） |
| DAO suspend 或 Flow 覆蓋率 | 100% ← 這點正確 |
| `SharedPreferences` 生態 | `PersistentManager` 219 檔 + `PreferencesHelper` 111 檔 + 直接用 27 檔 |
| `DataStore` | 24 檔（其中 4 個是 DI/測試） |

`exportSchema = false` 代表**沒有任何歷史 schema JSON**：現在去改 `ChatNotificationEntity` / `PushNotificationEntity` 的欄位，Room 沒有比對基準，等於靜默資料遺失或啟動崩潰。因此 `entity-change-no-migration`（MUST · new-only+on-touch，owner [07-persistence.md](07-persistence.md)）現在就生效：**改既有 entity 結構一律先問；新增獨立 entity + DAO 不受限，但同一 PR 要 bump `version` 並加 `AutoMigration`。** 真的要改既有 entity → 先做基建項 F。

**規則**：`ds-no-new-sharedpreferences`（MUST NOT · new-only）。新的持久化需求優先評估 DataStore，不要為單一 feature 擴大 Room 表面積（Room 在本專案只服務通知）。
> 規則寫成「**禁止新增 key**」而非「禁止使用 SharedPreferences」，否則 `on-touch` 會逼人改資料層、涉及資料搬移風險。

---

## 五、模組化 / 建置

<a id="m-23"></a>
### M-23 `compileOnly(project(...))` 反模式

**163 處**（對比 `implementation(project)` 180 處、`api(project)` 僅 4 處）。

`compileOnly` 的 project 依賴不進入 runtime classpath，等於把所有 runtime 組裝責任推給 `:app` → 模組無法獨立編譯 / 測試 / 驗證。Google 與 nowinandroid 皆未使用此模式。

最重的：`libs/feature/hotel/product/build.gradle.kts`（20 筆）、`libs/feature/product_page/build.gradle.kts`（19 筆）。

`AndroidFeatureConventionPlugin.kt:20-32` 直接以 `compileOnly` 注入 11 個 project 依賴（含 `:data:repository`、`:data:roomDb`、`:domain:usecase`）→ 每個 feature 模組一律「看得到但拿不到」整個 data 層。

**實際代價**：模組跑不了自己的 JVM/instrumented 測試（runtime 缺類）、無法獨立驗證 DI 綁定、任何 runtime 缺漏都延後到 `:app` 組裝甚至上線才爆。這也是當初評估 Hilt 時的阻礙之一（見 [M-27](#m-27)），但**現在它的成本與 DI 框架無關**：只要模組要有自己的測試，就必須改掉。

**規則**：`no-compile-only-project`（MUST NOT · new-only）。新模組依賴一律 `implementation` / `api`。

<a id="m-24"></a>
### M-24 依賴方向錯誤

| 問題 | 證據 |
|------|------|
| `:domain:usecase` 直接 `implementation :data:repository` / `:data:networking:api` / `:data:model` | `domain/usecase/build.gradle.kts:10-14`；7 個 main 檔案直接 `import com.kkday.data.repository.*`，17 檔 import `com.kkday.model.*` |
| `:domain:usecase` **沒有宣告** `:domain:contract` 依賴，卻 import 51 處 `com.kkday.library.*` —— 透過 `:data:networking:api` 的 `api(project(":domain:contract"))` 傳遞取得 | domain 存取自己的契約要繞經 networking 模組，依賴路徑完全倒轉，且屬未宣告的隱性依賴 |
| `:domain:contract` 自己依賴 `:data:model` | `domain/contract/build.gradle.kts:10` → domain 層無法在不帶 Retrofit/Gson 的情況下編譯 |
| feature 模組互相依賴 | 47 條 project 依賴邊，其中 **11 條是頂層 feature 互依**（`chat → home/order`、`presale_chat → chat`、`search → ticket`、`product → transportation`、`transportation → coupon_page`、`hotel:product → product`） |
| `:feature:shared:ui`（純 UI 共用模組）反向依賴 `:data:repository` / `:data:networking:api` / `:domain:usecase` | `libs/feature/shared_ui/build.gradle.kts:21-23` |

**規則**：`android-in-domain`、`domain-imports-impl`（MUST NOT · new-only+on-touch）、`no-feature-to-feature-dep`（MUST NOT · new-only）。
**前置基建**：專案**沒有任何**模組依賴規則的自動檢查（無 dependency-analysis plugin、無 module graph assertion、無自訂依賴方向 task）→ 建議加一支檢查 task 進 CI。

<a id="m-25"></a>
### M-25 建置設定過時項

| 項目 | 現況 | 處置 |
|------|------|------|
| `buildSrc` 殘留 | 只剩 6 行 `DistConfig.kt`，但任何變動都會使全專案 task 失效並拖慢 configuration | 併入 `build-logic`，刪除 buildSrc |
| `composeOptions.kotlinCompilerExtensionVersion = 1.5.15` | Kotlin 2.0 起**完全無效**的死設定，卻留在 convention plugin 與 3 個模組 → 誤導開發者以為 compiler 是 1.5.15（實際隨 Kotlin 2.1.0） | 刪除該設定與 `androidxComposeCompiler` version 條目 |
| `kotlinOptions {}` + jvmTarget 字串 DSL（用 `(this as ExtensionAware).extensions.configure("kotlinOptions")` 反射取用） | 已淘汰 | 改 `kotlin { compilerOptions { jvmTarget.set(JvmTarget.JVM_17) } }` |
| kapt 無條件套用到所有 application 模組 | `AndroidApplicationConventionPlugin.kt:29` 硬套 `kotlin-kapt`；實際 kapt 依賴 3 處（autoValue、reductor compiller） | 改為 opt-in；reductor 是移除 kapt 的最後阻礙（見 M-01） |
| `:app` 混用新舊 variant 過濾 API | convention 用 `androidComponents.beforeVariants`，`:app` 又用 deprecated 的 `android.variantFilter` + `gradle.startParameter.taskNames` 字串判斷 → 也是 configuration cache 的直接阻礙 | 統一到 `beforeVariants` |
| `composeCompiler {}` DSL | 完全沒有 → strong skipping 僅靠 Kotlin 2.1 預設、無 compiler metrics / stability config，無法量測 recomposition | 前置基建項，**與上一列刪死設定併為同一支 build-logic PR**：加 `composeCompiler { stabilityConfigurationFiles / metricsDestination / reportsDestination }` + `compose_compiler_config.conf` |

> 在這支 build-logic PR 完成前，穩定性照 `uistate-stability-default`（新 UiState 不標註）、效能主張照 `perf-claim-without-evidence`（無量測不得宣稱），兩條都已是現行規則，不等基建。功能 PR 內**不要**自建 `compose_compiler_config.conf`。

**版本落後項**：`navigation 2.7.7`（type-safe route 需 2.8+）、`lifecycle 2.6.0`、`okhttp 4.9.0`、`gson 2.8.8`、`mockk 1.12.5`、`mockito 3.0.0`、`assertj 3.23.1`、`accompanist 0.28.0`。
**應直接刪除**：`dagger = "2.48.1"` 與 `dagger` / `dagger-compiler` 兩個 library 條目（`gradle/libs.versions.toml:84, 303-304`）—— 全庫零引用，且本專案已定案不採用 Hilt/Dagger（見 [M-27](#m-27)），留著只會讓人以為 Hilt 是選項。
**缺少宣告（不是落後）**：`koin-test`、`turbine` 兩個 testImplementation 依賴不存在 → 見第八節基建項 C、D。
> 依 AGENTS.md，**升版必須先取得確認**，不得為了讓建置通過自行調整。刪除零引用的孤立宣告不算升版。

**navigation 2.7.7 → 2.8+ 的影響面**（升版評估用；升版前一律照 [12-navigation.md](12-navigation.md) 的 `route-string-convention` 寫字串 route）：

| 影響項 | 內容 |
|-------|------|
| 四個 artifact 共用同一個 version ref | `navigation-fragment-ktx`、`navigation-ui-ktx`、`navigation-compose`、`navigation-safe-args-gradle-plugin`（`gradle/libs.versions.toml:40, 206-208, 404`）→ 不能只升 Compose 那一個 |
| XML nav graph | 13 份 graph、`findNavController` 20 檔跟著換底層（見 [M-11](#m-11)） |
| safe-args 產碼 | plugin 套用在 convention（`AndroidApplicationConventionPlugin.kt:31`，全部 application 模組）+ 3 個 library 模組（`product_page`、`coupon_page`、`transportation`），classpath 宣告在 root `build.gradle.kts:29` → 升版會重產所有 `XxxDirections` / `XxxArgs`，需全量編譯驗證 |
| 傳遞依賴會被拉高 | navigation 2.8 會連帶抬升 lifecycle / compose runtime 的傳遞版本（目前 `lifecycle 2.6.0`）→ 影響面遠大於 navigation 本身。實際數字以升版後 `./gradlew :app:dependencies` 為準，**不要憑印象估** |
| 導航機制不只一套 | 本專案 Compose Navigation / XML nav graph / KRouter / `startActivity` 四套並存，升版只解決其中一套的寫法問題，不會減少機制數量 |
| 決策未結 | P-02「留 2.x vs 評估 navigation3」尚未定案（[91-decisions.md](91-decisions.md)）→ 應先結掉再談升版 |

**升版前的實際做法**：照 [12-navigation.md](12-navigation.md) 的字串 route 慣例寫（route 常數集中在各 feature 的 `navigation/XxxRoutes.kt`、參數只傳識別碼、取值走 `SavedStateHandle`）。**這不是暫時方案** —— 即使日後升到 2.8+，這些寫法都能平順轉成 type-safe route；反之若現在到處寫字面字串、把整包 model 塞進 route，升版時要重寫的是呼叫點而不只是宣告。

---

## 六、DI

<a id="m-26"></a>
### M-26 Koin 使用現況

| 項目 | 數字 |
|------|------|
| DSL `val xxx = module { }` | 64 個 top-level 變數 |
| `@Module @ComponentScan` 類別 | 19 個 |
| `startKoin` 一次載入的 module 數 | 59（`KKdayApp.kt:233-298`，其中 `actionModule` 重複列兩次） |
| `by inject()` | 758 處 |
| 實作 `KoinComponent` 的類別 | 218 |
| `KoinJavaComponent` | 35 |
| `named()` 字串 qualifier / `@Named` | 83 / 15 |
| Koin scope（`scope { }` / `@Scope`） | **0**（只用 single / factory / viewModel） |
| `checkModules` / `verify()` / KoinTest | **0** → DI 錯誤只能 runtime crash 才發現 |
| 主動關閉 `KOIN_CONFIG_CHECK` 的模組 | 3（chat、hotel:product、presale_chat） |

**規則**：`service-locator-get`、`manual-impl-instantiation`（· new-only）。
**白名單**（`by inject()` 允許出現的位置）：`Activity` / `Fragment` / `Application` / `Service` / `BroadcastReceiver` / `Worker`。**Composable 內禁止 `by inject()`**，只允許 `koinViewModel()`。
**前置基建**：`koin-test` 依賴未加入 → 見第八節基建項 C。加完後 `koin-module-not-verified` 才有辦法用 `module.verify()` 落實。
**三個關閉 `KOIN_CONFIG_CHECK` 的模組**（`libs/feature/chat`、`libs/feature/hotel/product`、`libs/feature/presale_chat` 的 `build.gradle.kts:10-13`）：**觸碰到該模組的 DI 檔案時順手打開並修掉重複綁定**，不要為此另開 PR，也不要在新模組複製這個關法。
**正面樣板**：`libs/feature/presale_chat/.../di/PresaleChatModule.kt` 全面採用 annotation 風格（`@Module` + `@ComponentScan` + `@Single` + `@KoinViewModel` + constructor injection）。**新模組照這個抄。**
**service locator 邊界**：`KoinJavaComponent` 35 處、`KoinComponent` 218 個類別 —— 新程式碼一律建構子注入；`KoinJavaComponent.get()` / `getKoin().get()` 只允許出現在 `:app` 的 `di/` 套件（見 `di-container-single-framework`）。

<a id="m-27"></a>
### M-27 不採用 Hilt 的技術理由（存查）

**這一節不是待辦，是結案紀錄。** 本專案 DI 一律 Koin（決策見 [91-decisions.md](91-decisions.md) D-01），Hilt / Dagger / `javax.inject` 一律不引入。下表是當初評估時實測到的阻礙 —— **技術事實仍然成立**，留著是為了讓後續有人再提「要不要導入 Hilt」時，不必重跑一次調查。

現況：`hiltViewModel` 使用數 **0**，Hilt 完全未落地；`dagger 2.48.1` 在 version catalog 是零引用的孤立宣告（應刪，見 M-25）。

| 阻礙 | 說明 | 可否用小成本解掉 |
|------|------|----------------|
| **base class 帶必填建構子參數** | `BaseActivity<VB: ViewBinding>(val bindingFactory: (LayoutInflater) -> VB)` → Hilt 生成的 `Hilt_XxxActivity` 無法轉發 super 建構子參數，**52 個畫面無法加 `@AndroidEntryPoint`**。同樣問題在 `BaseFragment<VB>(inflate)`、`BaseBottomSheetDialogFragment`、`BaseDialogFragment` | 否，要改 4 條繼承鏈的 API 與 52 個畫面 |
| **`attachBaseContext()` 時序** | `BaseComposeActivity.kt:24-25,49-70` 與 app 層 `BaseActivity.kt:17,33-43` 在 `attachBaseContext()` 內就用 `by inject()` 取 `IResourcesProxy` / `ILocaleHelper` 做 locale 包裝。`attachBaseContext` 早於 `onCreate`，Hilt 欄位注入在 `onCreate` 才發生 | **否，這是硬時序**。這條路徑無論如何都得留 Koin → 必然雙框架並存 |
| **Application 層不可橋接** | Hilt `@Inject` 欄位在 `super.onCreate()` 內、`startKoin` 之前解析 → 橋接必然 `NoDefinitionFoundException` | 否 |
| **debug flavor 有第二個 Application** | `KKdayDebugApp` 繼承 `KKdayApp`，manifest 分兩份；`@HiltAndroidApp` 只能標在父類 | 需重整 Application 繼承結構 |
| **qualifier 同名陷阱** | 83 處 `named()` + 15 處 Koin `@Named`；`org.koin.core.annotation.Named` 與 `javax.inject.Named` **同名**，共存期間誤 import 會編過但綁錯 | 否，只能靠人工 review 擋 |
| **build 設定無 opt-in** | `configureDI` 由 convention plugin 無條件套用到 26 個 library + 7 個 application 模組 → 需另建 `HiltConvention` 並逐模組開關 | 工程量中等，但收益為零 |
| **`compileOnly` 模組邊界** | 見 [M-23](#m-23)，163 處 `compileOnly(project)` 會讓 feature 模組的 Hilt `@Module` `NoClassDefFound` | 否，是 163 處的獨立大工程 |

**結論**：第 2 項（`attachBaseContext` 時序）單獨就足以否決 —— 它代表 Koin 永遠移不掉，導入 Hilt 得到的不是「換框架」而是「兩套框架同時在跑」，外加一層只能放 `:app` 的橋接程式碼。第 1、7 項各自是獨立的大型重構，且完成後對業務零收益。**因此本專案 DI 一律 Koin**，投入改投在 Koin 這側能立即兌現的地方（module `verify()` 測試、annotation 風格統一、消滅 service locator）。

**這個結論如何體現在規則裡**：

| 規則 | 狀態 |
|------|------|
| `di-container-single-framework`（MUST NOT · new-only+on-touch） | 只有 Koin 一套容器；禁止第二套 DI 框架與跨框架橋接碼 |
| `hilt-module-no-installin`、`hilt-scope-mismatch` | `exempt`，`rules.yaml` 內附 `reason`（不刪條目，留負面訊號，避免有人重新加回來） |

不要再寫「Hilt 橋接」「Hilt 前置條件」「等 `HiltConvention`」這類敘述 —— 它們已經不是本專案的待辦。

---

## 七、測試 / 品質工具

<a id="m-28"></a>
### M-28 測試堆疊落後

| 項目 | 現況 |
|------|------|
| 單元測試 | 252 檔 / 1804 `@Test` / 24 個模組（總模組 53） |
| androidTest | **8 檔**（含 1 helper）→ instrumented test 幾乎放棄 |
| Turbine / Robolectric / Truth / Compose UI test | **全部 0** |
| MockK / Mockito 並存 | 84 檔 / 8 檔 |
| AssertJ / `org.junit.Assert` 並存 | 38 檔 / 176 檔 |
| `mockk(relaxed = true)` | **220 處** ← 軟性假綠燈主要來源 |
| `@Ignore` | 6 處 |
| 斷言被註解掉但檔案留著 | 5 檔（`MainViewModelTest.kt` 整檔 @Ignore + 11 行註解掉的 assert） |
| 完全無斷言的測試 | **0 檔** ← 這點優於多數同規模專案 |
| 恆真斷言 / 空 catch 吞例外 | 0 |

**規則**：`test-no-assert`、`assert-tautology`、`relaxed-mock-overuse`、`commented-out-assertion`。
**正面樣板**：`GetPresaleOtherFaqsUseCaseTest.kt`（手寫 Fake、`runTest`、AssertJ 具體斷言、涵蓋成功/空/失敗三路徑）、`PresaleChatViewModelTest.kt`（`StandardTestDispatcher` + `Dispatchers.setMain` + `advanceUntilIdle`，並註明為何用 Fake 而非 MockK）、`OtpRegisterViewModelTest.kt:119`（`backgroundScope.launch(UnconfinedTestDispatcher(...))` 收 Flow 序列）。

**基建清單（各為一支獨立小 PR，與規則解耦 —— 規則現在就生效，基建只是讓寫法更好看）**：

| # | 基建 | 影響的規則 | 現況 |
|---|------|-----------|------|
| T-1 | **加 `app.cash.turbine`**：`gradle/libs.versions.toml` 新增條目 + `TestingConvention.kt` 加 `testImplementation` | [`flow-sequence-without-turbine`](14-testing.md#flow-sequence-without-turbine) —— 依賴進來後把手動 collect 換成 `test { awaitItem() }`，並把規則正文的「禁止 import」改成「序列驗證一律用 Turbine，手動 collect 僅保留於既有測試」 | 未加入，**現在 import 會編譯失敗** |
| T-2 | MockK 1.12.5 / AssertJ 3.23.1 / Mockito 3.0.0 升版（Mockito 應直接移除） | `mockito-in-new-test`、`junit-assert-in-new-test` | 全部停在 2019–2022 年版本 |
| T-3 | `koin-test` + `module.verify()` | 見 M-26 | 只覆蓋 `chatModule` |
| T-4 | `TestingConvention.kt:28-41` 有 7 行依賴宣告重複貼上兩次，順手修掉 | — | 未修 |

**不列入基建的**：`androidx.compose.ui:ui-test-junit4` / `ui-test-manifest`。畫面驗收改走 [`screen-acceptance-coverage`](14-testing.md#screen-acceptance-coverage)（四分支 `@Preview` + Maestro flow + ViewModel 單元測試），Maestro/Mockoon 資產見 M-30，比引入第三套 UI 測試框架務實。截圖測試選型 P-05 若日後定案，再回頭評估。

<a id="m-29"></a>
### M-29 靜態檢查覆蓋不足

| 項目 | 現況 |
|------|------|
| 套用 detekt 的模組 | **1**（僅 `:app`）／總模組 53 |
| detekt 規則 `active: false` vs `active: true` | **117 vs 87** ← 關掉的比開啟的多 |
| 關閉最集中處 | formatting 36 條（含 `ImportOrdering`、`ChainWrapping`、`FinalNewline`）、style 34 條 |
| ktlint / spotless | 不存在 → 格式面實質無人把關 |
| detekt 自訂規則 | 0 |
| Compose 專用靜態檢查（compose-rules / detekt-compose） | **0** ← 這正是 modifier 缺失率 89%、`collectAsState` 濫用能長期存在的原因 |
| Android Lint baseline 未追蹤 issue | **2776**（app 2414 + designsystem 362） |
| CI 執行 Android lint 的 workflow | **0** |
| Kover 套用模組 | 2 |
| 覆蓋率門檻 | 無 `koverVerify`；codecov threshold 0%（僅防退步） |
| 自訂 lint 規則 | 1（`libs/tool/lint` 的 `FragmentDetector`）← 可作為擴充基礎 |

**前置基建**：
1. detekt 套用到所有模組（或至少所有 feature 模組）
2. 加入 Compose 靜態檢查 ruleset
3. lint 進 CI
4. `TestingConvention.kt:28-41` 有整段 7 行依賴**重複貼上兩次**，順手修掉

<a id="m-30"></a>
### M-30 E2E 基礎（狀況良好）

Maestro 100 個 yaml / 11 個功能域 / 7 個共用 flow；Mockoon mock JSON 162 個。這塊不是技術債，是資產。

---

## 八、前置基建（小型 PR，做完可強化規則）

**這些不是規則的前置條件 —— 沒有它們，對應規則一樣現在就生效**（見 [README.md](README.md) 的 enforce 說明：本專案不使用 `dormant`）。它們的價值是「把現在靠人記住的事變成工具擋得住的事」。每一項都是**獨立小 PR**，不要併進功能 PR，也不要一次做完六項。

| # | 基建 | 強化哪條規則 | 風險 |
|---|------|------------|------|
| A | `KoinConstant` 補三個 dispatcher 常數 | `koin-named-string-literal`、`hardcoded-dispatcher` | 零 |
| B | `WhileUiSubscribed` 常數 | `statein-while-subscribed` | 低 |
| C | `koin-test` 依賴 | `koin-module-not-verified` | 低（僅 test classpath） |
| D | `turbine` 依賴 | `flow-sequence-without-turbine` | 低（僅 test classpath） |
| E | `composeCompiler {}` DSL + stability config + 刪死設定 | `uistate-stability-default`、`perf-claim-without-evidence` | 中低（需全量 build 驗證） |
| F | Room `exportSchema = true` + 歷史 schema + migration 測試 | `entity-change-no-migration` | 低，但 schema JSON 要人工核對 |

### A. `KoinConstant` 補 dispatcher 常數（零風險）

**做什麼**：`libs/model/src/main/java/com/kkday/data/consts/KoinConstant.kt` 加三個常數，並把 `app/src/main/java/com/kkday/member/di/CoroutinesScopeModule.kt:17-19` 的字面字串改成引用它們（**字串值不變**，DI 綁定完全等價）。

```kotlin
// KoinConstant.kt — 加在既有六個常數之後
const val DISPATCHER_MAIN = "DispatcherMain"
const val DISPATCHER_IO = "DispatcherIO"
const val DISPATCHER_DEFAULT = "DispatcherDefault"
```

```kotlin
// CoroutinesScopeModule.kt
single(named(KoinConstant.DISPATCHER_IO)) { Dispatchers.IO }
```

**注意**：`KoinConstant` 在 `:data:model`。注入端要引用常數，該模組必須看得到 `:data:model`；看不到的模組**維持字面字串 `@Named("DispatcherIO")`**，不要為了引用常數去加模組依賴。
**做完之前**：注入端一律寫 `@Named("DispatcherIO")` 字面字串 —— 這是 `koin-named-string-literal` 目前的明文例外。**不要寫 `KoinConstant.DISPATCHER_IO`，那個常數現在不存在，會編譯失敗。**

### B. `WhileUiSubscribed` 常數（低風險）

**做什麼**：在 `:shared:base`（`libs/base/src/main/java/com/kkday/library/common/util/`）新增一個常數檔，並修掉全庫唯一的魔術數字 `app/.../homeV2/presentation/HomeViewModelV2.kt:94` 的 `WhileSubscribed(5000)`。

```kotlin
package com.kkday.library.common.util

/** `stateIn` 的 `SharingStarted.WhileSubscribed` 停止逾時（毫秒）。5 秒可跨越設定變更重建，避免旋轉螢幕就斷開上游。 */
const val WhileUiSubscribed = 5_000L
```

**注意**：`:shared:base` 已被 28 個模組依賴（含 `:app`），不需新增依賴。
**做完之前**：新程式碼照 `statein-while-subscribed` 寫 `WhileSubscribed(5_000L)`，**不得寫無參數的 `WhileSubscribed()`**（`stopTimeoutMillis = 0`，旋轉螢幕就重訂閱）。既有 4 處違規列在 [M-05](#m-05)。

### C. `koin-test` 依賴（低風險）

**做什麼**：
1. `gradle/libs.versions.toml` 加 `koin-test = { group = "io.insert-koin", name = "koin-test" }`（版本由既有 `koin-bom` 帶，不要另外寫 version）。
2. `build-logic/convention/src/main/kotlin/com/kkday/convention/DIConvention.kt` 的 `dependencies { }` 內加 `"testImplementation"(platform(...koin.bom...))` 與 `"testImplementation"(libBy("koin.test"))` —— 與 `"ksp"(libBy("koin.compiler"))` 同一種寫法。

**注意**：`configureDI` 無條件套用到 26 個 library + 7 個 application 模組，所有模組的 test classpath 都會多一個依賴 → 合併前跑一次 `./gradlew testDevelopDebugUnitTest` 全量驗證。
**做完之後**：新增 `@Module` 的模組要附一支 `XxxModule().module.verify(extraTypes = listOf(Context::class))` 測試；三個關閉 `KOIN_CONFIG_CHECK` 的模組（見 M-26）順手打開。
**做完之前**：DI 綁定正確性只能靠 `KOIN_CONFIG_CHECK` 的編譯期檢查 + 手動跑 App，**因此更不能關掉 `KOIN_CONFIG_CHECK`**。

### D. `turbine` 依賴（低風險）

**做什麼**：`gradle/libs.versions.toml` 加 `app.cash.turbine:turbine`（版本取當時最新 stable），並在 `TestingConvention.kt` 的 `dependencies { }` 加 `"testImplementation"(libBy("turbine"))`。順手修掉 `TestingConvention.kt:28-41` **整段 7 行重複貼上兩次**的問題。

**注意**：與 mockk / assertj 升版**分開做**，不要一支 PR 動整個測試堆疊。
**做完之前**：Flow 序列驗證照 `PresaleChatViewModelTest.kt` 手動 collect（`backgroundScope.launch` + `advanceUntilIdle()`），**禁止 `import app.cash.turbine.*`，依賴不存在會編譯失敗**。

### E. `composeCompiler {}` DSL + 刪除失效設定（中低風險）

**做什麼**（同一支 build-logic PR）：
1. **刪除失效設定**：`composeOptions { kotlinCompilerExtensionVersion = ... }` 自 Kotlin 2.0 起完全無效（compiler 隨 Kotlin 版本走，實際是 2.1.0），出現在 4 個地方 —— `build-logic/.../AndroidComposeConvention.kt:21-23`、`libs/designsystem/app/build.gradle.kts`、`libs/designsystem/design/build.gradle.kts`、`libs/UI/kkcomponents-app/build.gradle.kts`；連同 `gradle/libs.versions.toml:20` 的 `androidxComposeCompiler = "1.5.15"` 一起刪。留著只會讓人誤以為 compiler 是 1.5.15。
2. **加 `composeCompiler {}` 設定**：專案已套用 `org.jetbrains.kotlin.plugin.compose`（`AndroidLibraryConventionPlugin.kt:25`、`AndroidApplicationConventionPlugin.kt:34`），DSL 直接可用。新增 `config/compose/stability_config.conf` 列出視為穩定的專案型別，metrics / reports 以 Gradle property 開關（不要每次 build 都產出）。

**注意**：convention plugin 內沒有 `composeCompiler { }` 的 Kotlin accessor，要用 `extensions.configure<ComposeCompilerGradlePluginExtension> { }`；屬性名（`stabilityConfigurationFiles` / `metricsDestination` / `reportsDestination`）以專案實際的 Kotlin 2.1.0 plugin 為準，實作時對照 plugin API 確認。stability config 會改變 skippability → 合併前跑一次全量 build。
**做完之前**：`uistate-stability-default`（新 UiState 用唯讀集合、不預先撒 `@Immutable`）與 `perf-claim-without-evidence`（無量測不得宣稱效能改善）已經生效，**功能 PR 內不要自建 `compose_compiler_config.conf`**。

### F. Room `exportSchema = true` + migration 樣板（低風險）

**做什麼**：
1. `data/roomDb/src/main/java/com/kkday/database/AppDatabase.kt:15` 改 `exportSchema = true`。
2. `data/roomDb/build.gradle.kts` 加 `ksp { arg("room.schemaLocation", "$projectDir/schemas") }`（Room Gradle plugin 未在 version catalog，走 ksp arg 即可）。
3. 產出並 **commit** `data/roomDb/schemas/com.kkday.database.AppDatabase/1.json`。
4. version catalog 加 `androidx.room:room-testing`，寫一支 `MigrationTestHelper` 樣板測試（現在沒 migration 可測，但樣板要先在）。

**注意**：`exportSchema` 只影響編譯期輸出，不改 runtime schema，風險低；但產出的 `1.json` 必須確實對應**線上現有的表結構**，兩個 entity（`ChatNotificationEntity`、`PushNotificationEntity`）的欄位要人工核對後才 commit —— 這份 JSON 一旦錯，之後所有 migration 都以錯的基準比對。
**做完之前**：`entity-change-no-migration` 的守門版生效 —— **改既有 entity 結構一律先問**；新增獨立 entity + DAO 可以做，但同一 PR 要 bump `version` 並加 `AutoMigration`。

> **不屬於小型 PR 的基建**：模組依賴方向檢查 task（見 [M-24](#m-24)）、detekt 套用到全模組 + Compose ruleset + lint 進 CI（見 [M-29](#m-29)）。這兩項工程量與影響面都大，走專案級任務，不在這一節。

---

## 九、批次遷移候選（優先級排序）

**排序原則已改**：規則不再等基建，所以基建不再是「解鎖」而是「加強」。優先級改以**單位工程量的違規攔截效果**排序 —— 能讓工具自動擋住新違規的排前面，純數量清理排後面。

| 優先 | 項目 | 影響面 | 風險 | 為什麼是這個順位 |
|-----|------|-------|------|----------------|
| 1 | 前置基建 A～D（見第八節：`KoinConstant` / `WhileUiSubscribed` / `koin-test` / `turbine`） | 小 | 低 | 四支各半天的小 PR，做完四條規則從「靠人記得」變成「工具可驗」 |
| 2 | detekt 套用到所有模組 + Compose ruleset | 小 | 低 | 目前 52/53 個模組零靜態檢查；這是唯一能大規模防止新違規的一項 |
| 3 | `collectAsState` → `collectAsStateWithLifecycle`（103 檔） | 中 | 低 | 機械式替換、收益明確 |
| 4 | 設計系統元件補 `modifier` 參數（KKButton 等 7 個） | 小 | 低 | 修一次全庫受益，且解掉 89% 缺失率的源頭 |
| 5 | 前置基建 E（`composeCompiler {}` + 刪 `kotlinCompilerExtensionVersion` 死設定） | 小 | 中低 | 順手併 `buildSrc` → `build-logic`，一次清掉兩個誤導來源 |
| 6 | `ViewCompositionStrategy` 補齊（143 檔） | 中 | 低 | 官方明確的洩漏來源 |
| 7 | 48 檔混用 `@Serializable` + `@SerializedName` 統一成一套 | 中 | 低 | 接 kotlinx converter 前必須清完，否則欄位靜默變預設值 |
| 8 | 兩個同名 `ApiResult` 收斂成一個 | 中 | 中 | 目前是 import 錯就語意錯的陷阱；需先結掉 P-01 |
| 9 | public Mutable 狀態收斂（33 處） | 小 | 低 | 數量小、破壞 UDF |
| 10 | 前置基建 F（Room schema）+ 模組依賴方向檢查 task | 小～中 | 低 | 沒有立即痛點，但都是「錯了才發現」類問題的唯一防線 |
| 11 | `AndroidViewModel` / ViewModel 持 Context（16 + 35 檔） | 中 | 中 | 洩漏風險 |
| 12 | `compileOnly(project)` → `implementation`（163 處） | 大 | 中 | 模組要能獨立測試就得改；與 DI 框架無關（見 M-27） |
| 13 | feature 互依 11 條解耦 | 大 | 高 | 架構級，需獨立規劃 |
| 14 | Reductor / RxJava 退場 | 極大 | 高 | 需長期路線圖，非單一任務 |

**已從清單移除**：Hilt 導入與其前置條件（本專案不採用，見 [M-27](#m-27)）。

---

## 十、本次未修登記區

格式：`- [規則 id] 檔案路徑 — 原因（PR 連結）`

<!-- 新增條目請加在下方，不要刪除既有條目 -->

（尚無登記）

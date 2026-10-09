# 01 · 架構分層與依賴方向

這份管**層與層之間的邊界**：哪一層放什麼、依賴只能往哪個方向、跨層能用什麼型別、model 要分幾層、在哪裡轉換。
它**不管**層內部怎麼寫——UseCase 要不要開、Repository 怎麼命名、UiState 怎麼設計、模組怎麼切，都在別的檔案。
碰到「這段邏輯該放哪」先看第二節的判斷表，那是這份檔案最常用的部分。

| 主題 | 去哪 |
|---|---|
| 模組依賴圖、`:core:*` 不得依賴 `:feature:*`、循環依賴、`implementation` vs `api` | `02-modularization` |
| DI 綁定寫法、scope、qualifier、建構子注入 | `03-dependency-injection` |
| UseCase 該不該開、命名、domain 層不得 import Android、domain model 不得帶框架註解 | `04-domain-layer` |
| Repository 命名、SSOT 實作、錯誤傳遞、mapper 寫法、`Context` 不得進 Repository 簽章 | `05-data-layer` |
| DTO 序列化、Retrofit / OkHttp 設定 | `06-network` |
| Entity、Room / DataStore 選型 | `07-persistence` |
| UiState 設計、one-off event、ViewModel 內部規範、不得暴露 Mutable 狀態 | `08-ui-state` |
| `suspend` / `Flow` 用法、dispatcher 注入、取消 | `12-coroutines-flow` |
| 畫面跳轉、single-activity、參數怎麼傳 | `13-navigation` |
| 各層測什麼、fake 還是 mock | `15-testing` |

---

## 一、三層的職責邊界

| 層 | 負責 | 不負責 | 對外只能公開 |
|---|---|---|---|
| **UI**（`:feature:*`：Composable、ViewModel、UI model） | 呈現狀態、接收操作、把 domain model 轉成看得懂的樣子 | 決定資料從哪來、快取、重試 | — |
| **Domain**（`:core:domain`、`:core:model`：UseCase、domain model、Repository 介面） | 可重用的商業規則、跨資料來源的組合 | Android 平台細節、呈現細節 | `suspend fun` / `Flow`，純 Kotlin 型別 |
| **Data**（`:core:data`、`:core:network`、`:core:database`：Repository 實作、DataSource、DTO、Entity） | 資料的唯一擁有者：取得、快取、SSOT、錯誤轉譯 | 畫面狀態、文案、格式化 | Repository 介面上的 `suspend fun` / `Flow<DomainModel>` |

依賴方向只能是 **UI → Domain → Data**，反向與循環一律禁止（模組層級的強制規則見 `02-modularization`）。

Domain 層是**選用**的：沒有可重用商業邏輯時可以不存在，ViewModel 直接依賴 Repository 介面（判準見 `04-domain-layer`）。但 Data 與 UI 之間的邊界不可省略。

## 二、這段邏輯該放哪一層

| 這段邏輯 | 放哪 | 判準 |
|---|---|---|
| 格式化金額／日期、決定顯示哪個字串資源或顏色 | UI（ViewModel） | 只影響呈現，換 UI 不會改變資料 |
| 處理點擊、維護畫面暫時狀態（選了哪個 tab、展開了沒） | UI（ViewModel 或 state holder） | 畫面關掉就不需要保留 |
| 商業規則判斷（訂單能不能取消、折扣怎麼算），**且 ≥2 個 ViewModel 用到** | Domain（UseCase） | 重用性；細部判準見 `04-domain-layer` |
| 同樣的商業規則但只有一個畫面用得到 | UI（ViewModel） | 不為單一呼叫端多加一層；第二個呼叫端出現再下推 |
| 把多個來源組合成**一種業務資料** | Data（Repository） | 組合結果本身就是一種資料型別 |
| 把多個來源組合成**某個畫面要的東西** | Domain（UseCase）或 ViewModel | 組合結果只有那個畫面看得懂 |
| 決定走網路還是本地、要不要快取、何時刷新 | Data（Repository） | 呼叫端不該知道資料哪來 |
| 把 API 回應轉成 app 型別、把技術例外轉成語意化錯誤 | Data（Repository / DataSource 邊界） | 邊界的責任是不讓外部形狀外洩 |
| 直接跟一個具體來源溝通（一支 API、一個 DAO、一個 DataStore） | Data（DataSource） | 只認識一種技術 |
| 需要 `Context` / `Resources` / `Intent` 才能做的事 | UI 層；或在 DI 組裝點建立成品後注入 | data / domain 簽章不得出現這些型別 |

**不確定時**：往上留在 ViewModel 通常比往下推安全。往下推錯會把 UI 概念（loading、文案、格式）永久汙染資料層，清理要動全部呼叫端；往上留錯只是暫時重複，等第二個呼叫端出現再下推即可。

## 三、model 分幾層、在哪裡轉

| model | 住哪 | 帶什麼註解 | 誰看得到 |
|---|---|---|---|
| Network DTO `NetworkOrder` | `:core:network` | `@Serializable` / `@SerialName` | `internal`，止步於 Repository 實作 |
| Entity `OrderEntity` | `:core:database` | `@Entity` / `@PrimaryKey` / `@ColumnInfo` | `internal`，止步於 Repository 實作 |
| Domain model `Order` | `:core:model`（或 `:core:domain`） | 無 | 全 app |
| UI model `OrderUiModel` | `:feature:order` | 無 | 只有該 feature |

**要幾層**：有本地持久化 → DTO / Entity / Domain 三層；純網路讀取無快取 → DTO / Domain 兩層。UI model 只在需要預先算好顯示資料（已格式化字串、已排序、已選狀態）時才新增，否則 UiState 直接包 domain model。

**轉換鏈**（一律 extension function，可用 `::` 直接餵給 `map`）：

```
NetworkOrder --asEntity()--> OrderEntity --asExternalModel()--> Order --asUiModel()--> OrderUiModel
     └────────── 都寫在 :core:data ─────────┘                       └── 寫在 :feature:order ──┘
```

mapper 檔案該放哪個模組、命名怎麼統一，見 `05-data-layer`。

---

## 四、規則

### ui-accesses-datasource · MUST_NOT · new-only+on-touch · regex

ViewModel、Composable、Activity、Fragment 的建構子參數、屬性或函式內不得出現 DataSource 型別（`*ApiService`、`*Dao`、`DataStore`、`SharedPreferences`、Firebase client）。

✗ `class OrderViewModel @Inject constructor(private val api: OrderApiService)`
✓ `class OrderViewModel @Inject constructor(private val repository: OrderRepository)`

例外：無。即使某份資料只有單一來源，仍要建 Repository。
來源：https://developer.android.com/topic/architecture/recommendations

### composable-calls-data-layer · MUST_NOT · new-only+on-touch · regex

Composable、Activity、Fragment 不得注入或呼叫 Repository / UseCase，也不得直接寫入 ViewModel 的狀態欄位。資料存取與狀態變更一律經 ViewModel 的方法（單向資料流）。

✗ `@Composable fun OrderRoute(repository: OrderRepository) { ... }`
✓ `@Composable fun OrderRoute(viewModel: OrderViewModel = hiltViewModel())`，操作走 `viewModel.refresh()`

例外：無
來源：https://developer.android.com/topic/architecture/recommendations

### data-layer-imports-ui-type · MUST_NOT · new-only+on-touch · regex

data 層模組（`:core:data`、`:core:network`、`:core:database`）的檔案不得 import UI 型別：`androidx.compose.*`、`androidx.lifecycle.ViewModel`、`androidx.fragment.*`、`android.app.Activity`、`android.view.*`。（domain 層的對應規則見 `04-domain-layer`。）

✗ `// :core:data` 內 `import androidx.compose.runtime.mutableStateOf`
✓ 狀態留在 `:feature:order` 的 ViewModel，data 層只回 `Flow<Order>`

例外：無
來源：https://developer.android.com/topic/architecture/recommendations

### callback-type-across-layer · MUST_NOT · new-only · regex

跨層公開的簽章只能是 `suspend fun`（一次性操作）或 `Flow`（會變化、需被觀察的資料）。不得用 callback 介面、`LiveData`、RxJava（`Single` / `Observable` / `Completable`）或 Retrofit `Call<T>`。

✗ `fun getOrders(callback: (List<Order>) -> Unit)` ／ `fun getOrders(): Single<List<Order>>`
✓ `suspend fun getOrder(id: String): Order` ＋ `fun getOrdersStream(): Flow<List<Order>>`

例外：包裝無法修改的第三方 callback SDK 時，在 DataSource 內用 `callbackFlow` 收斂，該 callback 不得外流。
來源：https://developer.android.com/topic/architecture/recommendations

### concrete-impl-dependency · MUST_NOT · new-only+on-touch · regex

上層型別的建構子只能宣告介面，不得宣告下層的具體實作類別（`Default*Repository`、`*RepositoryImpl`、`Offline*Repository`）。實作由 DI 綁定（`@Binds`）。

✗ `class GetOrderUseCase @Inject constructor(private val repo: DefaultOrderRepository)`
✓ `class GetOrderUseCase @Inject constructor(private val repo: OrderRepository)`

例外：Repository 實作注入自己的 DataSource 是正確的，不受此限。
來源：官方 sample nowinandroid

### dto-entity-in-ui-layer · MUST_NOT · new-only+on-touch · manual

Network DTO 與 Room Entity 不得出現在 UiState 欄位、Composable 參數或 ViewModel 的公開簽章。它們應宣告為 `internal`，止步於 Repository 實作。

✗ `data class OrderUiState(val orders: List<NetworkOrder>)`
✓ `data class OrderUiState(val orders: List<Order>)`（`Order` 為 domain model）

例外：無
來源：https://developer.android.com/topic/architecture/data-layer

### dto-entity-same-class · MUST_NOT · new-only+on-touch · regex

同一個 `data class` 不得同時兼任 DTO 與 Entity：一個型別上不得同時出現序列化註解（`@Serializable` / `@SerialName` / `@SerializedName`）與持久化註解（`@Entity` / `@PrimaryKey` / `@ColumnInfo`）。合體後改一個 API 欄位名就會連動 DB migration。

✗ `@Entity @Serializable data class Order(@PrimaryKey @SerialName("order_id") val id: String)`
✓ `NetworkOrder`（`@Serializable`）與 `OrderEntity`（`@Entity`）兩個獨立型別 ＋ `asEntity()`

例外：無
來源：https://developer.android.com/topic/architecture/data-layer/offline-first

### business-logic-in-mapper · SHOULD_NOT · new-only · manual

mapper 只做欄位對應、型別轉換與缺值補預設。商業判斷（能不能取消、要不要顯示、折扣計算）不得藏在 mapper 裡，否則同一條規則會散落到每個轉換點且無法單獨測試。

✗ `fun OrderEntity.asExternalModel() = Order(..., canCancel = status == "PAID" && !isGift)`
✓ mapper 只搬 `status`；`canCancel` 由 UseCase 或 ViewModel 依 `Order` 計算

例外：單位換算（分→元）、缺漏欄位補預設值視為轉換而非商業邏輯。
來源：業界共識

### app-component-as-data-holder · MUST_NOT · new-only+on-touch · regex

不得用 Activity / Fragment / Service / Application 的 `companion object`、`static` 欄位或可變屬性在畫面之間傳遞或保存資料。行程被系統重建後這些欄位會是 null，造成難以重現的崩潰。

✗ `companion object { var currentOrder: Order? = null }`
✓ 導航只傳 id，目的地自行從 Repository 讀取（傳參規範見 `13-navigation`）

例外：真正的常數（`const val`）。
來源：https://developer.android.com/topic/architecture/recommendations

---

## 五、尚無定論（以下為建議，不是規則）

**Repository 介面放哪**：官方文件未定。`nowinandroid` 把介面與 `internal` 實作都放 `:core:data`；嚴格依賴反轉則把介面放 `:core:domain`。建議：只有當你要把 domain 做成純 `java-library`（用編譯期擋掉 Android 依賴）時才拆出去，否則同模組即可。**全專案擇一，不要兩種並存。**

**domain model 要不要獨立 `:core:model` 模組**：被 3 個以上模組共用時值得獨立；否則放 `:core:data` 或 `:core:domain` 即可，不必為了對稱先開模組。

**UI model 要不要一律開**：業界分歧。建議只在需要預先計算顯示資料時才開；一律開會產生大量只有改名的 mapper。硬底線不變——DTO / Entity 絕不可直接進 UiState。

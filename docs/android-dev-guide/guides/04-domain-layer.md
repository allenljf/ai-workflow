# 04 · Domain 層

**管**：domain 層要不要存在、UseCase 的形狀／命名／生命週期、domain model 的形狀、domain 對框架的隔離。
**不管**：Repository 實作、SSOT、錯誤模型、mapper（都在 `05-data-layer`）；DI 綁定寫法（`03-dependency-injection`）。
domain 層永遠是**選配**的，本檔一半篇幅在講「什麼時候不要開」。

| 相關主題 | 去哪 |
|---|---|
| Repository 實作、錯誤模型、mapper、DTO 邊界 | `05-data-layer` |
| 分層與依賴方向、model 分幾層 | `01-architecture` |
| domain 要不要獨立成模組、模組命名 | `02-modularization` |
| UseCase / Repository 的 DI 綁定寫法 | `03-dependency-injection` |
| dispatcher 注入、main-safe、`CancellationException` | `12-coroutines-flow` |
| UseCase 該用 fake 還是 mock 測 | `15-testing` |

---

## 一、要不要開 UseCase

官方明說 domain layer 是 optional。沒有 domain 層時，ViewModel 直接注入 Repository 介面是**正確**做法（官方 sample nowinandroid 全 app 只有兩個 UseCase）。

| 情況 | 開？ |
|---|---|
| 組合 ≥ 2 個 Repository／資料來源 | 開 |
| 含商業分支、驗證、計算，且與畫面無關 | 開 |
| 同一段邏輯被 ≥ 2 個 ViewModel 使用 | 開 |
| 需要跨資料來源的重試／節流／排序策略 | 開 |
| 只是把呼叫原封不動轉給單一 Repository | 不開，ViewModel 直接注入 Repository |
| 邏輯只服務一個畫面、無分支、只有幾行 | 不開，留在 ViewModel |
| 「Clean Architecture 規定要有」 | 不開 |

上表四個「開」的條件任一成立即可；一個都不成立卻建了 UseCase，就是 `passthrough-usecase` 違規。官方對「強制全部走 domain 層」的評語是：連簡單呼叫都得新增類別，複雜度提高而無收益。

---

## 二、規則

### usecase-wrong-suffix · MUST · new-only · regex

UseCase 類別名稱必須是 `<現在式動詞>[名詞]UseCase`，以 `UseCase` 結尾。禁止 `Interactor`、`XxxManager`、`XxxService`、`XxxHelper` 或無後綴。

✗ `class OrderInteractor`、`class OrderHelper`、`class GetOrder`
✓ `class GetOrderUseCase`、`class SubmitOrderUseCase`、`class FormatPriceUseCase`
例外：無
source: https://developer.android.com/topic/architecture/domain-layer

### usecase-multiple-public-entrypoints · MUST · new-only · manual

一個 UseCase 只能有一個 public 進入點，且必須是 `operator fun invoke`（需要時加 `suspend`）。不同行為拆成不同 UseCase，不要把 UseCase 當 Service 用。

✗ `class OrderUseCase { suspend fun execute(id: String): Order; fun cancel(); fun refresh() }`
✓ `class GetOrderUseCase { suspend operator fun invoke(id: String): Order = ... }`
例外：`private` / `internal` 輔助函式不算進入點。
source: https://developer.android.com/topic/architecture/domain-layer

### usecase-interface-impl-split · MUST_NOT · new-only · regex

UseCase 不得拆成 `interface XxxUseCase` + `class XxxUseCaseImpl`。UseCase 用 concrete class；它的依賴（Repository）已經是介面，測試時建真實 UseCase 搭 fake repository 即可。

✗ `interface GetOrderUseCase` + `class GetOrderUseCaseImpl : GetOrderUseCase`
✓ `class GetOrderUseCase @Inject constructor(private val orderRepository: OrderRepository)`
例外：需要跨模組依賴反轉（domain 定介面、外層模組實作）時可拆，但那已不是 UseCase，改用其他命名。
source: 官方 sample nowinandroid

### passthrough-usecase · MUST_NOT · new-only · manual

不得建立「只把呼叫轉給單一 Repository、無任何邏輯」的 UseCase。必須滿足第一節表格中至少一個「開」的條件。

✗ `class GetOrderUseCase(private val repo: OrderRepository) { suspend operator fun invoke(id: String) = repo.getOrder(id) }`
✓ ViewModel 直接 `@Inject constructor(private val orderRepository: OrderRepository)`
例外：專案已明確採「UI 一律不得碰 Repository」的全域約定時（需在專案準則寫明），但那必須全案一致，不能半套。
source: https://developer.android.com/topic/architecture/domain-layer

### stateful-usecase · MUST_NOT · new-only+on-touch · regex

UseCase 不得持有可變狀態：`var` 屬性、`MutableList` / `MutableMap` / `MutableStateFlow` 成員、自建快取。需要跨呼叫保存的狀態下推到 data 層，UI 狀態上推到 ViewModel。

✗ `class SearchOrderUseCase { private var lastKeyword: String? = null }`
✓ 關鍵字由 `invoke(keyword: String)` 傳入，快取放 Repository
例外：無
source: https://developer.android.com/topic/architecture/domain-layer

### singleton-scoped-usecase · MUST_NOT · new-only · regex

UseCase 不得綁成 singleton。UseCase 是無狀態、建立成本極低的物件，每次注入建立新實例即可。

✗ `@Singleton class GetOrderUseCase @Inject constructor(...)`
✓ `class GetOrderUseCase @Inject constructor(...)`（不加任何 scope 註解）
例外：無。若你覺得需要 singleton，通常代表它違反了 `stateful-usecase`。
source: https://developer.android.com/topic/architecture/domain-layer

### usecase-depends-on-datasource · MUST_NOT · new-only · regex

UseCase 建構子只能收介面／抽象型別（Repository 介面、其他 UseCase、純 Kotlin 型別）。禁止直接依賴具體實作或 DataSource：`DefaultXxxRepository`、`XxxApiService`、Retrofit service、`XxxDao`、`DataStore`、`SharedPreferences`。

✗ `class GetOrderUseCase @Inject constructor(private val api: OrderApiService)`
✓ `class GetOrderUseCase @Inject constructor(private val orderRepository: OrderRepository)`
例外：無
source: https://developer.android.com/topic/architecture/domain-layer

### android-import-in-domain · MUST_NOT · new-only+on-touch · regex

domain 層檔案不得 import `android.*`、`androidx.lifecycle.*`、`androidx.compose.*`、`Context`、`Resources`、`Intent`、`Bundle`、`Uri`。需要資源或導航能力時，在 domain 定義純 Kotlin 介面，由外層實作注入。（總則紅線 §三-2 的細則）

✗ `class FormatOrderDateUseCase @Inject constructor(private val context: Context)`
✓ `interface StringProvider { fun get(key: MessageKey, vararg args: Any): String }` 由 app 層實作
例外：`androidx.annotation`（`@StringRes` 等資源註解除外，見下條）、`androidx.paging`。
source: https://developer.android.com/topic/architecture/domain-layer

### framework-annotation-on-domain-model · MUST_NOT · new-only · regex

domain model 是純 Kotlin `data class`，檔案內不得出現序列化／持久化註解：`@Serializable`、`@SerialName`、`@SerializedName`、`@Json`、`@Entity`、`@PrimaryKey`、`@ColumnInfo`。出現代表 DTO 或 Entity 與 domain model 合體了。

✗ `@Entity data class Order(@PrimaryKey val id: String, @SerialName("total_amt") val total: Int)`
✓ `data class Order(val id: String, val total: Money)`，序列化欄位留在 `OrderNetworkModel` / `OrderEntity`
例外：無
source: https://developer.android.com/topic/architecture/data-layer

### presentation-type-in-domain · MUST_NOT · new-only · regex

domain model 與 UseCase 的簽章不得出現呈現層型別：`@StringRes Int`、`Color`、`Painter`、`Dp`、已格式化好的顯示字串、`XxxUiState` / `XxxUiModel`。呈現轉換發生在 ViewModel。

✗ `data class Order(@StringRes val statusLabel: Int, val displayPrice: String)`
✓ `data class Order(val status: OrderStatus, val total: Money)`，ViewModel 再轉字串資源
例外：`Money`、`OrderStatus` 這類**業務語意**的值型別不算呈現型別，鼓勵使用。
source: https://developer.android.com/topic/architecture/domain-layer

### mutable-domain-model · MUST · new-only · regex

domain model 必須不可變：所有欄位 `val`，集合用 `List` / `Set` / `Map`，不得用 `MutableList` / `MutableSet` / `MutableMap` / `Array`。修改一律走 `copy()`。

✗ `data class Order(var status: OrderStatus, val items: MutableList<OrderItem>)`
✓ `data class Order(val status: OrderStatus, val items: List<OrderItem>)`
例外：無
source: https://developer.android.com/topic/architecture/data-layer

### business-logic-in-static-util · SHOULD_NOT · new-only · manual

需要依賴（locale、幣別、時區、使用者偏好）或含商業分支的邏輯，不得放在 `object XxxUtils` 的 static 函式。抽成 UseCase，依賴用建構子注入。

✗ `object PriceUtils { fun format(amount: Int): String = ... }`（幣別只能從全域狀態拿）
✓ `class FormatPriceUseCase @Inject constructor(private val currencyRepository: CurrencyRepository)`
例外：無依賴的純函式工具（字串補零、數學運算）留在 top-level function 或 `object` 是合理的。
source: https://developer.android.com/topic/architecture/domain-layer

### circular-usecase-dependency · MUST_NOT · new-only · manual

UseCase 可以依賴其他 UseCase（MAY），但依賴圖必須是有向無環。禁止 A → B → A，也禁止 UseCase 依賴 ViewModel 或任何 UI 型別。

✗ `GetOrderUseCase(private val syncOrderUseCase: SyncOrderUseCase)` 而 `SyncOrderUseCase(private val getOrderUseCase: GetOrderUseCase)`
✓ 兩者共同依賴的邏輯下推到第三個 UseCase 或 Repository
例外：無
source: https://developer.android.com/topic/architecture/domain-layer

---

## 三、尚無定論

**Repository 介面該放 domain 模組還是 data 模組？** 官方文件沒有指定，兩種都能在官方素材裡找到依據。

| 做法 | 適用 |
|---|---|
| 介面與實作同放 `:core:data`，介面 public、實作 `internal` | 官方 sample nowinandroid 的做法。模組數少、耦合成本低的專案優先選這個 |
| 介面放 `:core:domain`（純 Kotlin JVM 模組），實作放 `:core:data` | 想用**編譯期**擋掉 domain 對 Android 的依賴時選這個——`android-import-in-domain` 會由編譯器代為執行 |

**建議（非規則）**：專案若已有獨立 domain 模組，一律用第二種並把該模組設為純 Kotlin library；否則跟隨 nowinandroid 用第一種。無論選哪一種，同一個專案不得兩種混用，且 `usecase-depends-on-datasource` 的底線不變。

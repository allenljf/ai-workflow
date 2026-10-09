# 05 · Data 層與錯誤模型

**管**：Repository 與 DataSource 的職責、命名、邊界；SSOT 與 offline-first 同步；model 邊界與 mapper；**錯誤模型（本檔是唯一 owner）**。
**不管**：Retrofit / OkHttp / JSON 設定（`06-network`）、Room / DataStore 用法（`07-persistence`）、UiState 形狀（`08-ui-state`）。

| 相關主題 | 去哪 |
|---|---|
| UseCase 要不要開、domain model 形狀 | `04-domain-layer` |
| Retrofit service、interceptor、序列化 | `06-network` |
| Room migration、DataStore、快取儲存選型 | `07-persistence` |
| Repository / DataSource 的 DI 綁定與 singleton | `03-dependency-injection` |
| dispatcher 注入、main-safe、`CancellationException`、Flow `catch` operator | `12-coroutines-flow` |
| 錯誤最終怎麼呈現成 UiState | `08-ui-state` |
| fake repository 怎麼寫 | `15-testing` |

---

## 一、錯誤模型（本檔是 owner）

官方立場：**Repository 拋語意化 exception，不在 data 層簽章塞三態包裝**；Loading 是 UI 概念。四道邊界：

| 邊界 | 型別 | 誰負責 |
|---|---|---|
| DataSource | 技術例外：`IOException` `HttpException` `SerializationException` `SQLiteException` | 框架丟出，原樣往上 |
| **Repository（轉換點）** | 語意化例外或 sealed 錯誤型別：`NoConnectivityException` `UnauthorizedException` `OrderNotFoundException` | Repository `catch` 後轉換，技術例外到此為止 |
| ViewModel | `Result.Loading / Success / Error` | 用共用的 `asResult()` 包裝 |
| UI | 字串資源 | 依 error 型別選 `stringResource`，訊息不從下層帶上來 |

```kotlin
// 放在共用模組，全 app 一份
sealed interface Result<out T> {
    data class Success<T>(val data: T) : Result<T>
    data class Error(val exception: Throwable) : Result<Nothing>
    data object Loading : Result<Nothing>
}

fun <T> Flow<T>.asResult(): Flow<Result<T>> = map<T, Result<T>> { Result.Success(it) }
    .onStart { emit(Result.Loading) }
    .catch { emit(Result.Error(it)) }
```

**何時 sealed class、何時 `kotlin.Result`**：跨層一律自訂 sealed interface（如上）。`kotlin.Result` 只能當單一檔案內的區域性回傳，不得進入跨層簽章——它沒有 Loading 態，且 `runCatching` 會吞掉 `CancellationException`（見 `12-coroutines-flow`）。

---

## 二、規則

### repository-named-after-screen · MUST_NOT · new-only · regex

Repository 依**資料型別**切分並命名為 `<DataType>Repository`，不得依畫面命名。畫面所需的多來源組合放 UseCase 或 ViewModel。

✗ `HomeRepository`、`OrderDetailScreenRepository`、`SettingsPageRepository`
✓ `OrderRepository`、`UserRepository`、`PaymentMethodRepository`
例外：依賴多個 Repository 的高階聚合類別可用 `<DataType>Manager` 後綴，但不得形成循環依賴。
source: https://developer.android.com/topic/architecture/data-layer

### repository-impl-wrong-name · MUST · new-only · regex

Repository 是「介面 + 實作」兩個型別。實作宣告為 `internal`，命名要描述策略：`Default<X>Repository`、`OfflineFirst<X>Repository`。禁止 `<X>RepositoryImpl`。測試替身命名 `Fake<X>Repository`。

✗ `class OrderRepositoryImpl : OrderRepository`
✓ `internal class DefaultOrderRepository @Inject constructor(...) : OrderRepository`
例外：無
source: 官方 sample nowinandroid

### datasource-outside-repository · MUST_NOT · new-only+on-touch · regex

`XxxApiService`、`XxxDao`、`RoomDatabase`、`DataStore`、`SharedPreferences`、`XxxRemoteDataSource` 只能被 Repository 注入。ViewModel、UseCase、Composable、Activity / Fragment 的建構子與函式簽章不得出現這些型別。（總則紅線 §三-3 的細則）

✗ `class OrderViewModel @Inject constructor(private val orderDao: OrderDao)`
✓ `class OrderViewModel @Inject constructor(private val orderRepository: OrderRepository)`
例外：無
source: https://developer.android.com/topic/architecture/data-layer

### datasource-name-leaks-technology · MUST · new-only · regex

DataSource 命名為 `<DataType><Remote|Local>DataSource`，不得把實作技術寫進名稱。換掉底層技術時不應該改名字。

✗ `OrderRetrofitDataSource`、`UserSharedPreferencesDataSource`、`OrderFirebaseSource`
✓ `OrderRemoteDataSource`、`UserLocalDataSource`
例外：無
source: https://developer.android.com/topic/architecture/data-layer

### datasource-mixes-sources · MUST_NOT · new-only · regex

一個 DataSource 只能操作一個資料來源。禁止同一個 DataSource 同時注入 network 與 database 依賴——接合兩者是 Repository 的職責。

✗ `class OrderDataSource @Inject constructor(private val api: OrderApiService, private val dao: OrderDao)`
✓ `OrderRemoteDataSource(api)` 與 `OrderLocalDataSource(dao)` 兩個類別，由 `DefaultOrderRepository` 接合
例外：DAO 本身已是介面且 main-safe，無額外邏輯時可直接注入 Repository，不必為它多包一層 LocalDataSource。
source: https://developer.android.com/topic/architecture/data-layer

### read-path-mixes-network-and-local · MUST · new-only · manual

每個 Repository 必須有明確的單一可信來源（SSOT）。**有本地儲存時，讀取路徑只查本地並回傳 `Flow`；網路只負責寫入本地。** 禁止同一個讀取函式依條件分別回傳網路資料或本地資料。

✗ `suspend fun getOrders() = if (isOnline) api.getOrders() else dao.getOrders()`
✓ `fun getOrdersStream(): Flow<List<Order>> = dao.getOrdersStream().map { it.map(OrderEntity::asExternalModel) }`，另有 `suspend fun sync()` 做 `upsert`
例外：無本地儲存的功能，SSOT 就是遠端，讀取直接 `suspend fun` 打 API。
source: https://developer.android.com/topic/architecture/data-layer/offline-first

### remote-first-write-for-user-content · MUST · new-only · manual

使用者產生的內容（收藏、備註、草稿、設定）採 lazy write：先寫本地 SSOT 讓 UI 立即反映，再排入同步佇列（WorkManager）。金流、下單、轉帳等交易相反，必須 online-only（遠端成功才寫本地），且離線時 UI 停用該操作。

✗ 收藏功能等 `api.addFavorite()` 回 200 才 `dao.upsert()`，離線就整個失效
✓ `dao.upsert(favorite)` → `syncManager.requestSync()`；下單則維持 online-only
例外：無
source: https://developer.android.com/topic/architecture/data-layer/offline-first

### full-overwrite-sync · SHOULD_NOT · new-only · manual

同步不得每次全量刪除重寫。用版本號 + change list 做增量同步；WorkManager 加 `NetworkType.CONNECTED` constraint；暫時性失敗回 `Result.retry()` 而非 `Result.failure()`。

✗ `dao.deleteAll(); dao.insertAll(api.getAll())`（會讓觀察中的 Flow 先發射空列表造成閃動，也抹掉未同步的本地變更）
✓ 讀上次版本 → 拉 change list → 分別套用刪除／`upsert` → 更新版本號
例外：資料量極小且無本地未同步變更（例如一份設定檔）時，全量覆寫可接受。
source: https://developer.android.com/topic/architecture/data-layer/offline-first

### technical-exception-crosses-repository · MUST · new-only+on-touch · manual

技術例外不得離開 Repository：`HttpException`、`IOException`、`SocketTimeoutException`、`SerializationException`、`SQLiteException` 必須在 Repository 邊界攔截，依語意轉成 data 層定義的例外或錯誤型別（HTTP status 也在此對應）。

✗ ViewModel 裡 `catch (e: HttpException) { if (e.code() == 401) ... }`
✓ Repository 內 `catch (e: HttpException) { throw if (e.code() == 401) UnauthorizedException() else ServerException(e.code()) }`
例外：無。`CancellationException` 必須先 rethrow，寫法見 `12-coroutines-flow`。
source: https://developer.android.com/topic/architecture/data-layer

### kotlin-result-in-cross-layer-signature · MUST_NOT · new-only · regex

Repository / DataSource / UseCase 的對外簽章不得使用 `kotlin.Result` 或 `runCatching` 的回傳值。跨層錯誤用自訂 sealed 型別或例外。

✗ `suspend fun getOrder(id: String): kotlin.Result<Order>`
✓ `suspend fun getOrder(id: String): Order`（失敗拋語意化例外），ViewModel 端用專案自訂的 `Result` 包
例外：同一檔案內的 `private` 輔助函式可用 `runCatching`，但必須先 rethrow `CancellationException`。
source: 業界共識

### ui-state-in-data-signature · MUST_NOT · new-only · regex

data 層簽章不得出現 UI 狀態或呈現型別：`XxxUiState`、`Loading` / `Loaded` 三態包裝、`@StringRes Int`、已格式化的顯示字串、`Color`、`Painter`。Loading 是「誰在等」的資訊，只有 UI 知道。

✗ `suspend fun loadOrderScreen(): OrderUiState`、`suspend fun getStatusLabel(id: String): Int`
✓ `fun getOrderStream(id: String): Flow<Order>`，三態由 ViewModel 的 `asResult()` 產生
例外：無
source: https://developer.android.com/topic/architecture/data-layer

### localized-message-in-domain-error · SHOULD_NOT · new-only · manual

data 層定義的錯誤型別不得攜帶已本地化、可直接顯示的訊息字串。錯誤只帶**型別與參數**，文案由 UI 層依型別挑字串資源。

✗ `class PaymentFailedException(val message: String = "付款失敗，請稍後再試")`
✓ `class PaymentFailedException(val reason: PaymentFailureReason) : Exception()`
例外：後端回傳、規格明訂要原樣顯示的訊息（例如風控原因），以獨立欄位攜帶並標註來源。
source: 業界共識

### dto-or-entity-outside-data · MUST_NOT · new-only+on-touch · regex

帶 `@Serializable` / `@SerializedName` 的網路 DTO 與帶 `@Entity` 的資料庫 Entity 不得出現在 domain 層或 UI 層的任何簽章。Repository 一律回傳 domain model。（總則紅線 §三-4 的細則）

✗ `fun getOrdersStream(): Flow<List<OrderEntity>>`、`OrderScreen(order: OrderNetworkModel)`
✓ `fun getOrdersStream(): Flow<List<Order>>`
例外：無
source: https://developer.android.com/topic/architecture/data-layer

### mapper-outside-data-layer · MUST · new-only · manual

跨層轉換寫成 extension function，放在**同時認識來源與目標型別**的 data 模組、與來源型別同 package。命名固定：`asEntity()`（→ Entity）、`asExternalModel()`（→ domain model）、`asNetworkModel()`（→ DTO）。domain model 所在檔案不得出現任何指向 DTO / Entity 的 mapper，ViewModel 與 Composable 不得做欄位搬移。

✗ ViewModel 內 `Order(id = dto.id, total = dto.total_amt)`
✓ `internal fun OrderEntity.asExternalModel() = Order(...)`，用法 `it.map(OrderEntity::asExternalModel)`
例外：轉換需要外部依賴（幣別、時區）或有需獨立測試的分支時，改用建構子注入的 mapper class；但不得用泛型 `Mapper<I, O>` 介面。
source: 官方 sample nowinandroid

### oneshot-wrapped-in-flow · MUST · new-only · regex

依語意選簽章：一次性操作（寫入、單次讀取、動作）用 `suspend fun`；會隨時間變化、需被觀察的資料用 `Flow<T>`，且該 Flow 必須來自真正會持續發射的來源（DAO、DataStore、`MutableStateFlow`）。回傳 Flow 的函式名稱以 `Stream` 結尾（SHOULD）。

✗ `fun getOrders(): Flow<List<Order>> = flow { emit(api.getOrders()) }`
✓ `suspend fun getOrders(): List<Order> = ...`；持續觀察則 `fun getOrdersStream(): Flow<List<Order>> = dao.getOrdersStream().map { ... }`
例外：無
source: https://developer.android.com/topic/architecture/data-layer

### unsafe-inmemory-cache · MUST · new-only+on-touch · manual

Repository 的記憶體快取必須執行緒安全：`Mutex.withLock`、`MutableStateFlow.update`，或 `ConcurrentHashMap`。禁止用裸 `var` + 直接讀寫當共享快取。

✗ `private var cachedOrders: List<Order> = emptyList()` 由多個 coroutine 讀寫
✓ `private val cachedOrders = MutableStateFlow<List<Order>>(emptyList())`，更新一律 `update { }`
例外：只在單一 coroutine 內存取、且不對外暴露的區域狀態。
source: https://developer.android.com/topic/architecture/data-layer

### context-in-repository-signature · MUST_NOT · new-only · regex

Repository 與 DataSource 的建構子和函式簽章不得出現 `Context`、`Activity`、`Fragment`、`View`、`Resources`、`Intent`、`Bundle`、`LifecycleOwner`。需要 application context 的元件在 DI module 內組好再注入成品。

✗ `class DefaultOrderRepository @Inject constructor(private val context: Context)`
✓ DI module 內 `Room.databaseBuilder(context, ...)` 建好 `OrderDao` 後注入 Repository
例外：無
source: https://developer.android.com/topic/architecture/data-layer

---

## 三、尚無定論

**Repository 拋 exception，還是回傳 sealed `Result<T>`？** 官方文件與 nowinandroid 都是「介面回裸型別／裸 `Flow`，錯誤用 exception，三態在 ViewModel 用 `asResult()` 產生」，本檔規則依此設計。回傳 sealed 錯誤型別（不含 Loading）也是可行的業界做法，優點是呼叫端無法忘記處理失敗，缺點是 `combine` 多個 Flow 前得先解包。

**建議（非規則）**：預設採官方做法；若團隊偏好顯式錯誤，改成 Repository 回傳自訂 `sealed interface OrderResult { Success / Failure }` 也可以，但必須全案一致，且 `technical-exception-crosses-repository`、`ui-state-in-data-signature`、`kotlin-result-in-cross-layer-signature` 三條底線不變。

**model 要幾層？** 有本地持久化 → 三層（DTO / Entity / domain model）；純網路無快取 → 兩層（DTO / domain model）。UiModel 只在需要預先算好顯示資料時才加，且放 UI 層。分層總則見 `01-architecture`。

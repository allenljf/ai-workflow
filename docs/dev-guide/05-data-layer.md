# 05 · 資料層（Repository 實作 / DataSource / model 分層 / 錯誤模型）

**這份管**：Repository 實作類、DataSource 邊界、DTO→Entity→Domain→UiModel 的分層與 mapper 位置，以及**本專案錯誤模型的唯一定案處**。
**這份不管**：Repository 介面與 UseCase 的設計（04）、Retrofit / JSON / OkHttp（06）、Room 與 DataStore（07）、dispatcher 與協程取消（11）、Koin 綁定（03）。

跨檔主題（不在這裡重述，直接看該檔）：

> dispatcher 注入見 [11-coroutines-flow.md#hardcoded-dispatcher](11-coroutines-flow.md)
> suspend main-safe 見 [11-coroutines-flow.md#suspend-not-main-safe](11-coroutines-flow.md)
> `catch (e: Exception)` 吞取消見 [11-coroutines-flow.md#swallow-cancellation](11-coroutines-flow.md)
> Repository 介面設計與 UseCase 職責見 [04-domain-layer.md](04-domain-layer.md)
> Retrofit endpoint、`B2CApiResponse` envelope、序列化見 [06-network.md](06-network.md)
> Room / DataStore / offline-first 見 [07-persistence.md](07-persistence.md)
> 手動 new 實作類別見 [03-di.md#manual-impl-instantiation](03-di.md)

---

## 錯誤模型定案（P-01）

本專案有 4 套並存機制，**新程式碼只用第 1、2 列**：

| 機制 | 辨識方式 | 新程式碼 |
|------|---------|---------|
| `kotlin.Result<T>` + data 層語意化例外 | `data/repository/.../otpauth/ApiException.kt` | ✅ 一次性操作 |
| `Flow<T>` + `.catch {}` | 串流資料 | ✅ 需觀察的資料 |
| `ApiResult`（`com.kkday.library.networking.core.api`，`:data:model`） | `Success.data` / `Error.apiError: ApiError`，另有 `Loading` / `Loaded` / `Upgrade` | ❌ 不得新增（185 檔） |
| `ApiResult`（`com.kkday.member.network.trans`，`:app`） | `Success.result` / `Error.throwable: Throwable`，只有 4 個 state | ❌ 不得新增（42 檔） |
| Rx `onErrorResumeNext` + 手刻 `JSONObject` | `KKdayService` 路徑 | ❌ 不得新增 |

**兩個 `ApiResult` 完全同名、欄位不同**：import 錯了會編譯通過但語意錯（`data` vs `result`、`ApiError` vs `Throwable`）。改到既有檔案時先確認 import 來源。

---

## 一、錯誤模型

### apiresult-new-code · MUST NOT · new-only · lint:apiresult-new-code

新增的 Repository 實作與其契約不得 import 任一個 `ApiResult`。一次性操作回傳 `Result<T>`，需觀察的資料回傳 `Flow<T>`。

✗ `import com.kkday.library.networking.core.api.ApiResult`
✓ `override suspend fun fetchOtherFaqs(): Result<List<PresaleFaqItem>>`

例外：修改既有使用 `ApiResult` 的 Repository 時維持原型別，不要在同一個類別內混兩套。
既有違規：227 檔 → [90-migration-ledger.md#m-19](90-migration-ledger.md)

### raw-run-catching · MUST NOT · new-only+on-touch · lint:raw-run-catching

不得用 `runCatching {}` 包住 suspend 呼叫 —— 它會把 `CancellationException` 收進 `Result.failure`，破壞協程取消。

✗ `runCatching { api.getOtherFaqs() }.map { it.data.orEmpty() }`
✓ `try { Result.success(...) } catch (e: HttpException) { Result.failure(ApiException.fromHttpException(e) ?: e) }`

例外：非 suspend 的純運算（JSON 解析、格式轉換）可用 `runCatching`。

### raw-exception-leak · MUST · new-only+on-touch · manual

Repository 邊界必須把 `HttpException` / `IOException` / `SerializationException` / `JsonSyntaxException` 轉成 data 層語意化例外，不得讓技術例外流到 UseCase 或 ViewModel。

✗ `override suspend fun fetchFaqs(): List<Faq> = api.getOtherFaqs().data!!.map { it.toDomain() }`
✓ `catch (e: HttpException) { Result.failure(ApiException.fromHttpException(e) ?: e) }`

例外：`ApiException` 目前只在 `:data:repository` 的 otpauth 套件，新功能可直接沿用或在同層新增語意化例外類別。

### loading-in-data-layer · MUST NOT · new-only · manual

Repository 回傳的 `Flow` 不得夾帶 UI 狀態（`Loading` / `Loaded` / `Idle`）。載入中是 UI 概念，由 ViewModel 的 UiState 產生。

✗ `flow { emit(fetch()) }.onStart { emit(ApiResult.loading()) }.onCompletion { emit(ApiResult.loaded()) }`
✓ Repository 只發資料或拋例外；ViewModel 在 `launch` 前後自行設 `isLoading`

例外：無。`BaseApiRepository.safeApiCall` 是既有反例（`first()` 只會拿到 `Loading`），不要照抄。
既有違規：244 處 `safeApiCall` / 38 檔 → [90-migration-ledger.md#m-19](90-migration-ledger.md)

### empty-catch · MUST NOT · new-only+on-touch · lint:empty-catch

`catch` 區塊不得為空。至少要記錄並轉成可判斷的結果。

✗ `catch (e: IOException) { }`
✓ `catch (e: IOException) { FirebaseCrashlytics.getInstance().recordException(e); Result.failure(e) }`

例外：無（紅線 F6）。

### print-stacktrace · MUST NOT · new-only+on-touch · lint:print-stacktrace

不得用 `printStackTrace()`。用 `FirebaseCrashlytics.recordException()` 記錄並轉成 domain error。

✗ `catch (e: Exception) { e.printStackTrace() }`
✓ `catch (e: HttpException) { FirebaseCrashlytics.getInstance().recordException(e); Result.failure(e) }`

例外：無（紅線 G3）。

---

## 二、model 分層與 mapper

### dto-in-ui · MUST NOT · new-only · lint:dto-in-ui

UI 層（Composable 參數、UiState 欄位、ViewModel 對外型別）不得出現網路 DTO 或 Room Entity。

✗ `fun WishCard(product: B2CProductCardData)` // `com.kkday.library.networking.resource.*`
✓ `fun WishCard(product: WishProductUiModel)`

例外：既有畫面**不要**為了合規改 269 檔的參數型別（會擴散到整條呼叫鏈），只約束新畫面。
既有違規：269 個 Composable 檔 → [90-migration-ledger.md#m-17](90-migration-ledger.md)

### dto-as-domain-model · MUST NOT · new-only · manual

同一個 data class 不得兼任 DTO 與 domain model。domain model 檔案內不得出現 `@SerializedName` / `@Serializable` / `@SerialName` / `@Entity` / `@PrimaryKey` / `@ColumnInfo`。

✗ `@Serializable data class PresaleFaqDto(...)` 被 UseCase 與 ViewModel 直接使用
✓ `PresaleFaqDto`（`:data:model`）→ `toDomain()` → `PresaleFaqItem`（純 Kotlin）

例外：層數依是否有本地持久化決定 —— 有 Room/DataStore 快取用三層（DTO / Entity / Domain）；純網路讀取用兩層（DTO / Domain）。UiModel 只在需要預先計算顯示資料時才加。

### manual-mapping-in-ui · MUST NOT · new-only · manual

DTO → domain / UiModel 的欄位搬移必須寫成 data 層的 extension function（本專案慣例 `toDomain()`），不得在 ViewModel 或 Composable 內逐欄位組。

✗ ViewModel 內 `PresaleFaqItem(id = dto.oid, title = dto.title.orEmpty())`
✓ `fun PresaleFaqDto.toDomain(): PresaleFaqItem` 放在 DTO 同檔／同 package（`:data:model`）

例外：轉換需要外部依賴（幣別、`StringProvider`）或有分支邏輯需獨立單測時，改成建構子注入的 mapper class；仍禁止泛型 `Mapper<I, O>` 介面。

### uimodel-in-repository · MUST NOT · new-only · manual

Repository 與其契約不得回傳 UI 專用型別：`XxxUiState` / `XxxUiModel` / `@StringRes Int` / 已格式化字串 / `Color` / `Painter`。

✗ `suspend fun fetchOtherFaqs(): Result<List<FaqUiState>>`
✓ `suspend fun fetchOtherFaqs(): Result<List<PresaleFaqItem>>`

例外：無。顯示用轉換一律在 ViewModel。

### mutable-model-field · MUST · new-only · manual

data 層對外暴露的 model 欄位一律 `val`，集合用 `List` / `Set` / `Map`，不得用 `var` 或可變集合、`Array`。

✗ `data class Faq(var title: String, val tags: MutableList<String>)`
✓ `data class Faq(val title: String, val tags: List<String> = emptyList())`

例外：Room `@Entity` 若因 library 限制需 `var`，僅限 Entity 本身，不得外流。

---

## 三、Repository 與 DataSource 邊界

> Repository 必須「介面 + 實作」、介面一律放 `:domain:contract`：
> 見 [04-domain-layer.md#repository-needs-interface](04-domain-layer.md)。
> 本檔只規範實作端（`XxxRepositoryImpl` 放 `:data:repository`、命名、DI 綁定）。

### datasource-above-repository · MUST NOT · new-only · manual

ViewModel、UseCase、Composable、Fragment / Activity 的建構子與參數不得出現 `*ApiService`、`*Dao`、`DataStore`、`SharedPreferences`、`PersistentManager`。這些只能被 Repository 注入。

✗ `class WishViewModel(private val api: HomeApiService)`
✓ `class WishViewModel(private val repository: IWishRepository)`

例外：Repository 直接注入 DAO / ApiService 是正確的，不需要多包一層 DataSource。

### repository-per-screen · MUST NOT · new-only · manual

Repository 依「資料型別」切分與命名（`<DataType>Repository`），不得依畫面命名。

✗ `class HomeRepository`、`class OrderDetailScreenRepository`
✓ `class ProductRepositoryImpl`、`class OrderRepositoryImpl`；跨型別聚合用 `XxxManager`

例外：畫面需要多來源組合時，組合發生在 UseCase 或 ViewModel，不是新開一個畫面 Repository。

### datasource-tech-name · MUST NOT · new-only · manual

DataSource 命名不得帶實作技術，只能用 `Remote` / `Local` 角色。一個 DataSource 只操作一個來源。

✗ `class RetrofitOrderDataSource`、`class SharedPreferencesUserDataSource`
✓ `class OrderRemoteDataSource`、`class UserLocalDataSource`

例外：只有三種情況才需要建 DataSource —— 同一功能橫跨 Room + DataStore + 檔案、需要跨 DAO 的 `@Transaction`、或要包裝阻塞式舊 SDK。其餘直接注入 DAO / ApiService。

### mutable-cache-in-repository · MUST NOT · new-only+on-touch · manual

Repository 的 in-memory 快取不得用裸 `var` 讀寫，必須用執行緒安全機制。

✗ `private var cachedFaqs: List<PresaleFaqItem> = emptyList()`
✓ `private val cachedFaqs = MutableStateFlow<List<PresaleFaqItem>>(emptyList())` 搭配 `.update { }`；複合更新用 `Mutex.withLock`

例外：只在單一 coroutine 內讀寫且不對外暴露的區域變數。

> 新程式碼不得引入 RxJava、既有 Rx 鏈的收斂邊界：
> 見 [17-interop-views-compose.md#no-new-rxjava](17-interop-views-compose.md)。


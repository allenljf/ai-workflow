# 04 · Domain 層（UseCase / Repository 介面 / domain model）

這份管：UseCase 的命名、形狀與存在條件、domain 層的依賴邊界（不得碰 Android、不得碰 data 實作）、Repository **介面**的歸屬與命名、domain model 的純度。

這份不管，請看對應 owner：

> Repository 實作、DataSource、錯誤轉換見 [05-data-layer.md](05-data-layer.md)
> UI 層不得使用 DTO 見 [05-data-layer.md#dto-in-ui](05-data-layer.md)
> `suspend` 必須 main-safe、dispatcher 注入見 [11-coroutines-flow.md#suspend-not-main-safe](11-coroutines-flow.md)、[11-coroutines-flow.md#hardcoded-dispatcher](11-coroutines-flow.md)
> Rx 型別不得穿透 domain 簽章見 [17-interop-views-compose.md#no-new-rxjava](17-interop-views-compose.md)
> UseCase 一律綁 `@Factory` 見 [03-di.md#usecase-as-single](03-di.md)
> UseCase / Repository 的單元測試與 fake 見 [14-testing.md#prefer-fakes-over-mocks](14-testing.md)

**現況一句話**：`:domain:usecase` 目前直接依賴 `:data:repository` / `:data:model` / `:data:networking:api`，且**沒有宣告** `:domain:contract` 依賴（靠 networking 模組傳遞取得）。這是已登記的技術債，新程式碼不得擴大（[D-12](91-decisions.md)、[M-24](90-migration-ledger.md)）。

---

## 一、依賴邊界

### android-in-domain · MUST_NOT · new-only+on-touch · lint:android-in-domain

`:domain:contract` 與 `:domain:usecase` 不得 `import android.*` / `androidx.*`。白名單只有 `androidx.annotation` 與 `androidx.paging`（紅線 C1），**不得自訂其他白名單**。需要字串、資源、導航能力時，以純 Kotlin 介面抽象，實作放 `:app` 或 `:shared:*`。

✗ `import android.content.Context` / `import androidx.lifecycle.LiveData`
✓ `class GetOrderTitleUseCase(private val strings: StringProvider)`  // StringProvider 是純 Kotlin 介面

例外：`androidx.annotation`、`androidx.paging`（`PagingData` 需由下層穿到 UI）、測試碼。

### domain-imports-impl · MUST_NOT · new-only+on-touch · lint:domain-imports-impl

domain 層不得 import data 層實作型別（`*RepositoryImpl`、`*ApiService`、`*Dao`、`SharedPreferences`）。UseCase 的建構子參數只能是介面／抽象型別與純 Kotlin 型別。

✗ `class GetCreditCardListUseCase(private val repo: CreditCardRepositoryImpl)`
✓ `class GetCreditCardListUseCase(private val repo: CreditCardRepository)`  // 介面在 :domain:contract

例外：測試碼。
既有違規：7 個 main 檔直接 import `com.kkday.data.repository.*` → [90-migration-ledger.md#m-24](90-migration-ledger.md)

### domain-gradle-data-dep · MUST_NOT · new-only+on-touch · deps-graph

`domain/*/build.gradle.kts` 不得**新增**對 `:data:*` 的依賴；改到 domain 模組的 build 檔時，既有的 `:data:*` 依賴只能減少不能增加。新 UseCase 需要的型別若只在 `:data:*`，把契約補進 `:domain:contract`，不要加依賴。

✗ 在 `domain/usecase/build.gradle.kts` 新增 `implementation(project(":data:roomDb"))`
✓ 在 `domain/usecase/build.gradle.kts` 補上 `implementation(project(":domain:contract"))`

例外：無。
既有違規：`:domain:usecase` → `:data:model` / `:data:repository` / `:data:networking:api`；`:domain:contract` → `:data:model` → [90-migration-ledger.md#m-24](90-migration-ledger.md)

---

## 二、UseCase

### usecase-naming · MUST · new-only · manual

UseCase 類別名稱必須是 `<現在式動詞><名詞>UseCase`，以 `UseCase` 結尾。禁止 `Interactor`、`XxxManager`、`XxxService` 或無後綴命名。

✗ `class CreditCardListInteractor` / `class PasswordManager`
✓ `class GetCreditCardListUseCase` / `class ChangePasswordUseCase`

例外：依賴多個 Repository 的高階聚合類別可用 `<資料型別>Manager`，但它不是 UseCase，不放 `:domain:usecase`。

### usecase-single-invoke · SHOULD · new-only · manual

每個 UseCase 只暴露一個 public 進入點，宣告為 `operator fun invoke`（需要時 `suspend operator fun invoke`）。不得在同一個 UseCase 暴露多個不相關的 public 方法。

✗ `class OrderUseCase { suspend fun getOrder(...) ; suspend fun cancelOrder(...) }`
✓ `class ChangePasswordUseCase(private val repository: PasswordRepository) { suspend operator fun invoke(oldPassword: String, newPassword: String): Result<Unit> = repository.changePassword(oldPassword, newPassword) }`

例外：無。多個動作就拆多個 UseCase。

### usecase-passthrough · MAY · new-only · manual

純轉發單一 Repository 方法、且只有一個 ViewModel 使用的 UseCase **可以開也可以不開**，兩種都過 review。但下列情況**必須**開 UseCase：組合 ≥2 個資料來源、含分支／驗證／計算／快取策略、或 ≥2 個 ViewModel 重用同一段取資料邏輯。

✓ `class GetOrderUseCase(private val repo: OrderRepository)`  // pass-through，維持專案一致性
✓ `class OrderViewModel(private val repo: OrderRepository)`  // 不開 UseCase 也可以

例外：不要為了這條規則在 review 爭論；符合「必須開」三條件之一卻沒開才是違規。

### usecase-mutable-state · MUST_NOT · new-only · manual

UseCase 不得持有可變狀態：`var` 屬性、`MutableList` / `MutableMap` / `MutableStateFlow` 成員、可變快取。需要跨呼叫保存的狀態下推到 data 層（Repository 的 SSOT）或上推到 ViewModel。

✗ `class SearchProductUseCase { private var lastKeyword: String? = null }`
✓ `class SearchProductUseCase(private val repo: SearchRepository)`  // 無狀態，@Factory 綁定

例外：無。

---

## 三、Repository 介面

### repository-needs-interface · MUST · new-only · manual

新增的 Repository 必須是「介面 + 實作」兩個型別，且**介面一律放 `:domain:contract`**、實作 `Default<X>Repository` / `<X>RepositoryImpl` 放 `:data:repository`。禁止讓 UseCase 注入沒有介面的具體 Repository 類別，禁止把新介面放在 feature 模組自己的 `domain/repository` 套件。

✗ `domain/usecase/.../GetBundleDetailUseCase(private val repo: BundleRepository)`  // BundleRepository 是 :data 的 concrete class
✓ 介面 `domain/contract/.../repository/BundleRepository.kt` + 實作 `data/repository/.../DefaultBundleRepository.kt`

例外：既有 46 個無介面的 concrete Repository 不主動抽介面。
既有違規：67 個 Repository 只有 21 個有介面；契約散落 `:domain:contract` 8 個、feature 模組 13 個 → [90-migration-ledger.md#m-18](90-migration-ledger.md)

### repository-named-by-screen · MUST_NOT · new-only · manual

Repository 依「業務資料型別」命名與切分，不得依畫面命名。畫面所需的多來源組合在 UseCase 或 ViewModel 完成。

✗ `interface HomeRepository` / `interface OrderDetailScreenRepository`
✓ `interface OrderRepository` / `interface CreditCardRepository`

例外：無。新增前先確認 `:domain:contract` 沒有同名介面（已有 `ProductRepository` 一 class 一 interface 的同名衝突）。

---

## 四、Domain model

### serialization-in-domain-model · MUST_NOT · new-only · manual

domain model 檔案不得出現序列化／持久化註解：`@SerializedName`、`@Serializable`、`@SerialName`、`@Entity`、`@PrimaryKey`、`@ColumnInfo`。出現這些代表 DTO 與 domain model 已合體，API 改欄位會打穿全 app。

✗ `data class Order(@SerializedName("order_no") val orderNo: String)`  // 放在 domain
✓ `data class Order(val orderNo: String)` + data 層 `OrderResponse.asExternalModel()` 轉換

例外：無。DTO ↔ domain 的 mapper 用 extension function（`asExternalModel()`），放在 data 層。

### dto-in-domain-contract · MUST_NOT · new-only · manual

`:domain:contract` 的介面簽章與 `:domain:usecase` 的回傳型別不得使用 `:data:model` 的網路 DTO / DB Entity。新增契約時，需要的模型一併定義在 domain 端。

✗ `interface OrderRepository { suspend fun getOrder(id: String): Result<OrderResponse> }`
✓ `interface OrderRepository { suspend fun getOrder(id: String): Result<Order> }`  // Order 是 domain model

例外：既有介面（如 `PasswordRepository` 回傳 `com.kkday.model.otpauth.*`）不主動改；同一介面新增方法時沿用該檔既有型別以免半套。
既有違規：`:domain:contract` 依賴 `:data:model`；`:domain:usecase` 17/33 檔 import `com.kkday.model.*` → [90-migration-ledger.md#m-24](90-migration-ledger.md)

### ui-model-in-domain · MUST_NOT · new-only · manual

UseCase 與 Repository 介面不得回傳 UI 專用型別：`XxxUiState`、`XxxUiModel`、`@StringRes Int`、已格式化的顯示字串、`Color`、`Painter`。呈現用的轉換一律發生在 ViewModel。

✗ `suspend operator fun invoke(): OrderUiState`
✗ `suspend operator fun invoke(): String`  // 回傳 "NT$ 1,200" 這種已格式化字串
✓ `suspend operator fun invoke(): Result<Order>`  // 金額格式化留給 ViewModel

例外：`PriceFormatStringUseCase` 這類「純格式化」既有 UseCase 不主動改；新增格式化邏輯放 ViewModel。

# 典型功能完整路徑範例

> **AI 使用說明**：新增功能或排查問題時，以本文件的範例作為模板，對照同類型功能的完整檔案路徑串接。

---

## 如何使用本文件

1. 找出問題屬於哪種功能類型（列表查詢、詳情頁、CRUD）
2. 對照最接近的範例，找出對應的檔案路徑
3. 新增功能時，比照同類型範例的每一層結構

---

## 範例一：信用卡管理（CRUD 型功能）

完整的建立 → 查詢 → 刪除流程，含 Compose UI。

### 資料流向

```
CreditCardListActivity（Compose）
  └── CreditCardViewModel
        ├── GetCreditCardListUseCase
        ├── SaveCreditCardUseCase
        └── DeleteCreditCardUseCase
              └── CreditCardRepository（interface）
                    └── CreditCardRepositoryImpl（@Single binds）
                          └── CreditCardApiService（Retrofit）
```

### Layer 1：API Service

**位置**：`libs/networking/api/src/main/java/com/kkday/library/networking/service/creditcard/CreditCardApiService.kt`

```kotlin
interface CreditCardApiService {
    @POST("v2/payment-token/list")
    suspend fun getCreditCardList(@Body body: CreditCardListRequest): B2CApiResponse<CreditCardListResponse?>

    @POST("v2/payment-token/save")
    suspend fun saveCreditCard(@Body body: CreditCardSaveRequest): B2CApiResponse<CreditCardSaveResponse>

    @POST("v2/payment-token/delete")
    suspend fun deleteCreditCard(@Body body: CreditCardDeleteRequest): B2CApiResponse<Any?>
}
```

### Layer 2：Repository 介面 + 實作

**介面**：`data/repository/src/main/java/com/kkday/data/repository/creditcardlist/CreditCardRepository.kt`

```kotlin
interface CreditCardRepository {
    suspend fun fetchCreditCardList(currency: String, loginChannel: String): Result<List<PaymentChannel>>
    suspend fun saveCreditCard(pmchOid: Int, transPmch: String, prime: String, phoneNumber: String): CreditCardSaveResponse?
    suspend fun deleteCreditCard(fingerprint: String): Boolean
}
```

**實作**：同目錄 `CreditCardRepositoryImpl.kt`

```kotlin
@Single(binds = [CreditCardRepository::class])
internal class CreditCardRepositoryImpl(
    private val creditCardApiService: CreditCardApiService
) : BaseApiRepository(), CreditCardRepository
```

### Layer 3：UseCase

**位置**：`domain/usecase/src/main/java/com/kkday/domain/creditcard/`

```kotlin
@Factory
class GetCreditCardListUseCase(private val creditCardRepository: CreditCardRepository) {
    suspend operator fun invoke(currency: String, loginChannel: String): Result<List<PaymentChannel>>
}

@Factory
class DeleteCreditCardUseCase(private val creditCardRepository: CreditCardRepository) {
    suspend operator fun invoke(fingerprint: String): Boolean
}

@Factory
class SaveCreditCardUseCase(private val creditCardRepository: CreditCardRepository) {
    suspend operator fun invoke(pmchOid: Int, transPmch: String, prime: String, phoneNumber: String?): CreditCardSaveResponse?
}
```

### Layer 4：ViewModel

**位置**：`libs/feature/creditcard_list/src/main/java/com/kkday/feature/creditcardlist/CreditCardViewModel.kt`

```kotlin
@KoinViewModel
internal class CreditCardViewModel(
    application: Application,
    private val getCreditCardListUseCase: GetCreditCardListUseCase,
    private val deleteCreditCardUseCase: DeleteCreditCardUseCase,
    private val saveCreditCardUseCase: SaveCreditCardUseCase
) : AndroidViewModel(application) {

    sealed class ViewState {
        data object Loading : ViewState()
        data class Success(val data: PaymentChannel) : ViewState()
        data class Empty(val data: PaymentChannel?) : ViewState()
        data object Unavailable : ViewState()
    }

    val creditCardViewState: StateFlow<ViewState>
    val creditCardEventState: SharedFlow<EventState>

    suspend fun fetchCreditCards()
    fun deleteCreditCard(cardInfo: CardInfo)
    fun saveCreditCard(tapPayCardData: TapPayCardData, paymentChannel: PaymentChannel)
}
```

### Layer 5：UI（Compose Activity）

**位置**：`libs/feature/creditcard_list/src/main/java/com/kkday/feature/creditcardlist/CreditCardListActivity.kt`

```kotlin
class CreditCardListActivity : BaseComposeActivity() {
    private val viewModel: CreditCardViewModel by viewModel()
    private val formContract: CreditCardFormContract by inject()
    override fun onCreate(savedInstanceState: Bundle?) { /* setContent { CreditCardScreen(...) } */ }
}

@Composable
internal fun CreditCardScreen(viewModel: CreditCardViewModel, formContract: CreditCardFormContract)
```

### DI 注冊

```kotlin
// libs/feature/creditcard_list/.../di/CreditCardListAnnotationModule.kt
@Module
@ComponentScan("com.kkday.feature.creditcardlist")
class CreditCardListAnnotationModule

// libs/networking/api/.../creditcardApiServiceModule.kt
val creditCardApiServiceModule = module {
    single { retrofit.create(CreditCardApiService::class.java) }
}
```

---

## 範例二：商品詳情頁（複雜詳情型功能）

多個 UseCase 組合、大型 ViewModel、Fragment 繼承體系。

### 資料流向

```
CommonProductDetailFragment
  └── ProductDetailViewModel
        └── GetProductUseCase（聚合 UseCase）
              ├── GetProductDetailUseCase
              ├── GetProductPackagesUseCase
              ├── GetProductPackageCalendarUseCase
              └── GetProductAnnouncementUseCase
                    └── ProductRepository（@Single）
                          └── IProductApiService（Retrofit）
```

### Layer 1：API Service

**位置**：`libs/networking/api/src/main/java/com/kkday/library/networking/service/product/IProductApiService.kt`

```kotlin
interface IProductApiService {
    @GET("v2/cdn/product/{product_mid}")
    suspend fun getProductDetail(
        @Path("product_mid") productId: String?,
        @Header("currency") currency: String?,
        @Header("lang") lang: String?,
        @Header("locale") countryCode: String?
    ): B2CApiResponse<ProductDetailData>

    @GET("v2/product/{product_mid}/pkg")
    suspend fun getProductPackages(@Path("product_mid") productId: String?, ...): B2CApiResponse<ProductPackagesData>

    @GET("v2/product/{product_mid}/calendar")
    suspend fun <T> getProductPackageCalendar(...): B2CApiResponse<T>
}
```

### Layer 2：Repository

**位置**：`data/repository/src/main/java/com/kkday/data/repository/ProductRepository.kt`

```kotlin
@Single
class ProductRepository(
    private val kkApi: KKApi,
    private val dataStoreHelper: DataStoreHelper
) : BaseApiRepository() {
    suspend fun getProductDetail(productId: String, currency: String, lang: String, countryCode: String): B2CApiResponse<ProductDetailData>
    suspend fun getProductPackages(productId: String, ...): B2CApiResponse<ProductPackagesData>
    suspend fun getProductPackageCalendar(productId: String, beginDate: String, endDate: String, ...): B2CApiResponse<ProductPackageCalendarData>
}
```

### Layer 3：UseCase（聚合模式）

**位置**：`libs/feature/product_page/src/main/java/com/kkday/product_page/domain/useCase/`

```kotlin
// 各自獨立 UseCase
class GetProductDetailUseCase(...)  { operator fun invoke(productId: String, ...): Flow<ApiResult<ProductDetailData>> }
class GetProductPackagesUseCase(...)  { operator fun invoke(...): Flow<ApiResult<ProductPackagesData>> }
class GetProductPackageCalendarUseCase(...) { operator fun invoke(...): Flow<ApiResult<ProductPackageCalendarData>> }

// 聚合 UseCase（組合多個 UseCase，注入至 ViewModel）
class GetProductUseCase(
    val getProductDetailUseCase: GetProductDetailUseCase,
    val getProductPackageCalendarUseCase: GetProductPackageCalendarUseCase,
    val getProductPackagesUseCase: GetProductPackagesUseCase,
    val getProductAnnouncementUseCase: GetProductAnnouncementUseCase,
    // ... 更多
)
```

### Layer 4：ViewModel

**位置**：`libs/feature/product_page/src/main/java/com/kkday/product_page/presentation/detail/viewModel/ProductDetailViewModel.kt`

```kotlin
class ProductDetailViewModel(
    savedStateHandle: SavedStateHandle,
    private val getProductUseCase: GetProductUseCase,
    private val appSharedData: AppSharedData,
    private val persistentManager: PersistentManager,
) : ViewModel() {
    suspend fun loadProductDetail(productId: String, isNeedGetProductDetail: Boolean)
    suspend fun loadProductPackages(productId: String)
    suspend fun loadProductPackageCalendar(productId: String, beginDate: String, endDate: String)
}
```

### Layer 5：Fragment（繼承體系）

```
SharedProductDetailFragment（抽象基礎）
  └── CommonProductDetailFragment（一般商品）
  └── TransProductDetailFragment（交通商品）
  └── BlankProductDetailFragment（空白佔位）
```

**位置**：`libs/feature/product_page/src/main/java/com/kkday/product_page/presentation/detail/view/CommonProductDetailFragment.kt`

### DI 注冊（Module DSL 模式）

**位置**：`libs/feature/product_page/src/main/java/com/kkday/product_page/di/productPageModule.kt`

```kotlin
val productPageModule = module {
    single { provideApiService(get(named(KKNetworking.RETROFIT_NAME_DEFAULT))) }
    factory { GetProductDetailUseCase(get(), get(), get(), get()) }
    factory { GetProductPackagesUseCase(get(), get()) }
    factory { GetProductUseCase(get(), get(), get(), get(), get(), get(), get(), get()) }
    viewModel { params -> UserCommentViewModel(get(), get(), get(), get(), params[0], params[1]) }
}
```

---

## 範例三：訂單憑證（Flow 型資料查詢）

UseCase 回傳 `Flow<ApiResult<T>>`，ViewModel 用 StateFlow 管理狀態。

### 資料流向

```
OrderDetailFragment
  └── NewOrderDetailViewModel（StateFlow<OrderDetailState>）
        ├── GetVoucherByOrderUseCase → Flow<ApiResult<VoucherListInfo>>
        └── GetBarcodesResultUseCase → Flow<ApiResult<BarcodesResult>>
              └── OrderVoucherRepository（interface）
                    └── OrderVoucherRepositoryImpl（@Single）
                          └── OrderVoucherApiService（Retrofit）
```

### Layer 1：API Service

**位置**：`libs/feature/order_page/src/main/java/com/kkday/order_page/network/OrderVoucherApiService.kt`

```kotlin
interface OrderVoucherApiService {
    @GET("v2/order/{order_mid}/vouchers")
    suspend fun getVouchersByOrder(@Path("order_mid") orderMid: String, @Query("lang") lang: String): B2CApiResponse<VoucherListInfo>

    @GET("v2/order/{order_id}/barcodes")
    suspend fun getBarcodesResult(@Path("order_id") orderId: String, @Query("lang") lang: String): B2CApiResponse<BarcodesResult>
}
```

### Layer 2：Repository

**介面**：`libs/feature/order_page/src/main/java/com/kkday/order_page/domain/repository/OrderVoucherRepository.kt`

**實作**：`libs/feature/order_page/src/main/java/com/kkday/order_page/data/OrderVoucherRepositoryImpl.kt`

```kotlin
@Single
class OrderVoucherRepositoryImpl(
    private val apiService: OrderVoucherApiService
) : OrderVoucherRepository {
    override suspend fun getVouchersByOrder(orderMid: String, lang: String): B2CApiResponse<VoucherListInfo>
    override suspend fun getBarcodesResult(orderId: String, lang: String): B2CApiResponse<BarcodesResult>
}
```

### Layer 3：UseCase

**位置**：`libs/feature/order_page/src/main/java/com/kkday/order_page/domain/useCase/GetVoucherUseCase.kt`

```kotlin
@Factory
class GetVoucherByOrderUseCase(
    private val orderVoucherRepository: OrderVoucherRepository,
    private val persistentManager: PersistentManager
) {
    operator fun invoke(orderMid: String): Flow<ApiResult<B2CApiResponse<VoucherListInfo>?>>
}
```

### Layer 4：ViewModel（State + Event 模式）

**位置**：`libs/feature/order_page/src/main/java/com/kkday/order_page/new_detail/NewOrderDetailViewModel.kt`

```kotlin
data class OrderDetailState(
    val isLoading: Boolean = false,
    val voucherListInfo: VoucherListInfo? = null,
    val barcodesResult: BarcodesResult? = null,
)

sealed class OrderDetailEvent {
    data class LoadOrderDetail(val orderId: String) : OrderDetailEvent()
    data class NavigateToVoucher(val orderId: String, val placement: String) : OrderDetailEvent()
}

@KoinViewModel
class NewOrderDetailViewModel(
    private val getVoucherByOrderUseCase: GetVoucherByOrderUseCase,
    private val getBarcodesResultUseCase: GetBarcodesResultUseCase,
) : ViewModel() {
    val orderDetailState: StateFlow<OrderDetailState>
    fun onEventReceived(event: OrderDetailEvent)
}
```

### Layer 5：Fragment

**位置**：`app/src/main/java/com/kkday/member/view/order/detail/order/OrderDetailFragment.kt`

### DI 注冊

```kotlin
// libs/feature/order_page/.../di/orderVoucherModule.kt
val orderVoucherModule = module {
    single { retrofit.create(OrderVoucherApiService::class.java) }
}

// libs/feature/order_page/.../di/orderModule.kt（Repository annotation scan）
@Module @ComponentScan("com.kkday.order_page")
class OrderAnnotationModule
```

---

## 三種功能類型對照

| 類型 | 代表範例 | ViewModel State | UseCase 回傳型別 | UI 技術 |
|------|---------|----------------|----------------|---------|
| CRUD（操作型） | 信用卡管理 | `sealed class ViewState` | `suspend` 直接回傳 | Compose Activity |
| 複雜詳情頁 | 商品詳情 | ViewModel 直接持有欄位 | 聚合 UseCase + `Flow` | Fragment（繼承體系） |
| 資料查詢 | 訂單憑證 | `data class XxxState` | `Flow<ApiResult<T>>` | Fragment + ViewBinding |

---

## 新增功能 Checklist

```
1. libs/networking/api/.../service/[feature]/I[Feature]ApiService.kt    ← API 介面
2. data/model/src/.../[Feature]Request.kt / [Feature]Response.kt         ← 資料模型
3. data/repository/src/.../[Feature]Repository.kt                        ← Repository 介面
4. data/repository/src/.../[Feature]RepositoryImpl.kt（@Single binds）   ← Repository 實作
5. domain/usecase/src/.../[Verb][Feature]UseCase.kt（@Factory）           ← UseCase
6. [feature]/presentation/viewModel/[Feature]ViewModel.kt（@KoinViewModel）← ViewModel
7. [feature]/presentation/view/[Feature]Fragment.kt                       ← UI
8. app/src/.../di/ 或 @Module @ComponentScan 確認 DI 已涵蓋               ← DI 注冊
9. KKdayApp.kt：確認新 Module 已加入 startKoin modules 清單               ← 初始化
```

---

*文件版本：Step 8 of AI Guide（最終步驟）| 最後分析日期：2026-03-17*

## 相關筆記
- [02-modules](02-modules.md)
- [03-ui-patterns](03-ui-patterns.md)
- [05-networking](05-networking.md)
- [06-data-layer](06-data-layer.md)
- [order-detail-compose](features/order-detail-compose.md)
- [sku-activity-shell](features/sku-activity-shell.md)

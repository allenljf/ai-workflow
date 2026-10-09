# Koin 依賴注入指南

> **AI 使用說明**：新增類別或排查注入錯誤時，對照本文件確認應使用哪種 annotation、Named qualifier 如何取得、以及介面綁定方式。

---

## 快速參考

| 類別類型 | 使用 annotation | 範例 |
|---------|----------------|------|
| UseCase | `@Factory` | `GetVoucherByOrderUseCase` |
| Repository 實作 | `@Single(binds = [Interface::class])` | `CreditCardRepositoryImpl` |
| ViewModel | `@KoinViewModel` | `CartViewModel` |
| 全域 Service/Helper | `@Single` | `AppConfigManagerImpl` |
| ChatRepository（特例） | `@Factory(binds = [...])` | `ChatRepositoryImpl` |

---

## Annotation 說明

### @Factory（UseCase、短生命週期元件）

每次注入建立新實例，確保無狀態、可測試。

```kotlin
@Factory
class DeleteCreditCardUseCase(
    private val creditCardRepository: CreditCardRepository  // 注入介面，非實作
) {
    suspend operator fun invoke(fingerprint: String): Boolean {
        return creditCardRepository.deleteCreditCard(fingerprint)
    }
}
```

- 檔案：`domain/usecase/src/main/java/com/kkday/domain/creditcard/DeleteCreditCardUseCase.kt`
- 慣例：UseCase 只注入介面（Contract），不直接注入實作類別

### @Single（Repository、Service、全域狀態）

應用程式生命週期內只有一個實例。

```kotlin
@Single(binds = [CreditCardRepository::class])
internal class CreditCardRepositoryImpl(
    private val creditCardApiService: CreditCardApiService
) : BaseApiRepository(), CreditCardRepository {
    // 實作介面方法
}
```

- 檔案：`data/repository/src/main/java/com/kkday/data/repository/creditcardlist/CreditCardRepositoryImpl.kt`
- `binds` 參數：讓 Koin 知道此實作對應哪個介面，UseCase 才能注入介面型別

### @KoinViewModel（ViewModel）

與 Android ViewModel 生命週期整合，Fragment/Activity 重建時自動保留。

```kotlin
@KoinViewModel
class CartViewModel(
    private val paymentStrategyViewModelDelegate: PaymentStrategyViewModelDelegate,
    private val footerViewModelDelegate: FooterViewModelDelegate
) : ViewModel()
```

- 在 Fragment/Activity 中取得：`val vm: CartViewModel by viewModel()`
- 在 Composable 中取得：`val vm: CartViewModel = koinViewModel()`

---

## Named Qualifier 清單

### 定義位置

**KoinConstant**：`libs/model/src/main/java/com/kkday/data/consts/KoinConstant.kt`

```kotlin
object KoinConstant {
    const val APP_DEFAULT_SCOPE = "APP_DEFAULT_SCOPE"
    const val APP_IO_SCOPE = "APP_IO_SCOPE"
    const val APP_DATA_STORE = "APP_DATA_STORE"
    const val APP_CATEGORY_HISTORY = "APP_CATEGORY_HISTORY"
    const val NAMED_SHARED_PREFERENCE = "sharedPrefs"
    const val NAMED_SECURE_SHARED_PREFERENCE = "securePrefs"
}
```

**Dispatcher**：`app/src/main/java/com/kkday/member/di/CoroutinesScopeModule.kt`

```kotlin
val coroutinesModule = module {
    single(named("DispatcherMain"))    { Dispatchers.Main }
    single(named("DispatcherIO"))      { Dispatchers.IO }
    single(named("DispatcherDefault")) { Dispatchers.Default }
    single(named(APP_DEFAULT_SCOPE))   { CoroutineScope(SupervisorJob() + Dispatchers.Default) }
    single(named(APP_IO_SCOPE))        { CoroutineScope(SupervisorJob() + Dispatchers.IO) }
}
```

### 使用方式

```kotlin
// 注入 Dispatcher（在 UseCase 或 Repository 中）
@Factory
class GetHotelRoomUseCase(
    private val repository: HotelRepository,
    private val dispatcher: CoroutineDispatcher  // named("DispatcherIO")
)

// Module 宣告（非 annotation 方式）
factory { GetHotelRoomUseCase(get(), get(named("DispatcherIO"))) }

// 注入 DataStore
single { HotelSearchRepository(kkApi = get(), dataStoreHelper = get(named(APP_DATA_STORE))) }
```

---

## 介面綁定模式

### 方式一：annotation `binds` 參數（推薦）

```kotlin
// 介面（:domain:contract 或 :data:repository）
interface CreditCardRepository {
    suspend fun saveCreditCard(...): CreditCardSaveResponse?
}

// 實作（:data:repository）
@Single(binds = [CreditCardRepository::class])
internal class CreditCardRepositoryImpl(...) : CreditCardRepository
```

### 方式二：Module DSL `single<Interface> { Implementation() }`

```kotlin
// WebModule.kt
val webModule = module {
    single<WebRouter> { WebRouterImpl() }
    single<ChatNavigator> { ChatNavigatorImpl(get(), get(), get(), get()) }
}
```

### 方式三：`factory<Interface> { ... }` 搭配條件判斷

```kotlin
// 依參數決定注入哪個實作（appModule.kt）
factory<IDeepLinkHelper> { parameters ->
    when (val config: DeepLinkHelperConfig = parameters.get()) {
        is DeepLinkHelperConfig.Fcm  -> FcmNotificationDeepLinkHelper(...)
        is DeepLinkHelperConfig.Main -> MainActivityDeepLinkHelper(...)
    }
}
```

---

## Module 檔案位置

### 核心 Module（`app/src/main/java/com/kkday/member/di/`）

| 檔案 | 內容 |
|------|------|
| `appModule.kt` | App 層 ViewModels、Store、DeepLink helper |
| `RepositoryModule.kt` | Repository singleton 綁定 |
| `UseCaseModule.kt` | 非 annotation UseCase 宣告 |
| `CoroutinesScopeModule.kt` | Dispatcher、CoroutineScope named injection |
| `ChatModule.kt` | Chat 相關 API Service、Navigator |
| `actionModule.kt` | Reductor Action handler |
| `presenterModule.kt` | Presenter 綁定 |

### Feature Module DI（`app/.../view/*/di/`）

| 檔案 | 內容 |
|------|------|
| `view/order/di/OrderModule.kt` | 訂單功能模組 |
| `view/transportation/di/TransModule.kt` | 交通功能模組 |
| `view/login/di/LoginModule.kt` | 登入功能模組 |
| `view/launch/di/LaunchModule.kt` | 啟動畫面模組 |

### KSP Annotation 生成 Module

| 檔案 | ComponentScan 範圍 |
|------|-------------------|
| `app/com/kkday/di/AppAnnotationModule.kt` | `com.kkday`（全域） |
| `domain/usecase/.../UseCaseAnnotationModule.kt` | `com.kkday.domain` |
| `libs/base/.../BaseAnnotationModule.kt` | `com.kkday.library.common` |
| `libs/networking/api/.../NetworkingApiAnnotationModule.kt` | `com.kkday.library.networking.api` |

---

## Koin 初始化

**位置**：`app/src/main/java/com/kkday/member/KKdayApp.kt`

```kotlin
startKoin {
    androidContext(this@KKdayApp)
    modules(
        arrayListOf(
            appModule,
            repositoryModule,
            useCaseModules,
            coroutinesModule,
            UseCaseAnnotationModule().module,   // KSP 生成
            AppAnnotationModule().module,        // KSP 生成
            NetworkingApiAnnotationModule().module,
            // ... 30+ 個模組
        )
    )
}
```

---

## KSP 自動掃描機制

```
@Module + @ComponentScan("com.kkday.domain")
         ↓
KSP 在編譯時掃描 com.kkday.domain 下所有 @Factory / @Single 類別
         ↓
自動生成對應的 Koin module 程式碼
         ↓
在 KKdayApp.kt 中用 UseCaseAnnotationModule().module 載入
```

**優點**：新增 `@Factory` / `@Single` 類別後不需手動修改任何 Module 檔案。

---

## 新增依賴的標準流程

1. **新增 UseCase**：在類別加 `@Factory`，constructor 注入介面 → 自動被 KSP 掃描
2. **新增 Repository**：實作 domain contract 介面，加 `@Single(binds = [Interface::class])` → 自動掃描
3. **新增 ViewModel**：加 `@KoinViewModel` → 自動掃描
4. **需要 named injection**：在 `KoinConstant.kt` 定義常數，在 `CoroutinesScopeModule.kt` 或對應 Module 提供，constructor 參數加 `@Named("xxx")`

---

*文件版本：Step 3 of AI Guide | 最後分析日期：2026-03-17*

## 相關筆記
- [02-modules](02-modules.md)
- [03-ui-patterns](03-ui-patterns.md)
- [05-networking](05-networking.md)
- [06-data-layer](06-data-layer.md)
- [checkout](features/checkout.md)
- [order-detail-compose](features/order-detail-compose.md)
- [order-success](features/order-success.md)
- [sku-activity-shell](features/sku-activity-shell.md)

# 03 · 依賴注入（Hilt）

這份管**依賴怎麼取得、綁定寫在哪、scope 怎麼選、測試怎麼替換**。以 Hilt 為唯一標準（官方推薦方案）。
不管介面該放哪個模組（02）、不管某段邏輯屬於哪一層（01）。
用其他 DI 框架的專案看最後一節「換成別的框架時」。

| 疑問 | 去哪 |
|---|---|
| 介面與實作分別放哪個 Gradle 模組 | `02-modularization` |
| 該不該開 UseCase、Repository 職責邊界 | `01-architecture` `05-data-layer` |
| ViewModel 能持有什麼、UiState 怎麼設計 | `08-ui-state` |
| Dispatcher 該用哪個、application scope 怎麼開 | `12-coroutines-flow` |
| fake 還是 mock、哪一層測什麼 | `15-testing` |

---

## 一、component 與 scope 對照

| `@InstallIn` component | scope 註解 | 實例存活期間 |
|---|---|---|
| `SingletonComponent` | `@Singleton` | Application 全程 |
| `ActivityRetainedComponent` | `@ActivityRetainedScoped` | Activity 建立到銷毀，**跨設定變更保留** |
| `ViewModelComponent` | `@ViewModelScoped` | 該 ViewModel 存活期間 |
| `ActivityComponent` | `@ActivityScoped` | Activity 實例（設定變更會重建） |
| `FragmentComponent` | `@FragmentScoped` | Fragment 實例 |
| `ViewComponent` / `ViewWithFragmentComponent` | `@ViewScoped` | View 實例 |
| `ServiceComponent` | `@ServiceScoped` | Service 實例 |

**預設是不加 scope。** 先問「這個型別有共用的可變狀態嗎？初始化很貴嗎？」，兩個都否就 unscoped。

## 二、綁定該用哪一種

```
這個型別自己能加 @Inject constructor 嗎？
├ 可以（自家 Repository / UseCase / ViewModel / Mapper）
│   ├ 注入端要的是介面 ──── @Binds abstract fun bindX(impl: DefaultX): X
│   └ 注入端要的就是它 ──── 不用寫 module，@Inject constructor 就夠
└ 不行（第三方 SDK、需要 Builder、由工廠方法產生）
    └ @Provides fun provideX(...): X = ...
```

---

## 三、規則

### manual-dependency-instantiation · MUST_NOT · new-only+on-touch · manual

一般類別（Repository、UseCase、ViewModel、Mapper）的依賴一律由建構函式參數傳入。類別內部不得自行 `new` 依賴、不得呼叫 `getInstance()` 取得依賴。只有由系統建構的 Android 類別才允許 field injection。

✗ `class DefaultOrderRepository { private val api = OrderApiService.create() }`
✓ `class DefaultOrderRepository @Inject constructor(private val api: OrderApiService)`

例外：無狀態的純值物件（data class、Kotlin 標準型別）可直接建立 ｜ src: developer.android.com/topic/architecture/recommendations

### service-locator-access · MUST_NOT · new-only+on-touch · regex

不得新增 service locator：全域 `object XxxServiceLocator`、`AppContainer` 手動取件、或在 domain / data 類別中反查 DI 容器。跨模組共享的能力一律注入介面取得，不得用 Kotlin `object` 單例持有狀態。

✗ `object ServiceLocator { fun orderRepository(): OrderRepository = ... }`
✓ 建構函式注入 `OrderRepository`，綁定由 `@Module` 提供

例外：無 ｜ src: developer.android.com/training/dependency-injection

### missing-hilt-android-app · MUST · migrate · regex

`Application` 子類別必須標註 `@HiltAndroidApp`，並在 `AndroidManifest.xml` 的 `android:name` 註冊；整個 App 只能有一個。

✗ `class MainApplication : Application()`（無註解）
✓ `@HiltAndroidApp class MainApplication : Application()`

例外：無 ｜ src: developer.android.com/training/dependency-injection/hilt-android

### missing-android-entry-point · MUST · new-only+on-touch · manual

任何需要接受注入的 Android 類別（Activity、Fragment、Service、BroadcastReceiver、View）必須標註 `@AndroidEntryPoint`；標註 Fragment 時其宿主 Activity 也必須標註。Activity 必須繼承 `ComponentActivity`。純 Compose App 只需標註根 Activity。

✗ `class OrderActivity : ComponentActivity()` 內用 `hiltViewModel()` 卻沒有註解
✓ `@AndroidEntryPoint class OrderActivity : ComponentActivity()`

例外：無 ｜ src: developer.android.com/training/dependency-injection/hilt-android

### private-inject-field · MUST_NOT · new-only · regex

`@Inject` 注入的欄位不得宣告為 `private`。

✗ `@Inject private lateinit var analytics: AnalyticsLogger`
✓ `@Inject internal lateinit var analytics: AnalyticsLogger`

例外：無 ｜ src: developer.android.com/training/dependency-injection/hilt-android

### module-without-install-in · MUST · new-only+on-touch · regex

每個 `@Module` 都必須同時標註 `@InstallIn(<Component>::class)`。

✗ `@Module object NetworkModule { ... }`
✓ `@Module @InstallIn(SingletonComponent::class) object NetworkModule { ... }`

例外：dynamic feature 模組不得用 `@InstallIn` 對 app 提供綁定，改用 `@EntryPoint` ｜ src: developer.android.com/training/dependency-injection/hilt-multi-module

### provides-wrapping-constructor · SHOULD_NOT · new-only · manual

介面 → 實作的綁定用 `@Binds` 抽象函式，不得用 `@Provides` 包一層 `return DefaultXxx(...)`（那等於把依賴清單手抄一遍，實作改建構函式時要跟著改）。

✗ `@Provides fun provideOrderRepository(api: OrderApiService): OrderRepository = DefaultOrderRepository(api)`
✓ `@Binds internal abstract fun bindOrderRepository(impl: DefaultOrderRepository): OrderRepository`

例外：實作類別無法加 `@Inject constructor`（第三方型別）時用 `@Provides` ｜ src: 官方 sample nowinandroid `core/data/.../di/DataModule.kt`

### wrong-module-container-kind · MUST · new-only · manual

含 `@Binds` 的 module 必須是 `abstract class` 或 `interface`；只含 `@Provides` 的 module 必須是 `object`。不得用 `companion object` + `@JvmStatic` 的舊寫法。

✗ `@Module @InstallIn(SingletonComponent::class) class NetworkModule { @Provides fun ... }`
✓ `@Module @InstallIn(SingletonComponent::class) object NetworkModule { @Provides fun ... }`

例外：同一 module 同時需要 `@Binds` 與 `@Provides` 時用 `abstract class` + `companion object` ｜ src: developer.android.com/training/dependency-injection/hilt-android

### scope-component-mismatch · MUST · new-only+on-touch · manual

scope 註解必須與 module 的 `@InstallIn` component 對應（見第一節對照表），不得交叉使用。

✗ `@Module @InstallIn(ViewModelComponent::class)` 內的綁定標 `@Singleton`
✓ `@Module @InstallIn(ViewModelComponent::class)` 內的綁定標 `@ViewModelScoped`

例外：無 ｜ src: dagger.dev/hilt/components

### unnecessary-scoped-binding · SHOULD_NOT · new-only · manual

不得為了「少建立幾個物件」而加 scope。只有兩種情況才 scope：該型別持有需要共用的可變狀態，或初始化成本高昂且被廣泛使用。

✗ `@Singleton class GetOrderListUseCase @Inject constructor(...)`（無狀態）
✓ `class GetOrderListUseCase @Inject constructor(...)`（unscoped）

例外：無 ｜ src: developer.android.com/training/dependency-injection/hilt-android

### over-wide-scope · SHOULD · new-only · manual

需要 scope 時取「最窄仍能滿足需求」的層級：單一畫面的暫存狀態用 `@ViewModelScoped`，需跨設定變更但不跨畫面用 `@ActivityRetainedScoped`，真正全 App 共用才 `@Singleton`。

✗ `@Singleton class CheckoutFormStateHolder`（只有結帳畫面用）
✓ `@ViewModelScoped class CheckoutFormStateHolder`

例外：無 ｜ src: developer.android.com/training/dependency-injection/manual

### manual-viewmodel-factory · MUST_NOT · new-only · regex

ViewModel 一律 `@HiltViewModel` + `@Inject constructor`，Compose 端用 `hiltViewModel()` 取得。不得為了傳遞依賴而手寫 `ViewModelProvider.Factory`、`AbstractSavedStateViewModelFactory` 或 `@IntoMap` ViewModelKey multibinding；導航參數改由注入的 `SavedStateHandle` 讀取。

✗ `class OrderViewModelFactory(private val repo: OrderRepository) : ViewModelProvider.Factory`
✓ `@HiltViewModel class OrderViewModel @Inject constructor(private val repository: OrderRepository, savedStateHandle: SavedStateHandle) : ViewModel()`

例外：需要 runtime 參數時用 `@AssistedInject` + `@AssistedFactory`，仍不得手寫 Factory 樣板 ｜ src: developer.android.com/training/dependency-injection/hilt-android

### duplicate-type-without-qualifier · MUST · new-only+on-touch · manual

同一型別存在多個綁定時必須用自訂 `@Qualifier` 註解區分，且該型別的所有提供處與注入處都要帶 qualifier。不得靠參數名稱區分，也不得為了區分而多包一層 wrapper 型別。

✗ 兩個 `@Provides fun ...: OkHttpClient`，靠函式名 `provideAuthClient` / `providePlainClient` 區分
✓ `@Qualifier @Retention(BINARY) annotation class AuthenticatedClient` 標在提供處與注入處

例外：無 ｜ src: developer.android.com/training/dependency-injection/hilt-android

### string-based-qualifier · MUST_NOT · new-only · regex

不得用 `@Named("...")` 字串 qualifier，一律自訂 `@Qualifier` 註解（型別安全，拼錯會編譯失敗）。

✗ `@Named("io") dispatcher: CoroutineDispatcher`
✓ `@Dispatcher(IO) dispatcher: CoroutineDispatcher`

例外：無 ｜ src: developer.android.com/training/dependency-injection/hilt-android

### custom-context-binding · MUST_NOT · new-only · regex

需要 `Context` 時一律使用內建 qualifier `@ApplicationContext` / `@ActivityContext`，不得自行提供 Context 綁定或自訂 Context qualifier。

✗ `@Provides fun provideContext(app: Application): Context = app.applicationContext`
✓ `class LocalFileStore @Inject constructor(@ApplicationContext private val context: Context)`

例外：無 ｜ src: developer.android.com/training/dependency-injection/hilt-android

### dispatcher-binding-without-qualifier · MUST · new-only+on-touch · manual

`CoroutineDispatcher` 必須以帶 qualifier 的 `@Provides` 提供並由建構函式注入；application 級 `CoroutineScope` 同樣以綁定提供。（消費端不得硬寫 `Dispatchers.IO` 的規則見 `12-coroutines-flow`。）

✗ 沒有任何 dispatcher 綁定，各處自行取用
✓ `@Provides @Dispatcher(IO) fun providesIoDispatcher(): CoroutineDispatcher = Dispatchers.IO`

例外：無 ｜ src: 官方 sample nowinandroid `core/common/.../network/Dispatchers.kt`

### di-module-centralized-in-app · SHOULD_NOT · new-only · manual

DI module 檔案要放在「提供該綁定的 Gradle 模組」內（慣例 `<module>/src/main/kotlin/.../di/`），不得把所有綁定集中寫在 `:app`。`:app` 只保留自身綁定與 `@HiltAndroidApp` 組裝，但必須把所有含綁定的模組放進自己的 runtime classpath（新增 impl 模組時要同步加依賴，否則執行期找不到綁定）。

✗ `app/.../di/AllRepositoriesModule.kt` 列出每個 data 模組的實作綁定
✓ `core/data/.../di/DataModule.kt` 自帶 `@Binds`，`:app` 只依賴該模組

例外：介面在 `:x:api`、實作在 `:x:impl` 時，綁定放 `:x:impl` 的 di 目錄 ｜ src: developer.android.com/training/dependency-injection/hilt-multi-module

### missing-entry-point-for-unsupported-class · MUST · new-only · manual

Hilt 不支援的類別（`ContentProvider`、第三方框架建構的物件、legacy 類別）必須透過 `@EntryPoint` interface + `EntryPointAccessors` 取得依賴，且 interface 的 `@InstallIn` component 要與所用 accessor 相符。不得因此改回全域單例。

✗ `class OrderProvider : ContentProvider() { private val repo = OrderRepositoryHolder.instance }`
✓ `@EntryPoint @InstallIn(SingletonComponent::class) interface OrderProviderEntryPoint { fun orderRepository(): OrderRepository }` + `EntryPointAccessors.fromApplication(...)`

例外：無 ｜ src: developer.android.com/training/dependency-injection/hilt-android

### di-container-in-unit-test · SHOULD_NOT · new-only · regex

JVM 單元測試不得啟動 DI container（`HiltAndroidRule`、`@HiltAndroidTest`），直接呼叫建構函式傳入 fake。

✗ `@HiltAndroidTest class OrderViewModelTest { @get:Rule val hiltRule = HiltAndroidRule(this) }`
✓ `val viewModel = OrderViewModel(FakeOrderRepository(), SavedStateHandle())`

例外：專門驗證 DI 圖是否完整的測試 ｜ src: developer.android.com/training/dependency-injection/hilt-testing

### ad-hoc-test-binding-override · SHOULD · new-only · manual

instrumented / UI 測試要替換綁定時，優先在 `androidTest` 建立 `@Module @TestInstallIn(components = [...], replaces = [...])` 的測試 module；只有單一測試需要特例才用 `@UninstallModules` + `@BindValue`。不得讓 fake 綁定進入 main source set 或 release variant。

✗ 在 `src/main` 加一個 `FakeDataModule`，用 build flag 切換
✓ `src/androidTest/.../TestDataModule.kt` 標 `@TestInstallIn(replaces = [DataModule::class])`

例外：無 ｜ src: developer.android.com/training/dependency-injection/hilt-testing

---

## 四、換成別的框架時

若專案已使用其他 DI 框架，本檔的 Hilt 專屬語法規則（`@InstallIn`、`@Binds` 容器形狀、內建 Context qualifier、`@TestInstallIn`）不適用，但以下原則與框架無關，一律成立：

1. **建構函式注入是預設**，只有系統建構的 Android 類別才用容器反查；任何在 domain / data 類別中反查容器的寫法都是 service locator。
2. **介面與實作分離**，綁定必須顯式宣告暴露的介面型別，消費端只依賴介面。
3. **scope 語意要對應**：全 App 單例 / 畫面級 / 每次建立三種語意必須明確選擇，判準同 `unnecessary-scoped-binding` 與 `over-wide-scope`；不得用 App 級單例保存單一畫面的暫存狀態。
4. **DI 圖必須在建置或測試階段被驗證**。Hilt 天生編譯期驗證；沒有這項能力的框架必須補上等價機制（編譯期檢查選項，或每個對外模組一支驗證用單元測試並納入 CI），否則缺漏綁定會變成使用者進到該畫面才炸的執行期錯誤。
5. **DI 定義跟著實作模組走**，不集中在 `:app`。
6. **qualifier 用集中定義的常數或型別安全 qualifier**，不寫字面字串。
7. **手動建立的 scope 必須保證關閉**（含例外路徑），畫面級 scope 交給框架的生命週期整合管理。
8. **單元測試不啟動容器**，直接呼叫建構函式。

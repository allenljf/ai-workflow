# 12 · 協程與資料流

**管**：scope 與 dispatcher 的取得方式、結構化併發、取消與例外、Flow 的建立／轉換／共享（冷熱流、`shareIn`／`stateIn`、`callbackFlow`）。
**不管**：UiState 怎麼設計、一次性事件怎麼傳、Compose 端怎麼收集、測試怎麼寫。AGENTS.md 通用紅線 9–12 落在本檔領域，以下是它們可判定的完整定義。

| 想找 | 去 |
|---|---|
| UiState 形狀、一次性事件（導航／Snackbar）、`Mutable*Flow` 不得外露、Views 端 `repeatOnLifecycle` | `08-ui-state` |
| `collectAsStateWithLifecycle`、`LaunchedEffect` 等 side effect API | `10-compose-state` |
| `runTest`／`TestDispatcher`／Turbine／`stateIn` 的測試寫法 | `15-testing` |
| Repository 的錯誤模型與 `Result` 包裝 | `05-data-layer` |
| Hilt module、`@Qualifier` 的撰寫慣例 | `03-dependency-injection` |

---

## 一、Flow 選型判斷樹

由上而下，**第一個命中即採用**。

| # | 判準 | 選 |
|---|---|---|
| 1 | 來源是 callback／listener／第三方 SDK 回呼 | `callbackFlow`（要背壓策略或合併多來源用 `channelFlow`） |
| 2 | 語意是「當下狀態」：有初始值、新訂閱者要立刻拿到最新值、同值不需重發 | `StateFlow`（`MutableStateFlow` 或 `stateIn`） |
| 3 | 語意是「事件流」：無初始值、同值必須重發、需 replay 給後加入者 | `SharedFlow`，放 data 層、由 application scope 驅動 |
| 4 | 語意是「ViewModel → UI 的一次性動作」（導航、Snackbar、開外部 App） | 四者都不用 → 建模成 UI state 欄位，見 `08-ui-state` |
| 5 | 需要「恰好被消費一次」的佇列（序列化寫入、上傳排程） | `Channel`，只限單一模組內部，不對 UI／domain 暴露 |
| 6 | 以上皆非 | 維持冷 Flow；只有「多 collector ＋ 上游昂貴」才轉熱 |

```kotlin
// 1 val isOnline: Flow<Boolean> = callbackFlow { register(cb); awaitClose { unregister(cb) } }
// 2 private val _uiState = MutableStateFlow(OrderUiState()); val uiState = _uiState.asStateFlow()
// 3 private val _invalidations = MutableSharedFlow<Unit>(replay = 0)  // 對外 asSharedFlow()
// 5 private val uploadQueue = Channel<UploadTask>(capacity = Channel.BUFFERED)
// 6 fun observeOrders(): Flow<List<Order>> = orderDao.observeAll().map(OrderEntity::toDomain)
```

**冷熱差異**：冷 Flow（`flow { }`、Room 的 Flow）在每個 terminal operator 各跑一次 producer；`StateFlow` / `SharedFlow` 是熱流，producer 只跑一份、與 collector 數量無關。判準是「同一份資料被 N 處看」，不是「寫起來比較順手」。上游是輪詢、網路請求或註冊型 listener 又會被多處 collect 時，必須在 data 層以 `shareIn` / `stateIn(externalScope, ...)` 轉熱共享，否則同一支 API 會被打 N 次、listener 註冊 N 份。

## 二、Dispatcher 與 scope 的注入樣板

```kotlin
// :core:common
enum class AppDispatchers { Default, IO }
@Qualifier @Retention(AnnotationRetention.RUNTIME) annotation class Dispatcher(val d: AppDispatchers)
@Qualifier @Retention(AnnotationRetention.RUNTIME) annotation class ApplicationScope

@Module @InstallIn(SingletonComponent::class)
object CoroutineModule {
    @Provides @Dispatcher(AppDispatchers.IO)
    fun providesIoDispatcher(): CoroutineDispatcher = Dispatchers.IO
    @Provides @Dispatcher(AppDispatchers.Default)
    fun providesDefaultDispatcher(): CoroutineDispatcher = Dispatchers.Default
    @Provides @Singleton @ApplicationScope  // SupervisorJob：單一子工作失敗不拖垮整個 scope
    fun providesApplicationScope(@Dispatcher(AppDispatchers.Default) d: CoroutineDispatcher) =
        CoroutineScope(SupervisorJob() + d)
}

class DefaultOrderRepository @Inject constructor(
    private val orderApi: OrderApiService,
    @Dispatcher(AppDispatchers.IO) private val ioDispatcher: CoroutineDispatcher,
) : OrderRepository
```

**scope 怎麼選**：綁畫面生命週期 → `viewModelScope`；要活過畫面（書籤、上傳、事件送出）→ 注入 `@ApplicationScope`；只是在 `suspend` 內開子工作 → `coroutineScope { }`，不要建 scope。

---

## 三、規則

### hardcoded-dispatcher · MUST_NOT · new-only+on-touch · regex

production 程式碼（非 DI module、非測試）不得出現 `Dispatchers.IO` / `Dispatchers.Default` / `Dispatchers.Main` 字面量，一律以 `@Dispatcher(...)` qualifier 建構子注入。建構子預設參數 `= Dispatchers.IO` 同樣違規——它讓「忘記注入」在編譯期看不出來。

✗ `suspend fun fetch() = withContext(Dispatchers.IO) { api.fetch() }`
✓ `suspend fun fetch() = withContext(ioDispatcher) { api.fetch() }`

例外：DI module 的 `@Provides` 本體 · source: https://developer.android.com/kotlin/coroutines/coroutines-best-practices

### blocking-call-in-suspend · MUST · new-only+on-touch · manual

`suspend` 函式必須 main-safe：內部若有阻塞 I/O、DB、檔案、大量序列化或重運算，必須自己 `withContext(injectedDispatcher)` 包住，呼叫端不需知道它跑在哪條執行緒。反過來，呼叫端也不得再包一層 `withContext`——要包代表下層不 main-safe，去修下層。

✗ `suspend fun fetch(): List<Order> = api.fetchBlocking()`
✓ `suspend fun fetch(): List<Order> = withContext(ioDispatcher) { api.fetch() }`

例外：底層已 main-safe 的 suspend API（Retrofit `suspend fun`、Room `suspend` DAO）不需再包 · source: https://developer.android.com/kotlin/coroutines/coroutines-best-practices

### runblocking-in-production · MUST_NOT · new-only+on-touch · regex

production 程式碼不得出現 `runBlocking`，包含用它把 suspend 結果同步取出。需要同步讀值就暴露 `StateFlow.value`，或把呼叫端改成 `suspend`。

✗ `val user = runBlocking { userRepository.getUser() }`
✓ `val user: StateFlow<User?> = userRepository.userStream.stateIn(...)`

例外：測試碼、`main()` 進入點 · source: https://developer.android.com/kotlin/coroutines/coroutines-best-practices

### global-scope · MUST_NOT · new-only+on-touch · regex

不得使用 `GlobalScope`。需要活過呼叫端生命週期的工作，改注入 application scope。

✗ `GlobalScope.launch { dataSource.bookmark(id) }`
✓ `externalScope.launch { dataSource.bookmark(id) }`

例外：無 · source: https://developer.android.com/kotlin/coroutines/coroutines-best-practices

### custom-scope-in-viewmodel · MUST_NOT · new-only+on-touch · regex

ViewModel 內不得出現 `CoroutineScope(...)` 建構。自建 scope 不會在 `onCleared()` 取消，coroutine 與 ViewModel 一起洩漏。

✗ `private val scope = CoroutineScope(Dispatchers.Main + Job())`
✓ `fun load() = viewModelScope.launch { /* ... */ }`

例外：無（要在測試控制執行時機，注入 `CoroutineDispatcher` 而非注入 scope）· source: https://developer.android.com/topic/libraries/architecture/coroutines

### unstructured-scope-in-suspend · MUST · new-only · manual

`suspend` 函式內要開子 coroutine，只能用 `coroutineScope { }` 或 `supervisorScope { }`（子工作彼此獨立、單一失敗不該連坐時用後者）。自建 scope 會脫離結構化併發：呼叫端取消時不取消、例外不往上傳、函式回傳後工作還在跑。互不依賴的多個呼叫在此以 `async` 並行，不要循序等待。

✗ `suspend fun sync() { CoroutineScope(ioDispatcher).launch { repo.pull() } }`
✓ `suspend fun sync() = coroutineScope { val a = async { repoA.get() }; val b = async { repoB.get() }; merge(a.await(), b.await()) }`

例外：無 · source: https://developer.android.com/kotlin/coroutines/coroutines-best-practices

### swallowed-cancellation · MUST_NOT · new-only+on-touch · detekt:SuspendFunSwallowedCancellation

不得 catch `CancellationException`，也不得用 `catch (e: Exception)` / `catch (e: Throwable)` 包住 suspend 呼叫而不先把它重新拋出。取消靠它傳播，吞掉會讓已取消的工作繼續往下跑（更新已銷毀畫面、送出不該送的請求）。

✗ `try { repo.login() } catch (e: Exception) { showError(e) }`
✓ `try { repo.login() } catch (e: CancellationException) { throw e } catch (e: IOException) { showError(e) }`

例外：無 · source: https://developer.android.com/kotlin/coroutines/coroutines-best-practices

### uncaught-exception-in-launch · MUST · new-only+on-touch · manual

`viewModelScope.launch` / `lifecycleScope.launch` 內呼叫可能失敗的 suspend 函式時，必須以具體例外型別 try/catch，或在 Flow 上用 `catch` operator。這些 scope 內未捕捉的例外會直接 crash。

✗ `viewModelScope.launch { _uiState.value = Success(getOrders()) }`
✓ `viewModelScope.launch { runCatchingOrders() }`（內部具體 catch `IOException` 並先 rethrow `CancellationException`）

例外：下層已把失敗收斂成回傳值（`Result` 型別）時不需 catch · source: https://developer.android.com/kotlin/coroutines/coroutines-best-practices

### uncancellable-cpu-loop · MUST · new-only · manual

不含任何 suspend 呼叫的長迴圈（純運算、阻塞式 API、逐檔處理）必須在迴圈內 `ensureActive()` 或檢查 `isActive`。取消是協作式的，純運算迴圈不會自動檢查。

✗ `for (file in files) { readFile(file) }`
✓ `for (file in files) { ensureActive(); readFile(file) }`

例外：迴圈體本身含 `delay` / `withContext` / 其他 suspend 呼叫 · source: https://developer.android.com/kotlin/coroutines/coroutines-best-practices

### suspend-fun-returning-flow · MUST_NOT · new-only+on-touch · detekt:SuspendFunWithFlowReturnType

不得宣告 `suspend fun x(): Flow<T>`。取得冷 Flow 本身不執行任何工作，加 `suspend` 只是誤導呼叫端並逼出無謂的 coroutine 包裝。

✗ `suspend fun observeOrders(): Flow<List<Order>>`
✓ `fun observeOrders(): Flow<List<Order>>`

例外：無 · source: 業界共識（detekt `coroutines>SuspendFunWithFlowReturnType`）

### withcontext-in-flow-builder · MUST_NOT · new-only+on-touch · manual

`flow { }` 內不得用 `withContext` 或另開 coroutine 後 `emit`，runtime 會拋 `IllegalStateException`（Flow invariant violated）。要換 context 用 `flowOn`，要從其他 context／callback 發射用 `callbackFlow` / `channelFlow`。

✗ `flow { withContext(ioDispatcher) { emit(api.fetch()) } }`
✓ `flow { emit(api.fetch()) }.flowOn(ioDispatcher)`

例外：無 · source: https://developer.android.com/kotlin/flow

### flowon-misplaced · MUST · new-only · manual

`flowOn` 只影響它上游的 producer 與 operator，必須放在要改變 context 的那些 operator「之後」；下游與 collector 仍在收集端的 context。

✗ `upstream.flowOn(defaultDispatcher).map { heavyFilter(it) }`（`map` 仍跑在主執行緒）
✓ `upstream.map { heavyFilter(it) }.flowOn(defaultDispatcher).catch { emit(cached()) }`

例外：無 · source: https://developer.android.com/kotlin/flow

### try-catch-around-emit · MUST_NOT · new-only+on-touch · manual

不得在 `flow { }` 內用 try/catch 包住 `emit`——它會連下游 collector 拋的例外一起攔到，違反 exception transparency。上游例外一律用 `catch` operator 處理。另注意 `catch` 攔不到 `collect { }` lambda 內的例外，那種情況改寫成 `.onEach { }.catch { }.collect()`。

✗ `flow { try { emit(remote.fetch()) } catch (e: IOException) { emit(cached()) } }`
✓ `remote.orders.catch { emit(cached()) }`

例外：無 · source: https://developer.android.com/kotlin/flow

### callbackflow-without-awaitclose · MUST · new-only+on-touch · manual

`callbackFlow` / `channelFlow` 的最後一行必須是 `awaitClose { }`，並在其中反註冊 callback／listener；缺了會 runtime 拋 `IllegalStateException`，且取消時 listener 不移除（洩漏＋殭屍回呼）。從非 suspend 的 callback 發射值一律用 `channel.trySend()`，不得用已廢棄的 `offer()`。

✗ `callbackFlow { manager.register(cb) }`
✓ `callbackFlow { manager.register(cb); awaitClose { manager.unregister(cb) } }.flowOn(ioDispatcher)`

例外：無 · source: https://developer.android.com/kotlin/flow（官方 sample nowinandroid `ConnectivityManagerNetworkMonitor`）

### manual-collect-into-mutablestateflow · SHOULD · new-only · manual

ViewModel 的衍生狀態應以 `stateIn` 宣告，不得在 `init { viewModelScope.launch { flow.collect { _state.value = ... } } }` 手動搬值。手動搬值等於自己重寫一次 `stateIn`，而且上游訂閱不會隨 UI 訂閱自動啟停。

✗ `init { viewModelScope.launch { getOrders().collect { _uiState.value = Success(it) } } }`
✓ `val uiState: StateFlow<OrderUiState> = getOrders().map(::Success).stateIn(viewModelScope, WhileSubscribed(5_000), Loading)`

例外：該狀態同時被使用者操作直接寫入（`_uiState.update { }`）而非純衍生 · source: https://developer.android.com/topic/libraries/architecture/coroutines

### statein-outside-property-initializer · MUST_NOT · new-only+on-touch · manual

`stateIn` / `shareIn` 只能在 property 初始化時呼叫一次，不得放在 `get()`、一般函式或 `@Composable` 內。每次呼叫都會建立新的熱流與新的上游訂閱 → 重複請求、狀態不同步、scope 洩漏。

✗ `val uiState: StateFlow<UiState> get() = upstream.stateIn(viewModelScope, ..., Loading)`
✓ `val uiState: StateFlow<UiState> = upstream.stateIn(viewModelScope, ..., Loading)`

例外：無 · source: 業界共識（kotlinx.coroutines `stateIn` 文件；官方 sample nowinandroid）

### sharing-started-eagerly · SHOULD_NOT · new-only · regex

UI 導向的 `stateIn` / `shareIn` 不得用 `SharingStarted.Eagerly` / `Lazily`（producer 永久存活，沒人看畫面也在耗電、佔連線），一律 `WhileSubscribed(5_000)`——5 秒是為了跨越設定變更與 Activity 重建而不重啟上游。

✗ `.stateIn(viewModelScope, SharingStarted.Eagerly, Loading)`
✓ `.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), Loading)`

例外：上游極昂貴且必須立即斷開（長連線、相機、定位）時用 `WhileSubscribed(0)`，並在 PR 說明理由 · source: https://developer.android.com/topic/libraries/architecture/coroutines

### mutable-collection-in-stateflow · MUST · new-only+on-touch · manual

放進 `StateFlow` 的型別必須 immutable 且有正確 `equals`（data class／sealed interface／`List`）。`StateFlow` 以 `equals` 做 conflation，就地修改可變集合後參考不變，collector 完全收不到更新——這是典型的「畫面不更新」bug。

✗ `_uiState.value.items.add(order)`（欄位宣告成 `MutableList<Order>`）
✓ `_uiState.update { it.copy(items = it.items + order) }`

例外：無 · source: https://developer.android.com/kotlin/flow/stateflow-and-sharedflow

---

## 四、尚無定論

官方未表態，以下是**建議不是規則**，專案內一致即可：

- **`WhileSubscribed` 的 timeout 值**：官方 snippet 用 `5_000` 但未說明是唯一正確值。建議定義一個共用常數全專案沿用，不要每個 ViewModel 各寫一個魔術數字。
- **Dispatcher 要幾種**：官方只示範 IO / Default，多數專案這兩個就夠；要加 `Main.immediate` 之前先確認真有需求。
- **`Channel` 的容量與 `onBufferOverflow`**：依情境選，但務必顯式指定，不要靠預設值。

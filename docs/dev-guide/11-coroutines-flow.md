# 11 · Coroutines 與 Flow

**這份管**：dispatcher 注入（本檔是 dispatcher 規則的唯一 owner）、scope 選擇與 structured concurrency、取消與例外、Flow 選型（StateFlow / SharedFlow / Channel / callbackFlow / 冷流）、冷熱流轉換、RxJava 收斂邊界。

**這份不管**：UiState 欄位設計與 one-off event 出口（[08-ui-state.md](08-ui-state.md)）、Compose 端收集 Flow（[09b-compose-state.md](09b-compose-state.md)）、Fragment / Activity 端收集 Flow 與 View 互通（[17-interop-views-compose.md](17-interop-views-compose.md)）、coroutine 測試寫法（[14-testing.md](14-testing.md)）。

跨檔主題（只在對應檔案定義，這裡不重述）：

> Compose 收集 Flow 用 `collectAsStateWithLifecycle` → [09b-compose-state.md#collect-as-state](09b-compose-state.md)
> ViewModel 衍生 UI state 用 `stateIn(WhileSubscribed)` → [08-ui-state.md#statein-while-subscribed](08-ui-state.md)
> `SharingStarted.Eagerly` / `Lazily` 的限制 → [08-ui-state.md#eager-sharing-started](08-ui-state.md)
> one-off event 一律 events-as-state（Channel 白名單見該檔）→ [08-ui-state.md#one-off-event-as-state](08-ui-state.md)
> 對外暴露 Mutable 狀態 → [08-ui-state.md#mutable-state-exposed](08-ui-state.md)
> Rx 型別不得跨出 data 層 → [17-interop-views-compose.md#rx-type-crosses-boundary](17-interop-views-compose.md)
> 既有 Rx 鏈的觸碰邊界 → [checklists/touch-legacy-rx.md](checklists/touch-legacy-rx.md)

---

## 一、Flow 選型判斷樹

自上而下，**第一個命中即採用**。不要跳著挑。

| # | 條件 | 用什麼 |
|---|------|-------|
| 1 | 來源是 callback / listener / 第三方 SDK（Socket.IO、FCM、`ConnectivityManager`、TapPay / Adyen 回呼） | `callbackFlow` + `awaitClose`；需背壓策略或合併多來源時用 `channelFlow` |
| 2 | 語意是「當下狀態」：有初始值、新訂閱者要立刻拿到最新值、同值不必重發（UI state、登入狀態、購物車數量、選中的 tab） | `StateFlow`（ViewModel 內用 `MutableStateFlow`，衍生值用 `stateIn`） |
| 3 | 語意是「事件流」：無初始值、同值必須重複發、需要 replay 給後加入者（refresh tick、跨模組廣播、資料失效通知） | `MutableSharedFlow(replay = 0 或 1)`，放 data 層由 application scope 驅動 |
| 4 | 語意是「ViewModel → UI 的一次性動作」（導航、Snackbar、Toast、開啟外部 App） | **都不要用** → [08-ui-state.md#one-off-event-as-state](08-ui-state.md) |
| 5 | 真的需要「恰好被消費一次」的生產者／消費者佇列（序列化寫入、上傳工作隊列） | `Channel`，且只限 data 層內部，不對 domain / UI 暴露 |
| 6 | 以上皆非 | 維持冷 Flow（Room 的 `Flow`、`flow { }` 包 suspend 呼叫） |

**冷熱差異**：冷 Flow 的 producer 對每個 collector 各跑一次（兩個畫面 collect 同一個 `flow { api.get() }` = 兩次網路請求）；`shareIn` / `stateIn` 轉成熱流後多個 collector 共用一份上游。判斷「要不要轉熱」見 `cold-flow-multi-collector`。

---

## 二、Dispatcher 與 main-safety

### hardcoded-dispatcher · MUST NOT · new-only+on-touch · lint:hardcoded-dispatcher

生產程式碼（非測試、非 DI module）禁止字面 `Dispatchers.IO` / `Dispatchers.Default` / `Dispatchers.Unconfined`。Repository / DataSource / UseCase 由建構子收 `CoroutineDispatcher`，**不得給預設值** `= Dispatchers.IO`（忘了注入時編譯期看不出來）。切執行緒是最底層實作的責任，**ViewModel 一律不得 `launch(Dispatchers.IO)`**，只寫 `viewModelScope.launch { }`。紅線 F1。

✗ `viewModelScope.launch(Dispatchers.IO) { repository.getOrder(id) }`  // ViewModel 不決定執行緒
✗ `class OrderRepositoryImpl(private val io: CoroutineDispatcher = Dispatchers.IO)`  // 預設值等於沒注入
✓ `@Single class OrderRepositoryImpl(@Named("DispatcherIO") private val ioDispatcher: CoroutineDispatcher)`（import `org.koin.core.annotation.Named`；DSL module 內寫 `get(named("DispatcherIO"))`）
✓ 可用 qualifier 只有 `CoroutinesScopeModule.kt` 已註冊的三個：`DispatcherMain` / `DispatcherIO` / `DispatcherDefault`，**不得自行發明新字串**

例外：DI module 本身（`CoroutinesScopeModule.kt` 這類）與測試碼。
偏離官方之處：官方建議 qualifier 用集中常數，但 `KoinConstant` 目前沒有 dispatcher 常數（照舊版文件寫 `KoinConstant.DISPATCHER_IO` 會編譯失敗），故暫時寫字面字串；補常數後改引用 → [90-migration-ledger.md#m-08](90-migration-ledger.md)。
既有違規：139 檔（ViewModel 38 檔、`viewModelScope.launch(Dispatchers.IO)` 54 處）→ [90-migration-ledger.md#m-08](90-migration-ledger.md)。不得把功能 PR 擴大成 dispatcher 重構。

### suspend-not-main-safe · MUST · new-only+on-touch · lint:suspend-not-main-safe

`suspend` 函式必須 main-safe：內部若有阻塞 I/O、DB、檔案、大量 JSON 解析或重運算，必須自己用 `withContext(注入的 dispatcher)` 包住。呼叫端不需要知道該切哪條執行緒。紅線 F4。

✗ `override suspend fun getOrder(id: String): Order = api.getOrder(id).toDomain()`  // 阻塞式解析留在呼叫端執行緒
✓ `override suspend fun getOrder(id: String): Order = withContext(ioDispatcher) { api.getOrder(id).toDomain() }`

例外：函式本體只是轉發另一個已經 main-safe 的 suspend 函式時不需再包。

### withcontext-at-call-site · SHOULD NOT · new-only · manual

ViewModel / UseCase 呼叫 repository 的 suspend 函式時，不得再包一層 `withContext`。切執行緒的責任只屬於最底層實作。

✗ `viewModelScope.launch { withContext(ioDispatcher) { repository.getOrder(id) } }`
✓ `viewModelScope.launch { val order = repository.getOrder(id) }`

例外：ViewModel 內自己做的 CPU 重運算（大量排序、影像處理）仍需自行 `withContext(defaultDispatcher)`。

---

## 三、Scope 與 structured concurrency

### global-scope · MUST NOT · new-only+on-touch · lint:global-scope

禁止 `GlobalScope`（無法取消、必然洩漏）。需要活過呼叫端生命週期的工作，注入 application 級 `CoroutineScope`（以 `SupervisorJob() + 注入的 dispatcher` 建立、DI 註冊為 singleton）。紅線 F2。

✗ `GlobalScope.launch { uploadLog() }`
✓ 建構子收 `@Named(KoinConstant.APP_IO_SCOPE) private val appScope: CoroutineScope`，用 `appScope.launch { uploadLog() }`

既有違規：6 檔 → [90-migration-ledger.md#m-08](90-migration-ledger.md)

### vm-custom-scope · MUST NOT · new-only · manual

ViewModel 內禁止自建 `CoroutineScope(...)`；一律用 `viewModelScope`（它會在 `onCleared` 自動取消）。需要在測試控制排程時由建構子注入 dispatcher，而不是自建 scope。

✗ `private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)`
✓ `viewModelScope.launch { ... }`

### new-scope-in-suspend · MUST · new-only · manual

`suspend` 函式內要開子 coroutine，必須用 `coroutineScope { }` 或 `supervisorScope { }`；禁止 `CoroutineScope(...).launch`（脫離父層、取消訊號傳不到）。兩個以上互相獨立的呼叫用 `async` 並行後再 `await`。

✗ `suspend fun load() { CoroutineScope(Dispatchers.IO).launch { ... } }`
✓ `suspend fun load(): Pair<A, B> = coroutineScope { val a = async { getA() }; val b = async { getB() }; a.await() to b.await() }`

### run-blocking-prod · MUST NOT · new-only+on-touch · lint:run-blocking-prod

生產程式碼禁止 `runBlocking`（阻塞執行緒、可能 ANR），包含用它把 suspend 結果同步取出。需要同步讀值時暴露 `StateFlow.value`，或把呼叫端改成 suspend。紅線 F3。

✗ `val token = runBlocking { tokenRepository.getToken() }`
✓ `val token = tokenStateFlow.value`  // 或把呼叫端改成 suspend fun

例外：測試碼一律用 `runTest` → [14-testing.md](14-testing.md)。
既有違規：30 檔 → [90-migration-ledger.md#m-08](90-migration-ledger.md)

### thread-sleep-in-coroutine · MUST NOT · new-only · manual

coroutine 或 suspend 函式內禁止 `Thread.sleep()`（阻塞整條執行緒且不可取消），一律 `delay()`。

✗ `viewModelScope.launch { Thread.sleep(300) }`
✓ `viewModelScope.launch { delay(300) }`

---

## 四、取消與例外

### swallow-cancellation · MUST NOT · new-only+on-touch · lint:swallow-cancellation

禁止 catch 掉 `CancellationException`：不得直接 `catch (e: CancellationException)`，也不得用 `catch (e: Exception)` / `catch (e: Throwable)` 包住 suspend 呼叫而不重拋。紅線 F5。

✗ `try { repository.getOrder(id) } catch (e: Exception) { showError() }`
✓ `try { repository.getOrder(id) } catch (e: CancellationException) { throw e } catch (e: ApiException) { showError() }`
✓ 或直接只捕捉具體例外型別（`ApiException` / `IOException`）

### unhandled-launch-exception · MUST · new-only · manual

`viewModelScope.launch` 內呼叫可能失敗的 suspend 函式時，必須以 try/catch 捕捉**具體例外型別**（或 Flow 的 `catch` operator）並反映到 UiState；不得讓例外靜默終結該 coroutine。

✗ `viewModelScope.launch { _uiState.value = Success(repository.getOrder(id)) }`
✓ `viewModelScope.launch { runCatchingApi { ... } }` 之類的統一處理，或 `try { ... } catch (e: ApiException) { _uiState.value = Error(e.toUiMessage()) }`

例外：錯誤模型用哪一套 → [05-data-layer.md](05-data-layer.md)。

### cpu-loop-no-ensure-active · MUST · new-only · manual

不含任何 suspend 呼叫的長迴圈（純 CPU 運算、阻塞式 API、逐檔處理）必須在迴圈內 `ensureActive()` 或檢查 `isActive`，否則取消訊號永遠不會生效。

✗ `for (item in tenThousandItems) { heavyTransform(item) }`
✓ `for (item in tenThousandItems) { ensureActive(); heavyTransform(item) }`

---

## 五、Flow 撰寫

### flow-builder-context-switch · MUST NOT · new-only · manual

`flow { }` builder 內禁止 `withContext` 或另開 coroutine 後 `emit`（違反 context preservation，runtime 會丟例外）。要換上游 context 用 `flowOn`，且 `flowOn` 只影響**它上面**的 operator；要從其他 context / callback 發射改用 `callbackFlow` / `channelFlow`。

✗ `flow { withContext(ioDispatcher) { emit(api.get()) } }`
✓ `flow { emit(api.get()) }.map { it.toDomain() }.flowOn(ioDispatcher)`  // map 與 emit 都在 ioDispatcher，下游不受影響

### flow-catch-inside-builder · MUST NOT · new-only · manual

禁止在 `flow { }` 內用 try/catch 包住 `emit`（破壞例外透明性）。上游例外一律用 `catch` operator 處理，需要降級資料時在 `catch` 內 `emit`。注意 `catch` 只看得到它上游的例外，`collect { }` lambda 內的例外要自己處理。

✗ `flow { try { emit(api.get()) } catch (e: IOException) { emit(empty) } }`
✓ `flow { emit(api.get()) }.catch { e -> emit(empty) }`

### suspend-fun-returning-flow · MUST NOT · new-only · manual

禁止宣告 `suspend fun foo(): Flow<T>`。回傳 Flow 的函式不加 `suspend`（Flow 本身是冷的，取得它不需要掛起）。

✗ `suspend fun observeOrders(): Flow<List<Order>>`
✓ `fun observeOrders(): Flow<List<Order>>`

### callbackflow-no-awaitclose · MUST · new-only · manual

`callbackFlow` / `channelFlow` 的最後一行必須是 `awaitClose { }`，並在其中反註冊 callback / listener（否則 Flow 一被取消 listener 就永久洩漏）。非 suspend 的 callback 內發射一律 `trySend()`，不得用已廢棄的 `offer()`。

✗ `callbackFlow { socket.on("msg") { offer(it) } }`  // 沒有 awaitClose，且用了 offer
✓ `callbackFlow { val l = Listener { trySend(it) }; socket.on("msg", l); awaitClose { socket.off("msg", l) } }`

### cold-flow-multi-collector · SHOULD · new-only · manual

上游是輪詢、長連線、註冊型 listener 或昂貴網路請求，且會被兩處以上 collect 時，必須在 **data 層**用 `shareIn` / `stateIn` 轉熱流共享；只有單一 collector 時維持冷 Flow。

✗ 兩個 ViewModel 各自 collect 同一個 `callbackFlow` → 開兩條 socket 連線
✓ Repository 內 `upstream.shareIn(appScope, SharingStarted.WhileSubscribed(5_000), replay = 1)`

例外：`SharingStarted` 的選擇與限制見 [08-ui-state.md#eager-sharing-started](08-ui-state.md)。

---

## 六、RxJava 收斂邊界

既有 194 檔 `io.reactivex`、209/528 個 Retrofit endpoint 回傳 Rx 型別（[90-migration-ledger.md#m-09](90-migration-ledger.md)）。與 coroutine 交界的三件事各有 owner，這裡不重述：

> Rx 型別不得出現在 domain / UI 公開簽章，只在 Repository 實作內用 `await()` / `asFlow()` 收斂 → [17-interop-views-compose.md#rx-type-crosses-boundary](17-interop-views-compose.md)
> 新程式碼不得新增 Rx → [17-interop-views-compose.md#no-new-rxjava](17-interop-views-compose.md)
> data 層新程式碼的 Rx 限制 → [05-data-layer.md#rx-in-new-data-code](05-data-layer.md)
> 既有 Rx 鏈的觸碰邊界（不要整段重寫）→ [checklists/touch-legacy-rx.md](checklists/touch-legacy-rx.md)

收斂後的 Flow 一樣受本檔規則約束：轉換出來的 Flow 若被多處 collect，套用 `cold-flow-multi-collector`；`Disposable` 的生命週期管理不屬於本檔。

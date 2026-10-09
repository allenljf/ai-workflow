# 並發模型指南

> **AI 使用說明**：排查非同步問題、執行緒切換、或狀態更新問題時參考本文件。

---

## 快速摘要

| 工具 | 使用場景 |
|------|---------|
| `viewModelScope` | ViewModel 內所有 coroutine（自動取消） |
| `APP_IO_SCOPE` | 跨頁面長效背景任務（App 生命週期） |
| `Dispatchers.IO` | 網路、DB、File I/O |
| `Dispatchers.Main` | UI 更新（viewModelScope 預設） |
| `StateFlow` | 持續 UI 狀態 |
| `SharedFlow` | 一次性事件（導航、Toast） |
| `LiveData` | 舊版 View，漸進遷移中 |

---

## Dispatcher 設定

**位置**：`app/src/main/java/com/kkday/member/di/CoroutinesScopeModule.kt`

```kotlin
val coroutinesModule = module {
    // 應用層 CoroutineScope（SupervisorJob 隔離子 coroutine 錯誤）
    single(named(APP_DEFAULT_SCOPE)) { CoroutineScope(SupervisorJob() + Dispatchers.Default) }
    single(named(APP_IO_SCOPE))      { CoroutineScope(SupervisorJob() + Dispatchers.IO) }

    // 可注入的 Dispatcher（供 UseCase 使用）
    single(named("DispatcherMain"))    { Dispatchers.Main }
    single(named("DispatcherIO"))      { Dispatchers.IO }
    single(named("DispatcherDefault")) { Dispatchers.Default }
}
```

### Dispatcher 使用時機

```
Dispatchers.IO      → 網路請求、Room 查詢、File 讀寫、SharedPreferences
Dispatchers.Main    → ViewState 更新（viewModelScope 已預設 Main）
Dispatchers.Default → CPU 密集計算（排序、解析大型 JSON）
```

---

## viewModelScope vs 應用層 Scope

### viewModelScope（最常用）

```kotlin
@KoinViewModel
class UserViewModel(...) : BaseViewModel() {

    fun getTravelGuideUrl() {
        viewModelScope.launch {  // 預設 Dispatchers.Main
            homeRepository.getTravelGuideUrl().collect { url ->
                _travelGuideLiveData.value = Uri.parse(url)  // 直接更新 UI
            }
        }
    }

    fun loadData() {
        viewModelScope.launch(Dispatchers.IO) {  // 指定切換至 IO
            val result = repository.getData()
            withContext(Dispatchers.Main) {
                _state.value = result
            }
        }
    }
}
```

**特點**：ViewModel.onCleared() 時自動取消所有 coroutine。

### 應用層 Scope（跨頁面任務）

```kotlin
@Single
class MarketplaceNotificationRepository(
    @Named(APP_IO_SCOPE) private val applicationIOScope: CoroutineScope,
    // ...
) {
    fun startPolling() {
        // 不受任何 ViewModel 生命週期影響
        applicationIOScope.launch {
            while (true) { /* 輪詢 */ }
        }
    }
}
```

**使用時機**：WebSocket 連線維護、推播處理、跨頁面狀態同步。

---

## Flow 使用模式

### BaseApiRepository 的標準 Flow 鏈

```kotlin
safeApiCall { kkApi.b2cApi.xxx.getData() }
    // BaseApiRepository 內部：
    .onStart { emit(ApiResult.loading()) }
    .catch { e -> emit(ApiResult.error(...)) }
    .onCompletion { emit(ApiResult.loaded()) }
    .flowOn(Dispatchers.IO)
```

### UseCase 的 Flow 建構

```kotlin
operator fun invoke(params: Params) = flow {
    val response = repository.suspendCall(params)  // suspend
    emit(ApiResult.success(response.data))
}
.flowOn(Dispatchers.IO)
.onStart { emit(ApiResult.loading()) }
.catch { e -> emit(ApiResult.error(ApiError("-1", e.message ?: ""), null)) }
```

### 常用 Flow Operator

| Operator | 用途 | 範例位置 |
|----------|------|---------|
| `.flowOn(Dispatchers.IO)` | 切換上游執行緒 | UseCase、BaseApiRepository |
| `.onStart { }` | 發出 Loading 狀態 | UseCase |
| `.catch { }` | 捕獲錯誤，轉為 ApiResult.Error | UseCase、DataStoreHelper |
| `.onCompletion { }` | 發出 Loaded 狀態 | BaseApiRepository |
| `.distinctUntilChanged()` | 過濾連續重複值 | MultipleProductViewModel |
| `.map { }` | 資料轉換 | DataStoreHelper |
| `.collect { }` | 終端消費（ViewModel 內） | 所有 ViewModel |

---

## StateFlow vs SharedFlow vs LiveData

### StateFlow（UI 持續狀態）

```kotlin
// 定義（ViewModel）
private val _viewState = MutableStateFlow(OrderViewState())
val viewState: StateFlow<OrderViewState> = _viewState.asStateFlow()

// 更新
_viewState.update { it.copy(isLoading = true) }

// 訂閱（Fragment/Composable）
lifecycleScope.launch {
    viewModel.viewState.collect { state -> /* 更新 UI */ }
}
```

**特性**：
- 永遠有值（`.value` 可直接讀取）
- 新訂閱者立即收到最新值
- 連續相同值只發送一次

### SharedFlow（一次性事件）

```kotlin
// 定義（ViewModel）
private val _packageGroupTabClickState = MutableSharedFlow<Int>()
val packageGroupTabClickState = _packageGroupTabClickState.asSharedFlow()

// 發送
viewModelScope.launch {
    _packageGroupTabClickState.emit(tabIndex)
}
```

**特性**：
- 無快取，新訂閱者不會收到歷史值
- 適合導航、Toast、Dialog 等一次性副作用

### Channel<Event>（側效事件，另一種模式）

```kotlin
// 定義（ViewModel）
private val _events = Channel<CancelOrderEvent>(Channel.UNLIMITED)
val events = _events.consumeAsFlow()

// 發送
_events.send(CancelOrderEvent.ShowError(message))

// 訂閱（Fragment）
lifecycleScope.launch {
    viewModel.events.collect { event -> /* 處理 */ }
}
```

### LiveData（舊版，漸進遷移）

```kotlin
// 仍存在於多個 ViewModel
private val _travelGuideLiveData: MutableLiveData<Uri?> = MutableLiveData(null)
val travelGuideLiveData: LiveData<Uri?> = _travelGuideLiveData

// 常見橋接模式：收集 Flow → 更新 LiveData
viewModelScope.launch {
    repository.getData().collect { _travelGuideLiveData.value = it }
}
```

**遷移方向**：新功能一律用 StateFlow，現有 LiveData 逐步替換（非強制立即遷移）。

---

## 常見錯誤處理模式

### withContext + try/catch

```kotlin
suspend fun initAdvertisingId() {
    withContext(Dispatchers.IO) {
        val adId = try {
            AdvertisingIdClient.getAdvertisingIdInfo(context).id ?: ""
        } catch (e: Exception) {
            FirebaseCrashlytics.getInstance().recordException(e)
            ""  // 降級處理：回傳預設值
        }
        _advertisingId.value = adId
    }
}
```

### Flow.catch（統一錯誤轉換）

```kotlin
flow { emit(repository.call()) }
    .catch { e ->
        emit(ApiResult.error(ApiError("-1", e.message ?: "unknown"), null))
    }
```

---

## 多 StateFlow 組合（ViewModel 內）

```kotlin
// MultipleProductViewModel 範例：多個獨立 State
private val _secondaryTabConfigState = MutableStateFlow<SecondaryTabConfig?>(null)
private val _packageGroupItemsState  = MutableStateFlow<List<PackageGroupItems>>(listOf())
private val _selectedPackageGroupIndex = MutableStateFlow<Int?>(null)

val secondaryTabConfigState    = _secondaryTabConfigState.asStateFlow()
val packageGroupItemsState     = _packageGroupItemsState.asStateFlow()
val selectedPackageGroupIndex  = _selectedPackageGroupIndex.asStateFlow()
```

**原則**：每個獨立關注點用獨立 StateFlow，避免一個大 State 物件頻繁整體更新。

---

*文件版本：Step 6 of AI Guide | 最後分析日期：2026-03-17*

## 相關筆記
- [02-modules](02-modules.md)
- [03-ui-patterns](03-ui-patterns.md)
- [05-networking](05-networking.md)
- [06-data-layer](06-data-layer.md)
- [checkout](features/checkout.md)
- [order-detail-compose](features/order-detail-compose.md)
- [order-success](features/order-success.md)
- [sku-activity-shell](features/sku-activity-shell.md)

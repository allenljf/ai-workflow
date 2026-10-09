# 架構模式指南

> **AI 使用說明**：分析業務邏輯或狀態管理相關問題時，優先閱讀本文件確認資料流向與錯誤處理模式。

---

## 快速摘要

| 項目 | 現況 |
|------|------|
| 整體架構 | Clean Architecture（部分實踐）|
| UI 模式 | MVI（Intent → State → UI） |
| 狀態管理 | Reductor（全域，漸進淘汰）+ StateFlow（局部，現行標準） |
| 非同步 | Coroutines + Flow（主流）|
| 錯誤處理 | `ApiResult<T>` sealed class 封裝 |

---

## 資料流向

```
UI（Fragment/Composable）
  │ sendIntent(intent)
  ↓
ViewModel（IntentChannel）
  │ viewModelScope.launch
  ↓
UseCase（@Factory，suspend / Flow）
  │ 呼叫 Repository
  ↓
Repository（BaseApiRepository.safeApiCallFlow）
  │ Retrofit Service
  ↓
API Response
  │ 封裝為 ApiResult<T>
  ↓
ViewModel 收集 Flow，更新 StateFlow<ViewState>
  │
  ↓
UI 訂閱 state，重新渲染
```

---

## ViewModel 模式

### 現行標準（StateFlow + Intent Channel）

```kotlin
@KoinViewModel
class CancelOrderViewModel(
    private val someUseCase: SomeUseCase
) : ViewModel() {

    private val _viewState = MutableStateFlow(CancelOrderViewState())
    val viewState: StateFlow<CancelOrderViewState> = _viewState.asStateFlow()

    // 一次性 UI 事件（導航、Toast）用 Channel 分開
    private val _events = Channel<CancelOrderEvent>(Channel.UNLIMITED)
    val events = _events.consumeAsFlow()

    private val intentChannel = Channel<CancelOrderIntent>(Channel.UNLIMITED)

    init { handleIntents() }

    fun sendIntent(intent: CancelOrderIntent) {
        viewModelScope.launch { intentChannel.send(intent) }
    }

    private fun handleIntents() {
        viewModelScope.launch {
            intentChannel.consumeAsFlow().collect { intent ->
                when (intent) {
                    is CancelOrderIntent.CheckPolicy -> checkCancelPolicy()
                }
            }
        }
    }
}

data class CancelOrderViewState(...)
sealed class CancelOrderIntent { ... }
sealed class CancelOrderEvent { ... }
```

**關鍵規則**：
- `StateFlow` 用於持續狀態（UI 顯示）
- `Channel<Event>` 用於一次性副作用（導航、Dialog）
- `Channel<Intent>` 用於處理 UI 輸入

### 具體 ViewModel 範例

| ViewModel | 路徑 | 特點 |
|-----------|------|------|
| `ZzimAirHomeViewModel` | `app/src/main/java/com/kkday/member/view/zzimair/home/ZzimAirHomeViewModel.kt` | StateFlow、Intent Channel、Transportation 功能 |
| `CancelOrderViewModel` | `app/src/main/java/com/kkday/member/view/order/cancel/CancelOrderViewModel.kt` | StateFlow + Event Channel 雙 Channel 標準範本 |
| `OrderViewModel` | `libs/feature/order_page/src/main/java/com/kkday/order_page/presentation/viewModel/OrderViewModel.kt` | Compose `mutableStateOf` 管理狀態、UseCase 注入 |

**Base 類別**：
- `BaseViewModel`：`shared/base/.../base/BaseViewModel.kt`
- `BaseAndroidViewModel`：帶 Application context 的基礎 ViewModel

---

## UseCase 模式

```kotlin
@Factory  // Koin：每次注入建立新實例
class GetVoucherByOrderUseCase(
    private val orderVoucherRepository: OrderVoucherRepository,
    private val persistentManager: PersistentManager
) {
    operator fun invoke(orderMid: String): Flow<ApiResult<VoucherListInfo>> = flow {
        val result = orderVoucherRepository.getVouchersByOrder(
            orderMid = orderMid,
            lang = persistentManager.getLanguage()
        )
        emit(ApiResult.success(result?.data))
    }
    .flowOn(Dispatchers.IO)
    .catch { e ->
        emit(ApiResult.error(ApiError("-1", e.message ?: ""), null))
    }
}
```

**規則**：
- 命名：`[動詞][名詞]UseCase`（例：`GetVoucherByOrderUseCase`）
- 一律用 `operator fun invoke()` 作為入口
- 回傳 `Flow<ApiResult<T>>` 或 `suspend` 函數
- `@Factory` 確保無狀態、可測試
- 只依賴 `:domain:contract` 介面（理想），或 Repository（現況技術債）

---

## Repository 模式

### BaseApiRepository.safeApiCallFlow

```kotlin
// 位於：data/networking/api/.../BaseApiRepository.kt
protected fun <T> safeApiCallFlow(
    cacheBehavior: CacheBehavior = CacheBehavior.NONE,
    apiCall: suspend () -> T
): Flow<ApiResult<T>> = flow {
    emit(ApiResult.Loading())
    // 快取策略處理
    // Retry 邏輯
    val response = apiCall()
    emit(ApiResult.success(response))
}
.catch { e ->
    when (e) {
        is HttpException -> emit(ApiResult.Error(parseHttpError(e)))
        else -> emit(ApiResult.Error(ApiError("-1", e.message)))
    }
}
```

**提供的能力**：
- `CacheBehavior` 快取控制
- 自動 Retry（RetryPolicy）
- HttpException → ApiError 轉換
- System Upgrade 回應碼處理

---

## 錯誤處理：ApiResult<T>

**位置**：`data/model/.../ApiResult.kt`

```kotlin
sealed class ApiResult<T> {
    data class Success<T>(val data: T?, val metadata: Metadata? = null) : ApiResult<T>()
    data class Error<T>(val apiError: ApiError, val data: T? = null) : ApiResult<T>()
    class Loading<T> : ApiResult<T>()
    data class Upgrade<T>(val systemUpgrade: SystemUpgrade?) : ApiResult<T>()
    class Loaded<T> : ApiResult<T>()
}
```

**ViewModel 中的標準處理**：

```kotlin
viewModelScope.launch {
    someUseCase(params).collect { result ->
        when (result) {
            is ApiResult.Loading -> _viewState.update { it.copy(isLoading = true) }
            is ApiResult.Success -> _viewState.update { it.copy(data = result.data, isLoading = false) }
            is ApiResult.Error   -> _viewState.update { it.copy(error = result.apiError, isLoading = false) }
            is ApiResult.Upgrade -> _events.send(Event.ShowUpgradeDialog(result.systemUpgrade))
            else -> {}
        }
    }
}
```

---

## Reductor（全域狀態，漸進淘汰）

**用途**：管理全域 App 狀態（登入、通知等跨頁面共用狀態）

```
Store<AppState>
  ├── dispatch(Action) → Reducer → new AppState
  └── Reducer 內可觸發 EpicCommands（副作用，類似 Redux-Saga）
```

**主要檔案**：
- Actions：`app/src/main/java/com/kkday/member/reducer/order/OrderActions.kt`
- Reducer：`app/src/main/java/com/kkday/member/reducer/order/OrderReducer.kt`
- DI 模組：`app/src/main/java/com/kkday/member/di/actionModule.kt`

**新功能不應使用 Reductor**，改用 StateFlow 局部狀態。

---

## 技術債與遷移現況

| 問題 | 影響範圍 | 方向 |
|------|---------|------|
| `:domain:usecase` 直接依賴 `:data:repository` | 違反 Clean Architecture 純粹性 | 新增時只依賴 `:domain:contract` |
| Reductor 全域狀態 | ~30 個 legacy 功能模組 | 逐步改為 StateFlow 局部狀態 |
| 混用 Compose State + StateFlow + LiveData | 維護成本高 | 新功能統一用 StateFlow |

---

*文件版本：Step 2 of AI Guide | 最後分析日期：2026-03-17*

## 相關筆記
- [03-ui-patterns](03-ui-patterns.md)
- [05-networking](05-networking.md)
- [06-data-layer](06-data-layer.md)
- [checkout](features/checkout.md)
- [home](features/home.md)
- [order-detail-compose](features/order-detail-compose.md)
- [order-success](features/order-success.md)
- [sku-activity-shell](features/sku-activity-shell.md)

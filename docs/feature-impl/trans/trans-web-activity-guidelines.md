# TransWeb 架構指南

## 概述

TransWeb 架構由三個主要元件組成，這些元件遵循 MVVM（Model-View-ViewModel）模式來處理 KKday 應用程式中與交通運輸網頁相關的功能：

1. `TransWebActivity` - 視圖（View）元件
2. `TransWebViewModel` - 視圖模型（ViewModel）元件
3. `TransGetBookingDataUseCase` - 模型/業務邏輯（Model/Business Logic）元件

## 元件關係

```
┌───────────────────┐     ┌──────────────────────┐     ┌─────────────────────────────┐
│                   │     │                      │     │                             │
│  TransWebActivity │────►│  TransWebViewModel   │────►│  TransGetBookingDataUseCase │
│    (View)         │     │  (ViewModel)         │     │  (Business Logic)           │
│                   │◄────│                      │◄────│                             │
└───────────────────┘     └──────────────────────┘     └─────────────────────────────┘
```

## 1. TransWebActivity

**角色**：作為 MVVM 架構中的視圖層。

**主要職責**：
- 渲染交通運輸服務的 WebView
- 處理導航和工具欄設置
- 管理 WebView 配置和交互
- 處理深層連結和支付 URL
- 觀察 ViewModel 狀態並相應地更新 UI

**導航**：與 `TransHomeActivity` 協同工作，支援各種交通運輸服務類型（如 Thsrtw、RailEurope、KosokuBus 等）

## 2. TransWebViewModel

**角色**：作為 ViewModel 層，連接視圖與業務邏輯。

**主要職責**：
- 處理來自視圖的意圖（Intent）
- 使用 Kotlin Flow 維護 UI 狀態
- 通過 UseCase 獲取預訂數據
- 處理令牌（Token）管理
- 處理交通運輸訂單信息
- 向視圖提供狀態更新

**狀態管理**：使用 `MutableStateFlow` 發出視圖狀態，如 `Idle`、`Loading` 和數據狀態。

## 3. TransGetBookingDataUseCase

**角色**：實現獲取交通運輸預訂數據的業務邏輯。

**主要職責**：
- 與交通運輸 API 存儲庫通信
- 將 API 響應轉換為領域模型
- 處理不同交通運輸類型的數據轉換
- 處理預訂訂單並將其轉換為 `OrderSpecificationData`
- 管理錯誤處理和加載狀態

**數據流**：遵循基於 Flow 的響應式模式進行異步操作。

## 整合點

- **WebView JavaScript 接口**：TransWeb 元件與 `JavascriptInterfaceUtil` 整合，實現網頁-應用通信
- **深層連結**：使用 `WebDeepLinkHelper` 處理指向各種交通運輸服務的深層連結
- **支付處理**：處理支付 URL 並與支付流程整合
- **路由註解**：使用 `@Router` 註解進行應用內導航

## 使用示例

- 加載交通運輸網頁並正確認證
- 處理來自網頁界面的預訂數據
- 處理交通運輸服務之間的重定向
- 將網頁預訂數據轉換為應用原生格式

## WebView 與支付流程詳解

### 從 WebView 呼叫 getBookingData 到支付頁面的完整流程

本節詳細介紹從 WebView 中獲取預訂數據到進入支付頁面的完整流程。

#### 1. WebView JavaScript 與原生應用通信

```
┌─────────────┐     ┌────────────────────┐     ┌────────────────────┐
│  WebView    │────►│JavascriptInterface │───► │ TransWebActivity   │
│ (網頁內容)   │     │  (通信橋接層)        │     │  (原生Activity)     │
└─────────────┘     └────────────────────┘     └────────────────────┘
```

- **初始化**：在 `TransWebActivity` 的 `onCreate()` 方法中使用 `JavascriptInterfaceUtil.initialize(this)` 初始化 JavaScript 介面。
- **通信機制**：網頁端通過 JavaScript 調用 `android.getBookingData(bookingOrderId)` 方法觸發原生端處理。
- **參數傳遞**：預訂訂單 ID (bookingOrderId) 從網頁傳遞到原生應用。

#### 2. 獲取預訂數據流程

```
┌────────────────────┐     ┌────────────────────────┐     ┌───────────────────────────────┐
│ TransWebActivity   │────►│ TransWebViewModel      │────►│ TransGetBookingDataUseCase    │
│ (接收API請求)       │     │ (處理請求並管理狀態)      │     │ (執行API呼叫並轉換數據)          │
└────────────────────┘     └────────────────────────┘     └───────────────────────────────┘
                                                                    │
                                                                    ▼
                                                        ┌──────────────────────────────┐
                                                        │ TransApiRepository           │
                                                        │ (與後端API通信)                │
                                                        └──────────────────────────────┘
```

1. **接收請求**：`TransWebActivity` 接收來自 WebView 的 `getBookingData` 請求，其中包含預訂訂單 ID。

2. **發送意圖**：Activity 創建 `ViewIntent.GetBookingData` 意圖並發送給 ViewModel：
   ```kotlin
   viewModel.fetchIntent.send(ViewIntent.GetBookingData(
       context = this,
       type = transportationType,
       bookingOrderId = orderId, 
       // ...其他參數
   ))
   ```

3. **處理意圖**：`TransWebViewModel` 在 `handleIntent()` 方法中處理意圖：
   ```kotlin
   private fun handleIntent() {
       viewModelScope.launch {
           fetchIntent.consumeAsFlow().collect {
               when (it) {
                   is ViewIntent.GetBookingData -> getBookingData(
                       it.context,
                       it.type,
                       it.bookingOrderId,
                       // ...其他參數
                   )
                   // ...其他意圖處理
               }
           }
       }
   }
   ```

4. **呼叫 UseCase**：ViewModel 調用 `TransGetBookingDataUseCase` 獲取預訂數據：
   ```kotlin
   private fun getBookingData(context: Context, type: TransportationType, bookingOrderId: String, ...) {
       viewModelScope.launch {
           useCase(TransGetBookingDataUseCase.Parameters(...)).collect { apiResult ->
               when (apiResult) {
                   is ApiResult.Error -> _state.value = ViewState.Error(...)
                   is ApiResult.Loading -> _state.value = ViewState.Loading
                   is ApiResult.Success -> apiResult.result?.let {
                       _thsrOrderState.value = it
                   }
                   // ...
               }
           }
       }
   }
   ```

5. **API 呼叫與數據轉換**：`TransGetBookingDataUseCase` 向 `TransApiRepository` 發起請求並處理回應：
   ```kotlin
   override suspend fun execute(parameters: Parameters): Flow<ApiResult<OrderSpecificationData>> {
       return flow {
           val result = apiRepository.getBookingData(
               lang = sharedPreferencesHelper.getLanguage(),
               token = sharedPreferencesHelper.getAccessToken(),
               bookingOrderId = parameters.bookingOrderId,
               // ...其他參數
           )
           
           when {
               !result.metadata.isResultSuccess -> throw Exception(...)
               else -> {
                   val orderData = convertToOrderSpecificationData(...)
                   emit(ApiResult.success(orderData))
               }
           }
       }
       .onStart { emit(ApiResult.loading()) }
       .catch { e -> emit(ApiResult.error(e)) }
   }
   ```

6. **數據格式轉換**：UseCase 負責將 API 返回的數據轉換為 `OrderSpecificationData` 格式，適用於下一步的支付流程。

#### 3. 進入支付頁面

```
┌───────────────────┐     ┌───────────────────────────┐     ┌─────────────────────────┐
│ TransWebActivity  │────►│ OrderFormFillingActivity  │────►│ Booking & Payment Flow  │
│ (觀察狀態變化)      │     │ (訂單填寫與支付入口)         │     │ (支付流程處理)            │
└───────────────────┘     └──────────────────────  ───┘     └─────────────────────────┘
```

1. **觀察狀態變化**：`TransWebActivity` 使用 `Flow` 監聽 `thsrOrderState` 的變化：
   ```kotlin
   private fun initObservers() {
       viewModel.thsrOrderState
           .filterNotNull()
           .onEach { orderData ->
               // 確保只啟動一次支付流程
               if (!viewModel.paymentLaunched) {
                   // ...
                   launchOrderFormFilling(orderData)
               }
           }
           .launchIn(lifecycleScope)
   }
   ```

2. **啟動支付頁面**：當獲取到有效的訂單數據後，啟動 `OrderFormFillingActivity`：
   ```kotlin
   private fun launchOrderFormFilling(orderData: OrderSpecificationData) {
       OrderFormFillingActivity.launch(
           context = this,
           productId = orderData.productId,
           // ...必要參數
           transBookingData = orderData
       )
       
       // 關閉當前 Activity
       finish()
   }
   ```

3. **處理支付流程**：`OrderFormFillingActivity` 接收訂單數據，處理用戶填寫的表單信息，並最終進入支付流程。

#### 4. 錯誤處理與恢復機制

- **異常處理**：在數據獲取過程中，各層都有錯誤處理邏輯，例如：
  - UseCase 層使用 `catch` 捕獲異常並轉換為 `ApiResult.error`
  - ViewModel 層將錯誤狀態通過 `_state.value = ViewState.Error(...)` 傳遞給 UI
  - Activity 層顯示適當的錯誤提示並提供重試機制

- **狀態恢復**：如果應用在支付過程中被終止，`TransWebActivity` 會在重新啟動時檢查參數和 URI 數據，確保支付流程可以繼續。
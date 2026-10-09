# 取消訂單 技術文件

> 自動產生 | 最後更新：2026-03-19

---

## 概述

- **所在 Module**：`:app`
- **UI 入口**：`CancelOrderActivity.kt`
- **功能描述**：訂單取消流程頁面，讓使用者填寫取消原因（含其他原因文字輸入）並送出取消申請，支援一般訂單與多種交通類型（機場接送、JR 鐵路、遊輪、租車等）的差異化取消政策顯示，送出後導向取消成功頁。

---

## 檔案清單

```
UI（使用者介面入口）
 ├─ CancelOrderActivity.kt           → app/src/main/java/com/kkday/member/view/order/cancel/
 ├─ CancelOrderMvpView.kt            → app/src/main/java/com/kkday/member/view/order/cancel/
 ├─ CancelOrderStateHelper.kt        → app/src/main/java/com/kkday/member/view/order/cancel/
 └─ CancelOrderSuccessActivity.kt    → app/src/main/java/com/kkday/member/view/order/cancel/success/

ViewModel（機場接送訂單專用狀態管理）
 └─ CancelOrderViewModel.kt          → app/src/main/java/com/kkday/member/view/order/cancel/

Presenter / Reducer（一般訂單 MVP + Reductor 狀態機）
 ├─ CancelOrderPresenter.kt          → app/src/main/java/com/kkday/member/view/order/cancel/
 ├─ CancelOrderActions.kt            → app/src/main/java/com/kkday/member/reducer/order/
 └─ CancelOrderReducer.kt            → app/src/main/java/com/kkday/member/reducer/order/

Data（資料層）
 └─ TransportationRepository.kt      → app/src/main/java/com/kkday/member/view/transportation/repository/

Network（API）
 └─ KKdayService.kt                  → app/src/main/java/com/kkday/member/network/retrofit/
    - GET  v2/order/{order_mid}/cancellation         （舊版訂單取消資料）
    - GET  v2/new_order/{order_mid}/cancellation     （新版訂單取消資料）
    - PUT  v2/order/{order_mid}/cancellation         （送出取消申請）
    - POST transportation/checkCancelPolicy           （機場接送取消政策查詢）
```

---

## 資料流

### 主流程：頁面載入（一般訂單）

```
UI（CancelOrderActivity）
 │  onCreate() → cancelOrderPresenter.viewReady(orderId, isNewProductOrder)
 │
 ↓
Presenter（CancelOrderPresenter）
 │  store.dispatch(cancelOrderActions.viewReady(orderId, isNewProductOrder))
 │
 ↓
Reducer（CancelOrderReducer.viewReady）
 │  根據 isNewProductOrder 選擇 API：
 │  - true  → NetworkApi.getOrderCancellation(orderId)        GET v2/new_order/{id}/cancellation
 │  - false → NetworkApi.getOldProductOrderCancellation(orderId) GET v2/order/{id}/cancellation
 │
 ↓
後端 API
```

### 回傳流（一般訂單）

```
後端 API
 ↓
Reducer（getOrderCancellationResult）：Response<OrderCancellation> → AppState.orderCancellation
 ↓
Presenter（observes AppState）：combineLatest(summary, orderCancellation, cancelPolicyInfoRule)
 ↓
UI（CancelOrderMvpView.updateData）：依 TransportationType 分支渲染取消政策、退款摘要、原因選擇器
```

### 送出取消申請

```
UI（CancelOrderActivity）
 │  textCancel 按鈕點擊 → cancelOrderPresenter.clickCancelButton(orderId, cancelReasonViewInfo)
 │
 ↓
Presenter（CancelOrderPresenter）
 │  store.dispatch(cancelOrderActions.clickCancelButton(orderId, cancelReason))
 │
 ↓
Reducer（CancelOrderReducer.clickCancelButton）
 │  NetworkApi.cancelOrder(orderId, CancelOrderData(reasonId, description, lang))
 │  PUT v2/order/{order_mid}/cancellation
 │
 ↓
後端 API
 ↓
Reducer（cancelOrderResult）：
 - 成功 → AppState.showSuccessDialog = true，清空 orderList
 - 失敗 → AppState.showFailDialog = true
 - 無網路 → AppState.showNetworkUnavailableError = true
 ↓
UI：showSuccessDialog(true) → 導向 CancelOrderSuccessActivity
```

### 機場接送取消政策載入（ViewModel 分支）

```
UI（CancelOrderActivity）
 │  updateData() 判斷 TransportationType == PICK_UP / DROP_OFF 且 cancelPolicyCheckResponse == null
 │  → viewModel.sendIntent(CancelOrderIntent.InitializeWithAirportData(...))
 │
 ↓
ViewModel（CancelOrderViewModel）
 │  handleInitializeWithAirportData() → checkCancelPolicy(tradeNo)
 │  transportationRepository.checkCancelPolicy(JsonWrapper(BookingOrderMidRequest))
 │
 ↓
TransportationRepository
 │  kkApi.b2cApi.transportation.checkCancelPolicy<CancelPolicyCheckResponse>(request)
 │
 ↓
後端 API（交通 API）
 ↓
ViewModel：ApiResult.Success → 轉換 AirportCancelReason → OrderCancelReason，轉換 RefundInfo → CancelPolicyInfo
 → _events.send(CancelOrderEvent.UpdateDataWithCancelPolicy)
 ↓
UI：observeViewModelEvents() 收到 event → updateData(..., cancelPolicyCheckResponse) → updateAirportCancelPolicy()
```

---

## 逐層說明

### UI 層

`CancelOrderActivity` 同時實作 `CancelOrderMvpView` 並注入 `CancelOrderPresenter`（MVP）與 `CancelOrderViewModel`（機場接送用）。

- `onCreate()`：初始化 Presenter、觀察 ViewModel events、初始化退款摘要 View
- `updateData()`：依 `TransportationType` 分支渲染不同取消政策 UI（一般、機場接送、JR 鐵路、遊輪、租車等）
- `CancelOrderStateHelper`：持有 `CancelReasonViewInfo` 狀態，監聽原因選擇與文字輸入，控制取消按鈕的 enabled 狀態
- 兩種啟動方式：`CancelOrderRoutingInput`（由 MVP 請求 API 取資料）或 `CancelOrderRoutingWithDataInput`（直接傳入資料，機場接送用）

### ViewModel 層

`CancelOrderViewModel` 採用 MVI 架構（Intent/State/Event），僅用於機場接送訂單的取消政策查詢：
- `StateFlow<CancelOrderViewState>`：持有頁面狀態（含 isLoading）
- `Channel<CancelOrderEvent>`：One-shot 事件，發送給 Activity 更新 UI
- `Channel<CancelOrderIntent>`：接收 UI 送出的 intent

### Presenter 層

`CancelOrderPresenter` 繼承 `RxBasePresenter`，透過 RxJava `combineLatest` 觀察 Reductor `AppState` 中的三個 stream（summary、orderCancellation、cancelPolicyInfoRule），有任一變動即呼叫 `mvpView.updateData()`。

### Reducer 層

`CancelOrderReducer` 為 Reductor `@AutoReducer`，處理 VIEW_READY（觸發 API 請求）、GET_CANCEL_ORDER_DATA_RESULT（寫入 AppState）、CLICK_CANCEL_BUTTON（觸發取消 API）、CANCEL_ORDER_RESULT（更新對話框狀態）四個 Action。

### Repository 層

`TransportationRepository` 直接放在 `app` 模組的 `view/transportation/repository/` 目錄，繼承 `BaseApiRepository`，透過 `KKApi.b2cApi.transportation` 呼叫交通相關 API（含 `checkCancelPolicy`）。

### API 層

| Endpoint | 方法 | 說明 |
|----------|------|------|
| `v2/order/{order_mid}/cancellation` | GET | 取舊版訂單取消資料（含可選原因、退款政策） |
| `v2/new_order/{order_mid}/cancellation` | GET | 取新版訂單取消資料 |
| `v2/order/{order_mid}/cancellation` | PUT | 送出取消申請，Body 含 reasonId、description、lang |
| transportation `checkCancelPolicy` | POST | 機場接送取消政策查詢，Body 含 tradeNo |

---

## View 方法清單

| 方法 | 說明 |
|------|------|
| `onCreate()` | 初始化 Toolbar、Presenter、ViewModel 觀察、退款摘要 View；若為 `withDataInput` 模式直接 render 資料 |
| `observeViewModelEvents()` | 收集 `viewModel.events`，處理 `UpdateDataWithCancelPolicy` 事件（機場接送用） |
| `onSaveInstanceState()` | 儲存 `CancelOrderRoutingInput` 以支援 Activity 重建 |
| `restoreFromSaveInstance()` | 從 savedInstanceState 或 Intent 還原 input |
| `onBackPressed()` | 返回並套用 slideOutRight 動畫 |
| `onDestroy()` | 關閉所有 Dialog、detach Presenter |
| `initPaymentSummaryView()` | 初始化退款摘要標題（一般 vs. 現場付款模式文案不同） |
| `updateToolbar()` | 設定 Toolbar 標題與返回按鈕 |
| `onCancelOrderClickListener()` | 顯示 loading dialog 並呼叫 Presenter 送出取消 |
| `updateData()` (MvpView impl) | 依 `TransportationType` 分支更新取消政策、退款摘要、選擇原因 UI |
| `updateOrderTitle()` | 控制商品標題區塊顯示/隱藏 |
| `updateOrderSummary()` | 更新商品圖、名稱、套餐名稱 |
| `updateReason()` | 初始化取消原因下拉選擇器與其他原因文字輸入框 |
| `updatePolicy()` | 渲染一般取消政策（含 KK 點數退款資訊） |
| `updatePaymentSummary()` | 渲染退款金額摘要（含折扣、KK 點數、取消費、退款額） |
| `updateRoyalCruisesPolicy()` | 遊輪類型的取消政策（Compose View） |
| `updateZzimairPolicy()` | 機票類型的取消政策 |
| `updateRentalCarsPolicy()` | 租車類型的取消政策 |
| `updateJrRailPolicy()` | JR 鐵路的取消政策（Compose JRCancelRuleView） |
| `updateAirportCancelPolicy()` | 機場接送取消政策（Compose CancellationPolicyItem） |
| `updateCancelButton()` | 設定「保留」/「取消訂單」按鈕行為 |
| `showSuccessDialog()` | 顯示成功 Dialog 並延遲導向 CancelOrderSuccessActivity |
| `showFailDialog()` | 顯示失敗 Dialog |
| `getDefaultCancelInfoList()` | 計算預設注意事項清單（依付款類型與 KK 點數使用情況） |

---

## ViewModel 方法清單

| 方法 | 說明 |
|------|------|
| `init` | 啟動 `handleIntents()` 協程，持續消費 intentChannel |
| `sendIntent()` | 從 UI 送入 Intent，透過 Channel 傳遞 |
| `handleIntents()` | 消費 intentChannel，分派至對應 handler |
| `handleInitializeWithAirportData()` | 更新 ViewState 並呼叫 `checkCancelPolicy()` |
| `checkCancelPolicy()` | 呼叫 `TransportationRepository.checkCancelPolicy()`，將結果轉換後送出 Event |
| `convertAirportCancelReasonToOrderCancelReason()` | 將機場取消原因轉換為通用取消原因格式 |
| `convertRefundInfoToCancelPolicyInfo()` | 將機場退款資訊轉換為通用取消政策格式（private） |

---

## 業務邏輯摘要

- **新舊訂單二分**：`isNewProductOrder` 決定呼叫哪個取消資料 API（`v2/new_order` 或 `v2/order`）
- **機場接送特殊流程**：機場接送（PICK_UP / DROP_OFF）不呼叫主站取消資料 API（`dispatchViewReady = false`），改由 ViewModel 呼叫交通 API 的 `checkCancelPolicy` 取得取消政策與退款資訊
- **取消按鈕啟用條件**：`CancelOrderStateHelper.isCancelReasonInfoRequiredFilled()` 為 true 時才啟用，規則：選擇「其他」原因需同時填寫文字說明
- **取消原因 `REASON_OTHER`**：當選擇此 reasonId 時顯示文字輸入框
- **`withDataInput` 直接渲染模式**：機場接送或特定情境下，資料直接透過 `CancelOrderRoutingWithDataInput` 傳入，無需等待 Presenter 的 API 回應
- **送出取消後清空訂單列表**：取消成功後 Reducer 將 AppState 中的 orderList 清空，回到訂單列表時重新呼叫 API
- **錯誤處理**：無網路 → `showNetworkUnavailableError`；API 非 200 或非 success status → `showFailDialog`
- **ViewModel 錯誤處理**：機場接送 `checkCancelPolicy` API 失敗時只將 `isLoading` 置為 false，不顯示錯誤 UI（silent fail）

---

## 已知技術債

- `TransportationRepository` 放在 `app/.../view/transportation/repository/`，未遵循 Clean Architecture 分層（應在 `:data:repository` 實作 `:domain:contract` 介面）
- `CancelOrderViewModel` 與 `CancelOrderPresenter` 並存同一頁面，混用 MVP+Reductor 與 MVI+ViewModel 兩種模式，增加理解成本
- `CancelOrderReducer` 直接依賴 `NetworkApi.sharedInstance()`（singleton），未透過 Repository/UseCase 注入，違反依賴反轉原則
- 機場接送的 `convertRefundInfoToCancelPolicyInfo()` 中多個欄位硬編碼預設值（`percent = null`、`beginDate = null` 等），轉換不完整

## 相關筆記
- [01-architecture](../01-architecture.md)
- [02-modules](../02-modules.md)
- [03-ui-patterns](../03-ui-patterns.md)
- [05-networking](../05-networking.md)
- [06-data-layer](../06-data-layer.md)
- [07-concurrency](../07-concurrency.md)
- [order-detail-compose](order-detail-compose.md)
- [repayment](repayment.md)
- [sku-activity-shell](sku-activity-shell.md)

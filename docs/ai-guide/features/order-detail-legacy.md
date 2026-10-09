# 舊版訂單詳情 技術文件

> 自動產生 | 最後更新：2026-03-19

---

## 概述

- **所在 Module**：`:app`
- **UI 入口**：`OrderDetailActivity.kt` → `OrderDetailFragment.kt`
- **功能描述**：顯示單一訂單的完整詳情，支援新版商品（`v2/new_order`）與舊版商品（`v2/order`）兩種 API 路徑，並提供憑證、重新付款、取消訂單、導覽員聯絡、eSIM、推薦卡等附加功能。

---

## 檔案清單

```
UI（使用者介面入口）
 ├─ OrderDetailActivity.kt         → app/.../view/order/detail/
 └─ OrderDetailFragment.kt         → app/.../view/order/detail/order/

ViewModel（UI 狀態管理）
 └─ OrderDetailViewModel.kt        → app/.../view/order/detail/order/

Presenter（Reductor MVP 橋接）
 ├─ OrderDetailPresenter.kt（Activity 層）  → app/.../view/order/detail/
 └─ OrderDetailPresenter.kt（Fragment 層）  → app/.../view/order/detail/order/

Reductor（狀態機）
 ├─ OrderDetailActions.kt          → app/.../reducer/order/
 └─ OrderDetailReducer.kt          → app/.../reducer/order/

Domain（業務邏輯 UseCase）
 ├─ GetBarcodesResultUseCase.kt     → libs/feature/order_page/.../domain/useCase/
 ├─ UpdateOrderPaymentFailedUseCase.kt → app/.../view/order/domain/usecase/
 ├─ CheckCanOrderRepayUseCase.kt    → app/.../view/repay/domain/useCase/
 └─ GetPaymentResultUseCase.kt      → app/.../view/repay/domain/useCase/

Data（資料層）
 ├─ OrderRepository.kt（類別，非介面）  → libs/feature/order_page/.../domain/repository/
 └─ TransportationRepository.kt        → app/.../view/transportation/repository/

Network（API 定義）
 ├─ IOrderApiService.kt（新版 Retrofit）  → libs/networking/api/.../service/order_api/
 └─ KKdayService.kt（舊版 Retrofit）      → app/.../network/retrofit/

舊版網路封裝
 ├─ Api.kt（介面）       → app/.../network/
 ├─ NetworkApi.kt（Singleton） → app/.../network/
 └─ RetrofitApi.kt（實作）     → app/.../network/retrofit/
```

---

## 資料流

### 主流程：頁面載入 / 訂單資料取得

```
OrderDetailActivity
 │  onCreate()：presenter.attachView(this)
 │              presenter.viewReady(orderId)
 │  → dispatch: ORDER_DETAIL_ACTIVITY_VIEW_READY
 │  → Reducer 判斷 isNewProductOrder
 │     若訂單不在列表中：先呼叫 NetworkApi.judgmentOrder(orderId)
 ↓
OrderDetailFragment.onViewCreated()
 │  orderDetailPresenter.attachView(this)
 │  orderDetailPresenter.viewReady(orderId)
 │  → dispatch: VIEW_READY（ORDER_DETAIL_VIEW_READY）
 ↓
OrderDetailReducer.viewReady()
 │  依 isNewProduct 選擇：
 │    新版：dispatch GET_ORDER_DETAIL
 │    舊版：dispatch GET_OLD_ORDER_DETAIL
 ↓
OrderDetailReducer.getOrderDetail() / getOldOrderDetail()
 │  呼叫：NetworkApi.sharedInstance().getOrderDetail(orderId)
 │        NetworkApi.sharedInstance().getOldOrderDetail(orderId)
 ↓
RetrofitApi → KKdayService（Retrofit）
 │  新版：GET v2/new_order/{order_id}?lang=<lang>
 │  舊版：GET v2/order/{order_id}?lang=<lang>
 ↓
後端 API

── 並行路徑（ViewModel MVVM）──
OrderDetailFragment.initAction()
 │  viewModel.checkCanOrderRepay(orderMasterMid)
 │    → CheckCanOrderRepayUseCase → IOrderApiService
 │  viewModel.getPaymentResult(orderMasterMid)
 │    → GetPaymentResultUseCase → IOrderApiService
 │  viewModel.fetchBarcodeInfo(orderId)  ← 若 shouldCallBarcodes=true
 │    → GetBarcodesResultUseCase + ESimDcsRepository（async/await 並發）
```

### 回傳流

```
後端 API
 │  Response<OrderDetailInfo> / Response<OldOrderDetailInfo>
 ↓
OrderDetailReducer.getOrderDetailResult()
 │  網路錯誤：state.setShowNetworkUnavailableError(true)
 │  404：state.setIsNotFoundOrder(true)
 │  成功：state.setOrderDetail(response.data)
 │        state.setOrderStatusInfoByOrderId(orderId, summary)
 ↓
AppState（Reductor Store）廣播更新
 ↓
OrderDetailPresenter.register()
 │  Observables.combineLatest(
 │    orderDetail, allOrderVouchers, allBarcodes,
 │    languageType, googleServiceAvailable,
 │    nationalitiesData, driverCallAvailableTime, conversationData
 │  ) → mvpView.updateOrderDetail(...)
 ↓
OrderDetailFragment.updateOrderDetail()（實作 OrderDetailMvpView）
 │  呼叫：viewModel.updateOrderDetailAdapterData(...)
 │  → _orderDetailAdapterData (LiveData) 更新
 ↓
observeData() 中觀察 orderDetailAdapterData
 │  orderDetailAdapter.updateData(...)
 └─ 成功：RecyclerView 渲染訂單詳情各 Delegate 卡片
    網路錯誤：showError(true, false)
    404：showError(false, true)
```

---

## 逐層說明

### UI 層

`OrderDetailActivity` 作為殼頁，內嵌 `OrderDetailFragment`（新版商品）或 `OldOrderDetailFragment`（舊版商品的更舊版本，位於 `old/` 目錄）。
Fragment 在 `onViewCreated()` 時通過 `orderDetailPresenter.viewReady(orderId)` 啟動 Reductor 資料流。同時在 `initAction()` 中並行啟動 ViewModel 的重新付款檢查與支付摘要取得（MVVM 路徑）。
`observeData()` 通過 LiveData / StateFlow 觀察：訂單詳情資料、重新付款狀態、Barcode/eSIM 資料、推薦卡。

### ViewModel 層

採用 MVVM 架構，管理以下獨立狀態：
- `viewState: StateFlow<ViewState>`：Loading 狀態
- `orderDetailAdapterData: LiveData<OrderDetailAdapterData>`：整合後的 Adapter 資料（由 Presenter 呼叫 ViewModel 方法寫入）
- `checkCanRepayInfo: LiveData<CheckCanOrderRepayResult>`：重新付款可行性
- `repayPaymentSummary: LiveData<PaymentResult>`：支付摘要
- `barcodeInfo: LiveData<BarcodeInfo>`：Barcode + eSIM 資料
- `transCheckCancelable: LiveData<...>`：交通訂單取消可行性
- `transRebookData: LiveData<...>`：交通訂單重新訂位資料

### Presenter / Reducer 層（主資料流）

使用 Reductor（Redux-like）架構，兩層 Presenter 分工：
- **Activity Presenter**：判斷 `isNewProductOrder`，管理頁面生命週期相關 Action
- **Fragment Presenter**：`register()` 訂閱多個 `AppState` slice，以 RxJava `combineLatest` 組合後推送 View

`OrderDetailReducer` 直接呼叫 `NetworkApi.sharedInstance()`（舊版全域 Singleton），未走 domain/contract Repository 介面。

### Repository 層

- `OrderRepository`（`libs/feature/order_page`）：Coroutine suspend 函式，使用 `IOrderApiService`，包含 `getOrderDetail`、`checkCanOrderRepay`、`getPaymentResultByOrderMId`、`getTransCheckCancelable`、`getBookingSuccessRecommendCard` 等
- `TransportationRepository`：負責交通相關資料，包含 `getTransMiscInfo`、`getTransSearchParams`、`getOrderDetail`（機場訂單）
- 舊版 Reductor 主流程直接呼叫 `NetworkApi`，不使用上述 Repository

### API 層

| Endpoint | HTTP | 用途 |
|----------|------|------|
| `v2/new_order/{order_id}` | GET | 取得新版訂單詳情（`OrderDetailInfo`） |
| `v2/order/{order_id}` | GET | 取得舊版訂單詳情（`OldOrderDetailInfo`） |
| `v2/order/{order_mid}/repay/check` | GET | 檢查重新付款可行性 |
| `v2/order/{order_mid}/payment_result` | GET | 取得支付摘要 |
| `v2/order/{order_mid}/barcodes` | GET | 取得 Barcode/QR Code 資料 |
| `v2/order/trans/check_cancelable` | GET | 檢查交通訂單取消可行性 |
| `v2/recommend/order/after_confirm` | POST | 取得訂單後推薦卡 |

---

## View 方法清單

| 方法 | 說明 |
|------|------|
| `onViewCreated()` | 附加 Presenter、呼叫 `viewReady(orderId)` 啟動資料載入 |
| `onResume()` | 頁面重新可見時觸發 KTM 追蹤事件 |
| `onDestroyView()` | 清除 ScrollListener、釋放機場待付款計時器、Presenter detach |
| `onDestroy()` | 關閉 deepLinkErrorDialog、accessAudioBlockedDialog |
| `initView()` | 初始化 Toolbar、RecyclerView（StaggeredGridLayout，2欄）及 ItemDecoration |
| `initAction()` | 啟動重新付款檢查、支付摘要查詢、Barcode 查詢（並行 ViewModel 路徑） |
| `observeData()` | 訂閱所有 LiveData/StateFlow，驅動 RecyclerView 及各 UI 狀態更新 |
| `setOnFlipListener()` | 設定翻轉動畫回呼（外部注入） |

---

## ViewModel 方法清單

| 方法 | 說明 |
|------|------|
| `init` | 啟動 `observePushNotification()`、`triggerTrackingESimSupportWarning()` |
| `updateOrderDetailAdapterData()` | 整合訂單詳情、憑證、Barcode 等資料，更新 `_orderDetailAdapterData` |
| `updateBarcodeData()` | 僅更新 barcodes 與 eSIM 欄位（局部更新） |
| `checkCanOrderRepay()` | 呼叫 `CheckCanOrderRepayUseCase`，結果寫入 `_checkCanRepayInfo` |
| `getPaymentResult()` | 呼叫 `GetPaymentResultUseCase`，解析訂單列表與交通類型 |
| `fetchBarcodeInfo()` | 並發取得 Barcode、eSIM 說明、eSIM 一鍵安裝資料 |
| `getMiscInfo()` | 為 JR Rail 訂單取得額外雜項資訊（車廂樣式、警告標籤） |
| `setOrderDetailInfo()` | 首次取得有效訂單資料時設定 KTM 追蹤屬性並觸發 PageLoad 事件 |
| `getMixRecommendCard()` | 呼叫 `OrderRepository.getBookingSuccessRecommendCard()`，取得推薦卡資料 |
| `getTransCheckCancelable()` | 確認交通訂單是否可取消（JR、DCL 等） |
| `getTransSearchParams()` | 取得交通訂單重新訂位搜尋參數（含 cancel 舊 Job 保護） |
| `getAirportOrderDetail()` | 透過 TransportationRepository 刷新機場訂單詳情 |
| `triggerShareQRCode()` | 準備 QR Code 分享快照資訊，emit 至 `_snapshotInfo` |
| `deepLink()` | 透過 KKEventBus 觸發 DeepLink 導航（加入推薦參數） |
| `addWishProduct()` / `removeWishProduct()` | 新增/移除願望清單，觸發 EventBus 廣播 |
| `setReadyToOpenContact()` | 控制聯絡客服頁面開啟時機（emit SharedFlow） |
| `updateOrderPaymentFailed()` | 通知後端支付失敗事件 |
| `trackProdCardViewed()` / `trackProdCardClicked()` | 追蹤推薦商品卡曝光/點擊 |
| `trackMixRecommendCardClick()` / `trackEachMixRecommendCard()` | 追蹤混合推薦卡互動 |
| `trackImpressionContactInfo()` | 追蹤導覽員聯絡資訊曝光 |
| `trackESimFAQButtonClicked()` / `trackShareQRCodeButtonClicked()` | 追蹤 eSIM 相關按鈕 |

---

## 業務邏輯摘要

- **新舊版商品判斷**：`OrderDetailActivity` 透過 `judgmentOrder` API 或訂單列表中的 `isNewProductOrder` flag 決定呼叫 `v2/new_order` 或 `v2/order`，分別對應 `OrderDetailFragment` 或 `OldOrderDetailFragment`
- **多資料合併渲染**：Presenter 使用 RxJava `combineLatest` 將訂單詳情、憑證、Barcode、語系、Google 服務可用性、國籍資料、司機通話時段、對話資料組合後一次推送 View，避免多次渲染
- **eSIM 支援判斷**：`triggerTrackingESimSupportWarningChecking()` 在渲染後檢查裝置是否支援 eSIM，若不支援則觸發追蹤事件（僅觸發一次，透過 `StateFlow.take(1)` 保護）
- **交通訂單取消前置檢查**：JR Rail / DCL 等交通訂單在點擊取消前先呼叫 `getTransCheckCancelable()`，依不同 error status 顯示不同錯誤說明 Dialog
- **支付失敗回報**：頁面載入後若偵測到支付失敗，呼叫 `updateOrderPaymentFailed()` 通知後端
- **錯誤處理**：網路不可用 → `showError(true, false)`，訂單不存在 → `showError(false, true)`，API 錯誤 status → 保留舊 state 不覆蓋

---

## 已知技術債

- **Reductor 與 MVVM 雙軌並存**：主資料流（訂單詳情）走 Presenter → Reductor → NetworkApi，而輔助資料（重新付款、Barcode、推薦卡）走 ViewModel → UseCase → Repository，兩套架構在同一頁面並存，增加維護複雜度
- **NetworkApi 全域 Singleton**：Reducer 直接呼叫 `NetworkApi.sharedInstance()` 的舊版 Retrofit 封裝，未走 domain/contract Repository 介面，無法替換或 mock
- **OrderRepository 非介面**：`libs/feature/order_page/.../OrderRepository.kt` 為直接的 class，未在 `:domain:contract` 定義介面，不符合 Clean Architecture 理想分層
- **兩層 Presenter 命名衝突**：Activity 與 Fragment 各有一個 `OrderDetailPresenter.kt`，同名不同包，容易混淆
- **`old/` 目錄的更舊版**：`OldOrderDetailFragment` + `OldOrderDetailPresenter` + `OldOrderDetailViewModel` 為更早一代實作，與本文件描述的 `OrderDetailFragment` 並存，共用同一個 `OrderDetailActivity` 殼，需依訂單類型路由

## 相關筆記
- [01-architecture](../01-architecture.md)
- [02-modules](../02-modules.md)
- [03-ui-patterns](../03-ui-patterns.md)
- [05-networking](../05-networking.md)
- [06-data-layer](../06-data-layer.md)
- [07-concurrency](../07-concurrency.md)
- [order-detail-compose](order-detail-compose.md)
- [order-list](order-list.md)
- [sku-activity-shell](sku-activity-shell.md)

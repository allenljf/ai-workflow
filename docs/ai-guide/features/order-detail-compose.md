# 新版訂單詳情（Compose）技術文件

> 自動產生 | 最後更新：2026-03-19

---

## 概述

- **所在 Module**：`:feature:common:order`（`libs/feature/order_page/`）
- **UI 入口**：`NewOrderDetailScreen.kt`
- **功能描述**：以 Jetpack Compose 實作的新版訂單詳情頁，顯示訂單完整資訊、狀態、票券、退款、取消政策、評論、推薦商品等功能，採用 MVI 架構。

---

## 檔案清單

```
UI（Compose 頁面）
 └─ NewOrderDetailScreen.kt                → libs/feature/order_page/.../new_detail/

UI 子元件（Compose Sections）
 ├─ OrderDetailStatusSectionScreen.kt       → .../new_detail/compose/status_section/
 ├─ OrderDetailInfoSectionScreen.kt         → .../new_detail/compose/
 ├─ OrderDetailProductInfoSectionScreen.kt  → .../new_detail/compose/
 ├─ OrderDetailBookingInfoSectionScreen.kt  → .../new_detail/compose/
 ├─ OrderDetailCancellationPolicySectionScreen.kt → .../new_detail/compose/
 ├─ OrderDetailReportIssueSectionScreen.kt  → .../new_detail/compose/
 ├─ OrderDetailNavBarScreen.kt              → .../new_detail/compose/
 ├─ OrderDetailRatingBarScreen.kt           → .../new_detail/compose/
 └─ OrderDetailTripInfoSectionScreen.kt     → .../new_detail/compose/info_section/

UI 子元件（狀態區塊）
 ├─ OrderDetailPendingPaymentStatusScreen.kt → .../new_detail/compose/status_section/
 ├─ OrderDetailHandleStatusScreen.kt         → .../new_detail/compose/status_section/
 ├─ OrderDetailSentStatusScreen.kt           → .../new_detail/compose/status_section/
 ├─ OrderDetailDoneStatusScreen.kt           → .../new_detail/compose/status_section/
 ├─ OrderDetailCancelingStatusScreen.kt      → .../new_detail/compose/status_section/
 ├─ OrderDetailCanceledStatusScreen.kt       → .../new_detail/compose/status_section/
 └─ OrderDetailStatusNoticeScreen.kt         → .../new_detail/compose/status_section/

UI 子元件（行程地點模組）
 ├─ OrderLocationModuleScreen.kt             → .../new_detail/compose/location_module/
 ├─ OrderGatheringPointScreen.kt             → .../new_detail/compose/location_module/
 ├─ OrderExchangeLocationSection.kt          → .../new_detail/compose/location_module/
 ├─ OrderExperienceLocationSection.kt        → .../new_detail/compose/location_module/
 ├─ OrderMeetingLocationSection.kt           → .../new_detail/compose/location_module/
 └─ MapWebViewComponent.kt                   → .../new_detail/compose/location_module/

UI 子元件（Dialog / BottomSheet）
 ├─ PaymentDetailBottomSheet.kt              → .../new_detail/compose/dialog/
 ├─ BookingDetailsBottomSheet.kt             → .../new_detail/compose/dialog/
 ├─ ConfirmTimeBottomSheet.kt                → .../new_detail/compose/dialog/
 ├─ HowToUseBottomSheet.kt                   → .../new_detail/compose/dialog/
 ├─ ImportantNotesBottomSheet.kt             → .../new_detail/compose/dialog/
 ├─ OrderCancelNotAllowedDialog.kt           → .../new_detail/compose/dialog/
 ├─ RepayCancelConfirmDialog.kt              → .../new_detail/compose/dialog/
 ├─ OrderDetailProductInfoModalBottomSheet.kt → .../new_detail/compose/dialog/
 └─ ExchangeLocationSelectCityDialog.kt      → .../new_detail/compose/dialog/

UI 子元件（商品資訊頁籤）
 ├─ ProductDetailsFeatureListTabContent.kt   → .../new_detail/compose/dialog/product_info_page/
 ├─ ProductDetailsFeeInfoTabContent.kt       → .../new_detail/compose/dialog/product_info_page/
 ├─ ProductDetailsInfoTabContent.kt          → .../new_detail/compose/dialog/product_info_page/
 ├─ ProductDetailsScheduleInfoTabContent.kt  → .../new_detail/compose/dialog/product_info_page/
 ├─ ProductDetailsStringListTabContent.kt    → .../new_detail/compose/dialog/product_info_page/
 ├─ ProductDetailsTableListTabContent.kt     → .../new_detail/compose/dialog/product_info_page/
 └─ ProductDetailsTravelScheduleTabContent.kt → .../new_detail/compose/dialog/product_info_page/

工具 / 常數
 ├─ OrderDetailConstants.kt                  → .../new_detail/
 └─ OrderDetailNav.kt                        → .../new_detail/

ViewModel（MVI 架構）
 └─ NewOrderDetailViewModel.kt               → .../new_detail/
     含：OrderDetailState, OrderDetailEvent, NavigationEffect

Domain（UseCase）
 ├─ GetVoucherByOrderUseCase.kt              → libs/feature/order_page/.../domain/useCase/
 └─ GetBarcodesResultUseCase.kt              → libs/feature/order_page/.../domain/useCase/

Data（Repository）
 ├─ OrderRepository.kt（order_page 內直接實作） → libs/feature/order_page/.../domain/repository/
 ├─ OrderVoucherRepository.kt（介面）          → libs/feature/order_page/.../domain/repository/
 ├─ OrderVoucherRepositoryImpl.kt              → libs/feature/order_page/.../data/
 └─ ESimDcsRepository.kt                      → data/repository/.../

Network（API）
 └─ IOrderApiService.kt                       → libs/networking/api/.../service/order_api/

Data Model
 └─ OrderDetailInfo, VoucherListInfo, BarcodesResult 等 → data/model/ & libs/networking/
```

---

## 資料流

### 主流程：頁面載入取得訂單詳情

```
UI（NewOrderDetailScreen）
 │  LaunchedEffect 觸發
 │  呼叫：viewModel.handleEvent(OrderDetailEvent.LoadOrderDetail(orderId))
 ↓
ViewModel（NewOrderDetailViewModel）
 │  handleEvent → fetchOrderDetail(orderId)
 │  更新 _state: isLoading = true
 │  呼叫：orderRepository.getOrderDetail(orderId, lang)
 ↓
Repository（OrderRepository - order_page）
 │  呼叫：orderService.getOrderDetail(orderId, lang)
 │  直接回傳 apiResultData 結果
 ↓
API（IOrderApiService）
 │  GET v2/new_order/{order_id}?lang={lang}
 ↓
後端 API
```

### 次要流程：並行取得票券 + 條碼 + eSIM 資料

```
fetchOrderDetail 成功後 → fetchVouchers(orderId)
 │
 ├─ async → GetVoucherByOrderUseCase.invoke(orderId)
 │           └─ OrderVoucherRepository.getVouchersByOrder()
 │               └─ GET v2/order/{order_mid}/vouchers
 │
 ├─ async → GetBarcodesResultUseCase.invoke(orderId)
 │           └─ OrderVoucherRepository.getBarcodesResult()
 │
 ├─ async → ESimDcsRepository.getESimInstruction()
 │
 └─ async → ESimDcsRepository.getESimOneClickInstallation()
```

### 次要流程：檢查可否重新付款

```
UI → handleEvent(OrderDetailEvent.CheckCanOrderRepay(context, orderMasterMId))
 ↓
ViewModel → checkCanOrderRepay()
 │  呼叫：orderRepository.checkCanOrderRepay(orderMasterMid)
 │         └─ GET v2/cart/payment/check/{order_master_mid}
 │  呼叫：orderRepository.getPaymentResultByOrderMId(orderMasterMid, locale, lang)
 │         └─ GET v3/cart/info/{order_master_mid}
```

### 回傳流

```
後端 API
 ↓
Repository：B2CApiResponse<OrderDetailInfo> → apiResultData 解析
 ↓
ViewModel：OrderDetailInfo → 更新 OrderDetailState（orderDetailInfo, vTagProduct, vTagPlan, vTagRoom, guideContactInput）
 ↓
UI：collectAsState() 觀察 state 變化，各 Section Screen 接收對應資料渲染
```

---

## 逐層說明

### UI 層

`NewOrderDetailScreen` 是純 Compose 函式，使用 `Scaffold` + `LazyColumn` 建構頁面。主要組成：
- 頂部導覽列（`OrderDetailNavBarScreen`）
- 狀態區塊（`OrderDetailStatusSectionScreen`，依訂單狀態顯示不同子元件）
- 商品資訊區塊（`OrderDetailProductInfoSectionScreen`）
- 訂單資訊區塊（`OrderDetailInfoSectionScreen`）
- 預訂資訊區塊（`OrderDetailBookingInfoSectionScreen`）
- 行程資訊與地點模組（`OrderDetailTripInfoSectionScreen` + `OrderLocationModuleScreen`）
- 取消政策區塊（`OrderDetailCancellationPolicySectionScreen`）
- 問題回報區塊（`OrderDetailReportIssueSectionScreen`）
- 評分區塊（`OrderDetailRatingBarScreen`）
- 推薦商品區塊
- 多個 BottomSheet / Dialog（付款明細、預訂詳情、確認時間、使用方式、注意事項等）

支援下拉重新整理（`PullRefreshIndicator`），透過 `LaunchedEffect` 收集 `navigationEffect` 處理一次性導航事件。

### ViewModel 層

採用 **MVI 架構**：
- **State**：`OrderDetailState`（data class），包含 `isLoading`、`orderDetailInfo`、`voucherListInfo`、`barcodesResult`、各 Dialog 顯示旗標等
- **Event**：`OrderDetailEvent`（sealed class），涵蓋所有 UI 互動意圖（約 30 種事件）
- **Effect**：`NavigationEffect`（sealed class），處理一次性導航（跳頁、分享、取消訂單等）
- 狀態管理：`MutableStateFlow<OrderDetailState>` + `MutableSharedFlow<NavigationEffect>`
- 統一入口：`handleEvent(event: OrderDetailEvent)` 分派所有事件
- 使用 `@KoinViewModel` 註解注入

### UseCase 層

- `GetVoucherByOrderUseCase`（`@Factory`）：透過 `OrderVoucherRepository` 取得訂單票券，內建記憶體快取（`HashMap`），避免重複請求
- `GetBarcodesResultUseCase`（`@Factory`）：透過 `OrderVoucherRepository` 取得條碼資料

注意：訂單詳情主流程中，ViewModel 直接呼叫 `OrderRepository.getOrderDetail()`，未經過 UseCase（技術債）。

### Repository 層

- `OrderRepository`（`libs/feature/order_page/.../domain/repository/`）：不是介面，而是直接繼承 `BaseApiRepository` 的具體類別。處理訂單相關所有 API 呼叫，使用 `safeApiCallFlow` / `safeApiCall` 包裝錯誤處理。
- `OrderVoucherRepository`（介面）+ `OrderVoucherRepositoryImpl`（實作）：票券與條碼相關 API
- `ESimDcsRepository`：eSIM DCS 配置資料

### API 層

`IOrderApiService` 主要相關端點：

| 端點 | HTTP 方法 | 用途 |
|------|-----------|------|
| `v2/new_order/{order_id}` | GET | 取得訂單詳情 |
| `v2/order/{order_mid}/vouchers` | GET | 取得票券清單 |
| `v2/new_order/{order_mid}/cancellation` | GET | 取得取消政策 |
| `v2/cart/payment/check/{order_master_mid}` | GET | 檢查可否重新付款 |
| `v3/cart/info/{order_master_mid}` | GET | 取得付款結果 |
| `v2/order/{order_master_mid}/payment/failed` | PUT | 更新付款失敗（取消付款） |
| `v2/recommend/order/after_confirm` | POST | 取得推薦商品 |
| `v2/tour-guide` | POST | 取得導遊/司機聯絡資訊 |
| `v2/comment/{comment_id}` | GET | 取得評論 |

---

## ViewModel 方法清單

| 方法 | 說明 |
|------|------|
| `handleEvent(event)` | MVI 統一事件入口，分派所有 UI 互動 |
| `fetchOrderDetail(orderId)` | 呼叫 API 取得訂單詳情，成功後觸發 fetchVouchers 與推薦商品 |
| `checkCanOrderRepay(context, orderMasterMid)` | 檢查訂單是否可重新付款，同時取得付款結果 |
| `fetchVouchers(orderId)` | 並行取得票券、條碼、eSIM 資料（4 個 async） |
| `getOrderCancellation()` | 取得取消政策資訊，成功則導航至取消訂單頁 |
| `cancelPayAndHandleResult()` | 執行取消付款，成功後發出 `CancelPaySuccess` 導航事件 |
| `getMixRecommendCard(orderAfterConfirm)` | 取得推薦商品卡片 |
| `createGuideContactInput(orderDetailInfo)` | 根據訂單資訊建立導遊/司機聯絡輸入物件 |
| `createOrderCommentInput(summaryData)` | 根據摘要建立評論路由輸入物件 |
| `triggerShareQRCode(...)` | 處理分享票券 QR Code 的導航事件 |
| `deepLink(url)` | 處理 DeepLink 導航，透過 EventBus 發送 |
| `refreshWish()` | 重新整理收藏清單 |
| `getPaymentResultOrders()` | 取得付款結果中的訂單清單 |
| `trackViewOrderDetailPg()` | 追蹤頁面瀏覽事件 |
| `trackClickCancelOrderBtn()` | 追蹤取消訂單按鈕點擊 |
| `trackClickEditOrderBtn()` | 追蹤編輯訂單按鈕點擊 |
| `trackClickOrderDetailVoucher(placement)` | 追蹤票券按鈕點擊 |
| `trackClickOrderDetailSendReceipt()` | 追蹤寄送收據點擊 |
| `trackClickOrderDetailBookAgain()` | 追蹤再次預訂點擊 |
| `trackClickOrderDetailReview()` | 追蹤評論按鈕點擊 |
| `trackClickOrderDetailContactInfo()` | 追蹤聯絡資訊點擊 |
| `trackClickOrderDetailReportIssue()` | 追蹤問題回報點擊 |
| `trackClickOrderDetailCancelPolicyDetail()` | 追蹤取消政策詳情點擊 |
| `trackClickOrderDetailConfirmDetail()` | 追蹤確認時間詳情點擊 |
| `trackClickOrderDetailPaymentDetail()` | 追蹤付款明細點擊 |
| `trackClickOrderDetailSKUDetail()` | 追蹤規格詳情點擊 |
| `trackClickOrderDetailBeforeGoDetail(section)` | 追蹤行前資訊區塊點擊 |
| `trackClickOrderDetailTopBarCancelBtn()` | 追蹤頂部取消按鈕點擊 |
| `trackClickOrderDetailTopBarRepayBtn()` | 追蹤頂部重新付款按鈕點擊 |
| `trackShareQRCodeButtonClicked()` | 追蹤分享 QR Code 點擊 |

---

## 業務邏輯摘要

- **MVI 事件驅動**：所有 UI 互動統一透過 `handleEvent()` 入口，事件定義於 `OrderDetailEvent` sealed class
- **並行資料載入**：訂單詳情載入成功後，使用 `async-await` 並行取得票券、條碼、eSIM 資料
- **訂單狀態分支**：根據 `orderStatus` 顯示不同狀態區塊（待付款、處理中、已出票、已完成、取消中、已取消）
- **重新付款流程**：`CheckCanOrderRepay` 事件觸發，成功後顯示付款相關按鈕；取消付款透過 `updateOrderPaymentFailed` API
- **導航效果分離**：一次性導航事件（跳頁、分享）透過 `SharedFlow<NavigationEffect>` 處理，與持久狀態分離
- **追蹤埋點完整**：幾乎所有使用者操作都有對應的 KKTracker 事件追蹤
- **錯誤處理**：Repository 使用 `BaseApiRepository.safeApiCallFlow` 統一包裝，ViewModel 額外 try-catch 處理例外，錯誤訊息透過 `state.error` 傳遞至 UI 顯示 Snackbar
- **eSIM 支援**：若商品為 eSIM 類別（`CATEGORY_081`），額外顯示 eSIM 安裝指引與一鍵安裝功能
- **VTag 規格標籤**：從 `VTagRoom`（房型）和 `VTagPlan`（餐食/料理類型）提取規格標籤顯示

---

## 已知技術債

- `OrderRepository` 在 `order_page` 模組內為具體類別（非介面），未實作 `domain/contract` 介面分離
- ViewModel 直接依賴 `OrderRepository` 具體類別，主要訂單詳情取得流程未經過 UseCase 抽象
- `NewOrderDetailViewModel` 建構子參數過多（9 個依賴），建議拆分或使用 UseCase 封裝
- 追蹤方法數量龐大（超過 15 個 track 方法），可考慮提取為獨立的 Tracker 類別
- `checkCanOrderRepay` 方法內同時處理 repay 檢查與付款結果查詢，職責過重

## 相關筆記
- [01-architecture](../01-architecture.md)
- [02-modules](../02-modules.md)
- [03-ui-patterns](../03-ui-patterns.md)
- [05-networking](../05-networking.md)
- [06-data-layer](../06-data-layer.md)
- [07-concurrency](../07-concurrency.md)
- [order-cancel](order-cancel.md)
- [order-contact-support](order-contact-support.md)
- [order-list](order-list.md)
- [sku-activity-shell](sku-activity-shell.md)

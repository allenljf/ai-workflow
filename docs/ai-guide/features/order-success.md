# 訂購成功頁 技術文件

> 自動產生 | 最後更新：2026-03-19

---

## 概述

- **所在 Module**：`:feature:order_page`（`libs/feature/order_page/`）
- **UI 入口**：`BookingSuccessB2CActivity.kt` + `BookingSuccessB2CFragment.kt`
- **功能描述**：完成訂購並付款後顯示的成功確認頁，呈現訂單摘要、買家信箱提示、市場活動 Banner、國泰保險推薦及個人化混合推薦商品卡。

---

## 檔案清單

```
UI（使用者介面入口）
 ├─ BookingSuccessB2CActivity.kt            → libs/feature/order_page/src/main/java/com/kkday/order_page/presentation/view/
 └─ BookingSuccessB2CFragment.kt           → libs/feature/order_page/src/main/java/com/kkday/order_page/presentation/view/

ViewModel（UI 狀態管理）
 └─ BookingSuccessViewModel.kt             → libs/feature/order_page/src/main/java/com/kkday/order_page/presentation/viewModel/

Domain（追蹤用 UseCase）
 ├─ ConfirmPageLoadTrackingUseCase.kt      → libs/feature/order_page/src/main/java/com/kkday/order_page/domain/useCase/
 └─ ConfirmPageLoadTransTrackingUseCase.kt → libs/feature/order_page/src/main/java/com/kkday/order_page/domain/useCase/

Data（資料層，Repository 兼介面與實作）
 └─ OrderRepository.kt                    → libs/feature/order_page/src/main/java/com/kkday/order_page/domain/repository/

Network（API 定義）
 └─ IOrderApiService.kt                   → libs/networking/api/src/main/java/com/kkday/library/networking/service/order_api/

Controller（Epoxy RecyclerView）
 └─ BookingSuccessController.kt           → libs/feature/order_page/src/main/java/com/kkday/order_page/presentation/controller/

Helper（View Model 資料轉換）
 └─ BookingSuccessViewInfoHelper.kt       → libs/feature/order_page/src/main/java/com/kkday/order_page/helper/
```

---

## 資料流

### 主流程：頁面載入，並行觸發三個 API

頁面載入後 `initAction()` 並行呼叫以下三個資料請求：

#### 流程一：CITI 市場活動 Banner

```
UI（BookingSuccessB2CFragment）
 │  initAction() 觸發
 │  呼叫：bookingSuccessVM.getCITIMarketEventBanner(orderMid)
 ↓
ViewModel（BookingSuccessViewModel）
 │  呼叫：orderRepository.getCITIMarketEventBanner(orderMid)
 │  （無 UseCase，直接呼叫 Repository — 技術債：缺少 UseCase 抽象層）
 ↓
Repository（OrderRepository）
 │  呼叫：orderService.getCITIMarketEventBanner(orderMid)
 │  以 safeApiCall + apiResultData 包裝
 ↓
API Service（IOrderApiService）
 │  GET v2/mkt/event/page
 │  Query: order_master_mid=<orderMid>
 ↓
後端 API
```

#### 流程二：國泰保險推薦

```
UI（BookingSuccessB2CFragment）
 │  initAction() 觸發
 │  呼叫：bookingSuccessVM.getCathayInsuranceInfo(orderMid)
 ↓
ViewModel（BookingSuccessViewModel）
 │  呼叫：orderRepository.getCathayInsuranceRecommendProduct(orderMid)
 ↓
Repository（OrderRepository）
 │  呼叫：orderService.getCathayInsuranceRecommendProduct("ANDROID", "android_booking", orderMid)
 │  以 safeApiCall + apiResultList 包裝
 ↓
API Service（IOrderApiService）
 │  GET v2/insurance/cathay/recommend-product
 │  Query: platform=ANDROID, channel=android_booking, order_master_mid=<orderMid>
 ↓
後端 API
```

#### 流程三：混合推薦商品卡

```
UI（BookingSuccessB2CFragment）
 │  initAction() 觸發，先組裝 OrderAfterConfirm（含 currency、orders 陣列）
 │  呼叫：bookingSuccessVM.getMixRecommendCard(orderAfterConfirm)
 ↓
ViewModel（BookingSuccessViewModel）
 │  先發送 Loading 狀態：_orderConfirmRecommendCardState.value = OrderConfirmRecommendCardState(isLoading=true)
 │  呼叫：orderRepository.getBookingSuccessRecommendCard(orderAfterConfirm)
 ↓
Repository（OrderRepository）
 │  呼叫：orderService.getBookingSuccessRecommendCard(orderAfterConfirm)
 │  以 safeApiCall + apiResultDataByKotlinx（kotlinx.serialization）解析
 ↓
API Service（IOrderApiService）
 │  POST v2/recommend/order/after_confirm
 │  Body: OrderAfterConfirm { currency, orders: [{ orderMid, prodMid, orderDate, backDate, status, destinationCodes }] }
 ↓
後端 API
```

### 回傳流

```
後端 API
 ↓
Repository（OrderRepository）
 │  ApiResult.Success → 資料透過 safeApiCall 包裝回傳
 │  ApiResult.Loading → 傳遞 loading 狀態（僅 getMixRecommendCard 處理此分支）
 │  其他（Error）     → CITI/Cathay 靜默忽略；MixRecommend 設 isLoading=false、data=null
 ↓
ViewModel（BookingSuccessViewModel）
 │  getCITIMarketEventBanner：_marketEventPage.value = MarketEventPage
 │  getCathayInsuranceInfo：_cathayInsuranceInfo.value = List<CathayInsuranceInfo>
 │  getMixRecommendCard：_orderConfirmRecommendCardState.value = OrderConfirmRecommendCardState(...)
 ↓
UI（BookingSuccessB2CFragment）—— observeData() 收集
 │  marketEventPage → updateMarketEventPage()：顯示活動 Banner、底部固定按鈕（fixBars）
 │  cathayInsuranceInfo → 重建 bookingSuccessController.bookingDetailViewInfo（加入保險推薦項目）
 └─ orderConfirmRecommendCardSate → 更新 Controller 的 mixRecommendCard、destination，
                                     渲染混合推薦商品列表
```

---

## 逐層說明

### UI 層

`BookingSuccessB2CActivity` 僅作路由殼，透過 `@RouterParam` 接收三個入口參數：
- `paymentResultJson`：PaymentResult JSON 字串，在 `getPaymentResult()` 以 Gson 反序列化
- `orderMid`：訂單 Master ID
- `productBundlesIds`：Bundle 套票商品 OID 列表

`BookingSuccessB2CFragment` 以 `activityViewModel<BookingSuccessViewModel>()` 共享 Activity scope。核心方法：
- `initView()`：初始化 RecyclerView（StaggeredGridLayoutManager 2欄）、設定返回鍵攔截（導向首頁）、設定購物車/訂單列表按鈕、建立初始 `bookingDetailViewInfo`、觸發頁面載入追蹤
- `initAction()`：並行呼叫三個 ViewModel 方法
- `observeData()`：以 `distinctUntilChangedBy + launchAndCollectIn` 收集四個 StateFlow

### ViewModel 層

以四個 `MutableStateFlow` 管理狀態，全部在獨立 `viewModelScope.launch` 中執行（並發、互不阻塞）：

| StateFlow | 型別 | 說明 |
|-----------|------|------|
| `_recommendProducts` | `RecommendProducts?` | 推薦商品（舊版，目前由 MixRecommend 替代） |
| `_marketEventPage` | `MarketEventPage?` | 市場活動 Banner 與固定按鈕 |
| `_cathayInsuranceInfo` | `List<CathayInsuranceInfo>?` | 國泰保險推薦列表 |
| `_orderConfirmRecommendCardState` | `OrderConfirmRecommendCardState?` | 混合推薦卡（含 isLoading） |

另持有 `latestViewedCardEventIndex` 追蹤最後曝光的推薦卡位置，避免重複觸發 Impression 事件。

### UseCase 層

主要資料請求**無 UseCase 抽象**，ViewModel 直接呼叫 `OrderRepository`（技術債）。

追蹤用 UseCase：
- `ConfirmPageLoadTrackingUseCase`：從 `CartRepository` 取得購物車商品資訊，發送 `ConfirmdPg` PageLoad KTM 事件（注意：依賴 `CartRepository`，違反模組邊界）
- `ConfirmPageLoadTransTrackingUseCase`：依 `SummaryData.transportationType` 對應各交通類型的 BookingConfirmed 追蹤頁面名稱（JREAST/JRWEST、Cruises、RentalCar、Bus、THSR、RailEurope 等）

### Repository 層

`OrderRepository` 為單一 class（未實作介面分離），直接依賴 `IOrderApiService` 與 `KKApi`。相關方法：

| 方法 | 包裝方式 | 回傳型別 |
|------|---------|---------|
| `getCITIMarketEventBanner` | `safeApiCall + apiResultData` | `Flow<ApiResult<MarketEventPage>>` |
| `getCathayInsuranceRecommendProduct` | `safeApiCall + apiResultList` | `Flow<ApiResult<List<CathayInsuranceInfo>>>` |
| `getBookingSuccessRecommendCard` | `safeApiCall + apiResultDataByKotlinx` | `Flow<ApiResult<OrderConfirmRecommendCardView>>` |

無本地快取邏輯，全部每次重新請求 API。

### API 層

| 方法 | HTTP 方法 | Endpoint | 用途 |
|------|---------|---------|------|
| `getCITIMarketEventBanner` | GET | `v2/mkt/event/page` | 取得市場活動 Banner 與底部固定按鈕 |
| `getCathayInsuranceRecommendProduct` | GET | `v2/insurance/cathay/recommend-product` | 取得國泰保險推薦商品列表 |
| `getBookingSuccessRecommendCard` | POST | `v2/recommend/order/after_confirm` | 取得訂單確認後個人化推薦商品卡 |

---

## View 方法清單

| 方法 | 說明 |
|------|------|
| `onAttach()` | 監聽 Fragment 附加事件，攔截 `KKBaseInfoDialog` 確認按鈕（國泰保險 WebView 跳轉） |
| `initView()` | 初始化 RecyclerView、設定按鈕點擊、建立 bookingDetailViewInfo、觸發頁面追蹤 |
| `initAction()` | 並行呼叫 getCITIMarketEventBanner、getCathayInsuranceInfo、getMixRecommendCard |
| `observeData()` | 收集四個 StateFlow，更新 Controller 資料 |
| `createBookingDetailViewInfo()` | 依是否有 Bundle 套票群組，分流轉換 PaymentResult 為 BookingDetailViewInfo 列表 |
| `handleBackPress()` | 攔截返回鍵，強制導向首頁（不允許返回結帳頁） |
| `setBuyerInfo()` | 顯示購買者信箱提示文字；依 `isOnlinePayment` 顯示不同成功標題 |
| `updateMarketEventPage()` | 更新活動 Banner 曝光追蹤、顯示底部固定按鈕、調整 RecyclerView 底部 margin |
| `onProductCardViewed()` | 混合推薦商品卡曝光追蹤，更新 `latestViewedCardEventIndex` |
| `onClickProductCard()` | 混合推薦商品卡點擊追蹤 |
| `onWishChanged()` | 加入/移除願望清單，觸發 KKEventBus `WishProduct` 事件 |
| `onCardEventView()` | 非商品卡（活動卡等）曝光追蹤 |
| `onCardEventClick()` | 非商品卡點擊追蹤 |
| `onDeeplinkUrlClick()` | 透過 KKEventBus MainDeepLink 處理推薦卡 DeepLink 跳轉 |
| `onInsuranceItemClick()` | 顯示國泰保險推薦 Dialog |
| `onEventUrlClick()` | 活動 Banner 點擊，開啟 WebView 並追蹤事件 |
| `updateCartButton()` | 依購物車是否有可用商品，顯示/隱藏購物車按鈕紅點 |
| `getOrderAfterConfirm()` | 組裝 `OrderAfterConfirm` request body（含各訂單 orderMid/prodMid/orderDate/destinationCodes） |
| `getPaymentResult()` | 從 Activity 取得已解析的 `PaymentResult`，無 Activity 時回傳 `defaultInstance` |
| `getOrderMid()` | 從 Activity 取得 orderMid |
| `getProductBundlesIds()` | 從 Activity 取得 Bundle 套票 OID 列表 |
| `getProdCardIndex()` | 在 `mixRecommendCard` 列表中找出指定商品 OID 的位置 |

---

## ViewModel 方法清單

| 方法 | 說明 |
|------|------|
| `getCITIMarketEventBanner()` | 呼叫 Repository 取得市場活動頁，成功時更新 `_marketEventPage` |
| `getCathayInsuranceInfo()` | 呼叫 Repository 取得國泰保險推薦，成功時更新 `_cathayInsuranceInfo` |
| `getMixRecommendCard()` | 先發 Loading 狀態，呼叫 Repository 取得混合推薦卡，成功/失敗皆更新 `_orderConfirmRecommendCardState` |
| `deepLink()` | 透過 KKEventBus 發送 `MainDeepLink` 事件（附加 `order_recommend` 參數） |
| `trackPageLoad()` | 呼叫兩個追蹤 UseCase（一般頁面載入 + 交通類型分流追蹤） |
| `trackProdCardViewed()` | 混合推薦商品卡曝光事件（`EventType.VIEW`，`BOOKING_SUCCESS_PG`） |
| `trackProdCardClicked()` | 混合推薦商品卡點擊事件（`EventType.CLICK`，`BOOKING_SUCCESS_PG`） |
| `addWishProduct()` | 呼叫 `AddWishProductUseCase`，更新 `appSharedData.wishChanged`，發 KKEventBus |
| `removeWishProduct()` | 呼叫 `DeleteWishProductUseCase`，更新 `appSharedData.wishChanged`，發 KKEventBus |
| `trackPromoEventBannerView()` | 活動 Banner 曝光追蹤 |
| `trackPromoEventButtonView()` | 活動固定按鈕曝光追蹤 |
| `trackPromoEventBannerClick()` | 活動 Banner 點擊追蹤 |
| `trackPromoEventButtonClick()` | 活動固定按鈕點擊追蹤 |
| `trackMixRecommendCardClick()` | 混合推薦卡點擊追蹤（含 destination、position、card_type、prod_mid 等屬性） |
| `trackEachMixRecommendCard()` | 混合推薦卡逐張曝光追蹤，利用 `latestViewedCardEventIndex` 避免重複上報 |

---

## 業務邏輯摘要

- **Bundle 套票群組訂單**：若 `productBundlesIds` 不為空，將 orders 拆分為 Bundle 群組與一般訂單兩類，分別以 `convertSummaryToGroupOrderBookingDetailViewInfo` 與 `convertSummaryToBookingDetailViewInfo` 轉換
- **付款方式差異**：`isOnlinePayment = true` 顯示「付款成功」標題；`false` 顯示「現場付款預訂完成」標題
- **返回攔截**：`OnBackPressedCallback` 強制導向首頁，防止用戶返回結帳流程
- **混合推薦卡曝光去重**：`latestViewedCardEventIndex` 記錄最後已曝光位置，位置 ≤ 已記錄值時不重複觸發 Impression
- **推薦卡 DeepLink**：跳轉時附加 `order_recommend` query 參數（透過 KKEventBus MainDeepLink 處理）
- **國泰保險 Dialog**：點擊保險項目後顯示確認 Dialog，確認後開啟 WebView；Dialog 的 onPositiveClickListener 透過 `parentFragmentManager.addFragmentOnAttachListener` 設定
- **錯誤處理**：CITI Banner 與 Cathay 保險 API 失敗時靜默忽略（`else -> {}`），不顯示錯誤提示；混合推薦卡失敗時 isLoading=false、data=null，Controller 隱藏 loading 狀態

---

## 已知技術債

- `OrderRepository` 為單一 class，未分離 domain/contract 介面與 data 實作，不符合 Clean Architecture
- `BookingSuccessViewModel` 直接依賴 `OrderRepository` class，缺少 UseCase 抽象層（主要資料請求）
- `ConfirmPageLoadTrackingUseCase` 依賴 `CartRepository`（`:data:repository`），違反 feature 模組對 data 層直接依賴的邊界
- Fragment 透過 `(activity as? BookingSuccessB2CActivity)` 強轉取得資料，耦合 Activity 型別

## 相關筆記
- [01-architecture](../01-architecture.md)
- [02-modules](../02-modules.md)
- [03-ui-patterns](../03-ui-patterns.md)
- [05-networking](../05-networking.md)
- [06-data-layer](../06-data-layer.md)
- [07-concurrency](../07-concurrency.md)
- [checkout](checkout.md)
- [order-detail-compose](order-detail-compose.md)
- [order-list](order-list.md)
- [sku-activity-shell](sku-activity-shell.md)

# 結帳填寫頁 技術文件

> 自動產生 | 最後更新：2026-07-15

---

## 概述

- **所在 Module**：`:app`
- **UI 入口**：`OrderFormFillingActivity.kt`
- **功能描述**：購物結帳流程中的表單填寫頁面，使用者需填寫聯絡資訊、選擇付款方式、套用優惠券，並確認訂單後送出結帳

---

## 檔案清單

```
UI（使用者介面入口）
 ├─ OrderFormFillingActivity.kt           → app/.../view/product/form/
 ├─ OrderFormFillingAdapter.kt            → app/.../view/product/form/
 ├─ OrderFormFillingMvpView.kt            → app/.../view/product/form/
 ├─ OrderFormFillingViewUpdateHelper.kt   → app/.../view/product/form/
 ├─ OrderFormFillingConstants.kt          → app/.../view/product/form/
 ├─ PaymentAdsInfoFragment.kt             → app/.../view/product/form/
 └─ GooglePayLauncherActivity.kt          → app/.../view/product/form/

Delegate（UI 區塊委派）
 ├─ OrderFormFillingContactDelegate.kt    → app/.../view/product/form/delegate/
 ├─ OrderFormFillingDetailDelegate.kt     → app/.../view/product/form/delegate/
 ├─ OrderFormFillingPassengerInfoDelegate.kt → app/.../view/product/form/delegate/
 ├─ OrderFormFillingCouponDelegate.kt     → app/.../view/product/form/delegate/
 ├─ OrderFormFillingPriceInfoDelegate.kt  → app/.../view/product/form/delegate/
 ├─ OrderFormFillingPointDelegate.kt      → app/.../view/product/form/delegate/
 ├─ OrderFormFillingScheduleDetailDelegate.kt → app/.../view/product/form/delegate/
 ├─ OrderFormFillingProdSessionDelegate.kt → app/.../view/product/form/delegate/
 ├─ OrderFormFillingPayHotelPriceDetailDelegate.kt → app/.../view/product/form/delegate/
 ├─ OrderFormFillingJrRailDetailDelegate.kt → app/.../view/product/form/delegate/
 ├─ OrderFormFillingAirportDelegate.kt    → app/.../view/product/form/delegate/
 └─ OrderFormFillingSummaryDelegate.kt    → app/.../view/product/form/delegate/summary/

ViewModel（UI 狀態管理）
 └─ OrderFormFillingViewModel.kt          → app/.../view/product/form/

Presenter（Reductor 狀態橋接）
 └─ OrderFormFillingPresenter.kt          → app/.../view/product/form/

State（頁面狀態）
 ├─ BookingStateHelper.kt                 → app/.../view/product/form/
 └─ BookingState（data class）            → app/.../view/product/form/BookingStateHelper.kt

Reducer（Reductor 狀態機）
 └─ OrderFormFillingReducer.kt            → app/.../reducer/product/

Domain（業務邏輯 UseCase）
 ├─ GetCartProductsPriceUseCase.kt        → app/.../view/product/form/
 ├─ GetCartProductsStatusUseCase.kt       → app/.../view/product/form/
 └─ GetProdSessionUseCase.kt             → app/.../view/share/useCase/

Data（資料層）
 ├─ CheckoutRepository.kt                → data/repository/.../
 ├─ CartProductsRepository.kt            → app/.../view/product/repository/
 ├─ OrderFormFillingRepository.kt        → app/.../view/product/repository/hotel/
 ├─ CartRepository.kt                    → （Koin 注入，退換貨政策查詢）
 └─ BookingRepository.kt                 → （Koin 注入，訂單規格資料）

Network（API 定義）
 ├─ Api.kt / NetworkApi.kt / RetrofitApi.kt → app/.../network/
 └─ KKdayService.kt（Retrofit 介面）     → app/.../network/retrofit/

信用卡表單
 ├─ AdyenCreditCardFormDialogFragment.kt  → app/.../view/product/form/credit/
 ├─ CreditCardFormView.kt                → app/.../view/product/form/credit/
 ├─ SelectCreditCardBottomSheet.kt        → app/.../view/product/form/credit/
 ├─ CreditCardFormFactory.kt             → app/.../view/product/form/credit/
 └─ CreditCardRedirectHandlerImpl.kt     → app/.../view/product/form/credit/

優惠券
 ├─ CouponFormActivity.kt                → app/.../view/product/form/coupon/
 ├─ CouponFormPresenter.kt               → app/.../view/product/form/coupon/
 ├─ CouponViewModel.kt                   → app/.../view/product/form/coupon/
 └─ CouponListFragment.kt                → app/.../view/product/form/coupon/list/

支付 Helper
 ├─ PaymentHelper.kt                      → app/.../view/product/form/helper/
 ├─ AdyenHelper.kt                        → app/.../view/product/form/helper/
 ├─ TappayHelper.kt                       → app/.../view/product/form/helper/
 └─ AlipayHKHelper.kt                     → app/.../view/product/form/helper/

外部依賴 Delegate
 ├─ PaymentViewModelDelegate              → order/domain 模組（支付授權處理）
 ├─ PbCreateOrderViewModelDelegate        → order/domain 模組（優先預訂建單）
 ├─ PaymentStrategyViewModelDelegate      → share/booking 模組（支付策略清單管理）
 └─ FooterViewModelDelegate               → base 模組（頁尾資訊）
```

---

## 資料流

### 主流程：頁面載入 → 取得訂單表單資料

```
UI（OrderFormFillingActivity）
 │  onCreate → initView() + initAction() + observeData()
 │  呼叫：orderFormFillingPresenter.getBookingData(...)
 ↓
Presenter（OrderFormFillingPresenter）
 │  store.dispatch(actions.getBookingData(...))
 ↓
Reducer（OrderFormFillingReducer）
 │  透過 Reductor 處理 Action
 │  呼叫：NetworkApi.getBookingData(...)
 ↓
API（KKdayService）
 │  GET /booking/data（帶 product_mid、product_oid、pkg_id、item_id 等參數）
 ↓
後端 API
```

### 回傳流（訂單表單資料）

```
後端 API
 ↓
Reducer：Response<BookingData> → 更新 AppState
 ↓
Presenter：透過 Rx Observable<AppState> 觀察狀態變更
 ↓
Activity（OrderFormFillingMvpView 回呼）→ BookingStateHelper 組合各區塊 ViewInfo
 ↓
OrderFormFillingViewUpdateHelper：組裝 Item 列表並更新 RecyclerView Adapter
```

### 支付策略載入流程

```
UI（OrderFormFillingActivity）
 │  呼叫：viewModel.getPaymentStrategyList(...)
 ↓
ViewModel → PaymentStrategyViewModelDelegate
 │  呼叫：NetworkApi.getPaymentChannelsData(...)
 ↓
API（KKdayService）
 │  POST /payment/channels
 ↓
後端 API → 回傳可用支付方式清單
 ↓
ViewModel：更新 paymentStrategyList StateFlow
 ↓
Activity：觀察更新，驅動 PaymentViewInfo 更新 Adapter
```

### 確認結帳（付款）流程

```
UI（OrderFormFillingActivity）
 │  使用者點擊「確認付款」按鈕
 │  呼叫：viewModel.confirmClick(...)
 ↓
ViewModel（OrderFormFillingViewModel）
 │  依產品類型分流：
 │  ├─ HotelDynamic → checkHotelV3PriceChange → getExtData → callPriorityBookingVerifyOrder
 │  ├─ ProdSession → checkSessionAndCreateOrder → getProdSessionUseCase → callPriorityBookingVerifyOrder
 │  ├─ Hotel → checkHotelPriceAndStock → callPriorityBookingVerifyOrder
 │  └─ 一般商品 → checkProductSoldOutOrNot → checkCommonProductPrice → callPriorityBookingVerifyOrder
 ↓
PbCreateOrderViewModelDelegate
 │  呼叫：Priority Booking 驗證 → 建立訂單
 ↓
Presenter / Reducer
 │  store.dispatch(actions.clickPayButton(createOrderData))
 ↓
Reducer（OrderFormFillingReducer）
 │  組裝 BookingFormData → NetworkApi.createOrder(...)
 ↓
API（KKdayService）
 │  POST /order/create（或 /order/create/v2）
 ↓
後端 API → CreateOrderResultData
 ↓
回傳至 Activity → 依支付方式走不同支付授權流程（TapPay / Adyen / Stripe / LinePay / Adyen Google Pay 等）
```

> Adyen Google Pay（KKAPP-5940）：`clickPayButton()` 的 `when(paymentStrategy)` 須將 `is AdyenGooglePayStrategy` 攔在 `is AdyenStrategy` 之前（否則誤開信用卡表單），建單後於 `launchGooglePay()` 啟動 Adyen `GooglePayComponent` 原生視窗，`onSubmit` 取 token → `createAdyenGooglePayPayment` 打 `v2/payment/adyen/payment`，3DS 複用既有 Adyen redirect。與 Stripe / TapPay 兩條 Google Pay 路線並存，由後端 `/list-available` 回傳 pmch 驅動。

### 優惠券套用流程

```
UI（OrderFormFillingActivity）
 │  使用者點擊優惠券區塊
 │  呼叫：launcher.launch(CouponFormActivity)
 ↓
CouponFormActivity
 │  使用者輸入/選擇優惠碼
 │  呼叫：CouponFormPresenter → Reducer 驗證
 ↓
Reducer → NetworkApi（驗證優惠券 API）
 ↓
結果回傳 → setResult(RESULT_OK)
 ↓
Activity（onActivityResult）
 │  orderFormFillingPresenter.clickCloseCouponButton()
 │  Reducer 更新 AppState 中的 CouponData
 ↓
BookingStateHelper → 重新計算價格 → 更新 UI
```

---

## 逐層說明

### UI 層
- `OrderFormFillingActivity` 繼承 `BookingActivity`，使用 ViewBinding (`ActivityOrderFormFillingBinding`)
- RecyclerView 搭配 `OrderFormFillingAdapter`，各區塊由 Delegate 模式處理：Summary、Contact、Payment、Coupon、Price、Invoice、Points、RefundPolicy、Terms 等
- `OrderFormFillingViewUpdateHelper` 負責依據 `BookingStateHelper` 產生的 ViewInfo，組裝各區塊的 `Item<*>` 列表並透過 DiffUtil 更新 Adapter
- 底部固定欄 (`layoutConfirmField`) 含價格顯示和「確認付款」按鈕，搭配 BottomSheet 展開價格明細
- 支援多種交通類型 (TransportationType) 的條件判斷，不同類型顯示不同區塊組合

### ViewModel 層
- `OrderFormFillingViewModel` 使用 `@KoinViewModel` 注入，繼承 ViewModel 並實作多個 Delegate 介面
- 狀態管理混合使用：
  - `MutableStateFlow` / `StateFlow`：prodSession、sessionInvalidCondition、refundPolicy、roomDynamic、countdown 等
  - `MutableSharedFlow`：hotelRoom UI State、commonProduct UI State（一次性事件）
  - `MutableLiveData`：paymentInstallmentData、summaryTotalPrice、showPaymentUncertainError 等
  - `Channel<ViewIntent>`：MVI 風格的意圖處理（CheckLockValidity）
- Reductor `Store<AppState>` 仍在使用中（透過 inject），部分狀態透過 Presenter 派發 Action

### Presenter 層（Reductor 橋接）
- `OrderFormFillingPresenter` 繼承 `RxBasePresenter`，負責 dispatch Action 至 Reductor Store
- 處理：getBookingData、clickPayButton、clickCheckCouponButton、clickScheduleDetail 等

### Reducer 層
- `OrderFormFillingReducer` 是 Reductor 架構下的核心狀態處理器
- 處理建單 (createOrder)、優惠券驗證、支付驗證、Stripe/GMO token 取得等副作用

### BookingStateHelper
- 持有 `BookingState` data class，封裝整個頁面所需狀態
- `BookingState` 包含：bookingInfo、bookingProductInfo、contactState、scheduleState、paymentStrategy、creditCard、coupon、invoice、points、refundPolicy 等
- 提供 `get*ViewInfo()` 方法將 BookingState 轉換為各 Delegate 所需的 ViewInfo
- **新 UI（V2）必填檢查**：`isAllRequiredFilledForV2()` → `isV2PaymentRequiredFieldsFilled()` 為付款按鈕的 gating，未通過會 `scrollToFirstUnfilledItem` 捲回未填欄位、不進付款。其中「存卡持卡人手機號」規則統一由純函式 `isSaveCardCardholderPhoneSatisfied()`（`view/product/form/CreditCardSaveCardRules.kt`）判斷，confirm 路徑（`OrderFormFillingActivity.checkBookingInfo`）與 V2 路徑共用同一條規則，避免分歧

### UseCase 層
- `GetCartProductsPriceUseCase`：取得商品最新價格（用於結帳前二次校驗）
- `GetCartProductsStatusUseCase`：檢查商品可售狀態（售罄、下架等）
- `GetProdSessionUseCase`：取得場次資訊（即時預訂場次庫存檢查）

### Repository 層
- `CheckoutRepository`：暫存結帳選擇的商品資料（記憶體快取）
- `CartProductsRepository`：透過 NetworkApi 查詢購物車商品價格與狀態
- `OrderFormFillingRepository`：Hotel V3 專用，提供 preCheck 價格、最新房價、ext data 查詢
- `CartRepository`：退換貨政策查詢 (getCartRefundPolicies)
- `BookingRepository`：取得 OrderSpecificationData

### API 層
- `getBookingData`：GET，取得訂單表單基礎資料（商品資訊、聯絡人預設值、取消政策等）
- `getPaymentChannelsData`：POST，取得可用支付方式清單
- `createOrder` / `createOrderV2`：POST，送出建單請求
- `getCartProductsPrices`：查詢商品最新價格
- `getCartProductsStatus`：查詢商品可售狀態
- `getPreCheckStatus`：Hotel V3 價格預檢
- `getOrderLatestRate`：Hotel V3 取得最新房價
- `getOrderExtData`：Hotel V3 取得擴展資料

---

## View 方法清單

| 方法 | 說明 |
|------|------|
| `onCreate()` | 初始化 Fragment 監聽、注入 router 參數、設定 ViewModel 資料、呼叫 initView/initAction/observeData |
| `initView()` | 設定 Toolbar、BottomSheet、RecyclerView ItemDecoration、確認付款按鈕點擊事件、建立 Adapter |
| `initAction()` | Hotel V3 初始化、Delegate 初始化、Launcher 註冊 |
| `observeData()` | 觀察 ViewModel 各種 StateFlow / LiveData / SharedFlow 狀態變更 |
| `getBookingData()` | 組裝參數呼叫 Presenter 取得訂單表單資料 |
| `getPaymentStrategyList()` | 呼叫 ViewModel 取得支付策略清單 |
| `setViewModelOriginPriceData()` | 從 Intent extra 取得上一頁帶過來的原始總價，用於變價提示 |
| `initHotelV3Request()` | Hotel Dynamic 產品初始化 preCheck 請求 |
| `handleReturnFromPayment()` | 處理第三方支付回調（各種 return URL 判斷） |

---

## ViewModel 方法清單

| 方法 | 說明 |
|------|------|
| `init` | 初始化各 Delegate（payment / pbCreateOrder / paymentStrategy / footer）、啟動 ViewIntent 處理 |
| `confirmClick()` | 結帳核心方法：依產品類型分流做二次校驗後建單 |
| `getProdSession()` | 取得即時預訂場次資訊並檢查庫存 |
| `setOriginPriceData()` | 設定前一頁帶入的原始價格與幣別 |
| `checkNewPriceAndCoupon()` | 比較新舊價格是否變動，發出變價通知 |
| `checkProductSoldOutOrNotUI()` | UI 層觸發的售罄檢查 |
| `requestRefundPolicy()` | 請求退換貨政策 |
| `triggerFreeCancelTooltips()` | 觸發免費取消提示文字 |
| `setPaymentStrategyList()` | 設定可用支付方式清單 |
| `setPaymentInstallmentDataList()` | 設定分期付款資料 |
| `setSummaryTotalPriceDouble()` | 更新摘要總價 |
| `setHotelV3PayTotalPrice()` | 設定 Hotel V3 支付總價 |
| `setOrderSpecificationData()` | 設定商品規格資料並計算 SKU 總數 |
| `getExtraDataForBookingForm()` | 取得場次相關的額外表單資料 |
| `setExtraBookingProd()` | 設定即時預訂商品資料 |
| `setCouponCode()` | 設定優惠碼 |
| `setFreeCancelToolTips()` | 設定免費取消提示 |
| `isTransNeedSavingUserProfile()` | 判斷交通類型是否需要儲存使用者資料 |
| `startObservingPaymentErrors()` | 開始監聽支付錯誤事件 |
| `handleViewIntent()` | 處理 MVI ViewIntent（目前支援 CheckLockValidity） |

---

## 業務邏輯摘要

- **二次價格校驗**：點擊確認付款時，會再次呼叫 API 確認商品價格是否變動或售罄，若有變動則顯示提示彈窗
- **多產品類型分流**：Hotel Dynamic、Hotel、ProdSession（即時預訂）、一般商品各有不同的結帳前校驗邏輯
- **支付方式多樣性**：整合 TapPay、Adyen、Stripe、LinePay、JkoPay、GooglePay、PayPay、AtomePay、KCP、GMO、PayDollar、PayMe、OnePay、TouchNGo、FPX、TossPay 等多種支付方式
- **GMO 綁卡（語系 ja + 幣別 JPY）**：新卡勾「儲存此卡」→ 付款 request 帶 `save_card=true`（`GMOPaymentHandler` 取 `bookingFormData().saveCard`），付款成功後由後端背景完成綁卡；已綁卡付款帶頂層 `payment_token_id` 並跳過 tokenize（reducer `checkGMOCreditCard` 入口分支）。**持卡人手機號依交易頻道（`transPmch`）分流**：僅 TapPay 顯示+檢查+帶值，GMO 等其他頻道整個隱藏、不檢查、不帶值（規格決議 GMO 綁卡不需手機號）。顯示邏輯（`CreditCardFormView.shouldShowPhoneFieldForSaveCard` 以 `isTapPayChannel` 判別，由 `CreditCardFormFactory` 於 ORDER_FLOW 帶入 `setTapPayChannel(transPmch==TAPPAY)`）與必填驗證 `isSaveCardCardholderPhoneSatisfied()` 採同一 TapPay 判別基準，購物車/結帳/獨立付款頁一致（早期顯示邏輯曾以 TWD 幣別判別，已對齊為交易頻道）
- **優惠券**：支援手動輸入優惠碼或從優惠券列表選取，驗證後重新計算價格
- **KK Points**：支援點數折抵
- **發票**：台灣市場且 TWD 幣別時顯示發票選項
- **免費取消提示**：結帳按鈕上方會顯示免費取消到期日提示
- **Priority Booking**：優先預訂流程，建單前需額外驗證
- **狀態管理混合架構**：Reductor (RxJava Observable) 與 Coroutines (StateFlow/SharedFlow/Channel) 並存
- **錯誤處理**：支付失敗可重試、網路錯誤顯示重試彈窗、商品售罄返回上一頁
- **交通類型特殊處理**：JR Rail、Airport 接送、高鐵、郵輪等各有額外的表單區塊與驗證邏輯

---

## 已知技術債

- ViewModel 直接依賴 Data 層（`CartRepository`、`OrderFormFillingRepository`、`CheckoutRepository`、`TransportationRepository`），未透過 Domain Contract 介面抽象
- Reductor（RxJava）與 Coroutines Flow/Channel 雙軌並存，狀態管理分散在 Presenter/Reducer 與 ViewModel 之間
- `OrderFormFillingReducer` 檔案龐大，包含建單、支付、優惠券等多種副作用邏輯，職責過多
- `OrderFormFillingActivity` 極為龐大（超過 2000 行），應拆分為更小的 Delegate 或改用 Compose
- UseCase（`GetCartProductsPriceUseCase`、`GetCartProductsStatusUseCase`）放在 `view/product/form` 下而非 `domain/usecase`，不符合理想的分層架構
- `BookingStateHelper` 同時承擔狀態管理與 ViewInfo 轉換職責，可進一步拆分

## 相關筆記
- [02-modules](../02-modules.md)
- [03-ui-patterns](../03-ui-patterns.md)
- [05-networking](../05-networking.md)
- [06-data-layer](../06-data-layer.md)
- [cart](cart.md)
- [credit-card-list](credit-card-list.md)
- [order-detail-compose](order-detail-compose.md)
- [order-success](order-success.md)
- [traveler-info](traveler-info.md)
- [voucher](voucher.md)

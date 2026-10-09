# 購物車頁面 技術文件

> 自動產生 | 最後更新：2026-03-20

---

## 概述

- **所在 Module**：`:app`
- **UI 入口**：`CartActivity.kt`
- **功能描述**：購物車頁面，讓使用者查看已加入購物車的商品清單、勾選/取消勾選商品、移除商品、套用優惠券、選擇支付方式，並進行結帳下單

---

## 檔案清單

```
UI（使用者介面入口）
 ├─ CartActivity.kt                        → app/.../view/cart/
 ├─ CartAdapter.kt                         → app/.../view/cart/
 ├─ CartMvpView.kt                         → app/.../view/cart/
 ├─ CartRouterImpl.kt                      → app/.../view/cart/
 ├─ AdapterData.kt                         → app/.../view/cart/
 └─ CartConstants.kt                       → app/.../view/cart/

Delegate（UI 區塊委派）
 ├─ CartContactDelegate.kt                 → app/.../view/cart/delegate/
 ├─ CartPointDelegate.kt                   → app/.../view/cart/delegate/
 ├─ CartStepsDelegate.kt                   → app/.../view/cart/delegate/
 ├─ CartViewInvalidProductDelegate.kt      → app/.../view/cart/delegate/
 └─ CartProductDelegate.kt                 → app/.../view/cart/delegate/product/

Compose UI（商品資訊 Compose 元件）
 ├─ CartProductInfoScreen.kt               → app/.../view/cart/delegate/product/
 ├─ CartProductContentScreen.kt            → app/.../view/cart/delegate/product/compose/
 ├─ CartProductContentViewInfo.kt          → app/.../view/cart/delegate/product/compose/
 ├─ CartProductCouponScreen.kt             → app/.../view/cart/delegate/product/compose/
 ├─ CartProductErrorMessageScreen.kt       → app/.../view/cart/delegate/product/compose/
 ├─ CartProductPointsScreen.kt             → app/.../view/cart/delegate/product/compose/
 ├─ CartProductTitleScreen.kt              → app/.../view/cart/delegate/product/compose/
 └─ CartProductTotalPriceScreen.kt         → app/.../view/cart/delegate/product/compose/

ViewModel（UI 狀態管理）
 └─ CartViewModel.kt                       → app/.../view/cart/

Presenter（Reductor 狀態橋接）
 └─ CartPresenter.kt                       → app/.../view/cart/

State（頁面狀態）
 ├─ CartStateHelper.kt                     → app/.../view/cart/
 ├─ CartState（data class）                → app/.../view/cart/CartStateHelper.kt
 └─ CartViewInfoConverter.kt               → app/.../view/cart/

Reducer（Reductor 狀態機）
 ├─ CartActions.kt                         → app/.../reducer/cart/
 └─ CartReducer.kt                         → app/.../reducer/cart/

過期商品頁面（子功能）
 ├─ CartExpiredActivity.kt                 → app/.../view/cart/expired/
 ├─ CartExpiredAdapter.kt                  → app/.../view/cart/expired/
 ├─ CartExpiredMvpView.kt                  → app/.../view/cart/expired/
 ├─ CartExpiredPresenter.kt                → app/.../view/cart/expired/
 ├─ CartExpiredViewInfoConvert.kt          → app/.../view/cart/expired/
 ├─ CleanAllDelegate.kt                    → app/.../view/cart/expired/
 └─ ProductDelegate.kt                     → app/.../view/cart/expired/

Domain（業務邏輯 UseCase）
 └─ GetProdSessionUseCase.kt              → app/.../view/share/useCase/

Data（資料層）
 ├─ CartRepository.kt（介面 + 實作）       → data/repository/.../
 └─ CartRepositoryImpl.kt（@Single）       → data/repository/.../CartRepository.kt

Network（API 定義）
 ├─ CartApiService.kt                      → libs/networking/api/.../service/cart/
 ├─ CartRefundPoliciesRequest.kt（Model）  → libs/model/.../
 └─ cartApiServiceModule.kt（DI）          → libs/networking/api/.../di/
```

---

## 資料流

### 主流程：頁面載入與商品清單取得

```
UI（CartActivity）
 │  onCreate → initView / initAction / observeData
 │  透過 Presenter.register() 訂閱 AppState
 ↓
Presenter（CartPresenter）
 │  register() 訂閱 cartRepository.getCartsFlow()
 │  cartProductsS 變化時呼叫 mvpView.updateData()
 ↓
CartStateHelper
 │  updateCartProducts() → 更新 CartState
 │  CartAdapter 依據 CartState 更新 RecyclerView
 ↓
ViewModel（CartViewModel）
 │  refreshView() → api.getCartProductsStatus()
 │  取得商品可用狀態後更新 UI
 ↓
Repository（CartRepositoryImpl）
 │  getCartsFlow() → DataStore 讀取本地購物車資料
 │  getCartRefundPolicies() → cartApiService.getCartRefundPolicies()
 ↓
API（CartApiService）
 │  POST v2/cart/refund-policies
 ↓
後端 API
```

### 回傳流

```
後端 API
 ↓
Repository：B2CApiResponse<Map<String, RefundPolicyInfo?>> → ApiResult<Map<String, RefundPolicyInfo?>>
 ↓
ViewModel：更新 _refundPolicyResult StateFlow / _cartProductStatusStateFlow SharedFlow
 ↓
UI：CartActivity 收集 Flow 更新畫面，CartAdapter 刷新列表
```

### 結帳流程：點擊付款按鈕

```
UI（CartActivity）
 │  clickPayButton() → 驗證表單資訊
 ↓
ViewModel（CartViewModel）
 │  clickBookingButton() → checkBookingInfo() 驗證 email/電話/持卡人
 │  → checkCartProductsPrices() 確認價格一致性
 │  → 若有 ProdSession 需先驗證場次
 ↓
Presenter（CartPresenter）
 │  clickPayButton() → store.dispatch(cartActions.clickPayButton(createOrderData))
 ↓
Reducer（CartReducer）
 │  處理 CLICK_CART_PAY_BUTTON action
 │  觸發建立訂單 API 呼叫
 ↓
AppState 更新 → Presenter 收到回調 → UI 更新付款結果
```

---

## 逐層說明

### UI 層
- `CartActivity` 繼承 `BookingBaseActivity`，實作 `CartMvpView` 介面
- 使用 `RecyclerView` + `CartAdapter`（Delegate 模式）呈現商品清單、聯絡人、支付方式等區塊
- 商品卡片內部使用 Compose 元件（`CartProductInfoScreen`、`CartProductContentScreen` 等）
- 底部結帳區域使用 `BottomSheetBehavior` 呈現價格摘要與付款按鈕
- 支援多種支付回調（LinePay、TapPay、Adyen、Stripe、GooglePay、Alipay 等），透過 `onNewIntent` 與 `ActivityResult` 處理

### ViewModel 層
- `CartViewModel` 使用 `@KoinViewModel` 注入，混合 LiveData + StateFlow + SharedFlow
- 委派模式：`PaymentStrategyViewModelDelegate`（支付策略）、`FooterViewModelDelegate`（頁尾）、`PaymentViewModelDelegate`（支付處理）
- 透過 Reductor `Store<AppState>` 與 RxJava `Observable<AppState>` 監聽全域狀態
- 商品狀態管理：`CartProductStatusState`（Loading / Loaded / Success / Error）
- 場次驗證：`getProdSession()` → 確認場次庫存是否售完

### Presenter 層
- `CartPresenter` 繼承 `RxBasePresenter<CartMvpView>`，作為 Reductor 狀態與 UI 之間的橋接
- `register()` 訂閱多個 AppState 屬性（語言、購物車商品、幣別、信用卡、錯誤訊息等）
- 所有使用者操作透過 `store.dispatch(cartActions.xxx())` 送入 Reductor

### State 層
- `CartStateHelper` 管理頁面完整狀態（`CartState`），包含商品列表、聯絡人、支付方式、優惠券、發票、KK Points 等
- `CartState.isAllRequiredFilled()` 判斷是否所有必填欄位完成，控制付款按鈕是否可點擊
- `CartViewInfoConverter` 將 `CartProductInfo` 轉換為 `CartProductViewInfo` 供 UI 使用

### Repository 層
- `CartRepositoryImpl` 使用 `@Single` 注入，繼承 `BaseApiRepository`
- 購物車資料儲存於 `DataStore`（key: `KEY_CART_LIST`），使用 Gson 序列化/反序列化
- `getCartsFlow()` 回傳 `Flow<List<CartProductInfo>>`，響應式資料源
- `getCartRefundPolicies()` 透過 `safeApiCallFlow` 呼叫 API 取得退款政策
- 無 domain:contract 介面分離（介面與實作在同一檔案）

### API 層
- `CartApiService`：定義退款政策查詢端點
  - `POST v2/cart/refund-policies` → 輸入 `CartRefundPoliciesRequest`，回傳 `Map<String, RefundPolicyInfo?>`
- 商品狀態與價格查詢使用舊版 `NetworkApi`（`api.getCartProductsStatus()`、`api.getCartProductsPrices()`），非透過 CartApiService

---

## View 方法清單

| 方法 | 說明 |
|------|------|
| `onCreate()` | 初始化 Presenter、ViewModel、StateHelper、UI 元件，設定 RecyclerView 與 BottomSheet |
| `initView()` | 設定 Toolbar、RecyclerView、BottomSheet 行為、付款按鈕 |
| `initAction()` | 綁定按鈕點擊事件（付款、繼續購物等） |
| `observeData()` | 收集 ViewModel 的 StateFlow/SharedFlow（商品狀態、場次、退款政策、價格不一致等） |
| `setupCreditCardSync()` | 設定信用卡狀態在 StateHelper 與 AppState 之間的雙向同步 |
| `onCartDataUpdated()` | CartState 更新時刷新 Adapter 與價格顯示 |
| `clickPayButton()` | 組裝 CreateOrderData 並觸發結帳流程 |
| `onProductCheckedChange()` | 勾選/取消勾選商品，更新 ViewModel 與 Presenter |
| `onClickDeleteProductButton()` | 顯示刪除確認 Dialog（CleanCartDialog） |
| `onClickScheduleDetailButton()` | 導航至旅遊資料填寫頁 |
| `onClickCouponButton()` | 導航至優惠券輸入頁 |
| `updateData()` | Presenter 回調，整合商品、語言、幣別、KK Points 更新 StateHelper |
| `updatePaymentResult()` | 處理付款結果，成功則導航至訂購成功頁 |
| `showPaymentErrorDialogOrLaunchRepay()` | 顯示付款錯誤 Dialog 或導向重新付款頁 |
| `showPaymentUncertainErrorDialog()` | 顯示付款結果不確定時的錯誤提示 Dialog |
| `navigateToOrderListAndFinish()` | 導航至訂單列表並結束當前頁面 |

---

## ViewModel 方法清單

| 方法 | 說明 |
|------|------|
| `init` | 初始化三個 Delegate（paymentStrategy、footer、payment） |
| `refreshView()` | 呼叫 API 檢查購物車商品狀態，更新可用性，觸發支付策略載入 |
| `fetchPaymentStrategyList()` | 根據已勾選商品取得可用支付方式列表 |
| `checkCartProduct()` | 切換商品勾選狀態，更新已勾選清單並重新載入支付策略 |
| `checkCartProductsPrices()` | 呼叫 API 確認商品價格是否與本地一致 |
| `comparePriceDifference()` | 比較本地價格與 API 回傳價格，找出不一致商品 |
| `getProdSession()` | 取得商品場次資訊，驗證庫存是否足夠 |
| `clickBookingButton()` | 結帳按鈕主邏輯：驗證表單 → 驗證場次 → 驗證價格 |
| `checkBookingInfo()` | 驗證 Email、電話、持卡人名稱格式是否正確 |
| `requestRefundPolicy()` | 呼叫 CartRepository 取得退款政策 |
| `trackerKTMPay()` | 追蹤結帳點擊事件（KTM Tracker） |
| `getExtraDataForBookingForm()` | 組裝場次選擇的額外資料供建立訂單使用 |
| `getBookingDataForProdSession()` | 將購物車商品轉換為場次查詢所需格式 |
| `startObservingPaymentErrors()` | 監聽 AppState 支付錯誤狀態 |
| `setSummaryTotalPriceDouble()` | 更新價格摘要資料（原價/折扣價） |
| `showInstallmentBottomSheetDialog()` | 觸發分期付款選擇 BottomSheet |
| `updateCouponBookingUserData()` | 更新優惠券使用的聯絡人資料至 Reductor |

---

## 業務邏輯摘要

- **購物車上限**：單次結帳最多勾選 10 筆商品（`CART_LIMIT_NUMBER_TO_BUY = 10`），超過上限的商品自動取消勾選
- **商品狀態檢查**：頁面載入時呼叫 API 驗證每筆商品是否仍可購買，不可用商品標記為 unavailable 並取消勾選
- **價格一致性驗證**：結帳前比對本地價格與 API 回傳價格，不一致則阻止結帳並提示使用者
- **場次驗證**：部分商品需選擇場次（Session），結帳前驗證場次庫存是否售完
- **本地儲存**：購物車資料存於 DataStore，非後端同步，使用 Gson 序列化 `List<CartProductInfo>`
- **支付整合**：支援多種支付方式（信用卡、LinePay、GooglePay、Alipay、TapPay、Adyen、Stripe、PayPay、PayMe、GMO、KCP、2C2P、TossPay、Atome、PayDollar、OnePay），每種有獨立的回調 URL
- **優惠券**：支援套用/刪除優惠券，與結帳填寫頁共用 Reductor 邏輯
- **KK Points**：支援折抵 KKday 點數，與支付策略聯動
- **發票**：台灣地區支援電子發票類型選擇
- **錯誤處理**：支付錯誤分為一般錯誤（顯示 Dialog）與不確定錯誤（導向訂單列表），Reductor 統一管理錯誤狀態
- **過期商品管理**：`CartExpiredActivity` 處理已過期商品的批次清除

---

## 已知技術債

- **雙重狀態管理**：同時使用 Reductor（CartPresenter + CartActions + CartReducer）與 ViewModel（CartViewModel + StateFlow），職責劃分不清晰，部分邏輯在 Presenter 處理、部分在 ViewModel
- **CartStateHelper 過度膨脹**：CartStateHelper 管理過多狀態與回調（700+ 行），應拆分為更小的 Delegate
- **RxJava 與 Coroutine 混用**：ViewModel 中 `api.getCartProductsStatus()` 使用 RxJava Observable 再透過 `asFlow()` 轉換，增加複雜度
- **Repository 介面未分離至 domain:contract**：`CartRepository` 介面與 `CartRepositoryImpl` 在同一檔案（`data/repository/`），未遵循理想的 Clean Architecture 分層
- **舊版 NetworkApi 直接呼叫**：商品狀態與價格查詢使用 `NetworkApi.sharedInstance()` 而非透過 Repository/ApiService，違反分層原則
- **GetProdSessionUseCase 位置不正確**：放在 `app/.../view/share/useCase/` 而非 `domain/usecase/`
- **LiveData 與 StateFlow 混用**：ViewModel 中部分欄位使用 LiveData、部分使用 StateFlow/SharedFlow，應統一

## 相關筆記
- [01-architecture](../01-architecture.md)
- [02-modules](../02-modules.md)
- [03-ui-patterns](../03-ui-patterns.md)
- [05-networking](../05-networking.md)
- [06-data-layer](../06-data-layer.md)
- [07-concurrency](../07-concurrency.md)
- [checkout](checkout.md)
- [order-detail-compose](order-detail-compose.md)
- [sku-activity-shell](sku-activity-shell.md)

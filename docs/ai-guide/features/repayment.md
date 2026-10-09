# 重新付款頁 技術文件

> 自動產生 | 最後更新：2026-07-15

---

## 概述

- **所在 Module**：`:app`
- **UI 入口**：`RepayActivity.kt`
- **功能描述**：針對未完成付款的訂單，讓使用者重新發起付款流程的頁面，整合多種支付方式（TapPay、Adyen、Stripe、GMO、LinePay、JkoPay、GooglePay 等）

---

## 檔案清單

```
UI（使用者介面入口）
 ├─ RepayActivity.kt             → app/.../view/repay/
 ├─ RepayAdapter.kt              → app/.../view/repay/
 ├─ RepayMvpView.kt              → app/.../view/repay/
 ├─ RepayGradientAppBar.kt       → app/.../view/repay/
 ├─ RepayConstants.kt            → app/.../view/repay/
 ├─ RepayProductViewInfo.kt      → app/.../view/repay/
 ├─ ProductDelegate.kt           → app/.../view/repay/
 ├─ ViewType.kt                  → app/.../view/repay/
 └─ TransMainOrderData.kt        → app/.../view/repay/

ViewModel（UI 狀態管理）
 └─ RepayViewModel.kt            → app/.../view/repay/

Presenter（Reductor 狀態橋接）
 └─ RepayPresenter.kt            → app/.../view/repay/

State（頁面狀態）
 └─ RepayState.kt                → app/.../view/repay/state/

Domain（業務邏輯 UseCase）
 ├─ GetRepayPageInfoUseCase.kt   → app/.../view/repay/domain/useCase/
 ├─ CheckCanOrderRepayUseCase.kt → app/.../view/repay/domain/useCase/
 ├─ GetPaymentResultUseCase.kt   → app/.../view/repay/domain/useCase/
 ├─ GetOrderCouponInfoUseCase.kt → app/.../view/repay/domain/useCase/
 ├─ GetPaymentChannelsUseCase.kt → app/.../view/repay/domain/useCase/
 ├─ CheckPriceUseCase.kt         → app/.../view/repay/domain/useCase/
 └─ CheckStockUseCase.kt         → app/.../view/repay/domain/useCase/

Data（資料層）
 ├─ RepayRepository.kt（介面）   → app/.../view/repay/domain/repository/
 └─ RepayRepositoryImpl.kt       → app/.../view/repay/data.repository/

Network（API 定義）
 └─ RepayApiService.kt           → app/.../view/repay/network/

DI（依賴注入）
 └─ RepayModule.kt               → app/.../view/repay/di/

外部依賴
 ├─ OrderRepository               → order_page 模組（國泰保險資訊）
 ├─ PaymentStrategyViewModelDelegate → share/booking 模組（支付策略清單）
 └─ UpdateOrderPaymentFailedUseCase  → order/domain 模組（付款失敗通報）
```

---

## 資料流

### 主流程：頁面載入 / 取得重新付款資訊

```
UI（RepayActivity）
 │  onResume → initAction()
 │  呼叫：viewModel.getRepayPageInfo(activity, orderMasterMid)
 ↓
ViewModel（RepayViewModel）
 │  並行呼叫三個 UseCase（combine）：
 │  ├─ checkCanOrderRepayUseCase(orderMasterMid)
 │  ├─ getPaymentResultUseCase(orderMasterMid)
 │  └─ getOrderCouponInfoUseCase(orderMasterMid)
 │
 │  三者成功後 → getPaymentStrategyList()（透過 PaymentStrategyViewModelDelegate）
 ↓
UseCase 層
 │  CheckCanOrderRepayUseCase → repository.checkCanOrderRepay()
 │  GetPaymentResultUseCase   → repository.getPaymentResultByOrderMId()
 │  GetOrderCouponInfoUseCase → repository.getOrderCouponInfo()
 ↓
Repository（RepayRepositoryImpl）
 │  apiService.checkCanOrderRepay()
 │  apiService.getPaymentResultByOrderMId()
 │  apiService.getOrderCouponInfo()
 ↓
API（RepayApiService）
 │  GET v2/cart/payment/check/{order_master_mid}
 │  GET v3/cart/info/{order_master_mid}
 │  GET v2/cart/{order_master_mid}/coupons
 ↓
後端 API
```

### 付款按鈕流程

```
UI（RepayActivity）
 │  clickPayButton()
 │  ├─ 交通類商品 → viewModel.confirmProductsPriceAndStock()
 │  │   ├─ CheckPriceUseCase → GET v2/trans/check_price/{service_name}/{order_mid}
 │  │   └─ CheckStockUseCase → GET v2/trans/check_available/{service_name}/{order_mid}
 │  └─ 一般商品 → proceedPayment()
 ↓
proceedPayment()
 │  根據 PaymentStrategy 類型分流：
 │  ├─ TappayCreditCardStrategy → repayPresenter.clickRepayButton()
 │  ├─ StripeCreditCardStrategy → repayPresenter.clickStripeRepayButton()
 │  ├─ GMOStrategy              → repayPresenter.clickGMORepayButton()
 │  ├─ AdyenGooglePayStrategy   → repayPresenter.clickRepayButton()（須先於 AdyenStrategy 攔截；建單後於 launchGooglePay 啟動 Adyen GooglePayComponent 原生視窗，onSubmit 取 token → createAdyenGooglePayPayment）
 │  ├─ AdyenStrategy            → showAdyenCreditCardDialog()
 │  └─ 其他（LinePay 等）       → repayPresenter.clickRepayButton()
 ↓
RepayPresenter
 │  store.dispatch(cartActions.clickRepayButton(orderRepayData))
 ↓
Reductor Store → 後續支付中介層處理
```

### 回傳流

```
後端 API
 ↓
Repository：B2CApiResponse<T> → Flow<ApiResult<T>>（safeApiCall 封裝）
 ↓
UseCase：mapError() 轉換錯誤碼為在地化字串資源
 ↓
ViewModel：combine 三個 Flow → RepayPageInfoState（sealed class）
 ↓
UI（RepayActivity）：collect repayPageInfoState
 ├─ Loading → 顯示載入中
 ├─ Success → 更新商品列表、金額、支付方式列表、倒數計時
 └─ Error   → 顯示錯誤訊息
```

---

## 逐層說明

### UI 層

`RepayActivity` 繼承 `BookingActivity`，同時實作 `RepayMvpView`、`PaymentReturn`、`InstallmentBottomSheetDialogFragment.Interaction` 三個介面。採用 **MVVM + Reductor 雙軌架構**：

- **ViewModel 負責**：頁面資料載入、狀態管理（`RepayPageInfoState`）、倒數計時、價格/庫存確認
- **Presenter（Reductor）負責**：支付流程的狀態管理（信用卡驗證、支付結果回傳、第三方支付回調）

UI 透過 `RepayAdapter`（繼承 `BookingAdapter`）以 RecyclerView 方式呈現商品資訊與支付方式選擇。`RepayAdapter` 內部使用 `CartStateHelper` 管理支付相關的 UI 狀態。

路由透過 `@Router(KRouterConst.PAGE_REPAY)` 註冊，支援 DeepLink 進入。

### ViewModel 層

`RepayViewModel` 使用 `StateFlow`（主要）+ `LiveData`（分期付款 dialog）混合管理狀態：

- `repayPageInfoState: StateFlow<RepayPageInfoState>` — 頁面主狀態（Loading/Loaded/Success/Error）
- `repayTimeLeft: StateFlow<String>` — 付款倒數計時
- `confirmProductsPriceAndStockResult: StateFlow<ApiResult<...>>` — 交通類商品的價格/庫存檢查
- `cathayInsuranceInfo: StateFlow<List<CathayInsuranceInfo>?>` — 國泰保險推薦
- `showPaymentUncertainError: LiveData<Boolean>` — PaymentResult API 錯誤的統一 dialog

透過 `PaymentStrategyViewModelDelegate` 委託取得支付管道清單，並過濾掉不允許的支付方式（根據優惠券限制）和離線支付（`OfflineStrategy`）。

### UseCase 層

`GetRepayPageInfoUseCase` 為組合型 UseCase（data class），聚合五個子 UseCase：

| UseCase | 職責 |
|---------|------|
| `CheckCanOrderRepayUseCase` | 檢查訂單是否可重新付款，取得付款截止時間與金額 |
| `GetPaymentResultUseCase` | 取得訂單的付款結果與商品明細 |
| `GetOrderCouponInfoUseCase` | 取得訂單的優惠券資訊（含允許的支付方式與信用卡 BIN 碼） |
| `CheckPriceUseCase` | 檢查交通商品價格是否有變動 |
| `CheckStockUseCase` | 檢查交通商品庫存是否充足 |

錯誤碼對應：`OM05` → 訂單已完成交易、`100020` → 請確認訂單狀態。

### Repository 層

`RepayRepositoryImpl` 繼承 `BaseApiRepository`，使用 `safeApiCall` 封裝 Retrofit 呼叫為 `Flow<ApiResult<T>>`。純粹的 API 呼叫代理，無快取邏輯。

### API 層

`RepayApiService` 定義六個 Endpoint：

| Endpoint | 方法 | 用途 |
|----------|------|------|
| `v2/cart/payment/check/{order_master_mid}` | GET | 檢查可否重新付款 |
| `v3/cart/info/{order_master_mid}` | GET | 取得付款結果與商品明細 |
| `v2/cart/{order_master_mid}/coupons` | GET | 取得優惠券資訊 |
| `v2.1/payment/booking/channels` | GET | 取得可用支付管道 |
| `v2/trans/check_price/{service_name}/{order_mid}` | GET | 交通商品價格檢查 |
| `v2/trans/check_available/{service_name}/{order_mid}` | GET | 交通商品庫存檢查 |

---

## View 方法清單

| 方法 | 說明 |
|------|------|
| `onCreate()` | 注入路由參數、綁定 Presenter、初始化 View 與觀察資料、檢查登入狀態、處理錯誤訊息 |
| `onNewIntent()` | 處理第三方支付回調的 DeepLink |
| `onActivityResult()` | 處理登入回調與取消訂單回調 |
| `onResume()` | 已登入時觸發 initAction 載入資料 |
| `onDestroy()` | 關閉 Dialog、Detach Presenter |
| `onBackPressed()` | 顯示關閉頁面確認 Dialog |
| `initView()` | 初始化 RepayAdapter、RecyclerView、AppBar 折疊效果、確認付款按鈕、CreditCard 同步 |
| `setupCreditCardSync()` | 建立 StateHelper 與 AppState 之間的信用卡資料雙向同步 |
| `observeData()` | 觀察 ViewModel 的所有 StateFlow/LiveData，包含頁面狀態、倒數計時、支付認證、支付結果檢查、分期付款、價格庫存確認 |
| `initAction()` | 呼叫 viewModel.getRepayPageInfo() 載入頁面資料 |
| `clickPayButton()` | 付款按鈕點擊：交通商品先檢查價格庫存，一般商品直接進入 proceedPayment |
| `proceedPayment()` | 依支付策略類型分流處理付款（TapPay/Stripe/GMO/Adyen/其他） |
| `checkCreditCard()` | 驗證信用卡 BIN 碼是否在優惠券允許清單中 |
| `checkAdyenCreditCard()` | Adyen 信用卡 BIN 碼驗證 |
| `showTimeOutDialog()` | 付款逾時 Dialog |
| `showClosePageDialog()` | 離開頁面確認 Dialog |
| `showTransportationCheckErrorDialog()` | 交通商品價格/庫存異常 Dialog（含重新導向連結） |
| `showPaymentUncertainErrorDialog()` | PaymentResult API 不確定錯誤的統一 Dialog，引導用戶至訂單列表 |
| `handleReturnFromPayment()` | 處理各種第三方支付回調（依 host 判斷是哪個支付管道） |
| `launchOrderPage()` | 導航至訂單列表頁 |
| `launchHome()` | 導航至首頁 |

---

## ViewModel 方法清單

| 方法 | 說明 |
|------|------|
| `init` | 初始化 PaymentStrategyViewModelDelegate |
| `setOrderIdAndType()` | 設定訂單 ID 與交通類型清單（從 SummaryData 過濾排序） |
| `saveOrderMid()` | 儲存 orderMid 至 StateFlow |
| `updateOrderPaymentFailed()` | 通報付款失敗（呼叫 UpdateOrderPaymentFailedUseCase） |
| `resetConfirmPriceAndStockStatus()` | 重置價格庫存確認狀態為 Loading |
| `confirmProductsPriceAndStock()` | 並行檢查所有交通訂單的價格與庫存，任一失敗即中斷 |
| `getRepayPageInfo()` | 頁面主要資料載入：combine 三個 API 結果 → 取得支付管道 → 更新頁面狀態 |
| `trackPay()` | 追蹤付款按鈕點擊事件（KTM） |
| `setPaymentInstallmentDataList()` | 設定分期付款資料 |
| `setSummaryTotalPriceDouble()` | 設定總價資料（供分期付款 BottomSheet 使用） |
| `showInstallmentBottomSheetDialog()` | 觸發顯示分期付款 BottomSheet |
| `checkPaymentUncertainError()` | 檢查 PaymentResult 是否有不確定錯誤狀態（精準攔截） |
| `onPaymentUncertainErrorConfirmed()` | 確認不明確付款錯誤 Dialog |

---

## 業務邏輯摘要

- **付款時間限制**：頁面載入後顯示倒數計時，逾時後點擊付款按鈕會顯示逾時 Dialog
- **三 API 並行載入**：checkCanOrderRepay、getPaymentResult、getOrderCouponInfo 三者使用 `combine` 並行請求，全部成功後才進入支付管道取得流程
- **支付方式過濾**：根據優惠券的 `allowedPaymentMethods` 過濾可用支付方式，且排除 `OfflineStrategy`
- **信用卡 BIN 碼限制**：優惠券可能限制僅允許特定信用卡 BIN 碼，付款前會驗證
- **交通商品特殊處理**：交通類商品付款前需額外檢查價格與庫存（並行呼叫所有訂單的 checkPrice + checkStock），任一失敗即中斷並顯示錯誤 Dialog
- **雙軌狀態管理**：ViewModel（StateFlow）管理頁面資料載入狀態，Presenter（Reductor）管理支付流程狀態。兩者透過 `setupCreditCardSync()` 同步信用卡資料
- **支付回調處理**：支援十多種第三方支付的回調（透過 DeepLink），於 `handleReturnFromPayment()` 依 host 判斷分流
- **PaymentResult 不確定錯誤**：若 PaymentResult API 返回有效資料但 Reductor Store 有 paymentErrorMessage，視為不確定錯誤，顯示統一 Dialog 引導用戶至訂單列表
- **國泰保險推薦**：交通商品（排除 THSRTW、RAIL_EUROPE、ZZIMAIR、UNIAIRHOLIDAYS）會額外請求保險推薦資訊
- **錯誤處理**：UseCase 層透過 `mapError` 將 API 錯誤碼（OM05、100020）對應至在地化錯誤訊息

---

## 已知技術債

- **UseCase / Repository / API 皆在 `:app` 模組內**：domain/repository/network 分層放在 `app/.../view/repay/` 內部子目錄，未抽至獨立的 `:domain:contract`、`:data:repository`、`:data:networking:api` 模組
- **MVVM + Presenter 雙軌架構**：ViewModel 與 RepayPresenter（Reductor）並存，信用卡狀態需透過 `setupCreditCardSync()` 手動同步，增加維護複雜度
- **LiveData 與 StateFlow 混用**：部分狀態用 StateFlow（主頁面狀態），部分用 LiveData（分期付款 dialog、支付不確定錯誤），風格不一致
- **RepayAdapter 繼承 BookingAdapter**：大量 override 方法為空實作（`DO NOTHING`），表示 BookingAdapter 的抽象層級不適合重新付款場景
- **GetRepayPageInfoUseCase 為 data class**：僅作為子 UseCase 的容器，不具業務邏輯封裝
- **onResume 整頁重載與 Adyen Google Pay 返回衝突**：`onResume() → initAction() → getRepayPageInfo()` 每次 resume 重載整頁；從 Adyen Google Pay 原生視窗返回時，此重載會使 loading 卡死並誤觸付款方式重繪彈出信用卡 dialog。以 `isReturningFromAdyenGooglePay` 旗標在返回那次略過重載（KKAPP-5940）作為權宜守門，根因（onResume 無條件重載）未整治

## 相關筆記
- [01-architecture](../01-architecture.md)
- [02-modules](../02-modules.md)
- [03-ui-patterns](../03-ui-patterns.md)
- [05-networking](../05-networking.md)
- [06-data-layer](../06-data-layer.md)
- [07-concurrency](../07-concurrency.md)
- [order-cancel](order-cancel.md)
- [order-detail-compose](order-detail-compose.md)
- [sku-activity-shell](sku-activity-shell.md)

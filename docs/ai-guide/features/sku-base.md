# 規格選擇基底頁（通用） 技術文件

> 自動產生 | 最後更新：2026-03-19

---

## 概述

- **所在 Module**：`:app`
- **UI 入口**：`SharedSpecificationActivity.kt`（abstract）、`CommonSpecificationActivity.kt`（具體實作）
- **功能描述**：商品規格選擇的基底/通用頁面，提供日期選擇、票種數量選擇、套餐選擇等核心 SKU 選擇邏輯，被其他規格選擇頁（票券、飯店 Bundle 等）繼承或組合使用。

---

## 檔案清單

```
UI（使用者介面入口）
 ├─ SharedSpecificationActivity.kt（abstract 基底）  → app/.../product/specification/
 ├─ CommonSpecificationActivity.kt（通用實作）        → app/.../product/specification/
 ├─ SharedSpecificationFragment.kt（Fragment 基底）   → app/.../product/specification/fragment/
 └─ CommonSpecificationFragment.kt（通用 Fragment）   → app/.../product/specification/fragment/

ViewModel（UI 狀態管理）
 ├─ SpecificationSharedViewModel.kt                  → app/.../product/specification/
 └─ SkuSharedViewModel.kt                            → app/.../product/specification/

Presenter（Reductor 狀態管理，漸進遷移中）
 └─ SpecificationPresenter.kt                        → app/.../product/specification/

狀態與模型
 ├─ SpecificationStateHelper.kt（狀態管理核心）       → app/.../product/specification/
 ├─ SkuSelectionState.kt（SKU 選擇狀態模型）          → app/.../product/specification/
 ├─ SkuPruningCalculator.kt（SKU 剪枝計算器）         → app/.../product/specification/
 ├─ SkuIntentHandler.kt（SKU 操作介面）               → app/.../product/specification/
 ├─ SpecificationMvpView.kt（MVP View 介面）          → app/.../product/specification/
 └─ SpecificationTrackDataUseCase.kt（追蹤資料組裝）  → app/.../product/specification/

Domain（業務邏輯 UseCase）
 ├─ GetProductDetailUseCase.kt        → libs/feature/product_page/.../useCase/
 ├─ GetProductPackagesUseCase.kt      → libs/feature/product_page/.../useCase/
 ├─ CalculateBundlePriceUseCase.kt    → domain/usecase/.../bundle/
 ├─ GetBundleDetailUseCase.kt         → domain/usecase/.../bundle/
 └─ GetHotelVTagUseCase.kt            → domain/usecase/.../hotel/

Data（資料層）
 ├─ SkuRepository.kt（本地 API 調用層） → app/.../product/specification/
 ├─ ProductRepository（介面）           → domain/contract 或 data/repository
 ├─ CartRepository                      → data/repository/
 └─ HotelProductRepository             → data/repository/

Network（API 定義）
 ├─ IProductApiService（商品 API）      → data/networking/api/
 ├─ IHotelProductApiService（飯店 API） → data/networking/api/
 └─ KKApi.b2cApi.product（底層 API）    → data/networking/api/
```

---

## 資料流

### 主流程：頁面載入 / 規格資料取得

```
UI（CommonSpecificationActivity / SharedSpecificationActivity）
 │  onCreate → initData() → viewModel.setExtras() → viewModel.viewReady()
 ↓
ViewModel（SpecificationSharedViewModel）
 │  viewReady() → initRequestData()
 │  並發呼叫：
 │    1. updateProductPackageCalendar() — 取得日曆資料
 │    2. updateProductDetail()          — 取得商品詳情
 │    3. updateProductPackages()        — 取得方案清單
 ↓
UseCase
 │  GetProductDetailUseCase → ProductRepository
 │  GetProductPackagesUseCase → ProductRepository
 ↓
Repository / SkuRepository
 │  SkuRepository.getProductPackageCalendarDataAPI()
 │  ProductRepository.getProductDetail()
 │  ProductRepository.getProductPackages()
 ↓
API（KKApi.b2cApi.product）
 │  GET v2/product/{product_mid}/calendar
 │  GET v2/product/{product_mid}
 │  GET v2/product/{product_mid}/pkg
 ↓
後端 API
```

### 規格選擇流程：使用者選擇套餐 / 日期 / 票種

```
UI（CommonSpecificationFragment）
 │  Epoxy Controller 觸發 specificationListener 回呼
 │  ├─ onEventButtonClicked()   — 場次選擇
 │  ├─ onSpecButtonClicked()    — 規格選擇
 │  └─ onCountButtonClicked()   — 票種數量選擇
 ↓
ViewModel（SpecificationSharedViewModel）
 │  stateHelper.updateEventStatus / updateSpecStatus / updateCountStatus
 │  clickSku() → 重新計算價格與可用性
 │  updateState() → _specificationStateFlow.emit(newState)
 ↓
StateHelper（SpecificationStateHelper）
 │  更新 SpecificationState（含日曆、方案、規格、數量）
 │  SkuPruningCalculator 計算各選項可用性
 ↓
UI（Fragment 觀察 specificationStateFlow）
 │  debounce(100ms) → specificationController.specificationState = state
 │  Epoxy Controller 重新渲染 UI
```

### 確認下單流程

```
UI（SharedSpecificationActivity）
 │  layoutConfirmField 按鈕點擊
 │  → 檢查 state.isAllRequiredFilled()
 │  → clickConfirmButton()
 ↓
ViewModel
 │  checkShouldShowESimReminder() — 檢查是否需顯示 eSIM 提醒
 ↓
Presenter（SpecificationPresenter）
 │  clickConfirmButton() → store.dispatch(specificationActions.clickConfirmButton())
 │  Reductor Store 處理 → isSpecCheckingSuccess 狀態更新
 ↓
Activity（observeData）
 │  launchOrderFormFillingPage() 或 CartActivity
```

### 回傳流

```
後端 API
 ↓
SkuRepository / ProductRepository：Response → Domain Model
 ↓
ViewModel：透過 SpecificationStateHelper 更新 SpecificationState
 ↓
UI：觀察 specificationStateFlow（debounce 100ms），Epoxy Controller 更新畫面
```

---

## 逐層說明

### UI 層

`SharedSpecificationActivity` 為 abstract 基底類，繼承 `BaseActivity`，實作 `SpecificationMvpView` 介面。onCreate 時依序執行 `initDelegate()` → `initData()` → `initView()` → `observeData()`。透過 `initFragment()` abstract 方法由子類決定要顯示哪個 Fragment：

- `CommonSpecificationActivity`：依據 vertical type 選擇 `CommonSpecificationFragment`（通用）、`FnbSpecificationFragment`（餐飲）、`BundleSkuFragment`（飯店組合）。

Fragment 層使用 Epoxy RecyclerView（`SharedSpecificationController`）渲染規格選擇 UI，觀察 `specificationStateFlow` 更新畫面。Fragment 透過 `activityViewModel` 取得 Activity scope 的 ViewModel 實例。

### ViewModel 層

`SpecificationSharedViewModel` 為核心 ViewModel，使用 `@KoinViewModel` 注入，主要狀態管理方式：

- **`MutableStateFlow<SpecificationState>`**：核心狀態流，包含日曆、方案、規格、數量、價格等所有規格選擇狀態
- **`MutableSharedFlow`**：用於一次性事件（Toast、SKU 點擊、loading 等）
- **`SpecificationStateHelper`**：封裝狀態更新邏輯的 helper，根據是否為 Bundle 產品自動切換為 `HotelSpecificationStateHelper`

提供 `calendarViewListener`（日曆選擇回呼）和 `specificationListener`（規格/數量選擇回呼）給 Fragment 使用。

### Presenter 層（Reductor，漸進遷移中）

`SpecificationPresenter` 使用 Reductor（Redux-like）架構，透過 `Store<AppState>` dispatch actions，處理：
- 登入狀態同步 → 更新確認按鈕
- 確認下單檢查 → `isSpecCheckingSuccess` 狀態
- KK Points 計算
- 錯誤訊息顯示/隱藏

此為技術債，部分邏輯已遷移至 ViewModel，但確認下單流程仍透過 Reductor 處理。

### SKU 剪枝計算層

`SkuPruningCalculator` 根據已選條件（日期、場次、規格、票種）計算各選項的可用性。核心資料模型：
- `SkuSelectionState`：記錄使用者當前選擇
- `SkuPruningResult`：計算後各維度的可用性（`DateAvailability`、`EventAvailability`、`SpecAvailability`、`TicketAvailability`）

`SkuIntentHandler` 定義 SKU 操作介面（`initSkuApiData`、`selectDate`、`selectEvent`、`selectSpec`、`selectTicketQuantity`）。

### Repository / Data 層

`SkuRepository`（`@Single`）負責純 API 調用，使用 `KKApi.b2cApi.product`：
- `getProductPackageDataAPI()` — `GET v2/product/{product_mid}/pkg`
- `getProductPackageCalendarDataAPI()` — `GET v2/product/{product_mid}/calendar`
- `getProductPackageItemCalendarAPI()` — `GET v2/product_item/{item_oid}/calendar`
- `getOrderKKPointsInfo()` — `POST v2/points/estimate`

另外透過 UseCase 使用 `ProductRepository`、`CartRepository`、`HotelProductRepository`。

### API 層

| API | HTTP 方法 | Endpoint | 用途 |
|-----|----------|----------|------|
| 商品詳情 | GET | `v2/product/{product_mid}` | 取得商品基本資訊 |
| 方案清單 | GET | `v2/product/{product_mid}/pkg` | 取得所有方案與規格 |
| 方案日曆 | GET | `v2/product/{product_mid}/calendar` | 取得可售日期與價格 |
| 方案項目日曆 | GET | `v2/product_item/{item_oid}/calendar` | 取得特定方案項目的日曆 |
| KK Points 預估 | POST | `v2/points/estimate` | 計算可獲得積分 |

---

## View 方法清單（SharedSpecificationActivity）

| 方法 | 說明 |
|------|------|
| `onCreate()` | 初始化 Window、Presenter、Delegate、Data、View、觀察資料 |
| `initData()` | 從 Intent/SpecificationData 取得參數，傳入 ViewModel |
| `initView()` | 設定 toolbar、fragment、按鈕事件、eSIM 提醒 Dialog |
| `initFragment()` | abstract — 由子類決定載入哪個 Fragment |
| `initOtherView()` | 子類可覆寫的額外 UI 初始化 |
| `viewReady()` | 通知 ViewModel 頁面準備完成 |
| `observeData()` | 觀察 ViewModel 的各種 StateFlow/SharedFlow |
| `selectedPackageId()` | 選擇方案後通知 ViewModel 和 Presenter |
| `updateLayoutConfirmField()` | 根據狀態更新底部確認欄位（價格、按鈕、優惠提示） |
| `updateTextTitle()` | 根據日期選擇模式更新 toolbar 標題 |
| `clickConfirmButton()` | 檢查票種數量限制、追蹤、eSIM 提醒檢查 |
| `clickButtonReselect()` | 重選按鈕 — 清除方案與資料、重新載入 |
| `onSKUClick()` | SKU 點擊回呼 — KK Points 更新、自訂監聽 |
| `updateConfirmButton()` | MVP View 實作 — 依登入狀態設定按鈕文字與行為 |
| `launchOrderFormFillingPage()` | 規格確認成功後導向購物車或結帳填寫頁 |
| `showOrHideErrorMessage()` | 顯示/隱藏錯誤訊息 |
| `onChildResume()` | Resume 時處理登入返回後自動下一步 |
| `onDestroy()` | 清除 stateHelper、detach Presenter、dismiss loading |
| `getProductId()` | 取得商品 ID（from SpecificationData or Intent） |
| `isAddToCart()` | 判斷是否為加入購物車模式 |
| `getVerticalType()` | 取得垂直類型（DEFAULT/HOTEL/FNB 等） |
| `getSelectedBundleId()` | 取得已選 Bundle ID |
| `openHotelDetailSheet()` | 開啟飯店房型詳情 Compose BottomSheet |

---

## ViewModel 方法清單（SpecificationSharedViewModel）

| 方法 | 說明 |
|------|------|
| `init` | 初始化 PB delegate、啟動 KTM spec/calendar 變更追蹤、收集 debounce count flow |
| `setExtras()` | 設定來自 Activity 的初始參數（productId、packageId、bundle 條件等） |
| `viewReady()` | 觸發 `initRequestData()`，並發取得日曆、商品詳情、方案資料 |
| `initRequestData()` | 核心初始化：更新幣別/語言、取得日曆/商品/方案資料、處理 Bundle/預選方案 |
| `selectPackage()` | 選擇方案 — 更新方案狀態、取得項目日曆、更新規格、觸發追蹤 |
| `autoSelectBundlePackage()` | Bundle 商品自動預選方案邏輯 |
| `loadMorePackageCalendarData()` | 載入更多月份的日曆資料（並發取得 package calendar + item calendar） |
| `updateProductPackageCalendar()` | 呼叫日曆 API 更新日曆資料 |
| `updateProductDetail()` | 呼叫 GetProductDetailUseCase 更新商品詳情 |
| `updateProductPackages()` | 呼叫 GetProductPackagesUseCase 更新方案清單 |
| `updatePackageCalendarData()` | 更新方案日曆資料（含 FnB 規格檢查） |
| `clickSku()` | SKU 選擇核心 — 透過 stateHelper 重算可用選項、發送 skuClickFlow |
| `collectDebounceCountFlow()` | 收集數量變更（debounce），重算條件並更新日曆 |
| `emitCountInfo()` | 發送數量變更事件 |
| `generateConditions()` | 根據規格類型（TICKET_SPEC/單規單票）生成 Condition 列表 |
| `checkFnbSpec()` | 餐飲商品規格檢查 |
| `updateState()` | 更新 `_specificationStateFlow` |
| `setSelectedPackageId()` | 設定已選方案 ID |
| `checkShouldShowESimReminder()` | 檢查是否需顯示 eSIM 購買提醒 |
| `fetchESimDeviceLink()` | 取得 eSIM 支援裝置連結 |
| `calendarViewListener` | 日曆選擇回呼物件 — 處理日期選擇、不可用日期、日期範圍限制 |
| `specificationListener` | 規格選擇回呼物件 — 處理場次/規格/數量按鈕點擊 |
| `roomPackageCardClickListener` | 飯店房型卡片點擊回呼 — 圖片預覽、詳情、選擇 |
| `triggerTrackDataChanged()` | 觸發 KTM 追蹤資料更新 |
| `track*()` | 各種追蹤方法（日曆、方案、規格、錯誤等） |

---

## 業務邏輯摘要

- **多類型商品支援**：透過 `getVerticalType()` 區分 DEFAULT（通用）、HOTEL（飯店）、FNB（餐飲）等垂直類型，分別載入不同的 Fragment 和狀態管理邏輯
- **日曆按月載入**：初始載入第一個月，使用者翻頁時 `loadPageDataListener()` 觸發 `loadMorePackageCalendarData()` 取得下個月資料
- **SKU 剪枝**：`SkuPruningCalculator` 根據已選條件計算各維度（日期/場次/規格/票種）的可用性，鎖定不可選項目
- **方案選擇**：選擇方案後並發取得 item calendar，更新規格、場次、價格
- **數量 debounce**：票種數量變更透過 `clickCountFlow` debounce 處理，避免頻繁 API 呼叫
- **Bundle 商品**：飯店組合商品有獨立的 `HotelSpecificationStateHelper`，支援房型選擇、Bundle 價格計算
- **Priority Booking**：支援優先預訂驗證流程，未驗證時顯示 BottomSheet
- **eSIM 提醒**：eSIM 商品在確認前顯示裝置相容性提醒 Dialog
- **KK Points**：選擇規格後計算可獲得積分（透過 Presenter throttle 1s 呼叫 API）
- **確認下單流程**：經由 Reductor Presenter dispatch action，檢查通過後導向 `OrderFormFillingActivity`（直購）或 `CartActivity`（加入購物車）
- **雙狀態管理架構（技術債）**：ViewModel 使用 StateFlow 管理 UI 狀態，同時 Presenter 使用 Reductor Store 管理確認下單與登入狀態，兩者並存

---

## 已知技術債

- **Presenter + Reductor 並存**：`SpecificationPresenter` 仍使用 Reductor `Store<AppState>` 處理確認下單、登入、KK Points 等邏輯，與 ViewModel 的 StateFlow 架構並存，增加維護複雜度
- **SkuRepository 未抽介面**：`SkuRepository` 放在 app 層且未實作 domain:contract 介面，直接在 ViewModel 中使用
- **SpecificationStateHelper 放在 app 層**：核心狀態管理邏輯未遷移至 domain 或 feature module
- **ViewModel 依賴過多**：`SpecificationSharedViewModel` 建構子注入超過 15 個依賴，職責過重
- **RxJava + Coroutines 混用**：Presenter 使用 RxJava，ViewModel 使用 Coroutines，跨層需要 `asFlow()` 轉換

## 相關筆記
- [01-architecture](../01-architecture.md)
- [02-modules](../02-modules.md)
- [03-ui-patterns](../03-ui-patterns.md)
- [05-networking](../05-networking.md)
- [06-data-layer](../06-data-layer.md)
- [07-concurrency](../07-concurrency.md)
- [order-detail-compose](order-detail-compose.md)
- [product-detail](product-detail.md)
- [sku-activity-shell](sku-activity-shell.md)
- [sku-fragment-v3](sku-fragment-v3.md)

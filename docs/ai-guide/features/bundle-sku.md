# 套票 Bundle SKU 選擇頁 技術文件

> 自動產生 | 最後更新：2026-03-20

---

## 概述

- **所在 Module**：`:app`
- **UI 入口**：`TicketBundleSKUFragment.kt`
- **功能描述**：套票（Bundle）商品的 SKU 選擇頁面，讓使用者選擇套票組合內的主商品與各項子商品的規格、數量與日期，並即時計算組合價格。

---

## 檔案清單

```
UI（使用者介面入口）
 ├─ TicketBundleSKUFragment.kt           → app/.../product/specification/multiple/ticket/bundle/view/
 ├─ VMCalendarScreenFragment.kt          → app/.../product/specification/multiple/ticket/bundle/view/
 └─ MultipleSpecificationActivity.kt     → app/.../product/specification/multiple/ticket/view/（Activity 殼）

UI 容器與元件
 ├─ EnhancedTicketBundleContainer.kt     → app/.../bundle/adapter/（響應式 UI 容器，管理資料綁定與自動刷新）
 ├─ TicketBundleScrollViewContainer.kt   → app/.../bundle/adapter/（ScrollView + LinearLayout 基底容器）
 ├─ TicketBundleSubPackageWidget.kt      → app/.../bundle/view/widget/（子商品規格 Widget）
 ├─ BundleCountItemView.kt              → app/.../bundle/view/widget/（數量選擇元件）
 └─ TicketSpecTextView.kt               → app/.../bundle/view/widget/

Adapter ViewHolder
 ├─ BundleSpecificationViewHolder.kt     → app/.../bundle/adapter/viewholder/
 ├─ MainPackageTitleViewHolder.kt        → app/.../bundle/adapter/viewholder/
 ├─ SubPackageItemViewHolder.kt          → app/.../bundle/adapter/viewholder/
 ├─ SubPackageTitleViewHolder.kt         → app/.../bundle/adapter/viewholder/
 ├─ SpecificationCountViewHolder.kt      → app/.../bundle/adapter/viewholder/
 ├─ SevenDayCalendarViewHolder.kt        → app/.../bundle/adapter/viewholder/
 ├─ MultipleOpenDateDescViewHolder.kt    → app/.../bundle/adapter/viewholder/
 └─ WhiteSpacerViewHolder.kt            → app/.../bundle/adapter/viewholder/

Epoxy Model
 ├─ BundleSpecificationModel.kt          → app/.../bundle/expoxy/
 ├─ BundleProductSubPackageItemModel.kt  → app/.../bundle/expoxy/
 ├─ TicketBundleCalendarModel.kt         → app/.../bundle/expoxy/
 ├─ TicketBundleProductSpecificationCountModel.kt → app/.../bundle/expoxy/
 ├─ TicketBundleSkuSectionTitle.kt       → app/.../bundle/expoxy/
 ├─ TicketBundleSubSkuSectionTitle.kt    → app/.../bundle/expoxy/
 └─ TicketBundleSubSpaceLineModel.kt     → app/.../bundle/expoxy/

Controller
 ├─ TicketBundleSkuController.kt         → app/.../bundle/controller/
 └─ TicketBundleSubPackagesController.kt → app/.../bundle/controller/

ViewModel（UI 狀態管理，activity scope 共享）
 └─ TicketSpecificationSharedViewModel.kt → app/.../bundle/model/

Domain（業務邏輯 UseCase）
 ├─ GetBundleDetailUseCase.kt            → domain/usecase/.../bundle/
 ├─ CalculateBundlePriceUseCase.kt       → domain/usecase/.../bundle/
 ├─ GetProductDetailUseCase.kt           → feature/shared/product/.../useCase/
 └─ GetProductPackagesUseCase.kt         → feature/shared/product/.../useCase/

Data（資料層）
 └─ BundleRepository.kt                  → data/repository/.../bundle/

Network（API 定義）
 ├─ BundleApiService.kt                  → libs/networking/api/.../bundle/
 └─ KKdayService.kt（getBundlePackageCalendarNew） → app/.../network/retrofit/

Data Model
 ├─ BundleDetailEntity.kt               → libs/model/.../bundle/
 ├─ BundleSkuPriceDto.kt                → libs/model/.../bundle/
 ├─ BundleGroupDto.kt                   → libs/model/.../bundle/
 ├─ BundleCalculatePriceRequest.kt      → libs/model/.../bundle/
 └─ TicketBundleDetailRequest.kt        → libs/model/.../bundle/

Local Model
 ├─ TicketSKUData.kt                    → app/.../bundle/model/
 └─ TicketBundleUtils.kt                → app/.../bundle/model/（數量規則計算工具）

Listener 介面
 ├─ ITicketSKUActionListener.kt          → app/.../bundle/listener/
 ├─ ISpecificationStateChangeListener.kt → app/.../bundle/listener/
 └─ IOnItemShowListener.kt              → app/.../bundle/listener/
```

---

## 資料流

### 主流程：頁面載入 / 查詢套票詳情

```
UI（TicketBundleSKUFragment）
 │  onCreate：取得 bundlePkgOid 參數
 │  initView → viewModel.viewReady(true)
 ↓
ViewModel（TicketSpecificationSharedViewModel）
 │  viewReady() → queryTicketSKUData(bundlePkgOid)
 │  呼叫：bundleDetailUseCase.invokeTicketBundle()
 ↓
UseCase（GetBundleDetailUseCase）
 │  呼叫：bundleRepository.getTicketBundleDetail()
 ↓
Repository（BundleRepository）
 │  呼叫：bundleApiService.getTicketBundleDetail()
 ↓
API（BundleApiService）
 │  POST v2/product/bundle-package/detail
 ↓
後端 API
```

### 回傳流（套票詳情）

```
後端 API
 ↓
Repository：B2CApiResponse<BundleDetailEntity?> → BundleDetailEntity
 ↓
ViewModel：BundleDetailEntity →
  1. 解析主包 mainPackages → buildSpecStateByBundlePackage → SpecificationState（主商品）
  2. 解析子包 subPackages → 多個 SpecificationState（子商品）
  3. 合併為 specState.ticketSubPackageSpecificationStateList
  4. 發射 ticketSKUDataFlow（主商品標題）
  5. 更新 specificationStateFlow → UI 觀察刷新
 ↓
UI：observeData() 收到 SpecificationState →
  enhancedContainer.setSpecificationState()
  enhancedContainer.setSubPackageStates()
  calendarViewModel.fillSevenDaysCalendar()
```

### 價格計算流程（使用者完成主商品+子商品選擇後）

```
UI 操作（選擇規格/日期/數量）
 │  透過 specificationListener / calendarViewListener 回調
 ↓
ViewModel（clickSku）
 │  TicketBundleUtils.validateBundleProductForPriceCalculation()
 │  驗證通過 → calculateTicketBundlePrice()
 │  呼叫：calculateBundlePriceUseCase(bundlePkgOid, bundleGroups, currency)
 ↓
UseCase（CalculateBundlePriceUseCase）
 │  呼叫：bundleRepository.calculateBundlePrice()
 ↓
Repository（BundleRepository）
 │  呼叫：bundleApiService.calculateBundlePrice()
 ↓
API（BundleApiService）
 │  POST v2/product/bundle-package/price
 ↓
後端 API → BundleSkuPriceDto
 ↓
ViewModel：handleBundlePriceResult() → 更新主商品與子商品 specExtra 中的 bundlePrice
 ↓
UI：onTicketBundlePriceChange → MultipleSpecificationActivity.updateLayoutConfirmField()
```

### 日曆資料載入流程

```
UI：loadMoreCalendar() / onMoreDatesClicked()
 ↓
ViewModel：loadTicketBundleSKUPackageCalendarData(startDate, endDate)
 │  呼叫：NetworkApi.getBundlePackageCalendarNew()
 ↓
KKdayService
 │  GET v2/product/packages/{pkg_oid}/items/{item_oid}/calendar
 ↓
後端 API → PackageItem
 ↓
ViewModel：更新 productPackageCalendarData → stateHelper.updatePackageCalendarItem()
 ↓
UI：calendarViewModel.fillSevenDaysCalendar() 刷新七日日曆
```

---

## 逐層說明

### UI 層
- `TicketBundleSKUFragment` 繼承 `BaseFragment`，使用 ViewBinding (`TicketBundleFragmentSpecificationBinding`)
- 已從 RecyclerView 遷移至 ScrollView + LinearLayout 實作
- 響應式 UI 由 `EnhancedTicketBundleContainer` 管理，內部組合 `TicketBundleScrollViewContainer`
- 日曆抽屜使用 Compose `VMCalendarScreen`
- 對話框使用 Compose `KKDialog`，支援 suspend 掛起式彈窗（`showComposeSuspendDialog`）
- ViewModel 透過 `activityViewModel` 取得，與 `MultipleSpecificationActivity` 共享 scope

### ViewModel 層
- `TicketSpecificationSharedViewModel` 繼承 `SpecificationSharedViewModel`，使用 `@KoinViewModel` 註冊
- 狀態管理：`specificationStateFlow`（StateFlow）+ `stateHelper`（SpecificationStateHelper）
- 主商品與子商品狀態統一管理於 `SpecificationState.ticketSubPackageSpecificationStateList`
- 價格相關事件透過 `onTicketBundlePriceChange`（LiveData）通知 UI
- 對話框類型透過 `ShowDialogType` enum 管理（PLEASE_SELECT_FIRST_PRODUCT / CONFIRM_CHANGE_FIRST_PRODUCT_COUNT / RESELECT_SUB_PRODUCT_COUNT / THE_PRODUCT_HAS_CHANGED）
- 子商品操作透過 `ITicketSKUActionListener` 介面委託至主 ViewModel 處理

### UseCase 層
- `GetBundleDetailUseCase`：取得套票詳情，支援一般 Bundle 和 Ticket Bundle 兩種模式
- `CalculateBundlePriceUseCase`：計算組合商品價格，傳入主商品+子商品的 BundleGroupDto 列表
- 兩個 UseCase 都直接依賴 `BundleRepository`（技術債，未經 domain:contract 介面分離）

### Repository 層
- `BundleRepository` 繼承 `BaseApiRepository`，處理 API 呼叫與快取
- `getTicketBundleDetail()`：POST 取得套票詳情，不使用快取
- `calculateBundlePrice()`：POST 計算價格，將 DTO 轉為 `BundleSkuPriceDto`
- 錯誤處理：API 失敗回傳 `BundleSkuPriceDto.defaultInstance`

### API 層
- `BundleApiService`（Retrofit）
  - `POST v2/product/bundle-package/detail`：取得套票詳情 → `B2CApiResponse<BundleDetailEntity?>`
  - `POST v2/product/bundle-package/price`：計算組合價格 → `B2CApiResponse<Price>`
- `KKdayService`（舊版 Retrofit，RxJava）
  - `GET v2/product/packages/{pkg_oid}/items/{item_oid}/calendar`：取得日曆資料 → `Observable<Response<PackageItem>>`

---

## View 方法清單

| 方法 | 說明 |
|------|------|
| `onCreate()` | 取得 `bundlePkgOid` 參數，設定 `setCanUpdateProductDetail(false)` 防止商品詳情被錯誤覆蓋 |
| `initView()` | 初始化響應式容器、設定數量變更回調、監聽 ticketSKUDataFlow / ticketSnapErrorMessage / viewReady、顯示 Dialog |
| `initAction()` | 空實作 |
| `observeData()` | 觀察 `specificationStateFlow`（debounce 100ms）更新規格狀態與七日日曆、觀察 `sevenDaysCalendar` 更新日曆 UI |
| `initOtherView()` | 初始化 Compose 日曆抽屜 `VMCalendarScreen` |
| `showDialog()` | 設定 Compose Dialog 內容，處理業務彈窗與 suspend 掛起彈窗 |
| `loadMoreCalendar()` | 載入更多日期資料 |
| `loadMoreCalendarItem()` | 呼叫 ViewModel 載入日曆 API |
| `checkProductThisDateSoldOut()` | 檢查指定日期是否已售完（考慮關閉日期、庫存、EventId） |
| `showComposeSuspendDialog()` | 掛起式確認對話框，回傳 Boolean（確認/取消） |
| `updatePackageCalendarData()` | 更新子商品的日曆資料中的數量規則 |
| `adjustCountIfNeeded()` | 單規格情況下，若數量超出範圍則調整為最小值 |
| `onDestroyView()` | 清理響應式容器資源 |

---

## ViewModel 方法清單

| 方法 | 說明 |
|------|------|
| `viewReady()` | 頁面就緒入口，呼叫 `queryTicketSKUData` 載入套票資料 |
| `queryTicketSKUData()` | 核心方法：查詢套票詳情、解析主包/子包、建構 SpecificationState、更新全局狀態 |
| `buildSpecStateByBundlePackage()` | 根據 BundlePackage 建構 SpecificationState，包含規格轉換、日曆、數量資訊 |
| `parsePackageItem()` | 解析 PackageItem JSON，合併套票數量規則（min/max） |
| `clickSku()` | SKU 點擊處理：主商品驗證後計算價格，子商品委託主 ViewModel |
| `calculateTicketBundlePrice()` | 組合價格計算：構建 main/sub BundleGroupDto，呼叫 UseCase |
| `handleBundlePriceResult()` | 處理價格計算成功結果，更新主商品與子商品的 specExtra |
| `handlePriceCalculationError()` | 處理價格計算失敗，顯示商品異動對話框 |
| `needShowConfirmChangeFirstProductCountDialog()` | 判斷修改主商品數量時是否需要顯示確認對話框 |
| `confirmResetSubProductCount()` | 確認重置子商品數量為預設值，更新數量規則 |
| `onUserSelectedDate()` | 使用者選擇日期後同步子商品日期、清空價格 |
| `loadTicketBundleSKUPackageCalendarData()` | 載入套票日曆資料，更新 packageCalendarItem |
| `requestCalendarData()` | 子商品請求日曆資料，更新子商品的規格與日曆狀態 |
| `setCanUpdateProductDetail()` | 控制是否允許更新商品詳情（避免組合商品進入時被覆蓋） |
| `setBundlePkgOid()` | 設定當前套票 OID |
| `showCalendar()` / `hideCalendar()` | 控制日曆抽屜顯示/隱藏 |
| `hideDialog()` | 隱藏對話框 |
| `showOrDismissDialog()` | 控制 Loading 對話框 |
| `changeSubPackageSpecificationStateList()` | 更新子商品規格狀態列表（選中/取消選中） |
| `setSubTicketBundleTicketSKUActionListener()` | 設定子商品 SKU 操作監聽器 |
| `onReSelect()` | 重新選擇時觸發 viewReady |
| `specificationListener` | 規格按鈕點擊監聽（onEventButtonClicked / onSpecButtonClicked / onCountButtonClicked） |
| `trackClickCalendar()` | 追蹤日曆點擊事件 |
| `trackErrorMessageImpression()` | 追蹤錯誤訊息曝光事件 |
| `trackImpressionProdSkuFormPgDisableStatus()` | 追蹤停用狀態曝光事件 |
| `trackClickProdSkuFormPgPackageInfoBtn()` | 追蹤套餐資訊按鈕點擊事件 |

---

## 業務邏輯摘要

- **主商品優先**：使用者必須先完成主商品的規格/日期/數量選擇，才能操作子商品。未完成時顯示「請先選完第一個商品」對話框
- **數量連動規則**：主商品數量變更時，透過 `TicketBundleUtils.getRefreshUIResult()` 動態計算子商品的數量上下限（`BundleMappingRule`），超出範圍時提示使用者確認重置
- **價格計算條件**：`TicketBundleUtils.validateBundleProductForPriceCalculation()` 驗證主商品與子商品都已填寫完整（規格、日期、數量都在合理範圍內）才觸發價格 API
- **日期同步**：主商品選擇日期後，符合條件的子商品日期會自動同步，同時清空已計算的價格
- **售完判斷**：`checkProductThisDateSoldOut()` 檢查指定日期是否屬於關閉日期（closeDates）或庫存為 0（含 EventId 維度的庫存判斷）
- **商品異動處理**：套票詳情返回 `isSoldOut` 或價格計算失敗時，顯示「商品有異動」對話框並結束頁面
- **狀態區分**：透過 `ProductType.TICKET_MAIN` / `TICKET_SUB` 區分主商品與子商品的處理邏輯
- **追蹤埋點**：涵蓋日曆點擊、規格選擇、錯誤訊息曝光、停用狀態等事件追蹤

---

## 已知技術債

- `TicketSpecificationSharedViewModel` 直接依賴 `CartRepository`、`ESimDcsRepository`、`BundleRepository`（data 層），未經 `domain:contract` 介面分離
- `GetBundleDetailUseCase` 與 `CalculateBundlePriceUseCase` 直接依賴 `BundleRepository`（data 層），缺少 domain contract 介面
- 日曆資料載入使用舊版 `NetworkApi.sharedInstance().getBundlePackageCalendarNew()`（RxJava Observable），未遷移至新架構的 Repository + UseCase 模式
- ViewModel 檔案過大（約 1997 行），包含大量業務邏輯、狀態管理、追蹤邏輯，建議拆分
- `TicketBundleUtils` 為 object 工具類，靜態方法難以測試與替換
- 主商品與子商品的狀態管理耦合在同一個 ViewModel 中，增加了複雜度

## 相關筆記
- [01-architecture](../01-architecture.md)
- [02-modules](../02-modules.md)
- [03-ui-patterns](../03-ui-patterns.md)
- [05-networking](../05-networking.md)
- [06-data-layer](../06-data-layer.md)
- [07-concurrency](../07-concurrency.md)
- [order-detail-compose](order-detail-compose.md)
- [sku-activity-shell](sku-activity-shell.md)

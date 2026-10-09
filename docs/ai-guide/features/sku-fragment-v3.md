# 票券規格選擇頁（Fragment V3） 技術文件

> 自動產生 | 最後更新：2026-03-20

---

## 概述

- **所在 Module**：`:app`
- **UI 入口**：`MultipleSpecificationV3Fragment.kt`
- **功能描述**：票券類商品的規格選擇 Fragment（第三版），以 SKU 剪枝演算法驅動，負責顯示七天日期選擇、場次選擇、規格選擇、票種與數量選擇等 UI，並將選擇結果傳回 Activity 觸發加入購物車或結帳流程。透過 `AppSharedData.isEnableSkuV3()` 開關分流。

---

## 檔案清單

```
UI（使用者介面入口）
 ├─ MultipleSpecificationV3Fragment.kt        → app/.../product/specification/multiple/ticket/view/
 ├─ MultipleSpecificationActivity.kt（Activity 殼）→ app/.../product/specification/multiple/ticket/view/
 └─ SharedSpecificationFragment.kt（基底類）    → app/.../product/specification/fragment/

Epoxy Controller（列表 UI 組裝）
 └─ MultipleSpecificationV3Controller.kt       → app/.../product/specification/multiple/ticket/epoxy/controller/

ViewModel（UI 狀態管理）
 ├─ SkuSharedViewModel.kt（SKU V3 核心狀態）     → app/.../product/specification/
 ├─ TicketSpecificationSharedViewModel.kt       → app/.../product/specification/multiple/ticket/bundle/model/
 └─ MultipleCalendarViewModel.kt（七天日曆）     → vm/ticket/.../common/product/page/

Domain（業務邏輯）
 ├─ SkuPruningCalculator.kt                     → app/.../product/specification/
 ├─ SkuSelectionState.kt（選擇狀態 + 剪枝結果） → app/.../product/specification/
 └─ SkuIntentHandler.kt（選擇意圖介面）          → app/.../product/specification/

Data（資料層）
 └─ SkuRepository.kt                            → app/.../product/specification/

Network（API 定義，透過 KKApi 統一入口）
 └─ KKApi.b2cApi.product                        → data/networking/api/
     ├─ getProductPackages()          → v2/product/{product_mid}/pkg
     ├─ getProductPackageCalendar()   → v2/product/{product_mid}/calendar
     ├─ getProductPackageItemCalendar() → v2/product_item/{item_oid}/calendar
     └─ getOrderKKPointsInfo()        → v2/points/estimate

Data Model
 ├─ ProductPackagesData               → data/model/.../product/
 ├─ ProductPackageCalendarData        → shared/base/.../model/product/
 ├─ PackageCalendarItem               → shared/base/.../model/product/
 ├─ PackageData / PackageItem         → shared/base/.../model/product/
 └─ OrderKKPointsInfo / KKPointsData  → data/model/.../points/
```

---

## 資料流

### 主流程：頁面載入與 SKU 資料取得

```
UI（MultipleSpecificationActivity）
 │  initFragment() → 判斷 isEnableSkuV3()
 │  建立 MultipleSpecificationV3Fragment
 ↓
UI（MultipleSpecificationV3Fragment）
 │  initAction()
 │  呼叫：skuViewModel.initSkuApiData(productId, pkgOid, useHybridCalendar=true)
 ↓
ViewModel（SkuSharedViewModel）
 │  1. skuRepository.getProductPackageDataAPI()     → 取得方案清單
 │  2. selectPkgOid()                               → 設定選中方案
 │  3. loadAllPackageCalendarData()                  → 分批載入日曆（每 3 個月一批）
 │     ├─ skuRepository.getProductPackageCalendarDataAPI()
 │     └─ skuRepository.getProductPackageItemCalendarAPI()
 │  4. calculateAndUpdateSkuAvailability()           → SKU 剪枝計算
 ↓
SkuPruningCalculator
 │  根據 SkuSelectionState 計算 SkuPruningResult
 │  （可用日期、場次、規格、票種）
 ↓
UI（MultipleSpecificationV3Fragment.observeData）
 │  觀察 skuViewModel.pruningResult
 │  → 更新 specificationController.skuPruningResult
 │  → 觸發 Epoxy requestModelBuild()
 ↓
MultipleSpecificationV3Controller.addChildModels()
 │  依序建構：方案標題 → 七天日曆 → 場次 → 規格 → 票種數量
```

### 用戶選擇流程（日期/場次/規格/票種）

```
UI 操作（點選日期/場次/規格/調整數量）
 ↓
SkuSharedViewModel（SkuIntentHandler 介面）
 │  selectDate() / selectEvent() / selectSpec() / selectTicketQuantity()
 │  → 更新 _selectionState
 │  → 觸發 calculateAndUpdateSkuAvailability()（防抖 debounce）
 ↓
SkuPruningCalculator → 新的 SkuPruningResult
 ↓
UI 觀察 pruningResult → Controller 重建 UI
```

### 加入購物車/結帳流程

```
UI（MultipleSpecificationActivity 底部按鈕）
 │  onButtonClick() → checkAllItemValid()
 │  → skuViewModel.isSKUV3AllRequiredFilled() 驗證
 ↓
clickConfirmButton()
 │  收集選擇資料 → 導向 OrderFormFillingActivity 或 CartActivity
```

---

## 逐層說明

### UI 層
- `MultipleSpecificationV3Fragment` 繼承 `SharedSpecificationFragment`，使用 `FragmentSpecificationBinding`（RecyclerView 容器）。
- 透過 `activityViewModel` 取得三個 ViewModel：`TicketSpecificationSharedViewModel`、`SkuSharedViewModel`、`MultipleCalendarViewModel`，皆為 Activity scope 共享。
- Epoxy Controller（`MultipleSpecificationV3Controller`）負責組裝列表 UI：方案標題、七天日曆條、場次選項、規格選項、票種數量調整。
- 日曆相關邏輯使用 `CalendarBottomSheetFragment` 展示完整日曆。

### ViewModel 層
- **SkuSharedViewModel**：V3 核心，持有所有原始 API 資料、`SkuSelectionState`（StateFlow）、`SkuPruningResult`（StateFlow）。負責 API 調用、資料合併、剪枝計算觸發、價格計算。
- **TicketSpecificationSharedViewModel**：繼承 `SpecificationSharedViewModel`，負責舊版票券規格邏輯、日曆監聽、商品詳情取得、加入購物車。V3 模式下主要作為商品資料來源和購物車/結帳橋接。
- **MultipleCalendarViewModel**：管理七天日曆 strip 的狀態（`sevenDaysCalendar: StateFlow<CalendarState>`）、展開日曆的顯示/隱藏、日期價格映射。

### Domain 層（業務邏輯）
- **SkuPruningCalculator**：根據 `SkuSelectionState` 和 `PackageCalendarItem` 計算各維度可用性，產出 `SkuPruningResult`。核心演算法：遍歷所有 SKU 組合，根據已選條件剪枝，判斷日期/場次/規格/票種是否可選。
- **SkuSelectionState**：不可變資料類，儲存 productId、selectedPkgOid、selectedDate、selectedEvent、selectedSpecs（map）、selectedTickets（map）、dateRange。
- **SkuPruningResult**：包含 `availableDates`、`availableEvents`、`availableSpecs`、`availableTickets` 四個可用性列表。

### Repository / API 層
- **SkuRepository**（`@Single`）：純 API 調用層，繼承 `BaseApiRepository`，透過 `KKApi.b2cApi.product` 呼叫後端。
- API 端點：
  - `v2/product/{product_mid}/pkg` → 取得商品方案清單
  - `v2/product/{product_mid}/calendar` → 取得方案日曆資料（分批載入，每批 3 個月）
  - `v2/product_item/{item_oid}/calendar` → 取得方案項目日曆（含 SKU 級別庫存/價格）
  - `v2/points/estimate` → 計算 KK Points 積分

---

## View 方法清單

### MultipleSpecificationV3Fragment

| 方法 | 說明 |
|------|------|
| `initAction()` | 呼叫 `skuViewModel.initSkuApiData()` 啟動 API 資料載入 |
| `initOtherView()` | 監聽 `calendarViewModel.calendarShowState2`，觸發展開日曆 |
| `observeData()` | 監聯 `skuViewModel.pruningResult`、`viewModel.productDetailDataFlow`、`calendarViewModel.sevenDaysCalendar`，驅動 UI 更新 |
| `showCalendarBottomSheet()` | 建構並顯示 `CalendarBottomSheetFragment`，傳入日期範圍、價格映射、關閉 SKU 日期 |
| `getCloseSkuDatesForSelection()` | 根據已選場次和規格，計算不可選日期清單 |
| `updateCalendarView()` | 根據剪枝結果和選擇狀態更新七天日曆 strip 的日期、價格、可用性 |
| `updateFullDatePriceMapFromSkuCalendarItems()` | 使用完整 API 資料更新展開日曆的價格映射 |
| `Companion.newInstance()` | 靜態工廠方法建立 Fragment 實例 |

---

## ViewModel 方法清單

### SkuSharedViewModel（核心方法）

| 方法 | 說明 |
|------|------|
| `initSkuApiData()` | 依序取得方案清單、設定選中方案、分批載入日曆資料、觸發剪枝計算 |
| `selectDate()` | 設定選中日期，觸發 SKU 可用性重算 |
| `selectEvent()` | 設定選中場次，觸發重算 |
| `selectSpec()` | 設定選中規格（specOid → specItemOid），觸發重算 |
| `selectTicketQuantity()` | 設定票種數量，觸發重算 |
| `selectPkgOid()` | 設定選中方案 |
| `selectProduct()` | 設定商品 ID 和 productOid |
| `setDateRange()` | 設定日期範圍限制（七天日曆範圍），影響剪枝計算範圍 |
| `calculateAndUpdateSkuAvailability()` | 觸發 `SkuPruningCalculator` 計算，更新 `_pruningResult` |
| `calculateDisplayPriceForDate()` | 計算指定日期的顯示價格（考慮已選票種） |
| `calculateDisplayPriceForDateWithState()` | 根據指定 selectionState 計算日期價格 |
| `calculatePriceFromSkuPruningResult()` | 根據當前選擇計算總價 |
| `calculateAndUpdateKKPoints()` | 根據價格觸發 KK Points 積分計算 |
| `getSelectedPackageInfo()` | 取得選中方案的基本資料 |
| `getSelectedPackageCalendarData()` | 取得選中方案的日曆資料 |
| `getAccumulatedPackageCalendarItem()` | 取得累積合併的方案項目日曆 |
| `getCurrentPackageSevenDaysCalendar()` | 計算七天日曆的日期清單（含價格/售罄狀態） |
| `hasAnyStockOnSelectedPackageDate()` | 檢查指定日期是否有庫存 |
| `getCurrencySymbolForPrice()` | 格式化價格為帶幣別符號的字串 |
| `getMinPriceForTicket()` | 取得指定票種在指定日期的最低價格 |
| `createCalendarBottomSheetCallbacks()` | 建立展開日曆的回調物件 |
| `isSKUV3AllRequiredFilled()` | 驗證所有必填項目是否完成 |
| `checkSKUV3BasicRequirements()` | 檢查基本必填項目，回傳錯誤訊息 |
| `setProductDetailData()` | 設定商品詳情資料（從 TicketSpecificationSharedViewModel 同步） |

---

## 業務邏輯摘要

- **SKU 剪枝演算法**：核心在 `SkuPruningCalculator`，根據用戶已選條件（日期、場次、規格），遍歷所有 SKU 組合，計算各維度剩餘可選項。選擇任一條件後，不相容的選項會被標記為不可用。
- **日期範圍管理**：七天日曆 strip 與展開日曆兩種模式切換，使用 `fixedDateRange` 機制防止選擇場次/規格時日期範圍被重置。`isFullCalendarMode` 和 `isDatePickerSelection` 旗標控制日期更新行為。
- **分批載入**：日曆資料按 3 個月為單位分批載入並累積合併（`mergeProductPackageCalendarData` / `mergePackageCalendarItem`），支援跨越大日期範圍的商品。
- **價格計算**：優先顯示已選票種的最低價；未選票種時優先顯示 adult 票種價格，其次為第一個票種價格。
- **V3 開關分流**：透過 `AppSharedData.isEnableSkuV3()` 控制，Activity 的 `initFragment()` 決定載入 V3 Fragment 或舊版 Fragment。
- **防抖機制**：`SkuSharedViewModel` 使用 debounce 防止快速操作導致的重複計算。
- **錯誤處理**：驗證不通過時顯示 Toast 提示（日期未選、規格未選、數量未選等）。

---

## 已知技術債

- `SkuSharedViewModel` 和 `TicketSpecificationSharedViewModel` 職責重疊，V3 模式下 `TicketSpecificationSharedViewModel` 仍作為商品資料來源和購物車橋接，兩者之間需要手動同步狀態（如 `setProductDetailData()`）。
- `SkuRepository` 放在 `app/.../view/product/specification/` 目錄下，未遵循專案架構規範（應放在 `:data:repository`，並在 `:domain:contract` 定義介面）。
- `SkuPruningCalculator` 和相關 model 直接放在 `:app` 模組的 view 層，未抽離至 `:domain:usecase`。
- V3 Fragment 與舊版 Fragment 並存於同一目錄，`MultipleSpecificationActivity` 透過 if-else 分流，增加維護複雜度。
- 七天日曆的日期範圍管理使用多個 Boolean 旗標（`isFullCalendarMode`、`isDatePickerSelection`、`fixedDateRange`），邏輯較複雜且容易出現邊界情況。

## 相關筆記
- [01-architecture](../01-architecture.md)
- [02-modules](../02-modules.md)
- [03-ui-patterns](../03-ui-patterns.md)
- [05-networking](../05-networking.md)
- [06-data-layer](../06-data-layer.md)
- [07-concurrency](../07-concurrency.md)
- [order-detail-compose](order-detail-compose.md)
- [sku-activity-shell](sku-activity-shell.md)
- [sku-base](sku-base.md)

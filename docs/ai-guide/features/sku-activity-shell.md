# 票券規格選擇頁（Activity 殼） 技術文件

> 自動產生 | 最後更新：2026-03-20

---

## 概述

- **所在 Module**：`:app`
- **UI 入口**：`MultipleSpecificationActivity.kt`
- **功能描述**：票券類商品的規格選擇入口 Activity，繼承 `SharedSpecificationActivity`，作為殼層承載不同 Fragment（舊版 `MultipleSpecificationFragment`、V3 版 `MultipleSpecificationV3Fragment`、套票 `TicketBundleSKUFragment`），處理 SKU 選擇流程的進入點、路由分流與底部確認欄位互動。

---

## 檔案清單

```
UI（Activity 殼層）
 ├─ MultipleSpecificationActivity.kt           → app/.../product/specification/multiple/ticket/view/
 ├─ ConfirmButtonFieldArrayViews.kt            → app/.../product/specification/multiple/ticket/view/
 └─ TicketBundleDialogActivity.kt              → app/.../product/specification/multiple/ticket/view/

UI（Fragment — 由 Activity 殼層載入）
 ├─ MultipleSpecificationFragment.kt（舊版）    → app/.../product/specification/multiple/ticket/view/
 ├─ MultipleSpecificationV3Fragment.kt（V3 版） → app/.../product/specification/multiple/ticket/view/
 └─ TicketBundleSKUFragment.kt（套票 Bundle）   → app/.../product/specification/multiple/ticket/bundle/view/

Epoxy Controller
 ├─ MultipleSpecificationController.kt（舊版）   → app/.../product/specification/multiple/ticket/epoxy/controller/
 └─ MultipleSpecificationV3Controller.kt（V3）   → app/.../product/specification/multiple/ticket/epoxy/controller/

ViewModel（UI 狀態管理）
 ├─ TicketSpecificationSharedViewModel.kt       → app/.../product/specification/multiple/ticket/bundle/model/
 ├─ SkuSharedViewModel.kt（V3 SKU 剪枝計算）    → app/.../product/specification/
 └─ MultipleCalendarViewModel.kt                → vm/ticket/.../product/page/

基底類（繼承鏈）
 ├─ SharedSpecificationActivity.kt（abstract）   → app/.../product/specification/
 ├─ SharedSpecificationFragment.kt（abstract）   → app/.../product/specification/fragment/
 └─ SpecificationSharedViewModel.kt（ViewModel 基底） → app/.../product/specification/
```

---

## 資料流

### 主流程：路由分流 — 決定載入哪個 Fragment

```
商品詳情頁（MultipleProductDetailFragment / TourProductDetailFragment / CartProductDelegate）
 │  KRouter.dispatch(KRouterConst.PAGE_VM_SPECIFICATION)
 │  攜帶 SpecificationData（packageId, selectedDate, bundlePkgOid 等）
 ↓
MultipleSpecificationActivity
 │  onCreate → initData() → initView() → initFragment()
 │
 │  initFragment() 分流邏輯：
 │  ├─ bundlePkgOid 有值 → TicketBundleSKUFragment（套票組合）
 │  ├─ isEnableSkuV3()  → MultipleSpecificationV3Fragment（V3 新版）
 │  └─ 其他             → MultipleSpecificationFragment（舊版）
 ↓
Fragment 載入 → 各自處理日曆、規格選擇 UI
```

### 確認下單流程

```
UI（底部確認欄位 — ConfirmButtonFieldArrayViews 組合）
 │  使用者點擊「立即預訂」或「加入購物車」
 │  → onButtonClick(hasLogin)
 ↓
MultipleSpecificationActivity
 │  分支判斷：
 │  ├─ 套票商品 → checkTicketBundleProductAllItemValid()
 │  │   驗證主商品 + 子商品是否皆已填寫完整
 │  └─ 一般商品 → checkAllItemValid()
 │       ├─ SKU V3：skuViewModel.isSKUV3AllRequiredFilled() + checkSKUV3QuantityRules()
 │       └─ 舊版：state.isAllRequiredFilled() + stateHelper.checkAllItemValid()
 ↓
驗證通過
 │  clickConfirmButton()（繼承自 SharedSpecificationActivity）
 │  → SpecificationPresenter.clickConfirmButton()
 │  → Reductor dispatch → isSpecCheckingSuccess
 ↓
launchOrderFormFillingPage()
 │  SKU V3：syncSKUV3ToSpecificationState() → createAndFixOrderSpecificationData()
 │  ├─ 加入購物車 → CartActivity.launch()
 │  └─ 直接購買   → OrderFormFillingActivity.launch()
```

### 價格更新流程（SKU V3）

```
SkuSharedViewModel
 │  pruningResult / selectionState / kkPointsInfo 狀態變更
 ↓
MultipleSpecificationActivity.initOtherView()
 │  launchAndCollectIn 觀察三個 Flow
 │  → updateLayoutConfirmField(state)
 ↓
ConfirmButtonFieldArrayViews
 │  計算價格（V3：skuViewModel.calculatePriceFromSkuPruningResult()）
 │  更新 KK Points
 │  更新底部確認欄位 UI（價格文字、積分、按鈕狀態）
```

---

## 逐層說明

### UI 層（Activity）

`MultipleSpecificationActivity` 使用 `@Router(KRouterConst.PAGE_VM_SPECIFICATION)` 註冊路由，繼承 `SharedSpecificationActivity`。核心職責：

1. **Fragment 分流**：`initFragment()` 依據 `bundlePkgOid` 與 `isEnableSkuV3()` 決定載入的 Fragment
2. **底部確認欄位組合**：使用 `ConfirmButtonFieldArrayViews`（Composite 模式）同時管理 `layoutConfirmField` 與 `layoutVmConfirmField` 兩組底部互動元件，解決因 API 回傳後才能判斷 `isKKGiftProduct` 而需切換元件的問題
3. **日曆同步**：透過 `calendarViewModel` 管理七天日曆條與完整日曆 BottomSheet 的狀態
4. **SKU V3 流監聽**：在 `initOtherView()` 中監聽 `pruningResult`、`selectionState`、`kkPointsInfo` 三個 Flow，驅動價格更新

### UI 層（Fragment）

- **MultipleSpecificationFragment（舊版）**：繼承 `SharedSpecificationFragment`，使用 `MultipleSpecificationController`（Epoxy），觀察 `specificationStateFlow`（debounce 100ms）更新 UI，管理七天日曆條與完整日曆 BottomSheet
- **MultipleSpecificationV3Fragment（V3）**：使用 `MultipleSpecificationV3Controller`，觀察 `SkuSharedViewModel.pruningResult` 驅動 UI，支援 `fixedDateRange` 機制避免選擇場次/規格時日期範圍跳動
- **TicketBundleSKUFragment（套票）**：獨立處理套票組合商品的規格選擇流程

### ViewModel 層

`TicketSpecificationSharedViewModel` 繼承 `SpecificationSharedViewModel`，使用 `@KoinViewModel` 注入，額外提供：
- 套票（Ticket Bundle）商品的子商品管理與價格計算
- `ITicketSKUActionListener` / `ISpecificationStateChangeListener` 回呼介面
- 套票驗證邏輯（`updateTicketSnapErrorMessage`）
- 日曆標題、子商品規格狀態切換

`SkuSharedViewModel`（V3 專用）負責 SKU 剪枝計算、選擇狀態管理、V3 驗證與價格計算。

`MultipleCalendarViewModel` 管理七天日曆條顯示、完整日曆 BottomSheet 狀態、日期價格映射。

### ConfirmButtonFieldArrayViews

實作 `IConfirmButtonField` 介面的 Composite 模式，內部持有多個 View（`layoutConfirmField` + `layoutVmConfirmField`），所有操作（設定價格、積分、按鈕事件、錯誤訊息）統一轉發至各子 View，`confirmPerformClick()` 只觸發可見的 View。

---

## View 方法清單（MultipleSpecificationActivity）

| 方法 | 說明 |
|------|------|
| `initOtherView()` | 初始化日曆 ViewModel、底部確認欄位組合、SKU V3 Flow 監聽 |
| `initFragment()` | 依 bundlePkgOid / isEnableSkuV3 分流載入不同 Fragment |
| `viewReady()` | 計算初始日曆請求日期範圍，觸發 ViewModel 載入資料 |
| `updateLayoutConfirmField()` | 根據商品類型判斷顯示哪組底部欄位，計算價格與積分並更新 UI |
| `onSKUClick()` | SKU 點擊回呼 — 觸發 KK Points 計算、呼叫 `clickSkuListener()` |
| `clickSkuListener()` | 同步 close dates 至日曆 ViewModel |
| `onButtonClick()` | 確認按鈕點擊入口 — 分流至套票或一般商品驗證 |
| `checkAllItemValid()` | 一般商品驗證 — V3 走 `skuViewModel` 驗證，舊版走 `stateHelper` |
| `checkTicketBundleProductAllItemValid()` | 套票商品驗證 — 依序檢查主商品、子商品選擇完整性與數量規則 |
| `launchOrderFormFillingPage()` | 驗證通過後導向結帳填寫頁或購物車 |
| `updateTextTitle()` | 設定 toolbar 標題為「選擇規格」 |
| `clickButtonReselect()` | 重選按鈕 — 清除所有選擇狀態與日曆資料 |
| `updateConfirmButton()` | 依登入狀態設定按鈕文字與點擊事件 |
| `showOrHideErrorMessage()` | 顯示或隱藏底部錯誤訊息 |
| `onChildResume()` | Resume 時處理登入返回後自動觸發下一步 |
| `selectedPackageId()` | 方案選擇回呼 — 通知 ViewModel 與 Presenter |
| `showOrDismissDialog()` | Loading Dialog 顯示/隱藏控制 |
| `onBackPressed()` | 返回時帶回已選日期至前一頁 |

---

## ViewModel 方法清單（TicketSpecificationSharedViewModel — 重點方法）

| 方法 | 說明 |
|------|------|
| `updatePreSelectedPackageId()` | 設定預選方案 ID 並觸發七天日曆更新 |
| `updateTicketSnapErrorMessage()` | 發送套票驗證錯誤訊息 |
| `needShowConfirmChangeFirstProductCountDialog()` | 判斷是否需顯示「變更主商品數量」確認 Dialog |
| `confirmResetSubProductCount()` | 確認重置子商品數量 |
| `viewReady()` | 初始化請求 — 並發取得商品詳情、方案清單、日曆資料，支援套票 Bundle 資料載入 |
| `setProductDetailData()` | 設定商品詳情並計算套票 Bundle 分組 |
| `updateProductDetail()` | 取得並更新商品詳情資料 |
| `clickSku()` | SKU 選擇核心 — 更新狀態、計算套票價格、觸發追蹤 |
| `onUserSelectedDate()` | 使用者選擇日期後更新狀態、觸發規格重算 |
| `loadMorePackageCalendarData()` | 載入更多月份日曆資料 |
| `requestCalendarData()` | 請求特定方案的日曆資料 |
| `onReSelect()` | 重選 — 清除所有資料與狀態 |
| `setBundlePkgOid()` | 設定套票 Bundle 方案 ID |
| `showCalendar()` / `hideCalendar()` | 控制子商品日曆 BottomSheet 顯隱 |

---

## 業務邏輯摘要

- **三路分流**：Activity 作為殼層，依據 `bundlePkgOid`（套票）和 `isEnableSkuV3()`（V3 Feature Flag）決定載入不同 Fragment，實現漸進式遷移
- **Composite 底部欄位**：因 `isKKGiftProduct` 判斷依賴 API 回傳結果，使用 `ConfirmButtonFieldArrayViews` 組合模式同時管理兩組底部 UI 元件，避免切換遺失狀態
- **SKU V3 雙軌**：V3 啟用時，價格計算由 `SkuSharedViewModel.calculatePriceFromSkuPruningResult()` 驅動，驗證邏輯改用 `isSKUV3AllRequiredFilled()` + `checkSKUV3QuantityRules()`，並在下單前透過 `syncSKUV3ToSpecificationState()` 同步狀態
- **套票驗證三階段**：(1) 主商品填寫完整性 (2) 是否已選擇子商品 (3) 子商品填寫完整性與數量規則
- **返回帶日期**：`onBackPressed()` 透過 `setResult()` 將已選日期帶回商品詳情頁
- **KK Points 即時更新**：V3 監聽 `kkPointsInfo` Flow，價格變更時觸發 `calculateAndUpdateKKPoints()`
- **登入中斷恢復**：未登入時導向登入頁，登入返回後 `onChildResume()` 透過 `shouldGoNext` 自動觸發確認按鈕

---

## 已知技術債

- **雙狀態管理並存**：Activity 同時依賴 ViewModel（StateFlow）與 `SpecificationPresenter`（Reductor Store）處理確認下單邏輯，V3 雖繞過部分 Reductor 路徑但仍需 `setOrderSpecificationData()` 寫入 AppState
- **ConfirmButtonFieldArrayViews 的必要性**：因無法在 API 回傳前確定顯示哪組底部元件，採用 Composite 模式為 workaround，理想上應統一為單一元件
- **V3 / 舊版分支散布**：`checkAllItemValid()`、`launchOrderFormFillingPage()`、`clickButtonReselect()` 等方法內部均有 `isEnableSkuV3()` 分支，增加維護成本
- **TicketSpecificationSharedViewModel 職責過重**：同時處理通用規格選擇、套票 Bundle 管理、子商品日曆、追蹤等邏輯，建構子依賴超過 15 個
- **簡體中文註解混雜**：部分程式碼註解為簡體中文，與專案繁體中文規範不一致

## 相關筆記
- [01-architecture](../01-architecture.md)
- [02-modules](../02-modules.md)
- [03-ui-patterns](../03-ui-patterns.md)
- [05-networking](../05-networking.md)
- [06-data-layer](../06-data-layer.md)
- [07-concurrency](../07-concurrency.md)
- [bundle-sku](bundle-sku.md)
- [checkout](checkout.md)
- [order-detail-compose](order-detail-compose.md)
- [sku-fragment-v3](sku-fragment-v3.md)

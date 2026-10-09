# 憑證頁 技術文件

> 自動產生 | 最後更新：2026-03-19

---

## 概述

- **所在 Module**：`:feature:order_page`
- **UI 入口**：`MultiOrderVoucherActivity.kt`
- **功能描述**：訂單憑證/票券顯示頁面，展示 QR code、barcode 或電子票券（eSIM）資訊，支援全螢幕放大掃碼與憑證截圖分享。

---

## 檔案清單

```
UI（使用者介面入口）
 ├─ MultiOrderVoucherActivity.kt        → libs/feature/order_page/src/main/java/com/kkday/order_page/presentation/view/
 ├─ MultiOrderVoucherDetailFragment.kt  → libs/feature/order_page/src/main/java/com/kkday/order_page/presentation/view/
 └─ VoucherScanCodeFragment.kt          → libs/feature/order_page/src/main/java/com/kkday/order_page/presentation/view/

ViewModel（UI 狀態管理）
 └─ MultiOrderVoucherDetailViewModel.kt → libs/feature/order_page/src/main/java/com/kkday/order_page/presentation/viewModel/

Domain（業務邏輯 UseCase）
 ├─ GetVoucherByOrderUseCase.kt         → libs/feature/order_page/src/main/java/com/kkday/order_page/domain/useCase/
 ├─ GetBarcodesResultUseCase.kt         → libs/feature/order_page/src/main/java/com/kkday/order_page/domain/useCase/
 └─ GetVoucherContentUseCase.kt         → libs/feature/order_page/src/main/java/com/kkday/order_page/domain/useCase/

Data（資料層）
 ├─ OrderVoucherRepository.kt（介面）   → libs/feature/order_page/src/main/java/com/kkday/order_page/domain/repository/
 └─ OrderVoucherRepositoryImpl.kt       → libs/feature/order_page/src/main/java/com/kkday/order_page/data/

Network（API 定義）
 └─ OrderVoucherApiService.kt           → libs/feature/order_page/src/main/java/com/kkday/order_page/network/

DI
 └─ orderVoucherModule.kt               → libs/feature/order_page/src/main/java/com/kkday/order_page/di/

其他
 ├─ MultiOrderVoucherAdapter.kt         → libs/feature/order_page/src/main/java/com/kkday/order_page/presentation/adapter/
 ├─ VoucherScanCodeAdapter.kt           → libs/feature/order_page/src/main/java/com/kkday/order_page/presentation/adapter/
 ├─ MultiOrderVoucherClickListener.kt   → libs/feature/order_page/src/main/java/com/kkday/order_page/
 └─ VoucherScreenShotGeneratorImpl.kt   → libs/feature/order_page/src/main/java/com/kkday/order_page/helper/
```

---

## 資料流

### 主流程：頁面載入 / 憑證資料取得

```
UI（MultiOrderVoucherDetailFragment）
 │  onResume() 無條件觸發；或 initAction() 偵測 voucherListInfo.vouchers 為空時觸發
 │  呼叫：viewModel.fetchData(input.orderId)
 ↓
ViewModel（MultiOrderVoucherDetailViewModel）
 │  更新狀態為 RequestState.Loading
 │  並發執行（viewModelScope.async-await）：
 │   ├─ GetVoucherByOrderUseCase.invoke(orderId)
 │   ├─ GetBarcodesResultUseCase.invoke(orderId)
 │   ├─ ESimDcsRepository.getESimInstruction(language)
 │   └─ ESimDcsRepository.getESimOneClickInstallation(language)
 ↓
UseCase 1（GetVoucherByOrderUseCase）
 │  快取命中：直接回傳 HashMap cache[orderMid + lang]
 │  快取未命中：呼叫 repository.getVouchersByOrder(orderMid, lang)
 ↓
UseCase 2（GetBarcodesResultUseCase）
 │  呼叫：repository.getBarcodesResult(orderId, lang)
 ↓
Repository（OrderVoucherRepositoryImpl）
 │  代理呼叫 apiService，無快取、無 model 轉換
 ↓
API Service（OrderVoucherApiService）
 │  GET v2/order/{order_mid}/vouchers?lang=
 │  GET v2/order/{order_id}/barcodes?lang=
 ↓
後端 API
```

### 回傳流

```
後端 API
 │  B2CApiResponse<VoucherListInfo>（憑證列表）
 │  B2CApiResponse<BarcodesResult>（條碼資料）
 ↓
Repository
 │  直接回傳原始 B2CApiResponse，無 model 轉換
 ↓
UseCase
 │  GetVoucherByOrderUseCase：成功時寫入記憶體快取
 │  emit ApiResult.Success / ApiResult.Error
 ↓
ViewModel
 │  全部成功：_pageState = RequestState.Success(PageData)
 │  任一失敗：_pageState = RequestState.Error(throwable)
 ↓
UI（MultiOrderVoucherDetailFragment）
 │  觀察：viewModel.pageState.observe(viewLifecycleOwner)
 ├─ Loading：顯示 loadingDialog
 ├─ Error：顯示 networkUnavailableViewHelper，隱藏 loadingDialog
 └─ Success：更新 multiOrderVoucherAdapter，觸發 eSIM 支援警告檢查
```

---

## 逐層說明

### UI 層
> `MultiOrderVoucherActivity` 為 Navigation Host，負責初始化 NavController 並傳遞 `MultiOrderVoucherRoutingInput` 給 Fragment。真正的 UI 邏輯在 `MultiOrderVoucherDetailFragment`，使用 RecyclerView + `MultiOrderVoucherAdapter` 展示憑證列表。點擊單一憑證會 navigate 至 `VoucherScanCodeFragment` 全螢幕顯示，支援 pinch-to-zoom 縮放（`ScaleGestureDetector`，1x ~ 2x）。分享憑證透過 `VoucherScreenShotGenerator` 截圖後呼叫系統分享。

### ViewModel 層
> 使用 `LiveData<RequestState<PageData>>` 管理頁面狀態。透過 `viewModelScope.launch` + `async-await` 並發發出 4 個非同步請求（vouchers、barcodes、eSIM instruction、eSIM one-click installation），全部完成後統一判斷成功/失敗。初始化時若傳入的 `voucherListInfo` 已有資料，直接設為 Success 狀態，跳過 API 呼叫。另處理 eSIM 不支援裝置的追蹤埋點。

### UseCase 層
> `GetVoucherByOrderUseCase` 具備 in-memory 快取（`HashMap<Pair<String, String>, B2CApiResponse<VoucherListInfo>>`，key 為 orderMid + language），同訂單同語系僅呼叫一次 API。
> `GetVoucherContentUseCase` 存在技術債：直接依賴 `OrderVoucherApiService`（Retrofit 介面），完全繞過 Repository 層，違反 Clean Architecture 分層原則，且未使用 `@Factory` 標注。

### Repository 層
> `OrderVoucherRepositoryImpl` 為薄層，無快取邏輯、無 model 轉換，直接代理 API Service 呼叫。Repository 介面定義於 module 內部 `domain/repository/` 而非全域 `:domain:contract`，未遵循專案理想架構。

### API 層
> 三個 endpoint：
> - `GET v2/order/{order_mid}/vouchers?lang=` → `B2CApiResponse<VoucherListInfo>`（訂單所有憑證）
> - `GET v2/order/{order_id}/barcodes?lang=` → `B2CApiResponse<BarcodesResult>`（條碼/QR code 結果）
> - `GET v2/voucher/{voucher_id}?last_modified=&lang=` → `B2CApiResponse<VoucherWrapperInfo>`（單一憑證內容，`last_modified` 支援差量更新）

---

## View 方法清單

### MultiOrderVoucherActivity

| 方法 | 說明 |
|------|------|
| `onCreate()` | 初始化 NavController，設定 Navigation Graph（`nav_order_voucher`），呼叫 `setupFragmentArguments()` |
| `onSaveInstanceState()` | 儲存 `MultiOrderVoucherRoutingInput` 至 Bundle，供橫豎切換恢復 |
| `restoreFromSaveInstance()` | 從 savedInstanceState 或 Intent extras 還原 routing input |
| `setupFragmentArguments()` | 將 routing input 轉為 Fragment ARG，navigate 至 `multiOrderVoucherDetailFragment` |
| `launch()` | 靜態工廠方法，建立 Intent 並啟動 Activity，可選 `ActivityResultLauncher` |

### MultiOrderVoucherDetailFragment

| 方法 | 說明 |
|------|------|
| `onResume()` | 每次頁面可見時觸發 `viewModel.fetchData()` 刷新資料 |
| `initView()` | 設定 RecyclerView（LinearLayoutManager + Adapter），設定返回按鈕點擊事件 |
| `initAction()` | 若 `voucherListInfo.vouchers` 為空則額外觸發一次 `fetchData()` |
| `observeData()` | 觀察 `pageState`，依 Loading / Error / Success 更新 UI |
| `onMultiVoucherViewAction()` | 處理三種 ViewAction：點擊憑證（navigate 至全螢幕）、點擊分享、點擊展開 |
| `showShareSuccessToast()` | 分享成功後顯示 Toast（3 秒後自動隱藏）|
| `setStatusBarColor()` | 設定 status bar 為 `kk_color_background_surface_light` |
| `onWhiteListClicked()` | 開啟 KKdayWebActivity 顯示白名單 URL |
| `onESimGuideClicked()` | 開啟 KKdayWebActivity 顯示 eSIM FAQ，並觸發追蹤事件 |

### VoucherScanCodeFragment

| 方法 | 說明 |
|------|------|
| `initView()` | 設定全螢幕 RecyclerView（PagerSnapHelper），載入憑證圖片，啟用 pinch-to-zoom |
| `setViewSupportScale()` | 透過 `ScaleGestureDetector` 支援捏合縮放（1x ~ 2x） |
| `setStatusBarColor()` | 設定 status bar 為白色（全螢幕模式） |
| `initAction()` | 無操作 |
| `observeData()` | 無操作（此 Fragment 無 ViewModel） |

---

## ViewModel 方法清單

### MultiOrderVoucherDetailViewModel

| 方法 | 說明 |
|------|------|
| `init` | 以傳入的 `voucherListInfo` 初始化 Success 狀態；啟動 eSIM 支援警告追蹤監聽 |
| `fetchData()` | 並發取得 vouchers、barcodes、eSIM instruction、eSIM one-click installation，合併為 `PageData` |
| `triggerTrackingESimSupportWarningChecking()` | 偵測裝置不支援 eSIM 且訂單為 eSIM 時，寫入 `_eSimNoticeShowingState` |
| `triggerTrackingESimSupportWarning()` | 監聽 `_eSimNoticeShowingState`，僅發送一次追蹤事件（`take(1)`） |
| `trackESimNotSupportMessage()` | 埋點：eSIM 不支援訊息 Impression |
| `trackClickShareVoucherLink()` | 埋點：點擊分享憑證連結 |
| `trackClickESimFAQ()` | 埋點：點擊 eSIM FAQ |

---

## 業務邏輯摘要

- **資料預載優化**：呼叫端（訂單詳情頁）可預先傳入 `VoucherListInfo`，若憑證列表非空則跳過 API 呼叫，直接渲染，減少等待時間。
- **記憶體快取**：`GetVoucherByOrderUseCase` 以 `(orderMid, language)` 為 key 快取 vouchers 結果，同訂單同語系在 App 生命週期內只呼叫一次 API。
- **並發請求**：頁面載入時同時發出 4 個並發請求（vouchers、barcodes、eSIM instruction、eSIM one-click installation），全部完成後統一更新 UI，降低總等待時間。
- **eSIM 支援檢查**：ViewModel 檢測裝置是否支援 eSIM，若不支援且訂單為 eSIM 類型，顯示提示並發送追蹤事件（僅觸發一次，透過 `take(1)`）。
- **全螢幕掃碼**：`VoucherScanCodeFragment` 支援水平/垂直方向的 RecyclerView 與 `PagerSnapHelper`，依憑證 `orientation` 屬性決定排列方向。
- **錯誤處理**：UseCase 層以 `catch` block 捕捉例外，統一回傳 `ApiResult.Error`；UI 層以 `networkUnavailableViewHelper` 呈現錯誤狀態。

---

## 已知技術債

- **`GetVoucherContentUseCase` 違反分層**：直接依賴 `OrderVoucherApiService`（Retrofit 介面），完全繞過 Repository 層，且未標注 `@Factory`，應重構為依賴 `OrderVoucherRepository`。
- **Repository 介面位置不正確**：`OrderVoucherRepository` 定義於 module 內部 `domain/repository/`，而非全域 `:domain:contract`，無法被其他 module 複用。
- **ViewModel 直接依賴 `ESimDcsRepository`**：`MultiOrderVoucherDetailViewModel` 直接注入 data 層 `ESimDcsRepository`（`@Single`），應透過 UseCase 抽象化，或至少依賴 `:domain:contract` 中的介面。
- **雙重觸發機制**：`onResume()` 與 `initAction()` 都可能觸發 `fetchData()`，邏輯重複，應統一為單一觸發點。

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

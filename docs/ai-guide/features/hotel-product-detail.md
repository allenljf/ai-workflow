# 飯店商品詳情頁 技術文件

> 自動產生 | 最後更新：2026-03-19

---

## 概述

- **所在 Module**：`:feature:hotel`（`libs/feature/hotel/product/`）
- **UI 入口**：`HotelProductDetailFragment.kt`
- **功能描述**：顯示飯店類型商品的詳細資訊、房間方案列表與價格，供使用者選擇房間方案後進入下單流程。支援 Hotel 2.0（舊版）與 Hotel Dynamic 3.0（新版）兩種資料版本並存。

---

## 檔案清單

```
UI（使用者介面入口）
 └─ HotelProductDetailFragment.kt          → libs/feature/hotel/product/.../presentation/view/

ViewModel（UI 狀態管理）
 ├─ HotelProductDetailViewModel.kt         → libs/feature/hotel/product/.../presentation/viewModel/
 ├─ BundleProductViewModel.kt              → libs/feature/hotel/product/.../presentation/viewModel/
 └─ HotelRoomPackageDialogViewModel.kt     → libs/feature/hotel/product/.../presentation/viewModel/

Domain（業務邏輯 UseCase）
 ├─ GetHotelRoomPackagesUseCase.kt         → domain/usecase/.../hotel/
 ├─ GetHotelOrderSpecDataUseCase.kt        → domain/usecase/.../hotel/
 └─ GetHotelV3OrderSpecDataUseCase.kt      → domain/usecase/.../hotel/

Data（資料層）
 └─ HotelProductRepository.kt（無介面分離）→ data/repository/.../hotel/

Network（API 定義）
 ├─ IHotelProductApiService.kt             → libs/networking/api/.../service/hotel/
 ├─ HotelDetailResponse.kt                 → libs/model/.../model/hotel/
 └─ HotelRoomDetailResponse.kt             → libs/model/.../model/hotel/

DI（依賴注入）
 └─ hotelProductModule.kt                  → libs/feature/hotel/product/.../di/
```

---

## 資料流

### 主流程（舊版 Hotel 2.0）：頁面載入取得商品資料

```
UI（HotelProductDetailFragment）
 │  initHotelProductAction() → initHotelRequest()
 │  判斷：isDynamicHotel = false
 │  呼叫：hotelProductVM.getHotelProductDetail(productId, isFromBack, isGetDetail)
 ↓
ViewModel（HotelProductDetailViewModel）
 │  _hotelProductPackageState = loading
 │  _bundlePackageState = loading
 │  呼叫：getProductUseCase.getProductDetailUseCase(productId, isGetDetail, Vertical.HOTEL)
 ↓
UseCase（GetProductUseCase）
 │  呼叫通用商品資料取得邏輯
 │  呼叫：hotelProductRepository.getHotelProductInfo(productMid)
 ↓
Repository（HotelProductRepository）
 │  呼叫：kkApi.b2cApi.hotelProduct.getHotelProductInfo(productMid)
 │  透過 safeApiCallFlow 包裝，自動處理快取與錯誤
 ↓
API（IHotelProductApiService）
 │  GET v2/cdn/product/{product_mid}/hotel
 ↓
後端 API
```

### 主流程（新版 Hotel Dynamic 3.0）：頁面載入取得動態飯店資料

```
UI（HotelProductDetailFragment）
 │  initHotelProductAction() → initHotelRequest()
 │  判斷：isDynamicHotel = true
 │  呼叫：hotelProductVM.getHotelDynamicProductDetail(productId, productDetailData)
 ↓
ViewModel（HotelProductDetailViewModel）
 │  直接呼叫：hotelProductRepository.getHotelDynamicProductDetail(productOid)
 │  （技術債：ViewModel 直接依賴 Repository，缺少 UseCase 抽象層）
 │  成功後 → 呼叫 getHotelRoomCombinePackage()
 ↓
Repository（HotelProductRepository）
 │  呼叫：kkApi.b2cApi.hotelProduct.getHotelDynamicProductDetail(HotelDetailRequestBody)
 ↓
API（IHotelProductApiService）
 │  POST v2/hotel/detail
 │  Body：HotelDetailRequestBody(productOid, basicHotelOid)
 ↓
後端 API
```

### 次流程：並發取得房間方案（2.0 + Dynamic 並發）

```
ViewModel（getHotelRoomCombinePackage）
 │  async 1：hotelProductRepository.getHotelProductPackage(productOid, dates, rooms)
 │  async 2（僅 Dynamic）：hotelProductRepository.getHotelDynamicRoomDetail(...)
 │  兩路並發執行，await() 等待後合併結果
 ↓
API 1（IHotelProductApiService）
 │  POST v2/product/{product_oid}/hotel/pkg
 │  Body：HotelPriceRequestBody(beginDate, endDate, rooms)
 ↓
API 2（IHotelProductApiService，僅 Dynamic）
 │  POST v2/hotel/detail/rooms
 │  Body：HotelRoomDetailRequestBody(productOid, checkIn, checkOut, adults, children, rooms, childrenAges)
 ↓
後端 API（兩路各自回應）
```

### 回傳流

```
後端 API
 │  B2CApiResponse<ProductDetailData>（舊版）
 │  B2CApiResponse<HotelDetailResponse>（新版 Dynamic）
 │  B2CApiResponse<PackageClusters>（房間 2.0 方案）
 │  B2CApiResponse<HotelRoomDetailResponse>（房間 Dynamic 方案）
 ↓
Repository（BaseApiRepository.safeApiCall / safeApiCallFlow）
 │  metadata.isResultSuccess() = true → ApiResult.Success(data)
 │  HTTP 錯誤 → handleApiError() → ApiResult.Error / ApiResult.Upgrade
 ↓
ViewModel
 │  ApiResult.Loading  → hotelProductDetailState = isLoading=true
 │  ApiResult.Success  → hotelProductDetailState = copy(productDetailData / productDynamicDetailData)
 │                     → 觸發 getHotelRoomCombinePackage()
 │  ApiResult.Error    → hotelProductDetailState = copy(error=desc)
 │  ApiResult.Upgrade  → KKEventBus.invokeEvent(ShowSystemUpgrade)
 │
 │  房間方案回傳：
 │  GetHotelRoomPackagesUseCase(PackageClusters) → List<RoomPackage>
 │  hotelProductPackageState = copy(data=room2Data, dynamicRooms=dynamicRoomData)
 │  bundlePackageState = copy(data=bundleData)
 ↓
UI（HotelProductDetailFragment）
 │  observeHotelProductData() / observeHotelDynamicData()
 │  成功：updateAppbarUI(), handleCommonHotelUI(), updateProductBasicInfo()
 │       productController.hotelPackage = packageState
 │  失敗（error）：networkUnavailableViewHelper.show()
 │  失敗（404）：KKBaseInfoDialog 彈出「商品已下架」提示
 └─ 系統升級：showSystemUnavailable()
```

---

## 逐層說明

### UI 層

`HotelProductDetailFragment` 繼承 `SharedProductDetailFragment`，複用商品頁基底 UI 架構。使用 `activityViewModel` 取得 `HotelProductDetailViewModel`（Activity scope 共享）。

進入頁面時，`initHotelProductAction()` 依 `hotelProductVM.isDynamicHotel` 決定走哪條請求路徑：
- 舊版（2.0）：`observeHotelProductData()` 單獨觀察 `hotelProductDetailState`
- 新版（Dynamic）：`observeHotelDynamicData()` 使用 `combine` 合併 `productVM.productDetailState` 與 `hotelProductVM.hotelProductDetailState`，Loading 狀態取決於 3.0 API 結果

`observerCommonData()` 觀察通用資料（評論、優惠券、活動 Banner、推薦商品等），兩個版本都會呼叫。

### ViewModel 層

使用多個 `MutableStateFlow` 管理頁面狀態：

| StateFlow | 型別 | 說明 |
|-----------|------|------|
| `hotelProductDetailState` | `HotelProductDetailUiState` | 商品主資料（loading/success/error） |
| `hotelProductPackageState` | `HotelProductPackageUiState` | 房間方案列表（2.0 + Dynamic） |
| `bundlePackageState` | `BundlePackagesUiState` | Bundle 套餐列表 |
| `hotelSearchFilter` | `HotelSearchFilter` | 目前日期/人數篩選條件 |
| `hotelSearchRestriction` | `HotelSearchRestriction` | 飯店入住限制（由 DCS 遠端配置） |
| `hotelOrderRouterdata` | `HotelOrderRouteData?` | 下單路由資料（準備好時觸發跳頁） |

DCS 設定透過 `hotelProductRepository.getHotelProductPageConfig()` 取得，覆寫預設的入住人數限制。

### UseCase 層

- `GetProductUseCase.getProductDetailUseCase`：取得通用商品資料（舊版路徑）
- `GetHotelRoomPackagesUseCase`：將 `PackageClusters` 轉換為 UI 用的 `List<RoomPackage>`，整合 VTag 標籤（`GetHotelVTagUseCase`）與退款政策（`GetHotelRefundPolicyUseCase`）
- `GetHotelOrderSpecDataUseCase`：組裝 Hotel 2.0 下單規格資料（`OrderSpecificationData`）
- `GetHotelV3OrderSpecDataUseCase`：組裝 Hotel Dynamic 3.0 下單規格資料

**技術債**：`getHotelDynamicProductDetail` 與 `getHotelRoomCombinePackage` 直接從 ViewModel 呼叫 Repository，缺少 UseCase 抽象層。

### Repository 層

`HotelProductRepository` 繼承 `BaseApiRepository`，**未實作 `domain/contract` 介面分離（技術債）**，直接透過 `KKApi` 呼叫各 API Service。

錯誤處理統一由 `BaseApiRepository` 負責：
- `safeApiCall`：包裝成 `Flow<ApiResult<T>>`，自動在頭尾發送 `Loading` / `Loaded`
- `safeApiCallFlow`：`suspend` 版本，支援 `CacheBehavior`（CacheOnly / CacheFirst / ReplaceApiError）
- HTTP 例外透過 `handleApiError()` 統一轉換，系統維護狀態碼會轉為 `ApiResult.Upgrade`
- DCS 設定（房間人數限制）透過 `Flow<HotelCategoryConfig?>` 回傳

### API 層

`IHotelProductApiService` 主要 Endpoint：

| Endpoint | 方法 | 說明 |
|----------|------|------|
| `v2/cdn/product/{product_mid}/hotel` | GET | 取得商品基本資料（舊版 2.0） |
| `v2/hotel/detail` | POST | 取得飯店 Dynamic 3.0 詳情 |
| `v2/product/{product_oid}/hotel/pkg` | POST | 取得房間 2.0 方案列表 |
| `v2/hotel/detail/rooms` | POST | 取得房間 Dynamic 方案列表 |
| `v2/product/{product_oid}/hotel/calendar` | GET | 取得日曆價格 |
| `v2/hotel/order/ext_data` | POST | 送出 Dynamic 3.0 下單前置資料 |

---

## View 方法清單

| 方法 | 說明 |
|------|------|
| `onAttach()` | 監聽 Fragment 掛載，處理 `KKBaseInfoDialog` 按鈕（商品下架後返回） |
| `onResume()` | 返回頁面時校正 shortcut tabs 顯示狀態 |
| `onDestroyView()` | 清除 stickyHeaderContent Compose 狀態 |
| `initView()` | 呼叫父類 + `initHotelProductUI()`，初始化飯店專屬 UI |
| `initOtherView()` | 設定公告 BottomSheet、房間詳情 BottomSheet（Compose），處理新版 Dynamic BottomSheet 顯示邏輯 |
| `initAction()` | 呼叫父類 + `initHotelProductAction()`，觸發資料請求 |
| `initHotelProductUI()` | 隱藏加購鍵、顯示「查看方案」按鈕，初始化吸頂容器 |
| `initHotelProductAction()` | 依 `needRequest` 決定是否發起 API 請求，註冊登入回調 |
| `initHotelRequest()` | 依 `isDynamicHotel` 走新舊版 API |
| `observeData()` | 決定觀察新版（Dynamic）或舊版資料流 |
| `observeHotelProductData()` | 觀察 Hotel 2.0 所有 StateFlow |
| `observeHotelDynamicData()` | 觀察 Hotel 3.0 + combine 資料，處理 Dynamic 專屬 UI |
| `observerCommonData()` | 觀察評論、優惠券、活動 Banner、推薦商品等通用資料 |
| `updateProductBasicInfo()` | 更新商品 AppBar 基本資訊（標題、評分、地圖按鈕） |
| `handleHotelDynamicUI()` | 更新 Dynamic 飯店照片、AppBar 資料 |
| `handleHotelDynamicFooterUI()` | 更新底部價格區塊（折扣標籤、最低價格） |
| `updateBookingButton()` | 更新「查看方案」按鈕可用狀態（舊版） |
| `onClickBookNow()` | 點擊立即預訂，呼叫 ViewModel 組裝下單資料後跳頁 |
| `hotelV3RouterToOrderFormPage()` | Dynamic 版本跳轉下單頁（呼叫 setHotelExtData 後跳頁） |
| `scrollToPackage()` | 捲動至房間方案區塊 |

---

## ViewModel 方法清單

| 方法 | 說明 |
|------|------|
| `getHotelProductDetail()` | 舊版：呼叫 `GetProductUseCase` 取得 Hotel 2.0 商品資料 |
| `getHotelDynamicProductDetail()` | 新版：直接呼叫 Repository 取得 Hotel Dynamic 3.0 商品資料 |
| `getHotelRoomCombinePackage()` | 並發取得 2.0 + Dynamic 房間方案，await 後合併更新狀態 |
| `setHotelSearchRestriction()` | 設定入住日期/人數限制（先用預設值，再從 DCS 覆寫） |
| `getHotelPackageRoomInput()` | 組裝房間請求參數，首次進入時與快取搜尋條件比對並校正 |
| `updateHotelSearchFilter()` | 更新搜尋篩選條件，使用者手動更改時同步 `HotelSearchRepository` |
| `getHotelOrderRouteData()` | 組裝 2.0 下單路由資料（呼叫 `GetHotelOrderSpecDataUseCase`） |
| `getHotelV3OrderRouteData()` | 組裝 3.0 下單路由資料（呼叫 `setHotelExtData` + `GetHotelV3OrderSpecDataUseCase`） |
| `getPackageItemById()` | 依 clusterOid + packageOid 取得選中的 2.0 房間方案 |
| `getV3RoomItemById()` | 依 itemOid + roomTypeId + ratePlanUniqueKey 取得選中的 3.0 房間 |
| `setDynamicHotel()` | 標記此商品為 Dynamic 飯店（由 Fragment 在 `beforeObserveData` 呼叫） |
| `reloadBundleList()` | 重新載入房間方案列表 |
| `setHotelDetailBottomSheetContent()` | 設定飯店介紹 BottomSheet 內容 |
| `setHotelRatePlanBottomSheetContent()` | 設定房型詳情 BottomSheet 內容 |
| `triggerShowAnnouncementBottomSheet()` | 觸發公告 BottomSheet 顯示 |
| `trackClickProdPgMap()` | 追蹤點擊地圖事件 |
| `trackViewProdPg()` | 追蹤商品頁瀏覽事件（KKTracker + KTMTracker） |

---

## 業務邏輯摘要

- **新舊版並存**：依 `ProductDetailRouteData.vertical` 決定走 `HOTEL_DYNAMIC`（3.0）或 `HOTEL`（2.0）路徑，在 `beforeObserveData()` 中設定 `isDynamicHotel` 旗標
- **房間方案並發**：`getHotelRoomCombinePackage()` 使用 `async/await` 並發呼叫 2.0 與 Dynamic 兩組 API，任一失敗不影響另一路資料顯示
- **搜尋條件校正**：首次進入（`isFirstEnterAutoFilter=true`）時從快取取得搜尋條件，比對飯店入住人數與日期限制，超出範圍則自動修正為預設值
- **DCS 遠端設定**：`hotel_productpage_search_config` 透過 DCS 取得搜尋限制（成人/兒童數量、兒童年齡範圍），覆寫預設常數
- **下架商品處理**：API 回傳 `productSetting.isNoLongerSold() = true` 時，顯示不可關閉的 Dialog 並在確認後退出頁面；API 回傳 404 時觸發 KTM 追蹤 `InvalidPg` 事件
- **系統升級**：`ApiResult.Upgrade` 透過 `KKEventBus` 廣播 `ShowSystemUpgrade` 事件，由上層統一處理
- **Dynamic 下單前置**：3.0 下單前需先呼叫 `POST v2/hotel/order/ext_data` 送出 `HotelDynamicInfoV2`（含飯店名稱、地址、搜尋條件、房間資訊），成功後才更新 `hotelOrderRouterdata` 觸發跳頁

---

## 已知技術債

- `HotelProductRepository` 未實作 `domain/contract` 介面分離，直接注入 `KKApi`，與理想 Clean Architecture 不符
- `getHotelDynamicProductDetail()` 和 `getHotelRoomCombinePackage()` 在 ViewModel 直接呼叫 Repository，缺少 UseCase 抽象層
- `HotelProductDetailViewModel` 依賴多個 Repository（`HotelProductRepository`、`ProductRepository`、`BookingRepository`、`BundleRepository`、`HotelSearchRepository`），建構子過重，應逐步拆分至 UseCase
- Hotel 2.0 與 Hotel 3.0 邏輯混在同一個 ViewModel 和 Fragment 中，條件判斷分支複雜，建議長期拆分

## 相關筆記
- [01-architecture](../01-architecture.md)
- [02-modules](../02-modules.md)
- [03-ui-patterns](../03-ui-patterns.md)
- [05-networking](../05-networking.md)
- [06-data-layer](../06-data-layer.md)
- [07-concurrency](../07-concurrency.md)
- [jira-auto-analysis-pipeline](../workflow/jira-auto-analysis-pipeline.md)
- [order-detail-compose](order-detail-compose.md)
- [product-detail](product-detail.md)
- [sku-activity-shell](sku-activity-shell.md)

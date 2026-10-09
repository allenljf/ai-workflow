# 通用商品詳情頁 技術文件

> 自動產生 | 最後更新：2026-03-19

---

## 概述

- **所在 Module**：`:feature:product_page`
- **UI 入口**：`CommonProductDetailFragment.kt`
- **功能描述**：顯示通用商品（非飯店）的完整資訊，包括商品圖片、方案選擇、日曆、評論、優惠券、公告等，並提供購買/加入購物車入口

---

## 檔案清單

```
UI（使用者介面入口）
 ├─ CommonProductDetailFragment.kt       → libs/feature/product_page/.../detail/view/
 ├─ SharedProductDetailFragment.kt       → libs/feature/product_page/.../detail/view/（父類，核心 UI 邏輯）
 └─ CommonProductDetailController.kt     → libs/feature/product_page/.../detail/controller/（Epoxy Controller）

ViewModel（UI 狀態管理）
 └─ ProductDetailViewModel.kt            → libs/feature/product_page/.../detail/viewModel/

Domain（UseCase 聚合）
 ├─ GetProductUseCase.kt                 → libs/feature/product_page/.../domain/useCase/（聚合以下 UseCase）
 │   ├─ GetProductDetailUseCase.kt       → 取得商品詳情
 │   ├─ GetProductPackagesUseCase.kt     → 取得商品方案
 │   ├─ GetProductPackageCalendarUseCase.kt → 取得方案日曆
 │   ├─ GetProductAnnouncementUseCase.kt → 取得商品公告
 │   ├─ GetProductPromoBannerUseCase.kt  → 取得促銷 Banner
 │   ├─ TrackSelectedOrderDateUseCase.kt → 追蹤選擇日期
 │   ├─ GetProductRedirectUrlUseCase.kt  → 交通商品轉導
 │   └─ GetProductRelocateUseCase.kt     → 交通商品搬遷
 ├─ UserCommentUseCase.kt               → 取得使用者評論
 ├─ GetProductCouponsUseCase.kt          → 取得商品優惠券
 ├─ GetTravelerTypeUseCase.kt            → 取得旅客類型
 ├─ OrderUserKKPointsUseCase.kt          → KKday 點數估算
 ├─ GetFreshChatStatusUseCase.kt         → 客服聊天狀態
 ├─ TrackChatOpenedUseCase.kt            → 追蹤客服開啟
 ├─ TrackNavBarItemClickedUseCase.kt     → 追蹤導覽列點擊
 ├─ AddWishProductUseCase.kt             → libs/feature/product_core/.../domain/useCase/（加入願望清單）
 └─ DeleteWishProductUseCase.kt          → libs/feature/product_core/.../domain/useCase/（移除願望清單）

Data（資料層）
 ├─ ProductRepository.kt                 → data/repository/（主要資料存取，依賴 KKApi）
 └─ ProductDetailDcsRepository.kt        → libs/feature/product_page/.../domain/repository/（DCS 遠端設定）

Network（API 定義）
 └─ IProductApiService.kt                → libs/networking/api/.../service/product/

Data Model（主要）
 ├─ ProductDetailData                    → libs/networking/api/.../resource/product/
 ├─ ProductPackagesData                  → data/model/
 ├─ ProductPackageCalendarData           → shared/base/.../model/product/
 └─ ProductDetailState / ProductPackagesState → libs/feature/product_page/.../detail/state/
```

---

## 資料流

### 主流程：頁面載入取得商品詳情

```
UI（SharedProductDetailFragment）
 │  onViewCreated → observeData + initView
 │  呼叫：productVM.getProductDetail(productId, isFromBack, isGetProductDetail)
 ↓
ViewModel（ProductDetailViewModel）
 │  透過 getProductUseCase.getProductDetailUseCase(productId, isGetProductDetail)
 │  收集 Flow，更新 _productDetailState
 ↓
UseCase（GetProductDetailUseCase）
 │  判斷是否需要重新請求（快取於 AppSharedData）
 │  依 vertical 類型決定呼叫 productRepository 或 hotelProductRepository
 │  呼叫：productRepository.getProductDetail(productId, currency, lang, countryCode)
 ↓
Repository（ProductRepository）
 │  先追蹤瀏覽：trackProductView（fire-and-forget）
 │  呼叫：kkApi.b2cApi.product.getProductDetail(...)
 │  錯誤處理：商品下架 / 找不到 / 系統升級
 ↓
API（IProductApiService）
 │  GET v2/cdn/product/{product_mid}
 │  Header: currency, lang, locale
 ↓
後端 API
```

### 回傳流

```
後端 API
 ↓
Repository：B2CApiResponse<ProductDetailData> → apiResultData 解包
 ↓
UseCase：判斷 metadata status，轉為 ApiResult<ProductDetailData>
 │  商品下架 → ApiResult.success(NoLongerSoldProduct)
 │  找不到   → ApiResult.success(NotFoundProduct)
 │  系統升級 → ApiResult.upgrade(SystemUpgrade)
 │  成功     → ApiResult.success(data)
 ↓
ViewModel：更新 _productDetailState（ProductDetailState）
 │  成功後觸發後續 API：callNextAPIsWithOutPackagesWhenProductDetailReady
 ↓
UI（SharedProductDetailFragment）
 │  觀察 productDetailState，更新畫面
 └─ 成功：設定商品資料、初始化各區塊（方案、日曆、評論等）
    下架：顯示 KKBaseInfoDialog 提示
    錯誤：顯示錯誤狀態
```

### 次要流程：取得商品方案與日曆

```
ViewModel.getProductPackages(productId, useHybridCalendar)
 ↓
GetProductPackagesUseCase.invoke(productId, useHybridCalendar)
 ↓
ProductRepository.getProductPackages(...)
 ↓
IProductApiService: GET v2/product/{product_mid}/pkg
```

```
ViewModel.loadMorePackageCalendarData(productId, ...)
 ↓
GetProductPackageCalendarUseCase.invoke(productId, loadedCalendar, useHybridCalendar)
 ↓
ProductRepository.getProductPackageCalendar(...)
 ↓
IProductApiService: GET v2/product/{product_mid}/calendar
```

---

## 逐層說明

### UI 層
> `CommonProductDetailFragment` 繼承 `SharedProductDetailFragment`，後者繼承 `BaseFragment`。核心 UI 邏輯集中在 `SharedProductDetailFragment`，使用 Epoxy（`CommonProductDetailController`）構建 RecyclerView 列表。Fragment 負責觀察 ViewModel 的多個 StateFlow，依狀態更新畫面區塊（商品資訊、方案列表、日曆、評論、優惠券、公告、推薦商品等）。子類 `CommonProductDetailFragment` 僅覆寫 `showCalendar` 與 `launchSpecification` 等抽象方法，提供通用商品的日曆顯示與規格選擇路由。

### ViewModel 層
> `ProductDetailViewModel` 使用 `@KoinViewModel` 注解，透過 Koin 注入大量 UseCase 與 Repository。狀態管理全部使用 `MutableStateFlow` / `StateFlow`，無 LiveData。init 區塊初始化 A/B 測試、DCS 設定、客服標籤等背景資料。商品詳情載入成功後，觸發一連串次要 API 呼叫（公告、促銷、供應商資訊等）。追蹤邏輯使用 `combine` 多個 StateFlow 加 `debounce(2000ms)` 確保所有資料就緒後才發送頁面瀏覽事件。

### UseCase 層
> `GetProductUseCase` 為聚合類，持有 8 個子 UseCase。`GetProductDetailUseCase` 為核心，回傳 `Flow<ApiResult<ProductDetailData>>`，包含完整的錯誤處理（商品下架、找不到、系統升級、HTTP 例外）。其他 UseCase 各負責單一 API 呼叫，遵循 `operator fun invoke()` 慣例。

### Repository 層
> `ProductRepository`（位於 `data/repository/`）依賴 `KKApi`，透過 `kkApi.b2cApi.product` 呼叫 `IProductApiService` 各方法。使用 `BaseApiRepository` 的 `apiResultData` / `safeApiCall` 統一解包。`ProductDetailDcsRepository` 獨立處理 DCS 遠端設定（售前客服開關、FreshBot 標籤、USJ 快速通關等）。

### API 層
> `IProductApiService` 定義所有商品相關 Retrofit 端點，主要包括：

| 端點 | 方法 | 用途 |
|------|------|------|
| `v2/cdn/product/{product_mid}` | GET | 商品詳情 |
| `v2/product/{product_mid}/pkg` | GET | 商品方案列表 |
| `v2/product/{product_mid}/calendar` | GET | 方案日曆 |
| `v3/product/{prod_oid}/calendar` | GET | Tour 商品日曆 |
| `v2/product/{product_oid}/announcement` | GET | 商品公告 |
| `v2/product/{product_oid}/coupons` | GET | 商品優惠券 |
| `v3/recommend/product/also_view` | GET | 推薦商品 |
| `v2/product/review/comment_summaries` | GET | 評論摘要 |
| `v2/product/review/comments` | GET | 評論列表 |
| `v3/cdn/product/{productId}/action_flows` | GET | 商品操作流程 |
| `v3/product/{productOid}/packages-groups` | GET | 方案群組 |
| `v2/product/{product_oid}/promo-banner` | GET | 促銷 Banner |
| `v2/tracking/product/view` | POST | 瀏覽追蹤 |
| `v2/faq/freshchat/status` | POST | 客服聊天狀態 |

---

## View 方法清單

> `SharedProductDetailFragment`（主要邏輯所在）

| 方法 | 說明 |
|------|------|
| `onCreate()` | 初始化參數、註冊 BackPress callback |
| `initView()` | 設定 RecyclerView（Epoxy）、綁定購買/加入購物車按鈕、初始化 AppBar |
| `initAction()` | 設定 Toolbar 返回、聊天按鈕點擊等事件 |
| `observeData()` | 註冊所有 ViewModel StateFlow 觀察者 |
| `observerData()` | 觀察商品詳情、方案、日曆、評論、優惠券、公告、推薦等狀態 |
| `initHeaderView()` | 初始化商品頭部資訊（圖片輪播、標題） |
| `setProductIntro()` | 設定商品介紹區塊 |
| `showCalendarFragment()` | 顯示日曆 Fragment |
| `showBottomSheet()` | 展開方案詳情 BottomSheet |
| `updateCartButton()` | 更新底部購買/加入購物車按鈕狀態 |
| `onProductCouponClicked()` | 處理優惠券點擊，顯示詳情 Fragment |
| `onClickChatFloatingButton()` | 處理客服聊天浮動按鈕點擊 |
| `goToContactMarketPlace()` | 導航至聯絡商家頁 |
| `scrollToPackageWithRetry()` | 滾動至方案區塊（含重試機制） |
| `callNextAPIsWhenProductDetailReady()` | 商品詳情就緒後觸發次要 API |
| `showLoadingProgress()` | 控制載入進度顯示/隱藏 |

> `CommonProductDetailFragment`（子類覆寫）

| 方法 | 說明 |
|------|------|
| `initOtherView()` | 空實作（通用商品無額外初始化） |
| `beforeObserveData()` | 空實作 |
| `showCalendar()` | 呼叫 `showCalendarFragment()` 顯示日曆 |
| `launchSpecification()` | 透過 KRouter 導航至規格選擇頁 |

---

## ViewModel 方法清單

| 方法 | 說明 |
|------|------|
| `init` | 載入 DataStore 快取、初始化 A/B 測試、DCS 設定、客服標籤 |
| `getProductDetail()` | 核心方法：呼叫 GetProductDetailUseCase 取得商品資料，更新 productDetailState |
| `getProductPackages()` | 取得商品方案列表，更新 productPackagesState |
| `loadMorePackageCalendarData()` | 載入更多月份的日曆資料 |
| `callNextAPIsWithOutPackagesWhenProductDetailReady()` | 商品詳情成功後觸發公告、促銷、供應商等 API |
| `getRecommendProducts()` | 取得推薦商品 |
| `getUserComment()` | 取得 AI 評論摘要 |
| `getProductCoupons()` | 取得商品優惠券 |
| `getProductAnnouncement()` | 取得商品公告 |
| `getOrderUserKKPoints()` | 估算 KKday 點數 |
| `getProductPromoBanners()` | 取得促銷 Banner |
| `getDCSFreshTags()` | 取得 DCS 客服標籤 |
| `getDCSConfigTags()` | 取得 DCS 設定（USJ 快速通關等） |
| `selectDate()` | 設定選擇日期，更新 selectedDateFlow |
| `refreshPackageListViewUIBySelectedDate()` | 依選擇日期刷新方案列表 |
| `addWishProduct()` / `removeWishProduct()` | 願望清單操作 |
| `getProductActionFlow()` | 取得商品操作流程設定 |
| `checkPackageCalendar()` | 檢查方案日曆可用性 |
| `sortPackageList()` | 依選擇日期排序方案（可售優先） |
| `getProductRedirectUrl()` / `getProductRelocate()` | 交通商品轉導/搬遷 |
| `getFreshChatStatus()` | 檢查客服聊天是否可用 |
| `checkUnreadChatNotification()` | 檢查未讀客服通知數 |
| `trackProductPageViewed()` 等 track* 方法 | 各類追蹤事件（頁面瀏覽、按鈕點擊、曝光等） |

---

## 業務邏輯摘要

- 商品詳情取得後，依 `vertical` 類型決定顯示方式（通用 / 飯店 / 交通），交通商品可能需要轉導至外部 WebView
- 方案日曆支援分月載入（`loadMorePackageCalendarData`），用戶滑動月曆時動態請求
- 商品下架（`PRODUCT_IS_NOT_SOLD` / `PRODUCT_IS_CLOSE_SOLD`）時顯示固定提示，不允許返回
- 追蹤頁面瀏覽事件需等待多個 API 回應就緒（商品詳情、供應商、客服狀態、方案、日曆），使用 `combine` + `debounce(2s)` 確保完整性
- DCS 遠端設定控制售前客服顯示（`HidePresaleSupportData`）、FreshBot 標籤、USJ 快速通關等功能開關
- 購買按鈕依登入狀態、商品類型（KHSR 高鐵）切換行為
- A/B 測試（`ProdPgPresaleSupportV2`）控制售前客服 UI 版本

---

## 已知技術債

- `ProductDetailViewModel` 直接注入 `ProductRepository`（`com.kkday.data.repository.ProductRepository`），未透過 `domain/contract` 介面抽象，違反 Clean Architecture 依賴規則
- `ProductDetailDcsRepository` 位於 `domain` 套件下但直接依賴 `KKApi`，實質為 Data 層，放置位置不符架構規範
- `ProductDetailViewModel` 建構子注入超過 20 個依賴，職責過重，追蹤邏輯與業務邏輯混合
- `SharedProductDetailFragment` 超過 2500 行，承載過多 UI 邏輯，應進一步拆分
- `GetProductDetailUseCase` 內含 HTTP 例外解析邏輯（JSON 手動解析 errorBody），應由 Repository 層統一處理
- `ProductRepository`（`data/repository/`）同時處理商品、評論、旅客、優惠券、追蹤等功能，違反單一職責原則

## 相關筆記
- [02-modules](../02-modules.md)
- [03-ui-patterns](../03-ui-patterns.md)
- [05-networking](../05-networking.md)
- [06-data-layer](../06-data-layer.md)
- [07-concurrency](../07-concurrency.md)
- [hotel-product-detail](hotel-product-detail.md)
- [order-detail-compose](order-detail-compose.md)
- [sku-activity-shell](sku-activity-shell.md)
- [sku-base](sku-base.md)
- [trans-product-detail](trans-product-detail.md)

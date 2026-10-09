# 目的地頁 技術文件

> 自動產生 | 最後更新：2026-03-19

---

## 概述

- **所在 Module**：`:feature:search_page`（UI/ViewModel）、`:feature:search_core`（Repository/API）
- **UI 入口**：`DestinationPageActivity.kt`
- **功能描述**：依目的地代碼（`DestinationCode`）或 URL 路徑展示目的地頁，包含頁面設定、分類、Top 商品、Showcase、熱門城市、部落格導覽、個人化推薦、無限滾動探索等多區塊內容。

---

## 檔案清單

```
UI（使用者介面入口）
 ├─ DestinationPageActivity.kt   → libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/category/
 └─ DestinationPage.kt（Compose）→ libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/category/compose/main/

ViewModel（UI 狀態管理）
 └─ DestinationPageViewModel.kt  → libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/category/viewmodel/
    └─ WishViewModel.kt（父類）  → libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/category/viewmodel/

Domain（業務邏輯）
 └─ UseCase 層不存在，ViewModel 直接依賴 Repository（技術債）

Data（資料層）
 ├─ DestinationRepository.kt（介面） → libs/feature/search_core/src/main/java/com/kkday/search/domain/repository/
 ├─ DestinationRepositoryImpl.kt     → libs/feature/search_core/src/main/java/com/kkday/search/data/repository/
 ├─ SearchExploreRepository.kt       → libs/feature/search_page/src/main/java/com/kkday/search_page/domain/repository/
 └─ RecommendCategoryRepository.kt   → libs/feature/search_page/src/main/java/com/kkday/search_page/domain/repository/

Network（API 定義）
 └─ DestinationApiService.kt         → libs/feature/search_core/src/main/java/com/kkday/search/network/

Data Model
 ├─ DestinationPageSetting.kt        → libs/model/src/main/java/com/kkday/library/networking/resource/search/destination/
 ├─ RecommendCategoryCategories.kt   → libs/model/src/main/java/com/kkday/library/common/model/search/recommend/
 ├─ RecommendCategoryProducts.kt     → libs/model/src/main/java/com/kkday/library/common/model/search/recommend/
 ├─ RecommendCategoryShowcases.kt    → libs/model/src/main/java/com/kkday/library/common/model/search/recommend/
 └─ RecommendPopularDestinationResult.kt → libs/model/src/main/java/com/kkday/library/common/model/search/recommend/

Paging
 └─ DestinationExplorePagingSource.kt → libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/category/compose/paging/
```

---

## 資料流

### 主流程：頁面初始化資料載入

```
UI（DestinationPageActivity）
 │  onCreate 呼叫 setContent，傳入 DestinationPage Composable
 │  ViewModel 在建構時（init）自動觸發 requestInit() 或 requestInitFromUrl()
 ↓
ViewModel（DestinationPageViewModel）
 │  若有 destinationCode → requestInit(destinationCode)
 │  若有 destinationUrlPath → requestInitFromUrl(url) → 取得 code 後再呼叫 requestInit()
 │  狀態以 Compose mutableStateOf / mutableStateListOf 管理
 ↓
Repository（DestinationRepositoryImpl）
 │  依各方法呼叫 DestinationApiService 對應 API
 │  以 BaseApiRepository.safeApiCall 包裝，轉換為 Flow<ApiResult<T>>
 ↓
API（DestinationApiService）
 │  Retrofit 介面，對接後端各個 v2/recommend/destination/* 端點
 ↓
後端 API
```

### 探索無限滾動流程（Paging3）

```
UI（DestinationPage Composable）
 │  呼叫 viewModel.getInitialExploreItems()
 ↓
ViewModel
 │  建立 DestinationExplorePagingSource
 │  以 Pager + cachedIn(viewModelScope) 產生 Flow<PagingData<B2CProductCardData>>
 ↓
DestinationExplorePagingSource
 │  每次分頁呼叫 getRecommendDestinationExplore(start, count, requestBody)
 ↓
Repository（DestinationRepositoryImpl）
 │  POST v3/recommend/destination/explore
 ↓
後端 API
```

### 回傳流

```
後端 API
 ↓
Repository：B2CApiResponse<T> → ApiResult<T>（由 safeApiCall 轉換）
 ↓
ViewModel：apiSuccess { } 解包，更新對應 mutableStateOf 欄位
 ↓
UI（Composable）：直接讀取 ViewModel 的 State 屬性（Compose 狀態自動重組）
 └─ 成功：各區塊渲染商品、城市、部落格等資料
    失敗：apiSuccess 失敗時不更新狀態，UI 維持空白或初始狀態
```

---

## 逐層說明

### UI 層

`DestinationPageActivity` 繼承 `BaseComposeActivity`，透過 `@Router(KRouterConst.PAGE_DESTINATION)` 及 `@RouterParam` 接收路由參數（`destinationCode`、`destinationUrlPath`、`exploreTabIndex`、`exploreRowIndex`）。`onCreate` 呼叫 `setContent`，先呼叫 `destinationPageVM.getDestinationSettings()` 取得設定後才渲染 `DestinationPage`；同時送出 KTM 頁面載入埋點。`onResume` 呼叫 `destinationPageVM.refreshWish()` 更新收藏狀態。

`DestinationPage` 是 Jetpack Compose 函式，使用 `LazyVerticalStaggeredGrid` 呈現各區塊內容。

### ViewModel 層

`DestinationPageViewModel` 繼承 `WishViewModel`，狀態全部使用 Compose 的 `mutableStateOf` / `mutableStateListOf` 管理（非 StateFlow/LiveData），Composable 直接讀取方法回傳值。探索模組使用 Paging3 的 `Flow<PagingData<B2CProductCardData>>`（`exploreProductsState`）。

`_impressionExploreItems` 以 `MutableStateFlow` 收集已曝光的商品，並透過 `collectInVM` 持續更新 `DestinationExplorePagingSource` 的 request，實現曝光排重。

A/B 測試：`getDestinationPgRecomDefault()` 在 init 時從 `KKAbTestingService` 取得目的地推薦預設 Tab 的實驗分組。

### UseCase 層

此功能**無 UseCase 層**，`DestinationPageViewModel` 直接持有並呼叫 `DestinationRepository`、`SearchExploreRepository`、`RecommendCategoryRepository`（技術債：應透過 UseCase 抽象）。部分業務邏輯（如類別 URL 路徑解析、Tier-1 分類查找）直接寫在 ViewModel 中。

例外：`HotelCategoryLauncherByUrlUseCase`、`ProductCardTrackingUseCase` 為 UseCase，負責飯店分類啟動與商品卡追蹤。

### Repository 層

| Repository | 功能 |
|------------|------|
| `DestinationRepository` / `DestinationRepositoryImpl` | 主要資料來源，負責頁面設定、分類、商品、城市、部落格等所有目的地相關 API |
| `SearchExploreRepository` | 依分類取得目的地列表（由 `SearchApiService` 提供） |
| `RecommendCategoryRepository` | 提供推薦分類相關 API（由 `SearchApiService` 提供） |

`DestinationRepositoryImpl` 繼承 `BaseApiRepository`，以 `safeApiCall { }` 統一包裝 Retrofit 呼叫，轉換錯誤為 `ApiResult.Error`。無本地快取（Room/DataStore）邏輯，但 ViewModel 使用 DataStore 讀取 `ProductCategoryUrl` 設定。

### API 層

`DestinationApiService`（Retrofit 介面）主要端點：

| 方法 | HTTP | Endpoint | 說明 |
|------|------|----------|------|
| `getDestinationSettingByUrl` | GET | `v2/recommend/destination/page_setting?url_name=` | 依 URL 取得頁面設定 |
| `getDestinationSettingByCode` | GET | `v2/recommend/destination/page_setting?code=` | 依代碼取得頁面設定 |
| `getDestinationPageCategories` | GET | `v2/recommend/destination/search/categories` | 取得分類列表 |
| `getDestinationPageTopProducts` | GET | `v2/recommend/destination/top_products` | Top 商品 |
| `getDestinationPagePopularDestinations` | GET | `v2/recommend/destination/popular_destinations` | 熱門目的地 |
| `getDestinationShowcaseProducts` | GET | `v2/recommend/destination/showcase_products` | Showcase 商品 |
| `getDestinationPersonalProducts` | GET | `v2/recommend/destination/personal` | 個人化推薦商品 |
| `getDestinationNewProducts` | GET | `v2/recommend/destination/new_products` | 新品 |
| `getNearByDestinations` | GET | `v2/recommend/destination/nearby_destinations` | 附近目的地 |
| `getBlogGuide` | GET | `v2/blog` | 部落格導覽 |
| `getRecommendDestinationExplore` | POST | `v3/recommend/destination/explore` | 探索分頁商品（含曝光 request body） |
| `getRecommendDestinationCategoryExplore` | POST | `v3/recommend/destination/category_explore` | 分類探索分頁商品 |

---

## View 方法清單（DestinationPageActivity）

| 方法 | 說明 |
|------|------|
| `onCreate()` | 初始化路由參數、StatusBar，設定 Compose UI，送出頁面載入埋點 |
| `onResume()` | 呼叫 `destinationPageVM.refreshWish()` 更新收藏狀態 |
| `openUrl()` | 開啟 KKday WebView 頁並送出 Banner 點擊埋點 |
| `goProduct()` | 導航至商品詳情頁（`KRouterConst.ACTION_OPEN_PRODUCT`） |
| `openDeepLink()` | 解析 deeplink URL；若 URL 非空則 launchDeepLink，否則導航至搜尋結果頁 |
| `initStatusBar()` | 設定全螢幕透明 StatusBar |
| `searchClick()` | 導航至搜尋頁（`KRouterConst.PAGE_SEARCH`），附帶 fromPage 參數 |

---

## ViewModel 方法清單（DestinationPageViewModel）

| 方法 | 說明 |
|------|------|
| `init` | 觸發 A/B 測試取得、依參數呼叫 `requestInit` 或 `requestInitFromUrl`；監聽曝光狀態更新 PagingSource |
| `getInitialExploreItems()` | 建立 `DestinationExplorePagingSource` 並初始化 Pager flow |
| `setImpressionExploreItem()` | 記錄已曝光商品 ID，並呼叫 `productCardTrackingUseCase` 發送曝光事件 |
| `requestInit()` | 依序請求頁面設定、分類、Top商品、Showcase、熱門城市、部落格、個人化、新品、附近目的地 |
| `requestInitFromUrl()` | 先依 URL 取得 `DestinationCode`，再呼叫 `requestInit()` |
| `requestPersonalRecommend()` | 請求個人化推薦商品 |
| `requestNewProducts()` | 請求新品 |
| `requestShowcaseProducts()` | 請求 Showcase 商品（過濾空商品的 showcase） |
| `requestHotCities()` | 請求熱門城市 |
| `requestBlogs()` | 請求部落格導覽 |
| `requestNearByDestinations()` | 請求附近目的地 |
| `navigatorSearchResultPage()` | 根據分類代碼解析 Tier-1 URL、送埋點，導航至搜尋結果頁；飯店分類走 `hotelCategoryLauncherByUrlUseCase` |
| `setFaqExpandState()` | 設定 FAQ 展開/收合狀態（以 `MutableIntSet` 記錄） |
| `getDestinationSettings()` | 取得 `DestinationPageSetting` |
| `getRecommendCategories()` | 取得推薦分類 |
| `getBanner()` | 取得 Banner 列表 |
| `getTopTenProdData()` / `getTopTenProducts()` | 取得 Top 商品資料 |
| `getShowCaseData()` / `getShowcases()` / `getTransports()` | 取得 Showcase 與交通資料 |
| `getHotCities()` / `getNearByCities()` | 取得熱門/附近城市列表 |
| `getBlogGuides()` | 取得部落格列表 |
| `getPersonalProducts()` / `getNewProducts()` | 取得個人化/新品商品列表 |
| `convertNewProductViewStateList()` | 將新品轉為 `MediumProductCardViewState`（含格式化價格與收藏狀態） |
| `convertPersonalProductViewStateList()` | 將個人化推薦轉為 `MediumProductCardViewState` |
| `convertTopTenProductViewStateList()` | 將 Top 商品轉為 `MediumProductCardViewState` |
| `getCategoryPageViewState()` | 取得當前分類頁狀態（分類代碼、名稱、位置代碼等） |
| `isTaiwanMarket()` | 判斷是否為台灣市場（語言為 ZH_TW_TAIWAN） |
| `trackClickBanner()` | 送出 Banner 點擊埋點（KKTracker） |
| `trackClickProdCat()` | 送出商品分類點擊埋點 |
| `trackClickProdCard()` | 送出商品卡點擊埋點（KTM） |
| `trackClickDestinationRecommend()` | 送出目的地推薦點擊埋點（KTM） |
| `trackPOIClick()` | 送出探索區塊商品點擊埋點（productCardTrackingUseCase） |
| `trackImpressionInfinityLoop()` | 送出無限滾動曝光埋點（KTM） |
| `trackImpressionProdCardView()` | 送出商品卡曝光埋點（productTrackingUseCase） |
| `trackClickProdCardView()` | 送出商品卡點擊埋點（productTrackingUseCase） |
| `onBlogClicked()` | 送出部落格點擊埋點（KTM） |
| `trackClickDestinationPgAccessBy()` | 送出 Showcase 存取點擊埋點（KTM） |

---

## 業務邏輯摘要

- 入口支援兩種模式：傳入 `DestinationCode` 直接初始化；或傳入 URL 路徑，先解析出 code 再初始化。
- 頁面設定（`DestinationPageSetting`）包含 `urlName`、`destinationCode`、`destinationName`、`description`、FAQ 列表、圖片列表、主題商品。
- 探索區塊採 Paging3，每頁固定筆數（`PER_LIMIT`），並持續將已曝光商品 ID 回傳給 API 以排除重複推薦。
- 收藏（Wish）由父類 `WishViewModel` 管理，透過 `AppSharedData` 同步跨頁收藏狀態；變更收藏透過 `RouterHelper` 發送 `ACTION_ADD_OR_REMOVE_WISH`。
- 飯店分類（`HOTEL_CAT_CODE`）需特殊處理，由 `HotelCategoryLauncherByUrlUseCase` 啟動，並在跳轉後結束本頁。
- A/B 測試（`DestinationPgRecomDefault`）控制推薦 Tab 預設顯示內容。
- 埋點同時使用 KKTracker（舊）與 KTM（新）雙軌發送。
- 台灣市場（`isTaiwanMarket()`）可能有差異化顯示邏輯。

---

## 重要資料轉換點

| 位置 | 輸入型別 | 輸出型別 | 說明 |
|------|---------|---------|------|
| `DestinationRepositoryImpl.safeApiCall` | `B2CApiResponse<T>` | `Flow<ApiResult<T>>` | HTTP response 轉 ApiResult |
| `ViewModel.apiSuccess { }` | `ApiResult<T>` | 解包 `T` | 成功才更新 State，失敗忽略 |
| `convertTopTenProductViewStateList()` | `B2CProductCardData` | `MediumProductCardViewState` | 含格式化價格與收藏狀態 |
| `convertNewProductViewStateList()` | `B2CProductCardData` | `MediumProductCardViewState` | 同上 |
| `convertPersonalProductViewStateList()` | `B2CProductCardData` | `MediumProductCardViewState` | 同上 |

---

## 已知技術債

- **缺少 UseCase 層**：`DestinationPageViewModel` 直接依賴 `DestinationRepository`、`SearchExploreRepository`、`RecommendCategoryRepository`，未透過 `:domain:contract` 介面分離，違反 Clean Architecture 理想架構。
- **狀態管理非標準**：頁面狀態使用 Compose `mutableStateOf` 而非 `StateFlow`/`LiveData`，ViewModel 方法直接回傳 State 值供 Composable 讀取，不符合 reactive 觀察模式。
- **業務邏輯在 ViewModel**：Tier-1 分類查找（`findTire1Category`）、ProductCategoryUrl 解析等業務邏輯直接寫在 ViewModel，應移至 UseCase。
- **雙軌埋點**：同時使用 KKTracker（舊系統）與 KTM（新系統）發送埋點，埋點維護成本高。

## 相關筆記
- [01-architecture](../01-architecture.md)
- [02-modules](../02-modules.md)
- [03-ui-patterns](../03-ui-patterns.md)
- [05-networking](../05-networking.md)
- [06-data-layer](../06-data-layer.md)
- [07-concurrency](../07-concurrency.md)
- [explore](explore.md)
- [order-detail-compose](order-detail-compose.md)
- [sku-activity-shell](sku-activity-shell.md)

# 主題分類頁 技術文件

> 自動產生 | 最後更新：2026-03-19

---

## 概述

- **所在 Module**：`:feature:search_page`
- **UI 入口**：`CategoryPageActivity.kt`
- **功能描述**：展示特定主題分類（如潛水、滑雪等）的專屬落地頁，包含分類橫幅、Top10 推薦商品、展示商品列表、熱門目的地及目的地篩選功能。

---

## 檔案清單

```
UI（使用者介面入口）
 ├─ CategoryPageActivity.kt         → libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/category/
 ├─ CategoryPage.kt（Compose）      → libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/category/compose/main/
 ├─ CategoryPageHeader.kt           → libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/category/compose/main/
 ├─ CategoryView.kt                 → libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/category/compose/main/
 ├─ CategoryBannerView.kt           → libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/category/compose/main/
 ├─ CategoryTopProductView.kt       → libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/category/compose/main/
 ├─ CategoryHotCityView.kt          → libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/category/compose/main/
 ├─ CategoryHotRecommendView.kt     → libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/category/compose/main/
 └─ CategoryPageBottomSheetFragmentV2.kt → libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/category/

ViewModel（UI 狀態管理）
 └─ CategoryPageViewModel.kt        → libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/category/viewmodel/

Domain（業務邏輯 UseCase）
 └─ 無獨立 UseCase（ViewModel 直接依賴 Repository，屬技術債）

Data（資料層）
 ├─ RecommendCategoryRepository.kt（含實作）→ libs/feature/search_page/src/main/java/com/kkday/search_page/domain/repository/
 ├─ SearchExploreRepository.kt（含實作）    → libs/feature/search_page/src/main/java/com/kkday/search_page/domain/repository/
 ├─ SearchDcsRepository.kt（含實作）        → libs/feature/search_page/src/main/java/com/kkday/search_page/domain/repository/
 └─ SearchRepository.kt（含實作）           → libs/feature/search_page/src/main/java/com/kkday/search_page/domain/repository/

Network（API 定義）
 └─ SearchApiService.kt             → libs/feature/search_core/src/main/java/com/kkday/search/network/

Data Model
 ├─ RecommendCategoryProducts.kt    → libs/model/src/main/java/com/kkday/library/common/model/search/recommend/
 ├─ RecommendCategoryCategories.kt  → libs/model/src/main/java/com/kkday/library/common/model/search/recommend/
 ├─ RecommendCategoryCategory.kt    → libs/model/src/main/java/com/kkday/library/common/model/search/recommend/
 ├─ RecommendCategoryShowcaseProducts.kt → libs/model/src/main/java/com/kkday/library/common/model/search/recommend/
 ├─ RecommendCategoryDestination.kt → libs/model/src/main/java/com/kkday/library/common/model/search/recommend/
 ├─ RecommendCategoryLinks.kt       → libs/model/src/main/java/com/kkday/library/common/model/search/recommend/
 ├─ RecommendCategoryBanner.kt      → libs/model/src/main/java/com/kkday/library/common/model/search/recommend/
 └─ RecommendUserLocation.kt        → libs/model/src/main/java/com/kkday/library/common/model/search/recommend/
```

---

## 資料流

### 主流程：頁面初始化資料載入

```
UI（CategoryPageActivity）
 │  onCreate() 呼叫 initRequest()、setContent { CategoryPage(...) }
 │  onResume() 呼叫 categoryPageVM.refreshWish()、trackKTMLoadPage()
 ↓
ViewModel（CategoryPageViewModel）
 │  initDeepLinkUrl(context) 解析 deeplink URL，決定分類代碼
 │  requestInit(locationCode, isCreated=true)
 │    ├─ searchExploreRepository.getDestinationByCategory()
 │    ├─ recommendCategoryRepository.getRecommendUserProfile()（首次載入）
 │    ├─ dcsRepository.getDcsCategoryHeaderImage()
 │    ├─ dcsRepository.getDcsCategoryBanner()
 │    ├─ recommendCategoryRepository.getRecommendCategoryPopularCategories()
 │    ├─ recommendCategoryRepository.getRecommendCategoryTopProducts()
 │    ├─ recommendCategoryRepository.getRecommendCategoryShowcaseProducts()
 │    ├─ recommendCategoryRepository.getRecommendCategoryPopularDestinations()
 │    ├─ recommendCategoryRepository.getRecommendCategoryDomestic()
 │    └─ recommendCategoryRepository.getRecommendCategoryOutbound()
 ↓
Repository（無 UseCase 抽象層，ViewModel 直接呼叫 Repository）
 │  RecommendCategoryRepository → searchApi.getRecommendCategoryTopProducts()
 │  SearchExploreRepository     → searchApi.getDestinationByCategory()
 │  SearchDcsRepository         → kkApi.b2cApi.dcs.fetch()（DCS 設定檔）
 ↓
API（SearchApiService，Retrofit）
 │  GET v2/recommend/user/profile
 │  GET v2.1/recommend/category/top_products?product_category=&destination=
 │  GET v2/recommend/category/popular_categories?product_category=&destination=
 │  GET v2.1/recommend/category/showcase_products?product_category=&destination=
 │  GET v2/recommend/category/popular_destinations?product_category=
 │  GET v2/recommend/category/domestic?product_category=&location=
 │  GET v2/recommend/category/outbound?product_category=&location=
 │  GET v2/search/destination?product_categories[]=
 ↓
後端 API
```

### 目的地篩選流程（使用者點擊目的地篩選）

```
UI（CategoryPageActivity）
 │  cityClickListener → showCityDialog()
 │  根據 AB Testing 決定新版（Compose BottomSheet）或舊版（Fragment BottomSheet）
 ↓
ViewModel（CategoryPageViewModel）
 │  getSearchDestinationsResult() → searchRepository.getSearchCategoryDestination()
 │  使用者選擇後：setPageLocation()、requestInit(newLocation, false)
 ↓
Repository（SearchRepository）
 │  searchApi.getSearchCategoryDestination(requestBody)
 ↓
API（SearchApiService）
 │  POST v3/search/category_destination
 ↓
後端 API
```

### 回傳流

```
後端 API
 ↓
Repository
 │  透過 BaseApiRepository.safeApiCall{} 包裝，回傳 Flow<ApiResult<T>>
 │  ApiResult.Success / ApiResult.Error / ApiResult.Loading
 ↓
ViewModel（CategoryPageViewModel）
 │  apiSuccess{} 擴充函式處理 Success 分支
 │  更新 Compose mutableStateOf：
 │    _topTenProductsData、_showcases、_recommendCategories
 │    _hotDestinations、_banner、_headerImage、_inlineLinks
 │  StateFlow：_countryCityFlow、_location、_searchDestinationUiState
 ↓
UI（CategoryPage Composable）
 │  categoryPageVM.getTopTenProducts()、getShowcases() 等 getter
 │  Compose derivedStateOf 追蹤狀態變化，自動重組
 └─ 成功：各區塊顯示對應內容
    失敗：無特定 Error State UI（內容保持空）
```

---

## 逐層說明

### UI 層

`CategoryPageActivity` 繼承 `BaseComposeActivity`，透過 `@Router` 與 KRouter 路由系統整合。接收三組路由參數：`productCategory`（分類代碼）、`productCategoryName`（分類名稱）、`categoryDestination`（初始目的地）。

`setContent` 直接渲染 `CategoryPage` Composable，將 Activity 級別的回呼函式（`showCityDialog`、`searchClick`、`openUrl`、`goProduct`、`openDeepLink`）以 lambda 傳入。

Compose UI 使用 `derivedStateOf` 包裝 ViewModel getter，讓 Compose 在資料變動時自動觸發重組。

### ViewModel 層

`CategoryPageViewModel` 繼承 `WishViewModel`，並直接注入四個 Repository（無 UseCase 抽象層）。

狀態管理混用兩種方式：
- Compose `mutableStateOf`：供 Composable 直接讀取（`_categoryPageViewState`、`_headerImage`、`_recommendCategories` 等），不使用 `collectAsState`
- `MutableStateFlow`：`_countryCityFlow`、`_location`、`_searchDestinationUiState`、`_abTestDestinationFilterTest`

初始化流程：`onCreate` → `initDeepLinkUrl()` → `requestInit()`，一次發出多支平行 API 請求。

`init` 區塊執行 AB Testing 初始化，決定目的地篩選器新舊版。

### UseCase 層

此功能無獨立 UseCase，ViewModel 直接依賴 Repository（技術債）。

### Repository 層

| Repository | 資料來源 | 主要用途 |
|---|---|---|
| `RecommendCategoryRepository` | `SearchApiService`（Retrofit） | 推薦商品、子分類、展示商品、熱門目的地、國內外連結 |
| `SearchExploreRepository` | `SearchApiService`（Retrofit） | 取得分類可篩選的目的地清單 |
| `SearchDcsRepository` | `KKApi.b2cApi.dcs`（DCS 設定檔系統） | 分頁 Header 圖片、Banner 設定 |
| `SearchRepository` | `SearchApiService`（Retrofit） | 目的地搜尋（新版篩選器用） |

所有 Repository 繼承 `BaseApiRepository`，使用 `safeApiCall{}` 包裝 API 呼叫，回傳 `Flow<ApiResult<T>>`。未做本地 Room 快取。

### API 層

所有 API 透過 `SearchApiService`（`libs/feature/search_core/`）定義，主要端點：

| HTTP 方法 | Endpoint | 用途 |
|---|---|---|
| GET | `v2/recommend/user/profile` | 取得使用者偏好目的地 |
| GET | `v2.1/recommend/category/top_products` | 分類 Top 10 商品 |
| GET | `v2/recommend/category/popular_categories` | 熱門子分類 |
| GET | `v2.1/recommend/category/showcase_products` | 展示商品（依子分類分組） |
| GET | `v2/recommend/category/popular_destinations` | 熱門目的地 |
| GET | `v2/recommend/category/domestic` | 國內推薦連結 |
| GET | `v2/recommend/category/outbound` | 出境推薦連結 |
| GET | `v2/search/destination` | 目的地清單（舊版篩選器） |
| POST | `v3/search/category_destination` | 目的地搜尋（新版篩選器） |

---

## View 方法清單

| 方法 | 說明 |
|------|------|
| `onCreate()` | 注入路由參數、初始化 Status Bar、呼叫 `initRequest()`、渲染 `CategoryPage` Composable |
| `onResume()` | 更新願望清單、發送 KTM 頁面載入埋點 |
| `openUrl()` | 開啟 KKDay WebView 並發送 Banner 點擊埋點 |
| `goProduct()` | 路由至商品詳情頁，傳遞商品 header 資料 |
| `openDeepLink()` | 解析 deeplink URL 並帶入分類參數後啟動；若 URL 為空則直接導向搜尋結果頁 |
| `showCityDialog()` | 根據 AB Testing 決定顯示新版（Compose BottomSheet）或舊版（Fragment BottomSheet）目的地篩選器 |
| `showLegacyCityDialog()` | 顯示舊版 `CategoryPageBottomSheetFragmentV2` |
| `showNewDestinationBottomSheet()` | 動態建立 ComposeView 顯示新版目的地搜尋 BottomSheet，選擇後呼叫 `requestInit()` 刷新頁面 |
| `initStatusBar()` | 設定透明 Status Bar 與全螢幕佈局旗標 |
| `initRequest()` | 監聽 `cityVM.cityChangedId` 目的地切換事件；合併 `countryCityFlow` 與 `location` 更新選擇目的地並重新請求資料 |
| `searchClick()` | 路由至分類搜尋頁（`CategorySearchPageActivity`），帶入分類代碼與目的地資訊 |

---

## ViewModel 方法清單

| 方法 | 說明 |
|------|------|
| `init` | 若有初始目的地則設定 `_location`；呼叫 `initABTesting()` 取得 AB Testing 分組 |
| `initABTesting()` | 透過 RxJava 訂閱 `KKAbTestingService.getDestinationFilter()`，更新 `_abTestDestinationFilterTest` |
| `requestInit()` | 清空 inlineLinks 後並行發起所有區塊 API 請求 |
| `initDeepLinkUrl()` | 解析 `categoryPageUrl`（deeplink 路徑），從 DataStore 取出分類 URL 映射表，更新分類代碼與目的地，最後呼叫 `requestInit()` |
| `requestRecommendUserProfile()` | 取得使用者偏好目的地，若無初始目的地則以此為預設值；並發送頁面瀏覽埋點 |
| `requestRecommendCategory()` | 取得熱門子分類清單，並在尾端附加「全部」項目 |
| `requestHeadImage()` | 從 DCS 取得分頁 Header 圖片清單，以分類代碼 random 選一張 |
| `requestBanner()` | 從 DCS 取得 Banner，依分類與目的地條件過濾後顯示 |
| `requestTopTenProducts()` | 取得分類 Top 10 推薦商品 |
| `requestShowcaseProducts()` | 取得分類展示商品（依子分類分組） |
| `requestHotDestinations()` | 取得分類熱門目的地 |
| `requestDomestic()` | 取得國內推薦連結，完成後接著呼叫 `requestOutbound()` |
| `requestOutbound()` | 取得出境推薦連結 |
| `setPageLocation()` | 依傳入的 `DestinationCode` 或 `CityCountryCode` 型別更新 `_categoryPageViewState` |
| `updatePageLocationName()` | 更新目的地顯示名稱 |
| `navigatorSearchResultPage()` | 透過 `NavigatorCategoryHelper` 路由至搜尋結果頁 |
| `getSearchDestinationsResult()` | 搜尋可選目的地清單，支援模糊搜尋 fallback，更新 `_searchDestinationUiState` |
| `addRecentlySearchDestination()` | 將目的地加入最近搜尋記錄（DataStore，上限 10 筆） |
| `getRecentlySearchDestination()` | 從 DataStore 讀取最近搜尋記錄 |
| `clearRecentlySearchDestination()` | 清除最近搜尋記錄並更新 UI 狀態 |
| `convertTopTenProductViewStateList()` | 將 Top10 商品轉換為 `MediumProductCardViewState`，帶入價格格式與願望清單狀態 |
| `formatDisplayPrice()` | 使用 `CurrencyDisplayManager` 格式化商品價格顯示 |
| `refreshWish()` | 刷新使用者願望清單（繼承自 `WishViewModel`） |
| `changeWishList()` | 切換商品願望清單狀態（繼承自 `WishViewModel`） |
| `trackKTMLoadPage()` | 發送 KTM 頁面載入事件 |
| `trackClickDestinationFilter()` | 發送目的地篩選器點擊埋點（KTM + KKTracker 雙軌） |
| `trackApplyDestinationFilter()` | 發送目的地篩選套用埋點 |
| `trackClickBanner()` | 發送 Banner 點擊埋點 |
| `trackClickTopTen()` | 發送 Top10 商品點擊埋點 |
| `trackClickProdCat()` | 發送子分類點擊埋點 |
| `trackClickProdCatList()` | 發送展示商品點擊埋點（透過 `ProductCardTrackingUseCase`） |
| `trackClickProdCatListViewMore()` | 發送「查看更多」點擊埋點 |
| `trackClickProdCatListViewAll()` | 發送「查看全部」點擊埋點 |
| `trackClickDestinationRecommend()` | 發送熱門目的地點擊埋點 |
| `trackClickPopRecommend()` | 發送國內/出境推薦連結點擊埋點 |
| `trackCategoryTopProductImpression()` | 發送 Top10 商品曝光埋點（透過 `ProductCardTrackingUseCase`） |
| `trackCategoryTopProductClick()` | 發送 Top10 商品點擊埋點（透過 `ProductCardTrackingUseCase`） |
| `trackCategoryProdCardImpression()` | 發送展示商品曝光埋點（透過 `ProductCardTrackingUseCase`） |
| `onCleared()` | 清除 RxJava `CompositeDisposable` |

---

## 重要資料轉換點

| 位置 | 輸入型別 | 輸出型別 | 說明 |
|------|---------|---------|------|
| Repository | `B2CApiResponse<RecommendCategoryProducts>` | `Flow<ApiResult<RecommendCategoryProducts>>` | safeApiCall 包裝 |
| ViewModel | `RecommendCategoryProducts` | `List<MediumProductCardViewState>` | `convertTopTenProductViewStateList()` 轉換，帶入價格格式與願望狀態 |
| ViewModel | `List<RecommendCategoryCategory>` | 直接暴露（`getRecommendCategories()`） | 未做額外轉換，由 Composable 直接使用 |
| ViewModel | `SearchProdDestinations` | `SearchDestinationUiState` | 依搜尋結果分 Initialize / Success / SuccessButNoMatch / Error |

---

## 業務邏輯摘要

- **目的地初始化優先順序**：路由傳入目的地 > deeplink URL 解析目的地 > 使用者偏好目的地（`getRecommendUserProfile`）> 全世界（空）
- **AB Testing**：目的地篩選器 UI 有新舊兩版，由 `KKAbTestingService.getDestinationFilter()` 決定，新版使用 Compose BottomSheet，舊版使用 `CategoryPageBottomSheetFragmentV2`
- **DCS 內容**：Header 圖片與 Banner 來自 DCS 設定檔，非 API 直接推送，允許後台動態設定
- **Banner 過濾邏輯**：Banner 依分類代碼與目的地代碼過濾，支援「分類限定」、「目的地限定」、「分類+目的地限定」、「全分類」四種條件
- **推薦商品模糊搜尋**：目的地搜尋若無結果，自動 fallback 至模糊搜尋（`fuzzySearch=true`）
- **願望清單**：繼承 `WishViewModel`，`onResume` 時刷新確保狀態同步
- **埋點雙軌**：同時使用 KTM（`KTMTracker`）與 KKTracker（`KKTrackTool`）發送不同格式的埋點

---

## 已知技術債

- **缺少 UseCase 抽象層**：`CategoryPageViewModel` 直接注入並呼叫 `RecommendCategoryRepository`、`SearchExploreRepository`、`SearchDcsRepository`、`SearchRepository`，共四個 Repository，違反 Clean Architecture 應透過 UseCase 隔離的原則
- **Repository 未實作 domain/contract 介面分離**：四個 Repository 皆為具體實作類別，未在 `:domain:contract` 定義對應介面
- **`pageLocationCode` 已標記棄用**：`CategoryPageViewState.pageLocationCode` 標記 `@Deprecated`，應統一改用 `pageDestinationCode`（`DestinationCode` 型別），但實作中兩者並存
- **Compose mutableStateOf 直接暴露給 Composable**：ViewModel 以 `mutableStateOf` 管理多數狀態，Composable 直接呼叫 getter 存取，未統一為 `StateFlow`，造成狀態管理方式不一致

## 相關筆記
- [01-architecture](../01-architecture.md)
- [02-modules](../02-modules.md)
- [03-ui-patterns](../03-ui-patterns.md)
- [05-networking](../05-networking.md)
- [06-data-layer](../06-data-layer.md)
- [07-concurrency](../07-concurrency.md)
- [category-search-result](category-search-result.md)
- [order-detail-compose](order-detail-compose.md)
- [sku-activity-shell](sku-activity-shell.md)

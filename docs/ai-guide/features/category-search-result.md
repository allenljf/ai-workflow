# 分類搜尋結果（Compose）技術文件

> 自動產生 | 最後更新：2026-03-19

---

## 概述

- **所在 Module**：`libs/feature/search_page`
- **UI 入口**：`CategorySearchResultPageActivity`
- **功能描述**：以 Jetpack Compose 實作的分類搜尋結果頁，展示指定商品分類下的商品列表，支援地點、日期、價格、排序等多維度篩選，並整合 Paging3 無限滾動與 AB Testing。

---

## 檔案清單

```
UI（使用者介面入口）
 ├─ CategorySearchResultPageActivity.kt   → libs/feature/search_page/.../category/
 └─ CategorySearchResultPage.kt（Compose）→ libs/feature/search_page/.../category/compose/search_result/

ViewModel（UI 狀態管理）
 └─ CategorySearchResultViewModel.kt      → libs/feature/search_page/.../category/viewmodel/

Paging（分頁資料源）
 └─ CategorySearchResultPagingSource.kt   → libs/feature/search_page/.../category/viewmodel/

Domain / Repository（資料層，位於 feature 模組內）
 ├─ RecommendCategoryRepository.kt        → libs/feature/search_page/.../domain/repository/
 └─ SearchRepository.kt                   → libs/feature/search_page/.../domain/repository/

Network（API 定義）
 └─ SearchApiService.kt                   → libs/feature/search_core/.../network/

Data Model
 ├─ CategorySearchResultViewState.kt      → 同 ViewModel 檔案底部
 ├─ SelectedFilter.kt                     → 同 ViewModel 檔案
 ├─ SearchProductResult                   → libs/model/.../model/SearchProductResult.kt
 └─ B2CProductCardData                    → libs/networking/.../resource/product/
```

---

## 資料流

### 主流程：頁面載入 / 商品清單取得

```
UI（CategorySearchResultPageActivity）
 │  onCreate() → 呼叫 initRequest()，設定 ComposeUI
 │  setContent { CategorySearchResultPage(searchVM, ...) }
 ↓
CategorySearchResultPage（Composable）
 │  collectAsLazyPagingItems(searchVM.products)
 ↓
CategorySearchResultViewModel（init）
 │  searchCategoryFilter() → 取得篩選器資料
 │  getPagingSourceFlow()  → 建立 Pager
 ↓
CategorySearchResultPagingSource
 │  load() → 呼叫 searchCategoryProduct(start, count)
 ↓
RecommendCategoryRepository
 │  getSearchCategoryList(requestBody)
 │  getSearchCategoryListRequestBody(...) → 建構 SearchProductListRequestBody
 ↓
SearchApiService
 │  POST v2.2/search/category_list（Body: SearchProductListRequestBody）
 ↓
後端 API
```

### 篩選器載入流程

```
ViewModel.searchCategoryFilter()
 │  RecommendCategoryRepository.getSearchCategoryFilter()
 │  POST v2.2/search/category_filter?page_name=category_xxx_menu_mobile
 ↓
取得 SearchFilterData（menu filter）
 │  再次呼叫 searchCategoryFilter()
 │  POST v2.2/search/category_filter?page_name=category_xxx_list_mobile
 ↓
取得 SearchFilterData（list filter）
 │  convertListFilterId() 對齊 menu/list filter id
 ↓
_searchMenuFilterResult / _searchListFilterResult（Compose State）
 ↓
CategorySearchResultPage 更新篩選器列
```

### 回傳流

```
後端 API
 ↓
RecommendCategoryRepository：SearchProductResult（含 prods, sessionId, expVersion）
 ↓
CategorySearchResultPagingSource：LoadResult.Page<B2CProductCardData>
 ↓
ViewModel：PagingData<B2CProductCardData> → _products（StateFlow）
 ↓
UI：collectAsLazyPagingItems → LazyVerticalStaggeredGrid 渲染
```

---

## 逐層說明

### UI 層

`CategorySearchResultPageActivity` 繼承 `BaseComposeActivity`，使用 `@Router(KRouterConst.PAGE_CATEGORY_SEARCH_RESULT)` 路由，透過 `@RouterParam` 接收 `CategorySearchResultViewState` 初始狀態。`onCreate()` 呼叫 `initRequest()` 設定城市篩選監聽後，以 `setContent` 掛載 `CategorySearchResultPage`。`onResume()` 觸發 `refreshWish()` 更新願望清單狀態並發送 KTM 曝光事件。

目的地篩選 BottomSheet 依 AB Testing（`destinationFilterTest`）切換新版 Compose BottomSheet 或舊版 Fragment BottomSheet。

### ViewModel 層

`CategorySearchResultViewModel` 以 Koin `viewModel { params }` 注入，繼承 `WishViewModel`。狀態管理混用：
- `MutableStateFlow`：products、isFirstLoadDone、isFilterApiError、abTestVariant 等
- Compose `mutableStateOf`：`_resultViewState`、`_selectedFilter`（篩選條件直接作為 Compose State）

`ViewIntent` / `SingleViewEvent` 透過 `MutableSharedFlow` + `debounce(300L)` 處理 BottomSheet 顯示事件，避免快速點擊重複觸發。

### Repository 層

無獨立 Domain Contract 介面（技術債），`RecommendCategoryRepository` 和 `SearchRepository` 直接在 `searchPageModule.kt` 以 `factory` 建立，並注入 ViewModel。Repository 繼承 `BaseApiRepository`，使用 `safeApiCall` / `safeApiCallFlow` 統一包裝錯誤處理。

### Paging 層

`CategorySearchResultPagingSource` 實作 `PagingSource<Int, B2CProductCardData>`，每頁固定 10 筆（`PER_LIMIT = 10`），起始 key 為 0。`getRefreshKey()` 一律回 0 以確保重新整理從頭取起。`onRecommendPropertyReceived` callback 傳遞 sessionId / expVersion / algoVersion 供 KTM 推薦追蹤用。

### API 層

| API | 方法 | 路徑 |
|-----|------|------|
| 商品清單 | POST | `v2.2/search/category_list` |
| 篩選器（menu）| POST | `v2.2/search/category_filter?page_name=category_{x}_menu_mobile` |
| 篩選器（list）| POST | `v2.2/search/category_filter?page_name=category_{x}_list_mobile` |
| 目的地清單 | GET | `v2/search/destination?product_categories[]=...` |
| 熱門城市 | GET | `v2/recommend/category_discover/popular_destinations` |
| 目的地資訊 | GET | `v2/destination_info/{urlName}` |

---

## Activity 方法清單

| 方法 | 說明 |
|------|------|
| `onCreate()` | 初始化請求、設定 Compose UI 內容 |
| `onStart()` | 初始化或恢復 PlayerManager（影片播放） |
| `onStop()` | 停止影片播放 |
| `onDestroy()` | 清除 PlayerManager |
| `onResume()` | 刷新願望清單、發送 KTM 頁面載入追蹤 |
| `initRequest()` | 設定城市選擇監聽、處理 deeplink URL 解析 |
| `showDateDialog()` | 顯示日期區間選擇 Dialog |
| `showDateResult()` | 將選擇日期回傳給 ViewModel |
| `showCityDialog()` | 依 AB Testing 決定顯示新版或舊版目的地篩選 |
| `showLegacyCityDialog()` | 舊版 Fragment BottomSheet（城市選擇） |
| `showNewDestinationBottomSheet()` | 新版 Compose BottomSheet（目的地選擇），動態 addView |
| `onClickProduct()` | 透過 RouterHelper 導向商品詳情頁，附帶 ProductHeaderData |
| `onClickMap()` | 導向 FB Map（JSBridge） |

---

## ViewModel 方法清單

| 方法 | 說明 |
|------|------|
| `init` | 取得目的地清單、初始化 AB Testing、初始化熱門目的地、啟動 ViewIntent 監聽 |
| `initDeepLinkUrl()` | 解析 categoryPageUrl DeepLink，更新 ViewState 並觸發第一次篩選器取得 |
| `reGetCategoryFilter()` | 重新取得篩選器（地點改變後呼叫） |
| `getPagingSourceFlow()` | 建立 Pager + PagingSource，結果流入 `_products` |
| `searchCategoryFilter()` | 依序取得 menu / list 兩種 filter，合併 ID 後存入 State |
| `searchCategoryProduct()` | 呼叫 Repository 取商品清單，更新計數並觸發 KTM PageLoad 追蹤 |
| `changeSelectedLocation()` | 更新地點篩選，重置探索商品狀態 |
| `changeSelectedDate()` | 更新日期篩選 |
| `changeSelectedFilterIds()` | 切換單一 filter tag（toggle 邏輯） |
| `changeSelectedFilterIdsWithBoolean()` | 以 boolean 設定 filter |
| `removeMultipleSelectionKey()` | 批次移除 filter tag |
| `clearAllFilter()` | 清除所有篩選條件，保留地點和關鍵字 |
| `changeSort()` | 更新排序方式 |
| `changePriceRange()` | 更新價格區間 |
| `refreshWish()` | 刷新願望清單狀態（繼承自 WishViewModel） |
| `refreshSearchResultCount()` | 呼叫 count=1 的 searchCategoryProduct 更新商品總數 |
| `goToCategorySearchPage()` | 跳轉到分類搜尋頁 |
| `getSearchDestinationsResult()` | 取得搜尋目的地下拉清單 |
| `clearRecentlySearchDestination()` | 清除最近搜尋目的地 |
| `filterProductTotalCount()` | 回傳格式化後的商品總數（>300 顯示 "300+"） |
| `getFBMapUrl()` | 產生 FB Map URL |
| `trackKTMLoadPage()` | 頁面曝光 KTM 追蹤 |
| `trackFilterConfirm()` | 篩選確認 KTM 追蹤 |
| `trackClearFilter()` | 清除篩選 KTM 追蹤 |
| `trackFilterMenuPg()` | 篩選選單頁曝光 KTM 追蹤 |
| `isTaiwanMarket()` | 判斷是否為台灣市場 |

---

## 業務邏輯摘要

- **篩選器兩階段載入**：先取 `menu_mobile` filter（決定頂部篩選列選項），再取 `list_mobile` filter（決定側邊全篩選），兩者 ID 需用 `convertListFilterId()` 對齊。
- **地點篩選**：支援 DestinationCode（城市/目的地）與 CityCountryCode（城市國家）兩種格式，改變地點後自動清除其他篩選條件並重新取資料。
- **DeepLink 支援**：可從 URL 解析 category、destination、keyword、filter 參數，進入時自動觸發相應狀態初始化。
- **AB Testing 整合**：`CatResultPgInfinityLoopAB`（無限滾動探索商品）與 `destinationFilterTest`（目的地篩選新舊版 UI）兩個實驗同時運行。
- **探索商品（Explore）**：無限滾動到底部後自動載入探索商品（`CategoryExplorePagingSource`），依目的地和分類重新初始化。
- **影片播放**：透過 `PlayerManager` 管理商品卡影片，Activity onStart 恢復、onStop 暫停、onDestroy 清除。
- **KTM 追蹤**：頁面載入、篩選操作、商品曝光均有對應 KTM 事件，sessionId / expVersion 由 PagingSource 回調傳入。
- **錯誤處理**：篩選器 API 失敗時設定 `_isFilterApiError = true`，UI 顯示網路錯誤提示；Paging load 失敗以 `LoadResult.Error` 處理。

---

## 已知技術債

- `RecommendCategoryRepository` 和 `SearchRepository` 直接在 `searchPageModule.kt` 以 `factory` 建立並注入 ViewModel，無對應的 Domain Contract 介面（違反理想 Clean Architecture），ViewModel 直接相依 Repository 實作。
- `SelectedFilter` 狀態以 Compose `mutableStateOf` 管理，非 `StateFlow`，在 non-Compose 場景下不易觀察。
- 目的地篩選 BottomSheet 的新版實作透過動態 `addView`/`removeView` 方式嵌入 Compose，屬過渡期做法。

## 相關筆記
- [01-architecture](../01-architecture.md)
- [02-modules](../02-modules.md)
- [03-ui-patterns](../03-ui-patterns.md)
- [05-networking](../05-networking.md)
- [06-data-layer](../06-data-layer.md)
- [07-concurrency](../07-concurrency.md)
- [category-page](category-page.md)
- [new-search-result](new-search-result.md)
- [order-detail-compose](order-detail-compose.md)
- [sku-activity-shell](sku-activity-shell.md)

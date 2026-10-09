# 新版搜尋結果頁 技術文件

> 自動產生 | 最後更新：2026-07-17

---

## 概述

- **所在 Module**：`:feature:search_page`
- **UI 入口**：`NewSearchResultActivity.kt`
- **功能描述**：使用者輸入關鍵字或透過 DeepLink 進入後，顯示搜尋結果商品列表，支援篩選（分類、目的地、日期、價格、排序等）、分頁載入、願望清單操作、推薦商品展示

---

## 檔案清單

```
UI（使用者介面入口）
 ├─ NewSearchResultActivity.kt         → libs/feature/search_page/.../search/
 ├─ SearchResultPage.kt（Compose）     → libs/feature/search_page/.../search/compose/
 ├─ SearchFilterBottomSheet.kt         → libs/feature/search_page/.../search/compose/
 ├─ BottomSheetSearchAllView.kt        → libs/feature/search_page/.../search/compose/
 ├─ BottomSheetSearchCategoryView.kt   → libs/feature/search_page/.../search/compose/
 ├─ BottomSheetSearchDestinationViewNew.kt → libs/feature/search_page/.../search/compose/
 ├─ BottomSheetSearchPriceView.kt      → libs/feature/search_page/.../search/compose/
 ├─ BottomSheetSearchOnOffView.kt      → libs/feature/search_page/.../search/compose/
 ├─ BottomSheetSearchMultipleSelectionView.kt → libs/feature/search_page/.../search/compose/
 └─ SearchError.kt                     → libs/feature/search_page/.../search/compose/

ViewModel（UI 狀態管理）
 ├─ SearchResultViewModel.kt           → libs/feature/search_page/.../search/viewmodel/
 └─ WishViewModel.kt（父類）           → libs/feature/search_page/.../category/viewmodel/

PagingSource（分頁資料源）
 └─ SearchResultPagingSource.kt        → libs/feature/search_page/.../search/viewmodel/

Domain（業務邏輯）
 └─ ProductCardTrackingUseCase.kt      → libs/feature/shared_core/.../usecase/

Data（資料層）
 ├─ SearchRepository.kt（search_page 內部）   → libs/feature/search_page/.../domain/repository/
 └─ SearchRepository.kt（search_core 介面）   → libs/feature/search_core/.../domain/repository/
     └─ SearchRepositoryImpl.kt                → libs/feature/search_core/.../data/repository/

Network（API 定義）
 └─ SearchApiService.kt（Retrofit 介面）       → libs/feature/search_core/.../network/

Model（資料模型）
 ├─ SearchFilterCondition.kt           → libs/model/.../search/
 ├─ SelectedFilter.kt（定義於 CategorySearchResultViewModel.kt 內）
 ├─ SearchFilterData.kt                → libs/model/.../
 ├─ SearchProductListRequestBody.kt    → libs/feature/search_core/.../data/
 ├─ B2CProductCardData.kt              → libs/networking/api/.../resource/product/
 ├─ SearchProdDestination.kt           → libs/model/.../
 └─ SearchDestinationUiState（定義於 BottomSheetSearchDestinationViewNew.kt 內）
```

---

## 資料流

### 主流程：頁面載入 / 搜尋商品列表

```
UI（NewSearchResultActivity）
 │  onCreate → initRequest()
 │  呼叫：searchVM.initDeepLinkUrl()
 ↓
ViewModel（SearchResultViewModel）
 │  initDeepLinkUrl() → searchCategoryFilter(keyword, "product_menu_mobile")
 │  先取得 menu filter，再取得 list filter
 │  呼叫：searchRepository.getSearchFilter(keyword, productName)
 ↓
SearchRepository（search_page 內部）
 │  safeApiCall → apiResultDataByKotlinx
 │  呼叫：searchApi.getSearchFilter(...)
 ↓
SearchApiService（Retrofit 介面）
 │  POST v2.2/search/product_filter
 ↓
後端 API
```

### 商品列表分頁載入

```
UI（SearchResultPage Compose）
 │  Pager flow → collectAsLazyPagingItems
 ↓
SearchResultPagingSource
 │  load() → searchCategory(start, count)
 ↓
ViewModel（SearchResultViewModel）
 │  searchCategoryProduct(start, count)
 │  呼叫：searchRepository.searchProductListFlow(requestBody)
 ↓
SearchRepository（search_page 內部）
 │  safeApiCallFlow
 │  呼叫：searchApi.searchProductList(requestBody)
 ↓
SearchApiService（Retrofit 介面）
 │  POST v2.1/search/product_list
 │  Body：SearchProductListRequestBody（keyword, filter, sort, start, count 等）
 ↓
後端 API
```

### 目的地搜尋

```
UI（BottomSheetSearchDestinationViewNew）
 │  使用者輸入目的地查詢
 │  呼叫：viewModel.getSearchDestinationsResult(query)
 ↓
ViewModel（SearchResultViewModel）
 │  呼叫：searchRepository.getSearchProductDestination(requestBody)
 ↓
SearchRepository（search_page 內部）
 │  safeApiCall
 │  呼叫：searchApi.getSearchProductDestination(requestBody)
 ↓
SearchApiService（Retrofit 介面）
 │  POST v3/search/product_destination
 ↓
後端 API
```

### 回傳流

```
後端 API
 ↓
SearchRepository：B2CApiResponse<SearchProductResult> → ApiResult
 ↓
ViewModel：ApiResult.Success → _isLoading=false → 更新 _filterProductTotalCount / _searchProductTotalCount / _saleProductCountText
         → 回傳 List<B2CProductCardData> 給 PagingSource
         → 若結果為空，自動呼叫 requestUserRecommendProducts() 取得推薦商品
         ApiResult.Error → _isLoading=false（必須關閉，否則卡骨架屏）→ 回傳 null
         → PagingSource 拋 NetworkException → UI 落到 LoadState.Error 顯示錯誤畫面
 ↓
UI：Pager flow → LazyPagingItems → LazyColumn 渲染商品卡片
    觀察 LoadState 處理 Loading / Error / Empty 狀態
    骨架屏由 isLoading 控制（初始 true）；僅 isLoading=false 後才組合結果/錯誤/推薦內容
```

---

## 逐層說明

### UI 層

`NewSearchResultActivity` 繼承 `BaseComposeActivity`，透過 `@Router` 註冊路由 `KRouterConst.PAGE_SEARCH_RESULT`。接收 `SearchFilterCondition` 做為啟動參數，注入 `SearchResultViewModel`（帶參數）。`setContent` 載入 `SearchResultPage` Compose 頁面。

`SearchResultPage` 為主要 Compose 畫面，包含：
- 頂部搜尋列（顯示關鍵字，點擊返回搜尋中繼頁）
- 篩選列（分類、目的地、日期、排序、更多篩選）
- 商品列表（`LazyColumn` + `LazyPagingItems` 分頁）
- 空結果推薦商品區
- 多種 BottomSheet 篩選器

Activity 生命週期管理 `PlayerManager`（影片播放），`onResume` 時刷新願望清單。

### ViewModel 層

`SearchResultViewModel` 繼承 `WishViewModel`（管理收藏功能），使用 Compose `mutableStateOf` / `MutableStateFlow` 管理狀態。

主要狀態：
- `products`：`Pager` flow，透過 `SearchResultPagingSource` 分頁載入
- `_selectedFilter`：`SelectedFilter` 物件，集中管理所有篩選條件
- `_newSearchMenuFilterResult` / `_newSearchListFilterResult`：兩階段篩選項資料
- `_filterProductTotalCount` / `_searchProductTotalCount`：搜尋結果計數
- `_saleProductCountText`：可售商品數文字
- `_userRecommendProducts`：空結果時的推薦商品
- `searchDestinationUiState`：目的地搜尋 UI 狀態
- `_viewIntentFLow`：ViewIntent 事件流（debounce 300ms）

init 時：
1. 啟動 `handleViewIntent()`（debounce 處理 BottomSheet 顯示事件）
2. 取得 A/B 測試（destination filter）
3. 初始化 DeepLink 目的地資訊

### UseCase 層

此功能無獨立 UseCase 層。ViewModel 直接呼叫 `SearchRepository`（技術債）。

唯一注入的 UseCase 為 `ProductCardTrackingUseCase`，負責商品卡片曝光/點擊埋點。

### Repository 層

**`SearchRepository`（search_page 內部，非介面）**：繼承 `BaseApiRepository`，直接呼叫 `SearchApiService`。主要方法：
- `getSearchFilter()`：取得篩選項（分類、價格範圍等）
- `searchProductListFlow()`：搜尋商品列表（suspend + Flow）
- `getSearchProductListRequestBody()`：組裝搜尋請求體
- `getUserRecommendProduct()`：取得個人推薦商品
- `getSearchProductDestination()`：搜尋目的地

**`SearchRepository`（search_core 介面）**：此功能僅使用其 `getDestinationPageInfo()` 方法，用於 DeepLink 進入時取得目的地名稱。實作為 `SearchRepositoryImpl`。

錯誤處理：透過 `BaseApiRepository.safeApiCall` / `safeApiCallFlow` 統一封裝，回傳 `ApiResult`。

### API 層

| Endpoint | HTTP 方法 | 用途 |
|----------|----------|------|
| `v2.2/search/product_filter` | POST | 取得搜尋篩選項（menu 與 list 兩次呼叫） |
| `v2.1/search/product_list` | POST | 搜尋商品列表（Body 帶 `SearchProductListRequestBody`） |
| `v2/recommend/user_products` | GET | 取得個人推薦商品（空結果時使用） |
| `v3/search/product_destination` | POST | 搜尋目的地 |
| `v2/destination_info/code/{code}` | GET | 取得目的地資訊（DeepLink 用） |

---

## View 方法清單

| 方法 | 說明 |
|------|------|
| `onCreate()` | 初始化搜尋請求，設定 Compose 內容（`SearchResultPage`），註冊返回鍵回調 |
| `onStart()` | 初始化或恢復 `PlayerManager` 影片播放 |
| `onStop()` | 暫停影片播放 |
| `onDestroy()` | 清理 `PlayerManager` |
| `onResume()` | 刷新願望清單（`searchVM.refreshWish()`） |
| `initRequest()` | 呼叫 `searchVM.initDeepLinkUrl()` 啟動篩選項載入 |
| `showDateDialog()` | 顯示日期範圍選擇 Dialog，確認後刷新列表 |
| `onClickProduct()` | 透過 `RouterHelper` 開啟商品詳情頁，傳入 `ProductHeaderInitData` |
| `showDateResult()` | 將選擇的日期傳入 ViewModel |
| `onSearchBarClickListener()` | 返回搜尋中繼頁（`RESULT_CODE_SEARCH_BAR_CLICK`） |
| `onBackClickListener()` | 返回上一頁（`RESULT_CODE_BACK_CLICK`） |

---

## ViewModel 方法清單

| 方法 | 說明 |
|------|------|
| `init` | 啟動 ViewIntent 處理、取得 A/B 測試、初始化 DeepLink 目的地 |
| `handleViewIntent()` | 收集 `_viewIntentFLow`（debounce 300ms），發送 `SingleViewEvent` |
| `sendViewIntent()` | 發送 `ViewIntent` 到事件流 |
| `initDeepLinkUrl()` | 以 keyword 呼叫 `searchCategoryFilter` 取得 menu 篩選項 |
| `searchCategoryFilter()` | 兩階段取得篩選項：先 menu，再 list，處理 category 對應；filter 失敗時經 error callback 釋放 `_searchParamsReady` gate |
| `searchCategoryProduct()` | 呼叫搜尋 API 取得商品列表，更新計數/埋點，空結果時取推薦商品；Success/Error 皆關閉 `_isLoading`，error 回 null 讓 UI 落到 `LoadState.Error` |
| `refreshSearchResultCount()` | 以 count=1 快速查詢篩選後的商品總數 |
| `changeSelectedCategories()` | 更新已選分類 |
| `changeSelectedDestinations()` | 更新已選目的地 |
| `changeSelectedDate()` | 更新已選日期範圍 |
| `changePriceRange()` | 更新價格篩選範圍 |
| `changeSort()` | 更新排序方式 |
| `changeSelectedFilterIds()` | 切換篩選 ID（toggle） |
| `changeSelectedFilterIdsWithBoolean()` | 以布林值設定/移除篩選 ID |
| `removeMultipleSelectionKey()` | 移除多選篩選項 |
| `clearAllFilter()` | 清除所有篩選，僅保留 keyword |
| `containsFilterValue()` | 檢查某篩選值是否已選中 |
| `getSearchDestinationsResult()` | 搜尋目的地，支援 fuzzy search 降級 |
| `addRecentlySearchDestination()` | 新增最近搜尋目的地（DataStore，上限 10 筆） |
| `getRecentlySearchDestination()` | 讀取最近搜尋目的地 |
| `clearRecentlySearchDestination()` | 清除最近搜尋目的地 |
| `updateSelectedDestinationsWithData()` | 更新已選目的地及其名稱映射 |
| `getSelectedDestinationsWithNames()` | 取得已選目的地（含名稱） |
| `convertRangeToPriceText()` | 價格範圍轉顯示文字 |
| `formatDisplayPrice()` | 格式化商品價格顯示 |
| `getCurrencySymbol()` | 取得貨幣符號 |
| `filterProductTotalCount()` | 取得篩選後商品數量文字（>300 顯示 "300+"） |
| `saleProductCountText()` | 取得可售商品數文字 |
| `saleProductCountInt()` | 取得可售商品數整數 |
| `trackFilterConfirm()` | 埋點：篩選確認（區分全篩選/單篩選頁面） |
| `trackClearFilter()` | 埋點：清除篩選 |
| `trackFilterMenuPg()` | 埋點：篩選選單頁載入 |
| `trackFilterDropDownSelector()` | 埋點：下拉選擇器點擊 |
| `trackFilterMainItemFilter()` | 埋點：主篩選項點擊 |
| `trackFeatureItemFilter()` | 埋點：特色篩選項點擊 |
| `trackScrollFeatureItemFilter()` | 埋點：特色篩選項滑動 |
| `trackProductCardImpression()` | 埋點：商品卡片曝光（委派 `ProductCardTrackingUseCase`） |
| `trackProductCardClick()` | 埋點：商品卡片點擊（委派 `ProductCardTrackingUseCase`） |

---

## 業務邏輯摘要

- **兩階段篩選項載入**：先取得 `product_menu_mobile` 篩選項（頂部快捷篩選列），再取得 `product_list_mobile` 篩選項（完整篩選 BottomSheet），並將 list filter 的 ID 對應回 menu filter ID
- **分頁搜尋**：使用 Paging3 `Pager` + 自訂 `SearchResultPagingSource`，每頁 10 筆，offset-based 分頁
- **空結果推薦**：搜尋結果為空時自動呼叫 `getUserRecommendProduct()` 取得個人推薦商品
- **loading 狀態流轉**（KKAPP-6030）：骨架屏由 `_isLoading` 控制（初始 `true`）。`searchCategoryProduct` 在 `ApiResult.Success` **與** `ApiResult.Error` 都必須 `emit(false)`，否則 error 時會永遠卡在骨架屏。此外 `searchCategoryProduct` 開頭以 `_searchParamsReady` gate 等待 filter 載入完成；`getSearchResultTab` / `searchCategoryFilter` 在前置 API 失敗時仍需釋放 gate（tab 失敗續發 filter、filter 失敗於 error callback 放行），避免前置失敗導致 gate 永不開啟
- **目的地搜尋降級**：精確搜尋無結果時自動以 `fuzzySearch=true` 重新搜尋
- **目的地搜尋歷史**：透過 DataStore 存取最近搜尋的目的地（上限 10 筆）
- **DeepLink 支援**：支援從 DeepLink 帶入 keyword、分類、目的地、日期、價格等篩選條件
- **A/B 測試**：目的地篩選器有 `destinationFilterTest` A/B 測試控制
- **願望清單**：繼承 `WishViewModel`，`onResume` 時刷新收藏狀態
- **影片播放管理**：Activity 生命週期管理 `PlayerManager` 的初始化/播放/暫停/清理
- **埋點**：KTM 追蹤頁面載入、篩選操作、商品卡曝光/點擊，包含推薦系統相關屬性（sessionId、expVersion、algoVersion）

---

## 重要資料轉換點

| 位置 | 輸入型別 | 輸出型別 | 說明 |
|------|---------|---------|------|
| ViewModel | `SearchFilterCondition`（啟動參數） | `SelectedFilter` | 將路由傳入的篩選條件轉為內部篩選狀態 |
| Repository | `SelectedFilter` | `SearchProductListRequestBody` | 組裝搜尋 API 請求體 |
| ViewModel | `B2CApiResponse<SearchProductResult>` | `List<B2CProductCardData>` | 從 API 回應取出商品列表 |
| ViewModel | `B2CProductCardData` | `ProductHeaderInitData` | 點擊商品時轉換為商品詳情頁初始資料 |
| ViewModel | `SearchFilterData.filter` | 轉換後的 `SearchFilterData.filter` | `convertListFilterId()` 將 list filter ID 對應回 menu filter ID |

---

## 已知技術債

- **ViewModel 直接呼叫 Repository**：無 UseCase 抽象層，`SearchResultViewModel` 直接依賴 `SearchRepository`（search_page 內部類別），不符合 Clean Architecture
- **search_page 內部 SearchRepository 非介面**：`SearchRepository` 為具體類別而非介面，未實作 `domain/contract` 介面分離
- **SelectedFilter 定義位置**：`SelectedFilter` data class 定義在 `CategorySearchResultViewModel.kt` 檔案內，非獨立檔案
- **SearchDestinationUiState 定義位置**：sealed interface 定義在 `BottomSheetSearchDestinationViewNew.kt` 內，與 UI 檔案耦合
- **兩個同名 SearchRepository**：search_page 內部有自己的 `SearchRepository`（具體類別），search_core 也有 `SearchRepository`（介面），命名容易混淆

## 相關筆記
- [01-architecture](../01-architecture.md)
- [02-modules](../02-modules.md)
- [03-ui-patterns](../03-ui-patterns.md)
- [05-networking](../05-networking.md)
- [06-data-layer](../06-data-layer.md)
- [07-concurrency](../07-concurrency.md)
- [category-search-result](category-search-result.md)
- [order-detail-compose](order-detail-compose.md)
- [search-result](search-result.md)
- [sku-activity-shell](sku-activity-shell.md)

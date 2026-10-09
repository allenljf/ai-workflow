# 舊版搜尋結果頁 技術文件

> 自動產生 | 最後更新：2026-03-19

---

## 概述

- **所在 Module**：`:app`
- **UI 入口**：`SearchResultActivity.kt`
- **功能描述**：舊版搜尋結果頁，負責接收搜尋條件（關鍵字、目的地、附近商品等），並以分頁列表呈現搜尋結果，支援篩選、排序與即時搜尋切換。

---

## 檔案清單

```
UI（使用者介面入口）
 ├─ SearchResultActivity.kt       → app/.../view/search/activity/
 ├─ SearchTabFragment.kt          → app/.../view/search/tab/
 ├─ SearchResultFragment.kt       → app/.../view/search/result/
 └─ SearchResultAdapter.kt        → app/.../view/search/result/

ViewModel（UI 狀態管理）
 ├─ SearchResultViewModel.kt（Activity 層）→ app/.../view/search/activity/
 ├─ SearchViewModel.kt（Tab 層共享）      → app/.../view/search/tab/
 └─ SearchResultViewModel.kt（Fragment 層）→ app/.../view/search/result/

Presenter（MVP 模式）
 ├─ SearchTabPresenter.kt         → app/.../view/search/tab/
 └─ SearchResultPresenter.kt      → app/.../view/search/result/

Domain（業務邏輯 UseCase）
 ├─ SearchPageLoadTrackingUseCase.kt          → app/.../view/search/result/
 └─ SearchProductCardClickTrackingUseCase.kt  → app/.../view/search/result/

Data（資料層）
 ├─ SearchRepository.kt           → app/.../view/search/repository/
 └─ NetworkApi.kt / RetrofitApi.kt → app/.../network/

Network（API 定義）
 ├─ ISearchApiService.kt          → libs/networking/api/.../service/search_api/
 ├─ SearchApiService.kt           → libs/networking/api/.../service/search_api/
 └─ KKdayService.kt（搜尋相關端點）→ app/.../network/retrofit/

State / Reducer（Reductor）
 ├─ SearchActions.kt              → app/.../reducer/search/
 └─ SearchFilterActions.kt        → app/.../reducer/filter/
```

---

## 資料流

### 主流程：頁面進入後觸發搜尋

```
SearchResultActivity（UI 入口）
 │  onCreate() 根據傳入參數（destinationCode / searchFilterCondition / 附近商品）
 │  決定搜尋類型，呼叫 fragment.switchToSearchProductByKeyword() / searchLocation() /
 │  searchNearbyProducts() / searchProduct()
 ↓
SearchTabFragment（搜尋 Tab 容器）
 │  持有共享 SearchViewModel（Activity scope）
 │  使用者輸入關鍵字 → 呼叫 viewModel.searchTextChanged(keyword)
 │  按下搜尋 → 呼叫 store.dispatch(searchActions.searchProduct(...))
 ↓
Reductor Store（AppState）
 │  SearchActions 包裝搜尋條件，由 Store 分發至 Reducer
 │  Reducer 更新 AppState，NetworkApi 執行實際 API 呼叫
 ↓
NetworkApi / RetrofitApi（技術債：ViewModel 直接依賴，無 Repository 抽象）
 │  呼叫 KKdayService.searchProductList()
 │  呼叫 KKdayService.getSearchLink()（即時搜尋建議）
 ↓
API Service（KKdayService / ISearchApiService）
 │  GET v2/search/product_list（關鍵字搜尋）
 │  GET v2/search/link（即時搜尋連結建議）
 │  GET v2/search/prod/map/nearby（附近商品）
 │  GET v2/destination（熱門目的地）
 ↓
後端 API
```

### 回傳流

```
後端 API
 ↓
NetworkApi / RetrofitApi
 │  回傳 Observable<Response<SearchProductListResult>>
 │  Reductor Reducer 處理回應，更新 AppState
 ↓
SearchResultFragment（觀察狀態）
 │  SearchResultPresenter 訂閱 appState，轉換為 SearchResultViewInfo
 │  透過 MVP View 介面更新 UI
 ↓
SearchResultViewModel（Fragment）
 │  selectFilterLiveData、searchResultLiveData 更新篩選器與商品列表
 ↓
SearchResultFragment（UI 更新）
 │  觀察 LiveData，更新 SearchResultAdapter
 └─ 成功：顯示商品列表、篩選器標籤
    失敗 / 空結果：顯示 Empty State，提供推薦商品
```

### 即時搜尋（InstantSearch）子流程

```
SearchTabFragment
 │  使用者輸入文字 → viewModel.searchTextChanged(keyword)
 ↓
SearchViewModel
 │  keywordChangeFlow debounce 500ms
 │  呼叫 networkApi.getSearchLink(keyword)
 │  合併 AppState、keywordLinkResultFlow、destinationUiState、haveLocationPermission
 ↓
NetworkApi → GET v2/search/link?q=<keyword>
 ↓
SearchViewModel
 │  更新 _instantSearchResultViewInfo (LiveData)
 ↓
SearchTabFragment / InstantSearchFragment
 │  觀察並顯示即時建議（連結、商品卡片、目的地）
```

---

## 逐層說明

### UI 層

`SearchResultActivity` 是頁面入口，透過 KRouter `@Router(PAGE_SEARCH)` 接受路由參數：
- `destinationCode`：若有值則轉導至目的地頁
- `searchFilterCondition`：包含關鍵字、城市 ID、目的地 code 等篩選條件
- `isSearchNearByProduct`：是否搜尋附近商品
- `isDirectToNewSearchResult`：是否導向新版搜尋結果頁

Activity 本身邏輯極少，主要工作交給 `SearchTabFragment`（Nav Host 容器）。

`SearchTabFragment` 是核心 UI 容器，包含搜尋欄位（`AppCompatEditText`）與 NavController 管理的子 Fragment（`SearchMainFragment`、`InstantSearchFragment`、`SearchResultFragment`）。

`SearchResultFragment` 呈現商品列表（`RecyclerView` + `SearchResultAdapter`），含篩選標籤列（目的地、分類、日期、排序）與無限捲動分頁載入。

### ViewModel 層

架構混合 MVP + MVVM + Reductor，三層 ViewModel 各有職責：

1. **`SearchResultViewModel`（Activity 層）**：僅持有 `PersistentManager`，幾乎無業務邏輯，主要用於 Koin DI 注入點。

2. **`SearchViewModel`（Tab 層，Activity scope 共享）**：
   - 管理即時搜尋關鍵字流（`keywordChangeFlow`）
   - 合併多資料源（AppState RxJava Observable → Coroutine Flow、searchLink API 回應、定位狀態）
   - 發出 `specialLinkClickFlow`（SharedFlow）處理特殊連結點擊（目的地頁、交通、WebView）
   - 透過 Reductor `Store.dispatch()` 觸發搜尋動作

3. **`SearchResultViewModel`（Fragment 層）**：
   - 訂閱 `appState` 取得搜尋結果與篩選狀態
   - 管理篩選條件 `_selectFilterItemSubject`（BehaviorSubject，throttle 300ms）
   - 提供 `selectFilterLiveData`、`searchResultLiveData`、`filterProductTotalCount` 給 Fragment 觀察

### UseCase 層

UseCase 在此功能中僅用於追蹤，不處理核心業務邏輯：
- `SearchPageLoadTrackingUseCase`：搜尋頁載入追蹤
- `SearchProductCardClickTrackingUseCase`：商品卡片點擊追蹤

核心搜尋業務邏輯分散在 `SearchResultPresenter`（Reductor Store dispatch）與 `NetworkApi`，**缺少業務 UseCase 抽象層（技術債）**。

### Repository 層

`SearchRepository`（`app/.../view/search/repository/`）僅提供單一方法 `getDestination()`，透過 `KKApi.b2cApi.search` 取得目的地資料。

搜尋商品的主要資料流不經過此 Repository，而是由 `NetworkApi`（Singleton）直接呼叫 `KKdayService`，並透過 Reductor Store 管理狀態。此為主要技術債。

### API 層

**`ISearchApiService`**（`libs/networking/api/.../service/search_api/`）：

| Endpoint | 方法 | 用途 |
|----------|------|------|
| `GET v2/search/link` | `getSearchLinkResult(@Query("q") keyword)` | 即時搜尋建議連結 |
| `GET v2/search/prod/map/nearby` | `getNearbyProducts(lat, lon, ...)` | 附近商品 |
| `GET v2/destination` | `getDestination()` | 熱門目的地 |
| `GET v2/city_info` | `getCityPageInfo(areaCode)` | 城市頁資訊 |
| `POST v2/search/promo_filter` | `getSearchPromoFilter(body)` | 促銷篩選條件 |

**`KKdayService`**（`app/.../network/retrofit/`，舊版主要呼叫點）：

| Endpoint | 方法 | 用途 |
|----------|------|------|
| `GET v2/search/product_list` | `searchProductList(q, filter[destinations][], ...)` | 關鍵字搜尋商品列表 |
| `GET v2/search/product_filter` | `searchProductFilter(...)` | 取得篩選器 facets |
| `GET v2/search/link` | `getSearchLink(q)` | 即時搜尋建議（舊版） |

---

## View 方法清單

### SearchResultActivity

| 方法 | 說明 |
|------|------|
| `onCreate()` | 建立 `SearchTabFragment`，依路由參數決定搜尋類型 |
| `switchSearchResult()` | 根據 `searchFilterCondition` 內容分派至不同搜尋方法 |
| `switchSearch(fromPage)` | 切換至即時搜尋，更新 Status Bar 顏色 |
| `onBackPressed()` | 委派給 `SearchTabFragment.backPage()` 處理返回邏輯 |

### SearchResultFragment

| 方法 | 說明 |
|------|------|
| `initView()` | 初始化 Toolbar、RecyclerView、篩選標籤，設定返回鍵監聽 |
| `observeData()` | 觀察篩選 LiveData，更新篩選標籤 UI 狀態 |
| `initAction()` | 呼叫 Presenter `viewCreated()`，若有初始城市條件則觸發篩選 |
| `onStart()` | 附加 Presenter、呼叫 `viewReady()`，建立 BottomSheet Dialog 實例 |
| `switchToInstantSearchFragment()` | 透過 NavController 導向 `InstantSearchFragment` |
| `onSearchResultProductClick()` | 處理商品卡片點擊，觸發商品詳情頁 |
| `onRecommendedProductClick()` | 處理推薦商品點擊 |
| `onWishChanged()` | 呼叫 Presenter 新增/移除收藏 |
| `selectSearchSortTag()` | 觸發排序篩選 Action |

---

## ViewModel 方法清單

### SearchViewModel（Tab 層）

| 方法 | 說明 |
|------|------|
| `init` | 啟動 `updateInstantSearchViewInfo()`，合併多資料流至 `_instantSearchResultViewInfo` |
| `searchTextChanged(keyword)` | 更新 `keywordChangeFlow`，觸發即時搜尋 |
| `onSearchLinkClick(dto, position)` | 處理即時搜尋建議點擊，依類型 emit `specialLinkClickFlow` |
| `saveKeyword(keyword)` | 暫存搜尋關鍵字（切換 Fragment 時保留） |
| `resetKeyword()` | 清除暫存關鍵字，重置 `restoreKeywordFlow` |
| `restoreKeyword()` | 還原暫存關鍵字，dispatch `searchProduct` Action |
| `updateEnterCountry(info)` | 更新目的地篩選狀態 |
| `updateLocationPermission(bool)` | 更新定位權限狀態 |
| `trackInstantSearchView()` | 發送曝光埋點（商品卡、特殊連結） |
| `clickPopularCity(cityId, name)` | dispatch `clickPopularCity` Action |
| `setPopularCityFlow(list)` | 更新 `_popularCitiesFlow` |

### SearchResultViewModel（Fragment 層）

| 方法 | 說明 |
|------|------|
| `init` | 訂閱 `appState` 取得搜尋結果、篩選商品數、篩選條件；設定篩選 throttle 訂閱 |
| `selectedSearchFilterDateCommit()` | 提交日期篩選，dispatch 至 Store |
| `selectedSearchFilterItemChanged()` | 篩選條件變更（預覽計數，未提交） |
| `selectedSearchFilterItemCommit()` | 篩選條件提交（實際搜尋） |
| `initSelectCities(cities)` | 初始化城市篩選，dispatch `searchProduct` |
| `resetFilter()` | 重置所有篩選條件 |
| `resetCity()` / `resetCategory()` | 重置特定篩選維度 |
| `setResetDateFlag(bool)` | 標記日期篩選重置狀態 |
| `trackProductCardClick()` | 呼叫 `searchProductCardClickTrackingUseCase` |
| `trackFilterOutsideClicked()` | 篩選 Dialog 外部點擊追蹤 |

---

## 業務邏輯摘要

- 搜尋入口支援多種進入方式：關鍵字搜尋、目的地搜尋、附近商品、深連結
- 即時搜尋（Instant Search）在輸入 debounce 500ms 後呼叫 `v2/search/link`，回傳分類連結（目的地、促銷頁、主題頁等）與商品卡片建議
- 搜尋結果支援無限捲動分頁（`PaginationScrollListener`）
- 篩選條件（目的地、分類、日期、價格、語言、時長）透過 Reductor Store 管理，篩選 throttle 300ms 避免重複觸發
- 收藏（Wish）行為透過 `WishActions` 分發，與搜尋流程解耦
- 若搜尋結果為空，顯示推薦商品（`recommendProducts`）
- 新版搜尋結果頁（`NewSearchResultActivity` in `:libs/feature/search_page`）已存在，舊版與新版共存，由 `isDirectToNewSearchResult` 參數控制

---

## 已知技術債

- **缺少 Repository / UseCase 抽象層**：搜尋商品 API 由 `NetworkApi`（Singleton）直接呼叫，`SearchViewModel` 直接依賴 `NetworkApi`，未遵循 Clean Architecture 分層
- **混合架構**：`SearchResultFragment` 同時使用 MVP（`SearchResultPresenter`）與 MVVM（`SearchResultViewModel`），職責劃分模糊
- **RxJava + Coroutine 混用**：`AppState Observable` 透過 `asFlow()` 橋接，`SearchViewModel` 同時使用 `MutableStateFlow`、`MutableLiveData`、`BehaviorSubject`
- **SearchResultViewModel（Activity 層）**實際無業務邏輯，僅作為 Koin 注入點
- **舊版與新版並存**：`SearchTabFragment` 中存在導向 `NewSearchResultActivity` 的邏輯（`RESULT_CODE_BACK_CLICK`、`RESULT_CODE_SEARCH_BAR_CLICK`），新舊版切換邏輯夾雜在同一 Fragment 中

## 相關筆記
- [01-architecture](../01-architecture.md)
- [02-modules](../02-modules.md)
- [03-ui-patterns](../03-ui-patterns.md)
- [05-networking](../05-networking.md)
- [06-data-layer](../06-data-layer.md)
- [07-concurrency](../07-concurrency.md)
- [instant-search](instant-search.md)
- [new-search-result](new-search-result.md)
- [order-detail-compose](order-detail-compose.md)
- [sku-activity-shell](sku-activity-shell.md)

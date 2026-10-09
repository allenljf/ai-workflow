# 搜尋中繼頁 技術文件

> 自動產生 | 最後更新：2026-03-19

---

## 概述

- **所在 Module**：`:app`
- **UI 入口**：`InstantSearchFragment.kt`
- **功能描述**：使用者在搜尋列輸入關鍵字時，即時顯示推薦關鍵字、搜尋歷史、熱門城市、附近商品、搜尋連結（Special Link）等資訊的中繼頁面。無關鍵字時展示探索內容（已開放國家 Tab、附近體驗 Tab），有關鍵字時展示即時搜尋結果。

---

## 檔案清單

```
UI（使用者介面入口）
 ├─ InstantSearchFragment.kt                → app/.../view/search/instant/
 ├─ InstantSearchAdapter.kt                 → app/.../view/search/instant/
 ├─ InstantSearchHotAndHistoryAdapter.kt    → app/.../view/search/instant/
 ├─ InstantSearchTabAdapter.kt              → app/.../view/search/instant/
 ├─ InstantSearchDiffCallback.kt            → app/.../view/search/instant/
 ├─ SearchProductDelegate.kt               → app/.../view/search/instant/
 ├─ SearchHistoryDelegate.kt               → app/.../view/search/instant/
 ├─ RecommendedKeywordDelegate.kt          → app/.../view/search/instant/
 ├─ SearchSpecialLinkDelegate.kt           → app/.../view/search/instant/
 ├─ MoreButtonDelegate.kt                  → app/.../view/search/instant/
 ├─ InstantSearchEmptyResultDelegate.kt    → app/.../view/search/instant/
 ├─ EnterCountryAdapter.kt                 → app/.../view/search/instant/
 ├─ ViewInfoConverter.kt                   → app/.../view/search/instant/
 ├─ AdapterData.kt（SearchInstantViewType） → app/.../view/search/instant/
 └─ empty/                                 → app/.../view/search/instant/empty/
     ├─ InstantPopularCityDelegate.kt
     ├─ InstantSearchPopularCityAdapter.kt
     ├─ PopularCityImageDelegate.kt
     ├─ SearchPopularCityDelegate.kt
     ├─ RecommendProductDelegate.kt
     ├─ ProductDelegate.kt / ProductAdapter.kt / RecommendProductAdapter.kt
     └─ helper/ (MediumProductViewHelper, SmallProductViewHelper, ProductViewHelper)

ViewModel（UI 狀態管理）
 ├─ SearchViewModel.kt                     → app/.../view/search/tab/    （主要狀態管理，Reductor + Coroutine 混合）
 └─ InstantSearchViewModel.kt              → app/.../view/search/instant/（目的地資料取得）

Presenter（MVP 模式 - 舊架構）
 └─ InstantSearchPresenter.kt              → app/.../view/search/instant/ （願望清單、附近商品 count、Reductor dispatch）

MVP Interface
 └─ InstantSearchMvpView.kt                → app/.../view/search/instant/

Data（資料層）
 └─ SearchRepository.kt                    → app/.../view/search/repository/（目的地 API 呼叫）

Network（API 定義）
 ├─ SearchApiService.kt                    → libs/networking/api/.../service/search_api/
 ├─ ISearchApiService.kt                   → libs/networking/api/.../service/search_api/（Retrofit 介面定義）
 └─ KKdayService.kt                        → app/.../network/retrofit/  （舊版 getSearchLink API）

Network Wrapper（舊版 API 封裝）
 ├─ NetworkApi.kt                          → app/.../network/
 └─ RetrofitApi.kt                         → app/.../network/retrofit/

Model
 ├─ InstantSearchResultViewInfo.kt         → app/.../view/search/tab/     （UI 顯示用 ViewInfo）
 ├─ EnterDestinationInfo.kt                → libs/model/.../resource/search/cityPage/
 ├─ SearchLinkResult.kt / SearchLinkDto.kt → libs/model/.../model/search/
 └─ SearchLinkType.kt                      → libs/model/.../model/search/ （與 SearchLinkResult 同檔）

Reductor（狀態管理）
 └─ SearchActions.kt                       → app/.../reducer/search/
```

---

## 資料流

### 主流程 1：頁面載入 - 取得目的地資料（已開放國家）

```
UI（InstantSearchFragment）
 │  initAction() 呼叫
 │  instantVM.fetchDestinations()
 ↓
ViewModel（InstantSearchViewModel）
 │  fetchDestinations()
 │  呼叫：searchRepository.getDestination()
 ↓
Repository（SearchRepository）
 │  safeApiCall { kkApi.b2cApi.search.getDestination<EnterDestinationInfo>() }
 ↓
API（SearchApiService → ISearchApiService）
 │  GET v2/destination
 ↓
後端 API
```

### 主流程 2：關鍵字輸入 - 取得搜尋連結（Search Link）

```
UI（上層 SearchTabFragment 傳入關鍵字）
 │  viewModel.searchTextChanged(keyword)
 ↓
ViewModel（SearchViewModel）
 │  keywordChangeFlow.emit(keyword)
 │  debounce(500ms) 後觸發 getSearchLinkFlow()
 │  呼叫：networkApi.getSearchLink(keyword)
 ↓
NetworkApi → RetrofitApi → KKdayService
 │  GET v2/search/link?q={keyword}
 ↓
後端 API
```

### 主流程 3：Reductor State 驅動的資料（搜尋結果、推薦關鍵字、歷史記錄等）

```
Reductor Store（AppState）
 │  state.map { ... } 轉換為 InstantSearchResultViewInfo
 │  包含：searchKeyword, recommendKeywords, searchProductResult,
 │        searchHistories, popularCities, nearbyProducts, wishInfos 等
 ↓
ViewModel（SearchViewModel）
 │  combine(instantSearchViewInfoFlow, keywordLinkResultFlow, destinationUiState, haveLocationPermission)
 │  debounce(500ms)
 │  更新 _instantSearchResultViewInfo (LiveData)
 ↓
UI（InstantSearchFragment）
 │  observe instantSearchResultViewInfo → updateData()
 │  keyword 為空 → showTabView()（顯示已開放國家 + 附近體驗 Tab）
 │  keyword 非空 → showResultView()（顯示搜尋結果列表）
```

### 回傳流

```
後端 API
 ↓
Repository / NetworkApi
 │  解析 response
 │  目的地 API：B2CApiResponse<EnterDestinationInfo>
 │  搜尋連結 API：Response<SearchLinkResult>
 ↓
ViewModel（SearchViewModel）
 │  combine 多個 Flow，組合成 InstantSearchResultViewInfo
 │  透過 LiveData 發送至 UI
 ↓
UI（InstantSearchFragment）
 │  updateData(viewInfo) 更新畫面
 └─ 成功：根據 keyword 切換 Tab 或搜尋結果模式
    失敗：搜尋連結 API 失敗時 catch 並回傳空結果，不影響其他資料
```

---

## 逐層說明

### UI 層

`InstantSearchFragment` 繼承 `BaseFragment`，同時實作 `InstantSearchMvpView`（空介面）。使用兩套 RecyclerView：
- `recyclerHot`：顯示熱門關鍵字與搜尋歷史（無關鍵字時）
- `recyclerSearchResult`：顯示搜尋結果（有關鍵字時）
- `viewpagerSearchTab` + `TabLayout`：分頁顯示「已開放國家」與「附近體驗」

透過 `viewModel.instantSearchResultViewInfo.observe()` 監聽 `InstantSearchResultViewInfo`，在 `updateData()` 中判斷 keyword 是否為空來切換顯示模式。

### ViewModel 層

**SearchViewModel**（主要）：
- 繼承 `BaseViewModel`，混合使用 Reductor（`Observable<AppState>`）與 Coroutine Flow
- `instantSearchViewInfoFlow`：從 Reductor `AppState` 映射產生，包含搜尋結果、推薦關鍵字、歷史記錄、願望清單等
- `keywordChangeFlow`：接收關鍵字變更，debounce 500ms 後呼叫 `getSearchLink` API
- `combine` 四個 Flow（state flow、search link flow、destination flow、permission flow）產出最終 `InstantSearchResultViewInfo`
- 大量追蹤邏輯（EventTracker + KTMTracker）

**InstantSearchViewModel**（輔助）：
- 僅負責呼叫 `searchRepository.getDestination()` 取得已開放國家資料
- 透過 `StateFlow<EnterDestinationInfo?>` 發送結果

### Presenter 層（舊架構）

`InstantSearchPresenter` 繼承 `RxBasePresenter`，透過 Reductor Store dispatch 處理：
- `getNearbyProductCount()`：dispatch `appActions.getNearbyProductCount()`
- `addWishProduct()` / `removeWishProduct()`：dispatch `wishActions`
- `clickSearchResultPageProduct()`：dispatch `searchActions`

### Repository 層

`SearchRepository`（`app/.../view/search/repository/`）：
- 繼承 `BaseApiRepository`
- 唯一方法 `getDestination()`：透過 `kkApi.b2cApi.search.getDestination<EnterDestinationInfo>()` 呼叫 API
- 使用 `safeApiCall` 包裝錯誤處理

搜尋連結 API 則直接由 `SearchViewModel` 透過 `NetworkApi.getSearchLink()` 呼叫（舊版架構，未經 Repository 抽象）。

### API 層

| Endpoint | HTTP 方法 | 參數 | Response | 用途 |
|----------|-----------|------|----------|------|
| `v2/destination` | GET | 無 | `EnterDestinationInfo`（title + destinations） | 取得已開放國家目的地 |
| `v2/search/link` | GET | `q`=keyword | `SearchLinkResult`（links: List<SpecialLinkDto>） | 取得搜尋建議連結 |

---

## View 方法清單

| 方法 | 說明 |
|------|------|
| `initAction()` | 觀察 viewModel 的 instantSearchResultViewInfo；呼叫 instantVM.fetchDestinations()；更新位置權限狀態 |
| `initView()` | 設定 recyclerHot / recyclerSearchResult / viewpagerSearchTab / TabLayout；註冊滑動監聽與觸控攔截 |
| `observeData()` | 空實作 |
| `onActivityCreated()` | 將 InstantSearchPresenter attach 至 view |
| `onStart()` | 透過 presenter 取得附近商品數量 |
| `onDestroy()` | detach presenter |
| `setSearchItemClickListener()` | 設定搜尋歷史、推薦關鍵字、商品點擊、熱門城市點擊等各類回調 |
| `updateData()` | 接收 InstantSearchResultViewInfo，清除/重建 Tab，更新 adapter 資料，切換 Tab/Result 顯示模式 |
| `showTabView()` | 顯示 Tab + ViewPager，隱藏搜尋結果列表 |
| `showResultView()` | (private) 隱藏 Tab，顯示搜尋結果列表 |
| `setOnMoreClick()` | 設定「更多」按鈕點擊回調 |
| `onScrollDown()` | 註冊向下滾動回調（超過 20dp 閾值時觸發） |
| `onWishChanged()` | (private) 處理願望清單新增/移除，透過 presenter dispatch |
| `onSearchResultProductClick()` | (private) 商品卡片點擊：tracker 記錄 + 啟動商品詳情頁 |
| `handleBackPress()` | (private) 攔截返回鍵，透過 EventBus 發送 BackPage 事件 |
| `newInstance()` | (companion) 工廠方法，建立 Fragment 並傳入 isOrderRecommend 與 fromPage 參數 |

---

## ViewModel 方法清單

### SearchViewModel

| 方法 | 說明 |
|------|------|
| `init` | 啟動 keywordLinkResultFlow，呼叫 updateInstantSearchViewInfo() combine 四個 Flow |
| `updateInstantSearchViewInfo()` | (private) combine instantSearchViewInfoFlow + searchLinkFlow + destinationFlow + permissionFlow，debounce 500ms 後更新 LiveData |
| `getSearchLinkFlow()` | (private) keyword debounce 500ms 後呼叫 networkApi.getSearchLink()，空 keyword 回傳空結果 |
| `updateEnterCountry()` | 更新已開放國家 StateFlow |
| `updateLocationPermission()` | 更新位置權限 StateFlow |
| `searchTextChanged()` | 接收 UI 輸入的關鍵字，emit 至 keywordChangeFlow |
| `saveKeyword()` / `resetKeyword()` / `restoreKeyword()` | 關鍵字暫存與恢復 |
| `onSearchLinkClick()` | 處理搜尋連結點擊，依 type 發送不同 LinkClickAction（Destination / Transportation / WebView） |
| `trackInstantSearchViewNew()` | 探索頁曝光追蹤 |
| `trackInstantSearchView()` | 搜尋結果曝光追蹤 |
| `trackProductItemClick()` | 商品點擊追蹤（區分有/無 keyword） |
| `trackInstantSearchClickHistory()` | 搜尋歷史點擊追蹤 |
| `trackInstantSearchClickKeyword()` | 熱門關鍵字點擊追蹤 |
| `trackInstantSearchClickPopularCity()` | 熱門城市點擊追蹤 |
| `trackInstantSearchClickNew()` | 通用點擊追蹤 |
| `trackInstantSearchSwitch()` | Tab 切換追蹤 |
| `setPopularCityFlow()` | 設定熱門城市 Flow |
| `clickPopularCity()` | dispatch Reductor action 處理城市點擊 |

### InstantSearchViewModel

| 方法 | 說明 |
|------|------|
| `fetchDestinations()` | 呼叫 searchRepository.getDestination()，成功後更新 destinationUiState |

---

## 業務邏輯摘要

- **雙模式顯示**：keyword 為空時顯示「探索模式」（熱門關鍵字、搜尋歷史、已開放國家 Tab、附近體驗 Tab）；keyword 非空時顯示「搜尋結果模式」（商品卡片、搜尋連結）
- **搜尋連結分類**：`SearchLinkType` 包含 ThemePage、PromoPage、Country、City、Destination、Point2Point、ProdCard、ProdList、PoiPage 等類型，點擊後分別導向 WebView、目的地搜尋結果或交通頁
- **Debounce 機制**：關鍵字變更 debounce 500ms 後才呼叫搜尋連結 API；combine 結果再 debounce 500ms 後更新 UI
- **位置權限**：影響附近商品的顯示方式（有權限直接顯示商品列表，無權限顯示提示文字 + 商品列表）
- **願望清單**：透過 Reductor WishActions 處理新增/移除
- **追蹤埋點**：使用 EventTracker（舊版）與 KTMTracker（新版）雙軌追蹤，涵蓋 impression / click 事件

---

## 已知技術債

- **MVP + MVVM + Reductor 混合架構**：同一頁面同時使用 `InstantSearchPresenter`（MVP）、`SearchViewModel`（MVVM + Reductor）、`InstantSearchViewModel`（純 MVVM），三種模式共存
- **SearchViewModel 直接依賴 NetworkApi**：搜尋連結 API 呼叫未經 Repository 抽象層，直接使用 `NetworkApi.getSearchLink()`（舊版 Retrofit 封裝）
- **SearchRepository 放置於 view 套件**：`app/.../view/search/repository/SearchRepository.kt` 未遵循 `:data:repository` 模組分離
- **Reductor 與 Coroutine Flow 混合**：`SearchViewModel` 將 RxJava `Observable<AppState>` 透過 `asFlow()` 轉為 Coroutine Flow，再與其他 StateFlow combine
- **InstantSearchMvpView 為空介面**：MVP 模式的 View 介面已無實質方法，但 Presenter 仍保留 attach/detach 生命週期
- **無 UseCase 層**：ViewModel 直接呼叫 Repository / NetworkApi，未經 Domain UseCase 抽象

## 相關筆記
- [01-architecture](../01-architecture.md)
- [02-modules](../02-modules.md)
- [03-ui-patterns](../03-ui-patterns.md)
- [04-di-koin](../04-di-koin.md)
- [05-networking](../05-networking.md)
- [06-data-layer](../06-data-layer.md)
- [07-concurrency](../07-concurrency.md)
- [order-detail-compose](order-detail-compose.md)
- [search-result](search-result.md)

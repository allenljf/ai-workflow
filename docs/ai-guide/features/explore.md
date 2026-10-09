# 搜尋首頁（Explore）技術文件

> 自動產生 | 最後更新：2026-03-19

---

## 概述

- **所在 Module**：`:feature:search_page`（UI 層）、`:feature:search_core`（Domain / Data 層）
- **UI 入口**：`ExploreFragment.kt` + `ExplorePage.kt`（Compose）
- **功能描述**：目的地探索頁面，提供推薦目的地（DCS 推薦標籤頁）與熱門目的地（洲際分類標籤頁）兩大區塊，支援點擊城市進入目的地頁、點擊標題進入國家頁，以及搜尋框跳轉至搜尋頁。

---

## 檔案清單

```
UI（使用者介面入口）
 ├─ ExploreFragment.kt    → libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/explore/
 ├─ ExplorePage.kt        → libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/explore/
 ├─ ExploreItem.kt        → libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/explore/
 ├─ ExploreContinentItem.kt → libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/explore/
 ├─ ExploreFlowItem.kt    → libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/explore/
 ├─ ExploreFlowItemTitle.kt → libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/explore/
 ├─ ExploreFlowLayout.kt  → libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/explore/
 ├─ HeaderTabTemplate.kt  → libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/explore/
 ├─ SearchBar.kt          → libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/explore/
 ├─ SearchBox.kt          → libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/explore/
 └─ SearchHeader.kt       → libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/explore/

ViewModel（UI 狀態管理）
 └─ ExploreViewModel.kt   → libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/explore/viewmodel/

Domain（業務邏輯 UseCase）
 └─ （無獨立 UseCase；ViewModel 直接依賴 DestinationRepository 介面）

Data（資料層介面與實作）
 ├─ DestinationRepository.kt（介面）  → libs/feature/search_core/src/main/java/com/kkday/search/domain/repository/
 └─ DestinationRepositoryImpl.kt      → libs/feature/search_core/src/main/java/com/kkday/search/data/repository/

Network（API 定義）
 └─ DestinationApiService.kt          → libs/feature/search_core/src/main/java/com/kkday/search/network/

Data Model
 ├─ DCSRecommendDestinations.kt       → libs/model/src/main/java/com/kkday/library/common/model/search/recommend/
 └─ SearchPopularDestination.kt       → libs/model/src/main/java/com/kkday/library/common/model/search/recommend/
```

---

## 資料流

### 主流程：頁面載入 / 資料取得

```
UI（ExploreFragment）
 │  onCreateView() 呼叫：viewModel.trackViewDestExplorePg()
 │  onCreateView() 呼叫：viewModel.getPopularDestinations(context)
 ↓
ViewModel（ExploreViewModel）
 │  並行發起兩個 Coroutine：
 │    1) destinationRepository.getRecommendDestinations()  → 推薦標籤頁
 │    2) destinationRepository.getSearchPopularDestinations() → 洲際分類頁
 ↓
Repository（DestinationRepositoryImpl）
 │  1) safeApiCall { destinationApiService.getRecommendDestinations() }
 │  2) safeApiCall { destinationApiService.getPopularDestinations() }
 ↓
API（DestinationApiService）
 │  GET v2/search/product/recommend_destinations
 │  GET v2/search/product/popular_destinations
 ↓
後端 API
```

### 回傳流

```
後端 API
 ↓
Repository
 │  B2CApiResponse<DCSRecommendDestinations> → ApiResult<DCSRecommendDestinations>
 │  B2CApiResponse<SearchPopularDestinationResult> → ApiResult<SearchPopularDestinationResult>
 ↓
ViewModel
 │  apiSuccess{} 解包 ApiResult，失敗則 return@apiSuccess（不更新狀態）
 │  推薦頁：將 DCSRecommendDestinations.tabs 中的多語言欄位透過 getStringWithLangKey() 轉換
 │  洲際頁：若帶有 destinationCode 參數，計算對應的 continentTabIndex / countryRowIndex
 │  更新：viewState（Compose mutableStateOf<ExploreViewState>）
 ↓
UI（ExplorePage Composable）
 │  觀察 viewModel.viewState（Compose State）自動重組
 └─ 成功：渲染標籤列（tabList）、推薦頁（exploreRecommendPage）、洲際頁（exploreContinentPage）
    失敗：狀態不更新，頁面保持預設空白（無明確錯誤提示 UI）
```

---

## 逐層說明

### UI 層

`ExploreFragment` 以 `ComposeView` 嵌入 Fragment，在 `onCreateView()` 觸發資料載入與追蹤事件。使用 `DisposableEffect` 監聽 Fragment 生命週期，在 `ON_RESUME` 時重新讀取 arguments 中的 `KEY_EXPLORE_TAB_INDEX` / `KEY_EXPLORE_ROW_INDEX`，支援從其他頁面返回時自動滾動定位。`LaunchedEffect` 監聽 ViewModel 計算出的 `continentTabIndex`，用於透過 `destinationCode` 參數自動定位至對應洲際標籤。

`ExplorePage` 是純 Composable，接收 `ExploreViewState` 渲染兩種內容：
- `pageIndex < exploreRecommendPage.tabs.size`：渲染推薦標籤頁（`ExploreItem`）
- 超出部分：渲染洲際頁（`ExploreContinentItem`）

### ViewModel 層

`ExploreViewModel` 持有一個 `var viewState: ExploreViewState` 以 Compose `mutableStateOf` 管理狀態，**非** StateFlow / LiveData。狀態更新使用 `viewState = viewState.copy(...)` 觸發 Compose 重組。

`ExploreViewState` 內部使用 `by mutableStateOf(...)` 對外暴露計算後的屬性（`tabList` 合併推薦與洲際標籤）。

ViewModel 無 UseCase 抽象層，直接依賴 `DestinationRepository` 介面（技術債）。

### UseCase 層

此功能無獨立 UseCase。`ExploreViewModel` 直接注入並呼叫 `DestinationRepository`，不符合理想 Clean Architecture（技術債）。

### Repository 層

`DestinationRepositoryImpl` 繼承 `BaseApiRepository`，使用 `safeApiCall {}` 將 Retrofit suspend call 包裝為 `Flow<ApiResult<T>>`，統一處理例外與錯誤轉換。Explore 功能用到兩個方法：
- `getRecommendDestinations()`：對應 DCS 推薦目的地
- `getSearchPopularDestinations()`：對應熱門洲際分類

無本地快取（Room / DataStore）邏輯。

### API 層

| 方法 | HTTP | Endpoint | 回傳 |
|------|------|----------|------|
| `getRecommendDestinations()` | GET | `v2/search/product/recommend_destinations` | `DCSRecommendDestinations` |
| `getPopularDestinations()` | GET | `v2/search/product/popular_destinations` | `SearchPopularDestinationResult` |

---

## View 方法清單

| 方法 | 說明 |
|------|------|
| `onCreateView()` | 觸發追蹤事件與資料載入；建立 ComposeView，設定 Compose 內容（狀態讀取、生命週期監聽、ExplorePage 渲染） |
| `onResume()` | 呼叫 `viewModel.trackKTMLoadPage()` 回報 KTM 頁面載入事件 |
| `searchBarClick()` | 透過 RouterHelper 導航至搜尋頁（`PAGE_SEARCH`），帶 `KEY_FROM_PAGE = "DestExplorePg"` |
| `exploreFlowItemClick()` | 追蹤城市點擊事件後，導航至目的地頁（`PAGE_DESTINATION`），帶 `destinationCode`、`tabIndex`、`rowIndex` |
| `exploreFlowItemTitleClick()` | 追蹤「查看更多」點擊事件後，導航至目的地頁（`PAGE_DESTINATION`）帶國家 `destinationCode` |
| `exploreTabClick()` | 追蹤標籤切換事件 |
| `newInstance()` | companion object factory，建立帶有 `destinationCode`、`initTabIndex`、`initRowIndex` 的 Fragment |

---

## ViewModel 方法清單

| 方法 | 說明 |
|------|------|
| `getPopularDestinations(context)` | 並行呼叫兩個 Repository 方法取得推薦目的地與洲際分類，更新 `viewState` |
| `trackKTMLoadPage()` | 發送 KTM 頁面載入事件（`DestinationMenuPg`） |
| `trackViewDestExplorePg()` | 發送 KKTracker 頁面瀏覽事件（`View_DestExplorePg`） |
| `trackClickDestExplorePgTab()` | 發送標籤點擊追蹤事件，帶 `tabTitle` |
| `trackClickDestExplorePgCity()` | 發送城市點擊追蹤事件，帶 `destinationCode`、`destinationName`、`action` |
| `trackClickDestExplorePgViewMore()` | 發送「查看更多」點擊追蹤事件，帶 `countryName`、`destinationCode` |

---

## 重要資料轉換點

| 位置 | 輸入型別 | 輸出型別 | 說明 |
|------|---------|---------|------|
| DestinationRepositoryImpl | `B2CApiResponse<DCSRecommendDestinations>` | `ApiResult<DCSRecommendDestinations>` | safeApiCall 包裝，統一錯誤處理 |
| DestinationRepositoryImpl | `B2CApiResponse<SearchPopularDestinationResult>` | `ApiResult<SearchPopularDestinationResult>` | safeApiCall 包裝 |
| ExploreViewModel（getPopularDestinations） | `DCSRecommendDestinations` | `SearchExploreData`（viewState） | 多語言欄位透過 `getStringWithLangKey(context)` 轉換 |
| ExploreViewModel（getPopularDestinations） | `SearchPopularDestinationResult` | `ExploreViewState.exploreContinentPage` + `continentTabIndex` | 若帶 `destinationCode` 參數，計算自動定位索引 |

---

## 業務邏輯摘要

- 頁面同時載入兩種資料（推薦標籤、洲際分類），互相獨立不阻塞
- 標籤列（`tabList`）由推薦標籤 + 洲際標籤合併組成，順序固定（推薦在前）
- 支援 `destinationCode` 傳入：ViewModel 自動計算對應的 `continentTabIndex`（洲際標籤索引）與 `countryRowIndex`（國家行索引），使 UI 自動滾動定位
- Arguments 中的 `KEY_EXPLORE_TAB_INDEX` / `KEY_EXPLORE_ROW_INDEX` 優先級高於 ViewModel 計算值，且用過後自動清除（`paramsUsed = true`）
- 錯誤處理：API 失敗時 `apiSuccess{}` 不觸發，`viewState` 保持上一次或預設空白狀態，無明確錯誤提示 UI

---

## 已知技術債

- `ExploreViewModel` 直接依賴 `DestinationRepository` 介面，缺少 UseCase 抽象層，不符合理想 Clean Architecture。新功能若需擴充探索頁邏輯，應補充對應 UseCase。
- `ExploreViewModel` 位於 `:feature:search_page`，但 `DestinationRepository` 介面與實作位於 `:feature:search_core`，跨 feature 模組直接依賴（未透過 `:domain:contract` 統一管理）。
- API 失敗時無錯誤 UI 回饋，使用者看到空白頁面而無任何提示。

## 相關筆記
- [01-architecture](../01-architecture.md)
- [02-modules](../02-modules.md)
- [03-ui-patterns](../03-ui-patterns.md)
- [05-networking](../05-networking.md)
- [06-data-layer](../06-data-layer.md)
- [07-concurrency](../07-concurrency.md)
- [destination](destination.md)
- [home](home.md)
- [order-detail-compose](order-detail-compose.md)
- [sku-activity-shell](sku-activity-shell.md)

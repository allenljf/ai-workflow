# 首頁主頁面 技術文件

> 自動產生 | 最後更新：2026-03-19

---

## 概述

- **所在 Module**：`:app`（UI / ViewModel / UseCase）、`:feature:home_page`（Repository）、`:libs:networking`（API）
- **UI 入口**：`HomeV2Fragment.kt`（Fragment 殼） + `HomeScreen.kt`（Compose 主畫面）
- **功能描述**：App 首頁，展示主題分類、行銷 Banner、近期瀏覽商品、即將出發訂單、Waterfall 瀑布流推薦商品等區塊，並負責通知角標、購物車數量更新與網路狀態監控。

---

## 檔案清單

```
UI（使用者介面入口）
 ├─ HomeV2Fragment.kt                   → app/src/main/java/com/kkday/member/view/homeV2/presentation/
 ├─ HomeScreen.kt（Compose 主畫面）      → app/src/main/java/com/kkday/member/view/homeV2/presentation/
 ├─ HomeUiState.kt（UI 狀態定義）        → app/src/main/java/com/kkday/member/view/homeV2/presentation/
 ├─ HomeUiEvent.kt（一次性事件）         → app/src/main/java/com/kkday/member/view/homeV2/event/
 └─ components/                         → app/src/main/java/com/kkday/member/view/homeV2/presentation/components/
     ├─ CollapsingToolbar.kt
     ├─ CouponBannerItem.kt
     ├─ DestinationCardItem.kt
     ├─ HomeProductCard.kt
     ├─ MKTBannerCardItem.kt
     ├─ RecentlyViewedProdItem.kt
     ├─ ThemeCategoryItem.kt
     ├─ WaterfallAppendIngItem.kt
     └─ ...及其他元件

ViewModel（UI 狀態管理）
 └─ HomeViewModelV2.kt                  → app/src/main/java/com/kkday/member/view/homeV2/presentation/

Domain（業務邏輯 UseCase）
 ├─ HomeUseCases.kt（Facade 聚合器）    → app/src/main/java/com/kkday/member/view/homeV2/useCase/
 ├─ GetHomeDataUseCase.kt              → app/src/main/java/com/kkday/member/view/homeV2/useCase/
 ├─ GetThemeCategoriesUseCase.kt       → app/src/main/java/com/kkday/member/view/homeV2/useCase/
 ├─ GetUpcomingOrderAndCrossSellUseCase.kt  → app/src/main/java/com/kkday/member/view/homeV2/useCase/
 ├─ GetWaterfallListPagingUseCase.kt   → app/src/main/java/com/kkday/member/view/homeV2/useCase/
 ├─ GetWaterfallFilterUseCase.kt       → app/src/main/java/com/kkday/member/view/homeV2/useCase/
 ├─ GetRecentProductsUseCase.kt        → app/src/main/java/com/kkday/member/view/homeV2/useCase/
 ├─ GetCartProdCountUseCase.kt         → app/src/main/java/com/kkday/member/view/homeV2/useCase/
 ├─ GetNotificationCountUseCase.kt     → app/src/main/java/com/kkday/member/view/homeV2/useCase/
 ├─ GetCohortCouponsUseCase.kt         → app/src/main/java/com/kkday/member/view/homeV2/useCase/
 ├─ GetCouponBannerUseCase.kt          → app/src/main/java/com/kkday/member/view/homeV2/useCase/
 ├─ GetHomeFabUseCase.kt               → app/src/main/java/com/kkday/member/view/homeV2/useCase/
 ├─ GetFooterStringUseCase.kt          → app/src/main/java/com/kkday/member/view/homeV2/useCase/
 ├─ GetRecommendKeywordsUseCase.kt     → app/src/main/java/com/kkday/member/view/homeV2/useCase/
 ├─ AcquireCouponUseCase.kt            → app/src/main/java/com/kkday/member/view/homeV2/useCase/
 ├─ CheckLoyaltyUseCase.kt             → app/src/main/java/com/kkday/member/view/homeV2/useCase/
 ├─ ShouldShowFirstPurchaseBannerUseCase.kt → app/src/main/java/com/kkday/member/view/homeV2/useCase/
 ├─ WaterfallListPagingSource.kt       → app/src/main/java/com/kkday/member/view/homeV2/useCase/
 └─ ...及其他設定 UseCase

Data（資料層）
 └─ HomeRepository.kt                  → libs/feature/home_page/src/main/java/com/kkday/home_page/data/repository/
    ※ 直接繼承 BaseApiRepository，無 domain/contract 介面分離（技術債）

Network（API 定義）
 ├─ IHomeApiService.kt（介面）          → libs/networking/api/src/main/java/com/kkday/library/networking/service/home/
 └─ HomeApiService.kt（實作）           → libs/networking/api/src/main/java/com/kkday/library/networking/service/home/

Data Model
 ├─ B2CHomeData                        → libs/networking/resource/home/
 ├─ WaterfallDestination               → libs/networking/resource/home/
 ├─ HomeCouponBanner                   → libs/networking/resource/home/
 ├─ B2CRecommendProducts               → libs/networking/resource/product/
 └─ HomeUiState.kt（UI 層狀態，非 API Model）
```

---

## 資料流

### 主流程：頁面載入 / 首頁資料取得

```
HomeV2Fragment（onViewCreated）
 │  設定 ComposeView，收集 viewModel.uiState
 │  呼叫：由 Koin 注入 HomeViewModelV2
 ↓
HomeViewModelV2（init block）
 │  依序呼叫：getHomeData() / getThemeCategories() / getHistoryProduct()
 │            getUpcomingOrder() / getWaterfallFilter() / getCartProdCount()
 │            getNotificationCount() / getHomeFab() / getFooterString()
 │            fetchContinueSearchKeywords() ...（共 11 項並行初始化）
 │  呼叫：homeUseCases.getHomeData()
 ↓
HomeUseCases（@Single Facade）
 │  委派至 GetHomeDataUseCase.invoke()
 ↓
GetHomeDataUseCase
 │  讀取快取設定（AppRepository.getDCSApiCacheModel）
 │  組裝 CacheRequestModel（若快取開啟）
 │  呼叫：homeRepository.getHomeData(currency, lang, countryCode, cacheRequestModel)
 ↓
HomeRepository
 │  呼叫：kkApi.b2cApi.home.getHomepage<B2CHomeData>(currency, lang, countryCode)
 │  包裝於 safeApiCall { } 統一錯誤處理
 ↓
IHomeApiService
 │  GET v3/home?currency=&lang=&locale=
 ↓
後端 API
```

### 回傳流

```
後端 API
 ↓
HomeRepository：B2CApiResponse<B2CHomeData> → ApiResult<B2CHomeData>
 ↓（Flow<ApiResult<B2CHomeData>>）
GetHomeDataUseCase：直接回傳 Flow，不轉換
 ↓
HomeViewModelV2：
  ApiResult.Success → _uiState.update { copy(homeData = result, isLoading = false) }
  ApiResult.Error   → _uiState.update { copy(apiError = errorMessage) }
 ↓（StateFlow<HomeUiState>）
HomeV2Fragment → collectAsState()
 ↓
HomeScreen（Compose）：根據 uiState 渲染各區塊
```

### Waterfall 瀑布流（Paging3）

```
HomeViewModelV2
 │  combine(_impression, _filter) → flatMapLatest
 │  呼叫：homeUseCases.getWaterfallListPaging(destination, impressions)
 ↓
GetWaterfallListPagingUseCase → WaterfallListPagingSource
 │  POST v3/home/waterfall_list（分頁）
 ↓
PagingData<HomeWaterfallCard>（cachedIn viewModelScope）
 ↓
HomeScreen：LazyColumn / collectAsLazyPagingItems()
```

---

## 逐層說明

### UI 層
`HomeV2Fragment` 作為 Fragment 殼，設定 `ComposeView` 並使用 `ViewCompositionStrategy.DisposeOnViewTreeLifecycleDestroyed`。實際畫面由 `HomeScreen.kt`（Compose）渲染。Fragment 負責處理 Activity Result（如優惠券底單）、DeepLink 路由、追蹤事件呼叫，並透過 `HomeEventClickListener` 轉發點擊事件。

### ViewModel 層
`HomeViewModelV2` 使用 `MutableStateFlow<HomeUiState>` 管理 UI 狀態，`MutableSharedFlow<HomeUiEvent>` 處理一次性事件（如優惠券領取成功 Toast）。`init` block 並行啟動 11 項資料載入。Waterfall 分頁採 Paging3 + `flatMapLatest` 動態切換目的地篩選。繼續搜尋功能有 30 秒防抖機制。

### UseCase 層
以 `HomeUseCases`（@Single）作為 Facade，聚合 20+ 個單一職責 UseCase。各 UseCase 標記 `@Single`（技術債：應為 `@Factory`）。`GetHomeDataUseCase` 包含快取判斷邏輯，透過 `ApiCacheKey.HOME` 實作 DCS 控制的 API 快取優化。

### Repository 層
`HomeRepository` 直接繼承 `BaseApiRepository`，統一透過 `safeApiCall { }` 包裝 API 呼叫做錯誤處理，回傳 `Flow<ApiResult<T>>`。同時整合 DCS 設定取得（主題分類、促銷廣告）與一般 API 呼叫（首頁資料、近期商品等）。

### API 層
主要 Endpoint：

| 方法 | 路徑 | 用途 |
|------|------|------|
| GET | `v3/home` | 首頁主資料（Banner、分類、首購等） |
| POST | `v3/home/waterfall_list` | 瀑布流商品列表（分頁） |
| GET | `v3/home/waterfall_filter` | 瀑布流目的地篩選選項 |
| GET | `v3/recommend/home/history` | 近期瀏覽商品 |
| GET | `v2/retargeting/bar` | 即將出發訂單（最新一筆） |
| GET | `v2/retargeting/cross-sell-banner` | 交叉銷售 Banner |
| GET | `v2/retargeting/cohort-coupon/banner` | Cohort 優惠券 Banner |
| GET | `v2/retargeting/cohort-coupon/bottom-sheet` | Cohort 優惠券底單 |

---

## View 方法清單

> `HomeV2Fragment.kt`

| 方法 | 說明 |
|------|------|
| `onCreateView()` | 初始化 ComposeView，設定 HomeScreen 與所有點擊事件 Listener，啟動 Currency 設定與搜尋關鍵字載入 |
| `onViewCreated()` | 監聽 KKEventBus 系統升級事件，並在已登入時更新 DeepLink helper 狀態 |
| `onResume()` | 觸發 `homeVM.onHomeResumed()`，刷新繼續搜尋關鍵字（含防抖） |
| `onStop()` | 關閉 Loyalty 通知 Dialog，避免背景殘留 |
| `observeHomeSingleEvent()` | 收集 `HomeUiEvent`：路由至 Cohort 優惠券底單、無效優惠券 Dialog、Loyalty 升級通知、App 存取權限彈窗 |
| `onCartClickListener()` | 點擊購物車 icon → 開啟 `CartActivity` |
| `onClickThemeCategoryListener(dcsThemeCategory)` | 點擊主題分類：有子標籤→`ThemeSubTagsFragment`；飯店分類→`HotelCategoryRouter`；其他→`CategoryPage` 或 DeepLink |
| `onClickFirstPurchaseCouponListener()` | 點擊首購優惠券 Banner：已登入→呼叫 `homeVM.acquireCoupon()`；未登入→記錄 pending 並導向登入 |
| `onNotificationClickListener()` | 點擊通知 icon → 開啟通知頁，返回後刷新未讀 Marketplace 訊息 |
| `onMapClickListener()` | 點擊地圖 icon → 開啟地圖搜尋 WebView，並送出 KTM 點擊事件 |
| `onUpcomingOrderClickListener(orderMid)` | 點擊即將出發訂單卡片 → 開啟訂單詳情頁 |
| `onContinueSearchClickListener(keyword)` | 點擊繼續搜尋標籤 → 直接跳轉搜尋結果頁（不經過搜尋中繼頁） |
| `onClickFABListener()` | 點擊浮動促銷按鈕 → 開啟促銷 WebView，送出 KKTrack 點擊事件 |
| `setOnClickSearchBarListener(listener)` | 由外部 Activity 注入搜尋 Bar 點擊回調 |
| `setOnClickSearchIconListener(listener)` | 由外部 Activity 注入搜尋 Icon 點擊回調 |
| `showCouponBottomSheet(cohortBottomSheet, trigger)` | 啟動 `CouponBottomSheetActivity` 顯示 Cohort 優惠券底單 |
| `showCouponInvalidDialog()` | 顯示優惠券無效 Dialog（`CouponInvalidDialogFragment`） |
| `showPermissionDialogFragment(content)` | 顯示 App 存取權限聲明彈窗，確認後呼叫 `homeVM.setAccessPermissionStatement()` |
| `loyaltyNoticeDialogViewListener(id)` | Loyalty Dialog 曝光時送出追蹤事件 |
| `loyaltyNoticeDialogClickListener(id, action)` | Loyalty Dialog 點擊時送出追蹤事件 |
| `goToWebView(url)` | 開啟 `KKdayWebActivity`（內部工具方法） |

---

## ViewModel 方法清單

> `HomeViewModelV2.kt`

| 方法 | 說明 |
|------|------|
| `init` | 依序啟動 11 項並行資料載入：主題分類、近期商品、首頁資料、即將出發訂單、頁尾文字、促銷 FAB、通知未讀數、購物車數、Loyalty 檢查、存取權限聲明、隱私政策、Waterfall 篩選、繼續搜尋關鍵字 |
| `acquireCoupon()` | 呼叫 API 領取首購優惠券；成功→隱藏 Banner 並記錄 `memberUuid`；失敗→發出錯誤事件，CN38/CN29 同樣隱藏 Banner |
| `getCohortCoupons(trigger)` | 取得 Cohort 優惠券底單資料，有效則發出 `ShowCohortBottomSheet` 事件，否則發出 `ShowInvalidCohort` |
| `onCouponBannerExpireListener()` | 優惠券 Banner 計時器到期 → 清除 `couponBanner` 狀態並發出 `ShowInvalidCohort` 事件 |
| `getCartProdCount()` | 取得購物車商品數量，更新 `uiState.cartCount` |
| `setConfirmPolicy()` | 儲存隱私政策確認狀態，並重讀同步更新 `uiState.hasConfirmedPolicy` |
| `setAccessPermissionStatement()` | 記錄使用者已確認 App 存取權限聲明 |
| `updateFilter(waterfallDestination, filterIndex)` | 更新 Waterfall 目的地篩選選中項，觸發 `_filter` 變更進而重新載入瀑布流 |
| `fetchContinueSearchKeywords()` | 合併搜尋歷史（最多 3 筆）與推薦關鍵字 API，更新 `continueSearchKeywords`；30 秒防抖避免重複呼叫 |
| `setSystemUpgrade(isShow, systemUpgrade)` | 控制系統升級遮蓋頁顯示狀態（由 KKEventBus 觸發） |
| `onHomeResumed()` | Fragment `onResume` 回調：觸發繼續搜尋刷新 + 檢查登入後 pending 首購領取 |
| `refreshUnreadMarketplaceMessage()` | 強制刷新未讀通知角標（通知頁返回時呼叫） |
| `getProductCategoryUrl()` | 從 DataStore 讀取商品分類 URL Mapping（供 Fragment 點擊主題分類時使用） |
| `shouldShowFirstPurchaseBanner(firstPurchase)` | 判斷是否應顯示首購優惠 Banner（委派 UseCase 判斷邏輯） |
| *(private) `getHomeData()`* | 取得首頁主資料，處理 Success / Error / Upgrade 三種 ApiResult |
| *(private) `getThemeCategories()`* | 取得 DCS 主題分類列表，更新 `themeCategories` |
| *(private) `getHistoryProduct()`* | 取得近期瀏覽商品，更新 `recentlyViewedProducts` |
| *(private) `getUpcomingOrder()`* | 取得即將出發訂單 + 交叉銷售 Banner；若系統判定需觸發 Cohort 底單則自動呼叫 |
| *(private) `getFooterString()`* | 取得頁尾文字（DCS 設定），更新 `footerString` |
| *(private) `getHomeFab()`* | 取得浮動促銷按鈕設定（DCS），更新 `promoFab` |
| *(private) `getUnreadNotificationCountChange()`* | 訂閱通知未讀數變化，更新 `hasUnreadNotification` |
| *(private) `getConfirmPolicy()`* | 讀取隱私政策確認狀態，更新 `hasConfirmedPolicy` |
| *(private) `checkLoyaltyNotice()`* | 首次登入後檢查 Loyalty 資格，符合則發出 `ShowLoyaltyDialog` 事件並標記已檢查 |
| *(private) `checkAccessPermissionStatement()`* | 確認是否需要顯示存取權限聲明彈窗，有內容則發出 `ShowPermissionDialogFragment` 事件 |
| *(private) `getWaterfallFilter()`* | 取得 Waterfall 目的地篩選選項，自動在首位插入「推薦」預設選項 |
| *(private) `checkPendingFirstPurchaseClaim()`* | 已登入 + 有 pending 紀錄時，自動觸發首購優惠券領取（登入返回首頁場景） |

---

## 業務邏輯摘要

- **首購優惠券**：`firstPurchase.isShow` 控制顯示，領取後本地記錄 `memberUuid` 避免重複顯示
- **Waterfall 分頁**：以 `destination`（目的地）篩選 + 已曝光商品 impression 作為請求參數，切換篩選時用 `flatMapLatest` 取消上一頁請求
- **繼續搜尋關鍵字**：30 秒防抖，避免 Tab 切換時重複呼叫
- **API 快取**：DCS 控制的 `ApiCacheKey.HOME` 快取策略，由 `AppRepository.getHomeCacheOptimizeEnable()` 開關
- **網路狀態**：`NetworkMonitor` 提供即時網路狀態 `StateFlow`，斷線時顯示提示
- **Loyalty 通知**：首次登入後檢查 Loyalty 會員資格，顯示通知 Dialog
- **隱私政策**：`hasConfirmedPolicy` 控制是否顯示隱私政策確認彈窗
- **錯誤處理**：`ApiResult.Error` 更新 `apiError`；`ApiResult.Success` 時清除錯誤狀態

---

## 已知技術債

- **UseCase 位置錯誤**：所有 UseCase 放在 `:app` 的 `view/homeV2/useCase/` 下，應位於 `:domain:usecase` 模組
- **UseCase 使用 @Single 而非 @Factory**：`HomeUseCases` 及子 UseCase 均標記 `@Single`，語意上 UseCase 應為 `@Factory`（每次注入新實例）
- **HomeRepository 無介面分離**：直接繼承 `BaseApiRepository`，未實作 `:domain:contract` 介面，ViewModel 透過 UseCase 耦合具體實作
- **UseCase 直接依賴 Data 層**：`GetHomeDataUseCase` import `com.kkday.home_page.data.repository.HomeRepository`（Data 層），違反 Clean Architecture 依賴方向

## 相關筆記
- [02-modules](../02-modules.md)
- [03-ui-patterns](../03-ui-patterns.md)
- [05-networking](../05-networking.md)
- [06-data-layer](../06-data-layer.md)
- [07-concurrency](../07-concurrency.md)
- [deals](deals.md)
- [explore](explore.md)
- [order-detail-compose](order-detail-compose.md)
- [sku-activity-shell](sku-activity-shell.md)
- [trans-home](trans-home.md)

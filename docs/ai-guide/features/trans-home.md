# 交通首頁 技術文件

> 自動產生 | 最後更新：2026-03-19

---

## 概述

- **所在 Module**：`:app`
- **UI 入口**：`TransHomeActivity.kt`
- **功能描述**：交通服務總入口頁面，以主 Tab（鐵路、巴士、租車、機票、遊輪、機場接送）分類，並透過子 Tab 切換各交通服務（台灣高鐵、JR、歐洲鐵路、高速巴士、港珠澳巴士、越南巴士、租車、機票、遊輪、機場接送等），並顯示各服務的 Banner 圖與搜尋入口。

---

## 檔案清單

```
UI（使用者介面入口）
 ├─ TransHomeActivity.kt          → app/src/main/java/com/kkday/member/view/transportation/home/
 ├─ TransHomeMainFragment.kt      → app/src/main/java/com/kkday/member/view/transportation/home/
 ├─ TransHomeMainTabAdapter.kt    → app/src/main/java/com/kkday/member/view/transportation/home/
 ├─ TransHomeSubTabDialog.kt      → app/src/main/java/com/kkday/member/view/transportation/home/dialog/
 ├─ TransHomeSubTabAdapter.kt     → app/src/main/java/com/kkday/member/view/transportation/home/dialog/
 └─ 各子頁面 Fragment（TransHomeThsrtwFragment、TransHomeJRFragment 等）
    → app/src/main/java/com/kkday/member/view/transportation/home/subpage/

ViewModel（UI 狀態管理）
 ├─ TransHomeViewModel.kt         → app/src/main/java/com/kkday/member/view/transportation/home/
 │   （Activity 層：提供地點搜尋、Banner 載入輔助方法，供子頁面共用）
 └─ TransHomeMainViewModel.kt     → app/src/main/java/com/kkday/member/view/transportation/home/
     （Fragment 層：主 Tab / 子 Tab 狀態管理、頁面載入主邏輯）

其他子頁面 ViewModel（各服務）
 ├─ TransHomeAirportViewModel.kt  → app/src/main/java/com/kkday/member/view/transportation/home/subpage/viewmodel/
 ├─ TransHomeCruisesViewModel.kt  → app/src/main/java/com/kkday/member/view/transportation/home/subpage/viewmodel/
 ├─ TransHomeDropoffViewModel.kt  → app/src/main/java/com/kkday/member/view/transportation/home/subpage/viewmodel/
 ├─ TransHomeJRViewModel.kt       → app/src/main/java/com/kkday/member/view/transportation/home/subpage/viewmodel/
 └─ TransHomePickupViewModel.kt   → app/src/main/java/com/kkday/member/view/transportation/home/subpage/viewmodel/

Domain（業務邏輯）
 └─ 無專屬 UseCase（技術債：ViewModel 直接依賴 Repository）
    補充：TransGetMinPriceUseCase、TransGetRecommendRoutesUseCase 存在於
    app/src/main/java/com/kkday/member/view/buslist/home/TransHomeUseCase.kt
    但僅供巴士列表子頁面使用，不屬於首頁主流程。

Data（資料層）
 └─ TransportationRepository.kt（實作，無 domain/contract 介面）
    → app/src/main/java/com/kkday/member/view/transportation/repository/

Network（API 定義）
 ├─ ITransportationApiService.kt  → libs/networking/api/src/main/java/com/kkday/library/networking/service/transportation/
 └─ 主要 Response Model（TransTopic、TransBanners 等）
    → libs/networking/api/src/main/java/com/kkday/library/networking/resource/transportation/

輔助資料結構
 ├─ TransHomeArgument.kt          → app/src/.../view/transportation/home/（sealed class，各服務的傳參類型）
 ├─ TransHomeMainTab.kt           → app/src/.../view/transportation/home/（主 Tab enum）
 └─ TransHomeArgumentHelper.kt    → app/src/.../view/transportation/home/（URL 解析 helper）
```

---

## 資料流

### 主流程：頁面載入 → 取得交通主題 Topics

```
UI（TransHomeActivity）
 │  onCreate() → launchHomeOrSearchResultPage()
 │  commit TransHomeMainFragment
 ↓
UI（TransHomeMainFragment）
 │  onViewCreated() → initObserver()
 │  觀察 viewModel.stateFlow
 ↓
ViewModel（TransHomeMainViewModel）
 │  init{} → getTransInfoApis() + getTransBanners(各服務) + trackKTMbyInitArgs()
 │  呼叫：transportationRepository.getTransTopics(platform)
 │  呼叫：transportationRepository.getTransBannerProducts(urlPathKey, currency, version?)
 ↓
Repository（TransportationRepository）
 │  呼叫：kkApi.b2cApi.transportation.getTransTopics(platform)
 │  呼叫：kkApi.b2cApi.transportation.getTransBannerProducts(urlPathKey, currency, version)
 ↓
API Service（ITransportationApiService）
 │  GET v2/trans/topics?platform=android
 │  GET v2/trans/banner_products?url_path_key=...&currency=...&version=...
 ↓
後端 API
```

### 回傳流

```
後端 API
 ↓
Repository（TransportationRepository）
 │  safeApiCall { apiResultData(...) } 包裝為 ApiResult
 ↓
ViewModel（TransHomeMainViewModel）
 │  getTransInfoApisSuccess() → 解析 TransMainTopic 列表
 │  建立 mainTabs、更新 argumentMap、更新 _stateFlow
 │  getTransBanners 回傳後更新 bannerMap 與 _stateFlow.currentTransBanners
 ↓
UI（TransHomeMainFragment）
 │  stateFlow.collect → mainTabAdapter.submitList()
 │  updateViewPager() → 依子 Topic 建立各服務 Fragment
 │  updateSubTab() → 更新子 Tab 清單
 └─ setServiceBanner() → 用 Glide 顯示 Banner 圖
```

---

## 逐層說明

### UI 層

`TransHomeActivity` 是整個交通服務的容器 Activity，以 `@Router(KRouterConst.PAGE_TRANS_HOME_PAGE)` 標記，支援 URL Routing 進入。`onCreate()` 時呼叫 `RouterHelper.inject(this)` 解析 RouterParam（`isNeedGoHomePage`、`productId`、`transportationAirport`）後，呼叫 `launchHomeOrSearchResultPage()` 決定載入首頁（`TransHomeMainFragment`）或直接跳轉搜尋結果頁。

Activity 同時持有各子服務的 ViewModel（`CnhkBusViewModel`、`BusListViewModel`、`ZzimAirViewModel` 等），並透過 `initObservers()` 統一監聽各子服務的登入需求、預訂頁跳轉等事件，再於 Activity 層執行 Fragment replace 操作。

整合 QueueIt 排隊機制（`QueueItActivityDelegate`），在 `onQueuePassed()` 後才實際載入頁面。

`TransHomeMainFragment` 是首頁主體，使用 RecyclerView（橫向主 Tab）+ ViewPager2（子頁面）+ TabLayout（子 Tab）三層結構展示各交通服務入口。

### ViewModel 層

**`TransHomeMainViewModel`**：頁面主狀態管理，以 `MutableStateFlow<ViewState>` 維持狀態：
- `currentHomeMainTab`：目前選中的主 Tab（RAILWAY/BUS/CAR_RENTAL/AIRPLANE/CRUISES/AIRPORT_TRANSFER）
- `transHomeMainTabItems`：主 Tab 清單（含選中狀態）
- `currentSubTopicList`：目前主 Tab 下的子 Topic 清單
- `currentSubTopicArguments`：子 Topic 對應的 `TransHomeArgument` 清單
- `currentArgument`：目前選中子頁面的 `TransHomeArgument`
- `currentTransBanners`：目前服務的 Banner 清單

`init{}` 並行發起所有服務的 Banner 請求（14 個服務）及 Topics 請求。Topics 回傳後呼叫 `getTransInfoApisSuccess()` 完成狀態初始化，並啟動 `handleIntent()` 與 `handleFlow()` 開始監聽 UI 意圖與狀態變化。

透過 `MutableSharedFlow<ViewIntent>` 接收 UI 意圖（`SetMainTab`、`ConvertArgumentFromCurrentSubTopic`）並觸發狀態更新。

**`TransHomeViewModel`**：Activity 層輔助 ViewModel，提供 `searchLocationFilter()`（地點搜尋）、`getTransSearchLocationAreaList()`、`getTransBanners()` 等方法，供各子頁面在 Activity 生命週期內共用。

### UseCase 層

主流程**無專屬 UseCase 抽象層**，`TransHomeMainViewModel` 直接依賴 `TransportationRepository`（技術債）。唯收藏功能透過標準 UseCase：
- `AddWishProductUseCase`：新增收藏
- `DeleteWishProductUseCase`：移除收藏

### Repository 層

`TransportationRepository` 繼承 `BaseApiRepository`，直接封裝 `KKApi` 呼叫，**無 domain/contract 介面**（技術債）。

首頁主要使用的兩個方法：
- `getTransTopics(platform: String)`：取得交通主題列表（TransTopic），含主 Tab 與子 Tab 結構
- `getTransBannerProducts(urlPathKey, currency, version?)`：取得指定服務的 Banner 商品列表

兩者均透過 `safeApiCall { apiResultData(...) }` 包裝，回傳 Flow。

### API 層

`ITransportationApiService`（Retrofit interface）中與首頁相關的端點：

| HTTP 方法 | Endpoint | 說明 |
|-----------|----------|------|
| GET | `v2/trans/topics` | 取得交通服務主題列表（主 Tab + 子 Tab 結構）|
| GET | `v2/trans/banner_products` | 取得指定服務 Banner 商品（依 `url_path_key` 區分服務）|

`getTransTopics` Request：`platform=android`

`getTransBannerProducts` Request：`url_path_key`（服務路徑鍵）、`currency`（幣別）、`version`（可選，部分服務如 JR 使用 v2）

---

## View 方法清單

### TransHomeActivity

| 方法 | 說明 |
|------|------|
| `onCreate()` | 初始化狀態列、QueueIt 觀察者、各子服務 Observer；解析 RouterParam |
| `onNewIntent()` | 處理 URL 再進入時的頁面重新載入 |
| `onQueuePassed()` | QueueIt 排隊通過後，觸發 `launchHomeOrSearchResultPage()` |
| `getViewBinding()` | 回傳 `ActivityTransHomeBinding` |
| `initStatusBar()` | 設定透明狀態列、edge-to-edge 顯示、處理 Android 15+ 虛擬導航列 |
| `initObservers()` | 統一初始化各子服務（CNHK巴士、高速巴士、ZzimAir 等）的 Observer |
| `initCnhkbusObserver()` ~ `initAirportObserver()` | 各子服務登入需求監聽 |
| `launchHomeOrSearchResultPage()` | 依 `TransHomeArgument.isGoToResultPage` 決定載入首頁或直接到搜尋結果 |
| `launchCnhkBusBookingPage()` 等各 `launch*Page()` | 各服務預訂/搜尋頁面的 Fragment replace 操作 |
| `getArgTransHomeArgument()` | 解析傳入的 `TransHomeArgument`（含 URL 查詢參數、productId 解析）|

### TransHomeMainFragment

| 方法 | 說明 |
|------|------|
| `onViewCreated()` | 初始化 Toolbar、主 Tab RecyclerView、子 Tab、ViewPager2、Observer |
| `onDestroyView()` | 移除 ViewPager GlobalLayoutListener、清除模糊效果 |
| `onDestroy()` | 解除 TabLayoutMediator |
| `initToolBar()` | 設定 Toolbar padding（含 StatusBar 高度）、返回鍵 |
| `initMainTabRecyclerView()` | 設定橫向主 Tab RecyclerView |
| `initSubTab()` | 監聽子 Tab 選擇，發出 `ViewIntent.ConvertArgumentFromCurrentSubTopic` |
| `initViewPager2()` | 設定 ViewPager2（停用手勢滑動）、綁定 GlobalLayoutListener |
| `initObserver()` | 訂閱 stateFlow：主 Tab 更新、Banner 更新、當前 Argument 更新 |
| `setServiceBanner()` | 以 Glide 顯示遠端 Banner 或預設本地圖 |
| `updateViewPager()` | 依子 Topic 建立各服務 Fragment，重建 ViewPager2 Adapter 與 TabLayoutMediator |
| `updateSubTab()` | 設定子 Tab「查看全部」按鈕，點擊開啟 `TransHomeSubTabDialog` |
| `getTabFragmentsCreators()` | 依 `TransHomeArgument` 類型建立對應子頁面 Fragment |
| `setSubPageFromSubTabDialog()` | 從 SubTabDialog 選擇後，更新 TabLayout 選中項 |
| `sendViewIntent()` | 發送 `ViewIntent` 給 ViewModel |
| `getCoverResUri()` | 從 Banner 清單取出 `COVER_PHOTO` 類型的圖片 URL |
| `getArgTransHomeArgument()` | 從 Fragment arguments 取得 `TransHomeArgument` |
| `updateViewPagerHeightIfNeeded()` | 依當前子頁面內容高度動態調整 ViewPager 高度（wrap_content 效果）|

---

## ViewModel 方法清單

### TransHomeMainViewModel

| 方法 | 說明 |
|------|------|
| `init` | 並行發起 14 個服務的 Banner 請求、1 個 Topics 請求；送出 KTM 初始追蹤 |
| `sendViewIntent()` | 將 `ViewIntent` emit 到 SharedFlow，觸發 `handleIntent()` 處理 |
| `handleIntent()` | 收集 `_intentFLow`，分發至 `setMainTab()` 或 `convertArgumentFromCurrentSubTopic()` |
| `handleFlow()` | 啟動 `updateMainTabItemsAndSubTab()` 監聽主 Tab 狀態變化 |
| `updateMainTabItemsAndSubTab()` | 依目前主 Tab 重新計算 Tab Items 清單與子 Topic/Argument 清單，更新 stateFlow |
| `getTransInfoApis()` | 呼叫 Repository 取得 Topics，成功後呼叫 `getTransInfoApisSuccess()` |
| `getTransInfoApisSuccess()` | 整合 Topics 資料、初始化 argumentMap 與 mainTabs、更新 stateFlow |
| `getTransBanners()` | 呼叫 Repository 取得指定服務的 Banner，快取至 bannerMap |
| `setMainTab()` | 更新 stateFlow 的 `currentHomeMainTab`，並送出 KTM 租車/機票追蹤事件 |
| `convertArgumentFromCurrentSubTopic()` | 依子 Tab 位置找到對應 Argument，更新 stateFlow（含 Banner 切換）|
| `addWishProduct()` | 呼叫 `AddWishProductUseCase`，同步透過 EventBus 更新收藏狀態 |
| `removeWishProduct()` | 呼叫 `DeleteWishProductUseCase`，同步透過 EventBus 更新收藏狀態 |
| `trackKTMbyInitArgs()` | 依初始進入的服務類型，送出 KTM 頁面瀏覽追蹤 |
| `trackKTMPageView()` | 封裝 KTMTracker.trackEvent()，加入 500ms 去抖動防止初始化重複觸發 |

### TransHomeViewModel（Activity 層）

| 方法 | 說明 |
|------|------|
| `searchLocationFilter()` | 依 `TransHomeArgument` 類型取得對應服務名稱，呼叫 Repository 查詢地點 |
| `getTransSearchLocationAreaList()` | 查詢交通地點區域列表，供地點選擇頁使用 |
| `getTransBanners()` | 供子頁面 Fragment 單次取得 Banner，回傳 `List<TransBanners>?` |

---

## 業務邏輯摘要

- **主 Tab 結構由後端決定**：`getTransTopics()` 回傳的 `TransMainTopic` 決定顯示哪些主 Tab 與子 Tab（並非 hardcode 全部顯示），`TransHomeMainTab.getTransHomeMainTabs()` 提供前端所有可能的 Tab 定義，取交集後顯示。
- **子 Tab 以 URL 驅動**：每個子 Topic 含 `mobilePageUrl`，透過 `TransHomeArgument.createTransHomeArgument(url)` 解析為對應的服務類型（Sealed Class），再根據類型建立對應的子頁面 Fragment。
- **Banner 預先並行載入**：初始化時對所有 14 個服務並行請求 Banner，快取於 `bannerMap`，切換服務時立即顯示（無需等待）；遠端 Banner 優先，若無則顯示本地 drawable 作為 fallback。
- **QueueIt 整合**：進入頁面前須通過 QueueIt 排隊檢查（`QueueWaitingRoom.APP_p2phomepage`），`onQueuePassed()` 後才真正載入頁面。
- **登入導向由 Activity 統一處理**：各子服務 ViewModel 發出 `NeedLogin` 狀態，由 `TransHomeActivity` 攔截並導向登入頁（`ActivityResultLauncher` 模式），登入成功後繼續原本操作。
- **ViewPager 高度動態調整**：`updateViewPagerHeightIfNeeded()` 監聽 ViewPager 子頁面佈局，動態更新高度以實現 wrap_content 效果（ScrollView 內使用）。
- **KTM 追蹤**：進入頁面及切換 Tab 時送出 KTM 分析事件（`CarRentalsPg`、`FlightPg`、`VacationPg`），初始化時設定 500ms debounce 防止重複計數。

---

## 已知技術債

- `TransportationRepository` 直接放置於 `app/src/main/.../view/transportation/repository/`，未建立 `domain/contract` 介面，ViewModel 直接依賴實作類別，不符合 Clean Architecture 的依賴反轉原則。
- `TransHomeMainViewModel` 與 `TransHomeViewModel` 直接依賴 `TransportationRepository`，缺少 UseCase 抽象層。
- `TransHomeUseCase.kt`（`TransGetMinPriceUseCase`、`TransGetRecommendRoutesUseCase`）位於 `view/buslist/home/` 路徑下，直接硬編碼了 `TransApiRepository(NetworkApi.sharedInstance())`（靜態依賴），不符合 Koin 注入慣例。
- `TransHomeMainFragment` 直接透過 `inject<TransportationRepository>()` 取得 Repository，未經 ViewModel 封裝，Layer 邊界不清晰。

## 相關筆記
- [01-architecture](../01-architecture.md)
- [02-modules](../02-modules.md)
- [03-ui-patterns](../03-ui-patterns.md)
- [05-networking](../05-networking.md)
- [06-data-layer](../06-data-layer.md)
- [07-concurrency](../07-concurrency.md)
- [home](home.md)
- [order-detail-compose](order-detail-compose.md)
- [sku-activity-shell](sku-activity-shell.md)

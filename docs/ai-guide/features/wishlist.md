# 願望清單（Compose）技術文件

> 自動產生 | 最後更新：2026-03-19

---

## 概述

- **所在 Module**：`:app`（UI + ViewModel + GetWishProdsUseCase + WishRepository）、`:feature:product_core`（AddWish/DeleteWish UseCase）
- **UI 入口**：`WishComposeFragment.kt`
- **功能描述**：以 Jetpack Compose 實作的收藏（Wishlist）頁面，讓使用者瀏覽與管理已收藏的商品；支援未登入本地收藏與登入後遠端同步兩種情境。

---

## 檔案清單

```
UI（使用者介面入口）
 ├─ WishComposeFragment.kt（Fragment 殼）  → app/.../view/wish/
 └─ WishScreen.kt（Compose 主畫面）        → app/.../view/wish/

ViewModel（UI 狀態管理）
 └─ WishViewModel.kt                       → app/.../view/wish/

Domain（業務邏輯 UseCase）
 ├─ GetWishProdsUseCase.kt                 → app/.../view/wish/（技術債：應在 domain/usecase/）
 ├─ AddWishProductUseCase.kt               → libs/feature/product_core/.../domain/useCase/
 └─ DeleteWishProductUseCase.kt            → libs/feature/product_core/.../domain/useCase/

Data（資料層介面與實作）
 ├─ WishProductRepository.kt（介面）       → libs/feature/product_core/.../domain/repository/
 ├─ WishProductRepositoryImpl.kt           → libs/feature/product_core/.../data/repository/
 └─ WishRepository.kt（讀取用）            → app/.../view/wish/（技術債：未實作 domain 介面）

Network（API 定義）
 ├─ IWishApiService.kt                     → libs/networking/api/.../service/wish/
 └─ WishApiService.kt                      → libs/networking/api/.../service/wish/

狀態
 └─ WishUiState.kt                         → app/.../view/wish/

舊版（Reductor 架構，保留中）
 ├─ WishActivity.kt / WishFragment.kt      → app/.../view/wish/
 ├─ WishPresenter.kt                       → app/.../view/wish/
 ├─ WishReducer.kt                         → app/.../reducer/wish/
 └─ WishActions.kt                         → app/.../reducer/wish/
```

---

## 資料流

### 主流程：頁面載入 / 取得收藏清單

```
UI（WishComposeFragment → WishScreen）
 │  Fragment 建立 ComposeView，WishScreen 透過 koinViewModel() 取得 WishViewModel
 │  ViewModel.init 自動呼叫：loadWishList()
 ↓
ViewModel（WishViewModel）
 │  更新狀態：isLoading = true
 │  呼叫：getWishProdsUseCase.invoke()
 ↓
UseCase（GetWishProdsUseCase）
 │  業務規則：合併本地 wishIds（PersistentManager）與遠端 wishIds（登入後才取）
 │  若未登入：僅使用本地 wishIds
 │  若已登入：呼叫 wishRepository.getWishIds()，合併去重
 │  若 uniqueIds 為空：直接回傳 flowOf()，不繼續呼叫 API
 │  呼叫：wishRepository.getWishProds(uniqueIds)
 ↓
Repository（WishRepository）
 │  getWishIds()  → kkApi.b2cApi.wish.getWishIds(start, count)
 │  getWishProds() → safeApiCall { kkApi.b2cApi.wish.getWishProds(productIds) }
 ↓
API（IWishApiService）
 │  GET  v2/wish_lists/id?start=0&count={limit}
 │  POST v3/search/product/ids  body: { prod_mids: [...] }
 ↓
後端 API
```

### 回傳流

```
後端 API
 │  GET  → WishIdsData（wishIds: List<WishInfo>）
 │  POST → SearchProductResult（prods: List<B2CProductCardData>）
 ↓
Repository（WishRepository）
 │  safeApiCall 包裝，回傳 ApiResult<SearchProductResult>
 │  錯誤以 catch(Exception) 靜默處理，回傳 flowOf()
 ↓
UseCase（GetWishProdsUseCase）
 │  本地 ids + 遠端 ids → distinct → uniqueIds
 ↓
ViewModel（WishViewModel）
 │  ApiResult.Success → _uiState.copy(products = prods, isLoading = false)
 │  ApiResult.Loading → isLoading = true（注意：此分支有 bug，未 assign 回 _uiState）
 │  else             → isLoading = false
 ↓
UI（WishScreen）
 │  collectAsState() 觀察 uiState
 └─ products 非空：顯示 WishList（LazyColumn + LargeProductCard）
    products 為空：顯示 WishEmptyScreen（空狀態插圖）
    isLoading：顯示 WishListLoadingScreen（Shimmer 動畫）
```

### 收藏/取消收藏流程

```
UI（WishScreen → WishList → LargeProductCard.onWishClick）
 │  isWish = true  → vm.removeProdFromWishList(prod)
 │  isWish = false → vm.addProdToWishList(prod)
 ↓
ViewModel（WishViewModel）
 │  樂觀更新：立即修改 _uiState.products
 │  發送 KKEventBus.WishProduct 事件通知其他頁面同步
 │  呼叫 AddWishProductUseCase / DeleteWishProductUseCase
 ↓
UseCase（AddWishProductUseCase / DeleteWishProductUseCase）
 │  更新 PersistentManager 本地快取
 │  更新 AppSharedData.wishInfos
 │  觸發埋點：OldKKEventTracker、KKTrackTool、KTMTracker
 │  若已登入：呼叫 WishProductRepository.addWishProduct() / deleteWishProduct()
 ↓
Repository（WishProductRepositoryImpl）
 │  呼叫 ProductApiService.addWishProduct() / deleteWishProduct()
 │  錯誤以空 catch 靜默吞噬
```

---

## 逐層說明

### UI 層

`WishComposeFragment` 只負責建立 `ComposeView` 並設定 `ViewCompositionStrategy.DisposeOnViewTreeLifecycleDestroyed`，實際 UI 邏輯全在 `WishScreen`。`WishScreen` 以 `koinViewModel()` 注入 `WishViewModel`，用 `collectAsState()` 訂閱 `uiState`，根據 `isEmpty`、`isLoading` 三元切換畫面。`WishList` 中每個 item 在 Composition 時立即呼叫 `RxEventTracker.prodCardViewed()` 觸發曝光埋點（注意：此方式在 recomposition 時可能重複觸發）。商品點擊透過 `IProductPageLaunchHelper` 跳轉商品詳情頁。

### ViewModel 層

`@KoinViewModel`，以 `MutableStateFlow<WishUiState>` 管理狀態。`init` 自動呼叫 `loadWishList()`。新增/移除時採樂觀更新（先更新 UI，再呼叫 API），並透過 `KKEventBus` 廣播 `WishProduct` 事件，讓其他頁面（如首頁、搜尋結果）的心願標記同步更新。

### UseCase 層

`GetWishProdsUseCase` 標記為 `@Single`（應為 `@Factory`）且位於 `app/.../view/wish/`（應在 `domain/usecase/`），均為技術債。核心邏輯：本地 ids（PersistentManager）與遠端 ids（已登入時才呼叫）合併去重，確保未登入情境也能顯示本地收藏。

`AddWishProductUseCase` / `DeleteWishProductUseCase` 位於 `:feature:product_core`，除呼叫 API 外，同時負責：(1) 更新本地 PersistentManager 快取、(2) 觸發三套埋點系統（OldKKEventTracker、KKTrackTool、KTMTracker），職責偏重。

### Repository 層

`WishRepository` 直接封裝 `KKApi`，未實作 `domain/contract` 介面（技術債）。`getWishIds()` 無快取；`getWishProds()` 以 `safeApiCall` 包裝，錯誤以空 catch 靜默處理。`WishProductRepositoryImpl` 實作 `WishProductRepository` 介面，呼叫 `ProductApiService`，新增/刪除錯誤均靜默忽略。

### API 層

`IWishApiService` 定義兩個端點：

| 端點 | 說明 |
|------|------|
| `GET v2/wish_lists/id?start=0&count={limit}` | 取得遠端收藏 ID 列表，支援分頁 |
| `POST v3/search/product/ids` body: `{ prod_mids: [...] }` | 依商品 ID 批次查詢商品資料 |

---

## View（Compose）方法清單

| Composable / 方法 | 說明 |
|------------------|------|
| `WishScreen()` | 主畫面，注入 ViewModel，根據狀態切換三種子畫面 |
| `WishList()` | 有商品時的列表，LazyColumn + LargeProductCard |
| `WishEmptyScreen()` | 無商品時的空狀態畫面（插圖 + 文字） |
| `WishListLoadingScreen()` | 載入中的 Shimmer 骨架屏（3 個佔位 item） |
| `WishListLoadingItem()` | 單一 Shimmer 佔位元件 |
| `Modifier.shimmerEffect()` | 自訂 Modifier，實作無限循環的線性漸層動畫 |
| `onBackClickListener()` | Fragment 層，處理返回鍵（finish Activity） |

## ViewModel 方法清單

| 方法 | 說明 |
|------|------|
| `init` | 頁面初始化時自動呼叫 `loadWishList()` |
| `loadWishList()` | 呼叫 `GetWishProdsUseCase`，依結果更新 `_uiState` |
| `addProdToWishList(product)` | 樂觀新增商品至清單，呼叫 `AddWishProductUseCase`，發送 EventBus |
| `removeProdFromWishList(product)` | 樂觀移除商品，呼叫 `DeleteWishProductUseCase`，發送 EventBus |

---

## 業務邏輯摘要

- **登入/未登入雙模式**：未登入時僅顯示本地（PersistentManager）儲存的收藏；登入後合併遠端收藏 IDs，確保不遺失。
- **樂觀更新**：新增/移除收藏時先更新 UI，再非同步呼叫 API，提升操作回饋速度。
- **跨頁狀態同步**：透過 `KKEventBus.WishProduct` 事件讓首頁、搜尋結果等其他頁面的愛心圖示即時同步。
- **埋點多系統觸發**：新增/移除收藏會同時觸發 OldKKEventTracker、KKTrackTool、KTMTracker 三套系統，且依 `PageType` 分流不同追蹤事件。
- **錯誤處理**：API 錯誤全數靜默忽略（空 catch），不向使用者顯示錯誤訊息；收藏清單為空時顯示空狀態插圖。
- **曝光埋點**：`WishList` 在每個商品 item 的 Composition 階段呼叫 `prodCardViewed()`，recomposition 時可能重複觸發（潛在問題）。

---

## 已知技術債

- `GetWishProdsUseCase` 位於 `app/.../view/wish/` 而非 `domain/usecase/`，且標記為 `@Single`（應為 `@Factory`）。
- `WishRepository` 未定義 `domain/contract` 介面，直接依賴 `KKApi`，違反 Clean Architecture 分層原則。
- `WishViewModel` 的 `loadWishList()` 中，`ApiResult.Loading` 分支使用 `.copy()` 但未 assign 回 `_uiState`，導致 Loading 狀態無法正確反映（功能性 bug）。
- 舊版 Reductor 架構（`WishActivity`、`WishFragment`、`WishPresenter`、`WishReducer`、`WishActions`）仍保留，與新版 Compose 架構並存，待棄用清理。
- `AddWishProductUseCase` / `DeleteWishProductUseCase` 負責 API 呼叫與埋點兩件事，違反單一職責原則。

## 相關筆記
- [01-architecture](../01-architecture.md)
- [02-modules](../02-modules.md)
- [03-ui-patterns](../03-ui-patterns.md)
- [05-networking](../05-networking.md)
- [06-data-layer](../06-data-layer.md)
- [07-concurrency](../07-concurrency.md)
- [member-profile](member-profile.md)
- [order-detail-compose](order-detail-compose.md)
- [sku-activity-shell](sku-activity-shell.md)

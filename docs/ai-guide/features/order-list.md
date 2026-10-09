# 訂單列表 技術文件

> 自動產生 | 最後更新：2026-03-19

---

## 概述

- **所在 Module**：`:feature:order_page`（`libs/feature/order_page/`）
- **UI 入口**：`OrderComposeFragment.kt`
- **功能描述**：會員訂單列表頁，以 Paging3 分頁載入訂單資料，支援進行中、已完成、已取消三個分頁 Tab，並整合 Marketplace 未讀訊息、推薦商品、及訂單倒數計時等功能。

---

## 檔案清單

```
UI（使用者介面入口）
 ├─ OrderComposeFragment.kt     → libs/feature/order_page/.../presentation/
 └─ OrderListPage.kt（Compose） → libs/feature/order_page/.../presentation/compose/

ViewModel（UI 狀態管理）
 └─ OrderViewModel.kt           → libs/feature/order_page/.../presentation/viewModel/

Domain（Paging3 資料來源）
 └─ NewOrderListSource.kt       → libs/feature/order_page/.../presentation/viewModel/

Data（資料層，介面與實作合一）
 └─ OrderRepository.kt          → libs/feature/order_page/.../domain/repository/

Network（API 定義）
 └─ IOrderApiService.kt         → libs/networking/api/.../service/order_api/
```

---

## 資料流

### 主流程：頁面載入 / Paging3 分頁資料取得

```
UI（OrderComposeFragment → OrderListPage）
 │  content() 呼叫：getVM().getNewOrderListFlow(currentPageCategory, false)
 │                   .collectAsLazyPagingItems()
 │  同時觸發：viewReady() → refreshOrderStatusCount() + trackViewOrderListPg()
 │  觀察：LaunchedEffect(triggerRefresh) → refreshOrder(orderPagingItems)
 ↓
ViewModel（OrderViewModel）
 │  getNewOrderListFlow() 建立 Pager<Int, OrderInfo>
 │  PagingConfig(pageSize = 5, initialLoadSize = 5)
 │  直接依賴 OrderRepository（無 UseCase 層，技術債）
 ↓
PagingSource（NewOrderListSource）
 │  load(params)：nextPage = params.key ?: 1
 │  呼叫：orderRepository.getNewOrderList(category, needOverDateOrder, nextPage, 5)
 │  副流程1（所有頁）：mapOrdersWithMarketplaceData() 注入 unreadMsgCount
 │  副流程2（僅第 1 頁）：handleRecommendOrders() 取推薦商品
 ↓
Repository（OrderRepository）
 │  包裝：safeApiCallFlow { apiResultData(orderService.getNewOrderList(...)) }
 ↓
API Service（IOrderApiService）
 │  GET v2.2/orders
 │  ?category={ON-GOING|BACK|CX}
 │  &need_over_date_order=false
 │  &current_page=1
 │  &page_size=5
 ↓
後端 API
```

### 回傳流

```
後端 API
 │  Response：B2CApiResponse<OrderListData>
 │  OrderListData { orders: List<OrderInfo>, existsOverDateOrder: Boolean }
 ↓
Repository
 │  apiResultData() 解包 → ApiResult.Success<OrderListData>（含 metadata.pagination）
 ↓
PagingSource（NewOrderListSource）
 │  enrichment：注入 unreadMsgCount、recommend 欄位
 │  回傳 LoadResult.Page(data, prevKey, nextKey)
 │  callback：onDataUpdateListener → _orderListFlow.value 更新
 ↓
ViewModel（OrderViewModel）
 │  _orderListFlow: MutableStateFlow<List<OrderInfo>> 更新（副本快取）
 │  orderStatusCountList 由 refreshOrderStatusCount() 獨立維護
 │  mkpConversationInfoList 由 observeUnreadMarketplaceMessage() 維護
 ↓
UI（OrderComposeFragment / OrderListPage）
 │  collectAsLazyPagingItems() 驅動 LazyColumn 渲染訂單卡片
 │  orderListFlow.launchAndCollectIn → 通知 MainActivity
 └─ 成功：LazyColumn 顯示訂單卡片，Tab 顯示未讀/數量角標
    失敗：LoadResult.Error → Paging 錯誤狀態，自動重試最多 3 次（每次間隔 3 秒）
```

---

## 逐層說明

### UI 層

`OrderComposeFragment` 繼承 `BaseComposeFragment<OrderViewModel>`，在 `content()` 中透過 Compose `NavHost` 管理三個路由：`orderListRoute`、`groupOrderRoute`、`orderDetailRoute`。

`OrderListPage.kt` 是主要 Composable，接收 Paging Items 與 ViewModel 狀態，渲染 Tab + LazyColumn。Tab 切換透過 `KKTabs` + `KKViewPager` 實作，切換時呼叫 `orderVM.onClickTab(page)`。

DeepLink 可指定進入特定 Tab（`KEY_DEEP_LINK_ORDER_LIST_CATEGORY`），進入 FAQ 來源可顯示提示 Dialog（14 天冷卻）。

### ViewModel 層

`OrderViewModel` 繼承 `BaseAndroidViewModel`，使用 Compose `mutableStateOf` 管理 UI 狀態（`currentPageCategory`、`showOverDateOrder`、`triggerRefresh` 等），而非 `StateFlow`/`LiveData`。

`init` 並發啟動四項背景任務：
- `observeUnreadMarketplaceMessage()`：監聽 Marketplace 未讀數
- `observeOrderCommentFlow()`：監聽評論更新
- `observeLoadState()`：5 秒後檢查資料，若空則自動重試（最多 3 次）
- `loadDcsConfiguration()`：從 DCS 載入 `hide_order_list_contact_button` 設定

`ButtonUiState` 封裝訂單卡片所有互動按鈕的回呼（聯絡客服、憑證、評論、司機聯絡、再訂一次、修改、補繳款）。

### UseCase 層

**無 UseCase 層**，`ViewModel` 直接依賴 `OrderRepository`（技術債）。`NewOrderListSource` 作為 `PagingSource<Int, OrderInfo>` 實作，邏輯上承擔部分 Domain 職責（enrichment、推薦商品整合），但放置在 `presentation/viewModel/` 目錄下，架構位置不理想。

### Repository 層

`OrderRepository` 是具體類別，未實作 `domain/contract` 介面（技術債）。直接持有 `IOrderApiService`（Retrofit）與 `KKApi`（內部 API 聚合器）。

`safeApiCallFlow {}` 統一包裝 Retrofit 呼叫，將 `B2CApiResponse<T>` 轉成 `ApiResult<T>`（Success/Error）。DCS 設定透過 `kkApi.b2cApi.dcs.fetch()` 取得，不走 Retrofit。

### API 層

| Endpoint | 方法 | 說明 |
|----------|------|------|
| `v2.2/orders` | GET | 主要訂單列表，Paging3 分頁 |
| `v2/order/status/count` | GET | Tab 角標數量 |
| `v2/marketplace/conversation/target_users` | POST | Marketplace 未讀訊息數 |
| `v2/recommend/order_list/also_bought` | POST | 第 1 頁推薦商品 |
| `v2/recommend/order_list/no_order` | GET | 未登入推薦商品 |

---

## View 方法清單

| 方法 | 說明 |
|------|------|
| `content()` | 主 Composable，建立 NavHost 與三個路由，啟動 Paging 資料流 |
| `initAction()` | 呼叫 `viewReady()`，設定 `onContactDriverClick`，未登入導向登入頁 |
| `observeData()` | 觀察 `orderListFlow`、`onClickContactServiceEvent`、`onClickNotificationCenterEvent`、`onClickOrderCommentEvent`、`onClickModifyButton`、`redirectLinkData` |
| `onResume()` | 空實作（繼承 super） |
| `onActivityResult()` | 處理登入回來（刷新列表）與取消補繳款回來（刷新列表並更新狀態） |
| `onDestroy()` | 清除 `dynamicRouterManager` 標記，取消 BroadcastReceiver 註冊 |
| `navigateToOrderDetail()` | 從通知導入訂單明細，透過 `pendingNavigation` 靜態變數傳遞 orderId |
| `showModifyDialog()` | 顯示訂單修改 BottomSheet Dialog |
| `onConfirmTimeIconClick()` | 顯示確認時間說明 BottomSheet |
| `onTimeoutDialog()` | 顯示超時 Dialog（交通類型提供重新導向連結，一般類型刷新列表） |
| `onContactDriverClick()` | 請求錄音權限後導向語音通話頁 |
| `trackProductCardImpression()` | 委派給 `getVM().trackProductCardImpression()` |
| `trackProductCardClick()` | 委派給 `getVM().trackProductCardClick()` |
| `ShowGroupBundleOrderBottomSheet()` | 顯示 Bundle 訂單詳情 BottomSheet |

---

## ViewModel 方法清單

| 方法 | 說明 |
|------|------|
| `init` | 並發啟動：觀察未讀訊息、評論更新、載入狀態監控、DCS 設定載入 |
| `viewReady()` | 頁面就緒：發送頁面瀏覽追蹤、載入未登入推薦、刷新狀態計數 |
| `getNewOrderListFlow()` | 建立 `Pager<Int, OrderInfo>`，回傳 `Flow<PagingData<OrderInfo>>` |
| `refreshOrderStatusCount()` | 取得三個 Tab 的數量角標 |
| `refreshUnreadMarketplaceMessageInfo()` | 觸發 Marketplace 未讀數更新 |
| `refreshOrder()` | 清空快取、重置狀態、觸發 Paging 刷新 |
| `onClickTab()` | 切換 Tab 並刷新資料 |
| `onClickOverDateOrderItem()` | 展開過期訂單 |
| `updateSelectedBundleOrderInfo()` | 更新 Bundle 訂單 BottomSheet 資料 |
| `updateSelectedBundleOrderInfoComment()` | 非同步取最新評論分數 |
| `getVouchersByOrder()` | 取訂單憑證列表 |
| `deepLink()` | 發送 EventBus DeepLink 事件 |
| `refreshWish()` | 刷新收藏商品清單 |
| `isFAQDescDialogOutdated()` | 判斷 FAQ 提示 Dialog 是否超過 14 天 |
| `setFAQDescDialogTime()` | 記錄 FAQ Dialog 顯示時間 |
| `trackXxx()` | 各種追蹤事件（KKTrackTool + KTMTracker） |
| `handleRetry()` | 自動重試邏輯，5 秒後啟動，最多 3 次每次間隔 3 秒 |

---

## 業務邏輯摘要

- **分頁**：每頁 5 筆，從第 1 頁開始，`nextKey = null` 表示無更多資料
- **過期訂單**：預設隱藏，展開後 `need_over_date_order=true` 重新載入
- **Marketplace 未讀數**：每頁訂單載入後，批次呼叫 `POST v2/marketplace/conversation/target_users` 取得 supplier 未讀數並注入至 `OrderInfo.unreadMsgCount`
- **聯絡按鈕顯示規則**（`shouldShowContactButton`）：
  1. DCS `hide_order_list_contact_button=true` → 隱藏
  2. RAIL_EUROPE / ZZIMAIR / THSRTW 交通類型 → 隱藏
  3. 非 Marketplace 訂單且有未讀訊息 → 顯示
  4. 進行中訂單且出發時間在 24 小時內 → 顯示
- **訂單明細路由**：新商品訂單（非交通、非飯店、非 KHSR）→ Compose 內嵌 `NewOrderDetailScreen`；其他 → 舊版 `OrderDetailFragment`
- **補繳款超時**：交通類型導向重新下單連結（`getRedirectUrlLink`）；一般類型直接刷新列表
- **自動重試**：`observeLoadState()` 於 5 秒後檢查列表是否為空，若空則每 3 秒重試一次，最多 3 次
- **評論同步**：`OrderCommentHandler.commentResultFlow` 收到評論結果後，直接更新 `_orderListFlow` 中對應訂單的 `comment` 欄位，不需重新拉 API

---

## 已知技術債

- `OrderRepository` 未實作 `:domain:contract` 的 Repository 介面，是具體類別，`ViewModel` 直接依賴實作而非抽象
- 無 UseCase 層，業務邏輯（enrichment、推薦整合）分散在 `NewOrderListSource`（位於 `presentation/viewModel/` 目錄，架構位置不當）
- `NewOrderListSource` 同時承擔 PagingSource 與部分 Domain 邏輯職責，職責不單一
- `_orderListFlow` 是 Paging Items 的副本快取，與 Paging3 的 `PagingData` 並行維護，存在資料一致性風險

## 相關筆記
- [01-architecture](../01-architecture.md)
- [02-modules](../02-modules.md)
- [03-ui-patterns](../03-ui-patterns.md)
- [05-networking](../05-networking.md)
- [06-data-layer](../06-data-layer.md)
- [07-concurrency](../07-concurrency.md)
- [order-detail-compose](order-detail-compose.md)
- [order-detail-legacy](order-detail-legacy.md)
- [order-success](order-success.md)
- [sku-activity-shell](sku-activity-shell.md)

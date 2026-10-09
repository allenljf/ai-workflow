# 通知中心

## 功能概述

- **入口**：`NotificationActivity`
- **Module**：`:app`（主要）+ `:feature:order_page`（Marketplace 部分）
- **架構**：3 個 Tab（Chat / Marketplace / FCM 推播），各 Tab 獨立 Fragment + ViewModel

---

## 檔案清單

### UI 層
- `NotificationActivity` — ViewPager + 3 Tab 容器，管理 badge 未讀數
- `ChatNotificationFragment` — Tab 0：聊天通知
- `MarketplaceNotificationFragment` — Tab 1：Marketplace 訊息，支援分頁載入
- `FcmNotificationFragment` — Tab 2：FCM 系統推播，進入時自動標為已讀

### ViewModel 層
- `NotificationViewModel` — 管理各 Tab 未讀計數，委派 `NotificationMainPageHandler`
- `ChatNotificationViewModel` — 聊天通知清單 + DCS FreshBot Tag
- `MarketplaceNotificationViewModel` — 分頁管理，追蹤 `lastMainConversationId`
- `FcmNotificationViewModel` — 混用 Coroutine Flow + RxJava，觀察通知清單、登入狀態、網路狀態

### Domain / Handler 層
- `PushNotificationDataHandler` / `PushNotificationDataHandlerImpl` — 代理 Repository，語意上扮演 UseCase + Repository 混合角色
- `MarketplaceNotificationDataHandler` / `MarketplaceNotificationDataHandlerImpl` — 並發請求 common + unread，含 200ms debounce 防抖
- `NotificationMainPageHandler` — 未讀計數聚合

### Data 層
- `PushNotificationRepository` — 純 Room DB 讀取（FCM 接收時寫入）
- `MarketplaceNotificationRepository` — 記憶體快取（HashMap），聚合 common/unread
- `ChatNotificationRepository` — 聊天通知本地記錄
- `ChatNotificationDcsRepository` — 呼叫 DCS API 取得 FreshBot Tag（位於 feature module，違反分層）
- `PushNotificationDao` — Room DAO，回傳 `Flow<List<PushNotificationEntity>>`

### Network 層
- `IOrderApiService`
  - `GET v2/marketplace/conversation/list` — common 訊息清單
  - `GET v2/marketplace/conversation/unread` — 未讀訊息清單
- DCS API：`kkApi.b2cApi.dcs.fetchList(configKey = DcsConfigKey.freshbot_tag, language)`

---

## 資料流

### Tab 2：FCM 系統推播

```
FcmNotificationFragment
 │  observeData() → 觀察 viewModel.pushNotificationList（LiveData）
 │  進入 Tab 時自動呼叫 viewModel.markAllPushNotificationAsRead()
 ↓
FcmNotificationViewModel
 │  init → register()
 │  register() → 訂閱 pushNotificationDataHandler.notificationListFlow
 │             → 訂閱 deeplinkDataObservable（登入狀態，RxJava）
 │             → 訂閱 isNetworkAvailableObservable（網路狀態，RxJava）
 ↓
PushNotificationDataHandlerImpl
 │  notificationListFlow = pushNotificationRepository.getPushNotificationListFlow()
 │  deeplinkDataObservable = AppState.hasAlreadyLoggedIn()（Reductor Store）
 │  isNetworkAvailableObservable = AppState.currentNetworkAvailability（Reductor Store）
 ↓
PushNotificationRepository → PushNotificationDao
 │  Room DB Flow<List<PushNotificationEntity>>（FCM 推播接收時寫入，頁面僅讀取）
 │  PushNotificationEntity.toPushNotificationInfo()
 ↓
LiveData 更新 → Fragment filter content.isNotBlank() → adapter 更新
```

### Tab 1：Marketplace 訊息

```
MarketplaceNotificationFragment
 │  initAction() → viewModel.refreshMessageList()
 │  PaginationScrollListener → viewModel.loadMoreData()
 ↓
MarketplaceNotificationViewModel
 │  init → observeListChange()（收集 handler.conversationInfoListFlow）
 │  refreshMessageList() → handler.refreshMessageList()
 │  loadMoreData() → handler.loadMoreData(lastMainConversationId)
 ↓
MarketplaceNotificationDataHandlerImpl
 │  debounce 200ms 防抖
 │  確認 appSharedData.hasAlreadyLoggedIn()
 │  並發：repository.getCommonMarketplaceMessageInfo()
 │        repository.getUnreadMarketplaceMessageInfo()
 │  合併：getCompleteConversationInfoList(unreadMessage)
 │  emit MarketplaceNotificationPageInfo
 ↓
MarketplaceNotificationRepository
 │  記憶體快取（commonCache / unreadCache HashMap）
 │  IOrderApiService.getCommonMarketplaceMessageInfo()
 │    → GET v2/marketplace/conversation/list
 │  IOrderApiService.getUnreadMarketplaceMessageInfo()
 │    → GET v2/marketplace/conversation/unread
```

### Tab 0：Chat 聊天通知

```
ChatNotificationFragment → ChatNotificationViewModel
 │  init → fetchList() + getDCSFreshTags()
 │  fetchList() → 收集 chatNotificationDataHandler.notificationListFlow
 │  getDCSFreshTags() → chatNotificationDcsRepository.getFreshBotTag(language)
 │    → kkApi.b2cApi.dcs.fetchList(DcsConfigKey.freshbot_tag, language)
```

---

## 業務邏輯摘要

- **未讀 badge**：`NotificationActivity.onCreate()` 呼叫 `viewModel.refreshUnreadCount()`，分別取三個 Tab 未讀數顯示紅點
- **FCM 自動已讀**：切換到 Tab 2 時自動呼叫 `markAllPushNotificationAsRead()`
- **Marketplace 分頁**：以 `lastMainConversationId` 作為 cursor，`PaginationScrollListener` 觸發 load more
- **FreshBot 路由**：DCS `freshbot_tag` 決定聊天通知點擊後的跳轉目標

---

## 已知技術債

1. `ChatNotificationDcsRepository` 位於 feature module，未走 `:domain:contract` 分層
2. `FcmNotificationViewModel` 混用 Coroutine Flow + RxJava（`deeplinkDataObservable`、`isNetworkAvailableObservable`）
3. Handler 層語意模糊，同時承擔 UseCase 與 Repository 職責，無 UseCase 抽象層
4. `NotificationViewModel` 注入方式為 `inject()`（Koin field injection）而非 `viewModel()` 委派

## 相關筆記
- [01-architecture](../01-architecture.md)
- [02-modules](../02-modules.md)
- [03-ui-patterns](../03-ui-patterns.md)
- [04-di-koin](../04-di-koin.md)
- [05-networking](../05-networking.md)
- [06-data-layer](../06-data-layer.md)
- [07-concurrency](../07-concurrency.md)
- [member-profile](member-profile.md)
- [order-detail-compose](order-detail-compose.md)

# 聯絡客服（訂單）技術文件

> 自動產生 | 最後更新：2026-07-30

---

## 概述

- **所在 Module**：`:feature:common:chat`（UI + ViewModel）、`:data:repository`（ChatRepositoryImpl）、`:data:networking:api`（IChatApiService）、`:app`（路由與推播）
- **UI 入口**：`ChatBotActivity.kt`（`libs/feature/chat`）
- **功能描述**：從訂單詳情頁或推播進入的售後聊天流程（AfterSale ChatBot）。支援 chatbot / 真人客服 session 切換、FAQ 快速回覆、圖片／PDF 附件、WebSocket 即時訊息、訊息翻譯。2.121.1 起為聯絡客服的實際主入口，取代舊版 `ContactUsActivity`。

---

## 檔案清單

```
UI（Compose）
 ├─ ChatBotActivity.kt            → libs/feature/chat/src/main/java/com/kkday/feature/chat/
 ├─ ChatScreen.kt                 → libs/feature/chat/src/main/java/com/kkday/feature/chat/compose/
 ├─ ChatBotMessageComponents.kt   → libs/feature/chat/src/main/java/com/kkday/feature/chat/compose/
 ├─ ChatServiceBottomSheet.kt     → libs/feature/chat/src/main/java/com/kkday/feature/chat/compose/
 ├─ FAQItemGroup.kt               → libs/feature/chat/src/main/java/com/kkday/feature/chat/compose/
 └─ FileActivity.kt               → libs/feature/chat/src/main/java/com/kkday/feature/chat/

ViewModel
 └─ ChatViewModel.kt              → libs/feature/chat/src/main/java/com/kkday/feature/chat/viewModel/

翻譯（子功能）
 └─ ChatTranslationManager.kt     → libs/feature/chat/src/main/java/com/kkday/feature/chat/translation/

Model
 └─ DomainModels.kt（ChatApiException、ChatUiState、MessageUiModel 等） → libs/model/src/main/java/com/kkday/model/chat/

Data（資料層）
 ├─ ChatRepositoryImpl.kt         → data/repository/src/main/java/com/kkday/data/repository/
 ├─ ChatWebSocketManager.kt       → data/networking/.../websocket/
 └─ OrderRepository.kt（FAQ 與訂單詳情沿用） → libs/feature/order_page/src/main/java/com/kkday/order_page/domain/repository/

Network（API 定義）
 ├─ IChatApiService.kt / ChatApiService.kt → libs/networking/api/src/main/java/com/kkday/library/networking/service/chat/
 └─ IOrderApiService.kt（訂單詳情、FAQ）    → libs/networking/api/src/main/java/com/kkday/library/networking/service/order_api/

路由與推播（:app）
 ├─ ContactUsRouterImpl.kt        → app/src/main/java/com/kkday/member/view/order/contact/（全專案唯一開啟 ChatBotActivity 的實作）
 ├─ KKdayNotificationHelper.kt    → app/src/main/java/com/kkday/member/fcm/
 └─ UserReducer.kt（登出清推播）   → app/src/main/java/com/kkday/member/reducer/user/
```

---

## 資料流

### 主流程：頁面初始化

```
ContactUsRouterImpl（8 個呼叫端統一經此；ChatBotActivity exported=false）
 ↓  ChatBotActivity.launch(orderMid, ...)
ChatBotActivity
 │  觀察 uiState / messages / isOrderNotFound
 ↓
ChatViewModel.initialize(orderMid)
 │  1. chatRepository.initializeChat() → join channel 取 notificationToken
 │  2. webSocketManager.connect(token) → 即時訊息
 │  3. async 並行：orderRepository.getOrderDetail()＋getSimpleFaq() / getMessageHistory()
 │  4. 阻擋檢查通過後才寫入 _messages 並進入 Success
 ↓
ChatRepositoryImpl
 │  metadata.isResultSuccess() → Result.success
 │  業務錯誤 → ChatApiException(status)
 │  HttpException → httpFailure() 解析 errorBody 還原 metadata.status
 ↓
IChatApiService（Retrofit）
 │  GET  v3/channels/after-sales/{order_mid}/join
 │  GET  v3/channels/after-sales/{order_mid}/msg-list
 │  POST v3/channels/after-sales/{order_mid}/msg-send
 │  POST v3/channels/after-sales/{order_mid}/msg-action
 │  POST v3/channels/after-sales/{order_mid}/token
 │  GET  v3/channels/after-sales/{order_mid}/channel-info
 └─ IOrderApiService：GET v2/new_order/{id}、POST v2/faq/simple
```

### 送出訊息（樂觀更新）

```
ChatViewModel.sendMessage(text)
 │  guard：isOrderNotFound 時直接 return
 │  appendUserTextMessage() → 樂觀訊息 uid = "local_<遞增序號>"（避免同毫秒碰撞）
 ↓
ChatRepositoryImpl.sendTextMessage()
 ├─ 成功：bot session 顯示 thinking indicator
 └─ 失敗：filterNot(uid) 回滾樂觀訊息
     ├─ ChatApiException.isOrderNotFound() → blockAsOrderNotFound()
     ├─ ChatApiException（一般業務錯誤）→ SnackBar 顯示後端 desc
     └─ 其他（IOException / HttpException）→ SnackBar 顯示 common_alert_connection_problem（不露技術訊息）
```

### 非本人訂單阻擋（LIVEBUG-4042）

```
判定點（任一命中即 blockAsOrderNotFound()）：
 ├─ initializeChat / loadHistoryMessages / 送訊 onFailure → ChatApiException.isOrderNotFound()
 └─ getOrderDetail 成功回應 → metadata.status ∈ ORDER_DETAIL_NOT_FOUND_STATUSES

blockAsOrderNotFound()（唯一阻擋入口，終局狀態）
 │  _isOrderNotFound = true、清空 messages / FAQ、uiState 離開 Success（輸入框鎖定）
 │  initialize / loadHistoryMessages 開頭 guard，重連與 onResume 不會解鎖
 ↓
ChatBotActivity 觀察 isOrderNotFound → 不可取消 dialog → finish()
```

錯誤碼白名單（`ChatApiException` companion）：
- `ORDER_NOT_FOUND_STATUSES = {100002, 100003, T101}` — chat 端點（v3/channels/after-sales/*）用
- `ORDER_DETAIL_NOT_FOUND_STATUSES = {100002}` — getOrderDetail（v2/new_order）用；100003 在其他端點另有 `PRODUCT_IS_CLOSE_SOLD` 語意，且 `OrderDetailReducer` 慣例只認 100002

---

## 逐層說明

### UI 層
> `ChatBotActivity` 為單一 Compose 入口，`ChatScreen` 依 `ChatUiState`（Loading / Success / Error）切換；輸入框、上傳、送出皆以 `uiState is Success` 為啟用條件。`ChatServiceBottomSheet` 提供服務選單。啟動一律經 `ContactUsRouterImpl`（Activity `exported=false`），無旁路入口，故入口驗證集中在 `ChatViewModel.initialize()` 即可覆蓋所有進入路徑。

### ViewModel 層
> `ChatViewModel`（@KoinViewModel）以 `MutableStateFlow` 管理 uiState / messages / simpleFAQ / isOrderNotFound，並實作 `WebSocketEventHandler` 接收即時訊息。樂觀訊息使用遞增序號產生本地 uid。tracking 方法（`trackViewCsContactPg` 等）在此層呼叫 `KKTrackTool`。

### Repository 層
> `ChatRepositoryImpl`（@Factory，binds ChatRepository）包裝 `ChatApiService` 與 `ChatWebSocketManager`。錯誤分類三層：metadata 業務錯誤 → `ChatApiException(status)`；非 2xx `HttpException` → `httpFailure()` 解析 errorBody 還原業務碼（解析不出或 status=API_EXCEPTION 時保留原始 exception，避免把網路錯誤偽裝成業務錯誤）；其他 exception 原樣回傳。FAQ 與訂單詳情沿用 `OrderRepository`。

### API 層
> chat 端點見上方資料流；回應皆為 `B2CApiResponse<T>`（`metadata.status` 業務碼判定，非 HTTP status）。`provideRetrofit` 未註冊 CallAdapter，非 2xx 一律以 `HttpException` 丟出——這是 `httpFailure()` 存在的原因。

---

## 業務邏輯摘要

- **非本人訂單阻擋**：訂單不存在／不屬於當前帳號時鎖頁並退出（見上方阻擋流程）；他人訂單歷史訊息在阻擋檢查前不寫入列表（隱私）。
- **Session 切換**：chatbot session 與真人客服 session 由後端 `SessionInfo` 控制；bot session 隱藏簡易 FAQ、送訊後顯示 thinking indicator。
- **WebSocket**：`ChatWebSocketManager` 負責連線與斷線重連，重連前先 refresh notification token；訊息、session 變更、互動狀態皆由 WS 事件驅動。
- **訊息翻譯**：`ChatTranslationManager` 走 Google Translate。
- **登出／切帳號清推播**：`UserReducer` 登出時呼叫 `KKdayNotificationHelper.cancelAccountBoundNotifications()`，只清帳號綁定的通知 ID（不動語音通話與其他 SDK），避免舊帳號推播殘留可點進他人訂單訊息頁（LIVEBUG-4042）。
- **送訊失敗提示**：回滾樂觀訊息＋SnackBar；僅後端業務錯誤顯示原文，網路／HTTP 技術訊息一律顯示通用連線錯誤文案。

---

## 舊版（Legacy）：ContactUsActivity

> 仍存在於 codebase，但已非主要入口；`ContactUsRouterImpl` 一律路由至 `ChatBotActivity`。

- 位置：`app/src/main/java/com/kkday/member/view/order/contact/`（ContactUsActivity、CustomerServiceScreen、ContactUsViewModel、ContactUsPresenter、ContactUsReducer 等）
- 架構：MVVM + MVP/Reductor 雙軌（`GET v2/msg/order/thread`、`NetworkApi.getOrderMessages()` RxJava 舊式 API）
- 附件瀏覽子功能（GalleryActivity、PdfContentActivity）與語音通話（Twilio）掛在此路徑下
- 詳細雙軌資料流見 git history 中本文件 2026-03-19 版本

---

## 已知技術債

- `ChatViewModel` 直接依賴 `OrderRepository`（具體類別）與 `ChatRepository`，未透過 `:domain:contract` UseCase 層。
- `provideRetrofit` 未註冊 CallAdapter，各 Repository 需自行處理 `HttpException`（`httpFailure()` 模式，先例：`PresaleChatRepositoryImpl`）。
- Legacy `ContactUsActivity` 全套（MVP + Reductor + RxJava NetworkApi）尚未移除，語音通話與附件瀏覽仍依賴該路徑。
- `100003` 錯誤碼在 `NetworkConstants` 同時定義為 `ORDER_IS_NOT_FOUND_FOR_MESSAGE` 與 `PRODUCT_IS_CLOSE_SOLD`（撞值），語意需與後端釐清。

## 相關筆記
- [01-architecture](../01-architecture.md)
- [02-modules](../02-modules.md)
- [03-ui-patterns](../03-ui-patterns.md)
- [05-networking](../05-networking.md)
- [06-data-layer](../06-data-layer.md)
- [07-concurrency](../07-concurrency.md)
- [presale-chat](presale-chat.md)
- [order-detail-compose](order-detail-compose.md)

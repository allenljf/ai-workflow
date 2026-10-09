# 售前訊息系統 技術文件

> 自動產生 | 最後更新：2026-07-06

---

## 概述

- **所在 Module**：`libs/feature/presale_chat`（獨立 feature module，與售後 `libs/feature/chat` 完全隔離）
- **UI 入口**：`PresaleEntryActivity`（WebView CTA 路由進入點）
- **Jira**：KKAPP-5541 | Branch：`feature/KKAPP-5541/presale-chat`
- **功能描述**：取代 Freshchat SDK 的自建售前客服聊天系統。包含 M1 入口路由（DCS 灰階控制）、M2 諮詢列表、M3 諮詢選擇 BottomSheet、M5 對話頁、M7 推播抑制，支援 Chatbot 與真人客服雙模式。

---

## 檔案清單

```
UI（使用者介面入口）
 ├─ PresaleEntryActivity.kt          → libs/feature/presale_chat/.../ui/entry/
 ├─ PresaleSessionListActivity.kt    → libs/feature/presale_chat/.../ui/session_list/
 ├─ PresaleSessionListContent.kt     → libs/feature/presale_chat/.../ui/session_list/
 ├─ SessionCard.kt                   → libs/feature/presale_chat/.../ui/session_list/component/
 ├─ ConsultPickerActivity.kt         → libs/feature/presale_chat/.../ui/consult_picker/
 ├─ ConsultPickerDialogFragment.kt   → libs/feature/presale_chat/.../ui/consult_picker/
 ├─ ConsultPickerContent.kt          → libs/feature/presale_chat/.../ui/consult_picker/
 ├─ RecentlyViewedTab.kt             → libs/feature/presale_chat/.../ui/consult_picker/component/
 ├─ OtherFaqsTab.kt                  → libs/feature/presale_chat/.../ui/consult_picker/component/
 ├─ PresaleChatActivity.kt           → libs/feature/presale_chat/.../ui/presale_chat/
 ├─ PresaleChatScreen.kt（Compose）  → libs/feature/presale_chat/.../ui/presale_chat/
 ├─ PresaleChatContent.kt（Compose） → libs/feature/presale_chat/.../ui/presale_chat/
 ├─ PresaleTextBubble.kt             → libs/feature/presale_chat/.../ui/presale_chat/component/
 ├─ PresaleImageBubble.kt            → libs/feature/presale_chat/.../ui/presale_chat/component/
 ├─ PresalePdfBubble.kt              → libs/feature/presale_chat/.../ui/presale_chat/component/
 ├─ PresaleInputBar.kt               → libs/feature/presale_chat/.../ui/presale_chat/component/
 ├─ PresaleThinkingIndicator.kt      → libs/feature/presale_chat/.../ui/presale_chat/component/
 ├─ PresaleConnectionBanner.kt       → libs/feature/presale_chat/.../ui/presale_chat/component/
 └─ ProductInfoCard.kt               → libs/feature/presale_chat/.../ui/presale_chat/component/

ViewModel（UI 狀態管理）
 ├─ PresaleEntryViewModel.kt         → libs/feature/presale_chat/.../viewmodel/
 ├─ PresaleSessionListViewModel.kt   → libs/feature/presale_chat/.../viewmodel/
 ├─ ConsultPickerViewModel.kt        → libs/feature/presale_chat/.../viewmodel/
 └─ PresaleChatViewModel.kt          → libs/feature/presale_chat/.../viewmodel/

Intent / State / Event 定義
 ├─ PresaleEntryViewIntent.kt        → libs/feature/presale_chat/.../viewmodel/
 ├─ PresaleChatViewIntent.kt         → libs/feature/presale_chat/.../viewmodel/
 ├─ ConsultPickerViewIntent.kt       → libs/feature/presale_chat/.../viewmodel/
 ├─ SessionListViewIntent.kt         → libs/feature/presale_chat/.../viewmodel/
 ├─ EntryRoutingState.kt             → libs/feature/presale_chat/.../viewmodel/
 ├─ PresaleMessageUiModel.kt         → libs/feature/presale_chat/.../viewmodel/
 └─ SessionCardUiModel.kt            → libs/feature/presale_chat/.../viewmodel/

UseCase（Domain 業務邏輯）
 └─ PresaleUseCases.kt               → libs/feature/presale_chat/.../usecase/
    （含 GetPresaleMessageConfigVariantUseCase、GetPresaleSimpleInfoUseCase、
      GetOngoingPresaleSessionsUseCase、GetClosedPresaleSessionsUseCase、
      MarkPresaleSessionReadUseCase、GetPresaleOtherFaqsUseCase、
      GetPresaleRecentlyViewedUseCase、GetPresaleSimpleFaqUseCase、
      JoinPresaleSessionUseCase、GetPresaleMessageHistoryUseCase、
      SendPresaleTextMessageUseCase、SendPresaleFileMessageUseCase、
      GetPresaleSessionInfoUseCase、GetPresaleNotificationTokenUseCase、
      ExecutePresaleMessageActionUseCase）

Repository 介面（Domain Contract）
 ├─ IPresaleChatRepository.kt        → domain/contract/.../presale/
 ├─ IPresaleSessionRepository.kt     → domain/contract/.../presale/
 ├─ IPresaleRoutingRepository.kt     → domain/contract/.../presale/
 └─ IPresaleFaqRepository.kt         → domain/contract/.../presale/

Repository 實作（Data Layer）
 ├─ PresaleChatRepositoryImpl.kt     → data/repository/.../presale/
 ├─ PresaleSessionRepositoryImpl.kt  → data/repository/.../presale/
 ├─ PresaleRoutingRepositoryImpl.kt  → data/repository/.../presale/
 └─ PresaleFaqRepositoryImpl.kt      → data/repository/.../presale/

Network（API 定義）
 ├─ IPresaleChatApiService.kt        → libs/networking/api/.../service/presale/
 ├─ PresaleChatWebSocketManager.kt   → libs/networking/api/.../websocket/presale/
 └─ PresaleSocketEvent.kt            → libs/networking/api/.../websocket/presale/

Data Model（API Response / Domain Model）
 ├─ PresaleJoinResponse.kt           → libs/model/.../presale/
 ├─ PresaleSessionListResponse.kt    → libs/model/.../presale/（含 SessionChannelDto.target_type）
 ├─ PresaleSessionInfoResponse.kt    → libs/model/.../presale/（含 is_bot、channel_oid、session_oid）
 ├─ PresaleMessageListResponse.kt    → libs/model/.../presale/
 ├─ PresaleCommonDto.kt              → libs/model/.../presale/（InteractionStateDto、ActorDto）
 ├─ PresaleJoinResult.kt             → libs/model/.../presale/model/（domain model）
 ├─ PresaleSessionInfo.kt            → libs/model/.../presale/model/（含 isBot: Boolean）
 ├─ PresaleMessage.kt                → libs/model/.../presale/model/
 └─ PresaleJoinTarget.kt             → libs/model/.../presale/model/（sealed class）

JSBridge Payload（WebView → Native）
 ├─ PresaleCTAIntent.kt              → libs/feature/presale_chat/.../model/
 │    欄位：type, sessionableType?, targetOid?, createdAtMillis
 │    （position / faqId / faqVersion 已移除，不再由 native 傳遞）
 └─ PresaleCtaPayload（in WebPayloadInfo.kt）→ libs/model/
      欄位：origin, sessionableType, targetOid
      （position / faq_id / faq_version 已移除）

輔助
 ├─ PresaleChatModule.kt             → libs/feature/presale_chat/.../di/（Koin DI）
 ├─ PresaleChatConstants.kt          → libs/feature/presale_chat/
 ├─ PresaleDebugLog.kt               → libs/feature/presale_chat/（Timber tag=PRESALECHAT）
 ├─ PresaleChatAnalyticsContext.kt   → libs/feature/presale_chat/.../analytics/
 ├─ PresaleChatFcmPayload.kt         → libs/feature/presale_chat/.../fcm/
 ├─ PresaleChatForegroundStateTracker.kt → libs/feature/presale_chat/.../fcm/
 └─ PresaleChatNotificationDispatcher.kt → libs/feature/presale_chat/.../fcm/
```

---

## 埋點架構（Tracking）

### 原生端（KKTracker）

埋點定義於 `PresaleChatEventCollection.kt`，分三個 EventPage：

| EventPage | 頁面 |
|-----------|------|
| `PRESALE_CS_CONTACT_PG` | M5 對話頁（`"PreSaleCsContactPg"`） |
| `PRESALE_CS_SELECT_INQUIRY_PG` | M3 諮詢選擇頁（`"PreSaleCsSelectInquiryPg"`） |
| `PRESALE_CS_INQUIRY_LIST_PG` | M2 諮詢列表頁（`"PreSaleCsInquiryListPg"`） |

主要事件範例（`KKTrackTool.shared().eventBuilder().setName(...).addProperty(...).trackEvent()`）：
- `View_PreSaleCsContactPg`：sessionOid、prodMid、isMp、faqId、hasUnRead、isClosed
- `Click_PreSaleCsSelectInquiryPg_ProdCard`：prodMid、position、isMp
- `Click_PreSaleCsSelectInquiryPg_Faq`：faqId

### Web → Mixpanel 直通（Pass-Through）

`Click_HelpCenter_PreSaleCsBtn`（Help Center WebView 點選按鈕）**由 Web 自行透過 postMessage 送出**，native 不需也不應定義對應 KKTracker 事件。

```
Web JS (Help Center)
 │  window.android.postMessage('{"name":"Click_HelpCenter_PreSaleCsBtn","props":{...}}')
 ↓
JavascriptInterfaceUtil.postMessage(jsonString)
 ↓
EventTracker.sharedInstance().postMessage(jsonString)
 ↓
mixpanelTracker.trackEvent(name, properties)   // 直接以 web 傳來的 name 發送，無需 WebPayloadInfo
```

**重要**：此路徑為純 pass-through，不解析結構，不需在 `WebPayloadInfo.kt` 定義對應 data class。

### 自訂事件（logRawEvent）

部分事件名稱無法由 enum 組合得出（snake_case），使用 `KKTrackTool.shared().logRawEvent(name, map)`：
- `presale_session_created`
- `presale_message_sent`

---

## 資料流

### 主流程：M5 對話頁進場初始化（ExistingSession 路徑）

```
PresaleChatActivity（AppCompatActivity）
 │  onCreate() → setContent { PresaleChatScreen(...) }
 │  從 Intent extras 讀取：sessionOid, sessionableType, faqQuestion,
 │  targetName, targetPictureUrl, isClosedSession
 ↓
PresaleChatScreen（Compose Stateful）
 │  LaunchedEffect(sessionOid, joinTargetId)：
 │  1. fetchFcmToken()（FirebaseMessaging 非同步取得）
 │  2. buildPresaleJoinTarget() → PresaleJoinTarget
 │  3. viewModel.init(target, fcmToken, ...)
 ↓
PresaleChatViewModel.init() → initWithExistingSession()
 │  coroutineScope {
 │    async { getInfo(sessionOid) }    ← 並行取 session info
 │    async { getMessages(sessionOid, null) }  ← 並行取歷史訊息
 │  }
 │  _state.value = copy(initState=Success, isBot=info.isBot, ...)
 │  connectSocketSuspend() → getNotificationToken() → socketManager.connect()
 ↓
GetPresaleSessionInfoUseCase
 │  repo.fetchSessionInfo(sessionOid): Result<PresaleSessionInfo>?
 ↓
PresaleChatRepositoryImpl.fetchSessionInfo()
 │  api.getSessionInfo(sessionOid)
 │  PresaleSessionInfoResponse.toDomain() → PresaleSessionInfo
 │  錯誤：Result.failure(IllegalStateException)
 ↓
IPresaleChatApiService
 │  @GET v3/channels/before-sales/sessions/{oid}/info
 ↓
後端 BFF API
```

### 主流程：M5 對話頁進場初始化（Join 路徑，新建 session）

```
PresaleChatViewModel.init() → initWithJoin()
 │  joinSession(target)（10 秒 timeout）
 │  getMessages(sessionOid, null)
 │  _state.value = copy(initState=Success, isBot=joinResult.isBot==true, ...)
 │  join response 帶 notificationToken → 直接 connectWithToken()
 │                     （否則 connectSocketSuspend()）
 │  handleFaqAutoSend()
 │    條件：target is Faq && isMessageListEmpty && is_bot=true
 │    → AutoSendFaqQuestion intent → sendTextMessage()
 ↓
JoinPresaleSessionUseCase.invoke(target)
 │  withTimeout(10_000) { repo.join(target) }
 │  失敗 → JoinOutcome.Failure(isTimeout, errorDesc)
 ↓
PresaleChatRepositoryImpl.join()
 │  ExistingSession → api.postJoin("sessions/{oid}")
 │  Product         → api.postJoinWithBody("product", body)
 │  Faq             → api.postJoinWithBody("faq", body)
 │  Others          → api.postJoin("others")
 │  PresaleJoinResponse.toDomain() → PresaleJoinResult
 ↓
IPresaleChatApiService
 │  @POST v3/channels/before-sales/{target}/join
 ↓
後端 BFF API
```

### 回傳流

```
後端 API
 ↓
PresaleChatRepositoryImpl
 │  PresaleSessionInfoResponse.toDomain() → PresaleSessionInfo
 │    （sessionState, interactionState, isBot, closedAt, updatedAt）
 │  PresaleMessageListResponse.toDomain() → PresaleMessagePage
 │    （messages: List<PresaleMessage>, nextCursor: String?）
 ↓
UseCase（nullable 回傳：成功回值，失敗回 null）
 ↓
PresaleChatViewModel
 │  initState = InitState.Success
 │  isBot = info.isBot（ExistingSession）/ joinResult.isBot==true（Join）
 │  sessionState = OPEN / CLOSED
 │  inputState = InputBarState(allowText, allowUploadFile, allowOpMsgAction)
 │  showProcessingIndicator = interactionState.showThinkingIndicator
 │  messages = List<PresaleMessageUiModel>（依 createdAt 排序）
 │  失敗：initState = InitState.Error(canRetry=true)
 ↓
PresaleChatScreen（collectAsStateWithLifecycle）
 │  成功：LazyColumn 渲染訊息 → 自動捲到底部 → InputBar 依 isInputEnabled 開放
 │  FAQ + isBot=true：觸發 AutoSendFaqQuestion → showProcessingIndicator=true
 └  失敗：全頁錯誤狀態 + 重試按鈕
```

### Socket 事件流（初始化後持續監聽）

```
PresaleChatWebSocketManager.observeEvents(): Flow<PresaleSocketEvent>
 ↓
PresaleChatViewModel.handleSocketEvent()
 ├─ MessageReceived  → refreshSessionInfo()（並行取 info + messages）
 ├─ SessionChanged   → refreshSessionInfo()
 ├─ InteractionStateChanged → 直接更新 inputState（不打 info API）
 ├─ SessionClosed    → sessionState = CLOSED
 └─ ConnectError / Disconnected → handleSocketDisconnected()（最多重連 3 次）
```

---

## 逐層說明

### UI 層（PresaleChatActivity + PresaleChatScreen）

`PresaleChatActivity` 負責 Android 系統整合：FCM token 取得、圖片/PDF picker、Crashlytics tag、`ForegroundStateTracker` onResume/onPause。所有業務 UI 邏輯委派給 `PresaleChatScreen`（Compose Stateful）。

`PresaleChatScreen` 透過 `LaunchedEffect` 管理三條初始化側效：
1. `LaunchedEffect(sessionOid, joinTargetId)`：取 FCM token → `viewModel.init()`
2. `LaunchedEffect(state.initState)`：init 完成後觸發 FAQ 自動代送
3. `DisposableEffect(Unit)`：監聽 `ProcessLifecycleOwner.ON_START` → `OnForeground` intent

### ViewModel 層（PresaleChatViewModel）

使用 `MutableStateFlow<PresaleChatUiState>`（非 Reductor），以 `copy()` 做 immutable 更新。關鍵欄位：
- `isBot: Boolean`：從 join / info API 取得，控制 ProcessingIndicator 顯示時機
- `initState: InitState`：Loading / Success / Error，驅動全頁載入與錯誤狀態
- `sessionState: SessionState`：OPEN / CLOSED，驅動 InputBar 替換
- `latestInfoUpdatedAt: Long`：info 刷新 last-wins 防競態

`refreshSessionInfo()` 在 onForeground、`MessageReceived`、`SessionChanged` 時觸發，同時更新 `isBot`、`inputState`、`showProcessingIndicator`。`sessionState` 走 last-wins（`updated_at` 比較）。

### UseCase 層

所有 UseCase 放在單一檔案 `PresaleUseCases.kt`，`@Factory`，回傳 nullable 而非 `Result`（避免 MockK inline value class 衝突）。`JoinPresaleSessionUseCase` 例外：回傳 `JoinOutcome` sealed class（Success / Failure），保留 `isTimeout` 與 `errorDesc` 供 SnackBar 顯示。

### Repository 層

全部 `@Factory(binds = [IXxx::class])`（非 `@Single`），確保無狀態、跨用戶無髒資料。錯誤統一包為 `Result.failure(IllegalStateException(desc))`，UseCase 層 `.getOrNull()` 轉 nullable。`join()` 在 Repository 內另有 10 秒 timeout（與 UseCase 層 timeout 對應）。

### API 層

`IPresaleChatApiService`（Retrofit，走 `B2CApiResponse` 統一錯誤處理），10 個端點。WebSocket 獨立於 `PresaleChatWebSocketManager`（`single {}` DSL，不加 `@Single` annotation），與售後 `ChatWebSocketManager` 完全隔離，notification token 各自持有。

---

## Activity / Screen 方法清單

### PresaleEntryActivity

| 方法 | 說明 |
|------|------|
| `onCreate()` | 處理 FCM deep link（`kkday://presale-chat/session/<oid>`）；啟動 observeEvents()、observeState()；dispatch StartRouting intent |
| `onNewIntent()` | singleTask：新 intent 到來時重新處理 deep link |
| `onActivityResult()` | 攔截 `REQUEST_CODE_LOGIN` 結果：登入成功 → dispatch `IdentityChanged` + `ResumeDeferredCta`；取消/失敗 → `finish()` 回到幫助中心 WebView |
| `handleDeepLinkIntent()` | 解析 FCM push deep link；有 session_oid → M5，無 → M2，非 deep link → false |
| `observeEvents()` | 收集 PresaleEntrySingleEvent，分派至 handleEvent() |
| `observeState()` | 收集 EntryRoutingState；Routing 時 show routingLoadingDialog，否則 dismiss |
| `navigateToLogin()` | 未登入時的 CTA 事件處理：`RouterHelper.dispatchWithReqCode(PAGE_LOGIN_SPLASH, REQUEST_CODE_LOGIN).navigator(this)`（feature 模組不可依賴 `:app` 的 `SocialLoginSplashActivity`，改走 KRouter） |
| `onDestroy()` | 防止 dialog leak：若 routingLoadingDialog isShowing 則 dismiss |
| `routingLoadingDialog` (lazy) | 共用 `loadingDialog(canCancelable=false)` + `FLAG_DIM_BEHIND` + `setDimAmount(0.5f)` 產生帶深色遮罩的路由等待蓋板 |

### PresaleChatActivity

| 方法 | 說明 |
|------|------|
| `onCreate()` | setContent PresaleChatScreen，注入所有 Intent extras |
| `onResume()` | foregroundStateTracker.onResume(sessionOid)、Crashlytics tag |
| `onPause()` | foregroundStateTracker.onPause()、清 Crashlytics tag |
| `fetchFcmToken()` | 非同步取得 FCM token，失敗回空字串不阻斷 |
| `handleImageSelection()` | 圖片格式驗證 + base64 壓縮 → SendImage intent |
| `handleFileSelection()` | PDF 格式驗證 + 8MB 大小限制 → SendPdf intent |
| `openProductPage()` | KRouter 路由至商品頁 |
| `openPdfPreview()` | base64 / URL → FileActivity 預覽 |

---

## ViewModel 方法清單

### PresaleEntryViewModel

| 方法 | 說明 |
|------|------|
| `runRouting()` | 路由決策入口：先檢查 `AppSharedData.hasAlreadyLoggedIn()`，未登入 → `deferUntilLogin()`（不打任何 API）；已登入 → 打 DCS variant API 判斷 `isNewFlow`，決定 M2 / M3 / 舊版 Freshchat |
| `dispatchIntent()` | Intent dispatch 入口，對應 StartRouting / ResumeDeferredCta / DeferUntilLogin / IdentityChanged / DismissForceUpdate |
| `deferUntilLogin()` | 未登入時保存 deferred CTA（`cta` 為 `null` 時以不指定 target 的通用 CTA 頂替，不再 fallback 舊版）、建立 `lastKnownMemberUuid` 比對基準、發出 `NavigateToLogin` 事件、狀態設為 `AwaitingLogin` |
| `resumeDeferredCtaIfAny()` | 登入成功後續行：deferred CTA 存在且未過期（5 分鐘 TTL）→ 重新呼叫 `runRouting()`；不存在或已過期 → 發出 `CloseAndReturnToWebView` 事件關閉頁面 |
| `handleIdentityChanged()` | 比對登入前後 member uuid，偵測到帳號切換（非首次登入）時清除 deferred CTA，讓 `resumeDeferredCtaIfAny()` 自然走向關閉頁面而非續行 |

### PresaleChatViewModel

| 方法 | 說明 |
|------|------|
| `init { }` | 讀取 RemoteConfig 客服服務時間，寫入 csServiceTimeText |
| `dispatchIntent()` | Intent dispatch 入口，對應所有 PresaleChatViewIntent |
| `init()` | M5 初始化入口，分流 ExistingSession / Join 兩路徑 |
| `initWithExistingSession()` | 並行取 info + messages，不呼叫 join API |
| `initWithJoin()` | 呼叫 join API（10 秒 timeout），取 messages，建立 Socket 連線 |
| `retryInit()` | 重試初始化（以 storedTarget / storedFcmToken 重新呼叫 init） |
| `connectSocketSuspend()` | 取 notification token → connectWithToken() |
| `connectWithToken()` | 建立 Socket 連線，重置重連計數 |
| `handleSocketEvent()` | 分派 PresaleSocketEvent 各種事件 |
| `handleSessionClosed()` | 設 sessionState=CLOSED |
| `refreshSessionInfo()` | 並行取 info + messages，更新 isBot/inputState/sessionState |
| `mergeLatestMessages()` | 合併 API 訊息與本地 optimistic 訊息（防重複） |
| `sendTextMessage()` | 樂觀插入 → API → Socket echo 去重 |
| `sendFileMessage()` | base64 上傳，FileUploadState=Locked 鎖附件 |
| `retrySendMessage()` | 重送失敗的文字訊息（同 clientMessageId） |
| `retryUpload()` | 重送失敗的圖片/PDF |
| `loadMoreHistory()` | cursor 分頁載入更早訊息 |
| `handleFaqAutoSend()` | 新建 FAQ session + 空訊息 + is_bot=true → 自動代送 |
| `handleSocketDisconnected()` | 重連邏輯（最多 3 次），更新 ConnectionBannerState |
| `reconnectSocket()` | 手動觸發重連（用戶點擊 ConnectionBanner） |
| `getWSUrl()` | 依環境建構 WebSocket URL |

### PresaleSessionListViewModel

| 方法 | 說明 |
|------|------|
| `dispatchIntent()` | 分派 SessionListViewIntent |
| `loadInitial()` | 並行取 ongoing + closed sessions |
| `onCardClicked()` | 樂觀清紅點（fire-and-forget）→ 導至 M5 |
| `loadMoreHistory()` | cursor 分頁載入更多歷史 |
| `refresh()` | 下拉刷新雙 Section |

### ConsultPickerViewModel

| 方法 | 說明 |
|------|------|
| `dispatchIntent()` | 分派 ConsultPickerViewIntent |
| `loadRecentlyViewed()` | 懶載入最近瀏覽（切 Tab 才觸發，已載入不重打） |
| `loadOtherFaqs()` | 載入 FAQ 列表（API 失敗仍保留「其他問題」固定項） |
| `joinSession()` | 10 秒 timeout + 300ms debounce + in-flight 鎖 |

---

## 業務邏輯摘要

- **Routing Loading 蓋板**：`PresaleEntryActivity` 在 DCS check 期間顯示帶深色遮罩（50% dim）的蓋板，避免點擊後停頓無回饋；`EntryRoutingState.Routing` 觸發 show，其餘狀態 dismiss
- **CTA 埋點委託 Web**：`Click_HelpCenter_PreSaleCsBtn` 由 Help Center WebView 透過 `postMessage` 直送 Mixpanel，native 不發此事件，`PresaleEntryViewModel` 不含任何 KKTracker 呼叫
- **DCS 灰階**：WebView CTA → DCS API（8 秒 timeout）→ `is_new_flow=true` 走新版，否則 fallback Freshchat
- **未登入 deferred CTA 續行**：未登入時導向登入頁並保存原始 CTA，**不呼叫**任何售前客服 API；登入成功後自動依原 CTA 續行路由（無需再次點擊）；取消登入、切換帳號、或 deferred CTA 超過 5 分鐘 TTL（`PresaleChatConstants.DEFERRED_CTA_TTL_MS`）時關閉頁面回到幫助中心 WebView
- **isBot 狀態**：從 join API（新 session）或 info API（既有 session）取得，`is_bot=true` 時才顯示 Processing Indicator、自動代送 FAQ 問題
- **FAQ 自動代送**：新建 session + sessionable_type=faq + messages 為空 + is_bot=true → 自動以用戶身份送出 FAQ 問題 1 次（不重送）
- **Info 刷新觸發時機**：`ProcessLifecycleOwner.ON_START`（前景）、`MessageReceived` socket 事件、`SessionChanged` socket 事件
- **InteractionStateChanged**：直接更新 inputState，**不打 info API**（避免 `updated_at` 相同跳過更新的問題）
- **樂觀更新**：送訊息時立即插入 PENDING 狀態；Socket echo 以 `clientMessageId` 配對去重；失敗顯示 ❗icon 可重送（closed session 不可重送）
- **SessionCard 標題**：`sessionable_type` 來源優先使用 `channel.target_type`（API 9 回傳），fallback 至 top-level `sessionable_type`；`"others"` 顯示「其他問題」文案
- **環境切換強制登出**：`UserReducer.selectAppConfig()` 切換環境時，同步清除 `PersistentManager` 的 `userInfo`、`loginChannel`、`userTokenInfo`，避免舊 token 在新環境造成 401
- **錯誤處理**：join 失敗 → 全頁錯誤狀態 + 重試；messages 失敗 → inline 重試（不阻斷 InputBar）；Socket 斷線 → 最多自動重連 3 次，超過顯示手動重連 banner

---

## 已知技術債

- `PresaleUseCases.kt` 集中放所有 UseCase（13 個），理想架構應各自分檔，但單檔可接受
- `PresaleChatViewModel` 直接依賴 `PersistentManager`（跨越 domain 邊界），與標準 Clean Architecture 偏差
- `libs/feature/presale_chat` 採 copy-as-starting-point 策略，部分 UI 元件與售後 `libs/feature/chat` 重複；Phase 3（2026 Q4+）預計抽取 `chat_core` 共用模組
- `Actor.Supplier` sealed class variant 已定義但 UI 層 fallback 至 `KKdayAgent` 樣式（Phase 2 預留）
- FCM 推播 deep link（`PresaleEntryActivity.handleDeepLinkIntent()`）未走未登入 deferred CTA 續行機制，未登入時仍直接嘗試 join，可能得到後端錯誤（spec 另一個 P1 需求，待後續變更補齊）
- `PresaleEntryViewModelTest.kt` 已移除：mock `AppSharedData.hasAlreadyLoggedIn()` 時會在此模組的測試環境直接執行到真正方法本體並 NPE（相同手法在 `:app` 模組正常），根因待查，目前以實機驗證取代單元測試

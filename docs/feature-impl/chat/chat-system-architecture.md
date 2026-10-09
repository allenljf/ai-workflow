# 售後訊息聊天系統架構說明

## 目錄
- [系統概覽](#系統概覽)
- [架構層次](#架構層次)
- [模組結構](#模組結構)
- [檔案職責](#檔案職責)
- [聊天運作流程](#聊天運作流程)
- [WebSocket 事件用途](#websocket-事件用途)
- [API 用途](#api-用途)
- [資料流向](#資料流向)

---

## 系統概覽

售後訊息聊天系統採用 **Clean Architecture** 設計，整合 **WebSocket (SocketIO)** 實現即時通訊。系統支援 Chatbot 與真人客服兩種模式，可動態切換。

### 核心功能
- 即時文字訊息收發
- 檔案（圖片/文件）上傳與預覽
- 訊息歷史記錄分頁載入
- Chatbot 互動（List/Button 選項）
- Session 狀態管理（Bot ↔ 真人客服）
- 連線狀態監控與自動重連
- FAQ 推薦

---

## 架構層次

```
┌─────────────────────────────────────────────────────────┐
│              Presentation Layer (UI)                     │
│  ┌──────────────────────────────────────────────────┐    │
│  │  ChatBotActivity / ChatScreen (Compose)          │    │
│  │  ChatViewModel (狀態管理 + 業務邏輯 + 事件處理) │    │
│  └──────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                  Domain Layer                            │
│  ┌──────────────────────────────────────────────────┐    │
│  │  Contract (介面定義)                             │    │
│  │  - ChatRepository                                │    │
│  │  - WebSocketEventHandler                         │    │
│  └──────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                   Data Layer                             │
│  ┌──────────────────────────────────────────────────┐    │
│  │  Repository (資料存取)                           │    │
│  │  - ChatRepositoryImpl                            │    │
│  └──────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────┐    │
│  │  API Service (網路層)                            │    │
│  │  - ChatApiService / IChatApiService              │    │
│  └──────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────┐    │
│  │  WebSocket Manager (即時通訊)                    │    │
│  │  - ChatWebSocketManager                          │    │
│  └──────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              Infrastructure Layer                        │
│  - Retrofit (HTTP API)                                   │
│  - SocketIO Client (WebSocket)                           │
└─────────────────────────────────────────────────────────┘
```

---

## 模組結構

### 1. Feature Module (`libs/feature/chat`)
**職責**: UI 層實作，包含 Compose 畫面與 ViewModel

```
libs/feature/chat/
├── ChatBotActivity.kt              # Activity 入口
├── FileActivity.kt                  # 檔案預覽 Activity
├── InteractionUiState.kt           # 互動狀態資料類別
├── viewModel/
│   └── ChatViewModel.kt             # ViewModel（狀態管理 + 業務邏輯）
├── compose/                         # Compose UI 元件
│   ├── ChatScreen.kt                # 主要 Compose UI
│   ├── ChatServiceBottomSheet.kt    # 服務選單 Bottom Sheet
│   ├── FAQItemGroup.kt               # FAQ 推薦區塊
│   ├── ChatBotMessageComponents.kt # Bot 訊息元件
│   ├── ChatErrorView.kt             # 錯誤顯示元件
│   ├── ChatInputBar.kt              # 輸入欄
│   ├── ChatLoadingView.kt           # 載入中顯示元件
│   ├── ConnectionStatusBar.kt        # 連線狀態提示
│   ├── FileMessageItem.kt           # 檔案訊息元件
│   ├── MessageActionsView.kt         # 訊息 Action 元件
│   ├── MessageItem.kt               # 訊息項目（文字/檔案）
│   ├── TextMessageItem.kt           # 文字訊息元件
│   └── ThinkingIndicatorItem.kt      # Bot 思考中動畫
└── navigation/
    └── ChatNavigator.kt              # 導航介面
```

### 2. Domain Layer

#### Contract (`domain/contract`)
**職責**: 定義 Repository 與 WebSocket 事件處理介面

```
domain/contract/
├── repository/
│   └── ChatRepository.kt            # Repository 介面
└── handler/
    └── WebSocketEventHandler.kt     # WebSocket 事件處理介面
```

### 3. Data Layer

#### 3.1 Repository (`data/repository`)
**職責**: 實作 Repository 介面，整合 API Service 與 WebSocket Manager

```
data/repository/
└── ChatRepositoryImpl.kt            # Repository 實作
```

#### 3.2 Networking (`libs/networking/api`)
**職責**: HTTP API 與 WebSocket 管理

```
libs/networking/api/
├── service/chat/
│   ├── IChatApiService.kt           # Retrofit API 介面
│   └── ChatApiService.kt            # API Service 實作
└── data/networking/websocket/
    ├── ChatWebSocketManager.kt      # WebSocket 連線管理器
    └── SocketEventParser.kt         # WebSocket 事件解析器
```

### 4. Model (`libs/model`)
**職責**: 資料模型定義與 Mapping

```
libs/model/chat/
├── ApiModels.kt                      # API 請求/回應模型
├── DomainModels.kt                   # Domain 層模型
├── WebSocketModels.kt                # WebSocket 事件模型
├── UiModels.kt                       # UI 層模型
├── ModelMappings.kt                  # Model 轉換擴充函數
└── MimeTypeDetector.kt               # MIME 類型偵測工具
```

### 5. DI Module (`app/src/main/java/com/kkday/member/di`)
**職責**: Koin 依賴注入設定

```
app/src/main/java/com/kkday/member/di/
├── ChatModule.kt                    # Chat 模組 DI 設定
└── ChatNavigatorImpl.kt             # ChatNavigator 實作
```

---

## 檔案職責

### Presentation Layer

#### `ChatBotActivity.kt`
- **職責**: Activity 入口，處理 Intent 參數（orderMid, wsUrl）
- **位置**: `libs/feature/chat/src/main/java/com/kkday/feature/chat/ChatBotActivity.kt`
- **主要功能**:
  - 接收外部 Intent，取得 `orderMid`
  - 初始化 `ChatViewModel`
  - 設定 Compose UI
  - 處理檔案選擇（圖片/文件）
  - 生命週期管理（onDestroy 時斷開 WebSocket）

#### `ChatViewModel.kt`
- **職責**: UI 狀態管理、業務邏輯處理、WebSocket 事件處理
- **位置**: `libs/feature/chat/src/main/java/com/kkday/feature/chat/viewModel/ChatViewModel.kt`
- **主要功能**:
  - 初始化聊天室（直接呼叫 Repository → 連接 WebSocket → 載入歷史訊息）
  - 發送文字/檔案訊息（樂觀更新）
  - 載入歷史訊息（支援分頁）
  - 執行訊息 Action（List/Button 點擊）
  - 處理 WebSocket 事件（實作 `WebSocketEventHandler`）
  - 管理 UI 狀態（`ChatUiState`、`messages`、`connectionEventState`）
  - 追蹤事件（KKTracker）

#### `ChatScreen.kt`
- **職責**: Compose UI 主要畫面
- **位置**: `libs/feature/chat/src/main/java/com/kkday/feature/chat/compose/ChatScreen.kt`
- **主要功能**:
  - 顯示訊息列表（文字/檔案/Thinking Indicator）
  - 顯示輸入欄（文字輸入、檔案上傳按鈕）
  - 顯示連線狀態提示（網路錯誤、Session 關閉）
  - 顯示 FAQ 推薦區塊
  - 處理滾動邏輯（自動滾到底部、載入歷史訊息）

#### `FileActivity.kt`
- **職責**: 檔案預覽 Activity（圖片/PDF）
- **位置**: `libs/feature/chat/src/main/java/com/kkday/feature/chat/FileActivity.kt`
- **主要功能**:
  - 顯示圖片預覽
  - 顯示 PDF 預覽
  - 處理檔案開啟邏輯

#### `InteractionUiState.kt`
- **職責**: 互動狀態資料類別
- **位置**: `libs/feature/chat/src/main/java/com/kkday/feature/chat/InteractionUiState.kt`
- **主要功能**: 定義互動狀態相關的資料結構

### Domain Layer

#### `ChatRepository.kt` (Interface)
- **職責**: 定義聊天功能核心介面
- **位置**: `domain/contract/src/main/java/com/kkday/library/common/repository/ChatRepository.kt`
- **主要方法**:
  - `initializeChat(orderMid)`: 初始化聊天室
  - `getMessageHistory(orderMid, cursor)`: 取得訊息列表
  - `sendTextMessage(orderMid, text, msgCategory)`: 發送文字訊息
  - `sendFileMessage(orderMid, file, msgCategory)`: 發送檔案訊息
  - `executeMessageAction(orderMid, actionData)`: 執行訊息 Action
  - `refreshNotificationToken(orderMid)`: 刷新 WebSocket token

#### `WebSocketEventHandler.kt` (Interface)
- **職責**: 定義 WebSocket 事件處理介面
- **位置**: `domain/contract/src/main/java/com/kkday/library/common/handler/WebSocketEventHandler.kt`
- **主要方法**:
  - `onMessageReceived(event)`: 收到新訊息
  - `onMessageDelivered(event)`: 訊息已送達
  - `onSessionClosed(event)`: Session 關閉
  - `onInteractionStateChanged(event)`: 互動狀態變更
  - `onSessionChanged(event)`: Session 變更（Bot ↔ 真人）
  - `onConnectionError(error)`: 連線錯誤
  - `onConnected()`: 連線成功

### Data Layer

#### `ChatRepositoryImpl.kt`
- **職責**: 實作 `ChatRepository` 介面
- **位置**: `data/repository/src/main/java/com/kkday/data/repository/ChatRepositoryImpl.kt`
- **主要功能**:
  - 呼叫 `ChatApiService` 執行 HTTP API 請求
  - 處理 API 回應（錯誤處理、Model Mapping）
  - 回傳 `Result<T>` 給 ViewModel

#### `IChatApiService.kt` / `ChatApiService.kt`
- **職責**: Retrofit API 介面與實作
- **位置**: `libs/networking/api/src/main/java/com/kkday/library/networking/service/chat/`
- **主要端點**:
  - `GET v3/channels/after-sales/{order_mid}/join`: 初始化聊天
  - `GET v3/channels/after-sales/{order_mid}/msg-list`: 取得訊息列表
  - `POST v3/channels/after-sales/{order_mid}/msg-send`: 發送訊息
  - `POST v3/channels/after-sales/{order_mid}/msg-action`: 執行 Action
  - `POST v3/channels/after-sales/{order_mid}/token`: 刷新 token

#### `ChatWebSocketManager.kt`
- **職責**: WebSocket 連線管理
- **位置**: `libs/networking/api/src/main/java/com/kkday/data/networking/websocket/ChatWebSocketManager.kt`
- **主要功能**:
  - 建立 SocketIO 連線（使用 `notification_token`）
  - 監聽 WebSocket 事件（`message.received`、`session.closed` 等）
  - 解析事件 JSON → Domain Model
  - 通知註冊的 `WebSocketEventHandler`
  - 自動重連機制（可設定 token refresher）
  - 連線狀態管理（connected/disconnected）

#### `SocketEventParser.kt`
- **職責**: 解析 WebSocket 事件 JSON
- **位置**: `libs/networking/api/src/main/java/com/kkday/data/networking/websocket/SocketEventParser.kt`
- **主要功能**:
  - 將 JSON 字串解析為 `WSMessageReceivedEvent`、`WSSessionClosedEvent` 等

### Model Layer

#### `ApiModels.kt`
- **職責**: API 請求/回應模型（含 Gson/kotlinx.serialization 標註）
- **位置**: `libs/model/src/main/java/com/kkday/model/chat/ApiModels.kt`
- **主要模型**:
  - `JoinChannelData`: 初始化回應
  - `MessageListData`: 訊息列表回應
  - `SendMessageRequest`: 發送訊息請求
  - `MessageActionRequest`: Action 執行請求

#### `DomainModels.kt`
- **職責**: Domain 層模型（純 data class，無序列化標註）
- **位置**: `libs/model/src/main/java/com/kkday/model/chat/DomainModels.kt`
- **主要模型**:
  - `ChatInitData`: 初始化資料
  - `MessageData`: 訊息資料
  - `SessionInfo`: Session 資訊
  - `InteractionState`: 互動狀態

#### `WebSocketModels.kt`
- **職責**: WebSocket 事件模型
- **位置**: `libs/model/src/main/java/com/kkday/model/chat/WebSocketModels.kt`
- **主要模型**:
  - `WSMessageReceivedEvent`: 訊息接收事件
  - `WSSessionClosedEvent`: Session 關閉事件
  - `WSInteractionStateChangedEvent`: 互動狀態變更事件
  - `WSSessionChangedEvent`: Session 變更事件

#### `UiModels.kt`
- **職責**: UI 層模型
- **位置**: `libs/model/src/main/java/com/kkday/model/chat/UiModels.kt`
- **主要模型**:
  - `ChatUiState`: UI 狀態（Loading/Success/Error）
  - `MessageUiModel`: UI 訊息模型
  - `FileUiInfo`: UI 檔案資訊

#### `ModelMappings.kt`
- **職責**: Model 轉換擴充函數
- **位置**: `libs/model/src/main/java/com/kkday/model/chat/ModelMappings.kt`
- **主要轉換**:
  - `ApiModel.toDomain()`: API Model → Domain Model
  - `DomainModel.toUi()`: Domain Model → UI Model
  - `WSModel.toDomain()`: WebSocket Model → Domain Model

#### `MimeTypeDetector.kt`
- **職責**: MIME 類型偵測工具
- **位置**: `libs/model/src/main/java/com/kkday/model/chat/MimeTypeDetector.kt`
- **主要功能**: 根據檔案名稱或內容判斷 MIME 類型

---

## 聊天運作流程

### 1. 初始化流程

```
使用者開啟聊天頁面
    ↓
ChatBotActivity.onCreate()
    ↓
ChatViewModel.initialize(orderMid)
    ↓
ChatRepository.initializeChat(orderMid)
    ↓
ChatApiService.joinChannel(orderMid)
    ↓
取得 notification_token、channel_oid、current_session
    ↓
ChatViewModel 註冊 WebSocketEventHandler
    ↓
ChatWebSocketManager.connect(notification_token)
    ↓
WebSocket 連線成功
    ↓
ChatViewModel.loadHistoryMessages()
    ↓
ChatRepository.getMessageHistory(orderMid, cursor=null)
    ↓
顯示訊息列表
```

### 2. 發送訊息流程

#### 2.1 發送文字訊息
```
使用者輸入文字並點擊發送
    ↓
ChatViewModel.sendMessage(text)
    ↓
樂觀更新：立即顯示使用者訊息（messageUid=null）
    ↓
ChatRepository.sendTextMessage(orderMid, text, msgCategory)
    ↓
ChatApiService.sendMessage(orderMid, SendMessageRequest)
    ↓
API 回應成功（取得 messageUid）
    ↓
下次載入歷史訊息時，本地訊息會被後端訊息取代（dedupe）
```

#### 2.2 發送檔案訊息
```
使用者選擇檔案（圖片/文件）
    ↓
檔案編碼為 Base64
    ↓
ChatViewModel.sendFileMessage(file, msgCategory)
    ↓
顯示「上傳中」SnackBar
    ↓
ChatRepository.sendFileMessage(orderMid, file, msgCategory)
    ↓
ChatApiService.sendMessage(orderMid, SendMessageRequest(file))
    ↓
API 回應成功
    ↓
清除 SnackBar，顯示檔案訊息
```

### 3. 接收訊息流程

```
WebSocket 收到 "message.received" 事件
    ↓
ChatWebSocketManager 解析事件 JSON
    ↓
觸發 WebSocketEventHandler.onMessageReceived(event)
    ↓
ChatViewModel.onMessageReceived(event)
    ↓
移除 Thinking Indicator（如有）
    ↓
ChatViewModel.loadHistoryMessages(isLatest=true)
    ↓
ChatRepository.getMessageHistory(orderMid, cursor=null)
    ↓
取得最新訊息列表（含新訊息）
    ↓
合併現有訊息（dedupe + merge）
    ↓
更新 UI（顯示新訊息）
```

### 4. 執行 Action 流程（List/Button 點擊）

```
使用者點擊 Chatbot List/Button 選項
    ↓
ChatScreen 建立 MessageActionData
    ↓
ChatViewModel.executeAction(actionData)
    ↓
ChatRepository.executeMessageAction(orderMid, actionData)
    ↓
ChatApiService.executeAction(orderMid, MessageActionRequest)
    ↓
API 回應成功
    ↓
如果是 Bot Session，顯示 Thinking Indicator
    ↓
等待 WebSocket "message.received" 事件觸發
    ↓
收到 Bot 回覆訊息
```

### 5. Session 變更流程（Bot → 真人）

```
WebSocket 收到 "session.changed" 事件
    ↓
ChatWebSocketManager 解析事件
    ↓
觸發 WebSocketEventHandler.onSessionChanged(event)
    ↓
ChatViewModel.onSessionChanged(event)
    ↓
檢測 isBot 從 true → false
    ↓
追蹤事件：trackMonitorCsContactPgChatbotToHuman()
    ↓
更新 UI（顯示真人客服頭像/名稱）
```

### 6. 載入歷史訊息流程（分頁）

```
使用者向上滑動到頂部
    ↓
ChatScreen 偵測 scrollState.value == 0
    ↓
ChatViewModel.loadHistoryMessages(isLatest=false)
    ↓
使用 nextCursor 載入更早的訊息
    ↓
ChatRepository.getMessageHistory(orderMid, cursor=nextCursor)
    ↓
取得歷史訊息列表
    ↓
插入到訊息列表最前面
    ↓
保持滾動位置（不跳到底部）
```

### 7. 連線錯誤處理流程

```
WebSocket 連線錯誤或斷線
    ↓
ChatWebSocketManager 觸發 onConnectionError()
    ↓
ChatViewModel.onConnectionError(error)
    ↓
更新 connectionEventState = CONNECTION_ERROR
    ↓
UI 顯示「重新連線」按鈕
    ↓
使用者點擊重新連線
    ↓
ChatViewModel.reinitialize()
    ↓
重新執行初始化流程
```

---

## WebSocket 事件用途

### 1. `message.received`
- **事件名稱**: `"message.received"`
- **用途**: 通知有新訊息到達
- **處理邏輯**:
  - 移除 Thinking Indicator
  - 呼叫 `getMessageHistory` API 取得最新訊息
  - 更新 UI 顯示新訊息
- **觸發時機**: Bot 或真人客服發送訊息時

### 2. `message.delivered`
- **事件名稱**: `"message.delivered"`
- **用途**: 通知訊息已送達（目前保留，不做處理）
- **觸發時機**: 訊息送達時

### 3. `session.closed`
- **事件名稱**: `"session.closed"`
- **用途**: 通知 Session 已關閉（對話終止）
- **處理邏輯**:
  - 更新 `connectionEventState = SESSION_CLOSED`
  - 顯示頂部警告提示
  - 顯示底部「繼續對話」按鈕
- **觸發時機**: 客服手動關閉對話時

### 4. `control.interaction.state_changed`
- **事件名稱**: `"control.interaction.state_changed"`
- **用途**: 通知互動狀態變更（控制 UI 可用性）
- **參數**:
  - `allowText`: 是否允許輸入文字
  - `allowUploadFile`: 是否允許上傳檔案
  - `allowOpMsgAction`: 是否允許點擊訊息 Action
  - `showThinkingIndicator`: 是否顯示思考中動畫
- **處理邏輯**:
  - 更新 `ChatUiState.Success.interactionState`
  - 控制輸入欄按鈕可用性
  - 顯示/隱藏 Thinking Indicator
- **觸發時機**: Bot 處理訊息時（限制使用者操作）

### 5. `session.changed`
- **事件名稱**: `"session.changed"`
- **用途**: 通知 Session 類型變更（Bot ↔ 真人）
- **參數**:
  - `sessionOid`: Session ID
  - `isBot`: 是否為 Bot
  - `sessionableType`: Session 類型
- **處理邏輯**:
  - 更新 `ChatUiState.Success.currentSession`
  - 檢測 Bot → 真人轉換，追蹤事件
  - 更新 UI（頭像/名稱）
- **觸發時機**: 從 Bot 轉接真人客服時

### 6. `connect` / `disconnect` / `connect_error`
- **事件名稱**: SocketIO 內建事件
- **用途**: 連線狀態管理
- **處理邏輯**:
  - `connect`: 重置重連計數，通知 `onConnected()`
  - `disconnect`: 若非手動斷線，觸發 `onConnectionError()`
  - `connect_error`: 觸發 `onConnectionError()`

---

## API 用途

### 1. `GET /v3/channels/after-sales/{order_mid}/join`
- **用途**: 初始化聊天室
- **請求參數**: `order_mid` (Path)
- **回應內容**:
  - `channel_oid`: 頻道 ID
  - `notification_token`: WebSocket 認證 token
  - `has_unread_messages`: 是否有未讀訊息
  - `current_session`: 目前 Session 資訊（Bot/真人）
  - `interaction_state`: 互動狀態（UI 控制）
  - `profile`: 客服/Bot 資訊（頭像/名稱）
  - `order`: 訂單資訊
  - `supplier`: 供應商資訊
  - `app_phone`: 電話資訊
- **使用時機**: 開啟聊天頁面時

### 2. `GET /v3/channels/after-sales/{order_mid}/msg-list`
- **用途**: 取得訊息列表（支援分頁）
- **請求參數**:
  - `order_mid` (Path)
  - `cursor` (Query, 可選): 分頁游標
- **回應內容**:
  - `messages`: 訊息列表
  - `cursor.next_cursor`: 下一頁游標（null 表示無更多訊息）
- **使用時機**:
  - 初始化時載入最新訊息（cursor=null）
  - 收到 WebSocket `message.received` 時刷新
  - 使用者向上滑動載入歷史訊息（cursor=nextCursor）

### 3. `POST /v3/channels/after-sales/{order_mid}/msg-send`
- **用途**: 發送訊息（文字或檔案）
- **請求 Body**:
  ```json
  {
    "msg_category": "OT03",
    "content_type": 1,  // 1=文字, 5=檔案
    "text": "訊息內容",  // 文字訊息時使用
    "file": {           // 檔案訊息時使用
      "file_name": "example.jpg",
      "mime_type": "image/jpeg",
      "encode_file": "base64_encoded_content"
    }
  }
  ```
- **回應內容**:
  - `session_oid`: Session ID
  - `sessionable_type`: Session 類型
  - `is_bot`: 是否為 Bot
- **使用時機**: 使用者發送訊息時

### 4. `POST /v3/channels/after-sales/{order_mid}/msg-action`
- **用途**: 執行訊息 Action（List/Button 點擊）
- **請求 Body**:
  ```json
  {
    "action_type": "list",  // "list" 或 "button"
    "action_id": "action_id",
    "action_text": "選項文字",
    "action_payload": {
      "eventId": "...",
      "eventType": "...",
      "eventPayload": "..."
    }
  }
  ```
- **回應內容**: 執行結果
- **使用時機**: 使用者點擊 Chatbot List/Button 選項時

### 5. `POST /v3/channels/after-sales/{order_mid}/token`
- **用途**: 刷新 WebSocket notification token
- **請求參數**: `order_mid` (Path)
- **回應內容**:
  - `notification_token`: 新的 token
- **使用時機**: WebSocket 重連前（透過 `notificationTokenRefresher`）

---

## 資料流向

### 1. 初始化資料流
```
API Response (JoinChannelData)
    ↓ toDomain()
Domain Model (ChatInitData)
    ↓
ChatViewModel 更新 ChatUiState.Success
    ↓
UI 顯示（頭像/名稱/Session 資訊）
```

### 2. 訊息資料流
```
API Response (MessageListData)
    ↓ toDomain()
Domain Model (MessageData)
    ↓ toUi()
UI Model (MessageUiModel)
    ↓
ChatViewModel.messages StateFlow
    ↓
ChatScreen 渲染 Compose UI
```

### 3. WebSocket 事件資料流
```
WebSocket Event JSON
    ↓ SocketEventParser.parseXXX()
WebSocket Model (WSMessageReceivedEvent)
    ↓
ChatWebSocketManager 通知 WebSocketEventHandler
    ↓
ChatViewModel.onMessageReceived(event)
    ↓
觸發 API 呼叫取得最新訊息
    ↓
更新 UI
```

### 4. 發送訊息資料流
```
UI 輸入 (文字/檔案)
    ↓
ChatViewModel.sendMessage() / sendFileMessage()
    ↓
樂觀更新（立即顯示本地訊息）
    ↓
ChatRepository.sendTextMessage() / sendFileMessage()
    ↓
ChatApiService.sendMessage()
    ↓
API 回應（取得 messageUid）
    ↓
下次載入歷史訊息時 dedupe
```

---

## 重點功能說明

### 1. 樂觀更新 (Optimistic Update)
- **實作位置**: `ChatViewModel.sendMessage()` / `sendFileMessage()`
- **邏輯**: 發送訊息時立即顯示本地訊息（`messageUid=null`），不等待 API 回應
- **優點**: 提升使用者體驗，訊息立即顯示
- **處理**: 下次載入歷史訊息時，後端訊息會取代本地訊息（dedupe）

### 2. 訊息去重 (Deduplication)
- **實作位置**: `ChatViewModel.loadHistoryMessages()`
- **邏輯**: 載入最新訊息時，移除所有 `messageUid=null` 的本地訊息，用後端訊息取代
- **目的**: 確保訊息列表一致性

### 3. Thinking Indicator 三階段
- **實作位置**: `ChatViewModel.ensureThinkingIndicatorShown()`
- **階段**:
  1. **階段 1** (0-5秒): 顯示 `THINKING_INDICATOR`（LoadingDotsIndicator）
  2. **階段 2** (5-10秒): 顯示 `BotStatusLoadingItem`（hideSecondary）
  3. **階段 3** (10秒後): 顯示 `BotStatusLoadingItem`（showSecondary）
- **觸發時機**: Bot Session 且 `showThinkingIndicator=true` 時

### 4. 分頁載入歷史訊息
- **實作位置**: `ChatScreen` 偵測滾動位置 + `ChatViewModel.loadHistoryMessages(isLatest=false)`
- **邏輯**:
  - 使用者滑到頂部時，使用 `nextCursor` 載入更早訊息
  - 新訊息插入到列表最前面
  - 保持滾動位置（不跳到底部）

### 5. WebSocket 自動重連
- **實作位置**: `ChatWebSocketManager`（目前部分實作）
- **邏輯**:
  - 連線錯誤時，可設定 `notificationTokenRefresher` 刷新 token
  - 自動重連機制（可設定最大重連次數）
  - 手動斷線時不觸發重連

### 6. Session 狀態管理
- **實作位置**: `ChatViewModel` 監聽 `session.changed` 事件
- **邏輯**:
  - 檢測 Bot → 真人轉換，追蹤事件
  - 更新 UI（頭像/名稱）
  - 根據 `isBot` 決定是否顯示 Thinking Indicator

### 7. 互動狀態控制
- **實作位置**: `ChatViewModel` 監聽 `control.interaction.state_changed` 事件
- **邏輯**:
  - 根據 `allowText`、`allowUploadFile`、`allowOpMsgAction` 控制 UI 可用性
  - 根據 `showThinkingIndicator` 顯示/隱藏思考動畫

---

## 總結

售後訊息聊天系統採用 Clean Architecture 設計，清楚分離 UI、Domain、Data 三層。ViewModel 直接呼叫 Repository，業務邏輯集中在 ViewModel 中處理。透過 WebSocket 實現即時通訊，支援 Chatbot 與真人客服動態切換。系統具備完整的錯誤處理、自動重連、樂觀更新等功能，提供流暢的使用者體驗。

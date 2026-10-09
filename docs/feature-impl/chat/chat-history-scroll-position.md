# 聊天室歷史訊息載入位置保持邏輯

## 📝 功能說明

在聊天室中上滑載入歷史訊息時，保持用戶當前的視覺位置不變，避免畫面跳動或位移，提供流暢的使用體驗。

### 實現目標

- ✅ 訊息之間保持固定間距（`kkSpacing200`）
- ✅ 實現類似 RecyclerView `clipToPadding="false"` 的效果
- ✅ 沒有更多歷史時，頂部自動顯示 padding
- ✅ 載入歷史訊息後，畫面位置精確保持不變
- ✅ 滑到頂部時靈敏地觸發載入

---

## 🎯 核心實現

### 1. LazyColumn 配置

使用動態 `contentPadding` 控制頂部空間，實現 clipToPadding 效果。

```kotlin
LazyColumn(
    modifier = Modifier
        .fillMaxSize()
        .padding(
            start = kkSpacing200,      // 左側固定 padding
            end = kkSpacing200,        // 右側固定 padding
            bottom = kkSpacing200      // 底部固定 padding
        ),
    state = listState,
    verticalArrangement = Arrangement.spacedBy(kkSpacing200),  // 訊息之間的間距
    contentPadding = androidx.compose.foundation.layout.PaddingValues(
        top = if (!hasMoreHistory) kkSpacing200 else 0.dp  // 動態頂部 padding
    ),
) {
    // 訊息項目...
}
```

**關鍵設計：**
- **固定 padding**：左、右、底部使用 `modifier.padding()` 固定
- **動態 padding**：頂部使用 `contentPadding` 根據 `hasMoreHistory` 動態調整
  - `hasMoreHistory = true`：頂部無 padding，訊息可滑到最頂端觸發載入
  - `hasMoreHistory = false`：頂部顯示 `kkSpacing200`，提供視覺緩衝

**視覺說明：**
```
當 hasMoreHistory = false 時：
┌────────────────┐
│ [kkSpacing200] │ ← contentPadding.top (動態新增)
│                │
│ Message A      │
│                │
│ [kkSpacing200] │ ← verticalArrangement spacing
│                │
│ Message B      │
└────────────────┘

當 hasMoreHistory = true 時：
┌────────────────┐
│                │ ← 頂部無 padding，可滑到最頂端
│ Message A      │
│                │
│ [kkSpacing200] │ ← verticalArrangement spacing
│                │
│ Message B      │
└────────────────┘
```

---

### 2. 觸發載入條件

精確檢測用戶是否滑到頂部，避免過早或過晚觸發。

```kotlin
val shouldLoadMore by remember {
    derivedStateOf {
        val firstVisibleItem = listState.firstVisibleItemIndex
        val firstVisibleOffset = listState.firstVisibleItemScrollOffset
        
        // 當滑到第一個項目且偏移量小於 100px 時觸發載入
        hasInitialized && hasMoreHistory && !isLoadingHistory &&
            firstVisibleItem == 0 && firstVisibleOffset < 100
    }
}
```

**條件說明：**
- `hasInitialized`：確保初始化完成
- `hasMoreHistory`：確認還有更多歷史可載入
- `!isLoadingHistory`：避免重複觸發
- `firstVisibleItem == 0`：滑到第一個項目
- `firstVisibleOffset < 100`：距離頂部小於 100px

---

### 3. 位置保持邏輯（核心）

使用「錨點訊息（Anchor Message）」模式保持滾動位置。

#### 流程圖

```
載入前                載入中              載入後
┌─────────┐        ┌─────────┐        ┌─────────┐
│ 記錄錨點 │──觸發→│ API 請求 │──完成→│ 恢復位置 │
└─────────┘        └─────────┘        └─────────┘
```

#### 3.1 載入前：記錄錨點狀態

```kotlin
LaunchedEffect(shouldLoadMore) {
    if (shouldLoadMore) {
        isLoadingHistory = true
        
        // 1️⃣ 記錄第一則訊息 ID（判斷是否有新資料）
        firstMessageId = items.firstOrNull()?.messageUid
        
        // 2️⃣ 記錄當前滾動位置
        val firstVisibleIndex = listState.firstVisibleItemIndex
        savedScrollOffset = listState.firstVisibleItemScrollOffset
        
        // 3️⃣ 記錄錨點訊息 ID（核心：用於載入後找回位置）
        val visibleItem = displayItems.getOrNull(firstVisibleIndex)
        anchorMessageIdForHistory = if (visibleItem is ChatDisplayItem.Message) {
            visibleItem.message.messageUid
        } else {
            items.firstOrNull()?.messageUid
        }
        
        // 4️⃣ 觸發載入
        onLoadHistory()
    }
}
```

**關鍵變數：**
- `anchorMessageIdForHistory`：當前可見的訊息 ID，恢復位置的錨點
- `savedScrollOffset`：當前的滾動偏移量（像素值）
- `firstMessageId`：載入前的第一則訊息 ID

#### 3.2 載入後：計算補償並恢復位置

```kotlin
if (isLoadingHistory && isNewMessageAtTop) {
    val anchorId = anchorMessageIdForHistory
    if (anchorId != null) {
        // 1️⃣ 重新計算 displayItems（包含新載入的訊息）
        val updatedDisplayItems = buildDisplayItems(
            items, shouldShowFAQ, faqAnchorMessageId, simpleFAQ
        )
        
        // 2️⃣ 找到錨點訊息在新列表中的索引
        val anchorIndex = updatedDisplayItems.indexOfFirst { item ->
            item is ChatDisplayItem.Message && item.message.messageUid == anchorId
        }
        
        if (anchorIndex >= 0) {
            // 3️⃣ 計算 contentPadding 變化的補償偏移量
            val topPaddingOffset = if (!hasMoreHistory) {
                // 沒有更多歷史時，頂部會新增 contentPadding
                // 需要補償：contentPadding + verticalArrangement spacing
                with(context.resources.displayMetrics) { 
                    kkSpacing200.value * density 
                }.toInt() * 2
            } else {
                0  // 還有更多歷史，無需補償
            }
            
            // 4️⃣ 滾動到錨點位置並套用補償
            listState.scrollToItem(
                index = anchorIndex,
                scrollOffset = (savedScrollOffset - topPaddingOffset).coerceAtLeast(0)
            )
        }
    }
    
    // 5️⃣ 重置狀態
    firstMessageId = currentFirstMessageId
    isLoadingHistory = false
    anchorMessageIdForHistory = null
}
```

#### 3.3 補償計算公式

```kotlin
topPaddingOffset = if (!hasMoreHistory) {
    kkSpacing200 × density × 2
} else {
    0
}

finalScrollOffset = (savedScrollOffset - topPaddingOffset).coerceAtLeast(0)
```

**為什麼乘以 2？**

當 `hasMoreHistory` 從 `true` 變為 `false` 時，會新增約兩倍 `kkSpacing200` 的空間：
1. **contentPadding.top** = `kkSpacing200`
2. **verticalArrangement.spacedBy** = `kkSpacing200`（第一個 item 前的間距）

---

## 📊 完整場景說明

### 場景 1：載入歷史訊息，還有更多歷史

```
【載入前】
- hasMoreHistory = true
- 頂部 padding = 0
- 訊息 B 在頂部，偏移量 = 50px

【載入後】
- 載入新訊息 [X, Y, Z, A, B, ...]
- hasMoreHistory = true（還有更多）
- 找到 B 的新 index = 4
- topPaddingOffset = 0（無需補償）
- 滾動到 index=4, offset=50
- ✅ 訊息 B 保持在原位置
```

### 場景 2：載入歷史訊息，沒有更多歷史

```
【載入前】
- hasMoreHistory = true
- 頂部 padding = 0
- 訊息 B 在頂部，偏移量 = 50px

【載入後】
- 載入新訊息 [A, B, ...]（已經到底）
- hasMoreHistory = false（沒有更多）
- 找到 B 的新 index = 1
- topPaddingOffset = kkSpacing200 × 2 ≈ 32px
- finalOffset = 50 - 32 = 18
- 滾動到 index=1, offset=18
- ✅ 訊息 B 在視覺上保持原位置
- ✅ 頂部自動顯示 padding
```

---

## 🎓 核心技術要點

### 1. LazyColumn 位置控制

```kotlin
// 取得當前滾動狀態
val firstVisibleItemIndex = listState.firstVisibleItemIndex
val firstVisibleItemScrollOffset = listState.firstVisibleItemScrollOffset

// 控制滾動到指定位置
listState.scrollToItem(
    index = targetIndex,
    scrollOffset = targetOffset
)
```

### 2. contentPadding vs modifier.padding

| 特性 | modifier.padding() | contentPadding |
|------|-------------------|----------------|
| 影響範圍 | 整個元件尺寸 | 內容區域 |
| 是否可滾動 | ❌ 不可滾動 | ✅ 可滾動 |
| 適用場景 | 固定邊距 | 實現 clipToPadding 效果 |

### 3. 錨點訊息模式（Anchor Message Pattern）

保持列表位置的通用模式：

1. **記錄階段**：記錄錨點項目的唯一識別（ID）和滾動偏移量
2. **變更階段**：內容發生變化（載入歷史、新增項目等）
3. **恢復階段**：在新列表中找到錨點項目，計算補償，恢復位置

### 4. 響應式狀態管理

使用 `derivedStateOf` 建立衍生狀態：

```kotlin
val shouldLoadMore by remember {
    derivedStateOf {
        // 基於其他狀態的計算
        // 當依賴的狀態改變時，自動重新計算
    }
}
```

---

## ✅ 測試驗證清單

### 功能測試

- [ ] 初次進入聊天室，自動滾動到最新訊息
- [ ] 上滑到頂部，觸發載入歷史訊息
- [ ] 載入歷史後，畫面位置保持不變
- [ ] 載入完所有歷史後，頂部顯示 padding
- [ ] 接收新訊息時，自動滾動到底部
- [ ] 送出訊息時，自動滾動到底部
- [ ] 上傳圖片/檔案時，自動滾動到底部

### 邊界測試

- [ ] 只有一則訊息時的表現
- [ ] 訊息數量很多（100+ 則）時的效能
- [ ] 快速連續上滑多次的穩定性
- [ ] 網路緩慢時的 loading 狀態顯示

---

## 🔮 優化建議

### 效能優化
- 使用 `LazyColumn` 的 `key` 參數優化重組效能
- 對於大量歷史訊息，考慮分頁載入策略

### 使用者體驗
- 加入「返回最新訊息」浮動按鈕
- 載入歷史時顯示更明顯的視覺回饋
- 支援快速滾動到特定訊息（如搜尋結果）

### 程式碼維護
- 將位置保持邏輯抽取為獨立的 use case
- 建立單元測試驗證滾動計算的正確性
- 加入效能監控，追蹤滾動恢復的耗時

---

## 📁 相關檔案

- **主要實現**：`libs/feature/chat/src/main/java/com/kkday/feature/chat/compose/ChatScreen.kt`
  - `ChatMessageColumn` 函數（載入歷史與位置保持邏輯）
  
- **支援元件**：
  - `FAQItemGroup.kt`：FAQ 顯示元件
  - `ChatBotMessageComponents.kt`：訊息顯示元件

---

## 📚 參考資料

- [Jetpack Compose LazyColumn 官方文件](https://developer.android.com/jetpack/compose/lists)
- [LazyListState API 文件](https://developer.android.com/reference/kotlin/androidx/compose/foundation/lazy/LazyListState)
- [Android RecyclerView clipToPadding](https://developer.android.com/reference/android/view/ViewGroup#attr_android:clipToPadding)

---

**文件版本：** 1.1  
**最後更新：** 2026-02-05  
**作者：** KKday Android Team


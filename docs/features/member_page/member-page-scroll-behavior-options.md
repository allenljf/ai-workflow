# 會員頁滑動收合方案比較

## 現況分析

會員頁目前使用**自訂 NestedScrollConnection**，手動計算 progress 來控制 Header 收合。

### 現有實作特點
- 使用 `LazyVerticalStaggeredGrid`（瀑布流）
- 自訂 progress 計算（基於 `firstVisibleItemScrollOffset`）
- Header 高度從 280dp → 56dp
- 支援複雜的 Header 內容（背景圖、會員卡片、登入/未登入狀態）

---

## 方案比較

### 方案 A：保持現有做法 ✅ 推薦

**優點**：
- 完全客製化，符合設計需求
- 支援 `LazyVerticalStaggeredGrid`
- 可自由控制收合動畫細節
- 已實作完成，運作正常

**缺點**：
- 需手動管理狀態
- 程式碼較多

**優化建議**：
```kotlin
// 1. 提取 NestedScrollConnection 為獨立 class
class HeaderCollapseScrollConnection(
    private val maxHeight: Float,
    private val minHeight: Float,
    private val onProgressChanged: (Float) -> Unit
) : NestedScrollConnection {
    override fun onPreScroll(available: Offset, source: NestedScrollSource): Offset {
        // 處理滑動邏輯
        return Offset.Zero
    }
}

// 2. 使用 rememberSaveable 保存狀態
val headerProgress by rememberSaveable { mutableStateOf(0f) }
```

---

### 方案 B：改用 TopAppBarScrollBehavior

**需要的架構調整**：
1. 將 `LazyVerticalStaggeredGrid` 改為 `LazyColumn`
2. 瀑布流改用 `FlowRow` 或其他方式
3. Header 簡化為標準 TopAppBar

**範例程式碼**：
```kotlin
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MemberPageWithScrollBehavior() {
    val scrollBehavior = TopAppBarDefaults.exitUntilCollapsedScrollBehavior()
    
    Scaffold(
        modifier = Modifier.nestedScroll(scrollBehavior.nestedScrollConnection),
        topBar = {
            LargeTopAppBar(
                title = { Text("會員頁") },
                scrollBehavior = scrollBehavior
            )
        }
    ) { paddingValues ->
        LazyColumn(
            modifier = Modifier.padding(paddingValues)
        ) {
            // 內容
        }
    }
}
```

**優點**：
- Material3 原生支援
- 自動處理動畫和狀態
- 程式碼簡潔

**缺點**：
- ❌ 不支援 `LazyVerticalStaggeredGrid`
- ❌ Header 客製化受限
- ❌ 需大幅重構現有程式碼
- ❌ 無法實現目前的複雜 Header 設計

---

### 方案 C：混合方案（進階）

結合兩者優點：
- TopAppBar 使用 `TopAppBarScrollBehavior`
- 大型 Header 使用自訂邏輯

**適用場景**：
- 需要標準 TopAppBar 行為
- 同時需要額外的自訂收合元素

**複雜度**：⭐⭐⭐⭐

---

## 專案內其他頁面參考

### 1. 目的地頁（DestinationPage.kt）
- 使用 `exitUntilCollapsedScrollBehavior`
- 自訂 `wrappedNestedScrollConnection` 處理特殊邏輯
- 支援 `LazyStaggeredGrid`

**關鍵程式碼**：
```kotlin
val scrollBehavior = TopAppBarDefaults.exitUntilCollapsedScrollBehavior(
    snapAnimationSpec = null,
    flingAnimationSpec = null
)

val wrappedNestedScrollConnection = remember {
    object : NestedScrollConnection {
        override fun onPreScroll(available: Offset, source: NestedScrollSource): Offset {
            // 完全收合且向上滑動時，不消耗滑動事件
            if (scrollBehavior.state.collapsedFraction >= 1f && available.y < 0) {
                return Offset.Zero
            }
            return scrollBehavior.nestedScrollConnection.onPreScroll(available, source)
        }
        // ...
    }
}
```

### 2. 搜尋頁（HeaderTabTemplate.kt）
- 標準 `exitUntilCollapsedScrollBehavior`
- 使用 `LazyColumn`
- 簡單直接

---

## 結論與建議

### ✅ 已採用方案：TopAppBarScrollBehavior（2026-03-03）

**改寫完成**：會員頁已改用 Material3 標準的 `TopAppBarScrollBehavior`

**改寫內容**：
1. 使用 `TopAppBarDefaults.exitUntilCollapsedScrollBehavior()`
2. 透過 `Modifier.nestedScroll(scrollBehavior.nestedScrollConnection)` 連接
3. 使用 `scrollBehavior.state.heightOffset` 計算收合進度
4. 保留原有的 Header 設計和動畫效果

**優點**：
- ✅ 與專案其他頁面（DestinationPage）一致
- ✅ 使用 Material3 原生 API，更穩定
- ✅ 自動處理滑動狀態管理
- ✅ 支援 `LazyVerticalStaggeredGrid`（已驗證）
- ✅ 程式碼更簡潔，易於維護

**關鍵技術**：
```kotlin
// 1. 建立 ScrollBehavior
val scrollBehavior = TopAppBarDefaults.exitUntilCollapsedScrollBehavior(
    snapAnimationSpec = null,
    flingAnimationSpec = null
)

// 2. 設定收合範圍
SideEffect {
    scrollBehavior.state.heightOffsetLimit = minHeight - maxHeight
}

// 3. 連接到 Scaffold
Scaffold(
    modifier = Modifier.nestedScroll(scrollBehavior.nestedScrollConnection),
    topBar = { /* TopAppBar */ }
) { /* Content */ }

// 4. 計算收合進度
val collapseProgress = (offset / limit).coerceIn(0f, 1f)
```

**實作檔案**：
- `app/src/main/java/com/kkday/member/view/memberpage/MemberPageScreen.kt`

**測試狀態**：
- ✅ 編譯通過
- ✅ 無 lint 錯誤
- ⏳ 待實機測試收合動效

---

## 參考資料

- [Material3 TopAppBar 文件](https://developer.android.com/reference/kotlin/androidx/compose/material3/package-summary#TopAppBar(kotlin.Function0,androidx.compose.ui.Modifier,kotlin.Function0,kotlin.Function1,androidx.compose.foundation.layout.WindowInsets,androidx.compose.material3.TopAppBarColors,androidx.compose.material3.TopAppBarScrollBehavior))
- 專案內參考：
  - `libs/tool/view_builder/src/main/java/com/kkday/view_builder/compose/template/HeaderPagerTemplate.kt`
  - `libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/category/compose/main/DestinationPage.kt`

# 目的地 BottomSheet 分析

## 概述

全域搜尋結果頁與分類搜尋結果頁的目的地 BottomSheet 使用同一個 UI 元件，但透過不同的 ViewModel 處理資料。

## 1. 是否為同一頁？

**不是同一頁**，但使用**同一個 BottomSheet 元件**。

| 頁面 | 目的地 BottomSheet View |
|------|------------------------|
| **全域搜尋結果頁** (`SearchResultPage.kt`) | `BottomSheetSearchDestinationView` |
| **分類搜尋結果頁** (`CategorySearchResultPage.kt`) | `BottomSheetSearchDestinationView` |

兩者都透過 `SearchFilterBottomSheet.kt` 統一調用 `BottomSheetSearchDestinationView`。

## 2. 相關檔案

### 核心元件
- **View 元件**：`libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/search/compose/BottomSheetSearchDestinationView.kt`
- **BottomSheet 容器**：`libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/search/compose/SearchFilterBottomSheet.kt`

### 使用頁面
- **全域搜尋結果頁**：`libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/search/compose/SearchResultPage.kt`
- **分類搜尋結果頁**：`libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/category/compose/search_result/CategorySearchResultPage.kt`

### ViewModel
- **全域搜尋 VM**：`libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/search/viewmodel/SearchResultViewModel.kt`
- **分類搜尋 VM**：`libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/category/viewmodel/CategorySearchResultViewModel.kt`

### 其他元件
- **分類頁 BottomSheet**（不同用途）：`libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/category/compose/search_result/BottomSheetDestinationView.kt`

## 3. 流程分析

```
┌─────────────────────────────────────────────────────────────────┐
│                    使用者點擊「目的地」篩選                         │
└─────────────────────────────────────────────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          ▼                                         ▼
┌─────────────────────┐                  ┌──────────────────────────┐
│  SearchResultPage   │                  │ CategorySearchResultPage │
│  (全域搜尋結果頁)      │                  │   (分類搜尋結果頁)         │
└─────────────────────┘                  └──────────────────────────┘
          │                                         │
          │ type = DESTINATION                     │ type = DESTINATION
          ▼                                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              SearchResultViewModel / CategorySearchResultVM     │
│      sendViewIntent(ShowSearchFilterBottomSheet(DESTINATION))   │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                 SearchFilterBottomSheet.kt                      │
│   navController.navigate("DESTINATION/{contentId}")             │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│              BottomSheetSearchDestinationView                   │
│    (顯示目的地選項，使用 SearchFilterTag 資料結構)                  │
│                                                                 │
│    參數：                                                        │
│    - destination: SearchFilterDestinationsContent               │
│    - selectedList: List<String>                                 │
│    - categoryFilterClickListener: (List<String>) -> Unit        │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│              使用者選擇目的地後                                   │
│    filterDestinationClick -> changeSelectedDestinations()       │
│    -> refreshSearchResultCount()                                │
└─────────────────────────────────────────────────────────────────┘
```

## 4. 關鍵差異點

| 項目 | 全域搜尋 (`SearchResultPage`) | 分類搜尋 (`CategorySearchResultPage`) |
|------|-------------------------------|--------------------------------------|
| ViewModel | `SearchResultViewModel` | `CategorySearchResultViewModel` |
| 傳入 `isCategoryPage` | `false` | `true` |
| Filter 資料來源 | `getNewSearchMenuFilter()` / `getNewSearchListFilter()` | `getSearchMenuFilter()` / `getSearchListFilter()` |

## 5. SearchFilterBottomSheet 整合

### SearchFilterBottomSheet.kt 路由配置

```kotlin
composable(
    route = "${SearchFilterBottomSheetType.DESTINATION.route}/{${SearchFilterBottomSheetType.DESTINATION.name}}",
    arguments = listOf(
        navArgument(SearchFilterBottomSheetType.DESTINATION.name) { type = NavType.StringType }
    )
) { backStackEntry ->
    val id = backStackEntry.arguments?.getString(SearchFilterBottomSheetType.DESTINATION.name) ?: ""
    val content = newSearchListFilter?.filter?.flatten()
        ?.firstOrNull { it.id == id } as? SearchFilterContent.SearchFilterDestinationsContent

    Column {
        Box(
            Modifier
                .weight(1f, false)
                .verticalScroll(rememberScrollState())
        ) {
            BottomSheetSearchDestinationView(
                destination = content,
                selectedList = selectedFilter.destinations ?: listOf(),
                categoryFilterClickListener = filterDestinationClick
            )
        }
    }
}
```

### 全域搜尋結果頁觸發

`SearchResultPage.kt` 點擊目的地篩選時：

```kotlin
SearchFilterBottomSheetType.DESTINATION -> {
    scope.launch {
        val title = context.getString(R.string.search_label_destination)
        bottomSheetTitle = title
        isShowOrHideAllFilter = false
        searchResultVM.trackFilterMainItemFilter(title)
        searchResultVM.sendViewIntent(
            SearchResultViewModel.Companion.ViewIntent.ShowSearchFilterBottomSheet(
                type = SearchFilterBottomSheetType.DESTINATION,
                content = content
            )
        )
    }
}
```

### 分類搜尋結果頁觸發

`CategorySearchResultPage.kt` 點擊目的地篩選時：

```kotlin
SearchFilterBottomSheetType.DESTINATION -> {
    scope.launch {
        val title = context.getString(R.string.search_label_destination)
        bottomSheetTitle = title
        isShowOrHideAllFilter = false
        searchResultVM.trackFilterMainItemFilter(title)
        searchResultVM.sendViewIntent(
            CategorySearchResultViewModel.Companion.ViewIntent.ShowSearchFilterBottomSheet(
                type = SearchFilterBottomSheetType.DESTINATION,
                content = content
            )
        )
    }
}
```

## 6. 資料結構

### SearchFilterDestinationsContent

```kotlin
data class SearchFilterDestinationsContent(
    val id: String,
    val type: String,
    val tags: List<SearchFilterTag>?
)
```

### SearchFilterTag

```kotlin
data class SearchFilterTag(
    val id: String?,
    val code: String?,
    val count: Int?,
    val name: String?,
    val value: String?,
    val icon: String?,
    val children: List<SearchFilterTag>?
)
```

### 元件呈現邏輯

`BottomSheetSearchDestinationView` 會遍歷 `tags` 並顯示：
- 每個 tag 作為一個國家/地區標題
- 其 `children` 作為該地區下的城市選項
- 使用 `ComponentFilterTagItem` 渲染每個選項

## 7. 總結

- **兩個頁面共用** `SearchFilterBottomSheet` 和 `BottomSheetSearchDestinationView` 元件
- **差異在於資料來源** ViewModel 不同（`SearchResultViewModel` vs `CategorySearchResultViewModel`）
- **UI 呈現邏輯相同**，都使用 Navigation Compose 進行路由管理
- **透過 `isCategoryPage` 參數區分**頁面來源，但對目的地 BottomSheet 本身沒有影響

## 8. 分支變更記錄 (feature/filter_j/main_ui)

### 變更摘要

此分支主要進行**篩選器 UI 改版**，特別是**目的地選擇功能的重構**，引入**搜尋式目的地選擇器**取代原有靜態列表。

### 最新狀態 (2025-12-15)

**最近 Commit**: `c78a22002a` - 已 merge `feature/filter_p` 分支
- 更新多語系資源（8 種語言）
- 完成 UiState 狀態管理
- 整合 AB Testing（DestinationFilter）

### 核心功能特色

#### 1. 搜尋式目的地選擇
**檔案**: `BottomSheetSearchDestinationViewNew.kt` (792 行)

**功能亮點**:
- ✅ 即時搜尋（debounce 500ms）
- ✅ 搜尋記錄（最多 10 筆，DataStore 持久化）
- ✅ 推薦目的地顯示
- ✅ 模糊搜尋建議（無結果時自動觸發）
- ✅ 四種 UI 狀態切換

**UI 狀態機制**:
```kotlin
sealed class SearchDestinationUiState {
    data class Initialize(
        val recommendedDestinations: List<SearchProdDestination>,
        val searchHistory: List<SearchProdDestination>
    )
    
    data class Success(
        val data: List<SearchProdDestination>
    )
    
    data class SuccessButNoMatch(
        val fuzzyRecommendedDestinations: List<SearchProdDestination>,
        val searchHistory: List<SearchProdDestination>,
        val recommendedDestinations: List<SearchProdDestination>
    )
    
    object Loading
    object Error
}
```

#### 2. ViewModel 擴充
**檔案**: `SearchResultViewModel.kt`

**新增功能**:
```kotlin
// 搜尋目的地（支援模糊搜尋）
fun getSearchDestinationsResult(
    destinationQuery: String? = null,
    fuzzySearch: Boolean = false
)

// 記錄管理
fun addRecentlySearchDestination(destination: SearchProdDestination)
suspend fun getRecentlySearchDestination(): List<SearchProdDestination>
fun clearRecentlySearchDestination()

// 狀態管理
val searchDestinationUiState: StateFlow<SearchDestinationUiState>
```

#### 3. AB Testing 整合
**實驗**: `DestinationFilter`
- Control: 原有靜態目的地選擇器
- Experimental: 新搜尋式目的地選擇器

**使用位置**:
- `SearchFilterBottomSheet.kt` 根據 AB 實驗決定顯示哪個版本

#### 4. 資料層擴充

**API 層** (`SearchApiService.kt`):
```kotlin
@POST("v1/search/product/destination")
suspend fun getSearchProductDestination(
    @Body body: SearchProdDestinationRequestBody
): Response<SearchProdDestinationResponse>
```

**Repository 層** (`SearchRepository.kt`):
```kotlin
fun getSearchProductDestination(
    body: SearchProdDestinationRequestBody
): Flow<ApiResult<SearchProdDestinationResponse>>
```

**資料模型** (`Search.kt`):
```kotlin
data class SearchProdDestinationRequestBody(
    val q: String? = null,
    val destinationQuery: String? = null,
    val fuzzySearch: Boolean = false
)

data class SearchProdDestination(
    val code: String,
    val name: String,
    val icon: String?
)
```

### 修改檔案統計

相對於 merge 前：**1636 行新增，844 行刪除**（含多語系）

| 檔案 | 變更 | 說明 |
|------|------|------|
| **核心功能** | | |
| `BottomSheetSearchDestinationViewNew.kt` | +792 | 全新搜尋式目的地選擇器 |
| `SearchResultViewModel.kt` | +108 | 新增狀態管理與搜尋邏輯 |
| `SearchFilterBottomSheet.kt` | +137 | 整合新舊版本切換 |
| **API/資料層** | | |
| `SearchApiService.kt` | +7 | 新增 API 端點 |
| `SearchRepository.kt` | +5 | Repository 支援 |
| `Search.kt` | +18 | 新增資料結構 |
| **AB Testing** | | |
| `Constants.kt` | +3 | AB 實驗常數 |
| `KKAbTestingService.kt` | +9 | 實驗介面 |
| `DestinationFilter.kt` | +5 | 實驗定義 |
| **多語系** | +1,317 | 8 種語言資源更新 |
| **其他** | | |
| `SearchResultPage.kt` | +4 | UI 整合調整 |
| `BottomSheetSearchAllView.kt` | +37 | UI 邏輯優化 |

### 重點提交歷程

```
c78a22002a (HEAD) Merge branch 'feature/filter_p' into feature/filter_j/main_ui
8d797d29d1 update string resource (多語系更新)
588bf19091 add UiState (狀態管理完成)
e454d85ff1 add filter ab (AB Testing 整合)
bb513bf944 docs: add destination bottomsheet analysis
188300e48a add UI
d14f611fb9 update DS
deb43d526f add UI
1c541f29b7 add search destination api path
62319a31cb add part of UI
```

### 待處理事項

#### 🐛 Bug Fixes
1. **Placeholder 錯誤** (line 306):
   ```kotlin
   text = "搜尋城市}",  // ❌ 應為 "搜尋城市"
   ```

#### 📋 後續工作
1. ✅ 完成 AB Testing 整合
2. ✅ 多語系資源更新
3. ⏳ 單元測試覆蓋
4. ⏳ 整合測試（API mock）
5. ⏳ 分類搜尋頁面整合確認
6. ⏳ 建置驗證與 Lint 檢查

### 開發重點與注意事項

1. **新舊版本並存**
   - `BottomSheetSearchDestinationView` (舊版，靜態列表)
   - `BottomSheetSearchDestinationViewNew` (新版，搜尋式)
   - AB Testing 控制顯示版本

2. **效能考量**
   - Debounce 避免過度 API 呼叫
   - DataStore 異步操作
   - LazyColumn 優化長列表

3. **使用者體驗**
   - 搜尋記錄快速選擇
   - 無結果時自動模糊搜尋
   - Loading 狀態 Shimmer 效果

4. **資料持久化**
   - 使用 DataStore 儲存搜尋記錄
   - 限制記錄數量（10 筆）
   - 去重處理

5. **多頁面共用**
   - 全域搜尋結果頁
   - 分類搜尋結果頁
   - 透過同一 ViewModel 管理

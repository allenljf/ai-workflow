# 搜尋歷史與推薦關鍵字顯示邏輯分析

## 📋 概述

本文件分析 Android Member App 中「搜尋歷史」和「推薦關鍵字」的顯示邏輯，包含搜尋中繼頁 (Instant Search) 和搜尋結果頁 (Search Result)。

---

## 🔍 搜尋中繼頁 (InstantSearchFragment)

### 位置
- **Fragment:** `app/src/main/java/com/kkday/member/view/search/instant/InstantSearchFragment.kt`
- **Adapter:** `InstantSearchHotAndHistoryAdapter.kt`

### 顯示邏輯

#### 1. **搜尋歷史 (Search History)**
- **顯示條件：**
  ```kotlin
  val isShowSearchHistoryItem = searchHistories.isNotEmpty() && keyword.isEmpty()
  ```
  - ✅ 有搜尋歷史記錄
  - ✅ **且** 搜尋框為空（未輸入任何關鍵字）

- **顯示內容：**
  - 標題：「搜尋紀錄」(`R.string.search_label_history`)
  - 最多顯示：由 `PersistentManager.getSearchHistories()` 決定（預設最多 3 筆）
  - 顯示方式：水平滾動的 FlowLayout，最多 1 行
  - 右側操作：「清除紀錄」按鈕

- **UI 組件：** `SearchHistoryDelegate.kt`

#### 2. **推薦關鍵字 (Recommend Keywords)**
- **顯示條件：**
  ```kotlin
  val isShowRecommendedKeywordsItem = recommendKeywords.isNotEmpty() && keyword.isEmpty()
  ```
  - ✅ 有推薦關鍵字
  - ✅ **且** 搜尋框為空（未輸入任何關鍵字）

- **顯示內容：**
  - 標題：「熱門搜尋」(`R.string.search_keyword_hot_searches`)
  - 最多顯示：8 筆（含當前位置名稱）
  - 顯示方式：水平滾動的 FlowLayout，最多 2 行
  - 無右側操作

- **UI 組件：** `RecommendedKeywordDelegate.kt`

### 資料來源

#### API 呼叫時機
```kotlin
@AutoReducer.Action(value = SearchActions.VIEW_READY, from = SearchActions::class)
fun viewReady(state: AppState): Pair<AppState, Commands<AppState>> {
    return Pair.create(
        state.setShowNetworkUnavailableError(false),
        EpicCommands.create(
            listOf(
                NetworkApi.sharedInstance().getRecommendKeywords(
                    persistentManager.getLanguage(),
                    persistentManager.getLanguage().toLocale(persistentManager.getLanguageType()).country,
                    RECOMMEND_KEY_WORDS_DEFAULT_NUMBER
                ).map(searchActions::fetchRecommendKeywordsResult),
                // ...
            )
        )
    )
}
```

- **觸發時機：** 進入搜尋頁面時 (`VIEW_READY` action)
- **API Endpoint:** `v2/recommend/search_discover/keywords`
- **參數：**
  - `language`: 當前語言
  - `country`: 國家代碼
  - `number`: 預設數量（常數 `RECOMMEND_KEY_WORDS_DEFAULT_NUMBER`）

#### 資料處理邏輯
```kotlin
@AutoReducer.Action(value = SearchActions.FETCH_RECOMMEND_KEYWORDS_RESULT, from = SearchActions::class)
fun fetchRecommendKeywordsResult(state: AppState, res: Response<RecommendKeywords>): Pair<AppState, Commands<AppState>> {
    val locationName = state.currentLocation().name
    var keywords = res.data.keywords
        .filter { it != locationName }  // 過濾掉與當前位置重複的關鍵字
        .take(8)                         // 最多 8 筆
    
    if (locationName.isNeitherNullNorEmpty()) {
        keywords = keywords.prepend(locationName)  // 將當前位置名稱加到最前面
    }
    return Pair.create(state.setRecommendKeywords(keywords))
}
```

**處理步驟：**
1. 過濾掉與當前位置名稱重複的關鍵字
2. 取前 8 筆
3. 如果當前位置名稱不為空，將它加到列表最前面
4. 更新到 AppState

### 顯示順序
在搜尋中繼頁中，顯示順序為：
1. **搜尋歷史** (如果有且 keyword 為空)
2. **推薦關鍵字** (如果有且 keyword 為空)

```kotlin
val newItems = listOf<Item<*>>()
    .plusIfValid(searchHistoryItem, isShowSearchHistoryItem)
    .plusIfValid(recommendedKeywordItem, isShowRecommendedKeywordsItem)
```

### 互動行為
- **點擊搜尋歷史：** 使用該關鍵字進行搜尋
- **點擊推薦關鍵字：** 使用該關鍵字進行搜尋
- **清除搜尋歷史：** 清空 SharedPreferences 中的搜尋記錄

---

## 📊 搜尋結果頁 (SearchResultFragment)

### 位置
- **Fragment:** `app/src/main/java/com/kkday/member/view/search/result/SearchResultFragment.kt`

### 顯示邏輯

**搜尋結果頁不顯示搜尋歷史和推薦關鍵字！**

從 `SearchResultViewInfo` 的定義可以看出：
```kotlin
data class SearchResultViewInfo(
    val searchResultTotalCount: Int,
    val products: List<B2CProductCardData>,
    val wishIds: List<Id>,
    val searchKeyword: String,
    val recommendProducts: List<B2CProductCardData>,  // 推薦商品，非推薦關鍵字
    val selectedFilterItems: SelectedFilterItems,
    val isTaiwanMarket: Boolean,
    val corrections: List<String>? = null,  // 搜尋校正詞
)
```

- ❌ 沒有 `searchHistories` 欄位
- ❌ 沒有 `recommendKeywords` 欄位
- ✅ 只有 `recommendProducts`（推薦商品）和 `corrections`（搜尋校正詞）

### 互動行為
- **點擊搜尋框：** 會切換回 `InstantSearchFragment`
  ```kotlin
  componentSearchToolBar.inputSearch.setOnTouchListener { _, event ->
      if (event.action == MotionEvent.ACTION_UP) {
          switchToInstantSearchFragment()
          true
      }
      false
  }
  ```

---

## 🔄 資料流程圖

```
┌─────────────────────────────────────────────────────────────┐
│                    進入搜尋頁面                                │
│                 (InstantSearchFragment)                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  VIEW_READY Action   │
              └──────────┬───────────┘
                         │
        ┌────────────────┴────────────────┐
        │                                 │
        ▼                                 ▼
┌───────────────────┐          ┌────────────────────────┐
│ 呼叫 API:         │          │ 讀取 SharedPreferences │
│ getRecommendKeywords│         │ getSearchHistories     │
└─────────┬─────────┘          └───────────┬────────────┘
          │                                │
          ▼                                ▼
┌───────────────────────────┐    ┌────────────────────┐
│ 處理 API 回應：            │    │ 回傳最多 3 筆      │
│ 1. 過濾重複位置           │    │ 搜尋歷史記錄       │
│ 2. 取前 8 筆              │    └────────┬───────────┘
│ 3. 加入當前位置到最前面   │             │
└───────────┬───────────────┘             │
            │                             │
            └─────────────┬───────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │  更新 AppState        │
              │  - recommendKeywords  │
              │  - searchHistories    │
              └───────────┬───────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │  UI 顯示邏輯          │
              │  if (keyword.isEmpty())│
              └───────────┬───────────┘
                          │
        ┌─────────────────┴─────────────────┐
        │                                   │
        ▼                                   ▼
┌───────────────────┐          ┌──────────────────────┐
│ 顯示搜尋歷史       │          │ 顯示推薦關鍵字        │
│ (最多 1 行)       │          │ (最多 2 行)          │
└───────────────────┘          └──────────────────────┘
```

---

## 📝 關鍵條件總結

| 項目 | 顯示頁面 | 顯示條件 | API | 最大數量 |
|------|---------|---------|-----|---------|
| **搜尋歷史** | 搜尋中繼頁 | `searchHistories.isNotEmpty() && keyword.isEmpty()` | - (本地 SharedPreferences) | 3 筆 |
| **推薦關鍵字** | 搜尋中繼頁 | `recommendKeywords.isNotEmpty() && keyword.isEmpty()` | `v2/recommend/search_discover/keywords` | 8 筆 + 當前位置 |
| **推薦商品** | 搜尋結果頁 | 搜尋結果為 0 時 | `getUserRecommendProducts` | - |

---

## 🆚 Home 頁繼續搜尋 vs 搜尋中繼頁

### 相同點
- 都使用 `v2/recommend/search_discover/keywords` API
- 都合併搜尋歷史 + 推薦關鍵字
- 都是水平滾動顯示

### 不同點

| 特性 | Home 頁繼續搜尋 | 搜尋中繼頁 |
|------|----------------|-----------|
| **顯示時機** | Toolbar 展開時 (`progress > 0.x`) **且有搜尋歷史** | `keyword.isEmpty()` |
| **前置條件** | ⚠️ **必須有搜尋歷史記錄** | 無特殊條件 |
| **API 呼叫條件** | ⚠️ **有搜尋歷史時才呼叫 API** | 進入頁面時就呼叫 |
| **搜尋歷史數量** | 3 筆 | 3 筆 |
| **推薦關鍵字數量** | 7 筆 | 8 筆 + 當前位置 |
| **總數量** | 最多 10 筆（去重） | 最多 11 筆（8 推薦 + 1 位置 + 最多顯示部分歷史） |
| **分區顯示** | ❌ 合併為單一區塊 | ✅ 分為「搜尋紀錄」和「熱門搜尋」兩區 |
| **清除功能** | ❌ 無 | ✅ 可清除搜尋歷史 |
| **UI 組件** | `ContinueSearchChips` (Compose) | `SearchHistoryDelegate` + `RecommendedKeywordDelegate` (XML View) |
| **更新時機** | 進入/Resume Home 頁（含 30 秒防抖） | 進入搜尋頁 (`VIEW_READY`) |
| **顯示行數** | 1 行（水平滾動） | 搜尋歷史 1 行 + 推薦關鍵字 2 行 |

---

## 🔧 技術實作細節

### 搜尋中繼頁使用的技術
- **架構：** MVP + Redux (Reductor)
- **狀態管理：** AppState (Redux Store)
- **UI：** XML View + RecyclerView + AdapterDelegate
- **資料儲存：** SharedPreferences (PersistentManager)

### Home 頁使用的技術
- **架構：** MVVM + UseCase
- **狀態管理：** StateFlow + UIState
- **UI：** Jetpack Compose
- **資料儲存：** SharedPreferences (PersistentManager)

---

## 💡 總結

1. **搜尋歷史和推薦關鍵字只在「搜尋中繼頁」顯示，不在「搜尋結果頁」顯示**
2. **搜尋中繼頁：顯示的前提條件是「搜尋框為空」** (`keyword.isEmpty()`)
3. **搜尋中繼頁：API `v2/recommend/search_discover/keywords` 在進入搜尋頁時呼叫一次**
4. **搜尋中繼頁：推薦關鍵字會自動將當前位置名稱加到最前面**
5. **Home 頁「繼續搜尋」：⚠️ 必須有搜尋歷史記錄才顯示和呼叫 API**
6. **Home 頁「繼續搜尋」：無搜尋歷史時，不顯示區塊也不呼叫 API（節省資源）**

---

**文件建立時間：** 2025-11-04
**相關 Ticket：** KKAPP-4576


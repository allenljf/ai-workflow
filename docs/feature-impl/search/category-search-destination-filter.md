# 分類搜尋結果頁 - 目的地篩選器開發任務

## 專案概述

**開發目標**: 在分類搜尋結果頁（`CategorySearchResultPage`）整合新版搜尋式目的地篩選器

**Figma 設計**:
- 分類搜尋結果頁 Flow: https://www.figma.com/design/tMhV3CirPyZ5W0y4d9ul2M/2025-q4-App---mWeb-%E7%9B%AE%E7%9A%84%E5%9C%B0-Filter-%E5%84%AA%E5%8C%96?node-id=999-21516&m=dev
- 分類搜尋結果頁 Spec: https://www.figma.com/design/tMhV3CirPyZ5W0y4d9ul2M/2025-q4-App---mWeb-%E7%9B%AE%E7%9A%84%E5%9C%B0-Filter-%E5%84%AA%E5%8C%96?node-id=886-20277&m=dev
- 分類落地頁: https://www.figma.com/design/tMhV3CirPyZ5W0y4d9ul2M/2025-q4-App---mWeb-%E7%9B%AE%E7%9A%84%E5%9C%B0-Filter-%E5%84%AA%E5%8C%96?node-id=1249-14939&m=dev

**開發分工**:
- ✅ 搜尋結果頁（`SearchResultPage`）- 已由 Patrick 完成
- 🔲 分類搜尋結果頁（`CategorySearchResultPage`）- 本次任務
- 🔲 分類落地頁（`CategoryPageActivity`）- 待規劃

---

## 一、API 分析

### 1.1 目的地搜尋 API 現況

根據需求，有兩隻 API 需要確認：

#### API 1: `/v3/product/search/product-destination` ❌ **不存在**

**實際實作**: `/v3/search/product_destination`

**檔案**: `SearchApiService.kt` (line 242-245)
```kotlin
@POST("v3/search/product_destination")
suspend fun getSearchProductDestination(
    @Body requestBody: SearchProdDestinationRequestBody
): B2CApiResponse<SearchProdDestinations>
```

**Request Body**:
```kotlin
data class SearchProdDestinationRequestBody(
    @SerializedName("count") val count: Int = 10,
    @SerializedName("q") val q: String? = null,
    @SerializedName("destination_query") val destinationQuery: String? = null,
    @SerializedName("fuzzy_search") val fuzzySearch: Boolean? = null,
)
```

**Response**:
```kotlin
data class SearchProdDestinations(
    @SerializedName("destinations") val destinations: List<SearchProdDestination>
)

data class SearchProdDestination(
    @SerializedName("destination_code") val code: String,
    @SerializedName("name") val name: String,
    @SerializedName("sub_name") val subName: String
)
```

**實作狀態**:
- ✅ API 介面已定義
- ✅ Request/Response Model 已建立
- ✅ Repository 層已實作（`SearchRepository.getSearchProductDestination()`）
- ✅ 搜尋結果頁已使用（`SearchResultViewModel.getSearchDestinationsResult()`）
- ❌ 分類搜尋結果頁**尚未使用**

---

#### API 2: `/v3/product/search/category-destination` ❌ **未實作**

**現況**: 此 API 在專案中**完全找不到**

**需要確認**:
1. ❓ 此 API 是否真的存在？（Swagger 文件確認）
2. ❓ 與 `/v3/search/product_destination` 有何差異？
3. ❓ 是否專門用於分類頁的目的地搜尋？

**可能情境**:
- **情境 A**: 此 API 不存在，分類頁應使用 `/v3/search/product_destination`
- **情境 B**: 此 API 存在但尚未整合，需要新增完整實作

**如果需要新增**，需要：
1. 在 `SearchApiService` 新增介面定義
2. 定義 Request/Response Model
3. 在 `SearchRepository` 新增方法
4. 在 ViewModel 中呼叫

---

### 1.2 API 使用差異分析

| 項目 | 搜尋結果頁 | 分類搜尋結果頁 | 說明 |
|------|-----------|---------------|------|
| **API** | `/v3/search/product_destination` | ❓ 應使用哪一隻？ | **需確認** |
| **Request `q`** | `_resultViewState.keyword`（使用者搜尋關鍵字） | ❓ Category slug? 還是其他？ | **需確認** |
| **Request `destination_query`** | 目的地搜尋輸入 | 同左 | ✅ 相同 |
| **Request `fuzzy_search`** | 無結果時自動觸發 | 同左 | ✅ 相同 |
| **推薦目的地** | 從 API 回傳 | ❓ 是否需要依 category 調整？ | **需確認** |

---

### 1.3 同事已完成工作（搜尋結果頁）

**檔案**: `SearchResultPage.kt` + `SearchResultViewModel.kt`

✅ **已實作功能**:
1. AB Testing 整合（`DestinationFilter.Experimental` vs `Control`）
2. 新版 UI 元件（`BottomSheetSearchDestinationViewNew`）
3. ViewModel 擴充:
   - `searchDestinationUiState: StateFlow<SearchDestinationUiState>`
   - `getSearchDestinationsResult()`
   - `addRecentlySearchDestination()`
   - `getRecentlySearchDestination()`
   - `clearRecentlySearchDestination()`
4. **API 整合**（`/v3/search/product_destination`）✅
5. 多語系資源更新（8 種語言）

**API 使用方式**:
```kotlin
// SearchResultViewModel.kt (line 733)
searchRepository.getSearchProductDestination(
    SearchProdDestinationRequestBody(
        q = _resultViewState.keyword,  // 使用者搜尋關鍵字
        destinationQuery = destinationQuery,  // 目的地搜尋輸入
        fuzzySearch = fuzzySearch  // 模糊搜尋開關
    )
)
```

**AB Testing 使用方式**:
```kotlin
// SearchResultPage.kt (line 146)
val destinationFilter = searchResultVM.abTestDestinationFilter.collectAsState()

// SearchFilterBottomSheet.kt (line 398, 526)
if (destinationFilter == DestinationFilter.Experimental) {
    // 新版搜尋式目的地選擇器
    BottomSheetSearchDestinationViewNew(...)
} else {
    // 舊版靜態列表
    BottomSheetSearchDestinationView(...)
}
```

### 1.4 共用元件現況

**共用**: `SearchFilterBottomSheet`
- 搜尋結果頁與分類搜尋結果頁都使用同一個 BottomSheet 元件
- 透過 `isCategoryPage` 參數區分來源
- 已整合 AB Testing 控制新舊版本切換

**路由配置**: 兩個目的地相關路由
1. `DESTINATION` - 從篩選 bar 點擊進入
2. `ALL_DESTINATION` - 從「全部篩選」頁面進入

---

## 二、API 整合缺失分析

### 2.1 `/v3/product/search/category-destination` API 調查結果

**🔴 重要發現**: 此 API 在專案中**完全未實作**

#### 需要確認的問題：

1. **API 是否存在？**
   - ❓ Swagger 文件中是否有此 API？
   - ❓ 後端是否已實作？
   - ❓ API 規格是什麼？

2. **與 product_destination 的差異？**
   - ❓ 專門用於分類頁嗎？
   - ❓ Request/Response 結構是否不同？
   - ❓ 回傳的目的地清單是否依 category 過濾？

3. **是否需要使用？**
   - **選項 A**: 不需要，分類頁直接使用 `/v3/search/product_destination`
   - **選項 B**: 需要，但尚未實作，需完整新增

#### 如果選項 B（需要新增），缺失項目：

**❌ 需要新增的部分**:

1. **API 介面定義** (`SearchApiService.kt`)
   ```kotlin
   @POST("v3/product/search/category-destination")  // 或正確路徑
   suspend fun getSearchCategoryDestination(
       @Body requestBody: ???RequestBody  // 需定義
   ): B2CApiResponse<???Response>  // 需定義
   ```

2. **Request Model** (`Search.kt` 或新檔案)
   ```kotlin
   data class SearchCategoryDestinationRequestBody(
       // 需確認欄位
       val productCategory: String?,
       val destinationQuery: String?,
       // ... 其他欄位
   )
   ```

3. **Response Model** (`Search.kt` 或新檔案)
   ```kotlin
   data class SearchCategoryDestinationResponse(
       // 需確認結構
       val destinations: List<???>,
       // ... 其他欄位
   )
   ```

4. **Repository 層** (`SearchRepository.kt`)
   ```kotlin
   suspend fun getSearchCategoryDestination(requestBody: ???) = safeApiCall {
       searchApi.getSearchCategoryDestination(requestBody)
   }
   ```

5. **ViewModel 使用** (`CategorySearchResultViewModel.kt`)
   ```kotlin
   fun getSearchDestinationsResult(...) {
       viewModelScope.launch {
           searchRepository.getSearchCategoryDestination(...)
           // 處理回應...
       }
   }
   ```

---

### 2.2 建議方案

#### 🎯 方案 A: 共用 `/v3/search/product_destination`（推薦）

**優點**:
- ✅ 無需新增 API 整合
- ✅ 與搜尋結果頁邏輯一致
- ✅ 開發時間短

**缺點**:
- ⚠️ 可能無法依 category 過濾目的地
- ⚠️ 推薦結果可能不夠精準

**實作重點**:
- `CategorySearchResultViewModel` 直接複用 `SearchResultViewModel` 的 API 呼叫邏輯
- 需確認 `q` 參數應傳入什麼（category slug? 或其他）

---

#### 🎯 方案 B: 新增 `/v3/product/search/category-destination`

**優點**:
- ✅ 依 category 提供更精準的目的地清單
- ✅ 符合產品需求（如果確實需要）

**缺點**:
- ❌ 需要完整 API 整合（5 個檔案修改）
- ❌ 需要後端 API 規格確認
- ❌ 開發時間長

**前置條件**:
1. 後端確認 API 已實作
2. 取得完整 API 規格文件
3. 確認 Request/Response 結構

---

## 三、搜尋結果頁 vs 分類搜尋結果頁差異分析

### 3.1 ViewModel 層差異

| 項目 | 搜尋結果頁 | 分類搜尋結果頁 | 說明 |
|------|-----------|---------------|------|
| **ViewModel** | `SearchResultViewModel` | `CategorySearchResultViewModel` | ❌ 不同 ViewModel |
| **API 整合** | ✅ `/v3/search/product_destination` | ❌ 無 | **需新增** |
| **目的地狀態** | ✅ `searchDestinationUiState` | ❌ 無 | **需新增** |
| **搜尋方法** | ✅ `getSearchDestinationsResult()` | ❌ 無 | **需新增** |
| **記錄管理** | ✅ `addRecentlySearchDestination()` 等 | ❌ 無 | **需新增** |
| **AB Testing** | ✅ `abTestDestinationFilter` | ❌ 無 | **需新增** |
| **Filter 資料** | `getNewSearchMenuFilter()` / `getNewSearchListFilter()` | `getSearchMenuFilter()` / `getSearchListFilter()` | ✅ 方法名不同但功能相同 |
| **DataStore** | ✅ 已注入 `dataStoreHelper` | ❓ 需確認 | **需檢查** |
| **SearchRepository** | ✅ 已注入 | ❓ 需確認 | **需檢查**（API 呼叫需要） |

### 3.2 UI 層差異

| 項目 | 搜尋結果頁 | 分類搜尋結果頁 | 說明 |
|------|-----------|---------------|------|
| **Page 檔案** | `SearchResultPage.kt` | `CategorySearchResultPage.kt` | 不同頁面 |
| **AB Test 讀取** | ✅ `searchResultVM.abTestDestinationFilter.collectAsState()` | ❌ 無 | **需新增** |
| **傳遞給 BottomSheet** | ✅ `destinationFilter = destinationFilter.value` | ❌ 無（使用預設 Experimental） | **需修改** |
| **BottomSheet** | ✅ 共用 `SearchFilterBottomSheet` | ✅ 共用 `SearchFilterBottomSheet` | ✅ 相同 |
| **isCategoryPage** | `false` | `true` | ✅ 已正確區分 |

---

## 四、關鍵差異點與開發重點

### 4.1 API 層差異（🔴 最關鍵）

**現況**:
- 搜尋結果頁使用 `/v3/search/product_destination` ✅
- 分類搜尋頁**尚未整合任何目的地搜尋 API** ❌

**決策點**:
1. **使用相同 API** (`/v3/search/product_destination`)
   - 調整 `q` 參數傳入 category 相關資訊
   - 最快完成，邏輯一致

2. **使用獨立 API** (`/v3/product/search/category-destination`)
   - 需先確認 API 是否存在
   - 需完整實作 5 個檔案
   - 可能提供更精準的目的地清單

**👉 建議**: 先使用方案 1，如產品需求確認需要方案 2 再擴充

---

### 4.2 ViewModel 層差異

#### 🔴 **需要在分類搜尋頁新增的功能**:

1. **ViewModel 擴充**（`CategorySearchResultViewModel.kt`）:
   ```kotlin
   // 1. AB Testing 支援
   private var _abTestDestinationFilter = MutableStateFlow<DestinationFilter>(DestinationFilter.Experimental)
   val abTestDestinationFilter = _abTestDestinationFilter.asStateFlow()
   
   // 2. 搜尋狀態管理
   private val _searchDestinationUiState = MutableStateFlow<SearchDestinationUiState>(...)
   val searchDestinationUiState = _searchDestinationUiState.asStateFlow()
   
   // 3. 搜尋方法
   fun getSearchDestinationsResult(destinationQuery: String? = null, fuzzySearch: Boolean = false)
   
   // 4. 記錄管理
   fun addRecentlySearchDestination(destination: SearchProdDestination)
   suspend fun getRecentlySearchDestination(): List<SearchProdDestination>
   fun clearRecentlySearchDestination()
   ```

2. **UI 層調整**（`CategorySearchResultPage.kt`）:
   ```kotlin
   // 讀取 AB Test 狀態
   val destinationFilter = searchResultVM.abTestDestinationFilter.collectAsState()
   
   // 傳遞給 SearchFilterBottomSheet
   SearchFilterBottomSheet(
       // ... 其他參數
       destinationFilter = destinationFilter.value // 新增
   )
   ```

3. **DI 注入檢查**:
   - 確認 `CategorySearchResultViewModel` 是否已注入 `dataStoreHelper`
   - 如未注入，需要在 Koin module 中新增

#### 🟡 **需要注意的差異**（可能影響行為）:

1. **Filter 資料來源方法名不同**:
   - 搜尋頁: `getNewSearchMenuFilter()` / `getNewSearchListFilter()`
   - 分類頁: `getSearchMenuFilter()` / `getSearchListFilter()`
   - ⚠️ 確認這兩組方法回傳的資料結構是否一致

2. **搜尋關鍵字來源**:
   - 搜尋頁: `_resultViewState.keyword`
   - 分類頁: 需確認分類頁的關鍵字來源（可能是 category slug 或其他）

---

## 三、開發任務拆分

### Phase 1: ViewModel 層擴充（優先）

#### Task 1.1: 確認依賴注入
- [ ] 檢查 `CategorySearchResultViewModel` 建構子是否有 `dataStoreHelper`
- [ ] 如無，修改 Koin module 加入 `dataStoreHelper` 注入
- [ ] 確認是否需要注入 `searchRepository`（用於 API 呼叫）

**檔案**:
- `libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/category/viewmodel/CategorySearchResultViewModel.kt`
- `libs/feature/search_page/src/main/java/com/kkday/search_page/di/searchPageModule.kt`

---

#### Task 1.2: 新增 AB Testing 支援
- [ ] 在 ViewModel 新增 `_abTestDestinationFilter` 與 `abTestDestinationFilter`
- [ ] 在 `init` 或適當時機讀取 AB Test 結果
- [ ] 參考 `SearchResultViewModel` 實作方式

**預期程式碼**:
```kotlin
private var _abTestDestinationFilter = MutableStateFlow<DestinationFilter>(
    DestinationFilter.Experimental
)
val abTestDestinationFilter = _abTestDestinationFilter.asStateFlow()

init {
    // 讀取 AB Test
    viewModelScope.launch {
        // TODO: 從 KKAbTestingService 讀取實驗結果
    }
}
```

---

#### Task 1.3: 新增搜尋目的地狀態管理
- [ ] 新增 `_searchDestinationUiState` 與 `searchDestinationUiState`
- [ ] 確認初始狀態設定

**預期程式碼**:
```kotlin
private val _searchDestinationUiState = MutableStateFlow<SearchDestinationUiState>(
    SearchDestinationUiState.Initialize(emptyList(), emptyList())
)
val searchDestinationUiState = _searchDestinationUiState.asStateFlow()
```

---

#### Task 1.4: 實作搜尋目的地方法
- [ ] 實作 `getSearchDestinationsResult()` 方法
- [ ] 處理搜尋邏輯（一般搜尋 + 模糊搜尋）
- [ ] 更新 UI 狀態（Loading/Success/SuccessButNoMatch/Error）
- [ ] ⚠️ 注意：分類頁的搜尋 query 可能與搜尋頁不同，需確認傳入參數

**預期程式碼**:
```kotlin
fun getSearchDestinationsResult(
    destinationQuery: String? = null,
    fuzzySearch: Boolean = false
) {
    viewModelScope.launch {
        // TODO: 確認分類頁的搜尋 context（keyword/category slug）
        val searchContext = ??? // 需確認
        
        searchRepository.getSearchProductDestination(
            SearchProdDestinationRequestBody(
                q = searchContext,
                destinationQuery = destinationQuery,
                fuzzySearch = fuzzySearch
            )
        ).collectInVM(this) { apiResult ->
            when (apiResult) {
                is ApiResult.Success -> {
                    val destinations = apiResult.data?.destinations ?: emptyList()
                    // 處理不同情境...
                }
                is ApiResult.Error -> {
                    _searchDestinationUiState.value = SearchDestinationUiState.Error
                }
                is ApiResult.Loading -> {
                    _searchDestinationUiState.value = SearchDestinationUiState.Loading
                }
            }
        }
    }
}
```

**⚠️ 需釐清**:
- 分類搜尋頁的 `q` 參數應該傳什麼？（category slug? keyword?）
- 是否需要額外的 filter 參數？

---

#### Task 1.5: 實作搜尋記錄管理
- [ ] 實作 `addRecentlySearchDestination()`
- [ ] 實作 `getRecentlySearchDestination()`
- [ ] 實作 `clearRecentlySearchDestination()`
- [ ] 使用 DataStore 持久化（key: `"RecentlySearchDestination"`）

**預期程式碼**:
```kotlin
fun addRecentlySearchDestination(destination: SearchProdDestination) {
    viewModelScope.launch {
        val currentList = getRecentlySearchDestination().toMutableList()
        currentList.removeAll { it.code == destination.code }
        currentList.add(0, destination)
        val limitedList = currentList.take(10)
        dataStoreHelper.setAsync("RecentlySearchDestination", limitedList)
    }
}

suspend fun getRecentlySearchDestination(): List<SearchProdDestination> {
    return dataStoreHelper.getAsync<Array<SearchProdDestination>>(
        key = "RecentlySearchDestination", 
        default = emptyArray()
    )?.toList() ?: emptyList()
}

fun clearRecentlySearchDestination() {
    viewModelScope.launch {
        dataStoreHelper.setAsync("RecentlySearchDestination", emptyList<SearchProdDestination>())
        
        when (val currentState = _searchDestinationUiState.value) {
            is SearchDestinationUiState.Initialize -> {
                _searchDestinationUiState.value = currentState.copy(searchHistory = emptyList())
            }
            is SearchDestinationUiState.SuccessButNoMatch -> {
                _searchDestinationUiState.value = currentState.copy(searchHistory = emptyList())
            }
            else -> { }
        }
    }
}
```

---

### Phase 2: UI 層整合

#### Task 2.1: 修改 CategorySearchResultPage
- [ ] 新增 AB Test 狀態讀取
- [ ] 傳遞 `destinationFilter` 參數給 `SearchFilterBottomSheet`

**檔案**: `CategorySearchResultPage.kt`

**修改位置**:
```kotlin
// 在 @Composable fun CategorySearchResultPage 內，約 line 146 附近

// 新增這行
val destinationFilter = searchResultVM.abTestDestinationFilter.collectAsState()

// 然後在 SearchFilterBottomSheet 呼叫處（約 line 503）
SearchFilterBottomSheet(
    // ... 其他參數保持不變
    destinationFilter = destinationFilter.value, // 新增此行
    // ... 後續參數
)
```

---

#### Task 2.2: 驗證 SearchFilterBottomSheet 參數傳遞
- [ ] 確認 `SearchFilterBottomSheet` 已正確接收 `destinationFilter` 參數
- [ ] 確認兩個路由都有正確的 AB Test 判斷:
  - `DESTINATION` 路由（line 398）
  - `ALL_DESTINATION` 路由（line 526）

**檔案**: `SearchFilterBottomSheet.kt`（已完成，僅需驗證）

---

### Phase 3: 測試與驗證

#### Task 3.1: 單元測試
- [ ] 為 `CategorySearchResultViewModel` 新增方法撰寫單元測試
- [ ] 測試 `getSearchDestinationsResult()` 各種情境
- [ ] 測試搜尋記錄管理功能
- [ ] 測試 AB Test 狀態管理

**檔案**: 新建 `CategorySearchResultViewModelTest.kt`

---

#### Task 3.2: 整合測試
- [ ] Mock API 回應測試搜尋流程
- [ ] 測試無結果時的模糊搜尋觸發
- [ ] 測試搜尋記錄持久化

---

#### Task 3.3: UI 測試
- [ ] 測試分類搜尋結果頁點擊「目的地」篩選
- [ ] 驗證新版 UI 正確顯示（AB Test = Experimental）
- [ ] 驗證舊版 UI 正確顯示（AB Test = Control）
- [ ] 測試搜尋功能（輸入 → debounce → 結果顯示）
- [ ] 測試搜尋記錄顯示與清除
- [ ] 測試推薦目的地顯示
- [ ] 測試無結果時的模糊搜尋建議

---

#### Task 3.4: 回歸測試
- [ ] 確認搜尋結果頁功能未受影響
- [ ] 確認分類落地頁功能未受影響
- [ ] 確認舊版目的地篩選器功能正常（Control 版本）

---

### Phase 4: 建置與發布準備

#### Task 4.1: 程式碼品質檢查
- [ ] 執行 `./gradlew detekt` 確保無 lint 錯誤
- [ ] 執行 `./gradlew lintDevelopDebug`
- [ ] 修正所有阻斷性錯誤與警告

---

#### Task 4.2: 建置驗證
- [ ] 執行 `./gradlew assembleDevelopDebug` 成功
- [ ] 執行 `./gradlew testDevelopDebugUnitTest` 全數通過
- [ ] 安裝 APK 實機測試

---

#### Task 4.3: 文件更新
- [ ] 更新 `destination_bottomsheet_analysis.md`
- [ ] 記錄分類搜尋頁的整合細節
- [ ] 記錄與搜尋結果頁的差異處理方式
- [ ] 更新 CHANGELOG（如有）

---

## 四、風險與注意事項

### 4.1 技術風險

| 風險項目 | 影響 | 緩解措施 |
|---------|------|---------|
| **DataStore 依賴未注入** | ❗ 高 | Task 1.1 優先確認，如需修改 DI 需謹慎測試 |
| **搜尋 context 參數不明確** | ❗ 高 | Task 1.4 需與 PM/後端確認分類頁應傳入什麼參數 |
| **Filter 資料結構差異** | ⚠️ 中 | 需仔細比對 `getSearchMenuFilter()` vs `getNewSearchMenuFilter()` 回傳結構 |
| **AB Test 讀取失敗** | ⚠️ 中 | 使用預設值 `Experimental`，確保新版能顯示 |
| **搜尋記錄跨頁面共用** | ⚠️ 中 | 使用相同 DataStore key，但需確認是否符合產品需求 |

### 4.2 產品需求釐清

#### 🔴 **必須釐清的問題**:

1. **搜尋 context**:
   - Q: 分類搜尋頁的目的地搜尋 API 的 `q` 參數應該傳什麼？
   - 選項 A: Category slug
   - 選項 B: 使用者輸入的關鍵字（如果有）
   - 選項 C: 空值或特定標識
   - **👉 需與後端/PM 確認**

2. **搜尋記錄共用**:
   - Q: 搜尋結果頁與分類搜尋頁的搜尋記錄是否要共用？
   - 目前實作: 共用（使用相同 DataStore key `"RecentlySearchDestination"`）
   - **👉 需與 PM 確認產品邏輯**

3. **推薦目的地來源**:
   - Q: 分類搜尋頁的推薦目的地是否與搜尋結果頁相同？
   - 可能需要根據 category 提供不同的推薦
   - **👉 需與 PM/後端確認**

4. **AB Test 實驗範圍**:
   - Q: DestinationFilter AB 實驗是否同時涵蓋搜尋結果頁與分類搜尋頁？
   - 還是分開實驗？
   - **👉 需與數據/PM 確認**

### 4.3 開發注意事項

1. **不影響舊頁面**: 
   - ✅ 已有 AB Test 機制，Control 版本會顯示舊 UI
   - 開發時確保 `DestinationFilter.Control` 路徑可正常運作

2. **程式碼複用**:
   - ViewModel 方法可參考 `SearchResultViewModel` 實作
   - 保持邏輯一致性，便於後續維護

3. **Placeholder 錯誤修正**:
   - `BottomSheetSearchDestinationViewNew.kt` line 306 有文字錯誤
   - `"搜尋城市}"` → `"搜尋城市"`
   - 可一併修正

---

## 五、時程預估

| Phase | 預估時間 | 說明 |
|-------|---------|------|
| Phase 1: ViewModel 層擴充 | 2-3 天 | 包含依賴注入檢查、方法實作 |
| Phase 2: UI 層整合 | 0.5 天 | 修改量少，主要是參數傳遞 |
| Phase 3: 測試與驗證 | 2 天 | 單元測試 + 整合測試 + UI 測試 |
| Phase 4: 建置與發布準備 | 0.5 天 | Lint、建置、文件 |
| **總計** | **5-6 天** | 不含等待需求釐清時間 |

---

## 六、檢查清單

### 開發前確認
- [ ] 已閱讀 Figma 設計稿
- [ ] 已理解搜尋結果頁與分類搜尋頁的差異
- [ ] 已釐清「搜尋 context 參數」問題
- [ ] 已確認「搜尋記錄共用」產品邏輯
- [ ] 已確認 AB Test 實驗範圍

### Phase 1 完成確認
- [ ] DataStore 依賴正確注入
- [ ] AB Test 支援已新增且可讀取
- [ ] 搜尋目的地方法已實作且邏輯正確
- [ ] 搜尋記錄管理已實作且可持久化
- [ ] 所有新增方法有對應的單元測試

### Phase 2 完成確認
- [ ] `CategorySearchResultPage` 已傳遞 `destinationFilter` 參數
- [ ] `SearchFilterBottomSheet` 接收參數正確
- [ ] AB Test 判斷邏輯已驗證

### Phase 3 完成確認
- [ ] 單元測試全數通過
- [ ] 整合測試涵蓋主要流程
- [ ] UI 測試確認新舊版本都可正常運作
- [ ] 回歸測試確認無 breaking changes

### Phase 4 完成確認
- [ ] Detekt 與 Lint 檢查通過
- [ ] 建置成功且 APK 可正常安裝
- [ ] 實機測試通過
- [ ] 文件已更新

---

## 七、參考資料

### 相關檔案
- **UI 元件**: `BottomSheetSearchDestinationViewNew.kt`
- **BottomSheet 容器**: `SearchFilterBottomSheet.kt`
- **搜尋頁 ViewModel**: `SearchResultViewModel.kt`（參考實作）
- **分類頁 ViewModel**: `CategorySearchResultViewModel.kt`（待修改）
- **搜尋頁 UI**: `SearchResultPage.kt`（參考實作）
- **分類頁 UI**: `CategorySearchResultPage.kt`（待修改）
- **AB Test 定義**: `DestinationFilter.kt`
- **API Service**: `SearchApiService.kt`
- **資料模型**: `Search.kt`

### 文件
- 分析文件: `docs/features/search/destination_bottomsheet_analysis.md`
- 專案規範: `AGENTS.md`

### Figma
- 分類搜尋結果頁 Flow: [連結](https://www.figma.com/design/tMhV3CirPyZ5W0y4d9ul2M/2025-q4-App---mWeb-%E7%9B%AE%E7%9A%84%E5%9C%B0-Filter-%E5%84%AA%E5%8C%96?node-id=999-21516&m=dev)
- 分類搜尋結果頁 Spec: [連結](https://www.figma.com/design/tMhV3CirPyZ5W0y4d9ul2M/2025-q4-App---mWeb-%E7%9B%AE%E7%9A%84%E5%9C%B0-Filter-%E5%84%AA%E5%8C%96?node-id=886-20277&m=dev)

---

## 八、API 整合總結

### 8.1 目前實作狀況

| API 路徑 | 狀態 | 使用頁面 | 說明 |
|---------|------|---------|------|
| **`/v3/search/product_destination`** | ✅ 已實作 | 搜尋結果頁 | 全域搜尋使用 |
| **`/v3/search/category_destination`** | ✅ 已新增 | 分類搜尋頁 | 本次新增 |

### 8.2 兩隻 API 的差異分析

#### `/v3/search/product_destination` (全域搜尋用)

**Request**:
```kotlin
data class SearchProdDestinationRequestBody(
    @SerializedName("count") val count: Int = 10,
    @SerializedName("q") val q: String?,                          // 全域搜尋關鍵字
    @SerializedName("destination_query") val destinationQuery: String?,
    @SerializedName("fuzzy_search") val fuzzySearch: Boolean?,
)
```

**Response**:
```kotlin
data class SearchProdDestinations(
    destinations: List<SearchProdDestination>
)

data class SearchProdDestination(
    destination_code: String,   // "D-JP-3255"
    url_name: String,            // "jp-osaka"
    name: String,                // "大阪"
    sub_name: String,            // "日本・關西"
    parent_name: String,         // "關西"
    tier1_name: String           // "日本"
)
```

---

#### `/v3/search/category_destination` (分類搜尋用)

**Request**:
```kotlin
data class SearchCategoryDestinationRequestBody(
    @SerializedName("count") val count: Int = 10,
    @SerializedName("product_category") val productCategory: String?,  // 🆕 分類標識
    @SerializedName("q") val q: String?,                               // 搜尋關鍵字（如有）
    @SerializedName("destination_query") val destinationQuery: String?,
    @SerializedName("fuzzy_search") val fuzzySearch: Boolean?,
)
```

**Response**: 與 `product_destination` **完全相同**
- 使用相同的 `SearchProdDestinations` model
- 包含相同欄位：`destination_code`, `url_name`, `name`, `sub_name`, `parent_name`, `tier1_name`

---

#### 🔍 關鍵差異

| 項目 | product_destination | category_destination |
|------|---------------------|----------------------|
| **用途** | 全域搜尋結果頁 | 分類搜尋結果頁 |
| **Request 參數** | 無 `product_category` | ✅ 有 `product_category` |
| **`q` 參數意義** | 使用者搜尋關鍵字 | 搜尋關鍵字（可能為空） |
| **回傳目的地** | 基於全域搜尋過濾 | 基於分類 + 搜尋過濾 |
| **Response Model** | ✅ 相同 | ✅ 相同 |

---

### 8.3 已實作內容

#### ✅ `/v3/search/product_destination`（搜尋結果頁）

**完整實作包含**:
1. ✅ API 介面 (`SearchApiService.kt`)
2. ✅ Request Model (`SearchProdDestinationRequestBody`)
3. ✅ Response Model (`SearchProdDestinations`, `SearchProdDestination`)
4. ✅ Repository 層 (`SearchRepository.getSearchProductDestination()`)
5. ✅ ViewModel 使用 (`SearchResultViewModel.getSearchDestinationsResult()`)

---

#### ✅ `/v3/search/category_destination`（分類搜尋頁）

**本次已新增 API 層整合**:
1. ✅ API 介面定義 (`SearchApiService.kt`)
   ```kotlin
   @POST("v3/search/category_destination")
   suspend fun getSearchCategoryDestination(
       @Body requestBody: SearchCategoryDestinationRequestBody
   ): B2CApiResponse<SearchProdDestinations>
   ```

2. ✅ Request Model (`Search.kt`)
   ```kotlin
   data class SearchCategoryDestinationRequestBody(
       val count: Int = 10,
       val productCategory: String?,  // 新增欄位
       val q: String?,
       val destinationQuery: String?,
       val fuzzySearch: Boolean?,
   )
   ```

3. ✅ Response Model (共用 `SearchProdDestinations`)
   - 已更新 `SearchProdDestination` 增加新欄位：
     - `url_name`, `parent_name`, `tier1_name`

4. ✅ Repository 層 (`SearchRepository.kt`)
   ```kotlin
   suspend fun getSearchCategoryDestination(
       requestBody: SearchCategoryDestinationRequestBody
   ) = safeApiCall {
       searchApi.getSearchCategoryDestination(requestBody)
   }
   ```

---

### 8.4 仍需實作的部分

**❌ ViewModel 層**（`CategorySearchResultViewModel`）:
1. 搜尋目的地狀態管理
2. `getSearchDestinationsResult()` 方法（呼叫 category_destination API）
3. 搜尋記錄管理
4. AB Testing 支援

**❌ UI 層**（`CategorySearchResultPage`）:
1. AB Test 參數傳遞
2. 目的地選擇器整合驗證

### 8.5 API 整合決策

**✅ 已確認**: 使用 `/v3/search/category_destination` API

**關鍵優勢**:
1. ✅ 專門為分類頁設計
2. ✅ 可傳入 `product_category` 參數，回傳更精準的目的地清單
3. ✅ API 層已完整實作（本次新增）
4. ✅ Response 與 `product_destination` 相同，可共用 UI 元件

**參數說明**:
```kotlin
SearchCategoryDestinationRequestBody(
    productCategory = "your-category-slug",  // 必填，分類標識
    q = searchKeyword,                       // 選填，搜尋關鍵字
    destinationQuery = userInput,            // 目的地搜尋輸入
    fuzzySearch = false                      // 模糊搜尋開關
)
```

---

### 8.6 開發順序（已更新）

#### ✅ Phase 0: API 層整合（已完成）
- ✅ 新增 `SearchCategoryDestinationRequestBody`
- ✅ 新增 API 介面 `getSearchCategoryDestination()`
- ✅ 新增 Repository 方法
- ✅ 更新 `SearchProdDestination` 欄位

#### 🔲 Phase 1: ViewModel 層實作（待開發）
1. 注入 `searchRepository`（如尚未注入）
2. 實作 `getSearchDestinationsResult()` 方法
   - 呼叫 `searchRepository.getSearchCategoryDestination()`
   - 傳入 `productCategory` 參數
3. 實作搜尋記錄管理
4. 實作 AB Testing 支援

#### 🔲 Phase 2: UI 層整合（待開發）
1. 傳遞 AB Test 參數給 `SearchFilterBottomSheet`
2. 驗證新舊版本切換
3. 測試目的地搜尋功能

#### 🔲 Phase 3: 測試與發布
1. 單元測試
2. 整合測試
3. UI 測試
4. 建置驗證

---

## 九、後續工作（不在本次範圍）

1. **分類落地頁**（`CategoryPageActivity`）整合
2. **其他篩選條件 BottomSheet** 優化（如有需求）
3. **效能優化**（如搜尋 debounce 調整、快取策略等）
4. **AB Test 實驗結果分析**與後續版本決策
5. **如果需要**: 完整實作 `/v3/product/search/category-destination` API

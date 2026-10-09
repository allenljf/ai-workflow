# API 整合完成摘要

## 日期：2025-12-15

## 一、API 規格確認

### 1.1 兩隻 API 差異

| API | 用途 | Request 差異 | Response |
|-----|------|------------|----------|
| `/v3/search/product_destination` | 全域搜尋結果頁 | 無 `product_category` | 相同 |
| `/v3/search/category_destination` | 分類搜尋結果頁 | ✅ 有 `product_category` | 相同 |

### 1.2 Request 結構

**product_destination**:
```json
{
  "count": 20,
  "q": "全域搜尋文字",
  "destination_query": "地點搜尋文字",
  "fuzzy_search": false
}
```

**category_destination**:
```json
{
  "count": 20,
  "product_category": "分類標識",  // 🆕 新增欄位
  "q": "搜尋文字",
  "destination_query": "地點搜尋文字",
  "fuzzy_search": false
}
```

### 1.3 Response 結構（兩者相同）

```json
{
  "data": {
    "destinations": [
      {
        "destination_code": "D-JP-3255",
        "url_name": "jp-osaka",
        "name": "大阪",
        "sub_name": "日本・關西",
        "parent_name": "關西",
        "tier1_name": "日本"
      }
    ]
  }
}
```

---

## 二、已完成的實作

### 2.1 資料模型更新

**檔案**: `libs/model/src/main/java/com/kkday/library/common/model/Search.kt`

#### ✅ 新增 Request Model
```kotlin
@Parcelize
data class SearchCategoryDestinationRequestBody(
    @SerializedName("count") val count: Int = 10,
    @SerializedName("product_category") val productCategory: String? = null,
    @SerializedName("q") val q: String? = null,
    @SerializedName("destination_query") val destinationQuery: String? = null,
    @SerializedName("fuzzy_search") val fuzzySearch: Boolean? = null,
): Parcelable
```

#### ✅ 更新 Response Model
```kotlin
@Parcelize
data class SearchProdDestination(
    @SerializedName("destination_code") private val _code: String?,
    @SerializedName("url_name") private val _urlName: String?,          // 🆕
    @SerializedName("name") private val _name: String?,
    @SerializedName("sub_name") private val _subName: String?,
    @SerializedName("parent_name") private val _parentName: String?,    // 🆕
    @SerializedName("tier1_name") private val _tier1Name: String?,      // 🆕
): Parcelable {
    val code: String get() = _code ?: ""
    val urlName: String get() = _urlName ?: ""                          // 🆕
    val name: String get() = _name ?: ""
    val subName: String get() = _subName ?: ""
    val parentName: String get() = _parentName ?: ""                    // 🆕
    val tier1Name: String get() = _tier1Name ?: ""                      // 🆕
}
```

**變更說明**:
- 新增 3 個欄位：`url_name`, `parent_name`, `tier1_name`
- 保持向下相容（使用 private + getter 模式）

---

### 2.2 API 介面定義

**檔案**: `libs/feature/search_core/src/main/java/com/kkday/search/network/SearchApiService.kt`

#### ✅ 新增 API 方法
```kotlin
@POST("v3/search/category_destination")
suspend fun getSearchCategoryDestination(
    @Body requestBody: SearchCategoryDestinationRequestBody
): B2CApiResponse<SearchProdDestinations>
```

#### ✅ 新增 Import
```kotlin
import com.kkday.library.common.model.SearchCategoryDestinationRequestBody
```

---

### 2.3 Repository 層

**檔案**: `libs/feature/search_page/src/main/java/com/kkday/search_page/domain/repository/SearchRepository.kt`

#### ✅ 新增方法
```kotlin
suspend fun getSearchCategoryDestination(
    requestBody: SearchCategoryDestinationRequestBody
) = safeApiCall {
    searchApi.getSearchCategoryDestination(requestBody)
}
```

#### ✅ 新增 Import
```kotlin
import com.kkday.library.common.model.SearchCategoryDestinationRequestBody
```

---

## 三、架構完整性

### 3.1 API 整合層級對比

| 層級 | product_destination | category_destination |
|------|---------------------|----------------------|
| **Model** | ✅ 完整 | ✅ 完整 |
| **API Service** | ✅ 完整 | ✅ 完整 |
| **Repository** | ✅ 完整 | ✅ 完整 |
| **ViewModel** | ✅ 搜尋結果頁已使用 | ❌ 分類搜尋頁待實作 |
| **UI** | ✅ 搜尋結果頁已使用 | ❌ 分類搜尋頁待實作 |

---

## 四、待完成工作

### 4.1 分類搜尋頁 ViewModel 實作

**檔案**: `CategorySearchResultViewModel.kt`

**需要新增**:
1. 注入 `searchRepository`（如尚未注入）
2. AB Testing 支援
3. 搜尋目的地狀態管理
4. `getSearchDestinationsResult()` 方法（呼叫 `category_destination` API）
5. 搜尋記錄管理方法

**參考範例**:
```kotlin
fun getSearchDestinationsResult(
    destinationQuery: String? = null,
    fuzzySearch: Boolean = false
) {
    viewModelScope.launch {
        searchRepository.getSearchCategoryDestination(
            SearchCategoryDestinationRequestBody(
                productCategory = currentCategory,  // 從 state 取得
                q = searchKeyword,                  // 搜尋關鍵字（如有）
                destinationQuery = destinationQuery,
                fuzzySearch = fuzzySearch
            )
        ).collectInVM(this) { apiResult ->
            // 處理回應...
        }
    }
}
```

---

### 4.2 分類搜尋頁 UI 整合

**檔案**: `CategorySearchResultPage.kt`

**需要修改**:
1. 讀取 AB Test 狀態
2. 傳遞 `destinationFilter` 參數給 `SearchFilterBottomSheet`

**範例**:
```kotlin
val destinationFilter = searchResultVM.abTestDestinationFilter.collectAsState()

SearchFilterBottomSheet(
    // ... 其他參數
    destinationFilter = destinationFilter.value, // 新增
    // ... 其他參數
)
```

---

## 五、關鍵差異總結

### 5.1 為什麼需要兩隻 API？

1. **分類頁需要更精準的目的地清單**
   - 根據 `product_category` 過濾
   - 只顯示該分類相關的目的地

2. **保持搜尋結果頁的通用性**
   - `product_destination` 不限定分類
   - 基於全域搜尋關鍵字過濾

### 5.2 Response 為何相同？

- 目的地資料結構一致
- 共用 UI 元件（`BottomSheetSearchDestinationViewNew`）
- 降低維護成本

### 5.3 開發時間預估

**API 層整合**：✅ 已完成（本次）
- 資料模型：✅
- API 介面：✅
- Repository：✅

**ViewModel 層**：約 2-3 天
- 參考 `SearchResultViewModel` 實作
- 調整參數傳遞

**UI 層整合**：約 0.5 天
- 參數傳遞簡單

**測試驗證**：約 2 天
- 單元測試
- 整合測試
- UI 測試

**總計**：約 4.5-5.5 天

---

## 六、驗證項目

### 6.1 建置驗證
- [x] 專案可正常編譯
- [ ] 無 lint 錯誤
- [ ] 無 detekt 錯誤

### 6.2 API 層驗證
- [x] Request Model 正確
- [x] Response Model 正確
- [x] API 介面定義正確
- [x] Repository 方法正確

### 6.3 後續驗證（待 ViewModel 實作後）
- [ ] API 可正常呼叫
- [ ] Response 解析正確
- [ ] 錯誤處理正常
- [ ] AB Test 切換正常

---

## 七、相關檔案清單

### 已修改檔案
1. `libs/model/src/main/java/com/kkday/library/common/model/Search.kt`
   - 新增 `SearchCategoryDestinationRequestBody`
   - 更新 `SearchProdDestination` 欄位

2. `libs/feature/search_core/src/main/java/com/kkday/search/network/SearchApiService.kt`
   - 新增 `getSearchCategoryDestination()` 方法
   - 新增 import

3. `libs/feature/search_page/src/main/java/com/kkday/search_page/domain/repository/SearchRepository.kt`
   - 新增 `getSearchCategoryDestination()` 方法
   - 新增 import

### 待修改檔案
1. `libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/category/viewmodel/CategorySearchResultViewModel.kt`
2. `libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/category/compose/search_result/CategorySearchResultPage.kt`
3. `libs/feature/search_page/src/main/java/com/kkday/search_page/di/searchPageModule.kt`（如需調整 DI）

---

## 八、Commit 建議

```
feat: add category destination search API integration

- Add SearchCategoryDestinationRequestBody model
- Add getSearchCategoryDestination API method
- Add Repository layer support
- Update SearchProdDestination with new fields (url_name, parent_name, tier1_name)

Related to: category search destination filter optimization
API: /v3/search/category_destination
```

---

## 九、下一步行動

1. **確認建置成功** ✅
2. **Commit API 層修改**
3. **開始實作 ViewModel 層**（參考任務文件 Phase 1）
4. **整合 UI 層**（參考任務文件 Phase 2）
5. **測試驗證**（參考任務文件 Phase 3）

---

## 十、參考文件

- 完整任務規劃：`docs/features/search/category_search_destination_filter_tasks.md`
- 分析文件：`docs/features/search/destination_bottomsheet_analysis.md`
- 專案規範：`AGENTS.md`

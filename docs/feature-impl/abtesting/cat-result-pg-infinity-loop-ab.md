# CatResultPgInfinityLoopAB 使用說明

## 📋 實驗概述

**實驗名稱**: `CatResultPgInfinityLoopAB`

**目的**: 測試在分類搜尋結果頁底部加入探索商品瀑布流的效果

**兩個組別**:
- **`InfiniteLoopOriginal`** (對照組) - 沒有探索商品區域
- **`InfiniteLoopVariant`** (實驗組) - 有探索商品瀑布流區域

---

## 🚀 使用方式

### 1. 在 ViewModel 中注入 ABTesting Service

```kotlin
import com.kkday.abtesting.KKAbTestingService
import com.kkday.abtesting.experiment.cases.CatResultPgInfinityLoopAB
import io.reactivex.disposables.CompositeDisposable

class CategorySearchResultViewModel(
    private val applicationContext: Context,
    // ... 其他依賴
): WishViewModel(applicationContext, appSharedData) {

    private val disposables = CompositeDisposable()
    
    // AB Testing 狀態
    private val _abTestVariant = MutableStateFlow<CatResultPgInfinityLoopAB>(
        CatResultPgInfinityLoopAB.InfiniteLoopOriginal
    )
    val abTestVariant: StateFlow<CatResultPgInfinityLoopAB> = _abTestVariant.asStateFlow()
    
    init {
        // 初始化 AB Testing
        initABTesting()
    }
    
    private fun initABTesting() {
        KKAbTestingService.getCatResultPgInfinityLoopAB()
            .subscribe({ variant ->
                _abTestVariant.value = variant
            }, { error ->
                // 錯誤處理，預設使用對照組
                _abTestVariant.value = CatResultPgInfinityLoopAB.InfiniteLoopOriginal
            })
            .also { disposables.add(it) }
    }
    
    override fun onCleared() {
        super.onCleared()
        disposables.clear()
    }
}
```

### 2. 在 UI 中根據 AB Testing 結果顯示內容

```kotlin
@Composable
fun CategorySearchResultScreen(
    viewModel: CategorySearchResultViewModel
) {
    val abTestVariant by viewModel.abTestVariant.collectAsState()
    val exploreProducts = viewModel.exploreProductsState.collectAsState()
        .value.collectAsLazyPagingItems()
    
    CategorySearchResultPage(
        // ... 其他參數
        
        // 根據 AB Testing 結果決定是否顯示探索商品
        exploreProducts = when (abTestVariant) {
            CatResultPgInfinityLoopAB.InfiniteLoopVariant -> exploreProducts
            CatResultPgInfinityLoopAB.InfiniteLoopOriginal -> null
        },
        
        onInitExploreItems = {
            if (abTestVariant == CatResultPgInfinityLoopAB.InfiniteLoopVariant) {
                viewModel.getInitialExploreItems()
            }
        }
    )
}
```

### 3. 條件性初始化探索商品資料

```kotlin
// 在 ViewModel 中
fun getInitialExploreItems() {
    // 只在實驗組才初始化
    if (_abTestVariant.value != CatResultPgInfinityLoopAB.InfiniteLoopVariant) {
        return
    }
    
    val destinationCode = _resultViewState.pageDestinationCode?.codeString() ?: ""
    val productCategory = _resultViewState.pageCategoryCode ?: ""

    if (destinationCode.isEmpty() || productCategory.isEmpty()) {
        return
    }

    categoryExplorePagingSource = CategoryExplorePagingSource(
        destinationCode = destinationCode,
        productCategory = productCategory,
        searchProduct = ::getRecommendDestinationCategoryExplore
    )

    categoryExplorePagingSource?.let { pagingSource ->
        _exploreProductsState.value = Pager(
            PagingConfig(
                pageSize = CategoryExplorePagingSource.PER_LIMIT,
                prefetchDistance = 20
            )
        ) {
            pagingSource
        }.flow.cachedIn(viewModelScope)
    }
}
```

---

## 🔧 Apptimize 後台設定

在 Apptimize 後台需要建立實驗：

1. **實驗名稱**: `CatResultPgInfinityLoopAB`
2. **Variants**:
   - `InfiniteLoopOriginal` (預設對照組)
   - `InfiniteLoopVariant` (實驗組)
3. **分流比例**: 建議 50% / 50%

---

## 📊 埋點追蹤

### 實驗組特定埋點

當用戶在實驗組時，會額外追蹤：

- **曝光埋點**: `CatResultPgExplore` section
- **點擊埋點**: 探索商品的點擊
- **Wish 埋點**: 探索商品的收藏

這些埋點已經在 `ProductCardTrackingUseCase` 中實作，使用 `RecommendSectionName.CAT_RESULT_PG_EXPLORE`。

---

## 🧪 測試方式

### 使用 ABTesting Debug App

1. 開啟 `libs/tool/abtesting/app`
2. 切換實驗為 `CatResultPgInfinityLoopAB`
3. 手動設定為 `InfiniteLoopOriginal` 或 `InfiniteLoopVariant`
4. 重新開啟分類搜尋結果頁面
5. 驗證對照組不顯示探索商品，實驗組顯示瀑布流

---

## ⚠️ 注意事項

1. **預設行為**: 當 ABTesting 服務初始化失敗時，預設使用 `InfiniteLoopOriginal`（對照組）
2. **網路請求**: 只有在實驗組且觸發 `onInitExploreItems()` 時才會呼叫 API
3. **效能考量**: 使用 `PagingSource` 進行分頁載入，避免一次載入過多資料
4. **上限控制**: 最多載入 1000 筆探索商品

---

## 📝 相關檔案

- **實驗定義**: `libs/tool/abtesting/kkAbtesting/src/main/java/com/kkday/abtesting/experiment/cases/CatResultPgInfinityLoopAB.kt`
- **ViewModel**: `libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/category/viewmodel/CategorySearchResultViewModel.kt`
- **UI 層**: `libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/category/compose/search_result/CategorySearchResultPage.kt`
- **PagingSource**: `libs/feature/search_page/src/main/java/com/kkday/search_page/presentation/category/compose/paging/CategoryExplorePagingSource.kt`


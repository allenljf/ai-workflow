# LazyOnFirstVisible API

## 概述

這是一個針對 Lazy 元件（LazyColumn/LazyRow）的 `onFirstVisible` 擴展實作，解決了原生 `onFirstVisible` 在虛擬化場景下可能重複觸發的問題。

## 已解決的問題

### 原始問題
- ✅ **`launch` 未解析**：添加了正確的 coroutine 導入
- ✅ **`LocalLifecycleOwner` 已棄用**：使用 `androidx.lifecycle.compose.LocalLifecycleOwner`
- ✅ **`LayoutBounds` 未解析**：移除了不必要的 `viewportBounds` 參數
- ✅ **`Timber` 未解析**：範例文件改用 `println`
- ✅ **LazyColumn `key` 參數問題**：修正為正確的 Compose 語法

### 業務問題
- ✅ **商品卡專用 API 已刪除**：保持 API 簡潔通用
- ✅ **虛擬化重複觸發**：使用全域狀態管理確保真正的「一次觸發」

## 核心組件

### 1. LazyFirstVisibleManager (全域狀態管理器)
```kotlin
object LazyFirstVisibleManager {
    suspend fun tryTrigger(scopeId: String, itemId: String): Boolean
    suspend fun clearScope(scopeId: String)
    suspend fun clearAll()
    fun getTriggeredCount(scopeId: String): Int
}
```

### 2. LazyFirstVisibleState (狀態持有者)
```kotlin
@Stable
class LazyFirstVisibleState internal constructor(private val scopeId: String) {
    suspend fun tryTrigger(itemId: String, callback: () -> Unit)
    suspend fun clearScope()
}
```

### 3. Compose API

#### 基本版本
```kotlin
fun Modifier.onFirstVisibleInLazy(
    lazyState: LazyFirstVisibleState,
    itemId: String,
    minDurationMs: Long = 0,
    minFractionVisible: Float = 0f,
    callback: () -> Unit
): Modifier
```

#### 簡化版本
```kotlin
@Composable
fun Modifier.onFirstVisibleInLazy(
    scopeId: String,
    itemId: String,
    minDurationMs: Long = 0,
    minFractionVisible: Float = 0f,
    callback: () -> Unit
): Modifier
```

#### 狀態管理便利函數
```kotlin
@Composable
fun rememberLazyFirstVisibleState(
    scopeId: String,
    clearOnDestroy: Boolean = true
): LazyFirstVisibleState

@Composable
fun LazyFirstVisibleScope(
    scopeId: String,
    clearOnRefresh: Boolean = false,
    content: @Composable (LazyFirstVisibleState) -> Unit
)
```

## 使用方式

### 基本使用（推薦）
```kotlin
LazyColumn {
    itemsIndexed(products) { index, product ->
        ProductCard(
            modifier = Modifier
                // 基本曝光：80% 可見時觸發
                .onFirstVisibleInLazy(
                    scopeId = "product_list",
                    itemId = "basic_${product.id}_$index",
                    minFractionVisible = 0.8f
                ) {
                    analytics.logBasicImpression(product.id)
                }
                // 活躍曝光：80% 可見且持續 1 秒
                .onFirstVisibleInLazy(
                    scopeId = "product_list",
                    itemId = "active_${product.id}_$index",
                    minDurationMs = 1000,
                    minFractionVisible = 0.8f
                ) {
                    analytics.logActiveImpression(product.id)
                }
        )
    }
}
```

### 使用狀態管理器
```kotlin
val lazyState = rememberLazyFirstVisibleState("product_list")

LazyColumn {
    itemsIndexed(products) { index, product ->
        ProductCard(
            modifier = Modifier.onFirstVisibleInLazy(
                lazyState = lazyState,
                itemId = product.id,
                minFractionVisible = 0.8f
            ) {
                analytics.logImpression(product.id)
            }
        )
    }
}
```

### 使用 Scope 管理
```kotlin
LazyFirstVisibleScope(
    scopeId = "product_list",
    clearOnRefresh = shouldClear
) { state ->
    LazyColumn {
        items(products) { product ->
            ProductCard(
                modifier = Modifier.onFirstVisibleInLazy(
                    lazyState = state,
                    itemId = product.id,
                    minFractionVisible = 0.8f
                ) {
                    analytics.logImpression(product.id)
                }
            )
        }
    }
}
```
## 特色

- ✅ **真正的一次觸發**：跨 attach/detach 保持狀態
- ✅ **Scope 隔離**：不同業務場景互不影響
- ✅ **自動清理**：生命週期結束時自動釋放記憶體
- ✅ **線程安全**：使用 ConcurrentHashMap 和 Mutex
- ✅ **完全兼容**：與現有 `onFirstVisible` API 保持一致
- ✅ **高性能**：最小化記憶體佔用和計算開銷
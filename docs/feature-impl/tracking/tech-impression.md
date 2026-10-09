# Android Impression Tracking 使用指南

## 概述

本指南提供 Android 應用中實現 impression tracking（曝光追蹤）的完整解決方案，涵蓋 Jetpack Compose 和 RecyclerView 兩種主要 UI 框架的實現方式。

---

## Jetpack Compose Impression Tracking

### 版本要求

⚠️ **重要**: 這些可見性追蹤修飾符需要 Compose 版本 **1.9.0-alpha03** 或更高版本才能使用。

```kotlin
// build.gradle.kts (Module: app)
dependencies {
    implementation("androidx.compose.ui:ui:1.9.0-alpha03")
    implementation("androidx.compose.ui:ui-tooling-preview:1.9.0-alpha03")
    // 其他 Compose 相關依賴也需要更新到相同版本
}
```

### 可用的修飾符

Compose 提供兩個主要的可見性追蹤修飾符：

#### 1. onFirstVisible
用於追蹤元件首次變為可見的事件，在元件生命週期中最多觸發一次。

```kotlin
Modifier.onFirstVisible(
    minDurationMs: Long = 0,
    minFractionVisible: Float = 1f,
    viewportBounds: LayoutBoundsHolder? = null,
    callback: () -> Unit
)
```

#### 2. onVisibilityChanged
用於持續監控元件的可見性變化，每次狀態改變時都會觸發。

```kotlin
Modifier.onVisibilityChanged(
    minDurationMs: Long = 0,
    minFractionVisible: Float = 1f,
    viewportBounds: LayoutBoundsHolder? = null,
    callback: (Boolean) -> Unit
)
```

### 參數說明

- **minDurationMs**: 元件需要保持可見的最小時間（毫秒）
- **minFractionVisible**: 元件需要在視窗中可見的最小比例（0.0 - 1.0）
- **viewportBounds**: 自定義視窗邊界，用於排除導航欄等 UI 元素
- **callback**: 可見性變化時的回調函數

### Compose 使用範例

#### 列表中的曝光追蹤
```kotlin
@Composable
fun ContentList(items: List<ContentItem>) {
    // 追蹤滾動狀態，只在停止時記錄曝光
    val lazyListState = rememberLazyListState()
    val isScrolling by remember { derivedStateOf { lazyListState.isScrollInProgress } }
    
    LazyColumn(state = lazyListState) {
        items(items) { item ->
            ContentCard(
                item = item,
                modifier = Modifier
                    .onFirstVisible(
                        minDurationMs = 500,
                        minFractionVisible = 0.8f
                    ) {
                        // 只有在非滾動狀態下才記錄曝光
                        if (!isScrolling) {
                            // 使用 KTM 格式記錄曝光
                            ktmTracker.trackEvent(
                                pageType = PageCommonProperty.PageType(KTMPageType.Impression),
                                pageName = PageCommonProperty.PageName(getCurrentPageName()),
                                pageComponentName = PageCommonProperty.PageComponentName("ProductCard"),
                                propertyMap = mapOf(
                                    KTMModuleType.Product to listOf(
                                        ProductProperty.ProdName(item.name),
                                        ProductProperty.ProdCategory(listOf(item.mainCategory)),
                                        ProductProperty.ProdPrice(item.priceDouble),
                                        ProductProperty.ProdDestinations(item.destinations.map { it.code.codeString() }),
                                        // 固定參數
                                        ProductProperty.TargetType("prod"),
                                        ProductProperty.EventType("view"),
                                        ProductProperty.SourceType("recommend")
                                    )
                                )
                            )
                        }
                    }
                    .onVisibilityChanged(
                        minFractionVisible = 0.5f
                    ) { isVisible ->
                        // 追蹤可見性變化（僅用於其他用途，不用於曝光追蹤）
                        if (isVisible && !isScrolling) {
                            analyticsTracker.startViewTimer(item.id)
                        } else {
                            analyticsTracker.endViewTimer(item.id)
                        }
                    }
            )
        }
    }
}
```

#### 進階 Compose 曝光追蹤（滾動停止檢測）
```kotlin
@Composable
fun ProductCardWithScrollAwareImpression(
    product: ProductItem,
    modifier: Modifier = Modifier
) {
    // 滾動狀態檢測
    val lazyListState = LocalLazyListState.current
    var hasTriggeredImpression by remember { mutableStateOf(false) }
    
    // 監聽滾動停止事件
    LaunchedEffect(lazyListState.isScrollInProgress) {
        if (!lazyListState.isScrollInProgress && !hasTriggeredImpression) {
            // 滾動停止後延遲檢查，確保真正停止
            delay(100)
            if (!lazyListState.isScrollInProgress) {
                hasTriggeredImpression = true
            }
        }
    }
    
    ProductCard(
        product = product,
        modifier = modifier
            .onFirstVisible(
                minDurationMs = 500,
                minFractionVisible = 0.8f
            ) {
                // 只有在滾動停止且未觸發過曝光時才記錄
                if (!lazyListState.isScrollInProgress && !hasTriggeredImpression) {
                    hasTriggeredImpression = true
                    trackProductImpression(product)
                }
            }
    )
}

@Composable
fun rememberScrollStoppedTracker(): Boolean {
    val lazyListState = LocalLazyListState.current
    var isScrollStopped by remember { mutableStateOf(true) }
    
    LaunchedEffect(lazyListState.isScrollInProgress) {
        if (lazyListState.isScrollInProgress) {
            isScrollStopped = false
        } else {
            // 滾動停止後等待一小段時間確保真正停止
            delay(200)
            if (!lazyListState.isScrollInProgress) {
                isScrollStopped = true
            }
        }
    }
    
    return isScrollStopped
}
```



---

## RecyclerView Impression Tracking

### 架構概述

RecyclerView impression tracking 支援兩種主要的實現方式：

1. **現代化架構（Epoxy）**：自動整合，無需額外適配
2. **傳統 Adapter**：需要實現特定介面和適配邏輯

### 核心實現

```kotlin
/**
 * RecyclerView Impression Tracker (Lifecycle-aware)
 * 
 * 用於追蹤 RecyclerView 中項目的曝光事件，支援可見度閾值和最小可見時間控制。
 * 實現 LifecycleObserver 介面，自動管理生命週期，在背景時暫停追蹤，銷毀時清理資源。
 * 
 * @param recyclerView 要追蹤的 RecyclerView
 * @param lifecycleOwner 生命週期擁有者（通常是 Activity 或 Fragment）
 * @param visibilityThreshold 可見度閾值 (0.0 - 1.0)，表示項目需要可見的比例
 * @param minDurationMs 最小可見時間（毫秒），0 表示立即觸發
 * @param impressionCallback 曝光事件回調函數
 */
class ImpressionTracker(
    private val recyclerView: RecyclerView,
    private val lifecycleOwner: LifecycleOwner,
    private var visibilityThreshold: Float = 0.8f,
    private var minDurationMs: Long = 0L,
    private var impressionCallback: ((position: Int, item: Any?) -> Unit)? = null
) : LifecycleObserver {
    
    /** 已追蹤的項目位置集合，防止重複追蹤 */
    private val trackedItems = mutableSetOf<Int>()
    
    /** 等待中的計時器任務，用於實現最小可見時間控制 */
    private val pendingItems = mutableMapOf<Int, Job>()
    
    /** 滾動監聽器，用於追蹤可見項目 */
    private var scrollListener: RecyclerView.OnScrollListener? = null
    
    /** 是否正在追蹤中 */
    private var isTracking = false
    
    init {
        // 註冊生命週期觀察者
        lifecycleOwner.lifecycle.addObserver(this)
        
        // 創建滾動監聽器
        scrollListener = object : RecyclerView.OnScrollListener() {
            override fun onScrolled(recyclerView: RecyclerView, dx: Int, dy: Int) {
                super.onScrolled(recyclerView, dx, dy)
                // 滾動中不記錄曝光，只在停止時記錄
                // 滾動時取消所有等待中的計時器
                if (isTracking) {
                    cancelAllPendingTimers()
                }
            }
            
            override fun onScrollStateChanged(recyclerView: RecyclerView, newState: Int) {
                super.onScrollStateChanged(recyclerView, newState)
                // 只有當滾動完全停止時才開始記錄曝光
                if (isTracking && newState == RecyclerView.SCROLL_STATE_IDLE) {
                    trackVisibleItems()
                }
            }
        }
    }
    
    /**
     * 生命週期事件：當進入 STARTED 狀態時開始追蹤
     */
    @OnLifecycleEvent(Lifecycle.Event.ON_START)
    private fun onStart() {
        startTracking()
    }
    
    /**
     * 生命週期事件：當進入 STOPPED 狀態時暫停追蹤
     */
    @OnLifecycleEvent(Lifecycle.Event.ON_STOP)
    private fun onStop() {
        stopTracking()
    }
    
    /**
     * 生命週期事件：當銷毀時清理所有資源
     */
    @OnLifecycleEvent(Lifecycle.Event.ON_DESTROY)
    private fun onDestroy() {
        destroy()
    }
    
    /**
     * 開始追蹤
     */
    private fun startTracking() {
        if (!isTracking) {
            isTracking = true
            scrollListener?.let { recyclerView.addOnScrollListener(it) }
            // 立即檢查當前可見項目
            trackVisibleItems()
        }
    }
    
    /**
     * 停止追蹤
     */
    private fun stopTracking() {
        if (isTracking) {
            isTracking = false
            scrollListener?.let { recyclerView.removeOnScrollListener(it) }
            // 取消所有等待中的計時器
            cancelAllPendingTimers()
        }
    }
    
    /**
     * 取消所有等待中的計時器
     * 滾動時取消所有等待中的曝光計時器
     */
    private fun cancelAllPendingTimers() {
        pendingItems.values.forEach { it.cancel() }
        pendingItems.clear()
    }
    
    /**
     * 追蹤當前可見的項目
     * 檢查可見項目並啟動或取消相應的計時器
     */
    private fun trackVisibleItems() {
        val layoutManager = recyclerView.layoutManager as? LinearLayoutManager ?: return
        
        val firstVisiblePosition = layoutManager.findFirstVisibleItemPosition()
        val lastVisiblePosition = layoutManager.findLastVisibleItemPosition()
        
        val currentVisiblePositions = mutableSetOf<Int>()
        
        // 檢查當前可見範圍內的項目
        for (position in firstVisiblePosition..lastVisiblePosition) {
            if (position == RecyclerView.NO_POSITION) continue
            
            val viewHolder = recyclerView.findViewHolderForAdapterPosition(position)
            if (viewHolder != null && isViewVisible(viewHolder.itemView)) {
                currentVisiblePositions.add(position)
                
                // 如果項目還沒有被追蹤且不在等待中，啟動計時器
                if (!trackedItems.contains(position) && !pendingItems.containsKey(position)) {
                    startImpressionTimer(position)
                }
            }
        }
        
        // 取消不再可見的項目的計時器
        val invisiblePositions = pendingItems.keys - currentVisiblePositions
        invisiblePositions.forEach { position ->
            cancelImpressionTimer(position)
        }
    }
    
    /**
     * 檢查視圖是否達到可見度閾值
     * 
     * 算法說明：
     * 1. 使用 getGlobalVisibleRect() 獲取視圖在螢幕上的可見區域
     * 2. 計算視圖總面積 = width × height
     * 3. 計算可見面積 = 可見區域的 width × height
     * 4. 計算可見比例 = 可見面積 ÷ 視圖總面積
     * 5. 判斷可見比例是否達到設定的閾值
     * 
     * 範例：
     * - 視圖大小：100×100 (總面積 = 10,000)
     * - 可見區域：100×80 (可見面積 = 8,000)
     * - 可見比例：8,000 ÷ 10,000 = 0.8 (80%)
     * - 如果閾值設為 0.8，則此視圖被認為可見
     * 
     * @param view 要檢查的視圖
     * @return 是否達到可見度閾值
     */
    private fun isViewVisible(view: View): Boolean {
        // 步驟 1: 創建 Rect 對象來接收可見區域座標
        val rect = Rect()
        
        // 步驟 2: 獲取視圖在全局座標系中的可見矩形區域
        // 如果視圖完全不可見（如被其他視圖遮擋或在螢幕外），返回 false
        val isVisible = view.getGlobalVisibleRect(rect)
        
        // 步驟 3: 基本可見性檢查
        // - isVisible: 視圖是否有任何部分可見
        // - view.width/height: 視圖尺寸檢查，避免除零錯誤
        if (!isVisible || view.width == 0 || view.height == 0) return false
        
        // 步驟 4: 計算面積比例
        val viewArea = view.width * view.height          // 視圖總面積
        val visibleArea = rect.width() * rect.height()   // 可見區域面積
        val visibilityPercentage = visibleArea.toFloat() / viewArea  // 可見比例
        
        // 步驟 5: 與閾值比較
        // 例如：visibilityThreshold = 0.8 表示需要 80% 以上可見才算曝光
        return visibilityPercentage >= visibilityThreshold
    }
    
    /**
     * 啟動曝光計時器
     * 
     * @param position 項目位置
     */
    private fun startImpressionTimer(position: Int) {
        if (minDurationMs == 0L) {
            // 立即觸發曝光事件
            trackImpression(position)
        } else {
            // 使用 lifecycleScope 啟動延遲計時器
            val job = lifecycleOwner.lifecycleScope.launch {
                delay(minDurationMs)
                trackImpression(position)
            }
            pendingItems[position] = job
        }
    }
    
    /**
     * 取消曝光計時器
     * 
     * @param position 項目位置
     */
    private fun cancelImpressionTimer(position: Int) {
        pendingItems[position]?.cancel()
        pendingItems.remove(position)
    }
    
    /**
     * 記錄曝光事件
     * 
     * @param position 項目位置
     */
    private fun trackImpression(position: Int) {
        // 防止重複追蹤
        if (trackedItems.contains(position)) return
        
        trackedItems.add(position)
        pendingItems.remove(position)
        
        // 獲取對應的數據項目
        val adapter = recyclerView.adapter
        var item: Any? = null
        
        if (adapter != null && position < adapter.itemCount) {
            item = if (adapter is ImpressionTrackableAdapter<*>) {
                adapter.getItemForImpression(position)
            } else null
        }
        
        // 觸發回調
        impressionCallback?.invoke(position, item)
        onImpressionTracked(position, item)
    }
    
    /**
     * 曝光事件處理
     * 可以在此處添加日誌記錄或其他處理邏輯
     * 
     * @param position 項目位置
     * @param item 項目數據
     */
    private fun onImpressionTracked(position: Int, item: Any?) {
        println("Item at position $position has been viewed (${(visibilityThreshold * 100).toInt()}% visible for ${minDurationMs}ms)")
    }
    
    // === 公開配置方法 ===
    
    /**
     * 設置可見度閾值
     * 
     * @param threshold 0.0 - 1.0，表示需要可見的比例
     */
    fun setVisibilityThreshold(threshold: Float) {
        require(threshold in 0.0f..1.0f) { "Visibility threshold must be between 0.0 and 1.0" }
        this.visibilityThreshold = threshold
    }
    
    /**
     * 設置最小可見時間
     * 
     * @param durationMs 毫秒，0 表示立即觸發
     */
    fun setMinDurationMs(durationMs: Long) {
        require(durationMs >= 0) { "Min duration must be non-negative" }
        this.minDurationMs = durationMs
    }
    
    /**
     * 設置曝光回調函數
     * 
     * @param callback 回調函數
     */
    fun setImpressionCallback(callback: (position: Int, item: Any?) -> Unit) {
        this.impressionCallback = callback
    }
    
    /**
     * 重置追蹤狀態
     * 通常在數據更新時調用
     */
    fun resetTracking() {
        // 取消所有等待中的計時器
        pendingItems.values.forEach { it.cancel() }
        pendingItems.clear()
        trackedItems.clear()
    }
    
    /**
     * 清理資源
     * 由生命週期自動調用，也可手動調用
     */
    fun destroy() {
        // 停止追蹤
        stopTracking()
        
        // 移除生命週期觀察者
        lifecycleOwner.lifecycle.removeObserver(this)
        
        // 清理數據
        trackedItems.clear()
        scrollListener = null
    }
}

interface ImpressionTrackableAdapter<T> {
    fun getItemForImpression(position: Int): T?
}
```

### RecyclerView Extension 函數

```kotlin
fun RecyclerView.setupImpressionTracking(
    lifecycleOwner: LifecycleOwner,
    visibilityThreshold: Float = 0.8f,
    minDurationMs: Long = 0L,
    callback: (position: Int, item: Any?) -> Unit
): ImpressionTracker {
    return ImpressionTracker(
        recyclerView = this,
        lifecycleOwner = lifecycleOwner,
        visibilityThreshold = visibilityThreshold,
        minDurationMs = minDurationMs,
        impressionCallback = callback
    )
}
```

---

## 傳統 RecyclerView Adapter 適配

### 適配步驟

#### 步驟 1: 實現 ImpressionTrackableAdapter 介面

```kotlin
interface ImpressionTrackableAdapter<T> {
    fun getItemForImpression(position: Int): T?
}

// 傳統 Adapter 必須實現此介面
class ProductCardAdapter(
    private var products: List<ProductViewInfo> = listOf()
) : RecyclerView.Adapter<ProductCardAdapter.ViewHolder>(), 
    ImpressionTrackableAdapter<ProductViewInfo> {  // 🔑 實現介面
    
    // 🔑 提供數據訪問方法
    override fun getItemForImpression(position: Int): ProductViewInfo? {
        return if (position in 0 until products.size) {
            products[position]
        } else null
    }
    
    // 其他 Adapter 方法...
}
```

#### 步驟 2: 保存 RecyclerView 引用

```kotlin
class ProductCardAdapter : RecyclerView.Adapter<ViewHolder>(), 
    ImpressionTrackableAdapter<ProductViewInfo> {
    
    private var recyclerView: RecyclerView? = null
    
    // 🔑 保存 RecyclerView 引用
    override fun onAttachedToRecyclerView(recyclerView: RecyclerView) {
        super.onAttachedToRecyclerView(recyclerView)
        this.recyclerView = recyclerView
    }
    
    override fun onDetachedFromRecyclerView(recyclerView: RecyclerView) {
        super.onDetachedFromRecyclerView(recyclerView)
        this.recyclerView = null
    }
    
    // 在需要時可以訪問 RecyclerView
    fun getRecyclerView(): RecyclerView? = recyclerView
}
```

#### 步驟 3: 外部設置 ImpressionTracker

```kotlin
class ProductListFragment : Fragment() {
    
    private lateinit var adapter: ProductCardAdapter
    private lateinit var impressionTracker: ImpressionTracker
    
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        
        // 設置 Adapter
        adapter = ProductCardAdapter()
        recyclerView.adapter = adapter
        recyclerView.layoutManager = LinearLayoutManager(requireContext())
        
        // 🔑 外部設置 ImpressionTracker（提供 LifecycleOwner）
        impressionTracker = recyclerView.setupImpressionTracking(
            lifecycleOwner = viewLifecycleOwner,  // Fragment 提供生命週期
            visibilityThreshold = 0.8f,
            minDurationMs = 500L
        ) { position, item ->
            handleProductImpression(position, item as? ProductViewInfo)
        }
    }
    
    private fun handleProductImpression(position: Int, product: ProductViewInfo?) {
        product?.let {
            // 處理商品曝光事件
            Analytics.track("product_impression", mapOf(
                "product_id" to it.id,
                "position" to position,
                "category" to it.category
            ))
        }
    }
}
```

### 完整適配範例

#### 適配後的 ProductCardAdapter

```kotlin
class ProductCardAdapter(
    private var products: List<ProductViewInfo> = listOf()
) : RecyclerView.Adapter<ProductCardAdapter.ViewHolder>(), 
    ImpressionTrackableAdapter<ProductViewInfo> {
    
    private var recyclerView: RecyclerView? = null
    private var categoryTitle = ""
    
    // === Adapter 基本方法 ===
    
    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_product_large, parent, false)
        return ViewHolder(view)
    }
    
    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.bind(products[position], position, categoryTitle)
    }
    
    override fun getItemCount(): Int = products.size
    
    // === RecyclerView 引用管理 ===
    
    override fun onAttachedToRecyclerView(recyclerView: RecyclerView) {
        super.onAttachedToRecyclerView(recyclerView)
        this.recyclerView = recyclerView
    }
    
    override fun onDetachedFromRecyclerView(recyclerView: RecyclerView) {
        super.onDetachedFromRecyclerView(recyclerView)
        this.recyclerView = null
    }
    
    // === ImpressionTrackableAdapter 實現 ===
    
    override fun getItemForImpression(position: Int): ProductViewInfo? {
        return if (position in 0 until products.size) {
            products[position]
        } else null
    }
    
    // === 數據更新方法 ===
    
    fun updateData(products: List<ProductViewInfo>, categoryTitle: String = "") {
        this.products = products
        this.categoryTitle = categoryTitle
        notifyDataSetChanged()
    }
    
    // === ViewHolder ===
    
    class ViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        fun bind(product: ProductViewInfo, position: Int, categoryTitle: String) {
            // ViewHolder 綁定邏輯
            itemView.setOnClickListener {
                product.onClickProductCardListener(
                    product.id, position + 1, categoryTitle, product.type
                )
            }
            // 其他 UI 更新邏輯...
        }
    }
}
```

### 使用範例

#### 在 Fragment 中使用適配後的 Adapter

```kotlin
class ProductListFragment : Fragment() {
    
    private lateinit var adapter: ProductCardAdapter
    private lateinit var impressionTracker: ImpressionTracker
    private lateinit var recyclerView: RecyclerView
    
    override fun onCreateView(
        inflater: LayoutInflater, 
        container: ViewGroup?, 
        savedInstanceState: Bundle?
    ): View? {
        return inflater.inflate(R.layout.fragment_product_list, container, false)
    }
    
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        
        setupRecyclerView()
        setupImpressionTracking()
        loadProducts()
    }
    
    private fun setupRecyclerView() {
        recyclerView = view?.findViewById(R.id.recyclerView) ?: return
        adapter = ProductCardAdapter()
        
        recyclerView.apply {
            adapter = this@ProductListFragment.adapter
            layoutManager = LinearLayoutManager(requireContext())
        }
    }
    
    private fun setupImpressionTracking() {
        impressionTracker = recyclerView.setupImpressionTracking(
            lifecycleOwner = viewLifecycleOwner,
            visibilityThreshold = 0.8f,
            minDurationMs = 500L
        ) { position, item ->
            handleProductImpression(position, item as? ProductViewInfo)
        }
    }
    
    private fun handleProductImpression(position: Int, product: ProductViewInfo?) {
        product?.let {
            // KTM 追蹤或其他分析工具
            ProductCardImpressionTracker.trackImpression(
                product = it,
                position = position,
                sectionName = "product_list"
            )
        }
    }
    
    private fun loadProducts() {
        // 載入商品數據
        val products = getProductList()
        adapter.updateData(products, "推薦商品")
    }
    
    override fun onDestroyView() {
        super.onDestroyView()
        // ImpressionTracker 會自動清理，無需手動調用
    }
}
```

### 適配檢查清單

在適配傳統 RecyclerView Adapter 時，請確認以下項目：

- [ ] **實現 ImpressionTrackableAdapter 介面**
  - [ ] 提供 `getItemForImpression(position: Int)` 方法
  - [ ] 確保位置邊界檢查

- [ ] **管理 RecyclerView 引用**
  - [ ] 在 `onAttachedToRecyclerView` 中保存引用
  - [ ] 在 `onDetachedFromRecyclerView` 中清理引用

- [ ] **外部設置 ImpressionTracker**
  - [ ] 在 Fragment/Activity 中提供 LifecycleOwner
  - [ ] 使用 `setupImpressionTracking` 擴展函數
  - [ ] 設置適當的可見度閾值和最小時間

- [ ] **處理數據更新**
  - [ ] 在數據變更時考慮調用 `impressionTracker.resetTracking()`
  - [ ] 確保位置索引的一致性

### RecyclerView 使用範例

#### 實現 ImpressionTrackableAdapter

```kotlin
data class MyDataItem(
    val id: String,
    val title: String,
    val description: String
)

class MyAdapter(
    private val items: List<MyDataItem>
) : RecyclerView.Adapter<MyAdapter.ViewHolder>(), ImpressionTrackableAdapter<MyDataItem> {
    
    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_layout, parent, false)
        return ViewHolder(view)
    }
    
    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.bind(items[position])
    }
    
    override fun getItemCount(): Int = items.size
    
    // 實現 ImpressionTrackableAdapter 介面
    override fun getItemForImpression(position: Int): MyDataItem? {
        return if (position in 0 until items.size) {
            items[position]
        } else null
    }
    
    class ViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val titleText: TextView = itemView.findViewById(R.id.titleText)
        private val descriptionText: TextView = itemView.findViewById(R.id.descriptionText)
        
        fun bind(item: MyDataItem) {
            titleText.text = item.title
            descriptionText.text = item.description
        }
    }
}
```

#### 基本使用
```kotlin
class MainActivity : AppCompatActivity() {
    
    private lateinit var impressionTracker: ImpressionTracker
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        val recyclerView = findViewById<RecyclerView>(R.id.recyclerView)
        
        // 設置 Adapter
        val adapter = MyAdapter(getDataItems())
        recyclerView.adapter = adapter
        recyclerView.layoutManager = LinearLayoutManager(this)
        
        // 設置曝光追蹤
        impressionTracker = recyclerView.setupImpressionTracking(
            lifecycleOwner = this,
            visibilityThreshold = 0.8f,
            minDurationMs = 1000L
        ) { position, item ->
            handleImpression(position, item)
        }
    }
    
    private fun handleImpression(position: Int, item: Any?) {
        // 使用泛型版本時，可以進行更安全的類型轉換
        val dataItem = item as? MyDataItem
        Analytics.track("item_impression", mapOf(
            "position" to position,
            "item_id" to dataItem?.id,
            "item_title" to dataItem?.title,
            "visibility" to "80%",
            "duration" to "1000ms"
        ))
    }
    
    private fun getDataItems(): List<MyDataItem> {
        return listOf(
            MyDataItem("1", "標題 1", "描述 1"),
            MyDataItem("2", "標題 2", "描述 2"),
            MyDataItem("3", "標題 3", "描述 3")
            // ... 更多項目
        )
    }
    
    // 不再需要手動調用 destroy()，生命週期會自動管理
    // override fun onDestroy() {
    //     super.onDestroy()
    //     impressionTracker.destroy()
    // }
}





---

## 總結

本指南提供了 Jetpack Compose 和 RecyclerView 兩種框架下實現 impression tracking 的完整解決方案：

### 🎯 **核心特性**
- **真實可見性檢測**：基於視圖在螢幕上的實際可見比例
- **可配置參數**：支援可見度閾值、最小時間控制
- **生命週期感知**：自動管理追蹤狀態，避免記憶體洩漏
- **防重複追蹤**：確保每個項目只被追蹤一次

開發者可以根據專案架構和需求選擇適合的實現方式，所有方案都提供一致的追蹤行為和效能表現。

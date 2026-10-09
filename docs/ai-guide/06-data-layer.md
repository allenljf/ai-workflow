# Data 層指南

> **AI 使用說明**：排查資料存取、快取、本地儲存相關問題時參考本文件。

---

## 快速摘要

| 儲存類型 | 用途 | 模組 |
|---------|------|------|
| Remote API | 主要資料來源 | `BaseApiRepository` + Retrofit |
| DataStore | 非同步偏好設定（新） | `DataStoreHelper` |
| SharedPreferences | 使用者設定、Token、快取（廣泛） | `PreferencesHelper` |
| Room | 通知歷史（Chat + Push） | `AppDatabase` |

---

## BaseApiRepository

**位置**：`libs/networking/api/src/main/java/com/kkday/library/networking/core/api/BaseApiRepository.kt`

### 核心方法

```kotlin
// 入口點：包裝 API call 為 Flow
fun <T> safeApiCall(block: suspend () -> B2CApiResponse<T>): Flow<ApiResult<T>>

// 核心邏輯：快取策略 + 錯誤處理（withContext(Dispatchers.IO)）
private suspend fun <T> safeApiCallFlow(
    cacheKey: String? = null,
    cacheBehavior: CacheBehavior? = null,
    block: suspend () -> B2CApiResponse<T>
): ApiResult<T>

// Flow extension：加入 retry policy（指數退避）
fun <T> Flow<T>.execute(retryPolicy: RetryPolicy? = null): Flow<T>

// Flow extension：加入 loading/completion emission + 錯誤捕獲
private fun <T> Flow<ApiResult<T>>.onLoadingAndCatch(): Flow<ApiResult<T>>
```

### 快取策略：CacheBehavior

**位置**：`libs/model/src/main/java/com/kkday/library/networking/core/cache/CacheBehavior.kt`

```kotlin
enum class CacheBehavior {
    CacheOnly,        // 只回傳快取，不打 API
    CacheFirst,       // 先回傳快取，再打 API 更新
    ReplaceApiError   // API 失敗時以快取取代（離線備援）
}
```

使用方式：
```kotlin
safeApiCall(
    cacheKey = "product_${productId}",
    cacheBehavior = CacheBehavior.CacheFirst
) {
    kkApi.b2cApi.product.getProductDetail(productId)
}
```

---

## 具體 Repository 範例

### MemberRepository（簡單 API 呼叫）

**位置**：`app/src/main/java/com/kkday/member/view/user/repository/MemberRepository.kt`

```kotlin
@Single
class MemberRepository(private val kkApi: KKApi) : BaseApiRepository() {
    fun getMemberTerms() = safeApiCall {
        kkApi.b2cApi.member.getMemberTerms<MemberTermsData>(TermsEvent.CHECKOUT.name)
    }
}
```

### Repository with Direct Suspend（直接回傳，非 Flow）

```kotlin
// domain contract interface
interface OrderRepository {
    suspend fun updateOrderPaymentFailed(
        orderMasterMid: String,
        paymentFailedData: PaymentFailedData
    ): B2CApiResponse<Any>
}
```

UseCase 再包裝為 Flow：
```kotlin
operator fun invoke(...) = flow {
    val response = repository.updateOrderPaymentFailed(orderMId, data)
    emit(ApiResult.success(response.data))
}
.flowOn(Dispatchers.IO)
.onStart { emit(ApiResult.loading()) }
.catch { e -> emit(ApiResult.error(...)) }
```

---

## Room 資料庫

**位置**：`data/roomDb/src/main/java/com/kkday/database/AppDatabase.kt`

```kotlin
@Database(
    entities = [
        ChatNotificationEntity::class,
        PushNotificationEntity::class,
    ],
    version = 1,
    exportSchema = false,
)
@TypeConverters(NotificationTypeConverter::class)
abstract class AppDatabase : RoomDatabase() {
    abstract fun chatNotificationDao(): ChatNotificationDao
    abstract fun pushNotificationDao(): PushNotificationDao
}
```

### Entity 清單

| Entity | 路徑 | 主要欄位 |
|--------|------|---------|
| `ChatNotificationEntity` | `data/roomDb/.../ChatNotificationEntity.kt` | `dbId`（auto）、`id`（unique index）|
| `PushNotificationEntity` | `data/roomDb/.../PushNotificationEntity.kt` | `dbId`（auto）、`id`（unique index）|

每個 Entity 提供 mapping extension（`.toChatNotificationInfo()`）轉換為 domain model。

### DAO 操作

| DAO | 主要方法 |
|-----|---------|
| `ChatNotificationDao` | `insert()`, `insertAll()`, `deleteAll()`, `markAsReadByOrderId()`, `getChatNotificationListFlow(): Flow<List<...>>` |
| `PushNotificationDao` | `insert()`, `insertAll()`, `deleteAll()`, `deleteById()`, `updatePushNotification()`, `markAllAsRead()`, `getPushNotificationListFlow(): Flow<List<...>>` |

**目前無 Migration**（version = 1）。

---

## DataStore（非同步偏好設定）

**位置**：`libs/model/src/main/java/com/kkday/data/datastore/DataStoreHelper.kt`

```kotlin
class DataStoreHelper(
    private val context: Context,
    val gson: Gson,
    private val scope: CoroutineScope,  // 注入 APP_IO_SCOPE
    dbName: String = "",
    private val maxKeyCount: Int? = null,
)
```

**主要方法**：

```kotlin
// 非同步寫入（在注入的 CoroutineScope 執行）
fun <T> setAsync(key: String, value: T)
suspend fun <T> getAsync(key: String, default: T?): T?

// 型別安全讀寫
fun <T> getClass(key: DataStoreKey<T>): T?
fun <T> setClass(key: DataStoreKey<T>, value: T)

// Reactive 讀取（回傳 Flow，適合 ViewModel 訂閱）
fun <T> getClassFlow(key: DataStoreKey<T>): Flow<T?>

// 清理
fun remove(key: String)
fun clearAll()
fun checkCountThenClearAll()  // 超過 maxKeyCount 則清除
```

**Named 注入**（`KoinConstant`）：
- `APP_DATA_STORE`：主要 DataStore 實例（使用者設定、快取）
- `APP_CATEGORY_HISTORY`：類別瀏覽歷史

---

## SharedPreferences（PreferencesHelper）

**位置**：`libs/base/src/main/java/com/kkday/library/common/storage/PreferencesHelper.kt`

覆蓋範圍（80+ 方法）：

| 類別 | 例子 |
|------|------|
| 認證 | `getUserTokenInfo()`, `saveUserTokenInfo()`, `getMemberUUID()` |
| 使用者設定 | `getLanguage()`, `getCurrency()`, `getCountryCode()` |
| API 快取 | `getProductDetailData()`, `saveProductPackagesData()` |
| 購物車 | `getCartProductInfoList()`, `saveCartProductInfo()` |
| Feature Flags | `getIsDeveloperMode()`, `getNotificationPermissionGranted()` |
| 分析數據 | `getBookingGroupId()`, `saveMissionState()` |

---

## 本地 vs 遠端資料整合模式

```
[Remote API] ─────→ safeApiCall()
                          │
             ┌────────────┼────────────┐
             ↓            ↓            ↓
        CacheOnly    CacheFirst   ReplaceApiError
             │            │            │
             ↓            ↓            ↓
     [KKNetworkingCache]──────────────→ ApiResult<T>
             ↑
    [SharedPreferences / DataStore]
    （長期持久化，不走 KKNetworkingCache）
```

**規則**：
- **網路快取**（`KKNetworkingCache`）：短效，用 `CacheBehavior` 控制
- **SharedPreferences**：長效持久化，手動讀寫
- **DataStore**：長效持久化，新功能優先使用（非同步安全）
- **Room**：可查詢的結構化資料（通知歷史）

---

*文件版本：Step 5 of AI Guide | 最後分析日期：2026-03-17*

## 相關筆記
- [01-architecture](01-architecture.md)
- [02-modules](02-modules.md)
- [03-ui-patterns](03-ui-patterns.md)
- [05-networking](05-networking.md)
- [07-concurrency](07-concurrency.md)
- [checkout](features/checkout.md)
- [order-detail-compose](features/order-detail-compose.md)
- [sku-activity-shell](features/sku-activity-shell.md)

# 網路層指南

> **AI 使用說明**：排查 API 請求失敗、Token 問題、或新增 API 時參考本文件。

---

## 快速摘要

| 項目 | 實作 |
|------|------|
| HTTP Client | Retrofit 2.x + OkHttp 4.x |
| JSON 序列化 | Gson（HTTP）+ kotlinx.serialization（WebSocket） |
| API Response 封裝 | `B2CApiResponse<T>` |
| 認證方式 | `b2c-token1` header（SHA256 簽名） |
| 即時通訊 | Socket.IO（Chat 功能） |
| Retrofit 實例 | 2 個（`RETROFIT_NAME_DEFAULT`、`RETROFIT_NAME_ENABLE_BODY_NULL`） |

---

## Retrofit 初始化

**位置**：`libs/networking/api/src/main/java/com/kkday/library/networking/core/di/networkCoreModule.kt`

```kotlin
fun provideRetrofit(okHttpClient: OkHttpClient): Retrofit {
    return Retrofit.Builder()
        .addConverterFactory(KtConverterFactory.create())  // 自訂，底層用 Gson
        .baseUrl(B2CEnvironment.appConfig.getBaseApiUrl()) // 動態 base URL
        .client(okHttpClient)
        .build()
}

fun provideOkHttpClient(...): OkHttpClient {
    return OkHttpClient().newBuilder()
        .connectionPool(ConnectionPool(5, 5, TimeUnit.SECONDS))
        .connectTimeout(B2CEnvironment.appConfig.getConnectionTimeoutSeconds(), TimeUnit.SECONDS)
        .readTimeout(B2CEnvironment.appConfig.getReadTimeoutSeconds(), TimeUnit.SECONDS)
        .addNetworkInterceptor { chain -> /* User-Agent 設定 */ }
        .addInterceptor(B2CInterceptor())           // 認證 & 簽名
        .addInterceptor(httpLoggingInterceptor)      // OkHttp 日誌
        .build()
}
```

---

## API Service 命名與結構

**命名規則**：介面以 `I` 開頭（`IHomeApiService`、`IOrderApiService`）

```kotlin
// libs/networking/api/src/main/java/com/kkday/library/networking/service/home/IHomeApiService.kt
interface IHomeApiService {
    @GET("v3/home")
    suspend fun <T> getHomepage(
        @Query("currency") currency: String,
        @Query("lang") lang: String,
        @Query("locale") countryCode: String
    ): B2CApiResponse<T>

    @POST("v2/recommend/home/popular_destinations")
    suspend fun <T> getRecommendPopularDestinations(): B2CApiResponse<T>
}

// libs/networking/api/src/main/java/com/kkday/library/networking/service/order_api/IOrderApiService.kt
interface IOrderApiService {
    @GET("v2/priority_booking/{priority_booking_oid}")
    suspend fun <T> getPriorityBooking(
        @Path("priority_booking_oid") priorityBookingOid: Int,
        @Query("product_oid") productOid: String
    ): B2CApiResponse<T>

    @PUT("v2/order/changeData/{order_mid}")
    suspend fun <T> putOrderModifyData(
        @Path("order_mid") orderMId: String,
        @Body orderModifyPutDataRequest: OrderModifyPutDataRequest
    ): B2CApiResponse<T>
}
```

**常用 Annotation**：

| Annotation | 用途 |
|-----------|------|
| `@GET` / `@POST` / `@PUT` / `@DELETE` | HTTP 方法 |
| `@Path` | URL 路徑參數 `{param}` |
| `@Query` | Query string 參數 |
| `@Body` | Request body（data class） |
| `@HeaderMap` | 動態 header map |
| `@Url` | 覆蓋 base URL（動態 URL） |

---

## Response 封裝：B2CApiResponse<T>

**位置**：`libs/model/src/main/java/com/kkday/library/networking/core/api/B2CApiResponse.kt`

```kotlin
data class B2CApiResponse<T>(
    val metadata: Metadata? = null,
    var data: T? = null,
    val dynamic: Dynamic? = null,
    val experiment: Experiment? = null,
    @SerializedName("queue_it") val queueIt: QueueItVersion? = null,
)

class Metadata(
    var type: Int,          // 錯誤類型分類
    var httpStatusCode: Int,
    var status: String,     // 伺服器狀態碼（"0000" = 成功）
    @SerializedName("desc") val desc: Any?,
    // ...
)
```

**status 碼對照**（`NetworkConstants.kt`）：

| 狀態碼 | 意義 |
|-------|------|
| `"0000"` | 成功 |
| `"100000"` | 成功（新商品） |
| `"SERVERGG"` | 系統維護升級 |
| `"M001"` | 登入 Token 失效 |
| `"P109"` | 商品已售完 |
| 50+ 其他碼 | 見 `ServerErrorCode` object |

---

## Interceptor 鏈

```
Request
  ↓
[Network Interceptor] User-Agent 設定（非 API host 略過）
  ↓
[B2CInterceptor] 注入認證 headers、SHA256 簽名、中國區 URL 路由
  ↓
[HttpLoggingInterceptor] OkHttp body 層級日誌（debug）
  ↓
[ApiLogInterceptor] 完整請求/回應持久化日誌（非 production）
  ↓
OkHttp → 網路
```

### B2CInterceptor

**位置**：`libs/networking/api/.../core/network/B2CInterceptor.kt`

- 注入 `b2c-token1` = `sha256(secret + timestamp)`
- 注入 `x-auth-token`（使用者 token）、`timestamp`、device info 等 15+ headers
- 處理中國區 API host 路由切換
- Header value 非 ASCII 字元編碼

### ApiLogInterceptor

**位置**：`libs/networking/log/.../ApiLogInterceptor.kt`

- 所有 HTTP transaction 寫入本地 DB
- 保留一週，最多 250KB body
- 僅 non-production 啟用

---

## 認證機制

**Token 類型**：

| Header | 用途 | 來源 |
|--------|------|------|
| `b2c-token1` | API 請求簽名（所有請求） | `sha256(BuildKonfig.secret + timestamp)` |
| `x-auth-token` | 使用者身份驗證 | `B2CEnvironment.userProfile.getAuthToken()` |
| `token` | 舊版 auth token | 同上 |

**Token 計算**（`libs/networking/appApiToken/`）：

```kotlin
class APITokenEncoderImpl : APITokenEncoder {
    override fun encode(timestamp: Long): String {
        return "${secretByPlatform}+${timestamp}".encodeToByteArray().sha256().hex
    }
}
```

**注意**：目前無自動 Token refresh 機制，`M001`（登入失效）需由 ViewModel 層處理導回登入頁。

---

## WebSocket（Socket.IO）

**用途**：Chat 即時訊息

**設定**（`libs/networking/api/.../websocket/ChatWebSocketManager.kt`）：

```kotlin
@Single
class ChatWebSocketManager {
    fun connect(token: String) {
        val options = IO.Options().apply {
            transports = arrayOf("websocket")
            auth = mapOf("token" to token)
            reconnection = true
            reconnectionDelay = 3000
            reconnectionAttempts = Integer.MAX_VALUE
        }
        socket = IO.socket(baseUri, options)
    }
}
```

**事件對照**（`SocketEventParser.kt`）：

| Socket 事件 | Kotlin 類別 |
|------------|------------|
| `message.received` | `WSMessageReceivedEvent` |
| `message.delivered` | `WSMessageDeliveredEvent` |
| `session.closed` | `WSSessionClosedEvent` |
| `control.interaction.state_changed` | `WSInteractionStateChangedEvent` |
| `session.changed` | `WSSessionChangedEvent` |

---

## 錯誤處理流向

```
HTTP 層（OkHttp）
  ↓
B2CResponseConverter（自訂 Converter）
  → 檢查 dynamic.action → DynamicRouterManager
  → 檢查 queueIt.version → QueueItService
  ↓
B2CApiResponse<T>（status / metadata 解析）
  ↓
BaseApiRepository.safeApiCallFlow
  → status == "0000" → ApiResult.Success
  → status == "SERVERGG" → ApiResult.Upgrade
  → HttpException（403/503）→ ApiResult.Error
  → 網路異常（type 1~8）→ ApiResult.Error
  ↓
UseCase → ViewModel → ViewState
```

**網路錯誤類型**（`metadata.type`）：

| type | 對應例外 |
|------|---------|
| 0 | 正常 |
| 1 | UnknownHostException |
| 2 | ConnectException |
| 3 | SocketTimeoutException |
| 7 | IOException |
| 8 | HttpException |

**不走 safeApiCall 的 Repository（suspend fun → Result<T>）注意**：`provideRetrofit` 未註冊 CallAdapter，非 2xx 回應會直接丟 `HttpException`，errorBody 中的 `metadata.status` 業務碼不會被解析。若上層需要分辨業務錯誤（如訂單不存在），Repository 須自行解析 errorBody 還原業務碼；解析不出或 `status == API_EXCEPTION` 時保留原始 exception，避免把網路錯誤偽裝成業務錯誤。實作先例：`PresaleChatRepositoryImpl`、`ChatRepositoryImpl.httpFailure()`。

---

## 新增 API 標準流程

1. 在 `libs/networking/api/.../service/` 對應目錄新增或更新 `I*ApiService.kt` 介面
2. 在 `data/model/` 新增 Request/Response data class
3. 在 `data/repository/` 的 Repository 呼叫 service，回傳 `Flow<ApiResult<T>>`
4. 不需修改 Retrofit 初始化（自動繼承 `B2CInterceptor` 認證）

---

*文件版本：Step 4 of AI Guide | 最後分析日期：2026-03-17*

## 相關筆記
- [01-architecture](01-architecture.md)
- [02-modules](02-modules.md)
- [03-ui-patterns](03-ui-patterns.md)
- [06-data-layer](06-data-layer.md)
- [07-concurrency](07-concurrency.md)
- [checkout](features/checkout.md)
- [order-detail-compose](features/order-detail-compose.md)
- [sku-activity-shell](features/sku-activity-shell.md)

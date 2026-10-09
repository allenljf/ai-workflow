# 06 · 網路層

**管**：Retrofit service 介面定義、kotlinx.serialization 設定、OkHttpClient 與 interceptor 組裝、認證 token 處理、timeout、retry、release build 的日誌安全、HTTP 例外轉 domain error。

**不管**：Repository 怎麼切、快取與 offline-first、DTO↔domain model 的分層與 mapper、Room / DataStore、憑證與傳輸層安全設定。

| 想找 | 去 |
|---|---|
| Repository 邊界、錯誤對外的最終型別（`Result` 三態）、offline-first 資料流 | `05-data-layer` |
| DTO / Entity / domain model 要幾層、mapper 放哪 | `05-data-layer` |
| Room / DataStore / 本地快取 | `07-persistence` |
| `CancellationException` rethrow、dispatcher 注入、Flow 的 `.catch` operator | `12-coroutines-flow` |
| cleartext traffic、certificate pinning、API key / secret 存放 | `17-security` |
| `OkHttpClient` / `Retrofit` / `Json` 的 DI module 怎麼寫 | `03-dependency-injection` |
| DataSource 的 fake、`MockWebServer` 用法 | `15-testing` |

---

### retrofit-non-suspend-endpoint · MUST · new-only+on-touch · check: regex

Retrofit service 的每個 endpoint 必須是 `suspend fun`，回傳型別不得為 `Call<T>`、`Single<T>`、`Observable<T>`、`Flowable<T>`、`Completable`。

✗ `fun getOrder(@Path("id") id: String): Call<OrderDto>`  
✓ `suspend fun getOrder(@Path("id") id: String): OrderDto`

例外：檔案下載等串流回應可用 `@Streaming suspend fun ...: ResponseBody` ｜ 來源：https://developer.android.com/topic/architecture/data-layer

### mixed-retrofit-response-types · MUST_NOT · new-only · check: manual

同一個 Retrofit interface 內不得混用裸型別 `T` 與 `Response<T>`。預設全部用裸型別，非 2xx 由 Retrofit 拋 `HttpException`，錯誤轉換集中在一處。

✗ 同介面內 `suspend fun a(): ADto` 與 `suspend fun b(): Response<BDto>`  
✓ 同介面內一律 `suspend fun a(): ADto`

例外：需讀 response header、或後端把業務錯誤碼放在非 2xx body 的介面可整份改用 `Response<T>`，並在 PR 說明 ｜ 來源：官方 sample nowinandroid

### public-retrofit-service · SHOULD_NOT · new-only · check: regex

Retrofit interface 宣告為 `internal`；模組對外只暴露不含任何 Retrofit / OkHttp 型別的 DataSource 介面。

✗ `interface OrderApiService { ... }`（public，被 `:feature:order` 直接引用）  
✓ `internal interface OrderApiService` + 對外的 `interface OrderNetworkDataSource`

例外：單模組專案可省略 DataSource 介面，但 Retrofit interface 仍應 internal ｜ 來源：官方 sample nowinandroid

### retrofit-client-built-in-business-class · MUST_NOT · new-only+on-touch · check: regex

一個 process 內只能有一個 `OkHttpClient` 根實例——連線池、執行緒池與快取都掛在它身上，每多一個就多一組閒置連線與執行緒。`OkHttpClient.Builder()` 與 `Retrofit.Builder()` 只能出現在 DI module。需要不同 timeout 或不同 interceptor 的變體，必須從既有實例 `newBuilder()` 衍生以共用資源池。

✗ `val paymentClient = OkHttpClient.Builder().readTimeout(...).build()`（另起一組資源池）  
✓ `@Provides @Singleton @Payment fun providePaymentClient(base: OkHttpClient) = base.newBuilder().readTimeout(...).build()`

例外：無 ｜ 來源：官方 sample nowinandroid（`NetworkModule`）

### eager-okhttp-init · SHOULD · new-only · check: manual

Retrofit 以 `callFactory { lazyCallFactory.get().newCall(it) }` 建構，把 OkHttp 的建立延後到第一次請求，不要用 `.client(okHttpClient)` 讓它落在 App 啟動路徑上。

✗ `Retrofit.Builder().client(okHttpClient).build()`  
✓ `Retrofit.Builder().callFactory { callFactory.get().newCall(it) }.build()`（注入 `Lazy<Call.Factory>`）

例外：啟動時間非瓶頸的小型專案可省略 ｜ 來源：官方 sample nowinandroid（`NetworkModule`）

### okhttp-missing-call-timeout · MUST · new-only+on-touch · check: regex

每個 `OkHttpClient` 必須顯式設定 `connectTimeout`、`readTimeout`、`writeTimeout` 與 `callTimeout`。`callTimeout` 預設為 0（整通呼叫無上限），省略等於允許慢速滴送的回應無限期佔住連線。

✗ `OkHttpClient.Builder().addInterceptor(auth).build()`  
✓ `.connectTimeout(15.seconds.toJavaDuration()).readTimeout(...).writeTimeout(...).callTimeout(60.seconds.toJavaDuration())`

例外：WebSocket / 長輪詢需要獨立的長 readTimeout，另建具名 client 並以 DI qualifier 區分 ｜ 來源：https://square.github.io/okhttp/5.x/okhttp/okhttp3/-ok-http-client/-builder/call-timeout.html

### unconditional-http-logging-body · MUST · new-only+on-touch · check: regex

`HttpLoggingInterceptor` 的 `Level.BODY` / `Level.HEADERS` 必須以 build type 條件包裹，release build 一律 `Level.NONE`。

✗ `HttpLoggingInterceptor().apply { level = Level.BODY }`  
✓ `level = if (BuildConfig.DEBUG) Level.BODY else Level.NONE`

例外：無 ｜ 來源：https://github.com/square/okhttp/blob/master/okhttp-logging-interceptor/README.md

### unredacted-auth-header-log · MUST · new-only+on-touch · check: regex

每個 `HttpLoggingInterceptor` 實例都必須 redact 認證相關標頭，包含專案自訂的 token header。debug build 的 log 一樣會被側錄。

✗ `HttpLoggingInterceptor()`（從未呼叫 `redactHeader`）  
✓ `HttpLoggingInterceptor().apply { redactHeader("Authorization"); redactHeader("Cookie") }`

例外：無 ｜ 來源：https://github.com/square/okhttp/blob/master/okhttp-logging-interceptor/README.md

### manual-401-retry-in-interceptor · MUST_NOT · new-only · check: manual

401 token refresh 必須實作 `okhttp3.Authenticator` 並掛在 `.authenticator()`，內部以 `Mutex` 序列化 refresh、以自訂標記作為終止條件。不得在 Interceptor 內以迴圈或遞迴 `chain.proceed()` 手刻重試。多個請求同時 401 時只能有一次真正的 refresh，否則 refresh token 輪替後其餘請求會拿到失效 token 而讓使用者被登出。

✗ Interceptor 內 `if (res.code == 401) { refreshToken(); return chain.proceed(newRequest) }`  
✓ `class TokenAuthenticator : Authenticator { override fun authenticate(route: Route?, response: Response): Request? = runBlocking { mutex.withLock { ... } } }`

例外：`Authenticator.authenticate()` 是 blocking API 且執行在 OkHttp 工作執行緒，其中使用 `runBlocking` 是允許的 ｜ 來源：https://github.com/square/okhttp/blob/master/docs/features/interceptors.md

### header-added-in-network-interceptor · SHOULD_NOT · new-only · check: manual

加共用 header（auth token、語系、App 版本）用 `addInterceptor()`（application interceptor）。`addNetworkInterceptor()` 只用於觀察重導向／重試過程或實際上線位元組——它每次重導向都會再跑一遍，且看不到快取命中的請求。

✗ `.addNetworkInterceptor(AuthHeaderInterceptor())`  
✓ `.addInterceptor(AuthHeaderInterceptor())`

例外：需要觀測 gzip 前後大小或每一跳連線資訊的診斷用 interceptor ｜ 來源：https://github.com/square/okhttp/blob/master/docs/features/interceptors.md

### retry-on-non-idempotent-request · MUST_NOT · new-only · check: manual

自訂 retry interceptor 只能套用在冪等請求（GET / PUT / DELETE），且必須有明確次數上限。建立訂單、送出付款、扣款、驗證等非冪等請求不得自動重試。

✗ 全域 retry interceptor 對所有失敗請求重送三次  
✓ retry interceptor 開頭 `if (request.method != "GET") return chain.proceed(request)`，並限制最多 3 次

例外：後端提供 idempotency key 且明確保證該 endpoint 冪等時可重試，需在 PR 說明 ｜ 來源：業界共識

### gson-dto-for-new-api · MUST_NOT · new-only · check: regex

新增的網路 DTO 一律使用 kotlinx.serialization；不得新增 `@SerializedName` DTO，也不得新增 `GsonConverterFactory`。

✗ `data class OrderDto(@SerializedName("order_id") val orderId: String)`  
✓ `@Serializable data class OrderDto(@SerialName("order_id") val orderId: String)`

例外：既有 Gson DTO 維持現狀（enforce 為 migrate），動到某個 API 模組時整批轉換該模組，避免半套狀態 ｜ 來源：https://github.com/google/gson/blob/main/README.md

### mixed-json-annotations · MUST_NOT · migrate · check: regex

同一個 data class 不得同時出現 `@Serializable` 與 `@SerializedName`。這是遷移半途的產物，會導致實際解析錯誤（kotlinx 完全忽略 `@SerializedName`，欄位對不上而變成預設值或拋例外），不是風格問題。

✗ `@Serializable data class OrderDto(@SerializedName("order_id") val orderId: String)`  
✓ `@Serializable data class OrderDto(@SerialName("order_id") val orderId: String)`

例外：無 ｜ 來源：https://kotlinlang.org/docs/serialization.html

### default-json-instance · MUST · new-only+on-touch · check: regex

解析後端回應的 `Json` 實例必須設定 `ignoreUnknownKeys = true`，且由 DI 以 singleton 提供並注入。不得直接使用 `Json` companion object，也不得在 mapper 或函式內 `Json { ... }` 建臨時實例（每次建立都要重新初始化設定）。

✗ `Json.decodeFromString<OrderDto>(body)`  
✓ `@Provides @Singleton fun provideJson(): Json = Json { ignoreUnknownKeys = true }`

例外：無 ｜ 來源：https://kotlinlang.org/docs/serialization-json-configuration.html

### snake-case-kotlin-property · MUST · new-only · check: regex

JSON key 與 Kotlin 命名慣例不同（snake_case、縮寫、保留字）時用 `@SerialName` 對應，不得把 Kotlin 屬性命名成 snake_case 來遷就 JSON。

✗ `@Serializable data class OrderDto(val order_id: String, val created_at: String)`  
✓ `@Serializable data class OrderDto(@SerialName("order_id") val orderId: String)`

例外：無 ｜ 來源：https://kotlinlang.org/docs/serialization.html

### dto-required-collection-field · SHOULD · new-only · check: regex

DTO 的集合型別欄位與後端可能不回傳的欄位必須給預設值，避免後端少回一個 key 就整包解析失敗。

✗ `@Serializable data class OrderDto(val items: List<ItemDto>, val note: String)`  
✓ `@Serializable data class OrderDto(val items: List<ItemDto> = emptyList(), val note: String? = null)`

例外：契約上保證必回傳、且缺漏就應該視為錯誤的核心欄位（如 `id`）｜ 來源：https://kotlinlang.org/docs/serialization.html

### third-party-kotlinx-converter · SHOULD_NOT · migrate · check: regex

kotlinx.serialization 的 Retrofit converter 使用官方套件 `com.squareup.retrofit2:converter-kotlinx-serialization`，第三方 converter 已由官方版本取代。

✗ `import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory`  
✓ `import retrofit2.converter.kotlinx.serialization.asConverterFactory`

例外：無 ｜ 來源：https://github.com/square/retrofit/blob/trunk/retrofit-converters/kotlinx-serialization/README.md

### unchecked-response-body · MUST · new-only+on-touch · check: regex

endpoint 回傳 `Response<T>` 時必須先檢查 `isSuccessful` 再取 `body()`，且不得用 `!!`。

✗ `val dto = api.getOrder(id).body()!!`  
✓ `val res = api.getOrder(id); if (!res.isSuccessful) throw HttpException(res); res.body() ?: error("empty body")`

例外：無 ｜ 來源：https://github.com/square/retrofit/blob/trunk/retrofit/src/main/java/retrofit2/HttpException.java

### adhoc-error-body-parsing · MUST · new-only+on-touch · check: manual

後端放在非 2xx body 的錯誤內容也是 DTO：宣告 `@Serializable` 的 error DTO，用注入的同一個 `Json` 實例，在單一處（interceptor 或 DataSource 的統一 catch）解析。不得在各呼叫點自行 `errorBody()?.string()` 後手刻字串解析，也不得對 `errorBody()` 重複讀取（它是一次性串流，第二次讀會拿到空值）。

✗ 每個 Repository 各自 `e.response()?.errorBody()?.string()?.substringAfter("\"message\":\"")`  
✓ 集中一處 `json.decodeFromString<ApiErrorDto>(e.response()?.errorBody()?.string().orEmpty())`

例外：後端不回傳結構化錯誤 body 的 endpoint ｜ 來源：https://github.com/square/retrofit/blob/trunk/retrofit/src/main/java/retrofit2/HttpException.java

`HttpException` / `IOException` / `SerializationException` 不得跨出 Repository 邊界、以及該轉成什麼錯誤型別，規則由 `05-data-layer` 定義；`catch` 前必須先 rethrow `CancellationException`，見 `12-coroutines-flow`。

---

## 尚無定論（以下是建議，不是規則）

**Retrofit 回傳型別**：官方無立場（Google 沒有 Retrofit 專頁）。建議預設回傳裸型別 `T`，錯誤轉換集中在 Repository。不建議自製 `CallAdapter.Factory` + `ApiResult` sealed class——要自行處理 suspend、泛型擦除與邊界情況，維護成本高於它省下的 try/catch。

**timeout 秒數**：官方無立場（OkHttp 預設 connect / read / write 各 10 秒、callTimeout 為 0）。建議全域基準 connect 15s、read 30s、write 30s、callTimeout 60s。檔案上傳、長流程驗證等另建具名 client 放寬，不要調高全域值。

**JSON 函式庫**：kotlinx.serialization 與 Moshi + codegen 技術上都可接受（皆為編譯期生成、與 R8 相容）。建議 kotlinx.serialization：官方 sample 採用、Retrofit 有 first-party converter。務必避開 Moshi 的 reflection adapter 與 Gson——反射在混淆後失效是官方點名的風險。已重度使用 Moshi 的專案不需為此遷移。

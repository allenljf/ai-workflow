# 06 · 網路層（Retrofit / OkHttp / 序列化）

**這份管**：Retrofit service 介面的簽章、`B2CApiResponse` envelope 的使用、JSON 序列化選型（Gson ↔ kotlinx 共存）、OkHttp client 與 interceptor 的分層與 release 安全邊界。
**這份不管**：例外轉成 domain error 與 `Result` 契約（05）、DTO 的分層與 mapper（05）、Room / DataStore（07）、token 儲存與 PII 遮蔽（18）。

註：ApiService 的 `internal` 可見性在本專案為 `exempt`（跨模組不可行），見 [91-decisions.md](91-decisions.md) D-11。等價約束由 05 與 04 的依賴規則涵蓋。

跨檔主題（不在這裡重述，直接看該檔）：

> 技術例外轉語意化例外見 [05-data-layer.md#raw-exception-leak](05-data-layer.md)
> ViewModel / UseCase 不得注入 ApiService 見 [05-data-layer.md#datasource-above-repository](05-data-layer.md)
> DTO 不得進 UI 見 [05-data-layer.md#dto-in-ui](05-data-layer.md)
> 錯誤模型（`Result` vs `ApiResult`）定案見 [05-data-layer.md](05-data-layer.md)
> token 儲存、憑證硬編碼、PII 遮蔽、cleartext traffic 見 [18-security.md](18-security.md)
> `runBlocking` 見 [11-coroutines-flow.md#run-blocking-prod](11-coroutines-flow.md)

---

## 一、Retrofit service 簽章

### retrofit-non-suspend · MUST · new-only · lint:retrofit-non-suspend

Retrofit interface 的每個 endpoint 一律 `suspend fun`，不得回傳 `Call<T>` 或 RxJava 型別。

✗ `fun getOrders(@Query("oid") oid: String): Observable<Response<OrderList>>`
✓ `suspend fun getSessions(@Query("cursor") cursor: String?): B2CApiResponse<PresaleSessionListResponse>`

例外：`KKdayService.kt` 等既有 Rx 巨石不改寫，只凍結（不得新增 Rx endpoint）。
既有違規：209 / 528 endpoint → [90-migration-ledger.md#m-09](90-migration-ledger.md)

### api-no-type-erasure · MUST NOT · new-only · lint:api-no-type-erasure

endpoint 不得宣告泛型型別參數讓呼叫端指定回傳型別。回傳型別必須是具名 DTO。

✗ `suspend inline fun <reified T> getRecentlyBrowsedProducts(...): B2CApiResponse<T>`
✓ `suspend fun getOtherFaqs(): B2CApiResponse<List<PresaleFaqDto>>`  // IPresaleChatApiService 是正面樣板

例外：既有泛型 endpoint 不主動改（會連動 256 個 `apiResultData` 呼叫點與所有 caller 型別參數）。
既有違規：198 endpoint / 256 個雙重轉換呼叫點 → [90-migration-ledger.md#m-16](90-migration-ledger.md)

### mixed-response-types · MUST NOT · new-only · manual

同一個 Retrofit interface 內不得混用 `B2CApiResponse<T>`、裸 `T`、`retrofit2.Response<T>` 三種回傳風格。新 service 一律用專案 envelope `B2CApiResponse<具名DTO>`。

✗ 同一介面內 `suspend fun a(): B2CApiResponse<ADto>` 與 `suspend fun b(): Response<BDto>` 並存
✓ 全部 `B2CApiResponse<具名DTO>`

例外：需要讀 response header 或後端把業務錯誤碼放在非 2xx body 時，該 endpoint 可用 `Response<T>`，並在 PR 註明原因。

### unchecked-api-response · MUST · new-only+on-touch · manual

取用 `B2CApiResponse.data` 前必須先檢查 `metadata?.isResultSuccess()` 與 `data != null`，不得用 `!!` 或忽略失敗分支。

✗ `val faqs = api.getOtherFaqs().data!!.map { it.toDomain() }`
✓ `if (response.metadata?.isResultSuccess() == true && payload != null) Result.success(payload.map { it.toDomain() }) else Result.failure(...)`

例外：無。

---

## 二、序列化

### raw-gson · MUST NOT · new-only+on-touch · lint:raw-gson

不得 `Gson()` 直接建立實例，一律 `com.kkday.util.gson.GsonInstance`（pre-push hook 會擋，含測試碼）。

✗ `private val gson = Gson()`
✓ `GsonInstance.fromJson(body, B2CApiResponse::class.java)`

例外：無（紅線 G1）。

### ser-kotlinx-for-new-dto · MUST · new-only · manual

**以檔案為單位**：新建的 DTO 檔案用 kotlinx.serialization（`@Serializable` + `@SerialName`）；既有 Gson DTO 檔案新增欄位繼續用 `@SerializedName`。

✗ 新建檔案 `data class OrderDto(@SerializedName("order_oid") val orderOid: String)`
✓ 新建檔案 `@Serializable data class OrderDto(@SerialName("order_oid") val orderOid: String)`

例外：既有 Gson DTO 檔案加欄位維持 Gson（明文豁免）。動手前先確認該 endpoint 的解析路徑 —— Retrofit 目前只註冊 `KtConverterFactory`（內部包 Gson），kotlinx 尚未接成 converter factory。
既有違規：`@SerializedName` 394 檔 vs `@Serializable` 69 檔 → [90-migration-ledger.md#m-20](90-migration-ledger.md)

### mixed-json-annotations · MUST NOT · new-only+on-touch · lint:mixed-json-annotations

同一個 class 不得同時出現 `@Serializable` 與 `@SerializedName`。掛了 `@Serializable` 的類別，欄位改名一律 `@SerialName`。

✗ `@Serializable data class Dto(@SerializedName("user_id") val userId: String)`
✓ `@Serializable data class Dto(@SerialName("user_id") val userId: String)`

例外：無（D-14 明文無例外）。這是會實際出錯的缺陷，不是風格問題。

### json-instance-per-call · MUST NOT · new-only+on-touch · lint:json-instance-per-call

不得在函式內建立 `Json { }` 實例。`Json` 由 DI 提供 singleton，或至少宣告為類別的 `val` 欄位。

✗ `fun parse(raw: String) = Json { ignoreUnknownKeys = true }.decodeFromString<Dto>(raw)`
✓ `class OrderRemoteDataSource(private val json: Json) { fun parse(raw: String) = json.decodeFromString<Dto>(raw) }`

例外：無。`ApiService.apiResultDataKotlinx()` 是既有反例，`BaseApiRepository` 的 field 級 `val json` 是正確寫法。

### json-unknown-keys · MUST · new-only · manual

用於解析後端回應的 `Json` 實例必須設 `ignoreUnknownKeys = true`，不得直接用 `Json` 這個預設 companion 物件。

✗ `Json.decodeFromString<Dto>(raw)`
✓ `Json { ignoreUnknownKeys = true; isLenient = true; explicitNulls = false }`（定義一次並注入）

例外：解析自家寫入的本地檔案（非後端回應）可用嚴格設定。

### json-key-in-property-name · MUST · new-only · manual

不得為了遷就 JSON key 把 Kotlin 屬性命名成 snake_case，一律用 `@SerialName` / `@SerializedName` 對應。

✗ `@Serializable data class Dto(val order_oid: String)`
✓ `@Serializable data class Dto(@SerialName("order_oid") val orderOid: String)`

例外：無。

### dto-missing-defaults · SHOULD · new-only · manual

DTO 的集合欄位與後端可能不回傳的欄位必須給預設值，不得宣告成無預設值的必填欄位。

✗ `@Serializable data class Dto(val tags: List<String>, val note: String)`
✓ `@Serializable data class Dto(val tags: List<String> = emptyList(), val note: String? = null)`

例外：後端契約保證必回傳且缺值應視為錯誤的欄位，可維持必填。

---

## 三、OkHttp 與 interceptor

### okhttp-manual-build · MUST NOT · new-only · lint:okhttp-manual-build

不得在 Repository / DataSource / UseCase / ViewModel 內建立 `OkHttpClient` 或 `Retrofit`。一律由 DI 提供 singleton。

✗ `private val client = OkHttpClient.Builder().build()`
✓ 在 Koin module 內 `single { provideOkHttpClient(get(), get()) }`，Repository 只注入 ApiService

例外：需要不同 timeout 的長流程（付款 / 3DS）或 WebSocket，另建**具名** client 並在 DI 綁定，不得在業務類別內建。

### missing-call-timeout · MUST · new-only+on-touch · manual

每個 `OkHttpClient` 必須顯式設定 `connectTimeout`、`readTimeout`、`writeTimeout` 與 `callTimeout`；`callTimeout` 不得省略。

✗ `OkHttpClient().newBuilder().connectTimeout(15, SECONDS).readTimeout(30, SECONDS).build()`
✓ 再補 `.writeTimeout(30, TimeUnit.SECONDS).callTimeout(60, TimeUnit.SECONDS)`

例外：WebSocket client 需要獨立的長 `readTimeout`，不套用 HTTP 的值。
既有違規：`networkCoreModule.kt` 與 `RetrofitUtil.kt` 兩處都未設 `writeTimeout` / `callTimeout` → [90-migration-ledger.md#m-21](90-migration-ledger.md)

### interceptor-swallows-exception · MUST NOT · new-only+on-touch · manual

interceptor 不得 catch 例外後自行組一個假 `Response` 回傳。例外必須往上拋，由 Repository 邊界處理。

✗ `catch (e: Exception) { Response.Builder().code(0).body(e.stackTraceToString().toResponseBody(...)).build() }`
✓ 記錄後 `throw e`（或不 catch），讓 `IOException` 依 OkHttp 語意傳遞

例外：無。既有 `B2CInterceptor` 與 `networkCoreModule` 的 network interceptor 是反例 —— Retrofit 會拿 stacktrace 文字去跑 JSON 解析。
既有違規：2 處 → [90-migration-ledger.md#m-21](90-migration-ledger.md)

### interceptor-layering · SHOULD · new-only · manual

加 header（auth token、語系、共用 header）用 `addInterceptor()`；只有需要觀察重導向 / 重試 / 實際上線位元組時才用 `addNetworkInterceptor()`。

✗ 用 `addNetworkInterceptor` 塞 auth token
✓ `.addInterceptor(B2CInterceptor())`；`addNetworkInterceptor` 只留 User-Agent 這類需要看實際連線的處理

例外：無。

### release-http-body-log · MUST NOT · new-only+on-touch · manual

release build 不得輸出 request/response body 或敏感 header。`HttpLoggingInterceptor` 的 `Level.BODY` / `HEADERS` 必須由 build flag gate，且必須 `redactHeader` 掉 auth 類 header。會落地完整內容的 interceptor 只能放 debug/staging sourceSet。

✗ `HttpLoggingInterceptor().apply { level = Level.BODY }`；用 runtime 可變全域變數 gate 落地型 log
✓ `level = if (KKNetworking.isDebug) Level.BODY else Level.NONE` + `redactHeader("Authorization")`、`redactHeader("B2CTOKEN1")`

例外：無（紅線 G4）。`ApiLogInterceptor` 目前靠 `var isProductionEnv` gate，屬安全類遷移項。
既有違規：1 處 → [90-migration-ledger.md#m-21](90-migration-ledger.md)

### retry-non-idempotent · MUST NOT · new-only+on-touch · manual

不得對非 idempotent 請求套用自動重試（建立訂單、送出付款、扣款、3DS 驗證）。重試只能用於 GET 等 idempotent 請求且要有明確次數上限。

✗ 在全域 client 掛無條件 `retryWhen` / `RetryPolicy`，涵蓋所有 endpoint
✓ 只對指定的 GET endpoint 帶 `RetryPolicy`，並設定最大次數

例外：無。付款與訂單路徑的改動需附風險說明。

### token-refresh-in-interceptor · SHOULD · new-only · manual

401 token refresh 應實作 `okhttp3.Authenticator` 掛在 `.authenticator()`，內部用 `Mutex` 序列化 refresh，並以自訂標頭標記「已重試過」作為終止條件。

✗ 在 interceptor 內以迴圈或遞迴 `chain.proceed()` 手刻重試
✓ `.authenticator(B2CTokenAuthenticator(mutex, tokenRepository))`

例外：`Authenticator.authenticate()` 是 blocking API，在其中用 `runBlocking` 是合理例外（跑在 OkHttp 工作執行緒）。

### force-http1 · SHOULD NOT · new-only · manual

這是一條**圍堵**規則：新建的 `OkHttpClient` 一律不指定 `protocols`，交由 ALPN 與伺服器協商（寫死 HTTP/1.1 會關閉 HTTP/2 multiplexing）。**禁止從 `networkCoreModule.kt:127` 或 `RetrofitUtil.kt:69` 複製貼上 `.protocols(listOf(Protocol.HTTP_1_1))`** —— 那兩處是原因未記錄的歷史遺留，不是可照抄的樣板。

✗ 新 client 照抄 `.protocols(listOf(Protocol.HTTP_1_1))`
✓ 完全不呼叫 `.protocols(...)`；確有必要強制 HTTP/1.1（特定第三方 endpoint）時，PR 描述寫出是哪個 endpoint、什麼症狀，並在該行加註解

**既有兩處在後端 HTTP/2 相容性實測通過前不得移除，即使 `on-touch` 也不改** —— 這不是現代化清理項，貿然拿掉可能造成線上連線異常且難以歸因。解鎖動作（由後端／SRE 確認 gateway 與 CDN 的 HTTP/2 支援）見 [90-migration-ledger.md#m-21](90-migration-ledger.md)。
既有違規：2 處，**維持現狀不清償** → [90-migration-ledger.md#m-21](90-migration-ledger.md)

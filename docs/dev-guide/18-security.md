# 18 · 安全

**管**：機敏資訊的來源與儲存（token / API key / 個資）、log 與除錯工具的輸出邊界、傳輸層設定（cleartext、network security config）、WebView 安全設定、payment / 3DS 敏感路徑的額外要求。
**不管**：Retrofit / OkHttp 的一般設定與錯誤模型、`SharedPreferences` vs DataStore 的一般選型、Gson 實例共用、release build 的 R8 / mapping 設定。

跨檔主題（**只在對應檔案定義，這裡不重述**）：

- OkHttp interceptor 分層、timeout、401 refresh、非 idempotent 請求禁自動重試 → [06-network.md](06-network.md)
- `GsonInstance` 共用實例（紅線 G1）、`printStackTrace()`（紅線 G3） → [05-data-layer.md](05-data-layer.md)
- 新增 `SharedPreferences` key 的一般禁令與 DataStore 選型 → [07-persistence.md](07-persistence.md)
- StrictMode / LeakCanary 的 build type 邊界 → [15-performance.md](15-performance.md#strictmode-in-release)

---

## 一、機敏資訊

### hardcoded-secret · MUST_NOT · new-only+on-touch · manual

API key、client secret、auth token、x-auth-token、basic auth 字串、憑證 pin 值、第三方 SDK token、測試帳號的真實 uuid，一律不得以字面常數出現在 `.kt` / `.java` / `.xml`。必須來自 `BuildConfig`（由 gradle property 或環境變數注入）或安全儲存。

✗ `override fun getBaseApiXAuthTokenValue(): String = "hxjtgAwEqVh772HFWTP3Nc0eROqO5iEcsdXUKJx6nhI="`
✓ `override fun getBaseApiXAuthTokenValue(): String = BuildConfig.B2C_X_AUTH_TOKEN`

例外：無。demo / sample app 模組同樣適用（它們也會被建置與分發）。
既有違規：`libs/networking/app/.../MainApp.kt:85,109`、`libs/tool/env/app/.../MainApp.kt:68,92,96` → [90-migration-ledger.md#m-21](90-migration-ledger.md)

### plain-prefs-for-secret · MUST_NOT · new-only+on-touch · manual

認證憑證（auth token、refresh token、session id）、會員個資（姓名、電話、email、證件號）、付款相關識別碼不得以明文寫進 `SharedPreferences` / DataStore / 檔案。一律用專案的 `SecurePreferences`（`libs/base/.../storage/preference/SecurePreferences.kt`，底層 AndroidKeyStore + AES）。

✗ `prefs.edit().putString("auth_token", token).apply()`
✓ `securePreferences.edit().putString(KEY_AUTH_TOKEN, token).apply()`  // 由 storageModule 注入

例外：非機敏的 UI 偏好（語系、排序、是否看過引導頁）用一般 preferences 即可。

### token-in-url · MUST_NOT · new-only+on-touch · manual

token、密碼、身分證號、email、電話、訂單聯絡人資料不得放在 URL path 或 query string（會進入 access log、Referer、瀏覽歷史）。一律放 header 或 request body。

✗ `@GET("member/profile") suspend fun getProfile(@Query("token") token: String): ProfileDto`
✓ `@GET("member/profile") suspend fun getProfile(): ProfileDto`  // token 由 B2CInterceptor 加在 header

---

## 二、log 與除錯輸出

### pii-in-log · MUST_NOT · new-only+on-touch · manual

任何 log / Crashlytics 自訂鍵值 / 埋點 property 不得輸出 auth token、密碼、信用卡號、CVV、身分證號、完整 request/response body。需要辨識時只輸出遮蔽後的尾四碼或雜湊。

✗ `KKLog.d("TOKEN", "auth=$authToken")`
✓ `KKLog.d("TOKEN", "auth=***${authToken.takeLast(4)}")`

例外：無。紅線 G4。

### http-log-body-in-release · MUST · new-only · manual

`HttpLoggingInterceptor` 的 `Level.BODY` / `Level.HEADERS` 必須以 build type 條件決定，release 一律 `Level.NONE`；禁止無條件設定 BODY。

✗ `HttpLoggingInterceptor().apply { level = Level.BODY }`
✓ `HttpLoggingInterceptor().apply { level = if (BuildConfig.DEBUG) Level.BODY else Level.NONE }`

例外：專案現行寫法（由 `KKNetworking.isDebug` = `BuildConfig.DEBUG` gate）已符合，**維持不要改**。

### log-unredacted-auth-header · MUST · new-only+on-touch · manual

每個 `HttpLoggingInterceptor` 實例都必須呼叫 `redactHeader()` 遮蔽認證標頭，含專案自訂的 `B2CTOKEN1` / `x-auth-token`。

✗ `HttpLoggingInterceptor()` 直接加進 client
✓ `HttpLoggingInterceptor().apply { redactHeader("Authorization"); redactHeader("Cookie"); redactHeader("B2CTOKEN1") }`

### runtime-gated-debug-interceptor · MUST_NOT · migrate · manual

會落地或外送完整 request/response 的除錯元件（log interceptor、Flipper、Chucker、API log DB），其啟用條件不得是 runtime 可變的全域變數或初始化順序。必須靠 **sourceSet 隔離**（`src/debug` / `src/staging`）或 `BuildConfig` 常數。

✗ `if (!isProductionEnv) addInterceptor(ApiLogInterceptor())`  // `var isProductionEnv` 是可寫全域變數
✓ 把 `ApiLogInterceptor` 的註冊搬到 `src/debug` 的 DI module，release sourceSet 完全沒有該類別

例外：無。安全邊界依賴初始化時序等同沒有邊界。
既有違規：`GlobalVar.kt:9` + `networkCoreModule.kt:183-185`（另 `AppConfigManager.kt:45` 才設 true）→ [90-migration-ledger.md#m-21](90-migration-ledger.md)

---

## 三、傳輸層

### cleartext-traffic-enabled · MUST_NOT · new-only · manual

`release` / `miniDebug` 的 manifest 不得設 `android:usesCleartextTraffic="true"`，network security config 的 `base-config` / `domain-config` 不得設 `cleartextTrafficPermitted="true"`。HTTP 端點只能出現在 debug 專屬設定。

✗ 在 `app/src/main/AndroidManifest.xml` 加 `android:usesCleartextTraffic="true"`
✓ 只在 `app/src/debug/AndroidManifest.xml` 設定，並以 `tools:replace` 覆寫

例外：`app/src/debug/AndroidManifest.xml:8` 與 `app/src/debug/res/xml/network_security_config.xml:11` 是 Mockoon e2e mock server 所需，**維持不要改**；新增 HTTP 端點一律加在同一組 debug 檔案。

---

## 四、WebView

### webview-untrusted-url · MUST · new-only+on-touch · manual

WebView 只能載入允許清單內的網域（KKday 自有網域與已核可的金流網域）。外部連結一律丟給系統瀏覽器，`shouldOverrideUrlLoading` 必須對非允許清單的 URL 回傳攔截。

✗ `webView.loadUrl(intent.getStringExtra("url")!!)`  // 未驗證來源
✓ `if (UrlAllowList.isTrusted(url)) webView.loadUrl(url) else openInBrowser(url)`

### webview-mixed-content · MUST_NOT · new-only · manual

不得設定 `WebSettings.MIXED_CONTENT_ALWAYS_ALLOW`；一律 `MIXED_CONTENT_NEVER_ALLOW`（必要時 `COMPATIBILITY_MODE` 並在 PR 說明理由）。

✗ `settings.mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW`
✓ `settings.mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW`

既有違規：`libs/tool/webjs/src/main/java/com/kkday/library/common/webjs/DWebView.kt:233`（`migrate`，改動前須確認既有 H5 頁面的資源協定，不在功能 PR 順手改）。

### webview-file-access · MUST_NOT · new-only+on-touch · manual

`allowFileAccess`、`allowFileAccessFromFileURLs`、`allowUniversalAccessFromFileURLs`、`allowContentAccess` 一律不得設為 `true`。

✗ `settings.allowUniversalAccessFromFileURLs = true`
✓ `settings.allowFileAccess = false`  // `DWebView.kt:235` 已正確，維持

### webview-debug-always-on · MUST_NOT · new-only+on-touch · manual

`WebView.setWebContentsDebuggingEnabled(true)` 必須由 `BuildConfig.DEBUG` gate，不得無條件開啟。同理，`addJavascriptInterface` 註冊的 bridge 只能暴露在允許清單網域載入的頁面。

✗ `WebView.setWebContentsDebuggingEnabled(true)`
✓ `WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG)`

---

## 五、Payment / 3DS

### payment-secret-logged · MUST_NOT · new-only+on-touch · manual

卡號、CVV、到期日、3DS 驗證參數、TapPay / Adyen / Stripe 的 prime / token 不得寫入 log、埋點 property、Crashlytics 自訂鍵值，也不得存進任何本機儲存（含 `SecurePreferences`）。只能存在記憶體並在流程結束後釋放。

✗ `trackEvent("payment_submit", mapOf("card" to cardNumber))`
✓ `trackEvent("payment_submit", mapOf("card_brand" to brand, "last4" to cardNumber.takeLast(4)))`

例外：無。此規則涵蓋 `:shared:payment` 與所有呼叫端。

### payment-change-no-rollback-note · MUST · new-only · manual

變更付款 / 3DS / 登入認證流程的 PR，描述必須包含：影響範圍、風險說明、回滾方案、已驗證的支付通道（TapPay / Adyen / Stripe）。缺任一項不得合併。

✗ PR 描述只有「修正付款頁面按鈕」
✓ PR 描述列出「影響 TapPay 3DS callback；風險：驗證失敗會停在空白頁；回滾：revert commit X；已驗證：TapPay 測試卡成功 / 失敗兩路徑」

例外：純 UI 文案或 token 替換且不觸及 `:shared:payment` 與付款 API 呼叫時，可只註明「不影響交易流程」。

### sensitive-screen-not-secure · SHOULD · new-only · manual

輸入或顯示完整卡號、CVV、身分證件的畫面應加 `WindowManager.LayoutParams.FLAG_SECURE`，阻擋截圖與最近畫面預覽。

✗ 信用卡輸入 Activity 未設定任何旗標
✓ `window.setFlags(FLAG_SECURE, FLAG_SECURE)` 於 `onCreate`，離開畫面時 `clearFlags`

例外：e2e 測試需要截圖的畫面可在 debug sourceSet 關閉，但不得以 runtime 變數控制（同 `runtime-gated-debug-interceptor`）。

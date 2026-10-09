# 17 · 安全

**管**：密鑰與憑證的處置、認證 token 的儲存、log 的 PII 遮蔽、傳輸層安全設定（cleartext／pinning／TrustManager）、WebView 安全、外部輸入驗證、混淆與反編譯風險、敏感畫面與生物辨識。
**不管**：Retrofit／OkHttp 的用法與 interceptor 分層（`06-network`）、Room／DataStore 的一般用法（`07-persistence`）、R8 的效能面設定與 baseline profile（`16-performance`）。

| 相關主題 | 去哪 |
|---|---|
| `HttpLoggingInterceptor` 的層級與 `redactHeader` 設定 | `06-network` |
| token refresh 的 `Authenticator` 實作與序列化 | `06-network` |
| DataStore／Room 的一般存取規範 | `07-persistence` |
| `isMinifyEnabled`、`mapping.txt` 上傳、baseline profile | `16-performance` |
| 埋點事件不得攜帶 PII | `18-analytics` |
| 錯誤不得把後端原始訊息直接顯示給使用者 | `05-data-layer` `08-ui-state` |

---

### hardcoded-secret · MUST_NOT · new-only+on-touch · regex

API key、client secret、basic auth 字串、加密金鑰、憑證 pin 值不得以字面常數出現在 Kotlin/Java/XML/JSON 中；一律經 `BuildConfig`（由 gradle property 或環境變數注入）或安全儲存取得。

✗ `private const val API_KEY = "sk_live_9f2c…"`
✓ `BuildConfig.API_KEY`（`buildConfigField` 由 `local.properties`／CI secret 注入）

例外：公開且無保護價值的識別字串（例如 app 自己的 package name）。 來源：https://developer.android.com/privacy-and-security/security-tips

### secret-in-version-control · MUST_NOT · migrate · manual

keystore 檔、簽章密碼檔、service account JSON、含真實密鑰的 `.properties` 不得進版控；必須列入 `.gitignore` 並由 CI secret 提供。已外洩的密鑰必須輪替，光刪 commit 不算修好。

✗ repo 內存在 `release.keystore` 與 `keystore.properties`
✓ 兩者由 CI secret 於 build 時寫入，repo 只留 `.template` 範例

例外：測試專用、無法存取任何正式資源的假密鑰，且檔名明確標示。 來源：https://developer.android.com/privacy-and-security/security-tips

### client-side-secret-assumed-safe · MUST · new-only · manual

放在 client 的任何值（含 `BuildConfig`、native 字串、混淆後常數）都必須視為可被反編譯取得。高價值密鑰（後台 API key、支付私鑰、簽章用金鑰）不得下放到 app，必須由後端代理呼叫。

✗ app 直接持有可扣款的第三方後台 key
✓ app 呼叫自家後端，由後端持有該 key

例外：設計上就以公開為前提的可公開金鑰（public key、可撤銷的 client id）。 來源：https://developer.android.com/privacy-and-security/security-tips

### plaintext-credential-storage · MUST_NOT · new-only+on-touch · manual

存取／更新 token、密碼、完整卡號、身分證號不得明文寫入 `SharedPreferences`、DataStore、Room 或檔案；必須以 Android Keystore 產生的金鑰加密後再存，或只存於記憶體、每次重新換取。

✗ `dataStore.edit { it[REFRESH_TOKEN] = token }`
✓ `dataStore.edit { it[REFRESH_TOKEN] = keystoreCipher.encrypt(token) }`

例外：短生命週期且伺服器可即時撤銷的 access token，經專案風險評估後可只存記憶體。 來源：https://developer.android.com/privacy-and-security/keystore

### deprecated-security-crypto · SHOULD_NOT · new-only · manual

新程式碼不應新增 `androidx.security:security-crypto` 依賴（`EncryptedSharedPreferences`／`EncryptedFile` 已於 1.1.0-beta01 全面標記 deprecated）；改為直接使用 Android Keystore 產生 AES-GCM 金鑰自行加解密，或引入 Tink。

✗ `EncryptedSharedPreferences.create(…)`
✓ `KeyGenParameterSpec` 產生 Keystore 金鑰 + `Cipher.getInstance("AES/GCM/NoPadding")`

例外：既有已使用該套件的程式碼可維持現狀，另案評估遷移。 來源：https://developer.android.com/jetpack/androidx/releases/security

### pii-in-log · MUST_NOT · new-only+on-touch · regex

log 不得輸出 PII 或憑證：token、密碼、`Authorization` 標頭、email、電話、身分證／護照號、完整卡號、地址、精確座標、完整 API request/response body。需要追查時只輸出遮蔽值或不可逆識別碼。

✗ `Log.d(TAG, "login ok, token=$token, email=$email")`
✓ `Log.d(TAG, "login ok, userIdHash=${userId.hashed()}")`

例外：無。 來源：https://developer.android.com/privacy-and-security/security-tips

### debug-log-in-release · MUST · new-only · manual

release build 不得輸出 debug／verbose log。必須以可設定 level 的 log 封裝，或以 R8 規則移除 `android.util.Log` 的低階方法；不得靠「上線前記得刪掉」。

✗ 到處直接呼叫 `Log.d(…)`，release 照樣輸出
✓ 統一走 `AppLogger`，release 實作為 no-op（或 `-assumenosideeffects` 移除）

例外：明確的錯誤上報路徑（crash reporting），且內容已通過 `pii-in-log`。 來源：https://developer.android.com/privacy-and-security/security-tips

### cleartext-traffic-enabled · MUST_NOT · new-only · regex

release 設定不得允許明文 HTTP：AndroidManifest 不得有 `android:usesCleartextTraffic="true"`，network security config 的 `base-config`／`domain-config` 不得設 `cleartextTrafficPermitted="true"`。

✗ `<application android:usesCleartextTraffic="true">`
✓ 明文端點只寫在 `<debug-overrides>` 或 debug variant 專屬的 network security config

例外：僅限 debug variant 的本機 mock server。 來源：https://developer.android.com/privacy-and-security/security-config

### permissive-trust-manager · MUST_NOT · new-only · regex

不得自訂放行一切的 `X509TrustManager`（空的 `checkServerTrusted`）、`HostnameVerifier { _, _ -> true }` 或 `SSLSocketFactory` 繞過驗證，任何 build type 都不行。需要信任自簽憑證時，用 network security config 的 `<trust-anchors>` 限定在 debug。

✗ `builder.hostnameVerifier { _, _ -> true }`
✓ debug variant 的 network security config 加入該測試環境的 CA

例外：無。 來源：https://developer.android.com/privacy-and-security/security-ssl

### unmanaged-certificate-pin · MUST · new-only · manual

若採用 certificate pinning，必須同時具備：至少一組備用 pin（下一輪憑證）、明確的過期時間、以及不需發版就能停用 pinning 的遠端開關。做不到這三點就不要 pin——憑證輪替時會讓全體使用者無法連線。

✗ `CertificatePinner.Builder().add("api.example.com", "sha256/AAA…").build()`（單一 pin、無備援）
✓ 同時 pin 現行與備用中繼憑證，設定 `expiration`，並可由遠端設定關閉

例外：無。 來源：https://developer.android.com/privacy-and-security/security-config

### webview-javascript-enabled-for-remote-content · MUST · new-only+on-touch · manual

`javaScriptEnabled = true` 只能用於 app 自有、可控的內容；載入第三方或使用者可影響的 URL 時不得開啟。

✗ 通用 WebView 一律 `settings.javaScriptEnabled = true` 後載入任意連結
✓ 只在載入自家網域的 WebView 開啟 JS，外部連結交給系統瀏覽器（Custom Tabs）

例外：無。 來源：https://developer.android.com/privacy-and-security/security-tips

### webview-javascript-interface-exposed · MUST_NOT · new-only · manual

`addJavascriptInterface()` 不得用於會載入外部內容的 WebView；使用時介面方法必須標 `@JavascriptInterface`、只暴露最小必要能力，且不得提供可取得 `Context`、檔案系統或認證資訊的方法。

✗ 在載入外部行銷頁的 WebView 上掛 `addJavascriptInterface(NativeBridge(), "Android")`
✓ 只在載入 APK 內建資源的 WebView 掛橋接，且方法只回傳非敏感資料

例外：無。 來源：https://developer.android.com/privacy-and-security/security-tips

### webview-file-access-enabled · MUST_NOT · new-only+on-touch · regex

不得設定 `allowFileAccess = true`、`allowFileAccessFromFileURLs = true`、`allowUniversalAccessFromFileURLs = true`、`allowContentAccess = true`；需要載入本地資源時用 `WebViewAssetLoader`。

✗ `settings.allowUniversalAccessFromFileURLs = true`
✓ `WebViewAssetLoader.Builder().addPathHandler("/assets/", AssetsPathHandler(context)).build()`

例外：無。 來源：https://developer.android.com/privacy-and-security/security-tips

### webview-unvalidated-url · MUST · new-only+on-touch · manual

WebView 載入的 URL 必須先驗證 scheme 與 host（allowlist）；來自 deep link、推播或後端回傳的 URL 不得直接 `loadUrl`。同時要在 `shouldOverrideUrlLoading` 攔截非預期網域的跳轉。

✗ `webView.loadUrl(intent.getStringExtra("url")!!)`
✓ 先 `require(uri.scheme == "https" && uri.host in allowedHosts)` 再載入

例外：無。 來源：https://developer.android.com/privacy-and-security/security-tips

### exported-component-unprotected · MUST · new-only · manual

`android:exported="true"` 的 Activity／Service／Receiver／Provider 必須有 `android:permission` 保護或在入口驗證來源；不需被外部呼叫的元件一律明確設 `exported="false"`。intent filter 本身不是安全機制。

✗ `<receiver android:name=".SyncReceiver" android:exported="true"/>`
✓ `<receiver android:name=".SyncReceiver" android:exported="false"/>`

例外：確實需要對外開放的 deep link Activity，但仍須做 `unvalidated-external-input` 的驗證。 來源：https://developer.android.com/privacy-and-security/security-tips

### unvalidated-external-input · MUST · new-only+on-touch · manual

來自 Intent extras、deep link 參數、WebView、剪貼簿、外部儲存、第三方 SDK callback 的資料，使用前必須驗證型別、範圍與格式，且不得直接當作導航目標、檔案路徑或查詢條件。

✗ `val orderId = intent.getStringExtra("id")!!` 後直接送進 API
✓ 先驗證格式（長度、字元集）與歸屬（是否屬於當前使用者）再使用

例外：無。 來源：https://developer.android.com/privacy-and-security/security-tips

### sql-string-concatenation · MUST_NOT · new-only+on-touch · regex

不得以字串串接組出 SQL 或 `ContentResolver` 的 selection；一律用參數化查詢（Room 的 `:param` 綁定、`selectionArgs`）。

✗ `@Query("SELECT * FROM orders WHERE id = '" + id + "'")`
✓ `@Query("SELECT * FROM orders WHERE id = :id")`

例外：無。 來源：https://developer.android.com/privacy-and-security/security-tips

### wildcard-keep-rule · SHOULD_NOT · new-only · manual

不得用整包 wildcard keep 規則（`-keep class com.example.** { *; }`）：等同放棄該範圍的混淆與縮減，把完整類別／方法名留給反編譯者。只對真正經反射存取的類別做精準 keep 或加 `@Keep`。

✗ `-keep class com.example.** { *; }`
✓ `-keepclassmembers class com.example.data.dto.** { <fields>; }` 或在該類別加 `@Keep`

例外：第三方套件官方要求的 keep 規則。 來源：https://developer.android.com/build/shrink-code

### sensitive-screen-without-flag-secure · SHOULD · new-only · manual

顯示完整卡號、OTP、身分證件、還原碼的畫面應設定 `FLAG_SECURE`，阻擋截圖與最近工作清單縮圖外洩。

✗ 卡片管理頁顯示完整卡號、未設任何旗標
✓ `window.setFlags(FLAG_SECURE, FLAG_SECURE)`（進入該畫面時設定，離開時清除）

例外：使用者主動需要截圖的內容（票券 QR code 等），須為明確的產品決策。 來源：https://developer.android.com/reference/android/view/WindowManager.LayoutParams#FLAG_SECURE

### biometric-success-trusted-without-crypto · MUST · new-only · manual

生物辨識回呼成功不得單獨作為授權依據（僅是 UI 層 gate）。保護敏感操作時必須綁定 `CryptoObject`——用 `setUserAuthenticationRequired(true)` 產生的 Keystore 金鑰解密憑證，或以結果換取後端驗證；並明確指定 authenticator 強度。

✗ `onAuthenticationSucceeded { navigateToPayment() }`
✓ `onAuthenticationSucceeded { result -> decryptTokenWith(result.cryptoObject) }`

例外：純便利性用途的畫面解鎖，且解鎖後不解除任何實際權限。 來源：https://developer.android.com/training/sign-in/biometric-auth

### debuggable-or-backup-enabled-in-release · MUST_NOT · new-only · regex

release build 不得 `android:debuggable="true"`；含敏感資料時 `android:allowBackup` 必須為 `false` 或以 backup rules 排除敏感檔案。

✗ `<application android:allowBackup="true">` 且 app 會存 token
✓ `android:allowBackup="false"`，或以 `dataExtractionRules` 排除認證相關檔案

例外：明確不存任何敏感資料的 app 可保留備份。 來源：https://developer.android.com/privacy-and-security/security-tips

---

## 尚無定論（建議，非規則）

- **token 儲存方案**：`androidx.security-crypto` 已 deprecated 而官方尚未提供等價的高階替代。建議：refresh token 以 Keystore（`setUserAuthenticationRequired` 視敏感度）加密後存 DataStore；access token 只放記憶體。若不想自刻加解密，Tink 是目前業界主流選擇。
- **certificate pinning 要不要做**：官方立場是「多數 app 用系統信任鏈即可」。建議只對支付、登入等少數端點 pin，且必須滿足 `unmanaged-certificate-pin` 的三項條件；否則不做的風險低於做壞的風險。
- **root／模擬器偵測與完整性驗證**：無官方通用準則。建議把它當作風控訊號而非安全邊界，判斷放後端，client 只回報；不要用它擋功能。
- **第三方 SDK 的資料蒐集**：建議建立 SDK 引入的審查流程（要求哪些權限、送出哪些識別碼、是否可延後初始化），並與隱私政策對齊。

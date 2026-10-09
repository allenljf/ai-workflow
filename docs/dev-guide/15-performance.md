# 15 · 效能與相容性

**管**：App 啟動路徑（`Application` / `Activity.onCreate`）、主執行緒阻塞、記憶體洩漏、繪製熱路徑與 jank 量測、R8 / minify 設定、targetSdk 36 系統列相容。
**不管**：Compose 重組與 `LazyColumn` 效能、coroutine dispatcher 與 scope 選型、模組依賴與 Gradle 結構、release log 的敏感資訊。

跨檔主題（**只在對應檔案定義，這裡不重述**）：

- 硬寫 `Dispatchers.IO`、`runBlocking`、`GlobalScope`、suspend main-safe → [11-coroutines-flow.md](11-coroutines-flow.md)
- composition 內做 I/O 或重運算、`LazyColumn` 的 `key`、重組穩定性 → [10-compose-performance.md](10-compose-performance.md)
- ViewModel 持有 `Context` / `Activity` → [08-ui-state.md](08-ui-state.md#context-in-viewmodel)
- release 不得輸出 token / 個資 / 完整 body → [18-security.md](18-security.md#pii-in-log)
- 新增 `res/layout/*.xml` 與 Epoxy model → [09a-compose-api.md](09a-compose-api.md)

---

## 一、啟動路徑

### blocking-io-in-app-oncreate · MUST_NOT · new-only+on-touch · manual

`Application.onCreate()`（含其呼叫到的初始化函式）內不得出現同步磁碟 I/O、`SharedPreferences` 讀取、Room 建庫、網路請求、Gson/JSON 反序列化、Bitmap 解碼。需要這些的初始化一律延後或丟到注入的背景 dispatcher。

✗ `override fun onCreate() { val cfg = gson.fromJson(assets.open("config.json").reader(), Config::class.java) }`
✓ `override fun onCreate() { appScope.launch(ioDispatcher) { configLoader.warmUp() } }`  // appScope 由 DI 注入

例外：Crashlytics / Koin `startKoin` 本身的容器建立。

### eager-startup-init · MUST · new-only · manual

啟動期必要的元件一律 `by lazy` 或 Koin 預設的 lazy 解析；需要在啟動時自動跑的一次性工作用 `androidx.startup` 的 `Initializer<T>` 並在 `dependencies()` 宣告順序，不得在 `onCreate` 直接建構。

✗ `val imageCache = ImageCache(this)`  // Application 欄位，onCreate 一定被建構
✓ `class CartMigrationInitializer : Initializer<Unit> { override fun create(ctx: Context) { ... } }`

例外：`startKoin` 載入的 module 清單本身（Koin definition 是 lazy，登記不等於建構）。
既有違規：`KKdayApp.kt:233` 一次載入 59 個 Koin module → [90-migration-ledger.md#m-26](90-migration-ledger.md)

### custom-init-contentprovider · MUST_NOT · new-only · manual

不得為了初始化 SDK 而自建 `ContentProvider`。改實作 `androidx.startup` 的 `Initializer<T>`；不需要在啟動期跑的第三方元件，在 manifest 用 `tools:node="remove"` 拿掉其自動初始化 provider，改由 `AppInitializer.getInstance(ctx).initializeComponent(...)` 按需啟動。

✗ `class AnalyticsInitProvider : ContentProvider() { override fun onCreate(): Boolean { Sdk.init(context) ... } }`
✓ `<provider android:name="com.vendor.SdkInitProvider" tools:node="remove" />`

### custom-splash-activity · MUST_NOT · new-only · manual

不得新增專屬 splash Activity，也不得用 `windowDisablePreview` 做啟動畫面。一律 `androidx.core:core-splashscreen`，且 `installSplashScreen()` 必須在 `super.onCreate()` **之前**呼叫。

✗ `class SplashActivity : AppCompatActivity()` + `Handler().postDelayed({ startActivity(...) }, 1500)`
✓ `override fun onCreate(b: Bundle?) { installSplashScreen(); super.onCreate(b) }`

### heavy-work-in-oncreate · MUST_NOT · new-only+on-touch · manual

`Activity.onCreate()` / `Fragment.onViewCreated()` 內不得同步解碼 Bitmap、光柵化大型 VectorDrawable、讀寫磁碟或發網路請求。圖片一律交給 Coil 非同步載入並先顯示 placeholder。

✗ `imageView.setImageBitmap(BitmapFactory.decodeFile(path))`
✓ `imageView.load(path) { placeholder(R.drawable.img_placeholder) }`

例外：啟動路徑上的重量級 Composable（地圖、WebView、播放器）延後首個 frame 之後再 compose，判定條件見 [10-compose-performance.md](10-compose-performance.md)。

---

## 二、主執行緒與記憶體

### main-thread-blocking-call · MUST_NOT · new-only+on-touch · manual

主執行緒程式碼（非 suspend 函式、`onClick`、`onBindViewHolder`、Composable）不得呼叫 `SharedPreferences.Editor.commit()`、`Future.get()`、`CountDownLatch.await()`、`.blockingGet()`、`Thread.sleep()`。

✗ `prefs.edit().putString(KEY, v).commit()`
✓ `prefs.edit().putString(KEY, v).apply()`  // 或改 DataStore 的 suspend API

> `runBlocking` 屬同一類但由別處管 → 見 [11-coroutines-flow.md](11-coroutines-flow.md#run-blocking-prod)

### static-context-reference · MUST_NOT · new-only+on-touch · manual

`companion object`、top-level `object`、`@Single` 以外的靜態欄位不得存放 `Context`、`Activity`、`View`、`Fragment`、`Dialog`、`Adapter`。唯一例外是在 `Application.onCreate` 賦值的 `applicationContext`。

✗ `companion object { var currentActivity: Activity? = null }`
✓ `class ToastPresenter(private val appContext: Context)`  // 由 DI 注入 application context

### unbalanced-listener-registration · MUST · new-only+on-touch · manual

每一處 `register` / `add` / `subscribe`（`BroadcastReceiver`、`SensorManager`、`LocationListener`、EventBus、Socket.IO listener、`ViewTreeObserver`）都必須有對稱的解除，位置為 `onDestroy` / `onDestroyView` / `ViewModel.onCleared()` / `DisposableEffect` 的 `onDispose`。

✗ 只在 `onCreate` 呼叫 `socket.on(EVENT, listener)`
✓ `DisposableEffect(Unit) { socket.on(EVENT, l); onDispose { socket.off(EVENT, l) } }`

### allocation-in-hot-path · MUST_NOT · new-only+on-touch · manual

`onDraw()`、`onMeasure()`、`onBindViewHolder()`、Compose 的 draw / layout lambda、每 frame 執行的迴圈內不得 `new` 物件（`Paint`、`Rect`、`Path`、`Matrix`、字串串接）。改在建構期建立並重用。

✗ `override fun onDraw(c: Canvas) { val p = Paint().apply { color = ... }; c.drawRect(RectF(...), p) }`
✓ `private val paint = Paint()` + `private val rect = RectF()`，`onDraw` 只做 `rect.set(...)`

### animate-with-layout-params · MUST_NOT · new-only+on-touch · manual

動畫只能改 `translationX/Y`、`scaleX/Y`、`rotation`、`alpha` 等 render property。禁止在動畫每一 frame 改 `LayoutParams`、`padding`、`margin` 或呼叫 `requestLayout()`。

✗ `ValueAnimator.ofInt(0, 200).addUpdateListener { v.layoutParams.height = it.animatedValue as Int; v.requestLayout() }`
✓ `v.animate().translationY(target).setDuration(DURATION_MS)`

### notify-data-set-changed · MUST_NOT · new-only · manual

新增或改寫的 `RecyclerView.Adapter` 不得呼叫 `notifyDataSetChanged()`；用 `ListAdapter` + `DiffUtil.ItemCallback`。

✗ `items = newList; notifyDataSetChanged()`
✓ `class OrderAdapter : ListAdapter<Order, VH>(OrderDiff)` + `submitList(newList)`

例外：既有 Adapter **不在功能 PR 裡順手改**（動畫、捲動位置、選取狀態有行為風險）。
既有違規：110 檔 → [90-migration-ledger.md#m-11](90-migration-ledger.md)

---

## 三、量測與 build 設定

### measure-perf-on-release · MUST · new-only · manual

任何效能數據（啟動時間、jank、記憶體）不得以 `debug` build 或模擬器量測。必須用 `minify` 開啟且 `isDebuggable = false` 的 build type（本專案為 `miniDebug`）在實體裝置上跑。frame 預算：60Hz = 16ms、90Hz = 11ms、120Hz = 8ms；16ms–700ms 記 slow frame、>700ms 記 frozen frame。

✗ 用 `assembleDevelopDebug` 的 APK 量冷啟動並宣稱「沒有變慢」
✓ `./gradlew installStageMiniDebug` 後在實機量測，附上量測裝置與 build type

例外：無。任何未附 build type / 裝置的效能結論一律視為無效。

### baseline-profile-setup · SHOULD · migrate · manual

正式版 APK/AAB 應內含 baseline profile：`androidx.profileinstaller` 依賴 + `androidx.baselineprofile` plugin + 獨立 `com.android.test` 模組（`:benchmark`）產生 `baseline-prof.txt` / `startup-prof.txt`。產生用的 variant 必須 `isMinifyEnabled = false`，正式 release variant 必須 `true`。

✗ 手寫 `baseline-prof.txt` 塞進 `:app/src/main`
✓ `:benchmark` 模組的 `BaselineProfileGenerator` 涵蓋冷啟動 + 首頁捲動 + 下單前流程

例外：**絕對不進 PR gate**（frame timing 裝置雜訊過大）；產生時機為 release branch 建立時由 CI 手動觸發，不開 `automaticGenerationDuringBuild`。
既有違規：專案 0 個 baseline profile / 無 `:benchmark` 模組 → [90-migration-ledger.md#m-25](90-migration-ledger.md)

### proguard-non-optimize-file · MUST · migrate · manual

minify 開啟的 build type 必須用 `getDefaultProguardFile("proguard-android-optimize.txt")`；不得用 `proguard-android.txt`，`.pro` 檔內不得出現 `-dontoptimize` / `-dontshrink` / `-dontobfuscate`。

✗ `getDefaultProguardFile("proguard-android.txt")`
✓ `getDefaultProguardFile("proguard-android-optimize.txt")`

既有違規：`app/build.gradle.kts:153`（miniDebug）、`:171`（release）用非 optimize 檔；`gradle.properties:51` 另有 `android.enableR8.fullMode=false` → [90-migration-ledger.md#m-25](90-migration-ledger.md)

### shrink-resources-off · MUST · migrate · manual

`isMinifyEnabled = true` 的 build type 必須同時 `isShrinkResources = true`（資源縮減需搭配程式碼縮減才生效）。

✗ `release { isMinifyEnabled = true; isShrinkResources = false }`
✓ `release { isMinifyEnabled = true; isShrinkResources = true }`

例外：開啟後必須實機跑過主流程（反射取用的資源可能被移除），因此屬專案級任務而非功能 PR 順手改。
既有違規：`app/build.gradle.kts:165` → [90-migration-ledger.md#m-25](90-migration-ledger.md)

### wildcard-keep-rule · SHOULD_NOT · new-only · manual

`proguard-rules.pro` 不得新增整包 wildcard keep。只對真正靠反射存取的類別做精準 keep，或用 `@Keep` 註解；DTO 用 `-keepclassmembers`。

✗ `-keep class com.kkday.** { *; }`
✓ `-keepclassmembers class com.kkday.model.OrderDto { <fields>; }`

### mapping-upload-disabled · MUST · new-only · manual

任何對外發佈（Firebase App Distribution / Play Console）的 build type 必須保留並上傳 `mapping.txt`。

✗ `the(CrashlyticsExtension::class).mappingFileUploadEnabled = false`（在 miniDebug / release）
✓ release 與 miniDebug 皆 `mappingFileUploadEnabled = true`

例外：`debug` build type 可關閉（加快建置），目前設定正確，維持即可。

### strictmode-in-release · MUST_NOT · new-only · manual

`StrictMode` 只能在 `debug` build 啟用，penalty 一律 `penaltyLog`。`miniDebug` / `release` 不得有任何 StrictMode 設定，任何可出貨 build type 不得使用 `penaltyDeath` / `penaltyDeathOnNetwork`。

✗ `StrictMode.setThreadPolicy(Builder().detectAll().penaltyDeath().build())`
✓ `if (BuildConfig.DEBUG) StrictMode.setThreadPolicy(Builder().detectDiskWrites().detectNetwork().penaltyLog().build())`

### leakcanary-not-debug-only · MUST_NOT · new-only · manual

LeakCanary 只能以 `debugImplementation` 引入，release classpath 不得有任何 LeakCanary 參照。

✗ `implementation(libs.leakCanary)`
✓ `debugImplementation(libs.leakCanary)`

例外：`app/build.gradle.kts:502` 目前整行被註解，等同未導入；重新啟用時必須用 `debugImplementation`。

---

## 四、相容性

### legacy-system-bar · MUST_NOT · new-only+on-touch · lint:legacy-system-bar

不得指派 `window.statusBarColor` / `window.navigationBarColor`（targetSdk 36 起無效）。一律用專案的 `SystemBarLegacyCompat`，或其 `Activity` 擴充函式。

✗ `window.statusBarColor = StyleDictionary.kkColorBackgroundPrimary.toArgb()`
✓ `setStatusBarColorCompat(StyleDictionary.kkColorBackgroundPrimary.toArgb())`

例外：無。紅線 I1。
補充：`rememberSystemUiController`（Accompanist，20 檔）同樣不得新增，替代方案是 `SystemBarLegacyCompat` + `enableEdgeToEdge()` → [90-migration-ledger.md#m-14](90-migration-ledger.md)

# 16 · 效能與啟動

**管**：效能數字怎麼量才算數、冷啟動、主執行緒阻塞、記憶體洩漏、frame timing 與 jank、Baseline Profile、Macrobenchmark、R8／minify、App 大小。
**不管**：重組次數與 Compose 端的優化手法（`11-compose-performance` 全包，本檔一條都不重複）、測試寫法、混淆的安全面。
**先確認**：第一條規則是其餘所有條的前提——**debug build 量到的數字一律無效**，包含你憑手感覺得「有點卡」。

| 想找 | 去 |
|---|---|
| 重組過多、lazy list `key` / `contentType`、stability、延後讀取 state、非同步圖片 0px | `11-compose-performance` |
| dispatcher 注入、`runBlocking` 禁令、`GlobalScope`、取消與結構化併發 | `12-coroutines-flow` |
| wildcard `-keep`、release 不得留 debug log、`debuggable` / `allowBackup` | `17-security` |
| ViewModel 不得持有 `Context`（同時是最常見的洩漏來源） | `08-ui-state` |

---

## 一、量測紀律

順序不可顛倒，每一步做完才進下一步：① 說清楚要修的是啟動、jank 還是記憶體，寫下當前數字 → ② 在 release-like build ＋ 實體裝置建立基準，記錄中位數與 P90 → ③ 用 trace（system trace／Macrobenchmark）指出時間花在哪，不要用猜的 → ④ 一次只改一個變因 → ⑤ 同一支 benchmark、同一台裝置再量一次；沒有改善就 revert，不要「反正加了也不會壞」。

**build type 對照**（R8、JIT/AOT 狀態、debugger 附掛狀況都不同，數字沒有可比性）：

| build type | 能拿來做什麼 | 不能 |
|---|---|---|
| `debug` | 功能開發、StrictMode 抓主執行緒阻塞、抓洩漏 | 任何啟動／jank／記憶體數字 |
| `benchmark`（`isMinifyEnabled = true`、`debuggable = false`、簽 debug key） | Macrobenchmark、baseline profile 產生與驗證 | — |
| `release` | 送測前實機跑完主流程 | 未宣告 `profileable` 時無法接 profiler |

---

## 二、規則

### perf-number-from-non-release-build · MUST · new-only · manual

任何效能結論（啟動時間、frame time、記憶體、電量）必須在 `isMinifyEnabled = true` 且 `debuggable = false` 的 build type、實體裝置、未連接 debugger 的情況下取得，並在 PR 註明 variant 與機型。emulator 與 debug build 的數字不得作為優化依據或驗收依據。

✗ 「本機 debug 包測起來冷啟動 2.1s，所以要優化這段」
✓ 「`benchmark` variant／實體中階機／10 iterations：冷啟動 TTID 中位數 812ms → 604ms」

例外：無（Compose 重組次數的對應規則見 `11-compose-performance` 的 `perf-claim-from-debug-build`）· source: https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview

### optimization-without-measurement · MUST_NOT · new-only · manual

不得以「這樣比較快」為由改寫程式碼結構、換資料結構、加快取或加執行緒，除非 PR 內附前後對照數字。可讀性下降而效能無證據的改動一律 revert。

✗ 「把 `map` 改成手寫 for loop 以減少配置」——無任何量測
✓ 「trace 顯示 `OrderMapper` 在啟動路徑佔 180ms，改為 lazy 後降至 12ms（附 benchmark 輸出）」

例外：修正明確的正確性問題（主執行緒 I/O、洩漏、O(n²) 演算法）不需要先量測 · source: https://developer.android.com/topic/performance/overview

### blocking-work-in-application-oncreate · MUST_NOT · new-only+on-touch · manual

`Application.onCreate()` 內不得有任何同步阻塞呼叫：檔案／`SharedPreferences` 讀取、資料庫建立、網路請求、JSON 反序列化、Bitmap 解碼、第三方 SDK 的同步 init。需要這些工作時改為延後（首次使用才做）或丟到注入的背景 dispatcher。這一段是整個冷啟動最容易搞砸的地方，且所有畫面都躲不掉。

✗ `override fun onCreate() { super.onCreate(); val cfg = readConfigFile(); analytics.init(cfg) }`
✓ `override fun onCreate() { super.onCreate(); appScope.launch { configRepository.warmUp() } }`

例外：無 · source: https://developer.android.com/topic/performance/vitals/launch-time

### eager-global-singleton-init · MUST · new-only+on-touch · manual

全域單例不得在啟動期被動建構。DI 綁定一律保持 lazy（`@Singleton` 只在首次注入時建立），自行持有的全域欄位一律 `by lazy`；不得在 `Application` 內以欄位初始化的方式把整張物件圖拉起來。

✗ `class MainApplication : Application() { val db = Room.databaseBuilder(...).build() }`
✓ `class MainApplication : Application()` ＋ `@Provides @Singleton fun provideDb(...) = Room.databaseBuilder(...).build()`（首次注入才建）

例外：首幀就一定要用到的元件，但需在 PR 說明並計入啟動預算 · source: https://developer.android.com/topic/performance/vitals/launch-time

### sdk-init-via-custom-contentprovider · MUST_NOT · new-only · manual

不得為了初始化而新增自訂 `ContentProvider`（每一個都在 `Application.onCreate` 之前被建立，且無法排序）。啟動期必須初始化的元件一律實作 App Startup 的 `Initializer<T>` 並在 `dependencies()` 宣告順序；啟動期用不到的第三方自動初始化，必須在 manifest 以 `tools:node="remove"` 移除其 `<provider>`，改由 `AppInitializer.getInstance(context).initializeComponent(...)` 或該套件的按需機制啟動。

✗ `<provider android:name=".AnalyticsInitProvider" android:authorities="..." />`
✓ `class AnalyticsInitializer : Initializer<AnalyticsClient>` ＋ manifest 內對應的 `<meta-data>`

例外：真正提供資料給其他 App 的 `ContentProvider` · source: https://developer.android.com/topic/libraries/app-startup

### heavy-work-in-first-frame · MUST_NOT · new-only+on-touch · manual

首屏的 `onCreate()` 與首次 composition 內不得做同步 Bitmap 解碼、大型 vector 光柵化、磁碟或網路 I/O；圖片一律交給非同步載入器並先給 placeholder。啟動路徑上的重量級元件（地圖、`WebView`、影片播放器、大量圖卡）必須由狀態旗標控制，首幀之後才進入組合。也不得用專屬 splash Activity、`postDelayed` 停留或 `windowDisablePreview` 製作啟動畫面（多一個 Activity 就多一輪 inflate 與 transition）——一律用 SplashScreen API，`installSplashScreen()` 在 `super.onCreate()` 之前呼叫，延長顯示只能用 `setKeepOnScreenCondition { }` 綁真實的資料就緒條件。

✗ `setContent { MapView(...); OrderScreen(...) }`；`class SplashActivity` ＋ `postDelayed(1500) { startActivity(mainIntent) }`
✓ `var showMap by remember { mutableStateOf(false) }` ＋ `LaunchedEffect(Unit) { showMap = true }`；`installSplashScreen().setKeepOnScreenCondition { !viewModel.isReady }`

例外：該元件本身就是首屏的主要內容 · source: https://developer.android.com/develop/ui/views/launch/splash-screen

### missing-fully-drawn-report · SHOULD · migrate · manual

啟動路徑上的畫面必須回報「真正可互動」的時點（TTFD），否則統計上只看得到首幀（TTID），資料載入的延遲完全不會被算進去。Compose 用 `ReportDrawnWhen { }` / `ReportDrawnAfter { }`，Views 用 `reportFullyDrawn()`，時機是首屏資料到齊、使用者能操作的那一刻。

✗ 首屏 skeleton 顯示即算完成，實際資料 2 秒後才進來
✓ `ReportDrawnWhen { uiState.content !is OrderContent.Loading }`

例外：畫面無非同步資料，TTID 即 TTFD · source: https://developer.android.com/topic/performance/vitals/launch-time#time-full

### missing-strictmode-in-debug · MUST · new-only+on-touch · manual

debug build 的 `Application.onCreate` 必須啟用 StrictMode：`ThreadPolicy` 開 `detectDiskReads` / `detectDiskWrites` / `detectNetwork` / `detectCustomSlowCalls`，`VmPolicy` 開 `detectActivityLeaks` / `detectLeakedClosableObjects` / `detectLeakedRegistrationObjects`，penalty 一律 `penaltyLog()`。同一個 debug-only 區塊也必須掛上 heap 洩漏偵測工具，且只能以 `debugImplementation` 引入（release 不得留下任何參照）。可出貨的 build type 不得啟用 StrictMode，任何情況都不得用 `penaltyDeath()`。

✗ 專案完全沒有 StrictMode，主執行緒 I/O 與洩漏只能靠 code review 抓
✓ `if (BuildConfig.DEBUG) { StrictMode.setThreadPolicy(ThreadPolicy.Builder().detectAll().penaltyLog().build()) }` ＋ `debugImplementation("<leak-detector>")`

例外：無 · source: https://developer.android.com/reference/android/os/StrictMode ／ 官方 sample nowinandroid

### blocking-api-on-main-thread · MUST_NOT · new-only+on-touch · regex

主執行緒程式碼（Activity／Fragment／Composable／click listener／adapter bind／`BroadcastReceiver.onReceive`）不得呼叫阻塞式 API：`Thread.sleep`、`CountDownLatch.await()`、`Future.get()`、`.blockingGet()`、`SharedPreferences.Editor.commit()`、同步檔案或 DB 存取。`BroadcastReceiver` 需要較長處理時用 `goAsync()` 並在完成後 `finish()`，或直接改派背景工作排程。

✗ `prefs.edit().putBoolean(KEY_SEEN, true).commit()`
✓ `prefs.edit().putBoolean(KEY_SEEN, true).apply()`（或改用 DataStore 的 suspend API）

例外：`runBlocking` 的禁令與例外由 `12-coroutines-flow` 的 `runblocking-in-production` 定義 · source: https://developer.android.com/topic/performance/vitals/anr

### static-context-reference · MUST_NOT · new-only+on-touch · regex

`companion object`、top-level `object`、`static` 欄位不得存放 `Context`、`Activity`、`Fragment`、`View`、`Dialog`、`Adapter`，或任何間接抓著它們的物件（含 lambda 捕獲）。唯一可接受的是在 `Application.onCreate` 賦值的 `applicationContext`。

✗ `object ToastHelper { lateinit var context: Context }`（存進 Activity 就是整棵 view tree 洩漏）
✓ `class ToastHelper @Inject constructor(@ApplicationContext private val context: Context)`

例外：`applicationContext`（生命週期與進程相同）· source: https://developer.android.com/topic/performance/memory

### unbalanced-listener-registration · MUST · new-only+on-touch · manual

每一處 `register` / `add` / `subscribe`（`BroadcastReceiver`、感測器、定位、第三方 SDK listener、`ViewTreeObserver`）都必須有對稱的解除，位置分別是 `onDestroy` / `onDestroyView` / `ViewModel.onCleared()` / `DisposableEffect` 的 `onDispose`。`Handler` 的延遲訊息必須在銷毀時 `removeCallbacksAndMessages(null)`，且不得用非靜態內部類別的 `Handler` 或 `Runnable` 持有畫面。

✗ `sensorManager.registerListener(this, sensor, RATE)` 而 `onDestroy()` 內沒有 `unregisterListener`
✓ `DisposableEffect(Unit) { manager.register(callback); onDispose { manager.unregister(callback) } }`

例外：註冊對象生命週期與進程相同且全程只註冊一次 · source: https://developer.android.com/topic/performance/memory

### allocation-in-frame-hot-path · MUST_NOT · new-only · manual

每幀都會執行的程式碼（自訂 `View` 的 `onDraw` / `onMeasure` / `onLayout`、adapter 的 bind、Compose 的 draw／layout lambda、動畫 callback）內不得配置物件：`Paint`、`Rect`、`Path`、`Matrix`、字串串接、集合複製。一律在建構期建立並重用。動畫只改 `translationX/Y`、`scaleX/Y`、`rotation`、`alpha` 等 render property，不得每幀改 `LayoutParams` / padding 或呼叫 `requestLayout()`。

✗ `override fun onDraw(canvas: Canvas) { val paint = Paint().apply { ... }; canvas.drawRect(RectF(...), paint) }`
✓ `private val paint = Paint()` / `private val rect = RectF()`，`onDraw` 內只更新欄位值

例外：無 · source: https://developer.android.com/topic/performance/vitals/render

### scroll-without-frame-metric · SHOULD · migrate · manual

關鍵捲動與轉場必須有 Macrobenchmark `FrameTimingMetric` 覆蓋，判定用 frame 預算：60Hz 為 16ms、90Hz 為 11ms、120Hz 為 8ms；單幀 16ms–700ms 記為 slow frame、超過 700ms 記為 frozen frame。不得以「滑起來還好」作為驗收依據。

✗ 手動滑一滑目視判斷
✓ `metrics = listOf(FrameTimingMetric())` ＋ 在 CI 追 `frameDurationCpuMs` 的 P90

例外：非核心流程的次要畫面 · source: https://developer.android.com/topic/performance/vitals/render

### release-without-baseline-profile · SHOULD · migrate · manual

對外發佈的 APK/AAB 必須內含 baseline profile：加入 `androidx.profileinstaller` 依賴，用 Baseline Profile Gradle Plugin 產生 `src/<variant>/generated/baselineProfiles/`（同時含 `startup-prof.txt`）。profile 必須涵蓋啟動路徑與核心使用者旅程，不能只錄冷啟動就結束。

✗ 只有 `baseline-prof.txt`，內容僅到首屏
✓ benchmark 依序走過啟動 → 清單捲動 → 進入詳情 → 送出，全程錄進 profile

例外：無 · source: https://developer.android.com/topic/performance/baselineprofiles/overview

### baseline-profile-minify-mismatch · MUST · migrate · manual

產生 baseline profile 的 variant 必須 `isMinifyEnabled = false`（否則錄到的是混淆後名稱，對不上正式版），正式 release variant 必須 `isMinifyEnabled = true`。兩者不得顛倒，也不得設成同一值。

✗ 產生用 variant 設 `isMinifyEnabled = true`
✓ 產生用 variant `isMinifyEnabled = false` ／ release `isMinifyEnabled = true`

例外：無 · source: https://developer.android.com/topic/performance/baselineprofiles/create-baselineprofile

### stale-baseline-profile · MUST · new-only+on-touch · manual

改動啟動流程、重構關鍵路徑、變更套件名或升級主要相依後，必須重新產生 baseline profile 並驗證仍然有效：用同一支 Macrobenchmark 比較 `CompilationMode.None()` 與 `CompilationMode.Partial(baselineProfileMode = BaselineProfileMode.Require)` 的中位數，沒有差距代表 profile 沒命中熱路徑，等於沒有。產出檔案控制在 1.5 MB 以內。

✗ profile 自兩年前建立後從未更新，套件名早已變更
✓ CI 定期重新產生，PR 附 `None` vs `Partial` 的對照數字

例外：無 · source: https://developer.android.com/topic/performance/baselineprofiles/measure-baselineprofile

### release-without-code-shrinking · MUST · migrate · regex

release 與可壓測的 benchmark build type 必須 `isMinifyEnabled = true` 並同時 `isShrinkResources = true`（資源縮減必須搭配程式碼縮減才生效），且必須引用 `getDefaultProguardFile("proguard-android-optimize.txt")`。任何 `.pro` 檔不得出現 `-dontoptimize` / `-dontshrink` / `-dontobfuscate`。開啟後送測前必須實機跑過主流程——反射與序列化的路徑只會在 runtime 壞掉。

✗ `release { isMinifyEnabled = false }` ／ `getDefaultProguardFile("proguard-android.txt")`
✓ `release { isMinifyEnabled = true; isShrinkResources = true; proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro") }`

例外：keep 規則的寫法與 wildcard 禁令見 `17-security` 的 `wildcard-keep-rule` · source: https://developer.android.com/build/shrink-code

### mapping-file-not-preserved · MUST · new-only+on-touch · manual

每一個對外發佈的 build 都必須保存 `mapping.txt` 並上傳至 crash 報告服務與商店後台，CI 需將它列為 build artifact。沒有對應 mapping 的混淆 stack trace 無法還原，等於該版本的 crash 全部失去診斷能力。

✗ CI 只上傳 AAB
✓ CI artifact 含 `app/build/outputs/mapping/<variant>/mapping.txt`，並在發版流程上傳

例外：無 · source: https://developer.android.com/build/shrink-code#retracing

### raster-asset-for-new-image · SHOULD · new-only+on-touch · regex

新增圖片資源優先用 vector drawable，無法向量化時用 WebP，不得新增 PNG／JPG。發佈一律走 App Bundle，讓商店依裝置切分密度、語系與 ABI；不得為了省事發佈 universal APK，也不得把用不到的原生庫 ABI 一起打包。

✗ `res/drawable-xxhdpi/banner_hero.png`
✓ `res/drawable/ic_banner.xml`（vector）或 `res/drawable-nodpi/banner_hero.webp`

例外：需要精確像素的攝影圖，或第三方提供且無法轉檔的素材 · source: https://developer.android.com/topic/performance/reduce-apk-size

---

## 三、冷啟動階段與預算

| 階段 | 從 → 到 | 你能控制的 | 常見地雷 |
|---|---|---|---|
| 進程建立 | 點擊圖示 → 進程 fork | 幾乎不能控制 | 過多 `ContentProvider` 自動初始化 |
| Application | `onCreate` 進 → 出 | **最容易搞砸的一段** | SDK 同步 init、讀 `SharedPreferences`、建 DB、物件圖被整張拉起 |
| 首幀（TTID） | Activity `onCreate` → 第一幀 | 首屏層級深度、同步解碼 | splash Activity、首屏一次組合全部內容 |
| 可互動（TTFD） | 第一幀 → 資料就緒 | 首屏請求併發、快取先渲染 | 序列化的多支 API、沒有回報 fully drawn |

**預算**：冷啟動 TTID 目標 500ms、暖啟動 200ms、熱啟動 150ms 以內。任一項觸及商店 vitals 的不良門檻（冷 5s／暖 2s／熱 1.5s）視為阻斷性缺陷，不得排到下個版本。

## 四、一支 Macrobenchmark 長什麼樣

Macrobenchmark 必須放在獨立的 `com.android.test` 模組（例如 `:benchmark`，設 `targetProjectPath = ":app"`），不得與 App 程式碼同模組；受測 variant 需宣告 `<profileable android:shell="true" />` 並依賴 `androidx.profileinstaller`。

```kotlin
@RunWith(AndroidJUnit4::class) class StartupBenchmark {
    @get:Rule val rule = MacrobenchmarkRule()
    @Test fun coldStartup() = rule.measureRepeated(
        packageName = "com.example.app", metrics = listOf(StartupTimingMetric()),
        compilationMode = CompilationMode.Partial(BaselineProfileMode.Require),
        startupMode = StartupMode.COLD, iterations = 10,
    ) { pressHome(); startActivityAndWait() }
}
```

只把 `compilationMode` 換成 `CompilationMode.None()` 再跑一次，兩份 `timeToInitialDisplayMs` 中位數的差距就是 baseline profile 的實際效益。捲動場景把 metric 換成 `FrameTimingMetric()`，並在 `measureBlock` 內操作目標清單。

## 五、尚無定論

官方未表態，以下是**建議不是規則**，專案內一致即可：

- **baseline profile 產物要不要進版控**：commit 產物可重現、看得到 diff；改由 CI 每次重產則永不過期但拉長建置時間。建議 commit 產物 ＋ 排程定期重產。
- **正式版的線上 frame 監控**：商店後台的 vitals 是目前唯一穩定的來源；App 內 frame 監控函式庫尚無穩定版，導入請當選配而非驗收條件。
- **R8 full mode**：新版 AGP 預設開啟，優化更積極、對反射也更嚴格。建議維持開啟並補足精準 keep 規則，不要為了讓某個第三方套件跑起來就整包關掉。

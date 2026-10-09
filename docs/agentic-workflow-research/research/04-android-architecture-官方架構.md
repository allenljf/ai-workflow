# Official modern Android app architecture guidance (2025–2026): what an agent-authored codebase must comply with — layers, UDF, state, modularization, Compose, DI, and the 2026 platform/toolchain baseline

## SUMMARY
Google's official guidance is a 2–3 layer model: **UI layer** (Compose UI elements + state holders) → optional **domain layer** (use cases) → **data layer** (repositories + data sources). It is explicitly NOT Clean Architecture — Now in Android says so in a NOTE box and links a discussion thread. The `/topic/architecture/recommendations` page is the single most quotable artifact: it grades every rule as *Strongly recommended / Recommended / Optional*. Strongly recommended: clearly defined data layer + UI layer; expose data via a repository; coroutines+flows; UDF; AAC ViewModels; lifecycle-aware collection (`collectAsStateWithLifecycle`); **"Do not send events from the ViewModel to the UI"**; single-activity; Jetpack Compose; ViewModels at screen level only; plain state holder classes in reusable UI; DI; prefer fakes to mocks; test StateFlows. Only *Recommended*: use Hilt, expose a UI state, don't use `AndroidViewModel`, model-per-layer. Domain layer is "recommended in big apps" only.

The one-off-event question is settled officially: Channels/SharedFlow are called out by name as not guaranteeing delivery when the producer outlives the consumer — the doctrine is "handle such events immediately and reduce them to UI state." State production canonically uses `combine(...).stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), initialValue)`; `Lazily` is the documented alternative for off-screen back-stack retention. UI state is immutable, named `{functionality}UiState`, modelled as a sealed hierarchy (NiA) or a single data class with derived extension properties. Repositories are the *only* public API of the data layer; one repository per data type; data sources touch exactly one source; local storage is the source of truth for offline-first; reads are `Flow`, writes are `suspend`; everything must be main-safe.

Now in Android has moved on significantly since most blog content: feature modules are now **`:feature:x:api` + `:feature:x:impl`** Gradle module pairs (api holds `NavKey`s; impl may only depend on other features' `api`), navigation is **Navigation 3** (`NavKey`, `EntryProviderScope.entry<T>`, custom `Navigator`/`NavigationState`), and there is a `:core:navigation` module. Build config lives in an included build `build-logic/` with composable convention plugins + a version catalog with `TYPESAFE_PROJECT_ACCESSORS`. 2026 baseline: AGP 9.3 (Gradle 9.5, JDK 17, built-in Kotlin on by default, R8 strict full mode), Kotlin 2.4.10, Compose BOM 2026.08.00, Navigation3 1.1.6 stable, Play requires targetSdk 36 by 2026-08-31, and API 36 ignores orientation/resizability locks on sw≥600dp.

## KEY FACTS
### Official architecture is a 2-layer minimum (UI + data) with an OPTIONAL domain layer
"A well-designed Android app architecture should include at least two layers: UI layer (displays application data on the screen) and Data layer (contains the business logic of your app and exposes application data). An optional domain layer can simplify and reuse interactions between the UI and data layers." Dependency direction is UI → Domain → Data.
SRC: https://developer.android.com/topic/architecture

### The four common architectural principles are named and defined
1) Separation of concerns — "Don't write all your code in an Activity... Don't entrust state to UI components." 2) Drive UI from data models, preferably persistent. 3) Single source of truth — "The SSOT is the owner of that data, and only the SSOT can modify or mutate it"; SSOT exposes data as an immutable type and exposes functions/receives events for mutation. 4) UDF — "State flows in only one direction... Events that modify the data flow in the opposite direction."
SRC: https://developer.android.com/topic/architecture

### The recommendations page grades every rule by priority — this is the authoritative checklist to quote in a guide
STRONGLY RECOMMENDED: Use a clearly defined data layer; Use a clearly defined UI layer; Expose application data from the data layer using a repository; Use coroutines and flows; Follow UDF; Use AAC ViewModels if their benefits apply; Use lifecycle-aware UI state collection; Do not send events from the ViewModel to the UI; Use a single-activity application; Use Jetpack Compose; Keep ViewModels independent of the Android lifecycle; Use ViewModels at screen level; Use plain state holder classes in reusable UI components; Use lifecycle-aware effects in composables instead of overriding Activity lifecycle callbacks; Use dependency injection; Scope to a component when necessary; Know what to test; Prefer fakes to mocks; Test StateFlows. RECOMMENDED: Use a domain layer (in big apps); Do not use AndroidViewModel; Expose a UI state; Use Hilt; Create a model per layer in complex apps. OPTIONAL: all four naming conventions.
SRC: https://developer.android.com/topic/architecture/recommendations

### Hilt is only 'Recommended', while 'Use dependency injection' is 'Strongly recommended'
The architecture guide says "Use the dependency injection pattern and the Hilt library in Android apps" and "Use dependency injection (DI) rather than service locator", but the graded recommendations table lists 'Use dependency injection' as Strongly recommended and 'Use Hilt' only as Recommended. This is the doc hook for projects that use Koin instead.
SRC: https://developer.android.com/topic/architecture/recommendations

### Official position on one-off events: reduce them to UI state; Channels are called out by name as unsafe
"UI actions that originate from the ViewModel—ViewModel events—should always result in a UI state update." And: "you might have seen ViewModel events being exposed to the UI using Kotlin Channels or other reactive streams. When the producer (the ViewModel) outlives the consumer (Compose UI), these solutions don't guarantee the delivery and processing of those events... this could leave the app in an inconsistent state, it could introduce bugs, or the user might miss critical information." Remedy: "Handle such events immediately and reduce them to UI state." And: "don't think about what actions the UI needs to make; think about how those actions affect the UI state."
SRC: https://developer.android.com/topic/architecture/ui-layer/events

### Canonical state-production idiom is combine + stateIn(viewModelScope, WhileSubscribed(5_000), initialValue)
stateIn params: scope, started, initialValue. WhileSubscribed(5_000) = "If no subscriber is present, the upstream flow continues running for 5 seconds before stopping", so the pipeline is active only while the UI is visible and survives configuration changes. Documented alternative: "Use SharingStarted.Lazily if the pipeline must remain active as long as the user might return to the UI (e.g., on back stack or off-screen tab)." Output API selection table: one-shot APIs → StateFlow or Compose State; stream APIs → StateFlow; mixed → StateFlow.
SRC: https://developer.android.com/topic/architecture/ui-layer/state-production

### Mutable state must never be exposed — expose via asStateFlow() or a read-only interface
StateFlow path: `private val _uiState = MutableStateFlow(DiceUiState()); val uiState: StateFlow<DiceUiState> = _uiState.asStateFlow()` with mutation through `_uiState.update { it.copy(...) }` (atomic). Compose State path: `var uiState by mutableStateOf(NewsUiState()); private set`, or a `@Stable interface DiceUiState` with a `private class MutableDiceUiState : DiceUiState` backing it.
SRC: https://developer.android.com/topic/architecture/ui-layer/state-production

### Explicit warning: do not launch async work in a ViewModel init block/constructor
"Don't launch asynchronous operations in the init block or constructor of a ViewModel. This can cause IllegalStateException with Compose State." Prefer lazy initialisation via stateIn's `started` parameter; if explicit init is required use a guarded `@MainThread fun initialize()` with an `initializeCalled` flag.
SRC: https://developer.android.com/topic/architecture/ui-layer/state-production

### UI state modelling rules: immutable, named {functionality}UiState, single object preferred over multiple streams
"UI state must be immutable. Only the data owner should update it." Naming: NewsUiState, NewsItemUiState. "Use a single UI state object for related states to prevent inconsistencies; separate streams only when states are completely independent." Derived values go in extension properties, e.g. `val NewsUiState.canBookmarkNews: Boolean get() = isSignedIn && isPremium`.
SRC: https://developer.android.com/topic/architecture/ui-layer

### Now in Android models UI state as a sealed interface hierarchy (LCE), not booleans
"UI state is modeled as a sealed hierarchy using interfaces and immutable data classes. State objects are only ever emitted through the transform of data streams. This approach ensures that: the UI state always represents the underlying app data... the UI elements handle all possible states." Example: NewsFeedUiState { Loading, Success(feed) }. The offline-first page shows the same shape: `sealed interface AuthorUiState { data object Loading; data class Success(val author: Author); data object Error }` produced with `.map{...}.catch { emit(Error) }.stateIn(...)`.
SRC: https://github.com/android/nowinandroid/blob/main/docs/ArchitectureLearningJourney.md

### Data layer rules: repository is the only public API; one repository per data type; a data source touches exactly one source
"Each data source class should have the responsibility of working with only one source of data, which can be a file, a network source, or a local database." "Other layers must never access data sources directly—only through repositories." "The data exposed by this layer should be immutable so that it cannot be tampered with by other classes." One-shot ops → suspend functions; changes over time → Flows. "Calling data sources and repositories should be main-safe—safe to call from the main thread" (wrap in withContext(ioDispatcher)). Storage picks: Room for large queryable datasets, DataStore for small key-value, files for JSON blobs.
SRC: https://developer.android.com/topic/architecture/data-layer

### Data layer naming conventions are prescribed
Repository: `[DataType]Repository` (NewsRepository, MoviesRepository, PaymentsRepository). Remote source: `[DataType]RemoteDataSource`. Local source: `[DataType]LocalDataSource`. "Avoid naming based on implementation details" — do not use `UserSharedPreferencesDataSource`.
SRC: https://developer.android.com/topic/architecture/data-layer

### Official (Optional-priority) naming conventions for the rest of the codebase
Methods = verb phrases (`makePayment()`). Properties = noun phrases (`inProgressTopicSelection`). Streams = `get{model}Stream` → `getAuthorStream(): Flow<Author>`, plural for lists `getAuthorsStream(): Flow<List<Author>>`. Interface impls = meaningful names (`OfflineFirstNewsRepository`, `InMemoryNewsRepository`), `Default` prefix as last resort (`DefaultNewsRepository`), fakes prefixed `Fake` (`FakeAuthorsRepository`).
SRC: https://developer.android.com/topic/architecture/recommendations

### Domain layer: use cases named verb+noun+UseCase, single functionality, no mutable state, main-safe, new instance per injection
Convention is "verb in present tense + noun/what (optional) + UseCase": FormatDateUseCase, LogOutUserUseCase, GetLatestNewsWithAuthorsUseCase. Expose `operator fun invoke()`. "Use cases should not contain mutable data." "Create a new instance of a use case class every time you pass it as a dependency." Use cases depend on repositories and other use cases. NiA note: "the domain layer in Now in Android does not (for now) contain any use cases for event handling. Events are handled by the UI layer calling methods on repositories directly."
SRC: https://developer.android.com/topic/architecture/domain-layer

### Offline-first: local data source is the source of truth; three write strategies are named
"In order to provide offline-first support, a local data source—such as a database—is the recommended source of truth." Repository must have ≥2 data sources (local = canonical SoT; network = actual state). Write strategies: (1) Online-only writes — for time-sensitive transactions like bank transfers; (2) Queued writes — analytics/logging, drained with exponential backoff via WorkManager; (3) Lazy writes — write local first then queue network notify, for critical data like to-do items. Sync strategies: pull-based (Paging + RemoteMediator), push-based, hybrid. Conflict resolution: last-write-wins with timestamps. Directory layout shown: data/{local/{entities,dao}, network/{models}, model/, repository/} with `NetworkAuthor.asEntity()` and `AuthorEntity.asExternalModel()` mappers.
SRC: https://developer.android.com/topic/architecture/data-layer/offline-first

### Now in Android's module taxonomy has CHANGED: feature modules are now api/impl Gradle module pairs
"Feature modules aren't Gradle modules themselves, they are split into two submodules: `api` - contains navigation keys; `impl` - contains everything else." Dependency rules verbatim: "A feature's `api` module should not depend on another feature's `api` or `impl` module. A feature's `impl` should only depend on another feature's `api` module. Both submodules should only depend on the `core` modules that they require." Core modules: "can depend on other core modules, but they shouldn't depend on feature nor app modules." App module "depends on all feature modules and required core modules."
SRC: https://github.com/android/nowinandroid/blob/main/docs/ModularizationLearningJourney.md

### Actual Now in Android module list (settings.gradle.kts, main branch)
:app, :app-nia-catalog, :benchmarks, :core:analytics, :core:common, :core:data, :core:data-test, :core:database, :core:datastore, :core:datastore-proto, :core:datastore-test, :core:designsystem, :core:domain, :core:model, :core:navigation, :core:network, :core:notifications, :core:screenshot-testing, :core:testing, :core:ui, then :feature:{foryou,interests,bookmarks,topic,search}:{api,impl}, :feature:settings:impl, :lint. Also `enableFeaturePreview("TYPESAFE_PROJECT_ACCESSORS")` and `includeBuild("build-logic")`.
SRC: https://github.com/android/nowinandroid/blob/main/settings.gradle.kts

### core:designsystem vs core:ui distinction is explicit and load-bearing
core:designsystem = "Core UI components (many of which are customized Material 3 components), app theme and icons" (NiaIcons, NiaButton, NiaTheme) — viewable via the `app-nia-catalog` run configuration. core:ui = "Composite UI components and resources used by feature modules, such as the news feed. Unlike the designsystem module, it is dependent on the data layer since it renders models, like news resources" (NewsFeed, NewsResourceCardExpanded). core:common = NiaDispatchers, Result. core:model = Topic, Episode, NewsResource. core:testing = NiaTestRunner, TestDispatcherRule.
SRC: https://github.com/android/nowinandroid/blob/main/docs/ModularizationLearningJourney.md

### api vs implementation: core modules re-export their transitive layers with api(); features/app use implementation()
`:core:data/build.gradle.kts` declares `api(projects.core.common)`, `api(projects.core.database)`, `api(projects.core.datastore)`, `api(projects.core.network)` but `implementation(projects.core.analytics)`, `implementation(projects.core.notifications)`. Feature impl modules use `implementation(projects.core.data)`. `:app` uses `implementation(...)` for every feature and core module. The graph legend in the modularization doc encodes exactly this: app -.implementation.-> feature, library --api--> jvm.
SRC: https://github.com/android/nowinandroid/blob/main/core/data/build.gradle.kts

### Official modularization pitfalls are named: too fine-grained, too coarse-grained, too complex
"Every module brings a certain amount of overhead in the form of increased build complexity and boilerplate code... If overhead counteracts scalability improvements, you should consider consolidating some modules." "If your modules are growing too large you might end up with yet another monolith." "It doesn't always make sense to modularize your project. A dominating factor is the size of the codebase." Also: "You can mark everything but your public interface as `internal` or `private` to prevent it from being used outside the module."
SRC: https://developer.android.com/topic/modularization

### Now in Android is on Navigation 3, not Navigation Compose
gradle/libs.versions.toml pins androidxNavigation3 = "1.0.0" with `androidx.navigation3:navigation3-runtime` and `navigation3-ui`, plus `androidx.lifecycle:lifecycle-viewmodel-navigation3` and `androidx.compose.material3.adaptive:adaptive-navigation3`. Feature api modules hold `@Serializable data class TopicNavKey(val id: String) : NavKey`; impl modules hold an `EntryProviderScope<NavKey>.topicEntry(navigator: Navigator)` extension using `entry<TopicNavKey>(metadata = ListDetailSceneStrategy.detailPane())`. NiA also hand-rolls `core:navigation` with `Navigator(val state: NavigationState)` exposing navigate(key)/goBack().
SRC: https://github.com/android/nowinandroid/blob/main/gradle/libs.versions.toml

### Navigation 3 reached 1.0.0 stable on 2025-11-19; current stable is 1.1.6 (2026-08-12)
Release timeline: 1.0.0 (Nov 19 2025), 1.1.0 (Apr 8 2026), 1.1.5 (Jul 29 2026), 1.1.6 (Aug 12 2026); 1.2.0-alpha07 (Jul 29 2026). Core concepts: NavKey (unique identifier for navigable content), NavBackStack, NavDisplay (composable that renders the back stack), entryProvider (resolves keys to content), Scene/SceneStrategy (adaptive multi-pane layouts). Selling point: "you have full control over your back stack, and navigating to and from destinations is as simple as adding and removing items from a list."
SRC: https://developer.android.com/jetpack/androidx/releases/navigation3

### Compose state hoisting rule and the ViewModel boundary
"Hoist UI state to the lowest common ancestor between all composables that read and write it." State flows down (immutable params), events flow up (callback lambdas). Decision table: simple single-composable UI element state → keep internal; shared UI element state, UI logic only → hoist to lowest common ancestor composable; complex UI logic with multiple fields → plain state holder class scoped to Composition; screen UI state / business logic → ViewModel. Best practices include "Property drilling is preferable over wrapper classes" and "Don't pass ViewModel to children; only inject at screen level."
SRC: https://developer.android.com/develop/ui/compose/state-hoisting

### ViewModel vs plain state holder comparison table
ViewModel = business logic, survives Activity recreation, has access to data/domain layers, long-lived across navigation, NOT reusable, unique to its UI. Plain class = UI logic, does NOT survive Activity recreation, references UI-scoped sources (lifecycle APIs, Resources), short-lived, reusable across UIs. Guidance: "you should hold state as low as possible while maintaining proper ownership."
SRC: https://developer.android.com/topic/architecture/ui-layer/stateholders

### ViewModel best practices (verbatim bullets)
"use ViewModels as implementation details of a screen level state holder. Don't use them as state holders of reusable UI components such as chip groups or forms." "ViewModels shouldn't know about the UI implementation details." "As they can potentially live longer than the ViewModelStoreOwner, ViewModels shouldn't hold any references of lifecycle-related APIs such as the Context or Resources to prevent memory leaks." "Don't pass ViewModels to other classes, functions or other UI components." Also: "Use the ViewModel class, not AndroidViewModel. Don't use the Application class in the ViewModel." New API: `rememberViewModelStoreOwner()` scopes a ViewModel to a composable call site (e.g. per LazyList/Pager item).
SRC: https://developer.android.com/topic/libraries/architecture/viewmodel

### Compose side-effect API contract, with the two explicit warnings
LaunchedEffect (suspend work keyed to composition; "LaunchedEffect(true) is as suspicious as while(true)"), rememberCoroutineScope (composition-aware scope for launching from callbacks), rememberUpdatedState (reference a value without restarting the effect), DisposableEffect (must end with onDispose; "An empty onDispose block is not good practice"), SideEffect (publish Compose state to non-Compose code after every successful recomposition), produceState (non-Compose → Compose state), derivedStateOf ("expensive. Only use it to avoid unnecessary recomposition when a result hasn't changed. Don't use it just because you're 'combining' state objects"), snapshotFlow (Compose State → cold Flow, applies distinctUntilChanged).
SRC: https://developer.android.com/develop/ui/compose/side-effects

### Compose stability rules: standard collections are always unstable
"Compose always considers standard collections (List, Set, Map) unstable because it cannot guarantee immutability." Fixes: kotlinx.collections.immutable ImmutableList/Map/Set, or annotate the holder `@Immutable`. @Immutable contract = all properties immutable + all methods referentially transparent. @Stable contract = Compose will be notified of all property changes. Types with `var` properties are unstable. A `stability_config.conf` file declares external classes stable.
SRC: https://developer.android.com/develop/ui/compose/performance/stability

### Compose performance best practices are five concrete rules
1) remember expensive calculations (`remember(contacts, comparator) { contacts.sortedWith(comparator) }` — do NOT sort inside `items(...)`). 2) Provide lazy layout keys: `items(items = notes, key = { note -> note.id })`. 3) derivedStateOf to limit recompositions (`val showButton by remember { derivedStateOf { listState.firstVisibleItemIndex > 0 } }`). 4) Defer reads as long as possible — prefer lambda modifiers `Modifier.offset { IntOffset(0, scrollProvider()) }` over `Modifier.offset(y = offset)`, and `Modifier.drawBehind { drawRect(color) }` over `.background(color)`. 5) Avoid backwards writes — never write to state during composition.
SRC: https://developer.android.com/develop/ui/compose/performance/bestpractices

### Previews must be of stateless composables; multipreview annotations exist
"Previews should be of stateless composables without ViewModel dependencies." Pattern: a stateful `AuthorScreen(viewModel: AuthorViewModel = viewModel())` wrapper delegating to a stateless `AuthorScreen(name, posts)` which is the one previewed. Built-in multipreviews (Compose 1.6.0-alpha01+): @PreviewScreenSizes, @PreviewFontScales, @PreviewLightDark, @PreviewDynamicColors. @PreviewParameter + PreviewParameterProvider for data. Preview limits: no network, no file access, cannot instantiate a DI'd ViewModel; use LocalInspectionMode.current to branch.
SRC: https://developer.android.com/develop/ui/compose/tooling/previews

### Compose Preview Screenshot Testing is an official AGP plugin with its own source set
Plugin id `com.android.compose.screenshot` (0.0.1-alpha15+), still gated behind `android.experimental.enableScreenshotTest=true`. Source set: `app/src/screenshotTest/kotlin/...`. Tasks: `./gradlew updateDebugScreenshotTest` (record baselines) and `./gradlew validateDebugScreenshotTest` (verify); report at `{module}/build/reports/screenshotTest/preview/{variant}/index.html`. Annotate with `@PreviewTest` + `@Preview`. Deps: `screenshotTestImplementation(libs.screenshot.validation.api)` and `screenshotTestImplementation(libs.androidx.ui.tooling)`.
SRC: https://developer.android.com/studio/preview/compose-screenshot-testing

### Hilt is wired with KSP (not kapt) and has a fixed component/scope table
`plugins { id("com.google.devtools.ksp"); id("com.google.dagger.hilt.android") }` + `implementation("com.google.dagger:hilt-android:2.57.1")` + `ksp("com.google.dagger:hilt-android-compiler:2.57.1")`. "KSP is now used instead of kapt." Components/scopes: SingletonComponent/@Singleton, ActivityRetainedComponent/@ActivityRetainedScoped, ViewModelComponent/@ViewModelScoped, ActivityComponent/@ActivityScoped, ServiceComponent/@ServiceScoped. @Binds for interface→impl in an abstract module; @Provides for third-party/builder types in an object module. Entry points: @HiltAndroidApp, @AndroidEntryPoint (Activity must extend ComponentActivity), @HiltViewModel.
SRC: https://developer.android.com/training/dependency-injection/hilt-android

### Testing doctrine: fakes over mocks; Now in Android uses no mocking library at all
Official: "Fakes don't require a mocking framework and are lightweight. They are preferred." Stubs/spies are discouraged for complexity. NiA README: test doubles "implement the same interface as the production implementations" and provide "simplified (but still realistic) implementation with additional testing hooks"; real DataStore instances in instrumented tests; Roborazzi for screenshot testing; no mocking libraries. NiA AGENTS.md: Turbine for complex coroutine tests, Truth for assertions, "Tests for UI features should only use ComposeTestRule with a ComponentActivity"; bigger tests live in :app.
SRC: https://developer.android.com/training/testing/fundamentals/test-doubles

### StateFlow testing rule
"When testing StateFlow, do the following: Assert on the `value` property whenever possible. Use `WhileSubscribed`."
SRC: https://developer.android.com/topic/architecture/recommendations

### Now in Android toolchain pins (main branch, gradle/libs.versions.toml)
androidGradlePlugin = 9.0.0, androidTools = 32.0.0, kotlin = 2.3.0, ksp = 2.3.4, hilt = 2.59, androidxComposeBom = 2025.09.01 (compose-bom-alpha), androidxLifecycle = 2.10.0, androidxNavigation3 = 1.0.0, androidxNavigation = 2.8.5 (testing only), room = 2.8.3, androidxDataStore = 1.2.0, kotlinxCoroutines = 1.10.1, kotlinxSerializationJson = 1.8.0, retrofit = 2.11.0, okhttp = 4.12.0, coil = 2.7.0, robolectric = 4.16, roborazzi = 1.56.0, turbine = 1.2.0, truth = 1.4.4, spotless = 8.3.0.
SRC: https://github.com/android/nowinandroid/blob/main/gradle/libs.versions.toml

### Now in Android SDK/JVM baseline: compileSdk 36, minSdk 23, targetSdk 36, JVM target 11, core library desugaring on
KotlinAndroid.kt sets compileSdk = 36, minSdk = 23, sourceCompatibility/targetCompatibility = VERSION_11, isCoreLibraryDesugaringEnabled = true, jvmTarget = JVM_11, freeCompilerArgs += "-opt-in=kotlinx.coroutines.ExperimentalCoroutinesApi" and "-Xconsistent-data-class-copy-visibility". allWarningsAsErrors is opt-in via a `warningsAsErrors` Gradle property. AndroidApplicationConventionPlugin sets defaultConfig.targetSdk = 36; AndroidLibraryConventionPlugin sets testOptions.targetSdk = 36 and lint.targetSdk = 36 plus a derived `resourcePrefix` (":core:module1" → "core_module1_").
SRC: https://github.com/android/nowinandroid/blob/main/build-logic/convention/src/main/kotlin/com/google/samples/apps/nowinandroid/KotlinAndroid.kt

### Google Play targetSdk deadline: API 36 required by 2026-08-31
By August 31 2026 new apps AND app updates must target Android 16 (API 36) or higher (Wear OS/Automotive: API 35+; Android TV/XR: API 34+). Existing apps must target API 35+ to stay available to new users on newer OS versions. Extension to November 1 2026 requestable in Play Console.
SRC: https://developer.android.com/google/play/requirements/target-sdk

### Targeting API 36 forces adaptive layouts, edge-to-edge and predictive back
"For apps targeting Android 16 (API level 36), orientation, resizability, and aspect ratio restrictions no longer apply on displays with smallest width >= 600dp." Ignored: android:screenOrientation, android:resizableActivity, android:minAspectRatio, android:maxAspectRatio, setRequestedOrientation(), getRequestedOrientation(). Edge-to-edge: "R.attr#windowOptOutEdgeToEdgeEnforcement is deprecated and disabled, and your app can't opt-out of going edge-to-edge." Predictive back animations enabled by default; "onBackPressed is not called and KeyEvent.KEYCODE_BACK is not dispatched anymore." The PROPERTY_COMPAT_ALLOW_RESTRICTED_RESIZABILITY opt-out "is temporary and won't apply when targeting API level 37."
SRC: https://developer.android.com/about/versions/16/behavior-changes-16

### Adaptive layout APIs to use: currentWindowAdaptiveInfo(), NavigationSuiteScaffold, ListDetailPaneScaffold, SupportingPaneScaffold
`val windowSizeClass = currentWindowAdaptiveInfo().windowSizeClass`. Window size classes: compact / medium / expanded, driven mainly by width. NavigationSuiteScaffold "automatically switches between navigation bar and navigation rail depending on app window size class and device posture." ListDetailPaneScaffold shows list+detail side by side on expanded, one pane on compact/medium. Pane counts: compact 1, medium 1, expanded 2.
SRC: https://developer.android.com/develop/ui/compose/layouts/adaptive

### AGP 9.x is the 2026 baseline and changes many defaults an agent must not fight
AGP 9.3.0 (July 2026) is current stable: min Gradle 9.5.0, JDK 17, build tools 36.0.0, max compileSdk API 37. AGP 9.0 flipped defaults: android.newDsl=true (legacy applicationVariants/libraryVariants/variantFilter removed → use androidComponents.onVariants/beforeVariants), android.builtInKotlin=true (KGP 2.2.10 runtime dep; you no longer apply org.jetbrains.kotlin.android), android.uniquePackageNames=true, android.enableAppCompileTimeRClass=true (non-final R), android.sdk.defaultTargetSdkToCompileSdkIfUnset=true, android.r8.optimizedResourceShrinking=true, android.r8.strictFullModeForKeepRules=true, android.proguard.failOnMissingFiles=true, android.r8.proguardAndroidTxt.disallowed=true (only proguard-android-optimize.txt), defaults.buildfeatures.resvalues/shaders=false. org.jetbrains.kotlin.multiplatform is incompatible with the new DSL in the same subproject as com.android.library/application.
SRC: https://developer.android.com/build/releases/agp-9-0-0-release-notes

### R8 is on by default expectation, with a new AGP 9.3 optimization DSL
R8 full mode enabled by default since AGP 8.0 (android.enableR8.fullMode=false to disable — "not recommended"). AGP 9.3+: `buildTypes { release { optimization { enable = true } } }` with keep rules in `src/<variant>/keepRules/*.keep`. Legacy: isMinifyEnabled = true, isShrinkResources = true, proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), ...). Standalone analyzer task `./gradlew :app:analyzeReleaseR8Config`. Since AGP 8.12.0 R8 also optimizes resources.
SRC: https://developer.android.com/build/shrink-code

### Baseline Profiles: ~30% first-launch speedup, plus ~15% each from R8 rule rewriting and startup profiles
"Baseline Profiles improve code execution speed by about 30% from the first launch." ~15% more from R8 rewriting of rules (AGP 8.2+), ~15% more from Startup Profiles DEX layout. Generation build variant must have isMinifyEnabled = false (the Baseline Profile Gradle Plugin handles this); the release APK should always have isMinifyEnabled = true — R8 rewrites the unobfuscated profile. Binary profile ships at assets/dexopt/baseline.prof and must be < 1.5 MB. Min versions: AGP 8.0.0, benchmark-macro-junit4 1.4.1, profileinstaller 1.4.1.
SRC: https://developer.android.com/topic/performance/baselineprofiles/overview

### Compose BOM 2026.08.00 is the latest mapping
Maps to compose animation/foundation/material/runtime/ui 1.12.0, material3 1.4.0, material3.adaptive 1.3.0, ui-tooling 1.12.0. Preceding BOMs: 2026.06.01, 2026.06.00, 2026.05.01, 2026.05.00, 2026.04.01, 2026.04.00 — i.e. roughly monthly with patch revisions.
SRC: https://developer.android.com/develop/ui/compose/bom/bom-mapping

### Kotlin current stable is 2.4.10 (2026-07-14); 2.4.0 shipped 2026-06-03
Recent releases per kotlinlang.org: 2.4.10 (Jul 14 2026, bug fix), 2.4.0 (Jun 3 2026, language), 2.3.21 (Apr 23 2026), 2.3.20 (Mar 16 2026, tooling), 2.3.10 (Feb 5 2026), 2.3.0 (Dec 16 2025, language), 2.2.21 (Oct 23 2025), 2.2.20 (Sep 10 2025). K2 has been the stable default compiler since Kotlin 2.0.0 (May 2024).
SRC: https://kotlinlang.org/docs/releases.html

### Google's official KMP posture: stable, production-ready, share business logic; UI sharing optional
Google officially supports KMP for sharing business logic between Android and iOS, with a layered "choose what to share" approach and no complete rewrite. Jetpack libraries with KMP support: ViewModel, Room, DataStore, Lifecycle, Navigation, Paging, SQLite, Annotation, Collection, SavedState. Tiers: Tier 1 Android/JVM/iOS; Tier 2 macOS/Linux; Tier 3 watchOS/tvOS/Windows/JS/WASM. UI sharing is via JetBrains' Compose Multiplatform and is explicitly optional.
SRC: https://developer.android.com/kotlin/multiplatform

### Google now ships official agent skills for Android — directly relevant to agent-authored codebases
github.com/android/skills contains "AI-optimized, modular instructions... Android skills follow the open-standard agent skills - markdown files (SKILL.md)". Skill areas include AGP 9 upgrade, CameraX, app functions, Android CLI, Jetpack Compose, Media3 Cast, Navigation 3, R8 analyzer, Play distribution, profilers, intent security, edge-to-edge, testing setup, TV Leanback→Compose, Wear OS Compose M3, XR. Install: `android skills add --skill=r8-analyzer --project=.` (the Navigation 3 doc shows `android skills add --skill navigation-3`). Default install location targets Gemini/Antigravity at ~/.gemini/antigravity/skills.
SRC: https://github.com/android/skills

### Now in Android explicitly disclaims Clean Architecture
"> [!NOTE] The official Android architecture is different from other architectures, such as 'Clean Architecture'. Concepts from other architectures may not apply here, or be applied in different ways." (links github.com/android/nowinandroid/discussions/1273). The reactive model is stated as: "Higher layers react to changes in lower layers. Events flow down. Data flows up."
SRC: https://github.com/android/nowinandroid/blob/main/docs/ArchitectureLearningJourney.md

### Now in Android build hygiene defaults worth copying
gradle.properties: org.gradle.parallel=true, org.gradle.caching=true, org.gradle.configuration-cache=true, org.gradle.configuration-cache.parallel=true, org.gradle.configuration-cache.problems=warn, android.defaults.buildfeatures.resvalues=false, android.defaults.buildfeatures.shaders=false, roborazzi.test.verify=true, ksp.project.isolation.enabled=true, org.gradle.jvmargs=-Xmx4g -Xms4g -XX:+UseG1GC -XX:SoftRefLRUPolicyMSPerMB=1 -XX:ReservedCodeCacheSize=256m. Module dependency graphs live in each module's README.md and are regenerated by the `graphUpdate` task / Build.yaml workflow.
SRC: https://github.com/android/nowinandroid/blob/main/gradle.properties

## EXAMPLES
### Canonical ViewModel state production — combine + stateIn(WhileSubscribed(5_000)) — from Now in Android's TopicViewModel (also shows Hilt assisted injection for a nav argument)
FILE: feature/<name>/impl/src/main/kotlin/<pkg>/feature/<name>/impl/<Name>ViewModel.kt
```
@HiltViewModel(assistedFactory = TopicViewModel.Factory::class)
class TopicViewModel @AssistedInject constructor(
    private val userDataRepository: UserDataRepository,
    topicsRepository: TopicsRepository,
    userNewsResourceRepository: UserNewsResourceRepository,
    @Assisted val topicId: String,
) : ViewModel() {
    val topicUiState: StateFlow<TopicUiState> = topicUiState(
        topicId = topicId,
        userDataRepository = userDataRepository,
        topicsRepository = topicsRepository,
    )
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5_000),
            initialValue = TopicUiState.Loading,
        )

    fun followTopicToggle(followed: Boolean) {
        viewModelScope.launch {
            userDataRepository.setTopicIdFollowed(topicId, followed)
        }
    }

    @AssistedFactory
    interface Factory {
        fun create(topicId: String): TopicViewModel
    }
}

private fun topicUiState(...): Flow<TopicUiState> =
    combine(followedTopicIds, topicStream, ::Pair)
        .asResult()
        .map { result ->
            when (result) {
                is Result.Success -> TopicUiState.Success(...)
                is Result.Loading -> TopicUiState.Loading
                is Result.Error   -> TopicUiState.Error
            }
        }
```
SRC: https://github.com/android/nowinandroid/blob/main/feature/topic/impl/src/main/kotlin/com/google/samples/apps/nowinandroid/feature/topic/impl/TopicViewModel.kt

### Official MutableStateFlow + asStateFlow() + update{} exposure pattern
FILE: …/<Feature>ViewModel.kt + <Feature>UiState.kt
```
data class DiceUiState(
    val firstDieValue: Int? = null,
    val secondDieValue: Int? = null,
    val numberOfRolls: Int = 0,
)

class DiceRollViewModel : ViewModel() {
    private val _uiState = MutableStateFlow(DiceUiState())
    val uiState: StateFlow<DiceUiState> = _uiState.asStateFlow()

    fun rollDice() {
        _uiState.update { currentState ->
            currentState.copy(
                firstDieValue = Random.nextInt(from = 1, until = 7),
                secondDieValue = Random.nextInt(from = 1, until = 7),
                numberOfRolls = currentState.numberOfRolls + 1,
            )
        }
    }
}
```
SRC: https://developer.android.com/topic/architecture/ui-layer/state-production

### Official replacement for one-off events: a userMessage field on UiState + a *Shown() ack function
FILE: Screen composable + ViewModel in the same feature package
```
data class LatestNewsUiState(
    val news: List<News> = emptyList(),
    val isLoading: Boolean = false,
    val userMessage: String? = null
)

class LatestNewsViewModel(/* ... */) : ViewModel() {
    var uiState by mutableStateOf(LatestNewsUiState())
        private set

    fun refreshNews() {
        viewModelScope.launch {
            if (!internetConnection()) {
                uiState = uiState.copy(userMessage = "No Internet connection")
                return@launch
            }
        }
    }

    fun userMessageShown() {
        uiState = uiState.copy(userMessage = null)
    }
}

@Composable
fun LatestNewsScreen(snackbarHostState: SnackbarHostState, viewModel: LatestNewsViewModel = viewModel()) {
    viewModel.uiState.userMessage?.let { userMessage ->
        LaunchedEffect(userMessage) {
            snackbarHostState.showSnackbar(userMessage)
            viewModel.userMessageShown()
        }
    }
}
```
SRC: https://developer.android.com/topic/architecture/ui-layer/events

### Official navigation-as-state pattern (no Channel): observe the state field with snapshotFlow + flowWithLifecycle
FILE: feature screen composable
```
@Composable
fun LoginScreen(onUserLogIn: () -> Unit, viewModel: LoginViewModel = viewModel()) {
    Button(onClick = { viewModel.tryLogin() }) { Text("Log in") }

    val lifecycle = LocalLifecycleOwner.current.lifecycle
    val currentOnUserLogIn by rememberUpdatedState(onUserLogIn)
    LaunchedEffect(viewModel, lifecycle) {
        snapshotFlow { viewModel.uiState }
            .filter { it.isUserLoggedIn }
            .flowWithLifecycle(lifecycle)
            .collect { currentOnUserLogIn() }
    }
}
```
SRC: https://developer.android.com/topic/architecture/ui-layer/events

### Offline-first LCE UiState with .catch { emit(Error) } — the exact sealed-interface shape Google publishes
FILE: feature module ViewModel
```
sealed interface AuthorUiState {
    data object Loading : AuthorUiState
    data class Success(val author: Author) : AuthorUiState
    data object Error : AuthorUiState
}

class AuthorViewModel(authorsRepository: AuthorsRepository) : ViewModel() {
    val authorUiState: StateFlow<AuthorUiState> =
        authorsRepository.getAuthorStream(id = authorId)
            .map<Author, AuthorUiState> { AuthorUiState.Success(it) }
            .catch { emit(AuthorUiState.Error) }
            .stateIn(
                scope = viewModelScope,
                started = SharingStarted.WhileSubscribed(5_000),
                initialValue = AuthorUiState.Loading
            )
}
```
SRC: https://developer.android.com/topic/architecture/data-layer/offline-first

### Data-layer main-safety: data source wraps blocking work in withContext(ioDispatcher)
FILE: core/network/src/main/kotlin/<pkg>/core/network/<Type>RemoteDataSource.kt
```
class NewsRemoteDataSource(
    private val newsApi: NewsApi,
    private val ioDispatcher: CoroutineDispatcher
) {
    suspend fun fetchLatestNews(): List<ArticleHeadline> =
        withContext(ioDispatcher) {
            newsApi.fetchLatestNews()
        }
}
```
SRC: https://developer.android.com/topic/architecture/data-layer

### Offline-first model mapping functions (network → entity → domain)
FILE: data/local/entities/…, data/network/models/…, data/model/…, data/repository/… (official offline-first layout)
```
/** Converts the network model to the local model for persisting */
fun NetworkAuthor.asEntity() = AuthorEntity(
    id = id, name = name, imageUrl = imageUrl, bio = bio,
)

/** Converts the local model to the external model for use by other layers */
fun AuthorEntity.asExternalModel() = Author(
    id = id, name = name, imageUrl = imageUrl, bio = bio,
)
```
SRC: https://developer.android.com/topic/architecture/data-layer/offline-first

### Domain-layer use case: @Inject constructor + operator fun invoke returning a Flow (Now in Android)
FILE: core/domain/src/main/kotlin/<pkg>/core/domain/Get<Thing>UseCase.kt
```
/**
 * A use case which obtains a list of topics with their followed state.
 */
class GetFollowableTopicsUseCase @Inject constructor(
    private val topicsRepository: TopicsRepository,
    private val userDataRepository: UserDataRepository,
) {
    operator fun invoke(sortBy: TopicSortField = NONE): Flow<List<FollowableTopic>> = combine(
        userDataRepository.userData,
        topicsRepository.getTopics(),
    ) { userData, topics ->
        val followedTopics = topics.map { topic ->
            FollowableTopic(topic = topic, isFollowed = topic.id in userData.followedTopics)
        }
        when (sortBy) {
            NAME -> followedTopics.sortedBy { it.topic.name }
            else -> followedTopics
        }
    }
}
```
SRC: https://github.com/android/nowinandroid/blob/main/core/domain/src/main/kotlin/com/google/samples/apps/nowinandroid/core/domain/GetFollowableTopicsUseCase.kt

### Use case that must move off the main thread
FILE: domain/usecase module
```
class MyUseCase(
    private val defaultDispatcher: CoroutineDispatcher = Dispatchers.Default
) {
    suspend operator fun invoke(...) = withContext(defaultDispatcher) {
        // Long-running blocking operations happen on a background thread.
    }
}
```
SRC: https://developer.android.com/topic/architecture/domain-layer

### Now in Android settings.gradle.kts — included build-logic, typesafe project accessors, api/impl feature split
FILE: settings.gradle.kts (repo root)
```
pluginManagement {
    includeBuild("build-logic")
    repositories {
        google { content { includeGroupByRegex("com\\.android.*"); includeGroupByRegex("com\\.google.*"); includeGroupByRegex("androidx.*") } }
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode = RepositoriesMode.FAIL_ON_PROJECT_REPOS
    repositories { google { ... }; mavenCentral() }
}
rootProject.name = "nowinandroid"

enableFeaturePreview("TYPESAFE_PROJECT_ACCESSORS")
include(":app")
include(":core:common"); include(":core:data"); include(":core:database")
include(":core:datastore"); include(":core:designsystem"); include(":core:domain")
include(":core:model"); include(":core:navigation"); include(":core:network")
include(":core:testing"); include(":core:ui")
include(":feature:topic:api"); include(":feature:topic:impl")
include(":feature:search:api"); include(":feature:search:impl")
```
SRC: https://github.com/android/nowinandroid/blob/main/settings.gradle.kts

### Feature-impl convention plugin — the single place feature modules get their standard dependency set
FILE: build-logic/convention/src/main/kotlin/AndroidFeatureImplConventionPlugin.kt
```
class AndroidFeatureImplConventionPlugin : Plugin<Project> {
    override fun apply(target: Project) {
        with(target) {
            apply(plugin = "nowinandroid.android.library")
            apply(plugin = "nowinandroid.hilt")

            extensions.configure<LibraryExtension> {
                testOptions.animationsDisabled = true
                configureGradleManagedDevices(this)
            }

            dependencies {
                "implementation"(project(":core:ui"))
                "implementation"(project(":core:designsystem"))
                "implementation"(libs.findLibrary("androidx.lifecycle.runtimeCompose").get())
                "implementation"(libs.findLibrary("androidx.lifecycle.viewModelCompose").get())
                "implementation"(libs.findLibrary("androidx.hilt.lifecycle.viewModelCompose").get())
                "implementation"(libs.findLibrary("androidx.navigation3.runtime").get())
                "implementation"(libs.findLibrary("androidx.tracing.ktx").get())
                "androidTestImplementation"(libs.findLibrary("androidx.lifecycle.runtimeTesting").get())
            }
        }
    }
}
```
SRC: https://github.com/android/nowinandroid/blob/main/build-logic/convention/src/main/kotlin/AndroidFeatureImplConventionPlugin.kt

### Feature-api convention plugin — api modules only carry nav keys and api-export :core:navigation
FILE: build-logic/convention/src/main/kotlin/AndroidFeatureApiConventionPlugin.kt
```
class AndroidFeatureApiConventionPlugin : Plugin<Project> {
    override fun apply(target: Project) {
        with(target) {
            apply(plugin = "nowinandroid.android.library")
            apply(plugin = "org.jetbrains.kotlin.plugin.serialization")

            dependencies {
                "api"(project(":core:navigation"))
            }
        }
    }
}
```
SRC: https://github.com/android/nowinandroid/blob/main/build-logic/convention/src/main/kotlin/AndroidFeatureApiConventionPlugin.kt

### Hilt convention plugin — KSP wiring for both JVM and Android modules
FILE: build-logic/convention/src/main/kotlin/HiltConventionPlugin.kt
```
class HiltConventionPlugin : Plugin<Project> {
    override fun apply(target: Project) {
        with(target) {
            apply(plugin = "com.google.devtools.ksp")

            dependencies {
                "ksp"(libs.findLibrary("hilt.compiler").get())
                "ksp"(libs.findLibrary("kotlin.metadata").get())
            }

            pluginManager.withPlugin("org.jetbrains.kotlin.jvm") {
                dependencies { "implementation"(libs.findLibrary("hilt.core").get()) }
            }

            pluginManager.withPlugin("com.android.base") {
                apply(plugin = "dagger.hilt.android.plugin")
                dependencies { "implementation"(libs.findLibrary("hilt.android").get()) }
            }
        }
    }
}
```
SRC: https://github.com/android/nowinandroid/blob/main/build-logic/convention/src/main/kotlin/HiltConventionPlugin.kt

### Feature module build files — impl vs api, and api vs implementation across core
FILE: feature/<name>/{api,impl}/build.gradle.kts and core/<name>/build.gradle.kts
```
// feature/topic/impl/build.gradle.kts
plugins {
    alias(libs.plugins.nowinandroid.android.feature.impl)
    alias(libs.plugins.nowinandroid.android.library.compose)
    alias(libs.plugins.nowinandroid.android.library.jacoco)
}
android { namespace = "com.google.samples.apps.nowinandroid.feature.topic.impl" }
dependencies {
    implementation(projects.core.data)
    implementation(projects.feature.topic.api)
    implementation(libs.androidx.compose.material3.adaptive.navigation3)
    testImplementation(projects.core.testing)
    androidTestImplementation(libs.bundles.androidx.compose.ui.test)
}

// core/data/build.gradle.kts — re-exports its lower layers with api()
dependencies {
    api(projects.core.common)
    api(projects.core.database)
    api(projects.core.datastore)
    api(projects.core.network)
    implementation(projects.core.analytics)
    implementation(projects.core.notifications)
}
```
SRC: https://github.com/android/nowinandroid/blob/main/feature/topic/impl/build.gradle.kts

### Navigation 3 cross-module navigation contract: NavKey in :api, entry provider in :impl
FILE: feature/<name>/api/src/main/kotlin/.../navigation/<Name>NavKey.kt and feature/<name>/impl/src/main/kotlin/.../navigation/<Name>EntryProvider.kt
```
// feature/topic/api/.../navigation/TopicNavKey.kt
@Serializable
data class TopicNavKey(val id: String) : NavKey

fun Navigator.navigateToTopic(topicId: String) {
    navigate(TopicNavKey(topicId))
}

// feature/topic/impl/.../navigation/TopicEntryProvider.kt
@OptIn(ExperimentalMaterial3AdaptiveApi::class)
fun EntryProviderScope<NavKey>.topicEntry(navigator: Navigator) {
    entry<TopicNavKey>(
        metadata = ListDetailSceneStrategy.detailPane(),
    ) { key ->
        val id = key.id
        TopicScreen(
            showBackButton = true,
            onBackClick = { navigator.goBack() },
            onTopicClick = navigator::navigateToTopic,
            viewModel = hiltViewModel<TopicViewModel, Factory>(key = id) { factory ->
                factory.create(id)
            },
        )
    }
}
```
SRC: https://github.com/android/nowinandroid/blob/main/feature/topic/api/src/main/kotlin/com/google/samples/apps/nowinandroid/feature/topic/api/navigation/TopicNavKey.kt

### Compose convention plugin — BOM + tooling + compiler metrics/reports + stability config file
FILE: build-logic/convention/src/main/kotlin/<pkg>/AndroidCompose.kt
```
internal fun Project.configureAndroidCompose(commonExtension: CommonExtension) {
    commonExtension.apply {
        buildFeatures.apply { compose = true }
        dependencies {
            val bom = libs.findLibrary("androidx-compose-bom").get()
            "implementation"(platform(bom))
            "androidTestImplementation"(platform(bom))
            "implementation"(libs.findLibrary("androidx-compose-ui-tooling-preview").get())
            "debugImplementation"(libs.findLibrary("androidx-compose-ui-tooling").get())
        }
    }

    extensions.configure<ComposeCompilerGradlePluginExtension> {
        project.providers.gradleProperty("enableComposeCompilerMetrics").onlyIfTrue()
            .relativeToRootProject("compose-metrics").let(metricsDestination::set)
        project.providers.gradleProperty("enableComposeCompilerReports").onlyIfTrue()
            .relativeToRootProject("compose-reports").let(reportsDestination::set)
        stabilityConfigurationFiles
            .add(isolated.rootProject.projectDirectory.file("compose_compiler_config.conf"))
    }
}
```
SRC: https://github.com/android/nowinandroid/blob/main/build-logic/convention/src/main/kotlin/com/google/samples/apps/nowinandroid/AndroidCompose.kt

### Compose stability configuration file — declare whole model packages stable without annotating them
FILE: compose_compiler_config.conf (repo root), wired via stabilityConfigurationFiles
```
// This file contains classes (with possible wildcards) that the Compose Compiler will treat as stable.
// It allows us to define classes that are not part of our codebase without wrapping them in a stable class.

// We always use immutable classes for our data model, to avoid running the Compose compiler
// in the module we declare it to be stable here.
com.google.samples.apps.nowinandroid.core.model.data.*

// Java standard library classes
java.time.ZoneId
java.time.ZoneOffset
```
SRC: https://github.com/android/nowinandroid/blob/main/compose_compiler_config.conf

### Kotlin/Android baseline in the convention plugin (compileSdk/minSdk/JVM target/desugaring/warnings-as-errors)
FILE: build-logic/convention/src/main/kotlin/<pkg>/KotlinAndroid.kt
```
internal fun Project.configureKotlinAndroid(commonExtension: CommonExtension) {
    commonExtension.apply {
        compileSdk = 36
        defaultConfig.apply { minSdk = 23 }
        compileOptions.apply {
            sourceCompatibility = JavaVersion.VERSION_11
            targetCompatibility = JavaVersion.VERSION_11
            isCoreLibraryDesugaringEnabled = true
        }
    }
    configureKotlin<KotlinAndroidProjectExtension>()
    dependencies { "coreLibraryDesugaring"(libs.findLibrary("android.desugarJdkLibs").get()) }
}

private inline fun <reified T : KotlinBaseExtension> Project.configureKotlin() = configure<T> {
    val warningsAsErrors = providers.gradleProperty("warningsAsErrors").map { it.toBoolean() }.orElse(false)
    ...apply {
        jvmTarget = JvmTarget.JVM_11
        allWarningsAsErrors = warningsAsErrors
        freeCompilerArgs.add("-opt-in=kotlinx.coroutines.ExperimentalCoroutinesApi")
        freeCompilerArgs.add("-Xconsistent-data-class-copy-visibility")
    }
}
```
SRC: https://github.com/android/nowinandroid/blob/main/build-logic/convention/src/main/kotlin/com/google/samples/apps/nowinandroid/KotlinAndroid.kt

### Library convention plugin enforces a per-module resource prefix (kills cross-module resource collisions)
FILE: build-logic/convention/src/main/kotlin/AndroidLibraryConventionPlugin.kt
```
extensions.configure<LibraryExtension> {
    configureKotlinAndroid(this)
    testOptions.targetSdk = 36
    lint.targetSdk = 36
    defaultConfig.testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    testOptions.animationsDisabled = true
    configureFlavors(this)
    configureGradleManagedDevices(this)
    // The resource prefix is derived from the module name,
    // so resources inside ":core:module1" must be prefixed with "core_module1_"
    resourcePrefix =
        path.split("""\W""".toRegex()).drop(1).distinct().joinToString(separator = "_")
            .lowercase() + "_"
}
```
SRC: https://github.com/android/nowinandroid/blob/main/build-logic/convention/src/main/kotlin/AndroidLibraryConventionPlugin.kt

### Release build config with R8 + automatic Baseline Profile regeneration (Now in Android :app)
FILE: app/build.gradle.kts
```
buildTypes {
    debug { applicationIdSuffix = NiaBuildType.DEBUG.applicationIdSuffix }
    release {
        isMinifyEnabled = providers.gradleProperty("minifyWithR8")
            .map(String::toBooleanStrict).getOrElse(true)
        applicationIdSuffix = NiaBuildType.RELEASE.applicationIdSuffix
        proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        // Ensure Baseline Profile is fresh for release builds.
        baselineProfile.automaticGenerationDuringBuild = true
    }
}
// ...
dependencies { baselineProfile(projects.benchmarks) }
```
SRC: https://github.com/android/nowinandroid/blob/main/app/build.gradle.kts

### AGP 9.3+ R8 optimization DSL (replaces isMinifyEnabled/proguardFiles)
FILE: app/build.gradle.kts + app/src/main/keepRules/custom-rules.keep
```
android {
    buildTypes {
        release {
            optimization {
                enable = true // Enables code and resource optimizations
            }
        }
    }
}
// Keep rules move to src/<variant>/keepRules/*.keep
// Analyze with: ./gradlew :app:analyzeReleaseR8Config
```
SRC: https://developer.android.com/build/shrink-code

### Hilt module conventions: @Binds for interfaces, @Provides for third-party types, qualifiers for multiple bindings
FILE: core/<layer>/src/main/kotlin/<pkg>/core/<layer>/di/<Layer>Module.kt
```
@Module
@InstallIn(SingletonComponent::class)
abstract class DataModule {
    @Binds
    abstract fun bindNewsRepository(impl: OfflineFirstNewsRepository): NewsRepository
}

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {
    @AuthInterceptorOkHttpClient
    @Provides
    fun provideAuthInterceptorOkHttpClient(authInterceptor: AuthInterceptor): OkHttpClient =
        OkHttpClient.Builder().addInterceptor(authInterceptor).build()
}

@Qualifier
@Retention(AnnotationRetention.BINARY)
annotation class AuthInterceptorOkHttpClient
```
SRC: https://developer.android.com/training/dependency-injection/hilt-android

### Hilt Gradle wiring with KSP
FILE: build.gradle.kts (root) and app/build.gradle.kts
```
// root build.gradle.kts
plugins {
  id("com.google.dagger.hilt.android") version "2.57.1" apply false
}

// app/build.gradle.kts
plugins {
  id("com.google.devtools.ksp")
  id("com.google.dagger.hilt.android")
}
dependencies {
  implementation("com.google.dagger:hilt-android:2.57.1")
  ksp("com.google.dagger:hilt-android-compiler:2.57.1")
}
```
SRC: https://developer.android.com/training/dependency-injection/hilt-android

### Screen-level Compose consumption: collectAsStateWithLifecycle + stateful/stateless split
FILE: feature/<name>/impl/…/<Name>Screen.kt (one stateful overload + one stateless overload)
```
@Composable
private fun ConversationScreen(
    conversationViewModel: ConversationViewModel = viewModel()
) {
    val messages by conversationViewModel.messages.collectAsStateWithLifecycle()

    ConversationScreen(
        messages = messages,
        onSendMessage = { message: Message -> conversationViewModel.sendMessage(message) }
    )
}

@Composable
private fun ConversationScreen(
    messages: List<Message>,
    onSendMessage: (Message) -> Unit
) {
    MessagesList(messages, onSendMessage)
}
```
SRC: https://developer.android.com/develop/ui/compose/state-hoisting

### Compose Preview Screenshot Testing setup (plugin, flag, test)
FILE: <module>/src/screenshotTest/kotlin/<pkg>/…ScreenshotTest.kt
```
# gradle.properties
android.experimental.enableScreenshotTest=true

// libs.versions.toml
[versions]
screenshot = "0.0.1-alpha15"
[plugins]
screenshot = { id = "com.android.compose.screenshot", version.ref = "screenshot" }
[libraries]
screenshot-validation-api = { group = "com.android.tools.screenshot", name = "screenshot-validation-api", version.ref = "screenshot" }

// module build.gradle.kts
plugins { alias(libs.plugins.screenshot) }
dependencies {
    screenshotTestImplementation(libs.screenshot.validation.api)
    screenshotTestImplementation(libs.androidx.ui.tooling)
}

// app/src/screenshotTest/kotlin/.../ExamplePreviewScreenshotTest.kt
@PreviewTest
@Preview(showBackground = true)
@Composable
fun GreetingPreview() {
    MyApplicationTheme { Greeting("Android!") }
}

// ./gradlew updateDebugScreenshotTest   (record)
// ./gradlew validateDebugScreenshotTest (verify)
```
SRC: https://developer.android.com/studio/preview/compose-screenshot-testing

### Fake-over-mock test double (official example) — no mocking framework
FILE: core/testing/src/main/kotlin/<pkg>/core/testing/repository/Fake<Type>Repository.kt (NiA puts shared fakes in :core:testing / :core:data-test)
```
object FakeUserRepository : UserRepository {
    fun getUsers() = listOf(UserAlice, UserBob)
}

val const UserAlice = User("Alice")
val const UserBob = User("Bob")

@Test
fun viewModelA_loadsUsers_showsFirstUser() {
    val viewModel = ViewModelA(FakeUserRepository)
    assertEquals(viewModel.firstUserName, UserAlice.name)
}
```
SRC: https://developer.android.com/training/testing/fundamentals/test-doubles

### WorkManager sync setup for offline-first (Now in Android's Sync initializer + SyncWorker)
FILE: sync/work/src/main/kotlin/<pkg>/sync/…
```
class SyncInitializer : Initializer<Sync> {
    override fun create(context: Context): Sync {
        WorkManager.getInstance(context).apply {
            enqueueUniqueWork(SyncWorkName, ExistingWorkPolicy.KEEP, SyncWorker.startUpSyncWork())
        }
        return Sync
    }
}

fun startUpSyncWork() = OneTimeWorkRequestBuilder<DelegatingWorker>()
    .setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST)
    .setConstraints(SyncConstraints)
    .setInputData(SyncWorker::class.delegatedData())
    .build()

class SyncWorker(...) : CoroutineWorker(appContext, workerParams), Synchronizer {
    override suspend fun doWork(): Result = withContext(ioDispatcher) {
        val syncedSuccessfully = awaitAll(
            async { topicRepository.sync() },
            async { newsRepository.sync() },
        ).all { it }
        if (syncedSuccessfully) Result.success() else Result.retry()
    }
}
```
SRC: https://developer.android.com/topic/architecture/data-layer/offline-first

### Gradle build hygiene defaults from Now in Android
FILE: gradle.properties (repo root)
```
org.gradle.jvmargs=-Dfile.encoding=UTF-8 -XX:+UseG1GC -XX:SoftRefLRUPolicyMSPerMB=1 -XX:ReservedCodeCacheSize=256m -XX:+HeapDumpOnOutOfMemoryError -Xmx4g -Xms4g
kotlin.daemon.jvmargs=-Dfile.encoding=UTF-8 -XX:+UseG1GC -XX:SoftRefLRUPolicyMSPerMB=1 -XX:ReservedCodeCacheSize=320m -XX:+HeapDumpOnOutOfMemoryError -Xmx4g -Xms4g
org.gradle.parallel=true
org.gradle.configureondemand=false
org.gradle.caching=true
org.gradle.configuration-cache=true
org.gradle.configuration-cache.parallel=true
org.gradle.configuration-cache.problems=warn
android.useAndroidX=true
kotlin.code.style=official
android.defaults.buildfeatures.resvalues=false
android.defaults.buildfeatures.shaders=false
roborazzi.test.verify=true
ksp.project.isolation.enabled=true
```
SRC: https://github.com/android/nowinandroid/blob/main/gradle.properties

### Now in Android's own AGENTS.md — the shape of agent instructions Google ships for an Android repo
FILE: AGENTS.md (repo root)
```
## Commands to Build & Test

The app and Android libraries have two product flavors: `demo` and `prod`, and two build types: `debug` and `release`.

- Build: `./gradlew assemble{Variant}`. Typically `assembleDemoDebug`.
- Fix linting/formatting: `./gradlew spotlessApply`
- Run local tests: `./gradlew {variant}Test`
- Run single test: `./gradlew {variant}Test --tests "com.example.myapp.MyTestClass"`
- Run local screenshot tests: `./gradlew verifyRoborazziDemoDebug`

### Instrumented tests
- Gradle-managed devices: `./gradlew pixel6api31aospDebugAndroidTest`

### Creating tests
#### Instrumented tests
- Tests for UI features should only use `ComposeTestRule` with a `ComponentActivity`.
- Bigger tests live in the `:app` module and they can start activities like `MainActivity`.
#### Local tests
- kotlinx.coroutines for most assertions
- cashapp/turbine for complex coroutine tests
- google/truth for assertions
```
SRC: https://github.com/android/nowinandroid/blob/main/AGENTS.md

## GOTCHAS
- Blog/tutorial content about Now in Android is largely STALE. The repo has restructured: feature modules are now `:feature:x:api` + `:feature:x:impl` Gradle module pairs, there is a `:core:navigation` module with a hand-rolled `Navigator`/`NavigationState`, and navigation is Navigation 3 (`NavKey`, `EntryProviderScope.entry<T>`), not `NavHost`/`composable<Route>`. NiA's own AGENTS.md still says 'Jetpack Navigation 2 for Compose' — it contradicts the actual libs.versions.toml (androidxNavigation3 = 1.0.0) and the modularization doc. Trust the build files over the prose.
- The `stateIn(WhileSubscribed(5_000))` idiom silently misbehaves if the flow is collected from a non-lifecycle-aware collector: the 5 s grace period only helps because the UI stops collecting on STOPPED. Pairing `WhileSubscribed(5000)` with `collectAsState()` (instead of `collectAsStateWithLifecycle()`) means the upstream never stops — the timeout becomes dead code.
- `WhileSubscribed(5000)` is wrong for screens the user leaves on the back stack or in an off-screen tab where the pipeline must keep running — the docs prescribe `SharingStarted.Lazily` for that case. Blanket-applying 5000 everywhere is a real bug class (re-fetch storms, lost in-flight work).
- 'Do not send events from the ViewModel to the UI' is Strongly recommended but is genuinely contested in the community; teams commonly still use `Channel(Channel.BUFFERED)` + `receiveAsFlow()` for navigation and snackbars. If a guide bans Channels it must supply the replacement recipes (a nullable `userMessage` field + a `*Shown()` ack; navigation as a state predicate observed via `snapshotFlow{...}.filter{...}.flowWithLifecycle(...)`), otherwise agents will just reinvent Channels.
- `derivedStateOf` is the single most over-applied Compose API. The docs give an explicit anti-example (`derivedStateOf { "$firstName $lastName" }` is BAD) and say it is 'expensive. Only use it to avoid unnecessary recomposition when a result hasn't changed.' An agent rule that says 'use derivedStateOf when combining state' is actively harmful.
- Compose treats `List`/`Set`/`Map` as UNSTABLE always. A UiState data class holding `List<Item>` makes the whole screen non-skippable. Fixes are kotlinx-immutable collections, `@Immutable` on the holder, or a `compose_compiler_config.conf` stability file — but the config file only works if the module actually runs the Compose compiler, and wildcards must be kept in sync with package renames.
- Never launch async work in a ViewModel `init{}`/constructor — the docs warn it can throw `IllegalStateException` with Compose State. This is a very common agent-generated pattern (`init { loadData() }`).
- Suspend UI-element APIs (e.g. `drawerState.close()`, animations) crash when launched from `viewModelScope` because there is no `MonotonicFrameClock`. The documented workaround is `withContext(uiScope.coroutineContext)` using a `rememberCoroutineScope()` passed in from the composable.
- AGP 9.0 flipped `android.newDsl=true`, which REMOVES `applicationVariants`, `libraryVariants`, `variantFilter`, `dexOptions`. Any build script or convention plugin an agent copies from pre-2026 material will fail to configure. The opt-out `android.newDsl=false` is removed in AGP 10 (mid-2026).
- AGP 9.0 turned on `android.r8.strictFullModeForKeepRules=true` — implicit default-constructor keeping is gone, so reflection-based JSON (Gson/Moshi reflective adapters) and DI edge cases can break at runtime in release only. Keep rules must be spelled `-keep class A { <init>(); }`. Also `proguard-android.txt` is no longer accepted (only `proguard-android-optimize.txt`), and library consumer rules containing global options (`-dontoptimize`, `-dontobfuscate`) now fail the build.
- AGP 9.0 sets `android.sdk.defaultTargetSdkToCompileSdkIfUnset=true` — omitting `targetSdk` silently makes it equal `compileSdk`, which can push an app to API 36 behaviour (mandatory edge-to-edge, predictive back, ignored orientation locks) without anyone deciding to.
- `org.jetbrains.kotlin.multiplatform` is incompatible with the AGP 9 new DSL in the same subproject as `com.android.library`/`com.android.application`; KMP modules must use the separate Android Gradle Library Plugin for KMP. Any 'just add KMP to the existing module' plan is wrong on AGP 9.
- Targeting API 36 means `android:screenOrientation`, `android:resizableActivity`, `minAspectRatio`/`maxAspectRatio` and `setRequestedOrientation()` are IGNORED on sw≥600dp. Portrait-locked phone layouts will stretch, and activities will re-create far more often — so any state not in ViewModel/SavedStateHandle/rememberSaveable is now visibly lost. The compat property opt-out stops working at API 37.
- Compose Preview Screenshot Testing is still gated behind `android.experimental.enableScreenshotTest=true` with a `0.0.1-alphaNN` plugin — it is not a stable dependency to build CI gates on without accepting churn. NiA itself uses Roborazzi instead, and its AGENTS.md notes 'Screenshot tests are generated by CI, so they shouldn't be checked into the repo from a workstation.'
- The official modularization page is high-level only: it does NOT define module types (data/feature/app/core), does NOT state 'feature modules must not depend on each other', and does NOT discuss api vs implementation. Those rules only exist in Now in Android's ModularizationLearningJourney.md — cite that, not /topic/modularization, for the dependency rules.
- Modularization overhead is explicitly called out as a real cost: 'Every module brings a certain amount of overhead in the form of increased build complexity and boilerplate code... If overhead counteracts scalability improvements, you should consider consolidating some modules.' An api/impl split doubles the module count — NiA acknowledges it deliberately over-modularizes to demonstrate a pattern 'fit for a much larger codebase'.
- The domain layer is optional and NiA barely uses it — only 3 use cases in `:core:domain`, all read-only stream combinators, and 'Events are handled by the UI layer calling methods on repositories directly.' A rule mandating a UseCase per operation contradicts official practice.
- Now in Android is NOT Clean Architecture and says so explicitly. Importing Clean Architecture vocabulary (entities/interactors/presenters, strict inward dependency rule, domain models mandatory at every boundary) into a rules file will conflict with the official docs.
- NiA's own pinned versions lag the ecosystem: AGP 9.0.0 while 9.3.0 is stable, Kotlin 2.3.0 while 2.4.10 is stable, and a Compose BOM *alpha* (`compose-bom-alpha:2025.09.01`) rather than the stable BOM. Do not treat NiA's catalog as the recommended version floor — treat its structure as the reference and pick versions from the release-notes pages.
- Baseline Profile generation requires `isMinifyEnabled = false` for the generation variant while the shipped release must have `isMinifyEnabled = true`; getting this backwards produces profiles that silently don't apply. Profile must stay under 1.5 MB.

## OPEN
- Is there an official developer.android.com page that endorses api/impl feature-module splitting, or does that pattern exist only in Now in Android's ModularizationLearningJourney.md? /topic/modularization does not mention it, and /topic/modularization/patterns was not reachable in this pass.
- Has Google published a formal 'use Navigation 3 for new apps, Navigation Compose is maintenance-only' statement? The Nav3 overview page describes it as improving on Navigation 2 and NiA has migrated, but no explicit deprecation or 'new apps should use Nav3' sentence was found on developer.android.com.
- Whether Kotlin 2.4 actually removed the K1 frontend (`-language-version=1.9` rejected) — this came only from Medium posts, not kotlinlang.org. kotlinlang.org/docs/releases.html confirms 2.4.0 (2026-06-03) and 2.4.10 (2026-07-14) as stable but says nothing about K1 removal.
- Exact release dates for Compose BOM 2026.08.00 and whether the BOM cadence is now formally monthly — the bom-mapping page lists versions without dates.
- Whether the Compose Preview Screenshot Testing plugin has left alpha / had its experimental flag removed by August 2026 (the doc still shows 0.0.1-alpha15 and `android.experimental.enableScreenshotTest=true`).
- What the `android` CLI actually is and how it is installed (the `android skills add --skill navigation-3` command appears in official docs, and github.com/android/skills targets Gemini/Antigravity by default) — unclear whether these skills are usable outside those agents or have a Claude-compatible install path.
- Whether developer.android.com has updated its architecture pages to reference Navigation 3 / adaptive Scene strategies, or whether /topic/architecture still assumes Navigation Compose — the architecture pages fetched mention NavigationSuiteScaffold and currentWindowAdaptiveInfo() but not Nav3.
- AGP versions 9.1/9.2 compatibility rows (Gradle minimums) were not captured; only 9.0.x and 9.3.0 were verified.
- Whether Hilt's officially documented version has moved past 2.57.1 (docs) / 2.59 (NiA catalog) and whether `androidx.hilt:hilt-lifecycle-viewmodel-compose` (used by NiA for `hiltViewModel<VM, Factory>`) is out of alpha — NiA pins 1.3.0-alpha02.

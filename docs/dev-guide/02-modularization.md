# 02 · 模組化與建置

**這份管**：什麼時候該開新模組、模組怎麼命名、模組之間的依賴邊怎麼宣告、`build.gradle.kts` / version catalog / convention plugin 的寫法。
**這份不管**：層與層的職責與程式碼歸屬見 [01-architecture.md](01-architecture.md)、DI 綁定見 [03-di.md](03-di.md)、跨模組導航介面見 [12-navigation.md](12-navigation.md)、測試模組與 fake 放哪見 [14-testing.md](14-testing.md)。
本專案是水平分層、**沒有** feature `:api` / `:impl` 拆分；假設該結構的官方規則已標 exempt（[91-decisions.md](91-decisions.md) D-17），不要嘗試建立那種模組。

---

## 模組類型

| category | 實例 | 可以依賴 | 不可以依賴 |
|----------|------|---------|-----------|
| `:app` | `:app` | 全部 | — |
| `:feature:*` | `:feature:common:order` | `:shared:*`、`:data:*`、`:domain:*` | 其他 `:feature:*`、`:app` |
| `:shared:*` | `:shared:routing`、`:shared:UI:designsystem` | `:shared:*`、`:data:*`（僅非 UI 模組）、`:domain:*` | `:feature:*`、`:app` |
| `:data:*` | `:data:repository` | `:data:*`、`:domain:contract` | `:feature:*`、`:shared:UI:*`、`:app` |
| `:domain:*` | `:domain:contract`、`:domain:usecase` | `:domain:contract` | `:data:*`、`:feature:*`、`:app` |

convention plugin 共 4 個：`com.kkday.application` / `com.kkday.feature` / `com.kkday.android.library` / `com.kkday.jvm.library`（build-logic composite build）。

---

## 規則

### unjustified-new-module · SHOULD · new-only · manual

新增模組必須符合下列至少一項理由，並寫在 PR 描述：需要替換多種實作、被 2 個以上 feature 共用、由不同團隊擁有、或程式碼量與建置成本足以獨立。只有一兩個檔案、且與既有模組高度互依的程式碼一律放進既有模組。

✗ 為一個 `DateFormatter` 開 `:shared:tool:dateformat`
✓ 放進主題明確的既有模組（`:shared:base`）；等第二個 feature 需要時再評估搬出

例外：無。不確定時走 `/guide-modularization`。

### nonstandard-module-path · MUST · new-only · manual

新模組路徑必須是 `:<category>:<name>[:<submodule>]`，category 限 `app` / `shared` / `feature` / `data` / `domain`；`name` 一律小寫 kebab-case。禁止新增沒有 category 前綴的頂層模組。

✗ `include(":search_core")` ／ `include(":shared:tool:ViewBuilder")`
✓ `include(":shared:tool:view-builder")` + `projectDir = File("libs/tool/view_builder")`

例外：既有 snake_case 模組（`:feature:common:coupon_page` 等）**不改名**（改名成本高、影響 CI 與 projectDir 對應）。

### new-code-in-app-module · SHOULD_NOT · new-only · manual

新功能的畫面、ViewModel、Repository 實作不得新增到 `:app`。`:app` 只保留 Application、DI 組裝、導航實作、跨 feature 黏合。

✗ 在 `app/src/main/java/.../feature/` 下新增整個新畫面
✓ 新畫面放對應 `:feature:*` 模組，只在 `:app` 註冊 Koin module 與 Router 實作

例外：既有 `:app` 內畫面的局部修改。
既有違規：`:app` 44 個 project 依賴 / 911 行 build script → [90-migration-ledger.md#m-23](90-migration-ledger.md)

### no-feature-to-feature-dep · MUST_NOT · new-only · deps-graph

`:feature:*` 模組不得依賴另一個 `:feature:*` 模組。共用需求下沉到 `:shared:*` / `:data:*`，跨畫面跳轉走 `:shared:routing` 的 `XxxRouter` 介面。

✗ `implementation(project(":feature:common:chat"))` 寫在 `:feature:common:presale_chat`
✓ `implementation(project(":shared:routing"))` + 注入 `ChatRouter`，實作綁在 `:app`

例外：無。紅線 C4。
既有違規：11 條 feature 互依邊 → [90-migration-ledger.md#m-24](90-migration-ledger.md)

### module-dep-wrong-direction · MUST_NOT · new-only · deps-graph

`:shared:*` / `:data:*` / `:domain:*` 不得依賴 `:feature:*` 或 `:app`；純 UI 模組（`:shared:UI:*`、`:feature:shared:ui`）不得依賴 `:data:*` 或 `:domain:usecase`；`:domain:*` 不得依賴 `:data:*`。

✗ `libs/feature/shared_ui/build.gradle.kts` 內 `implementation(project(":data:repository"))`
✓ UI 模組只收 domain model / UiModel 當參數，資料由呼叫端的 ViewModel 供給

例外：`:domain:contract` → `:data:model` 與 `:domain:usecase` → `:data:*` 屬既有技術債，**不得擴大**（不要再新增這方向的 import）。
既有違規：`:feature:shared:ui` 3 條、`:domain:usecase` 3 條 → [90-migration-ledger.md#m-24](90-migration-ledger.md)

### no-compile-only-project · MUST_NOT · new-only · deps-graph

模組間的 project 依賴一律 `implementation(project(...))` 或 `api(project(...))`。禁止 `compileOnly(project(...))` —— 它不進 runtime classpath，模組無法獨立編譯／測試，也讓 Hilt module 在 runtime `NoClassDefFound`。

✗ `compileOnly(project(":shared:tool:tracker:KKTracker"))`
✓ `implementation(project(":shared:tool:tracker:KKTracker"))`

例外：第三方 library 的 `compileOnly(libs.xxx)`（非 project 依賴）不在此限。
既有違規：163 處 → [90-migration-ledger.md#m-23](90-migration-ledger.md)

### api-project-without-reason · SHOULD · new-only · deps-graph

依賴預設 `implementation`。只有當該模組的型別確實出現在本模組 public 簽章時才用 `api`，且必須在該行上方加註原因註解。

✗ `api(project(":data:model"))`（只是為了讓下游拿得到）
✓ `// OrderRouter 的參數型別 OrderDetailRoutingInput 來自本模組` + `api(project(":shared:routing"))`

例外：無。

### implicit-transitive-dep · MUST_NOT · new-only+on-touch · deps-graph

不得使用未宣告的傳遞依賴。程式碼 import 了哪個模組的型別，`build.gradle.kts` 就必須明確宣告該模組依賴。

✗ `:domain:usecase` import `com.kkday.library.*`（`:domain:contract`）卻只宣告 `:data:networking:api`
✓ 直接 `implementation(project(":domain:contract"))`

例外：無。
既有違規：`:domain:usecase` 51 處隱性 import → [90-migration-ledger.md#m-24](90-migration-ledger.md)

### catch-all-module · SHOULD_NOT · new-only · manual

不得新增或擴大無主題的大雜燴模組（`:common`、`:utils`、`XxxUtils` 集合）。共用程式碼放進主題邊界明確的模組：designsystem / networking / tracker / routing / model / base。

✗ 新開 `:shared:tool:common` 放各種 helper
✓ 字串格式化放 `:shared:base`、埋點放 `:shared:tool:tracker:KKTracker`

例外：無。

### android-plugin-for-pure-kotlin · MUST · new-only · manual

不使用 Android 資源、Manifest 或 framework API 的模組（model、domain 契約、mapper、純工具）必須套用 `com.kkday.jvm.library`，不得用 `com.kkday.android.library`。

✗ 新的 `:domain:xxx` 模組套 `id("com.kkday.android.library")`
✓ `plugins { id("com.kkday.jvm.library") }`

例外：`:domain:contract` 目前因依賴 `:data:model` 而無法純 JVM 化，屬既有技術債，新模組不得比照。

### module-missing-convention-plugin · MUST · new-only · manual

新模組必須套用對應的 convention plugin，`build.gradle.kts` 只保留 `namespace` 與該模組專屬依賴。禁止自行宣告 `compileSdk` / `minSdk` / `targetSdk` / `compileOptions` / `kotlinOptions` / Compose 開關。

✗ 模組內 `android { compileSdk = 36; defaultConfig { minSdk = 29 } }`
✓ `plugins { id("com.kkday.feature") }` + `android { namespace = "com.kkday.feature.order" }`

例外：無。新模組不得用 Groovy `build.gradle`。
既有違規：12 個 build 檔未套用（含 6 個 Groovy） → [90-migration-ledger.md#m-25](90-migration-ledger.md)

### version-catalog-single-source · MUST · new-only+on-touch · manual

所有依賴座標、版本與 plugin 版本一律宣告在 `gradle/libs.versions.toml`，以 `libs.*` 引用。禁止在 build script 硬寫 `"group:name:version"`、禁止動態版本（`1.+`、`latest.release`）、禁止用 `buildSrc` 的 Kotlin object 管版本。alias 用 kebab-case。

✗ `implementation("androidx.appcompat:appcompat:1.4.1")`
✓ `implementation(libs.androidx.appcompat)`

例外：升版本身須先取得確認（紅線 A3），本規則只管「寫在哪」。
既有違規：34 處硬寫版號 → [90-migration-ledger.md#m-25](90-migration-ledger.md)

### kapt-in-new-module · MUST_NOT · new-only · manual

新模組的註解處理器一律 KSP。禁止在新模組加 `kotlin-kapt` 或 `kapt(...)`。註解處理器只套用在真正需要產碼的模組，不得由 convention plugin 無條件套到全部模組。

✗ `plugins { id("kotlin-kapt") }` + `kapt(libs.koin.compiler)`
✓ `ksp(libs.koin.compiler)`

例外：既有 4 個 kapt 模組（`:app` 的 autoValue、reductor compiller 等）維持不動，reductor 是移除 kapt 的最後阻礙。
既有違規 → [90-migration-ledger.md#m-25](90-migration-ledger.md)

### flat-dir-repository · MUST_NOT · new-only · manual

不得新增 `flatDir { dirs("libs") }` 或以本地 aar / jar 檔案路徑宣告依賴 —— 無 metadata、無法解析傳遞依賴、破壞可重現建置與 build cache。

✗ `flatDir { dirs("libs") }` + `implementation(name = "sdk-release", ext = "aar")`
✓ 走 maven repository，並在 `dependencyResolutionManagement` 用 `content { includeGroup(...) }` 收斂範圍

例外：既有 `settings.gradle.kts` 的 flatDir 屬 `migrate`，不在功能 PR 內移除。

### implicit-cross-module-r · SHOULD · new-only · manual

跨模組使用他模組資源時必須明確 import 該模組的 `R`，不得依賴傳遞 R class（本專案 `android.nonTransitiveRClass=false`，寫錯也會編譯過）。

✗ 在 `:feature:common:order` 直接寫 `R.string.order_title`（實際來自 `:shared:app_resource`）
✓ `import com.kkday.member.resource.R as appR` + `appR.string.order_title`
  （`libs/app_resource/build.gradle.kts:7` 的 namespace 是 `com.kkday.member.resource`，不是模組目錄名）

例外：模組自己擁有的資源。字串資源的其他規範見 [13-designsystem.md](13-designsystem.md)（紅線 A2：`strings.xml` 由 PM 維護）。

### gradle-legacy-build-flags · MUST · migrate · manual

`gradle.properties` 必須開啟 `org.gradle.parallel`、`org.gradle.caching`、`android.nonTransitiveRClass`，移除 `android.enableJetifier`，並停用已 deprecated 的 `org.gradle.configureondemand`。

✗ `android.enableJetifier=true`、`android.nonTransitiveRClass=false`、`org.gradle.unsafe.configuration-cache=true`（8.1 前的舊 key，實質無效）
✓ 逐項在獨立 PR 開啟並驗證建置

例外：`org.gradle.configuration-cache=true` 同列 `migrate`，需獨立驗證（[91-decisions.md](91-decisions.md) D-19），**不要**為了合規在功能 PR 打開。
既有違規 → [90-migration-ledger.md#m-25](90-migration-ledger.md)

---

## 其他檔案的規則（只給指向，不在這裡重述）

| 主題 | 去哪查 |
|------|-------|
| 各層職責、SSOT、UDF、程式碼放哪一層 | [01-architecture.md](01-architecture.md) |
| 全域單例 / static 跨模組共享狀態 | [01-architecture.md#global-state-holder](01-architecture.md) |
| domain 禁 import data 實作 | [04-domain-layer.md#domain-imports-impl](04-domain-layer.md) |
| Repository 介面歸 `:domain:contract` | [05-data-layer.md#repository-needs-interface](05-data-layer.md)、[91-decisions.md](91-decisions.md) D-12 |
| 每模組宣告自己的 Koin module、由 `:app` 收集 | [03-di.md](03-di.md) |
| 跨模組導航契約（`XxxRouter` + `XxxRoutingInput`） | [12-navigation.md#cross-module-navigation](12-navigation.md) |
| 共用 fake / test double 放哪個 source set | [14-testing.md](14-testing.md) |
| Hilt 導入的模組前置條件 | [03-di.md](03-di.md)、[90-migration-ledger.md#m-27](90-migration-ledger.md) |

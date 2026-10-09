# 02 · 模組化

這份管**模組怎麼切、怎麼命名、誰能依賴誰，以及 Gradle 建置設定放在哪裡**。
不管單一模組內部的分層職責（01）、不管綁定怎麼寫（03）、不管導航契約的內容（13）。
單模組專案跳過第一～三節，第四節的 Gradle 規則仍然適用。

| 疑問 | 去哪 |
|---|---|
| 這段邏輯屬於哪一層、要不要開 UseCase | `01-architecture` |
| 介面與實作跨模組怎麼綁定 | `03-dependency-injection` |
| DTO / Entity / domain model 怎麼分、在哪轉換 | `04-domain-layer` `05-data-layer` |
| 跨模組導航的 route 定義與參數型別 | `13-navigation` |
| fake 該怎麼寫、哪一層測什麼 | `15-testing` |

---

## 一、模組分類與依賴方向

```
:app                    組裝層：DI 入口、NavHost、Application、Manifest 合併
:feature:<name>         一個使用者可見的功能：畫面 + ViewModel + 該功能專屬邏輯
:core:<topic>           跨 feature 共用：data / network / database / datastore /
                        model / domain / designsystem / ui / common / analytics / testing
```

依賴方向單向不可逆：`:app` → `:feature:*` → `:core:*`。外層按類別分（feature / core），feature 內部才分層 —— 不要在外層按層分成 `:ui` `:domain` `:data` 三個巨型模組，那會讓一個需求散落到所有模組。路徑一律小寫 kebab-case、單數名詞，不加 `-module` / `-lib` 後綴。

## 二、開新模組還是塞現有模組

```
這段程式碼現在有幾個使用者？
├ 只有一個 feature 用 ──────────────── 留在該 feature 模組內，不要開模組
└ 兩個以上模組要用
   ├ UI 元件 / theme / token ───────── :core:designsystem
   ├ 跨 feature 的資料存取 ─────────── :core:data 或 :data:<domain>
   ├ 純資料型別 ───────────────────── :core:model
   ├ 測試替身 / 測試工具 ───────────── :core:testing
   └ 以上皆非 → 只有滿足下列任一條件才開新模組：
        · 需要多實作替換（build variant、A/B、平台差異）
        · 多個 App 或多個變體共用
        · 由不同團隊獨立擁有
        · 程式碼量與建置成本大到足以獨立編譯
```

一兩個檔案、且與既有模組高度互依的程式碼**不要**單獨開模組：模組本身有 build script、DI 綁定、namespace 的固定成本。

## 三、要不要拆 `:api` / `:impl`

**值得拆**：該 feature 會被其他 feature 導航進入、需要在建置變體間替換實作、由不同團隊擁有。
**過度設計**：只有單一實作又沒有跨 feature 引用就先拆 —— 直接寫成一個 `:feature:<name>` 模組，等真的有第二個使用者再拆，拆分是機械性重構。
拆了之後，`:api` 只放契約（route / NavKey 定義、跨模組介面、契約需要的 model），不得出現 Composable、Activity、Fragment、ViewModel、Repository 實作或 UI 資源。

## 四、規則

### uncategorized-module-path · MUST · new-only · regex

`settings.gradle.kts` 中每個模組路徑都必須帶類別前綴 `:app` / `:feature:` / `:core:`（或既有專案已採用的 `:data:` / `:domain:`），不得出現無前綴的頂層模組。

✗ `include(":search")` `include(":utils")`
✓ `include(":feature:search")` `include(":core:common")`

例外：無 ｜ src: 官方 sample nowinandroid `settings.gradle.kts`

### cross-feature-module-dependency · MUST_NOT · new-only+on-touch · regex

feature 模組的 build script 不得依賴另一個 feature 模組；只有在對方拆了 `:api` 時，才能依賴該 `:api`。

✗ `implementation(project(":feature:order"))` 出現在 `feature/checkout/build.gradle.kts`
✓ `implementation(project(":feature:order:api"))`（僅含導航契約）

例外：無 ｜ src: 官方 sample nowinandroid ModularizationLearningJourney.md

### cross-feature-class-import · MUST_NOT · new-only+on-touch · regex

不得在一個 feature 內 import 另一個 feature 的 Screen / Activity / Fragment / ViewModel 類別，也不得用 `Intent(context, XxxActivity::class.java)` 直接跳轉；跨 feature 跳轉一律經契約模組公開的 route 或介面。

✗ `startActivity(Intent(context, OrderDetailActivity::class.java))`
✓ `navController.navigate(OrderDetailRoute(orderId = id))`（route 定義在 `:feature:order:api` 或 `:core:navigation`）

例外：無 ｜ src: developer.android.com/topic/modularization/patterns

### core-depends-on-feature · MUST_NOT · new-only · regex

`:core:*`（含 `:data:*` `:domain:*`）不得依賴任何 `:feature:*` 或 `:app`。core 之間可互相依賴，但不得形成環。

✗ `implementation(project(":feature:order"))` 出現在 `core/data/build.gradle.kts`
✓ core 只依賴其他 core：`implementation(project(":core:model"))`

例外：無 ｜ src: 官方 sample nowinandroid ModularizationLearningJourney.md

### circular-module-dependency · MUST_NOT · new-only · manual

任兩個模組間不得互相依賴。需要雙向溝通時，由第三方調節模組轉送（通常是持有導航圖的 `:app`），或雙方共同依賴同一個抽象模組。

✗ `:feature:cart` 依賴 `:feature:order`，`:feature:order` 又依賴 `:feature:cart`
✓ 兩者都依賴 `:core:navigation` 的契約，實際跳轉由 `:app` 組裝

例外：無 ｜ src: developer.android.com/topic/modularization/patterns

### impl-module-referenced-outside-app · MUST · new-only · manual

採 api/impl 分離時，`:x:impl` 只能被 `:app` 或測試設定依賴，其他模組一律依賴 `:x:api`。

✗ `:feature:checkout` 的 build script 出現 `implementation(project(":feature:order:impl"))`
✓ 只有 `app/build.gradle.kts` 有 `implementation(project(":feature:order:impl"))`

例外：測試模組可依賴 impl 以取得真實實作 ｜ src: developer.android.com/topic/modularization/patterns

### api-dependency-without-reason · SHOULD · new-only+on-touch · regex

模組依賴一律宣告 `implementation`；只有型別確實出現在本模組 public 簽章時才用 `api`，且該行要加註原因。

✗ `api(project(":core:network"))`（本模組沒有任何 public 簽章暴露 network 型別）
✓ `implementation(project(":core:network"))`

例外：型別出現在 public 簽章時可用 `api`，需同行註解說明 ｜ src: developer.android.com/topic/modularization/patterns

### unnecessary-public-declaration · MUST · new-only · manual

模組內不需要被其他模組使用的宣告一律標 `internal`（或 `private`）。資料來源型別（ApiService、DAO、DTO、Entity、DataSource）必須是 `internal`，模組對外只公開 Repository 介面與 domain model。

✗ `class OrderApiService { ... }`（public，其他模組可直接注入）
✓ `internal interface OrderApiService { ... }` + `interface OrderRepository { ... }` 為唯一 public API

例外：無 ｜ src: developer.android.com/topic/modularization/patterns

### class-duplicated-across-modules · MUST · new-only+on-touch · manual

一旦第二個模組需要某個類別，必須把它搬到對應的 `:core:*` 模組，不得複製貼上，也不得改成依賴對方 feature。

✗ 在 `:feature:checkout` 複製一份 `:feature:order` 的 `PriceFormatter`
✓ 搬到 `:core:ui`（或 `:core:common`），兩個 feature 都依賴它

例外：無 ｜ src: 官方 sample nowinandroid ModularizationLearningJourney.md

### catch-all-utility-module · SHOULD_NOT · new-only · manual

不得新增或擴大沒有主題邊界的大雜燴模組。共用程式碼要放進主題明確的模組。

✗ 新增 `:utils` 模組，或把第 12 個不相關的 `XxxUtils` 塞進 `:core:common`
✓ 依主題落位：`:core:designsystem` `:core:network` `:core:analytics` `:core:model`

例外：`:core:common` 可放真正跨主題的基礎設施（Result 型別、dispatcher qualifier），但不得成為函式垃圾桶 ｜ src: developer.android.com/topic/modularization/patterns

### premature-module-split · SHOULD · new-only · manual

新增模組必須具備第二節列出的理由之一並寫在 PR 描述；只有一兩個檔案、且與既有模組高度互依的程式碼不得單獨開模組。

✗ 為一個 `DateFormatter` 開 `:core:date`
✓ 放進 `:core:common`，等到出現第二種實作或第二個 App 共用時再拆

例外：無 ｜ src: developer.android.com/topic/modularization（Granularity）

### android-library-for-pure-kotlin · MUST · new-only · manual

不需要 Android 資源、Manifest 或 framework API 的模組（model、純邏輯、mapper）必須用 Kotlin JVM library plugin，不得宣告成 android library。

✗ `plugins { id("com.android.library") }` 出現在 `core/model/build.gradle.kts`
✓ `plugins { alias(libs.plugins.kotlin.jvm) }`

例外：無 ｜ src: developer.android.com/topic/modularization/patterns

### duplicated-build-config · MUST · new-only+on-touch · regex

模組 build script 不得重複宣告共通建置設定（`compileSdk`、`minSdk`、`targetSdk`、`jvmTarget`、`compileOptions`、Compose 開關、共通測試依賴）；這些一律由 `build-logic` included build 的 convention plugin 提供，模組只留 `namespace` 與自己專屬的依賴。也不要用 root build script 的 `subprojects { }` / `allprojects { }` 統一套設定。

✗ `android { compileSdk = 35; defaultConfig { minSdk = 24 } }` 出現在每個模組
✓ `plugins { alias(libs.plugins.myapp.android.feature) }` + `android { namespace = "..." }`

例外：無 ｜ src: developer.android.com/topic/modularization/patterns

### hardcoded-dependency-coordinate · MUST · new-only+on-touch · regex

依賴座標與版本一律宣告在 `gradle/libs.versions.toml` 並以 `libs.*` 引用（alias 用 kebab-case）。禁止在 build script 硬寫 `group:name:version` 字串、禁止動態版本（`1.+`、`latest.release`）、禁止用 `buildSrc` 的 Kotlin object 管版本。

✗ `implementation("androidx.core:core-ktx:1.13.1")`
✓ `implementation(libs.androidx.core.ktx)`

例外：無 ｜ src: developer.android.com/build/migrate-to-catalogs

### kapt-in-new-module · MUST_NOT · new-only · regex

新模組不得引入 `kotlin-kapt`，註解處理器一律用 KSP。既有 kapt 只在尚未支援 KSP 的情境保留，且必須隔離在單獨模組。

✗ `plugins { id("kotlin-kapt") }` + `kapt(libs.hilt.compiler)`
✓ `plugins { alias(libs.plugins.ksp) }` + `ksp(libs.hilt.compiler)`

例外：dataBinding 等官方尚未支援 KSP 的處理器 ｜ src: developer.android.com/build/migrate-to-ksp

### module-namespace-mismatch · MUST · new-only · manual

每個 Android 模組的 `namespace` 必須與模組路徑一致，套件目錄結構也要相符。

✗ `:feature:order` 的 namespace 寫成 `com.example.app`
✓ `:feature:order` → `namespace = "com.example.feature.order"`

例外：無 ｜ src: 官方 sample nowinandroid

### shared-fake-in-main-source-set · MUST · new-only+on-touch · manual

跨模組共用的 fake、test double、測試工具必須放在專用測試模組（`:core:testing`、`:core:data-test`）或 Gradle `testFixtures`，以 `testImplementation` 依賴；不得放進 main source set。

✗ `core/data/src/main/kotlin/.../FakeOrderRepository.kt`
✓ `core/testing/src/main/kotlin/.../FakeOrderRepository.kt`，消費端 `testImplementation(project(":core:testing"))`

例外：無 ｜ src: developer.android.com/topic/modularization/patterns

### transitive-r-class-reference · MUST_NOT · new-only · manual

不得倚賴傳遞 R class 取用他模組資源。跨模組資源必須明確 import 擁有模組的 `R`，或由擁有模組以 Composable / 函式封裝後提供。

✗ 在 feature 直接寫 `R.string.common_retry`，而該字串定義在 `:core:ui`
✓ `import com.example.core.ui.R as coreUiR` 後使用 `coreUiR.string.common_retry`

例外：無 ｜ src: developer.android.com/build/optimize-your-build

### missing-build-performance-flags · MUST · migrate · regex

`gradle.properties` 必須開啟 `org.gradle.parallel=true`、`org.gradle.caching=true`、`org.gradle.configuration-cache=true`、`android.nonTransitiveRClass=true`，且不得出現 `android.enableJetifier=true`。

✗ `android.enableJetifier=true` 或缺少 `android.nonTransitiveRClass=true`
✓ 四個 flag 齊備、無 Jetifier

例外：configuration cache 與既有 plugin 不相容時可暫緩，需在該行註解記錄阻塞原因與追蹤方式 ｜ src: developer.android.com/build/optimize-your-build

### unverified-module-graph · SHOULD · migrate · manual

依賴方向規則必須有自動檢查，不能只靠 code review。最低成本是在 CI 加一條 grep（feature 不得依賴 feature、core 不得依賴 feature）；模組數量成長後改用宣告式的模組依賴檢查 plugin。

✗ 只在 PR 描述寫「有注意依賴方向」
✓ CI 步驟：`! rg -q 'project\(":feature:' feature/*/build.gradle.kts`

例外：單模組專案 ｜ src: 業界共識

## 尚無定論

- **feature 進入點的註冊方式**：小型 App 由 `:app` 直接組裝 NavHost 即可；模組數量大時，官方模組化指引示範以 DI 多重綁定讓每個 feature 自行註冊進入點，避免 `:app` import 所有 Screen。兩者都可行，屬建議而非規則。
- **`:core:domain` 是否獨立**：官方 sample 把 UseCase 集中在 `:core:domain`；依 domain 主題切分成多個模組也常見。建議先集中，等該模組明顯過大再依主題拆，別一開始就切碎。

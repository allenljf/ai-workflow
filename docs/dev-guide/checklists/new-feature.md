# Checklist · 新功能／新需求

實作完成後**逐項回答**，不要只打勾。規則細節看對應準則檔，這裡不重述。

## 動工前

- [ ] 已讀 `00-red-lines.md` + `01-architecture.md` + `02-modularization.md`
- [ ] 確認這個功能要放哪個模組（新開？塞現有？）→ 不確定就跑 `/guide-modularization`
- [ ] 確認資料流：UI ← ViewModel ← UseCase(選用) ← Repository ← DataSource
- [ ] 若有 Figma：已確認每個元件對應的 StyleDictionary token
- [ ] 若有 API spec：已確認 endpoint、request/response 型別、錯誤碼

## 分層

- [ ] Repository 介面在 `:domain:contract`，`XxxRepositoryImpl` 在 `:data:repository` — `repository-needs-interface`
- [ ] domain 層沒有 `import android.*`（`androidx.annotation` / `androidx.paging` 除外） — `android-in-domain`
- [ ] domain 層沒有 import `*RepositoryImpl` / `*ApiService` / `*Dao` — `domain-imports-impl`
- [ ] UI 層沒有直接碰 `ApiService` / `Dao` / `SharedPreferences` / `DataStore`
- [ ] 網路 DTO 沒有直接送到 Composable 參數 — `dto-in-ui`
- [ ] UseCase 有商業邏輯或被 ≥2 個 ViewModel 用；純轉發的 pass-through 也可接受（見 91-decisions D-13）

## 模組與建置

- [ ] 模組依賴用 `implementation` / `api`，**沒有** `compileOnly(project(...))` — `no-compile-only-project`
- [ ] 沒有新增 feature 模組之間的直接依賴 — `no-feature-to-feature-dep`
- [ ] 依賴版本從 `gradle/libs.versions.toml` 取，沒有寫死版本號 — `version-catalog-single-source`
- [ ] 沒有為了讓建置過而升版（紅線 A3）

## DI

- [ ] 用建構子注入；`by inject()` 只出現在 Activity/Fragment/Application/Service/Worker — `service-locator-get`
- [ ] Composable 內沒有 `by inject()`（只允許 `koinViewModel()`）
- [ ] 沒有手動 `new XxxRepositoryImpl()` — `manual-impl-instantiation`
- [ ] 新模組用 Koin annotation 風格（照 `presale_chat` 樣板）；**沒有**寫 Hilt / `javax.inject`（本專案不採用）— `hilt-before-prerequisites`
- [ ] 新增 `@Module` 或新增綁定 → 有一支 `verify()` 測試，且 `KOIN_CONFIG_CHECK` 為 `"true"` — `koin-module-not-verified`

## 狀態與非同步

- [ ] ViewModel 沒有對外暴露 Mutable 型別 — `mutable-state-exposed` / `mutable-state-inferred`
- [ ] ViewModel 沒有持有 `Context` / `Activity` / `View` — `context-in-viewmodel`
- [ ] 沒有寫新的 Reductor store/reducer（紅線 D4）
- [ ] 沒有硬寫 `Dispatchers.IO` / `Default` — `hardcoded-dispatcher`
- [ ] 沒有 `GlobalScope`、production 沒有 `runBlocking` — `global-scope` / `run-blocking-prod`
- [ ] `catch (e: Exception)` 有處理 `CancellationException` — `swallow-cancellation`
- [ ] one-off event 用 state 表達；若用 Channel，屬於白名單（離開 app 的外部動作）

## UI

- [ ] 新畫面是 Compose，沒有新增 `res/layout/*.xml` — `new-xml-layout`
- [ ] 用 `collectAsStateWithLifecycle()` — `collect-as-state`
- [ ] 可重用 composable 有 `modifier: Modifier = Modifier` — `compose-modifier-missing`
- [ ] `LazyColumn` / `LazyRow` 的 `items` 有 `key` — `lazy-list-no-key`
- [ ] 間距/顏色/圓角/字級全部用 `StyleDictionary.kkXxx`，沒有 hardcode — `hardcoded-dimen` / `hardcoded-color` / `hardcoded-shape`
- [ ] 硬編碼字串有加 `// TODO: replace with stringResource - <說明>` 並列入 task
- [ ] 用 Material3，沒有新增 M2 import — `no-new-material2`

## 資料與網路

- [ ] Retrofit endpoint 是 `suspend fun` 且回傳**具名** DTO（不是 `<T>` 泛型抹除） — `retrofit-non-suspend` / `api-no-type-erasure`
- [ ] 新建 DTO 檔用 kotlinx.serialization；既有 Gson 檔加欄位維持 `@SerializedName`（見 91-decisions D-14）
- [ ] 沒有 `Gson()` 直接 new，用 `GsonInstance` — `raw-gson`
- [ ] 錯誤有轉成 domain error，沒有 `printStackTrace()` — `print-stacktrace`
- [ ] 用對了 `ApiResult`（專案有兩個同名的，見 `05-data-layer.md`）
- [ ] 新的持久化用 DataStore，沒有新增 SharedPreferences key — `ds-no-new-sharedpreferences`

## 測試

- [ ] 新的 UseCase 與 Repository 都有單元測試（紅線 H3）
- [ ] 每個 `@Test` 都有真正驗證行為的斷言 — `test-no-assert` / `assert-tautology`
- [ ] 沒有 `Thread.sleep`，用 `runTest` + `advanceUntilIdle` — `thread-sleep-test`
- [ ] 優先手寫 Fake 而非 `mockk(relaxed = true)` — `prefer-fakes-over-mocks`
- [ ] 沒有留下 `@Ignore` 或被註解掉的斷言

## 埋點

- [ ] 若需求含埋點：已讀 `16-tracking.md`，PIN 已同步（跑 `/axis-sync`）

## 收尾

- [ ] `./gradlew :<module>:compileDevelopDebugKotlin` 通過
- [ ] `./gradlew :<module>:detekt` 通過
- [ ] 單元測試綠燈
- [ ] 跑過 `/guide-audit` 且必修項為 0
- [ ] 觸碰到但本次未修的違規已登記 `90-migration-ledger.md` 第九節

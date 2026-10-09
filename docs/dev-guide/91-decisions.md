# 91 · 決策紀錄（Decisions）

準則檔只寫「規則是什麼」，這份寫「**為什麼是這樣規定**」。包含已定案決策、被否決的選項、規則衝突裁決、未啟用與不採用的規則。

規則檔中不得重述這裡的理由；有疑問就連到這裡的對應段落。

---

## 一、四項專案定案

### D-01 依賴注入：一律 Koin annotation 風格

**定案**：本專案 DI 容器只有 Koin，**明確不採用 Hilt**（不是「以後再說」，是評估後的決定）。新舊模組一律 Koin 的 annotation 風格：`@Module` + `@ComponentScan` + `@Single` / `@Factory` / `@KoinViewModel` + constructor injection，照 `libs/feature/presale_chat/.../di/PresaleChatModule.kt` 抄。

**為什麼不採用 Hilt**：官方推薦 Hilt，但本專案有 4 項架構阻礙，其中 **2 項是永久性的**，不是排一個 sprint 就能消掉：

| 阻礙 | 性質 | 說明 |
|------|------|------|
| base class 帶必填建構子參數 | **永久** | `BaseActivity<VB>(val bindingFactory: (LayoutInflater) -> VB)` 等 base class，Hilt 生成的 `Hilt_XxxActivity` 無法轉發 super 建構子參數 → **52 個畫面無法加 `@AndroidEntryPoint`**。要解只能把全部 base class 改成無參數建構子，等於重寫 View 層 |
| `attachBaseContext()` 時序 | **永久** | locale 包裝在 `attachBaseContext()` 內就要拿 `IResourcesProxy` / `ILocaleHelper`，該時點早於 `onCreate`，Hilt 欄位注入還沒發生 → 這條路徑無論如何都得留 Koin |
| `compileOnly(project)` 163 處 | 可解但工程量大 | Hilt `@Module` 在 feature 模組會 `NoClassDefFound`（M-23） |
| `configureDI` 無 opt-in | 可解 | convention plugin 無條件套用到 33 個模組，需另建 `HiltConvention` |

前兩項代表即使做完全部前置工作，專案仍會是「Hilt + Koin 兩套容器長期共存」，而雙容器的成本（橋接、型別歸屬、DI 錯誤要查兩邊）高於 Hilt 帶來的收益。**因此不採用。** 技術細節存查見 [90-migration-ledger.md#m-27](90-migration-ledger.md)。

**那 Hilt 的編譯期驗證怎麼補**：走 Koin 自己的兩條驗證管道 —— KSP 參數 `KOIN_CONFIG_CHECK=true`（建置期）＋ `module.verify()` JVM 測試（見 [03-di.md](03-di.md) `koin-module-not-verified`，已由 `dormant` 改為 `new-only`）。這兩條到位後，「DI 錯誤只能 runtime crash 才發現」的問題就解掉了，這也是原本傾向 Hilt 的唯一理由。

**現況數字**：`hiltViewModel` / `javax.inject` / Hilt gradle plugin 使用數皆為 **0**；`libs.versions.toml` 的 `dagger 2.48.1` 是零引用殘留宣告，應清理。寫任何 Hilt 註解都會編譯失敗。

### D-02 UI 狀態架構：MVVM + UDF

**定案**：ViewModel 暴露單一 `StateFlow<UiState>`，事件用 method call。不寫新的 Reductor store / reducer。

**為什麼不用 MVI**：官方沒有 MVI 的明文指南，樣板較多。UDF 已經涵蓋 MVI 的核心價值（單向資料流、狀態可預測），而官方文件與 nowinandroid 全部是 MVVM + UDF 寫法 —— 這對 AI agent 特別重要：**官方樣本多的寫法，agent 寫錯的機率最低**。

**為什麼不維持 Reductor**：vendored 第三方 Redux，上游 2017-01-12 後停止維護，且綁死 `:app` 的 kapt 與 RxJava2 兩條退場路徑。

**專案標準樣板**：`app/.../login_methods/feature/login_methods/LoginMethodsViewModel.kt`。

### D-03 UI 技術：新畫面一律 Compose

**定案**：新畫面禁止新增 `res/layout/*.xml`。既有 XML 畫面維持，重構時才轉。

**「新畫面」的判定**（這個邊界必須寫清楚，否則無法執行）：

| 情況 | 判定 |
|------|------|
| 新增 navigation destination | **新畫面** → Compose |
| 新增全螢幕內容（Activity / Fragment / dialog / bottom sheet） | **新畫面** → Compose |
| 既有 Fragment 內新增一個區塊 | **不是新畫面** → 用 `ComposeView` 嵌入（見 [17-interop-views-compose.md](17-interop-views-compose.md)） |
| 既有 RecyclerView 新增一種 item type | **不是新畫面**，但**不得新增 Epoxy model** → 該清單若要加新類型，評估整段換 `LazyColumn` |

**允許的 XML 例外**：第三方 View SDK 強制要求、既有 XML 畫面的局部修改。例外必須在 PR 說明並記入遷移帳。

### D-04 強制範圍：四級 enforce

**定案**：`new-only`（A）/ `on-touch`（B）/ `migrate`（C）/ `exempt`（D）四級。**不使用 `dormant`**，理由見 [D-20](#d-20-原-dormant-規則的處置已清空)。定義見 [README.md](README.md#enforce強制時機)。

**為什麼不是只有「新程式碼強制 + 觸碰即修」兩級**：本專案多項違規是**主流寫法而非少數例外**（`by inject()` 758 處、`Dispatchers.IO` 139 檔、`collectAsState` 103 檔、`io.reactivex` 194 檔）。兩級的話，agent 面對既有檔案只能猜該不該改，結果是要嘛不敢動、要嘛把功能 PR 改成 200 行重構。

`enforce` 回答的是「什麼時候要修」，`level` 回答的是「錯得多嚴重」。兩者獨立。

---

## 二、規則衝突裁決

研究階段從官方文件產出約 390 條規則，其中約 110 條重複、8 組直接對撞。以下是裁決結果。**準則檔一律以此為準。**

### D-05 dispatcher 注入 vs Repository 自行切 IO

**衝突**：一條規則要求「Repository 的 suspend 函式必須自行 `withContext(Dispatchers.IO)` 包住」，另一條禁止硬寫 `Dispatchers.IO`。前者的正文直接示範了後者禁止的寫法。

**裁決**：兩件事都對，但寫法只有一種 ——

```kotlin
class DefaultOrderRepository(
    private val api: OrderApiService,
    private val ioDispatcher: CoroutineDispatcher,   // 注入
) : OrderRepository {
    override suspend fun getOrder(id: String): Order =
        withContext(ioDispatcher) { api.getOrder(id).toDomain() }   // 自己負責 main-safe
}
```

全庫只保留**一條** dispatcher 規則：`hardcoded-dispatcher`（owner: [11-coroutines-flow.md](11-coroutines-flow.md)）。「suspend 必須 main-safe」是另一條獨立規則 `suspend-not-main-safe`，兩者不重述彼此。

### D-06 Compose 穩定性：預設就做 vs 量測後才做

**衝突**：兩條規則要求 UiState 集合預設用 `ImmutableList`、UI model 預設標 `@Immutable`；第三條 MUST NOT 禁止未量測就全面套用。

**裁決**：

- 新 UiState 的集合欄位**用 `List`**（不強制 `ImmutableList`）
- 新 UiState **不做任何穩定性標註**，寫成 `data class` + 全 `val`（規則 `uistate-stability-default`）
- `@Immutable` / `ImmutableList` **只在量測後**針對熱路徑補，量測依據照 `perf-claim-without-evidence` 附在 PR
- **Compose stability configuration file 屬 build-logic 基建**（[90-migration-ledger.md](90-migration-ledger.md) M-25），不在功能 PR 內自建；它到位與否都不改變上面三點

理由：Kotlin 2.1 的 strong skipping 已大幅降低穩定性標註的必要性；stability config file 是官方推薦的集中處理方式，比在幾百個 data class 上撒註解更好維護。

保留規則：`mutable-collection-in-state`（禁止 `MutableList` 等可變集合，這條沒有爭議）。降級移除：預設 `ImmutableList` 的要求。

### D-07 測 StateFlow：斷言 `.value` vs Turbine

**衝突**：一條說「優先直接斷言 `value`」，一條說「不得只斷言 `.value` 就宣稱通過」。

**裁決**：依測什麼決定，寫成一條帶條件的規則 ——

| 測什麼 | 怎麼測 |
|-------|-------|
| 單一終態（操作後的最終狀態） | 斷言 `.value`，**前提是已透過 `advanceUntilIdle()` 或已起 collector 確保狀態已更新** |
| 狀態序列（Loading → Success 的中間狀態） | 用 Turbine `test { awaitItem() }` |

Turbine 目前**不在專案依賴中**，屬前置基建項。在加入前，序列測試用手動 collect + `advanceUntilIdle()`（照 `PresaleChatViewModelTest.kt` 的做法）。

### D-08 Hilt 組不採用（exempt）

**衝突**：原本 10 條 Hilt MUST 與 5 條 Koin MUST 並存，agent 會在 Koin 模組裡寫 `@HiltViewModel`。

**裁決**：依 [D-01](#d-01-依賴注入一律-koin-annotation-風格)，Hilt 組**不採用**。`rules.yaml` 只保留 `hilt-module-no-installin`、`hilt-scope-mismatch` 兩條並標 `enforce: exempt` + `reason`（留負面訊號，避免有人日後又提案導入），其餘刪除；md 不保留段落。

Hilt 那幾條的實質價值改由現行 Koin 規則承擔，不重複造規則：

| 原 Hilt 規則 | 承擔它的 Koin 規則 |
|-------------|------------------|
| `@Module` 必須標 `@InstallIn` | `componentscan-too-broad`（掃描範圍必須是自己模組）＋ `koin-binds-missing`（對外型別必須顯式宣告） |
| component ↔ scope 嚴格對應 | `usecase-as-single`、`single-for-stateless`（含 ViewModel 不得 `@Single`）、`koin-scope-not-closed` |
| 禁止在錯的地方寫 Hilt 註解 | `hilt-before-prerequisites`（現行有效，`new-only`） |
| 共存橋接邊界 | `di-container-single-framework`（原 `di-bridge-outside-app` 改寫：DI 容器只有 Koin，禁止第二套框架） |

### D-09 `by inject()` 的白名單

**衝突**：一條允許在「Android framework 類別與 **Composable**」使用，另一條只允許「框架入口」（不含 Composable）。

**裁決**：白名單寫死為 `Activity` / `Fragment` / `Application` / `Service` / `BroadcastReceiver` / `Worker`。

**Composable 內禁止 `by inject()`**，只允許 `koinViewModel()`。理由：Composable 內 `by inject()` 等於繞過 state hoisting 直接拿 Repository，與 UDF 及「可重用 composable 不得持有 ViewModel」的規則精神衝突，也讓該 composable 無法 preview。

### D-10 domain 層的 androidx 白名單

**衝突**：三處給了三種白名單（`androidx.annotation`、`+androidx.collection`、`+androidx.paging`）。

**裁決**：以紅線 **C1** 為準 —— 允許 `androidx.annotation` 與 `androidx.paging`，其餘 `android.*` / `androidx.*` 一律禁止。另外兩處改為引用 C1，**不得自訂白名單**。

`androidx.paging` 必須在白名單內的原因：`PagingData` 由下層產生、需經 domain 傳到 UI，禁掉會讓 Paging 3 無法用於分層架構。

### D-11 Retrofit ApiService 的可見性

**衝突**：兩條規則要求 ApiService 標 `internal`。但 Kotlin `internal` 是 module-scoped，本專案 ApiService 在 `:data:networking:api`、Repository 實作在 `:data:repository` —— **跨模組，`internal` 物理上不可能達成**。

**裁決**：標為本專案 `exempt`。改寫成可執行的等價規則：「ApiService 必須 public，但不得被 `:domain:*` 或 UI 模組依賴」，由模組依賴檢查驗證（前置基建：目前**沒有任何**模組依賴自動檢查）。

### D-12 Repository 介面歸屬

**衝突**：一條說「data 模組對外只公開 repository 與 model」，一條說「UseCase 只能依賴 `:domain:contract` 的介面」。兩者對「誰擁有 Repository 介面」的心智模型不同。

**裁決**：**介面歸 `:domain:contract`**，實作歸 `:data:repository`。因此：

- `:data:repository` 對外只公開 domain model 與 DI 綁定，**不公開 Repository 介面**（介面本來就在 contract）
- 新 Repository 一律：介面 → `:domain:contract`，`XxxRepositoryImpl` → `:data:repository`
- 既有 46 個無介面的 concrete Repository 不主動抽介面（`migrate`）

現況：`:domain:contract` 只有 8 個 repository 介面，另 13 個散在各 feature 模組的 `domain/repository` 套件。新增一律進 `:domain:contract`。

### D-13 UseCase 是否允許 pass-through

**衝突**：官方建議「商業邏輯已過於複雜、或至少 2 個 ViewModel 重用時才抽 UseCase」且 MUST NOT 禁止 pass-through；AGENTS.md 的任務食譜要求每個新 API 流程都建 UseCase（第 5 步）。多數新 API 的 UseCase 就是 pass-through。

**裁決**：**允許 pass-through UseCase**，但降為 `MAY`（不強制、不禁止）。判斷準則：

| 情況 | 做法 |
|------|------|
| 有商業邏輯（組合多個 repository、轉換、驗證、快取策略） | **必須**開 UseCase |
| ≥2 個 ViewModel 會用到同一段取資料邏輯 | **必須**開 UseCase |
| 純轉發單一 repository 方法，只有一個 ViewModel 用 | **可以**開（維持專案一致性），也可以讓 ViewModel 直接用 Repository |

理由：AGENTS.md 的食譜是專案慣例，強行禁止 pass-through 會與既有 200+ 個 UseCase 的風格衝突；但也不該要求每個欄位都包一層。**不要為了規則爭論，兩種都可過 review。**

### D-14 kotlinx.serialization vs Gson

**衝突**：一條 MUST 要求新 DTO 一律 kotlinx.serialization；紅線 G1 要求一律用 `GsonInstance`（pre-push hook 會擋 `new Gson()`）；另一條 MUST NOT 禁止同 class 混用兩套註解。394 個 `@SerializedName` 檔案一旦要加欄位就進入無解區。

**裁決**：**以檔案為單位，不以欄位為單位** ——

| 情況 | 用哪個 |
|------|-------|
| 新建 DTO 檔案 | kotlinx.serialization（`@Serializable` + `@SerialName`） |
| 既有 Gson DTO 檔案新增欄位 | 繼續 `@SerializedName`（`exempt`，明文豁免） |
| 同一個 class 混用兩套註解 | **禁止**（MUST NOT，無例外） |

紅線 G1 的 `GsonInstance` 規則不變 —— 它管的是「要用 Gson 時必須用共用實例」，與「新 DTO 用 kotlinx」不衝突。

註：Retrofit 目前只註冊 `KtConverterFactory`（內部包 Gson），kotlinx **沒有接成 converter factory**。新 DTO 用 kotlinx 前，需先確認該 endpoint 的解析路徑（前置基建候選）。

### D-15 one-off event 的出口

**衝突**：4 條規則 MUST NOT 禁止用 Channel / SharedFlow 發 one-off event，但決策點自己承認「開啟外部 App、系統分享、播放音效」無法 reduce 成 state —— MUST NOT 沒留出口，**新程式碼也會卡住**。

**裁決**：預設 events-as-state；**白名單**內的「離開 app 的一次性外部動作」允許用 `Channel(Channel.CONFLATED)`：

- 開啟外部 App / 瀏覽器 / 撥號 / 系統分享
- 系統權限請求
- 播放音效 / 觸覺回饋
- 檔案下載或相機等系統 UI 呼叫

不在白名單內（導航、顯示 snackbar / dialog / toast、欄位驗證錯誤、重試提示）→ **一律 state 欄位 + 消費後回呼清除**。

owner: [08-ui-state.md](08-ui-state.md)。樣板見 `LoginMethodsViewModel.kt`。

### D-16 強度不一致的 13 組

同一件事被定義多次且強度衝突時，一律取**較嚴格**的那個，並只保留一個 id：

| 主題 | 統一後的 id 與強度 | owner |
|------|-----------------|-------|
| `collectAsStateWithLifecycle`（原 5 個 id） | `collect-as-state` · MUST NOT | 09b-compose-state.md |
| one-off event（原 4 個 id，MUST NOT vs SHOULD NOT） | `one-off-event-as-state` · MUST NOT | 08-ui-state.md |
| dispatcher 注入（原 5 個 id，MUST NOT vs SHOULD） | `hardcoded-dispatcher` · MUST NOT | 11-coroutines-flow.md |
| `stateIn(WhileSubscribed)`（原 4 個 id，SHOULD×3 vs MUST×1） | `statein-while-subscribed` · SHOULD | 08-ui-state.md |
| screen/content 兩層拆分（MUST vs SHOULD×2） | `screen-content-split` · SHOULD | 09b-compose-state.md |
| UseCase 單一 invoke（MUST vs SHOULD×2） | `usecase-single-invoke` · SHOULD | 04-domain-layer.md |
| fake 優先於 mock（SHOULD vs MUST） | `prefer-fakes-over-mocks` · SHOULD | 14-testing.md |
| ViewModel 僅畫面層級（4 個 id） | `viewmodel-in-reusable-composable` · MUST NOT | 09b-compose-state.md |
| ViewModel 禁 Android 型別（5 個 id） | `context-in-viewmodel` · MUST NOT | 08-ui-state.md |
| 禁 GlobalScope（3 個 id） | `global-scope` · MUST NOT | 11-coroutines-flow.md |
| Baseline Profile（4 條 / 2 種強度） | `baseline-profile-setup` · SHOULD · migrate | 15-performance.md |
| release 量測效能（2 個 id） | `measure-perf-on-release` · MUST | 15-performance.md |
| version catalog（2 個 id） | `version-catalog-single-source` · MUST | 02-modularization.md |
| model 分層（SHOULD vs MUST） | `dto-in-ui` · MUST NOT | 05-data-layer.md |

---

## 三、不採用與未啟用

### D-17 不採用規則（exempt）：feature `:api` / `:impl` 模組拆分

**約 8 條規則假設專案有 `:feature:x:api` / `:feature:x:impl` 模組結構。本專案沒有。**

本專案是**水平分層**：53 個模組分為 `:app` / `:shared:*`（25）/ `:feature:*`（19）/ `:data:*`（6）/ `:domain:*`（2），沒有任何 feature 的 api/impl 分離。

**這組規則標 `exempt`。** 不標的話 AI agent 會嘗試建立不存在的模組結構 —— 這是最容易讓 agent 產出結構性錯誤的一組。

等價的水平分層規則（這些**有效**）：

- `:domain:*` 不得 import `:data:*` 的實作類別 → `domain-imports-impl`
- feature 模組不得互相依賴 → `no-feature-to-feature-dep`
- 跨模組導航透過 `:shared:routing` 的介面 → `cross-module-navigation`
- 模組依賴一律 `implementation` / `api`，不得 `compileOnly(project(...))` → `no-compile-only-project`

### D-18 不採用：ApiService `internal`

見 [D-11](#d-11-retrofit-apiservice-的可見性)。

### D-19 降級：`org.gradle.configuration-cache=true`

原規則列為 MUST。本專案 53 模組 + KSP + 既有 kapt + `:app` 用 `gradle.startParameter.taskNames` 判斷 variant（configuration cache 的直接阻礙），開啟極可能整個 build 掛。

**裁決**：降為 `migrate`（專案級任務，需獨立驗證）。同一條規則裡的其他 3 個 Gradle flag 維持 MUST。

### D-20 原 dormant 規則的處置（已清空）

準則庫原有 13 條 `enforce: dormant`。**dormant 對開發者等於「這條現在不算數」**，結果是規則存在卻沒有任何指導效果。本次改版把每一條都改成現在就能執行的版本：要嘛降到專案做得到的程度，要嘛寫成「缺基建時的替代做法」，要嘛明確 `exempt` 並附理由。

| 原 dormant 規則 | 處置 | 改寫後 |
|---|---|---|
| Hilt 組（`@InstallIn`、component ↔ scope 對應等） | **不採用**（[D-01](#d-01-依賴注入一律-koin-annotation-風格) / [D-08](#d-08-hilt-組不採用exempt)） | `hilt-module-no-installin`、`hilt-scope-mismatch`：`exempt` + `reason`，md 不保留段落 |
| `di-bridge-outside-app`（Koin→Hilt 橋接邊界） | 改寫為單一容器邊界，永久有效 | `di-container-single-framework` · MUST_NOT · `new-only+on-touch` |
| `koin-module-not-verified` | 啟用（基建只差一行 `koin-test` 依賴） | 同 id · MUST · `new-only` |
| `hardcoded-dispatcher` | 啟用（`KoinConstant` 補三個 dispatcher 常數即可） | 同 id · `new-only+on-touch` |
| `statein-while-subscribed` | 啟用（基建只差一個 `WhileUiSubscribed` 常數） | 同 id · SHOULD · `new-only` |
| Room migration / schema | 改為守門版：既有 `@Entity` 結構變更一律先問；新增獨立 entity 不受限 | `entity-change-no-migration` · MUST · `new-only+on-touch` |
| Compose stability config | 改寫為「預設不標註」的可執行版 | `uistate-stability-default` · `new-only` |
| Compose metrics gate | 改寫為「效能主張必須附量測」 | `perf-claim-without-evidence` · SHOULD · `new-only` |
| Navigation type-safe route | 版本無法動，改寫為字串 route 的正確寫法 | `route-string-convention` · `new-only` |
| Turbine 序列測試 | 改寫為「依賴進來前的手動 collect 寫法」 | `flow-sequence-without-turbine` · `new-only` |
| Compose UI test | 改寫為 `@Preview` 四分支 + Maestro 的替代驗收 | `screen-acceptance-coverage` · `new-only` |
| `force-http1` | 改為圍堵版：不得擴散、既有兩處不得順手清 | 同 id · SHOULD_NOT · `new-only` |

**本次改版後 `rules.yaml` 不應再出現 `enforce: dormant`。** 日後若某條規則缺基建，寫法是「基建那一行寫進規則正文 + 給出缺基建時的替代做法」，不是標 dormant 等它。真的永久不適用才用 `exempt`，且必須填 `reason`。

---

## 四、前置基建

**有 6 條 A 級規則的前置基建在專案裡不存在。** 這些應各自為一個獨立小 PR。**規則本身已經生效**（[D-20](#d-20-原-dormant-規則的處置已清空) 起不再有 `dormant`），基建做完是把規則「加強」到完整版，不是解鎖規則。

| # | 基建 | 解鎖的規則 | 現況 |
|---|------|-----------|------|
| 1 | `DispatcherProvider` 或 Koin `named("io")` / `named("default")` 定義 + application-scope `CoroutineScope` 單例 | `hardcoded-dispatcher` | dispatcher 由 `app/.../di/CoroutinesScopeModule.kt:17-19` 以字面字串 `named("DispatcherIO")` 等提供；`libs/model/.../consts/KoinConstant.kt` 只有 6 個常數、**沒有** dispatcher 常數。基建＝補 `DISPATCHER_MAIN/IO/DEFAULT` 三個常數並把那三行改引用（零風險） |
| 2 | 專案常數 `WhileUiSubscribed = 5_000` | `statein-while-subscribed` | 不存在（`HomeViewModelV2.kt:88-94` 直接寫 5000） |
| 3 | one-off event 標準樣板（state 欄位 + `xxxShown()` + 外部動作白名單機制） | `one-off-event-as-state` | `LoginMethodsViewModel.kt` 可直接抽成樣板 |
| 4 | `:domain:contract` Repository 介面歸屬定案 + 一個示範遷移 | `repository-needs-interface` | 已定案（[D-12](#d-12-repository-介面歸屬)），待示範 |
| 5 | Room `exportSchema = true` + 歷史 schema + `MigrationTestHelper` 樣板 | Room migration 組 | `exportSchema = false`，0 個 migration |
| 6 | Compose stability configuration file + `composeCompiler {}` metrics 開關 | **無 —— 不再阻擋任何規則**：`uistate-stability-default`（新 UiState 不標註）與 `perf-claim-without-evidence`（效能主張須附量測）已是現行規則 | 完全沒有 `composeCompiler {}` DSL；本項降為純基建，與刪除死設定 `kotlinCompilerExtensionVersion` 併為一支 build-logic PR（[90-migration-ledger.md](90-migration-ledger.md) M-25） |

**額外建議基建**（非規則前置，但直接影響準則能否自動化）：

| 基建 | 為什麼 |
|------|-------|
| detekt 套用到所有模組 | 目前**只套用 `:app`**（1/53 模組）→ 其餘 52 個模組沒有任何靜態檢查 |
| Compose 靜態檢查 ruleset | 目前 **0** 條 Compose 規則 → 這正是 modifier 缺失率 89%、`collectAsState` 濫用能長期存在的原因 |
| Android lint 進 CI | 目前 **0** 個 workflow 跑 lint，baseline 有 2776 個未追蹤 issue |
| 模組依賴方向檢查 task | 目前**完全沒有**自動檢查 → 11 條 feature 互依、domain→data 反向依賴都是這樣長出來的 |
| `koin-test` + `module.verify()` | 目前 DI 解析測試只覆蓋 `chatModule` 一個 module |
| Turbine | Flow 序列測試目前只能手動 collect |

---

## 五、待定案（尚無結論）

以下項目研究階段有多個選項但尚未定案，**遇到時先問，不要自行決定**：

| # | 議題 | 選項 | 現況 |
|---|------|------|------|
| P-01 | 統一錯誤模型 | `sealed ApiResult` / `kotlin.Result + ApiException` / 各層自訂 | 4 套並存，兩個同名 `ApiResult` 是陷阱。owner 應在 [05-data-layer.md](05-data-layer.md) 定案 |
| P-02 | Navigation 2 vs 3 | 留在 2.x（需升 2.8+ 才有 type-safe route）/ 評估 navigation3 | 目前 2.7.7，四套導航機制並存 |
| P-03 | 深色模式 | 不支援 / 改造 StyleDictionary 成 theme-aware | 目前架構上不支援（token 是編譯期常數） |
| P-04 | Reductor / RxJava 退場路線圖 | 逐畫面 / 按模組 / 不主動退場 | 752 處 dispatch、194 檔 Rx，需獨立規劃 |
| P-05 | Screenshot test 選型 | Compose Screenshot Testing / Roborazzi / Paparazzi | 目前 0 |
| P-06 | 覆蓋率門檻 | 是否設 `koverVerify` 絕對下限 | 目前只有 codecov 防退步（threshold 0%） |
| P-07 | Kotlin / AGP 升版節奏 | | Kotlin 2.1.0（2024/11 版）、多個依賴停在 2022-2023。**依 AGENTS.md 升版須先確認** |

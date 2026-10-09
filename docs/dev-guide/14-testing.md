# 14 · 測試策略

這份管**測試怎麼寫才算數**：假綠燈防治、fake vs mock、協程測試、各層測什麼、畫面驗收（`@Preview` + Maestro）的定位。

這份**不管** production code 的 dispatcher 注入與 `Thread.sleep`（那是 11），也**不管** UiState / one-off event 該長什麼樣（那是 08 —— 先看完那份，才知道要斷言什麼）。

| 你要找的 | 去哪份 |
|---------|-------|
| production code 的 `CoroutineDispatcher` 注入、`GlobalScope`、coroutine 內 `Thread.sleep` | [11-coroutines-flow.md](11-coroutines-flow.md) |
| UiState 形狀、one-off event、`stateIn` —— 決定斷言什麼的前提 | [08-ui-state.md](08-ui-state.md) |
| Repository 介面歸屬 —— 能不能換成 Fake 的前提 | [05-data-layer.md](05-data-layer.md) |
| Koin 圖驗證測試（`module.verify()`） | [03-di.md](03-di.md) |
| `@Preview` 覆蓋（不算測試，但是 Compose 目前的最低驗收） | [09a-compose-api.md](09a-compose-api.md) |

**依賴現況**：`TestingConvention.kt` 已對所有模組注入 JUnit4 + MockK + AssertJ + `kotlinx-coroutines-test`（`coroutine = 1.8.1`，`backgroundScope` / `UnconfinedTestDispatcher` 可用）。**Turbine / Robolectric / Truth / `androidx.compose.ui.test` 全部未加入依賴，import 一律編譯失敗** —— 以下規則已按「沒有這些工具」寫成現在就能執行的版本，不是等基建的空頭支票。

---

## 一、假綠燈防治（紅線 H1）

### test-no-assert · MUST · new-only+on-touch · lint:test-no-assert

每個 `@Test` 至少要有一個針對**結果**的斷言（`assertThat` / `coVerify` / `awaitItem`）。只呼叫 SUT 而不驗證任何東西的測試一律不收。

✗ `@Test fun \`載入成功\`() = runTest { vm.load() }`
✓ `@Test fun \`載入成功\`() = runTest { vm.load(); advanceUntilIdle(); assertThat(vm.uiState.value.items).hasSize(2) }`

既有違規：0 檔（全庫 252 檔掃描結果，**這點不要退步**）→ [90-migration-ledger.md#m-28](90-migration-ledger.md)

### assert-tautology · MUST_NOT · new-only+on-touch · lint:assert-tautology

禁止恆真斷言：`assertTrue(true)`、`assertEquals(x, x)`、對剛剛自己 stub 進去的常數做斷言。期望值必須獨立於 SUT 的輸入計算出來。

✗ `val s = input.name; assertThat(model.name).isEqualTo(s)` （s 就是餵進去的那個值）
✓ `assertThat(useCase().map { it.faqId }).containsExactly("f1", "f2")`

既有違規：0 處 → [90-migration-ledger.md#m-28](90-migration-ledger.md)

### commented-out-assertion · MUST_NOT · new-only+on-touch · lint:commented-out-assertion

不得把斷言註解掉後留著測試檔。測試壞了就修；暫時修不了就整個 `@Ignore` 並依下一條掛票，不得留下「跑得過但什麼都沒驗」的空殼。

✗ `vm.load()` 後面接 `// assertEquals(2, vm.items.size)`
✓ 修好斷言，或整個測試 `@Ignore("KKAND-1234 …")`

既有違規：5 檔（`MainViewModelTest.kt` 11 行、`MemberPageViewModelTest.kt` 8 行）→ [90-migration-ledger.md#m-28](90-migration-ledger.md)

### ignore-without-ticket · MUST_NOT · new-only · lint:ignore-without-ticket

`@Ignore` 的理由字串必須含 Jira key。把測試檔改名成 `.kt.disabled` 等同無聲刪除，一律禁止 —— 沒有票就直接刪掉測試，不要留殭屍檔。

✗ `@Ignore("Test assertions are commented out")` ／ `ChatRepositoryTest.kt.disabled`
✓ `@Ignore("KKAND-1234 待 Gson 型別修正後恢復")`

既有違規：`@Ignore` 6 處 + `.kt.disabled` 4 檔 → [90-migration-ledger.md#m-28](90-migration-ledger.md)

### relaxed-mock-overuse · SHOULD_NOT · new-only · manual

`mockk(relaxed = true)` 只允許用在**與本次斷言無關的旁支依賴**（tracker、logger、未被驗證的 socket manager）。**本次要驗證的協作對象一律不得 relaxed** —— 未 stub 的呼叫會靜默回傳預設值，測試永遠不會紅。

✗ `val repo: OrderRepository = mockk(relaxed = true)`，然後斷言 `vm.uiState.value.orders`
✓ 旁支：`val socketManager: PresaleChatWebSocketManager = mockk(relaxed = true) { every { observeEvents() } returns emptyFlow() }`；主依賴改手寫 Fake

既有違規：220 處 → [90-migration-ledger.md#m-28](90-migration-ledger.md)

### verify-only-assertion · SHOULD_NOT · new-only · manual

只用 `verify` / `coVerify` 確認「參數有轉發下去」而不斷言回傳值或狀態，是互動測試不是行為測試。至少要有一條斷言看得到 SUT 的輸出。

✗ `coEvery { repository.saveCreditCard(any(), …) } returns null; useCase(…); coVerify { repository.saveCreditCard(…) }`
✓ 同時 `assertThat(useCase(…)).isEqualTo(expected)`

例外：SUT 唯一可觀察的效果就是副作用（送埋點、寫入）時，`verify` 即為結果斷言。
既有違規：`SaveCreditCardUseCaseTest.kt:18-54` → [90-migration-ledger.md#m-28](90-migration-ledger.md)

---

## 二、Test double 與斷言工具

### prefer-fakes-over-mocks · SHOULD · new-only · manual

主要協作對象（Repository、資料來源）優先在測試 sourceSet 手寫 Fake：實作介面、用可設定欄位控制回傳，而不是 mock framework。

✗ `val repo: IPresaleFaqRepository = mockk(relaxed = true)`
✓ `private inner class FakeRepo : IPresaleFaqRepository { var faqsResult: Result<List<PresaleFaqItem>> = Result.failure(NotImplementedError()); override suspend fun fetchOtherFaqs() = faqsResult }`

例外：依賴為 sealed / final 型別而 Fake 成本過高，或該依賴與本次斷言無關時可用 mock。
既有違規：MockK 84 檔 vs 手寫 Fake 約 20 → [90-migration-ledger.md#m-28](90-migration-ledger.md)

### mockito-in-new-test · MUST_NOT · new-only · lint:mockito-in-new-test

新測試不得 import `org.mockito`。專案 mock framework 統一 MockK（Mockito 3.0.0 停在 2019、無 Kotlin 支援）。

✗ `import org.mockito.Mockito.when`
✓ `import io.mockk.coEvery`

既有違規：8 檔 → [90-migration-ledger.md#m-28](90-migration-ledger.md)

### junit-assert-in-new-test · SHOULD_NOT · new-only · lint:junit-assert-in-new-test

新測試不得 import `org.junit.Assert.*`；斷言一律 AssertJ `assertThat`（失敗訊息含實際值、集合斷言可鏈式描述）。JUnit4 的 `@Test` / `@Before` / `@Rule` 不受影響。

✗ `import org.junit.Assert.assertEquals` → `assertEquals(2, list.size)`
✓ `import org.assertj.core.api.Assertions.assertThat` → `assertThat(list).hasSize(2)`

既有違規：`org.junit.Assert` 176 檔 vs AssertJ 38 檔 → [90-migration-ledger.md#m-28](90-migration-ledger.md)

---

## 三、協程與 Flow 測試

### thread-sleep-test · MUST_NOT · new-only+on-touch · lint:thread-sleep-test

（紅線 H2）測試不得 `Thread.sleep()`。等待一律走 `runTest` 虛擬時間：`advanceUntilIdle()` / `runCurrent()` / `advanceTimeBy()`。

✗ `vm.load(); Thread.sleep(500); assertThat(…)`
✓ `vm.load(); advanceUntilIdle(); assertThat(…)`

例外：無。
> production code / coroutine 內的 `Thread.sleep` → [11-coroutines-flow.md](11-coroutines-flow.md)

### runblocking-in-test · MUST_NOT · new-only · lint:runblocking-in-test

測試不得 `runBlocking`（走真實時間，`delay` 真的會等，且無法 `advanceUntilIdle`）。協程測試一律 `runTest { }`。

✗ `@Test fun x() = runBlocking { … }`
✓ `@Test fun \`API 失敗時回傳 null\`() = runTest { … }`

既有違規：19 檔 → [90-migration-ledger.md#m-28](90-migration-ledger.md)

### main-dispatcher-not-replaced · MUST · new-only · manual

測試碰到 `viewModelScope` 或任何 `Dispatchers.Main` 使用者時，必須 `Dispatchers.setMain(testDispatcher)` 並在結束 `resetMain()`；優先直接用專案既有的 `MainDispatcherRule`。

✗ 直接 `PresaleChatViewModel(…)` 後斷言 → `Module with the Main dispatcher had failed to initialize`
✓ `@get:Rule val mainDispatcherRule = MainDispatcherRule()`（`libs/feature/order_page/src/test/java/com/kkday/order_page/MainDispatcherRule.kt`）

例外：完全不涉及 Main dispatcher 的純 UseCase 測試不需要。

### test-dispatcher-not-shared · MUST · new-only · manual

一個測試只能有一個 `TestCoroutineScheduler`。手動建立 `StandardTestDispatcher()` 時必須傳入 `runTest` 的 `testScheduler`，否則 `advanceUntilIdle()` 推不動另一個 dispatcher 上排隊的工作。

✗ `runTest { val d = StandardTestDispatcher(); val repo = Repo(d); advanceUntilIdle() }`
✓ `runTest { val d = StandardTestDispatcher(testScheduler); val repo = Repo(d) }`

例外：整個測試共用 `MainDispatcherRule` 的 dispatcher 時已自動共用 scheduler。
> production code 必須把 dispatcher 開成建構子參數才測得到 → [11-coroutines-flow.md](11-coroutines-flow.md)

### state-value-without-idle · MUST · new-only · manual

斷言 `StateFlow.value` 前必須先讓待執行協程跑完（`advanceUntilIdle()`），或測試中已啟動 collector。否則讀到的只是初始值，測試會恆綠或恆紅。

✗ `vm.onRetry(); assertThat(vm.uiState.value.items).hasSize(2)`
✓ `vm.onRetry(); advanceUntilIdle(); assertThat(vm.uiState.value.items).hasSize(2)`

例外：斷言對象本來就是「初始狀態」時不需要。

### flow-sequence-without-turbine · SHOULD · new-only · manual

驗證**狀態序列**（Loading → Success 的中間態）時，**只斷言 `.value` 不算數** —— `.value` 只讀得到終態，loading 由始至終沒被驗證過，這是假綠燈。序列一律手動起 collector 收下每一次發射；只驗證單一終態時走上一條。

**禁止 `import app.cash.turbine.…`** —— Turbine 未加入依賴，import 會編譯失敗（加依賴屬基建項 → [90-migration-ledger.md#m-28](90-migration-ledger.md)）。

✗ `vm.load(); advanceUntilIdle(); assertThat(vm.uiState.value.isLoading).isFalse()` 後宣稱「驗證了 loading 流程」
✓ 樣板 `app/src/test/java/com/kkday/member/otpauth/viewmodel/OtpRegisterViewModelTest.kt:119`：`val seen = mutableListOf<Boolean>()` → `backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { vm.uiState.collect { seen += it.isLoading } }` → `vm.load(); advanceUntilIdle()` → `assertThat(seen).containsExactly(false, true, false)`（第一筆是訂閱當下的現值，別漏掉）

例外：無。裁決見 [91-decisions.md](91-decisions.md) D-07。

---

## 四、各層測什麼

| 層 | 必測 | 不要測 |
|----|------|-------|
| **UseCase** | 成功 / 空 / 失敗三路徑的**回傳值**、商業規則的邊界條件 | Repository 內部怎麼取資料 |
| **Repository** | DTO→domain mapping 結果、API 失敗轉成哪個 domain error、快取與離線分支 | Retrofit 本身、JSON 反序列化細節 |
| **ViewModel** | 每個公開方法對 **UiState 欄位**的影響、錯誤時的 UiState、event 消費後有被清除 | 內部呼叫了幾次 UseCase（除非那是唯一可觀察效果） |
| **Composable** | 四個 UiState 分支的 `@Preview` + 一支 Maestro flow（見 `screen-acceptance-coverage`） | 狀態轉換邏輯（那是 ViewModel 測的）、重組次數、內部 `remember` |

### usecase-repository-untested · MUST · new-only · manual

（紅線 H3）新增的 UseCase 與 Repository 實作必須附單元測試，至少涵蓋成功與失敗兩條路徑。

✗ 新增 `GetOrderDetailUseCase` 只有實作、沒有對應 `GetOrderDetailUseCaseTest`
✓ 照抄 `libs/feature/presale_chat/src/test/kotlin/com/kkday/feature/presale_chat/usecase/GetPresaleOtherFaqsUseCaseTest.kt`（Fake + `runTest` + AssertJ + 成功/空/失敗三路徑）

例外：純 pass-through UseCase（見 [91-decisions.md](91-decisions.md) D-13）可只測轉發正確性。

### android-framework-in-unit-test · MUST_NOT · new-only · lint:android-framework-in-unit-test

`src/test/` 下不得 import `android.*`（`Uri`、`Bundle`、`TextUtils` 等）。專案沒有 Robolectric，這些會 throw `Method not mocked`，最終逼人用 relaxed mock 蓋掉。

✗ `import android.net.Uri` 後 `mockkStatic(Uri::class)`
✓ 把 Android 相依收斂到 data / UI 層，UseCase 只收純 Kotlin 型別

例外：`androidx.annotation`；`src/androidTest/` 不受此限。
既有違規：6 檔 → [90-migration-ledger.md#m-28](90-migration-ledger.md)

### koin-start-in-unit-test · MUST_NOT · new-only · lint:koin-start-in-unit-test

單元測試不得 `startKoin` 或讓 SUT 走 `KoinComponent` 取依賴。需要起 Koin 才測得動，代表 SUT 用了 service locator —— 先改建構子注入再測。

✗ `@Before fun setUp() { startKoin { modules(appModule) } }`
✓ `val useCase = GetPresaleOtherFaqsUseCase(FakeRepo())`

例外：DI 圖驗證測試（`module.verify()`）→ [03-di.md](03-di.md)。
既有違規：11 檔（含 `B2CApiResponse` 這類 DTO 自帶 `KoinComponent`）→ [90-migration-ledger.md#m-26](90-migration-ledger.md)

---

## 五、畫面驗收、E2E 與命名

### screen-acceptance-coverage · MUST · new-only · manual

新增 Compose 畫面必須同時交出三項驗收，缺一不收：(A) stateless content composable 的 `@Preview` **逐一涵蓋 loading / empty / error / success 四個分支**，不是只有一個 happy path；(B) 一支 Maestro flow（用 `/e2e-create` 產生），mock 檔名與 yaml 同名（見 `e2e-mock-name-mismatch`）；(C) UiState 轉換邏輯的 JVM 單元測試 —— **狀態轉換不要拿 UI test 去測**。

**禁止 `import androidx.compose.ui.test.…`**：`ui-test-junit4` / `ui-test-manifest` 未加入依賴，import 會編譯失敗。`@Preview` + Maestro 是本專案的正式驗收管道，不是等 UI test 就位的暫代品。

✗ 一個 `XxxScreenPreview()` 餵成功假資料就送 PR，沒有 error / empty preview，也沒有 Maestro flow
✓ 四個 `@Preview` + `.maestro/tests/<feature>/xxx.yaml` + `XxxViewModelTest` 覆蓋 loading→success 與 error 兩條路徑

例外：無 loading / error 分支的純導航中介畫面可只留 success preview，需在 PR 說明。

### testtag-mismatch-maestro · MUST · new-only · manual

需要被 E2E 點擊或斷言的 composable 必須加 `Modifier.testTag(...)`，值為 `snake_case`，且**與 Maestro yaml 的 `id:` 完全一致**。順序是先寫 Maestro 腳本、再照腳本的 id 清單補 testTag。

✗ 程式碼 `testTag("sendBtn")` vs yaml `id: "presale_send_button"`
✓ `PresaleInputBar.kt:209` 的 `.testTag("presale_send_button")` ↔ `e2e_presale_m3_join_send_message.yaml:50` 的 `id: "presale_send_button"`

例外：已有穩定可見文字、可用 `text:` 定位的元件不需要 testTag。

### e2e-mock-name-mismatch · MUST · new-only · manual

新增 Maestro flow 時，對應的 Mockoon mock 檔名必須與 yaml **同名**（`<name>.json` + `<name>.scenario.json`），放在 `mockoon/tests/<feature>/`。命名不符會靜默跑到 base-routes 的預設回應。

✗ `.maestro/tests/home/home-pull-refresh.yaml` 配 `mockoon/tests/home/pull_refresh.json`
✓ `mockoon/tests/home/home-pull-refresh.json` + `home-pull-refresh.scenario.json`

例外：純 UI 導航、不打 API 的流程不需要 mock。

### test-name-not-descriptive · SHOULD · new-only · manual

測試函式用中文 backtick 命名，描述「條件 → 預期行為」，不要只寫被測方法名。

✗ `fun testGetFaqs()`
✓ ``fun `API 失敗時回傳 null（讓 ViewModel 保留固定項）`()``

例外：既有 Java 測試檔沿用原命名。

# 15 · 測試

**管**：測什麼、測到哪一層、測試替身（fake vs mock）、測試資料建構、協程與 Flow 的測試寫法、Compose UI 與 screenshot 測試、假綠燈防治、覆蓋率怎麼用。
**不管**：production code 本身的可測性設計（介面抽取、dispatcher 注入）、DI 綁定替換的寫法、共用 fake 該放哪個模組。AGENTS.md 通用紅線 19–20 落在本檔領域，以下是它們可判定的完整定義。

| 想找 | 去 |
|---|---|
| dispatcher 必須注入、ViewModel 不得持有 `Context`（兩者都是可測性前提）| `12-coroutines-flow`（`hardcoded-dispatcher`）、`08-ui-state`（`android-type-in-viewmodel`）|
| Hilt 綁定替換（`@TestInstallIn` 為預設、`@UninstallModules` 只給單一測試特例）、unit test 不得啟 DI 容器 | `03-dependency-injection`（`ad-hoc-test-binding-override`、`di-container-in-unit-test`）|
| 共用 fake 放哪個 source set／模組、DB schema migration 測試 | `02-modularization`（`shared-fake-in-main-source-set`）、`07-persistence`（`untested-migration`）|
| Macrobenchmark、Baseline Profile、效能數字怎麼量 | `16-performance` |

---

## 一、金字塔：測到哪一層

| 受測對象 | 一定要測 | 不要測 | 放哪 |
|---|---|---|---|
| 純函式／mapper／validator／UseCase | 邊界值、null 與空集合的轉換決策、商業規則的每個分支 | 函式庫本身（JSON 有沒有解析成功、DB 有沒有寫進去）、Repository 的實作細節 | `src/test` |
| Repository | 快取／遠端的取捨、錯誤轉換、離線行為 | Retrofit／DAO 的框架行為 | `src/test`（DataSource 用 fake）|
| ViewModel | UiState 的轉移（Loading → Success／Error）、使用者動作的處理 | Composable 長什麼樣 | `src/test` |
| Composable | 點擊 → state → 顯示什麼的行為、無障礙語意 | 像素外觀（交給 screenshot）| `src/test`（Robolectric）|
| DAO migration、WebView、system insets、跨 App | 只有真機成立的行為 | 業務規則分支 | `src/androidTest` |
| 關鍵旅程 E2E | 登入／下單／付款走得通 | 欄位驗證等分支條件 | E2E |

小測試最多、大測試最少，**一律選能給出正確回饋的最低層級**——能在 JVM 用 fake 驗證的不要放 Robolectric，能在 Robolectric 驗證的不要進真機。**不該對 Activity / Fragment / Service 寫 unit test 驗業務邏輯**：若非如此才驗證得到某段規則，代表邏輯放錯層，先搬到 ViewModel 或 UseCase。也不得因為「懶得注入 fake」把測試丟進 `src/androidTest`——那裡只放上表最後兩列的真機行為。

## 二、fake 優於 mock

官方立場是 fake（實作介面的輕量真實實作）優先，官方 sample nowinandroid 完全不用 mocking framework。理由不是風格偏好：**介面演進時 fake 會編譯失敗**，強迫你回頭看測試；mock 不會，它繼續回傳預設值、測試繼續全綠。fake 還能帶狀態（`setOrders()` 後 `observeOrders()` 就會發），測得到 mock 測不到的時序與快取行為。**仍需要 mock 的只有一種場合**：驗證「某個副作用有沒有被觸發」（分析事件是否送出、log 是否寫入）——這類依賴沒有可觀察的回傳值，寫 fake 只是自己數次數。此時用 `verify { }`，且只 stub 真正用到的方法。

## 三、協程、Flow 與 UI 的標準寫法

```kotlin
// 放共用 test 模組，全專案共用一份
class MainDispatcherRule(val testDispatcher: TestDispatcher = UnconfinedTestDispatcher()) : TestWatcher() {
    override fun starting(description: Description) = Dispatchers.setMain(testDispatcher)
    override fun finished(description: Description) = Dispatchers.resetMain()
}

class OrderViewModelTest {
    @get:Rule val mainDispatcherRule = MainDispatcherRule()
    private val orderRepository = FakeOrderRepository()     // fake，不是 mock
    private val viewModel = OrderViewModel(orderRepository)
    @Test
    fun uiState_repositoryReturnsOrders_emitsSuccess() = runTest {
        backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.uiState.collect {} }
        orderRepository.setOrders(listOf(order))
        assertEquals(OrderUiState.Success(listOf(order)), viewModel.uiState.value)
    }
}
```

- **Standard vs Unconfined**：預設 `UnconfinedTestDispatcher()`，讓 `viewModelScope.launch` 立刻跑完，測試最短。要驗證 Loading → Success 的中間狀態或 debounce／timeout 時序時，個案改傳 `StandardTestDispatcher()` 搭配 `advanceUntilIdle()` / `advanceTimeBy()`；兩者可並存但 scheduler 必須同源。
- **Turbine 什麼時候上**：預設用原生工具（`StateFlow` 斷言 `.value`、有限 flow 用 `first()` / `toList()`）；只有要驗證「多個 emission 的先後順序」或「操作與 emission 交錯」時才用 `flow.test { }`——它強制你消費每個事件，能抓到漏掉的中間狀態。
- **Compose 測試**：finder 優先用語意（`onNodeWithText`、`onNodeWithContentDescription`、role），沒有語意可用時才加 `Modifier.testTag`；tag 取共用常數、不得把資料拼進去（`testTag("item_$id")` 是錯的，改用 `hasText` 或父節點 `onChildren()`）。等待一律 `waitUntilExactlyOneExists` 系列；`useUnmergedTree = true` 只在真要抓被合併掉的子節點時用，找不到節點先 `onRoot().printToLog()` 診斷。畫面級 composable 要能吃固定的 `OrderUiState` 與 callback，不得在測試裡連上真實 Repository。
- **Robolectric 的定位**：把上述 UI 行為測試從模擬器搬回 JVM 的工具，不是讓不可測的程式碼通過的工具——需要 `Shadows.shadowOf` 或自訂 `@Implements` 才測得動，代表該重構成可注入的介面；真實渲染精度、`WebView`、window insets 一律改放 `src/androidTest`。

---

## 四、規則

### logic-tested-only-through-ui · MUST · new-only · manual

ViewModel、UseCase、Repository、純工具類別必須有 JVM unit test；不得只用 UI 測試或 E2E 覆蓋業務規則。

✗ 一個功能 PR：0 個 unit test ＋ 6 條 E2E flow 覆蓋所有欄位驗證分支
✓ 8 個 UseCase／ViewModel unit test ＋ 2 個 Compose 行為測試 ＋ 1 條關鍵旅程 E2E

例外：無 · source: https://developer.android.com/training/testing/fundamentals/what-to-test

### test-name-without-condition-expectation · SHOULD · new-only · regex

測試方法名採 `主體_條件_預期` 三段式 lowerCamelCase＋底線，主體已在類別名中就省略；不得出現 `given`／`when`／`then` 字樣。測試類別名為 `{受測類別}Test`，一個類別只對應一個受測類別。

✗ `@Test fun testLogin()` / `@Test fun given_no_data_when_load_then_empty()` / `class UtilsTest`
✓ `@Test fun uiState_apiReturns401_emitsSessionExpired()` / `class DefaultOrderRepositoryTest`

例外：`src/test` 可用 backtick 中文名；`src/androidTest` 一律不得用 backtick（該命名在部分舊版 runtime 會失敗）· source: https://developer.android.com/training/testing/fundamentals

### mock-where-fake-fits · SHOULD · new-only · manual

有介面的依賴（Repository、DataSource、Clock）一律寫 fake 注入；mock 只保留給「驗證副作用是否被觸發」。禁止 spy（`spyk`、`Mockito.spy`）——一半真一半假無法推理，需要控制的部分應抽成可注入依賴。

✗ `val orderRepository = mockk<OrderRepository>(); coEvery { orderRepository.getOrder(any()) } returns order`
✓ `val orderRepository = FakeOrderRepository().apply { setOrders(listOf(order)) }`

例外：`verify { analytics.track(event) }` 這類互動驗證；第三方 final class 且無介面可實作 · source: https://developer.android.com/training/testing/fundamentals/test-doubles

### duplicated-test-fixture-setup · SHOULD · new-only · manual

測試資料由共用 fixture 常數或 builder 產生（放與 fake 同一個測試模組），不得每個測試類別各自組裝一份完整物件。純資料型別（data class、value object、sealed class）一律真實建構，不得 mock。

✗ 每個測試檔各寫一次 `Order("1", "Tokyo", 2, 1200, Instant.parse(...), ...)`；或 `val order = mockk<Order> { every { id } returns "1" }`
✓ `fun testOrder(id: String = "1", total: Int = 1200) = Order(id = id, total = total, ...)` 放 `:core:testing`，測試只覆寫在意的欄位

例外：只有單一測試用得到、且欄位少於三個的資料 · source: 官方 sample nowinandroid

### relaxed-mock · MUST_NOT · new-only · regex

新測試不得使用寬鬆 mock（`mockk(relaxed = true)`、`relaxUnitFun = true`、`RETURNS_DEEP_STUBS`），也不得在模組打開 `unitTests.isReturnDefaultValues = true`。每個被呼叫的方法都必須明確 stub，未 stub 的呼叫要讓測試失敗。

✗ `val orderRepository = mockk<OrderRepository>(relaxed = true)`
✓ `val orderRepository = mockk<OrderRepository>(); coEvery { orderRepository.getOrder("1") } returns order`

例外：無法重構的既有測試維護時個案沿用，不得擴散到新檔案 · source: https://developer.android.com/training/testing/local-tests

### deprecated-coroutine-test-api · MUST · new-only+on-touch · regex

測試 suspend 函式一律用 `runTest`（虛擬時間，`delay` 不會真的等）。不得使用 `runBlocking { }`、`runBlockingTest`、`TestCoroutineDispatcher`、`TestCoroutineScope`。

✗ `@Test fun fetch_success_returnsData() = runBlocking { … }`
✓ `@Test fun fetch_success_returnsData() = runTest { … }`

例外：無 · source: https://developer.android.com/kotlin/coroutines/test

### setmain-without-reset · MUST · new-only · regex

會用到 `viewModelScope` 或 `Dispatchers.Main` 的 local test，必須用共用 `MainDispatcherRule` 設定與還原 main dispatcher；且同一測試內所有 `TestDispatcher` 必須共用同一個 scheduler（rule 的 `testDispatcher`，或 `runTest` 的 `testScheduler`），否則 `advanceUntilIdle()` 推不動另一顆 dispatcher。

✗ `@Before fun setUp() { Dispatchers.setMain(UnconfinedTestDispatcher()) }`（無 `resetMain()`）＋ 依賴另外無參數 `new` 的 `StandardTestDispatcher()`
✓ `@get:Rule val mainDispatcherRule = MainDispatcherRule()`，受測物件注入 `mainDispatcherRule.testDispatcher`

例外：無 · source: https://developer.android.com/kotlin/coroutines/test

### endless-flow-collected-in-test-scope · MUST · new-only · manual

收集不會自行結束的 flow（`StateFlow`、`SharedFlow`、`callbackFlow`）必須 `backgroundScope.launch(UnconfinedTestDispatcher(testScheduler))`；不得用 `this.launch`（`runTest` 會等它結束），也不得對其呼叫 `toList()` / `count()`。

✗ `val all = viewModel.uiState.toList()` / `launch { viewModel.uiState.collect {} }`
✓ `backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.uiState.collect {} }`

例外：有限 flow（一次性查詢、`flowOf`）可直接 `toList()` / `first()` · source: https://developer.android.com/kotlin/flow/test

### statein-asserted-without-collector · MUST · new-only · manual

斷言由 `stateIn(..., WhileSubscribed／Lazily, ...)` 產生的 `StateFlow.value` 前，必須先在 `backgroundScope` 起一個 collector。沒有 collector 上游根本沒啟動，讀到的永遠是初始值——初始值剛好等於期望值時就是假綠燈。

✗ `fakeOrderRepository.setOrders(orders); assertEquals(1, viewModel.uiState.value.count)`
✓ 先 `backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) { viewModel.uiState.collect {} }` 再斷言

例外：`MutableStateFlow` 直接暴露的狀態（無上游訂閱）· source: https://developer.android.com/kotlin/flow/test

### unasserted-await-item · MUST · new-only · regex

Turbine 的每個 `awaitItem()` 回傳值都必須被斷言；不得只呼叫不比對，也不得用 `cancelAndIgnoreRemainingEvents()` 蓋掉未驗證的 emission。

✗ `viewModel.uiState.test { awaitItem(); viewModel.load(); awaitItem() }`
✓ `viewModel.uiState.test { assertEquals(Loading, awaitItem()); viewModel.load(); assertEquals(Success(order), awaitItem()) }`

例外：`awaitComplete()` / `awaitError()` 這類確認終止狀態的呼叫 · source: https://developer.android.com/kotlin/flow/test

### sleep-as-wait-in-ui-test · MUST_NOT · new-only+on-touch · regex

UI 與 E2E 測試不得用固定時間等待（`Thread.sleep`、`SystemClock.sleep`、`delay()`、裸 `CountDownLatch.await()`、E2E 的固定秒數 wait）；一律用條件式等待。固定睡眠在快機器上浪費時間、慢機器上直接失敗，且 Compose 的測試時鐘不會因為 sleep 而前進。

✗ `Thread.sleep(2_000); composeTestRule.onNodeWithText("Done").assertIsDisplayed()`
✓ `composeTestRule.waitUntilExactlyOneExists(hasText("Done"), timeoutMillis = 5_000)`

例外：無 · source: https://developer.android.com/develop/ui/compose/testing/synchronization

### screenshot-baseline-not-verified · MUST · new-only · manual

screenshot 測試的基準圖必須進版控，CI 必須執行 verify／validate 任務（不得執行 record／update，那等於每次重寫基準、永遠不會紅）。設計系統元件的基準至少涵蓋 light／dark 與一組放大字級（`fontScale` ≥ 1.5）。

✗ CI 跑 record／update 任務後直接判定通過
✓ CI 跑 verify／validate 任務；基準更新在本機 review diff 後才 commit

例外：無 · source: https://developer.android.com/studio/preview/compose-screenshot-testing

### test-without-assertion · MUST · new-only+on-touch · manual

每個 `@Test` 至少要有一個真正的斷言（`assert*`、`assertFailsWith`、Turbine 的值比對、或 `verify` 互動驗證）。只呼叫受測方法、只確認「沒 crash」的測試不得提交。

✗ `@Test fun applyCoupon_expired() { validator.apply(expiredCoupon) }`
✓ `@Test fun applyCoupon_expired_returnsExpiredError() { assertEquals(CouponError.Expired, validator.apply(expiredCoupon)) }`

例外：無 · source: 業界共識（假綠燈防治）

### interaction-verified-without-behavior · MUST · new-only+on-touch · manual

依賴有可觀察結果（回傳值、狀態、發出的 flow）時，不得只用 `verify` 確認「有呼叫」就結束——那只證明實作長成現在這樣，重構即紅、行為錯了卻綠。必須斷言受測物件產出的值或狀態；`verify` 只用於本身沒有可觀察結果的副作用依賴。

✗ `viewModel.refresh(); coVerify { orderRepository.getOrders() }`
✓ `viewModel.refresh(); assertEquals(OrderUiState.Success(orders), viewModel.uiState.value)`

例外：受測行為本身就是「是否呼叫外部副作用」（送出分析事件、寫 log、觸發同步排程）· source: 業界共識（假綠燈防治）

### tautological-assertion · MUST_NOT · new-only+on-touch · regex

不得寫恆真斷言：`assertTrue(true)`、`assertEquals(x, x)`、`assertNotNull(<非空常數>)`、`assertTrue(list.size >= 0)`，或對 mock 剛 stub 的回傳值做斷言。期望值必須獨立於受測邏輯寫死。

✗ `every { calculator.total() } returns 210; assertEquals(210, calculator.total())`
✓ `assertEquals(210, calculator.total(listOf(100, 100), taxRate = 0.05))`

例外：無 · source: 業界共識（假綠燈防治）

### swallowed-exception-in-test · MUST_NOT · new-only+on-touch · regex

測試不得用 `try { } catch (e: Exception) { }` 或 `runCatching { }` 吞掉例外（那樣永遠是綠的）。驗證例外用 `assertFailsWith<T>`，並斷言型別與訊息／欄位。

✗ `try { orderRepository.getOrder("unknown") } catch (e: Exception) { }`
✓ `val error = assertFailsWith<OrderNotFoundException> { orderRepository.getOrder("unknown") }; assertEquals("unknown", error.orderId)`

例外：無 · source: 業界共識（假綠燈防治）

### unexplained-ignore · MUST · new-only+on-touch · regex

`@Ignore` 必須附原因與追蹤票號；同一票號拖過一個 release 週期就修好或刪掉該測試。同時不得提交被註解掉的斷言或測試方法——要停用整支測試用具名 `@Ignore`，不要的斷言直接刪。

✗ `@Ignore` / `// assertEquals(OrderUiState.Error, viewModel.uiState.value) // TODO 之後再開`
✓ `@Ignore("ISSUE-4821: 上游 sandbox 尚未提供該端點，SDK 升級後恢復")`

例外：無 · source: 業界共識（假綠燈防治）

### assertion-in-unjoined-coroutine · MUST_NOT · new-only · manual

不得把斷言寫在 `runTest` 內未 `join()` / `await()` 的 `launch { }` / `async { }` 區塊裡——那段可能根本沒跑完，失敗也不會讓測試變紅。斷言要放在測試主體，必要時先 `advanceUntilIdle()` 或 `join()`。

✗ `launch { orderRepository.add(order); assertEquals(listOf(order), orderRepository.all()) }`
✓ `launch { orderRepository.add(order) }; advanceUntilIdle(); assertEquals(listOf(order), orderRepository.all())`

例外：無 · source: https://developer.android.com/kotlin/coroutines/test

### coverage-as-quality-gate · SHOULD_NOT · migrate · manual

覆蓋率只能當「哪裡還沒被測到」的診斷工具，不得作為唯一品質門檻或 KPI（會逼出對 data class 寫 getter 測試這種行為）。報告必須排除 generated code、DI module、純資料類別（DTO／Entity／UiState）與 `@Preview`。

✗ CI 規則：整體覆蓋率 < 80% 就擋 merge
✓ ViewModel／UseCase 設較高目標並定期看未覆蓋清單；UI 與 generated code 排除在報告外

例外：無 · source: 官方 sample nowinandroid

---

## 五、尚無定論（官方未表態，以下是**建議不是規則**，專案內一致即可）

- **斷言函式庫**：官方只說「用可讀的斷言」。建議以 `kotlin.test` 為基準、複雜集合比對搭配一套流暢斷言庫，同一模組不要混用兩套。
- **screenshot 工具**：純 Compose 專案用官方的 Compose 預覽截圖測試最省事；Views 與 Compose 並存時選能同時涵蓋兩者的方案（官方 sample 採用 Roborazzi）。
- **紅燈驗證**：新增或修改測試時，先破壞產品程式碼確認它會失敗，並寫進 PR 描述——這是證明測試有效的最低成本手段。

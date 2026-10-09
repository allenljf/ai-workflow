# 18 · 埋點

**管**：埋點的抽象與注入方式、事件與參數的命名／定義位置、埋點與主流程的隔離、Compose 中的曝光追蹤寫法、埋點的可測性與同意管控。
**不管**：具體埋點 SDK 的設定與初始化（各 SDK 官方文件）、side effect API 的通用選型（`10-compose-state`）、PII 的定義與遮蔽（`17-security`）。

| 相關主題 | 去哪 |
|---|---|
| `LaunchedEffect` / `DisposableEffect` / `SideEffect` 的一般選型與 key 規則 | `10-compose-state` |
| 什麼算 PII、log 遮蔽 | `17-security` |
| `GlobalScope` 禁令、scope 歸屬、`CancellationException` 處理 | `12-coroutines-flow` |
| fake 與 mock 的取捨、測試分層 | `15-testing` |
| 事件該由 ViewModel 還是 UseCase 發出（分層） | `01-architecture` |

---

### analytics-sdk-called-from-ui · MUST · new-only · manual

UI、ViewModel、UseCase 不得直接呼叫埋點 SDK；必須經專案自訂的埋點介面，由 DI 注入。SDK 只在該介面的實作類別中出現一次。

✗ `FirebaseAnalytics.getInstance(context).logEvent("order_submitted", bundle)`
✓ `analyticsHelper.log(AnalyticsEvent.OrderSubmitted(orderId))`（`@Inject constructor(private val analyticsHelper: AnalyticsHelper)`）

例外：埋點介面實作模組本身。 來源：官方 sample nowinandroid

### analytics-sdk-type-leaked · MUST_NOT · new-only · manual

埋點 SDK 的型別（`Bundle`、SDK 的 event/param 類別）不得出現在 feature 模組的任何簽章或 import 中；feature 只依賴埋點抽象模組。

✗ `fun trackOrder(params: Bundle)`
✓ `fun log(event: AnalyticsEvent)`

例外：無。 來源：官方 sample nowinandroid

### analytics-throws-to-caller · MUST_NOT · new-only+on-touch · manual

埋點失敗不得影響業務流程：實作內必須自行捕捉例外並吞掉（僅記錄），不得往呼叫端拋。捕捉時必須先 rethrow `CancellationException`。

✗ `fun log(event: AnalyticsEvent) { sdk.send(event.toPayload()) }`（SDK 可能拋例外）
✓ `try { sdk.send(…) } catch (e: CancellationException) { throw e } catch (e: Exception) { logger.w(e) }`

例外：無。 來源：業界共識

### analytics-blocks-main-flow · MUST_NOT · new-only · manual

主流程不得等待埋點結果：不得 `await` 埋點回傳後才繼續導航或送出表單，不得把埋點放在阻塞的同步路徑上。埋點是 fire-and-forget。

✗ `analytics.logAndAwait(event); navigateToPayment()`
✓ `analytics.log(event); navigateToPayment()`

例外：法遵要求必須確認送達的稽核事件，且已明確標示為非埋點。 來源：業界共識

### analytics-in-composable-body · MUST_NOT · new-only+on-touch · regex

不得在 `@Composable` 函式主體直接呼叫埋點；重組會重複觸發。埋點只能放在事件 lambda（`onClick`）、`LaunchedEffect` 或 `SideEffect` 中。

✗ `@Composable fun OrderScreen(...) { analytics.log(ScreenViewed); … }`
✓ `LaunchedEffect(orderId) { analytics.log(ScreenViewed(orderId)) }`

例外：無。 來源：https://developer.android.com/develop/ui/compose/side-effects

### impression-tracking-with-unit-key · MUST · new-only+on-touch · manual

曝光埋點的 `LaunchedEffect` key 必須是能識別該次曝光的業務值（item id、頁碼、篩選條件），不得用 `Unit`／`true`；否則資料換了不會補送、或同一資料被重覆送。

✗ `LaunchedEffect(Unit) { analytics.log(ItemImpression(item.id)) }`
✓ `LaunchedEffect(item.id) { analytics.log(ItemImpression(item.id)) }`

例外：確實只需在進入畫面時送一次且不隨資料變動的事件，須加註理由。 來源：https://developer.android.com/develop/ui/compose/side-effects

### impression-without-dedup-in-lazy-list · MUST · new-only · manual

`LazyColumn`／`LazyRow` 內的曝光埋點必須跨 item 的 attach/detach 去重：以已送出 id 的集合（記在 ViewModel 或 `rememberSaveable`）過濾，或用 `snapshotFlow(listState) + distinctUntilChanged` 統一在容器層發送。上下捲一次就重送等於灌水。

✗ 每個 item 內 `LaunchedEffect(item.id) { log(impression) }`，回捲再進 viewport 又送一次
✓ `LaunchedEffect(listState) { snapshotFlow { listState.layoutInfo.visibleItemsInfo.map { it.key } }.distinctUntilChanged().collect { keys -> analytics.logNewImpressions(keys) } }`

例外：需求明確要求重複曝光計數時，須在事件命名上區分（`_impression` 對 `_view`）。 來源：https://developer.android.com/develop/ui/compose/side-effects

### state-derived-tracking-without-snapshotflow · SHOULD · new-only · manual

依 Compose 狀態變化觸發的埋點（捲動深度、搜尋輸入、tab 切換）應在 `LaunchedEffect` 內用 `snapshotFlow { }` 搭配 `distinctUntilChanged()`／`debounce()`，不得在 composable body 用 `if` 判斷後直接送。

✗ `if (listState.firstVisibleItemIndex > 10) analytics.log(ScrolledDeep)`
✓ `LaunchedEffect(Unit) { snapshotFlow { listState.firstVisibleItemIndex > 10 }.distinctUntilChanged().filter { it }.collect { analytics.log(ScrolledDeep) } }`

例外：無。 來源：https://developer.android.com/develop/ui/compose/side-effects

### analytics-in-pure-function · MUST_NOT · new-only · manual

埋點不得寫在純函式內：reducer、mapper、UiState 產生器、`init` 的資料轉換。這些會在測試與狀態重放時被重複執行，且讓純函式帶副作用。埋點屬於副作用，放事件處理處。

✗ `fun reduce(state: OrderState, action: Action): OrderState { analytics.log(…); … }`
✓ 在觸發該 action 的 ViewModel 函式中發送

例外：無。 來源：業界共識

### event-name-not-snake-case · MUST · new-only · regex

事件名稱一律小寫 snake_case，格式為 `<物件>_<動作（過去式）>` 或 `<畫面>_<動作>`，只含小寫英數與底線，長度不超過 40 字元，且在專案內唯一。

✗ `analytics.log("OrderSubmitted!")`
✓ `analytics.log("order_submitted")`

例外：埋點平台本身規定的保留事件名（例如 `screen_view`）。 來源：業界共識

### event-definition-scattered · MUST · new-only+on-touch · manual

事件名與參數 key 不得以字面字串寫在呼叫點；必須集中定義為型別（`sealed interface AnalyticsEvent` 的子類別，或 enum／常數集合），呼叫端只傳型別。同一語意的參數在全專案只能有一個 key。

✗ `analytics.log("order_submitted", mapOf("id" to id, "orderId" to id2))`
✓ `analytics.log(AnalyticsEvent.OrderSubmitted(orderId = id))`

例外：無。 來源：官方 sample nowinandroid

### event-param-unbounded-value · SHOULD_NOT · new-only · manual

參數值不應是高基數的自由文字：完整 URL、使用者輸入原文、JSON blob、堆疊追蹤。改送有限集合的列舉值、id 或分桶後的數值。

✗ `SearchPerformed(query = userInput)`
✓ `SearchPerformed(queryLength = userInput.length, hasFilter = true)`

例外：產品明確需要分析搜尋詞，且已通過隱私審查與 `pii-in-event-param`。 來源：業界共識

### pii-in-event-param · MUST_NOT · new-only+on-touch · manual

埋點事件不得攜帶 PII：email、電話、姓名、地址、身分證號、卡號、精確座標、原始 device id。需要識別使用者時只送後端配發的匿名 id。PII 的完整定義見 `17-security`。

✗ `UserLoggedIn(email = user.email)`
✓ `UserLoggedIn(userId = user.anonymousId)`

例外：無。 來源：https://developer.android.com/privacy-and-security/security-tips

### analytics-without-consent-gate · MUST · new-only · manual

需使用者同意才能蒐集的事件，必須在取得同意前完全不送出（不是先存再補送）；同意狀態必須是埋點實作的單一判斷點，不得由各呼叫端自行檢查。

✗ 每個呼叫點各寫 `if (hasConsent) analytics.log(…)`
✓ 埋點實作內統一判斷同意狀態，未同意即丟棄

例外：法規允許的必要營運事件（例如崩潰統計），須明確標示分類。 來源：業界共識

### analytics-untested · SHOULD · new-only · manual

關鍵埋點必須有測試：注入記錄事件的 fake 實作，斷言「送出的事件型別與參數」以及「不該送時沒送」。不得以 mock 靜態 SDK 方法或人工看 log 作為唯一驗證。

✗ 只在 debug build 用眼睛看 logcat 確認
✓ `viewModel.submit()` 後斷言 `fakeAnalytics.events == listOf(AnalyticsEvent.OrderSubmitted("A1"))`

例外：純曝光時序類埋點可只做手動驗證，但須在 PR 說明如何驗的。 來源：官方 sample nowinandroid

### debug-events-sent-to-production-dataset · SHOULD · new-only · manual

debug 與測試 build 產生的事件不得混入正式資料集；以 build variant 切換埋點實作（debug 走 no-op 或除錯用實作），或帶上環境標記由平台端過濾。

✗ 所有 variant 共用同一組正式埋點設定
✓ debug variant 綁定 `NoOpAnalyticsHelper` 或除錯專用的 dataset

例外：需要驗證埋點串接的專用 QA variant。 來源：業界共識

---

## 尚無定論（建議，非規則）

- **事件該從哪一層發**：官方無定論。建議「使用者互動事件」由 ViewModel 發（它知道畫面語境），「業務結果事件」（付款成功、訂單成立）由 UseCase 發（它知道結果，且多入口共用）。不要兩層都發同一事件。
- **共通參數（session、語系、實驗分組）怎麼帶**：建議由埋點實作統一附加，不要求每個呼叫點自己組；呼叫端只負責事件專屬參數。
- **曝光的「有效曝光」定義**（可見比例、停留時間門檻）：無官方標準。建議由資料端統一定義一次（例如可見 50% 且停留 1 秒），寫進埋點抽象，不要各畫面各自實作。
- **A/B 實驗分組資訊**：建議以共通參數方式附加，並確保分組來源與實驗平台一致；不要在 UI 層各自推導分組。

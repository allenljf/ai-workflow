# 16 · 埋點（KKTracker / KTM / AXIS PIN）

這份管 **埋點的定義與送出**：KKTracker 事件名稱怎麼組、property 型別怎麼配、自訂事件走哪個 API、埋點該寫在哪一層、Compose 曝光怎麼防重複觸發、AXIS PIN 何時要同步。

這份**不管** composable 副作用 API 的挑選（那是 09b），也**不管** log 與 release build 的個資遮蔽（那是 18）。

| 你要找的 | 去哪份 |
|---------|-------|
| composable 主體不得送埋點、effect key 完整性、`rememberUpdatedState` | [09b-compose-state.md](09b-compose-state.md) |
| ViewModel 不得往下傳給可重用 composable（含只為了埋點） | [09b-compose-state.md](09b-compose-state.md) |
| Composable 內禁止 `by inject()`，只允許 `koinViewModel()` | [03-di.md](03-di.md) |
| `LazyColumn` / `LazyRow` 的 `items` 必須有 `key` | [10-compose-performance.md](10-compose-performance.md) |
| log 不得輸出個資、release 不得輸出完整 body | [18-security.md](18-security.md) |
| `GlobalScope` 禁令 | [11-coroutines-flow.md](11-coroutines-flow.md) |
| 新畫面不得寫 Reductor reducer（紅線 D4） | [08-ui-state.md](08-ui-state.md) |

> **前提事實**：`KKBuildConfig.DEBUG` 恆為 `false`（`KKBuildConfig.kt:4-6`，`setDebugMode` 內容被註解掉），所以 KKTracker 內建的空值 / 型別 / 重複事件檢查**永遠不會拋例外、也不會 log**。埋點寫錯的唯一症狀是「資料團隊看不到事件」。以下規則全部要靠人與 review 把關。

---

## 一、事件定義（KKTracker）

事件名稱由 `Event.getEventName()` 組出 —— `type.value` + `page.value` + `component.value`（或 `type` + `behavior` + `result`），以 `_` 串接、空字串濾掉。事件定義放 `libs/base/src/main/java/com/kkday/library/common/tracker/kktracker/collection/`。

### event-not-registered · MUST · new-only · manual

新事件必須先在對應的 `IEventCollection.getEvents()` 註冊，且該 collection 必須列在 `KKTrackTool.eventListCollection`。沒註冊時 `KKEventTracker.filterEvent()` 回 `null`，事件靜默不送。

✗ ViewModel 直接 `setName(EventType.CLICK, EventPage.LOYALTY_PG, EventComponent.BTN, "…").trackEvent()`，collection 內查無此組合
✓ 先加 `Event(EventType.CLICK, EventPage.LOYALTY_PG, EventComponent.BTN, listOf(EventProperty.POSITION), "Click_LoyaltyPg_Btn")`

例外：`logRawEvent` 的自訂事件不經過 collection，見 `custom-event-via-enum`。

### event-name-from-hint · MUST NOT · new-only+on-touch · manual

`setName(type, page, component, hint)` 的 `hint` **完全不參與**名稱組成（`KKEventTracker.setName` 收下後直接丟棄），只是給人看的註記。實際名稱必須照 enum 的 `value` 推算，並讓 hint 與它逐字相同。

✗ `EventPage.EXPRESS_PASS_FILTER`（value = `ExpressPassFilterPg`）配 hint `"Click_ExpressPassFilter_Options"` → 實際送出 `Click_ExpressPassFilterPg_Options`
✓ hint 寫 `"Click_ExpressPassFilterPg_Options"`；要改事件名一律改 enum 的 `value`

例外：無。
既有違規：13 / 294 個註冊事件的 hint 與實際名稱不符（`CommodityCollection.kt`、`BookingSuccessEventCollection.kt` 最多）

### duplicate-event-name · MUST NOT · new-only · manual

同一組 (type, page, component) 或 (type, behavior, result) 只能註冊一個 `Event`。重複時 `filterEvent()` 只取第一個，後註冊那組的 properties 永遠送不出去。

✗ `BookingSuccessEventCollection.kt:21,30` 兩個 `VIEW + BOOKING_SUCCESS_PG + EMPTY`，只差在 hint
✓ 真要區分就補不同的 `EventComponent`（`PROMO_BANNER` / `PROMO_BTN`），讓名稱真的不同

例外：無。

---

## 二、事件屬性

### array-property-not-list · MUST · new-only+on-touch · manual

`valueType` 是 `ValueType.ARRAY` 的 property 只能用 `addProperty(prop, List<*>)` 多載。傳 `String` 會被 `BaseTracker.checkPropertyValueTypeIsWrong` 判定型別錯誤，但檢查恆關 → 靜默送出錯型別。`PROD_MID`、`PKG_OID`、`PROD_TAG_CODE` 都是 ARRAY。

✗ `.addProperty(EventProperty.PROD_MID, plusProperties[key].toString())`（`OrderDetailViewModel.kt:662-665`）
✓ `.addProperty(EventProperty.PROD_MID, listOf(productId))`

例外：無。加 property 前先看 `EventProperty` 該項宣告的 `valueType`。

### empty-property-value · MUST NOT · new-only+on-touch · manual

不得傳 `null`、空字串或空 `List` 給 `addProperty`。`PropertyValue.getValue()` 對空值回 `null`，整個 property 會被丟掉（不是送出空值）。沒值就不要加這個 property。

✗ `.addProperty(EventProperty.SESSION_OID, sessionOid ?: "")`
✓ `sessionOid?.let { builder.addProperty(EventProperty.SESSION_OID, it) }`

例外：無。

### property-not-in-event · MUST · new-only · manual

`addProperty` 用到的 property 必須列在該 `Event` 的 `properties` 清單內 —— `filterProperties()` 以 `Event.properties` 為白名單過濾，沒列到的一律丟棄。

✗ Event 宣告 `listOf(EventProperty.PROD_MID)`，呼叫端多加 `.addProperty(EventProperty.POSITION, "$index")` → position 不會送出
✓ 先在 collection 的該 `Event` 補上 `EventProperty.POSITION`，再於呼叫端 `addProperty`

例外：無。

### pii-in-tracking-property · MUST NOT · new-only+on-touch · manual

埋點屬性與 `logRawEvent` 的 map 不得帶個資：email、電話、姓名、證件號、生日、地址、完整卡號、原始 token。使用者身分由 `KKTrackTool.login(userId)` 的 Mixpanel identify 負責，事件屬性只送後端發放的去識別 id。

✗ `logRawEvent("presale_message_sent", mapOf("email" to user.email, "phone" to user.phone))`
✓ `logRawEvent("presale_message_sent", mapOf("session_oid" to sessionOid))`

例外：無。要新增帶個資的 property 前先問 PM／法務。
> log 與 release build 的遮蔽規則見 [18-security.md](18-security.md)

---

## 三、送出方式與呼叫位置

### custom-event-via-enum · MUST NOT · new-only · manual

事件名稱無法由 enum 組出（snake_case、Web 傳來的名稱）時，用 `KKTrackTool.shared().logRawEvent(name, Map<String, String>)`。不得為了湊名稱在 `EventPage` / `EventComponent` 塞一次性 enum，也不得改用 `IAutoPageTracker.trackEvent(name, map)`（那是 auto page tracking 與 KTM 備援專用）。

✗ 在 `EventComponent` 新增 `PRESALE_SESSION_CREATED { value = "presale_session_created" }`
✓ `KKTrackTool.shared().logRawEvent("presale_session_created", mapOf("sessionable_type" to type))`（`PresaleChatViewModel.kt:414-417`）

例外：無。

### tracker-builder-no-scope · MUST NOT · new-only+on-touch · lint:tracker-builder-no-scope

不得呼叫無參數的 `eventBuilder()` / `superEventBuilder()` / `userBuilder()` —— 這三個多載內部用 `GlobalScope`（`KKTracker.kt:49,57,65`，違反紅線 F2）。一律傳入呼叫端自己的 scope。

✗ `kkTrackTool.eventBuilder().setName(…).trackEvent()`
✓ `kkTrackTool.eventBuilder(viewModelScope).setName(…).trackEvent()`

例外：確實沒有 scope 可用的 Application 初始化流程，需在該行註明理由。
既有違規：239 處 / 63 檔

### tracker-singleton-access · SHOULD NOT · new-only · lint:tracker-singleton-access

新程式碼不得在 ViewModel / UseCase / Repository 內呼叫 `KKTrackTool.shared()`。Koin 已有 `single { KKTrackTool.shared() }`（`KKTrackerModule.kt:7`），一律建構子注入。

✗ `class OrderViewModel { fun onClick() { KKTrackTool.shared().eventBuilder(viewModelScope)… } }`
✓ `class OrderViewModel(private val kkTrackTool: KKTrackTool)`（`OrderDetailViewModel.kt:112`）

例外：DI module 內的綁定本身；非 DI 管理的 `BaseParser` 子類。
既有違規：112 處 / 35 檔
> Composable 內取依賴的白名單見 [03-di.md](03-di.md)

### tracking-in-reducer · MUST NOT · new-only+on-touch · manual

Reductor 的 `@AutoReducer.Action` 函式必須是純函式，不得在 reduce 內送埋點。埋點放在觸發該 action 的 ViewModel / Presenter 事件方法。

✗ `LoginReducer.kt:75-105` 的 `viewReady()` 內連續 `KKTrackTool.shared().eventBuilder().setName(…).trackEvent()`
✓ ViewModel `fun onLoginPageShown() { kkTrackTool.eventBuilder(viewModelScope).setName(…).trackEvent() }`

例外：無。reduce 可能被重放或在測試中重複呼叫，埋點會跟著多送。
既有違規：13 個 reducer 檔 → [90-migration-ledger.md#m-01](90-migration-ledger.md)
> composable 主體內送埋點的禁令見 [09b-compose-state.md](09b-compose-state.md)

### tracking-blocks-main-flow · MUST NOT · new-only+on-touch · manual

主流程不得依賴埋點：不得因取不到埋點參數就 `return` 中止業務、不得把埋點呼叫放進業務的 `try` 區塊（讓埋點例外被當成業務失敗）、不得用埋點結果決定後續流程。

✗ `suspend fun submit() { val p = getTrackerParams() ?: return; api.submit(); track(p) }`
✓ `suspend fun submit() { api.submit(); getTrackerParams()?.let { track(it) } }`

例外：無。

### duplicate-mixpanel-event · MUST NOT · new-only · manual

同一個使用者行為不得同時走 KKTracker 與 `KTMTracker.trackEvent(isMixpanelAllowed = true)` —— 後者會再以 `KKTrackTool.shared().trackEvent()` 補送一次 Mixpanel（`KTMTrackerImpl.kt:360-381`），造成重複計數。

✗ 同一次點擊先 `eventBuilder(viewModelScope)…trackEvent()`，再 `ktmTracker.trackEvent(…, isMixpanelAllowed = true)`
✓ 二選一：只送 KTM 並帶 `isMixpanelAllowed = true`，或只送 KKTracker

例外：資料團隊要求雙軌比對期間，需在 PR 說明並註記移除時機。

---

## 四、Compose 曝光追蹤

### impression-on-recomposition · MUST NOT · new-only+on-touch · manual

不得把重組次數或 composable 進入組合當作曝光訊號 —— 重組、Lazy 回收、設定變更都會重跑，曝光數必然膨脹。元件曝光一律用 `Modifier.onFirstVisible(...)`（`androidx.compose.ui.layout`）並設定 `minFractionVisible`。

✗ `@Composable fun ProductCard(p: Product) { LaunchedEffect(Unit) { onImpression(p.id) }; … }`
✓ `Modifier.onFirstVisible(minFractionVisible = 0.8f) { onImpression(p.id) }`（`OrderCardExpView.kt:116-119`）

例外：整頁 PV 由畫面層送一次即可。
> effect key 該怎麼挑見 [09b-compose-state.md](09b-compose-state.md)

### lazy-impression-no-scope-id · MUST · new-only+on-touch · manual

`LazyColumn` / `LazyRow` / `LazyVerticalGrid` 內的曝光必須用 `Modifier.onFirstVisibleInLazy(scopeId = …)`（`com.kkday.kktracker.impressiontracker`），不得用裸 `onFirstVisible` —— 虛擬化會讓同一 item 反覆 attach/detach，裸版每次重新進入畫面都再觸發一次。

✗ `items(products, key = { it.id }) { Card(Modifier.onFirstVisible { track(it.id) }) }`
✓ `Card(Modifier.onFirstVisibleInLazy(scopeId = "search_result_prod_${it.id}", minFractionVisible = 0.8f) { track(it.id) })`

例外：非 Lazy 容器（`Column` / `Box`）用 `onFirstVisible` 即可。

### impression-scope-id-by-index · MUST NOT · new-only+on-touch · manual

`scopeId` 是 `LazyFirstVisibleManager` 這個**全域** map 的去重鍵，必須是「畫面或區塊前綴 + 穩定業務 id」。用清單位置當 id，分頁載入、排序或篩選後會把不同項目誤判成已曝光；不加前綴則會跨畫面互相蓋掉。

✗ `scopeId = "item_$index"`
✓ `scopeId = "search_result_prod_${product.id}"`

例外：本來就唯一且不會重排的單一元件（banner、error 區塊）可用固定字串。

### impression-snapshotflow-no-distinct · MUST · new-only · manual

以捲動狀態自行計算曝光時，`snapshotFlow` 必須放在 `LaunchedEffect(listState)` 內並接 `distinctUntilChanged()`（或自訂比較），再 `collect` 送埋點。直接 `collect { track() }` 會在每次 layout 變動都送一次。

✗ `LaunchedEffect(Unit) { snapshotFlow { listState.firstVisibleItemIndex }.collect { track(it) } }`
✓ `LaunchedEffect(listState) { snapshotFlow { listState.layoutInfo }.distinctUntilChanged { a, b -> a.visibleItemsInfo.map { it.index } == b.visibleItemsInfo.map { it.index } }.collect { … } }`（`HomeScreen.kt:533-537`）

例外：能用 `onFirstVisibleInLazy` 表達的情境優先用它，不要自己接 `snapshotFlow`。

---

## 五、AXIS PIN

### pin-card-out-of-sync · MUST · new-only+on-touch · manual

下列變更必須在同一個 PR 同步 `axis/pins/{domain}/{feature}.yaml` 與 `axis/pins.md`：新增或改名 Screen / Fragment / Activity（`android.screen`、`android.path`）、增減 API 呼叫（`api`）、增減 data model（`data.android_models`）、搬移檔案路徑。收尾跑 `/axis-sync`。

✗ 把 `LoyaltyCenterScreen` 搬到新模組，`axis/pins/loyalty/center.yaml` 的 `android.path` 仍指舊路徑
✓ 同步更新 `android.path`、`api`（格式 `- method: GET` / `path: v3/member/points` / `service: IMemberApiService#getMemberPointsV3`）與 `pins.md`

例外：不需要建 PIN 的變更見 `pin-for-component`。

### pin-naming-invalid · MUST · new-only · manual

PIN 格式 `domain.feature.view`：全小寫、`.` 分隔三段、段內單詞用 `_` 連接；`domain` 必須是 `axis/RULES.md` 現有 18 個之一，要開新 domain 得先更新 RULES.md 並建 `axis/pins/{domain}/` 目錄。`ued` 欄位填 UED 埋點文件的 Page naming（PascalCase）。

✗ `pin: Loyalty.compareMain` ／ `pin: loyalty.compare`
✓ `pin: loyalty.compare.main` + `ued: LoyaltyComparePg`

例外：無。

### pin-for-component · MUST NOT · new-only · manual

純 UI 元件（按鈕、卡片、清單 item）、base class、demo 頁不得建 PIN。BottomSheet / Dialog 只有在 UED 有獨立 Page naming 時才建。

✗ 為 `KKProductCard` 建 `prod.card.main`
✓ 該卡片的曝光／點擊埋點掛在它所在頁面的 PIN 底下

例外：無。

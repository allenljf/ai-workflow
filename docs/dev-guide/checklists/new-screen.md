# Checklist · 新畫面／新頁面

**先確認這真的是「新畫面」**（判定表見 [91-decisions.md](../91-decisions.md) D-03）：

| 情況 | 走哪份 |
|------|-------|
| 新 navigation destination、新全螢幕內容（Activity / Fragment / dialog / bottom sheet） | **這份** |
| 既有 Fragment 內加一個區塊 | 改走 [17-interop-views-compose.md](../17-interop-views-compose.md) |
| 既有 RecyclerView 加一種 item type | 改走 [17-interop-views-compose.md](../17-interop-views-compose.md)（不得新增 Epoxy model） |

## 動工前

- [ ] 已讀 `00-red-lines.md` + `08-ui-state.md` + `09a-compose-api.md` + `09b-compose-state.md` + `13-designsystem.md`
- [ ] Figma 已讀，每個間距/顏色/圓角/字級都找到對應 `StyleDictionary.kkXxx` token
- [ ] **找不到對應 token 的已向使用者提問**，沒有自行決定數值（紅線 B3）
- [ ] 畫面要顯示的所有文案已確認來源（string resource？API 回傳？）
- [ ] 確認畫面進入點與導航方式 → 跨模組時跑 `/guide-navigation`

## 結構

- [ ] 畫面拆成 stateful `XxxScreen`（收 ViewModel）+ stateless `XxxContent`（只收 value 與 lambda） — `screen-content-split`
- [ ] stateless 那層可以獨立 `@Preview`（不需要 ViewModel）
- [ ] 可重用 composable 有 `modifier: Modifier = Modifier`，位置在必填參數之後 — `compose-modifier-missing`
- [ ] 參數傳 value 不傳 `State<T>`（不要把 State 型別洩漏進 API）
- [ ] ViewModel 沒有被傳進可重用 composable — `viewmodel-in-reusable-composable`
- [ ] Composable 內沒有 `by inject()`（要 ViewModel 用 `koinViewModel()`）

## 狀態

- [ ] ViewModel 暴露單一 `StateFlow<XxxUiState>`（不是散成 10 個 flow）
- [ ] `UiState` 是不可變 `data class`，集合欄位用 `List` 不用 `MutableList` — `mutable-collection-in-state`
- [ ] 沒有對外暴露 Mutable 型別 — `mutable-state-exposed`
- [ ] loading / error / empty 狀態有明確表達（不是靠 null 判斷）
- [ ] 用 `collectAsStateWithLifecycle()` — `collect-as-state`
- [ ] one-off event 用 state 欄位 + 消費後回呼清除（樣板：`LoginMethodsViewModel`）
- [ ] 需要跨 process death 保留的狀態有用 `SavedStateHandle`
- [ ] ViewModel 沒有持有 `Context` / `NavController` — `context-in-viewmodel`

## 副作用

- [ ] side effect 用對 API（`LaunchedEffect` / `DisposableEffect` / `produceState` / `snapshotFlow`）— 判斷樹見 `09b-compose-state.md`
- [ ] `LaunchedEffect` 的 key 正確（不是無腦 `Unit`）
- [ ] composition 內沒有 I/O、網路、DB 存取或重運算 — `composable-heavy-work`
- [ ] `derivedStateOf` 只用在「衍生值變動頻率遠低於來源」的情況（不是單純讀欄位）

## 設計系統

- [ ] 沒有任何 hardcode 的 `.dp` / `.sp` / `Color(0x...)` / `RoundedCornerShape(數字)` — `hardcoded-dimen` / `hardcoded-color` / `hardcoded-shape`
- [ ] 字型用 `com.kkday.design.font` 的 token，不是自組 `TextStyle`
- [ ] 優先使用設計系統既有的 `KK*` 元件，沒有重造輪子
- [ ] 硬編碼字串有加 `// TODO: replace with stringResource - <說明>` — `hardcoded-chinese-string`
- [ ] 沒有修改 `libs/app_resource/.../strings.xml`（紅線 A2）
- [ ] 用 Material3，沒有新增 M2 或 Accompanist import — `no-new-material2` / `no-new-accompanist`

## 清單

- [ ] `LazyColumn` / `LazyRow` 的 `items` 有穩定的 `key`（不是 index） — `lazy-list-no-key`
- [ ] Paging 用 `LazyPagingItems` 的 `itemKey`
- [ ] item 有明確尺寸或 `contentType`

## 導航

- [ ] 跨模組導航透過 `:shared:routing` 的 `XxxRouter` 介面 + `XxxRoutingInput`，沒有直接依賴目標 feature 模組
- [ ] `NavController` 沒有被傳進深層 composable（用 lambda 上拋）
- [ ] 參數只傳 id，不傳整個物件

## 預覽與測試

- [ ] stateless composable 有 `@Preview`，涵蓋 loading / error / empty / 正常至少 2 種
- [ ] ViewModel 有單元測試，涵蓋 loading → success 與錯誤路徑
- [ ] 每個 `@Test` 有真斷言 — `test-no-assert`
- [ ] 若有 E2E：`Modifier.testTag` 值與 Maestro 腳本的 `id:` 完全一致

## 埋點

- [ ] 曝光埋點沒有寫在 composition 內（會隨重組重複觸發），做法見 `16-tracking.md`
- [ ] PIN 已同步（跑 `/axis-sync`）

## 收尾

- [ ] 編譯 + detekt + 測試通過
- [ ] 跑過 `/guide-audit` 且必修項為 0

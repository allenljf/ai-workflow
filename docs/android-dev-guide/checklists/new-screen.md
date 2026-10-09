# Checklist · 新畫面

只加一個區塊到既有畫面時不用走這份 —— 那是既有畫面的修改，走 [refactor.md](refactor.md)。

## 動工前

- [ ] 已讀 `guides/08-ui-state.md` + `09-compose-api.md` + `10-compose-state.md` + `14-design-system.md`
- [ ] 設計稿已看過，每個間距／顏色／圓角／字級都找得到對應的設計系統 token
- [ ] **找不到對應 token 的已提出討論**，沒有自行決定數值
- [ ] 畫面的所有狀態已列出：loading / empty / error / success，以及各自要顯示什麼
- [ ] 進入這個畫面的路徑與參數已確定 → `guides/13-navigation.md`

## 結構

- [ ] 兩層拆分：`XxxScreen`（收 ViewModel、collect state）+ `XxxContent`（只收 value 與 lambda）
- [ ] `XxxContent` 不認識 ViewModel，可以獨立 `@Preview`
- [ ] 可重用的子元件有 `modifier: Modifier = Modifier`，位置在必填參數之後、其他選填之前
- [ ] 參數傳值不傳 `State<T>`（不要把 State 型別洩漏進 API）
- [ ] ViewModel 沒有被傳進子 composable
- [ ] 事件以 lambda 上拋（`onRetry: () -> Unit`），不是把 ViewModel 傳下去

## 狀態

- [ ] 單一 `XxxUiState` data class，欄位全 `val`
- [ ] 集合欄位用唯讀 `List` / `Map`，不是 `MutableList`
- [ ] loading / error / empty 有明確表達，不是靠 null 判斷
- [ ] 沒有對外暴露 Mutable 型別
- [ ] 用 `collectAsStateWithLifecycle()`
- [ ] one-off event（導航、snackbar、dialog）用 state 欄位 + 消費後回呼清除
- [ ] 需要跨設定變更保留的用 `rememberSaveable`；跨 process death 的用 `SavedStateHandle`
- [ ] 畫面資料由 ViewModel 持有，沒有存在 `remember` 裡

## 副作用

- [ ] side effect 用對 API（判斷樹見 `guides/10-compose-state.md`）
- [ ] `LaunchedEffect` 的 key 正確（不是無腦 `Unit`）
- [ ] 需要在離開時清理的用 `DisposableEffect`
- [ ] composition 內沒有 I/O、網路、DB 存取或重運算
- [ ] `derivedStateOf` 只用在「衍生值變動頻率遠低於來源」的情況

## 設計系統

- [ ] 沒有 hardcode 的尺寸／顏色／圓角／字級
- [ ] 字型用設計系統的 typography token，不是自組 `TextStyle`
- [ ] 優先使用設計系統既有元件，沒有重造輪子
- [ ] 使用者可見文案全部來自字串資源
- [ ] 複數與參數化文案用 `plurals` / 格式化參數，不是字串拼接
- [ ] 深色模式下顯示正常（若專案支援）

## 清單

- [ ] `items` 有穩定的 `key`（不是 index）
- [ ] Paging 用 `LazyPagingItems` 的 `itemKey`
- [ ] 非同步載入的 item 有指定尺寸（避免首次量測為 0 導致整份清單被組合）

## 導航

- [ ] route 用 type-safe 的 `@Serializable` class（Navigation 2.8+）
- [ ] 參數只傳 id，不傳整包物件
- [ ] `NavController` 沒有被傳進深層 composable
- [ ] ViewModel 沒有持有 `NavController`
- [ ] 跨模組導航沒有直接依賴目標 feature 模組

## 無障礙

- [ ] 圖片與圖示有 `contentDescription`（純裝飾的明確設 `null`）
- [ ] 可點擊區域至少 48dp
- [ ] 文字在字型放大時不會截斷或重疊

## 測試

- [ ] ViewModel 有測試，涵蓋 loading → success 與錯誤路徑
- [ ] `XxxContent` 的 `@Preview` 涵蓋 loading / empty / error / success 四種
- [ ] Compose UI test 驗證關鍵互動（若專案有此依賴）
- [ ] 每個 `@Test` 有真斷言

## 收尾

- [ ] 編譯 + 測試 + 靜態檢查通過
- [ ] `python3 android-dev-guide/tools/check-rules.py` 無必修項

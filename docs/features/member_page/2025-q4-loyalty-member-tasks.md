# 2025 Q4 Loyalty — 會員頁（我的）規格與任務

- **需求與設計**：見 [2025-q4-loyalty-spec.md](2025-q4-loyalty-spec.md) 二、會員頁。
- **本文件**：舊架構整理、新頁面共識、開發流程、後續任務細分與估時。

---

## 一、Figma 連結（會員頁）

| 項目                | 說明                | Figma                                                                                                              | nodeId (MCP) |
|-------------------|-------------------|--------------------------------------------------------------------------------------------------------------------|--------------|
| 說明                | 會員頁互動與主要頁面框架      | [5906-16571](https://www.figma.com/design/lhlUGHS1963vcOg9iKjnYl/2025-q4-Loyalty-program?node-id=5906-16571&m=dev) | 5906:16571   |
| 未登入時              | 會員頁未登入狀態          | [5571-38118](https://www.figma.com/design/lhlUGHS1963vcOg9iKjnYl/2025-q4-Loyalty-program?node-id=5571-38118&m=dev) | 5571:38118   |
| 已登入               | 會員頁已登入狀態          | [5342-28822](https://www.figma.com/design/lhlUGHS1963vcOg9iKjnYl/2025-q4-Loyalty-program?node-id=5342-28822&m=dev) | 5342:28822   |
| 會員資料區             | 頭像、等級、點數等         | [5914-38031](https://www.figma.com/design/lhlUGHS1963vcOg9iKjnYl/2025-q4-Loyalty-program?node-id=5914-38031&m=dev) | 5914:38031   |
| menu 區            | 設定、優惠券、任務等選單      | [5914-43779](https://www.figma.com/design/lhlUGHS1963vcOg9iKjnYl/2025-q4-Loyalty-program?node-id=5914-43779&m=dev) | 5914:43779   |
| 瀑布流區塊             | 底部瀑布流與 Sticky     | [5914-46813](https://www.figma.com/design/lhlUGHS1963vcOg9iKjnYl/2025-q4-Loyalty-program?node-id=5914-46813&m=dev) | 5914:46813   |
| Header 收合效果（參考 1） | 收合互動設計            | [5906-35908](https://www.figma.com/design/lhlUGHS1963vcOg9iKjnYl/2025-q4-Loyalty-program?node-id=5906-35908&m=dev) | 5906:35908   |
| Header 收合效果（參考 2） | 收合互動設計            | [5906-36485](https://www.figma.com/design/lhlUGHS1963vcOg9iKjnYl/2025-q4-Loyalty-program?node-id=5906-36485&m=dev) | 5906:36485   |
| 瀑布流收合 + Sticky    | Tabs sticky 與收合互動 | [5906-37073](https://www.figma.com/design/lhlUGHS1963vcOg9iKjnYl/2025-q4-Loyalty-program?node-id=5906-37073&m=dev) | 5906:37073   |

---

## 二、舊架構（我的頁）整理

### 2.1 入口與架構

| 項目 | 說明                                                                                                                                                                               |
|----|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 入口 | MainActivity Tab → **UserFragment**（ViewBinding `FragmentUserBinding`）                                                                                                           |
| 架構 | MVP：**UserPresenter** + **UserMvpView**（UserFragment 實作）                                                                                                                         |
| 狀態 | **Reductor**：`UserPresenter.viewReady()` dispatch `UserActions.viewReady()` → **UserReducer** 呼叫多支 API，結果寫入 **AppState**（userInfo、memberPoints、loyaltyMemberInfo、referralInfo 等） |
| UI | XML layout + 多個 component／PreferenceItem，依登入狀態與 API 結果顯示                                                                                                                         |

### 2.2 主要區塊與資料來源（舊版）

| 區塊      | 顯示內容                                 | 資料／API（摘要）                                                                                                    |
|---------|--------------------------------------|---------------------------------------------------------------------------------------------------------------|
| 頭像區     | 未登入：登入/註冊鈕、設定；已登入：大頭貼、姓名、等級文案、設定     | UserInfo（登入 API）、**getLoyaltyMemberInfo**(currency)                                                           |
| 優惠券／點數  | 優惠券數、點數                              | 無 B2C 數量 API；**getMemberPoints**(language)                                                                    |
| 列表 menu | 願望清單、信用卡、會員等級、邀請、任務、FAQ、規章、回饋、關於、導覽等 | getReferralData、RemoteConfig、DCS blog_url 等，詳見 [member-page-ui-api-mapping.md](member-page-ui-api-mapping.md) |
| 頁尾／錯誤   | 版本號、footer、網路錯誤                      | DCS app_footer_config、AppState 錯誤旗標                                                                           |

### 2.3 舊版進入時觸發 API（UserReducer.viewReady，已登入）

- getFriends、**getMemberPoints**、getReferralData、**getLoyaltyAllNotice**（內含 unlock/tier/exp
  notice）、**getLoyaltyMemberInfo**

---

## 2.4 會員頁已知 API 清單（開發可參考，有疑問再對照盤點文件並更新）

| 用途           | API                               | 備註                            |
|--------------|-----------------------------------|-------------------------------|
| 會員狀態         | `GET /v2/loyalty/member/info`     | 等級等，同首頁                       |
| KK Points 餘額 | `GET /v2/member/points`           | 同首頁                           |
| 折扣券（會員優惠券列表） | `GET /v2/member/coupons`          | 數量用 `availableCoupons.size`   |
| 任務列表（登入）     | `GET /v2/mission/list/status`     | 任務數量／列表                       |
| 任務列表（未登入）    | `GET /v2/mission/list/un_login`   | 任務數量／列表；詳情另見規格                |
| 推薦／邀請        | `GET /v2/member/referral`         | 推薦資料                          |
| 推薦 Banner    | `GET /v2/referral/inviter/banner` |                               |
| 邀請碼列表        | `GET /v2/referral/inviter/code`   |                               |
| 瀑布流（會員頁）     | `GET /api/v2/member/product-list` | **新增**，會員專用；回傳格式是否與首頁一致需與後端確認 |

開發中若有其他 API
或參數疑問，可先參考 [member-page-ui-api-mapping.md](member-page-ui-api-mapping.md)、[2025-q4-loyalty-home-tasks.md](2025-q4-loyalty-home-tasks.md)
（首頁 API／Loyalty unlock 盤點），並將結論更新至本表或「待討論」一節供討論。

---

## 三、登入狀態判斷（參考）

| 方式                                     | 位置                                                         | 說明                                                                                                         |
|----------------------------------------|------------------------------------------------------------|------------------------------------------------------------------------------------------------------------|
| **AppSharedData.hasAlreadyLoggedIn()** | `libs/base/.../AppSharedData.kt`                           | `persistentManager.getUserInfo().memberUuid.trim().isNotEmpty()`；Compose／ViewModel 可注入 `AppSharedData` 呼叫。 |
| **AppState.hasAlreadyLoggedIn()**      | Reductor 狀態                                                | 用於 Presenter 訂閱 Store 時；來源與登入流程寫入的 `userInfo`／`userTokenInfo` 一致，登出會清掉。                                    |
| **本地兜底**                               | 部分 Fragment（如 JRSearchResultListFragment、TransWebActivity） | `sharedPreferencesHelper.getUserInfo().memberUuid.trim().isNotEmpty()`，與 AppSharedData 邏輯相同。               |

**結論**：會員頁若為 Compose + ViewModel、不訂閱 Store，建議用 **AppSharedData.hasAlreadyLoggedIn()**
判斷登入狀態；與首頁 `ShouldShowFirstPurchaseBannerUseCase`、CouponMainViewModel
等用法一致。登入／登出後需在回到會員頁時更新 UI（可於 onResume 或 ViewModel 內依賴 Flow/State 刷新）。

---

## 四、新頁面共識

1. **全新頁面、Compose**  
   整頁以 Compose 重做，不沿用現有 UserFragment XML；參考首頁 **HomeScreen** 的架構與可收合設計。

2. **可收合 Header，分兩種狀態開發**
    - **未登入**：一種版面與互動（依 Figma「未登入時」）。
    - **已登入**：一種版面與互動（依 Figma「已登入」、會員資料區）。  
      兩者分開進行，便於對照 Figma 與驗收。

3. **頁面下方：瀑布流**
    - **參考並覆用首頁瀑布流架構**（LazyVerticalStaggeredGrid、篩選、四種卡、Paging）。
    - **API 不同**：會員頁使用會員專用 waterfall API（端點與參數由後端提供），**回傳格式與首頁一致**（如
      HomeExplore / homeWaterfallCards）。
    - 詳見 [member-page-waterfall-research.md](member-page-waterfall-research.md)：Model
      共用、PagingSource 可抽象、商品卡可抽共用 Composable。

4. **瀑布流 Tabs（篩選）Sticky + 與 Header 互動**
    - 滑動時 Tabs 會 **sticky 到上方**，與 Header 有互動效果（收合時 Tabs 貼頂等）。
    - 行為與規格以 **Figma「瀑布流區塊」**（5914-46813）為準。

5. **開發流程**
    - **第一階段：架構與佈局** — 新 Compose 頁、導航接點、可收合 Header（未登入／已登入分開）、下方瀑布流骨架、Sticky
      Tabs 與 Header 互動邏輯。
    - **第二階段：Figma UI/UX 與細節** — 對 Figma 做 UI/UX 對齊，含顏色、間距、字級、圖示等設計系統套用。

---

## 五、任務規劃

### Task 1：新頁面入口 + 暫時 flag（舊／新切換）

| 項目   | 說明                                                                                                                                                                                                                                                                                                                       |
|------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 目標   | 建立新「我的」Compose 頁面入口，用**暫時 flag** 決定顯示舊頁（UserFragment）或新頁（Compose）。                                                                                                                                                                                                                                                       |
| 實作要點 | ① 新增 Fragment（如 `MemberPageFragment`）內嵌 Compose `MemberPageScreen`（可先空白或簡單佔位）。② 新增 flag：例如 `BuildConfig` 欄位、或 `RemoteConfig`、或單一常數 `USE_NEW_MEMBER_PAGE`。③ 在 **MainActivity** 中 `R.id.tab_user` 分支：若 `useNewMemberPage()` 回傳 true 則 `replace` 為 `MemberPageFragment`，否則維持 `createUserFragment()`。④ 舊頁與新頁並存，切換 flag 即可驗證。 |
| 驗收   | Tab 切到「我的」時，flag 開→新頁、flag 關→舊頁，且無 crash。                                                                                                                                                                                                                                                                                |

### Task 2：新頁面架構與佈局（含收合／Sticky）

Task 2 拆成多個 **checkpoint**，每完成一個即可驗證再往下。

| Checkpoint | 內容                                                                                                                                                   | 驗收方式                                  |
|------------|------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------|
| **CP2.1**  | 新頁基本骨架：`MemberPageScreen` 單一 Column 或 LazyColumn，上方固定 Header 佔位（固定高度），下方簡單列表或空白。無收合。                                                                 | 進入新頁可見 Header 區 + 下方可捲動區域。            |
| **CP2.2**  | Header 可收合（單一狀態）：Header 高度隨 scroll 變化（例如 NestedScrollConnection 或 LazyList 的 firstVisibleItemScrollOffset），progress 驅動 Header 高度／alpha。先不做未登入／已登入分版。 | 上滑時 Header 會收合，下滑會展開，無明顯錯位或閃爍。        |
| **CP2.3**  | Header 分版：未登入版與已登入版兩種 UI 骨架（依登入狀態切換），各自套用 CP2.2 收合邏輯。                                                                                                | 切換登入狀態可看到兩種 Header 且收合行為一致。           |
| **CP2.4**  | 瀑布流區塊接入：在 Header + menu 區下方接入瀑布流（LazyVerticalStaggeredGrid 或共用首頁區塊 Composable），資料可 mock。篩選 Tabs 先靜態。                                                 | 頁面可從 Header 一路捲到瀑布流，捲動順暢。             |
| **CP2.5**  | Sticky Tabs：捲動時瀑布流上方的 Tabs（篩選）在到達頂部時 sticky，與 Header 收合狀態協調（例如收合後 Tabs 貼在 status bar 下方）。                                                            | 上滑時 Tabs 會吸頂，與 Figma 5906-37073 行為對齊。 |
| **CP2.6**  | 收合與 Sticky 細調：對照 Figma 5906-35908、5906-36485、5906-37073 微調閾值、過渡、陰影。                                                                                  | 產品／設計確認收合與 sticky 符合設計稿。              |

---

## 六、收合與 Sticky 架構建議（避免首頁痛點）

### 5.1 首頁現況的痛點（參考 HomeScreen）

| 痛點                            | 說明                                                                                                                                                                                               |
|-------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **依賴 onGloballyPositioned**   | `whiteContainerHeight`、`whiteContainerScreenY` 來自「白色圓角 Surface」的 layout 回調，需等測量完成且隨捲動不斷更新；初始或快速滑動時易有 0 或舊值，需 fallback 與「雙重保險」邏輯。                                                                 |
| **progress 與多個來源**            | `progress` 由 containerBottom/containerTop 與 `collapseThreshold` 推算，又與 `isToolbarCollapsedByScroll`（用 firstVisibleItem.index > 0）並存，邏輯分散，邊界要兩邊都顧。                                                 |
| **fullLineCount 依賴過多**        | `fullLineCount` 依賴 themeCategories、upcomingOrder、crossSell、couponBanner、recentlyViewed、firstPurchase、filter、loadState 等，任一變動就重算；且用於 `actualIndex`、`filterIndex`、`showStickyFilter`，與 layout 強耦合。 |
| **itemLayoutMap 與瀑布流 layout** | 用 `snapshotFlow { lazyGridState.layoutInfo }` 依 visible items 推 column，再用 0.8f viewport、rowKey/50 等經驗值分組，程式複雜且易在 item 增減時出錯。                                                                     |
| **NestedScroll 與 content 一體** | 收合「可滑動距離」綁在白色容器高度上，內容區塊動態變多變少時，行為難預期。                                                                                                                                                            |

### 5.2 會員頁建議：單一捲動來源、固定／可測高度

| 原則                         | 建議做法                                                                                                                                                                                                                                            |
|----------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **單一 scroll 狀態**           | 只用一個 `LazyListState`（或 LazyStaggeredGridState）作為捲動真相來源。progress 或「是否收合」**只**由 `firstVisibleItemIndex` + `firstVisibleItemScrollOffset`（及已知的 header 高度）推算，不再用 `onGloballyPositioned` 回傳的 Y 做主要依據。                                                |
| **Header 高度可預測**           | Header 未登入／已登入兩版各自給出**固定或最大高度**（或透過 `onSizeChanged` 只量一次），收合後高度也固定（如 minToolbarHeight）。progress = f(scrollOffset, maxHeaderHeight, minHeaderHeight) 一次算完，不依賴內容區塊的動態高度。                                                                          |
| **內容區用 contentPadding 頂開** | 列表的 `contentPadding` top = 最大 Header 高度（或加 status bar），讓「可捲動內容」從 Header 下方開始。Header 用 Box 疊在列表上方，依 progress 改高度與 alpha，視覺上像收合，實際不參與 layout 順序計算。                                                                                                |
| **Sticky Tabs 獨立一層**       | Tabs 不塞進 LazyList 裡當一般 item（避免首頁的 filterIndex、fullLineCount 問題）。Tabs 當作**疊在列表上的第二層**：用 `layoutInfo` 只判斷「篩選對應的 content 是否已滑過頂部」，滑過則 showStickyTabs = true，Tabs 用 `AnimatedVisibility` 或固定位置顯示在 Header 下方（或 status bar 下方）；高度固定，不需 itemLayoutMap。 |
| **瀑布流 column 簡化**          | 若兩欄瀑布流，可考慮：左欄右欄用兩條 `LazyColumn` 並排（各管一欄），或沿用 StaggeredGrid 但 column 只做 padding 對齊、不做複雜的 itemLayoutMap 推 column（必要時用 key 或預測順序）。                                                                                                                 |

### 5.3 建議的結構示意（會員頁）

```
Box {
  // 1. 底層：單一 LazyVerticalStaggeredGrid（或 LazyColumn）
  //    contentPadding.top = maxHeaderHeight
  //    內容 = [Header 佔位空白] + [menu 區] + [篩選 item] + [瀑布流 items]
  //    或：內容 = [可捲動的 Header 內容當第一個 item] + [menu] + [篩選] + [瀑布流]
  LazyVerticalStaggeredGrid(state = listState, contentPadding = ...) { ... }

  // 2. 疊層：Header（依 listState 算 progress，改 height / alpha）
  MemberPageHeader(progress = progress, isLoggedIn = ...)

  // 3. 疊層：Sticky Tabs（當 listState 顯示「篩選已過頂」時顯示）
  if (showStickyTabs) { MemberPageStickyTabs(...) }
}
```

- **progress**：由 `listState.firstVisibleItemIndex` 與 `listState.firstVisibleItemScrollOffset`
  及「Header 佔位高度」或「第一個 item 高度」計算，**不**用 onGloballyPositioned。
- 若採用「第一個 item = Header 內容」：Header 視覺在疊層，列表第一個 item 是等高的 spacer，scroll 只影響
  listState，progress 從 scroll 推得，邏輯單一。

### 5.4 小結

- 收合與 sticky 的困難點在「不依賴動態 layout 座標、不依賴多區塊加總的 fullLineCount」。
- 會員頁建議：**單一 LazyList 狀態 + 固定／可測 Header 高度 + progress 僅由 scroll 推導 + Sticky Tabs
  獨立疊層用 index/offset 判斷**，可避免首頁那種多處計算與雙重保險，較易維護與對齊
  Figma（5906-35908、5906-36485、5906-37073）。

---

## 七、開發流程（兩階段）

| 階段                     | 內容                                                      | 產出                          |
|------------------------|---------------------------------------------------------|-----------------------------|
| **1. 架構與佈局**           | 新 Compose 頁、Task 1 flag、Task 2 各 checkpoint（含收合／Sticky） | 可跑通的版面與滾動／收合行為，無需套完所有 UI 細節 |
| **2. Figma UI/UX 與細節** | 對照 Figma 做視覺與互動：顏色、間距、字級、圖示、狀態、動效                       | 與設計一致之 UI，含設計系統 token       |

### 7.1 Compose 開發準則

**Preview 規範**

- 每個 Composable 都應加上 `@Preview`，盡可能還原設計稿樣貌
- 資料處理原則：
    - **能 mock 就 mock**：Preview 內直接提供假資料（字串、數字、簡單物件）
    - **data 太大不能 mock**：設計 Composable 時傳入 UI 專用的 ViewInfo / UiState 類型，只包含必要欄位
    - **避免傳入完整 domain/data model**：不要讓 Composable 依賴龐大的 API response 或
      entity，改為傳入已處理好的 UI 資料
- 範例：
  ```kotlin
  // ❌ 不好：傳入完整 API model
  @Composable
  fun MemberCard(memberInfo: LoyaltyMemberInfo) { ... }
  
  // ✅ 好：只傳必要 UI 欄位
  data class MemberCardUiState(
      val name: String,
      val tier: String,
      val points: String
  )
  @Composable
  fun MemberCard(uiState: MemberCardUiState) { ... }
  
  @Preview
  @Composable
  private fun MemberCardPreview() {
      MemberCard(
          uiState = MemberCardUiState(
              name = "阿修魔魔內六",
              tier = "白銀會員",
              points = "999 KKday Points"
          )
      )
  }
  ```

**其他準則**

- 套用 KKday design tokens（spacing, colors, typography）
- 遵守 Material Design 3 規範
- 使用 `dimensionResource` / `colorResource` 而非硬編碼數值

---

## 八、開發決策（已確認）

| 項目                  | 決策                            | 說明                                                                                                                                                                                                                                   |
|---------------------|-------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **登入狀態來源**          | ✅ **沿用舊頁面邏輯**                 | 使用 `AppSharedData.hasAlreadyLoggedIn()` 判斷登入狀態，與舊版 UserFragment 一致。已在 `MemberPageViewModel` 實作。                                                                                                                                      |
| **API 呼叫架構**        | ✅ **新架構：ViewModel + UseCase** | **重要**：不走 Reductor Store，所有 API 都在 `MemberPageViewModel` 中透過 UseCase 呼叫。參考首頁 `HomeViewModelV2` 的模式。                                                                                                                                  |
| **狀態儲存策略**          | ✅ **使用 PersistentManager**    | 需要持久化的資料（如會員資訊、點數）使用 `PersistentManager` 儲存，不使用 Reductor AppState。ViewModel 中注入 `PersistentManager` 處理讀寫。                                                                                                                            |
| **舊版 API 是否沿用**     | ✅ **API 沿用，但架構改為新模式**         | 頭像、點數、等級、menu 等都使用現有 API（`getLoyaltyMemberInfo`、`getMemberPoints`、`getReferralData` 等），但透過 UseCase 在 ViewModel 中呼叫，不走 Reductor。                                                                                                      |
| **Menu 區項目與順序**     | ✅ **依照 Figma 順序與設定**          | 第二階段開發時，嚴格對照 Figma [5914-43779](https://www.figma.com/design/lhlUGHS1963vcOg9iKjnYl/2025-q4-Loyalty-program?node-id=5914-43779&m=dev) 的項目順序與顯示邏輯。需參考 [member-page-ui-api-mapping.md](member-page-ui-api-mapping.md) 確認各項目的資料來源與顯示條件。 |
| **追蹤（Analytics）**   | ✅ **沿用舊頁面 Event**             | 相同功能直接搬用舊版的 tracking event 名稱與參數。新增功能的 event 再另行定義。參考 `UserFragment` 與 `UserPresenter` 的現有 tracking 邏輯。                                                                                                                              |
| **Task 1 flag 存放處** | ✅ **已實作**                     | 使用 `MainActivity` 中的條件判斷，透過 `BuildConfig` 或簡單常數控制。已在 Task 1 完成。                                                                                                                                                                      |

## 九、待討論／待補（後續處理）

| 項目                   | 說明                                                                                                        | 狀態       |
|----------------------|-----------------------------------------------------------------------------------------------------------|----------|
| **會員 waterfall API** | 端點、request 參數（filter／list）需與後端確認；回傳格式與首頁一致（HomeExplore／homeWaterfallCards）即可共用 Model 與 Paging。目前暫用首頁 API。 | 🔄 待後端提供 |
| **估時**               | Task 1／Task 2 各 checkpoint 可補 AI 開發估時，方便排程。                                                               | 📝 可選    |

---

## 十、第二階段任務規劃（Figma UI/UX 與細節對齊）

**注意**
：設定頁開發功能實作已插隊優先處理，詳見 [2025-q4-loyalty-settings-tasks.md](2025-q4-loyalty-settings-tasks.md)

---

### 開發進度總覽（2025-03-04 更新）

| Phase   | 任務                | 狀態     | 備註                                 |
|---------|-------------------|--------|------------------------------------|
| Phase 1 | 架構與佈局（Task 1 & 2） | ✅ 完成   | 收合、Sticky 已實作                      |
| Phase 2 | 會員資料區 UI/UX       | 🔄 進行中 | Header Bar、會員卡已完成，待完善大頭貼與 callback |
| Phase 3 | Menu 區塊           | ⏳ 待開始  | Figma 5914-43779                   |
| Phase 4 | 瀑布流細節             | ⏳ 待開始  | Loading/空狀態/錯誤處理                   |
| Phase 5 | 互動與動效             | ⏳ 待開始  | 動畫優化                               |
| Phase 6 | 響應式與邊界            | ⏳ 待開始  | 測試與邊界處理                            |
| 後期      | 多國語系              | ⏳ 待開始  | 字串資源整理                             |
| 後期      | 瀑布流 API 切換        | ⏳ 待後端  | 待後端提供會員頁專用 API                     |

---

### 設計稿全局規範

**Figma
**: [5914-48292](https://www.figma.com/design/lhlUGHS1963vcOg9iKjnYl/2025-q4-Loyalty-program?node-id=5914-48292&m=dev)

| 規範            | 說明                                     |
|---------------|----------------------------------------|
| 未登入功能入口       | 所有需要登入才能使用的入口，未登入時**不隱藏**，點擊後的登入機制維持現況 |
| 原本未登入隱藏的功能    | 改為顯示，點擊直接喚起登入                          |
| 原本跳轉後才登入的功能   | 維持現況，不需特別改成直接喚起登入                      |
| sticky header | 頁面滑動超過頭像區域後顯示 sticky header bar        |
| 圖片圓角          | 需要前端控制圓角                               |

---

### StyleDictionary 設計 Tokens 參考

**檔案位置**：`libs/designsystem/design/src/main/res/values/design_tokens.xml`

#### 顏色（Color）

| 用途       | Token 名稱                               | 色碼      |
|----------|----------------------------------------|---------|
| 文字 - 最深  | `kk_color_text_darker`                 | #212121 |
| 文字 - 深   | `kk_color_text_dark`                   | #727272 |
| 文字 - 中   | `kk_color_text_medium`                 | #9C9DA0 |
| 文字 - 資訊深 | `kk_color_text_info_darker`            | #1565C0 |
| 背景 - 主色淺 | `kk_color_background_primary_lighter`  | #F0FAFB |
| 背景 - 表面淺 | `kk_color_background_surface_light`    | #F1F4F8 |
| 背景 - 表面中 | `kk_color_background_surface_medium`   | #E6E9ED |
| 背景 - 主按鈕 | `kk_color_background_primary_button`   | #1AB6C1 |
| 背景 - 危險淺 | `kk_color_background_critical_lighter` | #FFF2F2 |
| 邊框 - 淺   | `kk_color_border_lighter`              | #E6E9ED |
| 白色       | `kk_color_white`                       | #FFFFFF |

#### 圓角（Radius）

| 用途 | Token 名稱        | 數值                               |
|----|-----------------|----------------------------------|
| 超小 | `kk_radius_xs`  | 2dp                              |
| 小  | `kk_radius_sm`  | 4dp                              |
| 中  | `kk_radius_md`  | 8dp                              |
| 大  | `kk_radius_lg`  | 12dp                             |
| 超大 | `kk_radius_xl`  | 16dp                             |
| 圓形 | `radius-circle` | 999dp (Compose 使用 `CircleShape`) |

#### 間距（Spacing）

| 用途  | Token 名稱         | 數值   |
|-----|------------------|------|
| 025 | `kk_spacing_025` | 2dp  |
| 050 | `kk_spacing_050` | 4dp  |
| 075 | `kk_spacing_075` | 6dp  |
| 100 | `kk_spacing_100` | 8dp  |
| 150 | `kk_spacing_150` | 12dp |
| 200 | `kk_spacing_200` | 16dp |
| 250 | `kk_spacing_250` | 20dp |
| 300 | `kk_spacing_300` | 24dp |
| 400 | `kk_spacing_400` | 32dp |
| 500 | `kk_spacing_500` | 40dp |
| 600 | `kk_spacing_600` | 48dp |

#### 字型（Typography）

| 用途          | Token 名稱              | 大小/行高/粗細                   |
|-------------|-----------------------|----------------------------|
| H6          | `kk_text_h6`          | 18sp / 26sp / Bold(700)    |
| Subtitle-lg | `kk_text_subtitle_lg` | 16sp / 24sp / Bold(700)    |
| Subtitle-md | `kk_text_subtitle_md` | 14sp / 20sp / Medium(500)  |
| Subtitle-sm | `kk_text_subtitle_sm` | 12sp / 16sp / Medium(500)  |
| Body-lg     | `kk_text_body_lg`     | 16sp / 24sp / Regular(400) |
| Body-md     | `kk_text_body_md`     | 14sp / 20sp / Regular(400) |
| Body-sm     | `kk_text_body_sm`     | 12sp / 16sp / Regular(400) |

#### Icon 尺寸（Dimension）

| 用途  | Token 名稱                | 數值   |
|-----|-------------------------|------|
| 2XS | `kk_dimension_icon_2xs` | 14dp |
| XS  | `kk_dimension_icon_xs`  | 16dp |
| SM  | `kk_dimension_icon_sm`  | 20dp |
| MD  | `kk_dimension_icon_md`  | 24dp |
| LG  | `kk_dimension_icon_lg`  | 32dp |
| XL  | `kk_dimension_icon_xl`  | 48dp |

#### Compose 使用方式

```kotlin
// 顏色
colorResource(id = com.kkday.design.R.color.kk_color_text_darker)

// 間距
dimensionResource(id = com.kkday.design.R.dimen.kk_spacing_200)

// 圓角
RoundedCornerShape(dimensionResource(id = com.kkday.design.R.dimen.kk_radius_lg))

// 字型（參考 KKdayTypography）
MaterialTheme.typography.titleMedium  // 對應 Subtitle-lg
MaterialTheme.typography.bodyMedium   // 對應 Body-md
MaterialTheme.typography.bodySmall    // 對應 Body-sm
```

---

### 10.0 開發準則（基於已確認決策）

**架構原則（重要）**

- ⚠️ **不使用 Reductor Store**：所有 API 呼叫都在 ViewModel 中進行
- ✅ **UseCase 使用原則**：
    - **已存在的 UseCase**：直接使用（如 `GetLoyaltyMemberInfoUseCase`、`GetMemberPointsUseCase`）
    - **會被其他頁面覆用的邏輯**：抽成 UseCase
    - **會員頁專用功能**：直接在 ViewModel 中實作，保持簡單直觀
- ✅ **狀態管理**：ViewModel 使用 `StateFlow` 管理 UI 狀態
- ✅ **持久化儲存**：需要儲存的資料使用 `PersistentManager`，不使用 AppState
- ⚠️ **不確定時先提出討論**：避免自行決定架構方向

**API 策略**

- 沿用舊版 API：`getLoyaltyMemberInfo`、`getMemberPoints`、`getReferralData` 等
- 參考 `UserPresenter.viewReady()` 的 API 呼叫順序與時機
- 已有 UseCase 的直接用，沒有的直接在 ViewModel 注入 Repository 呼叫

**ViewModel 注入範例**

```kotlin
@KoinViewModel
class MemberPageViewModel(
    private val appSharedData: AppSharedData,
    private val persistentManager: PersistentManager,  // 用於儲存狀態
    // 已存在的 UseCase 直接用
    private val getLoyaltyMemberInfoUseCase: GetLoyaltyMemberInfoUseCase,
    private val getMemberPointsUseCase: GetMemberPointsUseCase,
    // 會員頁專用功能直接注入 Repository
    private val memberRepository: MemberRepository,  // 例如：取得優惠券、任務等
    // ... 其他依賴
): ViewModel() {
    // StateFlow 管理 UI 狀態
    private val _uiState = MutableStateFlow(MemberPageUiState())
    val uiState = _uiState.asStateFlow()

    // 會員頁專用功能直接在這裡實作
    fun loadCoupons() {
        viewModelScope.launch {
            memberRepository.getCoupons().collect { result ->
                // 處理結果
            }
        }
    }
}
```

**Tracking 策略**

- 相同功能搬用舊版 event（參考 `UserFragment`、`UserPresenter`）
- 新增功能的 event 另行定義
- 保持 event 參數格式與舊版一致

**UI 對齊**

- 嚴格對照 Figma 設計稿
- 使用 KKday design tokens
- 每個 Composable 都加 `@Preview`

### 10.1 Header 區塊（未登入版）

**Figma
**: [5571-38118](https://www.figma.com/design/lhlUGHS1963vcOg9iKjnYl/2025-q4-Loyalty-program?node-id=5571-38118&m=dev)

**任務**

- [x] 背景顏色（`kk_color_background_primary_lighter`）
- [x] 設定按鈕位置與樣式（右上角，`ic_setting_line`，24dp）
- [x] 標題文字樣式（"發現享受會員禮遇"，`titleMedium`）
- [x] 副標題樣式（"探索下一段旅程"，`bodySmall`）
- [x] 登入/註冊按鈕樣式（Primary Button，圓角 `kk_radius_md`）
- [x] 間距與 padding（置中佈局，使用 design tokens）
- [x] 收合動畫（alpha 漸變）
- [x] Callback 傳遞（`onLoginClick`、`onSettingsClick`）

**API**

- 無需 API（未登入狀態）

**Tracking**

- 登入按鈕點擊：沿用舊版 event（待在 Fragment/ViewModel 實作）
- 設定按鈕點擊：沿用舊版 event（待在 Fragment/ViewModel 實作）

**已完成**

- ✅ UI 樣式完全對齊 Figma
- ✅ 使用 KKday design tokens
- ✅ 收合動畫流暢
- ⏳ 待實作：Fragment/ViewModel 層的 callback 處理與 tracking

### 10.2 Header 區塊（已登入版）

**Figma**:

-
主頁面 [5342-28822](https://www.figma.com/design/lhlUGHS1963vcOg9iKjnYl/2025-q4-Loyalty-program?node-id=5342-28822&m=dev)
-
會員資料區 [5914-38031](https://www.figma.com/design/lhlUGHS1963vcOg9iKjnYl/2025-q4-Loyalty-program?node-id=5914-38031&m=dev)
- **會員資料區域規格
  ** [5914-53714](https://www.figma.com/design/lhlUGHS1963vcOg9iKjnYl/2025-q4-Loyalty-program?node-id=5914-53714&m=dev)

---

#### 會員資料區規範（來自 Figma 5914-38031）

**背景圖**

- 背景圖直接 Export 使用
- 根據登入狀態和會員等級顯示相應的背景圖
- 目前圖片為示意版，需要等視覺確定後再更新各等級背景圖片

**頭像名稱資料區域**

| 元素          | 規範                         |
|-------------|----------------------------|
| 用戶頭像        | 未設置頭像顯示預設頭像（視覺確定後提供）       |
| 用戶名稱        | 最多顯示 1 行，超過省略              |
| 管理賬戶 button | 最多顯示 1 行，超過省略（兜底設置，基本不要出現） |

**點擊行為**

| 元素                | 行為                         |
|-------------------|----------------------------|
| 頭像、名稱、管理賬戶 button | 進入基本資料頁（`ProfileActivity`） |

**會員等級卡片規範**

| 項目           | 規範                          | 對應 Token                              |
|--------------|-----------------------------|---------------------------------------|
| 卡片圓角         | 12dp                        | `kk_radius_lg`                        |
| 卡片內間距        | 12dp                        | `kk_spacing_150`                      |
| 等級徽章         | 容器 center & center 放置，不撐高卡片 | -                                     |
| 背景圖          | center & center 放置在卡片背景     | -                                     |
| 等級名稱字型       | H6 (18sp/26sp/Bold)         | `kk_text_h6`                          |
| 等級名稱顏色       | 藍色                          | `kk_color_text_info_darker` (#1565C0) |
| 禮遇中心按鈕       | 空間允許並排，過長換行                 | -                                     |
| 權益/Points 文字 | Body-sm (12sp/16sp)         | `kk_text_body_sm`                     |
| 點擊範圍         | 整張卡片                        | -                                     |
| 點擊行為         | 進入「會員禮遇中心頁」，預設進入用戶所在等級      | -                                     |

**文字過長處理**

| 元素                 | 處理方式                                      |
|--------------------|-------------------------------------------|
| 等級名稱 + 禮遇中心 button | 空間允許並排；過長則禮遇中心換行，最多一項獨占 1 行，超過截斷          |
| 權益數量 + Points 回饋   | 空間允許並排；過長則 icon+text 整項換行，最多一項獨占 1 行，超過省略 |

---

**任務**

- [x] 設定按鈕（右上角，與未登入版一致）
- [x] 會員姓名樣式（`titleMedium`）
- [x] 管理賬戶按鈕樣式（`bodySmall`，可點擊）
- [x] 等級文字顯示（會員等級卡片）
- [x] KK Points 顯示（`ic_kkday_points_color` 圖示 + 數量）
- [x] 禮遇中心按鈕（卡片右側）
- [x] 背景與間距（使用 design tokens）
- [x] 收合動畫（alpha 漸變）
- [ ] 大頭貼顯示（待實作）
- [ ] 等級徽章背景圖（待實作）
- [ ] 會員頁背景圖（待實作）
- [ ] 會員卡背景圖（待實作）

---

#### 10.2.1 大頭貼顯示規格

**資料來源（舊頁面邏輯）**

| 來源                                         | 說明                                  |
|--------------------------------------------|-------------------------------------|
| `UserInfo.photoUrl`                        | API 回傳的大頭貼 URL（`photo_webp_url` 欄位） |
| `PersistentManager.getUserInfo().photoUrl` | 本地儲存的使用者資訊                          |

**舊版實作參考**（`UserFragment.kt`）

```kotlin
// 未登入
imageProfile.setActualImageResource(R.drawable.ic_profile_default)

// 已登入
imageProfile.setImageURI(userInfo.photoUrl)
```

**顯示邏輯**

| 狀態             | 顯示                                   |
|----------------|--------------------------------------|
| 未登入            | 預設圖示（`ic_profile_default` 或設計指定）     |
| 已登入，有 photoUrl | 載入 photoUrl 圖片（使用 Coil/AsyncImage）   |
| 已登入，無 photoUrl | 顯示姓名首字（使用 `AvatarVariant.Text`）或預設圖示 |

**Compose 實作建議**

使用 designsystem 的 `KKAvatar` 元件：

- 有圖片：`AvatarVariant.Image(photoUrl, AvatarType.People)`
- 無圖片/失敗：`AvatarVariant.Text(name.first().toString(), position)`
- 尺寸：`AvatarSize.Medium48`（對應設計稿 48dp）

**點擊行為**

- 點擊大頭貼 → 進入「基本資料頁」（`ProfileActivity`）
- 參考：`UserFragment.kt` line 517-519

---

#### 10.2.2 會員等級資源選用規格

**等級徽章 Icon**

| 等級            | 常數                                       | Icon 資源                                                 |
|---------------|------------------------------------------|---------------------------------------------------------|
| 白銀 (Silver)   | `LoyaltyMemberInfo.TIER_SILVER` ("01")   | `com.kkday.design.R.drawable.ic_loyalty_sliver_color`   |
| 白金 (Platinum) | `LoyaltyMemberInfo.TIER_PLATINUM` ("02") | `com.kkday.design.R.drawable.ic_loyalty_platinum_color` |
| 鑽石 (Diamond)  | `LoyaltyMemberInfo.TIER_DIAMOND` ("03")  | `com.kkday.design.R.drawable.ic_loyalty_diamond_color`  |
| 黃金 (Gold)     | `LoyaltyMemberInfo.TIER_GOLD` ("04")     | `com.kkday.design.R.drawable.ic_loyalty_line`（暫用）       |

**會員頁背景圖（Header 背景）**

| 等級  | 資源                                  | 備註              |
|-----|-------------------------------------|-----------------|
| 未登入 | `R.drawable.default_menber_page_bg` | 預設背景            |
| 白銀  | `R.drawable.silver_menber_page_bg`  |                 |
| 白金  | `R.drawable.silver_menber_page_bg`  | 暫用 silver，待視覺提供 |
| 鑽石  | 待視覺提供                               | 目前暫用 silver     |
| 黃金  | `R.drawable.silver_menber_page_bg`  | 暫用 silver，待視覺提供 |

**會員卡背景圖（等級卡片背景）**

| 等級 | 資源                                 | 備註              |
|----|------------------------------------|-----------------|
| 白銀 | `R.drawable.silver_member_card_bg` | 藍色漸層            |
| 白金 | `R.drawable.silver_member_card_bg` | 暫用 silver，待視覺提供 |
| 鑽石 | 待視覺提供                              | 目前暫用 silver     |
| 黃金 | `R.drawable.silver_member_card_bg` | 暫用 silver，待視覺提供 |

**資源選用 Helper 函式**

```kotlin
// 建議在 MemberPageScreen.kt 或獨立工具類別實作
@DrawableRes
fun getTierBadgeIcon(tier: String): Int = when (tier) {
    LoyaltyMemberInfo.TIER_SILVER -> com.kkday.design.R.drawable.ic_loyalty_sliver_color
    LoyaltyMemberInfo.TIER_PLATINUM -> com.kkday.design.R.drawable.ic_loyalty_platinum_color
    LoyaltyMemberInfo.TIER_DIAMOND -> com.kkday.design.R.drawable.ic_loyalty_diamond_color
    LoyaltyMemberInfo.TIER_GOLD -> com.kkday.design.R.drawable.ic_loyalty_line
    else -> com.kkday.design.R.drawable.ic_loyalty_sliver_color
}

@DrawableRes
fun getMemberPageBackground(tier: String, isLoggedIn: Boolean): Int = when {
    !isLoggedIn -> R.drawable.default_menber_page_bg
    tier == LoyaltyMemberInfo.TIER_DIAMOND -> R.drawable.silver_menber_page_bg // TODO: 待視覺提供鑽石背景
    else -> R.drawable.silver_menber_page_bg
}

@DrawableRes
fun getMemberCardBackground(tier: String): Int = when (tier) {
    LoyaltyMemberInfo.TIER_DIAMOND -> R.drawable.silver_member_card_bg // TODO: 待視覺提供鑽石背景
    else -> R.drawable.silver_member_card_bg
}
```

**注意事項**

- 目前只有鑽石等級會在視覺確定後替換為專屬背景
- 其他等級（白銀、白金、黃金）暫時都使用 silver 背景
- 背景圖片說明來自 Figma：「目前圖片為示意版，需要等視覺確定後再確定和更新各等級背景圖片」

---

**API 與資料來源**

- ✅ `GetLoyaltyMemberInfoUseCase`: 等級、經驗值（已整合）
- ✅ `GetMemberPointsUseCase`: KK Points 餘額（已整合）
- ✅ `PersistentManager.getUserInfo()`: 姓名、大頭貼 URL（已整合）

**實作方式**

- ✅ ViewModel 在 `checkLoginStatus()` 時載入會員資料
- ✅ 使用 `StateFlow` 管理會員姓名、等級、點數
- ✅ Fragment 收集 state 並傳遞給 Screen

**已完成（2025-03-04）**

- ✅ Header Bar：X、聊天、設定、首頁 4 個 icon
- ✅ 頭像+名稱區：水平排列（左頭像 48dp、右名稱）
- ✅ 會員卡：藍色漸層背景 + 鑽石徽章（60x42dp）突出卡片上方
- ✅ 會員卡：顯示等級名稱、禮遇中心 tag、權益數、回饋倍率
- ✅ 統一使用 StyleDictionary 處理間距、顏色、字型
- ✅ 新增 isMemberDataReady 狀態，避免 API 載入前顯示預設值造成閃爍
- ✅ 會員卡背景使用 ContentScale.Crop 避免失真

**Phase 2 已完成（2025-03-04 更新）**

- ✅ 大頭貼顯示邏輯
    - 使用 `KKAvatar` 元件（`AvatarSize.Medium48`）
    - 有圖片：`AvatarVariant.Image(photoUrl, AvatarType.People)`
    - 無圖片：`AvatarVariant.Text(memberName.firstOrNull()?.toString())`
- ✅ 回首頁功能
    - `onHomeClick` 呼叫 `(activity as? MainActivity)?.goToHomeTab()`

**Phase 2 待完成（會員資料區）**

- [ ] 其他等級背景圖（白金、鑽石、黃金）
    - 目前都暫用 silver 背景
    - 待視覺確定後更新
- [ ] 會員卡背景圖（其他等級）
    - 目前都暫用 silver 卡片背景
    - 待視覺確定後更新
- [ ] 聊天功能實作
    - `onMessageClick` 待整合客服系統
    - 需確認會員頁聊天入口的產品需求（是否需要 orderId、或導向幫助中心）
- [ ] Tracking 實作
    - 大頭貼/名稱/管理賬戶點擊：參考 `UserFragment` line 517-519
    - 禮遇中心點擊：參考 `UserFragment` 舊版 event
    - 聊天、設定、首頁按鈕點擊：定義新 event

### 10.3 Menu 區塊（Phase 3）

**Figma
**: [5914-43779](https://www.figma.com/design/lhlUGHS1963vcOg9iKjnYl/2025-q4-Loyalty-program?node-id=5914-43779&m=dev)

**UI 任務**

- [ ] 確認項目清單與順序（對照 Figma）
- [ ] 各項目圖示（使用 design tokens icon 尺寸）
- [ ] 文字樣式與顏色（使用 StyleDictionary）
- [ ] 箭頭圖示（右側）
- [ ] 分隔線樣式（`kk_color_border_lighter`）
- [ ] 紅點提示（優惠券、任務）
- [ ] 點擊回饋效果（ripple）
- [ ] 間距與 padding（使用 StyleDictionary spacing）

**API 與資料來源**（參考 [member-page-ui-api-mapping.md](member-page-ui-api-mapping.md)）

| 項目        | API                             | 實作策略               |
|-----------|---------------------------------|--------------------|
| 優惠券數量     | `GET /v2/member/coupons`        | 直接在 ViewModel 實作   |
| 任務數量（已登入） | `GET /v2/mission/list/status`   | 檢查是否有現成 UseCase    |
| 任務數量（未登入） | `GET /v2/mission/list/un_login` | 檢查是否有現成 UseCase    |
| 推薦資料      | `GET /v2/member/referral`       | 檢查是否有現成 UseCase    |
| 項目顯示條件    | RemoteConfig                    | 參考 UserFragment 邏輯 |

**實作策略**

1. 先搜尋是否有現成的 UseCase 或 Repository method
2. 有現成的直接用
3. 沒有的話：
    - 會被其他頁面覆用 → 考慮抽成 UseCase
    - 會員頁專用 → 直接在 ViewModel 注入 Repository 實作
4. 不確定時先提出討論

**Tracking**

- 各項目點擊：沿用舊版 event（參考 `UserFragment` 的 menu item 點擊）

**預估工作量**

- UI 實作：1-2 天
- API 整合：1-2 天
- Tracking：0.5 天

### 10.4 瀑布流區塊細節（Phase 4）

**Figma
**: [5914-46813](https://www.figma.com/design/lhlUGHS1963vcOg9iKjnYl/2025-q4-Loyalty-program?node-id=5914-46813&m=dev)

**UI 任務**

- [ ] 背景漸層效果（對齊 Figma）
- [ ] 卡片間距微調（使用 StyleDictionary spacing）
- [ ] Loading 狀態 UI
    - Shimmer 效果或 Loading indicator
    - 參考首頁實作
- [ ] 空狀態 UI
    - 空狀態圖示 + 文字
    - 引導文案
- [ ] 錯誤狀態 UI
    - 錯誤圖示 + 文字
    - 重試按鈕
- [ ] 下拉刷新（PullRefresh）
- [ ] 上拉載入更多（Paging3 自動處理）

**API**

- ⚠️ 目前使用首頁 API（暫時）
- ⏳ 待後端提供會員頁專用 API（見 11.2）

**Tracking**

- 卡片曝光：參考首頁 waterfall tracking
- 卡片點擊：參考首頁 waterfall tracking
- 篩選切換：新增 event

**預估工作量**

- UI 狀態實作：1 天
- 下拉刷新：0.5 天
- Tracking：0.5 天

### 10.5 互動與動效（Phase 5）

**任務**

- [ ] Header 收合動畫流暢度優化
    - 檢查是否有掉幀
    - 調整動畫曲線
- [ ] Tabs sticky 過渡效果
    - 淡入淡出動畫
    - 位置過渡流暢
- [ ] 按鈕點擊 ripple 效果
    - 使用 Material3 ripple
    - 檢查所有可點擊元素
- [ ] 頁面進入動畫（可選）
    - 淡入效果
    - 元素依序出現
- [ ] 下拉刷新動畫
    - 使用 Material3 PullRefresh

**預估工作量**

- 動畫優化：1-2 天

### 10.6 響應式與邊界情況（Phase 6）

**測試項目**

- [ ] 不同螢幕尺寸測試
    - 小螢幕（5 吋以下）
    - 中螢幕（5-6 吋）
    - 大螢幕（6 吋以上）
    - 平板
- [ ] 長文字處理
    - 長姓名（ellipsis，最多 1 行）
    - 長等級名稱（ellipsis，最多 1 行）
    - 權益/回饋文字過長（換行處理）
- [ ] 錯誤處理
    - 網路錯誤提示（Toast 或 Snackbar）
    - API 失敗處理（顯示錯誤狀態）
    - 空資料狀態（顯示空狀態 UI）
- [ ] 極端情況
    - 無網路狀態
    - API 超時
    - 圖片載入失敗
    - 資料格式異常

**預估工作量**

- 測試與修正：1-2 天

---

## 十一、後續維護任務

### 11.1 多國語系待處理

**說明**：目前 Header 區塊的部分文字為 hard code，需要新增對應的多國語系字串資源。

**待處理項目**：

| 位置                | 目前 hard code 文字 | 建議字串資源 key                        | 狀態          |
|-------------------|-----------------|-----------------------------------|-------------|
| 未登入 Header - 標題   | "發現享受會員禮遇"      | `member_label_discover_benefits`  | 待新增         |
| 未登入 Header - 副標題  | "探索下一段旅程"       | `member_label_explore_journey`    | 待新增         |
| 未登入 Header - 按鈕   | "注册/登录"         | `member_label_login_or_sign_up`   | **已存在**，需改用 |
| 已登入 Header - 管理賬戶 | "管理賬戶 >"        | `member_label_account_management` | 待新增         |

**處理步驟**：

1. 在 `libs/app_resource/src/main/res/values/strings.xml` 新增英文字串
2. 在各語系資料夾新增對應翻譯（zh-rTW、zh-rCN、ja-rJP、ko-rKR、th-rTH、vi-rVN 等）
3. 修改 `MemberPageScreen.kt`，將 hard code 改為 `stringResource(id = R.string.xxx)`
4. 測試各語系切換是否正常顯示

**相關檔案**：

- `app/src/main/java/com/kkday/member/view/memberpage/MemberPageScreen.kt`（已標記 TODO）
- `libs/app_resource/src/main/res/values*/strings.xml`

### 11.2 瀑布流 API 待處理

**說明**：目前會員頁瀑布流使用首頁的 waterfall API（`GetWaterfallListPagingUseCase`、
`GetWaterfallFilterUseCase`），需改為會員頁專用 API。

**待處理項目**：

| 項目          | 目前狀態                               | 目標                                           |
|-------------|------------------------------------|----------------------------------------------|
| 瀑布流 UseCase | 使用 `GetWaterfallListPagingUseCase` | 新增 `GetMemberPageWaterfallListPagingUseCase` |
| 篩選 UseCase  | 使用 `GetWaterfallFilterUseCase`     | 新增 `GetMemberPageWaterfallFilterUseCase`     |
| 瀑布流 API 端點  | `/api/v2/home/waterfall`           | `/api/v2/member/product-list`（待後端確認）         |
| 篩選 API 端點   | `/api/v2/home/waterfall/filter`    | `/api/v2/member/waterfall/filter`（待後端確認）     |
| Repository  | `HomeRepository`                   | 新增 `MemberPageRepository` 或擴充現有 Repository   |
| ViewModel   | `MemberPageViewModel` 注入首頁 UseCase | 改注入會員頁專用 UseCase                             |

**處理步驟**：

1. 等待後端提供會員頁專用 waterfall API 端點與參數規格（包含瀑布流與篩選）
2. 在 `:data:networking:api` 新增 API 介面（或擴充現有）
3. 在 `:data:repository` 實作 Repository
4. 在 `:domain:usecase` 新增 `GetMemberPageWaterfallListPagingUseCase` 與
   `GetMemberPageWaterfallFilterUseCase`
5. 修改 `MemberPageViewModel`，注入新的 UseCase
6. 移除 `MemberPageScreen.kt` 與 `MemberPageViewModel.kt` 中的 TODO 註解
7. 測試瀑布流載入、分頁、篩選切換、錯誤處理

**相關檔案**：

- `app/src/main/java/com/kkday/member/view/memberpage/MemberPageViewModel.kt`（已標記 TODO）
- `app/src/main/java/com/kkday/member/view/memberpage/MemberPageScreen.kt`（已標記 TODO）
- `app/src/main/java/com/kkday/member/view/homeV2/useCase/GetWaterfallListPagingUseCase.kt`（參考）
- `app/src/main/java/com/kkday/member/view/homeV2/useCase/GetWaterfallFilterUseCase.kt`（參考）

---

## 十、維護任務（後期）

### 10.1 多國語系待處理

**說明**：目前 Header 區塊的部分文字為 hard code，需要新增對應的多國語系字串資源。

**待處理項目**：

| 位置                | 目前 hard code 文字 | 建議字串資源 key                        | 狀態          |
|-------------------|-----------------|-----------------------------------|-------------|
| 未登入 Header - 標題   | "發現享受會員禮遇"      | `member_label_discover_benefits`  | 待新增         |
| 未登入 Header - 副標題  | "探索下一段旅程"       | `member_label_explore_journey`    | 待新增         |
| 未登入 Header - 按鈕   | "注册/登录"         | `member_label_login_or_sign_up`   | **已存在**，需改用 |
| 已登入 Header - 管理賬戶 | "管理賬戶 >"        | `member_label_account_management` | 待新增         |

**處理步驟**：

1. 在 `libs/app_resource/src/main/res/values/strings.xml` 新增英文字串
2. 在各語系資料夾新增對應翻譯（zh-rTW、zh-rCN、ja-rJP、ko-rKR、th-rTH、vi-rVN 等）
3. 修改 `MemberPageScreen.kt`，將 hard code 改為 `stringResource(id = R.string.xxx)`
4. 測試各語系切換是否正常顯示

**相關檔案**：

- `app/src/main/java/com/kkday/member/view/memberpage/MemberPageScreen.kt`（已標記 TODO）
- `libs/app_resource/src/main/res/values*/strings.xml`

### 10.2 瀑布流 API 待處理

**說明**：目前會員頁瀑布流使用首頁的 waterfall API（`GetWaterfallListPagingUseCase`、
`GetWaterfallFilterUseCase`），需改為會員頁專用 API。

**待處理項目**：

| 項目          | 目前狀態                               | 目標                                           |
|-------------|------------------------------------|----------------------------------------------|
| 瀑布流 UseCase | 使用 `GetWaterfallListPagingUseCase` | 新增 `GetMemberPageWaterfallListPagingUseCase` |
| 篩選 UseCase  | 使用 `GetWaterfallFilterUseCase`     | 新增 `GetMemberPageWaterfallFilterUseCase`     |
| 瀑布流 API 端點  | `/api/v2/home/waterfall`           | `/api/v2/member/product-list`（待後端確認）         |
| 篩選 API 端點   | `/api/v2/home/waterfall/filter`    | `/api/v2/member/waterfall/filter`（待後端確認）     |
| Repository  | `HomeRepository`                   | 新增 `MemberPageRepository` 或擴充現有 Repository   |
| ViewModel   | `MemberPageViewModel` 注入首頁 UseCase | 改注入會員頁專用 UseCase                             |

**處理步驟**：

1. 等待後端提供會員頁專用 waterfall API 端點與參數規格（包含瀑布流與篩選）
2. 在 `:data:networking:api` 新增 API 介面（或擴充現有）
3. 在 `:data:repository` 實作 Repository
4. 在 `:domain:usecase` 新增 `GetMemberPageWaterfallListPagingUseCase` 與
   `GetMemberPageWaterfallFilterUseCase`
5. 修改 `MemberPageViewModel`，注入新的 UseCase
6. 移除 `MemberPageScreen.kt` 與 `MemberPageViewModel.kt` 中的 TODO 註解
7. 測試瀑布流載入、分頁、篩選切換、錯誤處理

**相關檔案**：

- `app/src/main/java/com/kkday/member/view/memberpage/MemberPageViewModel.kt`（已標記 TODO）
- `app/src/main/java/com/kkday/member/view/memberpage/MemberPageScreen.kt`（已標記 TODO）
- `app/src/main/java/com/kkday/member/view/homeV2/useCase/GetWaterfallListPagingUseCase.kt`（參考）
- `app/src/main/java/com/kkday/member/view/homeV2/useCase/GetWaterfallFilterUseCase.kt`（參考）

### 10.3 Tracking 實作說明

**已實作（沿用舊頁面事件）**：

- `trackClickAvatar()` →
  `RxEventTracker.memberSettingMemberModifyClicked(VALUE_LOYALTY_FROM_MEMBER_INFO)`
- `trackClickLoyaltyCenter()` → `RxEventTracker.memberLoyaltyBtnClicked()`

**未實作（舊頁面無對應事件）**：

- X 關閉按鈕
- 聊天按鈕
- 設定按鈕
- 首頁按鈕

**相關檔案**：

- `app/src/main/java/com/kkday/member/view/memberpage/MemberPageViewModel.kt`
- `app/src/main/java/com/kkday/member/view/memberpage/MemberPageFragment.kt`

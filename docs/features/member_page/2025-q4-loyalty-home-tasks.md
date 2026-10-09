# 2025 Q4 Loyalty — 首頁任務與估時

- **需求與設計**：見 [2025-q4-loyalty-spec.md](2025-q4-loyalty-spec.md)
- **本文件**：首頁現況分析、需求對照、任務細分、開發時間估時。
- **估時前提**：以下為 **AI 開發估時**（以 Cursor/Agent 輔助實作、程式生成與重構為前提，約為傳統估時 55–65%）。

---

## 一、現有程式分析

### 1.1 入口與架構

| 項目 | 路徑／說明 |
|------|------------|
| 入口 | `HomeV2Fragment` → Compose `HomeV2Screen` |
| ViewModel | `HomeViewModelV2`（Koin） |
| 狀態 | `HomeUiState`（themeCategories, homeData, upcomingOrder, crossSellInfo, couponBanner, waterfallDestination, continueSearchKeywords 等） |
| 版面 | 單一 `LazyVerticalStaggeredGrid(columns=2)`，FullLine 與 2 欄瀑布流混排 |

### 1.2 區塊順序（由上而下）

| 序 | 區塊 | 條件 | 備註 |
|----|------|------|------|
| 0 | 背景圖 | 固定 | Box 層，`homepage_top_bg_img`，隨 scroll alpha |
| 1 | 白色圓角 Surface | 固定 | 內含搜尋列與以下區塊，用於 progress 計算 |
|   | SearchBarWithContinueSearch | 固定 | 繼續搜尋關鍵字 |
|   | ThemeShortcutsItem | themeCategories 非空 | 主題快捷 |
|   | ShortcutsFirstPurchaseItem | 首單優惠需顯示 | 首單優惠 |
|   | UpcomingOrderItem | upcomingOrder 非空 | 即將到來訂單 |
|   | CrossSellScreen | crossSell + upcomingOrder 皆有 | CrossSell |
|   | CouponBannerItem | couponBanner 有且未過期 | Coupon Banner |
|   | RecentlyViewedProdItem | 最近瀏覽有資料 | 最近瀏覽 |
| 2 | DestinationFilterItem | 有 waterfall 目的地且已有推薦卡 | key=filter，可 Sticky |
| 3 | ShimmerRecommendItem / 瀑布流 items | 依 loadState / waterfallDestination | Banner/Product/Destination/Campaign 卡 |
| 4 | WaterfallAppendIngItem | append Loading | 載入更多 |
| 5 | WaterfallFooterPaginationEndItem | 到底 | 分頁結束 |
| 6 | FooterStringItem | footerString 非空 | 頁尾字串 |
| — | ShortcutsCollapsingToolbar | 固定 | 頂部疊層，依 progress 收合 |
| — | Sticky Filter | showStickyFilter | 收合時篩選置頂 |

### 1.3 上滑收合邏輯

- **NestedScrollConnection**：依白色容器高度計算可滑動範圍，`toolbarOffsetHeightPx` 驅動 toolbar 高度。
- **progress**：由白色容器 `whiteContainerScreenY`、`whiteContainerHeight` 與 `collapseThreshold`（minToolbarHeight + statusBarHeight）線性計算；用於背景圖、白色 Surface、頂部 Surface 的 alpha。
- **showStickyFilter**：當 filter item 到達 sticky 位置或已滑過 filter 時顯示置頂篩選；與 `AnimatedVisibility` 進出場。

### 1.4 登入／未登入差異（現況）

- 資料面：`upcomingOrder`、`crossSellInfo`、`recentlyViewedProduct` 等依 API 回傳有無；未強制依登入狀態切換整頁版面。
- UI 面：同一套區塊順序，僅依資料有無顯示；未登入時多數個人化區塊不顯示。

---

## 二、需求對照（Figma vs 現況）

| Spec 項目 | Figma node-id | 現況 | 差距摘要 |
|-----------|----------------|------|----------|
| 首頁未登入 | 5768:42638 | 同一套版面，資料空則不顯示區塊 | 需對照：區塊種類、順序、未登入專用元件是否一致 |
| 首頁已登入 | 5302:6764 | 同上，有資料則顯示 | 需對照：已登入專用區塊與順序 |
| 未登入上滑收合 | 5855:49101 | 已有上滑收合與 progress | 需對照：動效與閾值是否一致 |
| 已登入上滑收合 | 5802:25039 | 同上 | 需對照：是否需不同閾值或動效 |
| 新增與修改 | — | 依產品說明細化 | 待產品列出具體變更項 |

**說明**：Figma 節點若在 MCP 取不到，可於桌面版開啟該檔案並切到對應 frame 後再取；實作前建議以 Figma 連結逐項對照。

### 2.1 首頁 UI／工程細節現況

| 項目 | 狀態 | 備註 |
|------|------|------|
| 現有區塊與順序 | OK | 見 §1.2，與程式一致 |
| 上滑收合邏輯 | OK | progress、Sticky Filter、NestedScroll 已記錄 |
| 登入／未登入現況 | OK | 依資料有無顯示，未用明確 isLoggedIn 切版 |
| Figma 逐項差異表 | 待補 | 需開 Figma 對「未登入／已登入／收合」產出 |
| 新增與修改清單 | 待產品 | H5 依產品給的項目再細拆 |
| 資料／API 對應 | 見下 | 區塊與資料來源對照 |
| 追蹤／埋點 | 見下 | 現有首頁追蹤是否需調整 |

**設計稿 Icon 對照（程式內已有）**

| 用途 | 路徑 | 備註 |
|------|------|------|
| KK Points（線條） | `libs/designsystem/design/.../ic_kkday_points_line.xml` | 設計系統 |
| KK Points（彩色） | `ic_kkday_points_color.xml` | 設計系統 |
| KK Points（線條） | `libs/app_resource/.../ic_kkdaypoints_line.xml` | app_resource |
| Loyalty（線條） | `ic_loyalty_line.xml` | design + app_resource |
| Loyalty 銀／白金／鑽石 | `ic_loyalty_sliver_color`, `ic_loyalty_platinum_color`, `ic_loyalty_diamond_color` | designsystem/design |
| Loyalty 黃金（04） | 設計系統尚無專用 icon，暫用 `ic_loyalty_line` | 待設計補上後替換 |

**Bottom Tab（會員）**：Figma [5859-51280](https://www.figma.com/design/lhlUGHS1963vcOg9iKjnYl/2025-q4-Loyalty-program?node-id=5859-51280&m=dev)。已實作：登入後依會員等級顯示對應 icon（銀 01 → sliver_color、白金 02 → platinum_color、鑽石 03 → diamond_color、黃金 04 → 暫用 loyalty_line）。等級常數：`LoyaltyMemberInfo.TIER_SILVER/PLATINUM/DIAMOND/GOLD`（01/02/03/04）。

實作時依 Figma 指定選用；若設計稿有新增 icon 再走 style-dictionary／設計系統流程。

**數字顯示規則（點數／數量）**

- ≤999：顯示原數字（例：999）
- ≥1000：顯示 `999+`
- 實作：`Int.toCountDisplayString()`（`libs/base/.../IntExtension.kt`），會員頁點數已套用；首頁／其他顯示點數處請一併使用。

**區塊 ↔ 資料來源（工程對照）**

| 區塊 | 狀態欄位／來源 |
|------|----------------|
| 主題快捷 | `themeCategories`（HomeUiState） |
| 首單優惠 | `homeData.firstPurchase` |
| 即將到來訂單 | `upcomingOrder` |
| CrossSell | `crossSellInfo`、`upComingOrderState` |
| Coupon Banner | `couponBanner` |
| 最近瀏覽 | `recentlyViewedProducts` |
| 目的地篩選＋瀑布流 | `waterfallDestination`、`waterfallListPaging`（ViewModel） |
| Footer | `footerString` |

**首頁登入時 API（沿用舊 API）**

| 用途 | API |
|------|-----|
| 會員狀態 | `GET /v2/loyalty/member/info` |
| KK Points 餘額 | `GET /v2/member/points` |

### 2.3 Loyalty unlock 相關 API 盤點

**GET `v2/loyalty/member/unlock/notice`**

| 項目 | 說明 |
|------|------|
| 用途 | 取得「解鎖會員等級」通知內容，回傳 `UnlockNotice(unlock_tier)`。 |
| 觸發時機 | 已登入且 `!hasUnlockedLoyaltyProgram()` 時：**首頁 viewReady**（`HomeReducer`）、**「我的」viewReady**（`UserReducer`）會 dispatch `getLoyaltyAllNotice()` → `LoyaltyReducer` 內呼叫此 API。 |
| 結果寫入 | `AppState.loyaltyUnlockNotice()`，並經 `RxDBHelper` 同步至 `PersistentManager`。 |
| 顯示位置 | **會員／Loyalty 頁**（`LoyaltyActivity`）：依 `unlockNotice.unlockTier` 顯示 `LoyaltyUnlockDialogFragment`（有使用 API 回傳）。**首頁**（`HomeFragment`／`HomeV2Fragment`）：顯示 `LoyaltyNoticeDialog`，但目前寫死 `TIER_SILVER`，未使用 API 的 tier。 |

**POST `v2/loyalty/member/unlock`**

| 項目 | 說明 |
|------|------|
| 用途 | 通知後端「使用者已確認／解鎖」；不回傳供 UI 顯示的內容。 |
| 觸發時機 | 使用者在 **Loyalty 頁**看到解鎖彈窗後，點擊確認／解鎖 → `LoyaltyPresenter.handleUnlockNotice()` → dispatch `HANDLE_UNLOCK_NOTICE` → `LoyaltyReducer.handleUnlockNotice()` 內呼叫 `notifyLoyaltyUnlock()`（並同時打 tier/exp notice read）。 |
| 備註 | 打完後會設 `hasUnlockedLoyaltyProgram = true`，之後不再打 unlock/notice。 |

**開發前確認：首頁架構下能否取得這兩支 API**

| 項目 | 現況 |
|------|------|
| API 定義 | 已有：`KKdayService.getLoyaltyMemberInfo(currency)`、`getMemberPoints(lang)`，對外經 `NetworkApi`/`RetrofitApi`。 |
| 目前誰呼叫 | `UserReducer.viewReady`（由 **UserPresenter** 在「我的」頁 viewReady 時 dispatch）會呼叫這兩支，結果寫入 **AppState**（`memberPoints()`、`loyaltyMemberInfo()`）。 |
| 首頁是否取得得到 | **目前無法**。`HomeViewModelV2` 只依賴 `HomeUseCases`，未注入 Store/AppState，也沒有取得會員狀態或 KK Points 的 UseCase；且兩支 API 僅在用戶進入「我的」頁時才會被觸發。 |
| 建議做法 | 二擇一或並行：（1）**訂閱 Reductor**：首頁注入 Store，訂閱 `AppState.memberPoints()` / `loyaltyMemberInfo()`，並在進入首頁（或 Main viewReady）且已登入時觸發一次取得（例如 dispatch 與 User 相同的 fetch），或（2）**首頁自拉**：在 HomeUseCases 新增 GetLoyaltyMemberInfo / GetMemberPoints（或合併）UseCase，由 HomeViewModelV2 在已登入時呼叫並寫入 HomeUiState。開發時需先決定採用哪一種並補上對應依賴與觸發時機。 |

### 2.2 首頁取得會員狀態／KK Points — 規劃與已變更記錄

**採用方案**：首頁自拉、加在 ViewModel 層（較好維護）。不訂閱 Reductor，由 HomeViewModelV2 透過 UseCase 呼叫 API 並寫入 HomeUiState。

**規劃步驟（尚未全數實作前可僅做規劃）**

| 步驟 | 內容 |
|------|------|
| 1 | 新增 `GetLoyaltyMemberInfoUseCase`：依賴 `PersistentManager`（currency），呼叫 `NetworkApi.sharedInstance().getLoyaltyMemberInfo(currency)`，以 `kotlinx.coroutines.rx2.awaitFirst` 轉成 suspend，回傳 `LoyaltyMemberInfo?`。 |
| 2 | 新增 `GetMemberPointsUseCase`：依賴 `PersistentManager`（language），呼叫 `NetworkApi.sharedInstance().getMemberPoints(lang)`，同上轉 suspend，回傳 `MemberPointsInfo`（失敗時回傳 `MemberPointsInfo.defaultInstance`）。 |
| 3 | `HomeUiState` 新增欄位：`loyaltyMemberInfo: LoyaltyMemberInfo?`、`memberPoints: MemberPointsInfo`。 |
| 4 | `HomeUseCases` 注入上述兩 UseCase，對外暴露 `suspend fun getLoyaltyMemberInfo()`、`suspend fun getMemberPoints()`。 |
| 5 | `HomeViewModelV2` 在 `init` 內呼叫 `getMemberInfoAndPoints()`：`viewModelScope.launch` 依序呼叫兩 UseCase，將結果寫入 `_uiState`。未登入時 API 可能失敗，回傳 null/default 即可。 |
| 6 | （可選）若需僅在已登入時才打 API，可再注入 `AppSharedData` 或新增 `GetIsLoggedInUseCase`，在 `getMemberInfoAndPoints()` 內先判斷再呼叫。 |

**已變更記錄**（以下變更已還原，僅留紀錄供日後依規劃重做時對照）

| 檔案 | 變更摘要 |
|------|----------|
| **新增** `app/.../homeV2/useCase/GetLoyaltyMemberInfoUseCase.kt` | 單一 UseCase，`PersistentManager` 取 currency，`NetworkApi.sharedInstance().getLoyaltyMemberInfo(...).awaitFirst()`，回傳 `LoyaltyMemberInfo?`。 |
| **新增** `app/.../homeV2/useCase/GetMemberPointsUseCase.kt` | 單一 UseCase，`PersistentManager` 取 language，`NetworkApi.sharedInstance().getMemberPoints(...).awaitFirst()`，回傳 `MemberPointsInfo`。 |
| `HomeUiState.kt` | 新增 import `LoyaltyMemberInfo`、`MemberPointsInfo`；`data class` 新增 `loyaltyMemberInfo: LoyaltyMemberInfo? = null`、`memberPoints: MemberPointsInfo = MemberPointsInfo.defaultInstance`。 |
| `HomeUseCases.kt` | 建構子新增 `getLoyaltyMemberInfoUseCase`、`getMemberPointsUseCase`；新增方法 `suspend fun getLoyaltyMemberInfo()`、`suspend fun getMemberPoints()`。 |
| `HomeViewModelV2.kt` | `init` 尾端新增 `getMemberInfoAndPoints()`；新增 private 函式 `getMemberInfoAndPoints()`：`viewModelScope.launch` 內呼叫兩 UseCase 並 `_uiState.value = _uiState.value.copy(loyaltyMemberInfo = ..., memberPoints = ...)`。 |

**追蹤**：現有 `EventTracker.sharedInstance().homePage(...)`（HomePage_Loaded）；區塊點擊多經 `HomeEventClickListener`。改版若有新區塊或新事件，需補埋點規格。

---

## 三、首頁任務細分與估時（AI 開發）

### H1 — 首頁未登入版面對齊 Figma

| 子任務 | 內容 | AI 開發估時（人天） |
|--------|------|---------------------|
| H1.1 | 對照 Figma「首頁未登入」與現有區塊清單，產出差異表（區塊種類、順序、文案、佔位） | 0.25 |
| H1.2 | 依差異表調整/新增區塊（僅未登入顯示的區塊或佔位） | 0.5 |
| H1.3 | 未登入狀態下隱藏/替換僅登入顯示區塊，確保與 Figma 一致 | 0.25 |
| **小計** | | **1** |

### H2 — 首頁已登入版面對齊 Figma

| 子任務 | 內容 | AI 開發估時（人天） |
|--------|------|---------------------|
| H2.1 | 對照 Figma「首頁已登入」與現有區塊，產出差異表 | 0.25 |
| H2.2 | 依差異表調整已登入專用區塊與順序 | 0.5 |
| H2.3 | 串接登入狀態（若尚未注入），確保已登入時資料與版面一致 | 0.25 |
| **小計** | | **1** |

### H3 — 未登入上滑收合

| 子任務 | 內容 | AI 開發估時（人天） |
|--------|------|---------------------|
| H3.1 | 對照 Figma「未登入上滑收合」與現有 progress/閾值 | 0.15 |
| H3.2 | 必要時調整未登入時收合動效或閾值 | 0.35 |
| **小計** | | **0.5** |

### H4 — 已登入上滑收合

| 子任務 | 內容 | AI 開發估時（人天） |
|--------|------|---------------------|
| H4.1 | 對照 Figma「登入上滑收合」與現有邏輯 | 0.15 |
| H4.2 | 若設計要求與未登入不同，區分兩套閾值/動效並接登入狀態 | 0.35 |
| **小計** | | **0.5** |

### H5 — 首頁新增/修改功能

| 子任務 | 內容 | AI 開發估時（人天） |
|--------|------|---------------------|
| H5.1 | 依產品「新增與修改」清單拆成具體項目（UI/文案/連結/追蹤） | 0.25 |
| H5.2 | 逐項實作與驗證（依實際項數可再拆子項） | 0.75 |
| **小計** | | **1** |

### M7 — Scaffold 與 TopAppBar 整合（會員頁）✅

| 子任務 | 內容 | 狀態 | AI 開發估時（人天） |
|--------|------|------|---------------------|
| M7.1 | 將最外層 Box 改為 Scaffold | ✅ | 0.1 |
| M7.2 | 實作下滑收合效果：Header 收合時顯示 TopAppBar | ✅ | 0.3 |
| M7.3 | TopAppBar 未登入：「注册/登录」可點擊；已登入：頭像+會員名 | ✅ | 0.1 |
| M7.4 | 參考設計稿調整收合閾值與動畫 | ✅ | 0.2 |
| **小計** | | | **0.7** |

**設計稿規格**（Figma node-id=5914:38031）：
- 完整規格區域：https://www.figma.com/design/lhlUGHS1963vcOg9iKjnYl/2025-q4-Loyalty-program?node-id=5914-38031&m=dev
- 未登入 header bar：node-id=5914:42407
- 已登入 header bar：node-id=5914:42437

**TopAppBar 規格**：
- 高度：56dp（不含 status bar 44dp）
- 背景：白色
- 陰影：`shadow-[0px_1px_4px_0px_rgba(38,50,56,0.12)]`
- **未登入**：
  - 標題：「注册/登录」（Subtitle-lg：16sp/600/24lineHeight，居中）
  - 右側：設定按鈕（ic_setting_line，20dp）
  - 點擊標題：觸發 onLoginClick
- **已登入**：
  - 左側：頭像（32dp，avatar-1）
  - 標題：會員名（Subtitle-lg：16sp/600/24lineHeight，最多 1 行，超過省略）
  - 右側：設定按鈕（ic_setting_line，20dp）
  - 點擊頭像/名字：觸發 onAccountManageClick
- 顯示時機：progress > 0.7 時淡入

**實作摘要**：
- 檔案：`app/src/main/java/com/kkday/member/view/memberpage/MemberPageScreen.kt`
- 變更：
  1. 最外層改用 `Scaffold`，`topBar` 參數設定 `MemberPageTopAppBar`
  2. **改用 Material3 標準 `TopAppBarScrollBehavior`**（與 DestinationPage 一致）
  3. 使用 `TopAppBarDefaults.exitUntilCollapsedScrollBehavior()` 處理收合
  4. 透過 `nestedScroll(scrollBehavior.nestedScrollConnection)` 連接滑動事件
  5. 使用 `scrollBehavior.state.heightOffset` 計算收合進度（取代手動計算）
  6. TopAppBar 使用 `AnimatedVisibility` 包裝，依 `collapseProgress > 0.7f` 淡入淡出
  7. 已登入：頭像用圓形 Box + 會員名首字，點擊觸發 `onAccountManageClick`
  8. 未登入：「注册/登录」文字置中，點擊觸發 `onLoginClick`
  9. 右側設定按鈕統一使用 `ic_setting_line`（20dp）
  10. Status bar 延伸處理：所有 Header 元件使用 `windowInsetsTopHeight`

**技術優化**：
- 從自訂 `NestedScrollConnection` 改為標準 `TopAppBarScrollBehavior`
- 與專案其他頁面（搜尋頁、目的地頁）保持一致
- 程式碼更簡潔，狀態管理由 Material3 自動處理

### 緩衝與整合

| 項目 | AI 開發估時（人天） |
|------|---------------------|
| 整合測試、回歸、修 bug | 0.5 |
| **首頁總計（不含會員頁）** | **約 4.5 人天** |

---

## 四、依賴與備註

- **估時**：上表為 AI 輔助開發估時；若改為傳統開發，可約以 1.8–2x 換算。
- **H1 / H2**：若 Figma 與現況差異小，估時可下修；若需新增多個元件或改順序，可上修。
- **H3 / H4**：若設計與現有收合一致，H3.2、H4.2 可僅做確認（估時可再壓低）。
- **H5**：實際估時依「新增與修改」項數再細分；若有新 API 或追蹤規格，需另加接口與埋點時間。
- **登入狀態**：若專案尚未在首頁注入明確的「已登入／未登入」狀態，H1.3、H2.3、H4.2 需一併考慮從 Auth/User 取得並驅動 UI。

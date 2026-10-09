# 會員頁瀑布流研究：首頁瀑布流區塊與會員頁複用／模組化

## 一、首頁瀑布流區塊現況

### 1.1 API

| 用途 | API | 說明 |
|------|-----|------|
| 篩選選項 | `GET v3/home/waterfall_filter` | 回傳目的地篩選 (WaterfallDestinations)，用於「推薦／日本／韓國…」 |
| 列表 | `POST v3/home/waterfall_list` | Body: start, timezone, destination, page_token, impression；回傳 HomeExplore (session_id, page_token, homeWaterfallCards) |

### 1.2 資料與分頁

- **HomeRepository**（`libs/feature/home_page`）：`getWaterfallList(WaterfallListRequestBody)` → `HomeExplore`。
- **HomeExplore**：`explore.homeWaterfallCards` 為 `List<HomeWaterfallCard>`。
- **HomeWaterfallCard**（libs/model）：四種卡
  - `BannerCard`：banner 圖
  - `ProductCard`：`data: B2CProductCardData`（商品卡）
  - `DestinationCard`：目的地卡
  - `CampaignCard`：活動卡，內含多個 B2CProductCardData
- **分頁**：`WaterfallListPagingSource`（app/homeV2）+ `GetWaterfallListPagingUseCase`，PagingConfig pageSize 20、prefetchDistance 5。

### 1.3 UI 結構（HomeScreen）

- 單一 **LazyVerticalStaggeredGrid**（2 欄）包住整頁：上方 hero、快捷鍵、cross-sell 等，中間「目的地篩選」，再來才是瀑布流 items。
- **fullLineCount**：瀑布流之前所有 `item(span = FullLine)` 的數量，用來算每個 waterfall item 的 `actualIndex`。
- **itemLayoutMap**：依 `onGloballyPositioned` 記錄每個 item 的 column（0/1）與 size，用來做左右 padding，讓兩欄對齊。
- 瀑布流區塊：`items(count = personalRecommendCard.itemCount)` 內依 `waterfallCard` 型別渲染：
  - BannerCard → MKTBannerCardItem
  - ProductCard → **HomeProductCard**
  - DestinationCard → DestinationCardItem
  - CampaignCard → MKTProdCardItem

### 1.4 商品卡（HomeProductCard）

- **位置**：`app/.../view/homeV2/presentation/components/HomeProductCard.kt`
- **輸入**：`B2CProductCardData`、cardIndex、sessionId、destinationCode、subSection
- **依賴**：design system、CurrencyDisplayManager、IProductPageLaunchHelper、**HomeWaterfallListEventHelper**（曝光／點擊追蹤）、RecommendSectionName.HOME_PG_INFINITY_LOOP、product_core 的 MktTag
- **結論**：UI 是標準商品卡（圖、標題、價、標籤），但追蹤與 section 名稱綁在「首頁瀑布流」。

---

## 二、會員頁最下方做瀑布流要怎麼做

### 2.1 商品卡「一樣」

- **做法**：沿用同一張卡 UI，差別只在「追蹤來源」。
  - **選項 A**：直接複用 `HomeProductCard`，在會員頁傳入會員專用的 sessionId／sectionName（需改 HomeProductCard 或 Helper 支援可插 section）。
  - **選項 B**：把「商品卡 UI」抽成共用 Composable（例如在 `libs/feature/product_core` 或 shared UI），輸入 `B2CProductCardData` + 可選的追蹤 callback／section 參數，首頁與會員頁各自包一層傳入自己的追蹤邏輯。
- 若只做會員頁、不打算動首頁，可先在會員頁複製一份 HomeProductCard 並把 Section 改成會員頁專用，最快。

### 2.2 資料來源（已確認：兩頁 API 不同、回傳格式相同）

- **首頁**：`GET v3/home/waterfall_filter`、`POST v3/home/waterfall_list`。
- **會員頁**：**不同 API**（端點與參數由後端提供），但**回傳格式與首頁相同**（例如皆為 `HomeExplore` → `homeWaterfallCards: List<HomeWaterfallCard>`）。
- **結論**：
  - **Model 完全共用**：`HomeExplore`、`HomeWaterfallCard`、`WaterfallListRequestBody` 等（libs/model）兩頁都用。
  - **打 API 的層要分開**：首頁用現有 `HomeRepository.getWaterfallList`；會員頁需**會員專用 API 方法**（例如 MemberRepository 或 HomeRepository 擴充 `getMemberWaterfallList`），回傳型別同樣是 `HomeExplore`。
  - **PagingSource 可抽象**：抽成「依賴一個 suspend (page, token, destination, impression) → HomeExplore 的函數」，首頁注入 `homeRepository::getWaterfallList`，會員頁注入會員 API，這樣分頁邏輯（prevKey/nextKey、parse cards）只寫一次，只有打哪支 API 不同。

### 2.3 版面：會員頁「最下方」瀑布流

- 會員頁若為單一可捲動列表（例如 Column + LazyColumn），做法可以是：
  - 上方：新會員頁既有區塊（頭像、點數、設定列等）。
  - 最下方：一個 **瀑布流區塊**。
- 實作方式兩種：
  - **方式 1**：整頁一個 `LazyVerticalStaggeredGrid`，前面數個 `item(span = FullLine)` 是會員區塊，後面再接「目的地篩選 + 瀑布流 items」——邏輯類似首頁，但 fullLineCount 只算會員區塊，較單純。
  - **方式 2**：上方用一般 Column/LazyColumn，底部用 `LazyVerticalStaggeredGrid` 只負責瀑布流（不需要 fullLineCount／itemLayoutMap 與前面區塊對齊），實作更簡單，但捲動可能是「兩段」要處理嵌套捲動或一體成形的滾動體驗。
- 若採方式 1，可把「從目的地篩選到瀑布流結束」抽成一個 Composable（見下節）。

---

## 三、模組化 vs 重做

### 3.1 適合「模組化」的部份（兩頁 API 不同、回傳格式相同）

| 項目 | 說明 |
|------|------|
| **Model** | 完全共用：`HomeExplore`、`HomeWaterfallCard`、`B2CProductCardData`、`WaterfallListRequestBody`（或會員 API 的 request 結構若不同則僅 request 分開，response 仍用同一批 model）。 |
| **商品卡 UI** | 抽成共用 Composable，接受 `B2CProductCardData` + 追蹤參數（sectionName、sessionId、cardIndex 等），首頁／會員頁都用這張卡。 |
| **瀑布流區塊 Composable** | 輸入：`LazyPagingItems<HomeWaterfallCard>`、`List<WaterfallDestination>`、篩選 callback、sessionId、sectionName。內部：目的地篩選 + `items(count) { ... }` 依 card 型別渲染 Banner / **共用商品卡** / Destination / Campaign。兩頁都呼叫同一 Composable，只差追蹤參數。 |
| **PagingSource 抽象** | 抽成「通用」PagingSource，依賴一個 `suspend (page, pageToken, destination, impression) -> HomeExplore` 的函數（或介面）。首頁注入 `homeRepository::getWaterfallList`，會員頁注入會員 waterfall API，分頁邏輯（parse cards、prevKey/nextKey）只寫一次。 |
| **UseCase** | 可抽成 `GetWaterfallListPagingUseCase(fetch: suspend (WaterfallListRequestBody) -> HomeExplore)` 或依介面取得資料，首頁／會員頁各自提供自己的 fetch 實作。 |

### 3.2 需分開、不共用的部份

| 項目 | 說明 |
|------|------|
| **API 端點與 Request** | 首頁：`v3/home/waterfall_filter`、`v3/home/waterfall_list`。會員頁：會員專用 API（例如 `v3/member/waterfall_filter`、`v3/member/waterfall_list` 或後端指定），Repository/ApiService 各打各的。 |
| **ViewModel** | 首頁用 HomeViewModelV2；會員頁用自己的 ViewModel，持有會員 waterfall 的 paging flow + 篩選 state，並呼叫會員 API。 |
| **LazyGrid 與 fullLineCount** | 首頁整頁一個 Grid 含 hero 等；會員頁自己的 Grid 只含會員區塊 + 瀑布流，不共用同一份 LazyGrid 實作。 |

### 3.3 建議取捨（兩頁 API 不同、回傳格式相同）

- **共用**：Model、商品卡 UI、瀑布流區塊 Composable、PagingSource 抽象（依注入的 fetch 打不同 API）、追蹤只差 sectionName/sessionId。
- **分開**：首頁／會員頁各自的 API 呼叫、Repository 方法、ViewModel；篩選選項若會員有專用 API 則篩選資料來源也分開。
- 這樣**不必重做**：只多一個會員 waterfall API + 注入到同一套 PagingSource/UI，即可在會員頁最下方接上同一種瀑布流。

---

## 四、實作檢查清單（會員頁瀑布流，兩頁 API 不同、回傳格式相同）

- [ ] 後端：會員頁 waterfall 與篩選的 API 端點與 request 欄位（回傳格式與首頁一致：HomeExplore / homeWaterfallCards）。
- [ ] 會員 API 層：新增會員 waterfall 列表（及若有篩選則篩選）的 ApiService + Repository 方法，回傳型別用現有 `HomeExplore`。
- [ ] PagingSource：抽成依賴 `suspend (request) -> HomeExplore` 的抽象，首頁注入 home API，會員頁注入會員 API。
- [ ] UseCase：抽成接受 fetch 的 GetWaterfallListPagingUseCase，或會員頁專用 UseCase 內呼叫會員 Repository。
- [ ] 商品卡：抽成共用 Composable + 追蹤參數（sectionName、sessionId），會員頁傳 MEMBER_PG_RECOMMEND 等。
- [ ] 瀑布流區塊：抽成共用 Composable（LazyPagingItems + 篩選 + 四種卡），兩頁皆用，只差追蹤與資料來源。
- [ ] 版面：會員頁 LazyVerticalStaggeredGrid（會員區塊 + 瀑布流）或 上方區塊 + 底部瀑布流，二擇一。
- [ ] 篩選：若會員頁有目的地篩選且 API 不同，則篩選資料來源用會員 API，UI 仍可共用 DestinationFilterItem。

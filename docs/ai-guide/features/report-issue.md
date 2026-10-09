> **UNVERIFIED** | 此文件由 AI 自動產生，尚未經人工驗證。
> 產生時間：2026-08-03
> 觸發來源：OpenSpec change `report-issue-zendesk-migration`（Freshdesk → Zendesk 遷移需求分析）
> 請開發者確認檔案清單與資料流是否正確後，移除此標記。

# 問題申訴（Report Issue）技術文件

> 自動產生 | 最後更新：2026-08-03

> **⚠️ 此功能正在遷移中**：Freshdesk 合約 2026 年九月底到期，送出路徑將改為 `App → b2c-api → BM → Zendesk`。
> 本文件描述**遷移前的現況**，作為回歸測試基準。對應 OpenSpec change：`report-issue-zendesk-migration`。

---

## 概述

- **所在 Module**：`:libs:feature:order_page`（入口之一在 `:libs:feature:chat`）
- **UI 入口**：`ReportIssueActivity` → `ReportIssueFragment`
- **功能描述**：使用者從訂單明細頁或聊天室進入，選擇問題類型、填寫描述、選擇性上傳最多 2 張圖片，送出後建立客服工單。**現行由客戶端直連 Freshdesk 建單**，不經自家後端。

---

## 檔案清單

```
Router
 └─ KRouterConst.kt:37                      → libs/routing/.../com/kkday/router/
      PAGE_REPORT_ISSUE = "kkday://report_issue"
      KEY_REPORT_ISSUE_ARGS = "key_report_issue_args"  (L137)

UI（使用者介面）
 ├─ ReportIssueActivity.kt                  → libs/feature/order_page/.../presentation/view/
 ├─ ReportIssueFragment.kt（表單）           → libs/feature/order_page/.../presentation/
 ├─ ReportSuccessFragment.kt（成功頁）       → libs/feature/order_page/.../presentation/
 ├─ ReportIssueScreen.kt（Compose 表單）     → libs/feature/order_page/.../presentation/compose/
 ├─ IssueTypesScreen.kt（題型 BottomSheet）  → libs/feature/order_page/.../presentation/compose/
 └─ ReportSuccessScreen.kt（Compose 成功頁） → libs/feature/order_page/.../presentation/compose/

入口顯示判斷（四處，共用同一份收窄規則）
 ├─ OrderDetailReportIssueSectionScreen.kt      → libs/feature/order_page/.../new_detail/compose/
 │     shouldShowReportIssueSection(summary: SummaryData)
 │     唯一呼叫端：NewOrderDetailScreen.kt（新版明細頁）
 ├─ OrderDetailViewInfoConverter.kt             → app/.../view/order/detail/order/
 │     shouldShowReportIssueForOldDetailPage(orderDetail: OrderDetailInfo)（舊版明細頁）
 ├─ ChatServiceBottomSheet.kt                   → libs/feature/chat/.../compose/
 │     shouldShowReportIssueEntry(isNewOrder, orderInfo)
 │     唯一正式呼叫端：ChatScreen.kt（ChatBotActivity 新聊天室，寫死 isNewOrder = false）
 └─ CustomerServiceScreen.kt                    → app/.../view/order/contact/
       shouldShowReportIssueEntry(isNewOrder, isMarketPlace, msgHandler)
       唯一正式呼叫端：ContactMarketPlaceActivity（商城聊聊，固定 isMarketPlace = true）
       ContactUsActivity 也用同一畫面，但已無啟動點（死碼）

> 改動任一入口的顯示規則時，四處都要同步 —— OP-1643 就是因為只收窄了前三處而漏掉商城聊聊。

ViewModel
 └─ ReportIssueViewModel.kt                 → libs/feature/order_page/.../presentation/viewModel/

Helper（multipart 組裝 + Freshdesk header）
 └─ ReportIssueHelper.kt                    → libs/feature/order_page/.../helper/

Repository
 └─ OrderRepository.kt:167-186              → libs/feature/order_page/.../domain/repository/

Network（API 定義）
 └─ IOrderApiService.kt:185-201             → libs/networking/api/.../service/order_api/

Constants
 └─ Constants.kt:63                         → libs/base/.../common/util/
      KKDAY_FRESHDESK_TICKET_URL = "https://kkday.freshdesk.com/api/v2/tickets"

Data Model
 ├─ ReportIssue.kt                          → libs/model/.../resource/order/
 │     ReportIssue / TicketInfo / TicketResult / QuestionType
 ├─ ReportIssueCreateTicket.kt              → libs/model/.../resource/order/
 │     ReportIssueCreateTicket / ReportIssueResultAttachment
 ├─ ReportIssueViewTicket.kt                → libs/model/.../resource/order/
 └─ request/FAQReportIssueRequest.kt        → libs/model/.../resource/order/

DI
 └─ orderModule.kt:18, 36                   → libs/feature/order_page/.../di/
      L18: single { provideApiService(get(named(KKNetworking.RETROFIT_NAME_DEFAULT))) }
      L36: viewModel { ReportIssueViewModel(get()) }
```

**無單元測試檔案。**

---

## 資料流

### 主流程：進入頁面 → 取得題組與工單模板

```
訂單明細頁 / 聊天室 / ContactUsActivity
 │  RouterHelper.dispatch("kkday://report_issue")
 │  .withObj(KEY_REPORT_ISSUE_ARGS, ReportIssueArgs(
 │      orderId, msgHandler, bdTags, orderMasterId, orderStatus, isMarketPlace))
 ↓
ReportIssueActivity
 │  @RouterParam 接 ReportIssueArgs，拆成 6 個 bundle key 傳給 Fragment
 ↓
ReportIssueFragment.initAction()
 │  呼叫：reportIssueViewModel.getReportIssue(orderId)
 │        reportIssueViewModel.setReportSuccessOrderId(orderId)
 ↓
ReportIssueViewModel.getReportIssue():89
 │  呼叫：orderRepository.getReportIssue(FAQReportIssueRequest(orderMid))
 ↓
OrderRepository.getReportIssue():167
 │  safeApiCall { apiResultData(orderService.getReportIssue<ReportIssue>(order)) }
 ↓
IOrderApiService.getReportIssue():185
 │  POST {B2C_BASE_URL}/v2/faq/report-issue    Body: { "order_mid": "..." }
 ↓
b2c-api → b2c-service
```

回傳流：

```
ReportIssue { ticket_info, ticket_result, question_types[] }
 ↓
Repository：ApiResult.Success<ReportIssue>
 ↓
ViewModel：_reportIssue.value（MutableStateFlow<ReportIssue?>）
           _trackViewReportPg.emit(true)
 ↓
UI：ReportIssueScreen（商品名稱 / 訂單編號） + IssueTypesScreen（題型清單）
```

### 送出流程（Freshdesk，兩段式）

```
使用者點送出
 ↓
ReportIssueFragment.onSubmitButtonClickListener():178
 │  checkIfFiledRequired() → 若 isAllFieldFinish 才繼續（無 in-flight guard）
 ↓
ReportIssueViewModel.createReportIssue():164
 │  _loading.emit(true)
 │
 ├─① ReportIssueHelper.getFreshdeskTicketHeader():13
 │     → mapOf("Authorization" to "NzZCV1VXeDJIcGZrSjY4VG0wSUE=")   ⚠️ 硬編碼
 │
 ├─② ReportIssueHelper.getReportIssueRequestBody():15
 │     → MultipartBody（欄位見下表）
 │
 ├─③ OrderRepository.createReportIssueTicket():173
 │     → POST https://kkday.freshdesk.com/api/v2/tickets
 │        ⚠️ 走 B2C 的 OkHttp client，B2CInterceptor 會注入會員 token 等 header
 │     ← retrofit2.Response<ReportIssueCreateTicket>
 │
 │     isSuccessful == false → _showUploadFail.emit(true) → 失敗 dialog，return
 │     _loading.emit(false)   ← ⚠️ 在第二次 GET 之前就關閉
 │
 └─④ OrderRepository.getReportIssueSuccessResult():182
       → GET https://kkday.freshdesk.com/api/v2/tickets/{id}
          （唯一目的：取 created_at 與 attachments）
       ← ReportIssueViewTicket { created_at, attachments }
          ⚠️ 不檢查 isSuccessful，失敗時用 defaultInstance
       ↓
       _reportIssueViewTicket.emit() → Fragment replace 成 ReportSuccessFragment
       _reportSuccessViewInfo.copy(reportTime, hasAttachment) → ReportSuccessScreen
```

### Multipart 欄位對照

| form-data key | 值 | 來源 |
|---|---|---|
| `email` | `ticketInfo.email` | b2c `ticket_info.email` |
| `subject` | `ticketInfo.subject` | b2c `ticket_info.subject` |
| `description` | `issueContent` | 使用者輸入（≤5000 字，未做 HTML escape） |
| `type` | `ticketInfo.type` | b2c `ticket_info.type` |
| `tags[]` | `ticketInfo.tag.firstOrNull() ?: ""` | b2c `ticket_info.tags`，**只取第一個**，其餘丟棄 |
| `custom_fields[cf_complaint_item]` | `selectedQuestionType.cfComplaintItem` | 使用者選的題型（送中文字串，非 oid） |
| `custom_fields[<key>]` × N | `ticketInfo.customFields` 每個 key | JsonPrimitive → `asString`；否則 `Gson().toJson()` |
| `attachments[]` × 0–2 | temp File | filename 用 `File.name`（`.tmp` 隨機名），Content-Type **硬寫 `image/*`** |

> 若 b2c 回傳的 `custom_fields` 也含 `cf_complaint_item`，會送出兩個同名 part。

### 圖片處理流程

```
onImageClickListener():165
 │  PickMultipleVisualMedia(MEDIA_TYPE_MAX_NUM = 2)，ImageOnly，免權限
 ↓
pickMedia callback:41
 │  validNum = if (已選 1 張) 1 else 2
 │  setSelectedImage(uri.take(validNum))     → 預覽用 List<Uri>
 │  convertUriToFile(it)                     ⚠️ L46 呼叫後結果直接丟棄
 │  setSelectedFiles(mapOf(it to convertUriToFile(it)))  ⚠️ L47 又做一次
 ↓
convertUriToFile():193
 │  createTempFile() + contentResolver.openInputStream().copyTo()
 │  ⚠️ 純 byte copy，無 BitmapFactory / inSampleSize / compress / EXIF 處理
```

---

## 逐層說明

### UI 層
`ReportIssueActivity` 只負責接 Router 參數並塞 Fragment。表單與成功頁是**同一個 Activity 內 replace fragment**（`ReportIssueFragment.kt:101-103`），兩者透過 Koin `activityViewModel` 共用同一份 ViewModel state。

Compose 畫面由 `BaseComposeFragment.content()` 提供，狀態全部從 ViewModel 的 Flow `collectAsState()` 取得。題型選擇走 `KKBottomSheetDialog` + `IssueTypesScreen`。

### ViewModel 層
`ReportIssueViewModel` 繼承 `BaseViewModel`，全 StateFlow / SharedFlow，**無 Reductor**。

注意 `issueContent: String`（L50）與 `selectedImageFiles: Map<Uri, File>`（L61）是**普通 var，不是 Flow** — UI 不會觀察它們，只在送出時讀取。

`isSummitButtonEnable`（L69）雖然是 StateFlow 且有傳進 Compose，但 `ProblemsReportButtonItem` 內部完全沒使用（見技術債 4）。

### Repository 層
`OrderRepository` 對 report issue 有三個方法，**錯誤處理不一致**：

| 方法 | 是否 safeApiCall | 回傳 |
|---|---|---|
| `getReportIssue()` L167 | ✅ | `Flow<ApiResult<ReportIssue>>` |
| `createReportIssueTicket()` L173 | ❌ | `retrofit2.Response<ReportIssueCreateTicket>` |
| `getReportIssueSuccessResult()` L182 | ❌ | `retrofit2.Response<ReportIssueViewTicket>` |

後兩者直接把 Retrofit Response 拋回 ViewModel，例外不會被攔截。

### API 層

| Endpoint | 說明 |
|---|---|
| `POST v2/faq/report-issue` | 走 B2C base url，取題組與工單模板 |
| `POST @Url` | 絕對 URL 打 Freshdesk `/api/v2/tickets`，multipart |
| `GET @Url` | 絕對 URL 打 Freshdesk `/api/v2/tickets/{id}` |

三者**共用同一個 Retrofit instance**（`RETROFIT_NAME_DEFAULT`），因此對 Freshdesk 的請求也會經過 `B2CInterceptor`。

---

## View 方法清單（`ReportIssueFragment`）

| 方法 | 說明 |
|---|---|
| `content()` | Compose 入口，組 `ReportIssueScreen` 並綁定五個 callback |
| `initAction()` | 取題組 `getReportIssue(orderId)`、設定成功頁的 orderId |
| `observeData()` | 觀察 4 條 Flow：`loading`（loading dialog）、`showUploadFail`（失敗 dialog + 埋點）、`reportIssueViewTicket`（導向成功頁）、`trackViewReportPg`（頁面曝光埋點） |
| `onFragmentStart()` | `KKBottomSheetListener` 回呼，接題型 BottomSheet |
| `initBottomSheet()` | 建立並顯示題型選擇 BottomSheet |
| `setBottomSheetDialog()` | 把 `IssueTypesScreen` 塞進 BottomSheet 的 compose slot |
| `onQuestionTypeClickListener()` | 點題型欄位 → 開 BottomSheet |
| `onSelectQuestionType()` | 選定題型 → 寫回 VM + 關閉 BottomSheet |
| `onQuestionContentInput()` | 輸入問題描述 → 寫回 VM |
| `onImageClickListener()` | 啟動 Photo Picker |
| `onImageRemoveListener()` | 移除已選圖片（同時清 Uri 與 File，**temp 檔本體不刪**） |
| `onSubmitButtonClickListener()` | 必填檢查 → `createReportIssue()` + 點擊埋點（**無 in-flight guard**） |
| `convertUriToFile()` | Uri → temp File，純 byte copy，**無壓縮** |
| `getSelectedQuestionTypeIndex()` | 供 BottomSheet 標示目前選中項 |
| `getOrderId()` / `getMsgHandler()` / `getBdTags()` / `getOrderMasterId()` / `getOrderStatus()` / `getIsMarketplace()` | 從 arguments 取 Router 參數，皆有預設值 |

---

## ViewModel 方法清單（`ReportIssueViewModel`）

| 方法 | 說明 |
|---|---|
| `setReportSuccessOrderId()` L83 | 寫入成功頁要顯示的訂單編號 |
| `getReportIssue()` L89 | 取題組與 ticketInfo，`ApiResult.Loading/Success` 驅動 loading 與 `_reportIssue`（**未處理 Error 分支**） |
| `setSelectedQuestionType()` L111 | 記錄選中題型，同步更新 `isSummitButtonEnable` / `isAllFieldFinish` / `isSelectorError` |
| `setQuestionContent()` L120 | 記錄描述內容，同步更新按鈕狀態、成功頁預覽內容、`isTextFieldError` |
| `setSelectedImage()` L130 | 累加圖片 Uri（`distinct()` 去重） |
| `removeSelectedImage()` L137 | 移除圖片 Uri |
| `setSelectedFiles()` L144 | 累加 `Map<Uri, File>` |
| `removeSelectedFile()` L149 | 移除 File 對應 |
| `checkIfFiledRequired()` L156 | 送出前必填檢查，觸發兩個欄位的錯誤態 |
| `createReportIssue()` L164 | **送出主流程**：組 multipart → POST Freshdesk → 成功後 GET 取 created_at → 導向成功頁 |
| `trackViewReportIssuePg()` L202 | `View_ReportOrderIssuePg`，帶 msgHandler / bdTag / orderMid / orderMasterId / orderStatus / isMarketplace / questionIds |
| `trackClickReportIssueSubmit()` L229 | `Click_ReportOrderIssuePg_Submit`，property 同上 |
| `trackViewReportIssueSuccess()` L256 | `View_ReportOrderIssueSuccessPg`，帶 `TICKET_ID` |
| `trackReportIssueSubmitFail()` L270 | `Impression_ReportOrderIssuePg_SubmitFail` |

---

## 業務邏輯摘要

**入口顯示條件**

四處入口共用前兩道收窄條件：`msgHandler` 必須為 `SUPPLIER`（缺值視為 `KKDAY`，不顯示）、且**非商城訂單**（`is_marketplace`，明細頁的 `isSupplierProduct` 即此欄位）。商城訂單不論訂單狀態一律不顯示，因為商城的訊息系統無法定位到該筆訂單（OP-1643）。

| 入口 | 通過前兩道後的條件 |
|---|---|
| 新版訂單明細頁 | `isDeparted` 或 `orderStatusDisplay ∈ {DONE, CANCELED_USER, CANCELED_SUPPLY, CANCELING}`，且排除 `isUpcoming && DONE` |
| 舊版訂單明細頁 | `isDeparted` 或 `isCancelledOrApplyingCancelled` |
| 訂單訊息頁（新聊天室） | `!isNewOrder` — 唯一正式呼叫端寫死 `isNewOrder = false` |
| 商城聊聊 | `!isNewOrder` — 呼叫端固定 `isMarketPlace = true`，故實際恆不顯示 |

**表單規則**
- 問題類型：單選，來源 DCS 題組（經 b2c-service 下發）
- 問題描述：上限 5000 字，必填
- 圖片：最多 2 張，Photo Picker `ImageOnly`，無壓縮
- 送出按鈕：必填未完成時點擊只觸發錯誤態，不送出

**成功 / 失敗**
- 成功 → `ReportSuccessFragment`，顯示商品名稱、訂單編號、回報時間、問題類型、問題描述、已上傳照片提示
- 失敗 → 統一 `GeneralRoundedDialog`（`ReportOrderIssuePg_SubmitFailTitle` / `_SubmitFailContent` / `_SubmitFailNoted`，`setCanceledOnTouchOutside(false)`），**表單內容與已選圖片保留**，可直接重送
- **不依錯誤碼分支**，任何非 2xx 都是同一句失敗提示

**回報時間的取得**：Android 是送出成功後**再打一次 GET** 取 `created_at`（iOS 直接取建單回應，Web 由前端本地產生）。

---

## 已知技術債

| # | 項目 | 位置 | 說明 |
|---|---|---|---|
| 1 | **Freshdesk API key 硬編碼** | `ReportIssueHelper.kt:13` | `"NzZCV1VXeDJIcGZrSjY4VG0wSUE="` 明文存在於 APK，可被反編譯取得 |
| 2 | **第三方 domain 洩漏會員資料** | `orderModule.kt:18` + `NetworkConstants.kt:163-197` | Freshdesk 呼叫共用 B2C 的 OkHttp client，`B2CInterceptor` 無 host 白名單，會對 freshdesk.com 注入 `X_AUTH_TOKEN`、`MEMBER_UUID`、`ADVERTISING_ID`、經緯度、`UD1~UD5` 等 header |
| 3 | **網路例外會 crash** | `OrderRepository.kt:173,182` | 兩個 Freshdesk 呼叫不走 `safeApiCall`、無 try/catch，`BaseViewModel` 也無 `CoroutineExceptionHandler` → 斷線時 `IOException` 直接從 `viewModelScope` 拋出使 App crash，而非顯示失敗 dialog。失敗 dialog 只在 HTTP 非 2xx 時觸發 |
| 4 | **送出按鈕無 in-flight guard** | `ReportIssueScreen.kt:407-430` | `summitButtonEnable` 參數傳進來但**完全沒被使用**：背景色 L417 寫死、`clickable` L419 無 `enabled` 判斷。`createReportIssue()` 內部也沒有守門 → 連點會產生兩張工單 |
| 5 | **同一張圖被複製兩次** | `ReportIssueFragment.kt:46-47` | L46 的 `convertUriToFile()` 結果直接丟棄，L47 又做一次完整 I/O；temp 檔從不刪除（無 `deleteOnExit`、無 cleanup） |
| 6 | **圖片完全無壓縮** | `ReportIssueFragment.kt:193` | 相簿原檔直送，現代手機單張 3–12MB。專案已有 `IBitmapHelper.compressAndEncodeBitmap()` 可用但此處未使用 |
| 7 | **第二次 GET 無錯誤處理** | `ReportIssueViewModel.kt:183-187` | 不檢查 `isSuccessful`，失敗時落 `defaultInstance`（成功頁不顯示時間）；且 `_loading` 在 L179 就關閉，第二次 GET 期間畫面無遮罩 |
| 8 | **死碼：未使用的 ViewModel property** | `ReportIssueActivity.kt:25` | `by viewModels<ReportIssueViewModel>()` 宣告後從未被讀取，實際使用的是 Fragment 端 Koin 的 `activityViewModel` |
| 9 | **Model 欄位命名 bug** | `ReportIssueCreateTicket.kt:35` | `@SerializedName("content") val email: String` — 欄位名叫 `email` 但實際對應 `content` |
| 10 | **零測試覆蓋** | — | 無任何單元測試，`shouldShowReportIssueSection()` 這類純函式也沒測 |
| 11 | **KDoc 與實作不符** | `OrderDetailReportIssueSectionScreen.kt:95-101` | 註解說供應商商品是「除 HANDLE 外皆顯示」，實作是 `!isPendingPay` |
| 12 | **未使用常數** | `ReportIssueFragment.kt:223` | `MEDIA_TYPE_IMAGE_AND_GIF = "image/jpeg"` 宣告但未使用 |

---

## 相關筆記

- **遷移需求**：`openspec/changes/report-issue-zendesk-migration/`（Freshdesk → Zendesk，經 b2c-api → BM）
- **相關 feature doc**：[order-detail-compose.md](./order-detail-compose.md)（訂單明細頁入口）、[order-contact-support.md](./order-contact-support.md)（聊天室客服）
- **PRD 落差提醒**：PRD 附錄 A.7 稱「Android `SummaryData` 未宣告 `msgHandler`，需補上」— 實際 `OrderDetail.kt:245` 已宣告，getter L468 已 `?: MsgHandler.KKDAY` fallback，不需補欄位

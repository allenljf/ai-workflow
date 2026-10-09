# 優惠專區 技術文件

> 自動產生 | 最後更新：2026-03-19

---

## 概述

- **所在 Module**：`:app`
- **UI 入口**：`DealsFragment.kt`
- **功能描述**：以 WebView 內嵌方式呈現 KKday 優惠券與優惠活動頁面（`/coupons-n-best-deals/`），並透過 JavaScript Bridge 與 Native 層互動（登入、訂購、頁面樣式回傳）。

---

## 檔案清單

```
UI（使用者介面入口）
 ├─ DealsFragment.kt     → app/src/main/java/com/kkday/member/view/deals/
 └─ DealsActivity.kt     → app/src/main/java/com/kkday/member/view/deals/

Layout
 └─ fragment_deals.xml   → app/src/main/res/layout/

ViewModel（UI 狀態管理）
 └─ （無獨立 ViewModel，Fragment 直接操作 WebView）

Domain（業務邏輯 UseCase）
 └─ （無 UseCase，此功能為 WebView 嵌入，不經過 Domain 層）

Data（資料層）
 └─ PersistentManager.kt（介面 PreferencesHelper）
      → libs/base/src/main/java/com/kkday/library/common/storage/

Network（WebView URL 組裝）
 └─ appendQueryParameter()（StringExtension）
      → libs/base/src/main/java/com/kkday/library/common/extension/StringExtension.kt

JavaScript Bridge
 ├─ BridgeWebView.kt     → libs/tool/webjs/src/main/java/com/kkday/library/common/webjs/
 ├─ JsContainerApi.kt    → libs/tool/webjs/src/main/java/com/kkday/library/common/webjs/
 └─ JavascriptInterfaceUtil.kt → app/src/main/java/com/kkday/member/util/

路由
 └─ KRouterConst.PAGE_DEALS = "kkday://deals"
      → libs/routing/src/main/java/com/kkday/router/KRouterConst.kt
```

---

## 資料流

### 主流程：頁面載入（initView）

```
UI（DealsFragment）
 │  initView() 被呼叫
 │  1. getNowUrl() 組出基礎 URL：
 │     https://<webUrl>/<langKey>/coupons-n-best-deals/
 │     若 arguments 含有 DEALS_PAGE_URL 且語系符合，優先使用傳入的 URL
 │  2. appendQueryParameter(loginToken, currency) 附加查詢參數
 │  3. BridgeWebView.loadUrl(currentUrl)
 │  4. setPageStyle(pageStyle, loadingDialog)
 │     → pageStyle: "tabBar"（底部 Tab 嵌入）或 "other"（獨立頁面）
 │  5. setEventBus(eventBus)
 │  6. addJavascriptInterface(JavascriptInterfaceUtil, "android")
 │  7. JavascriptInterfaceUtil.initialize(requireActivity())
 ↓
BridgeWebView（libs/tool/webjs）
 │  loadUrl() → LightAgent WebView 載入 HTML
 │  JsContainerApi 掛載為 "container" JS interface：
 │    - container.dealsPageStyle() → 回傳 { pageStyle: "tabBar" | "other" }
 │    - container.showLoading() / hideLoading()
 │    - container.setTitleBar(json)
 │    - container.getAppVersion()
 ↓
Web 頁面（KKday 前端）
 │  呼叫 android.callKKdayMemberApp(json) 觸發 Native 動作
 │  呼叫 android.postMessage(json) 送出追蹤事件
```

### 回傳流（Web → Native）

```
Web 頁面
 │  android.callKKdayMemberApp({ type: "login_required", payload: { link } })
 ↓
JavascriptInterfaceUtil.callKKdayMemberApp()
 │  type == "login_required" → SocialLoginSplashActivity.launch()
 │  type == "booking"        → OrderFormFillingActivity.launch()（經過資料轉換）
 ↓
onActivityResult（REQUEST_CODE_LOGIN / REQUEST_CODE_EMAIL_LOGIN_OR_SIGN_UP）
 │  resultCode == RESULT_CODE_LOGIN_SUCCESS → DealsFragment.refresh()
 ↓
UI（DealsFragment）
 │  refresh() → BridgeWebView.showLoading() + 延遲 1 秒重新 loadUrl
```

---

## 逐層說明

### UI 層

`DealsFragment` 繼承 `BaseFragment<FragmentDealsBinding>`，無獨立 ViewModel。

- `initView()`：組裝最終 URL（基礎路徑 + 語系 + 登入 Token + 幣別），交由 `BridgeWebView` 載入，同時設定頁面樣式與 JS Bridge。
- `refresh()`：登入成功或收到 `KKMainEvent.MainLogout` 事件後，由 `MainActivity` 觸發，重新載入頁面（含最新 Token）。
- `onBack()`：委派給 `BridgeWebView.onBack()`，若 WebView 有歷史記錄則返回上一頁，否則回傳 `false` 交由 Activity 處理。

`DealsActivity`（路由：`kkday://deals`）：獨立頁面入口，以 `PAGE_STYLE_OTHER` 建立 `DealsFragment` 並 replace 到 `layout_main`，主要用於從外部 Deep Link 或跨頁跳轉進入。

`MainActivity` 中的 Tab 整合：
- 當 A/B 測試開關 `isDealSwitchOn` 為 `true` 時，底部導覽第四個 Tab 從「願望清單」切換為「優惠專區」。
- `DealsFragment` 以 `PAGE_STYLE_TAB` 建立，懶加載並 replace 到 `layout_deal` 容器。

### ViewModel 層

此功能**無獨立 ViewModel**。狀態與操作直接在 `DealsFragment` 中處理，透過 `PersistentManager`（Koin inject）取得 Token 與幣別，透過 `KKEventBus` 接收事件。

### UseCase 層

**無 UseCase**。此功能為純 WebView 嵌入，資料邏輯由 Web 前端負責，Native 端僅負責 URL 組裝與 JS Bridge 橋接，不涉及 Domain 層業務邏輯。

### Repository 層

**無 Repository**。登入 Token 與幣別由 `PersistentManager` 從 `SharedPreferences`（加密存儲）讀取：

- `getLoginTokenInWebView()`：從 `SecurePreferences` 讀取 `KEY_IN_APP_WEBVIEW_TOKEN`，失敗時回傳 `"GET_LOGIN_TOKEN_FAILED"`。
- `getCurrency()`：讀取使用者幣別設定。

### API 層

此功能**無 Retrofit API 呼叫**。所有商品資料、優惠內容均由 WebView 內 Web 頁面自行向後端請求，Native 僅透過 URL Query Parameter 傳遞身分識別資訊：

| Query Parameter | 來源 | 說明 |
|---|---|---|
| `inAppWebViewLogin` | `getLoginTokenInWebView()` | WebView 登入 Token |
| `currency` | `getCurrency()` | 使用者幣別 |
| `inAppWebViewSource` | 固定值 | 標識來源為 App 內嵌 WebView |

---

## View 方法清單

### DealsFragment

| 方法 | 說明 |
|------|------|
| `initView()` | 組裝 URL 並載入 WebView，設定頁面樣式、EventBus、JS Interface |
| `initAction()` | 空實作（無額外 UI 事件綁定） |
| `observeData()` | 空實作（無 ViewModel 資料觀察） |
| `getNowUrl()` | 根據當前語系組出基礎 URL，優先使用 arguments 傳入的 URL |
| `refresh()` | 顯示 Loading 後延遲 1 秒重新載入（附最新 Token / 幣別） |
| `onBack()` | 委派 WebView 歷史回退，若無歷史則回傳 false |
| `getPageStyle()` | 從 arguments 取得頁面樣式常數（tabBar / other） |
| `onActivityResult()` | 捕捉登入成功結果，觸發 refresh() |
| `newInstance()` | 靜態工廠，接受可選 url 與 pageStyle 參數 |

### DealsActivity

| 方法 | 說明 |
|------|------|
| `onCreate()` | 建立 `DealsFragment`（PAGE_STYLE_OTHER）並 replace 到 layout_main |
| `onBackPressed()` | 委派 `dealsFragment.onBack()`，false 時才真正返回 |
| `onActivityResult()` | 轉接給 super（登入結果由 Fragment 處理） |

---

## 業務邏輯摘要

- URL 以語系動態切換：`LocaleHelper.getCurrentLanguageType()` 取得 `langKey`，組入路徑。
- 若 arguments 提供的 URL 已包含正確語系路徑，優先使用該 URL；否則回退至預設優惠頁 URL。
- 登入後刷新：`onActivityResult` 偵測登入成功（`REQUEST_CODE_EMAIL_LOGIN_OR_SIGN_UP` 或 `REQUEST_CODE_LOGIN` + `RESULT_CODE_LOGIN_SUCCESS`），呼叫 `refresh()`。
- 登出後刷新：`MainActivity` 收到 `KKMainEvent.MainLogout` EventBus 事件，若 `dealsFragment != null`，呼叫 `dealsFragment!!.refresh()`，重新載入頁面（此時 Token 應為空，WebView 將以未登入狀態顯示）。
- 頁面樣式控制：`PAGE_STYLE_TAB`（底部 Tab 嵌入，隱藏 TitleBar）vs `PAGE_STYLE_OTHER`（獨立頁面，顯示 TitleBar）。
- JS Bridge 登入跳轉：Web 呼叫 `android.callKKdayMemberApp` 傳入 `type: "login_required"` 時，僅接受 KKday domain 的 link（`isKKdayDomainName()` 驗證），防止任意跳轉。
- JS Bridge 訂購跳轉：`type: "booking"` 時，將 WebView 傳回的 `WebBookingInfo` 轉換為 `OrderSpecificationData` 與 `PriorityBookingData`，啟動 `OrderFormFillingActivity`。

---

## 已知技術債

- `DealsFragment` 無 ViewModel，業務邏輯（URL 組裝、refresh 觸發）直接寫在 Fragment，不符合 MVVM 分層規範。
- 無 UseCase 與 Repository 抽象，Token / 幣別讀取透過 Koin inject `PersistentManager` 直接在 UI 層完成。
- `JavascriptInterfaceUtil` 以 `object`（singleton）實作，持有 `WeakReference<Activity>`，若頁面切換未及時呼叫 `initialize()` 可能指向舊 Activity。
- `BridgeWebView` 中的 `JsContainerApi` 使用 `GlobalScope.launch`，未綁定生命週期，存在記憶體洩漏風險。
- `onActivityResult` 已棄用（應改用 Activity Result API），目前仍沿用舊 API。

## 相關筆記
- [01-architecture](../01-architecture.md)
- [02-modules](../02-modules.md)
- [03-ui-patterns](../03-ui-patterns.md)
- [05-networking](../05-networking.md)
- [06-data-layer](../06-data-layer.md)
- [07-concurrency](../07-concurrency.md)
- [home](home.md)
- [order-detail-compose](order-detail-compose.md)
- [sku-activity-shell](sku-activity-shell.md)

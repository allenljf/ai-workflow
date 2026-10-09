# 會員資料頁 技術文件

> 自動產生 | 最後更新：2026-03-19

---

## 概述

- **所在 Module**：`:app`
- **UI 入口**：`UserFragment.kt`（會員頁總覽）→ `ProfileActivity.kt`（資料檢視）→ `UserFormFillingActivity.kt`（資料編輯）
- **功能描述**：讓已登入使用者查看個人資料（姓名、生日、電話、Email、護照、國籍等），並進入編輯表單修改與上傳頭像。

---

## 檔案清單

```
UI（使用者介面入口）
 ├─ UserFragment.kt              → app/src/main/java/com/kkday/member/view/user/
 ├─ ProfileActivity.kt           → app/src/main/java/com/kkday/member/view/user/profile/
 └─ UserFormFillingActivity.kt   → app/src/main/java/com/kkday/member/view/user/form/

ViewModel（僅 UserFragment 使用）
 └─ UserViewModel.kt             → app/src/main/java/com/kkday/member/view/user/

Presenter（MVP + Reductor，ProfileActivity / UserFormFillingActivity 使用）
 ├─ UserPresenter.kt             → app/src/main/java/com/kkday/member/view/user/
 ├─ ProfilePresenter.kt          → app/src/main/java/com/kkday/member/view/user/profile/
 └─ UserFormFillingPresenter.kt  → app/src/main/java/com/kkday/member/view/user/form/

Reductor（Redux-like 狀態管理）
 ├─ UserActions.kt / UserReducer.kt             → app/src/main/java/com/kkday/member/reducer/user/
 ├─ ProfileActions.kt                           → app/src/main/java/com/kkday/member/reducer/user/
 └─ UserFormFillingActions.kt / UserFormFillingReducer.kt → app/src/main/java/com/kkday/member/reducer/user/

Network（API 定義）
 ├─ KKdayService.kt（Retrofit 介面）    → app/src/main/java/com/kkday/member/network/retrofit/
 ├─ NetworkApi.kt（API 代理層）         → app/src/main/java/com/kkday/member/network/
 └─ Api.kt（介面定義）                  → app/src/main/java/com/kkday/member/network/

Data Model
 ├─ MemberData.kt / Member.kt           → 透過 AppState 在 Reductor Store 中管理
 ├─ UserInfo.kt                         → shared/base 或 networking 層（OAuth 登入資訊）
 └─ ProfileViewInfo.kt                  → app/src/main/java/com/kkday/member/view/user/profile/
```

---

## 資料流

### 主流程 A：載入個人資料（ProfileActivity 頁面載入）

```
ProfileActivity
 │  onResume() 觸發
 │  呼叫：presenter.viewReady(friendId)
 ↓
ProfilePresenter
 │  dispatch：profileActions.viewReady(friendId)
 │  訂閱 AppState：languageType / nationalitiesData / userInfo / member / friend
 ↓
ProfileReducer（Reductor 處理）
 │  NetworkApi.sharedInstance().getMember(language)
 ↓
NetworkApi → KKdayService（Retrofit）
 │  GET v2/member?lang=<language>
 ↓
後端 API
```

### 主流程 B：提交個人資料編輯（UserFormFillingActivity 點擊完成）

```
UserFormFillingActivity
 │  使用者點擊「完成」按鈕
 │  呼叫：presenter.clickDoneButton(isAllRequiredFilled, isPersonal, member, friend, photo, ...)
 ↓
UserFormFillingPresenter
 │  dispatch：userFormFillingActions.clickDoneButton(...)
 ↓
UserFormFillingReducer
 │  驗證欄位完整性
 │  dispatch：userFormFillingActions.updateMember(member, photo)
 ↓
UserFormFillingReducer.updateMember()
 │  NetworkApi.sharedInstance().updateMember(member)
 │  若 hasUploadPhoto：NetworkApi.sharedInstance().createMemberPhoto(photo)
 ↓
KKdayService（Retrofit）
 │  PATCH v2/member（更新會員資料）
 │  POST  v2/member/photo（上傳頭像，條件式）
 ↓
後端 API
```

### 回傳流 A：載入個人資料

```
後端 API
 │  Response<MemberData>
 ↓
NetworkApi / AppState（Reductor Store）
 │  MemberData 更新至 AppState.member
 ↓
ProfilePresenter.register()
 │  Observables.combineLatest(languageType, nationalitiesData, userInfo, member)
 │  呼叫 mvpView.updateData(languageType, nationalitiesData, userInfo, member)
 ↓
ProfileActivity.updateData()
 │  member.toProfileViewInfo(context, userInfo) → ProfileViewInfo
 │  setBasicInfo(profileInfo)
 └─ profileAdapter.updateData() 更新 RecyclerView 顯示姓名、生日、電話等欄位
```

### 回傳流 B：提交編輯

```
後端 API
 │  Response<Any>（PATCH v2/member）
 ↓
UserFormFillingReducer.updateMemberResult()
 │  成功：dispatch refreshUserInfo → 重新拉取 AppState.member
 │  失敗：state.setShowFailDialog(true).setErrorMessage(errorMsg)
 ↓
UserFormFillingPresenter.register() 訂閱 AppState
 │  hasUpdatedUserInfo → mvpView.updateUserInfoSuccessful()
 │  showFailDialog    → mvpView.showFailDialog()
 ↓
UserFormFillingActivity
 └─ 成功：finish()（關閉頁面，回到 ProfileActivity）
    失敗：顯示 alertStateDialog 錯誤提示
```

---

## View 方法清單

### UserFragment

| 方法 | 說明 |
|------|------|
| `initView()` | 設定各按鈕點擊事件（登入、設定、優惠券、忠誠計畫等） |
| `initAction()` | 呼叫 `viewModel.getTravelGuideUrl()` 與 `getDCSFooterConfig()` |
| `observeData()` | 訂閱 ViewModel 的 StateFlow/LiveData（開發者模式、旅遊指南、信用卡管理顯示） |
| `onResume()` | 呼叫 `userPresenter.viewReady()` 並更新信用卡管理項目可見性 |
| `updateUserProfile()` | 根據登入狀態更新頭像、姓名顯示 |
| `updateUserInfo()` | 更新點數數字顯示 |
| `updateData()` | 根據語言設定顯示/隱藏旅遊指南、FAQ、越南條款 |
| `updateLoyaltyMemberInfo()` | 根據忠誠計畫等級更新 Banner 背景 |
| `updateInviteItem()` | 根據推薦功能 flag 顯示推薦或邀請好友按鈕 |
| `updateMissionItem()` | 根據任務功能 flag 顯示任務入口 |
| `showGoToGooglePlayDialog()` | 觸發 Google Play 評分流程 |
| `updateView()` | 語言切換後重建 Activity |

### ProfileActivity

| 方法 | 說明 |
|------|------|
| `onCreate()` | 初始化 Toolbar、RecyclerView、FAB 點擊事件 |
| `onResume()` | 呼叫 `presenter.viewReady(friendId)` 載入資料 |
| `onCreateOptionsMenu()` | 設定 AppBar 展開/收合時的編輯按鈕顯示 |
| `onOptionsItemSelected()` | 點擊 menu 編輯項目進入 `UserFormFillingActivity` |
| `setBasicInfo()` | 設定頭像、名稱顯示，處理好友/會員的顯示差異 |
| `updateData(member)` | 更新自己的個人資料（會員模式） |
| `updateData(friend)` | 更新同伴資料（好友模式） |

### UserFormFillingActivity

| 方法 | 說明 |
|------|------|
| `onCreate()` | 初始化 RecyclerView adapter、Toolbar、完成按鈕事件、ReCaptcha |
| `onDestroy()` | 清理 dialog、detachView |
| `onBackPressed()` | 顯示「是否放棄編輯」確認 dialog |
| `updateData()` | 根據 isPersonal 呼叫 `adapter.updateMember()` 或 `adapter.updateFriend()` |
| `showLoadingProgress()` | 顯示/隱藏 loading dialog |
| `updateUserInfoSuccessful()` | 更新成功後呼叫 `finish()` 關閉頁面 |
| `showFailDialog()` | 顯示錯誤提示 dialog |
| `showErrorMessage()` | 顯示底部 ErrorSnackbar |
| `launchSMSValidationActivity()` | 進入手機號碼 SMS 驗證頁 |
| `updateMemberTermsData()` | 顯示需同意的會員條款 checkbox |

---

## ViewModel 方法清單（UserViewModel）

| 方法 | 說明 |
|------|------|
| `init` | 初始化 footerDelegate、檢查開發者模式狀態、呼叫 `updateCreditCardItemVisibility()` |
| `updateCreditCardItemVisibility()` | 判斷貨幣為 TWD 且非 KKDAY 登入管道時，顯示信用卡管理項目 |
| `getTravelGuideUrl()` | 從 `HomeRepository` 取得旅遊指南 URL，更新 LiveData |
| `getDCSFooterConfig()` | 取得 DCS footer 設定（由 `FooterViewModelDelegate` 委派處理） |
| `setIsShowDevelopMode()` | 設定開發者模式顯示狀態 |
| `clickTextVersion()` | 版本號連點計數，達 10 次開啟開發者模式 |
| `getAppConfigList()` | 取得可切換的 App Config 清單（含 Custom1, E2E 選項） |
| `getMemberName()` | 根據語言類型決定姓名顯示順序（日文為姓+名，其他為名+姓） |
| `getExperimentAndVariantNameList()` | A/B 測試實驗清單（開發者模式用） |
| `switchVariant()` | 切換 A/B 測試 variant（開發者模式用） |
| `trackClickHelpCenter()` | 追蹤點擊 Help Center 事件 |

---

## 業務邏輯摘要

- **登入狀態差異**：`UserFragment` 依登入狀態顯示「登入按鈕」或「會員資料」，未登入則點擊忠誠計畫、邀請等入口都會導向登入頁
- **會員/好友模式**：`ProfileActivity` 與 `UserFormFillingActivity` 共用，以 `PROFILE_TYPE` Intent Extra 區分（`ProfileViewInfo.MEMBER` 或 `ProfileViewInfo.FRIEND`），資料來源與顯示邏輯不同
- **姓名顯示優先順序**：`ProfileActivity` 優先使用 `Member.firstName/lastName`（若 `isValidName()`），否則 fallback 到 `UserInfo.firstName/lastName`（OAuth 資料）
- **頭像上傳**：照片透過 `ActivityResultContracts.PickVisualMedia` 選取，壓縮至 `DEFAULT_AVATAR_IMAGE_COMPRESSED_MAX_SIDE_SIZE` 後 Base64 編碼，上傳至 `POST v2/member/photo`
- **ReCaptcha 整合**：提交表單時帶入 `RecaptchaManager.reCaptchaToken`，防止機器人操作
- **會員條款驗證**：編輯前若後端要求同意條款（`v2/member/terms`），需先勾選才可提交
- **信用卡管理入口**：僅在貨幣為 TWD 且非 KKDAY 登入管道（Apple/Google/FB等社交登入）時顯示
- **錯誤處理**：API 錯誤透過 Reductor AppState 的 `showFailDialog` / `showErrorMessage` 欄位驅動 UI，錯誤訊息以 `response.metadata.desc` 或預設文字顯示

---

## 已知技術債

- `UserFragment` 同時持有 `UserViewModel`（MVVM）與 `UserPresenter`（MVP+Reductor），混用兩種架構模式
- `ProfileActivity` 與 `UserFormFillingActivity` 直接透過 `NetworkApi.sharedInstance()` singleton 呼叫 API，未實作 `domain:contract` Repository 介面分離
- 沒有獨立 UseCase 層，業務邏輯（欄位驗證、資料組合、條件判斷）全部散落在 Reducer 中
- `UserReducer` 在 `viewReady()` 中觸發多個並行 API 呼叫（好友清單、點數、推薦資訊、忠誠計畫等），未使用 UseCase 封裝各自業務
- 個人資料模型同時存在 `Member`（Reductor AppState）與 `UserInfo`（OAuth token 相關），兩者需在 `toProfileViewInfo()` 中手動合併，增加維護複雜度

## 相關筆記
- [01-architecture](../01-architecture.md)
- [02-modules](../02-modules.md)
- [03-ui-patterns](../03-ui-patterns.md)
- [05-networking](../05-networking.md)
- [06-data-layer](../06-data-layer.md)
- [07-concurrency](../07-concurrency.md)
- [notification-center](notification-center.md)
- [order-detail-compose](order-detail-compose.md)
- [sku-activity-shell](sku-activity-shell.md)
- [wishlist](wishlist.md)

# 會員頁 (User Tab) UI 功能與 API 對照

## 區塊一：頭像區 (component_profile)

| UI 功能 | 顯示內容 | 資料來源 / API | 備註 |
|--------|----------|----------------|------|
| 未登入：登入/註冊按鈕 | 按鈕 | 無 API，依 `AppState.hasAlreadyLoggedIn()` | 點擊 → SocialLoginSplashActivity |
| 未登入：設定圖示 | 圖示 | 無 | 點擊 → SettingActivity |
| 已登入：大頭貼 | 照片 | `UserInfo.photoUrl` | 來自**登入流程 API 回傳** (LoginReducer.loginResult)，非會員頁專用 API |
| 已登入：會員姓名 | 姓名 | `UserInfo` (firstName/lastName/displayName) | 同上，UserViewModel.getMemberName() 依語系排列 |
| 已登入：會員等級文案 | 如「白銀會員」 | `LoyaltyMemberInfo.tier` → 對應字串 | **getLoyaltyMemberInfo**(currency) |
| 已登入：設定圖示 | 圖示 | 無 | 點擊 → SettingActivity |
| 點擊大頭貼 | - | 無 | 進入 ProfileActivity (MEMBER)，ProfileReducer 會打 **getMember**(lang) |

---

## 區塊二：優惠券／點數 (component_user_info)

| UI 功能 | 顯示內容 | 資料來源 / API | 備註 |
|--------|----------|----------------|------|
| 優惠券數量 | 數字或預設「-」 | 目前**無 B2C API** 回傳數量 | UserReducer.viewReady 內 getMemberCoupons 已註解，顯示邏輯用預設 |
| 點擊優惠券 | - | 無 | 開啟 Coupon 路由 (libs routing) |
| 點數 | 數字或預設「-」 | **getMemberPoints**(language) | UserReducer.viewReady 呼叫，結果進 AppState.memberPoints() |
| 點擊點數 | - | 無 | 開 KKDAY_POINT_URL 網頁 |

---

## 區塊三：列表項目 (PreferenceItem)

| UI 功能 | 顯示內容 | 資料來源 / API | 備註 |
|--------|----------|----------------|------|
| 願望清單 (item_wish) | 固定文案 | 無 | 點擊 → WishActivity |
| 信用卡管理 (item_credit_card) | 固定文案，顯示與否 | 無 API 取數；顯示條件：幣別 TWD 且登入管道非 KKDAY | UserViewModel.updateCreditCardItemVisibility()，點擊 → CreditCardListRouter |
| 會員等級 (item_loyalty) | 固定文案 | 無 | 點擊 → LoyaltyActivity；頭像區等級來自 getLoyaltyMemberInfo |
| 邀請 (item_invite) | 文案／紅點 | **getReferralData**(language, countryCode)；紅點與 **member().isUserPhoneVerified**、**remoteConfig.isReferralEnabled** 有關 | UserReducer.viewReady 打 getReferralData；member 來自本地/Profile 的 getMember 或登入後同步 |
| 任務 (item_mission) | 固定文案／紅點 | **getRemoteConfig** → isMissionEnabled；紅點與 isMissionPageClicked 等 | 顯示與否由 Remote Config 控制；點擊 → MissionActivity 或登入頁 |
| 常見問題 (item_faq) | 固定文案 | 無 | 點擊 → HelpCenterRouter |
| 營運規章 (item_operation_regulation) | 固定文案，顯示與否 | **getRemoteConfig** → vnTermsAndConditionsURL；僅越南語且 URL 非空時顯示 | 點擊開 PDF URL |
| 意見回饋 (item_feedback) | 固定文案 | 無 | 點擊 → UserFeedbackActivity，傳 userInfo.email |
| 關於 KKday (item_about_us) | 固定文案 | 無 | 點擊 → KKdayInfoActivity |
| KKday 導覽 (item_guide) | 固定文案，顯示與否 | **DCS**：`blog_url` (HomeRepository.getTravelGuideUrl) | 僅繁體顯示；點擊開 DCS 的 blog_url |
| 開發者模式 / 開產品頁 / Debug / AB testing / Show Contact Notification | 非 production 才顯示 | 無 | 本機設定與除錯用 |

---

## 區塊四：頁尾與錯誤

| UI 功能 | 顯示內容 | 資料來源 / API | 備註 |
|--------|----------|----------------|------|
| 版本號 (text_version) | BuildConfig.VERSION_NAME | 無 | 僅顯示 |
| App config 名稱 (text_app_config_name) | 當前選的 AppConfig 名稱 | 無 API，來自 AppState.selectedAppConfig | 非 production 顯示 |
| 頁尾文案 (text_footer) | 公司資訊 HTML | **DCS**：`app_footer_config` (AppRepository.getFooterString(lang)) | UserViewModel 透過 FooterViewModelDelegate.getDCSFooterConfig() |
| 網路錯誤 (layout_network_error) | 錯誤提示 | 無 API；顯示時機為各 API 回傳 hasNetworkUnavailableError | UserReducer 多個 result 會 setShowNetworkUnavailableError |

---

## 會員頁進入時會觸發的 API (UserReducer.viewReady，已登入)

| API | 用途 |
|-----|------|
| **getFriends**(language) | 好友列表 → 更新 AppState.friendLites()（會員頁列表未直接顯示筆數，供他處用） |
| **getMemberPoints**(language) | 點數 → 顯示在 component_user_info 點數 |
| **getReferralData**(language, countryCode) | 推薦資格與狀態 → 邀請項目文案／紅點／是否開推薦頁 |
| **getLoyaltyAllNotice**（內部再打） | 解鎖／階級／經驗值通知 → getLoyaltyUnlockNotice、getLoyaltyTierNotice、getLoyaltyExpNotice |
| **getLoyaltyMemberInfo**(currency) | 會員等級 → 頭像區等級文案與樣式 |

---

## 資料來源整理（非會員頁專用但會影響顯示）

| 資料 | 來源 |
|------|------|
| UserInfo（頭像、姓名） | 登入流程 API 回傳，LoginReducer 寫入 AppState |
| RemoteConfig（vnTermsAndConditionsURL, isReferralEnabled, isMissionEnabled） | **getRemoteConfig**（App 啟動等時機） |
| member（isUserPhoneVerified 等） | 本地快取或 **getMember**(lang)（如從 Profile 進入後寫入 AppState） |
| 旅遊導覽 URL | DCS `blog_url`（HomeRepository.getTravelGuideUrl） |
| 頁尾 | DCS `app_footer_config`（AppRepository.getFooterString） |

---

## API 清單（依 Api.kt / NetworkApi）

- `getMemberPoints(language)` — 點數
- `getFriends(language)` — 好友（會員頁 viewReady 會打，列表本身不顯示）
- `getReferralData(language, locale)` — 推薦
- `getLoyaltyMemberInfo(currency)` — 會員等級
- `getLoyaltyUnlockNotice()` / `getLoyaltyTierNotice()` / `getLoyaltyExpNotice()` — 等級相關通知（經 getLoyaltyAllNotice 觸發）
- `getRemoteConfig()` — 遠端設定（越南規章、推薦/任務開關等）
- `getMember(language)` — 會員詳情（Profile 進入時用，結果含 member 寫入 AppState）
- 登入 API — 回傳 UserInfo，供頭像與姓名
- DCS：`blog_url`、`app_footer_config` — 導覽連結與頁尾

---

## v2/loyalty/member/info 呼叫階段

`GET v2/loyalty/member/info`（getLoyaltyMemberInfo）在兩個階段會被呼叫：

| 階段 | 觸發時機 | 程式位置 | 參數 |
|------|----------|----------|------|
| **App 初始化** | 啟動並完成環境設定後（取得 IP、設定 AppConfig 等），執行 `appInitializedTasks`；僅在已登入時會打 | `AppReducer.appInitializedTasks()` | `persistentManager.getCountryCode()`（以 currency query 傳出） |
| **會員頁顯示** | 使用者切到會員 Tab → `UserFragment.onResume` → `userPresenter.viewReady()` → `UserActions.VIEW_READY` | `UserReducer.viewReady()` | `state.currency()` |

用途：取得會員等級（LoyaltyMemberInfo），寫入 `AppState.loyaltyMemberInfo()`，供頭像區等級文案與樣式（如「白銀會員」）使用。

---

## KK Points 相關 API

| 用途 | API | 方法 | 回傳 | 說明 |
|------|-----|------|------|------|
| **取得 KK Points 餘額** | `GET v2/member/points` | `getMemberPoints(language)` | `Response<MemberPoints>` | 會員頁點數數字來源；UserReducer.viewReady 呼叫，結果進 AppState.memberPoints()。KKdayService 約 829–832 行。 |
| **訂單點數試算** | `POST v2/points/estimate` | `getOrderKKPointsInfo(pointsData)` | `Response<OrderKKPointsInfo>` | 依訂單內容試算可折抵的 KK Points，非取餘額。 |

---

## 折扣券 API

| 用途 | API | 方法 | 回傳 | 說明 |
|------|-----|------|------|------|
| **會員優惠券列表** | `GET v2/member/coupons` | `getMemberCoupons(currency, timezone)` | `Response<PersonalCouponListInfo>` | Query：currency、timezone（app 用 TimeZone.getDefault().id）。優惠券列表頁用此 API。 |
| **折扣券數量** | 同上 | 同上 | `PersonalCouponListInfo.availableCoupons.size` | 無獨立「只回傳數量」的 API，數量由列表回傳的 availableCoupons.size 取得。會員頁目前未打此 API（已註解），故頭像區優惠券數字為預設。 |

---

## 任務管理 API

「有什麼任務可做」由後端透過下列 API 回傳，App 依 `MissionItemData` 顯示。

| 用途 | API | 方法 | 參數 | 回傳 |
|------|-----|------|------|------|
| 任務列表（未登入） | `GET v2/mission/list/un_login` | getUnLoginMissionList | country_code | `List<MissionItemData>` |
| 任務列表（已登入） | `GET v2/mission/list/status` | getMissionList | statuses[]（NEW, PROG, COMPLETE, DONE） | `List<MissionItemData>` |
| 任務詳情（未登入） | `GET v2/mission/{mission_id}/un_login` | getUnLoginMissionDetail | mission_id, country_code | MissionItemData |
| 任務詳情（已登入、未接） | `GET v2/mission/{mission_id}` | getMissionDetail | mission_id | MissionItemData |
| 已接任務詳情 | `GET v2/mission/record/{mission_record_id}` | getAcceptedMissionDetail | mission_record_id | MissionItemData |
| 接任務 | `POST v2/mission/{mission_id}/accept` | acceptMission | mission_id | MissionItemData |
| 領獎勵 | `POST v2/mission/{mission_id}/reward/claim` | claimMissionReward | mission_id | MissionItemData |

任務狀態（MissionStatusType）：UNLOGIN、NEW、PROG、COMPLETE、DONE、INVALID。已登入列表帶 statuses[] = NEW, PROG, COMPLETE, DONE。任務內容含 mission_name、mission_desc、rewards、progress_bar 等，由 API 回傳之 MissionItemData 決定。

---

## 邀請好友相關 API

### 推薦／邀請（Referral）

| 用途 | API | 方法 | 參數 | 回傳 |
|------|-----|------|------|------|
| 推薦資料（資格與狀態） | `GET v2/member/referral` | getReferralData | lang, locale | `Response<ReferralData>` |
| 推薦 Banner | `GET v2/referral/inviter/banner` | referralBanner（property） | 無 | `Response<ReferralBanner>` |
| 邀請碼列表 | `GET v2/referral/inviter/code` | getReferralInviterCodeList | currency | `Response<List<InviterCode>>` |

### 手機驗證（邀請流程需先驗證手機）

| 用途 | API | 方法 | 參數 | 回傳 |
|------|-----|------|------|------|
| 發送簡訊驗證碼 | `POST v2/member/verify/sms` | sendSMSVerificationCode | tel_area, mobile, Body(ReCaptchaToken) | `Response<Any>` |
| 驗證並儲存手機 | `POST v2/member/verify/check_and_save_number` | verifyPhoneNumber | tel_area, mobile, verify_code | `Response<Any>` |

### 好友（Friend，邀請後之好友列表等）

| 用途 | API | 方法 | 參數 | 回傳 |
|------|-----|------|------|------|
| 好友列表 | `GET v2/friend` | getFriends | lang | `Response<FriendLites>` |
| 單一好友詳情 | `GET v2/friend/{friend_id}` | getFriend | friend_id, lang | `Response<FriendData>` |
| 建立好友 | `POST v2/friend` | createFriends | Body(CreateFriendsPayload) | `Response<CreateFriendsResult>` |
| 上傳好友照片 | `POST v2/friend/{friend_id}/photo` | createFriendPhoto | friend_id, Body(Photo) | `Response<PhotoInfoResult>` |
| 刪除好友 | `DELETE v2/friend/{friend_id}` | deleteFriend | friend_id, Body(DeletedFriendInfo) | `Response<Any>` |

會員頁「邀請」項目：顯示與紅點依 getReferralData、remoteConfig.isReferralEnabled、member().isUserPhoneVerified 等；未驗證手機時點擊會先進 PhoneValidationActivity（sendSMSVerificationCode / verifyPhoneNumber），驗證後可進 ReferralActivity。

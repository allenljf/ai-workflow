# KKAPP-5042 Member API - 任務進度

Branch: `feature/KKAPP-5042/member_api`
最新 commit: `16dd2016e6`

## 已完成

### 1. 瀑布商品 API 修正 (commit `bfbfd76f6f`)
- MemberProductListData SerializedName 修正
- PagingSource first page key 修正
- 瀑布流空資料/錯誤時隱藏整個區塊

### 2. UI Token 統一 (commit `16dd2016e6`)
- **MemberPageScreen**: MaterialTheme.typography / colorResource / dimensionResource 全面改用 StyleDictionary token 與 FontStyle
- **SettingsScreen**: 同上全面替換
- **MemberPageMenuComponents**: import alias `MemberR` 改為直接 `import com.kkday.member.R`

### 3. 設定頁語言/幣別顯示
- SettingsViewModel 新增 `currentLanguage` / `currentCurrency` StateFlow
- SettingsItem 新增 `trailingText` 參數，值顯示在箭頭左側 (Body-md, color-text-medium)
- MemberPageFragment / SettingsFragment 傳入並在 onResume refresh

### 4. Header 點擊修正
- TopAppBar alpha=0 時不 compose，避免透明狀態攔截 header 觸控
- Header clickable 區域縮限為 avatar + name + 管理帳戶內容範圍（移除 weight(1f)）

## 待做 / 已知問題

### i18n 待 PM 補充
- `MemberInfo_MissionTitle`, `MemberInfo_MissionSubtitle`
- `MemberInfo_ReferralTitle`, `MemberInfo_ReferralSubtitle`
- `MemberInfo_CardhelperText`, `MemberInfo_ProdlistTitle`
- `rewards_common_tier_name_gold` (Gold tier string 尚未建立)

### Hardcode 字串待替換
- 各處已標 `// TODO: replace with stringResource`
- SettingsScreen "其他" section title

### 各等級視覺資源
- 會員卡片背景 (`getMemberCardBackground`) 目前只有 silver
- 會員頁背景 (`getMemberPageBackground`) 目前只有 silver
- Lottie 動畫檔待設計提供

### MemberPageTabsSection
- 在 `ENABLE_WATERFALL_TABS = false` flag 後面，尚未啟用
- 內部仍使用 colorResource / dimensionResource（待啟用時再統一）

### SettingsScreen 背景色
- `Color(0xFFF4F4F4)` 無對應 StyleDictionary token，已留 TODO

## 相關檔案
- `app/.../view/memberpage/MemberPageScreen.kt`
- `app/.../view/memberpage/MemberPageMenuComponents.kt`
- `app/.../view/memberpage/MemberPageFragment.kt`
- `app/.../view/memberpage/MemberPageViewModel.kt`
- `app/.../view/user/setting/SettingsScreen.kt`
- `app/.../view/user/setting/SettingsFragment.kt`
- `app/.../view/user/setting/SettingsViewModel.kt`

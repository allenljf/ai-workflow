# 設定頁功能研究與盤點

## 一、Figma 設計稿對比

### 已登入版（5610-36611）
**帳號設定區塊**
- 基本資料
- 更改密碼
- 管理登入方式

**偏好設定區塊**
- 語言（顯示當前語言，如：繁體中文（台灣））
- 幣別（顯示當前幣別，如：TWD）
- 整合手機通話功能（Toggle 開關）

**其他區塊**
- 關於KKday

**底部**
- 登出按鈕
- 版本號（V.8.8888）

### 未登入版（6274-48361）
**偏好設定區塊**
- 語言（顯示當前語言）
- 幣別（顯示當前幣別）
- 整合手機通話功能（Toggle 開關）

**其他區塊**
- 關於KKday

**底部**
- 版本號（V.8.8888）

### 新增項目（從截圖標註）
1. **移出「常用旅客」**：從舊頁面移到設定頁的「帳號設定」區塊
2. **新增「關於KKday」**：庫本我的頁中的「關於KKday」

---

## 二、舊版設定頁功能盤點

### 當前 SettingActivity 功能

#### 已登入狀態
**帳號設定區塊（layout_personal_setting）**
- `item_profile` - 基本資料 → `ProfileActivity`
- `item_friends` - 更改密碼 → `FriendsActivity`
- `item_reset_password` - 重設密碼 → `ResetPasswordActivity`（僅 KKday 帳號顯示）
- `item_login_management` - 管理登入方式 → `LoginMethodsActivity`

**偏好設定區塊（layout_preference_setting）**
- `item_language` - 語言設定（Picker Dialog）
- `item_currency` - 幣別設定（Currency Dialog）
- `item_phone_call` - 整合手機通話功能（Toggle）

**其他區塊（layout_other_setting）**
- `item_about_us` - 關於KKday → `KKdayInfoActivity`

**底部**
- `button_logout` - 登出按鈕（Compose KKButton）
- `text_version` - 版本號（顯示 `BuildConfig.VERSION_NAME`）

#### 未登入狀態
- 隱藏「帳號設定」區塊
- 隱藏「登出」按鈕
- 保留「偏好設定」和「其他」區塊

---

## 三、開發模式功能盤點

### 觸發方式
**點擊版本號 10 次**（`TOTAL_CLICK_COUNT_TO_OPEN_DEVELOPER_MODE = 10`）
- 位置：UserFragment 底部的 `text_version`
- 邏輯：`UserViewModel.clickTextVersion()`
- 儲存：`persistentManager.updateIsDeveloperMode(true)`
- Toast 提示：
  - 未開啟時：顯示剩餘點擊次數
  - 已開啟：顯示「已在開發者模式」

### 開發模式項目（僅非 production 環境）

#### UserFragment 中的開發功能
1. **itemDebugMode** - Debug 模式
   - 點擊：`RouterHelper.navigator(requireContext(), KRouterConst.PAGE_DEBUG)`
   - 功能：導航到 Debug 頁面

2. **itemAbTestingMode** - AB Testing 模式
   - 點擊：`showAbTestingModeDialog()`
   - 功能：顯示 AB Testing 設定對話框
   - 可設定：
     - AB Testing 開關
     - 測試參數

3. **textVersion** - 版本號點擊
   - 點擊：`viewModel.clickTextVersion()`
   - 功能：計數並開啟開發者模式

4. **itemShowContactNotification** - 顯示聯絡通知
   - 點擊：觸發測試通知
   - 功能：測試 FCM 通知功能

5. **itemDeveloperMode** - 環境切換
   - 點擊：顯示 `AppConfigDialog`
   - 功能：切換 API 環境
   - 選項：
     - 預設環境
     - Custom1
     - E2E (http://10.0.2.2:3001)
     - 其他自訂環境

6. **itemOpenProductPage** - 開啟商品頁
   - 點擊：輸入商品 ID 開啟商品頁
   - 功能：快速測試商品頁

7. **textAppConfigName** - 顯示當前環境名稱
   - 顯示：當前選擇的 API 環境

### 顯示/隱藏邏輯
```kotlin
// 僅在非 production 環境顯示
if (!BuildConfig.FLAVOR.contains("production", true)) {
    // 設定開發功能的點擊事件
}

// 開發者模式開啟後才顯示
fun updateDeveloperModeVisibility(isShow: Boolean) {
    itemDeveloperMode.isVisible = isShow
    itemOpenProductPage.isVisible = isShow
    itemDebugMode.isVisible = isShow
    itemAbTestingMode.isVisible = isShow
    textAppConfigName.isVisible = isShow
    itemShowContactNotification.isVisible = isShow
}
```

---

## 四、新舊頁面差異分析

### 需要新增到設定頁的功能
1. ✅ **基本資料**（已存在）
2. ✅ **更改密碼**（已存在，但 Figma 顯示為「更改密碼」，舊版為「常用旅客」）
3. ✅ **管理登入方式**（已存在）
4. ✅ **語言**（已存在）
5. ✅ **幣別**（已存在）
6. ✅ **整合手機通話功能**（已存在）
7. ✅ **關於KKday**（已存在）
8. ❌ **常用旅客**（需確認：Figma 標註「移出」，但截圖顯示「更改密碼」）

### 需要從我的頁面移除的功能
- 常用旅客（移到設定頁）

### 疑問點
1. **「更改密碼」vs「常用旅客」**
   - Figma 已登入版顯示：基本資料、**更改密碼**、管理登入方式
   - 舊版 SettingActivity：基本資料、**常用旅客**（`item_friends` → `FriendsActivity`）、重設密碼、管理登入方式
   - 截圖標註：「移出常用旅客」
   - **需確認**：是否要將 `item_friends` 改為「更改密碼」？還是保持「常用旅客」？

2. **重設密碼 vs 更改密碼**
   - 舊版有「重設密碼」（`item_reset_password`）
   - Figma 顯示「更改密碼」
   - **需確認**：是否為同一功能？

---

## 五、開發優先順序建議

### Phase 1：基礎設定頁（優先）
由於需要使用開發環境功能，建議優先實作：

1. **版本號點擊功能**
   - 實作 10 次點擊開啟開發者模式
   - Toast 提示
   - 儲存到 PersistentManager

2. **開發者模式項目**（僅非 production）
   - Debug 模式入口
   - AB Testing 設定
   - 環境切換（AppConfigDialog）
   - 顯示當前環境名稱

3. **基本設定項目**
   - 語言切換
   - 幣別切換
   - 關於KKday

### Phase 2：完整設定頁
1. 帳號設定區塊（已登入）
2. 登出功能
3. 整合手機通話功能
4. UI 細節對齊 Figma

---

## 六、技術實作建議

### 架構
- 使用 Compose 重寫設定頁
- ViewModel 管理狀態（不走 Reductor）
- 使用 PersistentManager 儲存設定

### 狀態管理
```kotlin
data class SettingsUiState(
    val isLoggedIn: Boolean = false,
    val isDeveloperMode: Boolean = false,
    val currentLanguage: String = "",
    val currentCurrency: String = "",
    val currentEnvironment: String = "",
    val versionName: String = "",
    val versionClickCount: Int = 0,
    val isPhoneCallEnabled: Boolean = false
)
```

### 開發者模式邏輯
```kotlin
fun onVersionClick() {
    if (isDeveloperMode) {
        showToast("已在開發者模式")
        return
    }
    
    versionClickCount++
    val remaining = 10 - versionClickCount
    
    if (remaining == 0) {
        persistentManager.updateIsDeveloperMode(true)
        _uiState.value = _uiState.value.copy(isDeveloperMode = true)
        showToast("已開啟開發者模式")
    } else {
        showToast("還需點擊 $remaining 次開啟開發者模式")
    }
}
```

---

## 七、待確認問題清單

1. ❓ 「更改密碼」vs「常用旅客」的功能對應
2. ❓ 「重設密碼」是否與「更改密碼」為同一功能
3. ❓ 常用旅客功能是否要移到設定頁
4. ❓ 新設定頁是否要完全取代舊的 SettingActivity，還是並存
5. ❓ 開發者模式的所有功能是否都要移植到新頁面

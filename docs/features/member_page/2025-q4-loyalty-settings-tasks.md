# 設定頁重構任務規劃

## 一、任務分階段

### Phase 1：開發功能優先（本次）
**目標**：快速實作開發環境相關功能，讓開發測試更便利

**範圍**：
- 基本設定頁架構（Compose）
- 版本號點擊（10次開啟開發者模式）
- 環境切換（AppConfigDialog）
- Debug 模式入口
- AB Testing 設定
- 顯示當前環境名稱
- 其他開發功能（測試通知、快速開啟商品頁等）

**不包含**：
- 帳號設定區塊（基本資料、更改密碼等）
- 偏好設定區塊（語言、幣別等）
- 登出功能

### Phase 2：完整設定頁功能（會員頁完成後）
**目標**：實作完整的設定頁功能，對齊 Figma 設計

**範圍**：
- 帳號設定區塊（已登入）
- 偏好設定區塊
- 關於KKday
- 登出功能
- UI 細節對齊 Figma

---

## 二、Phase 1 任務細分

### Task S1：基本架構
- [ ] 建立 `SettingsScreen.kt`（Compose）
- [ ] 建立 `SettingsViewModel.kt`（不走 Reductor）
- [ ] 建立 `SettingsFragment.kt` 或整合到現有 `SettingActivity`
- [ ] 基本佈局：Toolbar + ScrollableColumn + 版本號

### Task S2：版本號點擊功能
- [ ] 版本號顯示（`BuildConfig.VERSION_NAME`）
- [ ] 點擊計數邏輯（10次）
- [ ] Toast 提示（剩餘次數 / 已開啟）
- [ ] 儲存到 `PersistentManager.updateIsDeveloperMode(true)`
- [ ] 從 `PersistentManager.isDeveloperMode()` 讀取狀態

### Task S3：開發者模式項目顯示
- [ ] 僅在非 production 環境顯示
- [ ] 開發者模式開啟後才顯示項目
- [ ] 項目列表：
  - Debug 模式
  - AB Testing 模式
  - 環境切換（開發者模式）
  - 顯示當前環境
  - 測試通知
  - 快速開啟商品頁

### Task S4：環境切換功能
- [ ] 整合 `AppConfigDialog`
- [ ] 顯示當前環境名稱
- [ ] 切換環境後重啟 App
- [ ] 環境選項：
  - 預設環境
  - Custom1
  - E2E
  - 其他自訂環境

### Task S5：Debug 模式入口
- [ ] 導航到 Debug 頁面（`PAGE_DEBUG`）
- [ ] 使用 `RouterHelper.navigator()`

### Task S6：AB Testing 設定
- [ ] 整合 `showAbTestingModeDialog()`
- [ ] AB Testing 開關
- [ ] 測試參數設定

### Task S7：其他開發功能
- [ ] 測試通知功能
- [ ] 快速開啟商品頁（輸入 product ID）

---

## 三、技術實作方案

### 架構設計
```
SettingsScreen (Compose)
├── Toolbar
├── LazyColumn
│   ├── 開發者模式區塊（條件顯示）
│   │   ├── Debug 模式
│   │   ├── AB Testing
│   │   ├── 環境切換
│   │   ├── 當前環境顯示
│   │   ├── 測試通知
│   │   └── 快速開啟商品頁
│   └── 版本號（可點擊）
└── SettingsViewModel
    ├── isDeveloperMode: StateFlow<Boolean>
    ├── versionClickCount: Int
    ├── currentEnvironment: StateFlow<String>
    └── 各種導航方法
```

### ViewModel 設計
```kotlin
@KoinViewModel
class SettingsViewModel(
    private val persistentManager: PersistentManager,
    private val appSharedData: AppSharedData
) : ViewModel(), KoinComponent {
    
    private val activity: Activity by inject()
    
    private val _isDeveloperMode = MutableStateFlow(false)
    val isDeveloperMode = _isDeveloperMode.asStateFlow()
    
    private val _currentEnvironment = MutableStateFlow("")
    val currentEnvironment = _currentEnvironment.asStateFlow()
    
    private var versionClickCount = 0
    
    init {
        loadDeveloperMode()
        loadCurrentEnvironment()
    }
    
    fun onVersionClick() {
        // 版本號點擊邏輯
    }
    
    fun navigateToDebug() {
        // 導航到 Debug 頁面
    }
    
    fun showAppConfigDialog() {
        // 顯示環境切換對話框
    }
    
    fun showAbTestingDialog() {
        // 顯示 AB Testing 對話框
    }
}
```

### 條件顯示邏輯
```kotlin
// 僅非 production 環境
val isNonProduction = !BuildConfig.FLAVOR.contains("production", true)

// 開發者模式項目
if (isNonProduction && isDeveloperMode) {
    // 顯示開發功能
}

// 版本號（永遠顯示，但只有非 production 可點擊）
Text(
    text = BuildConfig.VERSION_NAME,
    modifier = if (isNonProduction) {
        Modifier.clickable { viewModel.onVersionClick() }
    } else {
        Modifier
    }
)
```

---

## 四、開發順序建議

1. **Task S1** - 基本架構（Screen + ViewModel + Fragment）
2. **Task S2** - 版本號點擊（最基礎，先能開啟開發者模式）
3. **Task S3** - 開發者模式項目顯示（UI 骨架）
4. **Task S4** - 環境切換（最重要的功能）
5. **Task S5** - Debug 模式入口
6. **Task S6** - AB Testing 設定
7. **Task S7** - 其他開發功能

---

## 五、參考檔案

**舊版實作**：
- `app/src/main/java/com/kkday/member/view/user/UserFragment.kt` - 開發功能 UI
- `app/src/main/java/com/kkday/member/view/user/UserViewModel.kt` - 版本號點擊邏輯
- `app/src/main/java/com/kkday/member/view/user/setting/SettingActivity.kt` - 設定頁架構

**對話框**：
- `com.kkday.library.common.view.util.dialog.AppConfigDialog` - 環境切換
- `ComponentAbTestingModeBinding` - AB Testing 設定

**路由**：
- `KRouterConst.PAGE_DEBUG` - Debug 頁面路由

---

## 六、待確認問題

1. ❓ 新設定頁是建立新的 Activity 還是整合到現有的 `SettingActivity`？
   - **建議**：先建立新的 Compose Fragment/Screen，用 flag 切換（與會員頁一致）
   
2. ❓ 開發功能是否要完全移植？
   - 測試通知
   - 快速開啟商品頁
   - 其他隱藏功能

3. ❓ 環境切換後是否需要重啟 App？
   - 舊版邏輯需確認

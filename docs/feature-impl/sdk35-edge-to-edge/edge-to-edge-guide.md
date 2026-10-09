# Android SDK 35 Edge-to-Edge 解決方案指南

## 背景

- **targetSdkVersion**: 35
- **問題**: Android 15+ 強制 edge-to-edge，虛擬導航條遮擋底部 UI
- **解決日期**: 2025-10-20
- **狀態**: 開發完成，已通過初步測試

---

## 架構設計

已將 edge-to-edge 處理邏輯抽取到 `BaseActivity` 層，提供 3 種模式：

### 新增的檔案

- **EdgeToEdgeConfig.kt**：`libs/base/src/main/java/com/kkday/library/common/view/base/EdgeToEdgeConfig.kt`
  - `EdgeToEdgeMode` enum（DISABLED, AUTO_BOTTOM_PADDING, CUSTOM）
  - `EdgeToEdgeInsets` data class

- **BaseActivity.kt**：`libs/base/src/main/java/com/kkday/library/common/view/base/BaseActivity.kt`
  - `getEdgeToEdgeMode()` — 配置模式
  - `onApplyEdgeToEdgeInsets()` — 自定義處理
  - `setupEdgeToEdge()` — 自動化處理邏輯

---

## 使用方式

### 方式 1：自動處理（AUTO_BOTTOM_PADDING）

適合 80% 有底部按鈕或輸入框的頁面：

```kotlin
class MyActivity : BaseActivity<ActivityMyBinding>(ActivityMyBinding::inflate) {
    override fun getEdgeToEdgeMode() = EdgeToEdgeMode.AUTO_BOTTOM_PADDING
}
```

效果：自動為 `binding.root` 加底部 padding，同時處理 systemBars 和 IME。

---

### 方式 2：自定義處理（CUSTOM）

適合需要精確控制特定 view 的複雜頁面：

```kotlin
class MyActivity : BaseActivity<ActivityMyBinding>(ActivityMyBinding::inflate) {
    override fun getEdgeToEdgeMode() = EdgeToEdgeMode.CUSTOM

    override fun onApplyEdgeToEdgeInsets(view: View, insets: EdgeToEdgeInsets) {
        binding.layoutConfirmField.updatePadding(bottom = insets.suggestedBottomPadding)
    }
}
```

`EdgeToEdgeInsets` 提供的屬性：
- `systemBarsBottom` — navigation bar 高度
- `systemBarsTop` — status bar 高度
- `imeBottom` — 鍵盤高度
- `suggestedBottomPadding` — 取 systemBars 與 IME 較大值

---

### 方式 3：停用（DISABLED，預設）

不覆寫 `getEdgeToEdgeMode()` 時即為預設，維持原有行為，不影響現有頁面。

---

### 不繼承 BaseActivity 的頁面

Fragment 和 Dialog 保持手動實作：

```kotlin
ViewCompat.setOnApplyWindowInsetsListener(binding.root) { view, windowInsets ->
    val systemBarsInsets = windowInsets.getInsets(WindowInsetsCompat.Type.systemBars())
    val imeInsets = windowInsets.getInsets(WindowInsetsCompat.Type.ime())
    val bottomInset = maxOf(systemBarsInsets.bottom, imeInsets.bottom)
    binding.layoutConfirmField.updatePadding(bottom = bottomInset)
    windowInsets
}
```

Compose 頁面：

```kotlin
modifier = Modifier
    .windowInsetsPadding(WindowInsets.navigationBars)
    .imePadding()
```

---

## 已修正的頁面（17 個）

### P0 — 購買流程（必修）

| 頁面 | 問題 |
|------|------|
| `OrderFormFillingActivity` | 底部「確認支付」按鈕被遮擋 |
| `CartActivity` | 底部支付按鈕被遮擋 |
| `ProductHostActivity` | 商品詳情底部購買按鈕被遮擋 |
| `JRBookingFragment` (Compose) | 底部確認按鈕被遮擋 |
| `RepayActivity` | 重新支付頁面底部按鈕被遮擋 |

### P1 — 重要功能

| 頁面 | 問題 |
|------|------|
| `TransHomeActivity` | 底部按鈕被遮擋，影響 CNHKBus/ZzimAir/Zzimcar 等 |
| `OrderTransportation2Activity` | 訂單詳情交通資訊頁面 |
| `SocialLoginActivity` | 登入輸入框和按鈕被遮擋 |
| `SignUpActivity` | 註冊表單輸入框被遮擋 |
| `PaymentInfoActivity` | ScrollView 內容可能被遮擋 |

### P2 — 改善體驗

| 頁面 | 問題 |
|------|------|
| `SearchResultActivity` | 搜尋框和結果列表 |
| `InstallmentBottomSheetDialogFragment` (Compose) | 分期付款對話框底部按鈕 |
| `MainActivity` | 底部導航列被遮擋 |

---

## 注意事項

### 繼承層級限制

專案目前有兩條 BaseActivity 鏈：

```
libs/base/BaseActivity (ViewBinding)  ← 已整合 edge-to-edge 機制
app/BaseActivity (非 ViewBinding)     ← 尚未整合，子類需手動實作
   └── BookingActivity
       └── OrderFormFillingActivity, CartActivity, RepayActivity
```

- 繼承 `libs/base/BaseActivity` 的類別：可直接使用新機制
- 繼承 `app/BaseActivity` 的類別：仍需手動實作，長期目標是遷移至 ViewBinding

### 新頁面開發原則

1. 優先使用 `AUTO_BOTTOM_PADDING`
2. 複雜佈局改用 `CUSTOM`
3. 不繼承 BaseActivity 的 Fragment/Dialog 保持手動實作

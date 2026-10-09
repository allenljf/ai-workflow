# APP 首單優惠 Banner 實作 - 第一階段完成

## 📋 實作內容總結

### ✅ 已完成項目

#### 1. **資料模型更新**
- **檔案**: `libs/model/src/main/java/com/kkday/library/networking/resource/home/B2CHomeData.kt`
- **修改**: `FirstPurchaseDesc` 新增 `homepage_new` 欄位
- **用途**: 支援多語系文案顯示（來自 `/v3/home` API）

#### 2. **UI 元件重新設計**
- **檔案**: `app/src/main/java/com/kkday/member/view/homeV2/presentation/components/FirstBuyItem.kt`
- **變更**:
  - 從舊版圖片背景樣式改為扁平化 Banner 設計
  - 新增 `picto_coupon_firstorder` 圖示（左側）
  - 使用 `homepage_new` 作為主要文案來源，fallback 到 `row1.text + row2.text`
  - 自訂「領取」按鈕樣式（紅底白字 + 箭頭圖示）
  - 按鈕最大寬度限制 100dp（符合規格）
  - 支援多語系文案自動換行（最多 2 行）

#### 3. **顯示邏輯實作**
- **新增檔案**: `app/src/main/java/com/kkday/member/view/homeV2/useCase/ShouldShowFirstPurchaseBannerUseCase.kt`
- **顯示條件**:
  1. API 回傳 `first_purchase.is_show = true`
  2. 用戶未登入 **OR**
  3. 用戶已登入 且 本地未標記已領取
  
- **優先級**: 先參考本地儲存狀態，最終以 API 回應為準

#### 4. **整合到 HomeScreen**
- **修改檔案**: 
  - `app/src/main/java/com/kkday/member/view/homeV2/presentation/HomeScreen.kt`
  - `app/src/main/java/com/kkday/member/view/homeV2/presentation/HomeViewModelV2.kt`
  - `app/src/main/java/com/kkday/member/view/homeV2/useCase/HomeUseCases.kt`

- **修改內容**:
  - 新增 `shouldShowFirstPurchaseBanner` 計算屬性
  - 使用 `ShouldShowFirstPurchaseBannerUseCase` 判斷顯示邏輯
  - Banner 顯示位置：Recently Viewed Products 之後

---

## 🎨 UI 設計規格

### Banner 樣式
- **高度**: 56dp
- **背景色**: `kkColorBackgroundCriticalLight` (淡紅色)
- **圓角**: `kkRadiusSm`
- **左右間距**: `kkSpacing5` (16dp)
- **上下間距**: `kkSpacing7` (24dp) - 在 HomeScreen 中控制

### 圖示
- **Left Icon**: `picto_coupon_firstorder` (24dp)
  - 顏色: `kkColorTextCriticalDark`
- **Arrow Icon**: `ic_arrowright_line_semibold` (16dp)
  - 顏色: White

### 文案區域
- **文字樣式**: `fontBodyMd` + SemiBold weight
- **顏色**: `kkColorTextCriticalDark` (#E65F50)
- **最大行數**: 2
- **Overflow**: Ellipsis

### 按鈕樣式
- **最大寬度**: 100dp
- **高度**: 32dp
- **背景色**: `kkColorTextCriticalDark` (紅色)
- **圓角**: `kkRadiusSm`
- **文字樣式**: `fontBodySm` + SemiBold
- **文字顏色**: White
- **內容**: 領取文字 + 箭頭圖示

---

## 📊 資料流程

```
/v3/home API
  ↓
首購資料 (first_purchase)
  ├─ is_show: Boolean
  ├─ desc.homepage_new: String (多語系文案)
  ├─ desc.row1.text: String (fallback)
  ├─ desc.row2.text: String (fallback)
  └─ coupon: String (coupon code)
  ↓
ShouldShowFirstPurchaseBannerUseCase
  ├─ 檢查 is_show
  ├─ 檢查登入狀態 (AppSharedData)
  └─ 檢查本地領取狀態 (PersistentManager)
  ↓
HomeScreen shouldShowFirstPurchaseBanner
  ↓
FirstPurchaseItem 顯示
```

---

## 🔧 技術實作細節

### 多語系文案優先級
```kotlin
val displayText = firstPurchase.desc.homepageNew.ifEmpty {
    "${firstPurchase.desc.title.text} ${firstPurchase.desc.subTitle.text}".trim()
}
```

### 顯示判斷邏輯
```kotlin
operator fun invoke(firstPurchase: FirstPurchase): Boolean {
    // 1. API is_show = false 則不顯示
    if (!firstPurchase.isShow) return false

    // 2. 未登入，顯示
    val isLoggedIn = appSharedData.hasAlreadyLoggedIn()
    if (!isLoggedIn) return true

    // 3. 已登入，檢查是否已領取
    val hasAcquired = persistentManager.getHasAcquiredFirstPurchaseCoupon()
    return !hasAcquired
}
```

---

## 🚀 下一階段：點擊流程與 Dialog

### 待實作功能

1. **點擊領取按鈕流程**
   - 未登入：導向登入頁
   - 已登入：呼叫 `/v2/coupons/{coupon}/claim` API

2. **成功 Dialog**
   - 顯示成功訊息
   - Banner 消失
   - 更新本地狀態

3. **失敗 Dialog**
   - 根據 error code 顯示對應訊息
   - CN38 (已領取): Banner 消失
   - 其他錯誤: Banner 保留

4. **錯誤代碼處理**
   - CN01: coupon 不存在
   - CN30: 會員不存在
   - CN26: 會員狀態未知
   - CN14: 優惠券可用數量不足
   - CN12: 優惠券不匹配該會員
   - CN19: 會員國家不匹配
   - CN16: 信箱網域不符
   - CN22: 僅限新會員
   - CN29: 僅限首次 App 購買
   - CN41: 會員等級不符
   - CN38: 優惠券已經被領取 ⭐️
   - CN18: 適用出發日期不符
   - CN37: 適用訂單日期已超過
   - CN31: 優惠券不可被領取

---

## 📝 測試情境

### Banner 顯示測試
- [ ] **未登入狀態**: 顯示 Banner
- [ ] **已登入 + 未領取**: 顯示 Banner
- [ ] **已登入 + 已領取**: 不顯示 Banner
- [ ] **API is_show = false**: 不顯示 Banner

### UI 測試
- [ ] 文案顯示正確（多語系）
- [ ] 長文案自動換行（最多 2 行）
- [ ] 圖示顯示正確
- [ ] 按鈕樣式符合設計稿
- [ ] 按鈕寬度不超過 100dp

### 互動測試
- [ ] 點擊 Banner 觸發 `onClickFirstPurchaseCouponListener`
- [ ] 點擊後的行為（待第二階段實作）

---

## 📂 相關檔案

### 修改的檔案
1. `libs/model/src/main/java/com/kkday/library/networking/resource/home/B2CHomeData.kt`
2. `app/src/main/java/com/kkday/member/view/homeV2/presentation/components/FirstBuyItem.kt`
3. `app/src/main/java/com/kkday/member/view/homeV2/presentation/HomeScreen.kt`
4. `app/src/main/java/com/kkday/member/view/homeV2/presentation/HomeViewModelV2.kt`
5. `app/src/main/java/com/kkday/member/view/homeV2/useCase/HomeUseCases.kt`

### 新增的檔案
1. `app/src/main/java/com/kkday/member/view/homeV2/useCase/ShouldShowFirstPurchaseBannerUseCase.kt`

### 使用的資源
1. `app/src/main/res/drawable/picto_coupon_firstorder.xml`
2. `app/src/main/res/drawable/ic_arrowright_line_semibold.xml`
3. `libs/app_resource/src/main/res/values*/strings.xml` (使用既有的 `home_first_purchase_button_text`)

---

## ✨ 設計稿參考

- Figma: https://www.figma.com/design/iY5PetlEwUmfBprXwYob0d/2025-q3-首頁-shortcuts-區塊調整?node-id=5003-74389&m=dev
- 節點: 5003-74389

---

**實作完成日期**: 2025-11-05  
**實作者**: AI Assistant  
**狀態**: ✅ 第一階段完成 - Banner 顯示功能


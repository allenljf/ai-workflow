# SkuPruningCalculator 單元測試說明文檔

## 概述

本文檔說明如何執行 `SkuPruningCalculator` 的單元測試，以及測試涵蓋的項目與測試場景。

## 測試文件位置

- **測試類文件**: `app/src/test/java/com/kkday/member/view/product/specification/SkuPruningCalculatorTest.kt`
- **被測試類**: `app/src/main/java/com/kkday/member/view/product/specification/SkuPruningCalculator.kt`

## 如何執行測試

### 方法 1: 使用 Android Studio

1. 打開 Android Studio
2. 在項目視圖中找到 `SkuPruningCalculatorTest.kt` 文件
3. 右鍵點擊該文件，選擇 **"Run 'SkuPruningCalculatorTest'"**
4. 測試結果將顯示在 Run 窗口中

### 方法 2: 執行單個測試方法

1. 打開 `SkuPruningCalculatorTest.kt` 文件
2. 在想要執行的測試方法左側，點擊綠色的執行圖標
3. 選擇 **"Run 'test名稱'"**

### 方法 3: 使用命令行

在項目根目錄執行以下命令：

```bash
# 執行所有測試
./gradlew test

# 只執行 SkuPruningCalculatorTest
./gradlew test --tests "com.kkday.member.view.product.specification.SkuPruningCalculatorTest"

# 執行特定測試方法
./gradlew test --tests "com.kkday.member.view.product.specification.SkuPruningCalculatorTest.test01_calculateDateAvailability_skuAndTime_withEvents_noSelection"
```

### 方法 4: 使用 Gradle 任務視圖

1. 在 Android Studio 右側打開 **Gradle** 視圖
2. 展開 **app** → **Tasks** → **verification**
3. 雙擊 **test** 任務

## 測試涵蓋項目

### 主要測試方法

測試覆蓋了 `SkuPruningCalculator` 類的以下五個主要方法：

1. **`calculateDateAvailability`** - 日期可用性計算
2. **`calculateEventAvailability`** - 場次可用性計算  
3. **`calculateSpecAvailability`** - 規格可用性計算
4. **`calculateTicketAvailability`** - 票種可用性計算
5. **`calculateAvailability`** - 整合計算（調用上述四個方法）

### 測試的庫存類型

測試涵蓋了四種不同的庫存設定類型：

- **TYPE_SKU_AND_TIME** (2, 1) - SKU 層級 + 日期/場次庫存
- **TYPE_SKU_AND_REMAIN** (2, 0) - SKU 層級 + 總量庫存
- **TYPE_PRICE_AND_TIME** (1, 1) - 方案層級 + 日期/場次庫存
- **TYPE_PRICE_AND_REMAIN** (1, 0) - 方案層級 + 總量庫存

## 測試用例清單

## 測試用例詳細清單

### 第一部分：日期可用性測試 (Date Availability, test01-05)
測試重點在於驗證當使用者處於不同選擇階段時，日曆上的日期是否能正確顯示可用、不可用或已選中。

| 編號 | 測試名稱 | 輸入內容 (Selection State) | 預期輸出結果 (Expected Result) |
| :--- | :--- | :--- | :--- |
| **01** | **初始狀態無選擇** | 什麼都沒選 (空的 `SkuSelectionState`) | 所有在數據範圍內的日期 (2026-01-15~17) 皆為 `isAvailable = true`，且無日期被選中。 |
| **02** | **已選擇特定日期** | 選中 `2026-01-15` | 該日期 `isSelected = true` 且 `isAvailable = true`。 |
| **03** | **已選日期與場次** | 選中 `2026-01-15` 及場次 `10:00` | 日期 `isSelected = true`，計算結果不應因選擇場次而改變日期的可用性。 |
| **04** | **已選擇規格** | 選中某個規格項目 (例如：豪華車) | 僅有提供該規格項目的日期為 `isAvailable = true` (在此案例中所有日期均提供，故全可用)。 |
| **05** | **日期無庫存** | 無選擇，但數據中 `2026-01-17` 的庫存設為 0 | 該日期 `isAvailable = false`，其餘庫存大於 0 的日期仍為可用。 |

---

### 第二部分：場次可用性測試 (Event Availability, test06-10)
針對「時間型」商品，驗證在選擇日期前後，場次（如 10:00, 14:00）的可用狀態。

| 編號 | 測試名稱 | 輸入內容 (Selection State) | 預期輸出結果 (Expected Result) |
| :--- | :--- | :--- | :--- |
| **06** | **未選日期時的場次** | 什麼都沒選 | 返回所有日期場次的聯集。若所有日期皆有場次，則顯示可用。 |
| **07** | **已選日期後的場次** | 選中 `2026-01-15` | 返回該特定日期下的場次清單，並根據該日庫存判定 `isAvailable`。 |
| **08** | **已選擇特定場次** | 選中日期與場次 `10:00` | 該場次 `isSelected = true`。 |
| **09** | **場次被後台關閉** | 選中日期，但該場次在 `closeSkuList` 中 | 該場次 `isAvailable = false`，使用者無法點選。 |
| **10** | **無場次商品** | `hasEvent = false` 的商品數據 | `availableEvents` 清單應為空，不顯示場次選項。 |

---

### 第三部分：規格可用性測試 (Spec Availability, test11-15)
驗證除了票種以外的規格（如：顏色、車型、保險類型）在不同庫存類型下的行為。

| 編號 | 測試名稱 | 輸入內容 (Selection State) | 預期輸出結果 (Expected Result) |
| :--- | :--- | :--- | :--- |
| **11** | **初始狀態規格** | 什麼都沒選 | 所有定義好的規格項目 (Spec Items) 皆為 `isAvailable = true`。 |
| **12** | **選擇日期後的規格** | 選中 `2026-01-15` | 僅顯示該日期下有對應 SKU 的規格項目為可用。 |
| **13** | **選中規格項** | 選中「豪華車」規格 | 該規格項目 `isSelected = true`。 |
| **14** | **方案層級庫存類型** | 使用 `TYPE_PRICE_AND_TIME` 數據 | 即使庫存不在 SKU 層級，規格仍能根據日期判斷是否可用。 |
| **15** | **不可用的規格項目** | 某規格項目對應的所有 SKU 皆無庫存 | 該特定規格項目 `isAvailable = false`。 |

---

### 第四部分：票種可用性測試 (Ticket Availability, test16-20)
測試票種（成人、兒童等）的數量限制、選中狀態以及虛擬票種的生成。

| 編號 | 測試名稱 | 輸入內容 (Selection State) | 預期輸出結果 (Expected Result) |
| :--- | :--- | :--- | :--- |
| **16** | **初始狀態票種** | 選中日期與場次 | 列出所有票種，`isSelected = false`，`selectedQty = 0`。 |
| **17** | **已選擇票種數量** | 選擇「成人票 x 2」 | 該票種 `isSelected = true`，`selectedQty = 2`。 |
| **18** | **受庫存限制的票種** | SKU 庫存假設僅剩 5 | 票種的 `maxQty` (最大可選數量) 應受限於庫存 5，而不僅是設定的上限。 |
| **19** | **最小/最大購買規則** | 方案設定每筆最少買 1 張 | 票種結果反映 `minQty = 1`。 |
| **20** | **虛擬票種生成** | 數據中沒有票種規格 (只有一個單位項) | 計算器應自動生成一個 ID 為 `virtual-ticket-unit` 的票種供選擇。 |

---

### 第五部分：整合測試 (Integration Tests, test21-25)
模擬複雜的真實操作流程或不同的特殊庫存配置。

| 編號 | 測試名稱 | 輸入內容 (Selection State) | 預期輸出結果 (Expected Result) |
| :--- | :--- | :--- | :--- |
| **21** | **完整選擇路徑** | 模擬：日期 -> 場次 -> 規格 -> 票種 | 每一步後，下一步的選項皆能正確更新其可用性與關聯數據。 |
| **22** | **SKU 總量庫存類型** | 使用 `TYPE_SKU_AND_REMAIN` 數據 | 不論日期，只要總量 > 0，規格和票種即顯示可用。 |
| **23** | **方案總量庫存類型** | 使用 `TYPE_PRICE_AND_REMAIN` 數據 | 依方案剩餘總數判斷可用性，不綁定特定日期。 |
| **24** | **日期標記為售完** | 數據中 `isSoldOut = true` | 該日期 `isAvailable = false`，且原因 (reason) 顯示「已完售」。 |
| **25** | **多重規格組合判斷** | 同時選中「豪華車」+「全險」 | 獲取同時符合這兩個規格的 SKU，並決定接下來票種的庫存與價格。 |

## 測試數據結構

### SkuSelectionState

測試使用的選擇狀態包含以下字段：

```kotlin
data class SkuSelectionState(
    val productId: String? = null,
    val productOid: String? = null,
    val selectedPkgOid: PkgOid? = null,
    val selectedDate: String? = null,              // 選擇的日期 (yyyy-MM-dd)
    val selectedEvent: String? = null,             // 選擇的場次 ID
    val selectedSpecs: MutableMap<String, String> = mutableMapOf(),  // 規格選擇
    val selectedTickets: MutableMap<String, Int> = mutableMapOf(),   // 票種數量
    val dateRangeStart: String? = null,            // 日期範圍開始
    val dateRangeEnd: String? = null               // 日期範圍結束
)
```

### 測試場景示例

#### 1. 初始狀態（無選擇）
```kotlin
val selectionState = SkuSelectionState()
```

#### 2. 選擇日期
```kotlin
val selectionState = SkuSelectionState(
    selectedDate = "2026-01-15"
)
```

#### 3. 選擇日期和場次
```kotlin
val selectionState = SkuSelectionState(
    selectedDate = "2026-01-15",
    selectedEvent = "10:00"
)
```

#### 4. 選擇規格
```kotlin
val selectionState = SkuSelectionState(
    selectedDate = "2026-01-15",
    selectedEvent = "10:00",
    selectedSpecs = mutableMapOf("spec-car" to "luxury-car")
)
```

#### 5. 選擇票種
```kotlin
val selectionState = SkuSelectionState(
    selectedDate = "2026-01-15",
    selectedEvent = "10:00",
    selectedSpecs = mutableMapOf("spec-car" to "luxury-car"),
    selectedTickets = mutableMapOf("adult" to 2, "child" to 1)
)
```

## 測試數據模擬

測試使用多個輔助方法來創建不同場景的測試數據：

### 主要測試數據創建方法

1. **`createTestData_SkuAndTime_WithEvents()`**
   - 庫存類型: TYPE_SKU_AND_TIME
   - 有場次
   - 包含多個規格和 SKU

2. **`createTestData_SkuAndTime_NoEvents()`**
   - 庫存類型: TYPE_SKU_AND_TIME
   - 無場次

3. **`createTestData_PriceAndTime_WithSpecs()`**
   - 庫存類型: TYPE_PRICE_AND_TIME
   - 方案層級庫存

4. **`createTestData_WithTickets()`**
   - 包含票種規格
   - 成人/兒童/敬老票種

5. **`createTestData_VirtualTicket()`**
   - 無票種規格
   - 使用虛擬票種

6. **`createTestData_SkuAndRemain()`**
   - 庫存類型: TYPE_SKU_AND_REMAIN
   - SKU 總量限制

7. **`createTestData_PriceAndRemain()`**
   - 庫存類型: TYPE_PRICE_AND_REMAIN
   - 方案總量限制

8. **`createTestData_MultipleSpecs()`**
   - 多個規格組合
   - 車種 × 保險 × 票種

### 測試數據特點

- **日期範圍**: 2026-01-15 ~ 2026-01-17
- **場次時間**: 10:00, 14:00
- **庫存量**: 預設為 10（部分測試會設為 0 或特定值）
- **規格類型**: 車種、保險、票種等
- **票種類型**: 成人、兒童、敬老

## 驗證重點

每個測試都會驗證以下內容：

### 1. 可用性判斷
- `isAvailable`: 是否可選
- `reason`: 不可用原因（如：已完售、無庫存、無符合條件的方案等）

### 2. 選中狀態
- `isSelected`: 是否被選中

### 3. 數量限制
- `minQty`: 最小購買數量
- `maxQty`: 最大購買數量
- `availableQuantities`: 可選的數量列表

### 4. 數據一致性
- 選擇狀態與計算結果的一致性
- 不同方法之間的邏輯一致性

## 預期測試結果

所有 25 個測試應該全部通過。如果有測試失敗：

1. **檢查測試輸出**：查看具體哪個斷言失敗
2. **檢查測試數據**：確認測試數據是否符合預期
3. **檢查被測試類**：確認 `SkuPruningCalculator` 的邏輯是否正確
4. **檢查依賴類**：確認 `PackageData`, `PackageCalendarItem` 等數據結構是否正確

## 測試覆蓋率

本測試套件覆蓋了以下分支：

- ✅ 有場次 / 無場次商品
- ✅ 四種庫存類型（SKU+時間、SKU+總量、方案+時間、方案+總量）
- ✅ 有規格 / 無規格
- ✅ 有票種 / 虛擬票種
- ✅ 有庫存 / 無庫存
- ✅ 正常日期 / 售完日期 / 關閉日期
- ✅ 未選擇 / 部分選擇 / 完整選擇

## 常見問題排查

### 問題 1: 測試編譯失敗
**原因**: 缺少依賴或導入錯誤
**解決**: 
- 確認 JUnit 4 依賴已添加到 `build.gradle`
- 執行 `./gradlew clean` 清理項目
- 重新同步 Gradle

### 問題 2: 測試運行失敗
**原因**: 測試數據或邏輯問題
**解決**:
- 檢查失敗的測試輸出
- 啟用 `SkuPruningCalculator` 的日誌輸出（設置 `enableLog = true`）
- 逐步調試測試方法

### 問題 3: 測試結果不符合預期
**原因**: 業務邏輯理解偏差
**解決**:
- 參考本文檔的測試場景說明
- 檢查 `SkuPruningCalculator` 的實現邏輯
- 與實際業務需求對照

## 維護建議

1. **新增功能時**：同步更新測試用例
2. **修改邏輯時**：確保現有測試仍然通過
3. **重構代碼時**：運行所有測試確保無回歸
4. **發現 Bug 時**：先寫測試重現問題，再修復

## 總結

本測試套件提供了 `SkuPruningCalculator` 的全面測試覆蓋，包含：

- **25 個測試用例**
- **5 個主要方法**
- **4 種庫存類型**
- **多種選擇狀態組合**
- **各種邊界條件**

通過這些測試，可以確保 SKU 剪枝計算器在各種場景下都能正確工作。

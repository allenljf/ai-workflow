# PR #6671 覆蓋率報告負數百分比分析

## 問題描述

PR #6671 的覆蓋率報告顯示負數百分比，例如：
- Overall Project: `0% **-1.72%**`
- AirportProductCommentUtil.kt: `0% **-94.17%**`
- AirportKtmHelper.kt: `0% **-76.32%**`

## 根本原因

根據 `madrapps/jacoco-report@v1.7.1` 原始碼分析，**負數 delta 不是與 base branch 的覆蓋率比較**。

### Delta 計算邏輯

```typescript
// 來源: madrapps/jacoco-report/src/render.ts
const changedPercentage = (missed / totalInstructions) * 100
if (changedPercentage > 0 && changedPercentage < 100) {
  return -changedPercentage
}
```

**Delta 代表：PR 中被修改的程式碼，有多少比例的指令未被測試覆蓋。**

## 報告數據解讀

| 欄位 | 含義 |
|------|------|
| Coverage (0%) | 該檔案/專案的整體測試覆蓋率 |
| Delta (-X%) | PR 修改的程式碼中，有 X% 的指令未被測試覆蓋 |

### 範例解讀

| 檔案 | 覆蓋率 | Delta | 解讀 |
|------|--------|-------|------|
| Overall Project | 0% | -1.72% | 專案整體 0% 覆蓋；PR 修改的指令中 1.72% 未覆蓋 |
| AirportProductCommentUtil.kt | 0% | -94.17% | 檔案 0% 覆蓋；94.17% 的修改指令未覆蓋 |
| PaymentStrategyAdapter.kt | 0% | (無) | 檔案 0% 覆蓋；但此次 PR 未修改任何指令，或修改量太小 |

## 為什麼是負數？

這是 **設計上的呈現方式**，用來強調「損失」或「未覆蓋」的概念：
- `-94.17%` = 94.17% 的修改未被測試覆蓋
- 負號表示這是「缺失的覆蓋率」

根據官方文件：
> "The delta has limitations. It can never be positive."

Delta 永遠不會是正數，因為它只衡量「未覆蓋的比例」。

## 附加發現：整體覆蓋率為 0% 的問題

報告顯示整體覆蓋率為 0%，這可能是獨立的配置問題：

### 可能原因

1. **執行資料路徑不匹配**
   - 配置預期路徑：`app/build/**/testDevelopDebugUnitTest.exec`
   - 實際 `.exec` 檔案可能產生在不同位置

2. **JaCoCo Agent 未正確附加**
   - 測試執行時可能沒有收集覆蓋率資料

3. **Class 目錄配置錯誤**
   - `classDirectories` 指向的路徑可能不存在或為空

### 建議驗證步驟

```bash
# 1. 執行測試並檢查 .exec 檔案位置
./gradlew testDevelopDebugUnitTest
find . -name "*.exec" -type f

# 2. 檢查 class 目錄是否存在
ls -la app/build/tmp/kotlin-classes/developDebug/

# 3. 手動執行 JaCoCo 報告並檢查輸出
./gradlew jacocoMultiModuleTestReport --info
```

## 結論

1. **負數 delta 是正常設計** - 表示 PR 修改中未被覆蓋的比例
2. **不是與 base branch 的歷史比較** - 而是當前 PR 變更的即時分析
3. **0% 整體覆蓋率需要另外調查** - 可能是 JaCoCo 配置問題

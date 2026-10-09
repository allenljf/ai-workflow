---
name: android-review
description: Android 程式碼準則稽核。對變更逐條比對 android-dev-guide 的規則，依 enforce 級別分成必修／建議修／可延後三類，PR 前自我檢查用。觸發詞：android-review、準則稽核、檢查違規、review 我的變更、有沒有違反規範、PR 前檢查。
---

# Android 準則稽核

對變更逐條比對準則，依 **enforce 級別**分類 —— 不是把所有違規都要求修，而是明確區分「現在必須修」「可以延後」。

與 `tools/check-rules.py` 的分工：

| | 腳本 | 這個 skill |
|---|---|---|
| 抓什麼 | 單檔正則可判定的（約 1/3 規則） | 需要理解上下文的（分層、UiState 設計、錯誤處理、測試強度） |
| 範圍 | 單一檔案 | 整份 diff |

**腳本過了不代表這裡會過。** 先跑腳本處理機械性違規，再用這個 skill 看設計層面。

---

## 守則

1. **先讀準則再稽核**，每條指控都要能指到 `rule-id` 與 `guides/` 的哪一份
2. **依 enforce 分類**，不要把 `migrate` 級的既有違規列成必修（那會讓 PR 爆炸）
3. **只稽核變更範圍**，未修改的檔案不列入
4. **不確定就標「需確認」**，不要斷言違規
5. 沒問題就說沒問題，**不要為了顯得有做事而湊數**

---

## Step 1：確認範圍

```bash
git diff --stat HEAD              # 未提交
git diff --stat origin/main...HEAD # 整個分支
```

範圍超過 30 個檔案時建議分批。

先跑腳本清掉機械性違規：

```bash
python3 android-dev-guide/tools/check-rules.py
```

## Step 2：依變更內容決定讀哪幾份

| 變更特徵 | 讀 |
|---|---|
| `*ViewModel.kt` | `08-ui-state` `12-coroutines-flow` |
| 含 `@Composable` | `09-compose-api` `10-compose-state` `14-design-system` |
| 含 `LazyColumn` / 動畫 | + `11-compose-performance` |
| `*ApiService.kt` / DTO | `06-network` `05-data-layer` |
| `*Repository*.kt` | `05-data-layer` `04-domain-layer` |
| domain 層檔案 | `04-domain-layer` `01-architecture` |
| `*Test.kt` | `15-testing` |
| DI module | `03-dependency-injection` |
| `build.gradle*` | `02-modularization` |
| 導航相關 | `13-navigation` |

`00-principles.md` 一律要讀。

## Step 3：逐條比對

重點放在**腳本抓不到的**：

| 面向 | 檢查什麼 |
|---|---|
| 分層 | 邏輯放對層了嗎？有沒有跨層直取 DataSource？domain 有沒有沾到 Android？ |
| UiState 設計 | 狀態散成多條還是收斂？loading/error 表達一致嗎？有沒有可推導卻另存的欄位？ |
| 事件處理 | one-off event 的做法與專案其他畫面一致嗎？ |
| 錯誤處理 | 錯誤被吞了嗎？有轉成 domain error 嗎？UI 拿得到可顯示的訊息嗎？ |
| 測試強度 | 斷言在驗行為還是只驗互動？relaxed mock 讓測試失去意義了嗎？邊界情況有測嗎？ |
| model 分層 | DTO 有沒有穿透到 UI？mapper 在正確的層嗎？ |
| DI | 有沒有繞過建構子注入？scope 與生命週期相符嗎？ |
| 一致性 | 同一個 PR 內兩處做法不同嗎？ |
| 命名 | 與專案既有慣例一致嗎？ |

## Step 4：查 enforce 分類

```bash
grep -A6 "id: <rule-id>" android-dev-guide/rules.yaml
```

| 分類 | 條件 |
|---|---|
| **必修** | `new-only` 且在新增檔案；或 `new-only+on-touch` 且在本次改動的區塊 |
| **建議修** | `on-touch` 但在同檔未改動處；或 SHOULD 級 |
| **可延後** | `migrate` 級；或改動風險大於收益 |

`exempt` 的不要列。

## Step 5：輸出

```
## 準則稽核

**範圍**：N 個檔案
**已對照**：00-principles、<領域檔...>
**腳本結果**：必修 N / 建議 N

### 必修

1. **[rule-id]** `檔案:行號`
   <一句話說明違規>
   ```kotlin
   // 現況
   ```
   改成：
   ```kotlin
   // 正確寫法
   ```
   準則：guides/<檔案>

### 建議修
（同格式，說明為什麼是建議而非必修）

### 可延後
1. **[rule-id]** `檔案:行號` — <為什麼不在本次修>

### 需確認
1. <描述> — <需要什麼資訊才能判斷>

### 已檢查無問題
<簡短列出對照過的重點，讓人知道稽核涵蓋範圍>

---
必修 N 項 / 建議 N 項 / 可延後 N 項
```

## Step 6：詢問是否套用

```
要我修掉必修的 N 項嗎？(y / 指定編號 / n)
```

修改後**重跑 Step 3** —— 改一處常常會動到別處。

---

## 注意

**產出是報告，不是重構。** 使用者同意才動手，且只動被列為必修的。

**遇到大量同類既有違規**（幾十上百處）不要列成一長串，寫一行「本檔有 N 處 X 類違規，屬 migrate 級，
建議獨立 PR 處理」即可。

**假綠燈測試要特別看**：無斷言、恆真斷言、被註解掉的斷言、無 ticket 的 `@Ignore`、
`relaxed mock` 讓未 stub 的呼叫靜默通過、只 `verify` 不 `assert`。這些腳本抓得到一部分，
但「斷言強度不足」只能靠人看。

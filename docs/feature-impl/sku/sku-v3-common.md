# SKU V3 一般商品規格頁 — 技術文件

## 1. 架構總覽

```
┌─────────────────────────────────────────────────────────────────┐
│                  CommonSpecificationActivity                    │
│  isSkuV3Enabled() ──┐                                           │
│                     │ true                                      │
│  ┌──────────────────▼──────────────────────────────────────┐    │
│  │         CommonSpecificationV3Fragment                    │    │
│  │  ┌──────────────┐  ┌──────────────────────────────┐     │    │
│  │  │SpecSharedVM  │  │     SkuSharedViewModel       │     │    │
│  │  │(舊 state 維護)│  │(V3 剪枝 / 價格 / 驗證)       │     │    │
│  │  └──────┬───────┘  └──────────────┬───────────────┘     │    │
│  │         │                         │                     │    │
│  │         │   ┌─────────────────────┘                     │    │
│  │         ▼   ▼                                           │    │
│  │  CommonSpecificationV3Controller                        │    │
│  │  (Epoxy: 月曆 / 方案 / 場次 / 規格 / 票種)               │    │
│  └─────────────────────────────────────────────────────────┘    │
│                     │ false                                      │
│  ┌──────────────────▼──────────────────────────────────────┐    │
│  │  CommonSpecificationFragment  (舊版，不變)               │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 檔案清單

| 層級 | 檔案 | 職責 |
|------|------|------|
| Activity | `CommonSpecificationActivity` | Feature Flag 分流；V3 啟用時 override 價格/驗證/訂單 |
| Fragment | `SharedSpecificationV3Fragment` | 橋接雙 VM；wrapper listeners 雙向轉發使用者操作 |
| Fragment | `CommonSpecificationV3Fragment` | 注入 `CommonSpecificationV3Controller` 及 V3 listeners |
| Controller | `SharedSpecificationV3Controller` | 將 `SkuPruningResult` 轉為 Epoxy UI 模型（月曆/場次/規格/票種）|
| Controller | `CommonSpecificationV3Controller` | 定義一般商品的 UI 區塊順序 |
| ViewModel | `SkuSharedViewModel` | 管理 `SkuSelectionState`，驅動剪枝計算，處理價格/積分 |
| Calculator | `SkuPruningCalculator` | 純邏輯：根據 API 資料 + 選擇狀態，計算每個選項的可用性 |
| Model | `SkuSelectionState` / `SkuPruningResult` | 選擇狀態與計算結果的資料結構 |

---

## 2. 運作流程

### 2.1 啟動流程

```
CommonProductDetailFragment
  └─ RouterHelper.dispatch(PAGE_SPECIFICATION)
       └─ CommonSpecificationActivity.onCreate()
            ├─ BaseActivity.onCreate() → RouterHelper.inject() → 注入 specificationData
            ├─ initData() → viewModel.setExtras(...)
            ├─ initView()
            │    └─ initFragment()
            │         ├─ isSkuV3Enabled() == true
            │         │    ├─ skuViewModel.selectPkgOid(packageId)
            │         │    └─ return CommonSpecificationV3Fragment
            │         └─ isSkuV3Enabled() == false
            │              └─ return CommonSpecificationFragment (舊版)
            ├─ viewReady()
            │    └─ skuViewModel.setProductDetailData(...)
            ├─ initOtherView()
            │    └─ 開始監聽 skuViewModel.pruningResult / selectionState / kkPointsInfo
            └─ observeData()
                 └─ 監聽舊 VM 的 state / eventBus 等
```

### 2.2 選擇操作流程（以選日期為例）

```
使用者點擊月曆日期
  └─ v3CalendarViewListener.onSelectedDate()
       ├─ viewModel.calendarViewListener.onSelectedDate()    ← 舊 VM（維護 CalendarViewInfo）
       └─ skuViewModel.selectDate(dateStr)                   ← V3 VM
            └─ calculateAndUpdateSkuAvailability()
                 └─ SkuPruningCalculator.calculateAvailability(packageData, calendarItem, selectionState)
                      ├─ calculateDateAvailability()
                      ├─ calculateEventAvailability()
                      ├─ calculateSpecAvailability()
                      └─ calculateTicketAvailability()
                           └─ 結果寫入 _pruningResult (StateFlow)
```

結果觸發 UI 更新：

```
skuViewModel.pruningResult 變化
  ├─ Fragment: specificationController.skuPruningResult = result → Epoxy 重建 UI
  └─ Activity: updateLayoutConfirmField() → 重新計算價格與積分顯示
```

場次、規格、票種的操作流程完全相同，差異僅在呼叫的 `skuViewModel` 方法不同：

| 操作 | 舊 VM 方法 | V3 VM 方法 |
|------|-----------|-----------|
| 選日期 | `calendarViewListener.onSelectedDate()` | `selectDate(dateStr)` |
| 選場次 | `specificationListener.onEventButtonClicked()` | `selectEvent(eventId)` |
| 選規格 | `specificationListener.onSpecButtonClicked()` | `selectSpec(specOid, specItemOid)` / `removeSpec(specOid)` |
| 改票數 | `specificationListener.onCountButtonClicked()` | `selectTicketQuantity(ticketId, quantity)` |

### 2.3 確認送出流程

```
使用者按下確認按鈕
  └─ checkAllItemValidV3(hasLogin)
       ├─ 1. isSKUV3AllRequiredFilled(isRealOpenDate) — 基本必填檢查
       │     失敗 → checkSKUV3BasicRequirements() → Toast 提示 → return
       ├─ 2. hasLogin 檢查
       │     失敗 → launchLoginActivity() → return
       ├─ 3. checkSKUV3QuantityRules() — 票種數量規則檢查
       │     失敗 → Snackbar 提示 → return
       ├─ 4. syncSKUV3ToSpecificationState() — 將 V3 選擇同步回舊 state
       ├─ 5. createAndFixOrderSpecificationData() — 建立訂單資料
       └─ 6. clickConfirmButton() → launchOrderFormFillingPage()
```

---

## 3. 剪枝計算邏輯

### 3.1 核心思路

每個選項以「自己為視角」，根據當前其他已選條件和 API 資料，判斷自己是否可選。

**與舊版差異**：舊版 V1/V2 使用窮舉法遍歷所有 SKU 組合（可達百萬量級），V3 則是對每個選項獨立計算可用性，迴圈次數 = 選項數量 × 規則數量，遠低於窮舉。

### 3.2 四個計算函式

#### `calculateDateAvailability()`
對每個日期檢查：
1. 日期是否在 API 的 `calendars` 中（有賣）
2. 是否 `isSoldOut`
3. 若已選場次 → 該日期是否有該場次且未關閉
4. 若已選規格 → 遍歷含此規格的 SKU，檢查至少一個在此日期可用
5. 庫存檢查（根據 `inventoryType` 分四種模式）

#### `calculateEventAvailability()`
對每個場次檢查：
1. 若已選日期 → 該場次是否出現在該日期的 events
2. 若已選規格 → 遍歷含此規格的 SKU，檢查至少一個在此場次可用
3. 計算 `remainQty`（顯示剩餘庫存）

#### `calculateSpecAvailability()`
對每個規格選項（排除 `spec-ticket` 和 `spec-single`）檢查：
1. 找出含此規格選項的所有 SKU
2. 若已選日期 → 至少一個 SKU 在該日期未關閉且有庫存
3. 若已選場次 → 至少一個 SKU 在該場次可用
4. 若已選其他規格 → SKU 需同時包含所有已選規格

#### `calculateTicketAvailability()`
對每個票種檢查：
1. 從 `spec-ticket` 或 `spec-single` 取出票種選項
2. 找出含此票種的所有 SKU
3. 結合已選日期/場次/規格，檢查至少一個 SKU 可用
4. 計算 `minQty` / `maxQty` / `availableQuantities`

### 3.3 庫存類型矩陣

| `inventoryType` | 常數 | 庫存來源 |
|-----------------|------|---------|
| `TYPE_PRICE_AND_TIME` | 方案 × 日曆 | `packageItem.calendars[date].remainQuantity[event]` |
| `TYPE_PRICE_AND_REMAIN` | 方案總量 | `packageItem.remainQuantity` |
| `TYPE_SKU_AND_REMAIN` | SKU 總量 | `skuData.remainQuantity` |
| `TYPE_SKU_AND_TIME` | SKU × 日曆 | `skuCalendarItems[skuId].calendar[date].remainQuantity[event]` |

### 3.4 資料結構

```
SkuSelectionState
  ├─ selectedDate: String?          (yyyy-MM-dd)
  ├─ selectedEvent: String?         (場次 ID)
  ├─ selectedSpecs: Map<specOid, specItemOid>
  └─ selectedTickets: Map<ticketSpecItemId, quantity>

SkuPruningResult
  ├─ availableDates:   List<DateAvailability>    → 每個日期是否可選
  ├─ availableEvents:  List<EventAvailability>   → 每個場次是否可選 + 剩餘庫存
  ├─ availableSpecs:   List<SpecAvailability>    → 每個規格選項是否可選
  └─ availableTickets: List<TicketAvailability>  → 每個票種是否可選 + min/max/qty
```

---

## 4. UI 渲染方式

### 4.1 Controller 架構

```
SharedSpecificationController (舊版基底)
  └─ SharedSpecificationV3Controller (V3 基底)
       └─ CommonSpecificationV3Controller (一般商品具體實作)
```

`SharedSpecificationV3Controller` 新增三個 pruning-driven 建構方法：

| 方法 | Epoxy 模型 | 資料來源 |
|------|-----------|---------|
| `createCalendarModelFromPruningResult()` | `SpecificationCalendarModel_` | `CalendarViewInfo` + `pruningResult.availableDates` 過濾 |
| `createSpecificationFromPruningResult()` | `SpecificationModel_` | `pruningResult.availableEvents` + `availableSpecs` → `SpecificationViewInfo` |
| `createCountModelFromPruningResult()` | `SpecificationCountModel_` | `pruningResult.availableTickets` → `SpecificationCountViewInfo` |

### 4.2 月曆渲染

月曆使用按月左右滑動的 `SpecificationCalendarModel_`（非七天橫向預覽）。渲染流程：

```
CalendarViewInfo (舊 VM 提供月份結構 + 日期標記)
  └─ filterAvailableDatesByPruningResult()
       └─ 遍歷每個月每天的 DateInfo：
            ├─ pruningResult 中該日期 isAvailable == false
            │    → DateInfo.copy(selectable = false)    (灰色不可點)
            └─ 保留 ONLY_END / BOTH_USE 類型的原始狀態
                 → 這些特殊日期類型不被 V3 剪枝覆蓋
```

### 4.3 場次 / 規格渲染

`convertPruningResultToSpecificationViewInfo()` 將 pruning result 轉為既有的 `SpecificationViewInfo`：

- `EventAvailability` → `EventDataViewInfo` → 場次區塊
- `SpecAvailability` → `SpecificationDataViewInfo` → 規格區塊
- `isAvailable == false` → `SpecificationContentStatus.isEnable = false`（灰色不可點）
- `isSelected == true` → `SpecificationContentStatus.isSelected = true`（高亮）

### 4.4 票種渲染

`createCountViewInfoFromPruningResult()` 將 `TicketAvailability` 轉為 `SpecificationCountViewInfo`：

- 每個票種 → `CountInfo`（含 `OrderUnit`、`min`、`max`、`count`）
- 價格透過 `skuSharedViewModel.getMinPriceForTicket()` 取得
- 積分透過 `skuSharedViewModel.getAccumulatedPackageCalendarItem()` + `KKPointsUiElement` 顯示

### 4.5 UI 區塊順序 (`CommonSpecificationV3Controller.addChildModels()`)

```
1. 月曆（按月滑動）
2. 間距
3. 方案標題（舊元件複用）
4. 方案列表（舊元件複用）
5. 間距
6. 場次 + 規格（V3 pruning 驅動）
7. 間距
8. 票種數量（V3 pruning 驅動）
9. 底部間距
```

---

## 5. 動態變價（GYG Dynamic Pricing）

### 5.1 概述

部分供應商（如 GYG）的商品價格非固定，而是根據日期、場次、SKU 組合及數量即時計算。
此類商品的 `productPackageCalendarData.product.shouldInstantSkuPrice == true`，
V3 透過 `SkuSharedViewModel` 中的動態變價機制處理，與一般靜態價格商品走不同的價格計算路徑。

### 5.2 資料模型

```
// API Request
SkuDynamicPriceRequestBody
  ├─ beginDate: String        (yyyy-MM-dd)
  ├─ endDate: String          (yyyy-MM-dd)
  └─ skus: List<SkuDynamicPriceSkuQty>
       ├─ skuOid: String      (SKU ID)
       └─ qty: Int            (數量)

// API Response: dynamic_price[date][time_slot]
SkuDynamicPriceData
  └─ dynamicPrice: Map<date, Map<event, SkuDynamicPriceSlot?>>

SkuDynamicPriceSlot
  ├─ isSoldOut: Boolean?
  ├─ skuPrice: Map<skuOid, unitPrice>   (每個 SKU 的單價)
  └─ totalPrice: String?                (所有 SKU 的加總總價)
```

### 5.3 核心變數（SkuSharedViewModel）

| 變數 | 類型 | 說明 |
|------|------|------|
| `_skuDynamicPrice` | `MutableStateFlow<Double?>` | 動態總價（API 回傳），UI 層訂閱此 Flow 刷新價格 |
| `lastDynamicPriceRequestKey` | `String?` | 上次請求的 key（去重，避免相同參數重複呼叫 API） |
| `lastDynamicPriceSlot` | `SkuDynamicPriceSlot?` | 快取的 API 回傳 slot，用於取得各票種單價和防閃爍 |
| `dynamicPriceJob` | `Job?` | 當前動態價格的協程 Job，選擇變更時會 cancel 舊的 |

### 5.4 觸發流程

```
使用者選擇日期/場次/規格/票種/方案
  └─ selectDate() / selectEvent() / selectSpec() / selectTicketQuantity()
       ├─ resetDynamicPriceState()           ← 取消舊 Job + 清除 _skuDynamicPrice
       ├─ calculateAndUpdateSkuAvailability() ← 照常剪枝
       └─ fetchDynamicPriceIfNeeded()        ← 觸發動態價格 API
            ├─ !isGYGProduct() → return（非 GYG 商品不觸發）
            ├─ !isSKUV3AllRequiredFilled() → 清除快取 + return（必填未完成不呼叫）
            └─ fetchSkuDynamicPrice()
                 ├─ 組裝 requestKey（date|packageId|skuOid:qty,...）
                 ├─ requestKey == lastKey && _skuDynamicPrice != null → return（去重）
                 └─ skuRepository.getSkuDynamicPrice(itemOid, date, skus)
                      ├─ 成功 → lastDynamicPriceSlot = validSlot
                      │        → _skuDynamicPrice.value = totalPrice
                      └─ 失敗 → lastDynamicPriceSlot = null
                               → _skuDynamicPrice.value = null
```

### 5.5 防閃爍機制

選擇變更時，`resetDynamicPriceState()` 會立即清除 `_skuDynamicPrice`（確保 StateFlow emit），
但**不會**清除 `lastDynamicPriceSlot`。這是為了：

1. **總價區**：`_skuDynamicPrice = null` 時，Activity 透過 `getCachedDynamicTotalPrice()` 取 `lastDynamicPriceSlot` 的舊值，避免一直顯示 `"- "`
2. **票種單價區**：Controller 透過 `getDynamicUnitPriceForTicket()` 從 `lastDynamicPriceSlot` 取舊單價，避免每次選擇變更時票種價格閃爍為 `"-"`
3. **新 API 回傳後**：`lastDynamicPriceSlot` 和 `_skuDynamicPrice` 同時更新，UI 自然切到新值

特殊情況：若必填項未填完整（`isSKUV3AllRequiredFilled = false`），會同時清除 `lastDynamicPriceSlot`，確保不顯示過期價格。

### 5.6 三層串接

#### Activity 層（`CommonSpecificationActivity`）

```
initOtherView()
  └─ skuViewModel.skuDynamicPrice.launchAndCollectIn(this) {
       updateLayoutConfirmField(currentState)    ← API 回傳時觸發底部確認欄刷新
     }

updateLayoutConfirmField(state)
  ├─ isGYGProduct() == true
  │    ├─ skuDynamicPrice.value ?: getCachedDynamicTotalPrice()
  │    │    ├─ 有值 → 顯示動態總價 + calculateAndUpdateKKPoints(dynamicPrice)
  │    │    └─ null → isGYGPricePending = true
  │    │              → setPriceText("- ")
  │    │              → setPointText("- ")
  │    │              → setButtonEnabled(false)   ← 價格未就緒時停用確認按鈕
  │    │              → setCommonTipsText(null)    ← 隱藏折扣提示
  │    └─ return
  └─ isGYGProduct() == false
       └─ calculatePriceFromSkuPruningResult()    ← 走一般靜態價格計算

selectedPackageId(packageId)
  └─ viewModel.selectPackage(packageId, isVM = true)
       └─ SpecificationSharedViewModel.selectPackage() 內部
            └─ clickSku() → fetchDynamicPriceIfNeeded()  ← 方案選擇後觸發動態價格

launchOrderFormFillingPage()
  └─ originPrice = skuDynamicPrice.value
                    ?: getCachedDynamicTotalPrice()
                    ?: calculatePriceFromSkuPruningResult()  ← fallback 鏈
```

#### Fragment 層（`SharedSpecificationV3Fragment`）

```
observeData()
  └─ skuViewModel.skuDynamicPrice.launchAndCollectIn(viewLifecycleOwner) {
       specificationController.skuSelectionState = skuViewModel.selectionState.value
       specificationController.requestModelBuild()   ← API 回傳時觸發票種 UI 重繪
     }
```

#### Controller 層（`SharedSpecificationV3Controller`）

```
createCountViewInfoFromPruningResult()
  ├─ isGYGProduct = skuSharedViewModel.isGYGProduct()
  └─ 對每個 ticketAvailability:
       ├─ minPrice = getMinPriceForTicket(...)               ← 靜態最低價（fallback）
       ├─ dynamicUnitPrice = if (isGYGProduct)
       │    getDynamicUnitPriceForTicket(ticketSpecItemId)    ← 從 lastDynamicPriceSlot 取
       │  else null
       ├─ displayPrice = dynamicUnitPrice ?: minPrice
       ├─ isPricePending = isGYGProduct && dynamicUnitPrice == null
       └─ CountInfo(
            orderUnit = OrderUnit(price = displayPrice),
            isPriceDisplay = !isPricePending    ← pending 時隱藏價格，避免顯示過期靜態價
          )
```

### 5.7 `getDynamicUnitPriceForTicket()` 邏輯

```kotlin
fun getDynamicUnitPriceForTicket(ticketSpecItemId: String): Double?
  ├─ lastDynamicPriceSlot == null → return null
  ├─ 該票種 selectedQty <= 0 → return null（避免顯示已取消票種的過期價格）
  ├─ 找出對應的 SKU（透過 ticketSpecItemId → specMap 反查）
  │    ├─ 虛擬票種（"virtual-ticket-unit"）→ 用 selectedSpecs 匹配 SKU
  │    └─ 一般票種 → 用 ticketSpecItemId 匹配 SKU
  └─ return slot.getUnitPrice(sku.skuId)
```

### 5.8 `syncSKUV3ToSpecificationState()` 的動態價格同步

在送出訂單前，`syncSKUV3ToSpecificationState()` 會將動態價格同步到舊版 `SpecificationState`：

```
步驟 6: 同步動態價格
  └─ dynamicPrice = lastDynamicPriceSlot?.totalPrice?.toDoubleOrNull()
       └─ state.copy(dynamicTotalPrice = dynamicPrice)
            → 下游 OrderFormFillingViewModel / CartReducer 使用 dynamicTotalPrice 計算訂單金額
```

### 5.9 與一般靜態價格的差異矩陣

| 項目 | 一般商品 | GYG 動態變價商品 |
|------|---------|-----------------|
| 判斷條件 | `shouldInstantSkuPrice != true` | `shouldInstantSkuPrice == true` |
| 底部總價來源 | `calculatePriceFromSkuPruningResult()` | `skuDynamicPrice.value ?: getCachedDynamicTotalPrice()` |
| 票種單價來源 | `getMinPriceForTicket()` | `getDynamicUnitPriceForTicket()` fallback `getMinPriceForTicket()` |
| 價格更新時機 | 選擇變更後立即計算（本地） | 選擇變更後發 API，等回傳更新（非同步） |
| Pending 狀態 | 無 | 有（`"- "` + 按鈕停用 + 折扣提示隱藏） |
| 訂單金額 | `state.getTotalPrice()` | `state.dynamicTotalPrice` |
| KKPoints 計算 | 基於靜態總價 | 基於動態總價 |

---

## 6. 排查與修復指南

### 6.1 開啟 Debug Log

`SkuPruningCalculator.enableLog = true`（預設 debug build 已開啟）

使用 Logcat 過濾 tag **`SKUV3`** 可看到完整計算過程：
- 每次計算的輸入狀態（已選日期/場次/規格/票種）
- 每個選項的可用性判斷結果與原因（`reason` 欄位）
- SKU 遍歷過程中的關閉/庫存檢查細節

### 6.2 常見問題排查路徑

#### 「某日期/場次/規格應該可選但顯示灰色」

1. Logcat 過濾 `SKUV3`，找到對應的 `calculateXxxAvailability` 區塊
2. 檢查 `reason` 欄位（如 `"all SKUs closed on date"`, `"no stock"` 等）
3. 根據 reason 追查：
   - `"closed"` → 確認 `packageItem.closeSkuList` 資料是否正確
   - `"no stock"` → 確認 `remainQuantity` 和 `inventoryType`
   - `"no matching SKU"` → 確認 SKU 的 specs 組合是否包含該選項

#### 「價格顯示不正確」

1. 確認 `calculatePriceFromSkuPruningResult()` 的回傳值
2. 檢查 `skuViewModel.selectionState` 中的 `selectedTickets` 是否正確
3. 價格計算邏輯：`∑(ticket_price × quantity)`，ticket_price 來自 `getMinPriceForTicket()`
4. 若未選票種，顯示七天內最低價

#### 「確認按鈕點了沒反應或錯誤訊息不對」

1. 追查 `checkAllItemValidV3()` 流程：
   - `isSKUV3AllRequiredFilled()` → 哪個必填項未填
   - `checkSKUV3BasicRequirements()` → 回傳的錯誤訊息
   - `checkSKUV3QuantityRules()` → 票種數量規則（min/max/倍數）
2. 確認 `syncSKUV3ToSpecificationState()` 是否正確將 V3 選擇同步回舊 state

#### 「月曆日期過濾不正確」

1. 確認 `filterAvailableDatesByPruningResult()` 的輸入：
   - `calendarViewInfo.calendarDataList` 有哪些月份/日期
   - `skuPruningResult.availableDates` 各日期的 `isAvailable`
2. 注意 `ONLY_END` / `BOTH_USE` 類型日期不會被 V3 覆蓋

#### 「V3 和舊版選擇狀態不同步」

1. 確認 wrapper listener（`v3CalendarViewListener`, `v3SpecificationListener`）是否同時呼叫了兩個 VM
2. 確認 `syncSKUV3ToSpecificationState()` 在送出前是否有正確執行
3. 確認 `observeData()` 中 `selectedPackageId` 變化時是否觸發了 `skuViewModel.initSkuApiData()`

### 6.3 狀態流監控斷點

最有效的斷點位置：

| 要觀察什麼 | 在哪設斷點 |
|-----------|-----------|
| 使用者選擇被正確接收 | `SharedSpecificationV3Fragment` 的 wrapper listener 方法內 |
| 剪枝計算觸發 | `SkuSharedViewModel.calculateAndUpdateSkuAvailability()` |
| 計算邏輯細節 | `SkuPruningCalculator.calculateAvailability()` |
| UI 更新觸發 | `SharedSpecificationV3Controller` 的 `skuPruningResult` setter |
| 價格更新 | `CommonSpecificationActivity.updateLayoutConfirmField()` 的 V3 分支 |
| 訂單資料建立 | `SkuSharedViewModel.createAndFixOrderSpecificationData()` |

### 6.4 Feature Flag 控制

- 開關位置：`AppSharedData.isEnableCommonSkuV3()`（對應 DCS `enable_common_sku_v3_version`）
- Debug build 預設 `true`；Release 走 Remote Config 版本門檻
- 關閉 Feature Flag 後完全走舊版路徑，無任何 V3 程式碼執行
- 可用於線上緊急回退

### 6.5 已知技術債 / 注意事項

1. **雙 VM 共存**：`SpecificationSharedViewModel`（舊）和 `SkuSharedViewModel`（V3）同時運作。V3 穩定後應移除對舊 VM 的依賴
2. **`PkgOid` 值類別**：比較或判空時必須使用 `.codeString()`，不可直接與 `String` 比較
3. **`loadAllPackageCalendarData()`**：V3 會一次性載入所有月份的日曆資料，注意大量資料場景的記憶體使用
4. **月曆特殊日期類型**：`ONLY_END` 和 `BOTH_USE` 不受 V3 剪枝影響，這是設計決策而非 bug

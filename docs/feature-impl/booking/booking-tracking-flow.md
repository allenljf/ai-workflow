# 訂單追蹤事件流程文件

## 概述
本文件描述訂單成功後的追蹤事件實作邏輯，包括價格欄位傳遞和事件發送機制。

## 架構設計

### 核心原則
- **統一追蹤點**: 所有訂單追蹤邏輯集中在 `PaymentReducer.getPaymentResultByOrderMIdResult` 函數中
- **正確價格來源**: 使用來自 API 回應的 `trackingPrice` 和 `trackingPriceTotal` 欄位
- **類型區分**: 根據 `originalPage` 區分購物車訂單和單一產品訂單

## 資料流程

### 1. 價格欄位來源
從 `getPaymentResultByOrderMId` API (GET v2/cart/info/{order_master_mid}) 回應中取得:

```kotlin
// OrderDetail.kt - SummaryData class (lines 253-254)
@SerializedName("price") val trackingPrice: Double?        // 折扣後金額
@SerializedName("price_total") val trackingPriceTotal: Double?  // 原始金額
```

### 2. 追蹤邏輯實作位置
**PaymentReducer.kt** - `getPaymentResultByOrderMIdResult` 函數 (lines 638-850)

```kotlin
// 提取追蹤價格
val summaryData = response.data.orders.firstOrNull()
val priceInUsd = summaryData?.trackingPrice ?: 0.0
val totalPriceInUsd = summaryData?.trackingPriceTotal ?: 0.0

// 判斷訂單類型
val originalPage = state.repayInfo().originalPage
if (originalPage == PAGE_TYPE_CART) {
    // 購物車訂單追蹤
} else {
    // 單一產品訂單追蹤 (包含特殊交通工具類型)
}
```

## 追蹤事件類型

### 1. 購物車訂單追蹤
使用 `toTrackerCartBookingSuccessEventInfo` 函數:

```kotlin
val trackerInfo = toTrackerCartBookingSuccessEventInfo(
    cartProducts = state.cartProducts(),
    createOrderResult = createOrderResult,
    paymentStrategy = state.paymentStrategy(),
    creditCard = state.creditCard(),
    affiliateProgramInfo = state.affiliateProgramInfo(),
    userInfo = state.userInfo(),
    isUsedRewardPoints = state.orderDeductInfo().isUsedRewardPoints,
    priceInUsd = priceInUsd,      // 來自 API 的正確價格
    totalPriceInUsd = totalPriceInUsd  // 來自 API 的正確價格
)
```

### 2. 單一產品訂單追蹤
使用 `toTrackerBookingSuccessEventInfo` 函數，支援一般產品和特殊交通工具:

#### 一般產品
```kotlin
val trackerInfo = toTrackerBookingSuccessEventInfo(
    // ... 其他參數
    priceInUsd = priceInUsd,
    totalPriceInUsd = totalPriceInUsd
)
```

#### 特殊交通工具 (遊輪類型)
```kotlin
when (specificationData.transportationType) {
    ROYAL_CRUISES, TransportationType.CRUQO_CRUISES -> {
        val eventInfo = convertCruisesTypeEvent(
            // ... 參數包含正確價格
            priceInUsd = priceInUsd,
            totalPriceInUsd = totalPriceInUsd
        )
        // 發送遊輪專用追蹤事件
    }
    else -> {
        // 一般產品追蹤
    }
}
```

## 事件發送機制

### 雙追蹤器模式
所有追蹤事件都透過兩個追蹤器發送:

```kotlin
// 1. 新版追蹤器
RxEventTracker.getInstance()
    .sendBookingSuccessEvent(trackerInfo)
    .subscribe()

// 2. 舊版追蹤器
OldRxEventTracker.getInstance()
    .sendBookingSuccessEvent(trackerInfo)
    .subscribe()
```

## 程式碼清理

### 移除的邏輯位置
1. **CartReducer.kt** - `bookingSuccessViewReady` 函數
   - 移除原有的 `toTrackerCartBookingSuccessEventInfo` 調用
   - 清理相關的 import 和變數

2. **OrderFormFillingReducer.kt** - `bookingSuccessViewReady` 函數
   - 移除所有追蹤邏輯，包含複雜的遊輪追蹤邏輯
   - 清理相關的 import，如 `convertCruisesTypeEvent`, `ROYAL_CRUISES` 等

### 保留的邏輯
所有追蹤邏輯統一移至 `PaymentReducer.getPaymentResultByOrderMIdResult`，確保:
- 正確的價格資料來源
- 統一的事件發送時機
- 完整的功能支援 (包含特殊交通工具)

## 相關文件位置

### 核心文件
- `TrackerBookingSuccessEventInfo.kt`: 追蹤資料結構和轉換函數
- `OrderDetail.kt`: 價格欄位定義 (`trackingPrice`, `trackingPriceTotal`)
- `PaymentReducer.kt`: 統一追蹤邏輯實作

### 清理過的文件
- `CartReducer.kt`: 移除購物車追蹤邏輯
- `OrderFormFillingReducer.kt`: 移除單一產品追蹤邏輯

## 維護注意事項

1. **價格欄位**: 務必使用來自 API 的 `trackingPrice` 和 `trackingPriceTotal`
2. **統一入口**: 所有追蹤邏輯都在 `PaymentReducer.getPaymentResultByOrderMIdResult`
3. **雙發送**: 確保新舊追蹤器都有發送事件
4. **特殊類型**: 遊輪等特殊交通工具有獨立的追蹤邏輯
5. **測試**: 修改追蹤邏輯時需測試購物車和單一產品兩種場景
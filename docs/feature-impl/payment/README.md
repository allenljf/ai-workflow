# 導航至支付頁

## 路由機制

支付頁以 KRouter 框架管理，路由常數定義於 `libs/routing`：

```kotlin
// libs/routing/.../KRouterConst.kt
const val PAGE_PAYMENT = "kkday://payment"
const val KEY_ORDER_ID = "order_id"
```

---

## 推薦方式：使用 `OrderRouterHelper`

若你的模組已依賴 `:libs:feature:order_page`，直接呼叫封裝好的函式：

```kotlin
OrderRouterHelper.navigateToPayment(
    context = context,
    orderMid = order.id,                          // 必填：訂單 id（用於 checkout API）
    orderMasterMid = order.orderMasterMid,        // 必填：訂單 master mid（用於 status log API）
    launcher = paymentResultLauncher,             // 選填：接收支付結果
    actionSource = PaymentActionSource.ORDER_DETAIL,  // 選填：來源頁面
    paymentStatus = PaymentStatusLog.Repay,           // 選填：支付行為類型
)
```

**來源檔案：**
`libs/feature/order_page/src/main/java/com/kkday/order_page/helper/OrderRouterHelper.kt`

---


## 參數說明

| 參數 | 路由 key | 類型 | 必填 | 說明 |
|------|----------|------|------|------|
| `orderMid` | `order_id` | String | 是 | `OrderInfo.id`，用於 checkout API |
| `orderMasterMid` | `key_order_master_id` | String | 是 | `OrderInfo.orderMasterMid`，用於 status log API |
| `paymentStatus` | `payment_status` | String | 否（預設 `Repay`） | 支付行為類型，見下表 |
| `actionSource` | `ACTION_SOURCE_KEY` | String | 否（預設 `ORDER_LIST`） | 來源頁面，用於埋點 |

### `PaymentStatusLog` 可用值

`PaymentStatusLog` 是 sealed class，定義於 `libs/base/.../model/Payment.kt`：

| 子類 | 值 | 使用情境 |
|------|----|---------|
| `PaymentStatusLog.Repay` | `"REPAY"` | 訂單待付款，用戶重新支付（最常見） |
| `PaymentStatusLog.Pay(paymentGroupId = ...)` | `"PAY"` | 初次支付（booking form / 購物車下單），需帶 `paymentGroupId` |
| `PaymentStatusLog.CreateOrder` | `"CREATE_ORDER"` | 建立訂單時同步付款 |
| `PaymentStatusLog.PayCancel` | `"PAY_CANCEL"` | 取消支付後重試 |
| `PaymentStatusLog.RedirectToPay` | `"REDIRECT_TO_PAY"` | 重導至支付頁 |

### `PaymentActionSource` 可用值

| 枚舉 | 值 | 說明 |
|------|----|------|
| `ORDER_LIST` | `"order_list"` | 訂單列表 |
| `ORDER_DETAIL` | `"order_detail"` | 訂單詳情 |
| `BOOKING_FORM` | `"booking_form"` | 預訂表單 |
| `SHOPPING_CART` | `"shopping_cart"` | 購物車 |
| `EDIT_ORDER` | `"edit_order"` | 修改訂單 |

來源：`libs/feature/order_page/.../helper/PaymentActionSource.kt`

---

## 接收支付結果

```kotlin
// 在 Fragment/Activity 中宣告 launcher
private val paymentResultLauncher = registerForActivityResult(
    ActivityResultContracts.StartActivityForResult()
) { result ->
    when (result.resultCode) {
        Activity.RESULT_OK -> { /* 支付成功 */ }
        RESULT_CODE_PAYMENT_UNCERTAIN -> {
            // 支付結果不確定（網路問題或用戶中途離開）
            // 建議重新查詢訂單狀態
        }
        Activity.RESULT_CANCELED -> { /* 用戶取消 */ }
    }
}
```

`RESULT_CODE_PAYMENT_UNCERTAIN = 10100`，定義於 `libs/base/.../util/Constants.kt`

---

## 自訂支付成功行為（PaymentResultLauncherHolder）

預設情況下，支付成功後 `PaymentActivity` 會自動導向 `BookingSuccessActivity`。

若你的功能需要**自行處理成功後的流程**（例如 USJ 加價付款需導向自定義成功頁），可在啟動 `PaymentActivity` 前注入 launcher：

```kotlin
// 1. 取得 Koin singleton
val holder: PaymentResultLauncherHolder by inject()

// 2. 宣告你的 launcher（使用自訂 contract 指定目標 Activity）
val successLauncher = registerForActivityResult(/* 你的 contract */) { result ->
    // 支付成功後的自訂處理
}

// 3. 啟動 PaymentActivity 前設定 holder
holder.launcher = successLauncher
OrderRouterHelper.navigateToPayment(context = context, orderMid = orderMid, ...)
```

**PaymentActivity 成功後的路由邏輯：**

```
updatePaymentResult()
  ├─ holder.launcher != null → holder.clear() + launcher.launch(intent) + finish()
  └─ holder.launcher == null → goToBookingSuccessActivity()（預設）
```

intent 會帶入以下 extras：

| Extra key | 說明 |
|-----------|------|
| `KEY_BOOKING_SUCCESS_PAYMENT_RESULT` | payment result JSON |
| `KEY_ORDER_MASTER_ID` | order master mid |

> **注意：** holder 在 `launcher.launch()` 後立即清除，不需手動清理。若 `PaymentActivity` 因任何原因未走到成功，holder 不會自動清除，下次啟動前請確認是否需要重設。

**相關檔案：**
- `app/.../view/payment/PaymentResultLauncherHolder.kt` — Koin singleton holder
- `app/.../view/payment/di/PaymentModule.kt` — Koin 註冊（`single { PaymentResultLauncherHolder() }`）

---

## 關鍵檔案速查

| 用途 | 路徑 |
|------|------|
| 路由常數 | `libs/routing/src/main/java/com/kkday/router/KRouterConst.kt` |
| 推薦啟動方法 | `libs/feature/order_page/src/main/java/com/kkday/order_page/helper/OrderRouterHelper.kt` |
| 來源枚舉 | `libs/feature/order_page/src/main/java/com/kkday/order_page/helper/PaymentActionSource.kt` |
| 支付狀態常數 | `libs/base/src/main/java/com/kkday/library/common/model/Payment.kt` |
| 結果碼常數 | `libs/base/src/main/java/com/kkday/library/common/util/Constants.kt` |
| 支付 Activity | `app/src/main/java/com/kkday/member/view/payment/PaymentActivity.kt` |

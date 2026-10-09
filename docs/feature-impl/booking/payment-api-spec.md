# 支付 API 規格文檔

本文檔整理 KKday Android App 使用的各種支付方式 API 規格。

## 📋 目錄

### 通用支付 API
1. [取得付款頻道](#1-取得付款頻道) - `POST v2.2/payment/booking/channels`
2. [支付狀態檢查](#2-支付狀態檢查) - `GET v2/cart/payment/check/{order_master_mid}`
3. [取得訂單支付結果](#3-取得訂單支付結果) - `GET v3/cart/info/{order_master_mid}`

### 信用卡儲存功能（TapPay）
4. [取得儲存的信用卡列表](#4-取得儲存的信用卡列表) - `POST v2/payment-token/list`
5. [儲存新信用卡](#5-儲存新信用卡) - `POST v2/payment-token/save`
6. [刪除儲存的信用卡](#6-刪除儲存的信用卡) - `POST v2/payment-token/delete`

### 各支付方式 API
7. [TapPay 支付](#7-tappay-支付)
8. [Stripe 支付](#8-stripe-支付)
9. [Adyen 支付](#9-adyen-支付)
10. [GMO 支付](#10-gmo-支付)
11. [KCP 支付](#11-kcp-支付)

---

## 通用支付 API

### 1. 取得付款頻道

**端點：** `POST v2.2/payment/booking/channels`  
**說明：** 根據訂單內容獲取可用的付款通道列表

#### 請求參數

| 名稱 | 型別 | 必填 | 說明 |
| --- | --- | --- | --- |
| order_master_mid | string | 是 | 訂單主 ID |
| product_oids | array | 是 | 商品 OID 列表 |
| product_mids | array | 是 | 商品 MID 列表 |
| currency | string | 是 | 幣別 |
| amount | number | 是 | 訂單金額 |
| locale | string | 是 | 地區代碼 |
| lang | string | 是 | 語言代碼 |
| login_channel | string | 否 | 會員登入頻道 (如 "FACEBOOK", "GOOGLE") |

#### 回應欄位

| 名稱 | 型別 | 說明 |
| --- | --- | --- |
| available_channels | array | 可用付款通道列表 |
| available_channels[].id | integer | 付款通道 ID (pmch_oid) |
| available_channels[].pmch_name | string | 付款通道名稱 |
| available_channels[].pmch_code | string | 付款通道代碼 |
| available_channels[].payment_method | string | 支付方式 (CREDIT_CARD, APPLE_PAY, etc.) |
| available_channels[].is_bindable | boolean | 是否支援儲存卡片功能 |
| available_channels[].payment_param | object | 支付參數（包含已儲存的卡片） |

---

### 2. 支付狀態檢查

**端點：** `GET v2/cart/payment/check/{order_master_mid}`  
**說明：** 輕量級的支付狀態檢查，僅返回基本狀態資訊

#### 請求參數

| 名稱 | 型別 | 必填 | 說明 |
| --- | --- | --- | --- |
| order_master_mid | path | 是 | 訂單主 ID |

#### 回應欄位

| 名稱 | 型別 | 說明 |
| --- | --- | --- |
| pay_deadline | string | 支付期限 |
| pay_deadline_time_left | integer | 剩餘支付時間（秒） |
| currency | string | 幣別 |
| master_price_total | number | 訂單總金額 |
| orders | array | 訂單狀態列表 |
| orders[].order_mid | string | 訂單 ID |
| orders[].order_status | string | 訂單狀態 (NEW/GO/BACK/CX) |

---

### 3. 取得訂單支付結果

**端點：** `GET v3/cart/info/{order_master_mid}`  
**說明：** 完整的訂單支付結果，包含所有訂單詳情和追蹤資訊（主要使用的 API）

> 💡 詳細說明請參考 [booking_flow.md](./booking_flow.md#支付處理相關-api)

#### 請求參數

| 名稱 | 型別 | 必填 | 說明 |
| --- | --- | --- | --- |
| order_master_mid | path | 是 | 訂單主 ID |
| locale | query | 是 | 地區代碼 |
| lang | query | 是 | 語言代碼 |

#### 回應欄位

回傳 `PaymentResult` 物件，包含：
- `point`: KK Points 獎勵總數
- `orders`: 訂單詳細列表（`List<SummaryData>`）
- `error`: 支付錯誤資訊
- `isOnlinePayment`: 是否為線上支付

---

## 信用卡儲存功能（TapPay）

> 基於 [SA/SD] 2025-04-18 Payment TW 儲存信用卡 文件整理

### 4. 取得儲存的信用卡列表

**端點：** `POST v2/payment-token/list`  
**API 文件：** [連結](https://api-b2c-03.sit.kkday.com/api-spec.html#tag/Payment/paths/~1v2~1payment-token~1list/post)

#### 請求參數

| 名稱 | 型別 | 必填 | 說明 |
| --- | --- | --- | --- |
| currency | string | 是 | 網頁顯示幣別 (如 "NTD") |
| login_channel | string | 是 | 登入頻道 (如 "FACEBOOK") |

### 請求範例
```json
{
  "currency": "NTD",
  "login_channel": "FACEBOOK"
}
```

### 回應參數

| 名稱 | 型別 | 必填 | 說明 |
| --- | --- | --- | --- |
| data.pmch_list | array | 否 | 付款頻道列表 |
| data.pmch_list[].pmch_oid | integer | 否 | 付款頻道編號 |
| data.pmch_list[].pmch_code | string | 否 | 付款頻道代碼 |
| data.pmch_list[].trans_pmch | string | 否 | 金流商，交易對象頻道 |
| data.pmch_list[].pmgw_setting | object | 否 | 金流gateway設定 |
| data.pmch_list[].pmgw_setting.sandbox | string | 否 | 是否為測試環境 |
| data.pmch_list[].pmgw_setting.app_id | string | 是 | 金流ID |
| data.pmch_list[].pmgw_setting.app_key | string | 是 | 金流密鑰 |
| data.pmch_list[].card_info | array | 是 | 卡片資訊列表 |
| data.pmch_list[].card_info[].fingerprint | string | 否 | 信用卡唯一識別碼 |
| data.pmch_list[].card_info[].last_four | string | 否 | 信用卡後四碼 |
| data.pmch_list[].card_info[].card_brand | string | 否 | 發卡組織 |
| data.pmch_list[].card_info[].first_six | string | 否 | 卡片前六碼 |
| data.pmch_list[].card_info[].issuer | string | 否 | 發卡銀行 |

### 回應範例

**有儲存卡片：**
```json
{
    "metadata": {
        "status": "0000",
        "desc": "success"
    },
    "data": {
        "pmch_list": [
            {
                "pmch_oid": 249,
                "pmch_code": "TW_TAPPAY_CREDIT_CARD_3D_TWD",
                "trans_pmch": "TAPPAY",
                "pmgw_setting": {
                    "app_id": "13615",
                    "app_key": "app_mrVp1B1Iw7z9aFAaSAcKkZfcvg6bljPlnrC0ifkV7ZbBCG6VNSH4mL4YiH3Q",
                    "sandbox": true
                },
                "card_info": [
                    {
                        "fingerprint": "e1d6dd33-d303-4591-b59a-c8e166c6b2c1",
                        "first_six": "424242",
                        "last_four": "4242",
                        "card_brand": "VISA",
                        "issuer": "中國信託銀行(CTBC Bank)"
                    }
                ]
            }
        ]
    }
}
```

**無儲存卡片：**
```json
{
  "metadata": {
    "status": "0000",
    "desc": "success"
  },
  "data": {
    "pmch_list": [
      {
        "pmch_oid": 249,
        "pmch_name": "信用卡",
        "pmch_code": "B2C_TW_TAPPAY_CREDIT_CARD_3D",
        "trans_pmch": "TAPPAY",
        "pmgw_setting": {
            "app_id": "13615",
            "app_key": "app_mrVp1B1Iw7z9aFAaSAcKkZfcvg6bljPlnrC0ifkV7ZbBCG6VNSH4mL4YiH3Q",
            "sandbox": true
        },
        "card_list": []
      }
    ]
  }
}
```

**錯誤回應：**
```json
{
    "metadata": {
        "status": "PAYM-SVC-TK-001",
        "desc": "暫時無法提供綁卡服務，請稍後再試"
    },
    "dynamic": null,
    "queue_it": {
        "version": 24
    },
    "data": null
}
```

---

## 3. 儲存新信用卡

**端點：** `POST v2/payment-token/save`  
**API 文件：** [連結](https://api-b2c-03.sit.kkday.com/api-spec.html#tag/Payment/paths/~1v2~1payment-token~1save/post)

### 請求參數

| 名稱 | 型別 | 必填 | 說明 |
| --- | --- | --- | --- |
| pmch_oid | integer | 是 | 付款通道編號 |
| trans_pmch | string | 是 | 金流對象頻道 |
| prime | string | 是 | 前端卡片加密 token |
| card_holder_info | object | 是 | 持卡人資訊 |
| card_holder_info.phone_number | string | 是 | 持卡人電話號碼 (如 "+886920856778") |

### 請求範例
```json
{
  "pmch_oid": 249,
  "trans_pmch": "TAPPAY",
  "prime": "test_3a2fb2b7e892b914a03c95dd4dd5dc7970c908df67a49527c0a648b2bc9",
  "card_holder_info": {
    "phone_number": "+886920856778"
  }
}
```

### 回應參數

| 名稱 | 型別 | 必填 | 說明 |
| --- | --- | --- | --- |
| data.fingerprint | string | 是 | 信用卡唯一識別碼 |
| data.is_redirect | boolean | 是 | 是否需轉跳驗證 |
| data.redirect_data | object | is_redirect=true 時必填 | 轉跳資料 |
| data.redirect_data.redirect_type | string | is_redirect=true 時必填 | 轉跳類型<br/>- `internal_browser`內開瀏覽器<br/>- `external_browser`外開瀏覽器<br/>- `sdk` |
| data.redirect_data.url | string | is_redirect=true 時必填 | 轉跳url |

### 回應範例

**需要 3D 驗證：**
```json
{
  "metadata": {
    "status": "0000",
    "desc": "success"
  },
  "data": {
    "fingerprint": "a6fb02ecb5a3ec7aca6a212cc8c811c7147e8a2bd5cfc0ee58c2169e20c459cf",
    "is_redirect": true,
    "redirect_data": {
      "redirect_type":"internal_browser",
      "url":"https://payment-206.sit.kkday.com/v3/payment-router/6e49c4f5-5392-4f1b-be29-d6bebafe7881?lang_code=zh-hk&trans_pmch=2C2P&type=app&parameter%5Burl%5D=VTJGc2RHVmtYMThHeUZyWkhPcUIzeWlEQUFENERmVzhIUDdraU1mcDMxbkV4by9MUjFBZUJ0U2xGT24wa0k0cktSL0FLdlg2Um9qODVmQzM2WVkybTZqTDBwa3dTWCtvMm10emFOWStLT0xsMDNwRUlrR0w1bFQyRW90SXJQb2p4amQrNjgvVWMvN1ZvRk1wdWlhRTlPbWY4RFVHa0szUzM4WUxob3h3bVlndDJKUjBQbkJ6bDRBUzF1TyttVk5L"
    }
  }
}
```

**儲存失敗：**
```json
{
    "metadata": {
        "status": "PAYM-SVC-TK-002",
        "desc": "請確認您的信用卡資訊是否正確，若資訊無誤，請聯繫發卡行或更換信用卡再試一次。"
    },
    "dynamic": null,
    "queue_it": {
        "version": 19
    },
    "data": null
}
```

**系統異常：**
```json
{
    "metadata": {
        "status": "9999",
        "desc": "zh-tw-系統異常"
    },
    "dynamic": null,
    "queue_it": {
        "version": 19
    },
    "data": null
}
```

---

## 4. 刪除儲存的信用卡

**端點：** `POST v2/payment-token/delete`  
**API 文件：** [連結](https://api-b2c-03.sit.kkday.com/api-spec.html#tag/Payment/paths/~1v2~1payment-token~1delete/post)

### 請求參數

| 名稱 | 型別 | 必填 | 說明 |
| --- | --- | --- | --- |
| fingerprint | string | 是 | 唯一識別碼 |

### 請求範例
```json
{
  "fingerprint": "a6fb02ecb5a3ec7aca6a212cc8c811c7147e8a2bd5cfc0ee58c2169e20c459cf"
}
```

### 回應範例

**成功：**
```json
{
  "metadata": {
    "status": "0000",
    "desc": "Success"
  },
  "data": null
}
```

**刪除失敗：**
```json
{
  "metadata": {
    "status": "PAYM-SVC-TK-003",
    "desc": "發生錯誤，請稍後再試。"
  },
  "data": null
}
```

**系統異常：**
```json
{
    "metadata": {
        "status": "9999",
        "desc": "zh-tw-系統異常"
    },
    "dynamic": null,
    "queue_it": {
        "version": 19
    },
    "data": null
}
```

---

## 各支付方式 API

### 7. TapPay 支付

#### 7.1 TapPay 付款

**端點：** `POST v2/payment/tappay/payment`  
**說明：** 使用 TapPay 進行支付，支援儲存卡功能

#### 主要請求參數

**端點：** `POST v2/payment/tappay/payment`  
**API 文件：** [連結](https://api-b2c-03.sit.kkday.com/api-spec.html#tag/Payment/paths/~1v2~1payment~1tappay~1payment/post)

### 新增請求參數

| 名稱 | 型別 | 必填 | 說明 |
| --- | --- | --- | --- |
| save_card | boolean | 否 | 是否儲存卡片 |
| card_holder_info.phone_number | string | 當 save_card 為 true 時必填 | 持卡人電話號碼 (國家區碼+電話號碼，如 "+886920856778") |
| payment_token_id | string | 使用已儲存卡片付款時必填 | 儲存卡 token id |

### 請求範例
```json
{
    "save_card": true,
    "credit_holder_info": {
        "phone_number": "+886920856778"
    },
    "payment_token_id": "a6fb02ecb5a3ec7aca6a212cc8c811c7147e8a2bd5cfc0ee58c2169e20c459cf",
    "payment_param3": "7DA4957D-D7FF-40B4-AE36-B083F506EC32",
    "pmch_oid": "248",
    "product_mids": ["5989"],
    "locale": "tw",
    "first_six": "515721",
    "last_four": "6804",
    "product_oids": ["18565"],
    "go_dates": ["2025-04-25"],
    "pay_currency": "TWD",
    "card_type": "MASTERCARD",
    "payment_group_id": 33960002,
    "coupons": [],
    "group_data": [],
    "is_hrp": "N",
    "card_country_cd": "TW",
    "currency": "TWD",
    "order_master_mid": "25MM223642167",
    "booking_type": "instant",
    "prime": "63dfc9ee1910226dfa205a1bfa0e2daa12ed69c2015240f00168ba577427b958",
    "issuer": "Taishin Bank",
    "lang": "zh-tw",
    "amount": 666,
    "card_country": "TAIWAN R.O.C.",
    "pmch_code": "TW_TAPPAY_CREDIT_CARD_TWD",
    "client_ip": "211.23.126.123"
}
```

---

## 6. TAPPAY 付款回調

**端點：** `POST v2/payment/tappay/payment_return`  
**API 文件：** [連結](https://api-b2c-03.sit.kkday.com/api-spec.html#tag/Payment/paths/~1v2~1payment~1tappay~1payment_return/post)

### 新增請求參數

| 名稱 | 型別 | 必填 | 說明 |
| --- | --- | --- | --- |
| save_card | boolean | 否 | 是否儲存卡片 |
| card_holder_info.phone_number | string | 當 save_card 為 true 時必填 | 持卡人電話號碼 (國家區碼+電話號碼，如 "+886920856778") |

### 請求範例
```json
{
    "save_card": true,
    "card_holder_info": {
        "phone_number": "+886920856778"
    },
    "amount": 699,
    "payment_param3": "eaSQ6I45Tyexnci4VTm7mA",
    "auth_code": "085619",
    "bank_transaction_id": "25MM227642157ZM2Z",
    "currency": "TWD",
    "group_data": [],
    "is_hrp": "N",
    "lang": "zh-tw",
    "locale": "tw",
    "order_master_mid": "25MM227642157",
    "pmch_oid": "248",
    "product_mids": ["24011"],
    "product_oids": ["24011"],
    "rec_trade_id": "D20250421UQgFOj",
    "go_dates": ["2025-04-29"],
    "status": "0",
    "pmgw_trans_no": "PMGW054836322",
    "client_ip": "123.240.86.231"
}
```

---

## 錯誤代碼

| 錯誤代碼 | 說明 |
| --- | --- |
| 0000 | 成功 |
| PAYM-SVC-TK-001 | 暫時無法提供綁卡服務，請稍後再試 |
| PAYM-SVC-TK-002 | 請確認您的信用卡資訊是否正確，若資訊無誤，請聯繫發卡行或更換信用卡再試一次 |
| PAYM-SVC-TK-003 | 發生錯誤，請稍後再試 |
| 9999 | 系統異常 |

---

---

### 8. Stripe 支付

#### 8.1 Stripe 支付授權

**端點：** `POST v2/payment/stripe/auth`  
**說明：** 使用 Stripe Token 進行支付授權

#### 主要請求參數

| 名稱 | 型別 | 必填 | 說明 |
| --- | --- | --- | --- |
| pmch_oid | string | 是 | 付款通道 ID |
| order_master_mid | string | 是 | 訂單主 ID |
| product_mids | array | 是 | 商品 MID 列表 |
| product_oids | array | 是 | 商品 OID 列表 |
| go_dates | array | 是 | 出發日期列表 |
| currency | string | 是 | 幣別 |
| pay_currency | string | 是 | 支付幣別 |
| amount | number | 是 | 金額 |
| booking_type | string | 是 | 訂購類型 (instant/cart/repay) |
| source_id | string | 是 | Stripe Source ID |
| locale | string | 是 | 地區代碼 |
| lang | string | 是 | 語言代碼 |

#### 回應欄位

回傳 `PaymentResult` 物件

---

#### 8.2 Stripe V2 支付

**端點：** `POST v2.1/payment/stripe/payment`  
**說明：** Stripe V2 版本支付處理

#### 主要請求參數

使用 `TransactionData` 物件，包含：
- 訂單資訊（order_master_mid, product_mids, product_oids）
- 支付資訊（pmch_oid, currency, amount）
- 信用卡資訊（credit_card_info）

#### 回應欄位

| 名稱 | 型別 | 說明 |
| --- | --- | --- |
| is_success | boolean | 是否成功 |
| is_redirect | boolean | 是否需要跳轉（3D Secure） |
| redirect_data | object | 跳轉資料 |
| pmgw_trans_no | string | 交易號碼 |

---

#### 8.3 Stripe V2 確認支付

**端點：** `POST v2.1/payment/stripe/payment_return`  
**說明：** Stripe 3D Secure 驗證後確認支付

#### 主要請求參數

使用 `TransactionConfirmData` 物件

#### 回應欄位

回傳 `PaymentResult` 物件

---

#### 8.4 取得 Stripe 卡片資訊

**端點：** `GET v2/payment/stripe/card_info`  
**說明：** 取得 Stripe 儲存的卡片資訊

#### 請求參數

| 名稱 | 型別 | 必填 | 說明 |
| --- | --- | --- | --- |
| pmch_oid | query | 是 | 付款通道 ID |
| payment_method_id | query | 是 | 支付方式 ID |

---

### 9. Adyen 支付

#### 9.1 Adyen 支付處理

**端點：** `POST v2/payment/adyen/payment`  
**說明：** 使用 Adyen Components 進行支付

#### 主要請求參數

| 名稱 | 型別 | 必填 | 說明 |
| --- | --- | --- | --- |
| pmch_oid | string | 是 | 付款通道 ID |
| order_master_mid | string | 是 | 訂單主 ID |
| product_mids | array | 是 | 商品 MID 列表 |
| product_oids | array | 是 | 商品 OID 列表 |
| currency | string | 是 | 幣別 |
| amount | number | 是 | 金額 |
| payment_method | object | 是 | Adyen 支付方式資料 |
| return_url | string | 是 | 3D Secure 返回 URL |
| browser_info | object | 否 | 瀏覽器資訊（3D Secure 需要） |

#### 回應欄位

| 名稱 | 型別 | 說明 |
| --- | --- | --- |
| result_code | string | 結果代碼 (Authorised/RedirectShopper/etc) |
| action | object | 需要執行的動作（如 3D Secure） |
| psp_reference | string | PSP 參考號 |

---

#### 9.2 Adyen 3D Secure 確認

**端點：** `POST v2/payment/adyen/payment_details`  
**說明：** Adyen 3D Secure 驗證後提交詳情

#### 主要請求參數

| 名稱 | 型別 | 必填 | 說明 |
| --- | --- | --- | --- |
| details | object | 是 | 支付詳情 |
| payment_data | string | 否 | 支付數據 |

#### 回應欄位

回傳 `PaymentResult` 物件

---

### 10. GMO 支付

#### 10.1 GMO 支付處理

**端點：** `POST v2/payment/gmo/payment`  
**說明：** 使用 GMO 進行支付處理（日本市場）

#### 主要請求參數

使用 `TransactionData` 物件

#### 回應欄位

| 名稱 | 型別 | 說明 |
| --- | --- | --- |
| is_success | boolean | 是否成功 |
| is_redirect | boolean | 是否需要跳轉 |
| redirect_data | object | 跳轉資料 |
| pmgw_trans_no | string | 交易號碼 |

---

#### 10.2 GMO 支付確認

**端點：** `POST v2/payment/gmo/payment_return`  
**說明：** GMO 3D Secure 驗證後確認支付

#### 主要請求參數

使用 `TransactionConfirmData` 物件

#### 回應欄位

回傳 `PaymentResult` 物件

---

### 11. KCP 支付

#### 11.1 KCP 支付處理

**端點：** `POST v2/payment/kcp/payment`  
**說明：** 使用 KCP 進行支付處理（韓國市場）

#### 主要請求參數

使用 `TransactionData` 物件

#### 回應欄位

與 GMO 相同格式

---

#### 11.2 KCP 支付確認

**端點：** `POST v2/payment/kcp/payment_return`  
**說明：** KCP 支付驗證後確認

#### 主要請求參數

使用 `KCPTransactionConfirmData` 物件，額外包含：
- `res_cd`: 結果代碼
- `enc_data`: 加密數據
- `enc_info`: 加密資訊
- `tran_cd`: 交易代碼

#### 回應欄位

回傳 `PaymentResult` 物件

---

## 通用支付資料結構

### TransactionData

所有支付方式共用的交易數據結構：

```kotlin
data class TransactionData(
    pmch_oid: String,                    // 付款通道 ID
    order_master_mid: String,            // 訂單主 ID
    product_mids: List<String>,          // 商品 MID 列表
    product_oids: List<String>,          // 商品 OID 列表
    go_dates: List<String>?,             // 出發日期列表
    currency: String,                    // 幣別
    pay_currency: String,                // 支付幣別
    amount: Double,                      // 金額
    booking_type: String,                // 訂購類型 (instant/cart/repay)
    locale: String,                      // 地區
    lang: String,                        // 語言
    is_hrp: String,                      // 是否高風險商品 (Y/N)
    payment_group_id: Int?,              // 支付群組 ID
    group_data: List<PaymentGroupData>,  // 群組數據
    credit_card_info: CreditCardInfo?    // 信用卡資訊
)
```

### TransactionConfirmData

支付確認數據結構：

```kotlin
data class TransactionConfirmData(
    pmch_oid: String,
    pmgw_trans_no: String?,              // 交易號碼
    order_master_mid: String,
    currency: String,
    pay_currency: String,
    amount: Double,
    product_mids: List<String>,
    product_oids: List<String>,
    go_dates: List<String>?,
    is_hrp: String,
    locale: String,
    lang: String?,
    group_data: List<PaymentGroupData>
)
```

---

## 錯誤代碼

| 錯誤代碼 | 說明 |
| --- | --- |
| 0000 | 成功 |
| PAYMENT0001 | 支付處理失敗 |
| PAYMENT0002 | 信用卡驗證失敗 |
| PAYMENT0003 | 3D Secure 驗證失敗 |
| PAYMENT0004 | 支付金額異常 |
| PAYM-SVC-TK-001 | 暫時無法提供綁卡服務，請稍後再試 |
| PAYM-SVC-TK-002 | 請確認您的信用卡資訊是否正確，若資訊無誤，請聯繫發卡行或更換信用卡再試一次 |
| PAYM-SVC-TK-003 | 發生錯誤，請稍後再試 |
| T709 | 庫存不足（交通商品） |
| T722 | 價格異常（交通商品） |
| T721 | 內部錯誤（交通商品） |
| 9999 | 系統異常 |

---

## 重要注意事項

### TapPay 儲存卡功能
1. **適用對象**：本功能僅適用於第三方登入用戶(非KKDAY登入)
2. **3D 驗證**：儲存卡片時一定要進行3D驗證
3. **付款驗證**：付款時如勾選儲存卡片，也需進行3D驗證
4. **預設卡片**：預設卡為上次付款成功的卡片
5. **系統架構**：B2C API主要負責參數的處理與轉發，實際儲存卡片的邏輯由Payment Service處理

### 支付流程通用規則
1. **3D Secure 驗證**：大部分信用卡支付都需要進行 3D Secure 驗證
2. **Deep Link 返回**：驗證完成後透過 Deep Link 返回 App（格式：`kkday://[instant|cart|repay]/[payment_type]_return`）
3. **狀態檢查**：所有支付完成後都需要呼叫 `getPaymentResultByOrderMId` 確認最終狀態
4. **訂單狀態**：`orderStatusType = 0 (CREATE_ORDER)` 表示支付未完成，其他值表示支付成功

### 相關文檔
- 完整訂購流程：[booking_flow.md](./booking_flow.md)
- Deep Link 處理：[booking_flow.md#各支付方式的返回處理流程](./booking_flow.md#各支付方式的返回處理流程)

 
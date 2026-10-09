# 信用卡綁卡測試卡號

App 信用卡綁卡測試卡號留存，分為 **TapPay** 與 **GMO** 兩個頻道。

---

## TapPay 頻道

TapPay Direct Pay（prime）綁卡流程於 **Sandbox 環境**使用的測試卡號。

### 環境前提

- App 綁卡走 TapPay Direct Pay，環境由後端 API 回傳的 `tap_pay.is_sandbox` 決定，預設 `true`（Sandbox）。
- 以下卡號**僅於 Sandbox 有效**；正式環境（Production）會被拒絕，需使用真實卡片。
- 設定來源：`libs/payment/src/main/java/com/kkday/payment/source/Tappay.kt`
  - 預設 App ID `13615`、App Key `app_mrVp1B1...`（Sandbox 測試金鑰）

### 可用測試卡號

| 卡別 | 卡號 | 到期日 | CCV | 綁卡驗證狀態 |
|------|------|--------|-----|--------------|
| Mastercard | `5451 4178 2523 0575` | 任意未來日期（如 `12/30`） | 任意三碼（如 `123`） | ✅ 已實測可綁卡 |
| Visa | `4242 4242 4242 4242` | 任意未來日期 | 任意三碼 | 官方測試卡（未實測） |

- **到期日**：填任何「未來」的月年即可。
- **CCV**：任意 3 碼。

---

## GMO 頻道

GMO 綁卡走 token 流程（非 prime），限定 JPY + 日文語系 + 第三方登入情境。

### 可用測試卡號

| 卡號 | 3DS | 到期日 | CCV | 綁卡驗證狀態 |
|------|-----|--------|-----|--------------|
| `4100 0000 0000 5000` | ✅ 是（3D 驗證） | 任意未來日期 | 任意三碼 | 由使用者提供 |
| `4100 0000 0000 0100` | ✅ 是（3D 驗證） | 任意未來日期 | 任意三碼 | 由使用者提供 |

- 兩張 GMO 測試卡皆會觸發 3DS 驗證流程，可用於測試 3D Secure。

---

## 相關程式碼

| 階段 | 檔案 |
|------|------|
| TapPay Token / prime 生成 | `app/src/main/java/com/kkday/member/view/product/form/helper/TappayHelper.kt` |
| TapPay 綁卡處理 | `app/src/main/java/com/kkday/member/reducer/payment/paymentType/TapPayHandler.kt` |
| 綁卡儲存 API（TapPay 傳 `prime`、GMO 傳 `token`） | `data/repository/src/main/java/com/kkday/data/repository/creditcardlist/CreditCardRepository.kt` |

## 注意事項

- `PaymentViewModel.kt` 內曾有綁卡 UI 測試用的 hardcode JSON（`HARDCODE_GMO_CHANNEL_JSON` / `HARDCODE_TAPPAY_CHANNEL_JSON`），僅供 UI 驗證且金鑰非真值，**禁止 commit 進 release branch**。
- TapPay 測試卡號為官方公開 Sandbox 測試資料；GMO 測試卡號為測試環境用，皆非真實持卡人資訊。

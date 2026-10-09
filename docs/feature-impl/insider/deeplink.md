# Insider Deep Link 接收與路由

## 1. 接收器註冊

位置：[`KKdayApp.setupInsider()`](../../../app/src/main/java/com/kkday/member/KKdayApp.kt) 內，line 604-612。

```kotlin
Insider.Instance.registerInsiderCallback { payload, type ->
    if (type == InsiderCallbackType.NOTIFICATION_OPEN) {
        handleInsiderNotificationOpen(payload)
    }
}
```

SDK 提供 `InsiderCallback` 介面，會 fire 多種 type，目前只接 `NOTIFICATION_OPEN`：

| Type | 觸發時機 | 目前處理 |
|---|---|---|
| `NOTIFICATION_OPEN` | push 通知被點擊 | ✓ `handleInsiderNotificationOpen` |
| `INAPP_BUTTON_CLICK` | In-App Message CTA 被點擊 | ✗ 未接 |
| `TEMP_STORE_VISITED` | Smart Recommender 觸發 | ✗ 未接 |

## 2. payload 處理

位置：[`KKdayApp.handleInsiderNotificationOpen`](../../../app/src/main/java/com/kkday/member/KKdayApp.kt)，line 627-641。

```kotlin
private fun handleInsiderNotificationOpen(payload: JSONObject) {
    val data = payload.optJSONObject("data") ?: payload
    val target = sequenceOf("ins_dl_internal", "ins_dl_external", "ins_dl_url_scheme")
        .map { data.optString(it) }
        .firstOrNull { it.isNotEmpty() } ?: return
    val intent = Intent(ACTION_VIEW, Uri.parse(target)).apply {
        addFlags(FLAG_ACTIVITY_NEW_TASK)
    }
    startActivity(intent)
}
```

payload 結構（Insider SDK 16.x）：
```json
{
  "type": 0,
  "data": {
    "ins_dl_internal": "https://www.kkday.com/zh-tw/product/2425",
    "ins_dl_external": "...",
    "ins_dl_url_scheme": "kkday://..."
  }
}
```

deep link 在 `data` 內層。

## 3. 三種 key 的程式端行為

**沒有分流邏輯**。三種 key 差別只在 priority（誰被選中），被選中後**走同一條 ACTION_VIEW**，由 OS intent-filter 決定實際 routing。

優先序：`ins_dl_internal` → `ins_dl_external` → `ins_dl_url_scheme`

| Panel 填法 | 程式端行為 | 實際結果 |
|---|---|---|
| `ins_dl_internal = https://www.kkday.com/...` | ACTION_VIEW → kkday intent-filter 接 | 站內開 |
| `ins_dl_external = https://example.com/...` | ACTION_VIEW → 沒人接 → 落 browser | 瀏覽器開 |
| `ins_dl_external = https://www.kkday.com/...` | ACTION_VIEW → kkday intent-filter 接 | **站內開**（行銷預期瀏覽器會落空）|
| `ins_dl_url_scheme = kkday://...` | ACTION_VIEW → kkday intent-filter 接 | 站內開 |
| `ins_dl_json` | — | ✗ 未實作 |

## 4. 為什麼不做分流

Insider 設計 `internal` vs `external` 兩個欄位的本意是「行銷明示意圖」：
- internal = 在 app 內打開
- external = 踢出 app（強制瀏覽器 / 外部 app）

但 Android 端目前完全不看意圖、只看 URL 是否被 intent-filter 接：

| 取捨 | 說明 |
|---|---|
| ✓ 邏輯極簡，攻擊面小 | URL 字串怎麼填都不會誤開敏感頁，全由 OS 把關 |
| ✗ external 填 kkday URL 想開瀏覽器會被自家攔截 | 跟行銷意圖不符 |
| ✗ 強制 browser 的寫法跨 Android 版本行為不一致 | Custom Tabs vs browser chooser，實作分歧 |

決議：先打通，分流邏輯有實際案例再加。

## 5. 路由實際走向（OS intent-filter）

ACTION_VIEW 後 OS 依 intent-filter 比對 URL，落到 [`WelcomeActivity`](../../../app/src/main/java/com/kkday/member/view/launch/WelcomeActivity.kt)。詳細 host / scheme / path 對應見 [`AndroidManifest.xml`](../../../app/src/main/AndroidManifest.xml) line 222-403。

關鍵 intent-filter：

| scheme | host | path | filter 行號 |
|---|---|---|---|
| `https://` | kkday 全環境 host（sit/stage/prod web+mobile + `*.sit.kkday.com`）| 各語系首頁 path literal | 248-280（autoVerify）|
| `https://` | 同上 | `/.*/product/...`、`/.*/order/...` 等 pathPattern | 282-378（autoVerify）|
| `kkday://` | `appsflyer-launch` | — | 237-246 |
| `kkday://` | build flavor 的 `web_site_url` / `mobile_site_url` | **任意 path（含 lang prefix）** | 393-403 |
| `android-kkday://` | build flavor 的 `package_name` | `/product`、`/search` | 380-391 |

> `kkday://` 跟 `android-kkday://` 原本塞在同一 filter，pathPrefix `/product` `/search` 被連帶套到兩者，造成 `kkday://www.kkday.com/{lang}/...` 無法 resolve。已在 commit `7c15e00689` 拆成兩個獨立 filter。

## 6. 跨環境 host 對照

`kkday://` 與 `android-kkday://` 的 host 綁 build flavor，跨環境不通用：

| Build flavor | `kkday://` 接的 host | `android-kkday://` 接的 host |
|---|---|---|
| develop | `www.sit.kkday.com` / `m.sit.kkday.com` | `com.kkday.member.develop` |
| stage | `www.stage.kkday.com` / `m.stage.kkday.com` | `com.kkday.member.stage` |
| production | `www.kkday.com` / `m.kkday.com` | `com.kkday.member` |
| 全 build 共用 | `appsflyer-launch` | — |

`https://` 全 build 都接 sit / stage / prod 三套 host（[manifest line 254-261](../../../app/src/main/AndroidManifest.xml)），**推 PM 用 https 當主要填法**跨環境 0 痛苦。

## 7. 已知未驗證 / 風險

1. **Click tracking redirect**：Insider Panel 後台若開啟 click tracking URL wrapping，payload `ins_dl_*` 會變成 `https://eu1.insrv.com/click?...` 而非原始 URL，host 對不上 intent-filter → 落瀏覽器再 302 回 app（用戶會看到閃一下瀏覽器）。需與 CSM 確認 partner 後台是「SDK 內部追蹤」模式（mode A）而非「URL wrapping」模式（mode B）。實測：發 test push + logcat 比對 payload 與 Panel 填值是否一致。
2. **Cold start race**：app 被殺後點 push → `KKdayApp.onCreate` → `setupInsider()` 註冊 callback。理論上 SDK 可能在 callback 註冊前已 emit `NOTIFICATION_OPEN`，造成第一次冷啟 deep link 不 route。未實測。
3. **In-App Message CTA**：`registerInsiderCallback` 只接 `NOTIFICATION_OPEN`，畫面內彈窗 CTA 的 deep link 未處理。

## 相關 commit

- `7c15e00689` [feat][MEMAndroid-Insider] 支援 ins_dl_url_scheme + 拆 intent-filter

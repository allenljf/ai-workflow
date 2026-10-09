# KKday Android Member App 新增語系：後端配合說明

> 對象：後端團隊
> 範圍：App 端新增語系時，後端 / Web / 第三方平台需配合確認的事項
> 撰寫日期：2026-06-11

---

## 1. 重要釐清：8 語系 vs 17 LanguageType

「8 語系」是指 **8 種基礎語言代碼**，但 App 實際在 `LanguageType` enum 提供 **17 種「語言 + 國家/地區」組合**（主要是英文的多地區變體）。

**8 種基礎語言**（對應 8 套字串資源）：
`en`、`ja`、`ko`、`th`、`vi`、`zh-cn`、`zh-hk`、`zh-tw`

關鍵機制：**`lang`（languageCode）決定字串內容**，而 `locale`（countryCode）只影響 API `locale` header 與貨幣/地區邏輯。這就是 17 種 LanguageType 收斂成 8 套字串的原因——9 個英文變體共用 `lang=en`、2 個簡中變體共用 `lang=zh-cn`。

> 對後端的意義：App 送出的 `lang` 與 `locale` 是**兩個獨立維度**。同一個 `lang=en` 可能搭配 `locale=au/us/sg/...` 等多種國家碼，後端需依兩者各自處理（文案語言 vs 地區/幣別邏輯）。

---

## 2. 語系對照表

App 對每個語系送出的 API header / Web 參數 / 第三方追蹤值如下。後端串接時請以 **lang** 與 **locale** 兩欄為準。

| 顯示名稱 | API `lang` | API `locale` | `webLangKey` | Insider locale | 命中 strings.xml |
|---|---|---|---|---|---|
| English (Australia) | `en` | `au` | `en-au` | `en_AU` | `values/`（預設） |
| English (Indonesia) | `en` | `id` | `en-id` | `en_ID` | `values/` |
| English (International) | `en` | `kk` | `en` | `en_US` | `values/` |
| English (Malaysia) | `en` | `my` | `en-my` | `en_MY` | `values/` |
| English (Philippines) | `en` | `ph` | `en-ph` | `en_PH` | `values/` |
| English (New Zealand) | `en` | `nz` | `en-nz` | `en_NZ` | `values/` |
| English (Singapore) | `en` | `sg` | `en-sg` | `en_SG` | `values/` |
| English (United States) | `en` | `us` | `en-us` | `en_US` | `values/` |
| English (Hong Kong) | `en` | `hk` | `en-hk` | `en_HK` | `values/` |
| 日本語 | `ja` | `jp` | `ja` | `ja_JP` | `values-ja-rJP` |
| 한국어 | `ko` | `kr` | `ko` | `ko_KR` | `values-ko-rKR` |
| ไทย | `th` | `th` | `th` | `th_TH` | `values-th-rTH` |
| Tiếng Việt | `vi` | `vn` | `vi` | `vi_VN` | `values-vi-rVN` |
| 简体中文 | `zh-cn` | `cn` | `zh-cn` | `zh_CN` | `values-zh-rCN` |
| 简体中文(马来西亚) | `zh-cn` | `my` | `zh-my` | `zh_MY` | `values-zh-rCN` |
| 繁體中文(香港) | `zh-hk` | `hk` | `zh-hk` | `zh_HK` | `values-zh-rHK` |
| 繁體中文(台灣) | `zh-tw` | `tw` | `zh-tw` | `zh_TW` | `values-zh-rTW` |

> 補充：
> - `English (International)` 的 `locale=kk` 為 KKday 內部 placeholder（非 ISO 3166-1），第三方 Insider fallback 成 `en_US`。
> - 新增列「Bahasa Indonesia」為本次擴充語系，**請後端確認 `lang=id` / `locale=id` 支援**（詳見第 3 節情境 A）。

---

## 3. 新增語系 SOP

新增語系分兩種情境，後端需配合的程度不同。

### 情境 A：新增基礎語系（全新 `lang`，例如印尼文 `id`）

定義：全新的 `languageCode`，是目前清單沒有的語言。需新增整套字串資源，工作量重。

**App 端工作（摘要）：**
1. 在語系工具新增語言/國家常數（`lang=id`、`locale=id`）。
2. 在 `LanguageType` 新增 entry，含顯示名稱與 `webLangKey`。
3. 加入設定頁可選清單、系統語系冷啟反推 mapping。
4. 字串資源由 PM 透過 Lokalise 產出整套翻譯。

**後端 / Web / 平台需配合確認：**
- ✅ **B2C API 支援 `lang=id`**：所有帶 `lang` header / query 的 API 都需能辨識新語言碼，並回傳對應語系的文案內容（商品、Home、Order、Transportation 等）。
- ✅ **B2C API 支援 `locale=id`**：地區相關邏輯（幣別、可售商品等）需接受新國家碼。
- ✅ **`webLangKey=id` 對應的 Web 頁面存在**：App 內 WebView / 前端頁面以此參數開啟，需確認該語系頁面已上線。
- ✅ **遠端文案 / 翻譯服務**：商品評論翻譯、客服即時翻譯等遠端內容是否支援新語系。
- ✅ **第三方追蹤（Insider 等）**：確認平台已建立對應 locale（`id_ID`）。

### 情境 B：新增 LanguageType（既有語言的新地區變體，例如 `EN_CANADA`）

定義：沿用既有語言碼（如 `en`）、只是新的國家/地區。字串共用既有資源，工作量輕。

**App 端工作（摘要）：**
1. 視需要新增國家碼常數（如 `locale=ca`）。
2. 在 `LanguageType` 新增 entry，`lang` 沿用既有語言碼（如 `en`），設定 `webLangKey`（如 `en-ca`）。
3. 加入設定頁清單、冷啟反推 mapping。
4. **字串資源不需新增**（共用既有語言）。

**後端 / Web / 平台需配合確認：**
- ✅ **B2C API 支援新的 `locale`**（如 `locale=ca`）：`lang` 不變，但地區邏輯需接受新國家碼。
- ✅ **`webLangKey`（如 `en-ca`）對應的 Web 頁面存在**。
- ✅ **第三方追蹤**：確認對應 locale 已建立。

> 情境 B 因 `lang` 不變，後端文案層通常無需調整，重點在 `locale`（地區）與 Web 頁面參數。

---

## 4. 注意事項

### 4.1 資源資料夾的「舊版 ISO 碼」陷阱（已實機驗證，影響字串顯示）

Android runtime 會把部分語言正規化成**舊版 ISO 639 碼**：印尼文 `id`→`in`、希伯來文 `he`→`iw`、意第緒文 `yi`→`ji`。

- App 端的字串資源資料夾必須用**舊碼**（印尼文用 `values-in-rID`），否則切過去會 fallback 回英文。
- 但 **API header、儲存、`webLangKey` 仍使用新碼 `id`**——後端只會收到 `id`，不需處理 `in`。
- 對後端的意義：**後端端一律以新碼（`id`）為準**，舊碼僅是 App 內部資源資料夾的限制。

### 4.2 lang 與 locale 必須分開處理

如第 1 節所述，`lang` 決定文案語言、`locale` 決定地區。後端不可假設兩者一致（例如 `lang=en` + `locale=tw`、`lang=ja` + `locale=us` 等組合皆合法）。

### 4.3 非 Latin script 字型（未來新增前提醒）

若未來新增非拉丁字母語言（俄文、印地文、孟加拉文等），App 端需額外處理字型「豆腐字」問題；此為 App 端議題，但若後端文案中包含特殊符號，需確認編碼正確（UTF-8）。

### 4.4 動態讀取，無啟動時固定值

App 每次 API 請求即時帶入當前語系的 `lang` / `locale`。使用者在 App 內切換語系後，後續請求會立即帶新值，不需重啟。

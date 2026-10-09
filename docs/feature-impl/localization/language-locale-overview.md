# KKday Android Member App 語系邏輯完整盤點

> 盤點日期：2026-06-08
> 範圍：語系決定與儲存、API 語系傳遞、字串/資源對應、數值與日期的顯示排版

---

## 0. 重要釐清：8 語系 vs 17 LanguageType

「8 語系」是指 **8 種基礎語言代碼**，但 app 實際在 `LanguageType` enum 提供 **17 種「語言 + 國家/地區」組合**（主要是英文的多地區變體）。

**8 種基礎語言**（對應 8 個 `values-*` 資源目錄）：
`en`、`ja`、`ko`、`th`、`vi`、`zh-cn`、`zh-hk`、`zh-tw`

關鍵機制：**`languageCode` 決定字串資源**，而 `countryCode` 只影響 API `locale` header 與貨幣/地區邏輯。這就是 17 種 LanguageType 收斂成 8 套字串的原因——9 個英文變體共用 `languageCode="en"`、2 個簡中變體共用 `"zh-cn"`。

### 語系 ↔ LanguageType ↔ 資源 完整對照

來源：`libs/model/.../util/LanguageType.kt:5-81`、`LocaleUtil.kt:59-163`。

| LanguageType | 顯示名稱 | `languageCode` | `countryCode` | 實際命中 strings.xml | 解析 Locale `getLocaleByLanguage()` | API `lang` / `locale` | `webLangKey` | Insider `toInsiderLocale()` |
|---|---|---|---|---|---|---|---|---|
| EN_AUSTRALIA | English (Australia) | `en` | AU | `values/`(預設) | `en_AU` | `en` / `au` | en-au | en_AU |
| EN_INDONESIA | English (Indonesia) | `en` | ID | `values/` | `en_ID` | `en` / `id` | en-id | en_ID |
| EN_INTERNATIONAL | English (International) | `en` | kk | `values/` | `en_kk` | `en` / `kk` | en | en_US* |
| EN_MALAYSIA | English (Malaysia) | `en` | MY | `values/` | `en_MY` | `en` / `my` | en-my | en_MY |
| EN_PHILIPPINES | English (Philippines) | `en` | PH | `values/` | `en_PH` | `en` / `ph` | en-ph | en_PH |
| EN_NEW_ZEALAND | English (New Zealand) | `en` | NZ | `values/` | `en_NZ` | `en` / `nz` | en-nz | en_NZ |
| EN_SINGAPORE | English (Singapore) | `en` | SG | `values/` | `en_SG` | `en` / `sg` | en-sg | en_SG |
| EN_AMERICA | English (United States) | `en` | US | `values/` | `en_US` | `en` / `us` | en-us | en_US |
| EN_HONG_KONG | English (Hong Kong) | `en` | HK | `values/` | `en_HK` | `en` / `hk` | en-hk | en_HK |
| JA_JAPAN | 日本語 | `ja` | JP | `values-ja-rJP` | `ja_JP` | `ja` / `jp` | ja | ja_JP |
| KO_KOREAN | 한국어 | `ko` | KR | `values-ko-rKR` | `ko_KR` | `ko` / `kr` | ko | ko_KR |
| TH_THAILAND | ไทย | `th` | TH | `values-th-rTH` | `th_TH` | `th` / `th` | th | th_TH |
| VI_VIETNAM | Tiếng Việt | `vi` | VN | `values-vi-rVN` | `vi_VN` | `vi` / `vn` | vi | vi_VN |
| ZH_CN_CHINA | 简体中文 | `zh-cn` | CN | `values-zh-rCN` | `zh_CN` | `zh-cn` / `cn` | zh-cn | zh_CN |
| ZH_CN_MALAYSIA | 简体中文(马来西亚) | `zh-cn` | MY | `values-zh-rCN` | `zh_MY` | `zh-cn` / `my` | zh-my | zh_MY |
| ZH_HK_HONG_KONG | 繁體中文(香港) | `zh-hk` | HK | `values-zh-rHK` | `zh_HK` | `zh-hk` / `hk` | zh-hk | zh_HK |
| ZH_TW_TAIWAN | 繁體中文(台灣) | `zh-tw` | TW | `values-zh-rTW` | `zh_TW` | `zh-tw` / `tw` | zh-tw | zh_TW |

\* `EN_INTERNATIONAL` 的 `countryCode="kk"`（KKday 後端內部 placeholder，非 ISO 3166-1），Insider 轉換時 fallback 成 `US` → `en_US`（`LanguageType.kt:76-80`）。

### 多對一收斂關係（17 → 8 套字串）

```
languageCode "en"   →  values/(預設英文)   ← 9 種：EN_AU/ID/INTL/MY/PH/NZ/SG/US/HK
languageCode "zh-cn"→  values-zh-rCN        ← 2 種：ZH_CN_CHINA, ZH_CN_MALAYSIA
languageCode "zh-hk"→  values-zh-rHK        ← 1 種：ZH_HK_HONG_KONG
languageCode "zh-tw"→  values-zh-rTW        ← 1 種：ZH_TW_TAIWAN
languageCode "ja"   →  values-ja-rJP        ← 1 種：JA_JAPAN
languageCode "ko"   →  values-ko-rKR        ← 1 種：KO_KOREAN
languageCode "th"   →  values-th-rTH        ← 1 種：TH_THAILAND
languageCode "vi"   →  values-vi-rVN        ← 1 種：VI_VIETNAM
```

三層代碼貫穿關係（以 ZH_TW_TAIWAN 為例）：

```
LanguageType.ZH_TW_TAIWAN
  ├─ languageCode "zh-tw"  → 字串資源 values-zh-rTW、API header lang=zh-tw
  ├─ countryCode  "TW"     → API header locale=tw、貨幣/地區判斷
  ├─ webLangKey   "zh-tw"  → 開啟 WebView/前端頁面的語系參數
  └─ toInsiderLocale "zh_TW" → 第三方 Insider 追蹤
```

### 反向解析（系統語系 → LanguageType）

App 冷啟動無使用者設定時，`getLanguageTypeByLocale()`（`LocaleUtil.kt:83-96`）依系統 `Locale` 反推：
- `en` → 再依 country 細分 9 種英文變體（`getEnglishLanguageTypeByCountryCode`，無相符 country → `EN_INTERNATIONAL`）
- `zh` → 依 country：TW→繁中台灣、HK→繁中香港、MY→簡中馬來、CN/其他→簡中中國
- `ja/ko/th/vi` → 各自唯一對應
- 其他語言 → fallback `EN_INTERNATIONAL`

---

## 1. 語系決定與儲存

### 資料模型
- **`LanguageType` enum**（`libs/model/.../util/LanguageType.kt`）：每個 type 帶 `languageCode`（如 `zh-tw`）、`countryCode`（如 `TW`）、顯示名稱、`webLangKey`。
- **`LocaleUtil`**（`libs/model/.../util/LocaleUtil.kt`）：`SUPPORTED_LANGUAGES_DATA`（語系清單）、系統 Locale → LanguageType 對應、language ↔ Locale 互轉。

### 決定優先順序
1. 使用者主動選擇（已存 SharedPreferences）
2. SharedPreferences 既有值
3. 系統預設 Locale（`LocaleUtil.getDefaultLanguage()` / `getDefaultLanguageType()`，依系統 language+country 對應最近的 LanguageType）

### 儲存位置（SharedPreferences，非 DataStore/Room）
檔案：`libs/base/.../storage/preference/SharedPreferencesHelper.kt`

| Key | 型態 | 說明 |
|---|---|---|
| `KEY_LANGUAGE` | String | 語言代碼，如 `zh-tw` |
| `KEY_LANGUAGE_TYPE` | String | enum 名，如 `ZH_TW_TAIWAN` |
| `KEY_COUNTRY_CODE` | String | 國家碼小寫，如 `tw` |
| `KEY_HAS_SETUP_LANGUAGE` | Boolean | 使用者是否主動選過 |

讀寫：`getLanguage()/updateLanguage()`、`getLanguageType()/updateLanguageType()`、`getHasSetupLanguage()/updateHasSetupLanguage()`。

### 初始化流程（App 啟動）
1. `KKdayApp.onCreate()` → `LocaleHelper.sharedInstance().initialize(store)`（`app/.../KKdayApp.kt`）
2. `RxDBHelper.syncAppState()` 把 SharedPreferences 語系載入 Redux `AppState`，並建立雙向同步（`app/.../storage/RxDBHelper.kt`）
3. 每個 Activity 的 `attachBaseContext()`（`libs/base/.../view/base/BaseActivity.kt:98-106`）呼叫 `localeHelper.setLocale(context)`，再包一層 `LokaliseContextWrapper.wrap()`
4. `LocaleHelper.setLocale()`（`app/.../helper/LocaleHelper.kt`）→ `Locale.setDefault()` + `Configuration.setLocale()` + `createConfigurationContext()`，並觸發 `Lokalise.setLocale()/updateTranslations()`
5. 監聽系統 `ACTION_LOCALE_CHANGED` 廣播（`KKdayApp.kt:695-722`），系統語言變更時 dispatch `localeChanged`

> 採用 AppCompat per-app language 的「自製版」：透過 `attachBaseContext` + ContextWrapper 自行套用，**未使用** `AppCompatDelegate.setApplicationLocales`。

### 切換流程（使用者主動）
進入點：會員設定頁 `SettingActivity`（`app/.../view/user/setting/SettingActivity.kt`）→ `SimpleIdPickerDialog`（列出 17 個 LanguageType）

`SettingPresenter.setupLanguage()` → dispatch `userActions.setupLanguage` → **`UserReducer.setupLanguage()`**（`app/.../reducer/user/UserReducer.kt:442-527`）：
1. 立即 `LocaleHelper.setLocale()` 產生新 Context
2. 通知第三方（Freshchat、KKTrackTool、KTM、Insider）
3. 更新 AppState（`setLanguage/setCountryCode/setLanguageType/setHasSetupLanguage/setShouldRefreshUserPage`）
4. 清空網路快取 `kkNetworkingCache.clearAll()`
5. 重新載入資料

生效方式：`SettingPresenter` 監聽 AppState 變化（延遲 500ms）→ `SettingActivity.updateView()` → **`Activity.recreate()`** 觸發 `attachBaseContext` 重套語系。RxDBHelper 同步把新值寫回 SharedPreferences。

---

## 2. API 語系傳遞

### 傳遞方式：HTTP Header（主）+ Query Parameter（特定 API）
- **Header（統一機制）**：`B2CInterceptor`（`libs/networking/api/.../B2CInterceptor.kt`）對每個請求注入：
  - `lang` = `getCurrentLanguage()`（如 `zh-tw`）
  - `locale` = `getCurrentCountryCode()`（國家碼小寫，如 `tw`）
  - 定義於 `NetworkConstants.kt`（`B2CApiHeaderConst.getB2CApiHeaders()`，第 148-149、184-186 行）
- **Query Parameter（顯式宣告）**：Order / Home / Transportation 的 ApiService 同時用 `@Query("lang")` + `@Query("locale")`

### 代碼映射
| app 內部 | API header |
|---|---|
| `ZH_TW_TAIWAN`（languageCode=`zh-tw`, countryCode=`TW`） | `lang=zh-tw`, `locale=tw` |
| `EN_AMERICA`（`en`, `US`） | `lang=en`, `locale=us` |

特殊：`LanguageType.toInsiderLocale()` 給第三方 Insider 用 `zh_TW`/`en_US` 格式。

### 各 API 差異
| API | Header | Query | 備註 |
|---|---|---|---|
| Product/Home/Order/Transportation | ✓ | ✓ | Order/Transportation 兩者並用 |
| Payment / KTM | ✓ | ✗ | 僅靠 header |
| Insider（追蹤） | — | — | 專用 `toInsiderLocale()` |

### 更新時機
動態讀取——每次請求由 `B2CInterceptor` 即時讀 `B2CEnvironment.locale.getCurrentLanguage/CountryCode()`（優先 Redux Store，降級 SharedPreferences）。無啟動時固定值。

---

## 3. 字串資源與多語系

### 資源目錄（`libs/app_resource/src/main/res/`，共 8 套）
| 目錄 | 語系 | 字串數 |
|---|---|---|
| `values/`（預設 fallback） | English | 5037 |
| `values-ja-rJP` | 日本語 | 5014 |
| `values-ko-rKR` | 한국어 | 5026 |
| `values-th-rTH` | ไทย | 5018 |
| `values-vi-rVN` | Tiếng Việt | 5018 |
| `values-zh-rCN` | 简体中文 | 5023 |
| `values-zh-rHK` | 繁中(HK) | 5024 |
| `values-zh-rTW` | 繁中(TW) | 5033 |

- fallback = 英文 `values/`；各語系覆蓋率 99.5%+（缺漏 4~23 條，多為新增字串）。
- 取用方式：Compose `stringResource()`、View `getString()`。
- ⚠️ CLAUDE.md 規定 `strings.xml` 禁止修改（由 PM 維護）。

### 三層翻譯架構
1. **靜態層**：Android `values-*/strings.xml`
2. **動態層（OTA）**：Lokalise SDK 2.3.3（`KKdayApp.setupLokalise()` + `LokaliseContextWrapper`），可不發版更新文案
3. **API 遠端文案**：商品評論翻譯（`ProductCommentTranslation` / `IProductApiService.getProductCommentTranslation`）、客服訊息即時翻譯（`TranslationManager` / `ChatTranslationManager`，走 Google Translate）

---

## 4. 依 Locale/幣別呈現數值與日期（排版顯示，不做匯率換算）

> 此節談的是「拿到已確定的價格數字、日期後，依當前 locale 或幣別規則排版成顯示字串」——只改呈現、不改數值。價格的幣別在 API 回傳或使用者選定時就已固定，這裡**不包含匯率換算或幣別正規化**。

### 關鍵概念：幣別 ≠ 語系
| 維度 | 來源 | 儲存 |
|---|---|---|
| 語系 Locale | 系統或使用者選 | `getLanguage()` → LanguageType |
| 地區 Region | `LanguageType.countryCode` | 與語系綁定，無獨立設定 |
| 幣別 Currency | API 或使用者選 | `getCurrency()` 獨立儲存 |

→ 使用者可「日語介面 + USD 幣別」任意組合。

### 貨幣金額的顯示排版（符號、千分位、小數位、幣別代碼位置；三層）
1. **`CurrencyUtil.CurrencyType` enum**：每幣別帶 `symbol`、`supportedDecimalPoint`（JPY/KRW/VND = 無小數）、`defaultLocale`、縮放因子
2. **`CurrencyDisplayManager.formatPrice()`**（735 行，核心引擎）：比對「當前系統 Locale 對應的 Java Currency」是否等於要顯示的幣別 → 相同用 `preferredFormat`（SHORT/EXPLICIT），不同強制 `GLOBAL`；三種格式按 locale 匹配配置
3. **`DoubleExtension.formatPrice()`**：簡單版，硬編碼 `,` 千分位 + `.` 小數點（忽略 Locale），僅 VND 特例本地化
4. 對外：`PriceFormatStringUseCase`（從 `getCurrency()` 取使用者幣別）

### 日期/數字
- 日期（`DateExtension.kt`/`DateInfoUtil.kt`）：`SimpleDateFormat`，`toFormatString(locale,...)` 可傳 Locale，但多數用固定 pattern（無語言區分）
- 數字（`CurrencyUtil.numberOnlyFormatter()`）：`DecimalFormatSymbols.getInstance(defaultLocale)` 依幣別 defaultLocale 決定符號
- 「起」字樣（`PriceFormatConfig.kt`）：依語系顯示 From / ~ / 부터 / 起 / เริ่มต้น / Từ，且前綴/後綴位置依語言調整

---

## 5. 關鍵檔案速查

| 面向 | 檔案 |
|---|---|
| 語系 enum | `libs/model/.../util/LanguageType.kt` |
| 語系工具 | `libs/model/.../util/LocaleUtil.kt` |
| 儲存 | `libs/base/.../preference/SharedPreferencesHelper.kt` |
| 套用語系 | `app/.../helper/LocaleHelper.kt`、`libs/base/.../base/BaseActivity.kt` |
| 啟動初始化 | `app/.../KKdayApp.kt`、`app/.../storage/RxDBHelper.kt` |
| 切換 reducer | `app/.../reducer/user/UserReducer.kt`、`view/user/setting/SettingActivity.kt` |
| API header 注入 | `libs/networking/api/.../B2CInterceptor.kt`、`NetworkConstants.kt` |
| 字串資源 | `libs/app_resource/src/main/res/values-*/strings.xml` |
| 貨幣格式 | `libs/base/.../util/price/CurrencyDisplayManager.kt`、`util/CurrencyUtil.kt` |

---

## 6. 新增語系 SOP

### 共通前提
- ⚠️ `strings.xml` 由 PM/Lokalise 維護、禁止自行改（CLAUDE.md）→ 字串一律走 PM/Lokalise 流程，工程端只動 Kotlin enum 與對應邏輯。
- 無 `resConfigs`/`resourceConfigurations` 白名單 → 新增 `values-*` 目錄會自動打包。
- 無 `localeConfig` XML → 語系套用走自製 `attachBaseContext` + `LocaleHelper`，不經 `AppCompatDelegate.setApplicationLocales`。

### 先判斷情境

| | 情境 A：新基礎語系 | 情境 B：新 LanguageType |
|---|---|---|
| 定義 | 全新 `languageCode`（目前沒有的語言） | 既有語言的新地區變體 |
| 例子 | 法文 `fr`、印尼文 `id` | `EN_CANADA` 等 |
| 需新增字串資源 | 要（新 `values-XX/`） | 不要（共用既有 `values`） |
| 工作量 | 重 | 輕 |

### ⚠️ 共通陷阱：新增 `LanguageType` enum 值會打到窮舉 `when`

情境 A、B 都會在 `LanguageType` 新增 enum 值。專案內有多處 `when (languageType)` 作為運算式（return/賦值），**有 else 的安全、無 else 的會編譯失敗**，必須補上新分支。完成 enum 變更後**務必編譯整個 `:app` 模組**（`./gradlew :app:compileDevelopDebugKotlin`）抓出所有缺漏，不能只編 `:data:model`。

實例：新增 `ID_INDONESIA` 時，唯一無 else 的窮舉 `when` 在 `app/.../util/PaymentCardUtil.kt`（CardIO 語言對應），需補一條分支。其餘 `when` 多有 else（如 `SocialLoginViewInfoConverter`、各 `CurrencyUtil`）不受影響。快速定位：

```bash
rg -n "when\s*\(.*[lL]anguageType" --glob '*.kt'
```

### 情境 A：新增基礎語系（以法文 `fr`/`FR` 為例）

修改集中在 `libs/model/.../util/`：

1. `LocaleUtil.kt` 新增常數 `LANGUAGE_CODE_FRENCH = "fr"`、`COUNTRY_CODE_FRANCE = "FR"`。
2. `LanguageType.kt` 新增 entry：`FR_FRANCE(LANGUAGE_CODE_FRENCH, COUNTRY_CODE_FRANCE, "Français", "fr")`（`webLangKey` 與後端/web 約定一致）。
3. `LocaleUtil.SUPPORTED_LANGUAGES_DATA` 加入清單（決定設定頁是否顯示）。
4. `LocaleUtil.getLocaleByLanguage()` 新增 when 分支 `LANGUAGE_CODE_FRENCH -> Locale("fr","FR")`（否則落入 else 變英文）。
5. `LocaleUtil.getLanguageByLocale()` 新增 `LANGUAGE_CODE_FRENCH -> LANGUAGE_CODE_FRENCH`（決定冷啟存哪個 `KEY_LANGUAGE`）。
6. `LocaleUtil.getLanguageTypeByLocale()` 新增 `LANGUAGE_CODE_FRENCH -> LanguageType.FR_FRANCE`（系統語系冷啟反推）。
7. 字串資源（PM/Lokalise）：請 PM 在 Lokalise 建 `fr` 語系並產出整套翻譯，bundle 端會出現 `values-fr/strings.xml`。⚠️ **舊版 ISO 碼語言要用「舊碼」當資源資料夾**（見下方實證）。
8. Lokalise 平台：確認 `Lokalise.setLocale("fr","FR")` 抓得到 OTA 翻譯。
9. 後端 API：確認 `lang=fr`/`locale=fr` header 後端支援；`webLangKey` 對應 web 頁面存在。
10. 顯示排版（按需）：若新語系對金額/數字/日期有特殊呈現慣例（小數點符號、貨幣符號位置、「起」字樣等），檢查 `CurrencyUtil.CurrencyType`、`PriceFormatConfig.kt`；一般語系沿用預設。此步只關呈現，不涉匯率換算。
11. 測試：設定頁切換生效（`recreate`）、API header 帶值、字串顯示、冷啟跟隨系統、缺字 fallback 到 `values/`。

> ⚠️ **資源資料夾的「舊版 ISO 碼」陷阱（已實機驗證）**
> Android runtime 會把部分語言正規化成**舊版 ISO 639 碼**：印尼文 `id`→`in`、希伯來文 `he`→`iw`、意第緒文 `yi`→`ji`。資源資料夾必須用**舊碼**，否則切過去會 fallback 回英文 `values/`。
> 實證（印尼文）：`config.setLocale(Locale("id","ID"))` 後，runtime 實際請求 `in` → `values-id-rID` **不命中**、整片英文；改用 **`values-in-rID`** 後字串才正確顯示。程式碼端 enum/常數仍用新碼 `id`（API header、儲存都吃 `id`），**只有 `values-XX` 資料夾要用舊碼**。
> Kotlin/JDK 17 桌機端 `Locale("id").language` 會回 `id`（新碼），但 Android ART 不同——務必以實機行為為準。

> ⚠️ 若新增的是**非 Latin script**（Devanagari/Bengali/Tamil/Sinhala/Cyrillic/Greek 等），除上述步驟外還需處理字型問題，詳見 [第 7 節：非 Latin script 字型注意事項](#7-非-latin-script-字型注意事項未來新增前必讀)。

### 情境 B：新增 LanguageType（以 `EN_CANADA` 為例）

字串共用既有 `en`（`values/`），工作量輕：

1. `LocaleUtil.kt`：國家碼未定義才新增 `COUNTRY_CODE_CANADA = "CA"`。
2. `LanguageType.kt`：新增 entry，`languageCode` 用既有的 `en`：`EN_CANADA(LANGUAGE_CODE_ENGLISH, COUNTRY_CODE_CANADA, "English (Canada)", "en-ca")`。
3. `LocaleUtil.SUPPORTED_LANGUAGES_DATA` 加入清單。
4. 反推 mapping 新增 when 分支（冷啟反推用）：英文系 → `getEnglishLanguageTypeByCountryCode()`；中文系 → `getChineseLanguageTypeByCountryCode()`（另需確認 `getChineseLanguageByCountryCode()`）。例：`COUNTRY_CODE_CANADA -> LanguageType.EN_CANADA`。
5. 字串資源：**不需新增**。
6. 後端 API：確認 `webLangKey`（`en-ca`）與 `locale=ca` header 後端/web 支援。
7. 測試：切換 + API header（`lang=en`、`locale=ca`）+ 冷啟反推命中正確 LanguageType。

> `getLocaleByLanguage()` 情境 B 不需改——英文系走 `getEnglishLocale()`、中文系走 `getChineseLocale()`，兩者皆以 `countryCode` 動態組 `Locale`，新地區自動生效。

---

## 7. 非 Latin script 字型注意事項（未來新增前必讀）

新增非英文字母的語言（俄文、印地文、孟加拉文…）時，除了第 6 節的步驟，還要多顧一件事：**字畫不畫得出來**。畫不出來會變成「豆腐字」□□□，看起來很像翻譯沒生效，但其實是字型問題。

### 一句話判準

> 字會變豆腐，只有在「**app 自帶字型沒這個字、而且手機系統字型也沒有**」時才發生。任一邊有，就正常顯示。

app 自帶字型是 `noto_sans_medium.ttf`，實測有這些字：**英文、希臘文、俄文（Cyrillic）、印地文（Devanagari）**；沒有 **孟加拉文、坦米爾文、僧伽羅文、泰文、中日韓**。

所以新增語言分兩種：

| 語言 | 安全嗎 | 說明 |
|------|:--:|------|
| 俄文、希臘文、印地文 | ✅ 安全 | 自帶字型就有，直接加語系即可（印地文另見下方第 3 點） |
| 孟加拉文、坦米爾文、僧伽羅文 | ⚠️ 要小心 | 自帶字型沒有，只能靠手機系統字型；新手機多半 OK，老舊/客製手機可能變豆腐 → **最保險是自己打包對應的 Noto 字型** |

### 要檢查的 4 件事
1. **手機畫得出來嗎**：孟加拉/坦米爾/僧伽羅這類要在**多台實機**（不要只用模擬器）看會不會豆腐；不放心就自己打包字型。
2. **有些畫面寫死了字型**：少數 View 強制用 `noto_sans_medium`（如 `item_product_*.xml`、`HtmlText.kt`），這些地方就算手機有字型也救不回來，遇到上述語言要改掉。
3. **字會不會排錯**：印地/孟加拉/坦米爾/僧伽羅有連字、母音符號，就算字畫得出來，也要看實機上有沒有疊錯、排錯。
4. **字會不會被切到**：行高是寫死的 token（`kkText*LineHeight`），這些語言的字比較高，注意上下有沒有被裁掉。

> RTL 語言（阿拉伯文、希伯來文）目前清單裡沒有；真要做是整個版面左右翻轉的大工程，另案處理。

> 建議：先拿英文字母的語言（如印尼文 `id`）確認語系切換機制本身沒問題，再單獨處理這些字型問題。

---

## 備註：`Lokalise_Key` 髒資料（已驗證，非功能性 bug）

各 `strings.xml` 內有 `Lokalise_Key` 字串，其中泰/越值有誤：
- `values-th-rTH` 的 `Lokalise_Key` = `"en"`（看似應為 `th`）
- `values-vi-rVN` 的 `Lokalise_Key` = `"Tiếng Anh"`（越南語的「英文」，譯者誤把值 `en` 當可翻譯字串）

**驗證結論：不影響功能。** 全專案無任何 `R.string.Lokalise_Key`、`getIdentifier("Lokalise_Key")` 引用——此字串沒有被程式碼讀取。Lokalise 實際語系由 `Lokalise.setLocale(locale.language, locale.country)`（`app/.../helper/LocaleHelper.kt:71`）決定，泰/越分別傳入 `th`/`vi`，OTA 翻譯抓取正確。`Lokalise_Key` 僅為無用遺留字串。

# 13 · 設計系統與字串資源

這份管 **所有寫死的視覺數值與文案**：StyleDictionary token（間距／圓角／顏色／字級）、字型樣式、既有 KK\* 元件的複用、字串資源取用。紅線 A2、B1～B5 全部落在這裡。

這份**不管** composable 的 API 形狀（09a）、狀態與副作用（09b）、UiState 內的文案設計（08）。

| 你要找的 | 去哪份 |
|---------|-------|
| `modifier` 參數、參數順序、`@Preview` | [09a-compose-api.md](09a-compose-api.md) |
| Compose 端用 `colorResource` / `dimensionResource` 取 token | [17-interop-views-compose.md](17-interop-views-compose.md) |
| 跨模組 `R` 要明確 import 哪個模組 | [02-modularization.md](02-modularization.md) |
| UiState 不得攜帶已解析字串、錯誤用 `@StringRes` | [08-ui-state.md](08-ui-state.md) |
| 新增 `res/layout/*.xml` 的禁令、Epoxy／`ComposeView` | [17-interop-views-compose.md](17-interop-views-compose.md) |
| Material 2／3 混用、Accompanist | [90-migration-ledger.md](90-migration-ledger.md) |

## 一、token 速查（先看這裡，再決定要不要問）

單一來源：`libs/designsystem/design/.../com/kkday/design/StyleDictionary.kt`（318 行、約 305 個常數，style-dictionary 產生）。分類數量：kkColor 189、kkText 54、kkElevation 15、kkFont 14、kkSpacing 11、kkOpacity 11、kkDimension 6、kkRadius 5。

**kkSpacing 全部 11 級**（沒有其他值）：`025`=2 · `050`=4 · `075`=6 · `100`=8 · `150`=12 · `200`=16 · `250`=20 · `300`=24 · `400`=32 · `500`=40 · `600`=48（dp）

**kkRadius 全部 5 級**：`Xs`=2 · `Sm`=4 · `Md`=8 · `Lg`=12 · `Xl`=16（dp）。圓形用 `CircleShape`。
**kkDimensionIcon 6 級**：`2xs`=14 · `Xs`=16 · `Sm`=20 · `Md`=24 · `Lg`=32 · `Xl`=48（dp）

**顏色命名**：`kkColor{Background|Border|Text}{語意}{色階}`。語意 = Primary / Critical / Warning / Info / Highlight / Surface / Loyalty{Silver,Gold,Platinum,Diamond} 或省略（中性灰）。色階 = `Lighter` → `Light` → `Medium` → `Dark` → `Darker`。另有品牌色 `kkColorFacebookDefault` 等與 `kkColorWhite` / `kkColorBlack10`。

**字型**：`com.kkday.design.font` 的 19 個 `TextStyle` —— `fontH4/H5/H6`、`fontSubtitleLg/Md/Sm`、`fontBodyLg/Md/Sm`、`fontCategory`、`fontBodyMark`、`fontPriceBold{Xxl,Xl,Lg,Md}`、`fontPriceMedium{Lg,Md}`、`fontPriceRegular{Md,Sm}`；變體用擴充函式 `.color()` `.bold()` `.medium()` `.weightMedium()` `.regular()` `.light()` `.strikeThrough()`。

**XML 端同源**：Compose 的 `kkSpacing100` 對應 `@dimen/kk_spacing_100`，`kkColorTextDarker` 對應 `@color/kk_color_text_darker`，`kkRadiusMd` 對應 `@dimen/kk_radius_md`。轉換規則＝去掉 `kk` 前綴後 camelCase 轉 snake_case（數字自成一段），再加 `kk_`。字型在 XML 用 `style="@style/Font.Body.Md"` 系列。

## 二、常用 KK\* 元件（自己刻之前先查這裡）

設計系統共 45 個公開 composable，位於 `libs/designsystem/design/.../com/kkday/design/`。使用數前 15：

| 元件 | 用途 | 使用數 |
|------|------|-------|
| `KKButton` | 主要按鈕，帶 `ButtonType` / `ButtonState` / `ButtonSizeType` 與前後綴 icon | 104 |
| `KKTextLink` | 文字連結（含底線與點擊區） | 26 |
| `KKDialog` | 標準對話框（標題／內文／單雙按鈕） | 24 |
| `KKTextField` | 單行輸入框，含 label／placeholder／錯誤訊息／前後綴 icon | 23 |
| `KKSelect` | 下拉選擇欄位（外觀同 TextField，點擊開選單） | 17 |
| `KKModalBottomSheetV3` | 標準底部彈窗（含 drag handle） | 10 |
| `KKLabel` | 表單欄位標題，支援必填星號 | 10 |
| `KKFormMessage` | 欄位下方的說明／錯誤訊息 | 7 |
| `KKBadgedBox` | 角標容器（未讀數、紅點） | 6 |
| `KKViewPager` / `KKSwitch` | 分頁滑動容器／開關 | 5 |
| `KKTag` / `KKBaseTag` | 標籤、分類 chip | 4 |
| `KKTabs` / `KKTab` | 頁籤列 | 4 |
| `KKStepper` | 數量加減器 | 4 |
| `KKTextArea` | 多行輸入框 | 3 |

另有 `KKCheckbox` / `KKTriStateCheckbox` / `KKNestedCheckboxes` / `KKRadioButtonGroup` / `KKAvatar` / `KKTextBadge` / `KKBottomSheetScaffold`。文案參數多接 `StringType.Res(R.string.x)` 或 `StringType.Text(s)`。

## 三、token 取用（紅線 B1 / B2 / B3）

### hardcoded-dimen · MUST_NOT · new-only+on-touch · lint:hardcoded-dimen

間距、尺寸、字級不得寫字面量 `.dp` / `.sp`，一律引用 `StyleDictionary`。`0.dp` 與 `Dp.Hairline` 不在此限。

✗ `Modifier.padding(horizontal = 16.dp)` ／ `fontSize = 14.sp` ／ `.size(24.dp)`
✓ `Modifier.padding(horizontal = kkSpacing200)` ／ `fontSize = kkTextBodyMdFontSize` ／ `.size(kkDimensionIconMd)`

例外：`libs/designsystem/`、`libs/app_resource/`、`@Preview` 函式、測試碼。
既有違規：3252 處 / 557 檔（反例 `CarouselModel.kt:113` `.heightIn(10.dp, 10.dp)`、`FilterCheckBoxTitleModel.kt:41` `.width(375.dp)`）→ [90-migration-ledger.md#m-12](90-migration-ledger.md)

### hardcoded-color · MUST_NOT · new-only+on-touch · lint:hardcoded-color

顏色不得寫 `Color(0x…)` 或 `Color.White` / `Color.Black` 等內建常數，一律用 `kkColor*`。

✗ `tint = Color(0xFF212121)` ／ `style = fontSubtitleLg.color(Color(0xff333333))`
✓ `tint = kkColorTextDarker` ／ `style = fontSubtitleLg.color(kkColorTextDarker)`

例外：`libs/designsystem/`、`@Preview` 的 `backgroundColor`、測試碼。
既有違規：`Color(0x…)` 57 檔、`Color.White` 等 224 檔（反例 `SevenDayStripView.kt:466`、`TourFsrKeyInfoEpoxyModel.kt:165`）→ [90-migration-ledger.md#m-15](90-migration-ledger.md)

### hardcoded-shape · MUST_NOT · new-only+on-touch · lint:hardcoded-shape

圓角不得寫數值，用 `kkRadius*`；全圓角用 `CircleShape`；直角用 `RectangleShape`。

✗ `RoundedCornerShape(8.dp)` ／ `RoundedCornerShape(999.dp)` ／ `RoundedCornerShape(50)`
✓ `RoundedCornerShape(kkRadiusMd)` ／ `CircleShape`

例外：`libs/designsystem/`、`@Preview`。
既有違規：105 檔（反例 `TransHomeCruisesLocationFragment.kt:141`、`TourViewPlanFab.kt:47`）→ [90-migration-ledger.md#m-15](90-migration-ledger.md)

### token-not-found-unasked · MUST · new-only+on-touch · manual

設計稿數值在 token 級距中沒有完全相同的值時，**先向使用者確認**，不得自行四捨五入到最近 token、也不得直接 hardcode。使用者同意暫用字面量時，該行必須加 `// TODO: replace with token - <為什麼沒有對應 token>` 並列入待處理 task。

✗ 設計稿 10dp → 自行改用 `kkSpacing100`（8dp）或直接寫 `10.dp`
✓ 先問；獲准後 `lineHeight = 12.sp, // TODO: replace with token - Figma 12sp，StyleDictionary 無對應 lineHeight token`

例外：無。這是紅線 B3。
正面樣板：`libs/feature/presale_chat/.../session_list/component/SessionCard.kt:101`

### material-theme-token · MUST_NOT · new-only+on-touch · lint:material-theme-token

不得用 `MaterialTheme.colorScheme` / `MaterialTheme.typography` / `MaterialTheme.shapes` 取值。本專案從未建立 `MaterialTheme {}` 包裝（全庫 `colorScheme =` 賦值 **0** 處），取到的是 Material3 預設紫色與預設字型，不是 KKday 視覺。

✗ `containerColor = MaterialTheme.colorScheme.primary`
✓ `containerColor = kkColorBackgroundPrimaryButton`

例外：`libs/designsystem/app`（設計系統範例 App）。
既有違規：`colorScheme` 1 檔、`typography` 6 檔。

### legacy-color-palette · SHOULD_NOT · new-only · manual

不得使用 `libs/app_resource` 的舊調色盤（`R.color.colorPrimary`、`R.color.gray_*` 等 160 個非 `kk_` 開頭的色）。新程式碼一律 `StyleDictionary.kkColor*`。

✗ `Color(ContextCompat.getColor(context, R.color.colorPrimary))`
✓ `kkColorBackgroundPrimaryMedium`

例外：既有 XML 樣式沿用；第三方 View SDK 要求 `@ColorRes Int`。
既有違規：689 處 / 256 檔。
> Compose 端改用 `colorResource(R.color.kk_…)` 一樣不行 → 見 [17-interop-views-compose.md](17-interop-views-compose.md)

### xml-hardcoded-dimen · MUST_NOT · on-touch · manual

改到既有 layout / style XML 時，你動到的屬性一律換成 token 資源。新增 XML layout 本身另有禁令（見 [17-interop-views-compose.md](17-interop-views-compose.md)）。

✗ `android:padding="16dp"` ／ `android:textColor="#212121"`
✓ `android:padding="@dimen/kk_spacing_200"` ／ `android:textColor="@color/kk_color_text_darker"`

例外：`0dp`、`match_parent` / `wrap_content`、第三方 library 的 layout。
既有違規：664 個 layout 檔含字面量 dp（已有 577 檔用 token）→ [90-migration-ledger.md#m-11](90-migration-ledger.md)

## 四、字型

### adhoc-textstyle · MUST_NOT · new-only+on-touch · lint:adhoc-textstyle

不得用 `TextStyle(...)` 從零組裝字型。一律從 `com.kkday.design.font` 的 19 個 `fontXxx` 之一出發，再用擴充函式調整。

✗ `TextStyle(fontSize = kkTextBodyMdFontSize, lineHeight = 20.sp, fontWeight = FontWeight.Bold)`
✓ `fontBodyMd.bold()` ／ `fontSubtitleMd.color(kkColorTextMedium)`

例外：`libs/designsystem/`；需要 `platformStyle` / `TextGeometricTransform` 等 `fontXxx` 未覆蓋的欄位時用 `fontXxx.copy(...)`，不得改 `fontSize` / `lineHeight` / `fontWeight`。
既有違規：80 檔。

### hardcoded-font-weight · MUST_NOT · new-only · manual

字重不得用 `FontWeight.Bold` / `SemiBold` / `W600` 等字面常數，一律走 `fontXxx` 的擴充函式（背後是 `kkFontWeight*`：Light 300 / Regular 400 / Medium 500 / MediumAndroid 600 / Bold 700）。

✗ `fontWeight = if (unread) FontWeight.SemiBold else FontWeight.Normal`
✓ `style = if (unread) fontBodyMd.medium() else fontBodyMd.regular()`

例外：`libs/designsystem/`。
既有違規：155 檔。

## 五、設計系統的邊界

### styledictionary-edit · MUST_NOT · new-only+on-touch · manual

`StyleDictionary.kt`、`design/src/main/res/values/design_tokens.xml`、`integers.xml` 是 style-dictionary 自動產生（檔頭寫明 `Do not edit directly`），不得手改、不得新增 token。需要新 token 時走設計系統的 style-dictionary 更新流程並先詢問。

✗ 在 `StyleDictionary.kt` 補一行 `val kkSpacing350 = 28.00.dp`
✓ 先詢問；由設計系統重新產出後同步 `.kt` 與 `.xml` 兩端

例外：無。手改會在下次產生時被覆蓋，且 Compose／XML 兩端會不同步。

### reinvented-ds-component · SHOULD_NOT · new-only · manual

第三節列出的元件已存在時，不得自刻同功能 composable，也不得把設計系統元件整檔複製到 feature 模組微調。既有元件缺參數（例如多數 KK\* 元件缺 `modifier`）時，改設計系統本身。

✗ 在 feature 模組寫 `PrimaryButton()` 包一層 `Button` ／ 複製 `KKButton.kt` 成 `MyKKButton.kt`
✓ 直接用 `KKButton(...)`；缺 `modifier` 就補到 `libs/designsystem/design` 的 `KKButton`

例外：設計稿明確是一次性、與設計系統無關的版面元素。
既有違規：`KKButton` / `KKTextField` / `KKSelect` / `KKLabel` / `KKFormMessage` / `KKRadioButtonGroup` / `KKRadioButtonIcon` 皆缺 `modifier` → [90-migration-ledger.md#m-12](90-migration-ledger.md)（批次遷移優先級 3）

## 六、深色模式與主題（最容易誤解的一節）

**先看清楚三件事**：token 是 `object` 裡的**編譯期常數**，不是 theme-aware；`libs/designsystem/design` 沒有 `values-night`；token 名稱中的 `Dark` / `Light` / `Darker` / `Lighter` 是**色階**（shade），與系統深色模式無關 —— `kkColorTextDarker` 是最深的文字色，不是「深色模式的文字色」。全庫 `isSystemInDarkTheme` 使用數 **0**。是否支援深色模式尚未定案（[91-decisions.md](91-decisions.md) P-03）。

### dark-theme-branching · MUST_NOT · new-only · manual

不得用 `isSystemInDarkTheme()` 分支選 token，不得為設計系統資源新增 `values-night`，不得把 `Dark` / `Light` 色階當成主題模式使用。

✗ `val bg = if (isSystemInDarkTheme()) kkColorBackgroundSurfaceDarker else kkColorBackgroundSurfaceLighter`
✓ `val bg = kkColorBackgroundSurfaceLighter`（依設計稿指定的色階，與主題模式無關）

例外：無。此為架構級限制，不是可以順手補的項目 → [90-migration-ledger.md#m-15](90-migration-ledger.md)

### custom-design-theme · MUST_NOT · new-only · manual

不得自建 `KKTheme` / `AppTheme` composable、不得用 `CompositionLocalProvider` 包一層自訂 token、不得定義 `LocalKKColors` 這類 CompositionLocal 來間接取 token。取值一律直接引用 `StyleDictionary.kkXxx`。

✗ `CompositionLocalProvider(LocalKKColors provides KKColors(...)) { … }`
✓ `import com.kkday.design.StyleDictionary.kkColorTextDarker` 後直接使用

例外：無。專案沒有 theme 層，各自造一個等於再分岔一套設計系統。

## 七、字串資源（紅線 A2 / B4）

### strings-xml-edit · MUST_NOT · new-only+on-touch · manual

`libs/app_resource/src/main/res/values*/strings.xml`（8010 個 key × 15 個語系）由 PM 維護，**任何情況都不得新增、修改、刪除**，包含各語系翻譯檔。需要新 key 時向 PM 申請。

✗ 自行在 `values/strings.xml` 加 `<string name="presale_chat_title">售前諮詢</string>`
✓ 向 PM 申請 key；未到位前先用 `hardcoded-chinese-string` 的 TODO 標記流程

例外：`strings_additional_keys.xml` 的**非翻譯字串**（格式模板、字元集，`translatable="false"`，現有 69 條）可自行新增；仍不得放使用者可見文案。這是紅線 A2。

### hardcoded-chinese-string · MUST_NOT · new-only+on-touch · lint:hardcoded-chinese-string

程式碼中的使用者可見文案（含 `contentDescription`）不得寫中文字面量。PM 尚未提供 key 時，該行必須加 `// TODO: replace with stringResource - <說明>` 並列入待處理 task，否則視為違規。

✗ `contentDescription = "返回"`
✓ `contentDescription = stringResource(R.string.back)` ／ `contentDescription = "返回", // TODO: replace with stringResource - 返回按鈕 a11y label`

例外：測試碼、`@Preview` 假資料、log／埋點的內部字串。
正面樣板：`libs/feature/presale_chat/.../session_list/PresaleSessionListContent.kt:339`（既有 TODO 標記 9 檔）

### string-concat-for-i18n · MUST_NOT · new-only · manual

使用者可見文案不得用 `+` 或字串模板拼接，一律用帶參數的 string resource；分隔符號用 `strings_additional_keys.xml` 既有的模板 key（`text_with_colon`、`text_with_slash`、`text_with_vertical_bar` 等）。

✗ `Text(stringResource(R.string.total) + "：" + amount)` ／ `Text("$city・$country")`
✓ `Text(stringResource(R.string.order_total_amount, amount))`（請 PM 提供帶 `%1$s` 的 key）
✓ 數量文案請 PM 提供 `<plurals>`，用 `pluralStringResource(R.plurals.x, count, count)`

例外：純數字／日期格式化（走 `NumberFormat` / `DateTimeFormatter`）。

### localcontext-getstring · MUST_NOT · new-only · manual

Composable 內取字串一律 `stringResource(...)`，不得 `LocalContext.current.getString(...)` 或 `LocalContext.current.resources.*`（不參與重組、locale 變更不會刷新）。ViewModel／UseCase／Repository 需要字串時注入 `IResourcesProxy`（`domain/contract/.../IResourcesProxy.kt`，已做 locale 包裝），不得自持 `Context`。

✗ `Color(LocalContext.current.resources.getColor(R.color.x))` ／ ViewModel 內 `context.getString(...)`
✓ `stringResource(R.string.x)` ／ ViewModel 建構子注入 `resourcesProxy: IResourcesProxy`

例外：Activity / Fragment 自身的 `getString()`（locale 已由 `attachBaseContext` 包裝）。
> ViewModel 禁持 Context 的規則本身見 [08-ui-state.md](08-ui-state.md)；UiState 不得攜帶已解析字串同上。

## 八、對照設計稿

### figma-token-deviation · MUST · new-only · manual

實作前逐項對照 Figma 的 padding / size / color / 字型 / layout flow，並在 PR 說明中列出用到的 token。設計稿數值與 token 級距不符時走 `token-not-found-unasked`，不得自行取近似值。

✗ 設計稿 `#1AB6C1` 背景 → 隨手用 `kkColorBackgroundPrimaryMedium`（`#26BEC9`，不同色）
✓ 對到 `kkColorBackgroundPrimaryButton`（`#1AB6C1`）；對不到就先問

例外：無。這是紅線 B5。

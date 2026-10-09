# 14 · 設計系統

**管**：設計 token 的分層與取用、Compose Theme 的建立與擴充、深色模式與動態色彩、自訂元件何時上收設計系統、字串資源規範、無障礙底線。
**不管**：composable 怎麼拆與 side effect（`10-compose-state`）、元件 API 設計與 modifier 慣例（`09-compose-api`）、重組效能（`11-compose-performance`）、模組該不該開（`02-modularization`）。

| 相關主題 | 去哪 |
|---|---|
| `modifier` 參數慣例、slot API、composable 命名 | `09-compose-api` |
| `@Preview` 的簽章規範、side effect API 選型 | `10-compose-state` |
| 穩定性、`@Immutable` 對重組的影響 | `11-compose-performance` |
| `:core:designsystem` 該怎麼被依賴 | `02-modularization` |
| 文案裡的動態資料從哪來（UiState 形狀） | `08-ui-state` |
| 埋點不得含使用者可見文案以外的 PII | `17-security` `18-analytics` |

## token 的三層

```
primitive（原始值）   Blue500 = #1B6EF3、space4 = 4.dp、fontSize14 = 14.sp
        ↓ 只被 semantic 引用
semantic（語意）      colorScheme.primary、spacing.medium、typography.bodyMedium
        ↓ 被 UI 與 component 引用
component（元件級）    ButtonDefaults.shape、CardDefaults.elevation
```

UI 程式碼只能碰 semantic 與 component 層。primitive 層是實作細節，換色票時只改 semantic 的對應關係，不必掃全專案。

---

### hardcoded-dimension · MUST_NOT · new-only+on-touch · regex

UI 程式碼中不得出現字面尺寸數值（`N.dp`、`N.sp`、XML 的 `Ndp`/`Nsp`）表示間距、尺寸或字級，一律取自 theme。

✗ `Modifier.padding(horizontal = 16.dp)`
✓ `Modifier.padding(horizontal = AppTheme.spacing.medium)`

例外：`0.dp`／`0.sp`；設計系統模組內 token 本身的定義；`@Preview` 與測試專用程式碼。 來源：https://developer.android.com/develop/ui/compose/designsystems/custom

### hardcoded-color · MUST_NOT · new-only+on-touch · regex

不得寫 `Color(0x…)`、`Color.Red` 這類具名內建色，或 XML 的 `#RRGGBB` 字面值；顏色一律取自 `MaterialTheme.colorScheme` 或自訂色彩 token。

✗ `Text(color = Color(0xFF1B6EF3))`
✓ `Text(color = MaterialTheme.colorScheme.primary)`

例外：`Color.Unspecified`／`Color.Transparent`；設計系統模組內 palette 的定義。 來源：https://developer.android.com/develop/ui/compose/designsystems/material3

### hardcoded-corner-radius · MUST_NOT · new-only+on-touch · regex

圓角不得就地寫字面值，一律用 `MaterialTheme.shapes` 或設計系統的 shape token。

✗ `Modifier.clip(RoundedCornerShape(12.dp))`
✓ `Modifier.clip(MaterialTheme.shapes.medium)`

例外：`CircleShape`；設計系統模組內 shape 的定義。 來源：https://developer.android.com/develop/ui/compose/designsystems/material3

### inline-textstyle · MUST_NOT · new-only+on-touch · regex

不得就地建構 `TextStyle(fontSize = …, lineHeight = …)` 或在 XML 直接寫 `android:textSize`；字型一律取自 typography token，只允許以 `copy()` 覆寫單一屬性（顏色、對齊）。

✗ `Text(style = TextStyle(fontSize = 14.sp, fontWeight = FontWeight.Bold))`
✓ `Text(style = MaterialTheme.typography.bodyMedium)`

例外：以 `copy(color = …)`／`copy(textAlign = …)` 微調既有 token。 來源：https://developer.android.com/develop/ui/compose/designsystems/custom

### primitive-token-in-ui · MUST_NOT · new-only · manual

feature 或畫面程式碼不得直接引用 primitive 層 token（色票常數、原始間距常數）；只能引用 semantic 或 component 層。

✗ `Surface(color = AppPalette.Blue500)`
✓ `Surface(color = MaterialTheme.colorScheme.primary)`

例外：設計系統模組內把 primitive 對應到 semantic 的那一層。 來源：業界共識（Material Design token 分層）

### missing-theme-wrapper · MUST · new-only · manual

所有 UI 進入點都必須被專案 theme 包住：`setContent { AppTheme { … } }`、每個 `@Preview`、每個 Compose 互通用的 `ComposeView`。

✗ `setContent { OrderScreen() }`
✓ `setContent { AppTheme { OrderScreen() } }`

例外：無。 來源：https://developer.android.com/develop/ui/compose/designsystems/custom

### global-constant-token-object · MUST_NOT · new-only · manual

自訂 token 不得以 top-level 常數 object 直接被 UI 讀取（編譯期常數無法隨 theme 切換）；必須以 `@Immutable` data class + `staticCompositionLocalOf` 提供，並用與 `MaterialTheme` 同形的 object accessor 暴露。

✗ `Spacing.medium`（`object Spacing { val medium = 8.dp }`）
✓ `AppTheme.spacing.medium`（`object AppTheme { val spacing: AppSpacing @Composable get() = LocalAppSpacing.current }`）

例外：真正與主題無關的常數（例如動畫 duration 毫秒數）。 來源：https://developer.android.com/develop/ui/compose/designsystems/custom

### dark-mode-branching-in-ui · MUST_NOT · new-only+on-touch · manual

元件內不得用 `isSystemInDarkTheme()` 分岔顏色或資源；深淺色差異只能表現在 theme 提供的兩套 colorScheme（XML 端為 `values-night`）。

✗ `val bg = if (isSystemInDarkTheme()) Color.Black else Color.White`
✓ `val bg = MaterialTheme.colorScheme.surface`

例外：theme 定義處本身（決定要 provide 哪一套 colorScheme）；需要換整張點陣圖而非顏色時。 來源：https://developer.android.com/develop/ui/views/theming/darktheme

### dynamic-color-unconditional · SHOULD · new-only · manual

啟用動態色彩（`dynamicLightColorScheme`／`dynamicDarkColorScheme`）時必須做 API 31 版本判斷並保留品牌 fallback scheme，且品牌識別色（logo、主 CTA）不得交給動態色彩決定。

✗ `MaterialTheme(colorScheme = dynamicLightColorScheme(context))`
✓ `val scheme = if (Build.VERSION.SDK_INT >= 31 && dynamicColor) dynamicLightColorScheme(context) else BrandLightScheme`

例外：專案明確決定不支援動態色彩時，整個功能不啟用即可。 來源：https://developer.android.com/develop/ui/compose/designsystems/material3

### hardcoded-user-facing-string · MUST_NOT · new-only+on-touch · regex

使用者可見文案不得以字面字串寫在程式碼中；Compose 用 `stringResource(R.string.…)`，非 UI 層透過注入的字串解析抽象取得。

✗ `Text("Order confirmed")`
✓ `Text(stringResource(R.string.order_confirmed))`

例外：僅供開發者閱讀的字串（log、例外訊息、測試資料、`contentDescription` 為 null 的裝飾圖）。若文案 key 尚未產出，必須在該行加 `// TODO: replace with stringResource - <說明>` 並列入待辦。 來源：https://developer.android.com/guide/topics/resources/string-resource

### string-concatenation-for-sentence · MUST_NOT · new-only+on-touch · manual

不得以 `+` 或字串樣板把多段資源拼成句子；語序在其他語言會不同，必須用帶位置參數的單一格式化字串。

✗ `stringResource(R.string.hello) + " " + name + stringResource(R.string.suffix)`
✓ `stringResource(R.string.greeting_with_name, name)`（`<string name="greeting_with_name">Hello, %1$s!</string>`）

例外：串接的是非語意片段（例如以分隔符號組出的標籤清單）。 來源：https://developer.android.com/guide/topics/resources/localization

### manual-plural-branching · MUST_NOT · new-only+on-touch · manual

數量相關文案不得自行寫單複數判斷，必須用 `pluralStringResource` 搭配 `<plurals>` 資源。

✗ `if (n == 1) "1 item" else "$n items"`
✓ `pluralStringResource(R.plurals.item_count, n, n)`

例外：無。 來源：https://developer.android.com/guide/topics/resources/string-resource

### resolved-string-in-uistate · SHOULD_NOT · new-only · manual

UiState 不應攜帶已本地化完成的完整句子；應放 `@StringRes` id、格式化參數或 domain 型別，由 UI 層解析。這讓語系切換與測試都不必經過 `Context`。

✗ `data class OrderUiState(val errorMessage: String = "訂單已取消")`
✓ `data class OrderUiState(@StringRes val errorMessageRes: Int? = null)`

例外：文案完全來自後端（例如客服訊息內容）。 來源：官方 sample nowinandroid

### touch-target-below-48dp · MUST · new-only+on-touch · manual

可點擊元素的觸控區域不得小於 48dp × 48dp；視覺尺寸較小時用 `Modifier.minimumInteractiveComponentSize()` 或加 padding 撐開觸控範圍，而非縮小觸控區。

✗ `Icon(…, modifier = Modifier.size(24.dp).clickable { … })`
✓ `IconButton(onClick = { … }) { Icon(…, modifier = Modifier.size(24.dp)) }`

例外：無。 來源：https://developer.android.com/develop/ui/compose/accessibility

### insufficient-color-contrast · MUST · new-only · manual

文字與背景的對比度：一般文字至少 4.5:1，大字（18sp 以上，或 14sp 以上粗體）與圖示至少 3:1。深淺色兩套都要達標。

✗ 淺灰文字（`#AAAAAA`）配白底
✓ 使用成對的 semantic token（`colorScheme.surface` + `colorScheme.onSurface`），兩者由設計保證達標

例外：純裝飾且不承載資訊的元素。 來源：https://developer.android.com/develop/ui/compose/accessibility

### fixed-height-text-container · SHOULD_NOT · new-only+on-touch · manual

含文字的容器不得寫死高度；字型縮放到 200% 時會被裁切。用 `heightIn(min = …)` 或讓內容決定高度。

✗ `Row(modifier = Modifier.height(48.dp)) { Text(…) }`
✓ `Row(modifier = Modifier.heightIn(min = 48.dp)) { Text(…) }`

例外：不含文字的純圖形容器。 來源：https://developer.android.com/develop/ui/compose/accessibility/scalable-content

> `Image` / `Icon` 的 `contentDescription` 規範見 [09-compose-api.md#missing-content-description](09-compose-api.md)。
> 本檔只規範無障礙的視覺面（對比度、觸控目標、字型縮放）。


### duplicated-component-outside-design-system · SHOULD · new-only · manual

自刻新元件前必須先查設計系統模組既有元件；同一視覺元件在兩個以上 feature 各自實作時，必須上收到 `:core:designsystem`。

✗ 在 `:feature:order` 與 `:feature:cart` 各寫一份 `PriceTag`
✓ `:core:designsystem` 提供 `PriceTag`，兩個 feature 依賴它

例外：只在單一畫面使用且無複用預期的組合，留在該 feature 即可。 來源：官方 sample nowinandroid

### design-system-depends-on-feature · MUST_NOT · new-only · manual

設計系統模組不得依賴 feature／domain／data 模組，元件不得接收 ViewModel、不得含業務邏輯或發起 I/O；資料一律由參數傳入、事件一律由 lambda 傳出。

✗ `fun OrderCard(viewModel: OrderViewModel)`
✓ `fun OrderCard(title: String, price: String, onClick: () -> Unit, modifier: Modifier = Modifier)`

例外：無。 來源：官方 sample nowinandroid

### manual-edit-generated-tokens · MUST_NOT · new-only+on-touch · manual

若專案的 token 由工具鏈產生（檔頭標示 auto-generated），該檔不得手動編輯；新增或修改 token 必須改來源定義並重新產生，且 Compose 端與 XML 端必須同一次產出。

✗ 直接在產生出來的 token 檔補一個新的間距值
✓ 改來源 token 定義 → 重跑產生指令 → 兩端同時更新

例外：無。 來源：業界共識（Style Dictionary 類 token pipeline）

### undefined-design-value-silently-implemented · MUST · new-only+on-touch · manual

設計稿數值找不到對應 token 時，必須停下來向設計或負責人確認；不得自行決定數值、就近取用相近 token，也不得加註解豁免了事。

✗ 設計標 20dp、token 只有 16dp 與 24dp，於是選 16dp 繼續寫
✓ 停下來確認：是設計稿沒對齊，還是需要新增 token

例外：無。 來源：業界共識

---

## 尚無定論（建議，非規則）

- **token 該擴充 `MaterialTheme` 還是完全自建 theme**：官方三種做法都成立。建議先走「`MaterialTheme` + `CompositionLocal` 擴充」，只有在品牌語彙與 Material 差異極大時才自建整套；自建就必須自行處理 Material 元件內部的 `LocalContentColor`／`LocalTextStyle`。
- **是否支援深色模式**：若專案決定 light-only，必須是明文的專案決策並在 theme 層集中處理，而不是散落在各元件用條件判斷。決策前不要在新程式碼裡假設任一種。
- **token 產生工具鏈**：官方無定論。建議「單一來源 → 產生多平台輸出」，且產出物進版控、不可手改（見 `manual-edit-generated-tokens`）。
- **視覺回歸測試**：建議對設計系統元件建立 screenshot 測試（Roborazzi 或 Compose Screenshot Testing），涵蓋深／淺色與 200% 字型縮放三種組合。測試分層見 `15-testing`。

# UI 模式指南

> **AI 使用說明**：排查 UI 顯示問題、新增畫面、或處理導航問題時參考本文件。

---

## 快速摘要

| 項目 | 現況 |
|------|------|
| 主要 UI | XML + ViewBinding（134 個 Fragment、90 個 Activity） |
| Compose | 14 個檔案，選擇性採用（Dialog、局部元件） |
| Navigation | KRouter（自訂路由）+ 手動 Fragment transaction，無 Jetpack Navigation |
| RecyclerView | 標準 Adapter + Paging3 PagingDataAdapter，少量 Epoxy |
| 設計系統 | StyleDictionary（token）+ kkcomponents（元件庫） |

---

## Jetpack Compose

### 採用範圍

目前有 **14 個** Compose 檔案，分散在各 Feature 模組，以 Dialog 和局部元件為主：

```
app/.../transportation/pages/dialog/AgePickerScreenCompose.kt
app/.../order/detail/order/jrrail/JrRailFAQCompose.kt
app/.../rental/dialog/DriverSalutationPickerCompose.kt
libs/transportation/.../home/product_block/TransProductCardCompose.kt
```

### 整合模式

Compose 嵌入在 Fragment/DialogFragment 內，透過 `ComposeView` 掛載：

```kotlin
class AgePickerCompose : DialogFragment() {
    override fun onCreateView(...): View {
        return ComposeView(requireContext()).apply {
            setContent {
                AgePickerDialog(
                    onDismissRequest = { dismiss() },
                    selectedAge = getSelectedAge(),
                    onAgeSelected = { age -> onAgeSelected(age) }
                )
            }
        }
    }
}

@Composable
fun AgePickerDialog(
    onDismissRequest: () -> Unit,
    selectedAge: Int,
    onAgeSelected: (Int) -> Unit,
) {
    var selectedAgeState by remember { mutableStateOf(selectedAge) }
    Dialog(onDismissRequest = onDismissRequest) { /* ... */ }
}
```

### Compose 中使用設計系統

```kotlin
import com.kkday.design.StyleDictionary
import com.kkday.design.font.fontBodyMd

// spacing token
.padding(
    start = StyleDictionary.kkSpacing200,
    end   = StyleDictionary.kkSpacing200,
    top   = StyleDictionary.kkSpacing250,
)

// color（透過資源）
color = colorResource(R.color.kk_color_text_primary_dark)
```

### 命名規則

Compose 檔案以 `[功能]Compose.kt` 或 `[功能]ScreenCompose.kt` 命名。

---

## Fragment 結構

### 數量與比例

- Fragment：134 個
- Activity：90 個
- 架構：**非單一 Activity**，多個 Activity 作為功能容器

### ViewBinding（全面採用）

所有現代 Fragment 使用 ViewBinding，**不用 DataBinding**：

```kotlin
class ZzimAirBookingFragmentV2 :
    BaseTransFragment<FragmentZzimairBookingListBinding, ZzimAirBookingViewModel, ZzimAirViewModel>() {

    override fun getViewBinding() =
        FragmentZzimairBookingListBinding.inflate(layoutInflater)
}
```

**Base 類別**：
- `app/.../view/base/BaseFragment.kt`（app 層，提供 networkHelper、permissionHelper）
- `libs/base/.../view/base/BaseFragment.kt`（library 層，Generic ViewBinding support）
- `BaseComposeFragment`（Compose 用 Fragment base）
- `BaseBottomSheetDialogFragment`（BottomSheet 用）

### ViewModel 取得方式

```kotlin
// Fragment 級別（最常用）
private val viewModel: OrderViewModel by viewModelsFactory { ... }

// Activity 共享（跨 Fragment 共用同一 ViewModel）
private val homeVM by activityViewModel<HomeModuleViewModel>()

// Koin inject（非 ViewModel 依賴）
private val homePresenter: HomePresenter by inject()
private val deepLinkHelper: IDeepLinkHelper by inject { parametersOf(config) }
```

### 巢狀 Fragment

```kotlin
// Fragment 內建立子 Fragment
childFragmentManager.beginTransaction()
    .add(R.id.container, HomeModuleFragment.newInstance())
    .commitAllowingStateLoss()
```

---

## Navigation（KRouter）

**無 Jetpack Navigation**，使用內部自訂路由系統 KRouter。

### 基本用法

```kotlin
// 導向頁面
RouterHelper.dispatch(KRouterConst.PAGE_KKDAY_WEB)
    .withParam(KRouterConst.KEY_URL, url)
    .navigator(context)

// 定義 Router processor
@Router(KRouterConst.ACTION_ORDER_REBOOKING)
class OrderReBookingProcessor {
    @RouterParam(KRouterConst.KEY_PRODUCT_ID)
    lateinit var productId: String

    fun process() {
        RouterHelper.inject(this, uri)
        // 執行導航邏輯
    }
}
```

### DeepLink

```kotlin
// MainActivity 接收
val isFromDeepLink = intent.getBooleanExtra(Constants.KEY_IS_FROM_DEEP_LINK, false)

// Fragment 注入 DeepLinkHelper
private val deepLinkHelper: IDeepLinkHelper by inject {
    parametersOf(DeepLinkHelperConfig.Home(this))
}
```

### 跨 Activity 導航

```kotlin
// 啟動 Feature Activity
TransHomeActivity.launch(context, transHomeArgument = args)
MainActivity.launchFragment(context, MainFragmentId.SEARCH_RESULT)
```

---

## RecyclerView / Adapter

### 標準 RecyclerView.Adapter

```kotlin
class SeatDescriptionAdapter : RecyclerView.Adapter<SeatDescriptionAdapter.ViewHolder>() {
    inner class ViewHolder(private val binding: ItemSeatDescriptionBinding) :
        RecyclerView.ViewHolder(binding.root) {
        fun bind(item: SeatDescription) { /* ... */ }
    }
}
```

### Paging3（無限捲動列表）

```kotlin
class ZzimAirSearchResultAdapter :
    PagingDataAdapter<ZzimAirSearchResultData, RecyclerView.ViewHolder>(DIFF_CALLBACK) {

    companion object {
        private val DIFF_CALLBACK = object : DiffUtil.ItemCallback<ZzimAirSearchResultData>() {
            override fun areItemsTheSame(old: ZzimAirSearchResultData, new: ZzimAirSearchResultData) =
                old.id == new.id
            override fun areContentsTheSame(old: ZzimAirSearchResultData, new: ZzimAirSearchResultData) =
                old == new
        }
    }
}
```

### Loading 狀態

- **Shimmer**：用 `ShimmerFrameLayout` 包住 Skeleton layout
- **PagingLoadStateAdapter**：Paging3 頭尾 loading indicator

---

## 設計系統使用

### StyleDictionary（設計 Token）

**位置**：`libs/designsystem/design/src/main/java/com/kkday/design/StyleDictionary.kt`

```kotlin
// Spacing（Dp 值）
StyleDictionary.kkSpacing050   // 4dp
StyleDictionary.kkSpacing100   // 8dp
StyleDictionary.kkSpacing150   // 12dp
StyleDictionary.kkSpacing200   // 16dp
StyleDictionary.kkSpacing250   // 20dp
StyleDictionary.kkSpacing300   // 24dp

// Typography（Compose 用）
import com.kkday.design.font.fontBodyMd
import com.kkday.design.font.fontSubtitleLg
```

### 顏色（XML 資源）

```xml
<!-- 在 XML layout 中 -->
android:textColor="@color/kk_color_text_dark"
android:background="@color/kk_color_white"
```

```kotlin
// 在 Compose 中
color = colorResource(R.color.kk_color_text_primary_dark)
```

### kkcomponents（元件庫）

**位置**：`libs/UI/kkcomponents/`

提供：Bottom sheet、Dialog（`KKBaseInfoDialog`）、Button、Picker、Wheel picker、Text 元件

```kotlin
// 使用範例（Fragment 內）
KKBaseInfoDialog.show(
    fragmentManager = childFragmentManager,
    title = getString(R.string.some_title),
    message = getString(R.string.some_message),
    positiveText = getString(R.string.confirm),
    onPositiveClick = { /* ... */ }
)
```

---

## 關鍵參考檔案

| 用途 | 路徑 |
|------|------|
| 主 Activity | `app/.../view/main/MainActivity.kt` |
| HomeFragment（複雜 Fragment 範本） | `app/.../view/home/HomeFragment.kt` |
| ViewBinding Fragment 範本 | `app/.../view/zzimair/booking/ZzimAirBookingFragmentV2.kt` |
| Compose Dialog 範本 | `app/.../transportation/pages/dialog/AgePickerScreenCompose.kt` |
| Compose + StyleDictionary | `app/.../order/detail/order/jrrail/JrRailFAQCompose.kt` |
| PagingDataAdapter 範本 | `app/.../zzimair/search/ZzimAirSearchResultAdapter.kt` |

---

*文件版本：Step 7 of AI Guide | 最後分析日期：2026-03-17*

## 相關筆記
- [01-architecture](01-architecture.md)
- [02-modules](02-modules.md)
- [05-networking](05-networking.md)
- [06-data-layer](06-data-layer.md)
- [07-concurrency](07-concurrency.md)
- [checkout](features/checkout.md)
- [order-detail-compose](features/order-detail-compose.md)
- [sku-activity-shell](features/sku-activity-shell.md)

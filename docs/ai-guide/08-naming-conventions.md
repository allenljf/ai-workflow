# 命名規範與程式碼慣例指南

> **AI 使用說明**：新增程式碼或提供修改建議時，對照本文件確認命名、放置位置、與程式碼結構是否符合專案慣例。

---

## 類別命名規則

### UseCase

**格式**：`[動詞][名詞]UseCase`

| 範例 | 路徑 |
|------|------|
| `GetSearchProductsUseCase` | `domain/usecase/GetSearchProductsUseCase.kt` |
| `GetProductDetailUseCase` | `domain/usecase/GetProductDetailUseCase.kt` |
| `AddWishProductUseCase` | `domain/usecase/AddWishProductUseCase.kt` |
| `DeleteCreditCardUseCase` | `domain/usecase/DeleteCreditCardUseCase.kt` |
| `SaveCreditCardUseCase` | `domain/usecase/SaveCreditCardUseCase.kt` |
| `CalculateBundlePriceUseCase` | `domain/usecase/CalculateBundlePriceUseCase.kt` |
| `GetHotelRefundPolicyUseCase` | `domain/usecase/GetHotelRefundPolicyUseCase.kt` |

**常用動詞**：Get、Add、Delete、Save、Calculate、Check、Track、Update、Order

---

### Repository

**格式**：`[功能]Repository`（介面與實作同名，放不同模組）

| 類型 | 範例 |
|------|------|
| 介面 | `ProductRepository`、`OrderRepository`、`WishProductRepository` |
| 實作 | `ProductRepository`（放 `:data:repository`）、`ChatRepositoryImpl` |
| 帶 binds | `@Single(binds = [CreditCardRepository::class]) class CreditCardRepositoryImpl` |

---

### ViewModel

**格式**：`[功能][用途]ViewModel`，加 `@KoinViewModel`

```
HomeModuleViewModel、OrderViewModel、BookingSuccessViewModel
CancelOrderViewModel、CartViewModel、CalendarViewModel
ProductPackageDialogViewModel、UserCommentViewModel
```

---

### API Service

**格式**：介面 `I[功能]ApiService`，實作 `[功能]ApiService`

| 介面 | 實作 |
|------|------|
| `IHomeApiService` | `HomeApiService` |
| `IOrderApiService` | `OrderApiService` |
| `IPaymentApiService` | `PaymentApiService` |
| `IDCSApiService` | `DCSApiService` |
| `IHotelProductApiService` | `HotelProductApiService` |

---

### Fragment / Activity

**格式**：`[用途]Fragment`、`[用途]DialogFragment`、`[用途]BottomSheetDialogFragment`

```
HomeModuleFragment、CommonProductDetailFragment
AnnouncementFragment、CalendarFragment
ProductPackageDialogFragment（BottomSheet）
CouponInvalidDialogFragment
```

---

### Adapter

**格式**：`[用途]Adapter` 或 `[用途]RecyclerAdapter`

```
ZzimAirSearchResultAdapter（PagingDataAdapter）
SeatDescriptionAdapter、FlightDetailAdapter
InformationDetailRecyclerAdapter
```

---

### Sealed Class（State / Intent / Event）

**格式**：`[功能]ViewState`、`[功能]ViewIntent`、`[功能]SingleEvent`

```kotlin
// 狀態（data class，可 copy）
data class HomeViewState(val isLoading: Boolean = false, ...)

// Intent（object 或 data class，描述使用者動作）
sealed class HomeViewIntent {
    object GetThemeCategories : HomeViewIntent()
    data class ClickBanner(val url: String) : HomeViewIntent()
}

// 一次性事件（不存入 State）
sealed class HomeSingleEvent {
    data class ClickEventBannerItem(val url: String, val position: Int) : HomeSingleEvent()
    object AcquireCouponSuccess : HomeSingleEvent()
}
```

**放置位置**：`presentation/intent/[功能]ViewState.kt`、`presentation/intent/[功能]ViewIntent.kt`

---

## 常數命名

**格式**：`UPPER_SNAKE_CASE`，集中放在 `object [功能]Constants`

```kotlin
// model/src/main/java/com/kkday/library/common/tracker/TrackerConstants.kt
object TrackerConstants {
    const val PAGE_BOOKING_SUCCESS = "ConfirmPage_Loaded"
    const val EVENT_CLICK_RECOMMEND_CITY = "RecommendCity_Clicked"
    const val KEY_PRODUCT_ID = "ProdID"
}
```

**常數檔案命名**：`[功能]Constants.kt`（複數）

常見常數檔案：
- `TrackerConstants.kt`（追蹤事件）
- `KoinConstant.kt`（DI named qualifiers）
- `NetworkConstants.kt`（Server error codes）
- `ZzimAirConstants.kt`、`CartConstants.kt`（功能專屬）
- `ProductConst.kt`（商品相關，單數特例）

---

## 檔案放置規則

### UseCase

```
domain/usecase/src/main/java/com/kkday/domain/[feature]/[Verb][Noun]UseCase.kt
libs/feature/[feature]/src/main/java/com/kkday/[feature]/domain/useCase/[Verb][Noun]UseCase.kt
```

### Repository

```
介面：domain/contract/ 或 libs/feature/[feature]/src/main/java/.../domain/repository/
實作：data/repository/src/main/java/com/kkday/data/repository/[feature]/
```

### ViewModel

```
libs/feature/[feature]/src/main/java/com/kkday/[feature]/presentation/viewModel/
app/src/main/java/com/kkday/member/view/[feature]/[FeatureViewModel.kt]
```

### Fragment

```
libs/feature/[feature]/src/main/java/com/kkday/[feature]/presentation/[purpose]/
app/src/main/java/com/kkday/member/view/[feature]/
```

### API Service

```
libs/networking/api/src/main/java/com/kkday/library/networking/service/[feature]/
```

### Data Model

```
data/model/src/main/java/com/kkday/model/
libs/model/src/main/java/com/kkday/library/networking/core/
```

---

## Package 結構

```
com.kkday.member/            ← 主 app
  view/[feature]/
    domain/usecase/
    data/repository/
    presentation/
      viewModel/
      view/               ← Fragment
      intent/             ← State, Intent, Event
  di/                     ← Koin modules

com.kkday.[feature]/        ← Feature library module
  domain/
    repository/            ← 介面
    useCase/
  data/
    model/
    repository/            ← 實作
    network/
  presentation/
    viewModel/
    view/
    intent/
```

---

## 程式碼慣例

### companion object

用於**常數**與 **Fragment factory**：

```kotlin
companion object {
    const val PAGE_BOOKING_SUCCESS = "ConfirmPage_Loaded"

    fun newInstance(args: Bundle) = MyFragment().apply {
        arguments = args
    }
}
```

**Reducer 內可測試純函式**：Reducer 的 action handler 常依賴 `AppState`/DI，難以直接單元測試。當其中一段邏輯是不依賴外部狀態的純函式（輸入輸出明確、無副作用）時，抽到該 Reducer 的 companion object，讓它可被獨立測試，呼叫端仍在同一 class 內以未限定名稱呼叫：

```kotlin
abstract class SpecificationReducer: Reducer<AppState>, KoinComponent {
    // ...
    companion object {
        fun resolvePointsBannerType(products: List<KKPointsProductInfo>): String {
            // 純函式：只依賴輸入參數，無副作用
        }
    }
}
```

先例：`SpecificationReducer.resolvePointsBannerType`（KKAPP-6058）、`OrderFormFillingReducer.sumTotalPrice`（KKAPP-6126）。對應測試放在 `<ReducerName>Test.kt`，直接呼叫 `ReducerName.functionName(...)`，不需建置完整 `AppState`。

### Extension function

獨立放在 `extension/[目標]Extension.kt`，不寫在 class 內：

```kotlin
// ViewExtension.kt
fun View.showOrHide(isValid: Boolean?) {
    isVisible = isValid == true
}
```

### data class vs class

| 使用 data class | 使用 class |
|----------------|-----------|
| Model、DTO、Entity、State | UseCase、Repository、ViewModel、Adapter |
| 需要 `copy()`、`equals()`、`hashCode()` | 業務邏輯類別 |

### UseCase 入口點

一律用 `operator fun invoke()`：

```kotlin
@Factory
class GetProductDetailUseCase(...) {
    operator fun invoke(productId: String): Flow<ApiResult<ProductDetail>> = flow { ... }
}
```

---

*文件版本：Step 7 of AI Guide | 最後分析日期：2026-03-17*

## 相關筆記
- [02-modules](02-modules.md)
- [03-ui-patterns](03-ui-patterns.md)
- [05-networking](05-networking.md)
- [06-data-layer](06-data-layer.md)
- [order-detail-compose](features/order-detail-compose.md)
- [sku-activity-shell](features/sku-activity-shell.md)

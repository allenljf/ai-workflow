# 交通商品頁 技術文件

> 自動產生 | 最後更新：2026-03-19

---

## 概述

- **所在 Module**：`:feature:product_page`（`libs/feature/product_page/`）
- **UI 入口**：`TransProductDetailFragment.kt`
- **功能描述**：交通垂直類型商品詳情頁，目前主要承接遊輪（Cruises）類型商品，顯示商品資訊、行程、艙型選擇、規格選擇，提供前往訂購流程的入口。

---

## 檔案清單

```
UI（使用者介面入口）
 ├─ TransProductDetailFragment.kt          → libs/feature/product_page/.../detail/transportation/
 └─ TransProductBookingFragment.kt         → libs/feature/product_page/.../detail/transportation/

ViewModel（UI 狀態管理）
 ├─ ProductDetailViewModel.kt              → libs/feature/product_page/.../detail/viewModel/
 └─ TransCruisesViewModel.kt              → libs/feature/product_page/.../presentation/cruises/

Domain（業務邏輯 UseCase）
 ├─ GetProductUseCase.kt（UseCase 聚合）   → libs/feature/product_page/.../domain/useCase/
 ├─ GetProductDetailUseCase.kt             → libs/feature/product_page/.../domain/useCase/
 ├─ GetProductPackagesUseCase.kt           → libs/feature/product_page/.../domain/useCase/
 ├─ GetProductPackageCalendarUseCase.kt    → libs/feature/product_page/.../domain/useCase/
 ├─ GetProductAnnouncementUseCase.kt       → libs/feature/product_page/.../domain/useCase/
 ├─ GetProductCouponsUseCase.kt            → libs/feature/product_page/.../domain/useCase/
 ├─ UserCommentUseCase.kt                  → libs/feature/product_page/.../domain/useCase/
 ├─ GetTravelerTypeUseCase.kt              → libs/feature/product_page/.../domain/useCase/
 └─ OrderUserKKPointsUseCase.kt            → libs/feature/product_page/.../domain/useCase/

Data（資料層）
 ├─ ProductRepository.kt（實作）           → data/repository/.../
 └─ TransProductRepository.kt             → libs/feature/product_page/.../data/repository/

Network（API 定義）
 ├─ IProductApiService.kt                 → libs/networking/api/.../service/product/
 └─ ITransportationApiService.kt          → libs/networking/api/.../service/transportation/
```

---

## 資料流

### 主流程 A：商品詳情載入（頁面初始化）

```
UI（TransProductDetailFragment）
 │  initAction() 觸發
 │  呼叫：productVM.getProductDetail(productId, isFromProductPageBack, isGetProductDetail)
 ↓
ViewModel（ProductDetailViewModel）
 │  更新狀態：_productDetailState = ProductDetailState(isLoading = true)
 │  呼叫：getProductUseCase.getProductDetailUseCase(productId, isGetProductDetail)
 ↓
UseCase（GetProductDetailUseCase）
 │  快取判斷：若 appSharedData.productDetailData 已存在且 isNeedGetProductDetail=false → 直接回傳快取
 │  否則呼叫：productRepository.getProductDetail(productId, currency, lang, countryCode)
 │  錯誤碼處理：PRODUCT_IS_NOT_SOLD / PRODUCT_IS_CLOSE_SOLD / HTTP_NOT_FOUND / SystemUpgrade
 ↓
Repository（ProductRepository）
 │  先呼叫 kkApi.b2cApi.product.trackProductView()（非阻斷，catch 例外）
 │  呼叫：kkApi.b2cApi.product.getProductDetail(productId, currency, lang, countryCode)
 ↓
API（IProductApiService）
 │  GET v2/cdn/product/{product_mid}
 │  Header: currency, lang, locale
 ↓
後端 API
```

### 主流程 B：遊輪資訊載入（與 A 同時觸發）

```
UI（TransProductDetailFragment）
 │  initAction() 同時呼叫：transCruisesViewModel.getInitApi(productId)
 ↓
ViewModel（TransCruisesViewModel）
 │  呼叫：getCruisesInfo() 與 getCruisesCabinType("", listOf())
 ↓
Repository（TransProductRepository）
 │  直接依賴 KKApi（無 UseCase 抽象層，技術債）
 │  呼叫：kkApi.b2cApi.transportation.getCruisesInfo(productOid, locale, currency)
 │  呼叫：kkApi.b2cApi.transportation.getDefaultCruisesCabinType(...)
 ↓
API（ITransportationApiService）
 │  GET v2/trans/cruises/info?product_oid=&locale=&currency=
 │  POST v2/trans/cruises/cabin_types（DefaultCruisesCabinTypesRequest）
 ↓
後端 API
```

### 流程 C：商品詳情回傳後串接的次要 API

```
ViewModel（ProductDetailViewModel）
 │  收到 ProductDetailData 後，callNextAPIsWhenProductDetailReady() 觸發：
 ├─ getProductAnnouncement(productOid)
 ├─ getProductPromoBanners(productOid, prodCat, destinations)
 ├─ getSupplierInfoList(supplierOidList)
 ├─ loadMorePackageCalendarData(productId, dateRange, useHybridCalendar)
 └─ getProductPackages(productId, useHybridCalendar)
```

### 回傳流

```
後端 API（v2/cdn/product/{product_mid}）
 │  Response：ProductDetailData（含 product、product_setting、packages）
 ↓
Repository（ProductRepository）
 │  apiResultData() 解析 B2CApiResponse<ProductDetailData>
 ↓
UseCase（GetProductDetailUseCase）
 │  emit(ApiResult.success / error / upgrade)
 │  flow 管線：onStart 發 Loading，onCompletion 發 Loaded
 ↓
ViewModel（ProductDetailViewModel）
 │  ApiResult.Loading → _productDetailState = ProductDetailState(isLoading = true)
 │  ApiResult.Success → _productDetailState = ProductDetailState(productDetailData = data)
 │  ApiResult.Error → _productDetailState = ProductDetailState(error = desc)
 │  ApiResult.Upgrade → KKEventBus 發送 ShowSystemUpgrade
 ↓
UI（TransProductDetailFragment observeData()）
 │  productVM.productDetailState.launchAndCollectIn(viewLifecycleOwner)
 ├─ isLoading → showLoadingProgress()
 ├─ productDetailData != null →
 │    appBarHelper.updateProductDetailData()
 │    productController.productDetailData = data
 │    setProductSecondScreenData()（填充介紹、行程、供應商）
 │    callNextAPIsWhenProductDetailReady()
 └─ error → networkUnavailableViewHelper.show()
```

---

## 逐層說明

### UI 層
> `onCreate` 呼叫 `initArguments()`（嘗試從 bundle 取得 `ProductDetailData` 預先顯示 header）、`initDelegate()`、`initLauncher()`。`initAction()` 觸發所有 API 請求，包含商品詳情、遊輪資訊、評論、旅遊人數類型等。觀察多個 StateFlow（`productDetailState`、`productPackagesState`、`productCouponsState` 等）與一個 LiveData（`transCruisesViewModel.state`）。

### ViewModel 層
> `ProductDetailViewModel` 使用 `MutableStateFlow` 管理各 API 的獨立狀態（`ProductDetailState`、`ProductPackagesState`、`ProductCouponsState` 等），每個資料源對應一個 StateFlow。`TransCruisesViewModel` 以 `MutableLiveData<ViewState>` 管理遊輪專屬複合狀態（遊輪資訊、行帆日期、艙型清單等）。兩個 ViewModel 皆以 `activityViewModel` scope 共享。

### UseCase 層
> `GetProductUseCase` 為聚合類，整合商品頁所需的所有子 UseCase，方便 Koin 注入。`GetProductDetailUseCase` 含快取判斷，可直接回傳 `appSharedData` 暫存資料。`TransCruisesViewModel` 直接呼叫 `TransProductRepository`，缺少 UseCase 抽象層（技術債）。

### Repository 層
> `ProductRepository` 繼承 `BaseApiRepository`，`getProductDetail` 額外觸發 `trackProductView` 瀏覽埋點（非阻斷）。`TransProductRepository` 直接依賴 `KKApi`，未走 `domain/contract` 介面分離（技術債）。

### API 層
> - 商品詳情：`GET v2/cdn/product/{product_mid}`（Header 傳 currency/lang/locale）
> - 遊輪資訊：`GET v2/trans/cruises/info`
> - 預設艙型列表：`POST v2/trans/cruises/cabin_types`（DefaultCruisesCabinTypesRequest）
> - 套餐行事曆：`GET v2/product/{product_mid}/calendar`
> - 套餐列表：`GET v2/product/{product_mid}/pkg`
> - 商品公告：`GET v2/product/{product_oid}/announcement`

---

## View 方法清單

| 方法 | 說明 |
|------|------|
| `onCreate()` | 呼叫 `initArguments()`、`initDelegate()`、`initLauncher()`、同步持久化資料 |
| `initView()` | 初始化 RecyclerView、AppBar、購買按鈕點擊事件、BottomSheet 行為 |
| `initAction()` | 觸發所有初始 API 請求：遊輪資訊、評論照片、旅客類型、KK Points、用戶評論、推薦商品 |
| `observeData()` | 訂閱所有 StateFlow / LiveData，處理資料回傳後的 UI 更新 |
| `initHeaderView()` | 若有預帶 init data，先填充 header 避免白屏 |
| `hasDetailResponseData()` | 判斷商品詳情是否已從 API 取得（非初始預帶值） |
| `updateProductBasicInfo()` | 根據最新狀態重新產生 `TitleViewInfo`、`SkuSelectorViewInfo`、`CabinTypesViewInfo` 並交由 Controller 渲染 |
| `setProductSecondScreenData()` | 商品詳情取得後，填充介紹、行程（schedule）、使用方式（howTo）、供應商資訊 |
| `updateProductRouteMap()` | 更新遊輪航線地圖 |
| `updateBookingButton()` | 根據 `isPurchaseAvailable()` 與遊輪是否可訂，決定購買按鈕文字與可點擊狀態 |
| `btnPurchaseClickedAndCheck()` | 點擊購買後，先檢查資訊是否填寫完整，再呼叫 `getTranRouteDetail()` 取得路線詳情 |
| `goToBookingPage()` | 導航至 `TransProductBookingFragment` |
| `getProductCoupon()` | 取得商品優惠券 |
| `getProductUserComment()` | 取得用戶評論 |
| `onSailingDateClicked()` | 開啟遊輪日期選擇 Dialog（`TransCruisesDateDialogFragment`） |
| `onRoomsAndPassengerClicked()` | 開啟房間與乘客人數 Dialog（`TransCruisesRoomPeopleDialogFragment`） |
| `onCruisesCabinMoreClicked()` | 開啟艙型完整列表頁（`CruisesCabinTypesFullFragment`） |
| `onClickReadMore()` | 導航至文字詳讀頁（`TransProductReadMoreFragment`） |
| `onClickCommentReadMore()` | 導航至評論詳情頁（`TransProductCommentFragment`） |
| `onClickGalleryPhoto()` | 開啟圖片瀏覽器（`GalleryActivity`） |
| `onBannerItemClick()` | 開啟評論照片牆（`CommentGalleryWallActivity`） |
| `onDestroyView()` | 清理 ViewPager adapter、ChatFloatingView、RxJava disposable |
| `trackProductPageViewed()` | 觸發商品頁瀏覽埋點（僅觸發一次） |

---

## ViewModel 方法清單

### ProductDetailViewModel

| 方法 | 說明 |
|------|------|
| `init` | 讀取 DataStore（QuickSkuEntry AB 設定）、初始化 delegate、啟動 AB testing、取得 DCS 設定 |
| `getProductDetail()` | 觸發商品詳情 UseCase，更新 `_productDetailState` |
| `callNextAPIsWithOutPackagesWhenProductDetailReady()` | 取得詳情後串接：公告、Promo Banner、供應商資訊 |
| `getProductPackages()` | 取得套餐列表，更新 `_productPackagesState` |
| `loadMorePackageCalendarData()` | 載入套餐月曆資料，更新 `_productPackageCalendar` |
| `getUserComment()` | 取得用戶評論，轉換為 `AIProductComment` 並更新 `_aiProductCommentState` |
| `getTravelerType()` | 取得旅客類型，更新 `_travelerTypeState` |
| `getProductCoupons()` | 取得優惠券列表，更新 `_productCouponsState` |
| `getProductAnnouncement()` | 取得商品公告，更新 `_productAnnouncementState` |
| `getOrderUserKKPoints()` | 取得 KK Points 資訊，更新 `_orderKKPointsInfoState` |
| `getProductPromoBanners()` | 取得商品 Promo Banner，更新 `_productEventBannerState` |
| `getRecommendProducts()` | 取得推薦商品，更新 `_recommendProductsState` |
| `getDCSFreshTags()` | 從 DCS 取得 FreshChat bot tag |
| `trackPageViewOptimization()` | 在所有資料就緒後觸發商品頁瀏覽事件（combine 多個 StateFlow debounce 2秒） |

### TransCruisesViewModel

| 方法 | 說明 |
|------|------|
| `getInitApi()` | 設定 productOid，同時呼叫 `getCruisesInfo()` 與 `getCruisesCabinType()` |
| `getCruisesInfo()` | 取得遊輪基本資訊（服務名稱、退款政策、艙等等），更新 `_state.cruisesInfo` |
| `getCruisesCabinType()` | 取得艙型列表，更新 `_state.cruisesCabinTypes` |
| `getCruisesSailing()` | 取得指定日期範圍的航班，更新 `_state.cruisesSailing` |
| `initBookingPageData()` | 進入訂購頁前取得成員資料與行程資訊 |
| `checkProductAllInformationComplete()` | 點擊購買時驗證日期、房間、艙型是否已選完整 |
| `getTranRouteDetail()` | 取得路線詳情後觸發 `SingleEvent.GoToBookingPage` |
| `updateSessionKey()` | 產生新 session key（時間戳 hex + 隨機字符） |
| `setIsFromPaymentBackStack()` | 記錄是否從支付頁返回，決定是否直接跳轉訂購頁 |

---

## 重要資料轉換點

| 位置 | 輸入型別 | 輸出型別 | 說明 |
|------|---------|---------|------|
| `GetProductDetailUseCase` | `B2CApiResponse<ProductDetailData>` | `ApiResult<ProductDetailData>` | HTTP 狀態 + 業務狀態碼（NOT_SOLD、NOT_FOUND、UPGRADE）轉換 |
| `ProductDetailViewModel` | `ApiResult<ProductDetailData>` | `ProductDetailState` | 將 Loading/Success/Error 對應 UI 狀態 |
| `TransCruisesViewModel` | `CruisesInfoResponse` | `ViewState.cruisesInfo` | 遊輪資訊直接寫入 LiveData 複合狀態 |
| `Fragment.updateProductBasicInfo()` | `ProductDetailData` + `CruisesInfoResponse` | `TransTitleViewInfo` / `TransSkuSelectorViewInfo` / `TransCabinTypesViewInfo` | 透過 `generate*ViewInfo()` 系列方法轉換成 Epoxy Controller 所需的 ViewInfo |
| `ProductCommentViewInfoConverter` | `ProductReview` | `AIProductComment` | 評論資料轉換為含 AI 關鍵字摘要的 UI 呈現物件 |

---

## 業務邏輯摘要

- **購買按鈕啟用條件**：`productDetailData.isPurchaseAvailable()` 且 `transCruisesViewModel.state.value?.isAvailable == true`，兩者需同時成立。
- **商品不再銷售處理**：`GetProductDetailUseCase` 識別 `PRODUCT_IS_NOT_SOLD` / `PRODUCT_IS_CLOSE_SOLD` 狀態碼後，回傳特殊的 `ProductDetailData.getNoLongerSoldProduct()`，Fragment 顯示 Alert Dialog 後關閉頁面。
- **Init Data 預先渲染**：若 `appSharedData.enableProductPageInitData` 開啟，`initArguments()` 會從 bundle 取得前頁傳入的 `ProductDetailData` 預先填充畫面，API 回傳後再覆蓋，減少白屏時間。
- **遊輪訂購驗證**：點擊購買時，`TransCruisesViewModel.checkProductAllInformationComplete()` 驗證日期、乘客人數、艙型是否已選完整，未完整則捲動至對應選擇區域並顯示提示。
- **Session Key**：進入訂購頁前由 `updateSessionKey()` 產生，格式為時間戳 hex（低 10 碼）+ 隨機字符補齊，用於後端識別本次訂購流程。
- **從支付返回**：`TransCruisesViewModel.isFromPaymentBackStack` 記錄是否從支付頁返回，若是則直接跳過商品頁重新選擇流程，直接導向訂購頁。
- **商品詳情頁瀏覽事件**：`ProductDetailViewModel` combine 六個 StateFlow（詳情載入完成、供應商資訊、chat 狀態、AB testing、套餐、月曆），debounce 2 秒後觸發一次追蹤事件，確保所有資料就緒後才送出。
- **錯誤處理**：API 呼叫失敗顯示 `networkUnavailableViewHelper`（可重試）；SystemUpgrade 透過 `KKEventBus` 發送全局事件顯示維護頁。

---

## 已知技術債

- `TransCruisesViewModel` 直接持有 `TransProductRepository`，未走 `domain/contract` 介面分離，違反 Clean Architecture 理想架構。
- `TransProductRepository` 直接依賴 `KKApi`，未實作 domain/contract 介面，且放置在 `:feature:product_page` 模組內（應屬 `:data:repository`）。
- `GetProductDetailUseCase` 直接依賴 `ProductRepository`（`:data:repository`）與 `HotelProductRepository`，未透過 `:domain:contract` 介面，為現有技術債，新增功能時應避免擴大此依賴。
- `ProductDetailViewModel` 的建構子注入了大量依賴（超過 15 個），耦合度偏高，建議未來拆分為多個較小的 ViewModel 或 Delegate。

## 相關筆記
- [01-architecture](../01-architecture.md)
- [02-modules](../02-modules.md)
- [03-ui-patterns](../03-ui-patterns.md)
- [05-networking](../05-networking.md)
- [06-data-layer](../06-data-layer.md)
- [07-concurrency](../07-concurrency.md)
- [order-detail-compose](order-detail-compose.md)
- [product-detail](product-detail.md)
- [sku-activity-shell](sku-activity-shell.md)

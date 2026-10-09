# 模組結構指南

> **AI 使用說明**：分析問題時，先對照「問題類型 → 模組對照」表快速定位，再依模組職責確認搜尋範圍。

---

## 快速定位：問題類型 → 模組

| 問題類型 | 首先看這裡 | 其次看這裡 |
|---------|-----------|-----------|
| API 請求失敗 | `:data:networking:api` | `:data:repository` |
| 資料庫問題 | `:data:roomDb` | `:data:repository` |
| 業務邏輯錯誤 | `:domain:usecase` | `:domain:contract` |
| UI 顯示異常 | `:feature:common:*` 對應功能 | `:shared:UI:*` |
| Token/登入問題 | `:data:networking:apiToken` | `:domain:usecase` |
| 支付問題 | `:shared:payment` | `:data:networking:api` |
| 追蹤/埋點問題 | `:shared:tool:tracker:KKTracker` | `:shared:tool:tracker:KKAnalytics` |
| 路由/DeepLink | `:shared:routing` | `:shared:tool:router:krouter` |
| 通知問題 | `:feature:common:notification` | `:shared:routing` |
| 聊天功能 | `:feature:common:chat` | `:data:networking:api`（Socket.IO） |
| 飯店搜尋/商品 | `:feature:hotel:*` | `:feature:shared:product` |
| 票券/行程 | `:feature:multiple:ticket` / `:feature:multiple:tour` | `:feature:shared:*` |
| 設計元件 | `:shared:UI:kkcomponents` | `:shared:UI:designsystem` |

---

## 架構層次與模組清單

### Domain 層（業務邏輯）

| 模組 | 路徑 | 職責 |
|------|------|------|
| `:domain:contract` | `domain/contract/` | 定義 Repository 介面、Handler 介面（ChatRepository、WebSocketEventHandler、PushNotificationDataHandler 等） |
| `:domain:usecase` | `domain/usecase/` | UseCase 實作，Koin `@Factory`，目前直接依賴 `:data:repository`（技術債） |

**注意**：`:domain:usecase` 理應只依賴 `:domain:contract`，但目前也依賴 `:data:repository` 與 `:data:networking:api`，新增時避免擴大此依賴。

---

### Data 層（資料存取）

| 模組 | 路徑 | 職責 |
|------|------|------|
| `:data:model` | `data/model/` | API response model、Room entity、Parcelable data class，使用 `@Parcelize`、Gson/kotlinx.serialization |
| `:data:repository` | `data/repository/` | 實作 domain:contract 介面，聚合 API + DB，處理錯誤轉換 |
| `:data:roomDb` | `data/roomDb/` | Room 資料庫設定、DAO、Migration |
| `:data:networking:api` | `data/networking/api/` | Retrofit Service 定義，Socket.IO WebSocket |
| `:data:networking:apiToken` | `data/networking/apiToken/` | Token 管理與 refresh 邏輯 |
| `:data:networking:log` | `data/networking/log/` | OkHttp interceptor 網路日誌 |

**重要 Repository 範例**：BookingRepository、CartRepository、ProductRepository、ChatRepositoryImpl、HotelSearchRepository、CreditCardRepository、PushNotificationRepository

---

### Feature 層（功能模組）

#### Feature:Common（功能 UI）

| 模組 | 路徑 | 職責 |
|------|------|------|
| `:feature:common:product` | `feature/common/product/` | 商品頁面 UI |
| `:feature:common:search` | `feature/common/search/` | 搜尋頁面 UI |
| `:feature:common:order` | `feature/common/order/` | 訂單管理 UI |
| `:feature:common:home` | `feature/common/home/` | 首頁 UI |
| `:feature:common:notification` | `feature/common/notification/` | 通知頁面 UI |
| `:feature:common:coupon_page` | `feature/common/coupon_page/` | 優惠券頁面 |
| `:feature:common:chat` | `feature/common/chat/` | 聊天 UI |

#### Feature:Shared（功能核心邏輯）

| 模組 | 路徑 | 職責 |
|------|------|------|
| `:feature:shared:product` | `feature/shared/product/` | 商品業務邏輯（`@Parcelize`、Navigation safe args） |
| `:feature:shared:order` | `feature/shared/order/` | 訂單業務邏輯 |
| `:feature:shared:search` | `feature/shared/search/` | 搜尋業務邏輯 |
| `:feature:shared:core` | `feature/shared/core/` | Feature 間共用工具與基礎類（僅依賴 app_resource、data:model） |
| `:feature:shared:ui` | `feature/shared/ui/` | Feature 間共用 UI 元件 |
| `:feature:creditcard_list` | `feature/creditcard_list/` | 信用卡管理 |

#### Feature:Hotel（飯店專屬）

| 模組 | 路徑 | 職責 |
|------|------|------|
| `:feature:hotel:product` | `feature/hotel/product/` | 飯店商品詳情 |
| `:feature:hotel:search` | `feature/hotel/search/` | 飯店搜尋 |

#### Feature:Multiple Products（多商品）

| 模組 | 路徑 | 職責 |
|------|------|------|
| `:feature:multiple:ticket` | `vm/ticket/` | 票券訂購 |
| `:feature:multiple:tour` | `vm/Tour/` | 行程訂購 |

#### Feature:Transportation

| 模組 | 路徑 | 職責 |
|------|------|------|
| `:feature:transportation` | `libs/transportation/` | 交通/接駁訂購 |

---

### Shared 層（跨功能共用）

#### 基礎層

| 模組 | 路徑 | 職責 |
|------|------|------|
| `:shared:base` | `shared/base/` | 通用工具、View 擴充、Extension functions（被大多數模組依賴） |
| `:shared:routing` | `shared/routing/` | DeepLink 與 Navigation 管理 |
| `:shared:app_resource` | `shared/app_resource/` | 全域資源（strings、colors、drawables），無外部依賴（最底層） |
| `:shared:payment` | `shared/payment/` | TapPay、Adyen、Stripe、3DS 支付抽象層 |

#### UI 元件庫

| 模組 | 路徑 | 職責 |
|------|------|------|
| `:shared:UI:designsystem` | `libs/designsystem/design/` | Material3 Compose 設計 token 與基礎元件 |
| `:shared:UI:kkcomponents` | `libs/UI/kkcomponents/` | KKday 業務專用 Compose 元件 |
| `:shared:UI:kkcalendar` | `libs/UI/kkcalendar/` | 日曆 UI 元件 |
| `:shared:UI:material-date-time-picker` | `libs/UI/material-date-time-picker/` | 日期時間選擇器 |
| `:shared:UI:album` | `libs/UI/album/` | 圖片/媒體選擇器（原生 Views） |

#### 工具庫

| 模組 | 路徑 | 職責 |
|------|------|------|
| `:shared:tool:tracker:KKTracker` | `libs/tool/tracker/KKTracker/` | 追蹤事件入口（Analytics wrapper） |
| `:shared:tool:tracker:KKAnalytics` | `libs/tool/tracker/KKAnalytics/` | 多平台 Analytics 核心實作 |
| `:shared:tool:tracker:KKAnalyticsSpec` | `libs/tool/tracker/KKAnalyticsSpec/` | 追蹤事件 schema 定義 |
| `:shared:tool:router:krouter` | `libs/tool/router/krouter/` | DeepLink 路由引擎 |
| `:shared:tool:event_bus` | `libs/tool/event_bus/` | 事件發布/訂閱 |
| `:shared:tool:abtesting:KKAbtesting` | `libs/tool/abtesting/KKAbtesting/` | A/B 測試（Apptimize wrapper） |
| `:shared:tool:debugtool` | `libs/tool/debugtool/` | Debug 工具（僅 debug build） |
| `:shared:tool:webjs` | `libs/tool/webjs/` | WebView ↔ JavaScript bridge |
| `:shared:tool:view_builder` | `libs/tool/view_builder/` | 動態 UI 構建（Builder pattern） |
| `:shared:tool:lint` | `libs/tool/lint/` | 自訂 Lint 規則 |
| `:shared:tool:reductor:*` | `libs/tool/reductor/` | Redux-like 狀態管理（4 個子模組，漸進遷移中） |

---

## 依賴流向圖

```
:app
 └── :feature:multiple:ticket / :tour
      └── :feature:common:* / :feature:shared:*
           └── :domain:usecase ──(技術債)──> :data:repository
                ├── :domain:contract (應只依賴此)
                ├── :data:model
                ├── :data:networking:api
                └── :shared:base

:data:repository
 ├── :domain:contract
 ├── :data:model
 ├── :data:roomDb
 ├── :data:networking:api
 └── :shared:base

:shared:app_resource  ← 最底層，無依賴
:shared:UI:designsystem ← 設計 token，幾乎無業務依賴
```

---

## Build 基礎設施

| 位置 | 用途 |
|------|------|
| `build-logic/convention/` | 自訂 Gradle Convention Plugins（`com.kkday.feature`、`com.kkday.android.library` 等） |
| `gradle/libs.versions.toml` | 版本目錄（所有依賴版本集中管理） |
| `settings.gradle.kts` | 模組 include 與路徑對應 |
| `config/quality/` | Detekt、Lint 設定 |

---

---

## 功能頁面 → 入口檔案索引

> 快速定位各功能頁面的 Fragment/Activity 與對應 ViewModel、Repository、API Service。

### 首頁相關

| 功能 | 入口檔案 | 路徑 | ViewModel | Repository | API | Module |
|------|---------|------|-----------|-----------|-----|--------|
| 首頁主頁面 | `HomeV2Fragment.kt` | `app/.../homeV2/presentation/` | `HomeViewModelV2` | `HomeRepository` | `KKApi (b2cApi.home)` | `:app` |
| 主題分類頁 | `CategoryPageActivity.kt` | `libs/feature/search_page/.../category/` | `CategoryPageViewModel` | `RecommendCategoryRepository` `SearchExploreRepository` | `SearchApiService` | `:feature:search_page` |
| 交通首頁 | `TransHomeActivity.kt` | `app/.../transportation/home/` | Presenter 模式 | — | — | `:app` |
| 優惠專區 | `DealsFragment.kt` | `app/.../view/deals/` | — | — | — | `:app` |

### 搜尋相關

| 功能 | 入口檔案 | 路徑 | ViewModel | Repository | API | Module |
|------|---------|------|-----------|-----------|-----|--------|
| 搜尋首頁（Explore） | `ExplorePage.kt` | `libs/feature/search_page/.../explore/` | `ExploreViewModel` | `DestinationRepository` | `DestinationApiService` | `:feature:search_page` |
| 搜尋中繼頁 | `InstantSearchFragment.kt` | `app/.../search/instant/` | `InstantSearchViewModel` | `SearchRepository` | `SearchApiService` | `:app` |
| 舊版搜尋結果頁 | `SearchResultActivity.kt` | `app/.../search/activity/` | `SearchResultViewModel` | `SearchRepository` | `SearchApiService` | `:app` |
| 新版搜尋結果頁 | `NewSearchResultActivity.kt` | `libs/feature/search_page/.../search/` | `SearchResultViewModel` | `SearchRepository` | `SearchApiService` | `:feature:search_page` |
| 目的地頁 | `DestinationPageActivity.kt` | `libs/feature/search_page/.../category/` | `DestinationPageViewModel` | `SearchExploreRepository` `DestinationRepository` | `RecommendCategoryApiService` | `:feature:search_page` |
| 分類搜尋結果（Compose） | `CategorySearchResultPage.kt` | `libs/feature/search_page/.../category/compose/search_result/` | `CategorySearchResultViewModel` | `SearchRepository` | `SearchApiService` | `:feature:search_page` |

### 商品相關

| 功能 | 入口檔案 | 路徑 | ViewModel | Repository | API | Module |
|------|---------|------|-----------|-----------|-----|--------|
| 通用商品詳情頁 | `CommonProductDetailFragment.kt` | `libs/feature/product_page/.../detail/view/` | `ProductDetailViewModel` | `ProductRepository` `ProductDetailDcsRepository` | `IProductApiService` | `:feature:product_page` |
| 飯店商品詳情頁 | `HotelProductDetailFragment.kt` | `libs/feature/hotel/product/.../view/` | `HotelProductDetailViewModel` | `HotelProductRepository` `BookingRepository` | `IHotelProductApiService` | `:feature:hotel` |
| 交通商品頁 | `TransProductDetailFragment.kt` | `libs/feature/product_page/.../detail/transportation/` | `ProductDetailViewModel`（共用） | `ProductRepository` | `IProductApiService` | `:feature:product_page` |

### 規格選擇相關

> 規格選擇系統採用共用 ViewModel 架構：`SharedSpecificationActivity` 為基底類，`MultipleSpecificationActivity` 繼承並擴展票券邏輯。ViewModel 透過 activity scope 共享，Fragment 不持有自己的 ViewModel 實例。

| 功能 | 入口檔案 | 路徑 | ViewModel | Repository | API | Module |
|------|---------|------|-----------|-----------|-----|--------|
| 規格選擇基底頁（通用） | `SharedSpecificationActivity.kt` | `app/.../product/specification/` | `SpecificationSharedViewModel` | `ProductRepository` `CartRepository` `HotelProductRepository` | `IProductApiService` `IHotelProductApiService` | `:app` |
| 票券規格選擇頁（Activity 殼） | `MultipleSpecificationActivity.kt` | `app/.../product/specification/multiple/ticket/view/` | `TicketSpecificationSharedViewModel` `SkuSharedViewModel` `MultipleCalendarViewModel` | `ProductRepository` `CartRepository` `ESimDcsRepository` | `IProductApiService` | `:app` |
| 票券規格選擇頁（Fragment，V3） | `MultipleSpecificationV3Fragment.kt` | `app/.../product/specification/multiple/ticket/view/` | `TicketSpecificationSharedViewModel`（activity scope） `SkuSharedViewModel` `MultipleCalendarViewModel` | （同 Activity 共用） | （同 Activity 共用） | `:app` |
| 套票 Bundle SKU 選擇頁 | `TicketBundleSKUFragment.kt` | `app/.../product/specification/multiple/ticket/bundle/view/` | `TicketSpecificationSharedViewModel`（activity scope） `MultipleCalendarViewModel` | （同 Activity 共用） | （同 Activity 共用） | `:app` |

### 購物結帳相關

| 功能 | 入口檔案 | 路徑 | ViewModel | Repository | API | Module |
|------|---------|------|-----------|-----------|-----|--------|
| 結帳填寫頁 | `OrderFormFillingActivity.kt` | `app/.../product/form/` | `OrderFormFillingViewModel` | `CartRepository` `CheckoutRepository` | `CartApiService` `CheckoutApiService` | `:app` |
| 旅遊資料填寫頁 | `ScheduleFormActivity.kt` | `app/.../product/form/schedule/` | — | — | — | `:app` |
| 旅客資料 Item（元件） | `ScheduleFormTravelerInfoItemScreen.kt` / `V2` | `.../form/schedule/traveler/item/` | — | — | — | `:app` |
| 旅客資料 Dialog | `TravelerInfoDialog.kt` | `.../form/schedule/traveler/item/v2/dialog/` | — | — | — | `:app` |
| 購物車頁面 | `CartActivity.kt` | `app/.../cart/` | `CartViewModel` | `CartRepository` | `CartApiService` | `:app` |

### 訂單相關

| 功能 | 入口檔案 | 路徑 | ViewModel | Repository | API | Module |
|------|---------|------|-----------|-----------|-----|--------|
| 訂單列表（Fragment 殼） | `OrderComposeFragment.kt` | `libs/feature/order_page/.../presentation/` | `OrderViewModel` | `OrderRepository` | `IOrderApiService` | `:feature:order_page` |
| 訂單列表（Compose 頁） | `OrderListPage.kt` | `libs/feature/order_page/.../presentation/compose/` | `OrderViewModel`（同上） | `OrderRepository` | `IOrderApiService` | `:feature:order_page` |
| 舊版訂單詳情 | `OrderDetailFragment.kt` | `app/.../order/detail/order/` | `OrderDetailViewModel` | `OrderRepository` `TransportationRepository` | `IOrderApiService` | `:app` |
| 新版訂單詳情（Compose） | `NewOrderDetailScreen.kt` | `libs/feature/order_page/.../new_detail/` | `NewOrderDetailViewModel` | `OrderRepository` | `IOrderApiService` | `:feature:order_page` |
| 取消訂單 | `CancelOrderActivity.kt` | `app/.../order/cancel/` | `CancelOrderViewModel` | `TransportationRepository` | `TransportationApiService` | `:app` |
| 訂單評論/評價 | `OrderCommentActivity.kt` | `app/.../order/comment/` | — | — | — | `:app` |
| 憑證頁 | `MultiOrderVoucherActivity.kt` | `libs/feature/order_page/.../view/` | — | — | — | `:feature:order_page` |
| 訂購成功頁 | `BookingSuccessB2CActivity.kt` / `BookingSuccessB2CFragment.kt` | `libs/feature/order_page/.../view/` | — | — | — | `:feature:order_page` |
| 聯絡客服（訂單） | `ContactUsActivity.kt` | `app/.../order/contact/` | `ContactUsViewModel` | — | — | `:app` |

### 支付相關

| 功能 | 入口檔案 | 路徑 | ViewModel | Repository | API | Module |
|------|---------|------|-----------|-----------|-----|--------|
| 支付核心服務 | `PaymentService.kt` | `libs/payment/.../business/` | Service 類，非畫面 | — | — | `:shared:payment` |
| 信用卡列表頁 | `CreditCardListActivity.kt` | `libs/feature/creditcard_list/.../creditcardlist/` | `CreditCardViewModel` | `CreditCardRepository` | `CreditCardApiService` | `:feature:creditcard_list` |
| 重新付款頁 | `RepayActivity.kt` | `app/.../repay/` | `RepayViewModel` | `OrderRepository` | `IOrderApiService` | `:app` |

### 會員相關

| 功能 | 入口檔案 | 路徑 | ViewModel | Repository | API | Module |
|------|---------|------|-----------|-----------|-----|--------|
| 登入頁 | `SocialLoginActivity.kt` | `app/.../login/` | — | — | — | `:app` |
| 登入 Splash | `SocialLoginSplashActivity.kt` | `app/.../login/splash/` | — | — | — | `:app` |
| 註冊頁 | `SignUpActivity.kt` | `app/.../login/signup/` | — | — | — | `:app` |
| 會員條款頁 | `MemberTermsActivity.kt` | `app/.../login/terms/` | — | — | — | `:app` |
| 會員資料頁 | `UserFragment.kt` | `app/.../user/` | `UserViewModel` | `HomeRepository` | `KKApi (b2cApi)` | `:app` |
| 個人資料編輯 | `ProfileActivity.kt` | `app/.../user/profile/` | — | — | — | `:app` |
| 忠誠計畫頁 | `LoyaltyActivity.kt` | `app/.../user/loyalty/` | — | — | — | `:app` |
| 願望清單（Compose） | `WishComposeFragment.kt` | `app/.../wish/` | `WishViewModel` | `WishRepository` | `WishProductApiService` | `:app` |
| 優惠券詳情頁 | `CouponDetailActivity.kt` | `app/.../share/coupon/` | — | — | — | `:app` |
| 優惠券列表（Compose） | `CouponPage.kt` / `CouponMainActivity.kt` | `libs/feature/coupon_page/.../` | — | — | — | `:feature:coupon_page` |
| 設定頁 | `SettingActivity.kt` | `app/.../user/setting/` | — | — | — | `:app` |

### 通知相關

| 功能 | 入口檔案 | 路徑 | ViewModel | Repository | API | Module |
|------|---------|------|-----------|-----------|-----|--------|
| 通知中心 | `NotificationActivity.kt` | `libs/feature/notification_page/.../` | — | — | — | `:feature:notification_page` |
| 聊天頁 | `ChatBotActivity.kt` | `libs/feature/chat/.../` | — | — | — | `:feature:chat` |

### App 啟動/Onboarding

| 功能 | 入口檔案 | 路徑 | ViewModel | Repository | API | Module |
|------|---------|------|-----------|-----------|-----|--------|
| Splash 頁 | `WelcomeActivity.kt` | `app/.../launch/` | — | — | — | `:app` |
| 引導/Onboarding 頁 | `GuideActivity.kt` | `app/.../launch/` | — | — | — | `:app` |

### 交通/運輸（深層功能）

| 功能 | 入口檔案 | 路徑 | ViewModel | Repository | API | Module |
|------|---------|------|-----------|-----------|-----|--------|
| 巴士訂位填寫頁 | `BusListBookingFragment.kt` | `app/.../buslist/booking/` | — | — | — | `:app` |
| 巴士選座頁 | `BusListBookingSeatFragment.kt` | `app/.../buslist/booking/seat/` | — | — | — | `:app` |
| 港珠澳巴士訂位 | `CnhkBusBookingFragment.kt` | `app/.../cnhkbus/booking/` | — | — | — | `:app` |
| 租車訂位頁 | `CarRentalBookingFragment.kt` | `app/.../rental/zzimcar/booking/` | — | — | — | `:app` |
| 機場服務填表頁 | `AirportFillDetailActivity.kt` | `app/.../airport/pages/` | — | — | — | `:app` |
| 交通乘客資料 | `TransPassengerInfoFragment.kt` | `app/.../transportation/pages/dialog/` | — | — | — | `:app` |

### 商品評論

| 功能 | 入口檔案 | 路徑 | ViewModel | Repository | API | Module |
|------|---------|------|-----------|-----------|-----|--------|
| 商品用戶評論（票券） | `UserCommentFragment.kt` | `libs/feature/product_page/.../userComment/fragment/` | — | — | — | `:feature:product_page` |
| 商品用戶評論（飯店） | `HotelUserCommentFragment.kt` | `libs/feature/hotel/product/.../userComment/` | — | — | — | `:feature:hotel` |

### 地圖/店家

| 功能 | 入口檔案 | 路徑 | ViewModel | Repository | API | Module |
|------|---------|------|-----------|-----------|-----|--------|
| 店家/門市地圖頁 | `StoreActivity.kt` | `app/.../supplier/` | — | — | — | `:app` |
| 可縮放地圖頁 | `ZoomableMapActivity.kt` | `app/.../map/` | — | — | — | `:app` |

### 其他重要頁面

| 功能 | 入口檔案 | 路徑 | ViewModel | Repository | API | Module |
|------|---------|------|-----------|-----------|-----|--------|
| WebView 頁 | `KKdayWebActivity.kt` | `app/.../web/` | — | — | — | `:app` |
| 飯店分類搜尋頁 | `HotelCategoryPageActivity.kt` | `libs/feature/hotel/search/.../category/main/` | `HotelCategoryPageViewModel` | — | — | `:feature:hotel` |
| 商品規格選擇頁 | `CommonSpecificationActivity.kt` | `app/.../product/specification/` | — | — | — | `:app` |

---

*文件版本：Step 2 of AI Guide | 最後分析日期：2026-03-19*

## 相關筆記
- [03-ui-patterns](03-ui-patterns.md)
- [05-networking](05-networking.md)
- [06-data-layer](06-data-layer.md)
- [07-concurrency](07-concurrency.md)
- [checkout](features/checkout.md)
- [order-detail-compose](features/order-detail-compose.md)
- [order-success](features/order-success.md)
- [sku-activity-shell](features/sku-activity-shell.md)

# KTM 商品卡 Impression 埋點規格文件

## 概述

本文件定義了商品卡（ProductCard）在 KTM 追蹤系統中的 Impression 埋點規格，包含三種主要的曝光追蹤事件。

---

## 事件規格

### 1. 商品卡基本曝光 (Basic Impression)

**觸發條件：**
- 當商品卡出現在使用者螢幕上
- 商品卡面積顯示超過 80%
- 同個頁面的同張卡不會重複觸發
- v2, v3 card 都要埋點

**事件屬性：**
- **觸發方式：** `Impression`
- **發生頁面：** `XXXPg`（依實際頁面而定）

#### 必要參數 (recommendProperty)

| 參數名稱 | 資料類型 | 必填 | 範例值 | 說明 |
|---------|---------|------|--------|------|
| `eventType` | string | ✅ | `view` | 固定值 "view" |
| `cardIndex` | integer | ✅ | `1, 2, 3...` | 依照 API response 的 index，卡片編號從 1 開始 |
| `targetType` | string | ✅ | `prod` | 推薦內容類型 |
| `targetId` | string | ✅ | `12345` | 商品 ID (prod_mid)，使用英文名稱 |
| `sectionName` | string | ✅ | `DestPgRecom` | 區塊名稱（見下方區塊列表） |
| `subSection` | integer | ❌ | `1, 2, 3` | 子區塊編號（僅特定區塊需要） |

---

### 2. 商品卡活躍曝光 (Active View)

**觸發條件：**
- 當商品卡出現在使用者螢幕上，並且有停止畫面
- 商品卡顯示在螢幕上超過 80%
- 停留超過 1 秒
- 同個頁面的同張卡不會重複觸發
- v2, v3 card 都要埋點

**事件屬性：**
- **觸發方式：** `Impression`
- **發生頁面：** `XXXPg`（依實際頁面而定）
- **物件名稱：** `ProdCardView`

#### 必要參數 (recommendProperty)

| 參數名稱 | 資料類型 | 必填 | 範例值 | 說明 |
|---------|---------|------|--------|------|
| `eventType` | string | ✅ | `activeView` | 固定值 "activeView" |
| `cardIndex` | integer | ✅ | `1, 2, 3...` | 依照 API response 的 index，卡片編號從 1 開始 |
| `targetType` | string | ✅ | `prod` | 推薦內容類型 |
| `targetId` | string | ✅ | `12345` | 商品 ID (prod_mid)，使用英文名稱 |
| `sectionName` | string | ✅ | `DestPgRecom` | 區塊名稱（見下方區塊列表） |
| `subSection` | integer | ❌ | `1, 2, 3` | 子區塊編號（僅特定區塊需要） |

---

### 3. 商品卡點擊 (Click)

**觸發條件：**
- 點擊商品卡
- v2, v3 card 都要埋點

**事件屬性：**
- **觸發方式：** `Click`
- **發生頁面：** `XXXPg`（依實際頁面而定）
- **物件名稱：** `ProdCardView`

#### 必要參數 (recommendProperty)

| 參數名稱 | 資料類型 | 必填 | 範例值 | 說明 |
|---------|---------|------|--------|------|
| `cardIndex` | integer | ✅ | `1, 2, 3...` | 依照 API response 的 index，卡片編號從 1 開始 |
| `targetType` | string | ✅ | `prod` | 推薦內容類型 |
| `targetId` | string | ✅ | `12345` | 商品 ID (prod_mid)，使用英文名稱 |
| `sectionName` | string | ✅ | `DestPgRecom` | 區塊名稱（見下方區塊列表） |
| `subSection` | integer | ❌ | `1, 2, 3` | 子區塊編號（僅特定區塊需要） |

---

## 區塊名稱 (sectionName) 列表
> section_name - section_description | target_file | target_lines | is_compose | is_product_card |

### 目的地頁面
- `DestPgTopTen` - 目的地頁熱門 | @CategoryTopProductView.kt | L38-L49 | Y | Y |
- `DestPgRecom` - 目的地頁精選玩樂 ⭐ | @POIProdExhibitionView.kt | L143-L151 | Y | Y |
- `DestPgMarketing` - 目的地頁本月推薦 ⭐ | @POIProdExhibitionView.kt | L143-L151 | Y | Y |
- `DestPgLatest` - 目的地頁最新 | @CategoryTopProductView.kt | L54-L79 | Y | Y |
- `DestPgInfinityLoop` - 目的地探索更多 |  @DestinationPage.kt | L824-L835 | Y | Y |

### 訂單相關頁面
- `ConfirmPageRecom` - 訂購成功頁 | @BookingSuccessB2CFragment.kt | L101-L101 | N | Y |
- `OrderLstPgRecom` - 訂單列表頁二單推薦 | @OrderCardExpView | L286-L319 | Y | Y |
- `OrderDetailsPgRecom` - 訂單明細頁下方推薦 | @NewOrderDetailScreen.kt | L860-L921 | Y | Y |
- `OrderLstPgEmptyRecom` - 訂單列表頁無訂單推薦 | @OrderListPage.kt | L325-L346 | Y | Y |

### 個人化頁面
- `FavList` - 我的最愛頁 | @WishFragment.kt | L74-L83 | N | Y

### 分類頁面
- `CatLandingPgTop10` - 分類首頁 Top10 | @CategoryTopProductView.kt | L37-L50 | Y | Y |
- `CatLandingPgRecom` - 分類首頁推薦 ⭐ | @POIProdExhibitionView.kt | L143-L151 | Y | Y |
- `CatResultPg` - 分類列表頁 | @CategorySearchResultPage.kt | L796-L814 | Y | Y |

### 首頁
- `HomePgRecent` - 首頁最近瀏覽 | @ComponentRecentlyBrowsedProductEpoxyModel.kt | L35-L39 | N | N |
- `HomePgRecom` - 首頁為你推薦 | @RecommendProductDelegate.kt | L49-L60 | N | N |
- `HomePgSelect` - 首頁行銷設定 ⭐ | @ComponentCardsWithBoldTitleEpoxyModel.kt | L42-L52 | N | Y |
- `HomePgTopTen` - 首頁 Top10 | @ComponentCardsWithBoldTitleEpoxyModel.kt | L42-L52 | N | Y |

### 搜尋頁面
- `ProdList` - 商品列表 | @SearchResultPage.kt | L650-L669 | Y | Y |
- `ProdListNoResultRecom` - 商品列表無結果推薦 | @SearchResultPage.kt | L582-L587 | Y | Y |
- `SearchRecom` - Search Link 下方商品 | @SearchProductDelegate.kt | L62-L65 | N | N |

### 商品頁面
- `ProdPgRecom` - 商品頁下方推薦 | @ProductCardTitleListComponentModel.kt | L38-L46 | N | Y |

> ps. `DestPgPersonalRecom` Android 沒有，先不做
> ⭐ 標記的區塊支援 `subSection` 參數（1, 2, 3）

---

## 實作注意事項

### API Path
- DestPgTopTen - 目的地頁熱門 -> "v2/recommend/destination/top_products"
- DestPgMarketing - 目的地頁本月推薦 ⭐ -> "v2/recommend/destination/page_setting"
- DestPgRecom - 目的地頁精選玩樂 ⭐ -> "v2/recommend/destination/showcase_products"
- DestPgLatest - 目的地頁最新 -> "v2/recommend/destination/new_products"
- DestPgInfinityLoop - 目的地探索更多 -> "v3/recommend/destination/explore"
- OrderLstPgRecom - 訂單列表頁二單推薦 -> "v2/recommend/order_list/also_bought"
- OrderDetailsPgRecom - 訂單明細頁下方推薦 -> "v2/recommend/also_buy"
- OrderLstPgEmptyRecom-訂單列表真無訂單推薦 -> "v2/recommend/order_list/no_order"
- CatLandingPgTop10 - 分類首頁 Top10 -> "v2.1/recommend/category/top_products"
- CatLandingPgRecom- 分類首頁推薦 ⭐ -> "v2.1/recommend/category/showcase_products"
- CatResultPg- 分類列表頁 -> "v2.2/search/category_list"
- ProdList - 商品列表 -> "v2.1/search/product_list"
- ProdListNoResultRecom - 商品列表無結果推薦 -> "v2/recommend/user_products"


### 曝光追蹤規則
1. **可見度閾值：** 商品卡面積顯示超過 80%
2. **活躍曝光時間：** 停留超過 1 秒
3. **防重複：** 同個頁面的同張卡不會重複觸發
4. **卡片版本：** v2, v3 card 都要埋點

### 資料來源
- `pageType`：固定值 "impression"（僅基本曝光和活躍曝光使用）
- `eventType`：基本曝光為 "view"，活躍曝光為 "activeView"，點擊為 "click"
- `cardIndex`：依照 API response 的 index 順序
- `sectionName`：前端預設

### KTM 追蹤呼叫範例

```kotlin
// 基本曝光
ktmTracker.trackEvent(
    pageType = PageCommonProperty.PageType(KTMPageType.Impression),
    pageName = PageCommonProperty.PageName("DestPg"),
    propertyMap = mapOf(
        KTMModuleType.Product to listOf(
            ProductProperty.RecommendProperty(
                pageType = "impression",
                eventType = "view",
                cardIndex = 1,
                targetType = "prod",
                targetId = "12345",
                sectionName = "DestPgRecom",
                subSection = null
            )
        )
    )
)

// 活躍曝光
ktmTracker.trackEvent(
    pageType = PageCommonProperty.PageType(KTMPageType.Impression),
    pageName = PageCommonProperty.PageName("DestPg"),
    objectName = ObjectCommonProperty.ObjectName("ProdCardView"),
    propertyMap = mapOf(
        KTMModuleType.Product to listOf(
            ProductProperty.RecommendProperty(
                pageType = "impression",
                eventType = "activeView",
                cardIndex = 1,
                targetType = "prod",
                targetId = "12345",
                sectionName = "DestPgRecom",
                subSection = null
            )
        )
    )
)

// 點擊事件
ktmTracker.trackEvent(
    pageType = PageCommonProperty.PageType(KTMPageType.Click),
    pageName = PageCommonProperty.PageName("DestPg"),
    objectName = ObjectCommonProperty.ObjectName("ProdCardView"),
    propertyMap = mapOf(
        KTMModuleType.Product to listOf(
            ProductProperty.RecommendProperty(
                eventType = "click",
                cardIndex = 1,
                targetType = "prod",
                targetId = "12345",
                sectionName = "DestPgRecom",
                subSection = null
            )
        )
    )
)
``` 
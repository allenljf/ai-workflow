# 新交通專案架構與流程說明

## 概述

本文件詳細說明 KKday Android App 新交通專案的完整架構，涵蓋所有 `TransportationType` 支援的服務類型、頁面流程、以及機場接送（點對點）功能。

## TransportationType 支援服務清單

### 鐵路類 (Railway)

#### 1. THSRTW - 台灣高鐵聯票
- **服務名稱**: `thsrtw`
- **對應 Tab**: RAILWAY
- **TransHomeArgument**: `TransHomeArgument.Thsrtw`
- **子頁面**: `TransHomeThsrtwFragment`
- **說明**: 台灣高鐵聯票訂購服務
- **支援功能**: 選擇出發/抵達站點、日期、車次搜尋、訂票

#### 2. RAIL_EUROPE - 歐洲鐵路
- **服務名稱**: `raileurope`
- **對應 Tab**: RAILWAY
- **TransHomeArgument**: `TransHomeArgument.RailEurope`
- **子頁面**: `TransHomeRailEuropeFragment`
- **說明**: 歐洲火車票訂購服務
- **支援功能**: 多國鐵路網路、跨國列車預訂

#### 3. JR_RAIL - 日本 JR 鐵路
- **服務名稱**: `japanrail`
- **對應 Tab**: RAILWAY
- **TransHomeArgument**: `TransHomeArgument.JrRail`
- **子頁面**: `TransHomeJRFragment`
- **搜尋結果頁**: `JRSearchResultListFragment`
- **說明**: 日本 JR 鐵路服務，支援多個供應商
- **供應商**:
  - `JREAST` - JR 東日本 (jreast)
  - `JRWEST` - JR 西日本 (jrwest)
  - `JRCENTRAL` - JR 東海道 (jrcentral)
- **支援功能**: 
  - 出發/抵達站點選擇
  - 日期選擇
  - 篩選條件（filter）
  - 公告橫幅顯示

#### 4. KHSR - 高鐵假期
- **服務名稱**: `khsr`
- **說明**: 高鐵假期套裝行程
- **特殊處理**: 使用 WebView 流程

### 巴士類 (Bus)

#### 5. KOSOKUBUS - 日本高速巴士
- **服務名稱**: `kosokubus`
- **對應 Tab**: BUS
- **TransHomeArgument**: `TransHomeArgument.KosokuBus`
- **子頁面**: `TransHomeKosokubusFragment`
- **搜尋結果頁**: `BusListSearchResultFragmentV2`
- **訂票頁**: `BusListBookingFragment`
- **ViewModel**: `BusListViewModel`
- **說明**: 日本高速巴士訂票服務
- **支援功能**:
  - 出發地/目的地選擇（支援 locationTypes）
  - 日期選擇
  - 篩選條件
  - 登入驗證
  - 路線詳情保存

#### 6. VEXERE - 越南巴士
- **服務名稱**: `vexere`
- **對應 Tab**: BUS
- **TransHomeArgument**: `TransHomeArgument.VexereBus`
- **子頁面**: `TransHomeVexerebusFragment`
- **ViewModel**: `VexereBusViewModel`
- **說明**: 越南 Vexere 巴士服務

#### 7. CNHKBUS - 中港巴士
- **服務名稱**: `cnhkbus`
- **對應 Tab**: BUS
- **TransHomeArgument**: `TransHomeArgument.CnhkBus`
- **子頁面**: `TransHomeCnhkbusFragment`
- **搜尋結果頁**: `CnhkBusSearchResultFragmentV2`
- **訂票頁**: `CnhkBusBookingFragment`
- **ViewModel**: `CnhkBusViewModel`
- **區域**: 香港及澳門地區 (`HONG_KONG_AND_MACAU_SERVICE_COUNTRY_KEY`)
- **說明**: 中港通巴士服務
- **支援功能**:
  - 出發地/目的地選擇
  - 日期選擇
  - 篩選條件
  - 登入驗證

### 租車類 (Car Rental)

#### 8. ZZIMCAR - 韓國租車
- **服務名稱**: `zzimcar`
- **對應 Tab**: CAR_RENTAL
- **TransHomeArgument**: `TransHomeArgument.ZzimCar`
- **子頁面**: `TransHomeZzimcarFragment`
- **搜尋結果頁**: `CarRentalSearchResultFragment`
- **訂票頁**: `CarRentalBookingFragment`
- **ViewModel**: `CarRentalViewModel`
- **說明**: 韓國租車服務
- **支援功能**:
  - 取車/還車地點選擇（可相同）
  - 取車/還車日期與時間
  - 篩選條件
  - 登入驗證
  - 特殊標記: `isFromRepay` 用於重新支付流程

#### 9-12. 全球租車服務
- **GATHER_CAR** (`gathercars`) - 全球租車供應商
- **RENTAL_CARS** (`rentalcars`) - 全球租車供應商
- **ONLINE_TRAVEL_CAR** (`onlinetravelcar`) - 全球租車供應商
- **GO_GO_OUT** (`gogoout`) - 全球租車供應商

所有全球租車服務統一使用:
- **對應 Tab**: CAR_RENTAL
- **TransHomeArgument**: `TransHomeArgument.GatherCar`
- **子頁面**: `TransHomeGatherCarsFragment`
- **搜尋結果頁**: `GatherCarsSearchResultFragment`
- **訂票頁**: `GatherCarsBookingFragment`
- **ViewModel**: `GathercarsViewModel`
- **支援功能**:
  - 取車/還車地點選擇
  - 取車/還車日期與時間（支援時間格式 HHmm）
  - 駕駛年齡設定（`TransAgeData`）
  - 篩選條件
  - 登入驗證
  - 保存取車/還車地點資訊

### 機票類 (Airplane)

#### 13. ZZIMAIR - 韓國機票
- **服務名稱**: `zzimair`
- **對應 Tab**: AIRPLANE
- **TransHomeArgument**: `TransHomeArgument.ZzimAir` / `TransHomeArgument.ZzimAirAddCar`
- **子頁面**: `TransHomeZzimairFragment` / `TransHomeZzimairAddCarFragment`
- **搜尋結果頁**: `ZzimAirSearchResultFragmentV2`
- **訂票頁**: `ZzimAirBookingFragmentV2`
- **ViewModel**: `ZzimAirViewModel`
- **區域**: 韓國 (`KOREA_SERVICE_COUNTRY_KEY`)
- **說明**: 韓國機票預訂服務，可選擇加購租車
- **支援功能**:
  - 出發地/抵達機場選擇
  - 出發/回程日期選擇
  - 票種選擇:
    - `TripType.ONE_WAY` - 單程
    - `TripType.ROUND_TRIP` - 來回
  - 旅客人數設定:
    - `ZzimAirTicket.Adult` - 成人
    - `ZzimAirTicket.Child` - 兒童
    - `ZzimAirTicket.Infant` - 嬰幼兒
  - 艙等選擇 (`cabinClass`):
    - `All` - 全部（預設）
    - `Discount` - 折扣
    - `Normal` - 經濟
    - `Business` - 商務
  - 篩選條件
  - 登入驗證
  - 加購租車選項

#### 14. UNIAIRHOLIDAYS - 立榮假期
- **服務名稱**: `uniairholidays`
- **對應 Tab**: AIRPLANE
- **TransHomeArgument**: `TransHomeArgument.UniairHolidays`
- **子頁面**: `TransHomeUniairholidaysFragment`
- **ViewModel**: `UniairholidaysViewModel`
- **說明**: 立榮假期套裝行程

### 郵輪類 (Cruises)

#### 15-17. 郵輪服務
- **CRUISES** (`cruises`) - 一般郵輪
- **ROYAL_CRUISES** (`royalcruises`) - 皇家郵輪
- **CRUQO_CRUISES** (`cruqo`) - Cruqo 郵輪

統一使用:
- **對應 Tab**: CRUISES
- **TransHomeArgument**: `TransHomeArgument.Cruises`
- **子頁面**: `TransHomeCruisesFragment`
- **搜尋結果頁**: `CruisesSearchProductListFragment`
- **ViewModel**: `TransHomeCruisesViewModel`
- **說明**: 郵輪旅遊預訂服務
- **支援功能**:
  - 出發港口選擇（支援多選）
  - 抵達港口選擇（支援多選）
  - 出發/結束日期範圍選擇（預設 2 年）
  - 船舶代碼（shipCode）
  - 篩選條件
  - 使用 Area List API 取得港口資訊

### 機場接送類 (Airport Transfer) - 點對點服務

#### 18. PICK_UP - 機場接機
- **服務名稱**: `pick_up`
- **服務類型**: `AIRPORT_PICKUP_TYPE = "A-PL-01"`
- **對應 Tab**: AIRPORT_TRANSFER
- **TransHomeArgument**: `TransHomeArgument.PickUp`
- **子頁面**: `TransPickupFragment`
- **搜尋動作**:
  - `SEARCH_PICKUP_AIRPORT_ACTION = "SLA-01"` - 按機場搜尋
  - `SEARCH_PICKUP_FLIGHT_ACTION = "SLA-02"` - 按航班搜尋
- **搜尋類型**:
  - `VALUE_ARRIVE_AIRPORT` - 按機場抵達
  - `VALUE_ARRIVE_FLIGHT` - 按航班號抵達
- **ViewModel**: `TransHomePickupViewModel`
- **說明**: 機場接機服務，從機場接送到目的地

#### 19. DROP_OFF - 機場送機
- **服務名稱**: `drop_off`
- **服務類型**: `AIRPORT_DROPOFF_TYPE = "A-PL-02"`
- **對應 Tab**: AIRPORT_TRANSFER
- **TransHomeArgument**: `TransHomeArgument.DropOff`
- **子頁面**: `TransDropoffFragment`
- **搜尋動作**: `SEARCH_DROPOFF_AIRPORT_ACTION = "SLA-03"`
- **ViewModel**: `TransHomeDropoffViewModel`
- **說明**: 機場送機服務，從目的地送到機場

#### 機場接送共用元件

**車型搜尋與選擇**:
- `AirportModelListFragment` - 車型列表頁
- `CarModelSearchParams` - 搜尋參數
  - `type` - 服務類型（接機/送機）
  - `airportType` - 機場/航班類型
  - `airport` - 機場資訊
  - `dateTime` / `dateInfo` - 日期時間
  - `flightItem` - 航班資訊
  - `selectedLocation` - 目的地
  - `personNum` - 人數（成人+兒童）

**填寫訂單**:
- `AirportFillOrderScreenFragment` - 訂單填寫頁
- `AirportFillDetailActivity` - 訂單詳情頁
- `AirportFillOrderScreenViewModel` - 訂單 ViewModel

**輔助頁面**:
- `AirportSearchFragment` - 機場/航班搜尋
- `AirportFlightNumberFragment` - 航班號輸入
- `AirportArrivalFragment` - 抵達資訊
- `SelectAirportBottomSheetFragment` - 機場選擇底部彈窗
- `SelectLocationBottomSheetFragment` - 地點選擇底部彈窗
- `SelectPersonNumFragment` - 人數選擇對話框
- `CarServiceDetailFragment` - 車輛服務詳情
- `CarServiceVehInfoBottomSheetFragment` - 車輛資訊底部彈窗
- `CarServicePolicyBottomSheetFragment` - 政策資訊底部彈窗

**資料常數** (`AirportConstant`):
- 時間單位: `DAY_TU01` (天), `HOUR_TU02` (小時), `MINUTE_TU03` (分鐘)
- 年齡單位: `YEAR_AU02` (歲), `MONTH_AU01` (月)
- 重新安排類型: `REARRANGE_TYPE_SUPPLIER`, `REARRANGE_TYPE_KKDAY`
- 取消政策類型:
  - `CANCEL_TYPE_NON_REFUNDABLE` - 不可取消
  - `CANCEL_TYPE_FREE_CANCEL` - 免費取消
  - `CANCEL_TYPE_CONDITIONAL` - 有條件取消
- 兒童座椅類型:
  - `SEAT_TYPE_REAR` - 後向座椅
  - `SEAT_TYPE_FORWARD` - 前向座椅
  - `SEAT_TYPE_FORWARD_HEIGHT` - 前向增高座椅
  - `SEAT_TYPE_DEFAULT` - 預設座椅
- 詳情標籤類型:
  - `TYPE_VEH_INFO` - 車輛資訊
  - `TYPE_ADD_SERVICE` - 附加服務
  - `TYPE_CUS_POLICY` - 政策
  - `TYPE_COMMENT` - 評論
- 政策類型:
  - `TYPE_CANCEL_POLICY` - 取消政策
  - `TYPE_WAITING_TIME_POLICY` - 等候時間政策
  - `TYPE_MULTI_STOP_POLICY` - 多點下車政策
  - `TYPE_ALL_POLICIES` - 所有政策
- Facets 篩選項目:
  - `FACET_RATING` - 評分
  - `FACET_CAR_MODEL` - 車型
  - `FACET_SERVICE_PROVIDER` - 服務供應商
  - `FACET_PICK_UP_LOCATION` - 上車地點
  - `FACET_EXTRA_SERVICE` - 額外服務
  - `FACET_POLICY` - 政策
  - `FACET_FEE` - 費用
  - `FACET_MKT_CHILD_SEAT_RULE` - 兒童座椅規則
  - `FACET_BASE_PRICE` - 基本價格

**追蹤埋點** (`TransKtmTrackerConstants`):
- `AIRPORT_TRANSFER` - 機場接送
- `PICK_UP` - 接機
- `DROP_OFF` - 送機
- `ARR_AIRPORT` - 抵達機場
- `FLIGHT_NUM` - 航班號

**訂單顯示**:
- `TransportationAirportOrderItem` - 訂單列表項目 (Compose)
- `AirportOrderDetailDelegate` - 訂單詳情委派

#### 20. COMMON
- **服務名稱**: 空字串
- **說明**: 通用類型，非交通服務

## 架構層級

### 1. 入口層 - TransHomeActivity

**職責**:
- 整個交通首頁的統一入口
- 處理 QueueIt 排隊機制（`QueueWaitingRoom.APP_p2phomepage`）
- 管理頁面跳轉與路由
- 處理 DeepLink 與 ProductId 轉換
- 處理登入驗證回調

**核心流程**:
```kotlin
onCreate() 
  → initObservers() // 初始化各服務 ViewModel 觀察者
  → QueueIt 檢查
  → onQueuePassed() 
  → launchHomeOrSearchResultPage()
```

**啟動方式**:
```kotlin
TransHomeActivity.launch(
    context = context,
    isNeedGoHomePage = false,
    transHomeArgument = TransHomeArgument.Thsrtw("")
)
```

**路由註解**:
```kotlin
@Router(KRouterConst.PAGE_TRANS_HOME_PAGE)
```

**支援參數**:
- `ARG_TRANS_HOME_ARGUMENT` - TransHomeArgument 物件
- `NEED_GO_HOME_PAGE` - 是否回到首頁
- `KEY_PRODUCT_ID` - ProductId（透過 RouterParam 注入）

### 2. 主頁面層 - TransHomeMainFragment

**職責**:
- 顯示交通服務分類 Tab
- 載入對應的服務子頁面
- 管理 Tab 切換邏輯

**Tab 清單** (`TransHomeMainTab`):
1. **RAILWAY** (鐵路) - `ic_train_line`
2. **BUS** (巴士) - `ic_bus_line`
3. **CAR_RENTAL** (租車) - `ic_car_line`
4. **AIRPLANE** (機票) - `ic_airplane_line`
5. **CRUISES** (郵輪) - `ic_cruise_line`
6. **AIRPORT_TRANSFER** (機場接送) - `ic_airporttransfer_line`

**Fragment 結構**:
```
TransHomeMainFragment
├── ViewPager2 (顯示各 Tab 內容)
│   ├── TransHomeThsrtwFragment (台灣高鐵)
│   ├── TransHomeRailEuropeFragment (歐洲鐵路)
│   ├── TransHomeJRFragment (日本鐵路)
│   ├── TransHomeKosokubusFragment (日本巴士)
│   ├── TransHomeVexerebusFragment (越南巴士)
│   ├── TransHomeCnhkbusFragment (中港巴士)
│   ├── TransHomeGatherCarsFragment (全球租車)
│   ├── TransHomeZzimcarFragment (韓國租車)
│   ├── TransHomeZzimairFragment (韓國機票)
│   ├── TransHomeZzimairAddCarFragment (韓國機票+租車)
│   ├── TransHomeUniairholidaysFragment (立榮假期)
│   ├── TransHomeCruisesFragment (郵輪)
│   ├── TransPickupFragment (機場接機)
│   └── TransDropoffFragment (機場送機)
└── TabLayout (顯示分類 Tab)
```

### 3. 服務子頁面層

每個服務都有獨立的 Fragment 與 ViewModel，負責:
- 顯示搜尋表單
- 處理使用者輸入
- 呼叫搜尋 API
- 導航到搜尋結果頁

### 4. 搜尋結果層

顯示搜尋結果列表，支援:
- 列表展示
- 篩選條件
- 排序
- 點擊進入訂票頁

### 5. 訂票層

處理訂票流程:
- 填寫旅客資訊
- 選擇附加服務
- 確認訂單
- 進入支付流程

## URL DeepLink 處理

### URL 格式範例

**日本鐵路**:
```
https://m.kkday.com/zh-tw/transportation/japan-rail?dep_code=TYO&arr_code=OSA&dep_date=20250201&filter=jreast,shinkansen
```

**日本巴士**:
```
https://m.kkday.com/zh-tw/transportation/japan?dep_code=TYO&dep_type=city&arr_code=OSA&arr_type=city&dep_date=20250201&filter=wifi
```

**中港巴士**:
```
https://m.kkday.com/zh-tw/transportation/greater-bay-area?dep_code=HKG&arr_code=MAC&dep_date=20250201
```

**韓國機票**:
```
https://m.kkday.com/zh-tw/transportation/flights/korea?dep_code=ICN&arr_code=GMP&dep_date=20250201&arr_date=20250205&ticket_type=round_trip&adult=2&child=1&infant=0&cabin_class=All&filter=morning
```

**全球租車**:
```
https://m.kkday.com/zh-tw/car-rentals?dep_code=TYO&arr_code=TYO&dep_date=20250201&arr_date=20250203&dep_time=1000&arr_time=1800&driver_age=30&filter=automatic
```

**韓國租車**:
```
https://m.kkday.com/zh-tw/car-rentals/korea?dep_code=ICN&dep_date=20250201&arr_date=20250203&dep_time=1000&arr_time=1800&filter=suv
```

**郵輪**:
```
https://m.kkday.com/zh-tw/cruises?dep_code=SGN,HKG&arr_code=NHA,BKK&dep_date=20250201&arr_date=20271231&ship_code=royal&filter=luxury
```

### URL 參數說明

| 參數名稱 | 說明 | 適用服務 | 範例 |
|---------|------|---------|------|
| `dep_code` | 出發地代碼 | 全部 | `TYO`, `HKG`, `ICN` |
| `arr_code` | 抵達地代碼 | 大部分 | `OSA`, `MAC`, `GMP` |
| `dep_type` | 出發地類型 | 巴士 | `city`, `station` |
| `arr_type` | 抵達地類型 | 巴士 | `city`, `station` |
| `dep_date` | 出發日期 | 全部 | `20250201` (yyyyMMdd) |
| `arr_date` | 回程/結束日期 | 部分 | `20250205` |
| `dep_time` | 出發時間 | 租車 | `1000` (HHmm) |
| `arr_time` | 還車時間 | 租車 | `1800` (HHmm) |
| `ticket_type` | 票種類型 | 機票 | `one_way`, `round_trip` |
| `adult` | 成人數 | 機票 | `2` |
| `child` | 兒童數 | 機票 | `1` |
| `infant` | 嬰兒數 | 機票 | `0` |
| `cabin_class` | 艙等 | 機票 | `All`, `Business` |
| `driver_age` | 駕駛年齡 | 租車 | `30` |
| `ship_code` | 船舶代碼 | 郵輪 | `royal` |
| `filter` | 篩選條件 | 全部 | `wifi,breakfast` (逗號分隔) |

### DeepLink 處理流程

1. `TransHomeActivity.onCreate()` 接收 Intent
2. 解析 `TransHomeArgument` 從 URL
3. 判斷 `isGoToResultPage`:
   - `false`: 顯示 `TransHomeMainFragment` (首頁)
   - `true`: 直接跳轉到對應搜尋結果頁
4. 若為搜尋結果頁:
   - 解析 URL 參數（使用 `Uri.getQueryMap()`）
   - 呼叫對應 API 取得地點資訊
   - 設定 ViewModel 狀態
   - 導航到搜尋結果 Fragment

## 登入驗證流程

部分服務需要登入才能訂票:

1. 使用者點擊「立即預訂」
2. ViewModel 檢查登入狀態
3. 若未登入，發送 `NeedLogin` 事件
4. Activity 呼叫 `needLogin(resultLauncher)`
5. 啟動登入頁面
6. 登入成功後透過 `ActivityResultLauncher` 回調
7. 自動進入訂票頁面

**支援登入驗證的服務**:
- 日本巴士 (KOSOKUBUS)
- 中港巴士 (CNHKBUS)
- 韓國機票 (ZZIMAIR)
- 韓國租車 (ZZIMCAR)
- 全球租車 (GATHER_CAR 系列)
- 日本鐵路 (JR_RAIL)
- 機場接送 (PICK_UP, DROP_OFF)

## 支付流程

支付流程統一透過 `OrderFormFillingActivity` 處理:

1. 訂票頁確認訂單
2. 呼叫建立訂單 API
3. 取得 `TransBIDLData`
4. 啟動 `OrderFormFillingActivity`
5. 進入支付流程
6. 支付完成後跳轉到訂單詳情

詳見 `TransWebActivityGuidelines.md` 的支付流程說明。

## 資料層架構

### Repository
- `TransportationRepository` - 交通服務共用 Repository
- `TransApiRepository` - 交通 API Repository

### API Service
- 各服務 API 定義在 `:data:networking:api` 模組
- 使用 Retrofit + Coroutines Flow

### Model
- `LocationItem` - 地點資訊
- `LocationItems` - 地點列表
- `CountryCityInfoData` - 國家城市資訊
- `TransBIDLData` - 交通訂單資料
- `RouteItem` - 路線資訊
- `CarModelSearchParams` - 機場接送搜尋參數
- `AirportItem` - 機場資訊
- `FlightScheduleItem` - 航班資訊
- `ZzimAirRequirementInfo` - 機票需求資訊
- `BusListRequirementInfo` - 巴士需求資訊

### ViewModel 狀態管理

大部分 ViewModel 使用 `StateFlow` 或 `MutableStateFlow`:
```kotlin
data class ViewState(
    val isLoading: Boolean = false,
    val error: String? = null,
    // ... 其他狀態
)
```

部分服務使用 `ViewIntent` 模式處理使用者操作。

## 特殊功能

### QueueIt 排隊機制
當流量過大時，使用 QueueIt 讓使用者排隊進入頁面:
- `QueueWaitingRoom.APP_p2phomepage`
- 透過 `QueueItActivityDelegate` 介面實作
- 排隊通過後執行 `onQueuePassed()`

### 歷史搜尋記錄
機場接送服務支援歷史搜尋記錄:
- 接機: 讀取最近一筆 `type == AIRPORT_PICKUP_TYPE` 記錄
- 送機: 讀取最近一筆 `type == AIRPORT_DROPOFF_TYPE` 記錄
- 自動填充搜尋條件

### 多點下車 (Multi-Stop)
機場接機支援多點下車政策:
- 顯示額外費用
- 顯示政策說明
- 在訂單中標註

### 兒童座椅
機場接送服務支援兒童座椅預訂:
- 後向座椅 (0-12個月)
- 前向座椅 (1-4歲)
- 前向增高座椅 (4-12歲)
- 預設座椅

### 等候時間政策
機場接送服務的等候時間規則:
- 免費等候時間
- 超時費用說明
- 特殊情況處理

## 錯誤處理

### 常見錯誤碼

**機場接送專用**:
- `KVT-API-0077` - 無符合人數的車型商品
- `KVT-API-0127` - 超出兒童座椅容量
- `KVT-API-0134` - 搜尋服務區域資料為空
- `KVT-API-0135` - 至少提前 1 小時接送服務

**一般錯誤**:
- `TRS-431` - 特定交通服務錯誤
- 透過 `metadata.status` 與 `metadata.desc` 取得錯誤資訊

### 錯誤顯示
- 使用 `KKToast.show()` 顯示錯誤訊息
- 部分錯誤顯示在頁面上（如機場服務暫停）

## 測試與開發注意事項

1. **模組依賴**: 新交通功能逐步從 `:app` 模組遷移到 `:libs:transportation` 模組
2. **Koin DI**: 所有 ViewModel 與 Repository 使用 Koin 注入
3. **Compose 混用**: 新頁面優先使用 Jetpack Compose，與既有 View 系統共存
4. **追蹤埋點**: 所有頁面需實作完整的 KTM 追蹤埋點
5. **多語系**: 所有文字需支援多語系（`strings.xml`）
6. **圖片資源**: 使用設計系統統一的 Icon 與圖片資源

## 相關文件

- [TransWeb 架構指南](./TransWebActivityGuidelines.md) - WebView 與支付流程詳解
- [新交通首頁](./README.md) - 基本介紹與對照表
- [商品頁分流](../product/product_detail.md) - 商品頁進入邏輯
- [訂單追蹤流程](../booking/booking_tracking_flow.md) - 訂單追蹤埋點

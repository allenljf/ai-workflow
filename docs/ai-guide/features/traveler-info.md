# 旅遊資料填寫頁 技術文件

> 自動產生 | 最後更新：2026-03-20

---

## 概述

- **所在 Module**：`:app`
- **UI 入口**：`ScheduleFormActivity.kt`
- **功能描述**：結帳流程中的旅遊資料填寫頁，使用者需依商品需求填寫旅客個人資料（護照、出生日期、國籍、身高體重等），並支援從常用旅客清單快速帶入資料。頁面採 MVP + Reductor 架構，新版（實驗版）旅客區塊已遷移至 Compose。

---

## 檔案清單

```
UI（使用者介面入口）
 ├─ ScheduleFormActivity.kt                        → app/.../view/product/form/schedule/
 ├─ ScheduleFormAdapter.kt                         → app/.../view/product/form/schedule/
 ├─ ScheduleFormViewUpdateHelper.kt                → app/.../view/product/form/schedule/
 └─ 旅客區塊（Compose，V2 新版）
     ├─ ScheduleFormTravelerInfoItemScreenV2.kt    → .../traveler/item/v2/
     ├─ ScheduleFormTravelerInfoItemScreenV2WithPicker.kt → .../traveler/item/v2/
     ├─ ScheduleFormTravelerInfosDelegateV2.kt     → .../traveler/item/v2/
     ├─ TravelerInfoDialog.kt                      → .../traveler/item/v2/dialog/
     ├─ TravelerInfoDialogContent.kt               → .../traveler/item/v2/compose/
     ├─ TravelerInfoGrid.kt                        → .../traveler/item/v2/compose/
     ├─ TravelerSectionItem.kt                     → .../traveler/item/v2/compose/
     ├─ TravelerSectionTitle.kt                    → .../traveler/item/v2/compose/
     ├─ AddTravelerButton.kt                       → .../traveler/item/v2/compose/
     └─ SelectTravelerListBottomSheet.kt           → .../traveler/item/v2/compose/
 └─ 旅客區塊（舊版）
     ├─ ScheduleFormTravelerInfoItemScreen.kt      → .../traveler/item/
     ├─ ScheduleFormTravelerInfoItemDelegate.kt    → .../traveler/item/
     └─ TravelerInfoItemViewInfoCreator.kt         → .../traveler/item/
 └─ 其他表單區塊 Delegate
     ├─ ScheduleFormBackupDelegate.kt              → .../schedule/backup/
     ├─ ScheduleFormLanguageDelegate.kt            → .../schedule/language/
     ├─ ScheduleFormFlightDelegate.kt              → .../schedule/flight/
     ├─ ScheduleFormPickupDelegate.kt              → .../schedule/pickup/
     ├─ ScheduleFormCarRentalDelegate.kt           → .../schedule/car/
     ├─ ScheduleFormPassengerDelegate.kt           → .../schedule/passenger/
     ├─ ScheduleFormShippingDelegate.kt            → .../schedule/shipping/
     ├─ ScheduleFormOtherDelegate.kt               → .../schedule/other/
     ├─ ScheduleFormNoteDelegate.kt                → .../schedule/note/
     ├─ ScheduleFormEmergencyContactDelegate.kt    → .../schedule/contact/
     ├─ ScheduleFormEmergencyContactDelegateV2.kt  → .../schedule/contact/v2/
     └─ ScheduleFormSubscriptionDelegate.kt        → .../schedule/subscription/

Presenter（MVP 表現層）
 └─ ScheduleFormPresenter.kt                       → app/.../view/product/form/schedule/

ViewModel（追蹤事件專用）
 └─ ScheduleFormViewModel.kt                       → app/.../view/product/form/schedule/

State 管理
 ├─ ScheduleStateHelper.kt                         → app/.../view/product/form/schedule/
 ├─ TravelerStateHelper.kt                         → .../schedule/traveler/
 ├─ BackupStateHelper.kt                           → .../schedule/backup/
 ├─ LanguageStateHelper.kt                         → .../schedule/language/
 ├─ FlightStateHelper.kt                           → .../schedule/flight/
 ├─ PickupStateHelper.kt                           → .../schedule/pickup/
 ├─ CarRentalStateHelper.kt                        → .../schedule/car/
 ├─ PassengerStateHelper.kt                        → .../schedule/passenger/
 ├─ ShippingStateHelper.kt                         → .../schedule/shipping/
 ├─ OtherStateHelper.kt                            → .../schedule/other/
 ├─ EmergencyContactStateHelper.kt                 → .../schedule/contact/
 ├─ SubscriptionStateHelper.kt                     → .../schedule/subscription/
 └─ NoteStateHelper.kt                             → .../schedule/note/

Reductor（全域狀態 Action）
 └─ ScheduleFormActions.kt                         → app/.../reducer/order/

Data Model
 ├─ TravelerData.kt                                → libs/base/.../model/product/
 ├─ ScheduleState.kt                               → libs/base/.../model/product/
 ├─ BookingData.kt                                 → libs/base/.../model/
 ├─ BookingFormDataConverter.kt                     → app/.../view/product/form/schedule/
 ├─ FriendTravelersData.kt                         → app/.../view/product/form/schedule/
 └─ TravelersCollection.kt                         → .../schedule/common/

Utility
 ├─ ScheduleFormUtils.kt                           → app/.../view/product/form/schedule/
 ├─ ScheduleFormUtilsForCompose.kt                 → app/.../view/product/form/schedule/
 ├─ ScheduleFormTravelerUtil.kt                    → .../schedule/common/util/
 ├─ ScheduleFormNameUtil.kt                        → .../schedule/common/util/
 ├─ TravelerRequirementUtil.kt                     → app/.../util/
 └─ TravelerDataExt.kt                             → app/.../view/product/form/
```

---

## 資料流

### 主流程：頁面載入與表單資料初始化

```
UI（ScheduleFormActivity）
 │  onCreate() → initView()
 │  呼叫：scheduleFormPresenter.attachView(this)
 │  呼叫：scheduleFormPresenter.viewReady(cartProductId, packageId)
 ↓
Presenter（ScheduleFormPresenter）
 │  store.dispatch(scheduleFormActions.viewReady(...))
 ↓
Reductor Store（AppState）
 │  ScheduleFormActions.VIEW_READY → 觸發 Middleware
 │  取得 BookingData、Member、FriendLites 等資料
 │  更新 AppState 中對應欄位
 ↓
Presenter（register() 中的 RxJava 訂閱）
 │  combineLatest 9 個 Observable → 組合 UpdateDataBundle
 │  filter：travelerListReady && !isInterceptMemberUpdate
 ↓
UI（ScheduleFormMvpView.updateData()）
 │  adapter.updateData(languageType, bookingData, ...)
 ↓
Adapter（ScheduleFormAdapter）
 │  委派給 ScheduleFormViewUpdateHelper
 │  → ScheduleStateHelper 計算各區塊 ViewInfo
 │  → 各 Delegate 渲染對應表單區塊
```

### 送出流程：使用者點擊確認按鈕

```
UI（ScheduleFormActivity）
 │  sendScheduleFormData()
 │  adapter.checkRequiredFieldsNotFilled() → 驗證所有必填欄位
 │  若有錯誤 → 滾動到第一個錯誤欄位 + 顯示錯誤訊息
 │  若無錯誤 → scheduleFormPresenter.clickCompleteButton(state, ...)
 ↓
Presenter（ScheduleFormPresenter）
 │  store.dispatch(scheduleFormActions.clickCompleteButton(state, ...))
 ↓
Reductor Store
 │  將 ScheduleState 寫回 OrderSpecificationData
 │  回到結帳填寫頁（OrderFormFillingActivity）使用
 ↓
UI
 │  finish() → 返回上一頁
```

### 常用旅客選取流程（新版 V2）

```
UI（TravelerSectionItem / SelectTravelerListBottomSheet）
 │  使用者選取常用旅客 Chip
 │  呼叫：updateSelectedFriendIdsBySpecCustomToken(specCustomToken, friendId, ...)
 ↓
Activity → Presenter
 │  store.dispatch(scheduleFormActions.updateSelectedFriendIdsBySpecCustomToken(...))
 ↓
Reductor Store → Middleware
 │  取得 FriendData → 組合 FriendTravelersData
 │  更新 userSelectedFriendIdsBySpecCustomToken
 ↓
Presenter（register() 中的訂閱）
 │  mvpView.updateFriendTravelersState(friendTravelersData, ...)
 ↓
Adapter → ScheduleStateHelper → TravelerStateHelper
 │  updateTravelersBySpecCustomTokenFromFriendData()
 │  將旅客資料同步至 TravelerState.travelers
```

---

## 逐層說明

### UI 層
- `ScheduleFormActivity` 為 MVP 的 View 端，實作 `ScheduleFormMvpView` 介面
- 使用 `RecyclerView` + `ListDelegationAdapter` 渲染表單，各區塊由獨立 `Delegate` 負責
- 新版（實驗版）旅客區塊透過 Compose 渲染：`ScheduleFormTravelerInfoItemScreenV2`、`TravelerInfoDialog`（BottomSheet）
- 確認按鈕在新版使用 Compose `KKButton`，鍵盤彈出時自動隱藏（`AnimatedVisibility`）
- 透過 `ComposeView` overlay 機制顯示全螢幕 Compose 內容

### Presenter 層
- `ScheduleFormPresenter` 繼承 `RxBasePresenter`，透過 Reductor `Store<AppState>` 管理狀態
- `register()` 中使用 `combineLatest` 訂閱 9 個 AppState 子狀態，組合後推送至 View
- 所有使用者操作透過 `store.dispatch(scheduleFormActions.xxx())` 發送 Action

### ViewModel 層
- `ScheduleFormViewModel` 僅負責追蹤事件（KKTracker），不參與表單業務邏輯
- 追蹤事件包含：新增旅客 CTA、旅客卡片曝光、旅客資料 BottomSheet 瀏覽、旅客 Chip 點擊

### State 管理層
- `ScheduleStateHelper` 為核心狀態管理器，持有 13 個子 StateHelper（backup、language、flight、pickup、carRental、passenger、shipping、other、traveler、emergencyContact、subscription、note）
- 各子 StateHelper 負責對應區塊的狀態維護、必填驗證、資料取得
- `TravelerStateHelper` 最為複雜，管理旅客資料列表、常用旅客選取映射（`selectedFriendIdsBySpecCustomToken`）、年齡驗證、票種分組等

### Reductor 層
- `ScheduleFormActions` 定義所有 Action（viewReady、selectFriend、clickCompleteButton 等）
- Middleware 處理副作用：API 呼叫取得 FriendData、Member 資料、建立/更新常用旅客等
- 狀態儲存在 `AppState` 中，透過 `Observable<AppState>` 推送變更

---

## View 方法清單

| 方法 | 說明 |
|------|------|
| `onCreate()` | 呼叫 `initView()` 初始化頁面 |
| `initView()` | 設定 layout、attach Presenter、初始化 toolbar/按鈕/RecyclerView |
| `initDoneButton()` | 初始化確認按鈕，新版使用 Compose KKButton，舊版使用 TextView |
| `initRecyclerView()` | 設定 Adapter、LayoutManager、ItemDecoration |
| `sendScheduleFormData()` | 驗證必填欄位，無錯誤則送出資料並 finish |
| `checkScheduleExperimentCheckNameCompare()` | 新版平鋪場景下檢查是否需比較姓名以區分更新/新增旅客 |
| `onClickSelectedTravelerButton()` | 開啟常用旅客選擇 Picker |
| `onClickAddOrUpdateTraveler()` | 新版旅規：觸發新增或更新旅客資料 |
| `onClickCleanTravelerButton()` | 清除指定旅客資料 |
| `onClickSelectedTravelerCountButtonListener()` | 開啟旅客人數選擇 BottomSheet |
| `onClickEmergencyContactAddOrUpdateTravelerButton()` | 觸發緊急聯絡人新增或更新 |
| `showComposeOverlay()` / `hideComposeOverlay()` | 顯示/隱藏全螢幕 Compose 覆蓋層 |
| `scrollByKeyboardHeight()` | 鍵盤彈出時捲動至焦點欄位 |
| `onBackPressed()` | 顯示放棄填寫確認 Dialog |
| `onSaveInstanceState()` / `onRestoreInstanceState()` | 儲存/恢復 ScheduleState |
| `updateData()` | MVP View 回調：接收組合後的表單資料並更新 Adapter |
| `updateFriendLites()` | MVP View 回調：更新常用旅客清單 |
| `updateSelectedFriend()` | MVP View 回調：更新選取的旅客資料 |
| `updateFriendTravelersState()` | MVP View 回調：更新新版旅客映射狀態 |
| `showErrorMessage()` | MVP View 回調：顯示/隱藏錯誤 Snackbar |

---

## ViewModel 方法清單

| 方法 | 說明 |
|------|------|
| `trackAddTravelersCTA(position)` | 追蹤「新增旅客」按鈕點擊事件，position 區分初次新增/再新增 |
| `trackImpressionTravelerCardMissDataErrorMessage()` | 追蹤旅客卡片資料缺失錯誤訊息曝光 |
| `trackClickBookingDetailFormPgTravelerChip(travelerNum, position)` | 追蹤旅客 Chip 點擊事件 |
| `trackImpressionTravelerCard(isContactCard, isComplete, isDefault)` | 追蹤旅客/聯絡人卡片曝光（每類僅曝光一次） |
| `trackViewTravelerInfoBottomSheet(isFromMemberContact, isNewAddTraveler)` | 追蹤旅客資料 BottomSheet 瀏覽，區分 Buyer/FreqTraveler/New |
| `trackViewContactInfoBottomSheet()` | 追蹤聯絡資料 BottomSheet 瀏覽 |

---

## 業務邏輯摘要

- **表單區塊動態組成**：依據 `BookingData.bookingInfo` 中各 Requirement 是否有 `fieldsInfo` 決定顯示哪些區塊（備選日期、語言、航班、接送、租車、乘客人數、寄送、其他、旅客資料、緊急聯絡人、訂閱、備註）
- **旅客人數計算**：依 `OrderSpecificationData.skuList` 中各 SKU 的 `countInfo` 計算需填寫旅客數；`unitMax > 1` 時顯示人數選擇器
- **代表人模式**：`TravelerRequirementData.type == "01"` 時僅需填寫一位代表人資料
- **常用旅客選取（新版 V2）**：以 `specCustomToken`（票種 SKU ID 或自定義 key）為分組依據，管理各分組的旅客-常用旅客 ID 映射（`selectedFriendIdsBySpecCustomToken`）
- **姓名比較邏輯**：新版平鋪場景下（`NameCompareData.isNeedCompareName == true`），送出時比較使用者填寫的姓名與原始旅客資料，判定為「更新會員資料」或「新增常用旅客」
- **台灣商品特殊處理**：商品地區僅限台灣且旅客國籍為 TW 時，護照欄位自動填入 `-` 佔位值，護照到期日填入 `0001-01-01`，跳過護照相關驗證
- **生日年齡驗證**：若 `birthdayRequirement.isRequired == true` 且商品有年齡範圍限制（`hasAgeRange`），驗證每位旅客的出生日期是否符合對應 SKU 的年齡區間
- **必填欄位驗證**：送出前由 `ScheduleStateHelper` 逐區塊檢查所有必填欄位，收集 `ErrorInfo` 清單；有錯誤時滾動至第一個錯誤位置並顯示 Snackbar
- **狀態持久化**：`ScheduleState` 透過 Reductor `AppState` 保存在 `OrderSpecificationData` 中，跨頁面共享；`onSaveInstanceState` 亦有 JSON 序列化備份
- **錯誤處理**：統一使用 `ErrorSnackbar` 顯示錯誤，可手動關閉
- **新版/舊版共存**：透過 `isScheduleExperimental()` 判斷走新版（Compose V2 Delegate）或舊版（Views Delegate），實驗切全後舊版可移除

---

## 已知技術債

- **MVP + Reductor 架構**：此頁面使用 Presenter + Reductor Store，未採用 MVVM + StateFlow 的現代架構。`ScheduleFormViewModel` 僅用於追蹤事件，業務邏輯全在 Presenter
- **ScheduleStateHelper 過度膨脹**：單一類別管理 13 個子 StateHelper，責任過重，難以單元測試
- **新舊版本並存**：旅客區塊有 V1（Views）和 V2（Compose）兩套 Delegate 並行，增加維護成本
- **無 UseCase 層**：表單資料處理直接在 Presenter → Reductor Middleware 中完成，未抽取 Domain UseCase
- **無 Repository 層**：資料取得透過 Reductor Middleware 直接呼叫，未經過 Repository 抽象
- **Adapter Delegate 回調過多**：`ScheduleFormAdapter` 建構子接收超過 15 個回調函式，耦合度高

## 相關筆記
- [01-architecture](../01-architecture.md)
- [02-modules](../02-modules.md)
- [03-ui-patterns](../03-ui-patterns.md)
- [05-networking](../05-networking.md)
- [06-data-layer](../06-data-layer.md)
- [07-concurrency](../07-concurrency.md)
- [checkout](checkout.md)
- [order-detail-compose](order-detail-compose.md)
- [sku-activity-shell](sku-activity-shell.md)

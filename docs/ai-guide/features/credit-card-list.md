# 信用卡列表頁 技術文件

> 自動產生 | 最後更新：2026-06-26

---

## 概述

- **所在 Module**：`:feature:creditcard_list`（路徑：`libs/feature/creditcard_list/`）
- **UI 入口**：`CreditCardListActivity.kt`（Compose）
- **功能描述**：信用卡管理列表頁面，讓使用者查看、新增、刪除已儲存的信用卡

---

## 檔案清單

```
UI（使用者介面入口）
 ├─ CreditCardListActivity.kt         → libs/feature/creditcard_list/.../creditcardlist/
 ├─ CreditCardScreen（Composable）     → 同上（定義在 CreditCardListActivity.kt 內）
 └─ CreditCardTopBar（Composable）     → 同上

UI 子元件（View）
 ├─ CreditCardListView.kt             → libs/feature/creditcard_list/.../view/
 ├─ AddCreditCardBottomSheet.kt        → libs/feature/creditcard_list/.../view/
 ├─ EmptyCreditCardView.kt            → libs/feature/creditcard_list/.../view/
 ├─ BindCreditCardUnavailableView.kt   → libs/feature/creditcard_list/.../view/
 ├─ DeleteConfirmationDialog.kt        → libs/feature/creditcard_list/.../view/
 ├─ DeleteCardErrorDialog.kt           → libs/feature/creditcard_list/.../view/
 └─ VerificationFailedDialog.kt        → libs/feature/creditcard_list/.../view/

Contract（模組間契約）
 ├─ CreditCardFormContract.kt          → libs/feature/creditcard_list/.../contract/
 └─ CreditCardRedirectHandler.kt       → libs/feature/creditcard_list/.../contract/

Router（路由）
 ├─ CreditCardListRouter.kt（介面）    → libs/routing/.../
 └─ CreditCardListRouterImpl.kt        → libs/feature/creditcard_list/.../route/

ViewModel（UI 狀態管理）
 └─ CreditCardViewModel.kt            → libs/feature/creditcard_list/.../creditcardlist/

Domain（業務邏輯 UseCase）
 ├─ GetCreditCardListUseCase.kt        → domain/usecase/.../creditcard/
 ├─ DeleteCreditCardUseCase.kt         → domain/usecase/.../creditcard/
 └─ SaveCreditCardUseCase.kt           → domain/usecase/.../creditcard/

Data（資料層介面與實作）
 ├─ CreditCardRepository.kt（介面+實作）→ data/repository/.../creditcardlist/
 └─ CreditCardRepositoryImpl（同檔）    → 同上

Network（API 定義）
 └─ CreditCardApiService.kt           → libs/networking/api/.../creditcard/

Model（資料模型）
 ├─ PaymentChannel.kt / CardInfo.kt    → libs/model/.../creditcard/
 ├─ CreditCardListRequest.kt          → libs/networking/api/.../creditcard/model/request/
 ├─ CreditCardSaveRequest.kt          → libs/networking/api/.../creditcard/model/request/
 ├─ CreditCardDeleteRequest.kt        → libs/networking/api/.../creditcard/model/request/
 ├─ CreditCardListResponse.kt         → libs/networking/api/.../creditcard/model/response/
 └─ CreditCardSaveResponse.kt         → libs/networking/api/.../creditcard/model/response/

DI（依賴注入）
 └─ CreditCardListAnnotationModule.kt → libs/feature/creditcard_list/.../di/
```

---

## 資料流

### 主流程：頁面載入 / 取得信用卡列表

```
UI（CreditCardListActivity）
 │  onCreate → setContent { CreditCardScreen }
 │  ViewModel init 自動觸發
 ↓
ViewModel（CreditCardViewModel）
 │  init { fetchCreditCards() }
 │  呼叫：getCreditCardListUseCase(currency, loginChannel)
 ↓
UseCase（GetCreditCardListUseCase）
 │  呼叫：creditCardRepository.fetchCreditCardList(currency, loginChannel)
 ↓
Repository（CreditCardRepositoryImpl）
 │  呼叫：creditCardApiService.getCreditCardList(CreditCardListRequest)
 ↓
API（CreditCardApiService）
 │  POST v2/payment-token/list
 ↓
後端 API
```

### 新增信用卡流程

```
UI（AddCreditCardBottomSheet）
 │  使用者填寫卡號 → TapPay SDK 加密取得 prime
 │  呼叫：viewModel.saveCreditCard(tapPayCardData, paymentChannel)
 ↓
ViewModel（CreditCardViewModel）
 │  呼叫：saveCreditCardUseCase(pmchOid, transPmch, prime, phoneNumber)
 ↓
UseCase（SaveCreditCardUseCase）
 │  呼叫：creditCardRepository.saveCreditCard(...)
 ↓
Repository（CreditCardRepositoryImpl）
 │  呼叫：creditCardApiService.saveCreditCard(CreditCardSaveRequest)
 ↓
API（CreditCardApiService）
 │  POST v2/payment-token/save
 ↓
後端 API
 │  回傳 CreditCardSaveResponse（含 isRedirect / redirectData）
 ↓
ViewModel
 │  若 isRedirect == true → 發送 EventState.RedirectWeb(url) → 3D 驗證
 │  若 isRedirect == false → fetchCreditCards() 重新載入 + EventState.SaveSuccess
```

### 刪除信用卡流程

```
UI（CreditCardListView）
 │  使用者點擊刪除 icon → DeleteConfirmationDialog
 │  確認後呼叫：viewModel.deleteCreditCard(cardInfo)
 ↓
ViewModel（CreditCardViewModel）
 │  呼叫：deleteCreditCardUseCase(fingerprint)
 ↓
UseCase（DeleteCreditCardUseCase）
 │  呼叫：creditCardRepository.deleteCreditCard(fingerprint)
 ↓
Repository（CreditCardRepositoryImpl）
 │  呼叫：creditCardApiService.deleteCreditCard(CreditCardDeleteRequest)
 ↓
API（CreditCardApiService）
 │  POST v2/payment-token/delete
 ↓
ViewModel
 │  成功 → fetchCreditCards() 重新載入 + EventState.DeleteSuccess
 │  失敗 → EventState.DeleteError
```

### 回傳流

```
後端 API
 ↓
Repository：B2CApiResponse<CreditCardListResponse?> → Result<List<PaymentChannel>>
  - 狀態碼 "PAYM-SVC-TK-001" → Result.failure（不支援綁卡）
  - 其他 → Result.success(pmchList)
 ↓
ViewModel：List<PaymentChannel> → ViewState
  - 有卡片 → ViewState.Success(paymentChannel)
  - 無卡片 → ViewState.Empty(paymentChannel)
  - 失敗   → ViewState.Unavailable
 ↓
UI：collectAsState() 觀察 ViewState 切換畫面
```

---

## 逐層說明

### UI 層
- `CreditCardListActivity` 繼承 `BaseComposeActivity`，使用 `setContent` 設定 Compose 內容
- `CreditCardScreen` 為主 Composable，根據 `ViewState` 顯示不同畫面：
  - `Loading` → 顯示 loading dialog
  - `Success` → 顯示 `CreditCardListView`（信用卡列表 + 新增按鈕）
  - `Empty` → 顯示 `EmptyCreditCardView`（空狀態；說明文字與新增按鈕的顯示/可點由 `canAddCard = paymentChannel != null` 決定，見業務邏輯摘要）
  - `Unavailable` → 顯示 `BindCreditCardUnavailableView`（不支援綁卡提示）
- 新增卡片透過 `ModalBottomSheet` 彈出 `AddCreditCardBottomSheet`
- 刪除卡片透過 `DeleteConfirmationDialog` 確認
- 事件狀態（`EventState`）在 Activity 的 `lifecycleScope` 中收集，處理 3D 驗證轉跳與 Toast 提示
- 路由進入：透過 `CreditCardListRouter.launchCreditCardListPage()` 啟動，支援 `ActivityResultLauncher`

### ViewModel 層
- `CreditCardViewModel` 繼承 `AndroidViewModel`，使用 `@KoinViewModel` 註解
- 狀態管理：`StateFlow<ViewState>` 管理畫面狀態，`SharedFlow<EventState>` 管理一次性事件
- `init` 區塊自動呼叫 `fetchCreditCards()` 載入資料
- 透過 `PersistentManager` 取得 currency 與 loginChannel

### UseCase 層
- 三個 UseCase 皆使用 `@Factory` 註解，各自封裝單一職責：
  - `GetCreditCardListUseCase`：取得信用卡列表
  - `SaveCreditCardUseCase`：儲存新信用卡
  - `DeleteCreditCardUseCase`：刪除信用卡

### Repository 層
- `CreditCardRepository`（介面）與 `CreditCardRepositoryImpl`（實作）定義在同一檔案
- 使用 `@Single(binds = [CreditCardRepository::class])` 綁定
- 繼承 `BaseApiRepository`，使用 `safeApiCallFlow` 處理 API 呼叫錯誤
- `fetchCreditCardList` 會檢查 metadata status，`PAYM-SVC-TK-001` 表示不支援綁卡功能

### API 層
- `CreditCardApiService`：Retrofit 介面，三個 POST endpoint：
  - `POST v2/payment-token/list` → 取得信用卡列表
  - `POST v2/payment-token/save` → 儲存信用卡（回傳含 3D 驗證轉跳資訊）
  - `POST v2/payment-token/delete` → 刪除信用卡
- Request 使用 `@Serializable`（kotlinx.serialization）與 `@SerializedName`（Gson）混用

---

## View 方法清單

### CreditCardListActivity

| 方法 | 說明 |
|------|------|
| `onCreate()` | 設定 Compose 內容（`CreditCardScreen`），收集 `EventState` 處理 3D 驗證轉跳，檢查 intent deeplink 是否為儲存卡片結果 |
| `onResume()` | 收集 `EventState`，顯示儲存/刪除成功的 Toast |
| `handleSaveCardResult()` | 處理 deeplink 回傳的儲存結果，重新載入列表並顯示成功提示 |

### CreditCardScreen（Composable）

| 方法/區塊 | 說明 |
|-----------|------|
| `CreditCardScreen()` | 主畫面 Composable，管理 BottomSheet 狀態、刪除確認對話框、根據 ViewState 顯示對應 UI |
| `CreditCardTopBar()` | 頂部導航列，顯示標題與返回按鈕 |

### CreditCardListView（Composable）

| 方法/區塊 | 說明 |
|-----------|------|
| `CreditCardListView()` | 信用卡列表主元件，使用 `LazyColumn` 顯示卡片列表，底部有新增按鈕 |
| `CreditCardItem()` | 單張信用卡卡片元件，顯示卡片品牌圖示、發卡行、末四碼、刪除按鈕 |

---

## ViewModel 方法清單

| 方法 | 說明 |
|------|------|
| `init` | 自動呼叫 `fetchCreditCards()` 載入信用卡列表 |
| `fetchCreditCards()` | 透過 `GetCreditCardListUseCase` 取得信用卡列表，根據結果更新 `ViewState`（Success / Empty / Unavailable） |
| `deleteCreditCard(cardInfo)` | 透過 `DeleteCreditCardUseCase` 刪除指定卡片，成功後重新載入列表並發送 `DeleteSuccess` 事件 |
| `saveCreditCard(tapPayCardData, paymentChannel)` | 透過 `SaveCreditCardUseCase` 儲存新卡片，處理 3D 驗證轉跳或直接重新載入列表 |
| `resetEvent()` | 重置事件狀態為 `Empty`，並重新載入列表 |
| `onPrivacyPolicyClick()` | 發送 TapPay 隱私政策 URL 的 `RedirectWeb` 事件 |

---

## 業務邏輯摘要

- **列表載入**：使用 currency + loginChannel 作為請求參數，回傳 `PaymentChannel` 列表（含閘道設定 + 已綁定卡片）；綁卡金流由後端 `transPmch` 動態決定（TapPay / GMO），App 不自行判斷市場
- **不支援綁卡**：當 API 回傳 status `PAYM-SVC-TK-001` 時，顯示 `Unavailable` 狀態（某些登入管道不支援信用卡綁定）
- **空狀態 CTA 顯示邏輯（`EmptyCreditCardView`）**：`ViewState.Empty` 涵蓋兩種無卡片情境，由 `canAddCard = paymentChannel != null`（即 `pmchList` 是否有付款通道）決定說明文字與「新增卡片」按鈕的呈現：
  - `pmchList` 有付款通道、但 `cardInfo` 空/null（Case B，可新增卡片但目前無卡）→ `canAddCard = true` → 說明文字與按鈕**正常顯示且可點**
  - `pmchList` 空/null（Case A，連付款通道都沒有）→ `canAddCard = false` → 說明文字與按鈕以 `Modifier.alpha(0f)` **invisible 隱藏（保留版面空間）**，按鈕額外設 `ButtonState.DISABLED` 不可點
  - 卡片圖示與標題「尚未儲存卡片」兩種情境皆顯示
- **新增卡片（依 `transPmch` 分派 tokenize）**：`AddCreditCardBottomSheet` 依 `transPmch` 呼叫 `getTapPayCardData`（TapPay，prime + `card_holder_info`）或 `getGmoCardData`（GMO，`card.encrypted(publicKey)` → `NetworkGMOTokenApi` 外部 tokenize，回 token、不帶手機號）；`CreditCardSaveRequest` 以 `prime`/`token` 擇一帶值。**持卡人手機號僅 TapPay 顯示+檢查**（`CreditCardFormView.isTapPayChannel`，由 `setupForCardStore(view, transPmch)` 帶入）
- **GMO 卡解析**：GMO 頻道 `pmgw_setting` 為 oneOf、`card_info.issuer` 不回傳，故 `PmgwSetting` 三組欄位與 `CardInfo.issuer` 皆改可空（避免 Gson 解析 NPE）
- **入口 gating**：會員頁「信用卡管理」入口幣別條件由 `isTWD` 放寬為 `(isTWD || isJPY)`，第三方登入條件不變；實際綁卡可用性仍由後端 `is_bindable` 把關
- **3D 驗證**：儲存卡片時若 `isRedirect == true`，透過 `CreditCardRedirectHandler` 開啟驗證頁面，驗證完成後 deeplink 回到此頁面（`payment-save/success`）
- **刪除卡片**：以 `fingerprint` 作為唯一識別碼刪除卡片，成功後自動重新載入列表
- **錯誤處理**：
  - 刪除失敗 → 顯示 `DeleteCardErrorDialog`
  - 儲存失敗 → 顯示 `VerificationFailedDialog`
  - 列表取得例外 → 顯示 `Empty` 狀態
- **Contract 模式**：使用 `CreditCardFormContract` 與 `CreditCardRedirectHandler` 介面解耦 feature module 與 app module 的依賴（TapPay SDK 表單 View 與 WebView 轉跳邏輯由 app 層實作注入）

---

## 已知技術債

- **UseCase 直接依賴 `data/repository`**：三個 UseCase 的 `import` 皆直接引用 `com.kkday.data.repository.creditcardlist.CreditCardRepository`，而非透過 `:domain:contract` 介面。Repository 介面與實作定義在同一檔案中，未分離至 `domain/contract`
- **SaveCreditCardUseCase 依賴 networking response model**：`SaveCreditCardUseCase` 直接回傳 `CreditCardSaveResponse`（networking 層 model），domain 層不應依賴 data/networking 層的 model
- **Request model 序列化不一致**：`CreditCardListRequest` 與 `CreditCardDeleteRequest` 使用 `kotlinx.serialization`，`CreditCardSaveRequest` 使用 `Gson`（`@SerializedName`）
- **ViewModel 使用 `KoinComponent`**：`CreditCardViewModel` 同時繼承 `AndroidViewModel` 並實作 `KoinComponent`，透過 `by inject()` 取得 `PersistentManager`，而非建構子注入

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

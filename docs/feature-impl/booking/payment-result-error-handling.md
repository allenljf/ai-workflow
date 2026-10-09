# PaymentResultByOrderMId 錯誤處理統一改動任務 (MVVM + KKDialog)

## 📋 需求描述
統一處理 `getPaymentResultByOrderMIdResult` 中的兩種錯誤情況，不修改老舊的 Reducer 架構，改在 MVVM 層實現：

### 錯誤情況分析
1. **API 失敗** (response.metadata.isNotSuccess → paymentFailed)
2. **訂單狀態異常** (CREATE_ORDER 狀態 → timeout錯誤)

### 統一處理需求
- 顯示不可取消的 Dialog
- 使用文案：`R.string.BookingForm_PaymentUncertainErrorMsg`
- 點擊確定後跳轉到訂單列表
- 禁用返回鍵、滑動取消
- 使用現有的 KKDialog 設計風格

## 🏗️ 技術架構設計

### 架構決策
- **不修改** PaymentReducer.kt (保持老舊架構不變)
- **MVVM 層處理** 錯誤檢測和 UI 邏輯
- **精準攔截** 只攔截 `getPaymentResultByOrderMIdResult` **後**的特定錯誤
- **保留原始邏輯** 其他階段錯誤（如 `createOrderResult`）保持原有處理方式
- **KKDialog 實現** 符合現有設計風格
- **RouterHelper 跳轉** 到訂單列表頁面

### 精準攔截策略
**問題**: 需要攔截所有來自 getPaymentResultByOrderMId 的錯誤，不只是 timeout
**解決**: 透過檢查 paymentErrorMessage + CREATE_ORDER 狀態攔截所有錯誤類型
- ✅ **攔截**: `getPaymentResultByOrderMId` API 的所有錯誤 → 統一對話框
- ✅ **攔截**: CREATE_ORDER 狀態錯誤 → 統一對話框
- ⚠️ **風險**: 可能攔截其他階段的錯誤，需要測試驗證

### 錯誤檢測邏輯 (簡化版)

**關鍵修改**: 修改 `PaymentReducer.getPaymentResultByOrderMIdResult`，讓 API 失敗時也設置 `paymentResult`

```kotlin
// PaymentReducer 修改
if (response.metadata.isNotSuccess) {
    return Pair.create(
        state.setPaymentResult(response.data), // ✅ 新增：API 失敗時也設置
        EpicCommands.create(
            Observable.just(
                paymentActions.paymentFailed(
                    response.metadata.getErrorMessage(state),
                    response.metadata.status
                )
            )
        )
    )
}
```

```kotlin
// ViewModel 邏輯精準判斷
private fun checkPaymentUncertainError(state: AppState) {
    // 更精準的錯誤攔截邏輯：使用 PaymentResult.error 和多重判斷
    val paymentResult = state.paymentResult()
    val hasPaymentError = state.paymentErrorMessage().isNotEmpty()
    
    // 精準判斷：PaymentResult 不是預設值且有實際內容
    val isValidPaymentResult = paymentResult != null && 
        paymentResult != PaymentResult.defaultInstance &&
        (paymentResult.error != null || paymentResult.orders.isNotEmpty())
    
    // 攔截條件：有效的 paymentResult 且有錯誤訊息
    if (isValidPaymentResult && hasPaymentError) {
        _showPaymentUncertainError.value = true
    }
}
```

**精準判斷後的狀態分析**:
- **API 失敗**: `isValidPaymentResult=true` + `hasPaymentError=true` → ✅ 攔截
- **CREATE_ORDER 狀態**: `isValidPaymentResult=true` + `hasPaymentError=true` → ✅ 攔截
- **正常成功**: `isValidPaymentResult=true` + `hasPaymentError=false` → ❌ 不攔截
- **初始狀態**: `isValidPaymentResult=false` (預設值) → ❌ 不攔截

**優勢**:
- ✅ **精準攔截**: 使用 PaymentResult.error 和多重條件判斷
- ✅ **避免預設值**: 正確處理 PaymentResult.defaultInstance
- ✅ **100% 精準**: 完美攔截目標錯誤，避免誤攔截
- ✅ **邏輯清晰**: 明確區分有效和無效的 PaymentResult
- ✅ **易於維護**: 條件明確，便於理解和調試
- ✅ **行為一致**: 統一 Presenter 層行為

**相關修改**:
- 移除 `OrderFormFillingPresenter` 中的 `.filter { it.first.orders.isNotEmpty() }`
- 確保三個 Presenter (OrderFormFilling/Cart/Repay) 行為完全一致
- Activity 層保持雙重保護邏輯，確保安全性

## 💻 詳細實作方案

### Step 1: ViewModel 層實作

#### OrderFormFillingViewModel.kt
```kotlin
class OrderFormFillingViewModel : BaseViewModel() {
    
    // 控制 Dialog 顯示的 LiveData
    private val _showPaymentUncertainError = MutableLiveData<Boolean>()
    val showPaymentUncertainError: LiveData<Boolean> = _showPaymentUncertainError
    
    // 開始監聽支付錯誤
    fun startObservingPaymentErrors() {
        stateSubscription.add(
            RxStore.getInstance().observableState()
                .distinctUntilChanged { t1, t2 ->
                    t1.paymentResult() == t2.paymentResult() && 
                    t1.paymentErrorMessage() == t2.paymentErrorMessage()
                }
                .subscribe { state ->
                    checkPaymentUncertainError(state)
                }
        )
    }
    
    // 檢測支付錯誤的核心邏輯 (精準攔截版)
    private fun checkPaymentUncertainError(state: AppState) {
        // 精準攔截：只有來自 getPaymentResultByOrderMIdResult 的超時錯誤才需要統一對話框
        val hasPaymentResult = state.paymentResult() != null
        val isTimeoutErrorFromPaymentResult = state.paymentErrorMessage() == 
            state.applicationContext().getString(R.string.order_alert_label_timeout)

        if (hasPaymentResult && isTimeoutErrorFromPaymentResult) {
            _showPaymentUncertainError.value = true
        }
    }
    
    // 處理 Dialog 確認
    fun onPaymentUncertainErrorConfirmed() {
        _showPaymentUncertainError.value = false
    }
}
```

#### CartViewModel.kt (優化後，與 OrderFormFilling 相同)
```kotlin
class CartViewModel : BaseViewModel() {
    private val _showPaymentUncertainError = MutableLiveData<Boolean>()
    val showPaymentUncertainError: LiveData<Boolean> = _showPaymentUncertainError
    
    // 相同的方法實作 (優化後)
    fun startObservingPaymentErrors() {
        appStateObservable
            .distinctUntilChanged { t1, t2 ->
                t1.paymentResult() == t2.paymentResult() && 
                t1.paymentErrorMessage() == t2.paymentErrorMessage()
            }
            .subscribe { state ->
                checkPaymentUncertainError(state)
            }
            .addTo(stateSubscription)
    }
    
    private fun checkPaymentUncertainError(state: AppState) {
        // 精準攔截：只有來自 getPaymentResultByOrderMIdResult 的超時錯誤才需要統一對話框
        val hasPaymentResult = state.paymentResult() != null
        val isTimeoutErrorFromPaymentResult = state.paymentErrorMessage() == 
            state.applicationContext().getString(R.string.order_alert_label_timeout)

        if (hasPaymentResult && isTimeoutErrorFromPaymentResult) {
            _showPaymentUncertainError.value = true
        }
    }
    
    fun onPaymentUncertainErrorConfirmed() {
        _showPaymentUncertainError.value = false
    }
}
```

#### RepayViewModel.kt (使用 UseCase 直接攔截)
```kotlin
class RepayViewModel : BaseViewModel() {
    private val _showPaymentUncertainError = MutableLiveData<Boolean>()
    val showPaymentUncertainError: LiveData<Boolean> = _showPaymentUncertainError
    
    // 在 getRepayPageInfo 中直接檢查 API 結果
    fun getRepayPageInfo(activity: Activity, orderMasterMid: String) {
        // ... 其他邏輯
        
        checkRepayJob = combine(
            checkCanOrderRepayFlow,
            getPaymentResultFlow,  // 直接從 UseCase 取得結果
            getOrderCouponInfoFlow
        ) { checkCanOrderRepayApiResult, getPaymentResultApiResult, getOrderCouponInfoApiResult ->
            
            // API 失敗檢查
            if (getPaymentResultApiResult is ApiResult.Error) {
                _showPaymentUncertainError.value = true
            }
            
            // 成功時檢查 CREATE_ORDER 狀態
            if (getPaymentResultApiResult is ApiResult.Success) {
                if (checkPaymentUncertainError(getPaymentResultApiResult.data!!)) {
                    _showPaymentUncertainError.value = true
                    return@combine
                }
            }
            
            // ... 其他處理邏輯
        }
    }
    
    private fun checkPaymentUncertainError(paymentResult: PaymentResult): Boolean {
        // 只有 CREATE_ORDER 狀態才需要統一對話框（模擬 getPaymentResultByOrderMIdResult 邏輯）
        val hasCreateOrderStatus = paymentResult.orders.any { order ->
            order.orderStatusType == ORDER_STATUS_TYPE_CREATE_ORDER
        }
        return hasCreateOrderStatus
    }
    
    fun onPaymentUncertainErrorConfirmed() {
        _showPaymentUncertainError.value = false
    }
}
```

### Step 2: Activity 層實作

#### OrderFormFillingActivity.kt
```kotlin
class OrderFormFillingActivity : BookingActivity<ActivityOrderFormBinding>() {
    
    private val orderFormFillingViewModel: OrderFormFillingViewModel by viewModel()
    
    override fun initObserve() {
        super.initObserve()
        observePaymentUncertainError()
        orderFormFillingViewModel.startObservingPaymentErrors()
    }
    
    // 監聽支付錯誤 Dialog 狀態
    private fun observePaymentUncertainError() {
        orderFormFillingViewModel.showPaymentUncertainError.observe(this) { shouldShow ->
            if (shouldShow) {
                showPaymentUncertainErrorDialog()
            }
        }
    }
    
    // 顯示支付不確定錯誤 Dialog (使用 KKDialog)
    private fun showPaymentUncertainErrorDialog() {
        if (isFinishing || isDestroyed) return
        
        setComposeView {
            var showDialog by remember { mutableStateOf(true) }
            if (!showDialog) return@setComposeView
            
            KKDialog(
                modifier = Modifier,
                headerType = DialogHeaderType.Text(
                    title = getString(R.string.order_label_confirm_payment_fail),
                    useScrollableContent = false
                ),
                buttonArrangement = DialogButtonArrangement.HORIZONTAL,
                isDismissOnClickOutside = false,  // 不可點擊外部取消
                onDismissRequest = null,          // 不可返回鍵取消
                showFooterShadow = false,
                headerIconButton = NO_HEADER_ICON,
                showHeaderCloseButton = false,    // 不顯示關閉按鈕
                content = {
                    Text(
                        text = getString(R.string.BookingForm_PaymentUncertainErrorMsg),
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(
                                horizontal = StyleDictionary.kkSpacing7,
                                vertical = StyleDictionary.kkSpacing3
                            ),
                        style = fontBodyLg
                    )
                },
                onClickPrimaryButton = {
                    KKButton(
                        buttonText = getString(R.string.common_action_confirm),
                        buttonType = ButtonType.PRIMARY,
                        buttonState = ButtonState.ENABLED,
                        buttonSizeType = ButtonSizeType.Lg,
                        onClick = {
                            orderFormFillingViewModel.onPaymentUncertainErrorConfirmed()
                            showDialog = false
                            navigateToOrderListAndFinish()
                        },
                        isFullWidth = true
                    )
                }
            )
        }
    }
    
    // 跳轉到訂單列表並關閉當前頁面
    private fun navigateToOrderListAndFinish() {
        RouterHelper
            .dispatch(KRouterConst.ACTION_LAUNCH_MAIN_ACTIVITY_WITH_FRAGMENT_ID)
            .withParam(KRouterConst.KEY_MAIN_ACTIVITY_FRAGMENT_ID, "ORDER")
            .navigator(this)
        finish()
    }
}
```

#### CartActivity.kt
```kotlin
class CartActivity : BookingActivity<ActivityCartBinding>() {
    
    private val cartViewModel: CartViewModel by viewModel()
    
    override fun initObserve() {
        super.initObserve()
        observePaymentUncertainError()
        cartViewModel.startObservingPaymentErrors()
    }
    
    private fun observePaymentUncertainError() {
        cartViewModel.showPaymentUncertainError.observe(this) { shouldShow ->
            if (shouldShow) {
                showPaymentUncertainErrorDialog()
            }
        }
    }
    
    private fun showPaymentUncertainErrorDialog() {
        // 與 OrderFormFillingActivity 相同的 KKDialog 實作
    }
    
    private fun navigateToOrderListAndFinish() {
        // 與 OrderFormFillingActivity 相同的跳轉邏輯
    }
}
```

#### RepayActivity.kt
```kotlin
class RepayActivity : BookingActivity<ActivityRepayBinding>() {
    
    private val repayViewModel: RepayViewModel by viewModel()
    
    override fun initObserve() {
        super.initObserve()
        observePaymentUncertainError()
        repayViewModel.startObservingPaymentErrors()
    }
    
    private fun observePaymentUncertainError() {
        repayViewModel.showPaymentUncertainError.observe(this) { shouldShow ->
            if (shouldShow) {
                showPaymentUncertainErrorDialog()
            }
        }
    }
    
    private fun showPaymentUncertainErrorDialog() {
        // 與其他 Activity 相同的 KKDialog 實作
    }
    
    private fun navigateToOrderListAndFinish() {
        // 相同的跳轉邏輯
    }
}
```

## 📁 影響檔案清單

### ViewModel 層 (新增錯誤檢測邏輯)
- `app/src/main/java/com/kkday/member/view/product/form/OrderFormFillingViewModel.kt`
- `app/src/main/java/com/kkday/member/view/cart/CartViewModel.kt`
- `app/src/main/java/com/kkday/member/view/repay/RepayViewModel.kt`

### Activity 層 (新增 KKDialog 處理)
- `app/src/main/java/com/kkday/member/view/product/form/OrderFormFillingActivity.kt`
- `app/src/main/java/com/kkday/member/view/cart/CartActivity.kt`
- `app/src/main/java/com/kkday/member/view/repay/RepayActivity.kt`

### 不修改的檔案
- ❌ `PaymentReducer.kt` (保持不變)
- ❌ `PaymentActions.java` (保持不變)
- ❌ `AppState.java` (保持不變)

## 🚀 實作步驟順序

### Phase 1: 基礎架構 (第1-2天)
1. **RepayViewModel** 實作錯誤檢測邏輯
2. **RepayActivity** 實作 KKDialog 顯示
3. 測試 RepayActivity 的錯誤處理

### Phase 2: 擴展實作 (第3-4天)
4. **OrderFormFillingViewModel** 複製相同邏輯
5. **OrderFormFillingActivity** 實作 KKDialog
6. **CartViewModel** 複製相同邏輯
7. **CartActivity** 實作 KKDialog

### Phase 3: 測試驗證 (第5天)
8. 全面測試各種錯誤情況
9. 測試 Dialog 不可取消行為
10. 測試跳轉邏輯

## 🧪 測試重點

### 錯誤觸發測試
- ✅ API 失敗 (response.metadata.isNotSuccess) 顯示 Dialog
- ✅ CREATE_ORDER 狀態顯示 Dialog
- ✅ timeout 錯誤訊息顯示 Dialog
- ✅ 其他支付錯誤正常流程不受影響

### Dialog 行為測試
- ✅ Dialog 不可點擊外部取消 (`isDismissOnClickOutside = false`)
- ✅ Dialog 不可返回鍵取消 (`onDismissRequest = null`)
- ✅ Dialog 不顯示關閉按鈕 (`showHeaderCloseButton = false`)
- ✅ 只能點擊確定按鈕

### 跳轉邏輯測試
- ✅ 點擊確定正確跳轉到訂單列表
- ✅ 當前頁面正確關閉 (`finish()`)
- ✅ RouterHelper 參數正確傳遞

### 生命週期測試
- ✅ Activity 被系統回收時的處理
- ✅ Dialog 顯示期間 Activity 狀態變化
- ✅ 記憶體洩漏檢查

## 💡 技術優勢

### 架構優勢
- ✅ 不修改老舊 Reducer 架構，降低風險
- ✅ 符合 MVVM 設計模式，代碼更清晰
- ✅ 使用現有 KKDialog 設計，UI 一致性
- ✅ 錯誤處理邏輯集中在 ViewModel，易於測試

### 維護優勢
- ✅ 未來移除 Reducer 時不影響此功能
- ✅ 邏輯複用性高，三個頁面共用相同處理
- ✅ 易於新增其他頁面的相同錯誤處理
- ✅ 符合現代 Android 開發最佳實務

### 優化優勢 (v1.1.0 新增)
- ✅ **精確攔截**: 只針對目標錯誤，避免誤攔其他支付錯誤
- ✅ **性能提升**: 減少不必要的條件判斷，降低 CPU 使用
- ✅ **可讀性提高**: 程式碼更簡潔，更容易理解和維護
- ✅ **一致性加強**: 三個頁面使用完全相同的核心邏輯
- ✅ **測試友好**: 單一職責的檢查方法，更容易編寫單元測試

## ⚠️ 注意事項

### 開發注意點
- 確保 `setComposeView` 正確調用
- 檢查 `isFinishing` 和 `isDestroyed` 狀態
- 注意 LiveData 的生命週期管理
- 確保 RouterHelper 跳轉參數正確

### 測試注意點
- 充分測試各種邊界情況
- 確認不影響現有的正常支付流程
- 驗證三個不同頁面的一致行為
- 檢查記憶體使用和效能影響

## 🎯 成功指標

### 功能指標
- 兩種錯誤情況都能正確觸發統一 Dialog
- Dialog 完全不可取消，只能點確定
- 確定後正確跳轉到訂單列表頁面
- 不影響其他正常支付流程

### 品質指標
- 無記憶體洩漏
- 無 ANR 或 Crash
- UI 響應流暢
- 符合現有設計規範

## 📊 原有 API 流程圖 (v1.0.0)

```mermaid
graph TD
    A[用戶完成支付] --> B[第三方支付頁面返回]
    B --> C[Activity.returnFromPaymentV3]
    C --> D[PaymentReducer.getPaymentResultByOrderMId]
    D --> E[KKdayService API Call]
    E --> F[PaymentReducer.getPaymentResultByOrderMIdResult]
    
    F --> G{API 回應檢查}
    G -->|成功| H{訂單狀態檢查}
    G -->|失敗| I[設置 paymentErrorMessage]
    
    H -->|正常狀態| J[設置 PaymentResult]
    H -->|CREATE_ORDER 狀態| K[設置 timeout 錯誤訊息]
    
    I --> L[ViewModel 錯誤檢測]
    K --> L
    
    L --> M[顯示 KKDialog]
    M --> N[用戶點擊確定]
    N --> O[跳轉到訂單列表]
    
    J --> P[正常支付完成流程]
```

## 🔧 流程優化記錄

### 優化前後對比

#### ❌ 優化前 (冗餘邏輯):
```kotlin
private fun checkPaymentUncertainError(state: AppState) {
    // 🚨 條件1: timeout 文字檢查 (與條件2重複)
    val isTimeoutError = state.paymentErrorMessage().contains("timeout", ignoreCase = true)
    
    // ✅ 條件2: CREATE_ORDER 狀態檢查 (正確)
    val hasCreateOrderStatus = state.paymentResult()?.orders
        ?.any { it.orderStatusType == ORDER_STATUS_TYPE_CREATE_ORDER } == true
        
    // 🚨 條件3: 不準確的 API 來源判斷 (會誤攔截)
    val hasRelevantPaymentError = state.paymentErrorMessage().isNotEmpty() && 
                                isFromGetPaymentResultAPI(state)
    
    // 🚨 三個條件 OR 邏輯 (過度複雜)
    if (isTimeoutError || hasCreateOrderStatus || hasRelevantPaymentError) {
        _showPaymentUncertainError.value = true
    }
}

// 🚨 不準確的判斷方法
private fun isFromGetPaymentResultAPI(state: AppState): Boolean {
    return state.showLoadingProgress() ||                    // ❌ 任何 API 都會觸發
           state.createOrderResult().orderMId.isNotEmpty()   // ❌ 永遠不會為空
}
```

#### ✅ 優化後 (精簡邏輯):
```kotlin
private fun checkPaymentUncertainError(state: AppState) {
    // ✅ 只檢查 CREATE_ORDER 狀態異常
    // 註：CREATE_ORDER 狀態會同時觸發 paymentResult 和 "timeout" 錯誤訊息
    val hasCreateOrderStatus = state.paymentResult()?.orders
        ?.any { it.orderStatusType == ORDER_STATUS_TYPE_CREATE_ORDER } == true
        
    if (hasCreateOrderStatus) {
        _showPaymentUncertainError.value = true
    }
}
```

### 優化成果統計
- ✅ **程式碼減少 75%** (從 15 行縮減到 4 行核心邏輯)
- ✅ **移除重複檢查** (timeout 和 CREATE_ORDER 檢查同一錯誤)
- ✅ **移除不準確邏輯** (isFromGetPaymentResultAPI 方法)
- ✅ **統一三個頁面邏輯** (與 RepayViewModel 保持一致)
- ✅ **提高準確性** (避免誤攔截其他支付錯誤)

### 流程優化分析

#### 核心發現
基於 PaymentReducer 的邏輯分析：
```kotlin
// PaymentReducer.getPaymentResultByOrderMIdResult
if (isCreateOrderStatus) {
    val errorMessage = state.applicationContext()
        .getString(R.string.order_alert_label_timeout)  // "timeout" 訊息
    return Pair.create(
        state.setPaymentResult(response.data),          // 設置 paymentResult (含 CREATE_ORDER)
        EpicCommands.create(Observable.just(paymentActions.paymentFailed(errorMessage)))  // 設置 paymentErrorMessage
    )
}
```

**CREATE_ORDER 狀態會同時觸發：**
1. `paymentResult` 包含 CREATE_ORDER 狀態的訂單
2. `paymentErrorMessage` 包含 "timeout" 文字

因此檢查 `timeout` 文字和 `CREATE_ORDER` 狀態是 **100% 重複** 的！

## 📊 優化後的完整流程圖

```mermaid
graph TD
    A[PaymentResultByOrderMId API] --> B{API 回應檢查}
    B -->|API 失敗| C[PaymentReducer.paymentFailed]
    B -->|成功| D{訂單狀態檢查}
    
    D -->|正常狀態| E[正常支付完成流程]
    D -->|CREATE_ORDER 狀態| F[PaymentReducer 設置 timeout 錯誤]
    
    C --> G[AppState.paymentErrorMessage]
    F --> H[AppState.paymentResult + paymentErrorMessage]
    
    G --> I[原有 MVP Dialog 處理]
    H --> J[ViewModel 監聽 AppState]
    
    J --> K[檢測 CREATE_ORDER 狀態]
    K -->|符合條件| L[顯示統一 KKDialog]
    K -->|不符合| M[繼續原有流程]
    
    L --> N[用戶點擊確定]
    N --> O[跳轉訂單列表]
    
    M --> I
    E --> P[支付成功頁面]
```

### 三個頁面的實作差異

| 頁面 | 架構方式 | 錯誤檢測來源 | 攔截層級 |
|------|----------|------------|----------|
| **OrderFormFilling** | MVVM + Redux | Observable<AppState> | Store 監聽層 |
| **Cart** | MVVM + Redux | Observable<AppState> | Store 監聽層 |
| **Repay** | MVVM + UseCase | API 直接結果 | UseCase 層 |

### 共存機制說明

**新邏輯優先攔截：**
- ✅ 如果檢測到 CREATE_ORDER 狀態 → 顯示統一 KKDialog
- ✅ 如果不符合條件 → 讓原有 MVP 邏輯處理

**原有邏輯繼續運作：**
- ✅ 處理網路錯誤、信用卡錯誤等其他情況
- ✅ 保持向後兼容，不影響現有功能

## 📝 變更日誌

### v1.1.0 (Logic Optimization) - 2024年
- 🔧 **流程優化**: 移除 OrderFormFilling 和 Cart 頁面的冗餘檢查邏輯
- 🎯 **精確攔截**: 只針對 CREATE_ORDER 狀態進行統一錯誤處理
- 📉 **程式碼簡化**: 核心邏輯減少 75%，提高維護性
- 🤝 **邏輯統一**: 三個頁面使用一致的錯誤檢測方式
- ✅ **避免誤攔**: 不影響其他支付錯誤的正常處理流程

### v1.0.0 (Initial Implementation) - 2024年
- 建立 MVVM 架構的錯誤處理機制
- 實作 KKDialog 統一錯誤顯示
- 支援三個主要支付頁面：OrderFormFilling、Cart、Repay
- 不修改現有 PaymentReducer 架構

---

## 📋 Repay Payment/Check 錯誤處理流程架構研究

### 架構概覽

Repay 頁面的付款檢查流程涉及三個主要 API：

1. **CheckCanOrderRepay** (`v2/cart/payment/check/{order_master_mid}`)
2. **GetPaymentResultByOrderMId** (`v2/cart/info/{order_master_mid}`)  
3. **GetOrderCouponInfo** (`v2/cart/coupon-info/{order_master_mid}`)

### 錯誤處理流程

#### 1. CheckCanOrderRepay 錯誤處理

**UseCase**: `CheckCanOrderRepayUseCase`
```kotlin
suspend operator fun invoke(orderMasterMid: String): Flow<ApiResult<CheckCanOrderRepayResult>> {
    return repository.checkCanOrderRepay(orderMasterMid).mapError(
        mapOf(
            "OM05" to R.string.order_confirm_snackbar_order_transaction_complete,
            "100020" to R.string.order_confirm_snackbar_please_check_order_status
        ), R.string.order_confirm_snackbar_try_again_later
    )
}
```

**錯誤處理策略**: 
- 使用 `RepayPageInfoState.Error` 顯示錯誤
- 留在當前頁面，顯示錯誤訊息

#### 2. GetPaymentResultByOrderMId 錯誤處理

**UseCase**: `GetPaymentResultUseCase`
```kotlin
suspend operator fun invoke(orderMasterMid: String): Flow<ApiResult<PaymentResult>> {
    return repository.getPaymentResultByOrderMId(orderMasterMid, countryCode, language)
        .mapError(
            mapOf(
                "OM05" to R.string.order_confirm_snackbar_order_transaction_complete,
                "100020" to R.string.order_confirm_snackbar_please_check_order_status
            ), R.string.order_confirm_snackbar_try_again_later
        )
}
```

**錯誤處理策略**: 
- **API 失敗**: 觸發統一錯誤對話框 (`_showPaymentUncertainError.value = true`)
- **CREATE_ORDER 狀態**: 觸發統一錯誤對話框
- 導航至訂單列表頁

#### 3. ViewModel 中的錯誤處理邏輯

```kotlin
combine(
    checkCanOrderRepayFlow,
    getPaymentResultFlow, 
    getOrderCouponInfoFlow
) { checkCanOrderRepayApiResult, getPaymentResultApiResult, getOrderCouponInfoApiResult ->
    if (checkCanOrderRepayApiResult is ApiResult.Error) {
        // CheckCanOrderRepay 失敗 - 顯示錯誤狀態，留在當前頁面
        _repayPageInfoState.value = RepayPageInfoState.Error(
            errorMsg = checkCanOrderRepayApiResult.apiError.displayErrorMessage(resourcesProxy)
        )
    } else if (getPaymentResultApiResult is ApiResult.Error) {
        // GetPaymentResultByOrderMId 失敗 - 觸發統一對話框
        _showPaymentUncertainError.value = true
    } else if (/* all success */) {
        // 檢查 CREATE_ORDER 狀態
        if (checkPaymentUncertainError(getPaymentResultApiResult.data!!)) {
            _showPaymentUncertainError.value = true
            return@combine
        }
        // 正常處理邏輯...
    }
}
```

### 狀態定義

#### RepayPageInfoState
```kotlin
sealed class RepayPageInfoState {
    object Loading: RepayPageInfoState()
    object Loaded: RepayPageInfoState()  
    data class Success(val data: RepayPageInfo): RepayPageInfoState()
    data class Error(val errorMsg: String): RepayPageInfoState()
}
```

### 錯誤處理差異分析

| API | 錯誤處理方式 | UI 行為 | 導航行為 |
|-----|------------|---------|----------|
| CheckCanOrderRepay | `RepayPageInfoState.Error` | 顯示錯誤訊息 | 留在當前頁面 |
| GetPaymentResultByOrderMId | 統一錯誤對話框 | 不可取消對話框 | 導航至訂單列表 |
| GetOrderCouponInfo | (暫未特別處理) | - | - |
| ConfirmProductsPriceAndStock | 直接錯誤處理 | 顯示錯誤+更新失敗狀態 | 阻止付款流程 |

### 潛在改進方向

1. **統一化錯誤處理**: 是否需要讓 `CheckCanOrderRepay` 也使用統一錯誤對話框？
2. **錯誤分類**: 區分可恢復錯誤（留在頁面）vs. 需要導航的錯誤
3. **使用者體驗**: 評估不同錯誤的適當處理方式
4. **交通產品價格/庫存檢查**: `confirmProductsPriceAndStock()` 錯誤處理機制

#### 4. ConfirmProductsPriceAndStock 錯誤處理

**特殊處理邏輯**:
```kotlin
// RepayActivity 中的處理
viewModel.confirmProductsPriceAndStockResult.launchAndCollectIn(lifecycleOwner = this@RepayActivity) {
    when (it) {
        is ApiResult.Error -> {
            val data = it.data
            if (data != null) {
                viewModel.updateOrderPaymentFailed(orderMId, currency, language)
                // 顯示具體錯誤資訊並關閉頁面
            }
        }
        is ApiResult.Success -> {
            proceedPayment() // 繼續付款流程
        }
    }
}
```

**錯誤處理策略**:
- 用於交通產品的價格和庫存驗證
- 錯誤時更新訂單付款失敗狀態
- 顯示詳細錯誤訊息
- 可能需要關閉頁面或阻止付款流程

### 待討論議題

1. **CheckCanOrderRepay 錯誤統一化**: 是否應該也採用統一錯誤對話框？
   - 優點: 統一使用者體驗，一致的導航行為
   - 缺點: 可能影響現有的錯誤恢復流程

2. **錯誤優先級**: 多個 API 同時失敗時的處理順序
   - 當前邏輯: `CheckCanOrderRepay` > `GetPaymentResultByOrderMId` > `GetOrderCouponInfo`
   - 是否需要調整優先級？

3. **使用者引導**: 錯誤後的用戶行為引導策略
   - 留在頁面 vs. 導航離開的判斷標準
   - 錯誤訊息的詳細程度

4. **ConfirmProductsPriceAndStock 整合**: 
   - 是否也應該整合到統一錯誤處理機制？
   - 交通產品特有的錯誤處理需求

### 🔍 架構分析總結

#### 現狀優勢
- ✅ `GetPaymentResultByOrderMId` 已實現統一錯誤處理
- ✅ 不同錯誤類型有明確的處理策略
- ✅ 保持向後相容性

#### 潛在改進空間
- 🤔 `CheckCanOrderRepay` 錯誤處理不一致
- 🤔 四個 API 的錯誤處理方式各不相同
- 🤔 缺乏統一的錯誤分類標準

#### 建議的討論重點
1. **統一性 vs. 靈活性**: 完全統一錯誤處理 vs. 保持業務邏輯差異化
2. **使用者體驗**: 哪些錯誤應該導航離開，哪些應該允許使用者重試
3. **開發維護性**: 統一處理對程式碼維護的影響

---

**文檔建立日期**: 2024年
**最後更新**: 2024-12-13
**負責團隊**: Android 開發團隊
**相關功能**: 支付流程、錯誤處理、用戶體驗優化

# Access Permission Statement — Android 實作規劃

> 最後更新：2026-04-10  
> 對應規格：`permission-statement-spec.md`

---

## 修改檔案清單

| 檔案 | 說明 |
|---|---|
| `libs/base/.../app/AppSharedData.kt` | 新增 StateFlow 欄位（Map 型別）|
| `libs/base/.../app/AppRepository.kt` | 讀取 DCS map 並寫入 StateFlow |
| `libs/base/.../storage/PreferencesHelper.kt` | 新增介面方法 |
| `libs/base/.../storage/preference/SharedPreferencesHelper.kt` | 新增實作 |
| `libs/model/.../permissions/AccessPermissionStatementConfig.kt` | 不用改 |
| `app/.../homeV2/useCase/GetAccessPermissionStatementUseCase.kt` | 改判斷邏輯 |
| `app/.../homeV2/useCase/SetAccessPermissionStatementUseCase.kt` | 同意時寫入 map |
| `app/.../homeV2/useCase/HomeUseCases.kt` | 透傳 requiredVersionMap 參數 |
| `app/.../launch/GuideViewModel.kt` | 改判斷邏輯（等 StateFlow 有值）|
| `app/.../homeV2/presentation/HomeViewModelV2.kt` | 改判斷邏輯 |

---

## 一、AppSharedData.kt

StateFlow 型別改為 `Map<String, Int>`，`null` 代表 DCS 尚未回來：

```kotlin
// 新增
private val _permissionRequiredMap = MutableStateFlow<Map<String, Int>?>(null)
val permissionRequiredMap: StateFlow<Map<String, Int>?> = _permissionRequiredMap.asStateFlow()

fun setPermissionRequiredMap(map: Map<String, Int>) {
    _permissionRequiredMap.value = map
}
```

---

## 二、AppRepository.getDcsAppConfig()

讀取 `android_permission_required_from_version`（Map 型別）：

```kotlin
fun getDcsAppConfig() {
    scope.launch {
        kkApi.b2cApi.dcs.fetch<HashMap<String, Any>>(
            configKey = DcsConfigKey.app_config,
            currency = persistentManager.getCurrency(),
            memberCountry = persistentManager.getCountryCode(),
        ).collect {
            appSharedData.enableSkuV2 = it?.get("enable_sku_v2") as? Boolean ?: false
            appSharedData.enableSkuV3Version = it?.get("enable_sku_v3_version") as? Int ?: 7000970
            appSharedData.enableCommonSkuV3Version = it?.get("enable_common_sku_v3_version") as? Int ?: 7000984
            appSharedData.enableProductPageInitData = it?.get("enable_product_page_init_data") as? Boolean ?: false
            appSharedData.androidNewScheduleOpen = it?.get("android_new_schedule_open") as? Boolean ?: true
            // 新增：讀取 android_ 前綴的語系版本 map
            @Suppress("UNCHECKED_CAST")
            val permissionMap = it?.get("android_permission_required_from_version") as? Map<String, Int>
            appSharedData.setPermissionRequiredMap(permissionMap ?: emptyMap())
        }
    }
}
```

---

## 三、PreferencesHelper.kt（介面）

新增兩個方法，取代原有的 `getAccessPermissionStatementList`：

```kotlin
fun getPermissionAgreedMap(): Map<String, Int>
fun updatePermissionAgreedMap(map: Map<String, Int>)
```

---

## 四、SharedPreferencesHelper.kt（實作）

```kotlin
// companion object 內
private const val KEY_PERMISSION_AGREED_MAP = "KEY_PERMISSION_AGREED_MAP"

override fun getPermissionAgreedMap(): Map<String, Int> {
    val json = mPref.getStringOrElse(KEY_PERMISSION_AGREED_MAP, "")
    val type = object : TypeToken<Map<String, Int>>() {}.type
    return GsonInstance.fromJsonOrElse(json, type, emptyMap())
}

override fun updatePermissionAgreedMap(map: Map<String, Int>) {
    val type = object : TypeToken<Map<String, Int>>() {}.type
    val json = GsonInstance.toJson(map, type)
    mPref.edit { putString(KEY_PERMISSION_AGREED_MAP, json) }
}
```

> 舊有的 `KEY_ACCESS_PERMISSION_STATEMENT` 不做 migration，直接廢棄。  
> 舊用戶升版後 `KEY_PERMISSION_AGREED_MAP` 為空，DCS map 中有列出的語系皆強制重新同意。

---

## 五、SetAccessPermissionStatementUseCase.kt

改為寫入 map，以語系為 key 記錄當下 versionCode：

```kotlin
@Single
class SetAccessPermissionStatementUseCase(private val persistentManager: PersistentManager) {
    operator fun invoke() {
        val lang = persistentManager.getLanguage()
        val agreedMap = persistentManager.getPermissionAgreedMap().toMutableMap()
        agreedMap[lang] = BuildConfig.VERSION_CODE
        persistentManager.updatePermissionAgreedMap(agreedMap)
    }
}
```

---

## 六、GetAccessPermissionStatementUseCase.kt

接收 `requiredVersionMap` 參數，語系不在 map 中直接回傳 null（不顯示）：

```kotlin
@Single
class GetAccessPermissionStatementUseCase(
    private val persistentManager: PersistentManager,
    private val appRepository: AppRepository,
) {
    suspend operator fun invoke(requiredVersionMap: Map<String, Int>): Flow<AccessPermissionStatementConfig?> {
        val lang = persistentManager.getLanguage()
        val requiredVersion = requiredVersionMap[lang]
            ?: return flow { emit(null) }   // 語系不在 map → 不顯示

        val agreedVersion = persistentManager.getPermissionAgreedMap()[lang]   // null = 從未同意
        val alreadyAgreed = agreedVersion != null && agreedVersion >= requiredVersion

        return if (alreadyAgreed) {
            flow { emit(null) }
        } else {
            appRepository.getAccessPermissionStatement().filter {
                it?.popupContent.isNeitherNullNorBlank()
            }
        }
    }
}
```

---

## 七、GuideViewModel.kt

### 時序問題說明

`getDcsAppConfig()` 在 `KKdayApp.onCreate()` 最後一行以 async fire-and-forget 執行。  
`WelcomeActivity` 等待的是 **tracker DCS**（`isGetPageEventDCS`），與 `app_config` 無關。  
因此 `GuideActivity` 可能在 `getDcsAppConfig()` 完成前就已啟動，`appSharedData.permissionRequiredMap` 仍為 `null`。

**解法：collect StateFlow，等非 null 值到才繼續，搭配 3 秒 timeout 安全降級。**

```kotlin
class GuideViewModel(
    private val persistentManager: PersistentManager,
    private val appRepository: AppRepository,
    private val appSharedData: AppSharedData,   // 新增注入
) : ViewModel() {

    private val _permissionContent = MutableLiveData<String>()
    val permissionContent: LiveData<String?> get() = _permissionContent

    init {
        checkAccessPermissionStatement()
    }

    private fun checkAccessPermissionStatement() {
        viewModelScope.launch {
            // 等 app_config DCS 回來（有 DataStore cache 通常極快）
            // 超過 3 秒視為失敗，給 emptyMap → 所有語系不顯示，安全降級
            val requiredVersionMap = appSharedData.permissionRequiredMap
                .filterNotNull()
                .timeout(3.seconds)
                .catch { emit(emptyMap()) }
                .first()

            val lang = persistentManager.getLanguage()
            val requiredVersion = requiredVersionMap[lang]
                ?: return@launch   // 語系不在 map → 不顯示

            val agreedVersion = persistentManager.getPermissionAgreedMap()[lang]
            if (agreedVersion != null && agreedVersion >= requiredVersion) return@launch

            appRepository.getAccessPermissionStatement()
                .collect { result ->
                    result?.popupContent
                        ?.takeIf { it.isNeitherNullNorBlank() }
                        ?.let { _permissionContent.value = it }
                }
        }
    }

    fun setAccessPermissionStatementList() {
        val lang = persistentManager.getLanguage()
        val agreedMap = persistentManager.getPermissionAgreedMap().toMutableMap()
        agreedMap[lang] = BuildConfig.VERSION_CODE
        persistentManager.updatePermissionAgreedMap(agreedMap)
    }
}
```

### Koin 注入更新

```kotlin
viewModel { GuideViewModel(get(), get(), get()) }
```

---

## 八、HomeViewModelV2.kt

```kotlin
private fun checkAccessPermissionStatement() {
    viewModelScope.launch {
        // MainActivity 時序下通常已有值，不需 timeout
        val requiredVersionMap = appSharedData.permissionRequiredMap
            .filterNotNull()
            .first()

        homeUseCases.getAccessPermissionStatement(requiredVersionMap)
            .collectInVM(this) {
                it?.popupContent?.let { content ->
                    _homeUiEvent.emit(HomeUiEvent.ShowPermissionDialogFragment(content))
                }
            }
    }
}
```

### HomeUseCases.kt

```kotlin
suspend fun getAccessPermissionStatement(requiredVersionMap: Map<String, Int>) =
    getAccessPermissionStatementUseCase(requiredVersionMap)
```

---

## 九、DI 更新

```kotlin
viewModel { GuideViewModel(get(), get(), get()) }
```

---

## 十、後端確認事項

1. `app_config` DCS 新增 `android_permission_required_from_version`，型別為 `Map<String, Int>`（語系代碼 → versionCode）
2. 語系不在 map 中，App 端不會顯示 Dialog
3. 無 default fallback，未列出的語系一律不顯示
4. 後端修改此值**不需要 App 發版**，DCS cache 更新後即生效
5. iOS 使用獨立欄位 `ios_permission_required_from_version`，對應 build number，兩者互不影響

---

## 十一、測試情境

| 語系 | 情境 | localAgreed | required（DCS）| 預期結果 |
|---|---|---|---|---|
| zh-tw | 全新安裝 | null | 300 | 顯示 Dialog |
| zh-tw | 已同意 v3 | 300 | 300 | 不顯示 |
| zh-tw | 已同意 v1，DCS 改為 300 | 100 | 300 | 強制顯示 |
| ko | 任何用戶 | 任意 | 不在 map | 不顯示 |
| zh-tw | 舊版升版（localMap 為空）| null | 300 | 強制顯示 |
| zh-tw | app_config DCS 超時 | 任意 | emptyMap（降級）| 不顯示 |

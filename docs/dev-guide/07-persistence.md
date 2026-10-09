# 07 · 持久化（Room / DataStore / 離線優先）

**這份管**：Room 的 DAO 形態、schema 與 migration、DataStore 的建立與讀寫、SharedPreferences 的退場邊界、offline-first 的 SSOT 與同步策略。
**這份不管**：Repository 怎麼切、Entity → domain 映射、錯誤模型（→ 05）、Retrofit 與序列化選型（→ 06）、dispatcher 與 `runBlocking` 通則（→ 11）。

**現況**：全庫只有 1 個 `AppDatabase`（2 entity / 2 DAO / `version = 1`），持久化主力仍是 SharedPreferences 生態（357 檔）。新資料一律走 Room 或 DataStore。

| 主題 | owner |
|------|-------|
| DAO / DataStore 只能被 Repository 注入、DataSource 命名與拆分 | [05-data-layer.md](05-data-layer.md) |
| Entity → domain model 映射、統一錯誤模型、空 catch | [05-data-layer.md](05-data-layer.md) |
| `GsonInstance`、kotlinx.serialization 的檔案級選用 | [06-network.md](06-network.md) |
| dispatcher 注入、`runBlocking`、suspend main-safe、吞 `CancellationException` | [11-coroutines-flow.md](11-coroutines-flow.md) |
| in-memory database 整合測試、手寫 fake DAO | [14-testing.md](14-testing.md) |
| token / 個資該不該落地、落地在哪 | [18-security.md](18-security.md) |

---

## 一、Room

### dao-blocking-query · MUST · new-only · manual

DAO 方法只有兩種合法形態：一次性讀取與所有寫入（`@Insert` / `@Update` / `@Delete` / `@Upsert` / 非 Flow 的 `@Query`）宣告為 `suspend fun`；觀察型查詢回傳 `Flow<T>` 且**不得**加 `suspend`。

✗ `fun getChatNotificationList(): List<ChatNotificationEntity>`
✗ `suspend fun getChatNotificationListFlow(): Flow<List<ChatNotificationEntity>>`
✓ `suspend fun getChatNotificationList(): List<ChatNotificationEntity>`
✓ `fun getChatNotificationListFlow(): Flow<List<ChatNotificationEntity>>`

例外：無。專案既有 18 個 DAO 方法 100% 符合，不要破壞這個紀錄。

### allow-main-thread-queries · MUST_NOT · new-only · manual

不得呼叫 `RoomDatabase.Builder.allowMainThreadQueries()`，測試碼也不行（測試用 `runTest` + `inMemoryDatabaseBuilder`）。

✗ `Room.databaseBuilder(context, AppDatabase::class.java, "app_database").allowMainThreadQueries().build()`
✓ `Room.inMemoryDatabaseBuilder(context, AppDatabase::class.java).build()`  // 測試

例外：無。

### manual-database-builder · MUST_NOT · new-only · manual

`Room.databaseBuilder(...)` 只能出現在 DI module 並以 singleton 提供；不得寫 `@Volatile` + double-checked `getInstance()`，也不得在 Repository / Activity / Fragment 內建立。DAO 同樣由 DI 提供。

✗ `AppDatabase.getInstance(application).chatNotificationDao()`
✓ `single { Room.databaseBuilder(get(), AppDatabase::class.java, "app_database").build() }`
✓ `single { get<AppDatabase>().chatNotificationDao() }`

例外：既有 `AppDatabase.getInstance()` 不主動移除（手寫 singleton 與 Koin 兩套並存中）→ [90-migration-ledger.md#m-22](90-migration-ledger.md)

### export-schema-off · MUST · new-only · manual

新增的 `@Database` 必須 `exportSchema = true`，以 Room Gradle plugin 的 `schemaDirectory` 指定輸出位置，產生的 schema JSON 必須 commit 進版控。

✗ `@Database(entities = [...], version = 1, exportSchema = false)`
✓ `@Database(entities = [...], version = 1, exportSchema = true)`

例外：既有 `AppDatabase` 目前為 `false`。補歷史 schema 屬前置基建 5，**不要**在功能 PR 內順手打開（會產生一份沒有對照基準的 schema）。
既有違規：1 個 database → [90-migration-ledger.md#m-22](90-migration-ledger.md)

### entity-change-no-migration · MUST · new-only+on-touch · manual

`AppDatabase` 是 `version = 1` / `exportSchema = false` / 0 個 migration，磁碟上**沒有任何 schema JSON**，`Room.databaseBuilder` 也沒掛 `.addMigrations(...)`。所以這條是守門規則，不是等基建：

**(A) 既有 2 個 entity（`ChatNotificationEntity` / `PushNotificationEntity`）的任何結構變更，一律先詢問使用者**，不得夾在功能 PR 裡改欄位 —— 沒有歷史 schema 就生不出 migration，升級時只有 crash 或靜默資料遺失兩種結果。
**(B) 新增獨立的 `@Entity` + DAO 不受限**（不動既有表），但同一個 PR 必須 bump `@Database(version = 2)`、補一支手寫 `Migration(1, 2)`（`CREATE TABLE` 語句從建置產物 `AppDatabase_Impl.createAllTables()` 原樣抄出），並在 `AppDatabase.getInstance()` 的 builder `.addMigrations(...)` 註冊。**`exportSchema = false` 下 `AutoMigration` 生不出來**（Room 找不到 from 版本的 schema JSON，編譯期就報錯），不要照官方範例寫 `autoMigrations`。
**(C) 真要改既有 entity**，先出一支獨立基建 PR：`exportSchema = true` + Room Gradle plugin 的 `schemaDirectory` + 把 version 1 的 schema JSON commit 進版控 + 一支 `MigrationTestHelper` 樣板測試。該 PR merge 後本條才適用完整官方要求（改名／刪除須附 `AutoMigrationSpec` 的 `@RenameColumn` / `@DeleteColumn`）。
**(D) 新的持久化需求優先評估 DataStore**，不要為單一 feature 開新 Room 表擴大 DB 表面積 —— Room 在本專案只服務通知，判準見 [datastore-as-database](#datastore-as-database)。

✗ 直接在 `ChatNotificationEntity` 加欄位、`version` 不動 ／ 加了 `autoMigrations = [AutoMigration(from = 1, to = 2)]` 卻沒開 `exportSchema`
✓ 新表：`@Database(entities = [..., XxxEntity::class], version = 2)` + `val MIGRATION_1_2 = object : Migration(1, 2) { override fun migrate(db: SupportSQLiteDatabase) { db.execSQL("CREATE TABLE IF NOT EXISTS ...") } }` + `.addMigrations(MIGRATION_1_2)`

例外：無。(A) 的「先詢問」不得用行內豁免略過。
既有違規：0 個 migration、`exportSchema = false` → [90-migration-ledger.md#m-22](90-migration-ledger.md)

### destructive-migration · MUST_NOT · new-only · manual

release build 不得使用 `fallbackToDestructiveMigration()`。確有必要時只能用範圍受限的 `fallbackToDestructiveMigrationFrom(...)` 或 `fallbackToDestructiveMigrationOnDowngrade()`，並在 PR 說明資料遺失的影響範圍。

✗ `Room.databaseBuilder(...).fallbackToDestructiveMigration().build()`
✓ `Room.databaseBuilder(...).addMigrations(MIGRATION_1_2).build()`

例外：無。

### dao-flow-no-distinct · SHOULD · new-only · manual

消費 Room 觀察型 `Flow` 時，若下游會觸發重繪或重新計算，必須加 `.distinctUntilChanged()` —— Room 只要該表有寫入就會重發，即使查詢結果沒變。

✗ `dao.getChatNotificationListFlow().map { it.toDomain() }`
✓ `dao.getChatNotificationListFlow().distinctUntilChanged().map { it.toDomain() }`

例外：下游終點是 `StateFlow`（本身已去重）。

---

## 二、DataStore 與 SharedPreferences

### datastore-duplicate-instance · MUST · new-only · manual

同一個 process 內，一個 DataStore 檔名只能有一個實例：用檔案頂層的 `by preferencesDataStore(name = ...)` delegate，或由 DI 提供 singleton。不得在類別內、函式內呼叫 `PreferenceDataStoreFactory.create` / `DataStoreFactory.create`。

✗ `class Helper(context: Context, dbName: String) { private val Context.dataStore by preferencesDataStore(name = dbName) }`
✓ 檔案頂層：`private val Context.settingsDataStore by preferencesDataStore(name = "settings")`

例外：無。既有 `DataStoreHelper` 就是 ✗ 的來源，不要照抄。

### datastore-io-uncaught · MUST · new-only · manual

DataStore 讀寫必須處理 `java.io.IOException`：寫入的 `edit {}` / `updateData {}` 包 try/catch，讀取在 `data` 上掛 `.catch { if (it is IOException) emit(emptyPreferences()) else throw it }`。

✗ `dataStore.edit { it[KEY_ONBOARDED] = true }`  // 磁碟錯誤直接崩潰
✓ `try { dataStore.edit { it[KEY_ONBOARDED] = true } } catch (e: IOException) { logger.w(e) }`

例外：無。不得改用 `catch (e: Exception)` 全吞，見 [11-coroutines-flow.md#swallow-cancellation](11-coroutines-flow.md)。

### datastore-sync-read · MUST_NOT · new-only · manual

DataStore 讀取一律以 `Flow` 暴露；需要單次值時只能在 suspend 函式內 `.first()`。不得為了同步取值而阻塞執行緒。

✗ `fun isOnboarded(): Boolean = runBlocking { dataStore.data.first()[KEY_ONBOARDED] ?: false }`
✓ `val isOnboarded: Flow<Boolean> = dataStore.data.map { it[KEY_ONBOARDED] ?: false }`

例外：無。`runBlocking` 的通則見 [11-coroutines-flow.md#run-blocking-prod](11-coroutines-flow.md)。

### datastore-json-blob · MUST_NOT · new-only · manual

不得把任意物件序列化成字串塞進 `stringPreferencesKey`（喪失型別安全，泛型集合反序列化會靜默失效）。純旗標用 typed Preferences key；有結構的設定物件用 `@Serializable` + `DataStoreFactory.create(serializer)` 的 JSON DataStore。

✗ `dataStore.edit { it[stringPreferencesKey(key)] = GsonInstance.gson.toJson(value) }`
✓ `dataStore.edit { it[booleanPreferencesKey("has_seen_onboarding")] = true }`

例外：既有 `DataStoreHelper.setAsync` / `getClass` 不主動改（24 檔在用），但新資料不得再走它。
既有違規：→ [90-migration-ledger.md#m-22](90-migration-ledger.md)

### ds-no-new-sharedpreferences · MUST_NOT · new-only · manual

不得新增 SharedPreferences **key** —— 包含 `PersistentManager`、`PreferencesHelper`、`PreferenceManager.getDefaultSharedPreferences()` 與直接的 `context.getSharedPreferences()`。新的偏好設定一律走 DataStore。

✗ `PersistentManager.putString(KEY_NEW_FEATURE_SEEN, value)`  // 新 key
✓ 檔案頂層 `private val Context.featureDataStore by preferencesDataStore(name = "feature")` + `booleanPreferencesKey("new_feature_seen")`

例外：既有 key 的讀寫維持原樣。**不要**因為觸碰到檔案就把既有 key 搬去 DataStore —— 涉及資料搬移風險，需獨立任務。
既有違規：357 檔（`PersistentManager` 219 / `PreferencesHelper` 111 / 直接使用 27）→ [90-migration-ledger.md#m-22](90-migration-ledger.md)

### datastore-as-database · SHOULD_NOT · new-only · manual

DataStore 不得用來存大量、需局部更新或有關聯完整性需求的資料（清單、快取、訂單集合）—— 每次寫入都會重寫整個檔案。這類資料放 Room。

✗ `DataStoreKey.KeyHotelCategorySearchHistory`（整份搜尋歷史清單序列化成單一 value）
✓ `@Entity(tableName = "hotel_search_history")` + DAO 的 `@Upsert` / `@Query("DELETE FROM ...")`

例外：筆數上限明確且很小（≤ 20 筆）、且永遠整份讀寫的清單。

---

## 三、離線優先（offline-first）

### offline-read-hits-network · MUST · new-only · manual

宣稱離線可用的 Repository，讀取方法只能查本地 DataSource 並回傳 `Flow`；網路資料只能透過寫入本地（`upsert`）間接影響讀取結果。同一個讀取方法不得依條件分別回傳網路或本地資料。

✗ `suspend fun getOrders() = if (isOnline) api.getOrders() else dao.getOrders()`
✓ `fun getOrdersStream(): Flow<List<Order>> = dao.getOrdersFlow().map { it.toDomain() }`
✓ `suspend fun refreshOrders() { dao.upsertAll(api.getOrders().toEntity()) }`

例外：不做本地快取的資料（即時報價、支付狀態）維持 online-only，但命名不得叫 `OfflineFirstXxxRepository`。

### offline-write-remote-first · MUST · new-only · manual

使用者產生的內容（收藏、備註、草稿、設定）採 lazy write：先寫本地 SSOT 讓 UI 立即反映，再排入同步（WorkManager）。金流、下單、退款等交易相反，必須 online-only —— 網路成功才寫本地，離線時 UI 停用該操作。

✗ 收藏：`api.addWish(id); dao.insert(id)`  // 離線完全不能收藏
✓ 收藏：`dao.insert(id); syncScheduler.enqueueWishSync()`
✓ 付款：離線時按鈕 disabled，不預寫任何本地成功狀態

例外：無。分不清屬於哪一類時**先詢問**，不要自行決定。

### sync-full-refetch · SHOULD · new-only · manual

Push-based 同步必須是增量：讀上次同步版本 → 拉 change list → 套用更新與刪除 → 更新版本號。衝突策略必須明確（last-write-wins 需在 model 帶 `lastModified`）。

✗ `suspend fun sync() { dao.deleteAll(); dao.upsertAll(api.getAll()) }`
✓ `suspend fun sync() { val since = versionStore.last(); val changes = api.getChanges(since); dao.applyChanges(changes); versionStore.save(changes.version) }`

例外：資料量極小且後端沒有 change list API 時可全量重抓，但需在 PR 說明。

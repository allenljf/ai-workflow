# 07 · 本地儲存

**管**：Room（DAO 簽章、資料庫建立、migration 與 schema、transaction、index）、DataStore（取代 SharedPreferences、實例管理、錯誤處理）、本地快取的失效責任。

**不管**：Repository 怎麼包 local + remote、offline-first 的整體資料流設計、Entity↔domain model 的分層與 mapper、網路層、加密與金鑰。

| 想找 | 去 |
|---|---|
| single source of truth、offline-first 的資料流、同步策略 | `05-data-layer` |
| Entity / DTO ↔ domain model 要幾層、mapper 放哪 | `05-data-layer` |
| Retrofit、JSON 序列化、HTTP 錯誤 | `06-network` |
| DAO Flow 該掛哪個 dispatcher、`stateIn`、Flow 錯誤 operator | `12-coroutines-flow` |
| `RoomDatabase` / `DataStore` 的 DI module 怎麼寫 | `03-dependency-injection` |
| in-memory Room、fake DataStore 的測試寫法 | `15-testing` |
| 資料庫加密、敏感資料是否該落地 | `17-security` |

UI 層（含 ViewModel）不得直接持有 `Dao` / `DataStore`，一律經 Repository——見 AGENTS.md 通用紅線 3。

---

### blocking-dao-function · MUST · new-only+on-touch · check: regex

DAO 的所有寫入（`@Insert` / `@Update` / `@Delete` / `@Upsert`）與非 Flow 的 `@Query` 必須宣告為 `suspend fun`。

✗ `@Query("SELECT * FROM orders WHERE id = :id") fun getOrder(id: String): OrderEntity?`  
✓ `@Query("SELECT * FROM orders WHERE id = :id") suspend fun getOrder(id: String): OrderEntity?`

例外：Paging 3 的 `PagingSource<Int, OrderEntity>` 回傳型別不加 `suspend` ｜ 來源：https://developer.android.com/training/data-storage/room/async-queries

### suspend-on-flow-dao-query · MUST · new-only · check: regex

觀察型查詢回傳 `Flow<T>` 且**不得**加 `suspend`。Room 產生的 Flow 本身即非阻塞，加上 `suspend` 會編譯失敗或造成語義混淆。

✗ `@Query("SELECT * FROM orders") suspend fun observeOrders(): Flow<List<OrderEntity>>`  
✓ `@Query("SELECT * FROM orders") fun observeOrders(): Flow<List<OrderEntity>>`

例外：無 ｜ 來源：https://developer.android.com/training/data-storage/room/async-queries

### allow-main-thread-queries · MUST_NOT · migrate · check: regex

不得呼叫 `RoomDatabase.Builder.allowMainThreadQueries()`，測試碼亦不使用（改用 `runTest`）。

✗ `Room.databaseBuilder(...).allowMainThreadQueries().build()`  
✓ DAO 全部 `suspend` 或回傳 `Flow`，移除該呼叫

例外：無 ｜ 來源：https://developer.android.com/training/data-storage/room/async-queries

### multiple-room-database-instances · MUST · new-only+on-touch · check: regex

同一個 database 檔在 process 內只能有一個 `RoomDatabase` 實例。多個實例會各自持有連線與 invalidation tracker，A 實例的寫入不會通知 B 實例的觀察型 Flow，畫面就此停在舊資料。`Room.databaseBuilder` 只能出現在 DI module 並以 singleton 提供，不得寫在 Repository、Activity 或自製 `getInstance()`。

✗ `class DefaultOrderRepository { private val db = Room.databaseBuilder(ctx, AppDatabase::class.java, "app.db").build() }`  
✓ `@Provides @Singleton fun provideDatabase(@ApplicationContext ctx: Context): AppDatabase = Room.databaseBuilder(...).build()`

例外：測試使用 `Room.inMemoryDatabaseBuilder` ｜ 來源：官方 sample nowinandroid

### schema-change-without-migration · MUST · new-only+on-touch · check: manual

任何 `@Entity` 的結構變更（新增／刪除／改名欄位或表）必須同時 bump `@Database(version = N)` 並提供對應的 `@AutoMigration` 或手寫 `Migration`。改名／刪除必須附 `AutoMigrationSpec`（`@RenameColumn` / `@DeleteColumn` / `@RenameTable` / `@DeleteTable`），否則 Room 無法推斷意圖。

✗ Entity 加了欄位，`version` 維持不變  
✓ `@Database(entities = [OrderEntity::class], version = 3, autoMigrations = [AutoMigration(from = 2, to = 3)])`

例外：App 尚未發佈第一版、線上沒有任何舊 schema 時可直接改 ｜ 來源：https://developer.android.com/training/data-storage/room/migrating-db-versions

### untested-migration · MUST · new-only · check: manual

每個新增的 migration（含 AutoMigration）必須有一支 `MigrationTestHelper` 測試：以舊版建庫並寫入資料 → 執行遷移 → 斷言資料仍在且欄位正確。只驗證 schema 不驗證資料等於沒測。

✗ 只新增 `Migration(2, 3)`，沒有對應測試  
✓ `helper.createDatabase(TEST_DB, 2).apply { execSQL("INSERT INTO orders ..."); close() }` 後 `helper.runMigrationsAndValidate(TEST_DB, 3, true)` 並查詢比對

例外：無 ｜ 來源：https://developer.android.com/training/data-storage/room/migrating-db-versions

### export-schema-disabled · MUST · new-only · check: regex

`@Database` 必須設定 `exportSchema = true`，並以 Room Gradle plugin 的 `schemaDirectory` 指定輸出位置，產出的 schema JSON 必須 commit 進版控——沒有它就無法寫 migration 測試。

✗ `@Database(entities = [...], version = 1, exportSchema = false)`  
✓ `exportSchema = true` + `room { schemaDirectory("$projectDir/schemas") }`

例外：無 ｜ 來源：https://developer.android.com/training/data-storage/room/migrating-db-versions

### destructive-migration-in-release · MUST_NOT · migrate · check: regex

release build 不得使用 `fallbackToDestructiveMigration()`——它會在 schema 不符時直接清空使用者資料。

✗ `Room.databaseBuilder(...).fallbackToDestructiveMigration().build()`  
✓ 提供 `Migration`；確有必要時只用 `fallbackToDestructiveMigrationFrom(2, 3)` 或 `fallbackToDestructiveMigrationOnDowngrade()`

例外：純快取用途、資料可由 server 完整重建的 database，需在 DI 提供處註解說明並在 PR 標示資料遺失影響 ｜ 來源：https://developer.android.com/training/data-storage/room/migrating-db-versions

### multi-write-without-transaction · MUST · new-only+on-touch · check: manual

必須原子完成的多步寫入要收進 DAO 的 `@Transaction` 方法，不得在 Repository 內連續呼叫多個 DAO 方法。帶 `@Relation` 的查詢與跨表 JOIN 的讀取同樣需要 `@Transaction`，否則可能讀到不一致的中間狀態。

✗ Repository 內 `dao.deleteAll(); dao.insertAll(items)`（中間崩潰即資料全失）  
✓ `@Transaction suspend fun replaceAll(items: List<OrderEntity>) { deleteAll(); insertAll(items) }`

例外：單一 SQL 即完成的 DAO 方法本身已是一個 transaction，不需另加 ｜ 來源：https://developer.android.com/training/data-storage/room

### unindexed-filter-column · SHOULD · new-only · check: manual

出現在 `WHERE` / `JOIN` / `ORDER BY` 的欄位，以及所有 foreign key 欄位，必須建 index。缺 foreign key index 時 Room 會發出編譯警告，不得忽略。

✗ `@Entity data class OrderEntity(@PrimaryKey val id: String, val userId: String)` 搭配 `WHERE userId = :userId`  
✓ `@Entity(tableName = "orders", indices = [Index(value = ["userId"])])`

例外：資料列數固定且極少（數十筆）的設定表，index 的寫入成本大於查詢收益 ｜ 來源：https://developer.android.com/training/data-storage/room

### room-flow-without-distinct · SHOULD · new-only · check: manual

消費 Room 觀察型 `Flow` 且下游會觸發重繪或重新計算時，加 `.distinctUntilChanged()`。Room 在該表**任何**變更時都會重發，即使查詢結果沒變。

✗ `dao.observeOrders().map { it.map(OrderEntity::asDomainModel) }`  
✓ `dao.observeOrders().distinctUntilChanged().map { it.map(OrderEntity::asDomainModel) }`

例外：下游立刻收斂進 `StateFlow`（本身會比對相等值）時可省略 ｜ 來源：https://developer.android.com/training/data-storage/room/async-queries

### new-sharedpreferences-usage · MUST_NOT · new-only · check: regex

不得新增 `SharedPreferences` 或 `PreferenceManager.getDefaultSharedPreferences()` 的使用；新的偏好設定一律走 DataStore。既有 SharedPreferences 只允許讀取與漸進遷移，不得擴充新 key。

✗ `context.getSharedPreferences("settings", MODE_PRIVATE).edit().putBoolean("dark", true).apply()`  
✓ `dataStore.edit { it[DARK_THEME] = true }`

例外：第三方 SDK 強制要求時，包在單一 wrapper 類別內並註明原因 ｜ 來源：https://developer.android.com/topic/libraries/architecture/datastore

### datastore-instance-per-call · MUST · new-only+on-touch · check: regex

同一個 process 內每個 DataStore 檔名只能有一個實例：用 top-level `by preferencesDataStore(name = ...)` delegate，或由 DI 以 singleton 提供。不得在函式或類別內呼叫 `PreferenceDataStoreFactory.create` / `DataStoreFactory.create`。重複建立會拋出檔案已被使用的例外。

✗ `fun store(ctx: Context) = PreferenceDataStoreFactory.create { ctx.preferencesDataStoreFile("settings") }`  
✓ `private val Context.settingsDataStore by preferencesDataStore(name = "settings")`

例外：無 ｜ 來源：https://developer.android.com/topic/libraries/architecture/datastore

### unhandled-datastore-io-exception · MUST · new-only+on-touch · check: regex

DataStore 的讀取 Flow 必須攔截 `IOException` 並回退到預設值，寫入的 `edit {}` / `updateData {}` 必須 try/catch `IOException`。磁碟錯誤不應讓 App 崩潰。

✗ `val theme: Flow<Boolean> = dataStore.data.map { it[DARK_THEME] ?: false }`  
✓ `dataStore.data.catch { if (it is IOException) emit(emptyPreferences()) else throw it }.map { ... }`

例外：無 ｜ 來源：https://developer.android.com/topic/libraries/architecture/datastore

### runblocking-datastore-read · MUST_NOT · new-only+on-touch · check: regex

不得用 `runBlocking { dataStore.data.first() }` 做同步讀取。讀取一律暴露為 `Flow`，需要單次值時在 `suspend` 函式內 `.first()`。

✗ `val isFirstRun = runBlocking { dataStore.data.first()[FIRST_RUN] ?: true }`  
✓ `suspend fun isFirstRun(): Boolean = dataStore.data.first()[FIRST_RUN] ?: true`

例外：無 ｜ 來源：https://developer.android.com/topic/libraries/architecture/datastore

### datastore-for-relational-data · SHOULD_NOT · new-only · check: manual

不得用 DataStore 儲存大量、需要局部更新或有關聯完整性需求的資料（清單、快取、實體集合）。DataStore 每次寫入都是整檔重寫。這類資料存 Room。

✗ `Preferences.Key<String>` 存整包訂單清單的 JSON 字串  
✓ `OrderEntity` + `OrderDao`；DataStore 只放旗標與單一設定物件

例外：極小且整體讀寫、無查詢需求的資料 ｜ 來源：https://developer.android.com/topic/libraries/architecture/datastore

### datastore-without-corruption-handler · SHOULD · new-only · check: regex

以 `DataStoreFactory.create` 建立型別化 DataStore 時要掛 `ReplaceFileCorruptionHandler`。檔案損毀後若無處理器，每次讀取都會拋 `CorruptionException`，使用者只能重裝 App。

✗ `DataStoreFactory.create(serializer = UserSettingsSerializer) { ctx.dataStoreFile("settings.json") }`  
✓ `DataStoreFactory.create(serializer, corruptionHandler = ReplaceFileCorruptionHandler { UserSettings() }) { ... }`

例外：`preferencesDataStore` delegate 使用者可透過同名參數提供，未提供時視情況接受 ｜ 來源：https://developer.android.com/topic/libraries/architecture/datastore

### unbounded-local-cache · MUST · new-only · check: manual

落地的快取資料必須有明確的清除途徑：TTL 欄位（寫入時記 `cachedAt`，讀取或同步時淘汰過期列）、筆數上限，或至少在登出／切換帳號時整表清空。不得只寫不清而讓資料庫無限成長，也不得把別人的資料留在裝置上。

✗ `@Entity data class SearchResultEntity(...)` 只有 `upsert`，沒有任何刪除路徑  
✓ Entity 加 `cachedAt: Long`，同步時 `@Query("DELETE FROM search_results WHERE cachedAt < :expiry") suspend fun evictExpired(expiry: Long)`；登出時 `clearAllTables()`

例外：使用者自己產生且需長期保留的資料（草稿、離線收藏）不是快取，不適用 ｜ 來源：業界共識

寫入路徑該 local-first 還是 remote-first、single source of truth 怎麼選、同步與衝突處理，由 `05-data-layer` 定義。

---

## 尚無定論（以下是建議，不是規則）

**DataStore 選 Preferences / JSON / Proto**：官方三者並列，官方 sample 使用 Proto。建議少數彼此無關的旗標（深色模式、是否看過引導頁）用 Preferences DataStore，成本最低；有結構的設定物件（多欄位、需一次交易更新）用 JSON DataStore——直接複用專案既有的 kotlinx.serialization `@Serializable`，得到型別安全又不必引入 protobuf 建置流程。只有需要跨 process 共享或極在意序列化體積時才選 Proto。

**Room 主版本升級**：新主版本涉及 artifact / package 改名、必須呼叫 `setDriver()`、`Migration.migrate` 簽章改變、`MigrationTestHelper` 建構參數改變，且要求註解處理器全面走 KSP。這是 breaking change，建議獨立成一個 PR，不與功能開發混在一起，並把所有既有 migration 測試完整跑過——migration 是升級中風險最高的部分。目前版本運作正常且無跨平台需求時，延後升級是合理決定。

**註解處理器**：Room 的 compiler 建議用 KSP 而非 KAPT（編譯較快，且新主版本不支援 KAPT）。

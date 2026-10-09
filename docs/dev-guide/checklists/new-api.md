# Checklist · 新 API 串接

依「新增 API + 取用流程」的標準路徑逐層檢查。

## 動工前

- [ ] 已讀 `00-red-lines.md` + `06-network.md` + `05-data-layer.md` + `04-domain-layer.md`
- [ ] 已確認 API spec：endpoint、method、request/response 完整欄位、錯誤碼、分頁方式
- [ ] 已確認這支 API 屬於哪個既有 `*ApiService`，還是要新開一個
- [ ] 已確認回傳資料要不要快取／離線可用 → 要的話讀 `07-persistence.md`

## 1. Retrofit Service（`:data:networking:api`）

- [ ] 用 `suspend fun`，**不是** `Call<T>` / `Observable<T>` / `Single<T>` — `retrofit-non-suspend`
- [ ] 回傳**具名 DTO**，不是 `suspend fun <T>: B2CApiResponse<T>` 泛型抹除 — `api-no-type-erasure`
      （專案有 198 個泛型抹除 endpoint + 256 處雙重 Gson 轉換，不要再增加）
- [ ] 參數用 `@Query` / `@Path` / `@Body`，沒有手拼 URL
- [ ] 命名照既有慣例（`IXxxApiService`）
- [ ] 樣板參考：`libs/networking/api/.../service/presale/IPresaleChatApiService.kt`

## 2. DTO（`:data:model`）

- [ ] **新建的 DTO 檔案**用 kotlinx.serialization（`@Serializable` + `@SerialName`）
- [ ] 在既有 Gson DTO 檔案加欄位時維持 `@SerializedName`，**沒有同 class 混用兩套註解**（見 91-decisions D-14）
- [ ] DTO 只是資料容器，沒有業務邏輯、沒有 `KoinComponent`、沒有 `by inject()`
- [ ] 可為 null 的欄位有正確標註，沒有靠 `!!` 硬轉
- [ ] 有 `toDomain()` 或對應 mapper，DTO 不會外流到 domain / UI — `dto-in-ui`

## 3. Domain 契約（`:domain:contract`）

- [ ] Repository **介面**定義在 `:domain:contract` — `repository-needs-interface`
- [ ] 介面方法用 domain model，不是 DTO
- [ ] 介面方法是 `suspend fun`（一次性）或回傳 `Flow`（會變動的資料）
- [ ] 沒有 `import android.*`、沒有 import data 實作 — `android-in-domain` / `domain-imports-impl`

## 4. Repository 實作（`:data:repository`）

- [ ] 類別命名 `XxxRepositoryImpl`，實作 `:domain:contract` 的介面
- [ ] `CoroutineDispatcher` 由建構子注入，沒有硬寫 `Dispatchers.IO` — `hardcoded-dispatcher`
- [ ] suspend 函式自己負責 main-safe（內部 `withContext(ioDispatcher)`） — `suspend-not-main-safe`
- [ ] DTO → domain model 的轉換在這一層完成
- [ ] 錯誤有轉成 domain error，沒有直接把 `HttpException` 往上丟
- [ ] `catch (e: Exception)` 有先處理 `CancellationException` — `swallow-cancellation`
- [ ] 沒有空 catch、沒有 `printStackTrace()` — `empty-catch` / `print-stacktrace`
- [ ] 用對了 `ApiResult`（專案有兩個同名的，見 `05-data-layer.md`）
- [ ] 沒有 `Gson()` 直接 new — `raw-gson`

## 5. UseCase（`:domain:usecase`，選用）

- [ ] 有商業邏輯或 ≥2 個 ViewModel 會用 → 開 UseCase；純轉發也可接受（見 91-decisions D-13）
- [ ] 只依賴 `:domain:contract` 的介面
- [ ] 用 `operator fun invoke` 單一入口 — `usecase-single-invoke`
- [ ] 命名 `[動詞][名詞]UseCase`

## 6. DI 綁定

- [ ] 介面 → 實作的綁定有註冊
- [ ] 用建構子注入，沒有 `by inject()` 在非白名單位置 — `service-locator-get`
- [ ] 新模組用 Koin annotation 風格（`@Single` / `@Factory` + `@ComponentScan`），照 `presale_chat` 樣板
- [ ] **沒有**寫 Hilt / `javax.inject`（本專案不採用，見 91-decisions D-01）
- [ ] 新增 `@Module` 或新增綁定 → 有一支 `verify()` 測試 — `koin-module-not-verified`

## 7. ViewModel 取用

- [ ] ViewModel 依賴 UseCase 或 Repository **介面**，不是 `ApiService`
- [ ] 沒有對外暴露 Mutable 型別 — `mutable-state-exposed`
- [ ] loading / error 有反映到 UiState

## 8. 測試

- [ ] Repository 有單元測試（成功 / API 錯誤 / 網路錯誤 / 空資料 至少 3 條路徑）
- [ ] UseCase 有單元測試（紅線 H3）
- [ ] 用手寫 Fake 而非 `mockk(relaxed = true)` — `prefer-fakes-over-mocks`
- [ ] 用 `runTest` + 注入的 `TestDispatcher`，沒有 `Thread.sleep` — `thread-sleep-test`
- [ ] 斷言驗的是行為與回傳值，不只是 `coVerify` 參數轉發
- [ ] 樣板參考：`libs/feature/presale_chat/src/test/.../GetPresaleOtherFaqsUseCaseTest.kt`

## 9. 安全

- [ ] 沒有硬編碼 token / key / 密碼（紅線）
- [ ] 敏感欄位不會被 log 出來（release build 尤其） — 見 `18-security.md`
- [ ] 認證 header 走既有 interceptor，沒有自己加

## 收尾

- [ ] `./gradlew :data:networking:api:compileDevelopDebugKotlin` 等相關模組編譯通過
- [ ] detekt 通過
- [ ] 測試綠燈
- [ ] 跑過 `/guide-audit` 且必修項為 0
- [ ] PIN 已同步（跑 `/axis-sync`，API 變更需更新 PIN Card 的 api 欄位）

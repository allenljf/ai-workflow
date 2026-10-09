# Checklist · 串接 API

依 [AGENTS.md](../AGENTS.md) 的實作順序：契約 → 資料 → 業務 → 注入 → 使用。

## 動工前

- [ ] 已讀 `guides/06-network.md` + `05-data-layer.md` + `04-domain-layer.md`
- [ ] API 規格已確認：endpoint、method、完整的 request/response 欄位、錯誤碼、分頁方式
- [ ] 已確認回傳資料要不要快取或離線可用 → 要的話讀 `guides/07-persistence.md`
- [ ] 已確認這支 API 屬於哪個既有的 service 介面，還是要新開

## ① 契約

- [ ] Repository 介面定義在 domain 層
- [ ] 方法是 `suspend fun`（一次性）或回傳 `Flow`（會變動的資料）
- [ ] 用 domain model，不是 DTO
- [ ] 沒有 `android.*` import

## ② Retrofit service

- [ ] `suspend fun`，不是 `Call<T>` / RxJava 型別
- [ ] 回傳具名 DTO，不是泛型型別參數（泛型會退化成 map 再二次轉換，且無編譯期型別安全）
- [ ] 參數用 `@Query` / `@Path` / `@Body`，沒有手拼 URL
- [ ] service 介面本身沒有業務邏輯

## ③ DTO

- [ ] 用 kotlinx.serialization（`@Serializable` + `@SerialName`）
- [ ] **不得同一個 class 混用兩套序列化註解**（`@Serializable` 與 Gson 的 `@SerializedName`）
- [ ] 可為 null 的欄位正確標註，沒有靠 `!!` 硬轉
- [ ] 欄位有合理預設值，後端少傳欄位不會直接崩
- [ ] DTO 只是資料容器，沒有業務方法、沒有注入依賴
- [ ] 有 `toDomain()` 或對應 mapper

## ④ Repository 實作

- [ ] 命名 `DefaultXxxRepository` / `XxxRepositoryImpl`，實作 domain 的介面
- [ ] `CoroutineDispatcher` 由建構子注入，沒有硬寫
- [ ] `suspend` 函式自己 `withContext(ioDispatcher)`
- [ ] DTO → domain model 的轉換在這一層完成
- [ ] HTTP 錯誤轉成 domain error，沒有把 `HttpException` / `IOException` 往上丟
- [ ] `catch (e: Exception)` 有先處理 `CancellationException`
- [ ] 沒有空 catch、沒有把例外吞掉只印 log
- [ ] 錯誤模型與專案其他 Repository 一致（見 `guides/05-data-layer.md`）

## ⑤ 網路設定

- [ ] 沒有在 Repository / UseCase / ViewModel 內建立 `OkHttpClient` 或 `Retrofit`
- [ ] 認證 header 走既有的 interceptor 或 `Authenticator`，沒有每支 API 自己加
- [ ] timeout 有設定（連線／讀取／寫入）
- [ ] retry 只用在冪等請求（GET），非冪等的不重試
- [ ] release build 不會輸出 request/response body

## ⑥ UseCase（選用）

- [ ] 有商業邏輯或跨 ViewModel 重用才開
- [ ] 只依賴 domain 介面
- [ ] `operator fun invoke` 單一入口

## ⑦ DI

- [ ] service 由 DI 提供，不是自己 `Retrofit.create()`
- [ ] Repository 介面 → 實作的綁定已註冊
- [ ] Dispatcher 用 `@Qualifier` 區分

## ⑧ 使用端

- [ ] ViewModel 依賴 Repository 介面或 UseCase，不是 `ApiService`
- [ ] loading / error 有反映到 UiState
- [ ] 錯誤有轉成使用者看得懂的訊息（不是把 exception message 直接顯示）

## ⑨ 測試

- [ ] Repository 有測試：成功／HTTP 錯誤／網路異常／空資料 至少 3 條路徑
- [ ] mapper 有測試，特別是 null 與缺欄位的情況
- [ ] 用 fake 或 `MockWebServer`，不要打真實 API
- [ ] 用 `runTest` + 注入的 `TestDispatcher`

## 安全

- [ ] 沒有硬編碼 API key / token / 密碼
- [ ] 敏感欄位不會出現在 log
- [ ] 若涉及個資或金流，額外讀 `guides/17-security.md`

## 收尾

- [ ] 編譯 + 測試 + 靜態檢查通過
- [ ] `python3 android-dev-guide/tools/check-rules.py` 無必修項

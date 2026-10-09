# AI 參照指南索引

> **使用說明**：分析 Jira 工單前，先閱讀本索引確認相關主題，再查閱對應文件。

---

## 文件清單

| 文件 | 主題 | 狀態 |
|------|------|------|
| [02-modules.md](./02-modules.md) | 模組結構、職責、依賴關係、問題類型 → 模組對照表 | ✅ 完成 |
| [01-architecture.md](./01-architecture.md) | 架構模式（Clean Architecture + Reductor）、ViewModel/UseCase/Repository 互動 | ✅ 完成 |
| [03-ui-patterns.md](./03-ui-patterns.md) | Compose vs XML 用法、Fragment/Activity 結構、Navigation | ✅ 完成 |
| [04-di-koin.md](./04-di-koin.md) | Koin 模組位置、@Factory/@Single 慣例、DI 綁定方式 | ✅ 完成 |
| [05-networking.md](./05-networking.md) | Retrofit 結構、API 層、Token 管理、錯誤處理 | ✅ 完成 |
| [06-data-layer.md](./06-data-layer.md) | Repository pattern、Room、DataStore/SharedPreferences | ✅ 完成 |
| [07-concurrency.md](./07-concurrency.md) | Coroutines 用法、LiveData、Reductor 狀態管理 | ✅ 完成 |
| [08-naming-conventions.md](./08-naming-conventions.md) | 命名規則、檔案放置規範、程式碼慣例 | ✅ 完成 |
| [09-feature-examples.md](./09-feature-examples.md) | 典型功能完整路徑範例（信用卡、商品詳情、訂單憑證）| ✅ 完成 |

---

## 專案基本資訊

- **語言**：Kotlin
- **minSdk**：24 / **targetSdk**：35 / **JDK**：17
- **DI**：Koin（KSP annotation）
- **網路**：Retrofit + OkHttp + Gson/kotlinx.serialization
- **狀態管理**：Reductor（漸進遷移中）
- **UI**：XML Views + Jetpack Compose 混合

---

## 總模組數

- 應用層：1
- Domain 層：2
- Data 層：6
- Feature 層：17+
- Shared 層：20+
- Build 基礎設施：2

**總計：約 59+ 模組**

---

*持續更新中，每次 Step 分析完成後更新此索引*

## 相關筆記
- [02-modules](02-modules.md)
- [03-ui-patterns](03-ui-patterns.md)
- [05-networking](05-networking.md)
- [06-data-layer](06-data-layer.md)
- [jira-analyze-flow](jira-analyze-flow.md)
- [jira-auto-analysis-pipeline](workflow/jira-auto-analysis-pipeline.md)
- [order-detail-compose](features/order-detail-compose.md)
- [sku-activity-shell](features/sku-activity-shell.md)

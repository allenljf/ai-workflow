# 在新專案導入

新專案的優勢是沒有既有違規，所以可以直接全開。

---

## 1. 複製指南

```bash
cp -r android-dev-guide/ /path/to/your-project/
```

整個資料夾是自足的，沒有對外依賴（除了 `tools/check-rules.py` 需要 PyYAML）。

---

## 2. 建立專案骨架

依 [guides/02-modularization.md](../guides/02-modularization.md) 的模組分類建立：

```
:app
:core:designsystem     Theme、token、共用 Compose 元件
:core:data             Repository 實作
:core:domain           UseCase（選用，有商業邏輯時才需要）
:core:model            domain model
:core:network          Retrofit service、DTO
:core:database         Room entity、DAO
:core:common           純工具（不含 Android 相依）
:core:testing          測試用 fake、rule、測資
:feature:xxx           一個功能一個模組
```

小專案不需要一開始就全部建 —— 但**分層要從第一天就正確**，
因為分層錯誤是唯一難以後補的技術債（其他都可以漸進改善）。

---

## 3. 建置設定

必要項（依 [guides/02-modularization.md](../guides/02-modularization.md)）：

- Gradle version catalog（`gradle/libs.versions.toml`）
- convention plugin（`build-logic/`），不要用 `buildSrc`
- KSP，不要 KAPT
- Compose compiler 隨 Kotlin plugin（Kotlin 2.0 起不需要 `composeOptions`）

建議一開始就設好，之後補的成本高很多：

| 設定 | 為什麼要早 |
|---|---|
| Room `exportSchema = true` | 沒有歷史 schema 就無法做 AutoMigration，補不回來 |
| Compose stability configuration file | 晚做要回頭掃全部 UiState |
| `koin-test` / Hilt 測試依賴 | DI 圖驗證越早接越省事 |
| Turbine | Flow 測試的標準工具 |
| detekt 套用到**所有**模組 | 只套 `:app` 等於沒套 |
| CI 跑 lint 與稽核腳本 | 沒有 CI 把關的規則會慢慢失效 |

---

## 4. 接上檢查

```bash
# pre-commit
python3 android-dev-guide/tools/check-rules.py --staged || exit 1

# CI
python3 android-dev-guide/tools/check-rules.py --diff origin/main --format github
```

新專案直接讓它擋 —— 從第一天就乾淨，比之後補容易一百倍。

---

## 5. 接上 AI 工具

見 [integrating-ai-tools.md](integrating-ai-tools.md)。

---

## 6. 第一個功能怎麼寫

照 [AGENTS.md](../AGENTS.md) 的實作順序：契約 → 資料 → 業務 → 注入 → 狀態 → 畫面 → 測試。

第一個功能建議刻意寫「完整」一次（即使它很簡單），讓團隊有個可參照的樣板：

- Repository 介面在 domain、實作在 data
- DTO 與 domain model 分開，有 mapper
- UseCase（就算是 pass-through）
- Hilt module 綁定
- 單一 `UiState` data class + ViewModel 暴露 `StateFlow`
- stateless content composable + stateful screen
- UseCase / Repository / ViewModel 三支單元測試
- content composable 的 `@Preview` 涵蓋 loading / empty / error / success

之後所有功能照抄這個結構。**團隊內部的樣板比任何文件都有效** ——
人會抄旁邊的程式碼，不會去讀規範。

---

## 值得一開始就決定的三件事

這三件事後期改的成本極高，建議專案啟動時就定案並寫進你的 ADR：

1. **錯誤模型**：Repository 拋 exception 還是回 `Result`？UI 怎麼拿到可顯示的訊息？
   見 [guides/05-data-layer.md](../guides/05-data-layer.md)。中途改會動到每一條資料流。

2. **one-off event 的處理方式**：events-as-state 還是 Channel？
   見 [guides/08-ui-state.md](../guides/08-ui-state.md)。中途改會動到每個 ViewModel 與收集端。

3. **設計系統的 token 結構**：primitive / semantic / component 三層怎麼切？深色模式要不要支援？
   見 [guides/14-design-system.md](../guides/14-design-system.md)。
   **深色模式尤其要早決定** —— 如果 token 設計成編譯期常數而非 theme-aware，
   後期要支援深色模式等於重做整套設計系統。

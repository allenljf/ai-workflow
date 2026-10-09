# KKday Android 開發準則（dev-guide）

這是本專案的**強制開發準則庫**。目的是讓任何人（含 AI agent）在新增需求、新增畫面、串接 API、重構既有功能時，都寫出同一套現代化、官方推薦的程式碼，而不是各憑喜好或照抄專案裡的舊寫法。

> **核心立場**：準則優先於「專案既有寫法」。既有寫法與準則衝突時，**以準則為準**，並把無法立即修的部分記入 [90-migration-ledger.md](90-migration-ledger.md)。

---

## 一、準則來源優先序

判斷任何做法對錯時，依此順序：

| 順位 | 來源 | 說明 |
|-----|------|------|
| 1 | **Google 官方文件** | developer.android.com 的明文建議，特別是 [Architecture recommendations](https://developer.android.com/topic/architecture/recommendations) |
| 2 | **Google 官方 sample** | [android/nowinandroid](https://github.com/android/nowinandroid)、architecture-samples 的實際做法 |
| 3 | **業界主流共識** | 官方沒有立場時（如 Retrofit 設定細節、MVI 樣板），採業界普遍做法 |
| 4 | **本專案既有寫法** | 只有在 1～3 都沒有答案，或本專案有特殊限制時才參考 |

準則檔中每條規則都標註來源。看到 `來源：專案決策` 的，代表是本專案自行定案（如設計系統 token、埋點規範）。

---

## 二、四項專案定案

這四項已經定案，**不需要每次重新討論**：

| 項目 | 定案 | 說明 |
|------|------|------|
| **依賴注入** | **一律 Koin，annotation 風格** | 本專案評估後**明確不採用 Hilt** —— 不是「未來方向」，也不是「等前置條件」，是不做。新舊模組一律 `@Module` + `@ComponentScan` + `@Single` / `@Factory` / `@KoinViewModel` + 建構子注入。**寫任何 Hilt / Dagger / `javax.inject` 註解一律 review 退回。** 決策見 [91-decisions.md](91-decisions.md) D-01，技術理由見 [90-migration-ledger.md](90-migration-ledger.md) M-27，寫法見 [03-di.md](03-di.md) |
| **UI 狀態架構** | **MVVM + UDF**（官方寫法） | ViewModel 暴露單一 `StateFlow<UiState>`，事件用 method call。不寫新的 Reductor，見 [08-ui-state.md](08-ui-state.md) |
| **UI 技術** | 新畫面一律 **Compose**，禁止新增 XML | 既有 XML 畫面維持，重構時才轉。「新畫面」判定表見 [91-decisions.md](91-decisions.md) D-03 |
| **強制範圍** | **新程式碼強制 + 觸碰即修**（細分四級） | 見下方 enforce 說明 |

---

## 三、規則的兩個維度

每條規則都有兩個獨立標籤。**兩個都要看**：`level` 說「錯得多嚴重」，`enforce` 說「什麼時候必須修」。只看 level 會讓人在既有檔案裡不知道該不該動手。

### level：嚴重度

| 等級 | 意義 |
|------|------|
| **MUST** / **MUST NOT** | 官方明確要求，或違反會產生 bug、洩漏、無法測試 |
| **SHOULD** / **SHOULD NOT** | 官方建議做法，例外需在 PR 說明理由 |
| **MAY** | 可選，依情境判斷 |

### enforce：強制時機

| 級 | 代號 | 定義 | 強制點 |
|----|------|------|--------|
| **A** | `new-only` | 新增檔案 100% 符合 | lint 對 Write 全文稽核 → ERROR |
| **B** | `on-touch` | 你本次改到的函式/區塊要符合 | lint 對 Edit 只稽核新增內容 → ERROR |
| **C** | `migrate` | 既有違規不阻斷 PR，登記遷移帳，以專案級任務批次處理 | lint 降為 WARN |
| **D** | `exempt` | 本專案明確不採用；`rules.yaml` 必須寫 `reason` | lint 不檢查 |

常見組合是 `new-only+on-touch`（新檔案全符合 + 改到的地方順手修）。

**本專案不使用 `dormant`（待啟用）。所有規則都是現在就能執行的。** 2026-08 改版把原本 13 條 `dormant` 全數清掉：能降低要求的就降到專案做得到的程度，缺基建的改寫成「沒有基建時的替代做法」，確定不做的標 `exempt` 並附理由。原因是 `dormant` 對開發者等於「這條現在不算數」—— 規則存在卻沒有任何指導效果。**新規則一律不得標 `dormant`**：做不到就寫做得到的版本，或標 `exempt`。基建缺口本身登記在 [90-migration-ledger.md](90-migration-ledger.md) 的「前置基建」節，做完是加強規則，不是解鎖規則。

**沒有標 `enforce` 的規則視為 `migrate`。**

不要為了「順便重構」把 PR 擴散到十幾個檔案。`on-touch` 的邊界是**你本來就要改的那個檔案**。無法在本次修完的，寫入 [90-migration-ledger.md](90-migration-ledger.md)。

### 誤報處理

自動稽核由 `.claude/hooks/dev-guide-lint.py` 執行。確認誤報時可加行內豁免：

```kotlin
val ioDispatcher = Dispatchers.IO // dev-guide-ignore: hardcoded-dispatcher
```

加豁免時**必須在 PR 或回覆中說明理由**，不得無聲豁免。

---

## 三之二、rules.yaml 是唯一真相源

[rules.yaml](rules.yaml) 是機器可讀的規則索引，**每條規則的 id / level / enforce / owner / check 只在這裡定義一次**。

```yaml
- id: hardcoded-dispatcher
  level: MUST_NOT
  enforce: new-only+on-touch
  owner: 11-coroutines-flow.md
  check: lint:hardcoded-dispatcher
  source: "官方 coroutines-best-practices"
```

三個規矩，違反就會讓整套機制失效：

1. **一條規則只有一個 owner 檔案。** 其他檔案只能寫一行 cross-ref（`→ 見 11-coroutines-flow.md#hardcoded-dispatcher`），**不得重述規則內容** —— 重述必然漂移成 MUST/SHOULD 不一致。
2. **rule id 全域唯一，且與 `dev-guide-lint.py` 的 id 完全一致。** 行內豁免用的就是這個 id，對不上等於豁免機制失效。
3. **規則正文只寫「可判定條件 + 一組正反例 + 檢查方式」，理由寫在 [91-decisions.md](91-decisions.md)。** 每條 ≤ 12 行，每檔 ≤ 250 行 / ≤ 25 條。

`dev-guide-router.py`（決定注入哪幾份）與 `dev-guide-lint.py`（決定回灌什麼訊息）都以 rules.yaml 為基準，md 與 hook 因此不會漂移。一致性由 `scripts/check-dev-guide.py` 在 CI 檢查。

---

## 四、路由表：這次任務該讀哪幾份？

### 依場景（優先看這個）

| 場景 | Checklist | 必讀準則 |
|------|-----------|---------|
| 新功能／新需求 | [checklists/new-feature.md](checklists/new-feature.md) | 01, 02, 03, 04, 05 |
| 新畫面／新頁面 | [checklists/new-screen.md](checklists/new-screen.md) | 08, 09, 10, 12, 13 |
| 新 API 串接 | [checklists/new-api.md](checklists/new-api.md) | 04, 05, 06, 03 |
| 重構／修 bug（觸碰即修） | [checklists/refactor-on-touch.md](checklists/refactor-on-touch.md) | 01, 90 + 對應領域 |

### 依技術領域

| 檔案 | 範圍 | 什麼時候讀 |
|------|------|-----------|
| [00-red-lines.md](00-red-lines.md) | 不可協商紅線 | **每次都讀**，最短 |
| [rules.yaml](rules.yaml) | 機器可讀規則索引（唯一真相源） | 查某條規則的 enforce 級別、owner、檢查方式 |
| [01-architecture.md](01-architecture.md) | 分層、SSOT、UDF、依賴方向 | 任何新功能、任何重構 |
| [02-modularization.md](02-modularization.md) | 模組類型、命名、依賴規則（本專案為水平分層） | 新增模組、跨模組互動、Gradle 改動 |
| [03-di.md](03-di.md) | Koin annotation 寫法、綁定生命週期、qualifier、module 驗證（本專案不採用 Hilt） | 任何要注入依賴的地方 |
| [04-domain-layer.md](04-domain-layer.md) | UseCase、Repository 介面、domain model | 寫業務邏輯 |
| [05-data-layer.md](05-data-layer.md) | Repository 實作、DataSource、model 分層、**錯誤模型 owner** | 取資料、存資料 |
| [06-network.md](06-network.md) | Retrofit、OkHttp、序列化（含 Gson↔kotlinx 共存） | 串接 API |
| [07-persistence.md](07-persistence.md) | Room、DataStore、離線優先 | 本地儲存 |
| [08-ui-state.md](08-ui-state.md) | MVVM+UDF、UiState 設計、**one-off event owner**、ViewModel | 寫 ViewModel、設計畫面狀態 |
| [09a-compose-api.md](09a-compose-api.md) | Composable 慣例、modifier、參數順序、preview | 寫任何 Compose |
| [09b-compose-state.md](09b-compose-state.md) | state hoisting、side effect API 選擇、state holder | Compose 狀態與副作用 |
| [10-compose-performance.md](10-compose-performance.md) | 重組、穩定性、LazyList、三階段 | 列表、動畫、效能問題 |
| [11-coroutines-flow.md](11-coroutines-flow.md) | Flow/Channel 選型、**dispatcher owner**、scope、取消 | 任何非同步 |
| [12-navigation.md](12-navigation.md) | 導航原則、字串 route 慣例（2.7.7 無 type-safe route）、`:shared:routing` 跨模組導航 | 畫面跳轉 |
| [13-designsystem.md](13-designsystem.md) | StyleDictionary token、字串資源 | 任何 UI（紅線最密集） |
| [14-testing.md](14-testing.md) | 測試策略、fake vs mock、Compose UI test、假綠燈防治 | 寫測試（每個功能都要） |
| [15-performance.md](15-performance.md) | 啟動、記憶體、jank、baseline profile | 效能議題、Application 改動 |
| [16-tracking.md](16-tracking.md) | KKTracker 埋點、AXIS PIN、Compose 曝光追蹤 | 加埋點 |
| [17-interop-views-compose.md](17-interop-views-compose.md) | `ComposeView` / `AndroidView` / RxJava interop | **改既有 Fragment/Activity（本專案最高頻情境）** |
| [18-security.md](18-security.md) | token 儲存、PII 遮蔽、WebView、payment | 碰到認證、付款、log |
| [90-migration-ledger.md](90-migration-ledger.md) | 遷移帳：`migrate` 級規則的既有違規登記處 + 前置基建小型 PR 清單 | 重構前、遇到舊寫法時 |
| [91-decisions.md](91-decisions.md) | 已定案決策、被否決的選項、規則衝突裁決、`exempt` 規則 | 想知道「為什麼是這樣規定」 |

---

## 五、顧問 skill：不確定就先問

準則檔告訴你**規則是什麼**；顧問 skill 幫你**判斷這個情境該怎麼做**。有選型疑慮時先呼叫，不要自行決定。

| Skill | 什麼時候呼叫 |
|-------|-------------|
| `/dev-guide` | 不知道該讀哪些準則、想確認本次任務的完整檢查清單 |
| `/guide-architecture` | 這段邏輯該放哪一層？要不要開 UseCase？依賴方向對不對？ |
| `/guide-modularization` | 該開新模組還是塞現有模組？模組怎麼命名？跨模組怎麼接？ |
| `/guide-di` | 這個依賴該綁 `@Single` 還是 `@Factory`？qualifier 怎麼寫？綁不到怎麼查？（DI 框架不必問，一律 Koin） |
| `/guide-data` | Repository 怎麼切？model 要幾層？錯誤怎麼往上傳？ |
| `/guide-state` | UiState 要一個還是多個？loading/error 怎麼表達？one-off event 怎麼處理？ |
| `/guide-coroutines` | StateFlow / SharedFlow / Channel 選哪個？dispatcher 怎麼注入？ |
| `/guide-compose` | 這個 composable 怎麼拆？state 提到哪一層？該用哪個 side effect API？ |
| `/guide-navigation` | 跨模組怎麼導航？route 怎麼定義？參數怎麼傳？ |
| `/guide-testing` | 這個功能該測什麼？fake 還是 mock？測試怎麼寫才不是假綠燈？ |
| `/guide-performance` | 這段會不會影響啟動/重組/記憶體？怎麼量測？ |
| `/guide-audit` | 我改完了，幫我逐條稽核有沒有違規（PR 前自我檢查） |

---

## 六、強制機制怎麼運作

準則不靠自律，靠六層機制：

| 層 | 機制 | 觸發時機 | 強度 |
|----|------|---------|------|
| 1 | `CLAUDE.md` 路由段 | 每個 session 載入 | 提示 |
| 2 | `dev-guide-router.py`（UserPromptSubmit hook） | 每次你送出需求 | **自動注入必讀清單**，agent 一定看到 |
| 3 | 顧問 skill（`/guide-*`） | 主動呼叫 | 諮詢 |
| 4 | `dev-guide-lint.py`（PostToolUse hook） | 每次 Edit/Write `.kt` | **違規即時回灌**，毫秒級 |
| 5 | `post-kt-verify.py` + detekt | 每次 Edit/Write `.kt` | 編譯 + 靜態檢查 |
| 6 | `/guide-audit`、`/code-review`、`.githooks/pre-commit` | PR 前、commit 前 | 最後關卡 |

第 2 層與第 4 層是核心：**你不需要記得讀準則，hook 會告訴你讀哪幾份；你不需要記得每條規則，hook 會在你寫錯時當場指出。**

### 派發 subagent 時的注意事項

subagent **不會繼承** router hook 注入的 context。派發實作型 subagent（api-engineer / ui-engineer 等）時，必須把準則檔路徑原樣寫進它的 prompt，例如：

```
實作前先讀完這些準則檔，不得略過：
- docs/dev-guide/00-red-lines.md
- docs/dev-guide/08-ui-state.md
- docs/dev-guide/09a-compose-api.md
- docs/dev-guide/09b-compose-state.md
```

---

## 七、準則要改怎麼辦

準則不是聖經，過時就要改。但改法有規矩：

1. **不要在實作中偷偷偏離**。有意見先提出，不要「這次先這樣」。
2. **提出變更**：說明哪條規則、為什麼不適用、有沒有官方或業界依據、影響哪些既有程式碼。
3. **有官方依據的優先**：Google 更新了建議 → 直接改準則，並在該條標註更新日期。
4. **改完要回頭看**：準則變更後，`90-migration-ledger.md` 要同步更新受影響項目。
5. **hook 規則要同步**：若新規則可自動偵測，加進 `.claude/hooks/dev-guide-lint.py` 的 `RULES`。

---

## 八、與既有流程的關係

本準則庫**不取代**既有的 OpenSpec / AXIS / feature-doc 流程，是插在它們之間的品質基準：

```
feature-analyze → sbe-analyze → sasd-analyze → task-breakdown → task-impl → code-review → pr-create
                                     ↑                              ↑            ↑
                              設計時遵守準則              實作時 hook 稽核    review 對照準則
```

| 既有機制 | 與 dev-guide 的關係 |
|---------|-------------------|
| `openspec/` specs & design | design.md 的技術決策必須符合準則；有衝突時以準則為準 |
| `axis/` PIN | 準則不管 PIN 命名，PIN 同步照舊走 `/axis-sync` |
| `docs/ai-guide/features/` | 描述「現在的程式碼長怎樣」（現況）；dev-guide 描述「該長怎樣」（標準）。兩者不一致時，dev-guide 是目標 |
| `docs/feature-impl/` | 功能實作說明，不含準則 |

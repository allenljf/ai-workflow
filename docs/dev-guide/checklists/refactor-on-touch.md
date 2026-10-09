# Checklist · 重構／修 Bug（觸碰即修）

這份的重點不是「修好功能」，而是**劃清該修到哪裡**。本專案多項違規是主流寫法而非少數例外，不劃界線就會出現 200 行的功能 PR。

## 先劃界線

- [ ] 已讀 `00-red-lines.md` + `90-migration-ledger.md`
- [ ] **列出本次真正需要修改的檔案**（修 bug 的話：造成問題的那幾個）
- [ ] 這份清單就是 `on-touch` 的邊界 —— 清單外的檔案不動

## 判斷每個既有違規該不該修

對你**改到的區塊**內的每個違規，查 `rules.yaml` 的 enforce：

```bash
grep -A6 "id: <rule-id>" docs/dev-guide/rules.yaml
```

- [ ] `new-only` → 既有的不動
- [ ] `on-touch` / `new-only+on-touch` → **修**（限你改到的函式/區塊）
- [ ] `migrate` → **不要在這個 PR 修**，登記到 `90-migration-ledger.md` 第九節
- [ ] `exempt` → 本專案不採用，不用管（本庫已無 `dormant`）

**明確不要在功能 PR 裡動的**（都是 `migrate` 級，改動風險大於收益）：

| 項目 | 既有規模 | 為什麼不動 |
|------|---------|-----------|
| 既有 Reductor 畫面改 MVVM | 752 處 dispatch | 架構級改動，需獨立規劃 |
| 既有 XML 畫面改 Compose | 1185 個 layout | 同上 |
| `notifyDataSetChanged` 改 DiffUtil | 105 檔 | 動畫、捲動位置、選取狀態都可能變 |
| M2 元件換 M3 | 374 檔 | 視覺會變，需設計確認 |
| Rx 鏈整段改 Flow | 194 檔 | 見 [touch-legacy-rx.md](touch-legacy-rx.md) |
| `BaseViewModel.showLoading` | 87 檔引用 | 改基底類別會炸整片 |
| DTO 換成 domain model | 269 個 Composable 檔 | 會擴散到整條呼叫鏈 |
| SharedPreferences 遷 DataStore | 357 檔 | 涉及資料搬移 |

## 修 Bug 專用

- [ ] **先寫出能重現 bug 的測試**（紅燈），再修 → 見 `14-testing.md`
- [ ] 修完該測試轉綠，且**沒有註解掉任何既有斷言**
- [ ] 確認根因，不是只讓症狀消失
- [ ] 同類問題在別處有沒有？有的話寫進 PR 描述（不一定要一起修）
- [ ] 沒有為了讓測試過而放寬斷言

## 重構專用

- [ ] 重構前後**行為不變**（有測試保護；沒有的話先補測試再重構）
- [ ] 重構與功能變更**分開 commit**（review 才看得懂）
- [ ] 沒有順手改無關的檔案
- [ ] 若重構會改變公開 API，已確認呼叫端影響範圍

## 順手修的品質底線

在你改到的區塊內，這些是低風險高收益、**應該順手修**的：

- [ ] `collectAsState()` → `collectAsStateWithLifecycle()` — `collect-as-state`
- [ ] public Mutable 狀態 → private `_x` + `asStateFlow()` — `mutable-state-exposed`
- [ ] 空 `catch {}` → 至少記錄或轉 domain error — `empty-catch`
- [ ] `catch (e: Exception)` 補上 `CancellationException` 處理 — `swallow-cancellation`
- [ ] `printStackTrace()` → 統一 logger — `print-stacktrace`
- [ ] hardcode 的 `.dp` / `Color(0x...)` → `StyleDictionary.kkXxx` token — `hardcoded-dimen` / `hardcoded-color`
- [ ] `items(list)` 補 `key` — `lazy-list-no-key`
- [ ] `Thread.sleep` in test → `advanceUntilIdle` — `thread-sleep-test`
- [ ] `window.statusBarColor` → `SystemBarLegacyCompat` — `legacy-system-bar`

這些**不要**順手修（風險 > 收益，或會擴散）：

- 改基底類別（`BaseViewModel` / `BaseActivity` / `BaseFragment`）
- 改 `AppState` 欄位
- 改共用 model 的型別
- 改 DI module 的既有綁定
- 升套件版本（紅線 A3，需先確認）

## 收尾

- [ ] 編譯 + detekt + 相關測試通過
- [ ] 跑過 `/guide-audit`，必修項為 0
- [ ] **本次未修的違規已登記** `90-migration-ledger.md` 第九節，格式：
      `- [rule-id] 檔案路徑 — 原因（PR 連結）`
- [ ] PR 描述有寫「本次刻意不修什麼、為什麼」

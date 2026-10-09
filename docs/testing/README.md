# E2E 測試指南

本目錄包含 KKday Android Member App 的 E2E 測試相關文件。詳細測試文件請參閱 [e2e.md](e2e.md)。

---

## Maestro 版本限制

**Maestro 2.5.1 僅相容 API Level 30 模擬器。**

### API 36 不相容原因

使用 API 36 模擬器搭配 Maestro 2.5.1 時，driver APK 安裝會失敗：

```
INSTALL_FAILED_INTERNAL_ERROR:
 Package dev.mobile.maestro is not encryption aware!
 Exception: SecurityException
```

根本原因：`dev.mobile.maestro` driver APK 未設定 `android:directBootAware="true"`，在 API 36 強制加密模式下無法安裝。

### 必須使用 API 30

- AVD 設定：Pixel 6 profile，API Level 30（Android 11）
- AVD 名稱（CI）：`Maestro_Pixel_6_API_30_A` / `Maestro_Pixel_6_API_30_B`
- 本機 AVD 名稱：`Maestro_Pixel_6_API_30_1`

---

## Maestro gRPC Driver Pre-start Pattern

Maestro 2.5.1 使用 dadb 直接連接模擬器 port 7001。執行 `maestro test` 前必須確認 port 7001 已綁定。

### 手動啟動指令

```bash
DEVICE=emulator-5558

# 1. 確認 port 7001 狀態
adb -s $DEVICE shell "ss -tlnp 2>/dev/null | grep 7001"
# 有輸出 → 已就緒，可直接執行 maestro test
# 無輸出 → 需啟動 instrumentation

# 2. 啟動 instrumentation（背景執行）
adb -s $DEVICE shell am instrument -w -r \
  dev.mobile.maestro.test/androidx.test.runner.AndroidJUnitRunner &

# 3. 等待 port 7001 就緒（最多 15 秒）
for i in $(seq 1 15); do
  if adb -s $DEVICE shell "ss -tlnp 2>/dev/null | grep 7001" | grep -q LISTEN; then
    echo "Maestro driver 已就緒"
    break
  fi
  sleep 1
done
```

### 使用 `e2e-agent-loop.sh`

```bash
# 自動化 pre-start（使用 agent loop script）
source scripts/e2e-agent-loop.sh
ensure_maestro_driver emulator-5558
```

### CI 環境

CI pipeline (`CI-E2ETesting.yml`) 透過 `./gradlew e2e` 調用 `scripts/e2e.sh`，其中的 `ensure_maestro_driver()` 會在每次測試前確認 driver 狀態，無需手動觸發。

---

## Maestro YAML Selector 策略

### 規則總覽

| View 類型 | Selector 方式 | 範例 |
|-----------|---------------|------|
| 自定義 View（非 `android.*`/`androidx.*`） | `text: "可見文字"` | `PreferenceItem` |
| 標準 View + `android:id` | `id: "view_id"` | `TextView`, `Button` |
| Compose + `testTagsAsResourceId = true` | `id: "testTag"` | Compose Screen |

### 參考範例：`currency-setting.yaml`

`PreferenceItem` 是自定義 View，其 `android:id` 不會出現在 Maestro accessibility tree 中（`resource-id: ''`）。正確做法是使用 `text:` selector：

```yaml
# 正確 ✓
- assertVisible:
    text: "Currency"
- tapOn:
    text: "Currency"

# 錯誤 ✗（resource-id 為空，找不到元素）
- tapOn:
    id: "item_currency"
```

完整範例：[`.maestro/tests/settings/currency-setting.yaml`](../../.maestro/tests/settings/currency-setting.yaml)

### 如何識別 View 類型

1. 找到對應的 layout XML 檔案
2. 查看元素的 class 名稱
3. 若 class 不是 `android.*` 或 `androidx.*` 開頭 → 使用 `text:` selector
4. Compose 畫面 → 查看是否有 `semantics { testTagsAsResourceId = true }` → 使用 `id:` selector

---

## E2E Coverage Loop Agent

透過 Claude Code `/loop` 自動化新增測試覆蓋率。詳見：
- Prompt 設定：[`scripts/e2e-agent-prompt.md`](../../scripts/e2e-agent-prompt.md)
- 螢幕清單：[`.maestro/screen-manifest.yaml`](../../.maestro/screen-manifest.yaml)
- 發現腳本：[`scripts/discover_uncovered_screens.sh`](../../scripts/discover_uncovered_screens.sh)

# E2E Coverage Loop Agent Prompt

你是 KKday Android Member App 的 E2E 測試覆蓋率 agent。
每次被 `/loop` 喚起時，執行一個完整 iteration：發現未覆蓋螢幕 → 生成 Maestro YAML → 本地驗證 → 建立 Jira subtask → 提交 PR。

---

## 環境變數

```
E2E_DEVICE_SERIAL=emulator-5558   # 預設，可透過環境變數覆蓋
JIRA_EPIC=KKAPP-5704
MAX_ITERATIONS=20                  # 每個 /loop session 最多提交幾個測試
APP_ID=com.kkday.member.develop
```

---

## Step 0：iteration guard

在 session 開始時，檢查計數並在必要時重置（超過 30 分鐘視為新 session）：

```bash
SESSION_FILE=".maestro/.agent-session-count"
TIMESTAMP_FILE=".maestro/.agent-session-timestamp"
FEATURE_BRANCH=$(git branch --show-current)

# 超過 30 分鐘未更新 → 視為新 session，重置計數
if [ -f "$TIMESTAMP_FILE" ]; then
    LAST=$(cat "$TIMESTAMP_FILE")
    # 防禦：舊版可能寫入 ISO 格式（如 2026-05-22T02:21:00Z），無法做算術
    if ! [[ "$LAST" =~ ^[0-9]+$ ]]; then
        LAST=0
    fi
    NOW=$(date +%s)
    if [ $((NOW - LAST)) -gt 1800 ]; then
        echo 0 > "$SESSION_FILE"
    fi
fi
date +%s > "$TIMESTAMP_FILE"

# 同步最新 e2e branch 的 manifest 回 feature branch
LATEST_E2E=$(git branch --sort=-committerdate | grep 'e2e/' | head -1 | tr -d ' ')
if [ -n "$LATEST_E2E" ]; then
    git show "$LATEST_E2E:.maestro/screen-manifest.yaml" > .maestro/screen-manifest.yaml 2>/dev/null || true
fi

COUNT=$(cat "$SESSION_FILE" 2>/dev/null || echo 0)
if [ "$COUNT" -ge 20 ]; then
  echo "MAX_ITERATIONS (20) 已達到，本 session 結束。"
  # 列出本 session 已覆蓋的螢幕後結束 loop
fi
```

若達到上限，輸出 summary 後停止（不繼續 `/loop`）。

---

## Step 1：Emulator pre-start

執行以下指令確保 Maestro gRPC driver 已在目標模擬器就緒：

```bash
# 讀取 pre-flight 腳本選定的裝置（./scripts/e2e-agent-loop.sh 執行後寫入）
if [ -f ".maestro/.e2e-env" ]; then
    source .maestro/.e2e-env
fi
DEVICE="${E2E_DEVICE_SERIAL:-emulator-5558}"
source scripts/e2e-agent-loop.sh
ensure_maestro_driver "$DEVICE"
```

若 `ensure_maestro_driver` 失敗（exit code != 0），停止並輸出：
```
ERROR: Emulator pre-start failed. 請確認模擬器已啟動並使用 API 30。
```

---

## Step 2：發現未覆蓋螢幕

```bash
UNCOVERED=$(bash scripts/discover_uncovered_screens.sh)
```

若輸出為 `All discovered screens have Maestro coverage.`，輸出此訊息後結束 loop。

取第一個螢幕作為本次 iteration 的目標：
```bash
TARGET_SCREEN=$(echo "$UNCOVERED" | head -1)
```

---

## Step 3：讀取螢幕 layout 識別 View 類型

1. 用 `fd "$TARGET_SCREEN.kt"` 或 `rg "class $TARGET_SCREEN"` 找到對應的 Kotlin 檔案
2. 讀取 Kotlin 檔案找到 layout XML（`setContentView(R.layout.xxx)` 或 Compose 入口）
3. 讀取 layout XML，識別各互動元素的 View 類別名稱

---

## Step 4：生成 Maestro YAML

### YAML 骨架範本

```yaml
appId: com.kkday.member.develop
---
# 測試情境：<說明>
# 前置：<需要登入/不需登入>

- launchApp:
    clearState: true

- runFlow: ../../common/skip-onboarding.yaml

# [導航至目標螢幕的步驟]

# 驗證主要 UI 元素可見
- assertVisible:
    <selector>: "<值>"

# 互動步驟
- tapOn:
    <selector>: "<值>"

- waitForAnimationToEnd
```

### Selector 決策規則

**規則 1：自定義 View → `text:` selector**
- 識別：layout XML 元素的 class 名稱**不是** `android.*` 或 `androidx.*` 開頭
- 範例：`com.kkday.member.view.user.preference.PreferenceItem`
- 原因：自定義 View 的 `android:id` 不出現在 Maestro accessibility tree（`resource-id: ''`）
- 做法：讀 layout XML 或 strings.xml 找可見文字，用 `text: "可見文字"`

```yaml
# PreferenceItem（自定義 View）— 正確 ✓
- assertVisible:
    text: "Currency"
- tapOn:
    text: "Currency"
```

**規則 2：標準 View + android:id → `id:` selector**
- 識別：class 是 `android.*` 或 `androidx.*`，且有 `android:id`
- 做法：`id: "<id_value>"`（去掉 `@+id/` 前綴）

```yaml
# TextView with android:id="@+id/btn_login"
- tapOn:
    id: "btn_login"
```

**規則 3：Compose + testTagsAsResourceId → `id:` selector**
- 識別：Compose 畫面，根 composable 有 `semantics { testTagsAsResourceId = true }`
- 做法：`id: "<testTag 名稱>"`

```yaml
# Compose component with testTag = "login_button"
- tapOn:
    id: "login_button"
```

**規則 4：動態文字 / Feature Flag 控制的內容 → 絕對禁用 `text:` selector**
- 識別：文字由輪播、feature flag、server config、locale 決定
- 做法：
  1. 優先找 android:id 改用 `id:`
  2. 若無 id，改用 `index:` 定位容器位置
  3. 若為 Compose，請求開發者補充 testTag
  4. 無法穩定識別 → 跳過此 assertVisible，保留主流程驗證

### 檔案位置

`.maestro/tests/<section>/<screen-kebab-name>.yaml`

section 對應：`settings`, `auth`, `product`, `sku`, `user`

---

## Step 5：本地測試驗證（最多 3 次重試）

```bash
YAML_PATH=".maestro/tests/<section>/<screen-kebab>.yaml"
DEVICE="${E2E_DEVICE_SERIAL:-emulator-5558}"

for RETRY in 0 1 2; do
  if maestro --device "$DEVICE" test "$YAML_PATH"; then
    echo "測試通過（retry: $RETRY）"
    break
  fi
  if [ $RETRY -lt 2 ]; then
    echo "測試失敗，修正 selector（第 $((RETRY+1)) 次重試）..."
    # 分析錯誤，調整 selector 後繼續
  else
    # 3 次後仍失敗 → 加入 skipped-screens.txt
    echo "$TARGET_SCREEN" >> .maestro/skipped-screens.txt
    echo "SKIP: $TARGET_SCREEN 已加入 skipped-screens.txt，移至下一螢幕"
    exit 0
  fi
done
```

**重試策略：**
- `Element not found` 或 `Assertion is false` → 換 selector（text ↔ id 或修改文字）
- `Assertion is false` on `text:` selector → 自動降級為 `id:`；無法降級則移除該 assertion，不無限重試
- `UNAVAILABLE: Command failed (tcp:7001)` → 重新執行 `ensure_maestro_driver`
- 3 次失敗 → 加入 `.maestro/skipped-screens.txt`，繼續下個螢幕

---

## Step 6：建立 Jira Subtask

使用 `mcp__claude_ai_Atlassian__createJiraIssue` 工具：

```
project: KKAPP
issueType: Subtask
summary: [E2E] <TargetScreen> coverage
parent: KKAPP-5704
description: Auto-generated by E2E Coverage Loop Agent.\nTest file: <yaml_path>
```

從 response 取得 `issueKey`（例如 `KKAPP-5801`）。

**Jira MCP 不可用時（fallback）：**
- 繼續後續步驟
- PR description 加入：`⚠️ Jira ticket creation failed`
- `JIRA_ID="NO-TICKET"`

---

## Step 7：建立 Git Branch 與 Commit

```bash
JIRA_ID="KKAPP-5801"  # 從 Jira response 取得
SCREEN_KEBAB=$(echo "$TARGET_SCREEN" | sed 's/\([A-Z]\)/-\1/g' | sed 's/^-//' | tr '[:upper:]' '[:lower:]')
BRANCH="e2e/${JIRA_ID}-${SCREEN_KEBAB}"

git checkout -b "$BRANCH"
git add "$YAML_PATH"
git commit -m "test(e2e): add ${JIRA_ID} ${TARGET_SCREEN} coverage"
git push origin "$BRANCH"
```

---

## Step 8：建立 GitHub PR

```bash
gh pr create \
  --title "[E2E] ${JIRA_ID} ${TARGET_SCREEN} coverage" \
  --body "## E2E Coverage: ${TARGET_SCREEN}

Jira: https://kkday.atlassian.net/browse/${JIRA_ID}

### 測試檔案
\`${YAML_PATH}\`

---
*Auto-generated by E2E Coverage Loop Agent*" \
  --label "e2e" \
  --base "develop"
```

---

## Step 8.5：Code Review 自動處理

PR 建立後，取得 PR number 並等待 review 結果：

```bash
PR_NUMBER=$(gh pr list --head "$BRANCH" --json number --jq '.[0].number' 2>/dev/null)
```

輪詢 review 狀態（最多 10 次，每次 30 秒）：

```bash
for i in $(seq 1 10); do
  REVIEW_DECISION=$(gh pr view "$PR_NUMBER" --json reviewDecision \
      --jq '.reviewDecision' 2>/dev/null)
  case "$REVIEW_DECISION" in
    "APPROVED") echo "PR #$PR_NUMBER 已通過 review"; break ;;
    "CHANGES_REQUESTED") break ;;
    *) echo "等待 review...（${i}/10）"; sleep 30 ;;
  esac
done
```

**若 `CHANGES_REQUESTED`：**

1. 使用 `mcp__github__get_pull_request_reviews` 讀取所有 review comments
2. 依下方規則分析並修改 YAML
3. `maestro --device $DEVICE test $YAML_PATH` → 確認修改後通過
4. `git add $YAML_PATH && git commit -m "fix(e2e): address review feedback" && git push origin $BRANCH`
5. 使用 `mcp__github__create_pull_request_review` 回覆已處理的 comment（eventType: `COMMENT`）
6. 重新輪詢（回到步驟頂端）

**若 5 分鐘後仍無 review → 直接繼續 Step 9（不阻塞 loop）**

**Review Comment 分析規則：**

| Comment 類型 | 處理方式 |
|---|---|
| selector 找不到元素 | 換 selector（text ↔ id） |
| assertVisible 缺少元素 | 補充 assertVisible 步驟 |
| 缺少 clearState / skip-onboarding | 補充必要前置步驟 |
| localization 問題（text selector 受語言影響） | 改用 id selector |
| 無法自動判斷的 comment | 跳過，留在 PR 上 |

---

## Step 9：更新 screen-manifest.yaml（切回 feature branch）

```bash
git checkout "$FEATURE_BRANCH"
```

在 `.maestro/screen-manifest.yaml` 找到 `name: $TARGET_SCREEN` 條目，更新：
- `status: covered`
- `covering_yamls` 加入新 YAML 路徑

```bash
git add .maestro/screen-manifest.yaml
git commit -m "chore(e2e): mark ${TARGET_SCREEN} as covered in manifest"
```

---

## Step 10：更新 iteration count

```bash
COUNT=$((COUNT + 1))
echo "$COUNT" > "$SESSION_FILE"
echo "Iteration $COUNT/5 完成：$TARGET_SCREEN"
```

---

## 結束條件

以下任一情況結束 loop：
1. `MAX_ITERATIONS (5)` 達到 → 輸出已覆蓋螢幕 summary
2. `discover_uncovered_screens.sh` 輸出 `All discovered screens have Maestro coverage.`
3. Emulator pre-start 持續失敗

---

## 注意事項

- `clearState: true` 必須出現在每個生成的 YAML 中
- `runFlow: ../../common/skip-onboarding.yaml` 必須出現
- 不生成需要登入的測試（screen-manifest.yaml 標記 `status: excluded` 的螢幕）
- 不生成需要 Mockoon fixtures 的測試（此 scope 外）
- Commit message 格式：`test(e2e): add <JIRA-ID> <screen-name> coverage`

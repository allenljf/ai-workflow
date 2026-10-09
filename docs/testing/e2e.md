# Maestro E2E 測試指南

Maestro + Mockoon 的 E2E 測試框架，用於自動化測試 Android App 的 UI 流程。

---

## 目錄

1. [架構概覽](#架構概覽)
2. [環境安裝](#環境安裝)
3. [本機執行測試](#本機執行測試)
4. [Flow 語法速查](#flow-語法速查)
5. [Mockoon 運作原理](#mockoon-運作原理)
6. [新增測試](#新增測試)
7. [除錯技巧](#除錯技巧)
8. [請 AI 撰寫測試的 Prompt 指南](#請-ai-撰寫測試的-prompt-指南)

---

## 架構概覽

```
Android App (develop/stage build)
        ↑ HTTP 請求
Mockoon Server (port 3001)
  ├── 有 mock 規則的路由 → 回傳假資料（固定情境）
  └── 其他路由 → proxy 轉發到真實 SIT API
        ↑ 驅動 UI
Maestro CLI
  └── .maestro/tests/**/*.yaml
```

**兩種測試類型：**

| 類型 | appId | API 來源 | 使用時機 |
|------|-------|----------|----------|
| **Auth / 有 Mockoon** | `com.kkday.member.develop` | Mockoon → SIT proxy | 需要控制 API 回應（錯誤情境、固定 OTP）|
| **SKU / Product** | `com.kkday.member.stage` | 直連 Stage API | 測試真實商品頁面流程，需 VPN |

---

## 環境安裝

```bash
# 安裝 Maestro CLI
curl -Ls "https://get.maestro.mobile.dev" | bash
export PATH="$HOME/.maestro/bin:$PATH"

# 安裝 Mockoon CLI
npm install -g @mockoon/cli

# 驗證安裝
maestro --version
mockoon-cli --version
adb devices
```

**安裝 APK（擇一）：**

```bash
# Auth 測試用（develop build，搭配 Mockoon）
./gradlew installDevelopDebug

# SKU/Product 測試用（stage build，直連 Stage API）
./gradlew installStageDebug
```

> **注意**：執行 develop build 需連線公司 VPN（SIT proxy 需要）；stage build 同樣需要 VPN。

---

## 本機執行測試

### 執行 Auth 類測試（需先啟動 Mockoon）

```bash
# 步驟 1：啟動 Mockoon mock server（以 otp-login-complete 為例）
mockoon-cli start --data mockoon/tests/auth/otp-login-complete.json --port 3001

# 步驟 2：執行對應的 Maestro flow
maestro test .maestro/tests/auth/otp-login-complete.yaml
```

### 執行 SKU / Product 類測試（直連 Stage，不需 Mockoon）

```bash
maestro test .maestro/tests/sku/sku-10759.yaml
```

### 執行整個目錄

```bash
# 執行所有 auth 測試（需先手動啟動對應的 Mockoon）
maestro test .maestro/tests/auth/

# 執行單一測試
maestro test .maestro/tests/auth/login-email-success.yaml
```

### 互動式探索（找 UI element ID）

```bash
# 開啟 Studio，可以點擊 App 並查看元素 ID
maestro studio

# 只看 UI hierarchy（適合在 CI/終端機環境）
maestro hierarchy
```

### 截圖輸出路徑

flow 中的 `${SCREENSHOT_PATH}` 變數，本機執行時預設輸出到 `~/.maestro/tests/<timestamp>/screenshots/`。

---

## Flow 語法速查

### 基本結構

```yaml
appId: com.kkday.member.develop   # 每個 flow 頂端聲明 appId
---
# 啟動 App（clearState: true 會清除登入狀態、快取）
- launchApp:
    clearState: true

# 引用共用子流程
- runFlow: ../../common/skip-onboarding.yaml
```

### 常用指令

```yaml
# 點擊（優先使用 id，再用 text）
- tapOn:
    id: "button_login"
- tapOn:
    text: "Send verification code"
- tapOn:
    text: ".*Email.*"        # 支援正則

# 輸入文字
- inputText: "test@example.com"

# 按下按鍵
- pressKey: "back"           # 關閉鍵盤

# 等待動畫結束
- waitForAnimationToEnd

# 等待元素出現（帶超時）
- extendedWaitUntil:
    visible:
      id: "otp_verification_screen"
    timeout: 30000           # 毫秒

# 可選等待（元素不存在也不會失敗）
- extendedWaitUntil:
    visible:
      id: "indicator_bar_txt"
    timeout: 10000
    optional: true
- tapOn:
    id: "indicator_bar_txt"
    optional: true

# 斷言
- assertVisible: "Jason Ni"
- assertVisible:
    id: "button_login_success_setting"
- assertVisible:
    text: ".*驗證碼錯誤.*"   # 支援正則

# 截圖（CI 時輸出到指定目錄）
- takeScreenshot: ${SCREENSHOT_PATH}/login_success

# 捲動到元素可見
- scrollUntilVisible:
    element:
      text: "Package Options"
    direction: DOWN
    timeout: 30000

# 用 Deep Link 啟動到特定頁面（SKU 測試常用）
- launchApp:
    clearState: false
    arguments:
      url: "https://www.stage.kkday.com/zh-tw/product/10759"
```

### 選擇器優先順序

```
1. id          → 最穩定，優先使用
2. text        → 語意清楚，但多語系需注意
3. text 正則   → 彈性匹配（e.g. ".*驗證碼.*"）
4. index       → 多個同名元素時用（index: 0/1/2）
5. 座標        → 最後手段，設備相依
```

---

## Mockoon 運作原理

### 兩種 Mockoon 檔案

**`.scenario.json`（規則定義）：** 輕量的人類可讀格式，描述路由規則，用 script 產生完整的 `.json`。

```json
{
  "name": "otp-verify-error-states",
  "port": 3001,
  "proxyHost": "https://api-b2c-217.sit.kkday.com/api/",
  "output": "mockoon/tests/auth/otp-verify-error-states.json",
  "routes": [
    {
      "method": "post",
      "endpoint": "v3/auth/login-otp/verify",
      "responses": [
        {
          "label": "驗證碼錯誤（otp_code=999999）",
          "default": false,
          "rules": [
            { "target": "body", "modifier": "otp_code", "operator": "equals", "value": "999999" }
          ],
          "body": { "metadata": { "status": "MBR-LOGIN-OTP-002", "desc": "驗證碼錯誤" } }
        },
        {
          "label": "Default — proxy fallback",
          "default": true,
          "body": { "metadata": { "status": "0000", "desc": "Success" } }
        }
      ]
    }
  ]
}
```

**`.json`（完整環境檔）：** Mockoon CLI 直接讀取的格式，包含所有路由與錄製的 API 回應，由 `.scenario.json` 生成或錄製產生。

### Proxy 模式

Mockoon 以 **proxy 模式**運作：只有設定了規則的路由會被 mock，其餘請求全部透明轉發到真實的 SIT/Stage API。這樣只需 mock 特定情境，不影響其他正常請求。

### Rules 匹配邏輯

| operator | 說明 | 範例 |
|----------|------|------|
| `equals` | 完全相等 | `otp_code = "999999"` |
| `regex` | 正則匹配 | `email` 包含 `"daily-limit"` |

規則命中時回傳對應 response，都不命中則使用 `"default": true` 的 response。

---

## 新增測試

### 情境 A：需要控制 API 回應（Auth 類）

需要同時新增 Mockoon 環境檔 + Maestro Flow 檔。

#### 步驟 1：建立 Mockoon scenario 檔

參考現有的 `.scenario.json`，在 `mockoon/tests/auth/` 新增：

```json
// mockoon/tests/auth/my-new-test.scenario.json
{
  "name": "my-new-test",
  "port": 3001,
  "proxyHost": "https://api-b2c-217.sit.kkday.com/api/",
  "output": "mockoon/tests/auth/my-new-test.json",
  "routes": [
    {
      "method": "post",
      "endpoint": "v3/auth/login-otp/send",
      "responses": [
        {
          "label": "成功回應",
          "default": true,
          "body": {
            "metadata": { "type": 0, "httpStatusCode": 200, "status": "0000", "desc": "Success" },
            "data": { "expires_in": 600 }
          }
        }
      ]
    }
  ]
}
```

#### 步驟 2：產生完整 Mockoon 環境檔

目前需手動或透過既有 script 將 `.scenario.json` 轉成 `.json`。  
快速方式：複製現有的 `.json` 並修改對應路由與規則。

#### 步驟 3：撰寫 Maestro Flow

```yaml
# .maestro/tests/auth/my-new-test.yaml
appId: com.kkday.member.develop
---
# 說明此 flow 測試的情境，以及對應的 mockoon 檔案

- launchApp:
    clearState: true

- runFlow: ../../common/skip-onboarding.yaml
- runFlow: ../../common/navigate-to-login.yaml

# 輸入觸發特定情境的 email
- tapOn:
    text: "Email"
- inputText: "test@example.com"

- tapOn:
    text: "Send verification code"
- waitForAnimationToEnd

- extendedWaitUntil:
    visible:
      id: "otp_verification_screen"
    timeout: 30000

# 驗證預期結果
- assertVisible:
    text: ".*預期文字.*"

- takeScreenshot: ${SCREENSHOT_PATH}/my_new_test_result
```

#### 步驟 4：本機驗證

```bash
# 啟動 Mockoon
mockoon-cli start --data mockoon/tests/auth/my-new-test.json --port 3001

# 執行 flow
maestro test .maestro/tests/auth/my-new-test.yaml
```

---

### 情境 B：測試真實商品頁面（SKU / Product 類）

只需新增 Maestro Flow，直接連 Stage API，不需要 Mockoon。

```yaml
# .maestro/tests/sku/sku-99999.yaml
appId: com.kkday.member.stage
---
# 測試商品 99999 的 SKU 選擇流程
# 直連 Stage API，需 VPN

- launchApp:
    clearState: false
    arguments:
      url: "https://www.stage.kkday.com/zh-tw/product/99999"

- runFlow: ../../common/skip-onboarding.yaml

- scrollUntilVisible:
    element:
      text: "Package Options"
    direction: DOWN
    timeout: 30000

- tapOn: Package Options
- tapOn:
    text: "Select"
    index: 0

# 驗證 SKU 選擇頁面出現
- assertVisible:
    text: ".*Adult.*"
```

---

## 除錯技巧

### 查找 UI 元素 ID

```bash
# 開啟 Maestro Studio（連接裝置後執行）
maestro studio

# 或直接 dump hierarchy
maestro hierarchy
```

### 查看失敗日誌

Maestro 失敗後的 debug 資料位於：
```
~/.maestro/tests/<timestamp>/
├── screenshot-*.png    # 失敗當下截圖
├── commands-*.json     # UI hierarchy 快照
└── maestro.log         # 執行日誌
```

### 常見問題

**元素找不到 → timeout**
- 先用 `maestro studio` 確認元素 ID 是否正確
- 增加 `extendedWaitUntil` 的 `timeout` 值
- 確認 App 版本與 appId 對應

**Mockoon 沒有 intercept 請求**
- 確認 App 打到的 port 是 3001（`runnerPort` 設定）
- 確認 Mockoon 環境檔的 `endpoint` path 完全正確（不含 base URL）
- 用 `mockoon-cli start --data <file> --port 3001 --log-transaction` 看詳細 log

**OTP 驗證碼**
- `otp-login-complete.json` 固定 OTP 為 `000000`
- `otp-verify-error-states.json` 中 `999999` → 驗證碼錯誤，`888888` → 驗證碼過期

---

## 請 AI 撰寫測試的 Prompt 指南

### 必要背景資訊

讓 AI 寫出可用的測試，prompt 中需提供：

1. **測試目標**：要測試什麼情境（成功/錯誤/邊界）
2. **API 端點與回應格式**：如果需要 Mockoon mock
3. **UI 元素 ID**：從 Maestro Studio 或 `maestro hierarchy` 取得的實際 ID
4. **測試類型**：Auth（需 Mockoon）或 SKU/Product（連 Stage）

### Prompt 範本

#### 範本 A：Auth 錯誤情境（需 Mockoon）

```
我要幫 KKday Android App 的登入功能新增一個 Maestro E2E 測試。

【情境】
測試使用者輸入已被停用的帳號，系統應顯示「帳號已停用」錯誤訊息。

【技術資訊】
- appId: com.kkday.member.develop
- API: POST v3/auth/login-otp/send
- 觸發條件: request body 中 email 包含 "disabled-account"
- 錯誤回應:
  {
    "metadata": { "status": "MBR-LOGIN-001", "desc": "此帳號已停用，請聯繫客服" },
    "data": null
  }

【UI 元素 ID】（從 maestro hierarchy 取得）
- Email 輸入框: text "Email"
- 發送驗證碼按鈕: text "Send verification code"
- 錯誤訊息區域: id "text_otp_send_error"

【現有共用流程】
- .maestro/common/skip-onboarding.yaml
- .maestro/common/navigate-to-login.yaml

【產出】
1. mockoon/tests/auth/login-disabled-account.scenario.json（Mockoon rules 定義）
2. .maestro/tests/auth/login-disabled-account.yaml（Maestro flow）

請參考以下現有範例的格式：
- mockoon/tests/auth/otp-verify-error-states.scenario.json
- .maestro/tests/auth/otp-verify-error-states.yaml
```

---

#### 範本 B：SKU 商品頁測試（連 Stage）

```
我要幫 KKday Android App 的商品頁新增一個 Maestro E2E 測試。

【情境】
測試商品 ID 55555 的加購流程：
1. 從 deep link 開啟商品頁
2. 捲動到 Package Options
3. 選擇第一個 package
4. 新增 1 位成人
5. 驗證總價正確顯示

【技術資訊】
- appId: com.kkday.member.stage
- 商品頁 deep link: https://www.stage.kkday.com/zh-tw/product/55555
- 直連 Stage API（不需要 Mockoon）

【預期 UI 元素】（需 AI 補全，或我再執行 maestro hierarchy 後提供）
- Package Options 文字
- Select 按鈕
- 成人加人按鈕 id: btn_plus_adult
- 價格顯示文字（例如 "US$25.00"）

【產出】
1. .maestro/tests/sku/sku-55555.yaml

請參考現有 .maestro/tests/sku/sku-10759.yaml 的格式。
```

---

#### 範本 C：新增共用子流程

```
KKday Android App 中，目前已有以下共用流程：
- .maestro/common/skip-onboarding.yaml
- .maestro/common/navigate-to-login.yaml

我需要新增一個共用流程 navigate-to-checkout.yaml，
用途：從已登入狀態導航到購物車頁面。

【UI 流程】
1. 等待首頁 tab bar 出現（id: tab_user）
2. 點擊購物車 tab（id: tab_cart）
3. 等待購物車頁載入（id: checkout_screen）

【格式要求】
- appId: com.kkday.member.develop
- 使用 extendedWaitUntil 而非 tapOn 的 timeout（Maestro 2.0.10+ 的限制）
- 請參考 .maestro/common/navigate-to-login.yaml 的寫法
```

---

### 提升 AI 輸出品質的技巧

1. **提供現有範例路徑**，讓 AI 參考格式：  
   `請參考 .maestro/tests/auth/otp-verify-error-states.yaml 的寫法`

2. **告知 Maestro 版本限制**：  
   `Maestro 2.0.10 起 tapOn 不支援 timeout，需改用 extendedWaitUntil`

3. **明確指定 optional 元素**：  
   `skip-onboarding 步驟中的元素是 optional 的（非首次啟動不會出現）`

4. **提供截圖命名慣例**：  
   `截圖命名格式：${SCREENSHOT_PATH}/功能_情境 (e.g. otp_login_daily_limit_error)`

5. **指定錯誤訊息驗證方式**：  
   `錯誤訊息用正則匹配，例如 text: ".*驗證碼錯誤.*"（避免完整字串比對的脆弱性）`

---

## CI/CD 整合

PR 發出時，CI 會自動執行 E2E 測試（`CI-E2ETesting-Feature.yml`）：

- **Feature 模式**：只執行與此次 PR 差異相關的測試（透過 git diff 判斷）
- **Release 模式**：執行所有 `.maestro/tests/` 下的 flow

測試結果會以 PR comment 形式回報，包含通過/失敗數、截圖連結、覆蓋率數據。

---

## 參考資源

- [Maestro 官方文件 - Commands](https://maestro.mobile.dev/api-reference/commands)
- [Maestro 官方文件 - Selectors](https://maestro.mobile.dev/api-reference/selectors)
- [Mockoon CLI 文件](https://github.com/mockoon/mockoon/blob/main/packages/cli/README.md)
- 覆蓋率報告說明：[coverage-report-delta-explanation.md](coverage-report-delta-explanation.md)

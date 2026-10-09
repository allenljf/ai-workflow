# 任務列表 API 技術規格（給 iOS 對接用）

以下兩支 API 用於任務列表，**回傳格式相同**，差別在請求參數與使用情境（未登入 vs 已登入）。

---

## 1. 未登入任務列表

**用途**：使用者未登入時，取得可展示的任務列表（通常為預覽用）。

| 項目 | 說明 |
|------|------|
| **Method** | `GET` |
| **Path** | `v2/mission/list/un_login` |
| **Query 參數** | 見下表 |
| **Request Body** | 無 |

### Query 參數

| 參數名 | 型別 | 必填 | 說明 |
|--------|------|------|------|
| `country_code` | string | 選填 | 國家代碼（如 `TW`），用於依地區回傳任務。 |

### 回傳資料（Response）

- 與後端通用格式一致：通常為 `{ "metadata": { ... }, "data": [ ... ] }`。
- **data** 為 **陣列**，元素型別如下（與「已登入任務列表」的單一元素結構相同）。

---

## 2. 已登入任務列表

**用途**：使用者已登入時，依狀態取得任務列表（可接／進行中／已完成／已領獎／已失效）。

| 項目 | 說明 |
|------|------|
| **Method** | `GET` |
| **Path** | `v2/mission/list/status` |
| **Query 參數** | 見下表 |
| **Request Body** | 無 |

### Query 參數

| 參數名 | 型別 | 必填 | 說明 |
|--------|------|------|------|
| `statuses[]` | array of string | 選填 | 要取得的任務狀態，可多個。Android 目前傳：`NEW`, `PROG`, `COMPLETE`, `DONE`。 |

**status 枚舉值**（與後端約定一致即可）：

- `NEW`：可接任務  
- `PROG`：進行中  
- `COMPLETE`：已完成可領獎  
- `DONE`：已領獎  
- `INVALID`：已失效  

### 回傳資料（Response）

- 與後端通用格式一致：通常為 `{ "metadata": { ... }, "data": [ ... ] }`。
- **data** 為 **陣列**，元素型別如下。

---

## 3. 回傳資料結構（兩支 API 的 data 元素相同）

**data**：`Array<MissionItem>`，每個元素為一筆任務。

### MissionItem（單一任務）

| JSON 欄位 (key) | 型別 | 說明 |
|------------------|------|------|
| `mission_id` | int | 任務 ID |
| `mission_category` | string | 任務分類，如 `LOY`（會員等級）、`LIM`（限時） |
| `mission_icon` | object | 任務圖示 |
| `mission_banner` | object | 任務 Banner 圖 |
| `mission_link` | string | 任務按鈕連結（如 deeplink / 網址） |
| `mission_name` | string | 任務名稱 |
| `mission_desc` | string | 任務說明 |
| `action_btn_text` | string | 按鈕文案 |
| `mission_detail` | array | 任務步驟／說明區塊 |
| `end_time` | string | 結束時間（格式依後端，如 `yyyy-MM-dd`） |
| `rewards` | array | 獎勵列表 |
| `mission_record_id` | int | 已接任務的紀錄 ID（未接為 0） |
| `mission_status` | string | 狀態：`NEW` / `PROG` / `COMPLETE` / `DONE` / `INVALID` |
| `done_time` | string | 完成時間 |
| `complete_deadline` | string | 完成期限 |
| `progress_bar` | object | 進度條資訊 |

### mission_icon

| 欄位 | 型別 | 說明 |
|------|------|------|
| `active` | string | 啟用時圖示 URL |
| `inactive` | string | 未啟用時圖示 URL |

### mission_banner

| 欄位 | 型別 | 說明 |
|------|------|------|
| `mobile` | string | Banner 圖 URL |

### mission_detail（陣列元素）

| 欄位 | 型別 | 說明 |
|------|------|------|
| `title` | string | 區塊標題 |
| `list-type` | string | 列表型別，如 `order` / `unorder` |
| `contents` | array | 內容列表，見下 |

#### contents 元素

| 欄位 | 型別 | 說明 |
|------|------|------|
| `title` | string | 小標 |
| `desc` | array | 說明項，元素可含 `info`（object）、`desc`（string） |

### rewards（陣列元素）

| 欄位 | 型別 | 說明 |
|------|------|------|
| `type` | string | 獎勵類型：如 `POINT`（KK Points）、`EXP`（經驗值）、`COUPON` |
| `value` | int | 獎勵數值 |

### progress_bar

| 欄位 | 型別 | 說明 |
|------|------|------|
| `type` | string | `boolean` / `percent` / `count` |
| `target` | int | 目標值 |
| `current` | number | 目前值 |

---

## 4. 簡短對照（可複製給 iOS）

```
【未登入任務列表】
GET v2/mission/list/un_login
Query: country_code (string, 選填)
Response data: Array<MissionItem>

【已登入任務列表】
GET v2/mission/list/status
Query: statuses[] (array of string, 選填)，e.g. NEW, PROG, COMPLETE, DONE
Response data: Array<MissionItem>

兩支 API 的 data 元素結構相同，皆為 MissionItem（見上方欄位表）。
```

---

## 5. JSON 規格（可複製貼到 Slack）

**完整 JSON：**

```json
{
  "apis": [
    {
      "name": "未登入任務列表",
      "method": "GET",
      "path": "v2/mission/list/un_login",
      "query": { "country_code": "string, 選填, 國家代碼 e.g. TW" },
      "response_data": "Array<MissionItem>"
    },
    {
      "name": "已登入任務列表",
      "method": "GET",
      "path": "v2/mission/list/status",
      "query": { "statuses[]": "array of string, 選填, e.g. NEW, PROG, COMPLETE, DONE" },
      "response_data": "Array<MissionItem>"
    }
  ],
  "MissionItem": {
    "mission_id": "int",
    "mission_category": "string, LOY|LIM",
    "mission_icon": { "active": "string", "inactive": "string" },
    "mission_banner": { "mobile": "string" },
    "mission_link": "string",
    "mission_name": "string",
    "mission_desc": "string",
    "action_btn_text": "string",
    "mission_detail": "[{ title, list-type, contents }]",
    "end_time": "string",
    "rewards": [{ "type": "string, POINT|EXP|COUPON", "value": "int" }],
    "mission_record_id": "int",
    "mission_status": "string, NEW|PROG|COMPLETE|DONE|INVALID",
    "done_time": "string",
    "complete_deadline": "string",
    "progress_bar": { "type": "string", "target": "int", "current": "number" }
  }
}
```

**Slack 用一句版（貼在 code block）：**

```
任務列表 API（兩支回傳格式相同）
1) GET v2/mission/list/un_login  Query: country_code (string, 選填)  → data: Array<MissionItem>
2) GET v2/mission/list/status    Query: statuses[] (NEW,PROG,COMPLETE,DONE)  → data: Array<MissionItem>
MissionItem: mission_id, mission_category, mission_icon{b}, mission_banner{mobile}, mission_link, mission_name, mission_desc, action_btn_text, mission_detail[], end_time, rewards[{type,value}], mission_record_id, mission_status, done_time, complete_deadline, progress_bar{type,target,current}
```

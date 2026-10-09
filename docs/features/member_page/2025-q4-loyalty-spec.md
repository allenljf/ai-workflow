# 2025 Q4 Loyalty 改版 — 產品規格（Spec）

- **設計檔**：Figma `2025-q4-Loyalty-program`（fileKey: `lhlUGHS1963vcOg9iKjnYl`）
- **任務與估時**：見 [首頁任務與估時](2025-q4-loyalty-home-tasks.md)；會員頁任務另開文件。
- **本文件**：僅記載需求與設計連結，不包含任務拆解與估時。

---

## 一、首頁（Home）

### 1.1 需求與設計連結

| 項目 | 說明 | Figma |
|------|------|-------|
| 說明 | 首頁整體說明與規格 | [5855-49100](https://www.figma.com/design/lhlUGHS1963vcOg9iKjnYl/2025-q4-Loyalty-program?node-id=5855-49100&m=dev) |
| 首頁未登入 | 未登入狀態版面與元件 | [5768-42638](https://www.figma.com/design/lhlUGHS1963vcOg9iKjnYl/2025-q4-Loyalty-program?node-id=5768-42638&m=dev) |
| 首頁已登入 | 已登入狀態版面與元件 | [5302-6764](https://www.figma.com/design/lhlUGHS1963vcOg9iKjnYl/2025-q4-Loyalty-program?node-id=5302-6764&m=dev) |
| 未登入上滑收合 | 未登入時上滑收合互動 | [5855-49101](https://www.figma.com/design/lhlUGHS1963vcOg9iKjnYl/2025-q4-Loyalty-program?node-id=5855-49101&m=dev) |
| 登入上滑收合 | 已登入時上滑收合互動 | [5802-25039](https://www.figma.com/design/lhlUGHS1963vcOg9iKjnYl/2025-q4-Loyalty-program?node-id=5802-25039&m=dev) |
| 新增與修改 | 較簡單的新增/修改項目 | 依設計與產品說明，於任務文件拆解 |

---

## 二、會員頁（我的）

### 2.1 需求與設計連結

| 項目 | 說明 | Figma |
|------|------|-------|
| 說明 | 會員頁互動與主要頁面框架 | [5906-16571](https://www.figma.com/design/lhlUGHS1963vcOg9iKjnYl/2025-q4-Loyalty-program?node-id=5906-16571&m=dev) |
| 未登入時 | 會員頁未登入狀態 | [5571-38118](https://www.figma.com/design/lhlUGHS1963vcOg9iKjnYl/2025-q4-Loyalty-program?node-id=5571-38118&m=dev) |
| 已登入 | 會員頁已登入狀態 | [5342-28822](https://www.figma.com/design/lhlUGHS1963vcOg9iKjnYl/2025-q4-Loyalty-program?node-id=5342-28822&m=dev) |
| 會員資料區 | 頭像、等級、點數等 | [5914-38031](https://www.figma.com/design/lhlUGHS1963vcOg9iKjnYl/2025-q4-Loyalty-program?node-id=5914-38031&m=dev) |
| menu 區 | 設定、優惠券、任務等選單 | [5914-43779](https://www.figma.com/design/lhlUGHS1963vcOg9iKjnYl/2025-q4-Loyalty-program?node-id=5914-43779&m=dev) |
| 瀑布流區塊 | 底部瀑布流與 Sticky | [5914-46813](https://www.figma.com/design/lhlUGHS1963vcOg9iKjnYl/2025-q4-Loyalty-program?node-id=5914-46813&m=dev) |

**備註**：會員頁為整頁重做，Compose、參考 HomeScreen 架構（上滑收合 + 瀑布流 + Sticky）；任務與估時另文件規劃。

---

## 三、Figma node-id 對照（MCP 用）

- **fileKey**：`lhlUGHS1963vcOg9iKjnYl`
- **nodeId**：URL 的 `node-id=XXXX-YYYY` → MCP 使用 `XXXX:YYYY`

| 頁面 | 項目 | node-id (URL) | nodeId (MCP) |
|------|------|----------------|--------------|
| 首頁 | 說明 | 5855-49100 | 5855:49100 |
| 首頁 | 未登入 | 5768-42638 | 5768:42638 |
| 首頁 | 已登入 | 5302-6764 | 5302:6764 |
| 首頁 | 未登入上滑收合 | 5855-49101 | 5855:49101 |
| 首頁 | 登入上滑收合 | 5802-25039 | 5802:25039 |
| 會員 | 說明 | 5906-16571 | 5906:16571 |
| 會員 | 未登入時 | 5571-38118 | 5571:38118 |
| 會員 | 已登入 | 5342-28822 | 5342:28822 |
| 會員 | 會員資料區 | 5914-38031 | 5914:38031 |
| 會員 | menu 區 | 5914-43779 | 5914:43779 |
| 會員 | 瀑布流區塊 | 5914-46813 | 5914:46813 |
| 會員 | Header 收合（參考 1） | 5906-35908 | 5906:35908 |
| 會員 | Header 收合（參考 2） | 5906-36485 | 5906:36485 |
| 會員 | 瀑布流收合 + Sticky | 5906-37073 | 5906:37073 |

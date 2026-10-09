# 2025 Q4 Loyalty 首頁與會員頁改版 — 總覽

- **設計檔**：Figma `2025-q4-Loyalty-program`（fileKey: `lhlUGHS1963vcOg9iKjnYl`）
- **文件拆分**：規格與任務分開維護。

---

## 文件索引

| 文件 | 用途 |
|------|------|
| [2025-q4-loyalty-spec.md](2025-q4-loyalty-spec.md) | 產品規格：需求說明與 Figma 連結（首頁＋會員頁） |
| [2025-q4-loyalty-home-tasks.md](2025-q4-loyalty-home-tasks.md) | 首頁任務：現況分析、需求對照、任務細分、AI 開發估時（約 4.5 人天） |
| [2025-q4-loyalty-member-tasks.md](2025-q4-loyalty-member-tasks.md) | 會員頁（我的）：Figma 連結、舊架構整理、新頁共識、兩階段開發流程（架構→UI/UX） |

---

## 會員頁任務

會員頁為整頁重做（Compose，參考 HomeScreen）。需求與 Figma 連結見 [spec](2025-q4-loyalty-spec.md)；規格與任務見 [2025-q4-loyalty-member-tasks.md](2025-q4-loyalty-member-tasks.md)（舊架構、可收合 Header 未登入/登入、瀑布流+Sticky Tabs、兩階段開發流程）。

---

## Figma MCP 使用

- Section 節點會回傳 sparse metadata，實作時需對子節點再取 `get_design_context`。
- nodeId 格式：URL `node-id=XXXX-YYYY` → MCP 使用 `XXXX:YYYY`。完整對照表見 [spec](2025-q4-loyalty-spec.md)。

---

## 後續

- **會員頁**：架構與佈局完成後，再對 Figma 做 UI/UX 與細節（顏色、間距等）；任務細分與估時於 [member-tasks](2025-q4-loyalty-member-tasks.md) 補上。

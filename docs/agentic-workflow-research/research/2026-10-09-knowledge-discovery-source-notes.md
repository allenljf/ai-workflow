# 雙週知識探索：來源與 API 查核

查核日期：2026-10-09。這是實作依據，不表示所有工具都在這天重新驗證過。

## 搜尋契約

Tavily Search 使用 `POST https://api.tavily.com/search`，header 是 `Authorization: Bearer <API key>` 與 `Content-Type: application/json`；必要 body 欄位為字串 `query`。本專案可採以下固定參數：

```json
{
  "query": "agent workflow verification durable execution new tools",
  "topic": "general",
  "search_depth": "basic",
  "auto_parameters": false,
  "max_results": 5,
  "time_range": "month",
  "include_answer": false,
  "include_raw_content": "text",
  "include_published_date": true,
  "include_usage": true
}
```

`max_results` 範圍 0–20。`results[]` 提供 `title`、`url`、`content`、`score`、可空的 `raw_content`；日期欄位須啟用且可能為空或估算的更新日。只有 snippet 不能當作讀完原文。`usage.credits` 記錄點數，`request_id` 供查錯。設定 `include_domains` 會限制網域；探索新作者時應省略，否則仍會困在已知來源。自動參數可能選用較貴的 advanced，故明確關閉。[官方 Search 契約](https://docs.tavily.com/documentation/api-reference/endpoint/search)

錯誤狀態：400／422 請求格式、401 認證、429 限流、432 方案額度、433 PAYGO 上限、500 服務失敗；429 若有 `Retry-After`，依 header 延後重試，不比對錯誤文字。預設 Development 為每分鐘 100 次；Production 為 1,000 次，但需要付費方案或 PAYGO。[Search 錯誤](https://docs.tavily.com/documentation/api-reference/endpoint/search)、[限流文件](https://docs.tavily.com/documentation/rate-limits)

目前官方提供每月 1,000 免費 credits，不需信用卡；basic 一次 1 credit，advanced 一次 2 credits；PAYGO 是 US$0.008／credit。本專案每兩週 4 個 basic 查詢，約每月 8–12 credits（依月內批次數）；重試另計。這與 DeepSeek token 費用分開，不能用模型預算限制取代搜尋服務帳戶限制。[Credits 與費用](https://docs.tavily.com/documentation/api-credits)

## Graph、loop、harness 的時間證據

- LangGraph 官方發表於 **2024-01-17**，已討論帶循環的 graph 與 agent runtime；不能把 graph／loop 說成 2026 年下半年才誕生。[LangGraph 發表](https://www.langchain.com/blog/langgraph)
- Anthropic **2024-12-19** 的文章已說明 evaluator–optimizer loop，以及預定義 workflow 與模型自主 agent 的區別。[Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- Anthropic **2025-11-26** 的 long-running harness 文章討論 initializer、進度文件、增量工作與跨 context window 接續；因此也不能把 harness 當成本週新概念。[Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)

「最近才被重視」是採用趨勢主張，以上日期只能證明概念早已存在；要宣稱業界熱度上升，還需近期採用案例或可比較數據。知識總覽應分開記錄最初發表日、本次找到日期、最後查核日期及適用條件。

## 本專案的操作原則

以下是根據來源限制提出的設計建議：搜尋以工程問題與未知新工具為主，固定官方訂閱用來追蹤已知來源；搜尋結果只是候選，修訂須引用原作者／官方原文。擷取失敗、空結果、缺少日期不能被轉成「本雙週沒有新知識」。保留前一版核准總覽，將新增工具、主張修訂與來源建議一起交給審閱 PR；不因搜尋排名直接自動加入可信來源。

不要把搜尋到的網頁文字當作系統指令；只存必要證據與短摘要，避免大量第三方全文進入公開 Git 歷史。Secret 放 GitHub Actions Secrets，不能出現在 Markdown、下載檔或公開 workflow log。

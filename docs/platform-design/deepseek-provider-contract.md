# DeepSeek 整理 provider 查核

查核日：2026-10-08。支援政策版本：deepseek-nonthinking-2026-10-08。
此文件不是永久價目；config/model-pricing.yaml 的 checked_at / expires_at 最多相差14天。

- [官方價格](https://api-docs.deepseek.com/quick_start/pricing/)：Flash peak cache miss input USD0.30/M、output USD1.20/M；使用最高時段與不命中價格，不假設快取折扣。
- [Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/)：可指定 model、max_tokens、JSON output；模型支援 1M context。
- [Thinking mode](https://api-docs.deepseek.com/guides/thinking_mode/)：預設啟用；本 adapter 明確設定 thinking.type=disabled、reasoning_effort=none，不使用 tools。
- [Token usage](https://api-docs.deepseek.com/quick_start/token_usage/)：字元比率只是估計，不能作硬上界。本次不使用未證明對應目前模型的 tokenizer，改以完整官方 context ceiling 1,048,576 input tokens 預留；這是保守上界，不是實際輸入量。輸入另限制完整 HTTP JSON ≤50KB、40 revision、600字元短摘，輸出≤6000 tokens。Flash 最壞預留 USD0.3217728。
- output_tokens 使用 completion_tokens（包含 reasoning），不得再加 reasoning_tokens；非推理模式仍回傳推理用量時拒絕結果、保留預留待確認。
- 單批只一個 request、無任何自動重試；HTTP timeout、截斷、異常usage與模型不符皆待確認。Authorization 不寫入台帳、PR、診斷或網站。

API上限是供應商合約，非帳戶硬上限；若合約改變或價目過期，拒絕新付費。沒有真實付費驗證，所有 adapter 測試使用 MockTransport。

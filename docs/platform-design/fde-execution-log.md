# FDE 執行紀錄

基線 caa0ceb，分支 codex/fde-learning-hub；依三份已確認計劃原生 Sol 逐項執行。未 merge/push／付費呼叫／雲端部署。

## F1

基線140/140。索引缺失RED8 failures→GREEN8/8，完整148/148。公開12節點與15篇MD，DAG/private/path/date驗證，失敗保留舊export。
Ruling：三個adoption fixture原來只複製全registry但不帶content，加入FDE後不完整；補content而保留產品fail-closed檢查。

## F2

Domain/asset RED2 failures→GREEN3/3；完整151/151。兩個舊Android ZIP literal SHA不變。新增domain省略default以保持舊manifest bytes；FDE assets只明列fde_lab/fixtures、hash approval、不含runtime。
Ruling：兩個既有版本數量assert改為android範圍；整個catalog新增FDE不是Android版本數增加。
Ruling：新adapter manifest ref指開發基線9a4763c，ZIP本身及hash標識新技能內容，README不宣稱基線commit已有新skill；未嵌入第三方框架。

技能行為驗證依writing-skills：baseline無skill代理。交付情境提出tenant/驗收但缺當前report hash、commit/dataset/model版本及independent holdout的完整artifact契約；更新情境提出「獨立FDE預算設定草案」，沒有既有全站帳本約束。
建立fde-solution後fresh代理完成同交付情境，輸出當前report path/hash、acceptance IDs、commit/dataset/model環境、獨立holdout、prototype與enterprise pilot區別。建立fde-knowledge-review後fresh代理完成更新情境，保留0.2.0原bytes，提新候選版本、共用14天next_due與USD0.50/批/USD2/月、保存calling/ambiguous而不重扣費。兩份quick_validate均PASS。此為reference路由的應用測試，不是企業部署效果或統計可靠性證據。

## F3

RED browser3fail（新增FDE路由不存在、FDE包被舊UI誤標Android）→GREEN root7/7、Pages子路徑7/7。Astro check0errors/0warnings/10既有hints；完整pytest151/151（F4測試寫入前）。新增MD/ZIP實際HTTP下載、12節點、390pxoverflow與惡意titleescaping驗證。

## F4

RED缺RAG模組4fail、CLI1fail→GREEN8/8，完整159/159（F5測試加入前）。真SQLite版本化FTS、跨tenant/舊版本/偽造引用/無證據、embedding profile與本機HTTP非法輸出/連線失敗驗證；rag-demo實際執行，dataset hash與fixture evidence明列。
Ruling：小資料embedding檢索以明確set_embedding/search_embeddings接口提供，索引身份由已驗證model/digest傳入；不自動拉取模型。真Ollama性能未測。SQLite FTS unicode tokenizer不提供完整中文斷詞，指南列限制。

## F5

RED6fail缺jobs→GREEN6；追加cancel-crash/inflight/heartbeat RED3→GREEN9；CLI RED1→GREEN10，完整169/169。真子程序exit7後新worker恢復，local effect計數1。持久SQLite lease/version、receipt、attempt/deadline/cost、backoff、取消與ambiguous。
Ruling：新增begin_external_step（先保留budget與started狀態），因外部call中斷後僅看缺receipt不能安全自動重試；expired未確認call→ambiguous優先於取消/期限。成本是lab模擬ledger，與radar付款帳本完全分離。

## F6

RED6缺data/CLI→GREEN6；新0.2包缺失RED1→GREEN；程式字串被誤讀Markdown link RED1→GREEN（僅MD/reference檢查連結，hash-approved code不當Markdown）。0.2包解壓後實際執行三套CLI。
Ruling：新包lab sources存bundles/fde/labs-0.2固定快照，活躍examples仍可演進而不破壞已發行hash；額外只明列pyproject.toml與dataset.jsonl檔名及hash approval，不擴大任意附件root。代價是維護歷史快照，不修改已發布版本。

F6 完整pytest177/177；資料fixture CLI實際dry-run、同輸入可重現hash，來源快照包解壓後三套CLI均執行。

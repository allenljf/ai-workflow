# FDE 執行紀錄

基線 caa0ceb，分支 codex/fde-learning-hub；依三份已確認計劃原生 Sol 逐項執行。未 merge/push／付費呼叫／雲端部署。

## F1

基線140/140。索引缺失RED8 failures→GREEN8/8，完整148/148。公開12節點與15篇MD，DAG/private/path/date驗證，失敗保留舊export。
Ruling: 三個adoption fixture原來只複製全registry但不帶content，加入FDE後不完整；補content而保留產品fail-closed檢查。

## F2

Domain/asset RED2 failures→GREEN3/3；完整151/151。兩個舊Android ZIP literal SHA不變。新增domain省略default以保持舊manifest bytes；FDE assets只明列fde_lab/fixtures、hash approval、不含runtime。
Ruling: 兩個既有版本數量assert改為android範圍；整個catalog新增FDE不是Android版本數增加。
Ruling: 新adapter manifest ref指開發基線9a4763c，ZIP本身及hash標識新技能內容，README不宣稱基線commit已有新skill；未嵌入第三方框架。

技能行為驗證依writing-skills：baseline無skill代理。交付情境提出tenant/驗收但缺當前report hash、commit/dataset/model版本及independent holdout的完整artifact契約；更新情境提出「獨立FDE預算設定草案」，沒有既有全站帳本約束。
建立fde-solution後fresh代理完成同交付情境，輸出當前report path/hash、acceptance IDs、commit/dataset/model環境、獨立holdout、prototype與enterprise pilot區別。建立fde-knowledge-review後fresh代理完成更新情境，保留0.2.0原bytes，提新候選版本、共用14天next_due與USD0.50/批/USD2/月、保存calling/ambiguous而不重扣費。兩份quick_validate均PASS。此為reference路由的應用測試，不是企業部署效果或統計可靠性證據。

## F3

RED browser3fail（新增FDE路由不存在、FDE包被舊UI誤標Android）→GREEN root7/7、Pages子路徑7/7。Astro check0errors/0warnings/10既有hints；完整pytest151/151（F4測試寫入前）。新增MD/ZIP實際HTTP下載、12節點、390pxoverflow與惡意titleescaping驗證。

## F4

RED缺RAG模組4fail、CLI1fail→GREEN8/8，完整159/159（F5測試加入前）。真SQLite版本化FTS、跨tenant/舊版本/偽造引用/無證據、embedding profile與本機HTTP非法輸出/連線失敗驗證；rag-demo實際執行，dataset hash與fixture evidence明列。
Ruling: 小資料embedding檢索以明確set_embedding/search_embeddings接口提供，索引身份由已驗證model/digest傳入；不自動拉取模型。真Ollama性能未測。SQLite FTS unicode tokenizer不提供完整中文斷詞，指南列限制。

## F5

RED6fail缺jobs→GREEN6；追加cancel-crash/inflight/heartbeat RED3→GREEN9；CLI RED1→GREEN10，完整169/169。真子程序exit7後新worker恢復，local effect計數1。持久SQLite lease/version、receipt、attempt/deadline/cost、backoff、取消與ambiguous。
Ruling: 新增begin_external_step（先保留budget與started狀態），因外部call中斷後僅看缺receipt不能安全自動重試；expired未確認call→ambiguous優先於取消/期限。成本是lab模擬ledger，與radar付款帳本完全分離。

## F6

RED6缺data/CLI→GREEN6；新0.2包缺失RED1→GREEN；程式字串被誤讀Markdown link RED1→GREEN（僅MD/reference檢查連結，hash-approved code不當Markdown）。0.2包解壓後實際執行三套CLI。
Ruling: 新包lab sources存bundles/fde/labs-0.2固定快照，活躍examples仍可演進而不破壞已發行hash；額外只明列pyproject.toml與dataset.jsonl檔名及hash approval，不擴大任意附件root。代價是維護歷史快照，不修改已發布版本。

F6 完整pytest177/177；資料fixture CLI實際dry-run、同輸入可重現hash，來源快照包解壓後三套CLI均執行。

## F7

HTTP routes RED 3 failures→GREEN；模型引用 validator RED compile缺類別→GREEN。Maven verify 4 tests/0fail/0error；全pytest177/177。JUnit真HTTP/SQLite驗证401、跨tenant404、重複201/200、payload衝突409、取消、無證據與偽造引用拒絕。固定Java21 target / Boot4.1.1 / AI2.0.1 / JDBC3.53.4.0，官方Maven3.9.16 SHA512已驗證。
Ruling: Spring AI選配提供合成授權policy的生成adapter，完整版本化RAG保留Python；避免將Java fixture誤稱真文件搜尋，代價是企業Java檢索需另接adapter與eval。真Ollama推論未測。API只入列，worker仍由Python啟動。
Pre-flight F4/F5→F7：HTTP租戶由可信token映射；SQLite jobs v1欄位與Python一致，Java無claim worker，指南明列。

## F8

RED4→GREEN6新測試；enrichment相關35/35；全pytest183/183。18來源免費live收集無失敗，285 revisions/events，pgvector與anthropics-skills無release保持空。root/Pages各7/7，Astro0error/0warning/10既有hints。
Ruling: 泛用workflow來源仍入原開發桶，LangGraph亦入FDE；跨桶事件去重且多領域request按事件逐輪讀revision，避免第一個大事件填滿40上限。單領域既有排序/付款identity保留；新增topic_map只為可信metadata，不送模型、不改batch hash，舊request省略此欄保持bytes。
Ruling: 公開next_due不從其他領域精選或時間推估，顯示未公開並指向私人全站帳本；AI狀態是checked-in設定而非Actions override。成本是公開頁不能得知精確下次執行時間，避免誤報與暴露私人財務狀態。
Pre-flight F1/F3→F8：FDE頁讀source側topic與approved digest metadata，人工內容/技能仍經原export allowlist；F8→F9/F10：付款帳本與企業lab DB無共用連線。

## F9

Deployment parser/CLI RED7→GREEN7，Python HTTP缺模組RED→GREEN1（另cancel無body契約RED→GREEN）。Postgres缺adapter RED→GREEN13，owner拒絕RED→GREEN、真併發key/claim及遠端TLS RED→GREEN；最終PostgreSQL16＋API1＋parser7=24/24。Docker daemon29.5.2；本機pull pgvector pg18及Python3.12.12固定digest，container build及health200/業務無token401。全pytest191PASS/16顯式未配置DBskip（opt-in另已實跑）。
Ruling: Postgres JobStore沿用同一個狀態機，抽出連線seam，以transaction advisory lock對齊SQLite串行一致性；成本是吞吐量有限，升級row locks時需重跑race/lease/effect測試。RLS非owner/不BYPASS、API tenant scope與worker全域權限明列。
Ruling: 雲端image選Python API+worker，Java仍SQLite獨立對照；兩者HTTP契約相同，避免宣稱未實作的Java Postgres。成本是Java企業部署需另整合DB adapter。
Ruling: Scheduler觸發Cloud Run Jobs run API使用OAuth而非服務OIDC；API對服務呼叫仍需要audience/OIDC。API/worker分離SA和DBsecretrefs，生成步驟只列argv，不建立/push/deploy。成本是人仍需完成IAM/WIF、DB、image與網路前置並驗收。
Pre-flight F5→F9：連線seam不變租戶/key/lease/receipt狀態契約；F9→F10：同一strict parser做wizard check/dry-run，配置不包含secret值。

## F10

Wizard缺檔RED5→GREEN5；追加實際有效GCP refs取消/保存測試，macOS Bash把無大括號Unicode標點讀成變數名RED→GREEN6。未改template library，hash驗證；--check/cancel/local不登入/不寫secrets，gcp只auth list與browser、配置須確認，不apply。shellcheck/bash/actionlint與兩個skill quick_validate PASS。
補F8實際bounded revisions的topic回歸：RED→GREEN，不能因未送模型的FDE revision把Android輸出標FDE。舊request body/付款身份保持。
完整含真PostgreSQLpytest214/214；Maven4/4；Astro0errors/0warnings/10既有hints；root與Pages各7/7，setup MD HTTP200、390px無overflow、惡意title不執行。三套CLI實際跑，runtime合成；4份已發布ZIP literal SHA不變；live export恢復285原始events、無private draft/state進manifest。
Ruling: wizard不收集DB/password或API token值，api-db給secret/env指引，GitHub/provider路由既有wizard的隱藏stdin與原付費gate；成本是本機服務仍需人自行注入憑證，避免複製秘密到setup-state。
本機container health200/業務401；雲端IAM/WIF/遠端DB/實際模型/ANN品質/企業負載未驗證，不稱部署ready。後續完整分支fresh Sol review與一次重要問題修正記在下方。

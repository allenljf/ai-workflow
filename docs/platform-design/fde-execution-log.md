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

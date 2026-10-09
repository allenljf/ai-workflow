# 雙週 AI 整理設定

A1–A5 的本機程式已提供；預設 AI_ENABLED=false、CLI為dry-run。只有同時具備 --allow-paid、明確 enabled、新資料、到期、有效價目與足夠預算，才可送出一次 request。放入 token 不會自動啟用。

## 先跑不付費預覽

在主專案安裝 README 的依賴並完成 collect 後：

~~~bash
.venv/bin/python -m radar.cli enrich --config config --state-dir .build/live --dry-run
bash scripts/setup/ai.sh --check
bash scripts/setup/ai.sh
~~~

Wizard沿用 [wizard 技能模板](/Users/allen/.agents/skills/wizard/SKILL.md)，五階段：公開作品集 repo 與 hidden provider token → 官方模型/價目查核 → 14天與預算 → 本機dry-run報告 → 啟用未來排程及另一次確認首次付費。只有人類執行wizard會配置GitHub帳戶。未登入／取消／dry-run不呼叫模型。

寫入Secret只有 DEEPSEEK_API_KEY（stdin）；非敏感變數 AI_ENABLED、AI_PRICE_POLICY、AI_MAX_BATCH_USD、AI_MAX_MONTHLY_USD。非敏感resume位於忽略的 .build/ai-values.env；token不寫檔、不傳命令參數。重新設定確認後先停用AI，最後才啟用；開始前取消不會撤銷既有設定。需要停用時在GitHub將AI_ENABLED設false。

本作品集 repo 為公開 repo；AI 整理 PR、未核准草稿、已提交的 pipeline state 與 Git 歷史都會公開可讀。不要把機密、客戶資料或個資送入此流程。Settings → Actions → General 檢查是否允許 GitHub Actions 建立 pull requests。workflow使用Contents write、Pull requests write；collect另需Actions write以dispatch enrich。帳號／組織可能禁止此操作，不能僅憑本機測試宣稱權限成功。

## 到期、預算與價目

成功完成時間加14天才到期；無新資料不改到期日。預設每批USD0.50、每月USD2，Decimal字串計費。
價格設定持續有效，直到你手動修改。需要變更模型、單價或預算時可重跑wizard更新AI_PRICE_POLICY；程式不會自動猜價格。

[Provider查核契約](deepseek-provider-contract.md)記錄非推理模式與官方context ceiling的保守預留。預留不是帳单，usage按最高已核准價格記錄；折扣可能使實際帳單更低。應用層gate不控制別的程式或同帳戶其他token支出。

## Durable state 與中斷恢復

state branch: pipeline-state。
- snapshot.json：每週蒐集。
- enrichment-state.json：due、每批預留／usage／狀態、月度台帳。
- batches/<batch_id>/result.json：模型原結果；hash與台帳同commit保存。此作品集 repo 與 pipeline-state branch 公開，原結果可被任何人讀取。

付費前必須在state checkout中先完成CAS push兩個checkpoint（reserved、calling）。本機普通 .build/live 只可dry-run；沒有durable Git checkout會拒絕付費。

timeout、未知usage、process kill的calling/reserved狀態不自動重送。請先到provider查帳，確認是否收費／有無結果，再人工修復與核對台帳，勿直接刪batch重跑。第一版没有自動retry或一鍵清帳，防止誤釋放預留。跨月未確認預留仍占新月預算。請求若跨UTC月份完成，該批actual保守計入開始與完成兩個月份，避免未查核供應商結算邊界而低估新月費用。

現有台帳缺必填欄位、費用不等於已結算批次或遺忘due時會拒絕恢復，不能當成新狀態。

若只缺草稿或PR，用已存結果恢復；不再次呼叫模型。格式／引用驗證失敗保留未核准 payload 與 sanitized 診斷，需人工處理；它們也會留在公開 state branch。

## 排程與 PR 審閱

每週collect持久化後免費檢查gate，非同步dispatch enrich.yml；子workflow取得同pipeline-state鎖後重新讀state，不在父鎖內等待。

enrich.yml手動執行預設allow_paid=false，只做dry-run；啟用付費需另將allow_paid=true。Secret僅paid job中的provider step可讀，PR checks只用fixtures。AI review PR 位於公開 repo，草稿與審閱意見可被所有人閱讀。
[GitHub官方触發規則](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)：workflow_dispatch可由GITHUB_TOKEN觸發；該token建立的PR檢查可能需要人類approve workflows to run。

固定digest/<batch_id> branch與單一PR，不覆寫人類修改；closed記rejected、merged記reviewed，兩者都不重新付費。無權建PR時保留result，之後重試PR本身；人工改過的草稿會保留，PR協調不覆寫修改；台帳裡的review_pr_url與PR狀態在review協調步驟更新。

單純merge content/drafts下的private草稿不會發布。要公開需：
1. 核對原文引用、推論、Android適用性及案例等級。
2. 將審閱版本移至content/public/digests/。
3. 保留batch/model/prompt/schema/enriched_at，設定visibility: public、review_state: approved及具時區的reviewed_at。
4. 通過export與建置；網站雙週精選才顯示整理與人工核准兩個時間。

Youtube只有metadata必有「未檢視影片全文」。引用吻合只代表逐字可追溯，不能證明推論正確。這個階段沒有Android實測或公司採納結論。

## 本輪交付與限制

[合成精選示範](examples/digest-synthetic.md)、[synthetic dry-run報告](examples/enrichment-dry-run.json)只供看格式，不是實際模型案例。
paid live run、真實review PR、外部Actions與token權限尚未驗證；本輪沒有真token呼叫、遠端push或實際配置wizard。

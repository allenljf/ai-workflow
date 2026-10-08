# GitHub 設定與本機驗收

K1–K7 的程式已建立；未推送原始 repo、未建立外部 repo、未啟用網站或排程。付費 AI 不在本階段。

## 先在本機看網站

依根目錄 README 安裝依賴並執行 collect → export → build。確認首頁的新訊、來源健康與指南；只有核准來源 metadata 及 `content/public/` 的 approved 文件進入網站。原始 `docs/` 不會直接被讀取或匯出。

## Wizard 的五個階段

執行：`bash scripts/setup/github.sh`；唯讀檢查：`bash scripts/setup/github.sh --check`。

1. 原始 repo：輸入 `owner/repo`，由 gh 確認是私有 repo。wizard 不更改 visibility，不推送本機分支。
2. 匯出 repo：你在 [GitHub 建 repo](https://github.com/new) 建立獨立公開空 repo，不加 README／LICENSE。輸入 repo、網站 URL 及 base path。第一次發布會建立其 main 分支；不能拿有既有專案內容的 repo 當目標。
3. 預覽：顯示本機 `.build/export/manifest.json`。先看網站內容，再選擇是否寫入發布配置；取消不會啟用發布。第一次執行預設 disabled；若原本已啟用，取消不會撤銷遠端既有設定，需另外停用。
4. Secret：在 [fine-grained PAT](https://github.com/settings/personal-access-tokens/new) 選 **只包含匯出 repo**，Contents: Read and write，設定到期日。token 以隱藏輸入和 stdin 寫到來源 repo 的 `PUBLIC_EXPORT_TOKEN`；不寫 `.env`、resume 或 Git。
5. 啟用：最後才將 `PUBLISH_ENABLED` 設 true。之後把程式 workflow 整合／推送到私有來源 repo 的 default branch，再手動執行一次 Daily collection。匯出 main 分支出現後，在匯出 repo Settings → Pages 選 Deploy from a branch、main、/(root)。

wizard 不自行發布網站、不 dispatch workflow，也不建立 repo。它會寫入 GitHub 設定，所以應由你在確認具體預覽後親自執行。每次重新配置先停用發布，全部寫入驗證成功後才重新啟用。

## 值映射

| 值 | 存放位置 | 敏感性 |
|---|---|---|
| SOURCE_REPO | `.build/setup-values.env`、`.build/setup-state.json`；gh 操作上下文 | 公開名稱但可能是私有 repo |
| PUBLIC_EXPORT_REPO | 同上＋来源 repo Actions Variable | 非 secret |
| SITE_URL、SITE_BASE | 同上＋来源 repo Actions Variables | 非 secret |
| PUBLISH_ENABLED | 来源 repo Actions Variable；resume 記錄本次選擇 | 非 secret |
| PUBLIC_EXPORT_TOKEN | 来源 repo Actions Secret | Secret，只由發布 job使用 |
| YOUTUBE_API_KEY | 選配 Actions Secret；此 wizard 不收集 | Secret，沒設定不啟用 YouTube |

來源 repo 的 `GITHUB_TOKEN` 由平台提供，不需要你另外建立。collect 用它保存 `pipeline-state`，publish 則用只對匯出 repo 的 token。原始 repo 與匯出 repo 不可相同。

## URL 範例

一般專案 Pages：SITE_URL=`https://owner.github.io`，SITE_BASE=`/repo/`。SITE_URL 可包含專案路徑，但 canonical 行為以 Astro 當時版本為準；建議使用 origin 與獨立 base，以免重複。

使用自訂網域時，SITE_URL 是完整 HTTPS origin，SITE_BASE=`/`；仍需自行設定網域與 Pages 的 DNS／custom domain。內部登入網站不適用此公開 Pages wizard。

## 排程、補跑與故障

- 每日 UTC 01:17／台北 09:17；GitHub 排程可能延遲，只有 default branch 的 workflow 會排程。
- Daily collection 手動執行可補跑；相同事件不新增重複 revision。
- 單來源失敗保留旧資料；全部來源失敗仍記錄健康、workflow 顯示失敗且不發布。
- state CAS／push 失敗阻擋發布；重新執行會重新讀遠端 state，不能 force push解決。
- export-preview 只產 artifact；下載可檢視，但 artifact 不取代持久化 state。
- token 到期：先將 PUBLISH_ENABLED=false，更新 Secret，再重新啟用。
- 公開 repo 長期無活動可能停用 scheduled workflow，定期確認來源健康與 Actions 是否持續運作。
- 空來源／尚無release是正常空資料；不宣稱代表官方沒有其他產品更新。

## 已驗證與尚未驗證

已驗證：本機 Python 行為、暫存 bare Git remote 的 state CAS 與靜態發布、fake gh 下 wizard取消／token處理、網站root與子路徑、Actions語法。

尚未驗證：你帳戶的遠端權限、GitHub Actions真正執行、Pages初次發布、YouTube live API。這些在你完成設定後才能驗證。

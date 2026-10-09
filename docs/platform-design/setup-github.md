# 公開作品集 repo 與 GitHub Pages

這個設定使用同一個公開 GitHub repo 作為作品集原始碼與 Pages 部署來源。README、追蹤檔案、Git 歷史都可供任何人瀏覽；不要把密碼、token、個資或不願公開的資料提交到 repo。網站只從 export manifest 發布核准的內容，不會直接複製 `docs/`、`.build/` 或 pipeline state。

## 本機預覽

先依根目錄 README 安裝依賴並完成 collect → export → build，再檢查 `site/dist` 與 `.build/export/manifest.json`。只有核准來源 metadata、`content/public/` approved 文件以及 catalog 列出的技能 ZIP 會進入網站。

## 設定 wizard

唯讀檢查：`bash scripts/setup/github.sh --check`。互動設定：`bash scripts/setup/github.sh`。

Wizard 會確認來源 repo 公開、引導你在該 repo 的 Settings → Pages 將 Build and deployment source 設為 GitHub Actions，收集 `SITE_URL` 與 `SITE_BASE`，顯示 export 清單，最後才設定 `PUBLISH_ENABLED`。它不會建立 repo、改可見性、推送分支或立即部署。

一般 GitHub Pages 專案站：

- `SITE_URL=https://<owner>.github.io`（只填 origin，不附 repo 路徑）
- `SITE_BASE=/<repo>/`

若 repo 名稱為 `<owner>.github.io` 或使用已設定的自訂網域，通常使用完整 origin 與 `SITE_BASE=/`。wizard 要求 HTTPS 網址。

成功收集後 workflow 會把 `site/dist` artifact 交給同 repo 的 Pages deployment workflow，透過 GitHub Actions OIDC 發布。無需第二個 repo、PAT 或 `PUBLIC_EXPORT_TOKEN`。部署需要 `pages: write` 與 `id-token: write`；Actions artifact 只作為該次 workflow 的傳遞，不取代 `pipeline-state` 的持久資料。

## 設定值

| 值 | 位置 | 說明 |
|---|---|---|
| `SOURCE_REPO` | 忽略的 `.build/setup-values.env` 和 resume 狀態 | 公開作品集 repo 名稱 |
| `SITE_URL`、`SITE_BASE` | 同上及 repo Actions Variables | Astro canonical URL 與子路徑 |
| `PUBLISH_ENABLED` | repo Actions Variable | 預設 false；最後確認後才設 true |
| `YOUTUBE_API_KEY` | 選配 repo Actions Secret | 此 wizard 不收集；未設定時不啟用 YouTube |

排程 workflow 使用平台提供的 `GITHUB_TOKEN` 保存 `pipeline-state`；Pages deployment 使用 Actions OIDC，不需自建部署 token。

## 排程、補跑與故障

- 每週一 UTC 01:17／台北 09:17；GitHub 排程可能延遲，只有 default branch 的 workflow 會排程。
- `workflow_dispatch` 可手動補跑；相同事件不新增重複 revision。
- 單來源失敗保留舊資料；全部來源失敗仍記錄健康、workflow 顯示失敗且不發布。
- state CAS／push 失敗阻擋發布；重跑會重新讀遠端 state，不要 force push 解決。
- export-preview 只產 artifact；artifact 可下載檢視，但不取代持久 state。
- 公開 repo 長期無活動可能停用 scheduled workflow，需定期確認 Actions 與來源健康。
- 空來源／尚無 release 是正常空資料，不代表上游沒有其他更新。

## 驗證狀態

本機測試涵蓋公開 repo wizard、取消不啟用、變數寫入、export allowlist、workflow 權限與 Pages OIDC action。你的 GitHub 帳戶設定、Actions 真正執行與 Pages 首次部署，需要推送後由 GitHub 驗證。

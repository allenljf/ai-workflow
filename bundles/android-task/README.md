---
visibility: public
review_state: approved
---
# Android task adapter bundle

這是自有的薄 adapter，供既有上游流程處理 Android 任務；不是 Superpowers 的完整再散布，也沒有 Android 實測結論。
上游固定 [Superpowers commit](https://github.com/obra/superpowers/tree/8ca22dba9a94f28898bbce59f2537ff4d87c747d)。

## 安裝與相容性

先依 [該版本官方說明](https://github.com/obra/superpowers/blob/8ca22dba9a94f28898bbce59f2537ff4d87c747d/README.md)安裝上游。插件商店可能追最新版本；若需固定實驗版本，先確認實際載入ref，不以商店名稱推定版本。
此包只提供自有 Markdown/YAML；不執行 installer，不複製plugin cache。W1初版是來源／安装文件包，W2加入完整skill與references後另發新版本。
harness讀取adapter只代表可載入；不代表已驗證Android品質或效率。

## 移除與回滾

移除只刪此次新增的android-task目錄，勿刪上游或專案既有技能。保存前一個zip/hash與profile；失敗回到原流程。正式執行前必須binding測試repo、SHA、工具與環境。
本包授權見 [LICENSE](LICENSE.md)；來源／固定ref見zip根目錄SOURCES.md，版本與清單見manifest.yaml。

---
title: 案例與證據等級
visibility: public
review_state: approved
---


目前的範例是 **synthetic 契約測試**。例如 duration10→6、cost=null→null 只用來檢查比較工具；不是成功案例，也不證明效率改善。

| 等級 | 可以說什麼 |
| --- | --- |
| 第三方敘述 | 來源聲稱；尚未重現 |
| synthetic fixture | schema／依賴／失敗路徑與工具契約已測 |
| 真實任務觀察 | 固定版本、spec/base/head/environment 及實際執行報告支持該次觀察 |
| 配對評測與試用 | 多輪代表與holdout任務，品質、人工分鐘、成本、失敗率，註明限制 |
| 公司採納 | 人類記錄scope、理由、日期與rollback；不自動從熱門度推論 |

真實評測輸出與公司案例預設私有。脫敏後仍需發布核准，才放公開網站；公開文件核准與公司採納是兩種決策。

# FDE Content and Skills Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在既有網站提供 FDE 技能樹、指南、流程圖與可追溯技能下載。

**Architecture:** 內容維持 reviewed public Markdown，YAML 維護技能依賴；Python 驗證並輸出靜態 JSON。擴充既有 workflow domain policy，但舊 Android manifest 與 ZIP 保持 byte-identical。

**Tech Stack:** Python 3.12、PyYAML/jsonschema、Astro、Playwright。

**Spec:** [設計規格](../specs/2026-10-08-fde-learning-hub-design.md)

## Global Constraints

- 原生 Sol 逐項執行；每項先 RED→GREEN，最後一次 fresh-context 整體審查。
- 保留 Android 0.1/0.2 ZIP SHA：`4f2322e9be952869f21cf87951fe91cd62eb9650eef9eafcbfb522d9ee8467c7`、`ed9649b990da98b2f425806806ab00a12040405973ff83eaf62bdde80ebeb230`。
- FDE 技能 candidate，不宣稱公司採納或企業成功案例；查核日 2026-10-08。
- 公開只允許已核准內容；禁止放寬成整個 skills/examples 根目錄。
- 原始公司 docs、付費模型、main、遠端部署不在本計劃寫入範圍。

## Review Focus

- 技能依賴缺失／cycle 必須拒絕；F1 測試。
- FDE 引用 private／未核准檔案必須阻擋 export；F1/F2 測試。
- 無 domain 的歷史包不能因序列化預設值而變 hash；F2 測試。
- 惡意標題不能變 HTML，Pages 子路徑下載不能 404；F3 瀏覽器測試。
- 手機新增導覽／長 SHA 不可水平溢位；F3 瀏覽器測試。

## File Structure

`src/radar/fde/catalog.py` 負責索引與依賴驗證；`registry/fde/skills.yaml` 負責關係；`content/public/fde/*.md` 負責完整指南。`src/radar/workflows/{registry,bundle,catalog}.py` 僅增加 domain 與受控 assets。`site/src/pages/fde/` 呈現已匯出的資料。

### Task 1 / F1: 技能樹與公開學習內容

**Files:** Create `src/radar/fde/{__init__,catalog}.py`, `registry/fde/skills.yaml`, `content/public/fde/{getting-started,roadmap,enterprise-discovery,api,data,models,rag,local,eval,durable,cloud,analysis,training,handover,sources}.md`, `tests/test_fde_catalog.py`; modify `src/radar/export.py`, `scripts/build-site.py`。

**Interfaces:** Consumes reviewed MD 與 source URLs；produces `load_skills(root: Path) -> list[dict]` 與 `fde.json`（schema_version=1, checked_at, skills）。每節點欄位：id/title/level/prerequisite_ids/guide_path/source_refs/checked_at/practice_ids/evidence_level/visibility/review_state/skill_bundle_ids。guide_path 為 `fde/<name>.md`。

- [ ] Step 1: 寫 `test_fde_export_contains_reachable_approved_guides`，驗證 exported `fde.json` 有 12 節點，所有 guide_path 在 manifest，來源 HTTPS，依賴 id 存在；寫 `test_cycle_missing_dependency_private_guide_rejected` 分別引入 cycle、missing id、private MD 並 assert ValueError；寫 `test_fde_export_failure_preserves_previous` 驗證錯誤不替換舊 export。
- [ ] Step 2: `.venv312/bin/python -m pytest tests/test_fde_catalog.py -q`；Expected: 新索引缺失／功能未實作而失敗。
- [ ] Step 3: 實作 load_skills：唯一 id、日期、HTTPS、有限 enum、public review、依賴 DAG、指南在 approved export。export 在 stage 生成 fde.json、加入 manifest；prepare 只拷 manifest 允許的 fde.json。寫上述 12 節點指南與參考 12 週路線，沿用研究來源，Mermaid＋文字流程並列。
- [ ] Step 4: 同一測試＋`.venv312/bin/python -m pytest -q`；Expected: 全部 PASS。人工檢查 prose：來源／限制／使用方法／練習／驗收齊全。
- [ ] Step 5: 僅 stage 本 task 檔案；commit `feat: add reviewed FDE learning catalog`；記 execution ledger。

### Task 2 / F2: Domain policy 與兩個薄技能包

**Files:** Modify `src/radar/workflows/{registry,bundle,catalog}.py`, `schemas/workflow-manifest.schema.json`, `src/radar/workflows/workflow-manifest.schema.json`; create `skills/fde-solution/SKILL.md`, `skills/fde-knowledge-review/SKILL.md`, 各自 `references/*.md`, `profiles/fde/general.yaml`, `bundles/fde/{README,LICENSE}.md`, `registry/workflows/fde-solution-adapter-0.1.0.yaml`, `registry/bundle-locks/fde-solution-adapter-0.1.0.json`, `tests/test_fde_bundle.py`。

**Interfaces:** Consumes F1 sources；produces WorkflowManifest 可選 `domain: android|fde`、可選 `asset_approvals: dict[path, sha256]`；兩者缺省時 to_dict 必須省略，保持舊 serialization。catalog rows 增加 domain（舊 manifest 以 android 呈現），profile roots 依 domain 決定。

- [ ] Step 1: 寫 `test_legacy_zip_hashes_unchanged` 比對 Global Constraints 兩個 literal SHA；`test_fde_bundle_references_and_domain_isolation` 解包取得兩個 SKILL/references，未知 root/private profile assert ValueError；`test_asset_hash_and_approval_required` 對 FDE 允許的 lab code/JSON 修改 hash、移除 approval 均拒絕。
- [ ] Step 2: `.venv312/bin/python -m pytest tests/test_fde_bundle.py -q`；Expected: FDE domain/包不存在而失敗。
- [ ] Step 3: 定义明列 FDE roots：skills/fde-solution、skills/fde-knowledge-review、profiles/fde、bundles/fde；lab assets 僅額外明列 `examples/fde/python/` 自有 source/fixture，禁止 runtime/weights/secret，副檔名限定 .py/.json/.csv。非 MD/YAML 資產用 approval hash，不解讀可執行檔 frontmatter。用 skill-creator／writing-skills／writing-for-agents 編寫兩個路由，官方 upstream 另安裝。由原始 repo 已提交 ref 建立 candidate 0.1.0，產生 immutable lock。
- [ ] Step 4: 同一測試、既有 bundle/export/adoption 測試＋全 pytest；Expected: PASS、兩個舊 ZIP hash unchanged；skill 以需求探索／注入指令／缺證據／更新提案情境驗證，記結果。
- [ ] Step 5: 僅 stage 此 task 檔案；commit `feat: publish isolated FDE skill adapter`；記 ledger。

### Task 3 / F3: FDE 主頁與路線／下載 UI

**Files:** Create `site/src/pages/fde/{index,updates}.astro`, `site/src/components/FdeRoadmap.astro`; modify `site/src/layouts/Layout.astro`, `site/src/pages/workflows.astro`, `site/src/styles/custom.css`, `site/tests/smoke.spec.ts`。

**Interfaces:** Consumes F1 fde.json、F2 workflow rows；produces `/fde/`、`/fde/updates/`，guides 使用既有 Starlight `guides/fde/`、downloads 用 href 的 BASE_URL。FDE updates 初始 raw＋尚無核准精選，F8 才接 domain 時間資訊。

- [ ] Step 1: 新增 Playwright `FDE roadmap and verified downloads`：/fde/ 顯示技能及前置依賴、點入指南、取 MD 與 ZIP 200/PK；`FDE mobile and untrusted text`：390px 無 overflow、惡意 title 無 script。保留原 Android card 與下載 assertions。
- [ ] Step 2: build reviewed export 後執行 `npm run test:smoke`；Expected: FDE route 尚無內容而失敗。
- [ ] Step 3: 實作可讀技能樹、12 週參考路線、流程图與可選語言／local profile；導航新增 FDE。Android/FDE workflow 卡片按 domain 呈現，候選 wording 依 domain；不把所有包稱 Android。來源／證據與下載資訊可見。
- [ ] Step 4: Astro check/build、Playwright root 與 `/ai-workflow/` 各跑一次＋全 pytest；Expected: 無新增 error/warning、所有 browser PASS、MD/ZIP 正確、無 private sentinels。測試後恢復 live export。
- [ ] Step 5: commit `feat: add FDE roadmap and skill downloads`；ledger F1–F3 完成。下一份本機 labs 計劃依賴此輸出；不在此時做分支終審或合併。

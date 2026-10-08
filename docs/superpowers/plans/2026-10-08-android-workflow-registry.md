# Android Workflow Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 將現成工作流、Android/company profile、驗收證據與可下載版本串成可持續改善的流程。

**Architecture:** Registry 固定上游 ref；公司差異以profile疊加，bundle builder僅打包經授權且可公開的內容。評測工具收集實際 Android repo 的證據，不在此文件repo造假評測結果。

**Tech Stack:** Python/pytest/JSON schema、YAML、Markdown、可重現ZIP、既有靜態網站；Android側沿用目標repo的Gradle與Maestro命令，不另建一套Android App。

**Spec:** [架構提案](../../platform-design/2026-10-08-android-ai-workflow-platform-design.md)，§2、8–9、12–13。依賴 [K1、K4、網站K5](2026-10-08-knowledge-radar-mvp.md)。

## Global Constraints

- 一個主上游工作流；Matt的方法是選配，不疊加多套完整指揮邏輯。
- 規範優先順序：專案明確決策與例外 → 公司 profile → 通用 Android 基準 → 外部工作流預設。
- 公司採 Koin annotations；不能被通用 Hilt 範例覆寫。
- discovered→candidate→evaluated→trial→approved→deprecated；熱門不等於已驗證。
- 下游依賴必須已驗收且已提供於指定整合基線；ready_for_review不等於accepted。
- parallel 初期最多2實作者；worktree隔離外另管理Gradle/emulator/帳號。
- 本計劃不自動操作Play發布、不存簽章或正式支付／登入憑證。

## Review Focus

1. 第三方授權不允許打包或技能缺scripts → W1授權與完整性測試。
2. profile precedence衝突與例外失效 → W2 Koin/Hilt與專案override測試。
3. pending／stub任務誤解鎖與共享檔案／emulator衝突 → W2 ready-set測試。
4. 零執行／全部skip或舊head的結果被當成功 → W3 evidence validation。
5. internal案例與未評測版本標成public/company-approved → W4狀態與export regression。

## File Structure / Contracts

`registry/workflows/`放manifest；`profiles/android/`放通用技術與驗收；`profiles/company/`只放私有差異。`skills/android-task/` 是自有薄adapter，呼叫目標repo工具，不實作另一套完整orchestrator。`evaluations/`放脫敏任務定義／範例；真實輸出預設私有。

W1定義 `WorkflowManifest(id,version,upstream_url,upstream_ref,license,redistribution_allowed,supported_harnesses,profile_ids,bundle_files,visibility,review_state,adoption_state,evaluation_ids)`。沒有 verified evidence不得宣稱tested。

W2定義 `TaskContract(id,spec_hash,base_sha,depends_on,read_paths,write_paths,resource_locks,acceptance,validation_commands,max_attempts,time_budget_minutes,token_budget,checkpoint,handoff_summary)`；`TaskRecord(contract,status,head_sha,integrated_sha,evidence_ids)`。evidence profile由W3驗證。

## Task W1: Registry 與完整 bundle

**Files:** Create `schemas/workflow-manifest.schema.json`, `registry/workflows/superpowers.yaml`, `src/radar/workflows/{__init__,registry,bundle}.py`, `tests/test_workflow_bundle.py`, `docs/platform-design/upstream-policy.md`。

**Interfaces:** `load_manifest(path: Path) -> WorkflowManifest`；`build_bundle(manifest: WorkflowManifest, root: Path, out: Path) -> BundleReport`；report包含zip_path、sha256、included_files、errors。

- [x] Step 1：測unknown license／redistribution_allowed=false拒絕嵌入上游內容；missing referenced script拒絕；path traversal/symlink拒絕；同內容重打包hash一致。
- [x] Step 2：`python -m pytest tests/test_workflow_bundle.py -q`，確認 FAIL。
- [x] Step 3：核對上游repo、授權、完整ref，固定一個版本；未確認授權時manifest只提供官方安裝連結，bundle僅含自有adapter與授權允許項目。ZIP固定排序、時間metadata、相對路徑；含manifest、來源／授權、安装、移除、相容性與hash。不得把本機plugin cache全部複製進repo。
- [x] Step 4：同測試 PASS；人工比較上游所需references/scripts與bundle清單；不運行未知上游script以「測一下」。精確 commit `feat: register pinned workflows and reproducible bundles`。

## Task W2: Android/company profile 與任務依賴驗證

**Files:** Create `profiles/android/{baseline,verification}.yaml`, `profiles/company/{profile,decisions}.yaml`, `schemas/task-contract.schema.json`, `src/radar/workflows/{profiles,tasks}.py`, `skills/android-task/SKILL.md`, `skills/android-task/references/{task-contract,verification}.md`, `tests/{test_profiles,test_task_readiness}.py`。

**Interfaces:** `resolve_profile(upstream: dict, android: dict, company: dict, project: dict) -> ResolvedProfile`；`ready_tasks(records: list[TaskRecord], integrated_sha: str, available_resources: set[str]) -> list[str]`。明確枚舉規則欄位，來源與例外註記不得被merge丟失。

- [x] Step 1：測 upstream.di=hilt、company.di=koin_annotations，resolved.di==koin_annotations；project明確例外優先且附reason；未聲明覆寫的矛盾規範返回diagnostic；cycle拒絕；ready_for_review依賴不解鎖；accepted但未integrated不解鎖；write path祖先重疊／同emulator lock不同任務不能同批；最多2ready。
- [x] Step 2：指定兩個pytest檔先 FAIL。
- [x] Step 3：精讀既有guide與decision，把原則引用到profile而非複製數十頁。公司profile private。薄skill輸入TaskContract、輸出patch＋evidence＋handoff；要求依賴先整合、有限重試max3、失敗blocked、checkpoint恢復、支付／登入／發布人類確認。不替換上游自身的plan/execute流程。
- [x] Step 4：同測試 PASS；按 writing-for-agents及writing-skills skill實作時驗證skill能被目標harness讀取。此repo没有Android source，mock dry-run只能標為契約測試。Sol審查precedence與依賴語意。
- [x] Step 5：精確 commit `feat: add Android profiles and task acceptance contracts`。

## Task W3: 評測證據與採納決策

**Files:** Create `evaluations/tasks/{compose-state,viewmodel-retry,network-error,data-sync,koin-injection,module-contract,bug-regression,maestro-path}.yaml`, `schemas/evaluation-run.schema.json`, `src/radar/workflows/{evidence,evaluate}.py`, `tests/test_evaluation_evidence.py`, `docs/platform-design/evaluation-runbook.md`。

**Interfaces:** `validate_evidence(run: EvaluationRun, expected_head: str, acceptance_ids: set[str]) -> EvidenceVerdict`；`compare_runs(baseline: list[EvaluationRun], candidate: list[EvaluationRun]) -> ComparisonReport`。EvaluationRun含 task_id、spec_hash、base/head_sha、model/harness版本、commands/exitcodes、executed/failed/skipped、acceptance_results、cost/human_minutes/duration、artifact_refs、provenance；缺實測數據為null，不能補0。

- [x] Step 1：測executed=0拒絕；failed>0拒絕；expected_head與run.head不符拒絕；missing acceptance不complete；相同spec/base/env的run才可配對比較；mock fixture provenance=synthetic不得晉升evaluated。
- [x] Step 2：`python -m pytest tests/test_evaluation_evidence.py -q`，確認 FAIL。
- [x] Step 3：寫8個代表行為的任務目標、acceptance與風險，沒有實際repo時保留待binding，不能猜package/Gradle module命令。runbook說明baseline／upstream／company-profile三組、固定base、holdout及immutable驗收；只對文件／schemafixture跑測試。
- [x] Step 4：實作Gradle JUnit XML evidence輸入（有Maestro報告則adapter，無相容格式就人工提供明確結果不自造成功）；真實runner前要求target repo+SHA+命令+環境binding。命令作argument array且profile來源需核准，不執行文章給的任意指令。
- [x] Step 5：同測試 PASS；提供synthetic comparison示例、缺失資料清單。若有真實測試repo，才實際跑代表任務並另記證據；本輪無repo則實測部分blocked。Sol審查品質門檻，精確 commit `feat: evaluate workflow changes from execution evidence`。

## Task W4: 網站使用指南、下載與版本採納

**Files:** Create `content/public/{workflows/index,android/getting-started,android/task-flow,cases/evidence-levels}.md`, `schemas/change-proposal.schema.json`, `src/radar/workflows/adoption.py`, `tests/test_adoption.py`；Modify `src/radar/export.py`, site workflow/下載頁。

**Interfaces:** `transition(manifest: WorkflowManifest, target: str, evidence: list[EvaluationRun], review: AdoptionReview) -> WorkflowManifest`；AdoptionReview含owner、decision_at、reason、profile_scope、rollback_version。candidate→evaluated要有效實測，trial→approved要人類決策；deprecated可保留歷史下載並明顯標示。

- [x] Step 1：測候選版本沒有效run無法evaluated；mock不得company-approved；private profile與internal case排除export；bundle manifest/hash正確；deprecated顯示替代與風險；revision更新不改過去版本的評測。
- [x] Step 2：`python -m pytest tests/test_adoption.py tests/test_export.py -q`，確認 FAIL。
- [x] Step 3：實作catalog卡片、版本、harness/profile相容性、下載與安裝/移除說明、流程圖；案例明確標示證據等級。新自有指南用synthetic示範但非成功案例；第三方不自動再散布。W3沒有實測時狀態保持candidate，介面仍可展示。
- [x] Step 4：pytest PASS、site check/build/smoke PASS；確認搜尋與ZIP都沒有company profile。發布指南review與公司採納review分開；public guide approved不代表company-approved。
- [x] Step 5：精確 commit `feat: publish traceable workflow guides and adoption status`。

## Completion / Handoff

可交付registry、完整自有bundle、profile契約、評測工具與指南。不具備Android測試repo时不得宣稱此工作流提升品質／效率；交付需列「契約工具已驗證／Android實測待接」。後續按雙週資訊→候選→代表任務→trial→採納，不自動追每個新release更新公司規範。

本機交付與審查修正完成；驗證與裁定見 [W執行紀錄](../../platform-design/workflow-execution-log.md)。Android真實評測仍待repo/SHA/環境binding，所有發布版本為candidate。

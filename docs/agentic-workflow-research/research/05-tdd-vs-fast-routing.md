# Does test-first help LLM coding agents, and how do shipped kits route between a TDD path and a fast path (with an Android layer map)

## SUMMARY
The evidence does not support "TDD always" for agents; it supports "a valid oracle always, test-first only where red is cheap and real." The single most decision-relevant result (TDAD, arXiv 2603.17973v2, Qwen3-Coder 30B, 100 SWE-bench Verified instances) is that TDD *prompting alone* raised the test-regression rate from 6.08% to 9.94% (+42% P2P failures) at identical 31% resolution, while injecting a static source→test map (which tests to run) cut it to 1.82%. Its shipped SKILL.md is not test-first at all: step 1 is "make the change," step 2 is `grep test_map.txt`. TDFlow (2510.23761) shows why: 94.3% on SWE-Bench Verified with human tests vs 68.0/69.8% with self-generated ones — but 93.3% once you condition on the generated test actually being a valid reproducer. The loop does the work; an invalid self-generated oracle destroys it, at ~4x the cost ($4.12 vs $1.01/issue). TDD-Bench Verified (449 instances) puts hard numbers on oracle validity: GPT-4o's best agent reaches only 23.6% fail-to-pass; ~10% of its tests pass on the *unfixed* code (tautological) and ~73% of the ones that do fail keep failing after the gold patch. Non-fail-to-pass tests have 0.49–0.59 coverage vs 0.93 for humans, yet 35% of them still hit perfect coverage — coverage is not correctness. Test overfitting (2511.16858) shows iterating harder against self-generated tests makes things *worse* (Claude 21.8%→25.5% wrong-but-green). Counterweight: test-first genuinely helps when the model would otherwise see buggy code (25% vs 14% fault detection, 2607.05139; 8x misguided-test rate from buggy input, 2607.22883). Shipped kits converge on this: BMAD v6 collapsed five "project levels" to a single binary route on *zero blast radius*, freezes an I/O matrix pre-approval and audits tests against it after; cc-sdd gates TDD behind a Feature Flag Protocol explicitly skipped for refactor/config/docs and demands captured RED output as proof; spec-kit makes tests opt-in ("Tests are OPTIONAL"); Pocock forbids any test at an unconfirmed seam and puts refactoring outside the loop; Anthropic reserves "write a failing test" for the bug row and offers screenshot/build/lint oracles elsewhere.

## KEY FACTS
### TDD prompting alone increased agent regressions from 6.08% to 9.94%; graph context (which tests to run) cut it to 1.82%
TDAD Phase 1: Qwen3-Coder 30B (4-bit, llama.cpp), 100 SWE-bench Verified instances, 3 arms. Vanilla (49-line prompt): 6.08% test-regression rate, 562 pass-to-pass failures, 31% resolution, 86% generation. TDD Prompt (119-line): 9.94%, 799 P2P failures (+42%), 31% resolution, 75% generation. GraphRAG+TDD (TDD + SKILL.md + test_map.txt): 1.82%, 155 P2P failures, 29% resolution, 74% generation. Paper: 'TDD prompting without graph context increased regressions (6.08% -> 9.94%), producing 42% more P2P failures than vanilla.' Also: 'doubling prompt length without graph context (49-line vanilla vs 119-line TDD) produced identical 31% resolution' — so the harm is from the ambition TDD induces, not from prompt length. Explanation given: 'Verbose prompts hurt small models' + 'Ambition without localization' — TDD-prompted agents touched more files without knowing which tests to verify. Author conclusion: for smaller models 'surfacing the right information' beats 'prescribing workflow'. Limitations the paper states itself: 100 and 25 instances with NO formal significance tests, two small local models only, Python only, cannot capture dynamic dispatch/monkey-patching. Resolution dropped 31%->29% under TDAD, framed as intentional conservatism.
SRC: https://arxiv.org/html/2603.17973v2

### TDAD Phase 2: TDAD skill raised resolution 24%->32% and patch generation 40%->68% on 25 instances; regression 0% in both arms
Qwen3.5-35B-A3B (4-bit, MLX), 25 SWE-bench Verified instances, OpenCode agent. Baseline: 6/25 resolved (24%), 10/25 generated (40%), 15 empty patches. TDAD Skill: 8/25 (32%), 17/25 generated (68%), 8 empty patches. Resolution-of-generated 60% vs 62%. The paper also reports 'simplifying SKILL.md from 107 to 20 lines alone quadrupled resolution from 12% to 50%' — i.e. instruction bulk was the dominant negative factor for a small model.
SRC: https://arxiv.org/html/2603.17973v2

### TDAD's shipped SKILL.md is NOT test-first — it is a post-change regression guard
Verbatim workflow order in tdad/SKILL.md: '### 1. Make the change' -> '### 2. Find impacted tests' (grep test_map.txt) -> '### 3. Run impacted tests' -> '### 4. If test_map.txt has no entry' (naming-convention fallback). Rules section: 'Never submit a patch without running impacted tests first.' and 'Run the minimum set of tests needed (not the full suite) for speed.' Skill activates 'when there is a .tdad/ directory in the repository'. This is the arm that beat the TDD-prompt arm.
SRC: https://github.com/pepealonso95/TDAD/blob/main/tdad/SKILL.md

### TDFlow: 94.3% on SWE-Bench Verified with human tests vs 68.0% self-generated — but 93.3% when the self-generated test is a valid reproducer
arXiv 2510.23761. SWE-Bench Lite (300 instances, GPT-4.1 across all systems): TDFlow 88.8% vs next-best Agentless 61.0% = +27.8pp absolute. Other baselines: SWE-Agent 49.0% ($0.89), ExpeRepair 48.6% ($0.84), OpenHands 47.8% ($1.32), Agentless 61.0% ($0.53), TDFlow $1.51. SWE-Bench Verified (500): human-written tests 94.3% ($1.01/issue); human tests without debugging 87.2% ($0.73); LLM-generated tests 68.0%/69.8% ($4.12/issue). Sub-slice: when Bad Test Rate = 0 (all generated tests are valid reproduction tests), 93.3%. Models: Explore Files / Debug One / Revise Patch on GPT-5 for Verified; Generate Tests on Claude 4 Sonnet. Paper: 'whether the reproduction test is written by a human or an LLM doesn't matter for downstream test resolution performance so long as the test truly tests for reproduction behavior.' Interpretation of the delta: the ~26pp human-vs-self gap collapses to ~1pp once test validity is controlled, so the LOOP is doing the work and the TEST SOURCE only matters via validity — and the self-generated path costs ~4x per issue for that 26pp. Test hacking: 3 engineers manually reviewed 800 runs, found 7 instances (4 Lite, 3 Verified) ~= 0.875%, marked as failures.
SRC: https://arxiv.org/html/2510.23761v2

### TDD-Bench Verified: best agent reaches 23.6% fail-to-pass on 449 real issues; ~10% of generated tests pass on the UNFIXED code
arXiv 2412.02883 (Ahmed, Hirzel, Pan, Shinnar, Sinha, IBM). 449 instances filtered from SWE-bench Verified's 500 (7 removed for environment recreation failures, 44 for golden tests lacking fail-to-pass behavior or zero coverage), 12 Python repos, Django 47.2%. Table III (449 instances): Llama-3.1 zero-shot 51 F2P = 11.4% (tddScore 10.3), Auto-TDD 37 = 8.2% (7.8) — WORSE. Mistral-Large zero-shot 57 = 12.7% (11.8), Auto-TDD 85 = 18.9% (18.3). GPT-4o zero-shot 84 = 18.7% (17.2), Auto-TDD 106 = 23.6% (22.6). Tautology arithmetic for GPT-4o Auto-TDD: 15 lost to syntax/format, 392 fail on c_old out of 434 parseable, so ~42 (~9.7%) PASSED on the unfixed code ('Some tests may pass even on the prior version c_old of the code; such tests are irrelevant for us'); of the 392 that did fail, 286 still fail after the gold patch (73% broken-for-the-wrong-reason) and only 106 flip to pass. Union of all 3 models = 135/449 = 30% ceiling. Golden human tests themselves score only 0.94.
SRC: https://arxiv.org/abs/2412.02883

### TDD-Bench adequacy is bimodal, and coverage does not imply a valid test: 35% of non-fail-to-pass tests had perfect coverage
Table VII. Fail-to-pass model tests: 0.91-0.97 adequacy vs 0.93-0.99 for developer tests, difference not significant at 99% CI (Wilcoxon signed-rank, p=0.01-0.59). Non-fail-to-pass model tests ('Others', 313-349 of 449 per model): 0.49-0.59 vs 0.93-0.94 developer, p<0.001. Discussion: 'We have seen 35% of non-fail-to-pass tests with perfect coverage using GPT-4o based Auto-TDD. This indicates that tests can achieve perfect coverage even without being fail-to-pass.' Practical use the authors propose: low coverage can be used to DISCARD candidates unlikely to be fail-to-pass, since almost all fail-to-pass tests exceed 0.90.
SRC: https://arxiv.org/abs/2412.02883

### TDD-Bench counter-evidence: showing the model the implementation ('write first, test later') scored slightly HIGHER than test-first
RQ3, Table VI. With the git-diff code patch added to the prompt: GPT-4o Auto-TDD 109 F2P = 24.3% (final score 23.6%) vs 106 = 23.6% (22.6%) in the TDD setting. Mistral-Large 97 = 21.6% vs 85 = 18.9%. Llama-3.1 zero-shot 64 = 14.3% vs 51 = 11.4%. Caveat that matters: fail-to-pass is measured against the same gold patch the model was shown, so this metric structurally rewards a test that mirrors the diff — it does NOT show the resulting tests encode the requirement.
SRC: https://arxiv.org/abs/2412.02883

### Bug fixes yield ~45% valid reproducer tests; feature work drops to 15-30%, and proprietary repos collapse to 4%
'Reproduction Test Generation for Java SWE Issues' (Ahmed, Ganhotra, Shinnar, Hirzel, 2026-05-11). TDD-Bench-Java: 250 instances from Multi-SWE-bench (128) + SWE-PolyBench (165) after filtering for fail-to-pass and dedup. e-Otter++ achieves 43.6% (Claude-Sonnet-4.5) and 46.4% (GPT-5.2) fail-to-pass. Table 4 by issue type — Open-source: Bug 177 instances, 44.1% F2P; Feature 73 instances, 30.1%. Proprietary (150 instances): Bug 24 instances, 45.8%; Feature 126 instances, 15.1%. Aligned vs misaligned: open-source aligned 40.7%, proprietary aligned 21.3%, proprietary misaligned 14.3%. Finding 5 verbatim: 'With the default issue description, e-Otter achieved only 4% fail-to-pass rate on proprietary projects. However, adding hints with newly introduced class names and function signatures increased the performance to 20%.' Cost: ~$2.5/instance (Claude-Sonnet-4.5) and ~$1.5 (GPT-5.2) for 6 candidates + selector; $0.42/$0.30 per candidate.
SRC: https://arxiv.org/pdf/2605.04320

### Test overfitting: 21.8-33.0% of instances 'resolved' against self-generated tests actually fail the hidden golden tests — and refinement makes it worse
'Investigating Test Overfitting on SWE-bench' (Ahmed, Ganhotra, Shinnar, Hirzel, IBM; FSE 2026, Montreal, Jul 5-9). Without code refinement: Claude-3.7-Sonnet 21.8%, GPT-4o 33.0% of initially-resolved instances fail golden tests. WITH code refinement the rate INCREASES: Claude 25.5%, GPT-4o 35.9% — iterating harder against a self-generated oracle worsens overfitting. With access to golden tests: Claude 5.8%, GPT-4o 11.3%. Overfitted patches have median coverage 0.8 vs 1.0 for correct patches, so execution coverage is usable as an early-warning proxy without hidden-test access.
SRC: https://arxiv.org/html/2511.16858

### Tests written after seeing buggy code detect ~14% of faults vs ~25% written from the task description alone
'On the risk of coding before testing: An empirical study on LLM-based test generation workflow' (Konstantinou, Tambon, Papadakis; SnT, University of Luxembourg; arXiv 2607.05139v1, 2026-07-06). Benchmarks: HumanEval+ (164 tasks), MBPP (974), BigCodeBench (1140); 5 models (Claude Haiku 4.5, DeepSeek V4-Flash, GPT-4.1-mini, GPT-5-mini, Llama 3.3 70B); 10 implementations per task at temperature 0.8. Headline: 'Generating tests before code generation achieves a fault detection rate of 25%, significantly surpassing the fault detection rate of approximately 14% observed when tests are generated after erroneous code.' Per-model fault-detection reduction from exposing the implementation: 9.1% / 15.2% / 18.2% / 12.9% / 10.7%, average 13.2%. Test-Driven Workflow vs Agentic Workflow improvement: 10.6 / 13.8 / 17.7 / 13.6 / 7.9, average 11.7%. Crucial mechanism: 'Once the implementation is introduced to the model, it primarily relies on the implementation rather than the task description' — adding the task description back on top of the code gives only +1.9%. Names the failure mode 'aligned failures': incorrect code and incorrect tests mutually consistent, so 'tests validate incorrect behavior rather than expose it'.
SRC: https://arxiv.org/pdf/2607.05139

### Buggy code in context causes an 8x increase in tests that assert the bug and a 3x drop in bug-detecting tests
'Evaluating and Mitigating the Misguidance Effect of Buggy Code in LLM-Generated Unit Tests' (Zhao, Zhou, Cohen; University of Toronto; arXiv 2607.22883, 2026-07-24). Defects4J 3.0: 854 defects across 17 Java projects narrowed to 318 focal methods covering 233 defects; 11 LLMs across 6 vendors. Misguided tests (asserting buggy behavior): 3.84% of generated tests (137.69 avg) with buggy input vs 0.46% (16.46) with fixed input — >8x. Effective (bug-detecting) tests: 2.98% (104.15) vs 8.51% (304.08) — ~3x fewer. Mitigation via LLM-generated docstrings instead of buggy code: misguided 137.69 -> 113.00 (-17.9%), effective 104.15 -> 186.77 (+79.3%), focal methods detecting bugs 45.46 -> 73.31 (+61%). With intent-derivation: misguided -> 87.38 (-22.8%), effective -> 230.23 (+23.3%).
SRC: https://arxiv.org/html/2607.22883

### Agent-written tests are mostly observational, and flipping test-writing on or off barely moves resolve rate but moves cost a lot
'Rethinking the Value of Agent-Generated Tests for LLM-Based Software Engineering Agents' (arXiv 2602.07900v2). SWE-bench Verified 500 instances; 6 LLMs: Claude Opus 4.5, Gemini 3 Pro, GPT-5.2, Kimi K2 Thinking, MiniMax M2, DeepSeek v3.2 Reasoner; 1,500 baseline trajectories plus intervention runs. Signal composition: value-revealing prints consistently outnumber assertions (Claude 4.5 resolved tasks 25.00 prints vs 5.16 assertions per task; MiniMax M2 34.06 vs 7.37). Assertion taxonomy: C4 exact checks 40.85-42.91%, C2 property checks 33.62-41.42%, C1 sanity checks 14.92-19.83%, C3 relational checks 2.98-7.86%. RQ3 prompt interventions: GPT-5.2 'encourage' shifted 64.4% of tasks to 'has test' with 0 net success change (p=1.000) but +5.5% API calls and +19.8% output tokens; Kimi K2-T 'discourage' shifted 68.4% to 'no test' with -13 net success (p=0.228), -35.4% API calls, -49.0% input tokens, -2.6pp resolution. Conclusion: 'Agent-written testing is better understood as a model-dependent process style rather than a dependable driver of success.'
SRC: https://arxiv.org/html/2602.07900v2

### WebApp1K: letting tests conform to the code nearly doubles a weak model's pass rate — the tautology tax measured from the other side
'Tests as Prompt: A Test-Driven-Development Benchmark for LLM Code Generation' (Yi Cui, arXiv 2505.09027). 1,000 challenges across 20 domains, React, test pairs generated by GPT-4o; 19 frontier models. pass@1: o1-preview 0.952, o1-mini 0.939, deepseek-r1 0.927, gpt-4o-2024-08-06 0.885, claude-3.5-sonnet 0.881, llama-v3-70b 0.332, mixtral-8x22b 0.307, llama-v3-8b 0.068. Test-Last Development experiment: when tests were modified to accommodate the generated code, llama-v3-70b jumped from 33% to 64% — the models could write functional code but failed to follow the spec. Instruction loss: doubling prompt length (0.5K -> 1K tokens, duo-feature tasks) dropped claude-3.5 from 88% to 75%. Claim: 'instruction following and in-context learning as critical capabilities for TDD success, surpassing the importance of general coding proficiency or pretraining knowledge.' Note: 2025 paper, models are now two generations old; the mechanism (instruction loss in long prompts) is the durable part.
SRC: https://arxiv.org/abs/2505.09027

### TEBench: agents identify which tests need to evolve at only 45.7-49.4% F1, and are structurally blind to stale tests
'Breaking, Stale, or Missing? Benchmarking Coding Agents on Project-Level Test Evolution' (Shang, Zhang, Hu, Fang, Xiao, Chen; arXiv 2605.06125, submitted 2026-05-07). 314 task instances from 10 Defects4J Java projects. 7 configurations across Claude Code, Codex CLI, OpenCode with six base models plus a heuristic baseline. Identification F1: Codex CLI 49.4%, OpenCode-GLM 49.3%, OpenCode-Kimi 48.5%, OpenCode-Sonnet 48.3%, OpenCode-Qwen 48.2%, Claude Code 47.1%, OpenCode-DeepSeek 45.7%. By evolution type: Test-Breaking ~59.9%, Test-Missing ~52.9%, Test-Stale ~35.8%. Update composite 63.6-72.3% (Codex CLI 72.3% best, Claude Code 70.5%); executability 87.7-99.2% but modification similarity lags — 'producing executable tests is far easier than aligning with developer intent'. Core finding: agents run a 'reactive execute-fail-fix loop' that 'succeed[s] for Test-Breaking but cannot address Test-Stale, since no failure signal is available', and the reactive pattern 'encourages branch-level patching rather than behavior-level test design'.
SRC: https://arxiv.org/abs/2605.06125

### Coding agents add mocks to tests 38% more often than humans (36% vs 26% of commits)
'Are Coding Agents Generating Over-Mocked Tests? An Empirical Study' (Andre Hora, Romain Robbes; MSR 2026; arXiv 2602.00409, submitted 2026-01-30). 1.2M+ commits from 2025, 2,168 repositories (TypeScript, JavaScript, Python), 48,563 agent commits, 169,361 test-modifying commits, 44,900 mock-addition commits. 36% of agent commits add mocks to tests vs 26% by non-agents; 23% of agent commits add/change test files vs 13% non-agents; 60% of repos with agent activity have agent test activity; 68% of those have agent mock activity. Relevance: mock-heavy tests are the implementation-coupled anti-pattern, and Now in Android deliberately uses zero mocking libraries.
SRC: https://arxiv.org/abs/2602.00409

### Blind LLM-judged comparison found no discernible quality difference between TDD and non-TDD agent runs, at 3-8.5x the token cost
Martin Fowler / Thoughtworks memo 'TDD inside the agent loop - theater or actual value?'. Setup: Sonnet 4.6 generated solutions, Opus 4.8 judged them 'without knowledge of how the solutions were created' using a rubric created on the fly and passed to all subagents. Five batches (1 small, 3 medium, 1 large), each with 2 non-TDD and 2 TDD solutions (one medium batch also had test-first variants). Token multiples: small 8.50x, medium 2.96x, large 4.89x. Non-TDD solutions dominated top rankings (medium round 1: non-TDD ranked #1 and #2, TDD #3 and #4; pattern repeated in round 2). Conclusion verbatim: 'Based on Opus's judgment of the quality of the outcomes, there was no clearly discernable difference based on TDD workflow versus no TDD workflow.' CAVEAT: n is tiny, LLM-as-judge, no statistical testing — treat as directional only, not as a result on par with the arXiv work.
SRC: https://martinfowler.com/articles/exploring-gen-ai/tdd-in-the-agent-loop.html

### BMAD v6 shipped exactly two routes, keyed only on blast radius, and defaults to the heavy path when uncertain
src/bmm-skills/ship/bmad-build/step-01-clarify-and-route.md, step 5 'Route — choose exactly one': '(a) One-shot — zero blast radius: no plausible path by which this change causes unintended consequences elsewhere. Clear intent, no architectural decisions.' -> step-oneshot.md. '(b) Plan-code-review — everything else. When uncertain whether blast radius is truly zero, choose this path.' No numeric thresholds anywhere. Inputs read before routing, in order: explicit file argument (frontmatter status in {draft, ready-for-dev, in-progress, in-review, done} routes directly to step-02/03/04), recent conversation, then a scan of {implementation_artifacts} for active specs, plus sprint-status.yaml story-key resolution by exact numeric equality on the first two segments 'so 1-1 never collides with 1-10'.
SRC: https://github.com/bmad-code-org/BMAD-METHOD/blob/main/src/bmm-skills/ship/bmad-build/step-01-clarify-and-route.md

### BMAD v6 has four HALT points before code is written, and the human-owned intent is cryptographically-frozen text, not a vibe
Human confirmation points in bmad-build: (1) step-01 §2 clarify intent — numbered question list, 'When the human replies, verify that every single numbered question was answered. If any were ignored, HALT and re-ask'; (2) step-01 §3 version-control sanity — dirty tree or mismatched branch -> HALT; (3) step-01 §4 multi-goal check — 'Multi-goal means >=2 top-level independent shippable deliverables — each could be reviewed, tested, and merged as a separate PR without breaking the others. Never count surface verbs, "and" conjunctions, or noun phrases.' -> HALT with Split / Keep all goals; (4) step-02 CHECKPOINT 1 — Approve and continue / Approve and stop / Review spec, then 'Set status ready-for-dev; everything inside <frozen-after-approval> is then locked and only the human can change it.' SCOPE STANDARD: single user-facing goal, 900-1600 tokens ('Below 900 risks ambiguity; above 1600 risks context-rot in implementation agents'), and explicitly 'Neither limit is a gate. Both are proposals with user override.'
SRC: https://github.com/bmad-code-org/BMAD-METHOD/blob/main/src/bmm-skills/ship/bmad-build/step-02-plan.md

### BMAD v6 is NOT test-first: it freezes an I/O matrix before code, writes tests after, then audits tests against the frozen matrix
spec-template.md puts '## I/O & Edge-Case Matrix' (Scenario | Input/State | Expected Output/Behavior | Error Handling) inside <frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">, with 'If no meaningful I/O scenarios exist, DELETE THIS ENTIRE SECTION.' Tasks section comment: 'If an I/O Matrix is present, include a task to unit-test its edge cases.' Then step-03-implement.md '### Matrix Test Audit' runs AFTER implementation: 'verify every matrix row is covered by at least one test that verifies its expected behavior, and that each covering test ran and passed in the verification output. A covering test that exists but did not run — unregistered, filtered out, skipped, or disabled — counts as missing. If a test disagrees with the matrix, never edit the expectation to match the code: fix the code, or if the matrix row itself is ambiguous, HALT and ask the human.' This decouples 'agree the behavior contract first' from 'write the test first' — you get the spec-clarification benefit of TDD without paying the horizontal-slicing cost.
SRC: https://github.com/bmad-code-org/BMAD-METHOD/blob/main/src/bmm-skills/ship/bmad-build/spec-template.md

### BMAD's evolution: five project levels (0-4) -> three tracks -> deleted entirely -> one binary blast-radius route
CHANGELOG.md timeline: 6.0.0-alpha.0 (2025-09-28) 'BMad Method (BMM): Complete scale-adaptive rewrite supporting projects from small enhancements to massive undertakings'; 6.0.0-alpha.4 (2025-11-02) 'Quick Spec Flow: Intelligent Level 0-1 planning with auto-stack detection'; 6.0.0-alpha.5 (2025-11-04) '3-Track Scale System: Simplified from 5 levels to 3 intuitive preference-driven tracks'; 6.0.0-alpha.9 (2025-11-12) '3-Track System: Simplified from 5 levels to 3 intuitive tracks'; later 'Removed Scale Adaptive System: 618-line doc consolidated'. Stable v6 main ships the binary route above. Lesson: a multi-level a-priori project-size taxonomy did not survive contact with real use; one observable axis (blast radius) with a default-to-heavy tiebreak did. Separately, v6 now scores rather than judges follow-up review: 'followup_review_recommended is arithmetic over the final pass's patch-triaged findings: true if any high, or if 3 x medium + 1 x low >= 5' (#2580). Legacy V4 kept bmad-core/data/test-levels-framework.md, but that routes unit-vs-integration-vs-E2E, not TDD-vs-no-TDD.
SRC: https://github.com/bmad-code-org/BMAD-METHOD/blob/main/CHANGELOG.md

### cc-sdd v3.0.2 gates TDD behind a Feature Flag Protocol with an explicit skip list and an automated tautology check
tools/cc-sdd/templates/agents/claude-code-skills/skills/kiro-impl/SKILL.md, '## Feature Flag Protocol': '1. Add flag (OFF by default) ... 2. RED -- flag OFF: Write tests for the new behavior. Run tests -> must FAIL. If tests pass with flag OFF, the tests are not testing the right thing. Rewrite. 3. GREEN -- flag ON + implement ... 4. Remove flag: Make the code unconditional. Run tests -> must still PASS.' Then: 'Skip this protocol for: refactoring, configuration, documentation, or tasks with no behavioral change.' That skip list IS the fast-path route, and the 'if tests pass with flag OFF, rewrite' rule is a mechanised tautological-test detector — directly addressing TDD-Bench's ~10% already-passing rate. The flag also solves the practical problem that new code doesn't exist yet, so 'red' would otherwise be a compile error rather than a behavioral failure.
SRC: https://github.com/gotalab/cc-sdd/blob/main/tools/cc-sdd/templates/agents/claude-code-skills/skills/kiro-impl/SKILL.md

### cc-sdd requires captured RED output as a machine-parsed proof-of-red field, and hard-bounds every retry loop
implementer-prompt.md status block requires '- RED_PHASE_OUTPUT: <test command and failing output from before implementation -- proves tests were written first>' alongside '- TESTS_RUN:' and '- EVIDENCE:'. Depth routing in kiro-impl: (1) mode — task numbers given -> manual mode in main context, no task numbers -> autonomous mode with a fresh implementer subagent per task plus an independent reviewer subagent plus a fresh-context debugger; (2) '--review required|inline|off', default required, accepts NL opt-outs ('skip review', 'without review'), and 'If the request is ambiguous, keep required'; (3) bounded loops — 'Max 2 implementer re-dispatch rounds per reviewer rejection, then debug', 'Max 2 debug rounds per task', 'Cap final-validation remediation at 3 rounds'; (4) tasks.md annotations '_Blocked:_' (skip), '_Depends:_' (prereq gate), '_Boundary:_' (component scope), '(P)' which is 'informational for task planning, not an execution directive' — parallel-marked tasks still run sequentially to avoid git conflicts. Strict handoff parsing: only the exact '## Status Report' / '- STATUS:' in {READY_FOR_REVIEW, BLOCKED, NEEDS_CONTEXT} and '## Review Verdict' / '- VERDICT:' in {APPROVED, REJECTED} count; prose triggers exactly one re-dispatch. Debug escalation: 'NEXT_ACTION: STOP_FOR_HUMAN | BLOCK_TASK | RETRY_TASK'. The debug subagent 'runs in a fresh context — it receives only the error information, not the failed implementation history. This avoids the context pollution that causes infinite retry loops.'
SRC: https://github.com/gotalab/cc-sdd/blob/main/tools/cc-sdd/templates/agents/claude-code-skills/skills/kiro-impl/templates/implementer-prompt.md

### cc-sdd's Preflight is a working implementation of 'does a fast deterministic oracle already exist' — it discovers TEST/BUILD/SMOKE commands from the repo
kiro-impl SKILL.md, Step 1 Preflight '**Discover validation commands**': 'Inspect repository-local sources of truth in this order: project scripts/manifests (package.json, pyproject.toml, go.mod, Cargo.toml, app manifests), task runners (Makefile, justfile), CI/workflow files, existing e2e/integration configs, then README*. Derive a canonical validation set for this repo: TEST_COMMANDS, BUILD_COMMANDS, and SMOKE_COMMANDS. Prefer commands already used by repo automation over ad hoc shell pipelines. For SMOKE_COMMANDS, choose the lightest trustworthy runtime-liveness check for the app shape (for example: root URL load, Electron launch, CLI --help, service health endpoint, mobile simulator/e2e harness if one already exists). Keep the full command set in the parent context, and pass only the task-relevant subset to implementer and reviewer subagents.' Also '**Establish repo baseline**: Run git status --porcelain and note any pre-existing uncommitted changes.'
SRC: https://github.com/gotalab/cc-sdd/blob/main/tools/cc-sdd/templates/agents/claude-code-skills/skills/kiro-impl/SKILL.md

### Matt Pocock's 'pre-agreed seam' is agreed by the USER, before the first test is written, and no test may exist at an unconfirmed seam
skills/engineering/tdd/SKILL.md, '## Seams — where tests go': 'A seam is the public boundary you test at: the interface where you observe behavior without reaching inside. Tests live at seams, never against internals.' Then verbatim: '**Test only at pre-agreed seams.** Before writing any test, write down the seams under test and confirm them with the user. No test is written at an unconfirmed seam. You can''t test everything — agreeing the seams up front is how testing effort lands on the critical paths and complex logic instead of every edge case.' And: 'Ask: "What''s the public interface, and which seams should we test?"' Where it sits in the flow: skills/engineering/implement/SKILL.md is 11 lines total and says only 'Implement the work described by the user in the spec or tickets. / Use /tdd where possible, at pre-agreed seams. / Run typechecking regularly, single test files regularly, and the full test suite once at the end. / Once done, use /code-review to review the work. / Commit your work to the current branch.' — so the routing decision is deliberately delegated to a human-agreed artifact rather than inferred by heuristic, and the oracle cadence is explicitly graded (typecheck often > single test file often > full suite once).
SRC: https://github.com/mattpocock/skills/blob/main/skills/engineering/tdd/SKILL.md

### Pocock names the tautological test precisely and puts refactoring OUTSIDE the red-green loop
Anti-patterns section verbatim: '**Tautological** — the assertion recomputes the expected value the way the code does (expect(add(a, b)).toBe(a + b), a snapshot derived by hand the same way, a constant asserted equal to itself), so it passes by construction and can never disagree with the code. Expected values must come from an independent source of truth — a known-good literal, a worked example, the spec.' And '**Horizontal slicing** — writing all tests first, then all implementation. Bulk tests verify _imagined_ behavior: you test the _shape_ of things rather than user-facing behavior, the tests go insensitive to real changes, and you commit to test structure before understanding the implementation. Work in **vertical slices** instead — one test -> one implementation -> repeat, each test a **tracer bullet** that responds to what the last cycle taught you.' Rules of the loop: 'Red before green.' / 'One slice at a time.' / '**Refactoring is not part of the loop.** It belongs to the review stage (see the code-review skill), not the red -> green implementation cycle.'
SRC: https://github.com/mattpocock/skills/blob/main/skills/engineering/tdd/SKILL.md

### Pocock's /to-tickets uses blast radius as the named routing input, escaping vertical slicing into expand-contract
skills/engineering/to-tickets/SKILL.md: 'Each slice cuts a narrow but COMPLETE path through every layer (schema, API, UI, tests) — vertical, NOT a horizontal slice of one layer / A completed slice is demoable or verifiable on its own / Each slice is sized to fit in a single fresh context window.' Then the routing exception verbatim: '**Wide refactors are the exception to vertical slicing.** A **wide refactor** is one mechanical change — rename a column, retype a shared symbol — whose **blast radius** fans across the whole codebase, so a single edit breaks thousands of call sites at once and no vertical slice can land green. Don''t force it into a tracer bullet; sequence it as **expand-contract**. First expand: add the new form beside the old so nothing breaks. Then migrate the call sites over in batches sized by blast radius (per package, per directory), each batch its own ticket blocked by the expand, keeping CI green batch to batch because the old form still exists. Finally contract: delete the old form once no caller remains, in a ticket blocked by every migrate batch. When even the batches can''t stay green alone, keep the sequence but let them share an integration branch that all block a final integrate-and-verify ticket — green is promised only there.' Human gate is step 4 'Quiz the user' on granularity, blocking-edge correctness, and merge/split, 'Iterate until the user approves the breakdown.'
SRC: https://github.com/mattpocock/skills/blob/main/skills/engineering/to-tickets/SKILL.md

### GitHub spec-kit makes tests opt-in by human flag, not by heuristic, but enforces strict test-first ordering once enabled
templates/commands/tasks.md, Task Generation Rules: '**Tests are OPTIONAL**: Only generate test tasks if explicitly requested in the feature specification or if user requests TDD approach.' When enabled the ordering is hard: 'Within each story: Tests (if requested) -> Models -> Services -> Endpoints -> Integration'; 'If tests requested: Each interface contract -> contract test task [P] before implementation in that story''s phase'; tasks-template.md: 'Tests (if included) MUST be written and FAIL before implementation' and 'Verify tests fail before implementing'. templates/commands/implement.md: '**Follow TDD approach**: Execute test tasks before their corresponding implementation tasks'; '**Phase-by-phase execution**: Complete each phase before moving to the next'; '**Validation checkpoints**: Verify each phase completion before proceeding'. Phase structure: Phase 1 Setup -> Phase 2 Foundational (blocking prerequisites) -> Phase 3+ one phase per user story in priority order -> Final Polish.
SRC: https://github.com/github/spec-kit/blob/main/templates/commands/tasks.md

### spec-kit's [P] marker puts ALL of a story's tests before ANY of its implementation — the exact pattern Pocock's /tdd forbids
tasks-template.md: '**[P]**: Can run in parallel (different files, no dependencies)'; per-story block '### Tests for User Story 1 (OPTIONAL - only if tests requested) ⚠️ > **NOTE: Write these tests FIRST, ensure they FAIL before implementation**' followed by 'T010 [P] [US1] Contract test...', 'T011 [P] [US1] Integration test...', then '### Implementation for User Story 1' with 'T012 [P] [US1] Create [Entity1] model...'. Parallel guidance: 'All tests for a user story marked [P] can run in parallel' with example '# Launch all tests for User Story 1 together (if tests requested)'. This is horizontal slicing scoped to a story. Pocock's /tdd calls the same shape an anti-pattern: 'Bulk tests verify imagined behavior... you commit to test structure before understanding the implementation.' Two shipped kits, directly opposed — worth resolving deliberately rather than inheriting. Note the mitigation spec-kit does have: '[Story] label REQUIRED for user story phase tasks only' (Setup/Foundational/Polish get none) plus per-story '**Independent Test**: [How to verify this story works on its own]' and '**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently'.
SRC: https://github.com/github/spec-kit/blob/main/templates/tasks-template.md

### Anthropic's guidance is oracle-first, not test-first: 'write a failing test' appears only on the bug row; UI gets a screenshot oracle
code.claude.com/docs/en/best-practices, '## Give Claude a way to verify its work': 'Give Claude a check it can run: tests, a build, a screenshot to compare. It''s the difference between a session you watch and one you walk away from.' 'The check is anything that returns a signal Claude can read in the conversation: a test suite, a build exit code, a linter, a script that diffs output against a fixture, or a browser screenshot compared against a design.' Four escalating gate strengths: in one prompt; a /goal condition ('A separate evaluator re-checks it after every turn'); a Stop hook ('runs your check as a script and blocks the turn from ending until it passes. Claude Code overrides the hook and ends the turn after 8 consecutive blocks'); a verification subagent ('a fresh model try to refute the result, so the agent doing the work isn''t the one grading it'). In the specificity table, the bug row is '...write a failing test that reproduces the issue, then fix it' while the UI row is '[paste screenshot] implement this design. take a screenshot of the result and compare it to the original. list differences and fix them'. Failure pattern: '**The trust-then-verify gap.** ... **Fix**: Always provide verification (tests, scripts, screenshots). If you can''t verify it, don''t ship it.' Notably the current common-workflows page has NO TDD recipe; its 'Work with tests' recipe is tests-after ('find functions ... not covered by tests' -> 'add tests' -> 'run the new tests and fix any failures').
SRC: https://code.claude.com/docs/en/best-practices

### Anthropic's one-sentence routing test for planning depth: 'If you could describe the diff in one sentence, skip the plan'
code.claude.com/docs/en/best-practices, callout under 'Explore first, then plan, then code': 'Plan mode is useful, but also adds overhead. For tasks where the scope is clear and the fix is small (like fixing a typo, adding a log line, or renaming a variable) ask Claude to do it directly. Planning is most useful when you''re uncertain about the approach, when the change modifies multiple files, or when you''re unfamiliar with the code being modified. If you could describe the diff in one sentence, skip the plan.' Three named inputs: approach uncertainty, multi-file span, familiarity with the code. Reviewer caution worth carrying into any rubric: 'A reviewer prompted to find gaps will usually report some, even when the work is sound, because that is what it was asked to do. Chasing every finding leads to over-engineering... Tell the reviewer to flag only gaps that affect correctness or the stated requirements, and treat the rest as optional.'
SRC: https://code.claude.com/docs/en/best-practices

### Anthropic's verification-loop blog draws the line at what Claude can already infer
'Building verification loops in Claude Code with skills', Delba de Oliveira, Claude Code team, 2026-07-22. Claude already observes 'type checkers, linters, tests, and runtime errors'; the built-in /verify skill 'builds, runs, and observes the changes in your application'. The routing line: 'whatever Claude can''t infer becomes the steps you take to manually check a feature.' Example of a project-specific deterministic rule worth encoding: 'Reject any migration that drops a column without a backfill step' — 'a deterministic rule no generic linter will catch but a project-specific one will.' And: 'The check doesn''t have to be qualitative to belong here... Anything you keep having to enforce by hand as a manual check qualifies for capture as a loop.'
SRC: https://claude.com/blog/building-verification-loops-in-claude-code-with-skills

### Now in Android proves you CANNOT write a failing screenshot test first: the golden is recorded from the implementation after a human eyeballs it
nowinandroid README, '## Screenshot tests': 'recordRoborazziDemoDebug record new "known correct" screenshots. **Use this command when you have made changes to the UI and manually verified that they are rendered correctly.** Screenshots will be stored in modulename/src/test/screenshots.' 'verifyRoborazziDemoDebug run all screenshot tests, verifying the screenshots against the known correct screenshots.' 'compareRoborazziDemoDebug create comparison images between failed tests and the known correct images.' Roborazzi's own README confirms verify is a regression oracle: 'Validate changes made to an image. If there is any difference between the current image and the saved one, the test will fail.' NiA also warns: 'testDemoDebug run all local tests against the demoDebug variant. Screenshot tests will fail... To avoid this, run recordRoborazziDemoDebug prior to running unit tests.' and 'The known correct screenshots stored in this repository are recorded on CI using Linux. Other platforms may (and probably will) generate slightly different images, making the screenshot tests fail.' Consequence: a pixel golden is a REGRESSION oracle, never a SPECIFICATION oracle. Behavior assertions via createComposeRule + onNodeWithTag under Robolectric CAN be red first; pixels cannot.
SRC: https://github.com/android/nowinandroid/blob/main/README.md

### Now in Android uses zero mocking libraries and hand-written Test* repositories, and its ViewModel tests do NOT use Turbine
nowinandroid README '# Testing': 'In tests, Now in Android notably does _not_ use any mocking libraries. Instead, the production implementations can be replaced with test doubles using Hilt''s testing APIs (or via manual constructor injection for ViewModel tests). These test doubles implement the same interface as the production implementations and generally provide a simplified (but still realistic) implementation with additional testing hooks. This results in less brittle tests that may exercise more production code, instead of just verifying specific calls against mocks.' Concrete fakes live in core/testing/src/main/kotlin/.../core/testing/repository/: TestNewsRepository, TestTopicsRepository, TestUserDataRepository, TestRecentSearchRepository, TestSearchContentsRepository, plus util/MainDispatcherRule.kt, TestNetworkMonitor, TestSyncManager, TestTimeZoneMonitor and di/TestDispatcherModule. ForYouViewModelTest imports runTest, UnconfinedTestDispatcher, advanceUntilIdle, MainDispatcherRule — and no Turbine. Pattern: 'backgroundScope.launch(UnconfinedTestDispatcher()) { viewModel.onboardingUiState.collect() }' then assert 'viewModel.feedState.value'. Robolectric config: app/src/testDemo/resources/robolectric.properties pins 'sdk = 35'.
SRC: https://github.com/android/nowinandroid/blob/main/core/testing/README.md

### Turbine's 3-second timeout is WALL CLOCK and ignores runTest's virtual clock — a real flake source on loaded CI
cashapp/turbine README '### Timeouts': 'Turbine applies a timeout whenever it waits for an event. This is a wall clock time timeout that ignores runTest''s virtual clock time. The default timeout length is three seconds.' CHANGELOG: 'The default wall-clock timeout used to wait for an event has been increased from 1s to 3s.' (raised in 0.12.2 after flake reports). Overrides available: per-block 'flowOf("one","two").test(timeout = 10.milliseconds) { }', per-Turbine 'Turbine<String>(timeout = 10.milliseconds)', and scope-wide 'withTurbineTimeout(10.milliseconds) { }'. 'These timeout overrides only apply to the Turbine on which they were applied.' Implication for TDD: a *correct* ViewModel test can go red for wall-clock reasons on a contended machine, which poisons the red-green signal. NiA's backgroundScope-collect + .value assertion pattern avoids this entirely.
SRC: https://github.com/cashapp/turbine

### Koin module verify() is a JVM unit-test gate, not a red-green loop, and is being superseded by compile-time KSP validation
insert-koin.io/docs/reference/koin-test/verify/: verify() 'will verify all constructor classes and crosscheck with the Koin configuration to know if there is a component declared for this dependency'. JVM-only, Koin 3.3+. Basic form: '@Test fun checkKoinModule() { niaAppModule.verify() }'. Whitelist unresolvable types: 'niaAppModule.verify(extraTypes = listOf(MyType::class))'. Runtime-injected params (Koin 4.0+): 'module.verify(injections = injectedParameters(definition<Simple.ComponentB>(Simple.ComponentA::class)))'. Koin's own docs note the Koin Compiler Plugin now provides compile-time validation, making verify() largely obsolete for new annotation-style projects — so for an annotation-based Koin repo, kspDebugKotlin already carries most of this signal and verify() remains useful mainly for DSL-declared modules.
SRC: https://insert-koin.io/docs/reference/koin-test/verify/

### Robolectric can run Compose UI tests on the JVM but explicitly does not support WebView or system UI (edge-to-edge, PiP)
developer.android.com/training/testing/local-tests/robolectric: Robolectric 'lets you run tests in a simulated Android environment inside a JVM, without the overhead and flakiness of an emulator', supports API 21+. Enablement: 'android { testOptions { unitTests { isIncludeAndroidResources = true } } }' plus 'testImplementation("org.robolectric:robolectric:4.13")'. 'Robolectric can run UI tests such as Espresso or Compose tests' — you convert an instrumented test by moving it to the test source set. Stated limitations: 'It doesn''t support all the features and APIs', 'It doesn''t have a screen like an emulator does', 'Some APIs are only partially supported', 'It doesn''t support features like WebView, system UI (edge-to-edge, picture-in-picture)'. The edge-to-edge exclusion matters directly for any targetSdk 35/36 inset work — those changes have NO fast JVM oracle and must fall back to a device screenshot.
SRC: https://developer.android.com/training/testing/local-tests/robolectric

## EXAMPLES
### BMAD v6 routing decision — the entire scale-routing logic, verbatim (note: no numeric thresholds, one axis, default-to-heavy)
FILE: src/bmm-skills/ship/bmad-build/step-01-clarify-and-route.md (step 5)
```
5. Route — choose exactly one:

   **a) One-shot** — zero blast radius: no plausible path by which this change causes unintended consequences elsewhere. Clear intent, no architectural decisions.

   **EARLY EXIT** → `[[bmad-snapshot:step-oneshot.md]]`

   **b) Plan-code-review** — everything else. When uncertain whether blast radius is truly zero, choose this path.
```
SRC: https://github.com/bmad-code-org/BMAD-METHOD/blob/main/src/bmm-skills/ship/bmad-build/step-01-clarify-and-route.md

### BMAD v6 multi-goal split gate — an observable, non-vibes definition of 'is this one change?'
FILE: src/bmm-skills/ship/bmad-build/workflow.md (SCOPE STANDARD) + step-01 §4
```
- **Single goal**: One cohesive feature, even if it spans multiple layers/files. Multi-goal means >=2 **top-level independent shippable deliverables** — each could be reviewed, tested, and merged as a separate PR without breaking the others. Never count surface verbs, "and" conjunctions, or noun phrases. Never split cross-layer implementation details inside one user goal.
  - Split: "add dark mode toggle AND refactor auth to JWT AND build admin dashboard"
  - Don't split: "add validation and display errors" / "support drag-and-drop AND paste AND retry"
- **900–1600 tokens**: Optimal range for LLM consumption. Below 900 risks ambiguity; above 1600 risks context-rot in implementation agents.
- **Neither limit is a gate.** Both are proposals with user override.
```
SRC: https://github.com/bmad-code-org/BMAD-METHOD/blob/main/src/bmm-skills/ship/bmad-build/workflow.md

### BMAD v6 spec template — the frozen behavior contract (written before code) plus the oracle-or-manual-check section
FILE: src/bmm-skills/ship/bmad-build/spec-template.md
```
<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## I/O & Edge-Case Matrix

<!-- If no meaningful I/O scenarios exist, DELETE THIS ENTIRE SECTION. Do not write "N/A" or "None". -->

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | INPUT | OUTCOME | N/A |
| ERROR_CASE | INPUT | OUTCOME | ERROR_HANDLING |

</frozen-after-approval>

## Verification

<!-- If no build, test, or lint commands apply, DELETE THIS ENTIRE SECTION. -->
<!-- How the agent confirms its own work. Prefer CLI commands. When no CLI check applies, state what to inspect manually. -->

**Commands:**
- `COMMAND` -- expected: SUCCESS_CRITERIA

**Manual checks (if no CLI):**
- WHAT_TO_INSPECT_AND_EXPECTED_STATE
```
SRC: https://github.com/bmad-code-org/BMAD-METHOD/blob/main/src/bmm-skills/ship/bmad-build/spec-template.md

### BMAD v6 Matrix Test Audit — tests written after code, but audited against the frozen pre-approved matrix, with a no-moving-the-goalposts rule
FILE: src/bmm-skills/ship/bmad-build/step-03-implement.md
```
### Matrix Test Audit

If `{spec_file}`'s `<frozen-after-approval>` block contains an I/O & Edge-Case Matrix, verify every matrix row is covered by at least one test that verifies its expected behavior, and that each covering test ran and passed in the verification output. A covering test that exists but did not run — unregistered, filtered out, skipped, or disabled — counts as missing. If a test disagrees with the matrix, never edit the expectation to match the code: fix the code, or if the matrix row itself is ambiguous, HALT and ask the human.
```
SRC: https://github.com/bmad-code-org/BMAD-METHOD/blob/main/src/bmm-skills/ship/bmad-build/step-03-implement.md

### cc-sdd Feature Flag Protocol — the TDD/no-TDD router plus a mechanised tautological-test detector
FILE: tools/cc-sdd/templates/agents/claude-code-skills/skills/kiro-impl/SKILL.md
```
## Feature Flag Protocol

For tasks that add or change behavior, enforce RED → GREEN with a feature flag:

1. **Add flag** (OFF by default): Introduce a toggle appropriate to the codebase (env var, config constant, boolean, conditional -- agent chooses the mechanism)
2. **RED -- flag OFF**: Write tests for the new behavior. Run tests → must FAIL. If tests pass with flag OFF, the tests are not testing the right thing. Rewrite.
3. **GREEN -- flag ON + implement**: Enable the flag, write implementation. Run tests → must PASS.
4. **Remove flag**: Make the code unconditional. Run tests → must still PASS.

**Skip this protocol for**: refactoring, configuration, documentation, or tasks with no behavioral change.
```
SRC: https://github.com/gotalab/cc-sdd/blob/main/tools/cc-sdd/templates/agents/claude-code-skills/skills/kiro-impl/SKILL.md

### cc-sdd proof-of-red — a required, machine-parsed structured field so 'I wrote the test first' is verifiable rather than claimed
FILE: tools/cc-sdd/templates/agents/claude-code-skills/skills/kiro-impl/templates/implementer-prompt.md
```
- RED_PHASE_OUTPUT: <test command and failing output from before implementation -- proves tests were written first>
- TESTS_RUN: <test commands and final passing results>
- EVIDENCE: <concrete code paths, functions, and tests that prove the behavior>

# (and in the workflow body:)
- For non-behavioral tasks, use a standard RED → GREEN → REFACTOR cycle. **Run tests after writing them (before implementation) and capture the failing output.**
```
SRC: https://github.com/gotalab/cc-sdd/blob/main/tools/cc-sdd/templates/agents/claude-code-skills/skills/kiro-impl/templates/implementer-prompt.md

### cc-sdd oracle discovery — copyable Preflight recipe for 'does a fast deterministic oracle already exist here?'
FILE: tools/cc-sdd/templates/agents/claude-code-skills/skills/kiro-impl/SKILL.md (Step 1 Preflight)
```
**Discover validation commands**:
- Inspect repository-local sources of truth in this order: project scripts/manifests (`package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, app manifests), task runners (`Makefile`, `justfile`), CI/workflow files, existing e2e/integration configs, then `README*`
- Derive a canonical validation set for this repo: `TEST_COMMANDS`, `BUILD_COMMANDS`, and `SMOKE_COMMANDS`
- Prefer commands already used by repo automation over ad hoc shell pipelines
- For `SMOKE_COMMANDS`, choose the lightest trustworthy runtime-liveness check for the app shape (for example: root URL load, Electron launch, CLI `--help`, service health endpoint, mobile simulator/e2e harness if one already exists)
- Keep the full command set in the parent context, and pass only the task-relevant subset to implementer and reviewer subagents
```
SRC: https://github.com/gotalab/cc-sdd/blob/main/tools/cc-sdd/templates/agents/claude-code-skills/skills/kiro-impl/SKILL.md

### Matt Pocock /implement — the whole skill, 11 lines. Note the graded oracle cadence and that seams are the routing input.
FILE: skills/engineering/implement/SKILL.md
```
---
name: implement
description: "Implement a piece of work based on a spec or set of tickets."
disable-model-invocation: true
---

Implement the work described by the user in the spec or tickets.

Use /tdd where possible, at pre-agreed seams.

Run typechecking regularly, single test files regularly, and the full test suite once at the end.

Once done, use /code-review to review the work.

Commit your work to the current branch.
```
SRC: https://github.com/mattpocock/skills/blob/main/skills/engineering/implement/SKILL.md

### Matt Pocock /tdd — the pre-agreed-seam rule, the tautological anti-pattern, and refactoring-is-not-in-the-loop, verbatim
FILE: skills/engineering/tdd/SKILL.md
```
**Test only at pre-agreed seams.** Before writing any test, write down the seams under test and confirm them with the user. No test is written at an unconfirmed seam. You can't test everything — agreeing the seams up front is how testing effort lands on the critical paths and complex logic instead of every edge case.

Ask: "What's the public interface, and which seams should we test?"

## Anti-patterns

- **Tautological** — the assertion recomputes the expected value the way the code does (`expect(add(a, b)).toBe(a + b)`, a snapshot derived by hand the same way, a constant asserted equal to itself), so it passes by construction and can never disagree with the code. Expected values must come from an independent source of truth — a known-good literal, a worked example, the spec.
- **Horizontal slicing** — writing all tests first, then all implementation. [...] Work in **vertical slices** instead — one test → one implementation → repeat, each test a **tracer bullet**.

## Rules of the loop

- **Red before green.** Write the failing test first, then only enough code to pass it.
- **One slice at a time.** One seam, one test, one minimal implementation per cycle.
- **Refactoring is not part of the loop.** It belongs to the review stage (see the `code-review` skill), not the red → green implementation cycle.
```
SRC: https://github.com/mattpocock/skills/blob/main/skills/engineering/tdd/SKILL.md

### GitHub spec-kit — the opt-in test gate and the per-story test-first ordering it enforces once enabled
FILE: templates/commands/tasks.md and templates/tasks-template.md
```
# templates/commands/tasks.md
**Tests are OPTIONAL**: Only generate test tasks if explicitly requested in the feature specification or if user requests TDD approach.
...
- **Phase 3+**: User Stories in priority order (P1, P2, P3...)
  - Within each story: Tests (if requested) → Models → Services → Endpoints → Integration

# templates/tasks-template.md
### Tests for User Story 1 (OPTIONAL - only if tests requested) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T010 [P] [US1] Contract test for [endpoint] in tests/contract/test_[name].py
- [ ] T011 [P] [US1] Integration test for [user journey] in tests/integration/test_[name].py

### Implementation for User Story 1
- [ ] T012 [P] [US1] Create [Entity1] model in src/models/[entity1].py
...
**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

# Ordering rules
- Tests (if included) MUST be written and FAIL before implementation
- All tests for a user story marked [P] can run in parallel
```
SRC: https://github.com/github/spec-kit/blob/main/templates/tasks-template.md

### TDAD skill — the arm that actually cut regressions 70%. Copy this shape for a fast-path regression guard; note step 1 is 'make the change'.
FILE: tdad/SKILL.md (installed as .claude/skills/tdad/SKILL.md; artifact at .tdad/test_map.txt)
```
## Setup (one-time per repo)
If `.tdad/test_map.txt` does not exist yet:
```bash
pip install tdad
tdad index .
```

## Bug Fix / Feature Workflow
### 1. Make the change
### 2. Find impacted tests
```bash
grep 'path/to/changed_file.py' .tdad/test_map.txt
```
Output format: `source_file.py: test_a.py test_b.py test_c.py`
### 3. Run impacted tests
```bash
python -m pytest <test_files> -x -q 2>&1 | head -50
```
### 4. If test_map.txt has no entry — fall back to naming convention

## Rules
- **Never submit a patch without running impacted tests first.**
- Run the minimum set of tests needed (not the full suite) for speed.
```
SRC: https://github.com/pepealonso95/TDAD/blob/main/tdad/SKILL.md

### TDAD impact scoring — the actual weights, if you want to build a Kotlin/Gradle equivalent of test_map.txt
FILE: tdad-ts README (TypeScript port; same scoring as arXiv 2603.17973)
```
score = (1 - c_w) * w_strategy + c_w * confidence

with c_w = 0.3 and per-strategy weights:

| Strategy   | Weight | Confidence |
|------------|--------|------------|
| Direct     | 0.95   | 1.00       |
| Route      | 0.90   | 0.70       |
| Transitive | 0.70   | 0.56       |
| Coverage   | 0.80   | 0.50       |
| Imports    | 0.50   | 0.45       |

Tiers: high (>= 0.8), medium (0.5-0.8), low (< 0.5). Default cap 50 tests per source file.

Test linker heuristics: 1. naming convention  2. prefix matching (progressive truncation of test-file stem)  3. directory proximity
```
SRC: https://github.com/fmguerreiro/tdad-ts

### Cheap Kotlin/Gradle equivalent of TDAD's test_map lookup — 'which tests cover the file I'm about to touch?' (T0, <2s)
FILE: run from repo root before deciding TDD vs fast mode
```
# 1. Does a test class exist for this type at all?
fd -e kt '^FooUseCaseTest\.kt$'

# 2. Which test files reference this symbol (import or usage)?
rg -l --glob '**/src/test/**/*.kt' --glob '**/src/androidTest/**/*.kt' '\bFooUseCase\b'

# 3. Blast radius: how many call sites would a signature change break?
rg -c --glob '**/src/main/**/*.kt' '\bFooUseCase\b' | wc -l

# 4. How many Gradle modules does the current diff touch?
git diff --name-only | sed -E 's#/src/.*##' | sort -u | wc -l

# 5. Churn on the touched file (proxy for reversibility risk)
git log --oneline -n 50 -- path/to/Foo.kt | wc -l
```
SRC: https://github.com/pepealonso95/TDAD/blob/main/tdad/SKILL.md

### Now in Android's canonical test commands and screenshot workflow — the reference implementation's own answer, including the record-after-eyeball step
FILE: nowinandroid README '# Testing' / '## Screenshot tests'
```
# All local (JVM) tests for the demoDebug variant
./gradlew testDemoDebug

# NOTE: screenshot tests will fail unless goldens are recorded first
./gradlew recordRoborazziDemoDebug      # mint goldens AFTER manual visual verification
./gradlew verifyRoborazziDemoDebug      # regression oracle: fails on ANY pixel diff
./gradlew compareRoborazziDemoDebug     # writes [original]_compare.png diffs
./gradlew verifyAndRecordRoborazziDemoDebug  # verify, then re-record on diff

# Instrumented tests (device/emulator required)
./gradlew connectedDemoDebugAndroidTest

# Do NOT run these — they hit every variant and will fail:
#   ./gradlew test
#   ./gradlew connectedAndroidTest
```
SRC: https://github.com/android/nowinandroid/blob/main/README.md

### NiA's flake-free ViewModel assertion pattern (no Turbine, no wall-clock timeout) — this is what a red-green ViewModel cycle should look like
FILE: feature/<name>/impl/src/test/kotlin/.../<Name>ViewModelTest.kt
```
@get:Rule
val mainDispatcherRule = MainDispatcherRule()

@Test
fun stateIsInitiallyLoading() = runTest {
    assertEquals(NewsFeedUiState.Loading, viewModel.feedState.value)
}

@Test
fun stateIsLoadingWhenFollowedTopicsAreLoading() = runTest {
    backgroundScope.launch(UnconfinedTestDispatcher()) { viewModel.onboardingUiState.collect() }
    // ... drive the hand-written Test*Repository, then:
    advanceUntilIdle()
    assertEquals(/* expected */, viewModel.feedState.value)
}

// Fakes come from :core:testing — TestNewsRepository / TestTopicsRepository /
// TestUserDataRepository, hand-written, implementing the production interface.
// NiA uses NO mocking libraries anywhere.
```
SRC: https://github.com/android/nowinandroid/blob/main/core/testing/README.md

### Turbine wall-clock timeout overrides — required if you use Turbine at all in a red-green loop on a contended machine
FILE: any *ViewModelTest.kt using app.cash.turbine
```
// Default is 3s WALL CLOCK — it ignores runTest's virtual clock entirely.

// per test block
flowOf("one", "two").test(timeout = 10.milliseconds) { /* ... */ }

// per standalone Turbine
val standalone = Turbine<String>(timeout = 10.milliseconds)

// whole block
withTurbineTimeout(10.milliseconds) {
  // all Turbine calls inside use this timeout
}
```
SRC: https://github.com/cashapp/turbine

### Koin DI-graph gate as a JVM unit test (T1 oracle, ~seconds) — a gate, not a red-green cycle
FILE: app/src/test/kotlin/.../di/KoinModuleCheckTest.kt
```
class AppModuleCheck {
    @Test
    fun checkKoinModule() {
        appModule.verify()
    }
}

// whitelist types Koin cannot resolve statically
appModule.verify(extraTypes = listOf(SavedStateHandle::class))

// declare runtime-injected params (Koin 4.0+)
appModule.verify(
    injections = injectedParameters(
        definition<DetailViewModel>(String::class)
    )
)

// NOTE: for annotation-style Koin (@Single/@Factory + KSP), the Koin Compiler Plugin
// already validates at compile time, so `./gradlew :app:kspDevelopDebugKotlin` is the
// cheaper primary oracle; verify() covers DSL-declared modules.
```
SRC: https://insert-koin.io/docs/reference/koin-test/verify/

### Robolectric enablement for Compose behavior tests on the JVM (the only Compose thing that CAN be red-first)
FILE: module build.gradle.kts + src/test/resources/robolectric.properties
```
// build.gradle.kts
android {
  testOptions {
    unitTests {
      isIncludeAndroidResources = true
    }
  }
}
dependencies {
  testImplementation("org.robolectric:robolectric:4.13")
}

// src/testDemo/resources/robolectric.properties  (NiA pins this)
sdk = 35

// Then a Compose SEMANTICS test can be written red-first:
@RunWith(AndroidJUnit4::class)
class FooScreenTest {
  @get:Rule val composeRule = createComposeRule()

  @Test fun showsEmptyState_whenNoItems() {
    composeRule.setContent { FooScreen(state = FooUiState.Empty) }
    composeRule.onNodeWithTag("foo_empty").assertIsDisplayed()   // can fail before the code exists
  }
}
// A PIXEL golden cannot: Roborazzi's golden is minted by recordRoborazzi* from the
// implementation after a human eyeballs it. Robolectric also does NOT support
// WebView or system UI (edge-to-edge, picture-in-picture).
```
SRC: https://developer.android.com/training/testing/local-tests/robolectric

## GOTCHAS
- The headline TDD-Bench number is worse than it looks. 23.6% fail-to-pass for GPT-4o means ~76% of generated tests are not valid oracles: ~10% pass on the UNFIXED code (pure tautology, they'd never have gone red), and ~73% of the ones that do go red stay red after the correct fix (broken test, not encoded requirement). An agent that writes a failing test and then codes until it passes is, three-quarters of the time, coding against garbage.
- Coverage does not certify a test. TDD-Bench: 35% of non-fail-to-pass GPT-4o tests had PERFECT coverage of the changed lines. A test can execute every changed line and still assert nothing meaningful. Do not use coverage as the gate; use it only as a cheap filter to DISCARD candidates (fail-to-pass tests almost always exceed 0.90, so <0.6 is a strong negative signal).
- Iterating harder against a self-generated oracle makes correctness WORSE, not better. Test-overfitting (arXiv 2511.16858): Claude-3.7-Sonnet's wrong-but-green rate rose from 21.8% to 25.5% and GPT-4o's from 33.0% to 35.9% once code refinement was enabled. More red-green cycles against a test the agent wrote is negative-value work.
- TDAD's 9.94% regression result is real but statistically thin. n=100 (Phase 1) and n=25 (Phase 2), NO formal significance tests, a single 4-bit-quantised 30B local model, Python only. The direction is corroborated by the Fowler memo and by 2602.07900's null intervention results, but do not quote 9.94% as if it were a powered RCT. Also note the TDD arm's resolution rate was IDENTICAL to vanilla (31%) — TDD did not hurt task success, it hurt collateral damage.
- The Fowler 'no discernible difference' memo is a small blind LLM-as-judge study (5 batches, 2 TDD + 2 non-TDD each, Opus judging Sonnet). Its token multiples (8.5x / 2.96x / 4.89x) are the durable part; the quality ranking is not a statistically meaningful result and the author says the token figure 'likely overstates TDD's true dollar cost' due to cache hits.
- Test-first is NOT uniformly worse — the direction flips when the alternative is showing the model buggy code. 2607.05139 (25% vs 14% fault detection) and 2607.22883 (8x misguided tests from buggy input) both favour spec-derived tests. Reconciliation: test-first wins on ORACLE INDEPENDENCE, loses on PROCESS OVERHEAD. Route on which of those dominates for the change at hand.
- Fail-to-pass is a biased metric for judging test-first vs test-after, because it is scored against the same gold patch the 'test-after' arm was shown. TDD-Bench RQ3 showing write-first-test-later at 24.3% vs 23.6% is therefore weak evidence for test-after; it mostly shows the metric rewards mirroring the diff.
- Public-benchmark numbers do not transfer to a private repo. e-Otter++ hits 43.6-46.4% F2P on open-source Java but the SAME pipeline got 4.0% on a proprietary 150-instance dataset — recovering to only 20.0% after injecting generated class/function-name hints. Cause: 'the specifications or issue descriptions in proprietary projects are often not well written.' Expect your Jira tickets to behave like the 4% case, not the 44% case, unless they name identifiers.
- Feature work is materially harder to reproduce-test than bug fixes, and the gap widens on private code: bug 44.1% (OSS) / 45.8% (proprietary) vs feature 30.1% (OSS) / 15.1% (proprietary). 'Write a failing test first' is cheap and high-yield for bugs and expensive and low-yield for new features — the opposite of how most kits apply it uniformly.
- Agents cannot see stale tests. TEBench: Test-Stale identification F1 ~35.8% vs ~59.9% for Test-Breaking, because the reactive execute-fail-fix loop has no failure signal for a test that still passes but no longer validates the right thing. Any process that relies on 'run the tests, fix what's red' is structurally blind to the most dangerous class of test rot.
- Agent-written tests are mostly print statements, not assertions. 2602.07900 measured 25.00 prints vs 5.16 assertions per resolved task (Claude Opus 4.5) and 34.06 vs 7.37 (MiniMax M2), with only 2.98-7.86% of assertions being relational/bound checks. If you count 'the agent wrote tests' as a quality signal, you are mostly counting debug output.
- Prompting an agent to write more tests costs tokens and buys nothing measurable. GPT-5.2 'encourage tests': 64.4% of tasks flipped to having tests, net success change 0 (p=1.000), +5.5% API calls, +19.8% output tokens. Conversely discouraging tests on Kimi K2-T saved 35.4% API calls and 49.0% input tokens for a 2.6pp resolution drop (p=0.228).
- Agents over-mock relative to humans: 36% vs 26% of commits add mocks (1.2M commits, 2,168 repos, MSR 2026). Mock-heavy tests are Pocock's 'implementation-coupled' anti-pattern and Now in Android deliberately uses zero mocking libraries. If you route to TDD, also mandate hand-written fakes at the seam, or you buy brittleness instead of safety.
- spec-kit and Pocock's /tdd give directly contradictory guidance on test placement. spec-kit emits all of a story's tests as [P] tasks before any implementation task; Pocock names exactly that shape ('writing all tests first, then all implementation') as the 'horizontal slicing' anti-pattern that produces tests of imagined behavior. Pick one deliberately; do not inherit both.
- Compose pixel-golden tests can never be red-first. Roborazzi's baseline is minted by recordRoborazzi* from the implementation, and Now in Android's own README says to run it 'when you have made changes to the UI and manually verified that they are rendered correctly.' A screenshot test is a regression oracle, never a specification oracle. Anything that claims 'TDD for UI' with screenshots is either doing semantics tests (fine) or lying (not fine).
- Roborazzi goldens are OS-dependent. NiA: 'The known correct screenshots stored in this repository are recorded on CI using Linux. Other platforms may (and probably will) generate slightly different images, making the screenshot tests fail.' A macOS dev box will produce false reds against Linux-CI goldens, which destroys the red-green signal.
- Turbine's timeout is wall-clock, not virtual, and 3s by default. A correct ViewModel test can go red purely because the Gradle daemon was busy, which corrupts the meaning of 'red' in a red-green loop. NiA sidesteps this entirely — backgroundScope.launch(UnconfinedTestDispatcher()) { flow.collect() } + advanceUntilIdle() + assert .value, no Turbine anywhere.
- Robolectric does not support WebView or system UI (edge-to-edge, picture-in-picture). For targetSdk 35/36 inset and edge-to-edge work there is NO fast JVM oracle at all; the cheapest honest check is install + device screenshot, which is a T3/T4 loop. Do not attempt TDD there.
- Gradle and build-logic changes have no inner-loop oracle. GradleRunner/TestKit works but each run is a full nested build (tens of seconds each). Now in Android — the reference implementation — ships ~18 convention plugins in build-logic/convention/src/main/kotlin/ with NO TestKit tests at all. Its de facto answer is compile + assemble.
- Koin verify() is being superseded. For annotation-style Koin (@Single/@Factory + KSP), the Koin Compiler Plugin validates the graph at compile time, so kspDevelopDebugKotlin is the cheaper and earlier oracle; verify() only earns its keep for DSL-declared modules and runtime-injected params. Adding a verify() test to a fully-annotated graph is near-duplicate coverage.
- Do not conflate 'the agent produced tests' with 'the change is verified'. TDFlow's own conclusion is that the frontier is 'the accurate generation of valid reproduction tests' — the loop is worth ~everything provided the oracle is valid, and self-generated tests cost 4x ($4.12 vs $1.01/issue) for 26pp less. Budget accordingly: a human-supplied acceptance criterion is the single highest-leverage input in the whole system.

## OPEN
- No study I found measures TDD-vs-fast-path outcomes on Kotlin/Android specifically. Every quantitative result above is Python (TDD-Bench, TDAD, 2607.05139, 2602.07900), Java (TDD-Bench-Java, TEBench, 2607.22883), or JS/TS (WebApp1K, 2602.00409). Whether the ~5-40x latency spread between Android layers changes the calculus is untested — my Part D mapping is derived from tool documentation and Now in Android's shipped setup, not from a measured agent experiment.
- TDAD's 6.08% -> 9.94% regression result has never been replicated on a frontier model. Both TDAD phases used 4-bit-quantised local models (Qwen3-Coder 30B, Qwen3.5-35B-A3B). The paper's own explanation ('verbose prompts hurt small models', context displacement) predicts the effect should shrink or vanish on a 200k-context frontier model — but nobody has run it. This is the single most load-bearing number in the whole synthesis and it is the least robust.
- I could not verify latency numbers for Robolectric vs instrumented tests from a primary source. Google's own docs claim 'increased speed and reliability' with no metrics. A secondary source (androiddocs.com) claims 90ms/test Robolectric vs 850ms Espresso with 0.2% vs 1.4% flake over a 200-test suite across 30 CI runs, but I could not verify its methodology and would not build a rubric threshold on it. Measure this on the actual repo before setting the T1/T2/T3 boundaries.
- What happens when verifyRoborazzi runs and NO golden exists yet? The Roborazzi README documents 'if there is any difference between the current image and the saved one, the test will fail' but does not state the missing-baseline behavior. If a missing golden fails rather than silently passes, a very weak form of screenshot-test-first becomes possible (assert 'a golden must exist for this composable'), which would be worth confirming empirically.
- The bmad-build workflow.md placeholders ({workflow.implementation_handoff}, {workflow.oneshot_review_layers}, {workflow.persistent_facts}) are resolved at render time by _bmad/scripts/render_skill.py from layered TOML config. I read the templates, not a rendered instance, so the exact default implementation handoff text and the default oneshot review layer set are unverified.
- The TDFlow BTR definition I extracted reads slightly self-contradictory ('a test is deemed unsuccessful if it fails before the gold patch is applied or passes after'), which inverts the usual fail-to-pass convention. The 93.3%-at-BTR-0 conclusion is unaffected, but the exact metric wording should be checked against the v2 PDF before being quoted.
- No source gives a validated numeric threshold for any routing axis. BMAD deliberately removed its numeric levels; Anthropic's test is qualitative ('describe the diff in one sentence'); Pocock's is human-agreed. The thresholds I suggest in the rubric (1 module / <=3 files / no public-API change -> fast path) are my synthesis, not measured, and should be calibrated against this repo's own PR history before being encoded.
- Nobody has published a measurement of how often agent-written tests are tautological in the Pocock sense (assertion recomputes the expected value the way the code does) as distinct from the fail-to-pass sense. TDD-Bench's ~10% already-passing rate and 2607.22883's 3.84% misguided rate are proxies, but the specific 'expect(add(a,b)).toBe(a+b)' failure mode has no published base rate.

# Instrumenting, evaluating, and pruning an agentic coding workflow kit (Claude Code telemetry, per-run JSON, repo-local golden-task evals, skill/hook regression testing, scaffolding deletion)

## SUMMARY
Five layers; only the first two are genuinely solid today.

(A) Telemetry is a fully documented OTel surface. Claude Code emits exactly 8 metrics (session.count, lines_of_code.count, pull_request.count, commit.count, cost.usage [USD], token.usage [tokens], code_edit_tool.decision, active_time.total [s]), ~15 named log events, and 6 beta span types. Subagent attribution is free: query_source in {main, subagent, auxiliary} and agent.name on the cost/token counters; agent_id/parent_agent_id on spans; skill.name/plugin.name/mcp_server.name on every API request. Per-skill and per-subagent cost is a groupby, not a research project. Third-party names redact to "custom"/"third-party" unless OTEL_LOG_TOOL_DETAILS=1. Real dashboards (ColeMurray, AWS, Grafana, SigNoz) uniformly under-use this: most plot cost/tokens/LOC and ignore active_time.total, code_edit_tool.decision, and every subagent attribute.

(B) Per-run JSON is the kit's self-test. `claude -p --output-format json` returns duration_ms, duration_api_ms, num_turns, total_cost_usd, usage, modelUsage, permission_denials[], session_id, structured_output, errors[], stop_reason, and subtype from a closed set (success, error_max_turns, error_max_budget_usd, error_during_execution, error_max_structured_output_retries). The system/init event carries plugins/plugin_errors, mcp_servers/mcp_server_errors, skills, agents, slash_commands, capabilities — a CI gate can fail on a non-empty error array. parent_tool_use_id attributes messages to a subagent at any nesting depth. maxBudgetUsd does not hard-stop mid-request: it refuses new subagent spawns, kills background subagents, and ends the query with error_max_budget_usd; usage omits the response that crossed the budget while total_cost_usd/modelUsage include it.

(C) Repo-local golden tasks: SWE-bench's 3-stage pipeline (scrape merged PRs → attribute filter: resolves an issue AND touches test files → execution filter: at least one FAIL_TO_PASS) is the reference, and SWE-bench Verified's rubric (93 devs, 3 annotators/sample, 1,699 samples, ensemble-OR filtering) is the quality bar. For Kotlin/Android two real benchmarks already exist: JetBrains kotlin-swe-bench (105 tasks, 8 repos incl. Anki-Android, on Multi-SWE-bench infra) and Firebender Kotlin-bench (100 Kotlin+Android tasks; per-repo JSON configs with jdk_version, android_sdk_packages, install_script, test_command). Neither SWE-bench Multilingual nor Multi-SWE-bench includes Kotlin.

(D) Component evals: Anthropic's own skill-creator now ships a blind A/B comparator, grading.json/benchmark.json schemas, and mean±stddev per configuration. promptfoo covers prompt-level regression with llm-rubric.

(E) Deletion: Anthropic's Managed Agents post (Apr 8 2026) supplies the canonical wording — Sonnet 4.5 "context anxiety" → context resets → on Opus 4.5 "the resets had become dead weight." Agent OS v3 (Jan 20 2026) retired its implementation and orchestration phases on the same logic. Anthropic's skill-creator blog names "identifying when base model capabilities have made skills unnecessary" as an explicit purpose of evals.

Statistical reality: at n=100 (Kotlin-bench) a 7-point spread among the top four models was NOT statistically significant. Miller's power formula needs ~969 paired questions for 3 points; scaling by 1/δ² gives ~350 for 5 points under the same variance assumptions, and >1,500 per arm if unpaired. Anthropic's "20-50 tasks from real failures" is for directional debugging, not significance.

## KEY FACTS
### Claude Code exports exactly 8 OTel metrics with these units
claude_code.session.count (none), claude_code.lines_of_code.count (none), claude_code.pull_request.count (none), claude_code.commit.count (none), claude_code.cost.usage (USD), claude_code.token.usage (tokens), claude_code.code_edit_tool.decision (none), claude_code.active_time.total (s). All are counters.
SRC: https://code.claude.com/docs/en/monitoring-usage.md

### Per-metric attributes are enumerated and low-cardinality by design
session.count: start_type in {fresh, resume, continue, agents_view}. lines_of_code.count: type in {added, removed} + model. cost.usage: model, query_source, speed, effort, agent.name, skill.name, plugin.name, marketplace.name, mcp_server.name, mcp_tool.name. token.usage: same plus type in {input, output, cacheRead, cacheCreation}. code_edit_tool.decision: tool_name in {Edit, Write, NotebookEdit}, decision in {accept, reject}, source in {config, hook, user_permanent, user_temporary, user_abort, user_reject}, language (e.g. TypeScript/Python/Markdown or 'unknown'). active_time.total: type in {user, cli}.
SRC: https://code.claude.com/docs/en/monitoring-usage.md

### Subagent, skill and plugin activity IS separately attributable on metrics and events
query_source is one of "main", "subagent", "auxiliary" on cost.usage and token.usage. agent.name = subagent type that issued the request (built-in and official-marketplace agent names verbatim; other user-defined names collapse to "custom"). skill.name: built-in/bundled/user-defined verbatim, third-party -> "third-party". plugin.name: official verbatim, third-party -> "third-party". mcp_server.name / mcp_tool.name: built-in/official-registry verbatim, user-configured -> "custom". These same attributes appear on claude_code.api_request, api_error and api_refusal events.
SRC: https://code.claude.com/docs/en/monitoring-usage.md

### 15 structured log events, each a log record named claude_code.<name>
user_prompt, assistant_response, tool_result, api_request, api_error, api_refusal, api_request_body, api_response_body, tool_decision, permission_mode_changed, auth, mcp_server_connection, internal_error, plugin_installed, plugin_loaded. internal_error is NOT emitted on Amazon Bedrock, Google Cloud's Agent Platform, or Microsoft Foundry, or when DISABLE_ERROR_REPORTING is set.
SRC: https://code.claude.com/docs/en/monitoring-usage.md

### claude_code.api_request carries the full per-request cost/token breakdown
Attributes: model, cost_usd, cost_usd_micros, duration_ms, input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens, request_id, client_request_id, speed (fast|normal), query_source, effort (low|medium|high|xhigh|max), agent.name, skill.name, plugin.name, marketplace.name, mcp_server.name, mcp_tool.name.
SRC: https://code.claude.com/docs/en/monitoring-usage.md

### claude_code.tool_result is the per-tool-call latency/success record
tool_name, tool_use_id, success (true/false), duration_ms, error_type (e.g. "Error:ENOENT", "ShellError"), decision_type (always "accept"), decision_source (config|hook|user_permanent|user_temporary), tool_input_size_bytes, tool_result_size_bytes, mcp_server_scope; plus error, tool_parameters, tool_input only when OTEL_LOG_TOOL_DETAILS=1.
SRC: https://code.claude.com/docs/en/monitoring-usage.md

### Event correlation IDs let you stitch a prompt to its downstream API calls and tool calls
prompt.id (UUID correlating a user prompt with all subsequent events), message.uuid (persisted in the session transcript), client_request_id (sent as the x-client-request-id header).
SRC: https://code.claude.com/docs/en/monitoring-usage.md

### Standard attributes and their cardinality switches
session.id (OTEL_METRICS_INCLUDE_SESSION_ID, default true), app.version (OTEL_METRICS_INCLUDE_VERSION, default false), app.entrypoint (OTEL_METRICS_INCLUDE_ENTRYPOINT, default false; values cli, sdk-cli, sdk-ts, sdk-py, claude-vscode), organization.id (always if available), user.account_uuid + user.account_id (OTEL_METRICS_INCLUDE_ACCOUNT_UUID, default true), user.id (random anonymous ID persisted in ~/.claude.json, always), user.email (OAuth only, always if available), terminal.type, and OTEL_RESOURCE_ATTRIBUTES custom keys (OTEL_METRICS_INCLUDE_RESOURCE_ATTRIBUTES, default true).
SRC: https://code.claude.com/docs/en/monitoring-usage.md

### Content logging is opt-in via five variables, all off by default
OTEL_LOG_USER_PROMPTS=1 (prompt text on user_prompt events and the interaction span), OTEL_LOG_ASSISTANT_RESPONSES=1 (falls back to OTEL_LOG_USER_PROMPTS if unset), OTEL_LOG_TOOL_DETAILS=1 (tool parameters, file paths, bash commands, MCP/skill/workflow names), OTEL_LOG_TOOL_CONTENT=1 (full tool input/output as span events; requires tracing), OTEL_LOG_RAW_API_BODIES=1 or file:<dir> (full Messages API request/response JSON; includes entire conversation history, extended-thinking redacted). Truncation limit CLAUDE_CODE_OTEL_CONTENT_MAX_LENGTH default 61440 UTF-16 code units (60 KB).
SRC: https://code.claude.com/docs/en/agent-sdk/observability.md

### Export intervals and their defaults
OTEL_METRIC_EXPORT_INTERVAL default 60000 ms; OTEL_LOGS_EXPORT_INTERVAL default 5000 ms; OTEL_TRACES_EXPORT_INTERVAL default 5000 ms. Metrics temporality defaults to delta (OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE); CloudWatch/Grafana Cloud setups override it to cumulative.
SRC: https://code.claude.com/docs/en/monitoring-usage.md

### Tracing is beta and gives you the full delegation tree as one trace
Requires CLAUDE_CODE_ENABLE_TELEMETRY=1 AND CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1 (alias ENABLE_ENHANCED_TELEMETRY_BETA) plus OTEL_TRACES_EXPORTER. Span hierarchy: claude_code.interaction > {claude_code.llm_request, claude_code.hook, claude_code.tool > {claude_code.tool.blocked_on_user, claude_code.tool.execution}}. claude_code.hook additionally requires ENABLE_BETA_TRACING_DETAILED=1 and BETA_TRACING_ENDPOINT. Subagent llm_request/tool spans nest under the parent's claude_code.tool span.
SRC: https://code.claude.com/docs/en/monitoring-usage.md

### Span attributes give subagent identity and time-to-first-token
claude_code.llm_request: model, gen_ai.system, gen_ai.request.model, query_source, agent_id, parent_agent_id, workflow.run_id (wf_ prefix), workflow.name, speed, llm_request.context (interaction|tool|standalone), duration_ms, ttft_ms, input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens, request_id, gen_ai.response.id, client_request_id, attempt, success, status_code, error, response.has_tool_call, stop_reason, gen_ai.response.finish_reasons. claude_code.tool: tool_name, duration_ms, result_tokens, agent_id, parent_agent_id, tool_use_id, gen_ai.tool.call.id, plus file_path/full_command/skill_name/subagent_type gated by OTEL_LOG_TOOL_DETAILS.
SRC: https://code.claude.com/docs/en/monitoring-usage.md

### claude_code.hook span exposes hook cost and blocking behaviour — the only direct hook telemetry
hook_event (PreToolUse etc.), hook_name, num_hooks, hook_definitions (gated by OTEL_LOG_TOOL_DETAILS), duration_ms, num_success, num_blocking, num_non_blocking_error, num_cancelled. Requires ENABLE_BETA_TRACING_DETAILED=1.
SRC: https://code.claude.com/docs/en/monitoring-usage.md

### Claude Code does NOT propagate OTEL_* to subprocesses
OTEL_* variables are not passed to Bash tool commands, hooks, MCP servers, or language servers. Only TRACEPARENT is forwarded to Bash/PowerShell when tracing is active. So a hook cannot inherit the telemetry config; you must set the variables inside the hook command.
SRC: https://code.claude.com/docs/en/monitoring-usage.md

### Prometheus-only export drops unit suffixes; managed settings can lock the OTLP destination
When prometheus is the ONLY exporter in OTEL_METRICS_EXPORTER, unit strings (USD, tokens, s) are omitted so the text format stays valid; metric names are unchanged. Setting OTEL_EXPORTER_OTLP_ENDPOINT in managed settings removes every developer-set per-signal endpoint at startup (warning visible with claude --debug). Setting OTEL_EXPORTER_OTLP_HEADERS/CLIENT_KEY/CLIENT_CERTIFICATE additionally removes every developer-set endpoint variable. Exporter selectors (OTEL_METRICS_EXPORTER, OTEL_LOGS_EXPORTER, OTEL_TRACES_EXPORTER) follow normal per-key precedence, so a developer can still disable a signal unless you lock the selector too.
SRC: https://code.claude.com/docs/en/monitoring-usage.md

### Exporter failures are silent by default
The CLI fails silently on export errors: if the endpoint is unreachable the agent runs normally and the telemetry is dropped with no error. Set CLAUDE_CODE_OTEL_DIAG_STDERR=1 to surface exporter diagnostics (requires Claude Code v2.1.179+); read them via the SDK's stderr callback/option.
SRC: https://code.claude.com/docs/en/agent-sdk/observability.md

### Gateway auth changes the identity attributes
When signed into a Claude apps gateway: user.id becomes the IdP subject (not the anonymous install ID), user.email is the signed-in email, user.groups is comma-separated IdP group membership, identity.source is "gateway-oidc".
SRC: https://code.claude.com/docs/en/monitoring-usage.md

### SDKResultMessage field list (success and error variants)
Success: type:'result', subtype:'success', duration_ms, duration_api_ms, is_error, num_turns, result, total_cost_usd, usage (NonNullableUsage), modelUsage {[modelName]: ModelUsage}, permission_denials (SDKPermissionDenial[]), structured_output?, uuid, session_id. Error: same minus result, plus errors: string[] and subtype in {error_during_execution, error_max_turns, error_max_budget_usd, error_max_structured_output_retries}. Docs additionally document a stop_reason field (string|null; end_turn, max_tokens, refusal; null after a session crash). SDKPermissionDenial = {tool_name, tool_use_id, tool_input}. ModelUsage = {inputTokens, outputTokens, cacheReadInputTokens, cacheCreationInputTokens, webSearchRequests, costUSD, contextWindow}.
SRC: https://tessl.io/registry/tessl/npm-anthropic-ai--claude-agent-sdk/0.1.0/files/docs/types.md

### usage undercounts subagents; total_cost_usd and modelUsage do not
Explicit table in the docs: usage = 'Excluded. Counts only the top-level agent loop, so tokens consumed inside subagents are not added'; total_cost_usd = 'Included'; modelUsage/model_usage = 'Included ... broken down by model'. Also: per-step output_tokens on assistant messages is a placeholder taken from message_start — read output tokens from the result message only.
SRC: https://code.claude.com/docs/en/agent-sdk/cost-tracking.md

### --max-budget-usd does not abort mid-request; it enforces in three ways
Compared against the running total_cost_usd (so subagent spend counts). At the cap Claude Code (1) refuses to spawn more subagents, returning 'Budget limit reached', (2) stops background subagents still running, (3) ends the query with the error_max_budget_usd result subtype. Cap-enforcement behaviours require Claude Code v2.1.217+. On error_max_budget_usd, usage leaves out the response that crossed the budget while total_cost_usd and modelUsage include it. In streaming input mode a /clear resets the budget counter.
SRC: https://code.claude.com/docs/en/agent-sdk/agent-loop.md

### --max-turns counts tool-use round trips only
'You can cap the loop with max_turns / maxTurns, which counts tool-use turns only.' A turn = Claude produces output including tool calls, tools execute, results feed back. The final text-only response is not a tool-use turn. Hitting it yields subtype error_max_turns with no result field but with total_cost_usd, usage, num_turns and session_id intact, so you can resume the session_id with a higher limit.
SRC: https://code.claude.com/docs/en/agent-sdk/agent-loop.md

### system/init is the kit's self-test surface and has explicit CI-gate fields
plugins: array of {name, path} that loaded successfully. plugin_errors: array of {plugin, type, message}; affected plugins are demoted and absent from plugins; the key is omitted when there are no errors. mcp_servers: array of {name, status}. mcp_server_errors: array of {name, type, message} where type is a skip category such as unknown_type, url_missing_type, invalid_config, reserved_name; key omitted when empty 'so a CI gate can fail on a non-empty array' (requires v2.1.219+). Also carries skills, agents, slash_commands, tools, model, permissionMode, apiKeySource, claude_code_version, cwd, output_style, betas, capabilities (e.g. interrupt_receipt_v1; v2.1.205+), uuid, session_id.
SRC: https://code.claude.com/docs/en/headless.md

### parent_tool_use_id attributes messages to a subagent at any nesting depth
'Messages from subagents appear in the stream as assistant and user messages whose parent_tool_use_id field is the ID of the tool call that spawned the subagent. Messages from the main conversation carry null in that field.' By default only subagent tool_use/tool_result blocks are emitted; pass --forward-subagent-text or set CLAUDE_CODE_FORWARD_SUBAGENT_TEXT (v2.1.211+) to also emit subagent text and thinking. Nested subagents carry the ID of the Agent tool call that spawned them, so the full nesting tree is reconstructable (v2.1.219+). Note stream_event partial messages always carry parent_tool_use_id = null — token deltas from subagents are never forwarded.
SRC: https://code.claude.com/docs/en/headless.md

### The Agent tool was renamed from Task, and the old name still leaks into two places
'The tool name was renamed from "Task" to "Agent" in Claude Code v2.1.63. Current SDK releases emit "Agent" in tool_use blocks but still use "Task" in the system:init tools list and in result.permission_denials[].tool_name.' Check both names.
SRC: https://code.claude.com/docs/en/agent-sdk/subagents.md

### Subagent spend/depth/concurrency caps exist as env vars
CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH (default 3 layers below main; 1 stops subagents spawning their own), CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS (default 20; at the limit a tool_result block carries 'Concurrent subagent limit reached'), and maxBudgetUsd/max_budget_usd as a query option. Requires TS SDK v0.3.219 / Python SDK v0.2.127 (Claude Code v2.1.219+).
SRC: https://code.claude.com/docs/en/agent-sdk/subagents.md

### --json-schema uses JSON Schema draft-07 and fails the run at startup if invalid
Invalid schema: 'Error: --json-schema is not a valid JSON Schema' plus validator diagnostic (v2.1.205+; before that invalid schemas were silently ignored). `format` is accepted as an annotation but not enforced. Zod must be converted with z.toJSONSchema(schema, { target: "draft-7" }). A result can also be subtype success with NO structured_output — treat that as failure too. Structured output never streams; it appears only in the final result.
SRC: https://code.claude.com/docs/en/agent-sdk/structured-outputs.md

### --bare is the recommended CI mode and changes what loads
--bare skips auto-discovery of hooks, skills, plugins, MCP servers, auto memory and CLAUDE.md, and never reads OAuth credentials or the keychain (set ANTHROPIC_API_KEY). Without --bare, a -p session runs the hooks in a project's .claude/settings.json even in an untrusted folder, and connects .mcp.json servers, because -p shows no trust dialog. 'It will become the default for -p in a future release.'
SRC: https://code.claude.com/docs/en/headless.md

### Claude Code exits 0 on success, non-zero on failure, 143 on SIGTERM
SIGTERM aborts the in-progress turn, terminates the process tree of any running Bash command, runs SessionEnd hooks, and exits 143. Background Bash tasks are killed ~5s after the final result. Background subagents/workflows are waited for, capped at 10 minutes by default (CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS; 0 = no limit). Piped stdin is capped at 10MB.
SRC: https://code.claude.com/docs/en/headless.md

### SWE-bench construction pipeline is a 3-stage filter, ~90,000 PRs -> 2,294 instances
Stage I: scrape PRs from the top 100 most-downloaded PyPI packages, 12 repos, ~90,000 PRs. Stage II attribute filter: PR is merged AND resolves a GitHub issue AND makes changes to the repository's test files. Stage III execution filter: at least one test whose status changes fail->pass, and no installation/runtime errors. Result: 2,294 instances.
SRC: https://arxiv.org/html/2310.06770v3

### SWE-bench instance schema — the exact fields to mirror for a repo-local set
instance_id (repo_owner__repo_name-PR-number), repo, base_commit (HEAD before the solution PR), patch (gold patch excluding test code), test_patch (test-file patch from the solution PR), problem_statement (issue title + body), hints_text (comments made before the solution PR's first commit date), created_at, version, environment_setup_commit, FAIL_TO_PASS (JSON list of test strings), PASS_TO_PASS (JSON list), difficulty (4 categories).
SRC: https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified

### SWE-bench Verified human-validation protocol
93 experienced Python developers annotated 1,699 randomly sampled SWE-bench test instances; each sample reviewed by three separate annotators for (a) well-specified issue description, (b) appropriate unit tests, (c) other major reliability issues. 38.3% flagged for underspecified problem statements; 61.1% flagged for unit tests that may unfairly mark valid solutions incorrect. Filtering rule is ensemble-OR: drop a sample if ANY of the three annotators flagged it. Final set = 500 samples, deliberately over-weighting the 1-4 hour and >4 hour difficulty buckets.
SRC: https://openai.com/index/introducing-swe-bench-verified/

### Held-out PR tests are a weak oracle: ~half of test-passing SWE-bench patches would not be merged
METR recruited 4 active maintainers from scikit-learn, Sphinx and pytest to review 296 AI-generated PRs across 95 unique tasks (19% of SWE-bench Verified) from 5 models. Maintainer merge rate is ~24 percentage points below the SWE-bench pass rate after adjusting with a golden baseline: 47 human-written previously-merged patches were re-submitted and accepted only 68% of the time, establishing the noise floor.
SRC: https://metr.org/notes/2026-03-10-many-swe-bench-passing-prs-would-not-be-merged-into-main/

### Neither SWE-bench Multilingual nor Multi-SWE-bench includes Kotlin
SWE-bench Multilingual: 300 tasks, 42 repos, 9 languages (C, C++, Go, Java, JavaScript, TypeScript, PHP, Ruby, Rust). Multi-SWE-bench: 2,132 instances, 68 expert annotators, 8 languages (Python, Java, TypeScript, JavaScript, Go, Rust, C, C++). Kotlin is absent from both.
SRC: https://arxiv.org/pdf/2504.02605

### A Kotlin SWE-bench already exists: JetBrains kotlin-swe-bench, 105 tasks / 8 repos
Built on Multi-SWE-bench infrastructure. Per-repo task counts: ktlint/ktlint 43, detekt/detekt 28, oss-review-toolkit/ort 12, Hannah-Sten/TeXiFy-IDEA 8, ankidroid/Anki-Android 6, Kotlin/dataframe 5, square/okhttp 2, GradleUp/shadow 1. Each task = merged PR mined into {base commit, gold patch, regression tests, natural-language issue}, packaged as a reproducible Docker image with a layered-cache strategy. Resolved only when the generated solution passes the required tests.
SRC: https://kotlinlang.org/benchmark/methodology/

### An Android-inclusive benchmark exists: Firebender Kotlin-bench, 100 real-world Kotlin and Android tasks
Per-repo JSON configs at agent-bench/config/*.json cover anki (ankidroid/Anki-Android), thunderbird, wordpress, coroutines, datetime, ktlint — i.e. real Android app repos. Results (blog_findings.md): Claude Opus 4.5 leads at 46% across 100 tasks, 8 models evaluated, range 13%-46%. Difficulty split: 38 hard (unsolved by any model), 55 medium, 7 easy. Failing attempts make ~50% more tool calls than successful ones; successful tasks use fewer file reads (9.7 vs 12.7), fewer greps (5.0 vs 7.0), more test runs (4.6 vs 3.8).
SRC: https://github.com/firebenders/Kotlin-bench

### EMPIRICAL ANCHOR for statistical power: a 7-point spread at n=100 was not significant
Kotlin-bench: 'The top four models—Opus, GPT-5.2, Gemini Pro, and Gemini Flash (39-46%)—show no statistically significant performance differences.' Only larger gaps were significant (Opus 46% vs Sonnet 4 29%). This is a direct, real measurement on a 100-instance agentic coding benchmark.
SRC: https://github.com/firebenders/Kotlin-bench

### Sample-size formula and the 3-point / 969-question worked example
Evan Miller, 'Adding Error Bars to Evals: A Statistical Approach to Language Model Evaluations', arXiv:2411.00640 (1 Nov 2024). n = (z_{alpha/2} + z_beta)^2 (omega^2 + sigma_A^2/K_A + sigma_B^2/K_B) / delta^2. Worked example: detecting a 3% absolute difference at 80% power / 5% significance requires ~969 independent questions. Paired analysis (same questions, both arms) reduces variance by 2*Cov(x_A, x_B)/n. Clustered standard errors can be up to 3x the naive CLT value when questions share a source.
SRC: https://arxiv.org/html/2411.00640v1

### Terminal-Bench 2.0 is the closest thing to a harness-level benchmark
89 curated tasks across 16 categories, easy/medium/hard. Tasks are in the Harbor task format and run with the Harbor harness, which provisions a fresh Docker container per task, injects the agent and collects execution traces. Distributed via the Harbor registry, run with `harbor run -d`. Supports Claude Code, Codex CLI, OpenHands, Mini-SWE-Agent and Terminus 2 as pluggable harnesses — i.e. you can hold the model fixed and vary the harness. ICLR 2026 paper.
SRC: https://openreview.net/pdf/417ac3236de7dbf3fc3414c51754dd239271663e.pdf

### HARBOR (Apr 2026) treats harness design itself as an ML optimisation problem
Biswa Sengupta, Jinhua Wang, arXiv:2604.20938, submitted 22 Apr 2026. Opens: 'Long-horizon language-model agents are dominated, in lines of code and in operational complexity, not by their underlying model but by the harness that wraps it: context compaction, tool caching, semantic memory, trajectory reuse, speculative tool prediction, and the glue that binds the model to a sandboxed execution environment.' Formulates harness config as constrained noisy Bayesian optimisation over a mixed-variable cost-heterogeneous space (block-additive SAAS surrogate, multi-fidelity cost-aware acquisition, TuRBO trust regions), benchmarked against a controlled four-round manual-tuning study on a production coding agent.
SRC: https://arxiv.org/abs/2604.20938

### Skills measurably help less as the setting gets more realistic
'How Well Do Agentic Skills Work in the Wild', Liu et al., arXiv:2604.04323 (6 Apr 2026). 34,000 real-world skills, evaluated on Terminal-Bench 2.0. 'performance gains degrade consistently as settings become more realistic, with pass rates approaching no-skill baselines in the most challenging scenarios.' Best case with retrieval + refinement: Claude Opus 4.6 from 57.7% to 65.5%.
SRC: https://arxiv.org/abs/2604.04323

### Anthropic's own eval guidance: 20-50 tasks, isolated per-dimension judges, pass@k vs pass^k
'Demystifying evals for AI agents', Anthropic engineering, 9 Jan 2026. Start with '20-50 simple tasks drawn from real failures'. 'A good task is one where two domain experts would independently reach the same pass/fail verdict.' Create clear structured rubrics and 'grade each dimension with an isolated LLM-as-judge rather than using one to grade all dimensions'. Give the judge an out ('return Unknown when it doesn't have enough information'). Calibrate graders against human experts. 'grade what the agent produced, not the path it took'. pass@k = success in at least one of k; pass^k = all k succeed; 'pass@k for tools where one success matters, pass^k for agents where consistency is essential'.
SRC: https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents

### Anthropic's skill-creator ships a real blind A/B harness with named JSON schemas
skills/skill-creator/ contains agents/analyzer.md, agents/comparator.md, agents/grader.md, scripts/aggregate_benchmark.py, scripts/generate_report.py, scripts/improve_description.py, scripts/run_loop.py, eval-viewer/generate_review.py. Schemas (references/schemas.md): evals.json {skill_name, evals:[{id, prompt, expected_output, files?, expectations[]}]}, grading.json {expectations[{text, passed, evidence}], summary, execution_metrics, timing, claims, user_notes_summary, eval_feedback}, metrics.json {tool_calls, total_tool_calls, total_steps, files_created, errors_encountered}, timing.json {total_tokens, duration_ms}, benchmark.json {metadata, runs[], run_summary, notes}, comparison.json {winner, reasoning, rubric, expectation_results}, history.json {started_at, skill_name, current_best, iterations[{expectation_pass_rate, grading_result, parent}]}. Run layout: workspace/iteration-N/eval-ID/{with_skill,without_skill}/
SRC: https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md

### The comparator is explicitly blind and produces a 1-5 rubric across two dimensions
'You receive two outputs labeled A and B, but you DO NOT know which skill produced which. This prevents bias toward a particular skill or approach.' Content rubric: correctness, completeness, accuracy. Structure rubric: organization, formatting, usability. Each 1(Poor)/3(Acceptable)/5(Excellent); content_score and structure_score are averages, overall_score scaled to 1-10. Winner decided by (1) overall rubric score, (2) expectation pass rates as secondary evidence, (3) TIE only if genuinely equal. Guideline: 'Stay blind: DO NOT try to infer which skill produced which output.'
SRC: https://github.com/anthropics/skills/blob/main/skills/skill-creator/agents/comparator.md

### benchmark.json reports mean/stddev/min/max per configuration — the A/B statistics contract
metadata {skill_name, skill_path, executor_model, analyzer_model, timestamp, evals_run[], runs_per_configuration}; runs[] each {eval_id, configuration, run_number, result{pass_rate, passed, failed, total, time_seconds, tokens, tool_calls, errors}, expectations, notes}; run_summary per configuration ('with_skill'/'without_skill') with mean/stddev/min/max for pass_rate, time_seconds and tokens; plus a delta section comparing the first two configurations. CLI: `python -m scripts.aggregate_benchmark <benchmark_dir> --skill-name <name> --skill-path <path> -o <out>`.
SRC: https://github.com/anthropics/skills/blob/main/skills/skill-creator/scripts/aggregate_benchmark.py

### Anthropic names skill deletion as an explicit purpose of skill evals
'Improving skill-creator: Test, measure, and refine Agent Skills', claude.com blog, 3 Mar 2026. Evals have two primary uses: 'Catching quality regressions when models or infrastructure change' and 'Identifying when base model capabilities have made skills unnecessary.' Benchmark mode tracks 'pass rate, elapsed time, and token usage'. Comparator agents perform blind A/B between two skill versions or skill vs. unenhanced Claude. Description optimisation improved 5 of 6 public document-creation skills. Skills are split into 'capability uplift' (things the base model cannot do consistently) vs 'encoded preference' (org workflow sequencing) — only the first class expires as models improve.
SRC: https://claude.com/blog/improving-skill-creator-test-measure-and-refine-agent-skills

### THE canonical deletion quote: Anthropic Managed Agents, 8 Apr 2026
'Claude Sonnet 4.5 would wrap up tasks prematurely as it sensed its context limit approaching—a behavior sometimes called "context anxiety."' The team added context resets to the harness. On Claude Opus 4.5, 'we found that the behavior was gone. The resets had become dead weight.' The architectural response is not a prescription of what to delete but decoupled interfaces: 'We're opinionated about the shape of these interfaces, not about what runs behind them.' Managed Agents virtualises three components — Session (append-only event log), Harness (the Claude-calling loop), Sandbox (execution environment) — with operations execute(name, input), provision({resources}), wake(sessionId), getSession(id), emitEvent(id, event), getEvents(). Framed as a 'meta-harness' making 'no assumptions about the number or location of brains or hands that Claude will need.'
SRC: https://www.anthropic.com/engineering/managed-agents

### Agent OS v3 (20 Jan 2026) retired its implementation and orchestration phases
'The implementation and orchestration phases from v2 have been retired.' Rationale: 'Today's frontier models handle spec implementation well on their own—this is the recommended approach in 2026+' and 'It doesn't make sense to reinvent these core functions, which are much better handled by the core tools than 3rd-party frameworks like Agent OS.' Spec writing now defers to Plan Mode; task breakdown is done automatically by Claude Code. What remains: Standards (with discovery/injection tools), Specs (structure kept, creation deferred), Product Planning (mission/roadmap/tech-stack), Profiles.
SRC: https://github.com/buildermethods/agent-os/discussions/310

### LLM-judge bias magnitudes: style bias dominates, position bias is small
'Judging the Judges: A Systematic Evaluation of Bias Mitigation Strategies in LLM-as-a-Judge Pipelines', Sadman Kabir Soumik, arXiv:2604.23178 (25 Apr 2026, rev 24 Jun 2026). 9 debiasing strategies x 5 judge models from 4 providers. Style bias (markdown over plain text) is the dominant effect at 0.10-0.76; position bias is minor at <=0.04; verbosity bias is heterogeneous (Gemini Pro/Flash/Llama prefer longer, +0.24 to +0.44; Claude prefers concise, -0.12; GPT-4o neutral, -0.04). Best debiasing gains: 11.5 pp (Claude S8), 7.5 pp (Flash S8), 7.3 pp (Claude S5). Gemini 2.5 Flash + Combined Budget reached 71.0% agreement (kappa=0.549) at ~$0.001/eval, ~15x cheaper than Claude Sonnet 4's 69.5%.
SRC: https://arxiv.org/abs/2604.23178

### promptfoo model-graded assertion types (the prompt-regression option)
Output-based: llm-rubric, agent-rubric, search-rubric, model-graded-closedqa, factuality, g-eval, answer-relevance, similar, pi, classifier, moderation, select-best, max-score. Context-based: context-recall, context-relevance, context-faithfulness. Conversational: conversation-relevance. Trajectory: trajectory:goal-success. Grader provider is overridable at defaultTest.options.provider, per-test, or per-assertion.
SRC: https://www.promptfoo.dev/docs/configuration/expected-outputs/model-graded/

### DISCREPANCY: real dashboards use a subset of the documented metrics and invent Loki-derived ones
ColeMurray/claude-code-otel's claude-code-dashboard.json plots only claude_code_session_count_total, claude_code_cost_usage_USD_total, claude_code_token_usage_tokens_total, claude_code_lines_of_code_count_total, claude_code_commit_count_total, claude_code_pull_request_count_total. It has NO panel for claude_code.active_time.total or claude_code.code_edit_tool.decision, and derives all tool-usage/latency/error panels from Loki log queries over claude_code.tool_result / claude_code.api_request / claude_code.api_error instead of metrics. No panel uses query_source, agent.name, skill.name or plugin.name — subagent/skill cost attribution is available in the data and unused in every public dashboard I checked.
SRC: https://github.com/ColeMurray/claude-code-otel/blob/main/claude-code-dashboard.json

### DISCREPANCY: SigNoz's guide documents an event name absent from the current Anthropic docs
SigNoz's Claude Code monitoring guide lists claude_code.api_retries_exhausted as a key log event. That name does not appear anywhere in code.claude.com/docs/en/monitoring-usage.md as of Aug 2026 (the exhaustive event list is: user_prompt, assistant_response, tool_result, api_request, api_error, api_refusal, api_request_body, api_response_body, tool_decision, permission_mode_changed, auth, mcp_server_connection, internal_error, plugin_installed, plugin_loaded). Retry information is instead surfaced in stream-json as a system/api_retry event with fields attempt, max_retries, retry_delay_ms, error_status, error. Treat api_retries_exhausted as either stale or undocumented — do not build an alert on it without verifying against your own collector.
SRC: https://signoz.io/docs/claude-code-monitoring/

### AWS's reference implementation uses all 8 metrics and adds a custom resource attribute
guidance-for-claude-code-with-amazon-bedrock/assets/docs/MONITORING.md collects all 8 documented metrics including claude_code.active_time.total and claude_code.code_edit_tool.decision, using native PromQL chart widgets with no Lambda or DynamoDB. Dashboard sections: Overview, Token Usage, Developer Productivity, Organizational Breakdown, Bedrock API Health. It adds a settings_version resource attribute so 'every user's telemetry then carries the version of the distribution package they installed' — a directly reusable pattern for versioning a workflow kit.
SRC: https://github.com/aws-solutions-library-samples/guidance-for-claude-code-with-amazon-bedrock/blob/main/assets/docs/MONITORING.md

### Grafana Cloud's Claude Code integration requires cumulative temporality
Required env block: CLAUDE_CODE_ENABLE_TELEMETRY=1, OTEL_METRICS_EXPORTER=otlp, OTEL_LOGS_EXPORTER=otlp, OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf, OTEL_EXPORTER_OTLP_ENDPOINT=<grafana-cloud-otlp-endpoint>, OTEL_EXPORTER_OTLP_HEADERS=Authorization=Basic <base64 instanceid:token>, OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE=cumulative. Claude Code defaults to delta, so omitting the last line silently breaks Prometheus-style counters.
SRC: https://grafana.com/docs/grafana-cloud/monitor-infrastructure/integrations/integration-reference/integration-claude-code/

## EXAMPLES
### Minimal per-developer telemetry env block (OTLP gRPC to a local collector), plus the cardinality/privacy switches you actually want for a kit-instrumentation experiment
FILE: ~/.zshrc, or the `env` block of .claude/settings.json / managed-settings.json
```
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_METRICS_EXPORTER=otlp
export OTEL_LOGS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=grpc
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export OTEL_METRIC_EXPORT_INTERVAL=10000
export OTEL_LOGS_EXPORT_INTERVAL=5000
# needed to see real skill/plugin/MCP names instead of "custom"/"third-party":
export OTEL_LOG_TOOL_DETAILS=1
# tag the kit version so you can diff before/after a deletion:
export OTEL_RESOURCE_ATTRIBUTES="kit.version=2026.08.17,team.id=android-member,department=engineering"
# beta tracing = full subagent delegation tree as one trace:
export CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1
export OTEL_TRACES_EXPORTER=otlp
export OTEL_TRACES_EXPORT_INTERVAL=1000
# surface exporter failures instead of silently dropping telemetry (v2.1.179+):
export CLAUDE_CODE_OTEL_DIAG_STDERR=1
claude
```
SRC: https://code.claude.com/docs/en/monitoring-usage.md

### OTEL_RESOURCE_ATTRIBUTES escaping rules — the #1 silent-failure trap
FILE: shell profile / CI env
```
# INVALID (space is literal, quotes do not escape it):
export OTEL_RESOURCE_ATTRIBUTES="org.name=My Company"
# VALID:
export OTEL_RESOURCE_ATTRIBUTES="org.name=Johns_Organization"
export OTEL_RESOURCE_ATTRIBUTES="org.name=John%27s%20Organization"
# Allowed: US-ASCII only, excluding control chars, whitespace, " , ; \
# Custom keys never override standard attributes like user.id or session.id.
```
SRC: https://code.claude.com/docs/en/monitoring-usage.md

### OTel Collector config that fans metrics to Prometheus and events to Loki (working, from ColeMurray/claude-code-otel)
FILE: collector-config.yaml at repo root, mounted into the otel/opentelemetry-collector container
```
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  resource:
    attributes:
      - key: environment
        value: "production"
        action: upsert

exporters:
  prometheus:
    endpoint: "0.0.0.0:8889"
  debug:
    verbosity: normal
  otlphttp:
    endpoint: http://loki:3100/otlp

service:
  pipelines:
    metrics:
      receivers: [otlp]
      processors: [resource]
      exporters: [prometheus, debug]
    logs:
      receivers: [otlp]
      processors: [resource]
      exporters: [debug, otlphttp]
```
SRC: https://github.com/ColeMurray/claude-code-otel/blob/main/collector-config.yaml

### PromQL/LogQL that actually work against the Prometheus-normalized metric names (note the name mangling: dots -> underscores, unit appended, _total suffix)
FILE: Grafana dashboard JSON panels[].targets[].expr
```
# cost in the last hour
sum(increase(claude_code_cost_usage_USD_total{job="otel-collector"}[1h]))
# tokens per minute by type (input/output/cacheRead/cacheCreation)
sum by (type) (rate(claude_code_token_usage_tokens_total{job="otel-collector"}[5m]) * 60)
# cost by model
sum by (model) (increase(claude_code_cost_usage_USD_total{job="otel-collector"}[1h]))
# lines added vs removed per minute
sum by (type) (rate(claude_code_lines_of_code_count_total{job="otel-collector"}[5m]) * 60)
# --- NOT in any public dashboard; add these for kit instrumentation ---
# cost attributable to each skill
sum by (skill_name) (increase(claude_code_cost_usage_USD_total[24h]))
# main-loop vs subagent spend split
sum by (query_source) (increase(claude_code_cost_usage_USD_total[24h]))
# edit rejection rate = the single best proxy for "is the kit producing acceptable code"
sum(rate(claude_code_code_edit_tool_decision_total{decision="reject"}[1d]))
  / sum(rate(claude_code_code_edit_tool_decision_total[1d]))
# tool success rate from Loki events
100 * (sum by (tool_name) (count_over_time({service_name="claude-code"} |= "claude_code.tool_result" | json | success="true" [15m])))
     / (sum by (tool_name) (count_over_time({service_name="claude-code"} |= "claude_code.tool_result" [15m])))
```
SRC: https://github.com/ColeMurray/claude-code-otel/blob/main/claude-code-dashboard.json

### Kit self-test: assert the expected plugins / skills / MCP servers actually loaded, and fail CI if not
FILE: scripts/kit-selftest.sh, wired into .github/workflows/ and a Setup/SessionStart hook
```
#!/usr/bin/env bash
set -euo pipefail

INIT=$(claude -p "reply with OK and nothing else" \
  --output-format stream-json --verbose --max-turns 1 \
  | head -n 20 | jq -c 'select(.type=="system" and .subtype=="init")' | head -1)

# 1. hard failures: anything that failed to load
echo "$INIT" | jq -e '(.plugin_errors // []) | length == 0' \
  || { echo "PLUGIN LOAD FAILED:"; echo "$INIT" | jq '.plugin_errors'; exit 1; }
echo "$INIT" | jq -e '(.mcp_server_errors // []) | length == 0' \
  || { echo "MCP CONFIG REJECTED:"; echo "$INIT" | jq '.mcp_server_errors'; exit 1; }

# 2. presence assertions: the kit's own inventory
for s in spectra-propose spectra-apply guide-audit dev-guide; do
  echo "$INIT" | jq -e --arg s "$s" '.skills | index($s)' >/dev/null \
    || { echo "MISSING SKILL: $s"; exit 1; }
done

# 3. every declared MCP server is connected (not "pending"/"failed")
echo "$INIT" | jq -e '[.mcp_servers[] | select(.status != "connected")] | length == 0' \
  || { echo "MCP NOT CONNECTED:"; echo "$INIT" | jq '.mcp_servers'; exit 1; }

echo "kit self-test OK: $(echo "$INIT" | jq -r '.claude_code_version')"
```
SRC: https://code.claude.com/docs/en/headless.md

### Per-run cost/turn/denial record for a golden-task harness, with hard caps
FILE: evals/run-task.sh; per-run output at evals/runs/<instance_id>/result.json, rollup at evals/runs/summary.jsonl
```
claude --bare -p "$(cat tasks/$ID/issue.md)" \
  --output-format json \
  --max-turns 40 \
  --max-budget-usd 3.00 \
  --permission-mode dontAsk \
  --allowedTools "Read,Edit,Write,Glob,Grep,Bash(./gradlew *),Bash(git *)" \
  --model claude-opus-5 \
  > runs/$ID/result.json

jq -r '{
  id:            "'"$ID"'",
  subtype:       .subtype,          # success | error_max_turns | error_max_budget_usd | error_during_execution | error_max_structured_output_retries
  is_error:      .is_error,
  stop_reason:   .stop_reason,      # end_turn | max_tokens | refusal | null(crash)
  num_turns:     .num_turns,
  duration_ms:   .duration_ms,
  api_ms:        .duration_api_ms,
  cost_usd:      .total_cost_usd,   # includes subagents
  in_tok:        .usage.input_tokens,        # main loop ONLY
  out_tok:       .usage.output_tokens,
  cache_read:    .usage.cache_read_input_tokens,
  cache_create:  .usage.cache_creation_input_tokens,
  denied:        [.permission_denials[]?.tool_name] | unique,
  n_denied:      (.permission_denials | length),
  by_model:      (.modelUsage | to_entries | map({(.key): .value.costUSD}) | add),
  session:       .session_id,
  errors:        (.errors // [])
}' runs/$ID/result.json >> runs/summary.jsonl
```
SRC: https://code.claude.com/docs/en/agent-sdk/cost-tracking.md

### Attribute cost to a specific subagent from a stream-json transcript (parent_tool_use_id -> subagent_type)
FILE: evals/attribute-subagents.sh
```
claude -p "$PROMPT" --output-format stream-json --verbose \
  --forward-subagent-text > run.jsonl

# map Agent tool_use_id -> subagent_type
jq -r 'select(.type=="assistant") | .message.content[]?
       | select(.type=="tool_use" and (.name=="Agent" or .name=="Task"))
       | "\(.id)\t\(.input.subagent_type)"' run.jsonl > agent_ids.tsv

# count messages/tokens per subagent (main loop has parent_tool_use_id == null)
jq -r 'select(.type=="assistant")
       | "\(.parent_tool_use_id // "MAIN")\t\(.message.usage.input_tokens)"' run.jsonl \
  | awk -F'\t' '{sum[$1]+=$2} END {for (k in sum) print k, sum[k]}'

# authoritative per-model cost incl. subagents comes from the result message:
jq -r 'select(.type=="result") | .modelUsage' run.jsonl
```
SRC: https://code.claude.com/docs/en/headless.md

### Structured self-report from the agent itself (--json-schema), so a golden task can emit machine-checkable claims
FILE: evals/schemas/task-report.schema.json
```
claude -p "Fix the failing test in :domain:usecase and report what you did" \
  --output-format json \
  --json-schema '{
    "type":"object",
    "properties":{
      "files_changed":{"type":"array","items":{"type":"string"}},
      "tests_run":{"type":"array","items":{"type":"string"}},
      "all_tests_pass":{"type":"boolean"},
      "guidelines_consulted":{"type":"array","items":{"type":"string"}},
      "hardcoded_strings_added":{"type":"integer"}
    },
    "required":["files_changed","all_tests_pass"]
  }' | jq '.structured_output'

# Note: schema must be JSON Schema draft-07. Zod: z.toJSONSchema(S,{target:"draft-7"}).
# Guard BOTH failure shapes:
#   .subtype == "error_max_structured_output_retries"  -> could not produce valid output
#   .subtype == "success" and .structured_output == null -> also a failure
```
SRC: https://code.claude.com/docs/en/agent-sdk/structured-outputs.md

### Firebender Kotlin-bench per-repo config — the exact shape of an Android golden-task environment spec (build reproducibility solved by pinning JDK + SDK packages + a patch script)
FILE: agent-bench/config/<repo>.json; mirror as evals/env/<module>.json in your own repo
```
{
  "repo": "ankidroid/Anki-Android",
  "repo_url": "https://github.com/ankidroid/Anki-Android.git",
  "jdk_version": "17.0.9-tem",
  "base_commit": "bbfd8f4a10c796d4b955d54530c7f11e81ca250d",
  "android_sdk_packages": [
    "platform-tools",
    "build-tools;34.0.0",
    "build-tools;35.0.0",
    "platforms;android-34",
    "platforms;android-35",
    "extras;google;m2repository",
    "extras;android;m2repository"
  ],
  "install_script": "set -e\n# pin gradle jvmargs\nsed -i 's|org.gradle.jvmargs=.*|org.gradle.jvmargs=-Xmx2048M -XX:MaxMetaspaceSize=512M -Dfile.encoding=UTF-8|' gradle.properties\n# strip resolutionStrategy from settings.gradle.kts (non-reproducible)\nawk '/resolutionStrategy {/,/^    }$/ {next} {print}' settings.gradle.kts > t && mv t settings.gradle.kts\n# drop proprietary/unavailable plugins\nsed -i '/app.brant:amazonappstorepublisher/d' build.gradle\n# force JDK 17\nsed -i 's/JavaVersion.VERSION_11/JavaVersion.VERSION_17/g' AnkiDroid/build.gradle\n# pin floating dependency versions\nsed -i 's/com.github.ByteHamster:SearchPreference:[v]*[0-9].[0-9].[0-9]/com.github.ByteHamster:SearchPreference:2.7.2/g' AnkiDroid/build.gradle",
  "test_command": "./gradlew :AnkiDroid:testPlayDebugUnitTest"
}
```
SRC: https://github.com/firebenders/Kotlin-bench/blob/kotlin-bench/agent-bench/config/anki.json

### SWE-bench-shaped instance record to mine from your own merged PRs (Jira issue text + base commit + the PR's own tests as oracle)
FILE: evals/golden/instances.jsonl (one JSON object per line), environments at evals/golden/env/<instance_id>/Dockerfile
```
{
  "instance_id": "kkday-android-member-PR-4821",
  "repo": "kkday/kkday-android-member",
  "base_commit": "<sha of PR base>",
  "environment_setup_commit": "<sha with a known-good gradle/JDK state>",
  "problem_statement": "<Jira Story/Bug title + description, stripped of any hint of the implementation>",
  "hints_text": "<Jira comments made BEFORE the first commit of the fix branch>",
  "patch": "<git diff base..head -- ':!*/src/test/*' ':!*/src/androidTest/*'>",
  "test_patch": "<git diff base..head -- '*/src/test/*' '*/src/androidTest/*'>",
  "FAIL_TO_PASS": ["com.kkday.usecase.AuthUseCaseTest.refreshes_token_on_401"],
  "PASS_TO_PASS": ["com.kkday.usecase.AuthUseCaseTest.returns_cached_token"],
  "created_at": "2026-05-11T09:02:00Z",
  "test_command": "./gradlew :domain:usecase:testDevelopDebugUnitTest --tests '*AuthUseCaseTest*'",
  "difficulty": "15min-1hr"
}

# mining filter (SWE-bench stage II+III, adapted):
#  - PR is merged AND closes a Jira Story/Bug (parse the commit-message template)
#  - PR touches at least one */src/test/* file
#  - apply test_patch alone at base_commit -> at least one test goes FAIL
#  - apply test_patch + gold patch -> that test goes PASS and no PASS_TO_PASS regresses
#  - run the whole thing 3x; drop any instance whose result is not identical all 3 times (flake filter)
```
SRC: https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified

### Anthropic skill-creator eval set format (evals.json) and the workspace layout its A/B harness produces
FILE: <skill>/evals/evals.json; run artifacts under workspace/iteration-N/<eval-id>/{with_skill,without_skill}/
```
// evals/evals.json
{
  "skill_name": "guide-audit",
  "evals": [
    {
      "id": "detects-hardcoded-color",
      "prompt": "Audit the staged diff for dev-guide violations.",
      "files": ["fixtures/hardcoded-color.diff"],
      "expected_output": "A report listing the StyleDictionary token violation as must-fix.",
      "expectations": [
        "Report names the exact file and line of the hardcoded hex value",
        "Report classifies it under the correct enforce level from rules.yaml",
        "Report does NOT flag the unrelated import reordering"
      ]
    }
  ]
}

# resulting run layout (one directory per configuration = the A/B arms)
workspace/iteration-3/detects-hardcoded-color/with_skill/{outputs/,grading.json,timing.json}
workspace/iteration-3/detects-hardcoded-color/without_skill/{outputs/,grading.json,timing.json}
workspace/iteration-3/benchmark.json   # run_summary.{with_skill,without_skill}.pass_rate.{mean,stddev,min,max}

# aggregate + review
python -m scripts.aggregate_benchmark workspace/iteration-3 --skill-name guide-audit
python eval-viewer/generate_review.py workspace/iteration-3 \
  --skill-name "guide-audit" --benchmark workspace/iteration-3/benchmark.json

# description trigger tuning: 20 queries (8-10 should-trigger, 8-10 should-not-trigger)
python -m scripts.run_loop --eval-set evals/trigger-queries.json \
  --skill-path skills/guide-audit --model <id> --max-iterations 5 --verbose
```
SRC: https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md

### grading.json / benchmark.json / comparison.json field contracts (what your own fingerprint runner should emit to stay compatible)
FILE: <run-dir>/grading.json, workspace/iteration-N/benchmark.json, workspace/iteration-N/<eval-id>/comparison.json
```
// <run-dir>/grading.json
{
  "expectations": [{"text": "...", "passed": true, "evidence": "<=125 char quote"}],
  "summary": {"passed": 4, "failed": 1, "total": 5, "pass_rate": 0.8},
  "execution_metrics": {"tool_calls": {"Read": 9, "Bash": 4}, "total_tool_calls": 13,
                        "total_steps": 7, "files_created": 2, "errors_encountered": 0},
  "timing": {"total_tokens": 91234, "duration_ms": 184000},
  "claims": [...], "user_notes_summary": {...}, "eval_feedback": [...]
}

// workspace/iteration-N/benchmark.json
{
  "metadata": {"skill_name":"","skill_path":"","executor_model":"","analyzer_model":"",
               "timestamp":"","evals_run":[],"runs_per_configuration":5},
  "runs": [{"eval_id":"","configuration":"with_skill","run_number":1,
            "result":{"pass_rate":0.8,"passed":4,"failed":1,"total":5,
                      "time_seconds":184,"tokens":91234,"tool_calls":13,"errors":0}}],
  "run_summary": {"with_skill":   {"pass_rate":{"mean":0.78,"stddev":0.11,"min":0.6,"max":1.0}},
                  "without_skill":{"pass_rate":{"mean":0.62,"stddev":0.19,"min":0.2,"max":0.8}}}
}

// comparison.json from the BLIND comparator
{"winner":"A"|"B"|"TIE", "reasoning":"...",
 "rubric":{"A":{"content":{"correctness":5,"completeness":5,"accuracy":4},
                "structure":{"organization":4,"formatting":5,"usability":4},
                "content_score":4.7,"structure_score":4.3,"overall_score":9.0}},
 "expectation_results":{"A":{"passed":4,"total":5,"pass_rate":0.80,"details":[...]}}}
```
SRC: https://github.com/anthropics/skills/blob/main/skills/skill-creator/references/schemas.md

### promptfoo config for prompt/skill-body regression with a pinned grader (deterministic assertions first, llm-rubric only where judgement is genuinely needed)
FILE: evals/<suite-name>/promptfooconfig.yaml with prompts/ and tests/ subdirectories
```
# evals/guide-audit/promptfooconfig.yaml
prompts:
  - file://prompts/audit.txt
providers:
  - id: anthropic:messages:claude-opus-5
defaultTest:
  options:
    provider: anthropic:messages:claude-sonnet-5   # pin the GRADER separately from the SUT
  assert:
    - type: is-json
    - type: not-contains
      value: "#FF"          # no hardcoded hex in output
tests: file://tests/*.yaml

# evals/guide-audit/tests/hardcoded-color.yaml
- vars:
    diff: file://../fixtures/hardcoded-color.diff
  assert:
    - type: contains
      value: "StyleDictionary"
    - type: regex
      value: 'libs/designsystem/.*\.kt:\d+'
    - type: llm-rubric
      value: >
        The report classifies the violation using an enforce level from rules.yaml
        (new-only / on-touch / migrate / exempt) and does not invent a level.
      provider:
        id: anthropic:messages:claude-sonnet-5
        config: { temperature: 0 }

# run
npx promptfoo@latest validate config -c evals/guide-audit/promptfooconfig.yaml
npx promptfoo@latest eval -c evals/guide-audit/promptfooconfig.yaml -o out.json --no-cache
```
SRC: https://www.promptfoo.dev/docs/configuration/expected-outputs/model-graded/

### Cross-check matrix: metric name in docs vs Prometheus-normalized name vs whether public dashboards use it
FILE: docs/testing/observability/claude-code-metric-matrix.md
```
OTel name                             Prometheus name                            ColeMurray  AWS ref  Grafana Cloud
claude_code.session.count             claude_code_session_count_total            YES         YES      YES
claude_code.cost.usage                claude_code_cost_usage_USD_total           YES         YES      YES
claude_code.token.usage               claude_code_token_usage_tokens_total       YES         YES      YES
claude_code.lines_of_code.count       claude_code_lines_of_code_count_total      YES         YES      YES
claude_code.commit.count              claude_code_commit_count_total             YES         YES      YES
claude_code.pull_request.count        claude_code_pull_request_count_total       YES         YES      YES
claude_code.code_edit_tool.decision   claude_code_code_edit_tool_decision_total  NO          YES      YES
claude_code.active_time.total         claude_code_active_time_total_seconds*     NO          YES      YES

* unit suffix is DROPPED when prometheus is the only exporter in OTEL_METRICS_EXPORTER.
  Names in Prometheus-only mode: claude_code_active_time_total, claude_code_cost_usage_total,
  claude_code_token_usage_total. Confirm against your own /metrics before writing alerts.

Attributes present in the data and used by ZERO public dashboard I checked:
  query_source, agent.name, skill.name, plugin.name, marketplace.name,
  mcp_server.name, mcp_tool.name, effort, speed, start_type, source, language
```
SRC: https://code.claude.com/docs/en/monitoring-usage.md

## GOTCHAS
- Metric name mangling is not stable across exporter configs. In Prometheus-only mode Claude Code OMITS the unit string (USD, tokens, s) to keep the text format valid, but keeps it when combined with another exporter. So `claude_code_cost_usage_USD_total` and `claude_code_cost_usage_total` can both be correct depending on your OTEL_METRICS_EXPORTER value. Never hardcode a metric name into an alert without scraping /metrics first.
- Telemetry export fails SILENTLY by default. If the collector is unreachable the agent runs normally and drops the data with no error in your application. You will discover the gap weeks later when the dashboard is empty. Set CLAUDE_CODE_OTEL_DIAG_STDERR=1 (v2.1.179+) in any environment where you care.
- OTEL_* variables are NOT passed to subprocesses — not to the Bash tool, not to hooks, not to MCP servers, not to language servers. A hook cannot report its own telemetry by inheritance. Only TRACEPARENT is forwarded (and only when tracing is on).
- `usage` on the result message excludes subagent tokens. If your kit fans out to subagents (which most do), summing `usage.input_tokens` across runs undercounts badly. Use `total_cost_usd` and `modelUsage` for whole-tree accounting.
- Per-step `output_tokens` on assistant messages is a PLACEHOLDER copied from the message_start event, and every message in a parallel-tool turn carries the same value. Deduplicate by message id for input/cache tokens; read output tokens only from the result message.
- `--max-budget-usd` is not a hard mid-request stop. Claude Code checks it between requests: it refuses new subagent spawns ('Budget limit reached'), kills background subagents, then ends with error_max_budget_usd. Expect to overshoot by roughly one response. On that subtype, `usage` omits the response that crossed the line while `total_cost_usd`/`modelUsage` include it — the two disagree by design.
- After a session crash the final result is error_during_execution with total_cost_usd, usage AND modelUsage possibly all ZEROED and stop_reason null. If you naively sum result costs you will silently undercount crashed runs. Recover from the previous turn's result, or by summing per-step assistant usage.
- In streaming input mode a `/clear`, `/reset` or `/new` resets both the running totals and the budget counter, and issues a new session_id. Summing every result message across a streaming call double-counts; you must take the last result before each reset plus the final result.
- A `--json-schema` run can return subtype `success` with `structured_output` absent. Checking only the subtype gives you a false green. Check both.
- `--bare` (recommended for CI) skips hooks, skills, plugins, MCP servers, auto memory and CLAUDE.md — meaning it disables the very kit you are trying to evaluate. Conversely, WITHOUT --bare a `claude -p` run executes a repo's .claude/settings.json hooks and connects its .mcp.json servers even in a folder you never trusted, because -p shows no trust dialog. Pick deliberately per experiment arm.
- The Agent tool was renamed from Task in v2.1.63 but the old name still appears in the `system:init` tools list and in `result.permission_denials[].tool_name`. Match both strings or your attribution silently misses subagents.
- stream_event (partial) messages always carry parent_tool_use_id = null; token-level deltas from subagents are never forwarded. Subagent attribution only works on complete messages.
- Third-party skill/plugin/MCP names are redacted to "custom"/"third-party" in telemetry unless OTEL_LOG_TOOL_DETAILS=1 — which also turns on file paths and full bash command strings. There is no way to get names without also getting command content, so per-skill cost attribution has a real privacy cost.
- Third-party monitoring guides drift from the docs. SigNoz's guide names a `claude_code.api_retries_exhausted` event that does not exist in the current Anthropic event list; retries are surfaced instead as a stream-json `system/api_retry` message. Verify every event name against your own collector.
- Grafana Cloud's integration requires OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE=cumulative; Claude Code defaults to delta. Omit it and your counters look broken in ways that look like a Claude Code bug.
- Held-out PR tests are a systematically optimistic oracle. METR found maintainers would reject roughly half of test-passing SWE-bench Verified patches, ~24 percentage points below the automated pass rate even after adjusting for a 68% golden-patch acceptance baseline. A repo-local golden set built the same way will overstate your kit's real usefulness by a similar margin. Budget for a human-review arm.
- Kotlin/Android golden tasks are expensive to make reproducible. The Firebender configs show the real work: pin the JDK (17.0.9-tem), pin every Android SDK package, and run a per-repo install_script that strips resolutionStrategy blocks, deletes proprietary plugins (Amazon app store publisher), forces JavaVersion.VERSION_17, and pins floating dependency versions. Without that, Gradle resolves differently on different days and your oracle is noise.
- Emulator dependence is the hard wall. Both existing Kotlin/Android benchmarks avoid it: Firebender's test_command is `./gradlew :AnkiDroid:testPlayDebugUnitTest` (JVM unit tests only), and JetBrains' set is dominated by non-Android libraries (ktlint 43 + detekt 28 of 105 tasks; Anki-Android contributes only 6). If your kit's value shows up mainly in Compose UI and instrumentation tests, no published methodology covers you.
- n=100 is not enough to detect a 5-point difference. Kotlin-bench explicitly reports that its top four models, spanning 39%-46%, 'show no statistically significant performance differences.' Anthropic's own advice to start with '20-50 tasks drawn from real failures' is for finding bugs directionally, not for proving a skill helps. Do not present a 5-point delta on 30 tasks as evidence.
- Ordinary A/B on agent benchmarks is brutally underpowered. Miller's formula needs ~969 paired questions for a 3-point difference at 80% power / 5% alpha; scaling by 1/delta^2 gives ~350 paired instances for 5 points under the same variance assumptions, and an unpaired binary comparison at p~0.45 needs >1,500 instances PER ARM. Paired design (identical task set, both arms) plus repeated runs per instance is the only affordable route.
- LLM judges are far more style-biased than position-biased. Measured effects: style bias (markdown vs plain text) 0.10-0.76; position bias <=0.04; verbosity bias is model-dependent and even flips sign (Gemini +0.24 to +0.44, Claude -0.12). Randomizing A/B order is cheap and worth doing, but it fixes the SMALL bias. Normalize formatting across arms or your judge is grading markdown.
- A blind comparator is not automatically unbiased about your kit. Anthropic's own comparator explicitly instructs 'DO NOT try to infer which skill produced which output' precisely because a judge that can tell which arm is the 'engineered' one will favor it. If your kit's output has a signature format (e.g. an OpenSpec header, Traditional Chinese section titles), the comparison is no longer blind.
- Skills help less the more realistic the setting. arXiv:2604.04323 found gains from a 34,000-skill library 'degrade consistently as settings become more realistic, with pass rates approaching no-skill baselines in the most challenging scenarios.' Expect your measured uplift in a controlled eval to overstate what the team actually gets.
- Deleting scaffolding that no longer helps can still be wrong. Anthropic's Managed Agents post deliberately does not prescribe what to delete — 'We're opinionated about the shape of these interfaces, not about what runs behind them.' The dead-weight finding was specific to context resets on Opus 4.5, discovered by re-running the same harness on a new model. It is an empirical procedure, not a license to delete on vibes.
- Two kinds of kit component expire differently. Anthropic's skill-creator post splits 'capability uplift' skills (things the base model cannot do consistently) from 'encoded preference' skills (org workflow sequencing). Only the first class becomes dead weight as models improve. A skill that encodes 'we use Koin annotation style, never Hilt' or 'never touch libs/app_resource/.../strings.xml' never expires from model progress — deleting it because a benchmark shows no uplift is a category error, since its job is constraint enforcement, not capability.
- Guard-rail hooks are unmeasurable by pass-rate benchmarks. A PreToolUse hook that blocks edits to a PM-owned strings.xml will never show up as a pass-rate delta on a golden task set that never touches that file. Measure hooks by their fire rate and block rate (claude_code.hook span: num_blocking, num_non_blocking_error; claude_code.tool_decision with source=hook), not by task success.
- Agent OS v3 retired implementation and orchestration because 'today's frontier models handle spec implementation well on their own', but KEPT standards, specs structure, product planning and profiles. The pattern to copy is not 'delete the framework' — it is 'delete the parts that duplicate a capability the base tool now has, keep the parts that encode facts only your org knows.'
- Claude Opus 5 delegates to subagents far more readily than earlier models, so an old kit tuned to force delegation can now cause runaway fan-out. With the claude_code system-prompt preset, Claude Code itself adds a line telling Opus 5 NOT to call the Agent tool unless asked; with a custom systemPrompt that line is absent. If your kit replaces the system prompt, you inherit the fan-out problem and must set CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH / CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS yourself.
- Tracing is beta: 'Span names and attributes may change between releases.' Do not build a permanent dashboard on claude_code.hook attributes yet.
- Managed settings can silently rip out your telemetry config. Setting OTEL_EXPORTER_OTLP_HEADERS in managed settings removes every developer-set endpoint variable at startup, generic and per-signal. The warning is only visible with `claude --debug`.

## OPEN
- I could not retrieve the official SDKResultMessage / SDKSystemMessage TypeScript blocks from code.claude.com (the typescript.md page truncates before them). The field list I report comes from a tessl mirror of npm @anthropic-ai/claude-agent-sdk 0.1.x cross-checked against prose in headless.md, agent-loop.md and cost-tracking.md. That mirror predates `stop_reason` (documented in agent-loop.md) and the `capabilities`/`plugin_errors`/`mcp_server_errors` init fields (documented in headless.md). Verify against your installed SDK's .d.ts before writing a parser: `node -e "console.log(require.resolve('@anthropic-ai/claude-agent-sdk'))"` then read sdkTypes.d.ts.
- Whether metrics/events differ by auth tier (Claude subscription vs API key vs Bedrock/Vertex/Foundry) is only partially documented. The single explicit statement I found is that claude_code.internal_error is not emitted on Amazon Bedrock, Google Cloud's Agent Platform or Microsoft Foundry, or when DISABLE_ERROR_REPORTING is set. organization.id / user.account_uuid / user.email are described as 'when authenticated', which implies they are absent under raw API-key auth, but the docs never say so directly.
- Whether claude_code.cost.usage is populated at all on Bedrock/Vertex (where Anthropic does not price the request) is not stated. Verify empirically before building cost dashboards on a Bedrock deployment.
- Exact Prometheus-normalized names for claude_code.active_time.total and claude_code.code_edit_tool.decision in Prometheus-only mode — I inferred them from the naming pattern in the ColeMurray dashboard but did not see them in a real /metrics dump.
- Whether hook execution appears anywhere in the METRICS or LOG signals (as opposed to the beta claude_code.hook span). If not, measuring hook value on a non-beta deployment requires instrumenting the hook script itself.
- Firebender Kotlin-bench's exact mining filters, flaky-test handling and pass@k methodology — the tutorials/collection.md and tutorials/evaluation.md files are referenced by the README but I could not fetch them (404 on the branch paths I tried). The repo tree confirms agent-bench/run_eval.py, agent-bench/run_cli_agent_eval.py, agent-bench/data/kotlin_bench.json and agent-bench/data/kotlin_bench_raw.json exist; read those directly.
- Neither Kotlin benchmark documents how it handles Gradle test flakiness (retry policy, quarantine list, or repeated-run consensus). This is the single biggest unknown for building an Android golden set.
- No published benchmark covers Android instrumentation/emulator tasks. Both existing Kotlin sets are JVM-unit-test only. Whether Compose UI or Maestro-style E2E tasks can be made reproducible enough for a golden set is genuinely unsolved as far as I can find.
- I found no published A/B of a Claude Code HOOK (as opposed to a skill) with reported n and effect size. The closest published component ablations are Anthropic's skill-creator blind comparator (methodology published, no aggregate numbers) and arXiv:2604.04323 (57.7% -> 65.5% on Terminal-Bench 2.0's 89 tasks, which is a skill-library ablation, not a single-component one).
- The ~350-paired-instance figure for detecting a 5-point difference is my arithmetic (n proportional to 1/delta^2 applied to Miller's published 969-questions-for-3-points example), not a number Miller states. It inherits that example's variance assumptions. Recompute with your own observed per-instance variance and correlation between arms before committing to a task count.
- arXiv:2604.23178 (judge bias) is single-author and I only read the abstract-level extraction; I did not verify its methodology. Treat the specific bias magnitudes as indicative, not authoritative.
- Anthropic's Managed Agents post is short on prescriptive deletion guidance — it gives the context-anxiety/dead-weight anecdote and an interface-decoupling principle, but no stated procedure. The runnable procedure in my summary is synthesized from that post plus the skill-creator blog's stated eval purposes plus Agent OS v3's retirement rationale; it is not a quote from Anthropic.
- Whether `claude --bare` can be combined with `--plugin-dir` in a way that loads exactly one kit component (the ideal A/B arm isolation) — the docs list --plugin-dir/--plugin-url as bare-mode-compatible loaders but I did not verify that a single skill can be isolated this way.

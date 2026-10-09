# Graph/DAG orchestration for coding agents in 2025–2026

## SUMMARY
Industry has converged on a two-layer story. Layer 1 is Anthropic's taxonomy from "Building Effective Agents": prompt chaining, routing, parallelization (sectioning + voting), orchestrator-workers, evaluator-optimizer, and autonomous agents — with the explicit caveat that "many patterns can be implemented in a few lines of code" and you should "consider adding complexity only when it demonstrably improves outcomes." Layer 2 is the frameworks that make those patterns durable: LangGraph (StateGraph nodes/edges, reducer-merged state, checkpointers with thread_id, `interrupt()`/`Command(resume=)` for HITL, subgraphs, and `Send` for dynamic map-reduce fan-out), AutoGen/AG2 GraphFlow (`DiGraphBuilder` with real fan-out/join, activation_group/activation_condition), CrewAI Flows (`@start`/`@listen`/`@router`/`and_`/`or_`), and OpenAI Agents SDK, which deliberately does NOT ship a graph — it offers handoffs plus an explicit doctrine of "orchestrating via code" (asyncio.gather, while-loop evaluator).

The durable-execution camp (Temporal, plus Prefect/Restate/Inngest/DBOS) argues the real primitive isn't a graph, it's crash-safe replay: workflows are deterministic orchestration, LLM/tool calls are retried activities. Temporal's `temporalio.contrib.openai_agents` plugin is the canonical example. Airflow shipped `apache-airflow-providers-common-ai` 0.1.0 (Apr 2026) with `@task.agent`, dragging agents into classic DAG land; Prefect markets the opposite ("orchestrate state machines, not static DAGs").

For coding agents specifically, Claude Code has its own primitives and they matter more than a generic graph library: subagents (`.claude/agents/*.md`, YAML frontmatter, up to 20 concurrent), git worktree isolation (`--worktree`, `isolation: worktree` frontmatter, `/batch` spawning 5–30 worktree-isolated subagents each opening a PR), agent teams (experimental, shared task list + mailbox), and dynamic workflows — a JS script with `agent()`/`pipeline()` globals, 16 concurrent agents, 1,000 agents/run cap, resumable. The key architectural insight is that a workflow "moves the plan into code" so intermediate results live in script variables rather than a context window.

The critique is real: Cognition's "Don't Build Multi-Agents" argues parallel subagents make conflicting implicit decisions; Anthropic's own multi-agent post says multi-agent is a poor fit for "most coding work" and costs ~15x chat tokens; a June 2026 controlled study found at most 1 of 6 multi-agent systems beat a matched single-agent baseline.

## KEY FACTS
### Anthropic's canonical taxonomy is 5 workflow patterns + 1 agent pattern
Prompt chaining, routing, parallelization (two variants: sectioning and voting), orchestrator-workers, evaluator-optimizer, and autonomous agents. Orchestrator-workers is explicitly motivated by coding: "Coding products making complex multi-file changes" where "the number of files that need to be changed and the nature of the change in each file likely depend on the task." Parallelization/voting example: "Multiple prompts reviewing code for vulnerabilities."
SRC: https://www.anthropic.com/research/building-effective-agents

### Anthropic's own framework guidance is anti-framework by default
"Many patterns can be implemented in a few lines of code." "If you do use a framework, ensure you understand the underlying code. Incorrect assumptions about what's under the hood are a common source of customer error." Frameworks "can obscure the underlying prompts and responses, making them harder to debug." General principle: "You should consider adding complexity only when it demonstrably improves outcomes."
SRC: https://www.anthropic.com/research/building-effective-agents

### LangGraph self-describes as low-level orchestration, not an agent abstraction
"LangGraph is a low-level orchestration framework and runtime for building, managing, and deploying long-running, stateful agents." It "does not abstract prompts or architecture." Five stated benefits: durable execution, human-in-the-loop, comprehensive memory, debugging (LangSmith), production-ready deployment. Install: `pip install -U langgraph` or `uv add langgraph`.
SRC: https://docs.langchain.com/oss/python/langgraph/overview

### The Send API is LangGraph's dynamic fan-out primitive (map-reduce)
`from langgraph.types import Send`; a conditional-edge function returns a list of `Send(node_name, custom_state)` objects. Used "where the exact edges are not known ahead of time." The sent state can differ from the graph's core state. Results merge back via reducers, typically `Annotated[list, operator.add]`.
SRC: https://docs.langchain.com/oss/python/langgraph/graph-api

### LangGraph nodes execute in Pregel-style supersteps; `defer=True` postpones a node until parallel branches complete
Fan-out is expressed as multiple edges from one node; fan-in as multiple edges into one node. `add_node(..., defer=True)` "postpones node execution until branches complete" — the barrier primitive. `Command(update=..., goto=...)` combines a state update and a routing decision in one node return.
SRC: https://docs.langchain.com/oss/python/langgraph/use-graph-api

### LangGraph checkpointers give you thread-scoped persistence, time travel, and three durability modes
Checkpointers: `InMemorySaver` (lost on restart), `SqliteSaver` (local dev), `PostgresSaver`/`AsyncPostgresSaver`. Compile with `builder.compile(checkpointer=checkpointer, store=store)`, run with `{"configurable": {"thread_id": "thread-1"}}` (keep thread_id under 255 chars). `StateSnapshot` fields: values, next, config, metadata, created_at, parent_config, tasks. Durability: `"exit"` (best perf, no mid-run recovery), `"async"` (balance), `"sync"` (highest durability). `DeltaChannel` stores only incremental deltas for append-heavy channels.
SRC: https://docs.langchain.com/oss/python/langgraph/checkpointers

### LangGraph time travel replays from a checkpoint_id; nodes after it re-execute
"Nodes before the checkpoint are skipped (their results are already saved). Nodes after the checkpoint re-execute, including any LLM calls, API requests, or interrupts." `update_state()` "creates a new checkpoint with the updated values — it does not modify the original checkpoint," and values pass through reducers.
SRC: https://docs.langchain.com/oss/python/langgraph/checkpointers

### LangGraph HITL: on resume, the whole node re-runs from the top
`interrupt(value)` pauses and persists; `Command(resume=value)` resumes with the same thread_id and the resume value becomes `interrupt()`'s return. Critical rule: "When resumed, the entire node re-runs from the beginning (code before `interrupt()` runs again)." Therefore "Make side effects before `interrupt()` idempotent." Never wrap `interrupt()` in bare try/except (it catches the pause exception). Keep interrupt calls in consistent order; avoid conditional/looping interrupts inside one node — use conditional edges. Static breakpoints: `compile(interrupt_before=[...], interrupt_after=[...])`.
SRC: https://docs.langchain.com/oss/python/langgraph/interrupts

### LangGraph subgraphs have two modes depending on schema overlap
If parent and subgraph share at least one state key, pass the compiled subgraph directly: `builder.add_node("node_1", subgraph)`. If schemas differ, invoke it inside a node function and transform state manually. "The subgraph returns values from its output_schema, and each returned key is written back into the parent state using the parent's channel reducers."
SRC: https://docs.langchain.com/oss/python/langgraph/use-subgraphs

### LangGraph's Functional API (@entrypoint/@task) is the no-graph alternative
`@entrypoint` marks the workflow start and manages execution/interrupts; `@task` is a discrete unit of work. "When you call a task, it returns immediately with a future object" — parallelism is plain Python future resolution, no graph. Differences vs Graph API: no explicit State/reducers, state scoped to functions; Graph API checkpoints after supersteps, Functional API saves task results into existing checkpoints; Functional API has no visualization.
SRC: https://docs.langchain.com/oss/python/langgraph/functional-api

### LangGraph nodes accept retry_policy (and tasks too)
`StateGraph.add_node(..., retry_policy=RetryPolicy(max_attempts=3, retry_on=ConnectionError))`. RetryPolicy params include initial_interval, backoff_factor, max_interval, max_attempts, jitter, retry_on. Both `add_node` and `@task` accept a RetryPolicy or a sequence of them.
SRC: https://reference.langchain.com/python/langgraph/types/RetryPolicy

### Claude Code subagents are markdown files with YAML frontmatter, resolved by a 5-level precedence chain
Precedence: managed settings (1) > `--agents` CLI JSON (2) > `.claude/agents/` (3) > `~/.claude/agents/` (4) > plugin `agents/` (5). Required frontmatter: `name` (lowercase+hyphens, no colons), `description`. Optional: tools, disallowedTools, model, permissionMode, maxTurns, skills, mcpServers, hooks, memory, background, effort, `isolation: worktree`, color, initialPrompt.
SRC: https://code.claude.com/docs/en/sub-agents

### Claude Code caps concurrent subagents at 20 by default
"Default 20 subagents running simultaneously (configurable via `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` environment variable). Sessions with ultracode active are exempt." Subagents receive their own system prompt + the Agent tool's prompt + CLAUDE.md + git status + preloaded skills; they do NOT receive conversation history, output style, or auto memory. As of v2.1.198 subagents run in the background by default.
SRC: https://code.claude.com/docs/en/sub-agents

### Claude Code dynamic workflows are JavaScript scripts with `agent()` and `pipeline()` globals
"A dynamic workflow is a JavaScript script that orchestrates subagents at scale." Saved to `.claude/workflows/` (project) or `~/.claude/workflows/` (personal), or a plugin's `workflows/` dir (namespaced as `/plugin:name`). "The body is plain JavaScript with top-level `await`. `agent()` spawns one subagent and `pipeline()` runs one per item in a list." `agent()` resolves to `null` if stopped or on unrecoverable API error, so `.filter(Boolean)` is idiomatic. Saved workflows accept an `args` global.
SRC: https://code.claude.com/docs/en/workflows

### Dynamic workflow runtime limits: 16 concurrent agents, 1,000 agents per run, no imports, no filesystem access from the script
Constraints table: "No mid-run user input"; "No direct filesystem or shell access from the workflow itself"; "No module loading: a script that contains `import()` fails before the run starts"; "Up to 16 concurrent agents, fewer when Claude Code has fewer CPUs available"; "1,000 agents total per run." Requires Claude Code v2.1.154+.
SRC: https://code.claude.com/docs/en/workflows

### The core argument for a workflow over turn-by-turn orchestration is where the plan and the intermediate results live
Comparison table: subagents/skills keep intermediate results in "Claude's context window"; agent teams in "A shared task list"; workflows in "Script variables." Scale: subagents "A few delegated tasks per turn" vs workflows "Dozens to hundreds of agents per run." "A workflow script holds the loop, the branching, and the intermediate results itself, so Claude's context holds only the final answer."
SRC: https://code.claude.com/docs/en/workflows

### Fan-out prompt-cache staggering is a real cost mechanism in Claude Code workflows
"When a fan-out starts several matching agents at once, Claude Code holds all but the first until the first agent's response begins, then releases the held agents together so their first requests read the shared prefix instead of each processing it uncached." Capped by `CLAUDE_CODE_WORKFLOW_PREFIX_STAGGER_MS`, default `5000`; set to `0` to disable. Agents share a cache prefix when model, effort, agent type, tools, output schema and working directory match.
SRC: https://code.claude.com/docs/en/workflows

### Stopping a fan-out mid-run is expensive because replay follows start order
"An agent that was still running when you stopped isn't saved... Replay follows the order agents started. Cached results stop at the first agent that didn't finish, and every agent that started after that one runs again, even if it completed." Worked example: A,B,C,D started in order, stop while B runs → on resume A cached, B/C/D all re-run. "A workflow that fans work out across many small agents therefore preserves more progress than one long agent." Resume works only within the same Claude Code session.
SRC: https://code.claude.com/docs/en/workflows

### Claude Code flags runaway workflows at 25 agents or 1.5M projected tokens
"When a workflow schedules more than 25 agents, or its projected token total passes 1.5 million, its progress line... shows a `Large workflow` warning." Size guideline setting (`workflowSizeGuideline`, default `medium`): unrestricted / small (<5 agents) / medium (<15) / large (<50). The warning is advisory, not a cap.
SRC: https://code.claude.com/docs/en/workflows

### Claude Code's six reusable dynamic-workflow patterns are named explicitly by the team that built it
classify-and-act; fan-out-and-synthesize ("Split up a task into many smaller steps, run an agent on each step and then synthesize those results"); adversarial verification; generate-and-filter; tournament ("Spawn N agents that each attempt the same task using different approaches"); loop-until-done. The failure modes they address: "agentic laziness," "self-preferential bias," and "goal drift" ("Gradual loss of fidelity to the original objective across many turns").
SRC: https://claude.com/blog/a-harness-for-every-task-dynamic-workflows-in-claude-code

### Git worktree isolation is enforced by the harness, not just convention
Claude Code applies four checks while a session is isolated: blocks Edit/Write/NotebookEdit targeting the main checkout; blocks Bash/PowerShell/Monitor commands whose cwd resolves to the main checkout; blocks git redirects via `git -C`, `--git-dir`, `GIT_DIR`, `GIT_WORK_TREE`, or `cd` into main; and blocks command shapes it can't statically trace (brace expansion, heredocs with unquoted delimiters) — "You can't turn this check off." Same enforcement covers every subagent spawned from the isolated session.
SRC: https://code.claude.com/docs/en/worktrees

### `--worktree` creates `.claude/worktrees/<name>/` on branch `worktree-<name>`; base branch is configurable
`claude --worktree feature-auth`. `worktree.baseRef` accepts `"fresh"` (default: repo default branch on the remote) or `"head"` (current local HEAD, "Use this when isolating subagents that need to operate on in-progress work"). `.worktreeinclude` (gitignore syntax) copies gitignored files like `.env` into each new worktree. `claude --worktree "#1234"` branches from a PR into `.claude/worktrees/pr-<number>`.
SRC: https://code.claude.com/docs/en/worktrees

### Subagent worktrees are locked while running and swept afterward
"While an agent is running, Claude runs `git worktree lock` on its worktree so that concurrent cleanup cannot remove it." Temporary worktrees are removed automatically when the subagent finishes without changes; ones with changes survive until a periodic sweep older than `cleanupPeriodDays`. "The sweep skips a worktree that still holds work: changed or untracked files, or unpushed commits. It never removes worktrees you create with `--worktree`."
SRC: https://code.claude.com/docs/en/worktrees

### `/batch` is a bundled skill that is literally fan-out over worktrees with one PR per unit
"Orchestrate large-scale changes across a codebase in parallel. Researches the codebase, decomposes the work into 5 to 30 independent units, and presents a plan. Once approved, spawns one background subagent per unit in an isolated git worktree. Each subagent implements its unit, runs tests, and opens a pull request. Requires a git repository. Example: `/batch migrate src/ from Solid to React`"
SRC: https://code.claude.com/docs/en/commands

### Anthropic's four parallel modes and their decision axes
Subagents (delegated workers in one session), agent view (background sessions, `claude agents`, research preview), agent teams (coordinated sessions with shared task list, experimental/off by default), dynamic workflows (a script the runtime executes). Decision axes: who coordinates the work, do the workers need to talk to each other, do the tasks touch the same files (→ worktrees). "Running several sessions or subagents at once multiplies token usage."
SRC: https://code.claude.com/docs/en/agents

### Agent teams: shared task list with dependencies + file-locked claiming + per-agent JSON mailboxes
Enable with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. Mailbox: `~/.claude/teams/{team-name}/inboxes/{agent-name}.json`; team config `~/.claude/teams/{team-name}/config.json`; task list `~/.claude/tasks/{team-name}/`. Team name = `session-` + first 8 chars of session ID. "Task claiming uses file locking to prevent race conditions." "a pending task with unresolved dependencies cannot be claimed until those dependencies are completed." Hooks `TeammateIdle`, `TaskCreated`, `TaskCompleted` exit code 2 to block and send feedback.
SRC: https://code.claude.com/docs/en/agent-teams

### Anthropic's own sizing advice for parallel agents: start at 3–5, 5–6 tasks per teammate
"Start with 3-5 teammates for most workflows... If you have 15 independent tasks, 3 teammates is a good starting point... Three focused teammates often outperform five scattered ones." "Having 5-6 tasks per teammate keeps everyone productive." Limits listed: token costs scale linearly, coordination overhead increases, diminishing returns. "Agent teams don't isolate teammates in worktrees, so partition the work so each teammate owns a different set of files." "Two teammates editing the same file leads to overwrites."
SRC: https://code.claude.com/docs/en/agent-teams

### Measured token multipliers for multi-agent
Anthropic: "agents typically use about 4× more tokens than chat interactions" and "multi-agent systems use about 15× more tokens than chats." "Token usage alone explains 80% of performance variance in web-browsing evaluations." Separately, Claude Code docs state agent teams use "approximately 7x more tokens than standard sessions when teammates run in plan mode."
SRC: https://www.anthropic.com/engineering/multi-agent-research-system

### Anthropic's multi-agent research system beat single-agent Opus 4 by 90.2% — and they say it's a poor fit for coding
Orchestrator-worker with Claude Opus 4 lead + Claude Sonnet 4 subagents "outperformed single-agent Claude Opus 4 by 90.2% on our internal research eval." Parallel tool calling cut research time up to 90%. Effective for: breadth-first queries with independent directions, heavy parallelization, information exceeding one context window. Poor fit for: "Domains requiring shared context across agents, tasks with many interdependencies, most coding work, real-time coordination demands."
SRC: https://www.anthropic.com/engineering/multi-agent-research-system

### Subagents are a context-compression device: 10k+ tokens explored, 1–2k returned
"Each subagent might explore extensively, using tens of thousands of tokens or more, but returns only a condensed, distilled summary of its work (often 1,000-2,000 tokens)." Anthropic's three long-horizon techniques: compaction (best for "tasks requiring extensive back-and-forth"), structured note-taking ("iterative development with clear milestones"), sub-agent architectures ("complex research benefiting from parallel exploration").
SRC: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

### Cognition's counterargument: two principles that condemn naive parallel subagents
"Principle 1: Share context, and share full agent traces, not just individual messages." "Principle 2: Actions carry implicit decisions, and conflicting decisions carry bad results." Flappy Bird example: one subagent builds a Super Mario Bros background, another builds an unsuitable bird sprite, and the final agent must combine "these two miscommunications." "Subagent 1 and subagent 2 cannot see what the other was doing and so their work ends up being inconsistent." Recommendation: single-threaded linear agent, plus an LLM-based context-compression model for genuinely long tasks.
SRC: https://cognition.com/blog/dont-build-multi-agents

### A June 2026 controlled study found multi-agent systems mostly lose to a matched single agent
"Do More Agents Help? Controlled and Protocol-Aligned Evaluation of LLM Agent Workflows" (Fu, Fang, Shao, Zheng, Zhu, Luo, Lin; submitted 2026-06-04). BenchAgent normalized execution/logging across single-agent, fixed MAS, and evolving MAS on ten reasoning/coding/tool-use benchmarks with GPT-4.1. "at most one of six tested MAS exceeds the matched single-agent anchor on benchmark-balanced average accuracy." The five that lost trailed by "2.56-11.29 points" at higher compute cost.
SRC: https://arxiv.org/abs/2606.05670

### 12-Factor Agents Factor 8: own your control flow so you can break out of the loop
Custom control flow lets you interrupt "between the moment of tool selection and the moment of tool invocation." Enables "summarization or caching of tool call results," "LLM-as-judge on structured output," "logging, tracing, and metrics," and "durable sleep / pause / 'wait for event'." "certain types of tool calls may be reason to break out of the loop and wait for a response from a human or another long-running task like a training pipeline."
SRC: https://raw.githubusercontent.com/humanlayer/12-factor-agents/main/content/factor-08-own-your-control-flow.md

### LangChain's rebuttal: the hard part is context, and a loop doesn't give you persistence/streaming/HITL/observability
Harrison Chase: reliability comes down to "making sure the LLM has the appropriate context at each step. This includes both controlling the exact content that goes into the LM, as well as running the appropriate steps to generate relevant content." "most 'agentic systems' are a combination of workflows and agents." LangGraph is positioned as "an orchestration framework (with both declarative and imperative APIs), with a series of agent abstractions built on top." Production features a bare loop lacks: persistence/memory, token+step+event streaming, HITL, LangSmith observability, durable workflows with configurable retries.
SRC: https://www.langchain.com/blog/how-to-think-about-agent-frameworks

### OpenAI's Agents SDK deliberately offers handoffs instead of a graph, and documents code-orchestration as first-class
Handoffs become tools named `transfer_to_<agent_name>`; `handoff()` takes agent, tool_name_override, tool_description_override, on_handoff, input_type; `agents.extensions.handoff_filters` has prebuilt input filters; `RECOMMENDED_PROMPT_PREFIX` lives in `agents.extensions.handoff_prompt`. Handoffs "maintain a single run" — input guardrails apply only initially, output guardrails only to the final agent. The multi-agent doc contrasts "Allowing the LLM to make decisions" with "orchestrating via code: determining the flow of agents via your code" which is "more deterministic and predictable, in terms of speed, cost and performance," listing four patterns: structured-output classification routing, agent chaining, a `while`-loop evaluator, and "Running multiple agents in parallel, e.g. via Python primitives like `asyncio.gather`."
SRC: https://openai.github.io/openai-agents-python/multi_agent/

### AutoGen/AG2 GraphFlow is a genuine DiGraph team abstraction with activation groups
`DiGraphBuilder` methods: `add_node(agent)`, `add_edge(src, dst)`, `add_edge(..., condition=lambda msg: ...)`, `add_edge(..., activation_group="name", activation_condition="all"|"any")`, `set_entry_point(agent)`, `build()`, `get_participants()`. `GraphFlow(participants=..., graph=..., termination_condition=MaxMessageTermination(10))`, run with `flow.run_stream(task=...)`. `MessageFilterAgent` + `MessageFilterConfig(per_source=[PerSourceFilter(source=..., position="last", count=1)])` controls what each node sees.
SRC: https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/graph-flow.html

### CrewAI Flows use event decorators rather than an explicit graph object
`@start()` (multiple unconditional starts execute in parallel), `@listen(method)`, `@router(method)` returning a route label, `and_(m1, m2)` (all complete), `or_(m1, m2)` (any completes). Typed state via `class MyFlow(Flow[MyState])` with a Pydantic BaseModel; unstructured dict state also supported; both get a UUID. Run with `flow.kickoff()`, visualize with `flow.plot()`. Guidance: "Use Flows to orchestrate multiple Crews or tasks with conditional logic and state management. Use Crews for tightly-coupled agent teams."
SRC: https://docs.crewai.com/en/concepts/flows

### Temporal splits agents into deterministic workflows + retryable activities, with an official OpenAI Agents SDK plugin
`OpenAIAgentsPlugin(model_params=ModelActivityParameters(start_to_close_timeout=timedelta(seconds=30)))` is passed to `Client.connect(..., plugins=[...])`. Inside `@workflow.defn`, `Runner.run(agent, prompt)` executes normally while tools are wrapped: `openai_agents.workflow.activity_as_tool(get_weather, start_to_close_timeout=timedelta(seconds=10))`, which "automatically generates OpenAI-compatible tool schemas from Activity function signatures."
SRC: https://docs.temporal.io/ai-cookbook/openai-agents-sdk-python

### Airflow shipped first-class agent operators in April 2026
`apache-airflow-providers-common-ai` 0.1.0 released Tue, Apr 14, 2026; requires Apache Airflow 3.0+. Operators/decorators: `@task.llm`/`LLMOperator`, `@task.agent`/`AgentOperator`, `@task.llm_branch`, `@task.llm_sql`, `@task.llm_file_analysis`, `@task.llm_schema_compare`. Toolsets: `SQLToolset`, `HookToolset`, `MCPToolset`, `DataFusionToolset`.
SRC: https://airflow.apache.org/blog/common-ai-provider/

### Prefect explicitly markets itself as the anti-DAG orchestrator for agents
Tagline: "The only orchestrator built for AI agents." "Agents don't follow predetermined paths"; "Orchestrate state machines, not static DAGs." Claims: native Python control flow (while loops until success, runtime branching on LLM output) without precompiled graphs; type-safe human-in-the-loop via auto-generated UI forms; automatic result caching to avoid redundant LLM calls on retry; native Pydantic AI integration.
SRC: https://www.prefect.io/solutions/agents

### Dagger's container-use gives each agent a container + its own git branch, via MCP
"an open-source MCP server that works as a CLI tool with Claude Code, Cursor, and other MCP-compatible agents. Powered by Dagger." Install: `brew install dagger/tap/container-use` or `curl -fsSL https://raw.githubusercontent.com/dagger/container-use/main/install.sh | bash`. Wire up: `claude mcp add container-use -- container-use stdio`, plus optional `curl https://raw.githubusercontent.com/dagger/container-use/main/rules/agent.md >> CLAUDE.md`. "Each agent gets a fresh container in its own git branch - run multiple agents without conflicts, experiment safely, discard failures instantly." Review with `git checkout <branch_name>`. CLI alias: `cu`.
SRC: https://raw.githubusercontent.com/dagger/container-use/main/README.md

### Agent SDK caps subagent depth, concurrency, and dollar spend
`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` (default 3; set 1 to stop nesting), `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` (default 20; returns `Concurrent subagent limit reached`), and `maxBudgetUsd`/`max_budget_usd` (no default; ends the query with `error_max_budget_usd`, refuses new subagents, stops running background ones). TS `env` REPLACES the subprocess environment (spread `process.env`); Python `env` MERGES. Requires TS SDK v0.3.219 / Python SDK v0.2.127+.
SRC: https://code.claude.com/docs/en/agent-sdk/subagents

### Claude Opus 5 delegates to subagents more readily, so limits matter more
"Claude Opus 5 delegates to subagents more readily than earlier models, so the depth, concurrency, and spend limits matter most on queries that run Opus 5." With the `claude_code` system-prompt preset and an Opus 5 model, Claude Code adds a line telling Claude not to call the Agent tool unless asked; with a custom prompt that line is absent and you must add the delegation instruction yourself.
SRC: https://code.claude.com/docs/en/agent-sdk/subagents

### The `Workflow` tool is exposed through the TypeScript Agent SDK
"The `Workflow` tool is available in the TypeScript Agent SDK v0.3.149 and later. Include `Workflow` in `allowedTools` to auto-approve workflow runs." Orchestration-relevant `query()` Options: `agents` (Record<string, AgentDefinition>), `agent`, `maxBudgetUsd`, `forkSession`, `resume`, `resumeSessionAt`, `continue`, `forwardSubagentText`, `agentProgressSummaries`.
SRC: https://code.claude.com/docs/en/agent-sdk/typescript

### Anthropic's own recommended cheap fan-out is a bash for-loop over `claude -p`, not a graph
Three-step recipe in the official best-practices guide: (1) have Claude write the task list to a file, (2) loop `claude -p` over it with `--allowedTools` scoping, (3) "Refine your prompt based on what goes wrong with the first 2-3 files, then run on the full set." Also: `claude -p "<your prompt>" --output-format json | your_command` for pipeline integration, and `claude --permission-mode auto -p "fix all lint errors"` for unattended runs.
SRC: https://code.claude.com/docs/en/best-practices

### Generator-critic in Claude Code is a documented Writer/Reviewer two-session pattern, plus an adversarial subagent step
"A fresh context improves code review since Claude won't be biased toward code it just wrote." Session A implements, Session B reviews with a fresh context, feedback flows back. The subagent variant: "a reviewer running in a fresh subagent context sees only the diff and the criteria you give it, not the reasoning that produced the change." Warning: "A reviewer prompted to find gaps will usually report some, even when the work is sound... Chasing every finding leads to over-engineering."
SRC: https://code.claude.com/docs/en/best-practices

### Claude Code GitHub Action runs the same agent loop in CI, and cost control is via --max-turns + concurrency
`anthropics/claude-code-action@v1`. Two modes auto-detected: interactive (no `prompt` input → waits for `@claude`) and automation (`prompt` input given → runs on any event including `schedule`). Key inputs: prompt, claude_args, anthropic_api_key / claude_code_oauth_token, plugin_marketplaces, plugins, settings, trigger_phrase. `claude_args` passes any CLI flag: `--max-turns 5 --model claude-sonnet-5 --allowedTools "..."`. Cost guidance includes "Set `--max-turns` in `claude_args` to limit iterations" and "Use GitHub's concurrency controls to limit parallel runs."
SRC: https://code.claude.com/docs/en/github-actions

### Claude Code's own loop is three phases, not a DAG
"When you give Claude a task, it works through three phases: gather context, take action, and verify results. These phases blend together." "Claude decides what each step requires based on what it learned from the previous step, chaining dozens of actions together and course-correcting along the way." Claude Code is described as "the agentic harness around Claude: it provides the tools, context management, and execution environment."
SRC: https://code.claude.com/docs/en/how-claude-code-works

### Claude Code enterprise cost baseline for sizing parallel work
"the average cost is around $13 per developer per active day and $150-250 per developer per month, with costs remaining below $30 per active day for 90% of users." Agent-team cost advice: use Sonnet for teammates, keep teams small ("token usage is roughly proportional to team size"), keep spawn prompts focused, shut teammates down when done.
SRC: https://code.claude.com/docs/en/costs

## EXAMPLES
### Minimal LangGraph graph: state, node, edges, compile
FILE: Typically a module like `graph.py` / `src/agent/graph.py`; LangGraph Platform expects `langgraph.json` pointing at `./src/agent/graph.py:graph`
```
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict, Annotated
import operator

class State(TypedDict):
    messages: Annotated[list, operator.add]  # reducer appends items
    value: str

def node(state: State):
    return {"key": "value"}

builder = StateGraph(State)
builder.add_node("node_name", node)
builder.add_edge(START, "node_name")
builder.add_edge("node_name", END)
graph = builder.compile()
```
SRC: https://docs.langchain.com/oss/python/langgraph/use-graph-api

### LangGraph orchestrator-worker fan-out/fan-in with the Send API (the canonical map-reduce)
FILE: Single module; the `["llm_call"]` third arg to add_conditional_edges is the path map needed for graph drawing
```
from typing import Annotated, List
from typing_extensions import TypedDict
import operator
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from langchain.messages import SystemMessage, HumanMessage

class Section(BaseModel):
    name: str = Field(description="Name for this section of the report.")
    description: str = Field(description="Brief overview of topics to cover in this section.")

class Sections(BaseModel):
    sections: List[Section] = Field(description="Sections of the report.")

planner = llm.with_structured_output(Sections)

class State(TypedDict):
    topic: str
    sections: list[Section]
    completed_sections: Annotated[list, operator.add]   # <- the fan-in reducer
    final_report: str

class WorkerState(TypedDict):
    section: Section
    completed_sections: Annotated[list, operator.add]

def orchestrator(state: State):
    report_sections = planner.invoke([
        SystemMessage(content="Generate a plan for the report."),
        HumanMessage(content=f"Topic: {state['topic']}"),
    ])
    return {"sections": report_sections.sections}

def llm_call(state: WorkerState):
    section = llm.invoke([
        SystemMessage(content="Write a report section. Include no preamble. Use markdown."),
        HumanMessage(content=f"Name: {state['section'].name}\nDescription: {state['section'].description}"),
    ])
    return {"completed_sections": [section.content]}

def synthesizer(state: State):
    return {"final_report": "\n\n---\n\n".join(state["completed_sections"])}

def assign_workers(state: State):
    """Assign a worker to each section in the plan"""
    return [Send("llm_call", {"section": s}) for s in state["sections"]]

b = StateGraph(State)
b.add_node("orchestrator", orchestrator)
b.add_node("llm_call", llm_call)
b.add_node("synthesizer", synthesizer)
b.add_edge(START, "orchestrator")
b.add_conditional_edges("orchestrator", assign_workers, ["llm_call"])
b.add_edge("llm_call", "synthesizer")
b.add_edge("synthesizer", END)
orchestrator_worker = b.compile()
```
SRC: https://docs.langchain.com/oss/python/langgraph/workflows-agents

### LangGraph static parallel fan-out/fan-in (no Send — known branches at build time)
FILE: n/a
```
class State(TypedDict):
    topic: str
    joke: str
    story: str
    poem: str
    combined_output: str

parallel_builder = StateGraph(State)
parallel_builder.add_node("call_llm_1", call_llm_1)
parallel_builder.add_node("call_llm_2", call_llm_2)
parallel_builder.add_node("call_llm_3", call_llm_3)
parallel_builder.add_node("aggregator", aggregator)

parallel_builder.add_edge(START, "call_llm_1")
parallel_builder.add_edge(START, "call_llm_2")
parallel_builder.add_edge(START, "call_llm_3")
parallel_builder.add_edge("call_llm_1", "aggregator")
parallel_builder.add_edge("call_llm_2", "aggregator")
parallel_builder.add_edge("call_llm_3", "aggregator")
parallel_builder.add_edge("aggregator", END)
parallel_workflow = parallel_builder.compile()
```
SRC: https://docs.langchain.com/oss/python/langgraph/workflows-agents

### LangGraph evaluator-optimizer (generator-critic) loop via conditional edge back to the generator
FILE: n/a — note there is NO built-in max-iteration guard; add a counter in state
```
class Feedback(BaseModel):
    grade: Literal["funny", "not funny"] = Field(description="Decide if the joke is funny or not.")
    feedback: str = Field(description="If not funny, provide feedback on improvement.")

evaluator = llm.with_structured_output(Feedback)

def llm_call_generator(state: State):
    if state.get("feedback"):
        msg = llm.invoke(f"Write a joke about {state['topic']} considering: {state['feedback']}")
    else:
        msg = llm.invoke(f"Write a joke about {state['topic']}")
    return {"joke": msg.content}

def llm_call_evaluator(state: State):
    grade = evaluator.invoke(f"Grade the joke {state['joke']}")
    return {"funny_or_not": grade.grade, "feedback": grade.feedback}

def route_joke(state: State):
    if state["funny_or_not"] == "funny":
        return "Accepted"
    elif state["funny_or_not"] == "not funny":
        return "Rejected + Feedback"

ob = StateGraph(State)
ob.add_node("llm_call_generator", llm_call_generator)
ob.add_node("llm_call_evaluator", llm_call_evaluator)
ob.add_edge(START, "llm_call_generator")
ob.add_edge("llm_call_generator", "llm_call_evaluator")
ob.add_conditional_edges(
    "llm_call_evaluator", route_joke,
    {"Accepted": END, "Rejected + Feedback": "llm_call_generator"},
)
optimizer_workflow = ob.compile()
```
SRC: https://docs.langchain.com/oss/python/langgraph/workflows-agents

### LangGraph checkpointer + thread_id + durability mode
FILE: Checkpointer choice: InMemorySaver (dev), SqliteSaver (local file), PostgresSaver/AsyncPostgresSaver (prod)
```
graph = builder.compile(checkpointer=checkpointer, store=store)

result = graph.invoke(
    {"messages": [{"role": "user", "content": "Hi, my name is Bob."}]},
    {"configurable": {"thread_id": "thread-1"}},
)

# inspect / time travel
graph.get_state({"configurable": {"thread_id": "1"}})
graph.get_state({"configurable": {"thread_id": "1",
                                  "checkpoint_id": "1ef663ba-28fe-6528-8002-5a559208592c"}})
list(graph.get_state_history({"configurable": {"thread_id": "1"}}))  # newest-first

# durability: "exit" (fastest) | "async" (balanced) | "sync" (safest)
graph.stream({"input": "test"}, durability="sync")
```
SRC: https://docs.langchain.com/oss/python/langgraph/checkpointers

### LangGraph static breakpoints for human-in-the-loop debugging
FILE: n/a — dynamic HITL uses `interrupt(payload)` inside the node and `Command(resume=value)` to continue on the same thread_id
```
graph = builder.compile(
    interrupt_before=["node_a"],
    interrupt_after=["node_b"],
    checkpointer=checkpointer
)
```
SRC: https://docs.langchain.com/oss/python/langgraph/interrupts

### LangGraph subgraph — shared-key form vs different-schema form
FILE: n/a
```
# (a) shared state key: pass the compiled subgraph directly as a node
subgraph_builder = StateGraph(State)
subgraph_builder.add_node(subgraph_node_1)
subgraph_builder.add_edge(START, "subgraph_node_1")
subgraph = subgraph_builder.compile()

builder = StateGraph(State)
builder.add_node("node_1", subgraph)   # <- compiled graph as a node
builder.add_edge(START, "node_1")
graph = builder.compile()

# (b) different schemas: invoke inside a node and translate state
class SubgraphState(TypedDict):
    bar: str
class State(TypedDict):
    foo: str

def call_subgraph(state: State):
    subgraph_output = subgraph.invoke({"bar": state["foo"]})
    return {"foo": subgraph_output["bar"]}

builder = StateGraph(State)
builder.add_node("node_1", call_subgraph)
```
SRC: https://docs.langchain.com/oss/python/langgraph/use-subgraphs

### LangGraph Functional API — durability without a graph
FILE: n/a
```
@entrypoint(checkpointer=checkpointer)
async def my_workflow(some_input: int) -> int:
    return await slow_computation(some_input)

# @task returns a future immediately; fan-out is plain Python:
#   futures = [do_work(x) for x in items]
#   results = [await f for f in futures]
```
SRC: https://docs.langchain.com/oss/python/langgraph/functional-api

### Claude Code custom subagent file (the unit of fan-out in a coding agent)
FILE: .claude/agents/<anything>.md (project) or ~/.claude/agents/<anything>.md (user). Filename is arbitrary; the `name` field is the identifier.
```
---
name: api-developer
description: Implement API endpoints following team conventions. Use proactively for new endpoint implementation.
tools: Read, Write, Edit, Bash, Grep, Glob
model: sonnet
skills:
  - api-conventions
  - error-handling-patterns
memory: project
permissionMode: acceptEdits
---

You are an expert API developer. Implement endpoints following established patterns and conventions.

When implementing:
1. Review existing endpoints for patterns
2. Follow the preloaded API conventions
3. Apply error handling patterns
4. Write unit tests
5. Update API documentation
```
SRC: https://code.claude.com/docs/en/sub-agents

### Claude Code subagent pinned to its own git worktree (parallel edits without collisions)
FILE: .claude/agents/refactorer.md
```
---
name: refactorer
description: Applies mechanical refactors across many files
isolation: worktree
---

Apply the requested refactor across every affected file, then run the tests
and report the results.
```
SRC: https://code.claude.com/docs/en/worktrees

### Claude Code dynamic workflow script — the DAG-as-code that a coding agent actually runs
FILE: .claude/workflows/<name>.js (project, shared via repo) or ~/.claude/workflows/<name>.js (personal); plugin workflows go in the plugin's workflows/ dir and run as /plugin-name:workflow-name. Every run also writes its script under ~/.claude/projects/<session>/
```
export const meta = {
  name: 'audit-routes',
  description: 'Audit every route handler for missing auth checks',
}

const found = await agent('List every .ts file under src/routes/.', {
  schema: { type: 'object', required: ['files'], properties: { files: { type: 'array', items: { type: 'string' } } } },
})

const audits = await pipeline(found.files, file =>
  agent(`Audit ${file} for missing authentication checks.`, { label: file }),
)

return audits.filter(Boolean)
```
SRC: https://code.claude.com/docs/en/workflows

### Claude Code worktree settings — branch from in-progress work instead of origin/HEAD
FILE: .claude/settings.json or ~/.claude/settings.json. Pair with a `.worktreeinclude` at repo root (gitignore syntax) listing gitignored files to copy in:
.env
.env.local
config/secrets.json
```
{
  "worktree": {
    "baseRef": "head"
  }
}
```
SRC: https://code.claude.com/docs/en/worktrees

### Manual git worktree fan-out (the framework-free version everyone actually starts with)
FILE: Add `.claude/worktrees/` to .gitignore
```
# one worktree per agent
git worktree add ../project-feature-a -b feature-a
git worktree add ../project-bugfix fix-issue-456
cd ../project-feature-a && claude

# or let Claude Code do it
claude --worktree feature-auth       # -> .claude/worktrees/feature-auth on branch worktree-feature-auth
claude --worktree "#1234"            # -> .claude/worktrees/pr-1234 from origin pull/1234/head

git worktree list
git worktree remove ../project-feature-a   # add --force if dirty
git worktree unlock <path>                 # if a killed session left a lock
```
SRC: https://code.claude.com/docs/en/worktrees

### Anthropic's own bash fan-out over files — no orchestration framework at all
FILE: scripts/migrate.sh; `--output-format stream-json --verbose` emits one JSON object per line starting with an init event
```
# 1. have Claude write the task list:
#    "list all 2,000 Python files that need migrating and save the list to files.txt"

# 2. loop
for file in $(cat files.txt); do
  claude -p "Migrate $file from React to Vue. Return OK or FAIL." \
    --allowedTools "Edit,Bash(git commit *)"
done

# 3. pipeline integration
claude -p "<your prompt>" --output-format json | your_command

# unattended, with a safety classifier
claude --permission-mode auto -p "fix all lint errors"
```
SRC: https://code.claude.com/docs/en/best-practices

### Agent SDK: define parallel specialist subagents programmatically (TypeScript)
FILE: Any TS/JS module. AgentDefinition fields: description*, prompt*, tools, disallowedTools, model, skills, memory, mcpServers, initialPrompt, maxTurns, background, effort, permissionMode
```
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Review the authentication module for security issues",
  options: {
    allowedTools: ["Read", "Grep", "Glob", "Agent"],   // Agent must be allowed to auto-approve spawning
    agents: {
      "code-reviewer": {
        description: "Expert code review specialist. Use for quality, security, and maintainability reviews.",
        prompt: `You are a code review specialist...`,
        tools: ["Read", "Grep", "Glob"],
        model: "sonnet"
      },
      "test-runner": {
        description: "Runs and analyzes test suites.",
        prompt: `You are a test execution specialist...`,
        tools: ["Bash", "Read", "Grep"]
      }
    }
  }
})) {
  if ("result" in message) console.log(message.result);
}
```
SRC: https://code.claude.com/docs/en/agent-sdk/subagents

### Agent SDK: bound a fan-out's depth, concurrency and dollar spend
FILE: Python equivalent uses ClaudeAgentOptions(env={...}, max_budget_usd=5.0) and MERGES env
```
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Audit every service in this repo for unhandled promise rejections",
  options: {
    allowedTools: ["Read", "Grep", "Glob", "Agent"],
    // TS env REPLACES the subprocess env, so spread process.env to keep PATH
    env: {
      ...process.env,
      CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH: "1",
      CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS: "5",
    },
    maxBudgetUsd: 5,
  },
})) {
  if (message.type === "result") {
    console.log(`${message.subtype}: $${message.total_cost_usd}`);
  }
}
// subtypes: "success" | "error_max_budget_usd"; concurrency hits emit a tool_result
// block carrying "Concurrent subagent limit reached"
```
SRC: https://code.claude.com/docs/en/agent-sdk/subagents

### AutoGen/AG2 GraphFlow: real fan-out then join
FILE: n/a. Conditional loop form: builder.add_edge(reviewer, summarizer, condition=lambda msg: "APPROVE" in msg.to_model_text()) and builder.add_edge(reviewer, generator, condition=lambda msg: "APPROVE" not in msg.to_model_text()); builder.set_entry_point(generator)
```
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import DiGraphBuilder, GraphFlow
from autogen_ext.models.openai import OpenAIChatCompletionClient

client = OpenAIChatCompletionClient(model="gpt-4.1-nano")
writer = AssistantAgent("writer", model_client=client, system_message="Draft a short paragraph on climate change.")
editor1 = AssistantAgent("editor1", model_client=client, system_message="Edit the paragraph for grammar.")
editor2 = AssistantAgent("editor2", model_client=client, system_message="Edit the paragraph for style.")
final_reviewer = AssistantAgent("final_reviewer", model_client=client, system_message="Consolidate the grammar and style edits into a final version.")

builder = DiGraphBuilder()
builder.add_node(writer).add_node(editor1).add_node(editor2).add_node(final_reviewer)
builder.add_edge(writer, editor1)
builder.add_edge(writer, editor2)
builder.add_edge(editor1, final_reviewer)
builder.add_edge(editor2, final_reviewer)

graph = builder.build()
flow = GraphFlow(participants=builder.get_participants(), graph=graph)
```
SRC: https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/graph-flow.html

### CrewAI Flows: decorators instead of a graph object
FILE: src/<project>/main.py in a `crewai create flow` scaffold
```
from crewai.flow.flow import Flow, start, listen, router, and_, or_
from pydantic import BaseModel

class MyState(BaseModel):
    counter: int = 0

class MyFlow(Flow[MyState]):
    @start()
    def initialize(self):
        ...

    @listen(initialize)          # two @listen on the same upstream run in parallel
    def branch_a(self, out): ...

    @listen(initialize)
    def branch_b(self, out): ...

    @listen(and_(branch_a, branch_b))   # barrier / join
    def join(self, out): ...

    @router(join)                        # returns a label matched by @listen("label")
    def decide_path(self):
        return "route_label"

flow = MyFlow()
flow.kickoff()
flow.plot()
```
SRC: https://docs.crewai.com/en/concepts/flows

### Temporal + OpenAI Agents SDK: durable agent loop, tools as retryable activities
FILE: Conventional Temporal layout: workflows.py, activities.py, run_worker.py
```
from datetime import timedelta
from agents import Agent, Runner
from temporalio import workflow
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.contrib import openai_agents
from temporalio.contrib.openai_agents import ModelActivityParameters, OpenAIAgentsPlugin

client = await Client.connect(
    "localhost:7233",
    plugins=[OpenAIAgentsPlugin(
        model_params=ModelActivityParameters(start_to_close_timeout=timedelta(seconds=30))
    )],
)

@workflow.defn
class HelloWorldAgent:
    @workflow.run
    async def run(self, prompt: str) -> str:
        agent = Agent(
            name="Hello World Agent",
            instructions="You are a helpful assistant...",
            tools=[
                openai_agents.workflow.activity_as_tool(get_weather, start_to_close_timeout=timedelta(seconds=10)),
                openai_agents.workflow.activity_as_tool(calculate_circle_area, start_to_close_timeout=timedelta(seconds=10)),
            ],
        )
        result = await Runner.run(agent, prompt)
        return result.final_output

worker = Worker(
    client,
    task_queue="hello-world-openai-agent-task-queue",
    workflows=[HelloWorldAgent],
    activities=[get_weather, calculate_circle_area],
)
```
SRC: https://docs.temporal.io/ai-cookbook/openai-agents-sdk-python

### Airflow 3: an agent as a DAG task
FILE: dags/sql_analyst.py; install with `pip install 'apache-airflow-providers-common-ai'` (0.1.0, 2026-04-14, needs Airflow 3.0+)
```
from airflow.providers.common.ai.toolsets.sql import SQLToolset
from airflow.providers.common.compat.sdk import dag, task

@dag
def sql_analyst():
    @task.agent(
        llm_conn_id="my_openai_conn",
        system_prompt="You are a SQL analyst. Use tools to answer questions with data.",
        toolsets=[
            SQLToolset(
                db_conn_id="postgres_default",
                allowed_tables=["customers", "orders"],
                max_rows=20,
            )
        ],
    )
    def analyze(question: str):
        return f"Answer this question about our data: {question}"

    analyze("What are the top 5 customers by order count?")

sql_analyst()
```
SRC: https://airflow.apache.org/blog/common-ai-provider/

### Dagger container-use: container + branch per agent, wired in as an MCP server
FILE: CLAUDE.md gets the agent rules appended; `cu` is the CLI alias for `container-use`
```
brew install dagger/tap/container-use
# or
curl -fsSL https://raw.githubusercontent.com/dagger/container-use/main/install.sh | bash

claude mcp add container-use -- container-use stdio
curl https://raw.githubusercontent.com/dagger/container-use/main/rules/agent.md >> CLAUDE.md

# review any agent's work with plain git
git checkout <branch_name>
```
SRC: https://raw.githubusercontent.com/dagger/container-use/main/README.md

### Claude Code GitHub Action: agent-in-CI, with a skill as the prompt
FILE: .github/workflows/claude-code-review.yml; the @claude interactive variant lives in .github/workflows/claude.yml. Use `claude_args: "--max-turns 5 --model claude-sonnet-5"` plus GitHub `concurrency:` to bound cost.
```
name: Code Review
on:
  pull_request:
    types: [opened, synchronize, ready_for_review, reopened]
jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: read
      issues: read
      id-token: write
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 1
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          plugin_marketplaces: "https://github.com/anthropics/claude-code.git"
          plugins: "code-review@claude-code-plugins"
          prompt: "/code-review:code-review --comment ${{ github.repository }}/pull/${{ github.event.pull_request.number }}"
          claude_args: '--allowedTools "mcp__github_inline_comment__create_inline_comment"'
```
SRC: https://code.claude.com/docs/en/github-actions

### OpenAI Agents SDK handoffs (the non-graph delegation primitive)
FILE: n/a. Code-orchestration alternatives the SDK documents: structured-output classification routing, agent chaining, a while-loop evaluator, and asyncio.gather for parallel agents. Runnable versions live in examples/agent_patterns/ in the repo.
```
from agents import Agent, handoff
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents.extensions import handoff_filters

triage = Agent(
    name="triage",
    instructions=f"{RECOMMENDED_PROMPT_PREFIX} Route the user to the right specialist.",
    handoffs=[
        billing_agent,                       # bare Agent works
        handoff(                             # or wrap for control
            agent=refund_agent,
            on_handoff=log_handoff,
            input_type=RefundReason,
            input_filter=handoff_filters.remove_all_tools,
        ),
    ],
)
# SDK exposes each as a tool named transfer_to_<agent_name>
```
SRC: https://openai.github.io/openai-agents-python/handoffs/

### Claude Code agent-teams enablement + quality gates
FILE: ~/.claude/settings.json. Runtime state: ~/.claude/teams/{team}/config.json, ~/.claude/teams/{team}/inboxes/{agent}.json, ~/.claude/tasks/{team}/
```
// settings.json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  },
  "teammateMode": "auto"    // "in-process" (default) | "auto" | "tmux" | "iterm2"
}

// Hooks that gate teammate work (exit code 2 = block + send feedback):
//   TeammateIdle   -> keep the teammate working
//   TaskCreated    -> prevent creation
//   TaskCompleted  -> prevent completion
```
SRC: https://code.claude.com/docs/en/agent-teams

## GOTCHAS
- Multi-agent is explicitly a bad fit for most coding work, per Anthropic's own multi-agent post: poor fit for "Domains requiring shared context across agents, tasks with many interdependencies, most coding work, real-time coordination demands." The 90.2% win was on a *research* eval, not SWE.
- ~15x token cost. Anthropic measured multi-agent systems at "about 15× more tokens than chats" and single agents at ~4x. Claude Code separately reports agent teams at "approximately 7x more tokens than standard sessions when teammates run in plan mode." Any DAG that fans out is buying latency with tokens.
- Cognition's failure mode is real and specific: parallel subagents make *implicit* decisions that conflict, and merging their outputs is worse than never splitting. Sharing only the original task prompt is insufficient — "multi-turn conversations and tool calls create nuanced context that gets lost across agents."
- Controlled evidence is unflattering. arXiv 2606.05670 (June 2026) found "at most one of six tested MAS exceeds the matched single-agent anchor," with the losers trailing 2.56–11.29 points at higher compute. Beware benchmark comparisons that don't equalize thinking/token budget.
- LangGraph `interrupt()` re-runs the entire node on resume. Any side effect before the interrupt executes twice unless it's idempotent. Also: never wrap `interrupt()` in a bare try/except (it swallows the pause exception), and don't put conditional or looping interrupts inside a single node.
- LangGraph checkpoints are between nodes, not inside them. A node that internally runs a long loop loses all intermediate work on crash. This pushes toward smaller nodes — the same lesson as Claude Code's "fans work out across many small agents therefore preserves more progress than one long agent."
- LangGraph parallel writes to the same state key without a reducer are an error/overwrite. `Annotated[list, operator.add]` (or a custom reducer) is mandatory on any key multiple branches write. Forgetting this is the #1 map-reduce bug.
- Claude Code workflow resume is order-dependent and can be very expensive: cached results stop at the first agent that didn't finish, and *every agent that started after it re-runs even if it completed*. Stopping mid-fan-out can throw away most of a run.
- Claude Code workflows can't take mid-run user input and can't touch the filesystem or shell from the script itself, and `import()` fails the run before it starts. Anything needing a library must happen inside an agent's task, and stage sign-off requires splitting into separate workflows.
- Concurrency ceilings are lower than people assume: 16 concurrent agents per dynamic workflow (fewer on CPU-limited containers), 1,000 agents total per run, and 20 concurrent subagents by default (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`). Exceeding the subagent cap returns `Concurrent subagent limit reached`.
- Prompt-cache thrash in fan-out: without staggering, N simultaneous agents each process the shared tools+system prefix uncached. Claude Code holds all but the first for up to `CLAUDE_CODE_WORKFLOW_PREFIX_STAGGER_MS` (default 5000ms). Agents only share the prefix if model, effort, agent type, tools, output schema and working directory all match — so a heterogeneous fan-out gets no cache benefit.
- Agent teams do NOT isolate teammates in worktrees. "Two teammates editing the same file leads to overwrites." You must partition file ownership manually. Subagents and sessions can get worktrees; teammates can't.
- Agent teams are experimental and off by default, with real limitations: `/resume` and `/rewind` don't restore in-process teammates; teammates sometimes fail to mark tasks complete, blocking dependents; shutdown is slow; no nested teams; lead can't be transferred; permission mode is fixed at spawn.
- Turning agent teams on silently changes ordinary delegation: "a subagent that Claude names launches as a teammate", and teammates report only an idle notification without their output — "An orchestration flow that waits on subagent results can stall."
- Non-interactive `claude -p --worktree` runs never clean up: no exit prompt, and the creation lock stays until a later stale-lock sweep. You'll accumulate locked worktrees; recover with `git worktree unlock` then `git worktree remove --force`.
- Worktrees are fresh checkouts — no `.env`, no node_modules, no venv. Without a `.worktreeinclude` and a setup step, every parallel agent starts in a broken environment. Also, default `worktree.baseRef` is `"fresh"` (origin default branch), so agents branch off main, not your in-progress work, unless you set `"head"`.
- Claude Code blocks shell constructs it can't statically trace inside a worktree — brace expansion, heredocs with unquoted delimiters — even when no git is involved, and this check cannot be disabled. Scripts that work in the main checkout can fail inside isolation.
- Evaluator-optimizer loops have no built-in iteration cap in the LangGraph example; you must add a counter to state. Separately, Anthropic warns the reviewer side over-reports: "A reviewer prompted to find gaps will usually report some, even when the work is sound... Chasing every finding leads to over-engineering."
- Framework opacity is Anthropic's stated top customer-error source: "Incorrect assumptions about what's under the hood are a common source of customer error," and frameworks "can obscure the underlying prompts and responses, making them harder to debug."
- Opus 5 over-delegates. Docs state it "delegates to subagents more readily than earlier models," so a prompt that was cheap on Sonnet can spawn a tree of agents. With a custom systemPrompt the harness's anti-delegation line is absent entirely — you must add it and set hard limits.
- Cost blowups are quiet: Claude Code only warns at >25 scheduled agents or >1.5M projected tokens, and the warning "is advisory: it doesn't pause or limit the run." Ultracode sessions suppress the warning entirely.
- Temporal-style durability imposes determinism on the orchestration layer: LLM calls and tool invocations must live in activities, not the workflow body, or replay breaks. This is a real rewrite, not a wrapper.
- A graph is over-engineering when the branches aren't known statically and the work is one linear investigation. Both the OpenAI Agents SDK docs and the 12-factor-agents guidance point the other way: own a plain `while` loop so you can break between tool *selection* and tool *invocation* for approval, caching, judging, tracing, or durable sleep — capabilities a fixed DAG doesn't naturally give you either.

## OPEN
- No public head-to-head benchmark of Claude Code dynamic workflows vs. LangGraph vs. a plain bash `claude -p` loop on the same coding migration task, measured on tokens, wall-clock, and merge-conflict rate. The blog claims (Bun's Zig-to-Rust rewrite) carry no numbers.
- Claude Code's dynamic-workflow runtime is closed: the exact signatures/options of the `agent()` and `pipeline()` globals aren't documented publicly beyond the one saved-script example; the docs point to "the Workflow tool entry in the Agent SDK reference" but that section wasn't retrievable at the URLs fetched.
- Whether `isolation: worktree` subagents plus a merge step actually reduce net human review time versus sequential edits — no published data on how often the N parallel branches conflict, or how much of the token spend is wasted on branches that get discarded.
- Whether the tournament/best-of-N pattern ("Spawn N agents that each attempt the same task using different approaches") is cost-effective for code specifically. Anthropic names it as a pattern but publishes no pass-rate-vs-N curve.
- How LangGraph's `Send` fan-out interacts with `interrupt()` — i.e. whether one worker interrupting cleanly pauses a superstep and how the resume replays sibling workers. Docs cover each feature separately.
- LangGraph node-level `CachePolicy` (TTL, key function, `InMemoryCache`) exists in the API surface but wasn't confirmed from a primary docs page in this pass; verify against reference.langchain.com before relying on it.
- Whether the June 2026 "Do More Agents Help?" result holds for orchestrator-worker on genuinely parallelizable file-level work, or only for the reasoning/tool-use benchmarks it used — its coding tasks weren't broken out.
- Practical ceilings on parallel worktrees per developer (RAM, test-runner contention, port collisions) are widely quoted in blogs (4–8) but I found no primary source; treat as folklore until measured on your own build.
- Whether Prefect's "state machines, not static DAGs" positioning translates into measurable reliability gains for agents versus LangGraph's checkpointer model — the page is marketing, not benchmarks.

# Claude Code harness primitives — the official 2025-2026 surface for building a custom agent harness (settings, hooks, subagents, skills/commands, plugins, output styles, MCP, headless mode, Agent SDK, CLAUDE.md) plus Anthropic's engineering guidance on agent/harness design

## SUMMARY
**Docs moved.** Every `docs.claude.com/en/docs/claude-code/*` URL now 301s to `code.claude.com/docs/en/*`. Appending `.md` to any page returns raw markdown — use that for verbatim extraction. The full page index is `https://code.claude.com/docs/llms.txt`.

**Configuration is a 5-layer stack.** Managed policy > CLI args > `.claude/settings.local.json` > `.claude/settings.json` > `~/.claude/settings.json`. `permissions` holds `allow`/`deny`/`ask`/`additionalDirectories`/`defaultMode`/`disableBypassPermissionsMode`/`disableAutoMode`. Rules are `Tool` or `Tool(specifier)`, evaluated **deny → ask → allow, first match wins, specificity irrelevant** — so a broad deny cannot carry allowlist exceptions. Bash rules glob with `*`; a *space* before `*` enforces a word boundary (`Bash(ls *)` matches `ls -la` not `lsof`). Claude Code is shell-operator aware, so `Bash(safe *)` never authorizes `safe && evil`. New in 2026: parameter matching (`Agent(model:opus)`, `Bash(run_in_background:true)`) for deny/ask only, and tool-name globs (`mcp__*`).

**Hooks are the deterministic control plane and are far larger than the classic nine.** ~30 events now exist (Setup, UserPromptExpansion, PermissionRequest, PermissionDenied, PostToolUseFailure, PostToolBatch, SubagentStart, StopFailure, TaskCreated/TaskCompleted, ConfigChange, InstructionsLoaded, CwdChanged, FileChanged, WorktreeCreate/Remove, PostCompact, MessageDisplay, Elicitation…). Five handler types: `command`, `http`, `mcp_tool`, `prompt`, `agent`. Contract: stdin JSON → stdout JSON + exit code. Exit 0 = success (stdout-as-context only for UserPromptSubmit/UserPromptExpansion/SessionStart); exit 2 = block, with per-event semantics. Output fields: `continue`, `stopReason`, `systemMessage`, `additionalContext`, `terminalSequence`, plus a per-event `hookSpecificOutput` carrying `permissionDecision` (`allow|deny|escalate`), `permissionDecisionReason`, `updatedInput`, `updatedPrompt`, `retry`. Critically: **hook `allow` does not bypass deny/ask rules**, but a hook exiting 2 preempts allow rules.

**Custom commands merged into skills.** `.claude/commands/x.md` and `.claude/skills/x/SKILL.md` both yield `/x`; the skill wins on conflict. Skill frontmatter is ~20 fields (`description`, `when_to_use`, `allowed-tools`, `disable-model-invocation`, `user-invocable`, `context: fork`, `agent`, `model`, `effort`, `paths`, `hooks`, `arguments`). Substitutions: `$ARGUMENTS`, `$0`/`$1`, `$name`, `${CLAUDE_SKILL_DIR}`, `${CLAUDE_PROJECT_DIR}`, `${CLAUDE_PLUGIN_ROOT}`. Dynamic context injection via `` !`cmd` `` runs before Claude sees the body. Only 6 fields are portable outside Claude Code (Agent Skills spec).

**Headless** is `claude -p` with `--output-format text|json|stream-json`, `--json-schema` for structured output, `--allowedTools`, `--permission-mode`, `--max-turns`, `--max-budget-usd`, `--resume`, `--append-system-prompt`, and the new `--bare` (skips all auto-discovery; recommended for CI and slated to become the `-p` default). The `system/init` stream event is the harness's introspection point (`plugins`, `plugin_errors`, `mcp_servers`, `mcp_server_errors`, `capabilities`).

**Anthropic's own guidance converges on**: separate generation from evaluation (self-assessment is unreliable), pass state through structured files not conversation, use hard verification thresholds, treat context as a finite resource with just-in-time retrieval, and *delete harness scaffolding as models improve* — the "Managed Agents" post argues harness assumptions go stale within one model generation.

## KEY FACTS
### Claude Code docs relocated from docs.claude.com to code.claude.com with 301 redirects; appending .md returns raw markdown
https://docs.claude.com/en/docs/claude-code/settings returns 301 → https://code.claude.com/docs/en/settings. Every page is also available as raw markdown by appending .md (e.g. /docs/en/hooks.md). The machine-readable page index lives at https://code.claude.com/docs/llms.txt and lists all page URLs grouped by topic.
SRC: https://code.claude.com/docs/llms.txt

### Settings files: five scopes with a fixed precedence order
User `~/.claude/settings.json`; Project `.claude/settings.json` (git-shared); Local `.claude/settings.local.json` (gitignored); Managed (`/Library/Application Support/ClaudeCode/managed-settings.json` on macOS, `/etc/claude-code/managed-settings.json` on Linux/WSL, `C:\Program Files\ClaudeCode\managed-settings.json` on Windows, plus a `managed-settings.d/` drop-in dir merged alphabetically); and `~/.claude.json` for OAuth session, user/local-scope MCP servers, per-project trust state and caches. Precedence high→low: Managed > CLI args > Local > Project > User. Claude Code adds `**/.claude/settings.local.json` to the global git excludes file when it writes that file itself.
SRC: https://code.claude.com/docs/en/settings

### Permission rules are evaluated deny → ask → allow, first match wins, and specificity does not change the order
Verbatim: "Rules are evaluated in order: deny, then ask, then allow. The first match in that order determines the outcome, and rule specificity doesn't change the order." Consequence: "A broad deny rule like `Bash(aws *)` blocks every matching call, including calls that also match a narrower allow rule like `Bash(aws s3 ls)`, so a deny rule can't carry allowlist exceptions."
SRC: https://code.claude.com/docs/en/permissions

### Bash permission wildcards: the space before `*` creates a word boundary
`Bash(ls *)` matches `ls -la` but NOT `lsof`; `Bash(ls*)` (no space) matches both. `Bash(*)` == `Bash`. `:*` is an equivalent trailing-wildcard form (`Bash(ls:*)`), recognized only at pattern end. A single `*` spans spaces, so `Bash(git * main)` matches `git push origin main`.
SRC: https://code.claude.com/docs/en/permissions

### Claude Code is shell-operator aware; compound commands must match each subcommand independently
Recognized separators: `&&`, `||`, `;`, `|`, `|&`, `&`, and newlines. A rule like `Bash(safe-cmd *)` does not authorize `safe-cmd && other-cmd`. Wrappers stripped before matching: `timeout`, `time`, `nice`, `nohup`, `stdbuf`, shell builtins `command`/`builtin`, zsh `noglob`, and bare `xargs`. NOT stripped: `direnv exec`, `devbox run`, `mise exec`, `npx`, `docker exec` — so `Bash(devbox run *)` would allow `devbox run rm -rf .`.
SRC: https://code.claude.com/docs/en/permissions

### Permission rules can match arbitrary top-level tool input parameters — deny/ask only
`Tool(param:value)` syntax: `Agent(model:opus)`, `Agent(isolation:worktree)`, `Bash(run_in_background:true)`. `*` wildcard supported in the value. Allow rules deliberately cannot use this form. Primary content fields are excluded and ignored with a startup warning: `command` (Bash/PowerShell), `file_path` (Read/Edit/Write), `path` (Grep/Glob), `notebook_path`, `url` (WebFetch).
SRC: https://code.claude.com/docs/en/permissions

### Six permission modes
`default` (aka `manual`), `acceptEdits`, `plan`, `auto` (background classifier), `dontAsk` (auto-deny anything not pre-approved), `bypassPermissions`. Set session start mode via `permissions.defaultMode`. `bypassPermissions` still prompts for explicit `ask` rules, org-set connector `ask` tools, MCP `requiresUserInteraction` tools, and `rm -rf /` / `rm -rf ~` as a circuit breaker. Lock down with `permissions.disableBypassPermissionsMode` / `permissions.disableAutoMode` set to `"disable"`.
SRC: https://code.claude.com/docs/en/permissions

### The hook event surface in 2026 is ~30 events, not the classic nine
Full list: SessionStart, Setup, UserPromptSubmit, UserPromptExpansion, PreToolUse, PermissionRequest, PermissionDenied, PostToolUse, PostToolUseFailure, PostToolBatch, Notification, MessageDisplay, SubagentStart, SubagentStop, TaskCreated, TaskCompleted, Stop, StopFailure, TeammateIdle, InstructionsLoaded, ConfigChange, CwdChanged, DirectoryAdded, FileChanged, WorktreeCreate, WorktreeRemove, PreCompact, PostCompact, Elicitation, ElicitationResult, SessionEnd.
SRC: https://code.claude.com/docs/en/plugins-reference

### Five hook handler types, not just shell commands
`command` (exec form with `args` = no shell; shell form without `args`), `http` (with `url`, `headers`, `allowedEnvVars`), `mcp_tool` (`server`, `tool`, `input` with `${tool_input.x}` templating), `prompt` (LLM-evaluated, `model` field), `agent` (subagent-evaluated). Common fields on all: `type`, `if` (e.g. `"Bash(git *)"`), `timeout`, `statusMessage`, `once`. Default timeouts: 600s for command/http/mcp_tool, 30s for prompt, 60s for agent; UserPromptSubmit drops to 30s, MessageDisplay to 10s, SessionEnd shares a 1.5s budget.
SRC: https://code.claude.com/docs/en/hooks

### Hook exit-code contract
Exit 0 = success; stdout starting with `{` is parsed as JSON, otherwise plain text. Plain-text stdout is shown to Claude ONLY for UserPromptSubmit, UserPromptExpansion, and SessionStart; for all other events it goes to the debug log. Exit 2 = blocking error, and blocks even if the JSON says `permissionDecision: "allow"`. Other exit codes = non-blocking error unless valid JSON with a decision field is present. Timeout = hook canceled, output discarded, no decision rendered (a timed-out PreToolUse hook does NOT block).
SRC: https://code.claude.com/docs/en/hooks

### Exit-code-2 semantics differ per event
PreToolUse → blocks the tool call. UserPromptSubmit → blocks the prompt AND erases the input. UserPromptExpansion → blocks expansion. Stop → prevents stopping, continues the conversation. SubagentStop → prevents subagent stopping. PostToolBatch → stops the agentic loop before the next model call. PreCompact → blocks compaction. ConfigChange → blocks the change (except policy_settings). TaskCreated → rolls back task creation. WorktreeCreate → any non-zero exit fails creation. PostToolUse/PostToolUseFailure → non-blocking, shows stderr to Claude. Notification, SessionStart, SessionEnd, SubagentStart, PermissionRequest, PermissionDenied, InstructionsLoaded → cannot block.
SRC: https://code.claude.com/docs/en/hooks

### `additionalContext` only works on a specific subset of events, capped at 10,000 characters
Verbatim: "Only works on `UserPromptSubmit`, `UserPromptExpansion`, `SessionStart`, `PostToolUse`, `PostToolUseFailure`, `Stop`, `SubagentStop`, and `Notification`. Max 10,000 characters." `systemMessage` is also capped at 10,000 chars. `suppressOutput` is accepted but has no effect — hook stdout is never shown in the transcript regardless.
SRC: https://code.claude.com/docs/en/hooks

### Hook decisions do not bypass permission rules; but a blocking hook preempts allow rules
Verbatim: "Claude Code evaluates deny and ask rules regardless of what a PreToolUse hook returns: a matching deny rule blocks the call, and a matching ask rule still prompts even when the hook returned `"allow"` or `"ask"`." Conversely: "A hook that exits with code 2 stops the tool call before permission rules are evaluated, so the block applies even when an allow rule would otherwise let the call proceed." The recommended pattern for allow-all-but-a-few: put `"Bash"` in allow and register a PreToolUse hook that rejects the exceptions.
SRC: https://code.claude.com/docs/en/permissions

### Hook matcher grammar has three tiers
`"*"`, `""`, or omitted → match all. Strings of only letters/digits/`_`/`-`/spaces/`,`/`|` → exact string or `|`/`,`-separated list (e.g. `Edit|Write`). Anything else → JavaScript RegExp, unanchored (e.g. `^Notebook`, `mcp__memory__.*`). MCP tool format is `mcp__<server>__<tool>`; plugin-bundled servers are `mcp__plugin_<plugin-name>_<server-name>__<tool>` and a matcher against the bare server key never fires for them.
SRC: https://code.claude.com/docs/en/hooks

### Hooks can be declared in six places, including skill and subagent frontmatter
`~/.claude/settings.json`, `.claude/settings.json`, `.claude/settings.local.json`, managed policy settings, plugin `hooks/hooks.json`, skill frontmatter (persists for the rest of the session), and subagent frontmatter (only while the subagent runs). Kill switch: `disableAllHooks: true` (also disables the status line). Path placeholders available in hook commands: `${CLAUDE_PROJECT_DIR}`, `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}`, `${user_config.*}` (exec form only).
SRC: https://code.claude.com/docs/en/hooks

### Subagent frontmatter is ~17 fields and lives in `.claude/agents/` or `~/.claude/agents/` (scanned recursively)
Fields: `name`, `description` (both required), `tools`, `disallowedTools`, `model` (sonnet/opus/haiku/fable/inherit/full ID), `permissionMode`, `maxTurns`, `skills`, `mcpServers` (named or inline stdio defs), `hooks`, `memory` (user|project|local), `background`, `effort`, `isolation: worktree`, `color`, `initialPrompt`. Precedence high→low: managed settings > `--agents` CLI JSON > `.claude/agents/` > `~/.claude/agents/` > plugin `agents/`. Model resolution order: `CLAUDE_CODE_SUBAGENT_MODEL` env > per-invocation param > frontmatter > main conversation model.
SRC: https://code.claude.com/docs/en/sub-agents

### Subagents can restrict which subagents they may spawn, and nesting is depth-limited
`tools: Agent(worker, researcher), Read, Bash` restricts spawnable subagent types. Nested subagents go up to 3 layers by default, tunable with `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`. Non-fork subagents start with only the delegation prompt (not conversation history) but DO load the full CLAUDE.md hierarchy and git status. The main conversation's auto memory is NOT loaded into subagents; a fork is the exception since it inherits parent conversation + system prompt.
SRC: https://code.claude.com/docs/en/sub-agents

### Custom slash commands have been merged into skills
Verbatim: "A file at `.claude/commands/deploy.md` and a skill at `.claude/skills/deploy/SKILL.md` both create `/deploy` and work the same way. Your existing `.claude/commands/` files keep working." If both exist, the skill takes precedence. Command files support the same frontmatter as skills except `name` and `paths`, which are ignored. Skill name resolution: enterprise > personal > project; plugin skills are namespaced `plugin-name:skill-name` and cannot conflict.
SRC: https://code.claude.com/docs/en/skills

### Skill string substitutions include indexed and named arguments plus five path variables
`$ARGUMENTS` (full string; if absent from body, args are appended as `ARGUMENTS: <value>`), `$ARGUMENTS[N]`, `$N` shorthand (`$0` = first arg), `$name` from the `arguments:` frontmatter list, `${CLAUDE_SESSION_ID}`, `${CLAUDE_EFFORT}`, `${CLAUDE_SKILL_DIR}`, `${CLAUDE_PROJECT_DIR}`, `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}`. Indexed args use shell-style quoting. Escape a literal `$` before a digit with a backslash (`\$1.00`). `${CLAUDE_SKILL_DIR}` and `${CLAUDE_PROJECT_DIR}` substitute in BOTH the body and Bash rules in `allowed-tools`, which is how a skill can run a bundled script prompt-free.
SRC: https://code.claude.com/docs/en/skills

### Only 6 skill frontmatter fields are portable outside Claude Code
The Agent Skills spec (agentskills.io) allows `name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`. claude.ai uploads, the Skills API, and `package_skill.py` from github.com/anthropics/skills hard-error on anything else: `Unexpected key(s) in SKILL.md frontmatter: argument-hint. Allowed properties are: allowed-tools, compatibility, description, license, metadata, name`. The combined `description` + `when_to_use` text is truncated at 1,536 characters in the skill listing.
SRC: https://code.claude.com/docs/en/skills

### Skills load from nested `.claude/skills/` directories lazily, and support live change detection
Project skills load from `.claude/skills/` in the start dir and every parent up to the repo root. Nested skills below the start dir are NOT loaded at startup — they load the first time Claude reads/edits a file in that subdirectory, then stay for the session. Name clashes produce a directory-qualified name like `/apps/web:deploy`. `--add-dir` and `/add-dir` are an explicit exception to the config-vs-file-access rule: they DO load `.claude/skills/` and `.claude/commands/` from added dirs (but `permissions.additionalDirectories` does not). Claude Code file-watches skill dirs and picks up SKILL.md text edits without restart.
SRC: https://code.claude.com/docs/en/skills

### Plugin components must live at plugin root, not inside `.claude-plugin/`
Verbatim: "Components must be at plugin root, NOT inside `.claude-plugin/`. Only `plugin.json` belongs in `.claude-plugin/`." Directory layout: `.claude-plugin/plugin.json`, `skills/<name>/SKILL.md`, `commands/*.md` (flat), `agents/*.md`, `hooks/hooks.json`, `.mcp.json`, `.lsp.json`, `output-styles/`, `workflows/`, `bin/` (added to PATH), `scripts/`, plus experimental `themes/` and `monitors/`. Path field semantics differ: `skills` ADDS to the default scan; `commands`, `agents`, `workflows`, `outputStyles`, `themes`, `monitors` REPLACE defaults.
SRC: https://code.claude.com/docs/en/plugins-reference

### Plugin agents do not support hooks, mcpServers, or permissionMode
Supported plugin-agent fields: `name`, `description`, `model`, `effort`, `maxTurns`, `tools`, `disallowedTools`, `skills`, `memory`, `background`, `isolation`. Explicitly noted: "`hooks`, `mcpServers`, and `permissionMode` not supported for plugin agents" — a divergence from `.claude/agents/` frontmatter.
SRC: https://code.claude.com/docs/en/plugins-reference

### Plugin `userConfig` values reach components three ways, but are deliberately blocked from shell-form hook commands
Available as `${user_config.KEY}` in skill/agent content, and as `CLAUDE_PLUGIN_OPTION_<KEY>` environment variables. "**NOT** in shell-form hook commands (security restriction)" — exec form only. userConfig option types: `string|number|boolean|directory|file`, with `title`, `description`, `sensitive`, `required`, `default`, `multiple`, `min`, `max`.
SRC: https://code.claude.com/docs/en/plugins-reference

### Marketplace `.claude-plugin/marketplace.json` requires only name, owner, plugins; supports 7 plugin source types
Sources: relative path (`"./plugins/x"`, must start with `./`, resolved from marketplace ROOT not `.claude-plugin/`), `github` (`repo`, `ref?`, `sha?`), `url` (git URL), `git-subdir` (`url`, `path`, sparse clone), `npm` (`package`, `version?`, `registry?`), `archive` (`url`, `sha256?`, needs v2.1.224+), `command` (runs a local tool that prints one absolute path, needs v2.1.229+). When both `ref` and `sha` are set, `sha` wins. Optional top-level: `$schema`, `description`, `version`, `metadata.pluginRoot`, `allowCrossMarketplaceDependenciesOn`, `renames`. 16 marketplace names are reserved for Anthropic (`claude-plugins-official`, `agent-skills`, `anthropic-marketplace`, …) and impersonating names are blocked.
SRC: https://code.claude.com/docs/en/plugin-marketplaces

### Output styles replace the built-in software-engineering system prompt unless `keep-coding-instructions: true`
Locations: `~/.claude/output-styles`, `.claude/output-styles`, managed settings dir. Frontmatter: `name`, `description`, `keep-coding-instructions` (default false), `force-for-plugin` (plugin-only; applies the style automatically and overrides the user's `outputStyle`). Built-ins: Default, Proactive, Explanatory, Learning. Set via `"outputStyle": "Explanatory"` in settings; read once at session start, so changes need `/clear`. Output styles apply to the main conversation ONLY — subagents run their own system prompt (forks are the exception). The standalone `/output-style` command was deprecated in v2.1.73 and removed in v2.1.91.
SRC: https://code.claude.com/docs/en/output-styles

### MCP has three config scopes and four transports
Scopes: local (default, `~/.claude.json` under the project path, private), project (`.mcp.json` at repo root, git-shared), user (`~/.claude.json`, all projects). Transports: `stdio` (default when no `type`), `http` (alias `streamable-http`), `sse`, `ws` (config-only; `--transport` doesn't accept it). A JSON entry with `url` but no `type` is a hard configuration error. Reserved server names: `workspace`, `claude-in-chrome`, `computer-use`, `Claude Preview`, `Claude Browser`. Per-server `timeout` (ms) overrides `MCP_TOOL_TIMEOUT`.
SRC: https://code.claude.com/docs/en/mcp

### Project-scoped `.mcp.json` servers load WITHOUT approval in `claude -p`, Agent SDK, and cloud sessions
Verbatim: "`claude -p` runs, Agent SDK sessions, and cloud sessions can't show that prompt: Claude Code loads project-scoped servers there without asking." Same for hooks in a project's `.claude/settings.json` — a `-p` session shows no workspace trust dialog, so repo hooks run in folders you've never trusted. Mitigations: `--bare`, `disabledMcpjsonServers`, `--setting-sources`, or the SDK's `settingSources` option.
SRC: https://code.claude.com/docs/en/headless

### `--bare` is the new recommended mode for scripted/SDK calls and will become the `-p` default
Skips auto-discovery of hooks, skills, plugins, MCP servers, auto memory, and CLAUDE.md. In bare mode Claude Code never reads OAuth credentials or the system keychain — set `ANTHROPIC_API_KEY` or supply `apiKeyHelper` via `--settings` JSON. Bedrock/Google Cloud/Microsoft Foundry still read their own provider creds. Only Bash, file read, and file edit tools are available; load context back in with `--append-system-prompt(-file)`, `--settings`, `--mcp-config`, `--agents`, `--plugin-dir`/`--plugin-url`.
SRC: https://code.claude.com/docs/en/headless

### `system/init` stream event is the harness introspection point for CI gating
Carries `plugins` (name, path), `plugin_errors` (plugin, type, message — key omitted when empty), `mcp_servers` (name, status), `mcp_server_errors` (name, type ∈ `unknown_type`/`url_missing_type`/`invalid_config`/`reserved_name`, message — requires v2.1.219+), and an optional `capabilities` string array (e.g. `interrupt_receipt_v1`) for feature detection instead of version-string comparison (v2.1.205+). It is the first stream event unless `plugin_install` or `hook_started`/`hook_progress`/`hook_response` events precede it.
SRC: https://code.claude.com/docs/en/headless

### Subagent messages in stream-json are identified by `parent_tool_use_id`
Main-conversation messages carry `null`; subagent messages carry the ID of the tool call that spawned them. By default only subagent `tool_use`/`tool_result` blocks are emitted — pass `--forward-subagent-text` or set `CLAUDE_CODE_FORWARD_SUBAGENT_TEXT` to also get text and thinking blocks (v2.1.211+). Nested subagents at every depth are forwarded when enabled, so the full nesting tree can be rebuilt by following IDs (v2.1.219+).
SRC: https://code.claude.com/docs/en/headless

### `--output-format json` + `--json-schema` gives typed structured output in a `structured_output` field
The `json` payload also includes `total_cost_usd` and a per-model cost breakdown (client-side estimates). Invalid schemas now hard-fail with `Error: --json-schema is not a valid JSON Schema` (v2.1.205+; before that they were silently ignored). The `format` keyword is accepted as an annotation but not enforced. Piped stdin is capped at 10MB.
SRC: https://code.claude.com/docs/en/headless

### SIGTERM handling in headless mode is well-defined
SIGTERM aborts the in-progress turn, terminates the process tree of any running Bash command, runs `SessionEnd` hooks, and exits with code 143. Background Bash tasks are killed ~5s after the final result. Background subagents/workflows are exempt from that grace (their result is part of the output) but capped at 10 minutes by default — tune with `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`, or `0` for no limit.
SRC: https://code.claude.com/docs/en/headless

### Agent SDK packages: `@anthropic-ai/claude-agent-sdk` (TS) and `claude-agent-sdk` (Python)
TS entry point `query({prompt, options}): Query`; also exports `startup()` (pay startup cost upfront, then `warm.query(...)`), `tool()`, `createSdkMcpServer()`, `listSessions()`, `getSessionMessages()`. Python exports `query()`, `ClaudeSDKClient` (with `connect`/`query`/`receive_response`/`interrupt`/`set_permission_mode`/`set_model`/`disconnect`), `@tool()` decorator, `create_sdk_mcp_server()`, `list_sessions()`, `get_session_messages()`, `rename_session()`, `tag_session()`. The SDK is library-only for Python/TS — other languages should run the CLI as a subprocess with `-p --output-format json`.
SRC: https://code.claude.com/docs/en/agent-sdk/overview

### TS `Options.systemPrompt` is a union that controls whether you get the Claude Code preset at all
`string | { type: 'preset'; preset: 'claude_code'; append?: string; excludeDynamicSections?: boolean }`. Default is `undefined`, which means a MINIMAL prompt — not the Claude Code prompt. There is no separate `appendSystemPrompt` option; use the preset's `append`. `settingSources` controls which filesystem settings load (defaults to all CLI sources). Other harness-relevant options: `canUseTool`, `hooks`, `agents`, `plugins`, `skills` (`string[] | 'all'`), `sessionStore` + `sessionStoreFlush`, `maxBudgetUsd`, `outputFormat: {type:'json_schema', schema}`, `enableFileCheckpointing`, `toolAliases`, `managedSettings`, `spawnClaudeCodeProcess`.
SRC: https://code.claude.com/docs/en/agent-sdk/typescript

### CLAUDE.md hierarchy: 4 scopes, concatenated (not overriding), root-down ordering
Managed policy (`/Library/Application Support/ClaudeCode/CLAUDE.md`, `/etc/claude-code/CLAUDE.md`, `C:\Program Files\ClaudeCode\CLAUDE.md`) → user `~/.claude/CLAUDE.md` → project `./CLAUDE.md` or `./.claude/CLAUDE.md` → local `./CLAUDE.local.md`. Claude Code walks UP the tree from cwd; all discovered files are concatenated root-down, so files closest to cwd are read last. Within a directory, `CLAUDE.local.md` is appended after `CLAUDE.md`. Subdirectory CLAUDE.md files load on demand when Claude reads files there. Managed policy CLAUDE.md cannot be excluded by `claudeMdExcludes`.
SRC: https://code.claude.com/docs/en/memory

### `@path` imports: max depth 4 hops, relative to the importing file, skipped inside code spans/fences
Both relative and absolute paths allowed; relative resolves against the file containing the import, not cwd. Imported files are expanded and loaded at launch — imports organize but do NOT reduce context. Backticked `` `@README` `` stays literal. An import in a PROJECT-level memory file whose path resolves outside the working directory triggers a one-time external-imports approval dialog; imports in user-scope memory files load without it. Claude Code reads CLAUDE.md, not AGENTS.md — the documented bridge is a `@AGENTS.md` import (or a symlink, but Windows needs Admin/Developer Mode).
SRC: https://code.claude.com/docs/en/memory

### `.claude/rules/` is a path-scoped alternative to a growing CLAUDE.md
Markdown files in `.claude/rules/` (recursive, symlinks resolved, circular symlinks handled). YAML frontmatter `paths:` scopes a rule to glob patterns, loading only when Claude touches matching files. Rules without `paths` load at launch with the same priority as `.claude/CLAUDE.md`. User-level `~/.claude/rules/` loads BEFORE project rules (project wins). Brace expansion is budgeted: 1,000 expanded patterns and 4 MiB per rule's whole `paths` list; over-budget patterns are used unexpanded and match nothing. Project rules are skipped if `project` is excluded from `--setting-sources`.
SRC: https://code.claude.com/docs/en/memory

### Auto memory is a separate, machine-local system with a hard read limit
Stored at `~/.claude/projects/<project>/memory/` (derived from the git repo, so all worktrees share one dir). `MEMORY.md` is the index; only its first 200 lines OR first 25KB (whichever comes first) load at session start. Topic files load on demand. Frontmatter and block-level HTML comments are stripped before measuring. Claude Code stamps a `modified` ISO-8601 frontmatter field on writes (v2.1.214+). Configure with `autoMemoryEnabled`, `autoMemoryDirectory`, or `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`. Memory files are excluded from the `cleanupPeriodDays` retention sweep.
SRC: https://code.claude.com/docs/en/memory

### Status line receives a rich JSON session snapshot on stdin — usable as a cheap harness telemetry tap
`statusLine: { type: "command", command, padding?, refreshInterval?, hideVimModeIndicator? }`. stdin JSON includes `cwd`, `session_id`, `session_name`, `prompt_id`, `transcript_path`, `model.{id,display_name}`, `workspace.{current_dir,project_dir,added_dirs,git_worktree,repo}`, `version`, `output_style.name`, `cost.{total_cost_usd,total_duration_ms,total_api_duration_ms,total_lines_added,total_lines_removed}`, `context_window.{total_input_tokens,total_output_tokens,context_window_size,used_percentage,remaining_percentage,current_usage}`, `exceeds_200k_tokens`, `fast_mode`, `effort.level`, `thinking.enabled`, `rate_limits.{five_hour,seven_day}`, `agent.name`, `pr.{number,url,review_state}`, `worktree.*`, `vim.mode`.
SRC: https://code.claude.com/docs/en/statusline

### Anthropic: workflows vs agents is the primary design axis, and simplicity wins
Workflows = "Systems where LLMs and tools are orchestrated through predefined code paths." Agents = "Systems where LLMs dynamically direct their own processes and tool usage, maintaining control over how they accomplish tasks." Five workflow patterns: prompt chaining (with gates), routing, parallelization (sectioning + voting), orchestrator-workers, evaluator-optimizer. On the agent-computer interface: "While building our agent for SWE-bench, we actually spent more time optimizing our tools than the overall prompt."
SRC: https://www.anthropic.com/engineering/building-effective-agents

### Context rot is architectural, not a bug: n² attention means longer context = measurably worse recall
"as the number of tokens in the context window increases, the model's ability to accurately recall information from that context decreases" — caused by "n² pairwise relationships for n tokens." Prescriptions: system prompts at the right "altitude" (neither hardcoded brittle logic nor vague guidance), sectioned with `<background_information>`, `<instructions>`, `## Tool guidance`, `## Output description`; just-in-time retrieval via lightweight identifiers (file paths, queries, links) instead of pre-loading; compaction; structured note-taking; and sub-agent architectures where each sub-agent returns "a condensed, distilled summary of its work (often 1,000-2,000 tokens)."
SRC: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

### Code execution with MCP: 150,000 → 2,000 tokens (98.7% reduction) on a Drive→Salesforce task
Instead of exposing MCP servers as direct tool calls, present them as a filesystem tree of TypeScript modules (`./servers/<server>/<tool>.ts`) each wrapping `callMCPTool()`. Benefits: progressive disclosure (a `search_tools` function with detail-level params replaces pre-loading every definition), data filtering inside the execution environment before results reach context, privacy (intermediate results never enter context; the MCP client can tokenize PII), and state persistence where saved functions become reusable skills. Trade-off: requires secure sandboxing, resource limits, and monitoring.
SRC: https://www.anthropic.com/engineering/code-execution-with-mcp

### Multi-agent research: +90.2% over single-agent, at ~15x the tokens; token usage alone explains 80% of variance
"agents typically use about 4× more tokens than chat interactions, and multi-agent systems use about 15× more tokens than chats." On BrowseComp, "token usage by itself explains 80% of the variance." Opus 4 lead + Sonnet 4 subagents "outperformed single-agent Claude Opus 4 by 90.2% on our internal research eval." Tool description improvements produced "a 40% decrease in task completion time." LLM-as-judge rubric: factual accuracy, citation accuracy, completeness, source quality, tool efficiency. Production: resumability from error point, checkpoints + external memory, and rainbow deployments to avoid disrupting running agents.
SRC: https://www.anthropic.com/engineering/multi-agent-research-system

### Harness design for long-running apps (Mar 2026): separate generator from evaluator, because agents cannot grade themselves
"When asked to evaluate work they've produced, agents tend to respond by confidently praising the work—even when...quality is obviously mediocre." Three-agent GAN-inspired system: Planner (expands a 1-4 sentence prompt into a spec), Generator (React/Vite/FastAPI/SQLite), Evaluator (drives the live app via Playwright MCP, grades against hard thresholds, files bugs with reproducible steps and code locations). Agents hand off through FILES, not conversation threads. Opus 4.5 run: 6 hours, $200, vs solo agent 20 min / $9 that produced non-functional core features. Opus 4.6 run after removing the sprint construct: 3h50m, $124.70.
SRC: https://www.anthropic.com/engineering/harness-design-long-running-apps

### Effective harnesses for long-running agents (Nov 2025): two personas + a feature list + a progress file + init.sh + git
Initializer agent (first session only) vs Coding agent (subsequent sessions). Environment artifacts: a JSON feature list (200+ features for a claude.ai clone) where each feature has category, description, step-by-step verification, and a `passes` boolean, all initially false; `claude-progress.txt`; an `init.sh` bootstrap + e2e verification script; git history for rollback and continuity. Guardrail prompt: "It is unacceptable to remove or edit tests because this could lead to missing or buggy functionality." Explicit finding: SDK compaction alone is insufficient — the feature list and progress tracking compensate for context limits.
SRC: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents

### Managed Agents (Apr 2026): harness assumptions go stale within one model generation — so virtualize the harness
Claude Sonnet 4.5's "context anxiety" prompted engineers to add context resets; on Opus 4.5 the behavior was gone and those modifications became "dead weight." Anthropic's answer is three swappable abstractions: Session (append-only event log), Harness (the "brain" — the loop calling Claude and routing tool calls), Sandbox (the "hands"). Interfaces: `provision({resources})`, `emitEvent(id, event)`, `execute(name, input) → string`, `wake(sessionId)`, `getSession(id)`, `getEvents()`. Decoupling the harness from the container improved time-to-first-token ~60% at p50 and >90% at p95. Credentials never reach the sandbox; OAuth tokens sit in a vault behind a proxy.
SRC: https://www.anthropic.com/engineering/managed-agents

### Dynamic workflows (Jun 2026): Claude writes a JavaScript harness per task
"Claude is now intelligent enough to write a custom harness tailor-made for your use case." Workflows are JS files with special functions for spawning subagents; they control per-agent model choice, isolate subagents in separate worktrees, and resume from the last checkpoint. Seven named patterns: classify-and-act, fan-out-and-synthesize, adversarial verification, generate-and-filter, tournament, loop-until-done, and memory/rule adherence via dedicated verifier agents. Explicitly token-expensive; not for routine coding.
SRC: https://claude.com/blog/a-harness-for-every-task-dynamic-workflows-in-claude-code

### Writing effective tools: consolidate endpoints, namespace, and return semantic identifiers not UUIDs
Don't wrap every API endpoint — replace `list_contacts` + `get_contact` with one `search_contacts`; make `schedule_event` check availability internally. Namespace with consistent prefixes (`asana_projects_search`, `asana_users_search`). "Merely resolving arbitrary alphanumeric UUIDs to more semantically meaningful and interpretable language…significantly improves Claude's precision in retrieval tasks by reducing hallucinations." Offer response-format flexibility (`ResponseFormat.DETAILED` = 206 tokens vs `CONCISE` = 72 tokens). Method: paste eval transcripts back into Claude Code to have it identify failure patterns and rewrite the tools.
SRC: https://www.anthropic.com/engineering/writing-tools-for-agents

## EXAMPLES
### Minimal but complete settings.json with permissions + env (official example)
FILE: ~/.claude/settings.json | .claude/settings.json | .claude/settings.local.json
```
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "permissions": {
    "allow": [
      "Bash(npm run lint)",
      "Bash(npm run test *)",
      "Read(~/.zshrc)"
    ],
    "deny": [
      "Bash(curl *)",
      "Read(./.env)",
      "Read(./.env.*)",
      "Read(./secrets/**)"
    ]
  },
  "env": {
    "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
    "OTEL_METRICS_EXPORTER": "otlp",
    "OTEL_EXPORTER_OTLP_PROTOCOL": "http/protobuf"
  }
}
```
SRC: https://code.claude.com/docs/en/settings

### Canonical hooks block shape (EventName → matcher → hooks[] → type/command)
FILE: .claude/settings.json (hooks key); scripts in .claude/hooks/
```
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '.tool_input.file_path' | xargs npx prettier --write"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/protect-files.sh"
          }
        ]
      }
    ]
  }
}
```
SRC: https://code.claude.com/docs/en/hooks-guide

### PreToolUse hook that denies a command (full stdin→stdout contract)
FILE: .claude/hooks/block-rm.sh (chmod +x)
```
#!/bin/bash
input=$(cat)
command=$(jq -r '.tool_input.command' <<<"$input")

if [[ "$command" == rm* ]]; then
  jq -n '{
    "hookSpecificOutput": {
      "hookEventName": "PreToolUse",
      "permissionDecision": "deny",
      "permissionDecisionReason": "Destructive rm commands blocked"
    }
  }'
else
  exit 0
fi
```
SRC: https://code.claude.com/docs/en/hooks

### PreToolUse hook that rewrites tool input before execution
FILE: .claude/hooks/rewrite.sh
```
#!/bin/bash
jq -n '{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "updatedInput": {
      "command": "safer version of command"
    }
  },
  "systemMessage": "Command modified for safety"
}'
```
SRC: https://code.claude.com/docs/en/hooks

### Inject context into the conversation from a hook (UserPromptSubmit / SessionStart / PostToolUse etc.)
FILE: .claude/hooks/inject-context.sh
```
#!/bin/bash
jq -n '{
  "additionalContext": "This is important context for Claude",
  "systemMessage": "FYI to the user"
}'
```
SRC: https://code.claude.com/docs/en/hooks

### PreToolUse hook stdin JSON (what your script actually receives)
FILE: stdin to any PreToolUse hook handler
```
{
  "session_id": "abc123",
  "prompt_id": "550e8400-e29b-41d4-a716-446655440000",
  "transcript_path": "/home/user/.claude/projects/.../transcript.jsonl",
  "cwd": "/home/user/my-project",
  "permission_mode": "default",
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": {
    "command": "npm test",
    "description": "Run test suite",
    "timeout": 120000,
    "run_in_background": false
  },
  "tool_use_id": "toolu_01ABC123..."
}
```
SRC: https://code.claude.com/docs/en/hooks

### Non-command hook handler types (http, mcp_tool, prompt, agent) with the shared `if`/`timeout` fields
FILE: settings.json hooks[].hooks[] entries, or plugin hooks/hooks.json
```
{
  "type": "http",
  "url": "http://localhost:8080/hooks/pre-tool-use",
  "headers": { "Authorization": "Bearer $MY_TOKEN" },
  "allowedEnvVars": ["MY_TOKEN"]
}

{
  "type": "mcp_tool",
  "server": "my_server",
  "tool": "security_scan",
  "input": { "file_path": "${tool_input.file_path}" }
}

{
  "type": "prompt",
  "prompt": "Should this be allowed? $ARGUMENTS",
  "model": "claude-opus-4-1"
}

{
  "type": "agent",
  "prompt": "Validate this action: $ARGUMENTS",
  "model": "claude-opus-4-1"
}

// shared on all types:
{ "type": "...", "if": "Bash(git *)", "timeout": 600, "statusMessage": "Checking...", "once": false }
```
SRC: https://code.claude.com/docs/en/hooks

### Full subagent definition with every supported frontmatter field
FILE: .claude/agents/<name>.md or ~/.claude/agents/<name>.md (both scanned recursively)
```
---
name: unique-identifier
description: When to use this subagent
tools: Read, Grep, Glob
disallowedTools: Write, Edit
model: sonnet            # sonnet|opus|haiku|fable|inherit|full model ID
permissionMode: default  # default|acceptEdits|auto|dontAsk|bypassPermissions|plan
maxTurns: 10
skills:
  - skill-name
mcpServers:
  - server-name
  - inline-server:
      type: stdio
      command: npx
      args: ["-y", "@playwright/mcp@latest"]
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/validate.sh"
memory: user             # user|project|local
background: true
effort: high             # low|medium|high|xhigh|max
isolation: worktree
color: blue
initialPrompt: "Review this code"
---

You are a [role]. [System prompt in Markdown]
```
SRC: https://code.claude.com/docs/en/sub-agents

### Define subagents inline from the CLI (no files) — key for ephemeral harnesses
FILE: CLI flag; also settable as "agent": "code-reviewer" in .claude/settings.json to run the MAIN thread as that agent
```
claude --agents '{
  "code-reviewer": {
    "description": "Expert code reviewer",
    "prompt": "You are a senior code reviewer...",
    "tools": ["Read", "Grep", "Glob", "Bash"],
    "model": "sonnet"
  }
}'
```
SRC: https://code.claude.com/docs/en/sub-agents

### Skill with dynamic context injection + pre-approved bundled script
FILE: .claude/skills/<name>/SKILL.md or ~/.claude/skills/<name>/SKILL.md; supporting files alongside (scripts/, examples/, template.md)
```
---
name: render-chart
description: Render a chart from a CSV file
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/render.sh *)
---

Run `${CLAUDE_SKILL_DIR}/scripts/render.sh <csv-file>` to render the chart.

---
# and the dynamic-context pattern:
---
description: Summarizes uncommitted changes and flags anything risky.
---

## Current changes

!`git diff HEAD`

## Instructions

Summarize the changes above in two or three bullet points...
```
SRC: https://code.claude.com/docs/en/skills

### Skill that runs in a forked subagent and is user-invoke-only
FILE: .claude/skills/deploy/SKILL.md
```
---
name: deploy
description: Deploy the application to production
context: fork
disable-model-invocation: true
---

Deploy the application:
1. Run the test suite
2. Build the application
3. Push to the deployment target
```
SRC: https://code.claude.com/docs/en/skills

### Plugin directory layout (components at root, only plugin.json in .claude-plugin/)
FILE: plugin repo root
```
my-plugin/
├── .claude-plugin/
│   └── plugin.json        # ONLY this file goes here
├── skills/
│   └── code-reviewer/
│       └── SKILL.md
├── commands/              # flat .md files
│   └── status.md
├── agents/
│   └── security-reviewer.md
├── hooks/
│   └── hooks.json
├── output-styles/
│   └── terse.md
├── workflows/
├── bin/                   # added to PATH
├── scripts/
├── .mcp.json
└── .lsp.json
```
SRC: https://code.claude.com/docs/en/plugins-reference

### .claude-plugin/plugin.json manifest (all fields)
FILE: <plugin-root>/.claude-plugin/plugin.json
```
{
  "$schema": "https://json.schemastore.org/claude-code-plugin-manifest.json",
  "name": "plugin-name",
  "displayName": "Plugin Name",
  "version": "1.2.0",
  "description": "Brief plugin description",
  "author": { "name": "Author Name", "email": "author@example.com", "url": "https://github.com/author" },
  "homepage": "https://docs.example.com/plugin",
  "repository": "https://github.com/author/plugin",
  "license": "MIT",
  "keywords": ["keyword1"],
  "defaultEnabled": false,
  "skills": "./custom/skills/",
  "commands": ["./custom/commands/special.md"],
  "agents": ["./custom/agents/reviewer.md"],
  "hooks": "./config/hooks.json",
  "mcpServers": "./mcp-config.json",
  "outputStyles": "./styles/",
  "lspServers": "./.lsp.json",
  "userConfig": {
    "api_token": { "type": "string", "title": "API token", "sensitive": true }
  },
  "dependencies": ["helper-lib", { "name": "secrets-vault", "version": "~2.1.0" }]
}
```
SRC: https://code.claude.com/docs/en/plugins-reference

### .claude-plugin/marketplace.json (minimum viable catalog)
FILE: <marketplace-repo>/.claude-plugin/marketplace.json (relative plugin paths resolve from repo root, NOT from .claude-plugin/)
```
{
  "name": "company-tools",
  "owner": {
    "name": "DevTools Team",
    "email": "devtools@example.com"
  },
  "plugins": [
    {
      "name": "code-formatter",
      "source": "./plugins/formatter",
      "description": "Automatic code formatting on save",
      "version": "2.1.0",
      "author": { "name": "DevTools Team" }
    },
    {
      "name": "deployment-tools",
      "source": {
        "source": "github",
        "repo": "company/deploy-plugin",
        "ref": "v2.0.0",
        "sha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
      },
      "description": "Deployment automation tools"
    }
  ]
}
```
SRC: https://code.claude.com/docs/en/plugin-marketplaces

### Plugin MCP servers with path variables
FILE: <plugin-root>/.mcp.json (or inline in plugin.json under mcpServers)
```
{
  "mcpServers": {
    "plugin-database": {
      "command": "${CLAUDE_PLUGIN_ROOT}/servers/db-server",
      "args": ["--config", "${CLAUDE_PLUGIN_ROOT}/config.json"],
      "env": { "DB_PATH": "${CLAUDE_PLUGIN_DATA}" }
    }
  }
}

# Tools appear as: mcp__plugin_<plugin-name>_<server-name>__<tool>
# e.g. mcp__plugin_my-plugin_database-tools__query
```
SRC: https://code.claude.com/docs/en/plugins-reference

### Project-scoped .mcp.json (checked into git)
FILE: .mcp.json at project root. NOTE: an entry with `url` but no `type` is a hard error — Claude Code reads type-less entries as stdio.
```
{
  "mcpServers": {
    "shared-server": {
      "type": "http",
      "url": "https://example.com/mcp"
    },
    "events-server": {
      "type": "ws",
      "url": "wss://mcp.example.com/socket",
      "headers": { "Authorization": "Bearer YOUR_TOKEN" }
    },
    "local-tool": {
      "command": "npx",
      "args": ["-y", "airtable-mcp-server"],
      "env": { "AIRTABLE_API_KEY": "..." },
      "timeout": 600000
    }
  }
}
```
SRC: https://code.claude.com/docs/en/mcp

### MCP CLI: the `--` separator is mandatory for stdio servers
FILE: writes to ~/.claude.json (local/user) or .mcp.json (project)
```
# HTTP
claude mcp add --transport http notion https://mcp.notion.com/mcp
claude mcp add --transport http secure-api https://api.example.com/mcp \
  --header "X-API-Key: your-key-here"

# SSE
claude mcp add --transport sse asana https://mcp.asana.com/sse

# stdio — everything after `--` is passed to the server untouched
claude mcp add --env AIRTABLE_API_KEY=YOUR_KEY --transport stdio airtable \
  -- npx -y airtable-mcp-server

# WebSocket (config-only, --transport doesn't accept ws)
claude mcp add-json events-server \
  '{"type":"ws","url":"wss://mcp.example.com/socket","headers":{"Authorization":"Bearer TOKEN"}}'

# scopes: --scope local (default) | project | user
claude mcp list; claude mcp get <name>; claude mcp remove <name>
claude mcp reset-project-choices
```
SRC: https://code.claude.com/docs/en/mcp

### Output style file
FILE: ~/.claude/output-styles/<name>.md or .claude/output-styles/<name>.md; activate with {"outputStyle": "Diagrams first"}
```
---
name: Diagrams first
description: Lead every explanation with a diagram
keep-coding-instructions: true
---

When explaining code, architecture, or data flow, start with a Mermaid diagram showing the structure, then explain in prose.

## Diagram conventions

Use `flowchart TD` for control flow and `sequenceDiagram` for request paths. Keep diagrams under 15 nodes.
```
SRC: https://code.claude.com/docs/en/output-styles

### Headless: hermetic CI invocation, structured output, streaming, session capture/resume
FILE: CI scripts / package.json scripts
```
# Hermetic run (no host hooks/plugins/MCP/CLAUDE.md); needs ANTHROPIC_API_KEY
claude --bare -p "Summarize README.md" --allowedTools "Read"

# Typed structured output
claude -p "Extract the main function names from auth.py" \
  --output-format json \
  --json-schema '{"type":"object","properties":{"functions":{"type":"array","items":{"type":"string"}}},"required":["functions"]}' \
  | jq '.structured_output'

# Token-level streaming
claude -p "Write a poem" --output-format stream-json --verbose --include-partial-messages | \
  jq -rj 'select(.type == "stream_event" and .event.delta.type? == "text_delta") | .event.delta.text'

# Capture then resume a specific session (works from any directory, v2.1.223+)
session_id=$(claude -p "Start a review" --output-format json | jq -r '.session_id')
claude -p "Continue that review" --resume "$session_id"

# Prefix matching: the SPACE before * is load-bearing
claude -p "Look at my staged changes and create an appropriate commit" \
  --allowedTools "Bash(git diff *),Bash(git log *),Bash(git status *),Bash(git commit *)"

# Locked-down CI baseline
claude -p "..." --permission-mode dontAsk --max-turns 10 --max-budget-usd 5.00
```
SRC: https://code.claude.com/docs/en/headless

### TypeScript Agent SDK: query loop, in-process MCP tools, warm startup
FILE: npm install @anthropic-ai/claude-agent-sdk
```
import { query, tool, createSdkMcpServer, startup } from "@anthropic-ai/claude-agent-sdk";
import { z } from "zod";

const searchTool = tool(
  "search",
  "Search the web",
  { query: z.string() },
  async ({ query }) => ({ content: [{ type: "text", text: `Results for: ${query}` }] }),
  { annotations: { readOnlyHint: true, openWorldHint: true } }
);

const server = createSdkMcpServer({ name: "tools", version: "1.0.0", tools: [searchTool] });

for await (const message of query({
  prompt: "Hello",
  options: {
    maxTurns: 3,
    // default systemPrompt is MINIMAL — opt into the Claude Code prompt explicitly:
    systemPrompt: { type: 'preset', preset: 'claude_code', append: "Always use TypeScript" },
    mcpServers: { tools: server },
    settingSources: ['project'],
    permissionMode: 'acceptEdits',
    canUseTool: async (name, input) => ({ behavior: 'allow', updatedInput: input }),
  }
})) { console.log(message); }

// Pay startup cost upfront
const warm = await startup({ options: { maxTurns: 3 } });
for await (const m of warm.query("What files are here?")) console.log(m);
```
SRC: https://code.claude.com/docs/en/agent-sdk/typescript

### Python Agent SDK: persistent client, @tool decorator, in-process MCP server
FILE: pip install claude-agent-sdk
```
# pip install claude-agent-sdk
import asyncio
from claude_agent_sdk import (
    query, ClaudeSDKClient, ClaudeAgentOptions,
    tool, create_sdk_mcp_server, AssistantMessage, TextBlock,
)

@tool("add", "Add two numbers", {"a": float, "b": float})
async def add(args):
    return {"content": [{"type": "text", "text": f"Sum: {args['a'] + args['b']}"}]}

calculator = create_sdk_mcp_server(name="calculator", version="2.0.0", tools=[add])

options = ClaudeAgentOptions(
    system_prompt="You are an expert Python developer",
    permission_mode="acceptEdits",   # default|acceptEdits|plan|dontAsk|bypassPermissions|auto
    mcp_servers={"calc": calculator},
    allowed_tools=["mcp__calc__add"],
    max_turns=10,
)

async def main():
    async with ClaudeSDKClient(options=options) as client:
        await client.query("What's 2 + 2?")
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(block.text)

asyncio.run(main())
```
SRC: https://code.claude.com/docs/en/agent-sdk/python

### CLAUDE.md bridging an existing AGENTS.md (Claude Code does NOT read AGENTS.md)
FILE: ./CLAUDE.md at repo root
```
@AGENTS.md

## Claude Code

Use plan mode for changes under `src/billing/`.

# Or, if no Claude-specific content is needed:
#   ln -s AGENTS.md CLAUDE.md
# (Windows needs Administrator or Developer Mode for symlinks — use the import instead.)
```
SRC: https://code.claude.com/docs/en/memory

### Path-scoped rule (loads only when Claude touches matching files)
FILE: .claude/rules/api-design.md (recursive; symlinks supported). User-level: ~/.claude/rules/
```
---
paths:
  - "src/**/*.{ts,tsx}"
  - "lib/**/*.ts"
  - "tests/**/*.test.ts"
---

# API Development Rules

- All API endpoints must include input validation
- Use the standard error response format
- Include OpenAPI documentation comments
```
SRC: https://code.claude.com/docs/en/memory

### Status line as a telemetry tap
FILE: ~/.claude/settings.json or .claude/settings.json
```
{
  "statusLine": {
    "type": "command",
    "command": "jq -r '\"[\\(.model.display_name)] \\(.context_window.used_percentage // 0)% context\"'",
    "padding": 2,
    "refreshInterval": 5
  }
}
```
SRC: https://code.claude.com/docs/en/statusline

### Code-execution-with-MCP: MCP server presented as a TypeScript module tree
FILE: sandboxed execution workspace, e.g. ./servers/<server>/<tool>.ts + ./workspace/
```
servers
├── google-drive
│   ├── getDocument.ts
│   └── index.ts
└── salesforce
    ├── updateRecord.ts
    └── index.ts

// ./servers/google-drive/getDocument.ts
import { callMCPTool } from "../../../client.js";

interface GetDocumentInput { documentId: string; }
interface GetDocumentResponse { content: string; }

/* Read a document from Google Drive */
export async function getDocument(input: GetDocumentInput): Promise<GetDocumentResponse> {
  return callMCPTool<GetDocumentResponse>('google_drive__get_document', input);
}

// agent-authored code — intermediate data never enters the context window
import * as gdrive from './servers/google-drive';
import * as salesforce from './servers/salesforce';

const transcript = (await gdrive.getDocument({ documentId: 'abc123' })).content;
await salesforce.updateRecord({
  objectType: 'SalesMeeting',
  recordId: '00Q5f000001abcXYZ',
  data: { Notes: transcript }
});
```
SRC: https://www.anthropic.com/engineering/code-execution-with-mcp

### Plugin CLI surface for programmatic harness provisioning
FILE: installs recorded in ~/.claude/settings.json | .claude/settings.json | .claude/settings.local.json; cache at ~/.claude/plugins/cache
```
claude plugin init <name> --with skills,agents,hooks,mcp,lsp,output-style,channel
claude plugin install <plugin> --scope user|project|local --config key=value -y
claude plugin uninstall <plugin> --keep-data --prune -y
claude plugin enable|disable <plugin> --scope ...
claude plugin update <plugin> --scope user|project|local|managed -y
claude plugin list --json --available
claude plugin details <name>        # component inventory + projected token cost
claude plugin validate <path> --strict
claude plugin prune --dry-run
claude plugin tag [path] --push -m "v%s"
```
SRC: https://code.claude.com/docs/en/plugins-reference

## GOTCHAS
- DOC URLS MOVED. Every `docs.claude.com/en/docs/claude-code/*` link 301s to `code.claude.com/docs/en/*`. Any harness code, bookmark, or CLAUDE.md that hardcodes the old path will hit a cross-host redirect. Also: `/docs/en/slash-commands` no longer exists as a distinct page — it now serves the skills doc.
- WARNING ON MY OWN SOURCES: WebFetch summarizes pages through a small model, and one pass returned a fabricated settings.json hooks example using nonexistent `PreCommand`/`PostCommand`/`ConfigChange` top-level keys. The authoritative hook config shape is `hooks -> <EventName> -> [{matcher, hooks: [{type, command}]}]` as shown in the concrete_examples. There are no `PreCommand`/`PostCommand` events. Treat any single-fetch summary of these docs as needing a second confirming source.
- Hook `permissionDecision: "allow"` is NOT a permission override. Deny and ask rules are evaluated regardless of what a PreToolUse hook returns. Building an allowlist purely in hooks while a broad deny rule exists silently does nothing.
- Deny rules cannot carry exceptions. `deny: ["Bash(aws *)"]` + `allow: ["Bash(aws s3 ls)"]` blocks everything — first match in deny→ask→allow order wins and specificity is irrelevant. This is a common footgun when migrating from allowlist-style configs.
- `Bash(devbox run *)`, `Bash(npx *)`, `Bash(docker exec *)`, `Bash(direnv exec *)`, `Bash(mise exec *)` are effectively `Bash(*)` — Claude Code does not strip these runners, so the rule matches whatever follows, including `devbox run rm -rf .`. Write one rule per inner command instead.
- `claude -p`, Agent SDK, and cloud sessions load a repository's `.claude/settings.json` hooks AND its `.mcp.json` servers with no trust dialog and no approval prompt. Cloning an untrusted repo and running `claude -p` in it executes that repo's hooks. Use `--bare`, `--setting-sources`, `disabledMcpjsonServers`, or `--settings '{"disableAllHooks": true}'` (setting it in user settings alone is insufficient — project settings take precedence and can set it back to false).
- Agent SDK `systemPrompt` defaults to `undefined`, which means a MINIMAL prompt, NOT the Claude Code system prompt. Harnesses that assume Claude Code behavior must explicitly pass `{ type: 'preset', preset: 'claude_code' }`. There is no separate `appendSystemPrompt` option in TS — use the preset's `append`.
- `additionalContext` silently does nothing on most hook events. It only applies to UserPromptSubmit, UserPromptExpansion, SessionStart, PostToolUse, PostToolUseFailure, Stop, SubagentStop, Notification — and is capped at 10,000 chars. `suppressOutput` is accepted but has zero effect.
- A timed-out PreToolUse hook does not block — the call continues through the normal permission flow. Security-critical hooks must be fast, or you need a deny rule as backstop. Default timeout is 600s for command/http/mcp_tool, which is long enough to hang a harness.
- Plugin agents silently drop `hooks`, `mcpServers`, and `permissionMode` — fields that work fine in `.claude/agents/`. An agent that works locally may lose its guardrails when packaged as a plugin.
- Skill frontmatter is bifurcated: Claude Code accepts ~20 fields, but claude.ai upload / the Skills API / `package_skill.py` accept only 6 (`name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`) and HARD-ERROR on anything else. A skill using `argument-hint` or `context: fork` cannot be uploaded without stripping fields.
- Plugin `userConfig` values are deliberately unavailable in shell-form hook commands (exec form only) — a security restriction that will look like a bug if you're templating secrets into hook commands.
- Marketplace relative plugin paths resolve from the marketplace ROOT, not from `.claude-plugin/`. And they do not resolve at all if users add the marketplace via a direct URL to `marketplace.json`, since only that one file is downloaded.
- 16 marketplace names are reserved for Anthropic and are re-checked on every load, not just on add. A marketplace registered before a name became reserved stops loading entirely with an 'untrusted source' error.
- `~/.claude/skills/` is not read by Cowork sessions, cloud sessions, or routines — each routine run is a fresh remote session. A personal skill invoked by a routine reports 'skill not found'. Commit it to `.claude/skills/` or ship it in a repo-declared plugin instead.
- Nested `.claude/skills/` below your start directory are NOT loaded at startup; they appear only after Claude reads or edits a file in that subdirectory. They won't autocomplete or be invocable by name before then — a real surprise in monorepos.
- `--add-dir` and `permissions.additionalDirectories` behave differently: `--add-dir` loads `.claude/skills/` and `.claude/commands/` from the added dir; the settings key grants file access ONLY. CLAUDE.md from added dirs needs `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1`.
- Auto-memory `MEMORY.md` is truncated at 200 lines OR 25KB, whichever comes first — content past that is silently dropped on the next load. Writes over the limit still succeed but return an error telling Claude to rewrite the index.
- CLAUDE.md `@imports` reduce nothing: imported files expand and load at launch. Splitting a large CLAUDE.md into imports helps organization and costs the same context. Use `.claude/rules/` with `paths:` frontmatter if you actually want lazy loading.
- Output styles apply to the main conversation only — subagents run their own system prompt and ignore them (forks excepted). Output style is also read once at session start; changing it needs `/clear`.
- Multi-agent costs are non-linear: ~15x the tokens of chat, and Anthropic's own long-running-app harness cost $200 for a 6-hour run vs $9 for a 20-minute solo run (~20x) — though the solo run produced non-functional core features. Token usage alone explained 80% of eval variance.
- Anthropic's explicit warning against over-scaffolding: Sonnet 4.5's 'context anxiety' justified context-reset machinery that became 'dead weight' on Opus 4.5. Harness components that compensate for a model's weaknesses should be removed incrementally as models improve, or they become pure overhead.
- Agents cannot grade their own work — 'agents tend to respond by confidently praising the work, even when quality is obviously mediocre.' A harness that asks the generator to self-review instead of running a separate evaluator will report false success.
- Anthropic does not permit third-party developers to offer claude.ai login or rate limits for products built on the Agent SDK (unless previously approved) — use API key auth. Branding is also restricted: 'Claude Agent' is allowed, 'Claude Code' / 'Claude Code Agent' is not.
- Some 'settings.json' keys I captured came from a summarized fetch and may be imprecise (e.g. `disableAutoMode` appears as both boolean and the string `"disable"` in different places; `permissions.disableAutoMode` per the permissions doc takes `"disable"`). Verify individual exotic keys against `https://code.claude.com/docs/en/settings.md` before relying on them.

## OPEN
- The exact `--input-format stream-json` INPUT message schema (what a harness must write to stdin to drive a multi-turn headless session) was referenced in the CLI reference but I did not retrieve its field-level definition. It is likely on https://code.claude.com/docs/en/agent-sdk/streaming-input or the TypeScript SDK's SDKUserMessage type — needs a direct fetch.
- Full `SDKSystemMessage` / `SDKAssistantMessage` / `SDKResultMessage` field lists were not retrieved verbatim; the TypeScript reference page summary described them only by name. Fetch https://code.claude.com/docs/en/agent-sdk/typescript.md and grep those anchors for the exact fields (including the `capabilities` array values).
- The `--permission-prompt-tool` MCP contract (what request the tool receives and what response shape it must return to approve/deny) was named in the CLI reference but its schema was not retrieved. Likely at https://code.claude.com/docs/en/agent-sdk/permissions.md.
- The complete authoritative `permissions` object key list from settings.md was not retrieved verbatim — the summarizer explicitly said the page has no dedicated 'Permission settings' section in the form I asked for. `additionalDirectories`, `defaultMode`, `disableBypassPermissionsMode`, `disableAutoMode` are all confirmed elsewhere, but a definitive list should come from https://code.claude.com/docs/en/settings.md#permission-settings.
- Read/Edit path-pattern syntax (the gitignore-style `//abs`, `~/home`, `./relative` distinction for Read/Edit rules) was not captured verbatim — only Bash pattern semantics were. It lives further down https://code.claude.com/docs/en/permissions.md under 'Tool-specific permission rules'.
- `workflows/` as a plugin component (the JavaScript orchestration files behind 'dynamic workflows') has no dedicated reference page I located. The June 2026 claude.com blog post describes the concept and seven patterns but not the API surface (which functions spawn subagents, the resume/checkpoint format).
- The `sandbox` settings key / `sandbox.enabled` and the sandboxing docs (https://code.claude.com/docs/en/sandboxing, /sandbox-environments) were not fetched — relevant for a harness that needs isolation, and referenced by the memory doc as a managed-settings enforcement lever.
- Whether `claude -p --output-format stream-json` guarantees ordering of `hook_started`/`hook_progress`/`hook_response` events relative to `system/init` across all supported versions — the docs note a regression window (v2.1.169–v2.1.203 batched them) but the current guarantee is only described informally.
- Anthropic engineering posts I identified but did not fetch, all potentially relevant: 'How we contain Claude across products', 'How we built Claude Code auto mode: a safer way to skip permissions' (Mar 25 2026), 'Introducing advanced tool use on the Claude Developer Platform' (Nov 24 2025), 'Equipping agents for the real world with Agent Skills' (Oct 16 2025), 'Demystifying evals for AI agents' (Jan 9 2026), 'Building a C compiler with a team of parallel Claudes' (Feb 5 2026).

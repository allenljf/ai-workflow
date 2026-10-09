# Packaging, distribution, versioning, upgrade and cross-tool portability of published agentic-development kits (obra/superpowers, BMAD v6, spec-kit, OpenSpec, cc-sdd, Agent OS v3, rulesync) plus Claude Code plugin mechanics as a shipping vehicle

## SUMMARY
The single biggest finding: **the four-repo superpowers architecture in the brief is stale by ~10 months.** superpowers v2.0.0 (2025-10-12) split skills into `obra/superpowers-skills` cloned to `~/.config/superpowers/skills/`. Four days later v3.0.1 (2025-10-16) reverted it — "We now use Anthropic's first-party skills system!" `superpowers-skills` has been dead since 2025-10-14. There is **no** skills-search, **no** `commands/`, and **no** named agents in v6.3.0 (2026-08-12). What remains is startlingly minimal: one `skills/` dir with **14 skills**, **one** SessionStart hook, zero runtime dependencies.

The whole integration is one idea: **the bootstrap is the entire integration.** The SessionStart hook `cat`s `skills/using-superpowers/SKILL.md` (3,096 chars ≈ 700–860 tokens) verbatim, wraps it in `<EXTREMELY_IMPORTANT>`, and emits it in whichever JSON shape the host expects — `hookSpecificOutput.additionalContext` (Claude Code), `additional_context` (Cursor), top-level `additionalContext` (Copilot CLI/SDK) — sniffed from `CURSOR_PLUGIN_ROOT`/`CLAUDE_PLUGIN_ROOT`/`COPILOT_CLI` env vars, because "Claude Code reads BOTH... without deduplication."

Portability comes from two rules in `docs/porting-to-a-new-harness.md`: **(1) skills name actions, never tools** — one skill body runs everywhere, with per-harness tool mapping isolated in `skills/using-superpowers/references/<harness>-tools.md`; **(2) everything ships through the harness's own install mechanism — never edit the user's files.** Ports fall into three shapes (shell-hook / in-process plugin / instructions-file). 14 harnesses are supported from one `skills/` tree plus ~10 thin manifests, version-synced by `.version-bump.json` + `scripts/bump-version.sh` (with a repo-wide `--audit` grep for undeclared version strings). Frontmatter is only `name` + `description` — the maximally portable subset.

Installer-wise the field has converged hard on **skills, not slash commands**, and on **`.agents/skills/` as the cross-tool root**. Edit-preservation splits three ways: content-fingerprint-vs-known-generated-versions (OpenSpec — "only ever writes or removes files whose content it generated"), SHA256 + mtime (BMAD `syncDirectory` + `files-manifest.csv`), and prompt/skip/force + backup dir (cc-sdd). BMAD's `customize.toml` three-layer override model (`*.user.toml` > `*.toml` > skill default, merged by value *shape*) is the strongest "never edit installed files" design found. Both `--ai` (spec-kit → `--integration`) and Agent OS/cc-sdd are stale relative to the brief.

## KEY FACTS
### obra/superpowers is at v6.3.0, released 2026-08-12 (commit b36e0829c6d0140e93cfef2ca599b1b07d4a7797), and supports 14 harnesses from one skills tree
Harnesses with install instructions in README: Claude Code, Antigravity, Codex App, Codex CLI, Cursor, Devin CLI, Factory Droid, Gemini CLI, GitHub Copilot CLI, Grok Build CLI, Kimi Code, OpenCode, Pi, Hermes Agent. Repo layout: .agents/, .claude-plugin/, .codex-plugin/, .cursor-plugin/, .devin-plugin/, .hermes-plugin/, .kimi-plugin/, .opencode/, .pi/, gemini-extension.json, hooks/, skills/, scripts/, tests/, docs/. There is NO commands/ dir and NO agents/ dir.
SRC: https://github.com/obra/superpowers

### The four-repo split described as the superpowers model is STALE — the separate skills repo existed for exactly 4 days in October 2025
RELEASE-NOTES.md v2.0.0 (2025-10-12): 'all skills, scripts, and documentation have moved from the plugin into a dedicated repository (obra/superpowers-skills). This transforms superpowers from a monolithic plugin into a lightweight shim that manages a local clone... First install: Plugin automatically clones skills to ~/.config/superpowers/skills/'. Then v3.0.1 (2025-10-16), in full: 'We now use Anthropic's first-party skills system!' obra/superpowers-skills HEAD is cdcd624 dated 2025-10-14 — dead for ~10 months. Its README still says 'This repository is automatically cloned by the superpowers plugin to ~/.config/superpowers/skills/', which is no longer true.
SRC: https://github.com/obra/superpowers/blob/main/RELEASE-NOTES.md

### There is no skills-search mechanism in superpowers v6.3.0. The historical one (v2.x) was a 100-line bash grep script, not an index or subagent
skills/using-skills/find-skills in the archived obra/superpowers-skills repo: greps SKILL.md files for a pattern, extracts the `when_to_use:` frontmatter line with `grep '^when_to_use:' | sed`, and prints 'Use <path>/SKILL.md when <trigger>'. It logged every query to ${XDG_CONFIG_HOME:-$HOME/.config}/superpowers/search-log.jsonl as {"timestamp":...,"query":...} so a companion skill (meta/gardening-skills-wiki/analyze-search-gaps.sh) could mine misses for missing skills. v6.3.0 avoids the description-truncation problem structurally: it ships only 14 skills.
SRC: https://github.com/obra/superpowers-skills/blob/main/skills/using-skills/find-skills

### The skill-description truncation problem is a Claude Code platform behavior, not something a kit solves itself; the budget is 1% of context with LRU-style eviction
Claude Code docs: 'The listing always contains every skill name, but if you have many skills, Claude Code shortens descriptions to fit the listing's character budget... The budget scales at 1% of the model's context window. When the listing overflows, Claude Code drops descriptions starting with the skills you invoke least, so the skills you use most keep their full text.' Tunable via `skillListingBudgetFraction` setting or `SLASH_COMMAND_TOOL_CHAR_BUDGET`. Per-entry cap: combined `description` + `when_to_use` truncated at 1,536 chars (configurable via `skillListingMaxDescChars`). `skillOverrides` can set entries to "name-only". `/doctor` estimates the listing's context cost.
SRC: https://code.claude.com/docs/en/skills.md

### superpowers' SessionStart hook injects the full using-superpowers SKILL.md verbatim — 3,096 chars / 485 words ≈ 700–860 tokens — and hand-writes three different JSON envelopes because hosts disagree
hooks/session-start reads ${PLUGIN_ROOT}/skills/using-superpowers/SKILL.md (frontmatter included — unlike the OpenCode/Pi injectors which strip it), JSON-escapes it with pure bash parameter substitution, and wraps it: '<EXTREMELY_IMPORTANT>\nYou have superpowers.\n\n**Below is the full content of your superpowers:using-superpowers skill...**'. Comment in source: 'Claude Code reads BOTH additional_context and hookSpecificOutput without deduplication, so we must emit only the field the current platform consumes.' Dispatch is by env var: CURSOR_PLUGIN_ROOT → additional_context; CLAUDE_PLUGIN_ROOT && !COPILOT_CLI → hookSpecificOutput.additionalContext; else → top-level additionalContext. Uses printf not heredoc to dodge a bash 5.3+ heredoc hang (issue #571).
SRC: https://github.com/obra/superpowers/blob/main/hooks/session-start

### superpowers' Claude hook matcher is "startup|clear|compact" — it does not fire on `resume` or `fork`
hooks/hooks.json: {"hooks":{"SessionStart":[{"matcher":"startup|clear|compact","hooks":[{"type":"command","command":"\"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd\" session-start","shell":"bash","async":false}]}]}}. Claude Code documents five SessionStart `source` values: startup, resume, clear, compact, fork. Docs also note 'SessionStart hooks run again on resume with source set to "resume", or "fork" if you added --fork-session'. The `shell: "bash"` key was added in v6.2.0 to fix Windows (Claude Code >= 2.1.81 resolves it to Git for Windows; older versions ignore the unknown key).
SRC: https://github.com/obra/superpowers/blob/main/hooks/hooks.json

### superpowers SKILL.md frontmatter uses ONLY `name` and `description` across all 14 skills — no allowed-tools, no context: fork, no license, no version, no model
Verified by grep across skills/: zero occurrences of context:, allowed-tools, disable-model-invocation, license:, model:, version:. Skill sizes range 63 lines / 3.1KB (using-superpowers) to 679 lines / 26KB (writing-skills) and 568 lines / 32KB (subagent-driven-development). Total skills/ payload is 369,641 bytes across 14 skills. Progressive disclosure is done with sibling files (writing-good-tests.md, defense-in-depth.md, root-cause-tracing.md, implementer-prompt.md, task-reviewer-prompt.md, re-review-prompt.md) and references/ only in using-superpowers.
SRC: https://github.com/obra/superpowers/tree/main/skills

### superpowers' porting doc states the one hard requirement and the two rules that make cross-tool portability work
docs/porting-to-a-new-harness.md: 'The bootstrap is the entire integration. Without it, the skill files are inert — present on disk, never invoked.' Hard requirement: 'The harness must let you inject text into the model's context at the start of every session, with no per-session opt-in by your human partner.' Rule 1: 'Skills name actions, not tools. Do not edit skill bodies to fit your harness.' Rule 2: 'Everything ships through the harness's own install mechanism. Never edit the user's files.' Three integration shapes: A shell-hook (Claude Code, Cursor, Copilot CLI), B in-process plugin/extension (OpenCode, Pi), C instructions-file (Gemini `contextFileName` → the extension's own GEMINI.md).
SRC: https://github.com/obra/superpowers/blob/main/docs/porting-to-a-new-harness.md

### superpowers keeps 9 manifests version-synced via a declarative .version-bump.json plus a bump script with drift detection and a repo-wide audit
.version-bump.json lists {path, field} pairs: package.json:version, .hermes-plugin/plugin.yaml:version, .claude-plugin/plugin.json:version, .cursor-plugin/plugin.json:version, .codex-plugin/plugin.json:version, .devin-plugin/plugin.json:version, .kimi-plugin/plugin.json:version, .claude-plugin/marketplace.json:plugins.0.version, gemini-extension.json:version — plus audit.exclude. scripts/bump-version.sh supports `<new-version>`, `--check` (reports DRIFT DETECTED when versions disagree), and `--audit` (greps the whole repo for the current version string and reports UNDECLARED files containing it).
SRC: https://github.com/obra/superpowers/blob/main/scripts/bump-version.sh

### OpenSpec v1.9.0 (2026-08-13) targets 39 tools from one AI_TOOLS registry in a single 102-line file
src/core/config.ts exports AI_TOOLS: AIToolOption[] with 39 entries. Interface: {name, value, available, successLabel?, skillsDir?, legacySkillsDirs?, globalSkillsDir?, detectionPaths?, setupNote?, requiresIdeRestart?}. Skills path is computed, not hardcoded: resolveToolSkillsDir() returns path.join(projectRoot, tool.skillsDir, 'skills') or path.join(homeDir, tool.globalSkillsDir, 'skills'). 12 skills are generated per tool (OPENSPEC_SKILL_NAMES). TOOL_ID_ALIASES maps retired ids (windsurf→devin, after the 2026-06-02 rebrand) so scripted --tools invocations keep working.
SRC: https://github.com/Fission-AI/OpenSpec/blob/main/src/core/config.ts

### OpenSpec's edit-preservation mechanism is content-fingerprint comparison against current AND all historical generated versions — not checksums or markers
Docs state the policy: 'OpenSpec only ever writes or removes files whose content it generated — if you customize copilot-setup-steps.yml or openspec.agent.md, or already have your own, it is left untouched (and init/update tell you so).' Implementation in src/core/github-copilot/cloud-agent.ts: isManagedCopilotCloudFile() = isCurrentCopilotCloudFile() || isLegacyCopilotCloudFile(), where the current check is exact string equality against COPILOT_CLOUD_FILE_CONTENTS[relPath] after normalizing CRLF, and the legacy check tests membership in getLegacyCopilotCloudFileContents() (a list of every previously-shipped body). src/core/shared/skill-content-equivalence.ts does the same for skills but first normalizes the `generatedBy:` frontmatter version to "<generated-version>" so a version bump alone doesn't look like a user edit.
SRC: https://github.com/Fission-AI/OpenSpec/blob/main/src/core/shared/skill-content-equivalence.ts

### OpenSpec stamps its own version into every generated skill's frontmatter as metadata.generatedBy
generateSkillContent() in src/core/shared/skill-generation.ts emits exactly: `---\nname: ${template.name}\ndescription: ${template.description}\nallowed-tools: ${OPENSPEC_CLI_ALLOWED_TOOLS}\nlicense: ${template.license || 'MIT'}\ncompatibility: ${template.compatibility || 'Requires openspec CLI.'}\nmetadata:\n  author: ${...|'openspec'}\n  version: "${...|'1.0'}"\n  generatedBy: "${generatedByVersion}"\n---`. OPENSPEC_CLI_ALLOWED_TOOLS = 'Bash(openspec:*)' — scoped to the CLI so 'agents that honor it stop prompting on each openspec call; the field only pre-approves — it does not restrict'.
SRC: https://github.com/Fission-AI/OpenSpec/blob/main/src/core/shared/skill-generation.ts

### OpenSpec recommends committing the whole openspec/ folder and never touches git itself
docs/team-workflow.md: 'OpenSpec reads and writes plain Markdown under openspec/. It never commits, branches, pushes, or pulls in your project... You commit openspec/ like any source.' docs/faq.md: 'Should I commit the openspec/ folder to git? Yes. Your specs, active changes, and archive are part of your project's history... The archive in particular becomes a durable record of why your system works the way it does.' No .gitignore manipulation exists anywhere in src/ (grep for 'gitignore' returns zero hits outside shell-completion installers).
SRC: https://github.com/Fission-AI/OpenSpec/blob/main/docs/team-workflow.md

### spec-kit's `--ai` flag no longer exists — it was deprecated in favor of `--integration` and is absent from v0.16.5.dev0
CHANGELOG.md entries: 'chore: deprecate --ai flag in favor of --integration on specify init (#2218)' and 'docs: replace deprecated --ai flag with --integration in all documentation (#2359)'. Current signature in src/specify_cli/commands/init.py: `specify init [project_name] --integration <key> --integration-options="..." --script sh|ps|py --here --force --preset <id> --extension <name|path|url> --ignore-agent-tools`. README example: `specify init my-project --integration copilot`. Grep for '--ai' in src/ returns zero hits.
SRC: https://github.com/github/spec-kit/blob/main/src/specify_cli/commands/init.py

### spec-kit has 42 agent integrations, each a self-contained subpackage with a declarative registrar_config giving dir/format/args/extension
src/specify_cli/integrations/ contains 42 subpackages registered in INTEGRATION_REGISTRY. Each declares e.g. claude: {"dir": ".claude/skills", "format": "markdown", "args": "$ARGUMENTS", "extension": "/SKILL.md"}; gemini: {"dir": ".gemini/commands", "format": "toml", "args": "{{args}}", "extension": ".toml"}; goose: {"dir": ".goose/recipes", "format": "yaml", "args": "{{args}}", "extension": ".yaml"}; firebender: extension ".mdc"; copilot: two entries — ".github/skills" + "/SKILL.md" and ".github/agents" + ".agent.md"; codex and agy both target ".agents/skills"; hermes targets "~/.hermes/skills"; generic: {"dir": ""} set dynamically from --commands-dir. CommandRegistrar.AGENT_CONFIGS is derived from INTEGRATION_REGISTRY — 'single source of truth'.
SRC: https://github.com/github/spec-kit/tree/main/src/specify_cli/integrations

### spec-kit deliberately emits Agent-Skills-spec-portable frontmatter and only adds a Claude-specific field for Claude
CommandRegistrar.build_skill_frontmatter() in src/specify_cli/agents.py returns exactly {"name", "description", "compatibility": "Requires spec-kit project structure with .specify/ directory", "metadata": {"author": "github-spec-kit", "source": <template path>}} — all four are spec fields. apply_argument_hint() adds `argument-hint` only for 'integrations that support the field — those exposing inject_argument_hint (currently Claude) — leaving build_skill_frontmatter's shared shape unchanged for every other agent.'
SRC: https://github.com/github/spec-kit/blob/main/src/specify_cli/agents.py

### spec-kit's re-run policy is blunt: merge-and-may-overwrite behind a confirmation, with only the constitution explicitly preserved
init.py prints '[yellow]Template files will be merged with existing content and may overwrite existing files[/yellow]' and requires confirmation unless --force ('Force merge/overwrite when using --here (skip confirmation)'). The one protected file: _materialize_constitution_template is guarded by `if memory_constitution.exists(): tracker.skip("constitution", "existing file preserved"); return`. Project state lives in .specify/integration.json (INTEGRATION_STATE_SCHEMA = 1, with a schema_too_new error kind), plus .specify/memory/, .specify/scripts/, .specify/templates/, .specify/extensions/, .specify/init-options.json, .specify/integration-events.yml.
SRC: https://github.com/github/spec-kit/blob/main/src/specify_cli/commands/init.py

### spec-kit gitignores its own generated scaffolding in its own repo, revealing the intended posture for dogfooding
.gitignore contains: '# The following directories/file are intentionally ignored so that they are not accidentally committed to the repository. They contain the scaffolding `specify init --integration copilot` (or other agents) does and they are meant for dogfooding Spec Kit during its own feature development.' followed by .github/agents/, .github/prompts/, .github/copilot-instructions.md, .grok/, .specify/, specs/. Also .specify/extensions/.cache/, .specify/extensions/.backup/, .specify/extensions/*/local-config.yml.
SRC: https://github.com/github/spec-kit/blob/main/.gitignore

### BMAD-METHOD is at v6.11.0 (2026-08-16) and has restructured into skills plus a Claude Code marketplace manifest
package.json version 6.11.0, bin: {bmad, bmad-method} → tools/installer/bmad-cli.js. Source tree is src/core-skills/ (8 skills: bmad-advanced-elicitation, bmad-brainstorming, bmad-customize, bmad-deep-recon, bmad-forge-idea, bmad-help, bmad-party-mode, bmad-review) and src/bmm-skills/{agents,plan,ship,v6-shims}. .claude-plugin/marketplace.json declares one plugin 'bmad-method-analyze-plan-build' v6.11.0 with source './' and an explicit 28-entry `skills` array listing each skill directory.
SRC: https://github.com/bmad-code-org/BMAD-METHOD/blob/main/.claude-plugin/marketplace.json

### BMAD's installer targets 47 platforms from one YAML table, and most now point at the shared .agents/skills/ root
tools/installer/ide/platform-codes.yaml, 357 lines, header: 'Multiple platforms may share the same target_dir or global_target_dir — many tools read from the shared `.agents/skills/` and `~/.agents/skills/` cross-tool standard. Paths verified against each tool's primary docs as of 2026-04-25.' Schema per platform: {name, preferred, suspended?, installer: {target_dir, global_target_dir?, ancestor_conflict_check?, commands_target_dir?, commands_extension?, commands_body_template?, commands_filter?}}. claude-code → .claude/skills + ~/.claude/skills; codex/cursor/gemini/copilot/opencode/warp/windsurf/roo → .agents/skills. github-copilot additionally emits .github/agents/*.agent.md with commands_filter: agents-only and a one-line body template that just tells the agent to LOAD the full SKILL.md.
SRC: https://github.com/bmad-code-org/BMAD-METHOD/blob/main/tools/installer/ide/platform-codes.yaml

### BMAD is the only kit found that uses real checksums plus mtime to decide whether to overwrite a user-edited file
tools/installer/file-ops.js syncDirectory(): for each existing dest file it computes getFileHash(source) and getFileHash(dest); 'if (sourceHash === destHash) { // Files are identical, safe to update }' else it compares stat().mtime and only copies 'if (sourceStats.mtime > destStats.mtime)', with the comment '// Otherwise, preserve user modifications'. It then deletes dest files absent from source. Separately, tools/installer/core/manifest-generator.js writes _bmad/_config/files-manifest.csv with header 'type,name,module,path,hash' where hash is a SHA256 of every installed file, and _bmad/_config/manifest.yaml carries {installation: {version, installDate, lastUpdated}, modules: [{name, version, installDate, lastUpdated, source}], ides: []}.
SRC: https://github.com/bmad-code-org/BMAD-METHOD/blob/main/tools/installer/file-ops.js

### BMAD's customization design is the strongest 'never edit installed files' pattern found: a three-layer TOML override merged by value shape, not field name
docs/how-to/customize-bmad.md: 'Every customizable skill ships a customize.toml file with its defaults... You never edit this file. Instead, you create sparse override files containing only the fields you want to change.' Priority: 1 _bmad/custom/{skill-name}.user.toml (personal, gitignored) > 2 _bmad/custom/{skill-name}.toml (team/org, committed) > 3 the skill's own customize.toml (defaults). Merge rules: scalar → override wins; table → deep merge; array of tables where every item shares the same identifier field (all `code` or all `id`) → merge by that key, matching keys replace in place, new keys append; any other array → append (base, then team, then user). 'No removal mechanism. Overrides cannot delete base items.' Resolver is Python stdlib tomllib run via `uv run`.
SRC: https://github.com/bmad-code-org/BMAD-METHOD/blob/main/docs/how-to/customize-bmad.md

### BMAD has no automated v4→v6 migration script — it is back-up-and-remove plus manual artifact relocation
docs/how-to/upgrade-to-v6.md: when v4 (.bmad-method folder) is detected 'you can: Allow the installer to back up and remove .bmad-method, or Exit and handle cleanup manually. If you named your bmad method folder something else - you will need to manually remove the folder yourself.' IDE cleanup is explicitly manual: 'Manually remove legacy v4 IDE commands/skills'. Planning artifacts must be hand-moved to _bmad-output/planning-artifacts/ with descriptive filenames containing PRD/brief/architecture/ux-design. Advice for mid-planning work: 'Consider restarting with v6 workflows.'
SRC: https://github.com/bmad-code-org/BMAD-METHOD/blob/main/docs/how-to/upgrade-to-v6.md

### cc-sdd is at v3.0.2 with last commit 2026-04-27 — roughly 4 months stale as of 2026-08
tools/cc-sdd/package.json version 3.0.2. Agent registry src/agents/registry.ts defines 20 agent modes across 8 tools, each with {label, description, aliasFlags, recommendedModels, layout: {commandsDir, agentDir, docFile}, commands, manifestId, upgradeNotice?, completionGuide?, templateFallbacks?}. Every non-skills mode carries an upgradeNotice: 'This mode will be removed in a future release. Migrate now: npx cc-sdd@latest --claude-skills' etc. Skills modes: claude-code-skills (.claude/skills), codex-skills (.agents/skills), cursor-skills (.cursor/skills), github-copilot-skills (.github/skills), gemini-cli-skills (.gemini/skills), windsurf-skills (.windsurf/skills), opencode-skills (.opencode/skills), antigravity-skills (.agent/skills).
SRC: https://github.com/gotalab/cc-sdd/blob/main/tools/cc-sdd/src/agents/registry.ts

### cc-sdd is the only kit with an explicit per-file conflict policy plus a backup directory
src/cli/args.ts: `export type OverwritePolicy = 'prompt' | 'skip' | 'force'` with valueFlags including overwrite, backup, kiro-dir, manifest, profile, lang, os, agent. src/cli/config.ts defaults: overwrite 'prompt', backupDir '.cc-sdd.backup'; `const effectiveOverwrite = yes && overwrite === 'prompt' ? 'force' : overwrite`. src/plan/executor.ts adds per-category policy: `export type CategoryPolicy = 'inherit' | 'overwrite' | 'skip' | 'append'` and `export type ConflictDecision = 'overwrite' | 'skip' | 'append'`; resolveAction() checks category policy first, then the effective global policy, then falls back to an interactive onConflict() callback. Artifacts are declared in templates/manifests/<agent>.json as {version: 1, artifacts: [{id, source: {type: templateDir|templateFile, fromDir/from, toDir, rename?}, when: {agent}}]} with {{AGENT}}, {{AGENT_COMMANDS_DIR}}, {{AGENT_DOC}}, {{KIRO_DIR}} placeholders.
SRC: https://github.com/gotalab/cc-sdd/blob/main/tools/cc-sdd/src/plan/executor.ts

### Agent OS v3.0 (released 2026-01-20, last commit 2026-05-05) is Claude-Code-only, has no version file in the project, and no checksums
config.yml at the base install is just `version: 3.0` + `default_profile: default` + optional profile inheritance. scripts/project-install.sh writes only two things into a project: agent-os/standards/ (from the profile inheritance chain, base-first so later profiles override) and .claude/commands/agent-os/ (a flat cp of commands/agent-os/*.md). Edit protection is a single interactive prompt: confirm_standards_overwrite() warns 'This will overwrite your existing standards with standards from the <profile> profile' and reads y/N, suggesting `--commands-only` to 'update only commands without touching standards'. Only 5 commands ship: discover-standards, index-standards, inject-standards, plan-product, shape-spec. CHANGELOG v3.0 explains the shrink: spec writing now defers to Plan mode, task breakdown to the harness's todo list, and 'Implementation/orchestration phases retired—frontier models handle this well on their own now.'
SRC: https://github.com/buildermethods/agent-os/blob/main/scripts/project-install.sh

### Claude Code plugin.json is fully optional; `name` is the only required field, and unrecognized top-level fields are ignored by design
'The manifest is optional. If omitted, Claude Code auto-discovers components in default locations and derives the plugin name from the directory name.' 'Claude Code ignores top-level fields it does not recognize. You can keep metadata from another ecosystem in plugin.json and the plugin still loads. This makes it practical to maintain one manifest that doubles as a VS Code or Cursor extension manifest, an npm package.json, or an MCPB/DXT bundle manifest.' `claude plugin validate` reports them as warnings; `--strict` turns warnings into errors. Wrong-type values for recognized fields are load errors, except `experimental` and `metadata` which are ignored with a warning.
SRC: https://code.claude.com/docs/en/plugins-reference.md

### Plugin path fields differ in whether they replace or extend the default directory — `skills` is the only additive one
'Replaces the default: commands, agents, workflows, outputStyles, experimental.themes, experimental.monitors.' 'Adds to the default: skills. The default skills/ directory is always scanned, and directories listed in skills are loaded alongside it. Exception: for a marketplace entry whose source resolves to the marketplace root, declaring specific subdirectories replaces the default skills/ scan.' 'Own merge rules: hooks, MCP servers, and LSP servers.' All paths must start with './' except `skills` which also accepts '.' (and '.' failed validation before v2.1.221 — use './' for compatibility). A plugin with SKILL.md at its root, no skills/ subdir and no skills field auto-loads as a single-skill plugin.
SRC: https://code.claude.com/docs/en/plugins-reference.md

### Plugin hooks MERGE with user and project hooks — they do not override
Claude Code hooks doc: 'Define plugin hooks in hooks/hooks.json with an optional top-level `description` field. When a plugin is enabled, its hooks merge with your user and project hooks.' Separately: 'Hook entries merge across settings levels rather than replacing each other: user, project, and local settings add their own hooks without removing managed ones, and the disableAllHooks setting can't disable managed hooks from outside managed settings.' Plugin hooks support the same ~30 lifecycle events as user hooks and five hook types: command, http, mcp_tool, prompt, agent.
SRC: https://code.claude.com/docs/en/hooks.md

### Confirmed gap: plugin-shipped agents cannot declare hooks, mcpServers, or permissionMode
Verbatim from the plugin reference: 'Plugin agents support name, description, model, effort, maxTurns, tools, disallowedTools, skills, memory, background, and isolation frontmatter fields. The only valid isolation value is "worktree". For security reasons, hooks, mcpServers, and permissionMode are not supported for plugin-shipped agents.' Agents appear in @-mention typeahead under a scoped name like my-plugin:code-reviewer.
SRC: https://code.claude.com/docs/en/plugins-reference.md

### Confirmed gap: ${user_config.*} is rejected in shell-form hook commands, monitor commands, and MCP headersHelper
'Fields that run in a shell reject ${user_config.*}: substituting a configured value into a shell command would let the shell run whatever that value contains, so the component fails with an error instead.' Workarounds table — shell-form hook commands: 'Use exec form with args, or read CLAUDE_PLUGIN_OPTION_<KEY> from the hook's environment'; monitor commands and MCP headersHelper: 'Read the value from a config file in the script'. 'Before v2.1.207, these fields substituted ${user_config.KEY} values.' All userConfig values are exported to hook processes as CLAUDE_PLUGIN_OPTION_<KEY>. Non-sensitive values go to pluginConfigs in user settings.json; sensitive ones to the macOS Keychain or ~/.claude/.credentials.json (~2KB shared limit with OAuth tokens). Project .claude/settings.json pluginConfigs entries are IGNORED (a cloned repo could otherwise inject values into hook commands); enabledPlugins still honors project settings.
SRC: https://code.claude.com/docs/en/plugins-reference.md

### ${CLAUDE_PLUGIN_ROOT} is the plugin's install directory in the versioned cache and CHANGES on every update; ${CLAUDE_PLUGIN_DATA} is the persistent sibling
'${CLAUDE_PLUGIN_ROOT} changes when the plugin updates. The previous version's directory remains on disk for a grace period after an update, but treat it as ephemeral and don't write state there.' 'When a plugin updates mid-session, hook commands, monitors, MCP servers, and LSP servers keep using the previous version's path. Run /reload-plugins to switch hooks, MCP servers, and LSP servers to the new path; monitors require a session restart.' Plugins are copied into ~/.claude/plugins/cache except for a `command` source in link mode. The three substitution variables are ${CLAUDE_PLUGIN_ROOT}, ${CLAUDE_PLUGIN_DATA}, ${CLAUDE_PROJECT_DIR}.
SRC: https://code.claude.com/docs/en/plugins-reference.md

### There are 7 plugin source types and the version-resolution order determines whether users get pinned versions
Sources: relative path (string starting './'), github {repo, ref?, sha?}, url {url, ref?, sha?}, git-subdir {url, path, ref?, sha?} (sparse clone), npm {package, version?, registry?}, archive {url, sha256?} (requires v2.1.224+), command {command, timeout?, mode?} (requires v2.1.229+). Version resolution for all but `command`: 1) plugin.json version, 2) marketplace entry version, 3) git commit SHA (github/url/git-subdir/relative in a git marketplace), 4) SHA-256 digest first 12 chars (archive), 5) 'unknown' (npm, or local dirs outside git). 'Setting this pins the plugin to that version string, so users only receive updates when you bump it.' 'Pushing new commits without bumping it has no effect, and /plugin update reports "already at the latest version".' If set in both, plugin.json wins.
SRC: https://code.claude.com/docs/en/plugin-marketplaces.md

### Marketplace names are reserved and re-checked on every load, not just at add time
Reserved: claude-code-marketplace, claude-code-plugins, claude-plugins-official, claude-plugins-community, claude-community, anthropic-marketplace, anthropic-plugins, agent-skills, anthropic-agent-skills, knowledge-work-plugins, life-sciences, claude-for-legal, claude-for-financial-services, financial-services-plugins, first-party-plugins, healthcare. Impersonating names like 'official-claude-plugins' are also blocked. 'Claude Code re-checks reserved names every time it loads a marketplace... A marketplace that was registered under one of these names before the name became reserved stops loading.' Marketplace optional fields include metadata.pluginRoot, allowCrossMarketplaceDependenciesOn, and `renames` (map old plugin name → new name or null, requires v2.1.193+).
SRC: https://code.claude.com/docs/en/plugin-marketplaces.md

### The Agent Skills spec defines exactly 6 frontmatter fields, and using any others is a HARD ERROR on claude.ai upload / Skills API / package_skill.py
Spec fields: name (required, 1-64 chars, lowercase a-z0-9 and hyphens, no leading/trailing/consecutive hyphens, must match parent directory name), description (required, 1-1024 chars), license (optional), compatibility (optional, max 500 chars), metadata (optional, string→string map), allowed-tools (optional, space-separated, marked Experimental). Claude Code docs give the verbatim failure: 'Unexpected key(s) in SKILL.md frontmatter: argument-hint. Allowed properties are: allowed-tools, compatibility, description, license, metadata, name'. 'If you include any field the spec doesn't allow, packaging or upload fails with a hard error instead of ignoring the field.' Also: 'Claude Code-only body features, such as dynamic context injection, don't function in claude.ai chat or through the API.'
SRC: https://agentskills.io/specification

### Claude Code accepts ~22 skill frontmatter fields; 16 of them are Claude-Code-only and will break portable distribution
Full Claude Code set: name, description, when_to_use, argument-hint, arguments, disable-model-invocation, user-invocable, allowed-tools, disallowed-tools, model, effort, context, agent, background, hooks, paths, shell, metadata, license, compatibility. Only name/description/license/compatibility/metadata/allowed-tools are portable. `context: fork` runs the skill in a forked subagent (with `agent` selecting the subagent type and `background` defaulting to true). Notably `hooks` in skill frontmatter registers hooks that 'Claude Code registers when the skill is invoked and keeps running for the rest of the session'.
SRC: https://code.claude.com/docs/en/skills.md

### AGENTS.md standardizes almost nothing by design — it is plain Markdown with one precedence rule
agents.md FAQ: 'Are there required fields? No. AGENTS.md is just standard Markdown. Use any headings you like; the agent simply parses the text you provide.' Precedence: 'What if instructions conflict? The closest AGENTS.md to the edited file wins; explicit user chat prompts override everything.' Nesting: 'Place another AGENTS.md inside each package. Agents automatically read the nearest file in the directory tree... at time of writing the main OpenAI repo has 88 AGENTS.md files.' Claimed adoption: 'used by over 60k open-source projects'. Now 'stewarded by the Agentic AI Foundation under the Linux Foundation.' ~25 tools listed as honoring it including Codex, Jules, Factory, Aider, goose, opencode, Zed, Warp, VS Code, Devin, Junie, Amp, Cursor, RooCode, Gemini CLI, Kilo Code, Copilot coding agent, Ona, Windsurf, Augment Code.
SRC: https://agents.md/

### rulesync v16.12.0 (2026-08-14) is the most complete single-source→multi-tool generator found: ~35 tools × 9 feature types from one .rulesync/ tree
Source of truth is .rulesync/{rules/*.md, commands/, subagents/*.md, skills/<name>/SKILL.md, mcp.json, hooks.json, permissions.jsonc} plus a rulesync.jsonc config keyed by target with per-feature booleans. Features: rules, ignore (deprecated in favor of permissions), mcp, commands, subagents, skills, hooks, permissions, checks. CLI: `rulesync init`, `rulesync generate --targets "*" --features "*"`, `rulesync import --targets claudecode|cursor|copilot`, `rulesync convert --from cursor --to copilot,claudecode` (direct conversion with no .rulesync/ files written), `rulesync fetch <org/repo>`, `rulesync gitignore`. Distributed via npm, a Homebrew tap inside the repo, and a single-binary install.sh.
SRC: https://github.com/dyoshikawa/rulesync

### rulesync's rule format is one portable body plus optional per-tool frontmatter namespaces — the key design move for lossy targets
A .rulesync/rules/*.md file carries generic keys (root, localRoot, targets, description, globs) plus namespaced blocks consumed only by the matching adapter: `cursor: {alwaysApply, description, globs}`, `copilot: {name, excludeAgent, ...}`, `antigravity: {trigger: always_on|glob|manual|model_decision, globs, description}`, `devin: {...}`, `augmentcode: {type: always_apply|manual|agent_requested}`, `kiro: {inclusion: always|fileMatch|manual|auto, fileMatchPattern, name, description}`, `takt: {name, extends, facet}`, `agentsmd: {subprojectPath}`. Unmodeled copilot keys round-trip: 'Any other frontmatter key found in a hand-written *.instructions.md is imported into this section and written back out, so a field Rulesync does not model is not lost on regeneration.' root:true maps to AGENTS.md/CLAUDE.md; root:false maps to .cursor/rules/, .clinerules/, .opencode/memories/, .kiro/steering/ etc.
SRC: https://github.com/dyoshikawa/rulesync/blob/main/docs/reference/file-formats.md

### rulesync documents the ownership hazard of generating into directories the tool (not the generator) defined
Grok CLI note: 'Because this is a directory Grok defines rather than one Rulesync invented, a project may already have hand-written files there: Rulesync owns it from now on, so --delete removes anything in it — ~/.grok/rules/ included, in global mode — that .rulesync/rules/ does not produce. Move those files into .rulesync/rules/ first.' For shared config files it merges instead: for OpenCode/Kilo it registers generated rule files in the `instructions` array of opencode.json / kilo.jsonc and 'This merge is non-destructive: existing keys such as mcp, tools, and permission are preserved. Within the instructions list rulesync owns the entries under its managed rules directory — that subset is rebuilt from the current generate — while entries outside it pass through verbatim; the result is deduped and sorted.'
SRC: https://github.com/dyoshikawa/rulesync/blob/main/docs/reference/file-formats.md

### superpowers' SDD skill encodes a bounded review loop with a circuit breaker, plan-scoped workspace, and mandatory ledger — directly reusable as loop/graph engineering
Per task: dispatch implementer → 4 possible statuses (DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED) → one task reviewer returning TWO verdicts (spec compliance + quality) plus a '⚠️ Cannot verify from diff' class → fix loop of max 5 rounds (rounds 1-3 resume the SAME implementer agent; rounds 4-5 dispatch a fresh implementer one model tier up) → scoped re-review verdicting each finding ADDRESSED/NOT ADDRESSED → breaker at round 5 forces controller adjudication with every ruling written to the ledger. Hard rules: 'Never fix findings yourself in the controller session'; 'The controller can't tell a reviewer what to ignore' ('If the prompt you are writing contains "do not flag", "don't treat X as a defect", "at most Minor", or "the plan chose" — stop: you are pre-judging'); 'Implementers and reviewers may not spawn their own subagents'; 'Always specify the model explicitly when dispatching a subagent. An omitted model inherits your session's model.' Final: ONE fix dispatch for all findings, one scoped re-review, no second fix wave.
SRC: https://github.com/obra/superpowers/blob/main/skills/subagent-driven-development/SKILL.md

### superpowers hands artifacts to subagents as FILES, never pasted text, via three tiny bash scripts — the concrete anti-context-bloat mechanism
scripts/sdd-workspace PLAN_FILE resolves <repo-root>/.superpowers/sdd/<plan-basename>/ and writes a self-ignoring `printf '*\n' > $base/.gitignore`; comment explains it lives in the working tree not .git/ 'because Claude Code treats .git/ as a protected path and denies agent writes there'. scripts/task-brief PLAN_FILE N awk-extracts one task's heading section (fence-aware) to task-N-brief.md. scripts/review-package PLAN_FILE BASE HEAD writes commit list + `git diff --stat` + `git diff -U10` to review-<base7>..<head7>.diff. SKILL.md: 'Everything you paste into a dispatch prompt — and everything a subagent prints back — stays resident in your context for the rest of the session and is re-read on every later turn. Hand artifacts over as files.' Real-session evidence cited: 'a real session's dispatch hit 42k chars of which 99% was pasted history.'
SRC: https://github.com/obra/superpowers/blob/main/skills/subagent-driven-development/scripts/sdd-workspace

### superpowers' writing-skills meta-skill mandates TDD for documentation and warns that a workflow-summarizing description makes agents skip the skill body
'NO SKILL WITHOUT A FAILING TEST FIRST. This applies to NEW skills AND EDITS to existing skills. Write skill before testing? Delete it. Start over.' The load-bearing SDO rule: 'Description = When to Use, NOT What the Skill Does... Testing revealed that when a description summarizes the skill's workflow, an agent may follow the description instead of reading the full skill content. A description saying "code review between tasks" caused an agent to do ONE review, even though the skill's flowchart clearly showed TWO reviews.' Token targets: getting-started workflows <150 words, frequently-loaded skills <200 words total, other skills <500 words. Cross-reference rule: use `**REQUIRED SUB-SKILL:** Use superpowers:x`, never `@skills/...` because '@ syntax force-loads files immediately, consuming 200k+ context before you need them.' Frontmatter guidance points at agentskills.io/specification and says only name + description are required, max 1024 chars.
SRC: https://github.com/obra/superpowers/blob/main/skills/writing-skills/SKILL.md

### superpowers-developing-for-claude-code v0.3.1 is 8 months old (2025-12-03) and is a docs-mirror plugin, not part of the runtime architecture
Two skills: developing-claude-code-plugins (with references/plugin-structure.md, common-patterns.md, polyglot-hooks.md, troubleshooting.md) and working-with-claude-code (with ~40 references/*.md that mirror the official Claude Code docs: hooks.md, mcp.md, memory.md, iam.md, costs.md, github-actions.md, etc.). Ships two example plugins: examples/simple-greeter-plugin (plugin.json + one skill) and examples/full-featured-plugin (plugin.json + marketplace.json + commands/ + hooks/hooks.json + hooks/run-hook.cmd + hooks/session-init.sh + mcp/server.js + skills/workflow/SKILL.md). Listed in superpowers-marketplace at v0.3.1.
SRC: https://github.com/obra/superpowers-developing-for-claude-code

### superpowers-marketplace v1.0.13 is a pure catalog repo — 4 files total — listing 10 plugins, every one with strict:true and a pinned version
Only .claude-plugin/marketplace.json, README.md, LICENSE, .claude/settings.local.json. Entries: superpowers 6.3.0, superpowers-chrome 3.0.5, elements-of-style 1.0.0, episodic-memory 1.4.2, superpowers-lab 0.5.0, superpowers-developing-for-claude-code 0.3.1, superpowers-dev 0.0.2026021001 (source ref 'dev', description 'DEV BRANCH: YOU MUST UNINSTALL OTHER VERSIONS OF SUPERPOWERS BEFORE INSTALLING THIS'), claude-session-driver 4.0.0, private-journal-mcp 2.0.1, double-shot-latte 1.2.0. All use source {source: 'url', url: 'https://github.com/obra/<repo>.git'}. Superpowers is also on Anthropic's official marketplace: `/plugin install superpowers@claude-plugins-official`.
SRC: https://github.com/obra/superpowers-marketplace/blob/main/.claude-plugin/marketplace.json

### superpowers' contributor guidelines quantify the agent-slop problem and set an objective acceptance test for any new harness port
CLAUDE.md: 'This repo has a 94% PR rejection rate.' Requirements: all PRs target `dev` not `main`; 'Submitters MUST identify themselves' with model, harness, harness version and all installed plugins; zero third-party dependencies ('Superpowers is a zero-dependency plugin by design'). Explicitly rejected: '"Compliance" changes to skills... PRs that restructure, reword, or reformat skills to "comply" with Anthropic's skills documentation will not be accepted without extensive eval evidence.' The harness acceptance test is a single fixed prompt — 'Let's make a react todo list' — and 'A working integration auto-triggers the brainstorming skill before any code is written.' Not real integrations: manually copying skill files, `npx skills` runtime shims, anything requiring per-session opt-in.
SRC: https://github.com/obra/superpowers/blob/main/CLAUDE.md

### Codex required an explicitly empty hooks object to suppress Claude-hook auto-discovery — a concrete multi-harness packaging trap
RELEASE-NOTES v6.1.1 (2026-07-02): 'v6.1.0 removed the Codex hook config and its manifest hooks pointer... but with no hooks field, Codex fell back to auto-discovering hooks/hooks.json, the Claude Code SessionStart hook that the marketplace ships from the repo root, and re-registered it along with its install-time trust prompt. The Codex manifest now declares an explicit empty hooks object (hooks: {}), which Codex reads as "no hooks" instead of reaching the auto-discovery fallback. An absent field, [], and an empty inline list all collapse back to the fallback, so the value has to be exactly {}.'
SRC: https://github.com/obra/superpowers/blob/main/RELEASE-NOTES.md

### superpowers v6.1.0 explicitly trimmed the bootstrap because it is paid every session — the clearest statement of the per-session context tax
RELEASE-NOTES v6.1.0 (2026-06-30), section 'Lower Per-Session Token Cost': 'The using-superpowers bootstrap is injected into every session, so its size is paid for constantly. This release trims it and the per-harness references it points to, without dropping behavior-shaping content.' Cuts made: replaced a graphviz skill-flow diagram with the prose it encoded, folded the Instruction-Priority section into User Instructions, dropped the per-platform 'How to Access Skills' walkthrough, trimmed Platform Adaptation to harnesses that still ship a reference file, and deleted claude-code-tools.md and copilot-tools.md entirely because they 'had nothing harness-specific left'. The Red Flags rationalization table and user-instruction precedence rules were kept unchanged.
SRC: https://github.com/obra/superpowers/blob/main/RELEASE-NOTES.md

## EXAMPLES
### superpowers SessionStart hook — the entire cross-harness bootstrap, verbatim core
FILE: hooks/session-start (extensionless on purpose) + hooks/hooks.json + hooks/run-hook.cmd
```
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
using_superpowers_content=$(cat "${PLUGIN_ROOT}/skills/using-superpowers/SKILL.md" 2>&1 || echo "Error reading using-superpowers skill")

escape_for_json() {
    local s="$1"
    s="${s//\\/\\\\}"; s="${s//\"/\\\"}"; s="${s//$'\n'/\\n}"; s="${s//$'\r'/\\r}"; s="${s//$'\t'/\\t}"
    printf '%s' "$s"
}
using_superpowers_escaped=$(escape_for_json "$using_superpowers_content")
session_context="<EXTREMELY_IMPORTANT>\nYou have superpowers.\n\n**Below is the full content of your 'superpowers:using-superpowers' skill - your introduction to using skills. For all other skills, use the 'Skill' tool:**\n\n${using_superpowers_escaped}\n</EXTREMELY_IMPORTANT>"

# Claude Code reads BOTH additional_context and hookSpecificOutput without
# deduplication, so we must emit only the field the current platform consumes.
if [ -n "${CURSOR_PLUGIN_ROOT:-}" ]; then
  printf '{\n  "additional_context": "%s"\n}\n' "$session_context" | cat
elif [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -z "${COPILOT_CLI:-}" ]; then
  printf '{\n  "hookSpecificOutput": {\n    "hookEventName": "SessionStart",\n    "additionalContext": "%s"\n  }\n}\n' "$session_context" | cat
else
  printf '{\n  "additionalContext": "%s"\n}\n' "$session_context" | cat
fi
exit 0

# ---- hooks/hooks.json ----
{
  "hooks": {
    "SessionStart": [
      { "matcher": "startup|clear|compact",
        "hooks": [ { "type": "command",
                     "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd\" session-start",
                     "shell": "bash", "async": false } ] }
    ]
  }
}

# ---- hooks/hooks-cursor.json (note: different schema entirely) ----
{ "version": 1, "hooks": { "sessionStart": [ { "command": "./hooks/run-hook.cmd session-start" } ] } }
```
SRC: https://github.com/obra/superpowers/blob/main/hooks/session-start

### superpowers polyglot Windows/Unix hook wrapper — one file parsed by both cmd.exe and bash
FILE: hooks/run-hook.cmd — MUST be LF-only (.gitattributes pins `*.cmd text eol=lf`)
```
: << 'CMDBLOCK'
@echo off
REM On Windows: cmd.exe runs the batch portion, which finds and calls bash.
REM On Unix: the shell interprets this as a script (: is a no-op in bash).
REM Hook scripts use extensionless filenames (e.g. "session-start" not
REM "session-start.sh") so Claude Code's Windows auto-detection -- which
REM prepends "bash" to any command containing .sh -- doesn't interfere.
if "%~1"=="" ( echo run-hook.cmd: missing script name >&2 & exit /b 1 )
set "HOOK_DIR=%~dp0"
if exist "C:\Program Files\Git\bin\bash.exe" (
    "C:\Program Files\Git\bin\bash.exe" "%HOOK_DIR%%~1" %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)
where bash >nul 2>nul
if %ERRORLEVEL% equ 0 ( bash "%HOOK_DIR%%~1" %2 %3 %4 %5 %6 %7 %8 %9 & exit /b %ERRORLEVEL% )
REM No bash found - exit silently rather than error
exit /b 0
CMDBLOCK

# Unix: run the named script directly
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_NAME="$1"
shift
exec bash "${SCRIPT_DIR}/${SCRIPT_NAME}" "$@"
```
SRC: https://github.com/obra/superpowers/blob/main/hooks/run-hook.cmd

### The three per-harness bootstrap shapes, side by side — Shape A (hook, above), Shape B (in-process), Shape C (instructions file)
FILE: .opencode/plugins/superpowers.js | .pi/extensions/superpowers.ts | GEMINI.md + gemini-extension.json
```
// SHAPE B — OpenCode: register skills dir via config hook, inject via message transform
export const SuperpowersPlugin = async ({ client, directory }) => {
  const superpowersSkillsDir = path.resolve(__dirname, '../../skills');
  return {
    config: async (config) => {                       // no symlinks, no user-file edits
      config.skills = config.skills || {};
      config.skills.paths = config.skills.paths || [];
      if (!config.skills.paths.includes(superpowersSkillsDir))
        config.skills.paths.push(superpowersSkillsDir);
    },
    // Inject into the FIRST USER message, not a system message:
    //   1. Token bloat from system messages repeated every turn (#750)
    //   2. Multiple system messages breaking Qwen and other models (#894)
    'experimental.chat.messages.transform': async (_input, output) => {
      const bootstrap = getBootstrapContent();        // module-level cached
      const firstUser = output.messages.find(m => m.info.role === 'user');
      if (firstUser.parts.some(p => p.type === 'text' && p.text.includes('EXTREMELY_IMPORTANT'))) return;
      firstUser.parts.unshift({ ...firstUser.parts[0], type: 'text', text: bootstrap });
    }
  };
};

// SHAPE B — Pi: re-arm on session_start AND session_compact, disarm on agent_end
export default function superpowersPiExtension(pi: ExtensionAPI) {
  let injectBootstrap = true;
  pi.on("resources_discover", async () => ({ skillPaths: [skillsDir] }));
  pi.on("session_start",   async () => { injectBootstrap = true;  });
  pi.on("session_compact", async () => { injectBootstrap = true;  });   // survives compaction
  pi.on("agent_end",       async () => { injectBootstrap = false; });
  pi.on("context", async (event) => {
    if (!injectBootstrap) return;
    if (event.messages.some(messageContainsBootstrap)) return;
    const insertAt = firstNonCompactionSummaryIndex(event.messages);   // insert AFTER summaries
    return { messages: [...event.messages.slice(0, insertAt), bootstrapMessage, ...event.messages.slice(insertAt)] };
  });
}

# SHAPE C — Gemini: GEMINI.md is TWO LINES, shipped inside the extension
@./skills/using-superpowers/SKILL.md
@./skills/using-superpowers/references/gemini-tools.md

# gemini-extension.json
{ "name": "superpowers", "description": "...", "version": "6.3.0", "contextFileName": "GEMINI.md" }
```
SRC: https://github.com/obra/superpowers/blob/main/.opencode/plugins/superpowers.js

### superpowers declarative multi-manifest version sync — the file plus how the script uses it
FILE: .version-bump.json at repo root + scripts/bump-version.sh
```
{
  "files": [
    { "path": "package.json",                  "field": "version" },
    { "path": ".hermes-plugin/plugin.yaml",     "field": "version" },
    { "path": ".claude-plugin/plugin.json",     "field": "version" },
    { "path": ".cursor-plugin/plugin.json",     "field": "version" },
    { "path": ".codex-plugin/plugin.json",      "field": "version" },
    { "path": ".devin-plugin/plugin.json",      "field": "version" },
    { "path": ".kimi-plugin/plugin.json",       "field": "version" },
    { "path": ".claude-plugin/marketplace.json","field": "plugins.0.version" },
    { "path": "gemini-extension.json",          "field": "version" }
  ],
  "audit": { "exclude": ["CHANGELOG.md","RELEASE-NOTES.md","node_modules",".git",".version-bump.json","scripts/bump-version.sh"] }
}

# Usage:
#   bump-version.sh 6.4.0    -> rewrites every declared field (jq for .json, yq for .yaml),
#                               dotted paths like plugins.0.version -> .plugins[0].version
#   bump-version.sh --check  -> prints each path + version; "DRIFT DETECTED" if not all equal
#   bump-version.sh --audit  -> --check, then greps the repo for the current version string and
#                               lists "UNDECLARED files containing '<ver>'" so a manifest you
#                               forgot to add to .version-bump.json is caught, not shipped stale
```
SRC: https://github.com/obra/superpowers/blob/main/.version-bump.json

### superpowers SDD file-handoff scripts — how to keep diffs and task text OUT of the controller's context
FILE: skills/<skill>/scripts/<name> (extensionless, executable, invoked by relative path from the skill dir)
```
# scripts/sdd-workspace PLAN_FILE  -> prints <repo-root>/.superpowers/sdd/<plan-basename>/
slug=$(basename "$plan" .md)
root=$(git rev-parse --show-toplevel)
base="$root/.superpowers/sdd"
dir="$base/$slug"
mkdir -p "$dir"
printf '*\n' > "$base/.gitignore"      # self-ignoring: no tracked file is modified
cd "$dir" && pwd
# Why the working tree and not .git/: "Claude Code treats .git/ as a protected path and denies
# agent writes there -- which blocks an implementer subagent from writing its report file."
# Why per-plan: "A stale ledger misread as current progress makes controllers skip whole task
# sequences -- plan-scoping removes that failure structurally."

# scripts/task-brief PLAN_FILE N [OUT]  -> extracts ONE task's section, fence-aware
awk -v n="$n" '
  /^```/ { infence = !infence }
  !infence && /^#+[ \t]+Task[ \t]+[0-9]+/ {
    intask = ($0 ~ ("^#+[ \t]+Task[ \t]+" n "([^0-9]|$)"))
  }
  intask { print }
' "$plan" > "$out"

# scripts/review-package PLAN_FILE BASE HEAD [OUT] -> one file the reviewer Reads once
{
  echo "# Review package: ${base}..${head}"; echo
  echo "## Commits";       git log --oneline "${base}..${head}"; echo
  echo "## Files changed"; git diff --stat  "${base}..${head}"; echo
  echo "## Diff";          git diff -U10    "${base}..${head}"
} > "$out"
# Default OUT is review-<base7>..<head7>.diff so each fix round gets a distinct fresh file.
# BASE is the commit recorded BEFORE dispatching -- "never HEAD~1, which silently drops all
# but the last commit of a multi-commit task."
```
SRC: https://github.com/obra/superpowers/blob/main/skills/subagent-driven-development/scripts/review-package

### OpenSpec's 39-tool registry — the whole cross-tool mapping in one declarative array
FILE: src/core/config.ts; output path is COMPUTED as <skillsDir>/skills/<skill-name>/SKILL.md
```
export interface AIToolOption {
  name: string; value: string; available: boolean; successLabel?: string;
  skillsDir?: string;          // e.g. '.claude' - /skills suffix per Agent Skills spec
  legacySkillsDirs?: string[]; // former roots read for detection and migrated AFTER replacement
  globalSkillsDir?: string;    // resolved from the user's home directory
  detectionPaths?: string[];   // override skillsDir for auto-detection; any existing path triggers
  setupNote?: string;          // manual step required before the tool picks up generated files
  requiresIdeRestart?: boolean;
}

export const AI_TOOLS: AIToolOption[] = [
  { name: 'Claude Code', value: 'claude', available: true, successLabel: 'Claude Code', skillsDir: '.claude' },
  { name: 'Codex', value: 'codex', available: true, skillsDir: '.agents',
    legacySkillsDirs: ['.codex'], detectionPaths: ['.agents/skills', '.codex/skills'] },
  { name: 'GitHub Copilot', value: 'github-copilot', available: true, skillsDir: '.github',
    detectionPaths: ['.github/copilot-instructions.md', '.github/instructions',
                     '.github/workflows/copilot-setup-steps.yml', '.github/prompts',
                     '.github/agents', '.github/skills', '.github/.mcp.json'],
    requiresIdeRestart: true },
  { name: 'Hermes Agent', value: 'hermes', available: true, skillsDir: '.hermes',
    detectionPaths: ['.hermes', 'HERMES.md', '.hermes.md'],
    setupNote: "Hermes only loads skills from ~/.hermes/skills by default. Add this project's .hermes/skills directory to skills.external_dirs in ~/.hermes/config.yaml..." },
  { name: 'MiniMax Code', value: 'minimax-code', available: true, globalSkillsDir: '.minimax' },
  { name: 'Shared .agents skills', value: 'agents', available: true, skillsDir: '.agents',
    detectionPaths: ['.agents/skills'] }
  // ...33 more
];

// Rebrands do not break scripted --tools invocations:
export const TOOL_ID_ALIASES: Record<string, string> = { windsurf: 'devin' };

// Path resolution (src/core/shared/skill-paths.ts):
export function resolveToolSkillsDir(projectRoot, tool, options = {}) {
  if (tool.globalSkillsDir) {
    const homeDir = options.homeDir ?? process.env.USERPROFILE ?? process.env.HOME ?? os.homedir();
    return path.join(homeDir, tool.globalSkillsDir, 'skills');
  }
  if (tool.skillsDir) return path.join(projectRoot, tool.skillsDir, 'skills');
  throw new Error(`Tool '${tool.value}' does not support skill generation.`);
}
```
SRC: https://github.com/Fission-AI/OpenSpec/blob/main/src/core/config.ts

### OpenSpec's user-edit detection: normalize the generated-version stamp, then compare content against current + all historical bodies
FILE: src/core/shared/skill-content-equivalence.ts and src/core/github-copilot/cloud-agent.ts
```
// Normalizes BOM, CRLF, and a VALID semver in `generatedBy` so a version bump alone
// is not mistaken for a user edit. "Free-form generatedBy text in the instructions
// remains material."
function normalizeGeneratedSkill(content: string): string {
  const normalized = content.replace(/^﻿/, '').replace(/\r\n/g, '\n');
  const frontmatter = normalized.match(/^---\n[\s\S]*?\n---(?:\n|$)/)?.[0];
  if (!frontmatter) return normalized;
  const versionLine = /^(\s*generatedBy:\s*)(?:"([^"\n]+)"|'([^'\n]+)'|([^\s"'#]+))\s*$/m;
  const normalizedFrontmatter = frontmatter.replace(versionLine, (line, prefix, dq, sq, bare) => {
    const version = dq ?? sq ?? bare;
    return version && GENERATED_VERSION.test(version) ? `${prefix}"<generated-version>"` : line;
  });
  return normalizedFrontmatter + normalized.slice(frontmatter.length);
}

// The managed-file test: exact match against the CURRENT body, or ANY previously shipped body.
const OPENSPEC_MANAGED_MARKER = 'Generated by OpenSpec for GitHub Copilot coding agent support.';
function isCurrentCopilotCloudFile(relPath, content) {
  return normalizeLineEndings(content) === COPILOT_CLOUD_FILE_CONTENTS[relPath];
}
function isLegacyCopilotCloudFile(relPath, content) {
  return getLegacyCopilotCloudFileContents(relPath).includes(normalizeLineEndings(content));
}
function isManagedCopilotCloudFile(relPath, content) {
  return isCurrentCopilotCloudFile(relPath, content) || isLegacyCopilotCloudFile(relPath, content);
}
// Anything that matches neither is USER-OWNED: findUnmanagedCloudFiles() collects it and
// init/update report it instead of overwriting.

// The generated skill body (src/core/shared/skill-generation.ts):
// ---
// name: openspec-propose
// description: ...
// allowed-tools: Bash(openspec:*)     <- OPENSPEC_CLI_ALLOWED_TOOLS
// license: MIT
// compatibility: Requires openspec CLI.
// metadata:
//   author: openspec
//   version: "1.0"
//   generatedBy: "1.9.0"
// ---
```
SRC: https://github.com/Fission-AI/OpenSpec/blob/main/src/core/shared/skill-content-equivalence.ts

### spec-kit's per-integration output contract — 42 self-contained subpackages, one declarative dict each
FILE: src/specify_cli/integrations/<key>/__init__.py, registered in INTEGRATION_REGISTRY
```
class ClaudeIntegration(SkillsIntegration):
    key = "claude"
    config = { "name": "Claude Code", "folder": ".claude/", "commands_subdir": "skills",
               "install_url": "...", "requires_cli": True }
    registrar_config = { "dir": ".claude/skills", "format": "markdown",
                         "args": "$ARGUMENTS", "extension": "/SKILL.md" }
    multi_install_safe = True
    CANONICAL_TO_NATIVE = { "session_start": "SessionStart", "pre_tool_use": "PreToolUse",
                            "post_tool_use": "PostToolUse", "session_end": "SessionEnd",
                            "user_prompt_submit": "UserPromptSubmit", "stop": "Stop" }
    events_config_file = ".claude/settings.json"
    events_format = "json-nested"

# Representative registrar_config values across the 42 (dir / format / args / extension):
#   claude          .claude/skills          markdown  $ARGUMENTS      /SKILL.md
#   codex, agy      .agents/skills          markdown  $ARGUMENTS      /SKILL.md
#   copilot         .github/skills          markdown  $ARGUMENTS      /SKILL.md
#                 + .github/agents          markdown  $ARGUMENTS      .agent.md
#   cursor_agent    .cursor/skills          markdown  $ARGUMENTS      /SKILL.md
#   gemini          .gemini/commands        toml      {{args}}        .toml
#   goose           .goose/recipes          yaml      {{args}}        .yaml
#   firebender      .firebender/commands    markdown  $ARGUMENTS      .mdc
#   forge           .forge/commands         markdown  {{parameters}}  .md   (invoke_separator "-")
#   cline           .clinerules/workflows   markdown  $ARGUMENTS      .md   (invoke_separator "-")
#   hermes          ~/.hermes/skills        markdown  $ARGUMENTS      /SKILL.md   (GLOBAL)
#   generic         ""  <- set dynamically from --commands-dir

# Frontmatter is deliberately Agent-Skills-spec-portable (src/specify_cli/agents.py):
@staticmethod
def build_skill_frontmatter(agent_name, skill_name, description, source) -> dict:
    """Build consistent SKILL.md frontmatter across all skill generators."""
    return { "name": skill_name, "description": description,
             "compatibility": "Requires spec-kit project structure with .specify/ directory",
             "metadata": { "author": "github-spec-kit", "source": source } }
# argument-hint is added ONLY for integrations exposing inject_argument_hint (currently Claude),
# "leaving build_skill_frontmatter's shared shape unchanged for every other agent."
```
SRC: https://github.com/github/spec-kit/blob/main/src/specify_cli/agents.py

### BMAD's 47-platform install table and its checksum-based re-run policy
FILE: tools/installer/ide/platform-codes.yaml + tools/installer/file-ops.js + _bmad/_config/
```
# platform-codes.yaml — header comment states the cross-tool convergence explicitly:
#   "Multiple platforms may share the same target_dir or global_target_dir — many tools
#    read from the shared `.agents/skills/` and `~/.agents/skills/` cross-tool standard.
#    Paths verified against each tool's primary docs as of 2026-04-25."
platforms:
  claude-code:
    name: "Claude Code"
    preferred: true
    installer:
      target_dir: .claude/skills
      global_target_dir: ~/.claude/skills
  github-copilot:
    name: "GitHub Copilot"
    preferred: true
    installer:
      target_dir: .agents/skills
      global_target_dir: ~/.agents/skills
      commands_target_dir: .github/agents
      commands_extension: .agent.md
      commands_body_template: "LOAD the FULL {project-root}/{target_dir}/{canonicalId}/SKILL.md, READ its entire contents and follow its directions exactly!"
      commands_filter: agents-only   # detected by reading each skill's customize.toml for an [agent] section
  codex:  { name: "Codex",  preferred: true,  installer: { target_dir: .agents/skills, global_target_dir: ~/.codex/skills } }
  cursor: { name: "Cursor", preferred: true,  installer: { target_dir: .agents/skills, global_target_dir: ~/.agents/skills } }

// file-ops.js syncDirectory() — hash first, mtime as tiebreak, never clobber a user edit
if (await fs.pathExists(destFile)) {
  const sourceHash = await this.getFileHash(sourceFile);
  const destHash   = await this.getFileHash(destFile);
  if (sourceHash === destHash) {
    await fs.copy(sourceFile, destFile, { overwrite: true });   // identical, safe to update
  } else {
    const sourceStats = await fs.stat(sourceFile);
    const destStats   = await fs.stat(destFile);
    if (sourceStats.mtime > destStats.mtime) {
      await fs.copy(sourceFile, destFile, { overwrite: true }); // source is newer, update
    }
    // Otherwise, preserve user modifications
  }
} else { await fs.ensureDir(path.dirname(destFile)); await fs.copy(sourceFile, destFile); }

# Project-side state written by the installer:
#   _bmad/_config/manifest.yaml       {installation:{version,installDate,lastUpdated}, modules:[...], ides:[...]}
#   _bmad/_config/files-manifest.csv  header: type,name,module,path,hash   (hash = SHA256 per file)
```
SRC: https://github.com/bmad-code-org/BMAD-METHOD/blob/main/tools/installer/ide/platform-codes.yaml

### BMAD's three-layer customization override — the best 'never edit installed files' contract found
FILE: _bmad/custom/{skill-name}.user.toml (gitignored) > _bmad/custom/{skill-name}.toml (committed) > <skill>/customize.toml (shipped default)
```
Priority 1 (wins): _bmad/custom/{skill-name}.user.toml  (personal, gitignored)
Priority 2:        _bmad/custom/{skill-name}.toml        (team/org, committed)
Priority 3 (last): skill's own customize.toml            (defaults)

# "Every customizable skill ships a customize.toml file with its defaults. This file defines the
#  skill's complete customization surface -- read it to see what's customizable. You never edit
#  this file. Instead, you create sparse override files containing only the fields you want to change."
# "The _bmad/custom/ folder starts empty. Files only appear when someone actively customizes."

# Merge rules -- by SHAPE, not by field name ("Field names are never special-cased"):
#  Scalar (string,int,bool,float)  -> override wins
#  Table                           -> deep merge (recursively apply these rules)
#  Array of tables where EVERY item shares the same identifier field (all `code`, or all `id`)
#                                  -> merge by that key: matching keys REPLACE in place, new keys APPEND
#  Any other array (scalars; tables with no identifier; arrays mixing `code` and `id`)
#                                  -> APPEND: base items first, then team items, then user items
#
# "No removal mechanism. Overrides cannot delete base items. If you need to suppress a default menu
#  item, override it by `code` with a no-op description or prompt. If you need to restructure an
#  array more deeply, fork the skill."
#
# Read-only trap: agent.name and agent.title live in customize.toml as source-of-truth metadata but
# the SKILL.md does not read them at runtime -- "Putting name = \"Bob\" in an override file has no effect."
#
# Resolver: src/scripts/resolve_customization.py, stdlib tomllib, run via `uv run`.
# Guided authoring: the `bmad-customize` skill scans what's customizable and writes the override for you.
```
SRC: https://github.com/bmad-code-org/BMAD-METHOD/blob/main/docs/how-to/customize-bmad.md

### cc-sdd's declarative artifact manifest + tri-state conflict policy — the cleanest small installer design
FILE: templates/manifests/<agent-id>.json + src/plan/executor.ts
```
// templates/manifests/claude-code-skills.json
{
  "version": 1,
  "artifacts": [
    { "id": "skills",
      "source": { "type": "templateDir", "fromDir": "templates/agents/{{AGENT}}/skills",
                  "toDir": "{{AGENT_COMMANDS_DIR}}" },
      "when": { "agent": "claude-code-skills" } },
    { "id": "doc_main",
      "source": { "type": "templateFile", "from": "templates/agents/{{AGENT}}/docs/CLAUDE.md",
                  "toDir": ".", "rename": "{{AGENT_DOC}}" },
      "when": { "agent": "claude-code-skills" } },
    { "id": "settings_templates",
      "source": { "type": "templateDir", "fromDir": "templates/shared/settings/templates",
                  "toDir": "{{KIRO_DIR}}/settings/templates" },
      "when": { "agent": "claude-code-skills" } }
  ]
}
// Placeholders {{AGENT}}, {{AGENT_COMMANDS_DIR}}, {{AGENT_DIR}}, {{AGENT_DOC}}, {{KIRO_DIR}}
// are filled from the agent registry's `layout` + resolved config.

// src/cli/args.ts
export type OverwritePolicy = 'prompt' | 'skip' | 'force';
// src/plan/executor.ts
export type ConflictDecision = 'overwrite' | 'skip' | 'append';
export type CategoryPolicy   = 'inherit' | 'overwrite' | 'skip' | 'append';

const resolveAction = async (op, exists, resolved, opts) => {
  const categoryPolicy = resolveCategoryPolicy(op.category, opts.categoryPolicies);
  const effective = resolved.effectiveOverwrite;
  if (!exists) return categoryPolicy === 'skip' ? 'skip' : 'write';
  switch (categoryPolicy) {
    case 'skip': return 'skip';
    case 'overwrite': return 'write';
    case 'append': return 'append';
  }
  if (effective === 'skip')  return 'skip';
  if (effective === 'force') return 'write';
  const decision = await opts.onConflict?.({ relTargetPath: op.relTarget, category: op.category, sourceMode: op.sourceMode });
  return !decision || decision === 'skip' ? 'skip' : decision === 'append' ? 'append' : 'write';
};
// src/cli/config.ts defaults: overwrite 'prompt', backupDir '.cc-sdd.backup'
//   const effectiveOverwrite = yes && overwrite === 'prompt' ? 'force' : overwrite;
// CLI: npx cc-sdd@latest --claude-skills --lang ja --overwrite skip --backup .my-backup -y
```
SRC: https://github.com/gotalab/cc-sdd/blob/main/tools/cc-sdd/src/plan/executor.ts

### rulesync — one portable body + per-tool frontmatter namespaces, the generator design for lossy targets
FILE: .rulesync/{rules,commands,subagents,skills}/ + rulesync.jsonc; outputs to ~35 tool dirs
```
---
root: true              # true -> AGENTS.md / CLAUDE.md; false -> .cursor/rules/, .clinerules/, ...
localRoot: false        # true -> CLAUDE.local.md / AGENTS.local.md / .qwen/QWEN.local.md
targets: ["*"]          # "*" = all, or specific tool keys
description: "Project overview and development guidelines"
globs: ["**/*"]
agentsmd:               # AGENTS.md standard: nested files are the ONLY scoping mechanism
  subprojectPath: "packages/api"      # -> packages/api/AGENTS.md (root:false only)
cursor:
  alwaysApply: true
  globs: ["*"]
copilot:                # non-root *.instructions.md only
  name: "TypeScript Style"
  excludeAgent: "code-review"
  # "Any other frontmatter key found in a hand-written *.instructions.md is imported into this
  #  section and written back out, so a field Rulesync does not model is not lost on regeneration."
antigravity:
  trigger: "always_on"   # always_on | glob | manual | model_decision
augmentcode:
  type: "always_apply"   # always_apply | manual | agent_requested
kiro:
  inclusion: "fileMatch" # always | fileMatch | manual | auto
  fileMatchPattern: ["src/components/**/*.tsx"]
---

# Body: ONE portable markdown body, rendered per target adapter.

# rulesync.jsonc — per-target feature switches
{
  "$schema": "https://github.com/dyoshikawa/rulesync/releases/latest/download/config-schema.json",
  "targets": {
    "claudecode": { "rules": true, "commands": true, "mcp": true, "subagents": true, "skills": true, "hooks": true },
    "copilot":    { "rules": { "ruleDiscoveryMode": "explicit", "includeLocalRoot": false },
                    "commands": true, "mcp": false, "subagents": true, "skills": true, "hooks": true },
    "codexcli":   { "rules": true, "commands": false, "mcp": false, "subagents": true, "skills": true, "hooks": false }
  }
}

# Commands:
#   rulesync init
#   rulesync generate --targets "*" --features "*"
#   rulesync import   --targets claudecode|cursor|copilot     # adopt an existing repo
#   rulesync convert  --from cursor --to copilot,claudecode   # one-shot, writes no .rulesync/
#   rulesync gitignore                                        # derive ignores for generated output
```
SRC: https://github.com/dyoshikawa/rulesync/blob/main/docs/reference/file-formats.md

### RECOMMENDED repo layout for a new kit — superpowers' shape, generalized, with the generator seam added
FILE: repo root of the kit
```
my-kit/
├── skills/                              # ← THE ONLY SOURCE OF TRUTH. Tool-neutral.
│   ├── using-my-kit/
│   │   ├── SKILL.md                     # the bootstrap. Keep it <1000 tokens; it is paid EVERY session.
│   │   └── references/
│   │       ├── claude-code-tools.md     # per-harness tool mapping ONLY. Delete when empty.
│   │       └── codex-tools.md
│   ├── <skill-name>/
│   │   ├── SKILL.md                     # frontmatter: name + description ONLY (portable subset)
│   │   ├── <reference>.md               # progressive disclosure: siblings, loaded on demand
│   │   └── scripts/<name>               # extensionless, executable; artifacts-as-files helpers
│   └── ...
├── hooks/
│   ├── hooks.json                       # Claude Code:  SessionStart matcher "startup|resume|clear|compact|fork"
│   ├── hooks-cursor.json                # Cursor: {"version":1,"hooks":{"sessionStart":[...]}}  (different schema!)
│   ├── run-hook.cmd                     # polyglot cmd/bash wrapper (LF-only via .gitattributes)
│   └── session-start                    # extensionless; emits the right JSON envelope per host
├── .claude-plugin/
│   ├── plugin.json                      # name + version + metadata. Auto-discovers skills/ and hooks/hooks.json.
│   └── marketplace.json                 # dev marketplace, source "./"  (for /plugin marketplace add <path>)
├── .cursor-plugin/plugin.json           # MUST set "skills" and "hooks" explicitly (no auto-discovery)
├── .codex-plugin/plugin.json            # MUST set "hooks": {}  exactly, or hooks/hooks.json auto-registers
├── gemini-extension.json + GEMINI.md    # Shape C: contextFileName -> two @-includes
├── .agents/plugins/marketplace.json     # Codex marketplace root manifest
├── .version-bump.json                   # declarative {path, field} list for EVERY manifest
├── scripts/
│   ├── bump-version.sh                  # <ver> | --check (drift) | --audit (undeclared refs)
│   └── generate.mjs                     # ← ADD THIS: skills/ -> per-tool outputs (see below)
├── tests/<harness>/                     # per-harness manifest + bootstrap tests
├── .gitattributes                       # *.sh, *.cmd, hooks/session-start  ->  text eol=lf
├── .gitignore                           # .worktrees/  .superpowers/  node_modules/  evals/
├── CLAUDE.md  ->  symlink  AGENTS.md    # one contributor doc, two names
└── RELEASE-NOTES.md                     # dated, versioned, prose. This is your migration path.
```
SRC: https://github.com/obra/superpowers

### RECOMMENDED build/install/upgrade design — the generator seam, stated as an algorithm
FILE: scripts/generate.mjs consuming skills/ + a targets table, writing per-tool trees
```
// 1. TARGETS TABLE — one declarative array, the OpenSpec/BMAD pattern. Never branch in code.
const TARGETS = [
  { id: 'claude',  skillsDir: '.claude',  global: '~/.claude/skills' },
  { id: 'codex',   skillsDir: '.agents',  detect: ['.agents/skills', '.codex/skills'] },
  { id: 'copilot', skillsDir: '.github',  detect: ['.github/copilot-instructions.md', '.github/skills'] },
  { id: 'cursor',  skillsDir: '.cursor',  requiresIdeRestart: true },
  { id: 'agents',  skillsDir: '.agents',  detect: ['.agents/skills'] },   // vendor-neutral fallback
];
const outPath = (root, t, skill) => join(root, t.skillsDir, 'skills', skill, 'SKILL.md');

// 2. EMIT ONLY THE 6 PORTABLE FIELDS + a version stamp you can normalize away later.
const frontmatter = {
  name, description,
  'allowed-tools': 'Bash(mykit:*)',            // pre-approves; does NOT restrict
  license: 'MIT',
  compatibility: 'Requires the mykit CLI.',
  metadata: { author: 'mykit', version: '1.0', generatedBy: PKG_VERSION },
};
// Add Claude-only fields (context: fork, argument-hint, model, hooks) ONLY behind a per-target
// capability check — they are a HARD ERROR on claude.ai upload / Skills API / package_skill.py.

// 3. RE-RUN SAFETY — content fingerprint, not mtime, not markers (OpenSpec's design):
const isManaged = (body) =>
  norm(body) === norm(currentBody) || LEGACY_BODIES.some(b => norm(body) === norm(b));
// norm() strips BOM, normalizes CRLF, and rewrites a VALID semver in metadata.generatedBy to a
// placeholder, so a version bump alone never looks like a user edit.
// if (!exists)        -> write
// else if (isManaged) -> overwrite silently (and delete if the skill was removed upstream)
// else               -> PRESERVE, and PRINT the path. Never a silent skip.
// Keep LEGACY_BODIES append-only forever; it is what lets you reclaim files you shipped in v1.

// 4. USER CUSTOMIZATION — give it a protected home so nobody edits generated files (BMAD's model):
//    mykit/custom/<skill>.toml       committed, team-wide
//    mykit/custom/<skill>.user.toml  gitignored, personal, wins
//    merge by value SHAPE: scalar->override, table->deep merge, keyed array-of-tables->merge by key,
//    other array->append. No removal mechanism; document that forking is the escape hatch.

// 5. PROJECT STATE — one file, schema-versioned, so a newer kit can refuse an older reader:
//    .mykit/state.json  { stateSchema: 1, kitVersion, targets: [...], installedAt, lastUpdated }
//    Refuse to run when state.stateSchema > STATE_SCHEMA (spec-kit's schema_too_new).

// 6. COMMIT POLICY — say it out loud in the README (OpenSpec does; it removes all ambiguity):
//    Commit the SOURCE (skills/, specs/). Generated per-tool trees: commit them if your team
//    shares one toolchain, gitignore them if not. Do NOT auto-edit the user's .gitignore.
```
SRC: https://github.com/Fission-AI/OpenSpec/blob/main/src/core/shared/skill-content-equivalence.ts

### Packaging-choice cost table — what each vehicle buys and what it forecloses
FILE: decision record for the kit's distribution strategy
```
| Capability                        | CC plugin (marketplace) | .claude/ committed to repo | npm/uvx installer (writes files) | git submodule |
|-----------------------------------|-------------------------|----------------------------|----------------------------------|---------------|
| Skills                            | yes (skills/ auto-scan) | yes                        | yes (writes per-tool trees)      | yes, via path |
| Hooks                             | yes — MERGE with user+project hooks | yes (settings.json) | yes, but you EDIT the user's settings.json | no (manual wiring) |
| Agents/subagents                  | yes, BUT no hooks / no mcpServers / no permissionMode | full frontmatter | full frontmatter | full |
| MCP servers                       | yes (auto-start w/ plugin) | yes (.mcp.json)         | yes (edits user config)          | manual        |
| LSP servers / monitors / themes   | yes                     | no                         | no                               | no            |
| userConfig prompt at enable time  | yes — but ${user_config.*} REJECTED in shell-form hook commands, monitor commands, MCP headersHelper | n/a (plain env/settings) | n/a | n/a |
| Version pinning for users         | yes — plugin.json version pins; omit it to track commit SHA | whatever the repo commit is | package version + a state file you write | submodule SHA (explicit, manual) |
| Auto-update                       | yes (background marketplace refresh; skips if version unchanged) | via git pull of the repo | user must re-run the installer  | user must `git submodule update` |
| Rollback                          | pin an older version / sha in marketplace entry | git revert       | reinstall an older package version | move the SHA |
| Works in Cursor/Codex/Copilot/... | NO — Claude Code only    | NO — Claude Code only      | YES — the only vehicle that is genuinely multi-tool | yes, if each tool is pointed at it |
| Survives `git clean -fdx`         | yes (lives in ~/.claude/plugins/cache) | no             | no                               | no            |
| Offline install                   | only from a local dir or `archive`/`command` source | yes | needs the registry (npm/PyPI) unless vendored | needs the remote once |
| Per-repo customization            | poor — plugin is global; use userConfig | excellent — it IS the repo | good — a protected custom/ dir  | poor          |
| Team onboarding cost              | one /plugin install command | zero (clone the repo)    | one npx command                  | highest (submodule literacy) |
| Blast radius of a bad release     | every user on auto-update | one repo                  | only projects that re-run it     | only repos that bump the SHA |

# RECOMMENDATION for a kit that must work across tools:
#   PRIMARY  = npm/uvx installer that generates per-tool outputs from one skills/ source
#              (this is what OpenSpec, spec-kit, cc-sdd and BMAD all converged on)
#   PLUS     = a Claude Code plugin manifest in the SAME repo for the Claude-only fast path
#              (superpowers' trick: one skills/ tree, N thin manifests, .version-bump.json to sync)
#   AVOID    = git submodule (worst onboarding, no upgrade story, no per-tool rendering)
#   AVOID    = plugin-only, if you need Cursor/Codex/Copilot — it forecloses them entirely
```
SRC: https://code.claude.com/docs/en/plugins-reference.md

## GOTCHAS
- THE BRIEF'S PREMISE IS STALE. The four-repo superpowers split (plugin / superpowers-skills / marketplace / developing-for-claude-code) describes v2.0.0 from 2025-10-12. It was reverted in v3.0.1 four days later (2025-10-16: 'We now use Anthropic's first-party skills system!'). obra/superpowers-skills has had no commit since 2025-10-14. Do NOT copy the `~/.config/superpowers/skills/` clone architecture — its own author abandoned it in under a week. Also gone: skills-search (never existed in the modern repo), commands/ (removed v5.1.0, 2026-04-30), and named agents (removed v5.1.0).
- superpowers-marketplace/README.md is itself stale and will mislead you: it still advertises '20+ battle-tested skills', '/brainstorm, /write-plan, /execute-plan commands' and a 'Skills-search tool for discovery'. None of those exist in v6.3.0 — there are 14 skills, zero commands, and no search tool. The marketplace.json in the same repo is correct (v6.3.0); only the README rotted.
- superpowers' own SessionStart matcher is `startup|clear|compact`, which silently omits `resume` and `fork`. Claude Code documents five source values (startup, resume, clear, compact, fork) and explicitly states SessionStart re-runs on resume so hooks can refresh context. Any kit copying this matcher loses its bootstrap on `--continue`/`--resume` and on `--fork-session`. Use `startup|resume|clear|compact|fork`.
- Claude Code reads BOTH `additional_context` and `hookSpecificOutput.additionalContext` without deduplication — emitting both doubles your bootstrap's token cost every session. You must sniff the host (CURSOR_PLUGIN_ROOT / CLAUDE_PLUGIN_ROOT / COPILOT_CLI) and emit exactly one envelope.
- Multi-harness manifests interfere with each other. Codex auto-discovers `hooks/hooks.json` at the repo root when its own manifest has no `hooks` field — silently registering the Claude Code SessionStart hook plus its install-time trust prompt. Per superpowers v6.1.1: 'An absent field, [], and an empty inline list all collapse back to the fallback, so the value has to be exactly {}.'
- The 6-field Agent Skills frontmatter limit is a HARD ERROR, not a warning, on claude.ai uploads, the Skills API, and package_skill.py: 'Unexpected key(s) in SKILL.md frontmatter: argument-hint. Allowed properties are: allowed-tools, compatibility, description, license, metadata, name'. Claude Code accepts ~22 fields, so a skill that works locally can be unpublishable. Anything using `context: fork`, `argument-hint`, `model`, `hooks`, `paths`, `when_to_use` etc. is Claude-Code-only.
- Plugin-shipped agents silently lose capability: 'For security reasons, hooks, mcpServers, and permissionMode are not supported for plugin-shipped agents.' If your kit's agent design depends on any of those, the plugin vehicle cannot carry it — you need `.claude/agents/` committed to the repo instead.
- ${user_config.*} is rejected in shell-form hook commands, monitor commands, and MCP headersHelper (changed in v2.1.207 — it used to substitute). Existing plugins that relied on it break. Workaround for hooks: use exec form with `args`, or read CLAUDE_PLUGIN_OPTION_<KEY> from the environment.
- pluginConfigs in a project's .claude/settings.json or settings.local.json are IGNORED (since v2.1.207) — a cloned repo could otherwise inject values into hook commands, MCP configs, LSP commands and monitor commands. Only user settings, --settings, and managed settings are read. enabledPlugins is unaffected. Don't design a kit that expects per-project plugin config via committed settings.
- Setting `version` in plugin.json PINS the plugin: 'Pushing new commits without bumping it has no effect, and /plugin update reports "already at the latest version".' A kit that ships a version string and forgets to bump it will silently never update anyone. Omitting `version` entirely makes users track the commit SHA — which is what you want for internal/team kits.
- ${CLAUDE_PLUGIN_ROOT} changes on every plugin update and the old directory is only kept 'for a grace period'. Never write state there. Worse: when a plugin updates mid-session, hooks/monitors/MCP/LSP keep using the OLD path until /reload-plugins (monitors need a full restart). Use ${CLAUDE_PLUGIN_DATA} for anything persistent.
- BMAD's syncDirectory uses mtime as the tiebreak when hashes differ ('if sourceStats.mtime > destStats.mtime, update'). A fresh npm install gives every source file a NEW mtime, so a reinstall can overwrite genuine user edits on any file whose upstream copy happens to be newer. The hash check only protects unmodified files. This is why BMAD pushes customization into the separate customize.toml layer instead.
- BMAD has NO automated v4→v6 migration. The installer offers to 'back up and remove .bmad-method'; legacy IDE commands must be deleted by hand; planning artifacts must be manually renamed and moved into _bmad-output/planning-artifacts/; and the official advice for mid-planning work is 'Consider restarting with v6 workflows.' Budget for a rewrite, not a migration.
- spec-kit's `--ai` flag no longer exists — it is `--integration`. Any script or doc still using `--ai` is broken. spec-kit's re-run policy is also the bluntest of the five: 'Template files will be merged with existing content and may overwrite existing files', with only .specify/memory/constitution.md explicitly preserved. `--force` skips even the confirmation.
- cc-sdd (v3.0.2, last commit 2026-04-27) and Agent OS (v3.0, last commit 2026-05-05) are both months stale as of 2026-08. cc-sdd additionally marks every non-skills mode with 'This mode will be removed in a future release' — building on --claude-code / --cursor / --codex rather than the -skills variants is building on a deprecated surface. Agent OS v3 is Claude-Code-only, writes no version file into the project, and its only edit protection is a single y/N prompt before it overwrites your whole standards folder.
- Generating into a directory the TOOL defined (not your generator) creates a silent ownership conflict. rulesync documents this for Grok: 'a project may already have hand-written files there: Rulesync owns it from now on, so --delete removes anything in it that .rulesync/rules/ does not produce. Move those files into .rulesync/rules/ first.' Any kit writing to .cursor/rules/ or .github/prompts/ inherits this hazard.
- Skill descriptions get silently truncated at scale — this is a platform behavior, not something your kit controls. Claude Code's listing budget is 1% of the context window and 'drops descriptions starting with the skills you invoke least'. Per-entry cap is 1,536 chars for description + when_to_use combined. A 60-skill kit will have its least-used skills degraded to name-only, killing their trigger keywords. superpowers' answer is to ship only 14 skills.
- A description that summarizes the workflow makes agents skip the skill body. superpowers documents a measured instance: 'A description saying "code review between tasks" caused an agent to do ONE review, even though the skill's flowchart clearly showed TWO reviews.' Descriptions must state triggering conditions only.
- Bash 5.3+ hangs on heredocs in this hook context (superpowers issue #571) — hence printf everywhere in hooks/session-start. Windows adds two more: PowerShell parses a quoted-path command string as an expression and dies with a parser error (#1751), and cmd.exe's quote-stripping truncates the command when the profile path contains a metacharacter like '(' (#1918). The fix is `"shell": "bash"` in hooks.json, which requires Claude Code >= 2.1.81.
- Marketplace names are reserved and RE-CHECKED on every load, not just at add time. A marketplace already registered under a name that later becomes reserved stops loading entirely and reports 'registered from an untrusted source'. 16 names are reserved plus any impersonating variant.
- Relative-path plugin sources do not resolve when a marketplace is added via a direct URL to marketplace.json (Claude Code downloads only that one file). If you distribute by URL rather than git, every plugin entry needs a non-relative source.
- AGENTS.md standardizes essentially nothing: no required fields, no schema, no frontmatter. The only normative rule is precedence ('the closest AGENTS.md to the edited file wins; explicit user chat prompts override everything'). It cannot carry skills, hooks, or tool scoping — treat it as the lowest-common-denominator instruction file, not a packaging format.
- superpowers' contributor guidelines report a 94% PR rejection rate and explicitly reject 'PRs that restructure, reword, or reformat skills to "comply" with Anthropic's skills documentation... without extensive eval evidence'. Their skill philosophy deliberately diverges from Anthropic's published guidance. Don't assume superpowers' SKILL.md conventions are the official ones — they are tuned against their own eval harness (superpowers-evals, a separate private-ish repo cloned into evals/, gitignored and NOT shipped after v6.0.2 broke installs).

## OPEN
- Whether superpowers' `evals/` harness (github.com/prime-radiant-inc/superpowers-evals, the 'drill' runner) is public — it is gitignored and excluded from the published plugin after v6.0.2 broke installs, and I did not fetch it. Its scenario format would be the most valuable artifact for anyone wanting to regression-test skill behavior, and the eval-run counts cited in RELEASE-NOTES (e.g. 'control 8/10 → treatment 5/10', '25/25 baseline and GREEN eval runs') are unverifiable without it.
- The exact token count of the superpowers SessionStart injection. I measured the source file at 3,096 chars / 485 words and estimate 700–860 tokens by two different heuristics, plus roughly 60–80 tokens of wrapper text. I did not tokenize it with a real tokenizer, and the injected payload includes the YAML frontmatter (the bash hook cats the whole file) whereas the OpenCode and Pi injectors strip it — so the three harnesses do not pay the same amount.
- Whether Claude Code's official `claude-plugins-official` marketplace currently lists superpowers at 6.3.0 or lags behind obra's own marketplace. I read both repo manifests but did not query the official marketplace catalog.
- BMAD's interactive installer prompt sequence. I read the platform-codes.yaml mapping, file-ops.js, manifest-generator.js and bmad-modules.yaml, but did not run `npx bmad-method install` or fully trace tools/installer/commands/install.js, so the exact prompt order, the module picker behavior, and how `--channel`/`--pin`/`--next` interact with `default_channel: stable` are unconfirmed.
- Whether OpenSpec's LEGACY body list for skills is genuinely append-only across all releases, or whether old generated bodies get pruned. If pruned, a project that skipped several versions would have its untouched generated skills misclassified as user-edited and silently preserved at a stale version. I found the mechanism but not a retention policy.
- How rulesync resolves collisions when two kits both claim the same output path — e.g. a repo running both `rulesync generate` and `openspec update` against `.claude/skills/`. OpenSpec has an explicit guard ('Skipped <tool>: <dir>/skills is already managed by another tool'), but I did not find the reciprocal check in rulesync.
- Whether any kit has solved offline/air-gapped install well. spec-kit moved to bundled assets ('--offline: Deprecated (no-op). All scaffolding now uses bundled assets'), and Claude Code added `archive` and `command` plugin sources, but I did not verify an end-to-end air-gapped path for any of the five installers.
- The real-world adoption split between the `.agents/skills/` cross-tool root and per-tool roots. BMAD's YAML says paths were 'verified against each tool's primary docs as of 2026-04-25' and points ~20 tools at `.agents/skills`, while OpenSpec still maps most of the same tools to their own dirs and offers `.agents` only as an explicit opt-in target. These two registries disagree about the same tools; I could not determine which is currently correct per tool.

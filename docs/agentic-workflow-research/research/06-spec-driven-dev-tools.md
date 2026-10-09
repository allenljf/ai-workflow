# Spec-driven development (SDD) tooling for AI coding agents, 2025–2026: OpenSpec, GitHub spec-kit, AWS Kiro, BMAD-METHOD, Agent OS, Tessl

## SUMMARY
Six frameworks now dominate, and they have diverged into three architectural families.

**Delta-spec family (OpenSpec, v1.9.0, 65k stars).** Splits `openspec/specs/` (living source of truth) from `openspec/changes/<name>/` (in-flight). Each change folder holds `proposal.md`, `design.md`, `tasks.md`, `.openspec.yaml`, and `specs/<capability>/spec.md` deltas written as `## ADDED/MODIFIED/REMOVED/RENAMED Requirements`. Archive merges deltas into main specs and moves the folder to `changes/archive/YYYY-MM-DD-<name>/`. Uniquely, its workflow is data-driven: `schemas/spec-driven/schema.yaml` declares artifacts with `requires:` edges plus per-artifact `instruction:` prose, so the artifact graph is forkable (`openspec schema fork`). Mid-flight change is a first-class command (`/opsx:update`) that ripples edits backwards across artifacts; `/opsx:sync` merges without archiving.

**Linear-phase family (spec-kit v0.16.4, 129k stars; Kiro).** spec-kit went from `/specify` to namespaced `/speckit.specify|plan|tasks|implement`, adding `/speckit.clarify`, `/speckit.analyze`, `/speckit.checklist`, `/speckit.converge`, `/speckit.taskstoissues`. Artifacts live per-feature in `specs/###-slug/` (spec.md, plan.md, tasks.md, research.md, data-model.md, quickstart.md, contracts/), governed by `.specify/memory/constitution.md` — non-negotiable, and constitution violations are auto-CRITICAL in analyze. Traceability is ID-based: `FR-###`/`SC-###` in spec, `[ID] [P] [Story]` tasks, and analyze emits a Requirement→Task coverage table. `converge` is strictly append-only. Kiro is the same three-doc shape (`.kiro/specs/<feature>/requirements.md|design.md|tasks.md`) but with EARS notation ("WHEN … THE SYSTEM SHALL …"), plus `.kiro/steering/` (product/tech/structure.md with `inclusion: always|fileMatch|manual|auto`) and `.kiro/hooks/*.json` event automation.

**Code-bound / role-based outliers.** Tessl binds specs to code: `.spec.md` files with YAML `targets:` globs and inline `` `[@test] ../tests/x.py` `` links, checked by `check-spec-links.sh` — the only framework with machine-verifiable spec↔code↔test traceability. BMAD v6 abandoned v4's PRD-sharding/story-file pipeline for scale-adaptive routing inside `bmad-build`, which picks the smallest safe path. Agent OS v3 (Jan 2026) *retired* its spec/task/orchestration layers entirely, deferring to plan mode and keeping only standards injection.

Direction of travel in 2026: less scaffolding, more standards injection and drift detection.

## KEY FACTS
### OpenSpec separates a living spec store from in-flight change folders
`openspec/specs/` is the source of truth (organized by domain, e.g. auth/spec.md, payments/spec.md); `openspec/changes/<name>/` holds proposals until archived. Docs: 'Specs are the source of truth — they describe how your system currently behaves. Changes are proposed modifications — they live in separate folders until you're ready to merge them.' A change folder contains proposal.md, design.md, tasks.md, .openspec.yaml (optional metadata: schema, created, skip_specs, retire_capabilities), and specs/<capability>/spec.md deltas.
SRC: https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/docs/concepts.md

### OpenSpec's workflow is defined by a forkable YAML artifact graph, not hardcoded
schemas/spec-driven/schema.yaml declares `name: spec-driven`, `version: 1`, and four artifacts (proposal, specs, design, tasks) each with `generates:`, `template:`, `instruction:` (long prose prompt) and `requires:` dependency edges. tasks `requires: [specs, design]`; design and specs both `requires: [proposal]`. A separate `apply:` block declares `requires: [tasks]`, `tracks: tasks.md`. Users fork it via `openspec schema fork` into `openspec/schemas/<name>/schema.yaml`.
SRC: https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/schemas/spec-driven/schema.yaml

### OpenSpec delta specs use four operation headers with defined archive semantics
`## ADDED Requirements` → appended to main spec; `## MODIFIED Requirements` → replaces existing requirement (MUST include full updated content); `## REMOVED Requirements` → deleted from main spec, requires **Reason** and **Migration**; `## RENAMED Requirements` → FROM:/TO: format; `## Purpose` → seeds a brand-new capability's main spec, ignored if the spec already exists. Removing the last requirement retires the capability and deletes its spec file only when `.openspec.yaml` sets `retire_capabilities: true`.
SRC: https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/docs/concepts.md

### OpenSpec archive is a 7-step transactional merge with crash recovery
1) Validates the change 2) Prompts for confirmation 3) Claims the archive destination before changing any main spec 4) Validates and merges active delta specs into openspec/specs/ 5) Moves folder to `openspec/changes/archive/YYYY-MM-DD-<name>/` 6) On failure before a complete archive is secured, restores specs and returns the change to its active path 7) If a verified fallback copy completes but staged-source cleanup fails, retains the complete archive. Flags: `-y/--yes`, `--skip-specs`, `--no-validate`.
SRC: https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/docs/cli.md

### OpenSpec ships `/opsx:update` specifically for mid-flight spec change
'Revise a change's existing planning artifacts and keep them coherent with one another. Planning artifacts only - it never edits code.' It reads `openspec status --change <name> --json`, applies the revision, then 'Reconciles the other existing artifacts in any direction (a design edit may ripple back to the proposal)', confirming each edit one artifact at a time. Guidance: if the revision changes the *intent*, start a new change instead. `/opsx:sync` merges deltas into main specs without archiving (change stays active).
SRC: https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/docs/commands.md

### OpenSpec has a CI/pre-commit drift guard: `openspec validate --archived`
'--archived is its own scope: it does not validate spec deltas (already applied at archive time), it verifies that every change under changes/archive/ has all of its tasks.md checkboxes ticked, exiting non-zero if any are unchecked. This catches changes that were archived with unfinished work — handy in a pre-commit hook.' Other flags: --all, --changes, --specs, --strict, --json, --concurrency <n> (default 6).
SRC: https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/docs/cli.md

### OpenSpec CLI surface (v1.9.0) spans 9 categories
Setup: init, update. Stores: store setup/register/unregister/remove/list/doctor. Health: doctor. Working context: context. Worksets: workset create/list/open/remove. Browsing: list, view, show. Validation: validate. Lifecycle: archive. Workflow: new change, status, instructions, templates, schemas. Schemas: schema init/fork/validate/which. Config: config. Utility: feedback, completion. Agent-facing commands all support --json. npm latest = 1.9.0 (2026-08-13); repo at 65,096 stars.
SRC: https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/docs/cli.md

### GitHub spec-kit renamed all slash commands to a `speckit.` namespace
Core: /speckit.constitution, /speckit.specify, /speckit.plan, /speckit.tasks, /speckit.implement, /speckit.taskstoissues, /speckit.converge. Optional: /speckit.clarify, /speckit.analyze, /speckit.checklist. Codex CLI and Command Code in skills mode use `$speckit-*` instead. Widely-cited bare `/specify` `/plan` `/tasks` `/implement` names are the pre-namespace form and are now stale. Latest release v0.16.4 (2026-08-14); 129,579 stars.
SRC: https://raw.githubusercontent.com/github/spec-kit/main/README.md

### spec-kit resolves templates through a 4-layer priority stack at runtime
Priority 1 (highest) Project-Local Overrides `.specify/templates/overrides/`; 2 Presets `.specify/presets/templates/`; 3 Extensions `.specify/extensions/templates/`; 4 Spec Kit Core `.specify/templates/`. 'Templates are resolved at runtime — Spec Kit walks the stack top-down and uses the first match.' Extension/preset *commands* are applied at install time into agent dirs (e.g. `.claude/commands/`). On removal the next-highest-priority version is restored automatically.
SRC: https://raw.githubusercontent.com/github/spec-kit/main/README.md

### spec-kit's constitution is a hard gate, not advice
analyze.md states: 'The project constitution (`/memory/constitution.md`) is **non-negotiable** within this analysis scope. Constitution conflicts are automatically CRITICAL and require adjustment of the spec, plan, or tasks—not dilution, reinterpretation, or silent ignoring of the principle.' plan-template.md has a `## Constitution Check` section marked '*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*'. The live file is at `.specify/memory/constitution.md`.
SRC: https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/analyze.md

### spec-kit enforces traceability with stable requirement IDs and a coverage table
analyze builds a 'Requirements inventory: For each Functional Requirement (FR-###) and Success Criterion (SC-###), record a stable key' and a 'Task coverage mapping'. Six detection passes: A Duplication, B Ambiguity (flags vague adjectives fast/scalable/secure/intuitive/robust and placeholders TODO/TKTK/???), C Underspecification, D Constitution Alignment, E Coverage Gaps (requirements with zero tasks; tasks with no mapped requirement), F Inconsistency (terminology drift, conflicting requirements). Severity: CRITICAL/HIGH/MEDIUM/LOW. Output is a findings table + 'Coverage Summary Table' with columns Requirement Key | Has Task? | Task IDs | Notes. Limit 50 findings. STRICTLY READ-ONLY.
SRC: https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/analyze.md

### spec-kit's `/speckit.converge` is the drift-closing command and is append-only
'Close the gap between what a feature's specification, plan, and tasks call for and what the codebase currently implements… append each piece of remaining work as a new, traceable task at the bottom of tasks.md'. Constraint: 'APPEND-ONLY, NEVER REWRITE — The command's only write is appending a new `## Phase N: Convergence` section to tasks.md. It MUST NOT: modify spec.md or plan.md in any way; rewrite, renumber, reorder, or delete any existing task… When the codebase already satisfies everything, the command MUST leave tasks.md byte-for-byte unchanged.' Explicitly 'not a diff tool… no git, no branch comparison, no history.'
SRC: https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/converge.md

### spec-kit organizes tasks by user story for independently shippable MVP slices
tasks-template.md format is `[ID] [P?] [Story] Description` where [P] = 'Can run in parallel (different files, no dependencies)' and [Story] = 'Which user story this task belongs to (e.g., US1, US2, US3)'. Phases: Phase 1 Setup, Phase 2 Foundational ('⚠️ CRITICAL: No user story work can begin until this phase is complete'), then per-story phases. spec-template.md prioritizes user stories P1/P2/P3 and requires each to be 'INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them, you should still have a viable MVP'.
SRC: https://raw.githubusercontent.com/github/spec-kit/main/templates/tasks-template.md

### spec-kit added an extension/preset/bundle ecosystem with hook points
CLI: `specify extension search|add`, `specify preset search|add`, `specify bundle search|info|install|validate|build`, `specify integration list`, `specify self check`, `specify self upgrade`. Commands read `.specify/extensions.yml` for `hooks.before_analyze` entries with fields {extension, command, description, prompt, optional, enabled, condition}; `optional: false` emits `EXECUTE_COMMAND: {command}` and blocks until the hook finishes. In-repo presets: constitution-sync, lean, scaffold, self-test. Extensions: agent-context, assess, bug, git, selftest.
SRC: https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/analyze.md

### Kiro uses three docs per feature under .kiro/specs/ with EARS notation
Layout example from docs: `.kiro/specs/` containing user-authentication/, product-catalog/, shopping-cart/, payment-processing/, admin-dashboard/. Each holds requirements.md (or bugfix.md for bug specs), design.md, tasks.md. EARS pattern: 'WHEN [condition/event] THE SYSTEM SHALL [expected behavior]' — example 'WHEN a user submits a form with invalid data THE SYSTEM SHALL display validation errors next to the relevant fields'. Supports WHEN, IF, WHILE, WHERE clauses. tasks.md 'References linked requirements for traceability'. Two entry modes: Requirements-First (behavior→design→tasks) and Design-First (design→requirements→tasks).
SRC: https://kiro.dev/docs/specs/feature-specs/

### Kiro steering files carry YAML frontmatter controlling when they load
Locations: workspace `.kiro/steering/` and global `~/.kiro/steering/`. Three defaults: product.md (purpose, users, features, business objectives), tech.md (frameworks, libraries, tools, constraints), structure.md (file organization, naming conventions, architectural patterns). Inclusion modes: `inclusion: always` (default), `inclusion: fileMatch` + `fileMatchPattern: "components/**/*.tsx"`, `inclusion: manual` (invoked via `#filename`), `inclusion: auto` with name/description. Live file references use `#[[file:<relative_file_name>]]`, e.g. `#[[file:api/openapi.yaml]]`. Kiro also recognizes the AGENTS.md standard.
SRC: https://kiro.dev/docs/steering/

### Kiro agent hooks are JSON files with 10 trigger types
Stored as JSON in `.kiro/hooks/` with kebab-case names (e.g. lint-on-save.json); one file may hold multiple hooks. Triggers: PostFileSave, PostFileCreate, PostFileDelete, PreToolUse (can block), PostToolUse, UserPromptSubmit (can block), SessionStart, Stop, PreTaskExec, PostTaskExec. Two action types: `command` (shell command receiving context via STDIN) and `agent` (prompt injected into the conversation).
SRC: https://kiro.dev/docs/hooks/

### Kiro propagates mid-flight spec changes via Refine and Sync Files
Requirements-First: modify requirements.md directly, then open design.md and select **Refine** to update documentation and task lists. Design-First: update design.md, then ask Kiro to regenerate requirements for feasibility validation. Both then use **Sync Files** so downstream changes reach tasks.md; selecting Sync Files in tasks.md makes 'Kiro automatically mark completed tasks'. Specs are designed to be version-controlled.
SRC: https://kiro.dev/docs/specs/best-practices/

### Kiro is the official successor to Amazon Q Developer, which is being retired
AWS: 'Kiro is an agentic development environment (IDE, CLI) built from the ground up for spec-driven development.' Timeline: May 15 2026 new Q Developer signups blocked; May 29 2026 Opus 4.6 removed from Q Developer Pro; April 30 2027 full end-of-support for IDE plugins and paid subscriptions. Migration guide at kiro.dev/docs/migrating-from-q-developer/. Note: Spec-Driven Development is a Kiro *IDE* feature — Kiro CLI has Chat, Custom Agents, MCP, Hooks, Steering, Autocomplete and Headless, but not Specs.
SRC: https://aws.amazon.com/blogs/devops/amazon-q-developer-end-of-support-announcement/

### BMAD-METHOD v6 restructured into 4 phases with named agent personas (51,968 stars)
Phase 1 Analysis (optional): bmad-brainstorming, bmad-forge-idea, bmad-deep-recon, bmad-product-brief, bmad-prfaq. Phase 2 Planning: bmad-prd (create/update/validate intents → prd.md, addendum.md, .memlog.md), bmad-ux (DESIGN.md + EXPERIENCE.md), bmad-spec (SPEC.md five-field kernel: Why, Capabilities, Constraints, Non-goals, Success signal; optional stories.yaml). Phase 3 Solutioning: bmad-architecture (ARCHITECTURE-SPINE.md), bmad-create-epics-and-stories, bmad-sprint-planning (PASS/CONCERNS/FAIL gate + sprint-status.yaml). Phase 4 Implementation: bmad-build, bmad-code-review, bmad-correct-course, bmad-retrospective.
SRC: https://raw.githubusercontent.com/bmad-code-org/BMAD-METHOD/main/docs/reference/workflow-map.md

### BMAD agent personas map to skill IDs and two-letter menu triggers
Analyst (Mary) `bmad-agent-analyst` — BP, MR, DR, TR, CB, WB, PC. Product Manager (John) `bmad-agent-pm` — PRD, CE, IR, CC. Architect (Winston) `bmad-agent-architect` — CA, IR. Developer (Amelia) `bmad-agent-dev` — BD, QA, CR, SP, ER. UX Designer (Sally) `bmad-agent-ux-designer` — CU. Technical Writer (Paige) is on hiatus. Each agent is generated by the installer as a skill; typing the trigger code loads a structured workflow file.
SRC: https://raw.githubusercontent.com/bmad-code-org/BMAD-METHOD/main/docs/reference/agents.md

### BMAD's 'scale-adaptive' idea now lives inside bmad-build as routing, not project levels
'bmad-build is the canonical implementation workflow for all development work. It accepts anything from free-form intent or an issue to a fully planned story.' Step 2 'Route to the smallest safe path': 'the workflow decides whether this is a true one-shot change or whether it needs the fuller path. Small, zero-blast-radius changes can go straight to implementation. Everything else goes through planning.' Human checkpoints reduced to three: intent clarification, spec approval, review of the final product. Step 4 'Diagnose failure at the right layer' — review findings decide whether the fault entered at intent, spec generation, or local implementation, and regeneration restarts from that layer. bmad-build-auto orchestrates unattended iterations.
SRC: https://raw.githubusercontent.com/bmad-code-org/BMAD-METHOD/main/docs/explanation/build.md

### BMAD v4→v6 is a breaking restructure; v4 sharding artifacts must be relocated
v6 unified structure: `_bmad/` single installation folder containing `_config/` (with `agents/` customization files), `core/`, `bmm/` (BMad Method module), `bmb/` (BMad Builder), `cis/` (Creative Intelligence Suite). v4's `.bmad-method` folder is backed up and removed by the installer. Legacy skills move from `.claude/commands/` to `.claude/skills/`. Existing planning docs go to `_bmad-output/planning-artifacts/` with PRD/brief/architecture/ux-design in the filename; 'Sharded documents can be in named subfolders'. In-progress stories: place epics.md or epics/epic*.md there and run bmad-sprint-planning. Requires Node.js 20.12+.
SRC: https://raw.githubusercontent.com/bmad-code-org/BMAD-METHOD/main/docs/how-to/upgrade-to-v6.md

### Agent OS v3 (Jan 2026) deliberately RETIRED its spec-writing and orchestration layers
'Agent OS v3 is a major release that refocuses the framework on what it does best—establishing and injecting standards—while deferring to modern AI tools for the parts they now handle better.' Rationale: 'Spec writing — Now best handled using Plan mode; Task breakdown — Tools like Claude Code automatically create and track todo lists; Implementation orchestration — Frontier models manage task delegation on their own.' Explicitly: 'Implementation/orchestration phases retired—frontier models handle this well on their own now.' v2's six phases (plan-product, shape-spec, write-spec, create-tasks, implement-tasks, orchestrate-tasks) collapsed to five commands. 5,284 stars.
SRC: https://raw.githubusercontent.com/buildermethods/agent-os/main/CHANGELOG.md

### Agent OS v3's five commands and current directory layout
Commands live in `commands/agent-os/`: discover-standards.md, index-standards.md, inject-standards.md, plan-product.md, shape-spec.md. Project layout: `agent-os/standards/` (with generated `index.yml` for automatic detection), `agent-os/product/` (mission.md, roadmap.md, tech-stack.md), `agent-os/specs/{YYYY-MM-DD-HHMM-feature-slug}/`. Install: `scripts/project-install.sh` with flags `--profile <name>`, `--commands-only` (only update commands, preserve existing standards), `--verbose`, `-h/--help`. Profiles live in `profiles/<name>/standards/` with inheritance declared in root `config.yml` (`version: 3.0`, `default_profile: default`, optional `profiles: {x: {inherits_from: y}}`). `scripts/sync-to-profile.sh` pushes project standards back to base profiles.
SRC: https://raw.githubusercontent.com/buildermethods/agent-os/main/scripts/project-install.sh

### Agent OS /shape-spec requires plan mode and always makes 'save the spec' Task 1
'This command must be run in plan mode… If NOT in plan mode, stop immediately.' 9 steps: clarify scope → gather visuals → identify reference implementations → check agent-os/product/ → read agent-os/standards/index.yml and confirm applicable standards via AskUserQuestion → generate folder name YYYY-MM-DD-HHMM-{slug} (slug lowercase, hyphens, max 40 chars) → structure plan with 'Task 1 always being Save spec documentation' → complete plan → ready for execution. Output folder: plan.md, shape.md, standards.md, references.md, visuals/.
SRC: https://raw.githubusercontent.com/buildermethods/agent-os/main/commands/agent-os/shape-spec.md

### Tessl binds specs to code files and tests mechanically — the strongest traceability of the six
'All spec files end with .spec.md.' YAML frontmatter carries name, description, and `targets:` — 'A list of relative file paths or glob patterns described by the spec… Required: All specs must have at least one target.' Requirements carry inline `` `[@test] ../tests/calculator/test_divide_by_zero.py` `` links: 'Test links are intermingled with the requirements they verify, with context dictating what content is verified.' Specs 'typically begin with a code block describing any public API contracts in a compact, scannable format.'
SRC: https://raw.githubusercontent.com/tesslio/spec-driven-development-tile/main/docs/spec-format.md

### Tessl ships executable drift guards and always-on behavioral rules
`scripts/check-spec-links.sh [specs-directory]` (default ./specs): 'Check that [@test] links and targets in .spec.md files point to existing files. Glob patterns in targets are expanded; missing matches are flagged.' Plus `scripts/validate-specs.sh`. Rules with `alwaysApply: true` frontmatter: spec-before-code.md, spec-format-compliance.md, one-question-at-a-time.md. Skills: requirement-gathering, spec-writer, spec-verification, work-review. Ships 9 evals including spec-drift-after-refactor, skip-spec-pushback, trivial-change-exception, requirements-gap-analysis-from-existing-specs.
SRC: https://raw.githubusercontent.com/tesslio/spec-driven-development-tile/main/scripts/check-spec-links.sh

### Tessl's spec-before-code rule defines what does and does not count as approval
'Never begin implementation without an approved spec.' Procedure: 1) Check if a specs/ directory exists 2) If existing specs cover the work — verify they're still accurate before proceeding 3) If none cover the work — gather requirements and write a spec first 4) Get explicit stakeholder approval before writing any code. Counts as approval: stakeholder says it's accurate ('looks good', 'yes', 'approved'), or makes corrections then confirms. Does NOT count: silence, '"Just do it" without reviewing the spec', or 'Your own judgment that the spec is probably fine'. Exceptions: trivial changes; emergency hotfixes — 'but a spec must be written retroactively'.
SRC: https://raw.githubusercontent.com/tesslio/spec-driven-development-tile/main/rules/spec-before-code.md

### OpenSpec `init` writes tool-specific skill/command dirs for ~37 agents
Creates `openspec/{specs,changes,config.yaml}` plus `.claude/skills/`, `.cursor/skills/`, `.cursor/commands/`, `.agents/skills/` etc. Supported --tools IDs: amazon-q, antigravity, auggie, bob, claude, cline, command-code, codeartsagent, codex, devin (windsurf alias), forgecode, codebuddy, continue, costrict, crush, cursor, factory, gemini, github-copilot, hermes, iflow, junie, kilocode, kimi, kiro, lingma, minimax-code, vibe, oh-my-pi, opencode, pi, qoder, qwen, roocode, trae, zcode, agents. Default profile `core`, delivery `both`, workflows: propose, explore, apply, update, sync, archive. Invocation differs per tool: Cursor/Copilot register `/opsx-propose`, Codex uses `$openspec-propose`.
SRC: https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/docs/cli.md

## EXAMPLES
### OpenSpec spec-driven schema: the artifact dependency graph (this is the whole workflow definition, forkable per-project)
FILE: schemas/spec-driven/schema.yaml (built-in) or openspec/schemas/<name>/schema.yaml (project-local, via `openspec schema fork`)
```
name: spec-driven
version: 1
description: Default OpenSpec workflow - proposal → specs → design → tasks
artifacts:
  - id: proposal
    generates: proposal.md
    description: Initial proposal document outlining the change
    template: proposal.md
    instruction: |
      Create the proposal document that establishes WHY this change is needed.
      ...
    requires: []

  - id: specs
    generates: "specs/**/*.md"
    template: spec.md
    requires:
      - proposal

  - id: design
    generates: design.md
    template: design.md
    requires:
      - proposal

  - id: tasks
    generates: tasks.md
    template: tasks.md
    requires:
      - specs
      - design

apply:
  requires: [tasks]
  tracks: tasks.md
  instruction: |
    Read context files, work through pending tasks, mark complete as you go.
    Pause if you hit blockers or need clarification.
```
SRC: https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/schemas/spec-driven/schema.yaml

### OpenSpec delta spec template (verbatim, complete file — note the exactly-4-hashtag scenario rule)
FILE: openspec/changes/<change-name>/specs/<capability-path>/spec.md
```
## Purpose
<!-- New capabilities only: one or two sentences (50+ characters) on what this capability is for. Delete this section for an existing capability. -->

## ADDED Requirements

### Requirement: <!-- requirement name -->
<!-- requirement text -->

#### Scenario: <!-- scenario name -->
- **WHEN** <!-- condition -->
- **THEN** <!-- expected outcome -->
```
SRC: https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/schemas/spec-driven/templates/spec.md

### OpenSpec filled delta spec example, showing ADDED + REMOVED with mandatory Reason/Migration
FILE: openspec/changes/<change>/specs/<capability>/spec.md
```
## Purpose

Lets users take their data out of the product in a portable format.

## ADDED Requirements

### Requirement: User can export data
The system SHALL allow users to export their data in CSV format.

#### Scenario: Successful export
- **WHEN** user clicks "Export" button
- **THEN** system downloads a CSV file with all user data

## REMOVED Requirements

### Requirement: Legacy export
**Reason**: Replaced by new export system
**Migration**: Use new export endpoint at /api/v2/export
```
SRC: https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/schemas/spec-driven/schema.yaml

### OpenSpec proposal template (verbatim) — the Capabilities section is the proposal→specs contract
FILE: openspec/changes/<change-name>/proposal.md
```
## Why

<!-- Explain the motivation for this change. What problem does this solve? Why now? -->

## What Changes

<!-- Describe what will change. Be specific about new capabilities, modifications, or removals. -->

## Capabilities

### New Capabilities
<!-- Capabilities being introduced. Use kebab-case for path segments you introduce
     (e.g., user-auth or identity/user-auth) that follow the project's existing
     spec organization. Each creates specs/<capability-path>/spec.md. -->
- `<capability-path>`: <brief description of what this capability covers>

### Modified Capabilities
<!-- Existing capabilities whose REQUIREMENTS are changing (not just implementation).
     Only list here if spec-level behavior changes. Each needs a delta spec file.
     ... A change with no capabilities at all (pure refactor, tooling, docs)
     must set `skip_specs: true` in its .openspec.yaml -->
- `<existing-capability-path>`: <what requirement is changing>

## Impact

<!-- Affected code, APIs, dependencies, systems -->
```
SRC: https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/schemas/spec-driven/templates/proposal.md

### OpenSpec tasks + design templates (verbatim, complete). The `- [ ] X.Y` checkbox format is parsed by the apply phase — non-conforming tasks are not tracked.
FILE: openspec/changes/<change-name>/tasks.md and design.md
```
# --- tasks.md ---
## 1. <!-- Task Group Name -->

- [ ] 1.1 <!-- Task description -->
- [ ] 1.2 <!-- Task description -->

## 2. <!-- Task Group Name -->

- [ ] 2.1 <!-- Task description -->
- [ ] 2.2 <!-- Task description -->

# --- design.md ---
## Context

<!-- Current state and constraints that shape the approach. See proposal.md for motivation - don't restate it -->

## Goals / Non-Goals

**Goals:**
**Non-Goals:**

## Decisions

<!-- Key design decisions with rationale and alternatives considered -->

## Risks / Trade-offs
```
SRC: https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/schemas/spec-driven/templates/tasks.md

### OpenSpec on-disk layout: change folder, archive naming, and full tree
FILE: openspec/ at repo root
```
openspec/
├── specs/                      # source of truth, by domain
│   ├── auth/spec.md
│   ├── payments/spec.md
│   └── ui/spec.md
├── changes/
│   ├── add-dark-mode/
│   │   ├── proposal.md         # Why and what
│   │   ├── design.md           # How (technical approach)
│   │   ├── tasks.md            # Implementation checklist
│   │   ├── .openspec.yaml      # schema, created, skip_specs, retire_capabilities
│   │   └── specs/              # Delta specs
│   │       └── ui/spec.md
│   └── archive/
│       └── 2025-01-24-add-2fa/ # YYYY-MM-DD-<name>
│           ├── proposal.md
│           ├── design.md
│           ├── tasks.md
│           └── specs/auth/spec.md
└── config.yaml
```
SRC: https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/docs/concepts.md

### OpenSpec CLI: the commands worth wiring into CI / pre-commit hooks
FILE: shell / .githooks/pre-commit
```
npm install -g @fission-ai/openspec@latest   # latest = 1.9.0

openspec init --tools claude,cursor          # non-interactive setup
openspec update                              # regen agent instruction files after upgrade

openspec list --json                         # active changes, machine-readable
openspec status --change add-dark-mode --json
openspec instructions --json                 # next-artifact instructions for an agent
openspec templates --json                    # resolve template paths

openspec validate --all --strict --concurrency 12
openspec validate --archived                 # CI/pre-commit: fail if an archived change
                                             # still has unchecked tasks.md boxes

openspec archive add-dark-mode --yes         # agents/CI MUST pass --yes (no tty = exit 1)
openspec archive update-ci-config --skip-specs

openspec schema fork spec-driven             # fork the built-in workflow
openspec schema validate --all
openspec schema which
```
SRC: https://raw.githubusercontent.com/Fission-AI/OpenSpec/main/docs/cli.md

### spec-kit feature spec template: FR-###/SC-### IDs and the [NEEDS CLARIFICATION] marker that /speckit.clarify resolves
FILE: specs/[###-feature-name]/spec.md (template at .specify/templates/spec-template.md)
```
# Feature Specification: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`
**Created**: [DATE]
**Status**: Draft
**Input**: User description: "$ARGUMENTS"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - [Brief Title] (Priority: P1)

**Why this priority**: [Explain the value and why it has this priority level]
**Independent Test**: [e.g., "Can be fully tested by [action] and delivers [value]"]

**Acceptance Scenarios**:
1. **Given** [initial state], **When** [action], **Then** [expected outcome]

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST [specific capability, e.g., "allow users to create accounts"]
- **FR-002**: System MUST [specific capability, e.g., "validate email addresses"]

*Example of marking unclear requirements:*

- **FR-006**: System MUST authenticate users via [NEEDS CLARIFICATION: auth method not specified - email/password, SSO, OAuth?]
- **FR-007**: System MUST retain user data for [NEEDS CLARIFICATION: retention period not specified]

### Key Entities *(include if feature involves data)*

- **[Entity 1]**: [What it represents, key attributes without implementation]

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: [e.g., "Users can complete account creation in under 2 minutes"]
- **SC-002**: [e.g., "System handles 1000 concurrent users without degradation"]

## Assumptions
```
SRC: https://raw.githubusercontent.com/github/spec-kit/main/templates/spec-template.md

### spec-kit per-feature directory layout and the Constitution Check gate
FILE: specs/[###-feature]/ ; template at .specify/templates/plan-template.md
```
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks - NOT created by /speckit.plan)

# plan.md头 sections:
**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]

## Technical Context
**Language/Version**: [e.g., Python 3.11 or NEEDS CLARIFICATION]
**Primary Dependencies**: [e.g., FastAPI or NEEDS CLARIFICATION]
**Storage**: / **Testing**: / **Target Platform**: / **Project Type**:
**Performance Goals**: / **Constraints**: / **Scale/Scope**:

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
```
SRC: https://raw.githubusercontent.com/github/spec-kit/main/templates/plan-template.md

### spec-kit tasks.md format: [ID] [P] [Story] with a blocking Foundational phase
FILE: specs/[###-feature-name]/tasks.md
```
## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `src/`, `tests/` at repository root
- **Web app**: `backend/src/`, `frontend/src/`
- **Mobile**: `api/src/`, `ios/src/` or `android/src/`

## Phase 1: Setup (Shared Infrastructure)
- [ ] T001 Create project structure per implementation plan
- [ ] T002 Initialize [language] project with [framework] dependencies
- [ ] T003 [P] Configure linting and formatting tools

## Phase 2: Foundational (Blocking Prerequisites)
**⚠️ CRITICAL**: No user story work can begin until this phase is complete
- [ ] T004 Setup database schema and migrations framework
- [ ] T005 [P] Implement authentication/authorization framework
- [ ] T007 Create base models/entities that all stories depend on
```
SRC: https://raw.githubusercontent.com/github/spec-kit/main/templates/tasks-template.md

### spec-kit constitution template — the governing-principles file that gates plan/analyze
FILE: .specify/memory/constitution.md
```
# [PROJECT_NAME] Constitution

## Core Principles

### [PRINCIPLE_1_NAME]
<!-- Example: I. Library-First -->
[PRINCIPLE_1_DESCRIPTION]
<!-- Example: Every feature starts as a standalone library; Libraries must be self-contained, independently testable, documented -->

### [PRINCIPLE_3_NAME]
<!-- Example: III. Test-First (NON-NEGOTIABLE) -->
[PRINCIPLE_3_DESCRIPTION]
<!-- Example: TDD mandatory: Tests written → User approved → Tests fail → Then implement; Red-Green-Refactor cycle strictly enforced -->

## [SECTION_2_NAME]
<!-- Example: Additional Constraints, Security Requirements, Performance Standards -->

## [SECTION_3_NAME]
<!-- Example: Development Workflow, Review Process, Quality Gates -->

## Governance
<!-- Example: Constitution supersedes all other practices; Amendments require documentation, approval, migration plan -->

**Version**: [CONSTITUTION_VERSION] | **Ratified**: [RATIFICATION_DATE] | **Last Amended**: [LAST_AMENDED_DATE]
```
SRC: https://raw.githubusercontent.com/github/spec-kit/main/templates/constitution-template.md

### spec-kit command-file frontmatter — how a slash command binds to its prerequisite script across 3 shells
FILE: .specify/templates/commands/<name>.md → installed to .claude/commands/ etc.
```
---
description: Assess the current codebase against the feature's spec, plan, and tasks, then append any remaining unbuilt work as new tasks to tasks.md so implement can complete it.
scripts:
  sh: scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
  ps: scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks
  py: scripts/python/check_prerequisites.py --json --require-tasks --include-tasks
---
```
SRC: https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/converge.md

### spec-kit CLI + feature-branch creation script flags (controls the ###-slug numbering convention)
FILE: scripts/bash/create-new-feature.sh (also powershell/ and python/ variants)
```
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@vX.Y.Z
specify init my-project --integration copilot
specify self check
specify self upgrade
specify integration list
specify extension search | specify extension add <name>
specify preset search  | specify preset add <name>
specify bundle search|info|install|validate|build

# create-new-feature.sh
Usage: $0 [--json] [--dry-run] [--allow-existing-branch] [--short-name <name>] [--number N] [--timestamp] <feature_description>
  --json                   Output in JSON format
  --dry-run                Compute feature name and paths without creating directories or files
  --allow-existing-branch  Reuse an existing feature directory if it already exists
  --short-name <name>      Provide a custom short name (2-4 words) for the feature
  --number N               Prefer a feature number (auto-corrected if its specs prefix exists)
  --timestamp              Use timestamp prefix (YYYYMMDD-HHMMSS) instead of sequential numbering

Examples:
  $0 'Add user authentication system' --short-name 'user-auth'
  $0 'Implement OAuth2 integration for API' --number 5
```
SRC: https://raw.githubusercontent.com/github/spec-kit/main/scripts/bash/create-new-feature.sh

### spec-kit /speckit.analyze output contract — the traceability artifact
FILE: chat output only; STRICTLY READ-ONLY, writes no files
```
## Specification Analysis Report

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| A1 | Duplication | HIGH | spec.md:L120-134 | Two similar requirements ... | Merge phrasing; keep clearer version |

**Coverage Summary Table:**

| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|

**Constitution Alignment Issues:** (if any)

# Severity heuristic:
# CRITICAL: Violates constitution MUST, missing core spec artifact, or requirement
#           with zero coverage that blocks baseline functionality
# HIGH:     Duplicate/conflicting requirement, ambiguous security/performance
#           attribute, untestable acceptance criterion
# MEDIUM:   Terminology drift, missing non-functional task coverage
# LOW:      Style/wording improvements
```
SRC: https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/analyze.md

### Kiro steering file frontmatter (4 inclusion modes) and live file references
FILE: .kiro/steering/*.md (workspace) or ~/.kiro/steering/*.md (global)
```
---
inclusion: always
---

---
inclusion: fileMatch
fileMatchPattern: "components/**/*.tsx"
---

---
inclusion: manual        # invoke on demand with #filename in chat
---

---
inclusion: auto
name: api-design
description: REST API patterns
---

# Reference a live workspace file from inside a steering doc:
#[[file:api/openapi.yaml]]
```
SRC: https://kiro.dev/docs/steering/

### Kiro agent hook JSON and the .kiro/ project layout
FILE: .kiro/hooks/lint-on-save.json (kebab-case; one file may hold multiple hooks)
```
{
  "version": "v1",
  "hooks": [{
    "name": "hook-identifier",
    "trigger": "PostFileSave",
    "matcher": "regex-pattern",
    "action": {
      "type": "command",
      "command": "shell-command"
    }
  }]
}

# Triggers: PostFileSave, PostFileCreate, PostFileDelete, PreToolUse (blocking),
#           PostToolUse, UserPromptSubmit (blocking), SessionStart, Stop,
#           PreTaskExec, PostTaskExec
# action.type: "command" (context via STDIN) | "agent" (prompt injected into conversation)

# Project layout:
.kiro/
├── specs/
│   ├── user-authentication/{requirements.md, design.md, tasks.md}
│   ├── product-catalog/
│   └── payment-processing/
├── steering/{product.md, tech.md, structure.md}
└── hooks/*.json
```
SRC: https://kiro.dev/docs/hooks/

### Kiro EARS requirement syntax (the notation that distinguishes Kiro's requirements.md)
FILE: .kiro/specs/<feature>/requirements.md
```
WHEN [condition/event] THE SYSTEM SHALL [expected behavior]

# Concrete example from the docs:
WHEN a user submits a form with invalid data THE SYSTEM SHALL display
validation errors next to the relevant fields

# Supported clause keywords: WHEN, IF, WHILE, WHERE
```
SRC: https://kiro.dev/docs/specs/feature-specs/

### Tessl .spec.md: full worked example with frontmatter targets and inline [@test] traceability links
FILE: specs/**/*.spec.md (relative paths resolve from the spec file's own directory)
```
---
name: Calculator
description: Functional requirements for the calculator module
targets:
  - ../src/calculator.py
---

# Calculator

Performs basic arithmetic operations to two digits of precision.

```python
def add(a: int, b: int) -> int: ...
def subtract(a: int, b: int) -> int: ...
def multiply(a: int, b: int) -> int: ...
def divide(a: int, b: int) -> float: ...
```

`[@test] ../tests/calculator/test_basic_arithmetic.py`

## Error handling

- Division by zero should return `Nan`
  `[@test] ../tests/calculator/test_divide_by_zero.py`
- Non-numeric input should raise `TypeError`
  `[@test] ../tests/calculator/test_invalid_input_type.py`
```
SRC: https://raw.githubusercontent.com/tesslio/spec-driven-development-tile/main/docs/spec-format.md

### Tessl drift-guard script — runnable in CI to catch spec↔code↔test decoupling
FILE: scripts/check-spec-links.sh, scripts/validate-specs.sh
```
#!/usr/bin/env bash
#
# Check that [@test] links and targets in .spec.md files point to existing files.
# Glob patterns in targets are expanded; missing matches are flagged.
#
# Usage: check-spec-links.sh [specs-directory]
# Default: ./specs

set -euo pipefail
SPECS_DIR="${1:-./specs}"
EXIT_CODE=0

if [ ! -d "$SPECS_DIR" ]; then
    echo "No specs directory found at: $SPECS_DIR"
    exit 0
fi
```
SRC: https://raw.githubusercontent.com/tesslio/spec-driven-development-tile/main/scripts/check-spec-links.sh

### Tessl always-on rule file format (agent-behavior guardrail, not a document template)
FILE: rules/spec-before-code.md — also rules/spec-format-compliance.md, rules/one-question-at-a-time.md
```
---
alwaysApply: true
---

# Spec Before Code

Never begin implementation without an approved spec.

## The rule

1. Check if a `specs/` directory exists with relevant specs
2. If existing specs cover the work — verify they're still accurate before proceeding
3. If no specs exist or none cover the work — gather requirements and write a spec first
4. Get explicit stakeholder approval on the spec before writing any code

## What does NOT count as approval

- Silence or no response
- "Just do it" without reviewing the spec
- Your own judgment that the spec is probably fine

## Exceptions

- Trivial changes (typo fixes, formatting) that don't alter behavior
- Emergency hotfixes — but a spec must be written retroactively
```
SRC: https://raw.githubusercontent.com/tesslio/spec-driven-development-tile/main/rules/spec-before-code.md

### Agent OS v3 project layout, install flags, and profile-inheritance config
FILE: agent-os/ in project root; config.yml + profiles/ in the Agent OS base install
```
# --- config.yml (base install) ---
version: 3.0
default_profile: default

# Optional: define inheritance relationships for profiles
# profiles:
#   profile-a:
#     inherits_from: default
#   profile-b:
#     inherits_from: profile-a

# --- install ---
Usage: scripts/project-install.sh [OPTIONS]
    --profile <name>     Use specified profile (default: from config.yml)
    --commands-only      Only update commands, preserve existing standards
    --verbose            Show detailed output
    -h, --help           Show this help message
Examples:
    scripts/project-install.sh --profile rails
    scripts/project-install.sh --commands-only

# --- resulting project layout ---
agent-os/
├── standards/
│   ├── index.yml                 # auto-generated; drives /inject-standards
│   └── **/*.md                   # e.g. api/response-format.md
├── product/{mission.md, roadmap.md, tech-stack.md}
└── specs/{YYYY-MM-DD-HHMM-feature-slug}/
    ├── plan.md        # The full plan
    ├── shape.md       # Shaping decisions and context
    ├── standards.md   # Which standards apply and key points
    ├── references.md  # Pointers to similar code
    └── visuals/       # Mockups, screenshots (if any)

# Commands: /discover-standards /index-standards /inject-standards
#           /plan-product /shape-spec
# scripts/sync-to-profile.sh pushes project standards back to base profiles
```
SRC: https://raw.githubusercontent.com/buildermethods/agent-os/main/scripts/project-install.sh

### BMAD v6 installed directory structure (post v4→v6 migration)
FILE: _bmad/ and _bmad-output/ at project root
```
your-project/
├── _bmad/               # Single installation folder
│   ├── _config/         # Your customizations
│   │   └── agents/      # Agent customization files
│   ├── core/            # Universal core framework
│   ├── bmm/             # BMad Method module
│   ├── bmb/             # BMad Builder
│   └── cis/             # Creative Intelligence Suite
└── _bmad-output/
    └── planning-artifacts/   # brief / PRD / architecture / ux-design
                              # (sharded docs may sit in named subfolders)
                              # epics.md or epics/epic*.md for in-flight work

# v4 -> v6: .bmad-method/ is backed up and removed by the installer.
# Skills move from .claude/commands/ to .claude/skills/
# Requires Node.js 20.12+
```
SRC: https://raw.githubusercontent.com/bmad-code-org/BMAD-METHOD/main/docs/how-to/upgrade-to-v6.md

### BMAD v6 agent → skill-ID → trigger → workflow mapping (the persona layer)
FILE: installed as skills, e.g. .claude/skills/bmad-agent-dev/
```
Analyst (Mary)          bmad-agent-analyst      BP MR DR TR CB WB PC
Product Manager (John)  bmad-agent-pm           PRD CE IR CC
Architect (Winston)     bmad-agent-architect    CA IR
Developer (Amelia)      bmad-agent-dev          BD QA CR SP ER
UX Designer (Sally)     bmad-agent-ux-designer  CU

# Phase 2 planning outputs:
#   bmad-prd   -> prd.md, addendum.md, .memlog.md  (or validation-report.html)
#   bmad-ux    -> DESIGN.md (visual) + EXPERIENCE.md (behavioral)
#   bmad-spec  -> {output_folder}/specs/spec-{slug}/SPEC.md  + optional stories.yaml
#                 SPEC.md kernel = Why, Capabilities, Constraints, Non-goals, Success signal
# Phase 3: bmad-architecture -> ARCHITECTURE-SPINE.md
#          bmad-sprint-planning -> PASS/CONCERNS/FAIL + sprint-status.yaml
# Phase 4: bmad-build -> spec-*.md + code ; bmad-build-auto for unattended loops
```
SRC: https://raw.githubusercontent.com/bmad-code-org/BMAD-METHOD/main/docs/reference/agents.md

## GOTCHAS
- OpenSpec scenario headers fail SILENTLY if you use the wrong depth. From the schema instruction: '**CRITICAL**: Scenarios MUST use exactly 4 hashtags (`####`). Using 3 hashtags or bullets will fail silently.' Every requirement MUST have at least one scenario.
- OpenSpec MODIFIED requirements lose data if partially copied: 'Common pitfall: Using MODIFIED with partial content loses detail at archive time.' The documented workflow is to copy the ENTIRE requirement block (from `### Requirement:` through all scenarios) from openspec/specs/, paste under `## MODIFIED Requirements`, then edit. If you are only adding new concerns, use ADDED instead.
- OpenSpec `openspec archive` hangs-then-fails for agents/CI: 'an AI agent, a CI job, or any run with stdin closed cannot answer step 2, so archive stops before touching anything, exits 1'. Always pass the change name AND `--yes` up front.
- OpenSpec rejects zero-delta changes: validation fails unless the change's `.openspec.yaml` sets `skip_specs: true`. Explicit warning against gaming it — 'Do not invent a requirement just to satisfy validation.' Similarly, capability retirement silently does nothing unless `retire_capabilities: true` is set, and `--no-validate` also disables retirement.
- OpenSpec new-capability specs that omit `## Purpose` (or write under 50 chars) leave the archived main spec with a literal `TBD ... Update Purpose after archive` placeholder that must be fixed by hand. Conversely, adding `## Purpose` to a delta for an EXISTING capability is silently ignored.
- spec-kit command names in most blog posts and tutorials are stale. The bare `/specify`, `/plan`, `/tasks`, `/implement` were renamed to the `/speckit.*` namespace; Codex CLI and Command Code skills mode use `$speckit-*`. Anything citing bare `/specify` predates the rename.
- spec-kit's `/speckit.converge` explicitly does NOT use git — 'no git, no branch comparison, no history'. It re-assesses code against artifacts from scratch every run, which is expensive on large features and can produce duplicate convergence tasks across runs (it is forbidden from deleting prior Convergence phases).
- Token cost is the single most-cited criticism. Reported benchmarks claim Spec-Kit uses up to ~2x more tokens than OpenSpec, and one comparison cited SDD taking 33 minutes plus 2,577 lines of markdown to produce 689 lines of code versus 8 minutes with iterative prompting at no quality gain. Source is secondary/vendor-adjacent — treat the exact multipliers as unverified.
- Manual spec drift is the dominant community complaint across all of these: specs that 'keep drifting and drifting until you have duplication and contradictions.' Only Tessl has machine-verifiable spec↔code binding (targets globs + [@test] links + check-spec-links.sh); the rest rely on an LLM re-reading documents.
- Agent OS v3 (Jan 2026) is a strong signal against heavy SDD scaffolding — its own author retired spec writing, task breakdown, and implementation orchestration because 'Claude Code's plan mode, extended thinking, and improved models now handle much of the scaffolding that earlier versions provided.' v3 commands are entirely different from v2; only the content format is backward compatible.
- BMAD v4 → v6 is a hard break. The widely-blogged v4 model (Analyst/PM/Architect/SM/Dev/QA personas, PRD sharding into epics, per-story story files consumed by an SM agent) no longer describes the shipped product. v6 collapses implementation onto `bmad-build` with internal scale routing. Any v4 tutorial is stale.
- Kiro Specs are an IDE-only feature. Kiro CLI has Chat, Custom Agents, MCP, Hooks, Steering, Autocomplete and Headless mode but NOT Specs — so you cannot drive the requirements/design/tasks loop headlessly from Kiro CLI.
- Amazon Q Developer is being retired in favor of Kiro: new signups blocked May 15 2026, full end-of-support April 30 2027. Do not build on Q Developer agents.
- Kiro spec edits do not auto-propagate. You must explicitly hit **Refine** on design.md and **Sync Files** on tasks.md after editing requirements.md, which makes drift a manual-discipline problem rather than an enforced one.
- Broader methodological criticism worth weighing: SDD is frequently characterized as waterfall/contract-design rebranded — rigid upfront planning and the assumption requirements can be fully known in advance. Common advice is to skip SDD for small features (overhead exceeds return) and for cross-service work where spec drift creates coordination problems static documents cannot resolve.

## OPEN
- No primary source found for the exact BMAD 'scale-adaptive' project-level taxonomy (Level 0–4) that appears in v5/v6-alpha writeups. In shipped v6 docs the concept survives only as bmad-build's 'Route to the smallest safe path' language, with no numbered levels documented. The numbered-level model may have been removed or may live in files not surfaced by the docs tree.
- Could not fetch Kiro's requirements.md as a complete verbatim template — the docs describe EARS and give one example sentence, but no full generated requirements.md with numbered requirements and acceptance-criteria blocks. Also could not confirm the exact syntax Kiro's tasks.md uses to reference requirement IDs (docs say tasks 'reference linked requirements' without showing the format).
- Tessl's hosted product (registry, CLI, usage specs) was only reachable via secondary sources and search snippets — docs.tessl.io returned 404s on the paths tried. The verbatim spec format captured here is from the open-source spec-driven-development-tile repo, which may lag or differ from the commercial Tessl Framework. The tile version (2.0.1, ~Apr 2026) was not confirmed against tile.json.
- No head-to-head benchmark from a neutral primary source measuring token cost, wall-clock time, or defect rate across OpenSpec / spec-kit / Kiro. The 2x-token and 33-min-vs-8-min figures come from vendor blogs and Medium posts, not reproducible studies.
- Unclear how OpenSpec 'Stores' (beta, cross-repo shared openspec/ directories pushed via Git) interacts with the archive/merge flow when multiple repos consume the same specs — docs/stores-beta/user-guide.md was identified but not read.
- Whether any of these frameworks enforce traceability at CI-gate level by default. OpenSpec (`validate --archived`) and Tessl (`check-spec-links.sh`) ship runnable checks, but no evidence was found that either is wired into a default CI template — adoption appears to be opt-in per project.
- Adoption-versus-stars is unresolved. spec-kit has 129.6k stars and OpenSpec 65.1k, but star counts for AI-tooling repos are weak proxies for sustained team usage; no retention or production-usage data was found.

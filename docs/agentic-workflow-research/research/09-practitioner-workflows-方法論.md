# Named practitioner methodologies for AI-assisted software development, 2025–2026: the opinionated end-to-end workflows people publish and reuse

## SUMMARY
Across every named methodology I could verify from primary sources, the same five-stage spine recurs: **shape/interrogate → spec → slice into tickets → implement in a fresh context per slice → verify with an adversarial/independent pass → codify the learning**. What differs is (a) where artifacts live, (b) how hard the verification gate is, and (c) how much they trust the model's own judgement.

**Matt Pocock (aihero.dev, `mattpocock/skills`, 32 SKILL.md files)** is the most stack-agnostic and the most transferable. His chain is `/grill-me` (relentless interview, walks Brooks' "design tree") → `/to-spec` (synthesis, no re-interview, publishes to the *issue tracker*, not a file) → `/to-tickets` (tracer-bullet vertical slices with explicit blocking edges) → `/implement` (which calls `/tdd` at pre-agreed seams) → `/code-review` (two parallel subagents: Standards vs Spec) → `/triage`. Setup writes exactly three files: `docs/agents/issue-tracker.md`, `docs/agents/domain.md`, `docs/agents/triage-labels.md`, plus `CONTEXT.md` + `docs/adr/`. He is aggressively anti-CLAUDE.md: "Never run init", his own CLAUDE.md is six words. Steering belongs in skills (progressive disclosure), not a global file. His separate **Ralph** track (bash loop, fresh context per iteration, `PRD.md` + `progress.txt`, `<promise>COMPLETE</promise>` sigil, Docker sandbox, capped iterations) is the AFK half.

**HumanLayer's ACE-FCA** is the most rigorous context discipline: research → plan → implement as three separate fresh contexts, prompts in `.claude/commands/`, artifacts in `thoughts/shared/research|plans`, explicit 40–60% context-utilization target, "intentional compaction."

**Every/Kieran Klaassen's compound engineering** (23k-star plugin, 33 skills) adds a fifth step the others lack: `/ce-compound` writes learnings to `docs/solutions/` which the *next* brainstorm reads. 80% planning/review, 20% execution.

**Anthropic's own best-practices** is now the lowest-ceremony of the group: give Claude a check it can run; explore→plan→code→commit; `/clear` aggressively; adversarial review subagent; `--allowedTools` fan-out.

**Armin Ronacher and Simon Willison are the dissenters** — Ronacher warns loops produce codebases "that assume machine participation as part of their maintenance model"; Willison argues against over-prescribing and for letting the model use its own judgement.

## KEY FACTS
### Matt Pocock's skill kit is 32 SKILL.md files across four categories, split on invocation type: user-invoked skills orchestrate and never chain to other user-invoked skills; model-invoked skills hold reusable discipline
Repo tree: skills/engineering/ (18: ask-matt, code-review, codebase-design, diagnosing-bugs, domain-modeling, grill-with-docs, implement, improve-codebase-architecture, prototype, research, resolving-merge-conflicts, setup-matt-pocock-skills, tdd, to-spec, to-tickets, triage, wayfinder, wizard), skills/productivity/ (7: grill-me, grilling, handoff, teach, to-questionnaire, wait-what, writing-for-agents), skills/in-progress/ (6), skills/misc/ (4). Install via Claude Code plugin OR `npx skills@latest add mattpocock/skills` — explicitly NOT both ('No double-installation'). The four problems it targets: #1 Misalignment, #2 Verbosity, #3 Non-functional code, #4 Architectural debt.
SRC: https://api.github.com/repos/mattpocock/skills/git/trees/main?recursive=1

### `/setup-matt-pocock-skills` writes exactly three config files to `docs/agents/` and adds an `## Agent skills` block to whichever of CLAUDE.md or AGENTS.md already exists
Files: `docs/agents/issue-tracker.md` (which tracker + how to talk to it — GitHub, GitLab, local markdown under `.scratch/`, or custom), `docs/agents/domain.md` (where domain docs live), `docs/agents/triage-labels.md` (label→canonical role map). Five canonical triage roles: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. Domain docs default to single-context: one `CONTEXT.md` plus `docs/adr/` at repo root; switches to multi-context `CONTEXT-MAP.md` on monorepo signals. All config lives in the repo, under version control, never global.
SRC: https://www.aihero.dev/skills-setup-matt-pocock-skills

### Pocock's skill catalogue is organised as five layers around an 'idea→ship spine': Shaping, The Main Flow, Upkeep, Productivity Skills, Reference Skills
Shaping = 'Explore an open question and produce a decision/answer that feeds the flow'. Upkeep = 'Keep the codebase and issue list healthy; generates work for the flow'. Reference Skills = 'The reusable layer other skills invoke or cite'. v1.2 (Aug 2026) added /wait-what and /writing-for-agents plus Claude Code Plugin integration.
SRC: https://www.aihero.dev/skills

### Pocock's 7 phases of AI development, explicitly framed as stack- and tool-agnostic (works with Ralph, GSD, or Spec Kit)
1 Idea (refine with /grill-me) → 2 Research (optional; cache external-API knowledge into `research.md` in-repo; NOTE he says research assets 'typically live only for the duration of this sprint' because they rot) → 3 Prototype (throwaway route, multiple variations, impose taste early so PRD can cite concrete examples) → 4 PRD (describes the destination, not the journey; agent grills you through the decision tree) → 5 Kanban board (tickets with blocking relationships so non-blocking ones parallelise; GitHub Issues works but lacks blocking, Linear better) → 6 Execution (Ralph loop; AFK viable only once research+prototype+PRD+tickets are in place) → 7 QA (agent writes a QA plan for human review; findings become new tickets; iterate 5–7 repeatedly).
SRC: https://www.aihero.dev/my-7-phases-of-ai-development

### Pocock's `/tdd` skill states 'Refactoring is not part of the loop' — it belongs to the review stage, not red→green
Also: 'Test only at pre-agreed seams. Before writing any test, write down the seams under test and confirm them with the user. No test is written at an unconfirmed seam.' Three named anti-patterns: Implementation-coupled ('the test breaks when you refactor but behavior hasn't changed'), Tautological ('the assertion recomputes the expected value the way the code does... so it passes by construction'), Horizontal slicing ('writing all tests first, then all implementation. Bulk tests verify _imagined_ behavior'). Instructs reading `CONTEXT.md` so test names match domain language.
SRC: https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/tdd/SKILL.md

### `/to-tickets` mandates vertical tracer-bullet slices, each sized to a single fresh context window, with an explicit expand–contract escape hatch for wide refactors
Vertical slice rules verbatim: 'Each slice cuts a narrow but COMPLETE path through every layer (schema, API, UI, tests) — vertical, NOT a horizontal slice of one layer'; 'A completed slice is demoable or verifiable on its own'; 'Each slice is sized to fit in a single fresh context window'; 'Any prefactoring should be done first'. Wide refactor = 'one mechanical change — rename a column, retype a shared symbol — whose blast radius fans across the whole codebase'. Sequence: expand (add new form beside old) → migrate call sites in batches sized by blast radius, each batch its own ticket → contract (delete old form). Quotes 'Make the change easy, then make the easy change.'
SRC: https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/to-tickets/SKILL.md

### Pocock's `/code-review` runs two axes as parallel subagents — Standards and Spec — and carries a fixed 12-item Fowler code-smell baseline that applies even when the repo documents nothing
Diff is pinned with `git diff <fixed-point>...HEAD` (three-dot, against merge-base) plus `git log <fixed-point>..HEAD --oneline`. Spec source resolution order: (1) issue refs in commit messages, (2) path passed as arg, (3) spec file under `docs/`, `specs/`, or `.scratch/` matching branch name, (4) ask. Smells: Mysterious Name, Duplicated Code, Feature Envy, Data Clumps, Primitive Obsession, Repeated Switches, Shotgun Surgery, Divergent Change, Speculative Generality, Message Chains, Middle Man, Refused Bequest. Two binding rules: 'The repo overrides' and 'Always a judgement call' — each smell is a labelled heuristic, never a hard violation, and skip anything tooling already enforces.
SRC: https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/code-review/SKILL.md

### Pocock: 'Never run init… If you find one that was auto-generated, delete it.' His entire CLAUDE.md is six words
Verbatim: 'My entire `CLAUDE.md` is: `you are on WSL on Windows`… That's the bar: only include what is both **undiscoverable** and **globally relevant**.' Rationale: the system prompt is 'hardwired the moment the agent starts' whereas exploration/implementation/testing phases are flexible; LLMs have an instruction budget of 'around 300 to 400 instructions at a time'; CLAUDE.md is global so a React rule burns budget in backend and docs sessions. Prescription: 'Trust the explore step. Use skills for steering. Keep CLAUDE.md nearly empty.'
SRC: https://www.aihero.dev/never-run-claude-init

### Pocock's AGENTS.md minimum is three things: one-sentence project description, package manager (if non-default), non-standard build/typecheck commands
Cites HumanLayer's Kyle on instruction budget: 'Frontier thinking LLMs can follow ~ 150-200 instructions with reasonable consistency.' Warns specifically against documenting file-system structure: 'If your AGENTS.md says "authentication logic lives in src/auth/handlers.ts" and that file gets renamed or moved, the agent will confidently look in the wrong place… Instead of documenting structure, describe capabilities.' Domain concepts are 'more stable than file paths, so they're safer to document.' Monorepos: nested AGENTS.md files merge with root. Claude Code uses CLAUDE.md, so `ln -s AGENTS.md CLAUDE.md`.
SRC: https://www.aihero.dev/a-complete-guide-to-agents-md

### Pocock's 'grey box module' idea: you own the interface, AI owns the implementation, tests keep it honest
'AI is not a super-powered developer. It's a new starter with no memory… like the guy from Memento.' 'Your codebase, way more than your prompt or your AGENTS.md file, is the biggest influence on AI's output.' Three costs of bad design: poor feedback loops, hard to navigate, cognitive burnout. Fix = deep modules (from A Philosophy of Software Design): each module gets its own folder with a clear public interface; exports must come through that interface. 'Instead of holding hundreds of interrelated modules in your head, you keep seven or eight chunks.'
SRC: https://www.aihero.dev/how-to-make-codebases-ai-agents-love

### Pocock's `codebase-design` skill defines a strict shared vocabulary and explicitly bans substitute words
'Use these terms exactly — don't substitute "component," "service," "API," or "boundary."' Module (scale-agnostic; avoid: unit, component, service). Interface = 'everything a caller must know to use the module correctly: the type signature, but also invariants, ordering constraints, error modes, required configuration, and performance characteristics' (avoid: API, signature — too narrow). Seam (Michael Feathers) = 'a place where you can alter behaviour without editing in that place' (avoid: boundary — overloaded with DDD's bounded context). Depth = 'leverage at the interface'. Leverage = what callers get; Locality = what maintainers get.
SRC: https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/codebase-design/SKILL.md

### Pocock's Ralph loop: same prompt, fresh context every iteration, one task per iteration, capped iterations, completion sigil
HITL first (`ralph-once.sh`), then AFK (`afk-ralph.sh <iterations>`). 'For AFK Ralph, always cap your iterations. Infinite loops are dangerous with stochastic systems. I typically use 5-10 iterations for small tasks, or 30-50 for larger ones.' Artifacts: `PRD.md` (or `prd.json`) + `progress.txt`, both committed. 'The key improvement here is that the agent chooses the task, not you.' Alternative loop types he runs: test-coverage (took AI Hero CLI 16%→100%), duplication (jscpd), linting, entropy. Cost: Anthropic 5x Max plan ~£90/month, 'most of my usage is HITL'.
SRC: https://www.aihero.dev/getting-started-with-ralph

### Pocock's 'smart zone' claim: LLMs degrade past ~40% of context, and he says Anthropic's own Ralph plugin is broken because its stop-hook keeps everything in one session
Verbatim table: 'Smart Zone | First 40% of context | Sharp, capable, makes good decisions' vs 'Dumb Zone | Last 60% of context | Confused, mistakes, degraded performance'. On the plugin: 'Instead of exiting and restarting, the plugin uses a "stop hook" that intercepts Claude's exit attempts and feeds the same prompt back into the session… After 3-4 iterations, the AI is working entirely in the dumb zone… the plugin **guarantees** that you're going to fill up the smart zone.' His fix: 'Stick with the bash loop.' Also cites context rot research (research.trychroma.com/context-rot).
SRC: https://www.aihero.dev/why-the-anthropic-ralph-plugin-sucks

### HumanLayer's ACE-FCA sets an explicit context-utilization target of 40–60% and splits work into three fresh contexts: research, plan, implement
Prompts live at `.claude/commands/research_codebase.md`, `.claude/commands/create_plan.md`, `.claude/commands/implement_plan.md`. Artifacts under `thoughts/shared/research/` and `thoughts/shared/plans/`, plus `progress.md`. 'Intentional compaction' = 'deliberately structuring how you feed context to the AI throughout the development process' — synthesise findings into structured documents rather than dumping raw tool output. 'Frequent intentional compaction' = 'design your ENTIRE WORKFLOW around context management'. Key justification: 'a bad line of a plan could lead to hundreds of bad lines of code'. Explicit warning: 'You have to engage with your task when you're doing this or it WILL NOT WORK.' Also: 'you probably need at least one person who is an expert in the codebase' and 'Reading 200-line plans beats reviewing 2000-line PRs'.
SRC: https://github.com/humanlayer/advanced-context-engineering-for-coding-agents/blob/main/ace-fca.md

### Every's compound engineering is a four-step loop — plan, work, assess, compound — where the fourth step is the differentiator
Plan: 'Agents read issues, research approaches, and synthesize information into detailed implementation plans' containing 'the objective of the feature, the proposed architecture, specific ideas for how the code might be written, a list of sources for its research, and success criteria.' Work: 'You just tell the agent to start working. The agent will take your plan, turn it into a to-do list, and build step-by-step.' Assess: 'We ask the agent to review its own work, and we review the work too' — linters, unit tests, plus 'automatic code review agents'; their plugin runs '12 subagents that each check it from a different perspective' (security, performance, unnecessary complexity). Compound: 'We take what we learned… and record them so that the agent can use them next time.' Learnings are 'written down as prompts that live inside of your codebase or in plugins' and 'automatically distributed to the team'.
SRC: https://every.to/source-code/compound-engineering-how-every-codes-with-agents

### The EveryInc compound-engineering-plugin ships 33 skills, states '80% is in planning and review, 20% is in execution', and defines a six-step core loop
Core loop skills: `/ce-brainstorm` → `/ce-plan` → `/ce-work` → `/ce-simplify-code` → `/ce-code-review` → `/ce-compound`. Default artifact folders: `docs/solutions/` (compounded learnings), `docs/plans/`, `docs/pulse-reports/`, plus `STRATEGY.md` at root; relocatable via `docs_root` in `.compound-engineering/config.yaml`. `/lfg` is the autopilot: plans, works, simplifies, code-reviews and applies fixes, browser-tests, commits, pushes, opens PR, watches CI with a bounded repair loop — 'it does not merge'. Reviews are 'report-only… local apply is explicit'. 'Each skill seeds generic subagents with its own prompts instead of relying on standalone plugin agents, keeping the workflows portable across harnesses.' Philosophy line: 'Each unit of engineering work should make subsequent units easier -- not harder.'
SRC: https://raw.githubusercontent.com/EveryInc/compound-engineering-plugin/main/README.md

### Every's camp writeup gives the model split per stage and a hard warning about when to run /compound
Plan uses Claude Opus, Kieran estimates '70 percent thinking, 30 percent doing'. Work uses faster models (Claude Haiku 4.5, Gemini 2.5 Flash). Review deliberately uses a *different* model family (Gemini) 'for separate perspective', findings 'stored as to-do files for triage'. `test-browser` 'uses an AI-powered browser agent to click through the interface, verify that features work'. Warning on compounding: 'run this whenever the context is fresh' — not 'after compaction'.
SRC: https://every.to/source-code/compound-engineering-camp-every-step-from-scratch

### Anthropic's current best-practices doc leads with verification, not planning: 'Give Claude a check it can run'
'Claude stops when the work looks done. Without a check it can run, "looks done" is the only signal available, and you become the verification loop.' Four escalating gate strengths: (1) in one prompt, (2) across a session via a `/goal` condition re-checked by a separate evaluator every turn, (3) a deterministic Stop hook that 'blocks the turn from ending until it passes' — 'Claude Code overrides the hook and ends the turn after 8 consecutive blocks', (4) a verification subagent / dynamic workflow so 'the agent doing the work isn't the one grading it'. 'Have Claude show evidence rather than asserting success.'
SRC: https://code.claude.com/docs/en/best-practices

### Anthropic recommends running `/init` to generate a starter CLAUDE.md — the direct opposite of Pocock's advice — while agreeing on ruthless pruning
'Run `/init` to generate a starter CLAUDE.md file based on your current project structure, then refine over time.' Test for each line: 'Would removing this cause Claude to make mistakes? If not, cut it.' 'Bloated CLAUDE.md files cause Claude to ignore your actual instructions!' 'If Claude keeps doing something you don't want despite having a rule against it, the file is probably too long and the rule is getting lost.' Include: bash commands Claude can't guess, style rules that differ from defaults, test runners, repo etiquette, architectural decisions, env quirks, gotchas. Exclude: anything discoverable from code, standard conventions, detailed API docs, frequently-changing info, file-by-file descriptions. Supports `@path/to/import`. Recommends skills over CLAUDE.md for sometimes-relevant knowledge.
SRC: https://code.claude.com/docs/en/best-practices

### Anthropic's five named failure patterns and their fixes
(1) The kitchen sink session → `/clear` between unrelated tasks. (2) Correcting over and over → 'After two failed corrections, /clear and write a better initial prompt incorporating what you learned.' (3) The over-specified CLAUDE.md → 'Ruthlessly prune. If Claude already does something correctly without the instruction, delete it or convert it to a hook.' (4) The trust-then-verify gap → 'Always provide verification (tests, scripts, screenshots). If you can't verify it, don't ship it.' (5) The infinite exploration → scope narrowly or use subagents. Plus a counter-warning on adversarial review: 'A reviewer prompted to find gaps will usually report some, even when the work is sound… Chasing every finding leads to over-engineering.'
SRC: https://code.claude.com/docs/en/best-practices

### Anthropic's long-running-agent harness uses two distinct prompts (initializer vs coding agent) and a JSON feature list with a `passes` field, chosen specifically because models tamper with Markdown
Initializer session creates `init.sh`, `claude-progress.txt`, and the initial git commit. Rationale for JSON verbatim: 'the model is less likely to inappropriately change or overwrite JSON files compared to Markdown files.' Each feature entry: category, description, verification steps, `"passes": false`. Agents test 'as a human user would' via browser automation (Puppeteer MCP) rather than curl/unit tests alone; each session starts by running the dev server and smoke-testing before implementing. Hard rule: 'It is unacceptable to remove or edit tests because this could lead to missing or buggy functionality.' Four failure modes named: premature victory declarations, undocumented buggy states, incomplete feature verification, operational setup confusion.
SRC: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents

### Armin Ronacher's 2025 agentic-coding recommendations are language- and tooling-opinionated: Go over Python, plain SQL over ORMs, shell scripts over MCP
Runs `claude --dangerously-skip-permissions`, assigns a task and 'rarely interrupt[s] it'. Go preferred for 'explicit context systems, straightforward test execution, structural interfaces, and ecosystem stability'; Python problematic because agents struggle with 'magic (eg: Pytest's fixture injection)' and slow interpreter boot. 'Anything can be a tool' — shell scripts, MCP servers, log files; tools must be fast, user-friendly, and 'protected against an LLM chaos monkey using them completely wrong'. Custom tools are 'normal scripts that it just runs' rather than MCP-dependent. On-disk: Makefile with critical commands, pidfiles to prevent duplicate service spawn, log files alongside terminal output, CLAUDE.md noting quirks. 'Logging is super important' — his sign-in flow logs emails to stdout in debug mode so the agent can complete a full sign-in with a remote-controlled browser unaided. Warns: prefer 'stable ecosystems with little churn', avoid inheritance and 'overly clever hacks', and be 'even more conservative about upgrades than before' because agent breadcrumb comments go stale.
SRC: https://lucumr.pocoo.org/2025/6/12/agentic-coding/

### Ronacher (Jun 2026) draws the line at what loops should be allowed to produce: mechanical, verifiable artifacts — not lasting code
Two nested loops: the agent loop (model calls tools) and the harness loop (external orchestration). 'The task stays alive beyond the point where the model by itself would normally have said: "I am done."' The harness, not the human, now decides completion. He endorses loops for code porting, performance exploration, security scanning, research — 'loops that produce artifacts without necessity of longevity or that create some form of clearly verifiable mechanical translation.' Warns loops write 'defensive, complex, duplicative implementations' and produce 'codebases that are not merely hard to maintain by humans, but that assume machine participation as part of their maintenance model.' Predicts adoption anyway: 'If attackers and reporters loop, defenders will eventually need to loop too to keep up' and 'some startups will do with five people what used to require fifty.'
SRC: https://lucumr.pocoo.org/2026/6/23/the-coming-loop/

### Thorsten Ball's Amp workflow: one thread per task, keep threads under ~100k tokens, verify with screenshots
'A lot of problems… can be traced back to them not starting new threads often enough.' Keeps conversations under ~100k tokens to avoid Claude's 'doom loop' where the model repeatedly tries fixing the same issue. Prompt pattern is three-beat: analysis ('Analyze how we handle X') → clarifying question ('Don't we remove them somewhere in Y?') → action ('Okay, make that change!'). Context sources he leans on: specific file paths, recent git commits ('incredible amount of meta information'), Storybook URLs, `git diff`. Verification is dominated by Playwright screenshots of running components; 'Run the build and fix all the errors' is a standalone prompt. Uses git staging as the accept/reject model; treats threads as checkpoints.
SRC: https://ampcode.com/how-i-use-amp

### Amp's manual formalises the thread hygiene rule and the Oracle second-opinion pattern
'Use one thread per task.' 'Threads and tasks can go on forever but shouldn't. Do not ask the agent to write database migrations in the same thread as it previously changed CSS.' Oracle = 'a powerful "second opinion" model that's better suited for complex reasoning or analysis tasks', exposed as an `oracle` tool; 'We recommend explicitly asking Amp's main agent to use the oracle when you think it will be helpful.' Subagent limits stated bluntly: 'Subagents work in isolation — they can't communicate with each other, you can't guide them mid-task, they start fresh without your conversation's accumulated context.' AGENTS.md lookup order: AGENTS.md in current/parent dirs and subtrees → `$HOME/.config/amp/AGENTS.md` → `$HOME/.config/AGENTS.md` → `/etc/ampcode/AGENTS.md`; falls back to AGENT.md or CLAUDE.md if no AGENTS.md. Supports `@-mentions` with globs (`@doc/*.md`, `@.agent/**/*.md`) and YAML frontmatter `globs:` so guidance only applies when matching files are modified. On-disk: `.agents/skills/` (project, committable), `~/.config/agents/skills/` (personal), `.agents/checks/` (Markdown + YAML frontmatter), `.amp/plugins/`.
SRC: https://ampcode.com/manual

### Simon Willison argues against over-prescribing process and for letting the model exercise judgement — the clearest counterweight to the skills-and-specs camp
Rather than instructing 'only use automated testing for larger features', let the model 'use their own judgement' about when tests are necessary. On subagents: 'tell Fable to use other models for smaller tasks, applying its own judgement about which model to use' — Sonnet for substantive work, Haiku for trivial edits — so that 'judgment, review, and synthesis stay with the main loop'. He warns against over-specifying test requirements. Post dated Jul 3, 2026.
SRC: https://simonwillison.net/2026/Jul/3/judgement/

### Willison's durable practical rules (Mar 2025, still his baseline): set reasonable expectations, context is king, ask for options, tell them exactly what to do, you have to test what it writes
'LLMs are still fancy autocomplete' — treat as 'an over-confident pair programming assistant'. Context: 'starting fresh resets context to zero, which sometimes fixes unproductive conversations'; he prefers interfaces where context stays visible. Ask for options during research ('options for HTTP libraries in Rust') to surface battle-tested rather than cutting-edge choices. For production code, be directive: detailed specs, function signatures, technology preferences. 'Your responsibility as a software developer is to deliver working systems' — testing is non-negotiable. Warns about training cut-off dates affecting library knowledge, and that 'LLMs amplify existing expertise'.
SRC: https://simonwillison.net/2025/Mar/11/using-llms-for-code/

### Willison's 2026 coding-agent notes: auto mode default is safer than approval fatigue, but prompt injection remains unsolved; agents should record video demos to prove work
On auto mode (Aug 8, 2026): 'confirmation fatigue is real, and asking humans to click OK every few steps is clearly not going to result in safe behavior' — while worrying agents could be tricked by malicious third-party packages. Released `shot-scraper video` (Jun 30, 2026) so agents can record demonstrations, because 'proving code actually works' matters. On frontier-lab agent intrusions (Jul 28, 2026): 'the very best frontier models, unencumbered by additional guardrails, will find an exploit if there is one to be found.' Cites Geoffrey Litt: developers must maintain enough code understanding to 'participate further with the model' and avoid cognitive debt. Also notes newer Claude models sometimes hallucinate invented fields in tool schemas ('Better Models: Worse Tools', Jul 4, 2026).
SRC: https://simonwillison.net/tags/coding-agents/

### Addy Osmani's 'agentic engineering' (Feb 4, 2026): testing is the single biggest differentiator between agentic engineering and vibe coding
Four-stage loop: write specifications before prompting → task the agent then scrutinise output → run comprehensive test suites to validate iterations → maintain documentation, version control, production monitoring. Verbatim: 'The single biggest differentiator between agentic engineering and vibe coding is testing.' Without tests, 'it'll cheerfully declare "done" on broken code.' 'If you understand system design, security patterns, performance tradeoffs - you can leverage AI as a massive force multiplier.' Warnings: skill atrophy for juniors who ship without learning patterns; poor architecture invites 'weird abstractions'; false confidence because 'demos succeed; scaling, modification, and security reveal brittleness'. 'Human architectural ownership remains non-negotiable.'
SRC: https://addyosmani.com/blog/agentic-engineering/

### cc-sdd v3.0 (Kiro-inspired) is the most explicitly 'long-running autonomous' spec kit: 17 skills, 8 agents, boundary-first specs, per-task fresh implementer + independent reviewer + auto-debug
Entry point `/kiro-discovery` routes work into one of five paths (extend an existing spec / implement directly with no spec / one new spec / decompose into multiple specs / mixed) and writes `brief.md` plus `roadmap.md`. `/kiro-impl`: 'Each task gets a fresh implementer running TDD (RED → GREEN) behind a feature flag, an independent reviewer, and an auto-debug pass that investigates root causes in a clean context when the implementer is blocked or the reviewer rejects twice. Learnings from earlier tasks propagate forward via `## Implementation Notes` in tasks.md. 1 task per iteration, safe to re-run after interruption.' `design.md` includes a File Structure Plan driving task boundaries; tasks carry `_Boundary:_` and `_Depends:_` annotations; 'Review and validation look for boundary violations, not just style issues.' Philosophy: 'cc-sdd treats the spec as a contract between parts of the system, not a master command document handed to the agent. Code remains the source of truth.'
SRC: https://raw.githubusercontent.com/gotalab/cc-sdd/main/README.md

### GitHub's Spec Kit defines the canonical SDD command chain and a constitution artifact, across 30+ agents
Chain: `/speckit.constitution` (governing principles) → `/speckit.specify` (the what and why, not the tech stack) → `/speckit.clarify` (recommended before plan; formerly /quizme) → `/speckit.plan` (tech stack and architecture) → `/speckit.tasks` → `/speckit.analyze` (cross-artifact consistency & coverage, run after tasks before implement) → `/speckit.implement` → `/speckit.converge` (assess codebase against spec/plan/tasks and append remaining work). Also `/speckit.checklist` — 'unit tests for English'. `/speckit.taskstoissues` converts task lists to GitHub issues. Install: `uv tool install specify-cli`; `specify init my-project --integration copilot`. Template resolution priority: `.specify/templates/overrides/` > `.specify/presets/templates/` > `.specify/extensions/templates/` > `.specify/templates/`. Codex CLI and skills mode use `$speckit-*` instead of slash commands. Core philosophy: 'specifications become executable, directly generating working implementations rather than just guiding them.'
SRC: https://raw.githubusercontent.com/github/spec-kit/main/README.md

### Cline's Memory Bank is six fixed Markdown files that are re-read every session — the opposite pole from Pocock's near-empty CLAUDE.md
`memory-bank/projectbrief.md` (foundation: core requirements and goals), `productContext.md` (why the project exists, problems it solves, UX goals), `activeContext.md` (current focus, recent changes, next steps — 'updates most frequently'), `systemPatterns.md` (architecture, design patterns, component relationships), `techContext.md` (tech stack, setup, constraints, dependencies), `progress.md` (what works, what's left, known issues). Three magic phrases: 'initialize memory bank', 'follow your custom instructions', 'update memory bank'. Context-exhaustion workflow: say 'update memory bank' → start a fresh conversation → say 'follow your custom instructions'.
SRC: https://docs.cline.bot/prompting/cline-memory-bank

### Roo Code encodes the workflow as tool-permission-scoped modes, with Orchestrator ('Boomerang') delegating via new_task
Code (💻) — default, full tool access (read, edit, command, mcp). Ask (❓) — read + mcp only; cannot modify files or run commands. Architect (🏗️) — read, mcp, and edit restricted to markdown files only. Debug (🪲) — full access with instructions emphasising methodical analysis and confirmation. Orchestrator (🪃) — 'A strategic workflow orchestrator that breaks down complex tasks and delegates them to specialized modes', uses `new_task` to assign work rather than executing tools directly. Switch via dropdown, slash commands (`/architect`, `/ask`, `/debug`, `/code`, `/orchestrator`), or ⌘+. / Ctrl+.
SRC: https://roocodeinc.github.io/Roo-Code/basic-usage/using-modes

### Cursor rules: `.cursor/rules/*.mdc` with three frontmatter fields and four application types; official guidance is 'Keep rules under 500 lines'
Frontmatter: `description` (human-readable summary), `globs` (path patterns for auto-attach), `alwaysApply` (boolean). Four types: Always Apply (every chat), Apply Intelligently (agent decides from description), Apply to Specific Files (glob match), Apply Manually (`@rule-name`). Subdirectories supported (`.cursor/rules/frontend/components.mdc`). Nested AGENTS.md is a supported simple alternative; 'more specific instructions take precedence over parent directory versions'. Size guidance: 'Keep rules under 500 lines' and split oversized rules into composable units; 'Reference files rather than duplicating content to prevent staleness.'
SRC: https://cursor.com/docs/context/rules

### Steve Yegge's Beads replaces markdown plans with a dependency-aware issue graph and explicitly bans MEMORY.md files
'Beads provides a persistent, structured memory for coding agents. It replaces messy markdown plans with a dependency-aware graph, allowing agents to handle long-horizon tasks without losing context.' Dolt-backed (version-controlled SQL, cell-level merge, native branching). Loop: `bd create` → dependency graph → `bd ready` (tasks with no open blockers) → `bd update --claim` (atomic) → `bd close` → blockers released → back to ready. Hash-based IDs (`bd-a1b2`) prevent merge collisions across multi-agent/multi-branch work. Hierarchical epics: `bd-a3f8` / `bd-a3f8.1` / `bd-a3f8.1.1`. 'Compaction: Semantic "memory decay" summarizes old closed tasks to save context window.' The AGENTS.md snippet it installs says verbatim: 'Use `bd remember "insight"` for persistent project memory; do not create MEMORY.md files.' and 'Do not use markdown TODO lists for task tracking.' `bd setup` supports codex, claude, factory, cursor, mux.
SRC: https://raw.githubusercontent.com/steveyegge/beads/main/README.md

### steipete's widely-forked `agent-rules` repo is now explicitly deprecated — a caution against citing 2025-era rules kits
The entire README is now: 'AI moves fast. This was old stuff I used mid 2025 when I was still using Cursor. My new work is here: https://github.com/steipete/agent-scripts'. The successor repo drops rules-files in favour of skills as 'the main routing layer', with terse SKILL.md bodies, a `scripts/validate-skills` git hook, and a pointer-style AGENTS.md so downstream repos never copy shared blocks.
SRC: https://raw.githubusercontent.com/steipete/agent-rules/main/README.md

### steipete/agent-scripts documents a verified, non-obvious Claude Code skill-discovery constraint
'Claude Code loads only `~/.claude/skills/<name>/SKILL.md` (exactly one level deep; per-entry symlinks are followed, category subfolders are not scanned — verified on 2.1.197). It gets a flat per-skill link mirror.' Codex by contrast 'scans nested dirs, so it gets whole-root links'. Global pointers maintained by `scripts/sync-skills`: `~/.codex/AGENTS.md -> agent-scripts/AGENTS.MD`, `~/.claude/CLAUDE.md -> agent-scripts/AGENTS.MD`. Downstream repos use a pointer-style AGENTS.MD: 'READ ~/Projects/agent-scripts/AGENTS.MD BEFORE ANYTHING (skip if missing).' Skill frontmatter rule: 'Keep descriptions short and generic; optimize for routing, not documentation.'
SRC: https://raw.githubusercontent.com/steipete/agent-scripts/main/README.md

### claude-flow has been renamed Ruflo and repositioned as a 'meta-harness', with two install paths of very different footprint
'Agent = Model + Harness. The model writes; the harness gives it tools, memory, loops, sandboxes, and controls.' Plugin path = slash commands + some skills + agent definitions, zero files in your workspace, no hooks. CLI path (`npx ruflo init`) = 98 agents, 60+ commands, 30 skills, MCP server, hooks, daemon, and writes `.claude/`, `.claude-flow/`, `CLAUDE.md`, helpers, settings. 35 plugins covering orchestration (swarm, autopilot, loop-workers, workflows, federation), memory (agentdb, rag-memory, rvf, ruvector, knowledge-graph), intelligence, and code quality (testgen, browser, jujutsu, docs). Explicitly warns that plugin-track MCP tool names differ from CLI-track names.
SRC: https://raw.githubusercontent.com/ruvnet/claude-flow/main/README.md

### SuperClaude Framework v4.3.0: 30 slash commands, 20 agents, 7 behavioral modes, 8 MCP servers, plus a four-file project memory convention
Self-described as 'a meta-programming configuration framework that transforms Claude Code into a structured development platform through behavioral instruction injection and component orchestration.' Its own contributor memory files: PLANNING.md (architecture, design principles, absolute rules — read at session start), TASK.md (current tasks, priorities, backlog — daily), KNOWLEDGE.md (accumulated insights, troubleshooting), CONTRIBUTING.md. 'Claude Code reads these files at session start.' Commands are namespaced `/sc:*`. Install via pipx/PyPI (`superclaude`) or npm (`@bifrost_inc/superclaude`). README notes the TypeScript plugin system in older docs 'is not yet available (planned for v5.0)'. Not affiliated with Anthropic.
SRC: https://raw.githubusercontent.com/SuperClaude-Org/SuperClaude_Framework/master/README.md

### awesome-claude-code has been restructured and now carries a dedicated 'Ralph Wiggum' subsection under Agent Orchestration, plus Memory & Context Persistence and Linting sections
Top-level ToC: Start Here, From Anthropic, Documentation/Knowledge/Learning (incl. Obsidian), Research & Scientific Inquiry, Providers/Runtime/Integration Infrastructure, Remote Control/Notifications/Voice I/O, Alternative Clients, Status Lines, Design & UI/UX, Writing & Prose Quality, Creative Media, Infrastructure & DevOps, Security, Agent Orchestration (→ Ralph Wiggum), Skills, Memory & Context Persistence, Observability & Monitoring (Session Monitors / Usage & Cost / Observability), Linting. The current iteration deliberately excludes previously-listed 'legacy' resources, which live in README_ALTERNATIVES/ — so absence from the list is not a quality signal.
SRC: https://raw.githubusercontent.com/hesreallyhim/awesome-claude-code/main/README.md

### Pocock's `/wayfinder` is the only published pattern I found for work too big for any single spec: a 'map' issue with decision-ticket children
'A loose idea has arrived — too big for one agent session, and wrapped in fog.' The map is a single issue labelled `wayfinder:map`; its tickets are child issues, each 'sized to one 100K token agent session'. Map body sections: Destination, Notes, Decisions so far, Not yet specified (fog of war), Out of scope. 'The map is an index, not a store' — a decision lives in exactly one place, its ticket. Hard rule: 'Wayfinder is planning by default: each ticket resolves a decision… The pull to just do the work is usually the signal you've reached the edge of the map and it's time to hand off.' Also 'Refer by name' — never bare issue ids, because 'A wall of #42, #43, #44 is illegible'.
SRC: https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/wayfinder/SKILL.md

### Pocock's `/research` skill mandates a background agent, primary sources only, and one cited Markdown file placed by existing repo convention
Verbatim: 'Spin up a background agent to do the research, so you keep working while it reads. Its job: 1. Investigate the question against primary sources — official docs, source code, specs, first-party APIs — not a secondary write-up of them. Follow every claim back to the source that owns it. 2. Write the findings to a single Markdown file, citing each claim's source. 3. Save it where the repo already keeps such notes; match the existing convention, and if there is none, put it somewhere sensible and say where.'
SRC: https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/research/SKILL.md

### Pocock's `/triage` is a formal state machine over two category roles and five state roles, with a mandatory AI-disclosure header on every tracker comment
Categories: `bug`, `enhancement`. States: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. 'Every triaged issue should carry exactly one category role and one state role. If state roles conflict, flag it and ask the maintainer before doing anything else.' Transitions: unlabeled → needs-triage → {needs-info | ready-for-agent | ready-for-human | wontfix}; needs-info → needs-triage on reporter reply. Treats external PRs as 'an issue with attached code' — same roles, same machine. Every posted comment must begin: `> *This was generated by AI during triage.*` Reference docs: AGENT-BRIEF.md (durable agent briefs), OUT-OF-SCOPE.md (`.out-of-scope/` knowledge base).
SRC: https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/triage/SKILL.md

## EXAMPLES
### Matt Pocock's HITL Ralph — single iteration, human watches
FILE: ralph-once.sh at repo root, chmod +x
```
#!/bin/bash

claude --permission-mode acceptEdits "@PRD.md @progress.txt \
1. Read the PRD and progress file. \
2. Find the next incomplete task and implement it. \
3. Commit your changes. \
4. Update progress.txt with what you did. \
ONLY DO ONE TASK AT A TIME."
```
SRC: https://www.aihero.dev/getting-started-with-ralph

### Matt Pocock's AFK Ralph — capped loop, Docker sandbox, completion sigil
FILE: afk-ralph.sh at repo root; reads PRD.md + progress.txt, both committed
```
#!/bin/bash
set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <iterations>"
  exit 1
fi

for ((i=1; i<=$1; i++)); do
  result=$(docker sandbox run claude --permission-mode acceptEdits -p "@PRD.md @progress.txt \
  1. Find the highest-priority task and implement it. \
  2. Run your tests and type checks. \
  3. Update the PRD with what was done. \
  4. Append your progress to progress.txt. \
  5. Commit your changes. \
  ONLY WORK ON A SINGLE TASK. \
  If the PRD is complete, output <promise>COMPLETE</promise>.")

  echo "$result"

  if [[ "$result" == *"<promise>COMPLETE</promise>"* ]]; then
    echo "PRD complete after $i iterations."
    exit 0
  fi
done
```
SRC: https://www.aihero.dev/getting-started-with-ralph

### Anthropic's structured PRD item — the `passes` field the agent flips, in JSON specifically because models tamper with Markdown
FILE: prd.json (Pocock) / feature list JSON + claude-progress.txt + init.sh (Anthropic)
```
{
  "category": "functional",
  "description": "New chat button creates a fresh conversation",
  "steps": [
    "Click the 'New Chat' button",
    "Verify a new conversation is created",
    "Check that chat area shows welcome state"
  ],
  "passes": false
}
```
SRC: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents

### Pocock's `/implement` SKILL.md — the entire orchestration skill is six lines
FILE: skills/engineering/implement/SKILL.md — `disable-model-invocation: true` marks user-invoked orchestration skills
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
SRC: https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/implement/SKILL.md

### Pocock's `/grill-me` — the whole skill is three sentences
FILE: skills/productivity/grill-me/SKILL.md — 'design tree' is from Brooks, The Design of Design
```
Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one by one. And finally, if a question can be answered by exploring the code base, explore the code base instead.
```
SRC: https://www.aihero.dev/5-agent-skills-i-use-every-day

### Pocock's spec template (from /to-spec) — the exact section list, and the explicit ban on file paths
FILE: published to the configured issue tracker with the `ready-for-agent` label — NOT written to a file in the repo
```
## Problem Statement
## Solution
## User Stories
   1. As an <actor>, I want a <feature>, so that <benefit>
   ("This list of user stories should be extremely extensive")
## Implementation Decisions
   - modules built/modified, interfaces modified, technical clarifications,
     architectural decisions, schema changes, API contracts, specific interactions
   "Do NOT include specific file paths or code snippets. They may end up being
    outdated very quickly."
   Exception: a prototype snippet that encodes a decision more precisely than prose
   (state machine, reducer, schema, type shape) may be inlined.
## Testing Decisions
   - what makes a good test, which modules tested, prior art for the tests
## Out of Scope
## Further Notes
```
SRC: https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/to-spec/SKILL.md

### Anthropic's canonical Claude-interviews-you spec prompt
FILE: SPEC.md at repo root; then START A FRESH SESSION to execute it — 'The most useful specs are self-contained: they name the files and interfaces involved, state what is out of scope, and end with an end-to-end verification step'
```
I want to build [brief description]. Interview me in detail using the AskUserQuestion tool.

Ask about technical implementation, UI/UX, edge cases, concerns, and tradeoffs. Don't ask obvious questions, dig into the hard parts I might not have considered.

Keep interviewing until we've covered everything, then write a complete spec to SPEC.md.
```
SRC: https://code.claude.com/docs/en/best-practices

### Anthropic's adversarial review-against-plan prompt (fresh subagent context)
FILE: .claude/agents/<name>.md for reusable reviewers; or the bundled /code-review skill
```
Use a subagent to review the rate limiter diff against PLAN.md. Check that
every requirement is implemented, the listed edge cases have tests, and
nothing outside the task's scope changed. Report gaps, not style preferences.
```
SRC: https://code.claude.com/docs/en/best-practices

### Anthropic's fan-out pattern for large mechanical migrations
FILE: files.txt; `--allowedTools` restricts what Claude can do when running unattended
```
# Step 1: have Claude write the list to files.txt
# Step 2:
for file in $(cat files.txt); do
  claude -p "Migrate $file from React to Vue. Return OK or FAIL." \
    --allowedTools "Edit,Bash(git commit *)"
done
# Step 3: refine the prompt on the first 2-3 files, then run at scale
```
SRC: https://code.claude.com/docs/en/best-practices

### Anthropic subagent definition file
FILE: .claude/agents/security-reviewer.md
```
---
name: security-reviewer
description: Reviews code for security vulnerabilities
tools: Read, Grep, Glob, Bash
model: opus
---
You are a senior security engineer. Review code for:
- Injection vulnerabilities (SQL, XSS, command injection)
- Authentication and authorization flaws
- Secrets or credentials in code
- Insecure data handling

Provide specific line references and suggested fixes.
```
SRC: https://code.claude.com/docs/en/best-practices

### Anthropic skill with side effects — the flag that makes it manual-only
FILE: .claude/skills/fix-issue/SKILL.md — invoked as /fix-issue 1234
```
---
name: fix-issue
description: Fix a GitHub issue
disable-model-invocation: true
---
Analyze and fix the GitHub issue: $ARGUMENTS.

1. Use `gh issue view` to get the issue details
...
8. Push and create a PR
```
SRC: https://code.claude.com/docs/en/best-practices

### Pocock's minimal CLAUDE.md, and his plan-mode rules snippet (the only global rules he keeps)
FILE: ~/.claude/CLAUDE.md (global) — he publishes a heredoc one-liner to append it
```
# entire CLAUDE.md:
you are on WSL on Windows

# the plan-mode rules he does add:
## Plan Mode

- Make the plan extremely concise. Sacrifice grammar for the sake of concision.
- At the end of each plan, give me a list of unresolved questions to answer, if any.
```
SRC: https://www.aihero.dev/my-agents-md-file-for-building-plans-you-actually-read

### Pocock's tracer-bullet block to paste into a Ralph prompt or build-feature skill
FILE: inline in the loop prompt, or a skill body
```
## Tracer Bullets

When building features, build a tiny, end-to-end slice of the feature first, seek feedback, then expand out from there.

Tracer bullets comes from the Pragmatic Programmer. When building systems, you want to write code that gets you feedback as quickly as possible. Tracer bullets are small slices of functionality that go through all layers of the system, allowing you to test and validate your approach early. This helps in identifying potential issues and ensures that the overall architecture is sound before investing significant time in development.
```
SRC: https://www.aihero.dev/tracer-bullets

### Pocock's explicit feedback-loop clause for a loop prompt (TypeScript example — swap the commands for any stack)
FILE: the Ralph prompt string; enforced hard via a pre-commit hook so a red build cannot be committed
```
Before committing, run ALL feedback loops:
1. TypeScript: npm run typecheck (must pass with no errors)
2. Tests: npm run test (must pass)
3. Lint: npm run lint (must pass)
Do NOT commit if any feedback loop fails. Fix issues first.

# Android/Gradle equivalent for the same slot:
#   ./gradlew :module:compileDevelopDebugKotlin
#   ./gradlew testDevelopDebugUnitTest
#   ./gradlew detekt lintDevelopDebug
```
SRC: https://www.aihero.dev/tips-for-ai-coding-with-ralph-wiggum

### Pocock's task-prioritisation clause — forces the agent off easy wins onto risk
FILE: Ralph prompt string. He pairs it with: use HITL for architectural/risky tasks, AFK only once the foundation is solid
```
When choosing the next task, prioritize in this order:
1. Architectural decisions and core abstractions
2. Integration points between modules
3. Unknown unknowns and spike work
4. Standard features and implementation
5. Polish, cleanup, and quick wins
Fail fast on risky work. Save easy wins for later.
```
SRC: https://www.aihero.dev/tips-for-ai-coding-with-ralph-wiggum

### Pocock's software-quality clause — the counter to 'the repo wins'
FILE: AGENTS.md or the Ralph prompt. Context: 'You can write "never use any types" in your prompt. But if Ralph sees any throughout your existing code, it will follow the codebase, not your instructions.'
```
This codebase will outlive you. Every shortcut you take becomes
someone else's burden. Every hack compounds into technical debt
that slows the whole team down.

You are not just writing code. You are shaping the future of this
project. The patterns you establish will be copied. The corners
you cut will be cut again.

Fight entropy. Leave the codebase better than you found it.
```
SRC: https://www.aihero.dev/tips-for-ai-coding-with-ralph-wiggum

### Pocock's pre-commit gate — hooks as the hard verification boundary
FILE: .husky/pre-commit + .lintstagedrc. Rationale: 'AI agents don't get frustrated by repetition. When code fails type checking or tests, the agent simply tries again.'
```
pnpm install --save-dev husky
pnpm exec husky init

# .husky/pre-commit
npx lint-staged
npm run typecheck
npm run test

# .lintstagedrc
{
  "*": "prettier --ignore-unknown --write"
}
```
SRC: https://www.aihero.dev/essential-ai-coding-feedback-loops-for-type-script-projects

### HumanLayer ACE-FCA on-disk layout — three prompts, three artifact dirs, three fresh contexts
FILE: thoughts/ committed to the repo; each phase runs in a fresh context window; status updates are compacted back into the plan doc after each verification step
```
.claude/commands/research_codebase.md
.claude/commands/create_plan.md
.claude/commands/implement_plan.md

thoughts/
  shared/
    research/     # compacted research findings
    plans/        # implementation plans, phase by phase
  progress.md     # completed work + current failures

# target: keep context utilization in the 40%-60% range
```
SRC: https://github.com/humanlayer/advanced-context-engineering-for-coding-agents/blob/main/ace-fca.md

### Every / compound engineering — the six-command loop and its artifact folders
FILE: docs/solutions/ (compounded learnings), docs/plans/, docs/pulse-reports/, STRATEGY.md at root, .compound-engineering/config.yaml (docs_root relocates them all). Install: /plugin marketplace add EveryInc/compound-engineering-plugin
```
/ce-brainstorm make background job retries safer
/ce-plan
/ce-work
/ce-simplify-code
/ce-code-review
/ce-compound

# autopilot:
/ce-brainstorm describe the feature
/lfg

# bug flavour (replaces brainstorm→plan→work):
/ce-debug the checkout webhook sometimes creates duplicate invoices
/ce-code-review
/ce-compound
```
SRC: https://raw.githubusercontent.com/EveryInc/compound-engineering-plugin/main/README.md

### cc-sdd v3.0 spec-driven chain with autonomous implementation
FILE: brief.md + roadmap.md (from discovery); requirements.md (EARS format with acceptance criteria); design.md (architecture + Mermaid + File Structure Plan); tasks.md with `_Boundary:_`, `_Depends:_` annotations and forward-propagated `## Implementation Notes`
```
npx cc-sdd@latest                     # Claude Code Skills (default)
npx cc-sdd@latest --codex-skills --lang ja
npx cc-sdd@latest --cursor-skills --lang zh-TW

/kiro-discovery Photo albums with upload, tagging, and sharing
/kiro-spec-init photo-albums
/kiro-spec-requirements photo-albums
/kiro-spec-design photo-albums
/kiro-spec-tasks photo-albums
/kiro-impl photo-albums
```
SRC: https://raw.githubusercontent.com/gotalab/cc-sdd/main/README.md

### GitHub Spec Kit chain including the constitution and the consistency gate
FILE: .specify/templates/ (core) < .specify/extensions/templates/ < .specify/presets/templates/ < .specify/templates/overrides/ (highest priority, resolved at runtime)
```
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@vX.Y.Z
specify init my-project --integration copilot

/speckit.constitution Create principles focused on code quality, testing standards, user experience consistency, and performance requirements
/speckit.specify Build an application that can help me organize my photos...
/speckit.clarify        # recommended before plan
/speckit.plan The application uses Vite with minimal number of libraries...
/speckit.tasks
/speckit.analyze        # cross-artifact consistency & coverage, before implement
/speckit.implement
/speckit.converge       # append remaining work as new tasks
```
SRC: https://raw.githubusercontent.com/github/spec-kit/main/README.md

### Cline Memory Bank — six fixed files, re-read every session
FILE: memory-bank/ at repo root. Context-exhaustion drill: 'update memory bank' → new conversation → 'follow your custom instructions'
```
memory-bank/
├── projectbrief.md      # foundation: core requirements and goals
├── productContext.md    # why it exists, problems solved, UX goals
├── activeContext.md     # current focus, recent changes, next steps (most volatile)
├── systemPatterns.md    # architecture, design patterns, component relationships
├── techContext.md       # tech stack, setup, constraints, dependencies
└── progress.md          # what works, what's left, known issues

# the three phrases:
"initialize memory bank"
"follow your custom instructions"
"update memory bank"
```
SRC: https://docs.cline.bot/prompting/cline-memory-bank

### Cursor rule file format
FILE: .cursor/rules/*.mdc, subdirectories allowed. Four types: Always / Apply Intelligently (from description) / Apply to Specific Files (globs) / Apply Manually (@rule-name). 'Keep rules under 500 lines'
```
---
description: React component conventions for this codebase
globs: ["src/components/**/*.tsx"]
alwaysApply: false
---

- Prefer function components with explicit prop types
- Co-locate stories next to the component

# layout:
.cursor/rules/
  react-patterns.mdc
  frontend/
    components.mdc
```
SRC: https://cursor.com/docs/context/rules

### Beads minimal AGENTS.md block — the anti-markdown-memory stance
FILE: AGENTS.md (auto-written by `bd init`); `bd setup claude|codex|cursor|factory|mux` installs hooks/skills per agent; `bd init --stealth` keeps it out of the shared repo
```
This project uses bd (beads) for issue tracking.

- Run `bd prime` for workflow context and command guidance.
- Use `bd ready`, `bd show <id>`, `bd update <id> --claim`, and `bd close <id>`.
- Use `bd remember "insight"` for persistent project memory; do not create MEMORY.md files.
- Do not use markdown TODO lists for task tracking.
```
SRC: https://raw.githubusercontent.com/steveyegge/beads/main/README.md

### steipete's pointer-style AGENTS.MD — how to share one rules file across many repos without copying it
FILE: AGENTS.MD at repo root. Claude Code only scans ~/.claude/skills/<name>/SKILL.md exactly one level deep (per-entry symlinks followed, category subfolders NOT scanned — verified on 2.1.197)
```
READ ~/Projects/agent-scripts/AGENTS.MD BEFORE ANYTHING (skip if missing).

# repo-specific rules go below this pointer.
# Do not copy the shared blocks into downstream repos.

# global symlinks maintained by scripts/sync-skills:
~/.codex/AGENTS.md  -> ~/Projects/agent-scripts/AGENTS.MD
~/.claude/CLAUDE.md -> ~/Projects/agent-scripts/AGENTS.MD
~/.claude/AGENTS.md -> ~/Projects/agent-scripts/AGENTS.MD
```
SRC: https://raw.githubusercontent.com/steipete/agent-scripts/main/README.md

### Amp granular guidance via glob-scoped frontmatter — apply rules only when matching files change
FILE: .agents/skills/ (project, committable), ~/.config/agents/skills/ (personal), .agents/checks/ (Markdown + YAML frontmatter), .amp/plugins/
```
# AGENTS.md supports @-mentions with glob patterns:
@doc/*.md
@.agent/**/*.md

# and referenced files can carry YAML frontmatter with `globs:` so their
# content is only injected when those files are being modified.

# lookup order:
#   ./AGENTS.md (and parents, and subtrees)
#   $HOME/.config/amp/AGENTS.md
#   $HOME/.config/AGENTS.md
#   /etc/ampcode/AGENTS.md
# falls back to AGENT.md or CLAUDE.md when no AGENTS.md exists
```
SRC: https://ampcode.com/manual

### Roo Code mode-scoped permissions — Architect can only edit markdown, which is a cheap way to force plan-before-code
FILE: switch via dropdown, slash command, or ⌘+. / Ctrl+.
```
/architect     # read + mcp + edit RESTRICTED TO MARKDOWN ONLY
/ask           # read + mcp only; cannot modify files or run commands
/code          # full: read, edit, command, mcp
/debug         # full, with methodical-analysis instructions
/orchestrator  # "Boomerang": delegates via new_task, does not execute tools directly
```
SRC: https://roocodeinc.github.io/Roo-Code/basic-usage/using-modes

## GOTCHAS
- **The single biggest disagreement: CLAUDE.md.** Anthropic says 'Run /init to generate a starter CLAUDE.md file… then refine over time.' Pocock says 'Never run it. If you find one that was auto-generated, delete it.' They agree on the failure mode (bloat → ignored rules) but prescribe opposite starting points. Pocock's stronger claim — that everything /init generates is either trivially discoverable from source or will go stale — is the one worth stress-testing against your repo. Note that the CLAUDE.md in this very repo is exactly the kind of file Pocock argues against: long, global, mixing red-lines with tooling preferences with doc-placement rules.
- **Second biggest: does the loop share a context or reset it?** Pocock argues Anthropic's own Ralph plugin 'guarantees' degradation because its Stop hook keeps all iterations in one session, while Anthropic's best-practices doc actively recommends Stop hooks as the deterministic verification gate. Both can be right — a Stop hook is fine as a *gate* on one turn, catastrophic as a *loop driver* across many tasks — but the published advice reads as contradictory and people implement it wrong.
- **Context-budget numbers are folklore-grade and mutually inconsistent.** Pocock: smart zone = first 40%. HumanLayer ACE-FCA: target 40–60% utilization. Thorsten Ball: keep threads under ~100k tokens. Anthropic: no number, just 'manage aggressively'. None of these are measured against a shared benchmark; treat the shape (reset early, reset often) as the transferable signal and the numbers as vibes.
- **Prescription vs judgement is a live split.** Willison (Jul 2026) argues against telling the model when to write tests, preferring 'let the model use their own judgement'. Pocock, Osmani, spec-kit, cc-sdd and compound engineering all do the opposite — heavy prescribed process encoded as skills. The prescription camp is betting on repeatability; Willison is betting on model capability outrunning your process. Both camps agree that a *vague* prompt is fine for exploration and bad for production.
- **Ronacher is the load-bearing dissent on loops.** He accepts loops for 'artifacts without necessity of longevity or… clearly verifiable mechanical translation' (porting, perf exploration, security scanning) and warns the opposite case produces 'codebases that are not merely hard to maintain by humans, but that assume machine participation as part of their maintenance model.' Anyone adopting Ralph/lfg/kiro-impl on a long-lived product codebase is taking the bet he explicitly declines.
- **'The repo wins' beats every instruction file.** Pocock: 'You can write "never use any types" in your prompt. But if Ralph sees any throughout your existing code, it will follow the codebase, not your instructions… Agents amplify what they see.' Directly relevant to a codebase with documented legacy patterns (Reductor, XML views, 2019-2022 idioms): a rules file saying 'don't write new Reductor' is fighting thousands of lines of contrary evidence. Machine-enforced gates (hooks, lint rules, detekt rules) are the only reliable answer.
- **Markdown memory files are contested, not settled.** Cline's Memory Bank is six always-read Markdown files. Beads' installed AGENTS.md snippet says verbatim 'do not create MEMORY.md files' and 'Do not use markdown TODO lists for task tracking.' Pocock would classify the Memory Bank as exactly the stale, budget-burning global context he tells you to delete. Every/CE splits the difference: learnings go in `docs/solutions/` but are read *on demand* by the next brainstorm, not injected every session.
- **Where specs live is a real fork with real consequences.** Pocock publishes specs to the *issue tracker* and explicitly forbids file paths and code snippets in them ('They may end up being outdated very quickly'). HumanLayer keeps `thoughts/` in-repo. spec-kit keeps `specs/` in-repo. CE keeps `docs/plans/`. In-repo specs review well in PRs and rot with the code; tracker specs stay canonical but are invisible to the agent unless a config file tells it how to fetch them (which is why Pocock's setup writes `docs/agents/issue-tracker.md`).
- **Vertical slicing vs boundary-first is a genuine methodological conflict.** Pocock names horizontal slicing an anti-pattern and mandates tracer bullets cutting every layer. cc-sdd v3.0 does the opposite emphasis: a File Structure Plan in `design.md` drives task boundaries, and 'Review and validation look for boundary violations, not just style issues.' Pocock does carve out the exception (wide refactors → expand–contract), which is the reconciliation, but the default posture is opposed.
- **Adversarial review over-reports.** Anthropic's own caveat: 'A reviewer prompted to find gaps will usually report some, even when the work is sound, because that is what it was asked to do. Chasing every finding leads to over-engineering: extra abstraction layers, defensive code, and tests for cases that can't happen.' CE's answer is 'report-only… local apply is explicit'. If you wire a 12-subagent review into a loop without a severity filter, you will manufacture work.
- **Auto-generated ceremony is a cost nobody prices.** CE ships 33 skills, SuperClaude 30 commands + 20 agents + 7 modes + 8 MCP servers, Ruflo 98 agents / 60+ commands / 30 skills / hooks / daemon. Ruflo's own README concedes the plugin path writes zero files while the CLI path writes `.claude/`, `.claude-flow/`, `CLAUDE.md`, helpers and settings, and that MCP tool names differ between the two paths. More surface area = more instruction budget consumed before any work starts.
- **Rules kits rot within a year.** `steipete/agent-rules` — one of the most-cited 2025 rules repos — now has a README consisting solely of: 'AI moves fast. This was old stuff I used mid 2025 when I was still using Cursor.' Anything you find dated 2025 in this space needs a freshness check before adoption. awesome-claude-code has likewise been restructured such that absence from the current list is not a quality signal (legacy entries live in README_ALTERNATIVES/).
- **Sandboxing costs you your own config.** Pocock's Docker-sandbox recommendation for AFK loops has an explicit tradeoff: 'your global AGENTS.md and user skills won't be loaded.' If your workflow depends on user-scope skills, an AFK loop in a sandbox is running a different agent than the one you tested.
- **Skill discovery has undocumented depth limits.** steipete verified (on Claude Code 2.1.197) that only `~/.claude/skills/<name>/SKILL.md` is loaded — exactly one level deep; per-entry symlinks are followed but category subfolders are not scanned. Codex scans nested dirs. Organising your skills into `skills/engineering/` and `skills/productivity/` categories works in the source repo but will silently fail if you symlink the category folder into `~/.claude/skills/`.
- **Cost and the 'golden age' framing.** Pocock is on the Anthropic 5x Max plan (~£90/month) and says 'most of my usage is HITL', not AFK. He also declines to recommend local models: 'I don't think open source models you can run on your laptop are good enough for Ralph yet.' Anyone budgeting for AFK loops on the basis of published enthusiasm should note the authors themselves mostly run human-in-the-loop.
- **Osmani's skill-atrophy warning is the one nobody has a process answer for.** Junior developers 'risk shipping features without learning underlying patterns'; Willison echoes Geoffrey Litt on needing enough understanding to 'participate further with the model'. Every methodology here optimises throughput; none of them has a documented mechanism for keeping human comprehension current except HumanLayer's 'Reading 200-line plans beats reviewing 2000-line PRs' and Pocock's `/teach` skill.

## OPEN
- The 'the agent is the folder' quote widely attributed to Kieran Klaassen, along with the '44 agents' and `/orchestrate` dispatch-layer claims, appear only in secondary write-ups. I fetched render.com's Jul 26 2026 profile and it does NOT contain those quotes (it covers his '50/50 rule', stack, and the ideate/doc-review/brainstorm/lfg commands). The primary source for the dispatch layer is probably a podcast transcript or an every.to piece I did not reach — verify before quoting.
- Matt Pocock's 'Sand Castle' (a TypeScript framework for orchestrating sandboxed agents in git worktrees + Docker) surfaced only in a third-party summary of his workshop. It does not appear in aihero.dev's public sitemap. Whether it is public, and what its on-disk contract is, is unverified.
- The `/write-a-prd` and `/prd-to-issues` skills referenced in Pocock's '7 Phases' post appear to have been renamed to `/to-spec` and `/to-tickets` (the skills repo confirms 'This skill used to be called /to-prd' and 'Formerly /to-issues'), but the 7-phases post still links to the old names — so the published workflow diagram (Idea → /write-a-prd → PRD → /prd-to-issues → Kanban → ralph.sh → Ralph Loop → Manual QA) may be stale relative to the current kit.
- Nobody publishes an A/B measurement. Every claim here — 40% smart zone, 40-60% utilization, 80/20 plan-to-execute, 'TDD has been the most consistent way to improve agent outputs' — is practitioner assertion. The one cited study (arxiv 2602.11988, on unnecessary context files making tasks harder) I did not fetch or verify.
- How any of these methodologies behave on a large JVM/Gradle/Android codebase is untested in the literature. Every published example is TypeScript, Go, Rails, or Python. The specific frictions — 2-10 minute Gradle builds destroying the tight feedback loop that Pocock/Anthropic both depend on, no cheap `tsc`-equivalent for fast type feedback, instrumented tests requiring an emulator — are unaddressed. The closest transferable primitives are: fast per-module `compileDebugKotlin` as the typecheck analogue, unit tests as the test analogue, detekt/lint as the lint analogue, and a pre-push/pre-commit hook as the hard gate.
- cc-sdd's per-task 'feature flag' requirement in `/kiro-impl` (TDD RED→GREEN behind a feature flag) is stated but its mechanics are only in docs/guides/skill-reference.md, which I did not fetch. Whether it means literal runtime flags or branch isolation matters a lot for adoption cost.
- Anthropic's `/goal` condition and Stop-hook 8-block override are documented in best-practices but I did not fetch /docs/en/goal or /docs/en/hooks to confirm exact configuration syntax.
- Whether Every's `/ce-compound` learnings actually improve subsequent runs, or just accumulate a `docs/solutions/` directory nobody reads, is asserted but unmeasured. Note they ship `/ce-compound-refresh` to 'Refresh stale or drifting learnings' — an implicit admission that compounded knowledge rots too.

# Fast, reliable codebase search for coding agents (2025-2026), with Android multi-module specifics

## SUMMARY
Consensus 2025-2026: agentic lexical search first, structural (AST) second, LSP/graph third, embeddings optional fourth. Anthropic's Boris Cherny on HN: "Claude Code doesn't use RAG currently. In our testing we found that agentic search out-performed RAG for the kinds of things people use Code for." Cline published the same position (chunking tears code's logic apart; an index is "a snapshot frozen in time"; embeddings create "a secondary representation of your most valuable IP"). Anthropic's context-engineering post frames it as "just in time" retrieval: keep lightweight identifiers (file paths), load with glob/grep/head/tail at runtime, exploit "progressive disclosure" (file sizes suggest complexity, naming conventions hint at purpose). AAAI 2026 / arXiv 2602.23368 (Amazon) measured agentic keyword search at over 90% of RAG performance with no vector DB.

The counterweight is real. Cursor's own A/B data shows semantic search gives +12.5% average answer accuracy (6.5-23.5% by model), and removing it costs 2.6% code retention in codebases over 1,000 files and +2.2% user dissatisfaction. Sourcegraph argues "agentic coding's productivity ceiling is set by context, not model quality" and pushes deterministic SCIP-backed code intelligence over MCP rather than embeddings. The synthesis everyone converges on: expose three distinct tools - lexical (ripgrep/Zoekt), structural (ast-grep/tree-sitter), graph (LSP/SCIP) - and let the agent choose per question.

For a large Android multi-module Kotlin repo the practical stack is: (1) ripgrep + fd baseline; (2) ast-grep with sgconfig.yml + rules/ for Kotlin structural queries, plus the token-cheap `ast-grep outline`; (3) `kotlin-lsp` Claude Code plugin or Serena MCP for definitions/references; (4) a generated, committed module map (`./gradlew createModuleGraph` from dev.iurysouza.modulegraph, or `./gradlew projects`) plus `com.jraska.module.graph.assertion` to enforce layering; (5) layered per-module CLAUDE.md / AGENTS.md rather than one root file; (6) MADR ADRs in docs/decisions/ and drift-detection in CI.

Android-specific landmines: scip-java explicitly states "Android integration is not yet supported"; ast-grep's Kotlin grammar is a repackaged tree-sitter-kotlin whose upstream cross-validation is only 61.2% structural match against JetBrains' reference parser; repomix `--compress` has no Kotlin tree-sitter query file; JetBrains' official Kotlin LSP lists AGP support as experimental. So structural/semantic tooling for Kotlin is materially weaker than for TS/Python/Go, which pushes the balance further toward ripgrep + generated, committed maps.

## KEY FACTS
### Claude Code uses agentic search, not RAG - stated by its creator
bcherny (Boris Cherny, Anthropic) on Hacker News: "Claude Code doesn't use RAG currently. In our testing we found that agentic search out-performed RAG for the kinds of things people use Code for."
SRC: https://news.ycombinator.com/item?id=43164253

### Anthropic's official framing is 'just in time' context retrieval + progressive disclosure
"Rather than pre-processing all relevant data up front, agents built with the 'just in time' approach maintain lightweight identifiers (file paths, stored queries, web links, etc.) and use these references to dynamically load data into context at runtime using tools." Claude Code uses "primitives like glob and grep" and Bash head/tail "without ever loading the full data objects into context". CLAUDE.md files by contrast "are naively dropped into context up front". Also defines context rot: as token count rises, recall accuracy falls.
SRC: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

### Anthropic's large-codebase guidance: grep-style traversal + a lightweight hand-written repo index
Claude "traverses the file system, reads files, uses grep to find exactly what it needs, and follows references across the codebase", avoiding stale embedding indices. For non-conventional layouts they recommend "a lightweight markdown file at the repo root listing each top-level folder with a one-line description". Governance: assign a DRI for Claude Code config; review config every three to six months after model releases. Teams have built "MCP servers exposing structured search as a tool Claude can call directly" paired with LSP.
SRC: https://claude.com/blog/how-claude-code-works-in-large-codebases-best-practices-and-where-to-start

### CLAUDE.md load order and hierarchy (exact paths)
Managed policy: macOS /Library/Application Support/ClaudeCode/CLAUDE.md, Linux/WSL /etc/claude-code/CLAUDE.md, Windows C:\Program Files\ClaudeCode\CLAUDE.md. User: ~/.claude/CLAUDE.md. Project: ./CLAUDE.md or ./.claude/CLAUDE.md. Local: ./CLAUDE.local.md. Files in ancestor dirs load in full at launch; files in SUBdirectories load on demand when Claude reads files there. Imports use @path/to/import, max depth of four hops, skipped inside backticks/code fences. Target under 200 lines per file. HTML comments are stripped before injection.
SRC: https://code.claude.com/docs/en/memory

### Claude Code reads CLAUDE.md, not AGENTS.md - bridge with an import or symlink
"Claude Code reads CLAUDE.md, not AGENTS.md." Recommended bridge is a CLAUDE.md containing `@AGENTS.md` plus Claude-specific extras, or `ln -s AGENTS.md CLAUDE.md`. /init also reads .cursor/rules/, .cursorrules, .github/copilot-instructions.md; with CLAUDE_CODE_NEW_INIT=1 it also reads AGENTS.md, .devin/rules/, .windsurf/rules/, .clinerules.
SRC: https://code.claude.com/docs/en/memory

### Path-scoped rules under .claude/rules/ load only when matching files are touched
Markdown files in .claude/rules/ (discovered recursively, symlinks supported). YAML frontmatter `paths:` with globs scopes a rule so it loads only when Claude reads a matching file. Brace expansion budget: 1,000 expanded patterns / 4 MiB per rule. Rules without `paths` load unconditionally at the same priority as .claude/CLAUDE.md.
SRC: https://code.claude.com/docs/en/memory

### Claude Code monorepo settings: claudeMdExcludes, Read deny rules, sparse worktrees, additionalDirectories
claudeMdExcludes takes globs against absolute paths (e.g. "**/packages/web/**"); managed policy CLAUDE.md cannot be excluded. permissions.deny with Read(./**/dist/**) blocks reads of checked-in generated/vendored code (covers built-in file tools and recognized Bash cat/head/grep/find). worktree.sparsePaths + worktree.symlinkDirectories limit what a worktree checks out. permissions.additionalDirectories or --add-dir grants cross-package access; additionalDirectories never loads that dir's CLAUDE.md or skills.
SRC: https://code.claude.com/docs/en/large-codebases

### Claude Code has official LSP 'code intelligence' plugins including Kotlin and Java
Table of plugin -> required binary: Java `jdtls-lsp` -> `jdtls`; Kotlin `kotlin-lsp` -> `kotlin-language-server`; also clangd-lsp, csharp-lsp, gopls-lsp, lua-lsp, php-lsp, pyright-lsp, rust-analyzer-lsp, swift-lsp, typescript-lsp. Install e.g. `/plugin install typescript-lsp@claude-plugins-official`. Gives automatic post-edit diagnostics plus go-to-definition, find references, hover types, list symbols, find implementations, call hierarchies. Docs warn about high memory usage on large projects and false-positive diagnostics in monorepos.
SRC: https://code.claude.com/docs/en/discover-plugins

### AGENTS.md supports nested per-directory files with nearest-wins precedence
"Agents automatically read the nearest file in the directory tree, so the closest one takes precedence and every subproject can ship tailored instructions." OpenAI's main repo contains 88 such files. Format claims use by over 60k open-source projects.
SRC: https://agents.md/

### ast-grep supports Kotlin natively (32 languages built in)
Kotlin aliases `kotlin`, `kt`; extensions kt, ktm, kts. Also Java (java). All listed languages available through CLI and JS/Python bindings.
SRC: https://ast-grep.github.io/reference/languages.html

### ast-grep's Kotlin parser is a repackaged tree-sitter-kotlin
crates/language/Cargo.toml pins `tree-sitter-kotlin = { version = 0.4.1, optional = true, package = "tree-sitter-kotlin-sg" }` - published under a non-standard package name, distinct from the mainline grammar versions used for Java (0.23.0) etc.
SRC: https://raw.githubusercontent.com/ast-grep/ast-grep/main/crates/language/Cargo.toml

### The Kotlin tree-sitter grammar is measurably incomplete
fwcd/tree-sitter-kotlin cross-validation against JetBrains' Kotlin compiler reference parser reports "74/121 (61.2%) structural match among clean parses" - roughly 39% of fixtures do not match the reference AST structure. Known issues tracked in tools/cross-validation/TODO.md.
SRC: https://github.com/fwcd/tree-sitter-kotlin

### ast-grep rule anatomy: id + language + rule, with atomic/relational/composite rule types
Required: id, language, rule. Optional: message, severity, fix, files, ignores, constraints, utils. Atomic rules: pattern, kind, regex. Relational: inside, has, follows, precedes (with stopBy). Composite: all, any, not, matches. A rule has one single root `rule` matching one AST node per instance.
SRC: https://ast-grep.github.io/guide/rule-config.html

### sgconfig.yml is the project root marker and rule discovery config
Required key ruleDirs (paths resolve relative to sgconfig.yml). Optional: testConfigs (testDir required, snapshotDir optional), utilDirs, languageGlobs (map language -> globs, e.g. html: ['*.vue','*.svelte']), customLanguages (libraryPath + extensions, optional outlineRules/expandoChar/languageSymbol), languageInjections (experimental).
SRC: https://ast-grep.github.io/reference/sgconfig.html

### ast-grep CLI surface for agents
`ast-grep run` flags: -p/--pattern, -l/--lang, -r/--rewrite, --json, --debug-query, --stdin, --interactive, --color never. `ast-grep scan` flags: -r/--rule (single rule file), -c/--config, --format github, --json, --stdin, --interactive. Also `ast-grep outline`, `ast-grep test`, `ast-grep new`.
SRC: https://ast-grep.github.io/guide/tooling-overview.html

### ast-grep outline is a token-cheap structural TOC, explicitly LLM-targeted
"Explore code structure for symbols, imports, exports, and members" before opening full source. Flags: --items (auto|structure|exports|imports|all), --type (class, function, struct...), --match REGEX, --pub-members, --lang, --stdin, --globs, --json[=pretty|compact|stream], --view (names|signatures|digest|expanded), --color. The docs page carries an LLM-optimized markdown variant at /reference/cli/outline.md.
SRC: https://ast-grep.github.io/reference/cli/outline.html

### ast-grep meta-variable syntax
$VAR matches one named node (uppercase/underscore/digits only). $$$ or $$$NAME matches zero or more nodes. $_VAR is non-capturing (faster). $$VAR captures unnamed tree-sitter nodes. Reusing the same name enforces structural equality ($A == $A matches a == a but not a == b). Patterns must be valid parseable code.
SRC: https://ast-grep.github.io/guide/pattern-syntax.html

### An official ast-grep MCP server exists but is experimental
Tools: dump_syntax_tree (visualize AST of a snippet), test_match_code_rule (test YAML rules against snippets), find_code (simple pattern search with result limits/output formats), find_code_by_rule (complex YAML rules). Config runs it via `uv --directory /abs/path/to/ast-grep-mcp run main.py`. Repo self-describes as "an experimental Model Context Protocol (MCP) server".
SRC: https://github.com/ast-grep/ast-grep-mcp

### comby offers language-aware structural rewriting with balanced-delimiter holes
Syntax: :[hole] basic capture, :[[id]] identifier match, :[x~regex] regex-constrained hole. Handles nested expressions, comments and strings better than sed/regex. Interactive review mode, stdin support, Docker image, Homebrew/Linux/WSL binaries.
SRC: https://raw.githubusercontent.com/comby-tools/comby/master/README.md

### ripgrep ignore-file precedence and agent-relevant flags
Precedence: .rgignore > .ignore > .gitignore; also honours $GIT_DIR/info/exclude and core.excludesFile. Flags: -t/--type and -T/--type-not (rg --type-list to enumerate; --type-add 'web:*.{html,css,js}' to define), -g/--glob with ! for exclusion (later globs override earlier), --files (list what would be searched without searching), --json, -C/-A/-B context, -U/--multiline, -w/--word-regexp, --no-ignore, --hidden, --max-count, --stats.
SRC: https://raw.githubusercontent.com/BurntSushi/ripgrep/master/GUIDE.md

### fd flags worth putting in an agent's allowlist
-e/--extension, -t/--type (f|d|l|x|e|s|p|c|b), -g/--glob, -H/--hidden, -I/--no-ignore, -E exclude, -0/--print0, -x/--exec (parallel, per result), -X/--exec-batch (once with all results), --max-depth, -p/--full-path, --changed-within 1d.
SRC: https://raw.githubusercontent.com/sharkdp/fd/master/README.md

### Serena is an LSP-backed MCP server exposing symbol-level tools across 40+ languages incl. Kotlin/Java
Retrieval tools: find_symbol, symbol_overview (file outline), find_referencing_symbols, find_declaration, find_implementations, query_external_projects, diagnostics/inspections, type_hierarchy (JetBrains backend only), search_in_project_dependencies (JetBrains only). Refactoring: rename, move, inline, propagate_deletions. Symbolic editing: replace_symbol_body, insert_after_symbol, insert_before_symbol, safe_delete. Utilities: search_for_pattern, replace_content, list_dir/find_file, read_file, execute_shell_command. Install `uv tool install -p 3.13 serena-agent` then `serena init` (or `serena init -b JetBrains`). Explicit warning: "Do not install Serena via an MCP or plugin marketplace!"
SRC: https://raw.githubusercontent.com/oraios/serena/main/README.md

### Serena per-project config keys (.serena/project.yml)
project_name, language_backend (LSP or JetBrains), language_servers, encoding, line_ending (lf|crlf|native), ignore_all_files_in_gitignore, activation_command + activation_command_timeout (default 180s), ls_workspace_folders, ls_additional_workspace_folders, ls_specific_settings, ignored_paths (gitignore syntax), read_only, excluded_tools, included_optional_tools, fixed_tools, default_modes, added_modes, initial_prompt, symbol_info_budget, read_only_memory_patterns, ignored_memory_patterns.
SRC: https://raw.githubusercontent.com/oraios/serena/main/src/serena/resources/project.template.yml

### SCIP is Sourcegraph's LSIF successor; scip-java covers Java, Scala and Kotlin
"SCIP ... is a language-agnostic protocol for indexing source code, which can be used to power code navigation functionality such as Go to definition, Find references, and Find implementations." Indexers: scip-java (Java, Scala, Kotlin), scip-typescript, rust-analyzer, scip-clang, scip-ruby, scip-python, scip-dotnet, scip-dart, scip-php, debian-lsp.
SRC: https://github.com/sourcegraph/scip

### scip-java does NOT support Android, and Kotlin support is less mature
"Android integration is not yet supported" (tracking issue filed). "Kotlin support in scip-java is less mature compared to the Java support"; works with Gradle but not Maven. Supported JVMs: 17, 21, 25 (not 7/8/11). Default Gradle build command is `clean compileTestJava compileTestKotlin compileTestKotlinJvm`. Java 17+ needs five --add-exports jdk.compiler/... flags.
SRC: https://raw.githubusercontent.com/sourcegraph/scip-java/main/docs/getting-started.md

### scip-kotlin (semanticdb-kotlinc) is archived and pinned to old Kotlin versions
Repository archived: "This repository has been merged into scip-java and is no longer relevant." Version map: Kotlin 1.8.x -> scip-kotlin 0.3.2; Kotlin 1.9.x -> scip-kotlin 0.4.0. Invocation is a raw compiler plugin: -Xplugin=${SEMANTICDB_KOTLIN_JAR} -P plugin:semanticdb-kotlinc:sourceroot=... -P plugin:semanticdb-kotlinc:targetroot=...
SRC: https://github.com/sourcegraph/scip-kotlin

### Sourcegraph's 2026 position: deterministic SCIP over MCP, not approximate retrieval
"Approximate retrieval is fine on a small repo. On Big Code, it returns plausible-looking results that miss cross-cutting impact." Stack: MCP server exposing SCIP-powered code intelligence, Deep Search (NL search with citations), Code Search ("the deterministic, exact, exhaustive engine underneath everything"), Code Insights, Agentic Migrations. Core thesis: "Agentic coding's productivity ceiling is set by context, not model quality." Cites an 80% problem: agents complete visible work but miss the 20% outside the context window.
SRC: https://sourcegraph.com/blog/agentic-coding

### Cline's published anti-indexing argument (three claims)
(1) "When you chunk code for embeddings, you're literally tearing apart its logic." (2) "An index, by definition, is a snapshot frozen in time. The code inevitably drifts out of sync." (3) embeddings create "a secondary representation of your most valuable IP that needs to be stored somewhere", doubling the security surface. Instead: "Cline reads code the way you do - file by file, connection by connection."
SRC: https://cline.bot/blog/why-cline-doesnt-index-your-codebase-and-why-thats-a-good-thing

### Peer-reviewed counterpoint: keyword search reaches >90% of RAG performance
arXiv 2602.23368, "Keyword search is all you need: Achieving RAG-Level Performance without vector databases using agentic tool use" (Subramanian et al., AAAI 2026): "tool-based keyword search implementations within an agentic framework can attain over 90% of the performance metrics compared to traditional RAG systems"; substantial capability without a standing vector database; called out as especially suited to frequently updated knowledge bases.
SRC: https://arxiv.org/abs/2602.23368

### Cursor's measured case FOR semantic search
On Cursor Context Bench: semantic search gives "on average 12.5% higher accuracy in answering questions (6.5%-23.5% depending on the model)". A/B: without semantic search code retention dropped 0.3% overall and 2.6% in codebases with 1,000+ files; user dissatisfaction rose 2.2%. Their embedding model is trained on agent session traces ranked by an LLM, not generic similarity.
SRC: https://cursor.com/blog/semsearch

### How Cursor's index actually works (Merkle tree + Turbopuffer)
"Cursor builds its first view of a codebase using a Merkle tree, which lets it detect exactly which files and directories have changed without reprocessing everything." Changed files are split into syntactic chunks, embedded, cached by chunk content hash. A simhash summary of the tree enables index reuse across team members. Access control: "If the client can't prove it has a file, the result is dropped."
SRC: https://cursor.com/blog/secure-codebase-indexing

### The three-modality framing (lexical / structural / graph)
Lexical: "Where does this text appear?" (grep, ripgrep, Zoekt, BM25). Structural: "Where does this code shape appear?" (ast-grep, tree-sitter queries) - "ignores whitespace and formatting, respects nesting, and - critically - never matches inside comments or string literals." Graph: "Who actually calls or uses this?" (LSP, code property graphs). "Each modality knows more about code than the one above it and works on fewer things." Author's Gortex benchmarks vs ripgrep: BM25 R@5 55.1% vs 17.3%; 3-50x fewer tokens per response; 96.8% R@5 on exact symbol queries.
SRC: https://zzet.org/gortex/grep-replacement-for-ai-agents/

### The nuanced middle position: keyword generation closes most of grep's gap
Using an LLM to generate keywords improved grep retrieval by roughly 10x on the author's tests. Quote: "If it's not readily apparent what the name of a variable or a particular stage of your pipeline is, but you can reference some oblique aspect of it, embeddings will get you a lot closer than grep will." Also notes grep latency scales linearly with index size vs numpy vector search.
SRC: https://www.nuss-and-bolts.com/p/on-the-lost-nuance-of-grep-vs-semantic

### claude-context (Zilliz) is the mainstream vector-index MCP for Claude Code
MCP tools: index_codebase (hybrid BM25 + dense vector), search_code (NL query, hybrid), clear_index. Run with `npx @zilliz/claude-context-mcp@latest`. Env: OPENAI_API_KEY, MILVUS_ADDRESS, MILVUS_TOKEN. AST-based chunking; Merkle-tree incremental re-index. Languages include Kotlin. Claims "~40% token reduction" with "equivalent retrieval quality".
SRC: https://github.com/zilliztech/claude-context

### aider's repo map = tree-sitter tags + graph ranking, default 1k tokens
Uses py-tree-sitter-languages and "modified versions of the tags.scm files from these open source tree-sitter language implementations". Ranking: "a graph ranking algorithm, computed on a graph where each source file is a node and edges connect files which have dependencies". Budget via --map-tokens, "which defaults to 1k tokens"; expands dynamically when no files are in the chat. Replaced universal-ctags, giving "full function call signatures". Note: the design post is from 2023-10-22 and is the oldest source here.
SRC: https://aider.chat/2023/10/22/repomap.html

### repomix packs a repo into one AI-friendly file with tree-sitter compression
Flags: --style xml|markdown|json, --compress, --include, --ignore, --remote user/repo, --remote-branch, --token-count-tree [minChars], --token-budget, --stdout, --split-output 1mb, --mcp, --mcp --sandbox path. Tokenizers o200k_base and cl100k_base. Compression "can achieve ~70% token reduction while preserving semantic meaning" by keeping signatures/interfaces/class structure and dropping bodies.
SRC: https://raw.githubusercontent.com/yamadashy/repomix/main/README.md

### repomix --compress has NO Kotlin support
src/core/treeSitter/queries contains queryC, queryCSharp, queryCpp, queryCss, queryDart, queryGo, queryJava, queryJavascript, queryPhp, queryPython, queryRuby, queryRust, querySolidity, querySwift, queryTypescript, queryVue. No Kotlin query file - Kotlin files will not be structurally compressed.
SRC: https://github.com/yamadashy/repomix/tree/main/src/core/treeSitter/queries

### gitingest converts a repo to prompt-friendly text with token stats
CLI: --output/-o <file> (`-o -` for stdout), --token/-t (GitHub PAT), --include-gitignored, --include-submodules. Python: `from gitingest import ingest; summary, tree, content = ingest("path")`, plus ingest_async(). Output = summary + directory tree + file contents; token count estimated via tiktoken.
SRC: https://raw.githubusercontent.com/cyclotruc/gitingest/main/README.md

### code2prompt adds Handlebars templating, git diffs and an MCP server
Flags: --include, --exclude, --output-file, --tokens, --encoding, --template, --diff, --git-diff-branch, --line-numbers. Respects .gitignore. Ships a CLI, TUI, Python SDK, Rust core library and an MCP server for agentic use.
SRC: https://raw.githubusercontent.com/mufeedvh/code2prompt/main/README.md

### dev.iurysouza.modulegraph generates a Mermaid module graph into README.md
Plugin id `dev.iurysouza.modulegraph` version 0.13.0 (Oct 2025). Task `./gradlew createModuleGraph`. It appends/updates the graph in the README, which renders natively on GitHub, GitLab, JetBrains IDEs and VS Code.
SRC: https://github.com/iurysza/module-graph/blob/main/README.md

### com.jraska.module.graph.assertion enforces module-graph architecture rules in CI
Plugin id `com.jraska.module.graph.assertion` version 2.9.1. Tasks: assertModuleGraph, generateModulesGraphvizText, generateModulesGraphStatistics. DSL: maxHeight, allowed ([':feature.* -> :lib.*']), restricted ([':feature-[a-z]* -X> :forbidden']), configurations (default ['api','implementation']), assertOnAnyBuild.
SRC: https://github.com/jraska/modules-graph-assert

### io.github.adityabhaskar.dependencygraph emits per-module Mermaid graphs
Plugin id `io.github.adityabhaskar.dependencygraph`, task `dependencyGraph`. Config: graphDirection, showLegend, ignoreModules (List<String>), repoRootUrl, mainBranchName, graphFileName, shouldLinkModuleText. Renders direct dependents and direct+indirect dependencies, colouring Java / Android / multiplatform modules differently. Derived from Jake Wharton's script.
SRC: https://github.com/adityabhaskar/Gradle-dependency-graphs

### Gradle's built-in reporting tasks are the zero-dependency module map
`projects` "gives you a list of the subprojects of the selected project, displayed in a hierarchy". `dependencies` prints dependencies by configuration as a tree. `dependencyInsight --dependency X --configuration Y` explains a single dependency. `buildEnvironment` shows buildscript deps. `properties [--property name]`. `tasks --all --group X --provenance`. `--scan` produces a full visual dependency report.
SRC: https://docs.gradle.org/current/userguide/command_line_interface.html

### dependency-analysis-gradle-plugin finds unused/misdeclared deps across an Android build
Plugin ids `com.autonomousapps.dependency-analysis` and `com.autonomousapps.build-health`. Tasks: buildHealth (whole build), projectHealth (per module, e.g. `./gradlew app:projectHealth`), reason, fixDependencies. Detects unused deps, used-transitive deps that should be declared, wrong configuration (api vs implementation vs compileOnly), unused annotation processors, unnecessary plugins, duplicate classes. Supports com.android.application/library/test and org.jetbrains.kotlin.android.
SRC: https://github.com/autonomousapps/dependency-analysis-gradle-plugin

### Now in Android is the canonical Android module-map reference layout
Module types: app (MainActivity, NiaApp, NiaNavHost), feature:*:api (nav keys only, e.g. TopicNavKey), feature:*:impl (TopicScreen, TopicViewModel), core:* (data/designsystem/ui/network/database/model), plus sync, benchmark, test, app-nia-catalog. Rule: features depend only on core modules and other features' api modules; core modules never depend on feature or app modules.
SRC: https://github.com/android/nowinandroid/blob/main/docs/ModularizationLearningJourney.md

### MADR 4.0.0 is the current ADR template standard
Released 2024-09-17 with full, 'bare' and 'minimal' templates. Sections: YAML front matter (status, date, decision-makers, consulted, informed), Context and Problem Statement, Decision Drivers, Considered Options, Decision Outcome, Consequences, Confirmation, Pros and Cons of the Options, More Information. Filenames follow `NNNN-title-with-dashes.md`; stored in docs/decisions/.
SRC: https://adr.github.io/madr/

### C4 model gives four hierarchical abstractions for architecture docs
Software System (highest), Container, Component, Code (lowest). Presented as "a set of hierarchical abstractions" - useful as the vocabulary layer above a generated module graph.
SRC: https://c4model.com/

### fiberplane/drift binds markdown docs to AST symbols and fails CI when they drift
Bindings in drift.lock (TOML): doc = "docs/auth.md", target = "src/auth/provider.ts#AuthConfig", sig = "1a2b3c4d5e6f7890". Inline reference form: @./src/auth/provider.ts#AuthConfig. Commands: drift check (exit 1 if stale), drift link, drift status, drift unlink, drift refs, drift lint. Signature = XxHash3 of normalized AST (node kinds + tokens, no whitespace/position), so reformatting is transparent and no VCS history is needed. CI: `drift check --changed src/auth`. Tree-sitter languages: TypeScript, Python, Rust, Go, Zig, Java (others fall back to raw content compare).
SRC: https://github.com/fiberplane/drift

### JetBrains' official Kotlin Language Server is Alpha; AGP support is experimental
"JetBrains' official implementation of the Language Protocol (LSP) for Kotlin ... based on IntelliJ IDEA, the IntelliJ IDEA Kotlin plugin, JetBrains AIR, and Fleet." Build systems: Gradle (full), Maven (full), Android Gradle Plugin (experimental). Kotlin Multiplatform support still under development. Promoted to Alpha at KotlinConf 2026.
SRC: https://kotlinlang.org/docs/kotlin-lsp.html

### The vector-index counterargument in numbers
Milvus's rebuttal to grep-only retrieval claims "Token usage dropped by over 40%, without any loss in recall" after adding semantic search, and that grep "dumps massive blobs of code into the model, driving up token costs" while indexed chunks "reduce token load by 30-40%". Anecdote: a debugging scenario that took Claude Code five minutes of grepping was resolved to an exact file+line immediately with the index. Treat as vendor-authored.
SRC: https://milvus.io/blog/why-im-against-claude-codes-grep-only-retrieval-it-just-burns-too-many-tokens.md

## EXAMPLES
### ast-grep project layout for a Kotlin/Android repo (root marker + rules + tests)
FILE: sgconfig.yml at repo root; rules under a ruleDirs entry
```
repo-root/
  sgconfig.yml
  ast-grep/
    rules/
      no-raw-color.yml
      no-new-gson.yml
    rule-tests/
      no-new-gson/
        input.kt
    utils/

# sgconfig.yml
ruleDirs:
  - ast-grep/rules
utilDirs:
  - ast-grep/utils
testConfigs:
  - testDir: ast-grep/rule-tests
```
SRC: https://ast-grep.github.io/reference/sgconfig.html

### Full ast-grep lint rule with every documented field
FILE: <ruleDirs>/<id>.yml
```
id: no-await-in-loop
language: TypeScript
severity: warning
message: Don't use await inside of loops
note: |
  Performing an await as part of each operation is an indication that
  the program is not taking full advantage of the parallelization
  benefits of async/await.
files:
  - "src/**"
ignores:
  - "tests/**"
rule:
  pattern: await $_
  inside:
    any:
      - kind: for_in_statement
      - kind: while_statement
constraints:
  $_:
    kind: identifier
transform:
  AWAIT_EXPR: |
    Promise.all([$AWAIT_EXPR])
fix: await Promise.all([$AWAIT_EXPR])
labels:
  AWAIT_EXPR:
    style: primary
    message: "await expression in loop"
```
SRC: https://ast-grep.github.io/guide/project/lint-rule.html

### ast-grep relational rule (the canonical composable example)
FILE: rules/*.yml
```
id: no-await-in-promise-all
language: TypeScript
rule:
  pattern: Promise.all($A)
  has:
    pattern: await $_
    stopBy: end
```
SRC: https://ast-grep.github.io/guide/rule-config.html

### ast-grep ad-hoc structural queries (adapt -l kotlin for Android)
FILE: -
```
# search
ast-grep run -p 'Some($A)' -r 'None' --json
ast-grep run -p 'YOUR_PATTERN' --debug-query
# scan with rules
ast-grep scan -r path/to/your/rule.yml
ast-grep scan --interactive
# structural table-of-contents instead of reading whole files
ast-grep outline src/parser.ts
ast-grep outline src --items exports
```
SRC: https://ast-grep.github.io/guide/tooling-overview.html

### ast-grep MCP server registration
FILE: .mcp.json / claude_desktop_config.json
```
{
  "mcpServers": {
    "ast-grep": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/ast-grep-mcp", "run", "main.py"],
      "env": {}
    }
  }
}
```
SRC: https://github.com/ast-grep/ast-grep-mcp

### Serena MCP wired into Claude Code, with pre-warm index
FILE: .serena/project.yml (per project); .serena/ is machine-local cache, gitignore it
```
# pre-build the symbol index so the first find_symbol isn't cold
uvx --from git+https://github.com/oraios/serena serena project index --verbose

# register with Claude Code from the repo root
claude mcp add serena -- uvx --from git+https://github.com/oraios/serena \
  serena start-mcp-server --context ide-assistant --project $(pwd)
```
SRC: https://raw.githubusercontent.com/oraios/serena/main/README.md

### Claude Code code-intelligence (LSP) plugin for Kotlin
FILE: -
```
/plugin marketplace add anthropics/claude-plugins-official
/plugin install kotlin-lsp@claude-plugins-official
# requires the `kotlin-language-server` binary on PATH
# Java equivalent: /plugin install jdtls-lsp@claude-plugins-official  (binary: jdtls)
```
SRC: https://code.claude.com/docs/en/discover-plugins

### Per-module CLAUDE.md layering for an Android multi-module repo
FILE: CLAUDE.md per module dir; .claude/rules/*.md at root
```
repo-root/
  CLAUDE.md                       # repo-wide: layout, build commands, red lines
  .claude/settings.json           # deny rules for worktree sessions
  .claude/rules/
    compose.md                    # paths: ["**/*.kt"] scoped rules
    data-layer.md
  app/CLAUDE.md
  domain/usecase/CLAUDE.md
  data/repository/CLAUDE.md
  data/repository/.claude/skills/repo-testing/SKILL.md
  libs/designsystem/CLAUDE.md
```
SRC: https://code.claude.com/docs/en/large-codebases

### Path-scoped rule so Compose conventions only load when Compose files are read
FILE: .claude/rules/compose.md
```
---
paths:
  - "**/*.kt"
  - "libs/designsystem/**/*"
---

# Compose conventions
- Spacing/radius/type/color must come from StyleDictionary tokens
- No new XML layouts; new screens are Compose only
```
SRC: https://code.claude.com/docs/en/memory

### Stop Claude reading Android generated/build output
FILE: .claude/settings.json (repo root, committed)
```
{
  "permissions": {
    "deny": [
      "Read(./**/build/**)",
      "Read(./**/generated/**)",
      "Read(./**/*.generated.*)",
      "Read(./**/kapt/**)",
      "Read(./**/ksp/**)"
    ]
  }
}
```
SRC: https://code.claude.com/docs/en/large-codebases

### Exclude other teams' CLAUDE.md in a big monorepo
FILE: .claude/settings.local.json
```
{
  "claudeMdExcludes": [
    "**/packages/web/**",
    "**/packages/legacy-*/**",
    "/home/user/monorepo/other-team/.claude/rules/**"
  ]
}
```
SRC: https://code.claude.com/docs/en/large-codebases

### Sparse worktrees so subagents check out only the modules they need
FILE: .claude/settings.json
```
{
  "worktree": {
    "sparsePaths": [
      ".claude",
      "app",
      "domain/usecase",
      "data/repository"
    ],
    "symlinkDirectories": ["node_modules"]
  }
}
```
SRC: https://code.claude.com/docs/en/large-codebases

### CLAUDE.md that reuses an existing AGENTS.md instead of duplicating
FILE: CLAUDE.md at repo root
```
@AGENTS.md

## Claude Code

Use plan mode for changes under `shared/payment/`.

# or, if no Claude-specific content is needed:
#   ln -s AGENTS.md CLAUDE.md
```
SRC: https://code.claude.com/docs/en/memory

### Generate + commit a Mermaid module graph for an Android multi-module build
FILE: root build.gradle.kts; output written into the markdown file at readmePath
```
// root build.gradle.kts
plugins { id("dev.iurysouza.modulegraph") version "0.13.0" }

moduleGraphConfig {
    readmePath.set("./docs/ai-guide/module-graph.md")
    heading.set("### Module Graph")
    showFullPath.set(false)
    orientation.set(Orientation.LEFT_TO_RIGHT)
    linkText.set(LinkText.NONE)
    excludedConfigurationsRegex.set(".*test.*")
    excludedModulesRegex.set(".*moduleName.*")
    focusedModulesRegex.set(".*(projectName).*")
    rootModulesRegex.set(".*moduleName.*")
    setStyleByModuleType.set(true)
    strictMode.set(false)
    nestingEnabled.set(true)
    theme.set(Theme.NEUTRAL)
}

// $ ./gradlew createModuleGraph
```
SRC: https://github.com/iurysza/module-graph/blob/main/README.md

### Mermaid output shape the plugin produces
FILE: -
```
graph LR
    subgraph app
        main
        playground
    end
    subgraph core
        common
        design-system
    end
    match-day --> common
    match-day --> design-system
    playground --> match-day
    main --> match-day
```
SRC: https://github.com/iurysza/module-graph/blob/main/README.md

### Enforce the module graph so the generated map stays true
FILE: root build.gradle / build.gradle.kts
```
// root build.gradle
plugins { id "com.jraska.module.graph.assertion" version "2.9.1" }

moduleGraphAssert {
  maxHeight = 4
  allowed = [':feature.* -> :lib.*', ':.* -> :core']
  restricted = [':feature-[a-z]* -X> :forbidden-to-depend-on']
  configurations = ['api', 'implementation']
}

// $ ./gradlew assertModuleGraph
// $ ./gradlew generateModulesGraphvizText
```
SRC: https://github.com/jraska/modules-graph-assert

### Zero-plugin module map from Gradle itself (cheapest possible index)
FILE: commit outputs under docs/ai-guide/ so agents grep them instead of running Gradle
```
./gradlew projects > docs/ai-guide/modules.txt
./gradlew :app:dependencies --configuration developDebugRuntimeClasspath > docs/ai-guide/app-deps.txt
./gradlew :app:dependencyInsight --dependency okio --configuration developDebugRuntimeClasspath
./gradlew buildEnvironment
./gradlew tasks --all --provenance
```
SRC: https://docs.gradle.org/current/userguide/command_line_interface.html

### Dependency hygiene report the agent can read instead of guessing
FILE: -
```
./gradlew buildHealth
# -> build/reports/dependency-analysis/build-health-report.txt
./gradlew app:projectHealth
./gradlew lib:reason --id com.squareup.okio:okio:2.2.2
```
SRC: https://github.com/autonomousapps/dependency-analysis-gradle-plugin

### ripgrep patterns worth putting in an allowlist for agents
FILE: -
```
rg --files                                  # what would be searched
rg --type-list                              # available -t types
rg -t kotlin -w 'fun loginUser'             # word-boundary symbol hunt
rg -g '!**/build/**' -g '*.kt' 'StyleDictionary'
rg --json -C 3 'ApiResult<'                 # machine-readable with context
rg -U 'class \w+ViewModel[\s\S]{0,200}StateFlow'   # multiline
rg -l 'Reductor'                            # files-with-matches only (cheap)
rg --stats 'Dispatchers.IO'
# ignore precedence: .rgignore > .ignore > .gitignore (+ $GIT_DIR/info/exclude)
```
SRC: https://raw.githubusercontent.com/BurntSushi/ripgrep/master/GUIDE.md

### fd patterns for locating modules/files fast
FILE: -
```
fd -e kt -t f ViewModel app/
fd -g 'build.gradle*' --max-depth 3
fd -t d -g 'src' --max-depth 3
fd --changed-within 1d -e kt
fd -0 -e kt | xargs -0 wc -l
fd -e kt -X rg -l 'Reductor'
```
SRC: https://raw.githubusercontent.com/sharkdp/fd/master/README.md

### Pack a subset of a big Android repo for one-shot LLM context
FILE: repomix.config.json at repo root; NOTE --compress does not cover Kotlin
```
npx repomix@latest --style markdown --compress \
  --include "domain/**/*.kt,data/repository/**/*.kt,**/*.md" \
  --ignore "**/build/**,**/test/**" \
  --token-count-tree 1000 \
  -o /tmp/repo-pack.md

# repomix.config.json
{
  "output": { "filePath": "repomix-output.xml", "style": "xml", "compress": false, "removeComments": false },
  "include": ["**/*"],
  "ignore": { "useGitignore": true, "customPatterns": ["**/build/**"] }
}

# as an MCP server
repomix --mcp --sandbox path/to/project
```
SRC: https://raw.githubusercontent.com/yamadashy/repomix/main/README.md

### Bind an architecture doc to code so CI catches drift
FILE: drift.lock at repo root; anchors inside docs/*.md
```
# drift.lock (repo root)
[[bindings]]
doc = "docs/ai-guide/features/checkout.md"
target = "data/repository/src/main/java/.../CheckoutRepository.kt#CheckoutRepository"
sig = "1a2b3c4d5e6f7890"

# inline anchor inside the markdown
@./data/repository/src/.../CheckoutRepository.kt#CheckoutRepository

# CI
- run: drift check --changed data/repository
```
SRC: https://github.com/fiberplane/drift

### MADR ADR file naming and location
FILE: docs/decisions/NNNN-title-with-dashes.md
```
docs/decisions/0001-use-koin-not-hilt.md
docs/decisions/0002-mvvm-udf-retire-reductor.md
# front matter: status, date, decision-makers, consulted, informed
# sections: Context and Problem Statement / Decision Drivers / Considered Options /
#           Decision Outcome / Consequences / Confirmation / Pros and Cons / More Information
```
SRC: https://adr.github.io/madr/

### SCIP index for a JVM project (does NOT cover Android)
FILE: -
```
docker run -v $(pwd):/sources --env JVM_VERSION=17 \
  ghcr.io/scip-code/scip-java:latest scip-java index

# default gradle build command used:
#   clean compileTestJava compileTestKotlin compileTestKotlinJvm
# Java 17+ needs: --add-exports jdk.compiler/com.sun.tools.javac.{model,api,tree,util,code}=ALL-UNNAMED
```
SRC: https://raw.githubusercontent.com/sourcegraph/scip-java/main/docs/getting-started.md

### Vector-index MCP if you decide you want semantic search anyway
FILE: .mcp.json
```
{
  "mcpServers": {
    "claude-context": {
      "command": "npx",
      "args": ["@zilliz/claude-context-mcp@latest"],
      "env": {
        "OPENAI_API_KEY": "...",
        "MILVUS_ADDRESS": "...",
        "MILVUS_TOKEN": "..."
      }
    }
  }
}
# tools: index_codebase (BM25 + dense hybrid), search_code, clear_index
```
SRC: https://github.com/zilliztech/claude-context

## GOTCHAS
- Kotlin structural tooling is the weak link. ast-grep's Kotlin parser is `tree-sitter-kotlin-sg` 0.4.1; the upstream fwcd/tree-sitter-kotlin reports only 74/121 (61.2%) structural match against JetBrains' reference parser. Expect ast-grep Kotlin patterns to silently miss constructs (context receivers, complex generics, some DSL/trailing-lambda forms). Always validate a rule with `ast-grep run -p ... --debug-query` on real files before trusting a zero-result answer.
- scip-java says outright "Android integration is not yet supported", and "Kotlin support in scip-java is less mature compared to the Java support" (Gradle only, no Maven). scip-kotlin/semanticdb-kotlinc is ARCHIVED and its last release (0.4.0) targets Kotlin 1.9.x. A SCIP/LSIF index is effectively not an option for a modern AGP + Kotlin 2.x Android app.
- repomix `--compress` has no Kotlin tree-sitter query file, so the headline ~70% token reduction does not apply to a Kotlin codebase - Kotlin files get packed uncompressed. Same class of gap applies to fiberplane/drift (TS/Python/Rust/Go/Zig/Java only; Kotlin falls back to raw content compare, so any reformat marks docs stale).
- JetBrains' official Kotlin LSP is only Alpha and lists Android Gradle Plugin support as *experimental*; KMP support is still under development. The community `kotlin-language-server` binary that Claude Code's `kotlin-lsp` plugin expects is a different, older project. Budget time for it to fail or be slow on a 50+ module build.
- LSP/language servers are memory hogs on large projects - Anthropic's own docs warn about "high memory usage" and "false positive diagnostics in monorepos" (unresolved imports for internal packages). On an Android build with KAPT/KSP generated sources this is common and noisy.
- Index staleness is the core structural objection to embeddings: "An index, by definition, is a snapshot frozen in time." Any generated artifact you commit (module graph, feature->file map, packed context) has the same problem. Regenerate in CI or via a hook, and treat a stale map as worse than no map because the agent will trust it.
- Token cost cuts both ways. Grep-only retrieval is criticised for dumping "massive blobs of code into the model" (Milvus claims 30-40% more tokens than chunked retrieval); but embeddings add an index build, an API key, an egress path for your source, and a second copy of your IP. Cline's third argument is exactly this: embeddings "double the security surface".
- CLAUDE.md itself is a token cost - loaded in full every session, before compaction. Anthropic recommends under 200 lines per file and warns "Longer files consume more context and reduce adherence". @path imports do NOT reduce context (they expand at launch); only path-scoped `.claude/rules/` and skills defer.
- Nested CLAUDE.md files and path-scoped rules are NOT re-injected after /compact - only the project-root CLAUDE.md is. Long cross-module sessions silently lose module-local conventions. Mitigation: write the plan to a file in the repo before editing.
- In a monorepo started from the root, EVERY subdirectory's CLAUDE.md loads as soon as Claude reads a file there, and per-directory skills "can accumulate into the hundreds" - skill descriptions get truncated when there are many, stripping the keywords used for selection. Start Claude from the module directory, or use claudeMdExcludes.
- `permissions.deny` Read rules "do not filter denied paths out of a recursive search's output, and they do not cover arbitrary subprocesses that open files themselves" - so denying Read(./**/build/**) does not stop a `rg` invocation from spraying build output into context. Pair with .gitignore/.ignore and explicit -g '!**/build/**' globs.
- Gradle-based index generation (createModuleGraph, dependencies, buildHealth) costs a configuration phase on every run - on a large Android build that is tens of seconds to minutes. Do not wire it to a PreToolUse/SessionStart hook; run it in CI or on a pre-commit/nightly cadence and commit the output.
- `ast-grep run -p` requires the pattern to be valid, parseable code in the target language. Kotlin patterns with trailing lambdas, named args or annotations frequently fail to parse into the intended node and match nothing - a silent false negative, the exact failure mode grep does not have (grep "fails loudly").
- Structural search never matches inside comments or string literals - usually a feature, but it means ast-grep will not find a symbol referenced only in a string (reflection, DI qualifiers, Retrofit paths, resource names). Keep ripgrep for that class of question.
- Evidence on embeddings is genuinely mixed and vendor-inflected. Cline (agent vendor) and Milvus (vector DB vendor) both have skin in the game; Cursor's +12.5% figure comes from Cursor's own internal benchmark. The strongest neutral datapoint is arXiv 2602.23368 (AAAI 2026) at >90% of RAG performance without a vector DB - i.e. embeddings buy the last <10%, at real operational cost.
- aider's repo map design post is from 2023-10-22 - the oldest source here. The tree-sitter + graph-ranking idea holds up, but the 1k default map-token budget was sized for 8k-32k context models and is not a 2026 recommendation.
- ast-grep's MCP server is self-described as experimental; Serena's README explicitly warns "Do not install Serena via an MCP or plugin marketplace!" Both add per-turn tool-definition token cost to every request, which is a fixed tax whether or not the agent uses them.
- Generated docs (module graph, feature->file map) belong in a path the agent can grep but that does NOT auto-load into context. Putting a 200-module Mermaid graph into README.md or root CLAUDE.md is a large, permanent context tax.

## OPEN
- Which Kotlin language server does Claude Code's `kotlin-lsp` plugin actually launch - the community fwcd/kotlin-language-server binary or JetBrains' new official one? The docs only name the binary `kotlin-language-server`; behaviour on a 50+ module AGP project is unverified.
- Serena's exact Kotlin backend: the README claims 40+ languages including Kotlin, but which LSP it drives for Kotlin (fwcd vs JetBrains vs JetBrains-plugin backend) and whether it handles Gradle-variant source sets was not verifiable from the sources fetched.
- Whether `serena project index` produces a persistent on-disk symbol index for Kotlin or just warms the language server - the .serena/project.yml template exposes ls_workspace_folders and symbol_info_budget but no documented index artifact format.
- Real measured token/latency numbers for `ast-grep outline` vs Read on Kotlin files - the feature is documented as LLM-targeted but no published benchmark was found.
- Whether any maintained tool produces an Android *feature -> file* map automatically (as opposed to module -> module). All the Gradle plugins found operate at module granularity; feature-to-file maps appear to be hand-maintained or LLM-generated in every example encountered.
- Cursor's index sync interval and server-side retention were not stated in their secure-indexing post; only the Merkle/simhash/content-proof mechanism is described.
- Whether Zoekt (trigram-indexed lexical search) is being packaged as an MCP tool for local repos in 2026 - it was named as a lexical option but no maintained local-repo MCP wrapper was verified.
- Whether Claude Code's `--compress`-equivalent or Explore subagent has documented token accounting; a docs page at /docs/en/explore-subagent does not exist, so the sub-agent search path is described only in secondary sources.

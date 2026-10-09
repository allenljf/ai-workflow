# Operational substrate for parallel AI coding agents + closed verification loops on a large multi-module Kotlin/Android Gradle project (worktrees × Gradle, failure classification, sandboxing, headless verification, recommended topology)

## SUMMARY
Sharing one GRADLE_USER_HOME across concurrent worktree builds is *supported by design* — Gradle's dependency cache "uses file-based locking to ensure that it can safely be used by multiple Gradle processes concurrently" — but only "if the different Gradle processes can communicate together", which holds on one host and fails across containers. The practical failure mode is contention, not corruption: gradle/gradle#20055 shows `Timeout waiting to lock Java compile cache … It is currently in use by another Gradle instance`. The widely-quoted "unnecessarily expensive and can be unsafe" line is dotnet/android#12149 (Jul 2026) and is about *their own toolchain provisioning*, not Gradle's caches. Correct split: share `~/.gradle` (dependency cache + local build cache), isolate per worktree what is inherently per-directory (`<project>/.gradle`, `build/`), and expect **one daemon per distinct JVM-args/JAVA_HOME fingerprint**, not per worktree — so N worktrees with identical `gradle.properties` reuse one daemon and serialise. Remote build cache is the real fix for cold worktrees: zenn.dev/solenoid (2026-01-26) measured 4 parallel worktree `assembleDebug` at **786s → 109s (7.2x)** and single `testDebugUnitTest` **433.6s → 19.2s** using a Dockerised `gradle/build-cache-node` on :5071. Critically, `--offline` and remote cache are mutually exclusive: Gradle 9.4.1 emits `Remote build cache is disabled when running with --offline.` (verified in gradle-core-9.4.1.jar). Configuration cache is **not** relocatable ("entries … contain many absolute file paths"), so it never transfers between worktrees, and Spotless/JGit still invalidates it via `.git/HEAD` on Gradle 7.x+. For failure classification, Gradle ships exact, greppable strings: `No cached version of %s available for offline mode.`, `Gradle build daemon disappeared unexpectedly (…)`, `Expiring Daemon because JVM heap space is exhausted` — plus `rnett/gradle-mcp`'s `query_build(kind=FAILURES|PROBLEMS|TESTS|TASKS|CONSOLE|DASHBOARD)` already returns typed, auto-expanding failure objects. Sandboxing is now first-class (Seatbelt/bubblewrap, `allowedDomains`, `strictAllowlist`), but `docker` is documented-incompatible and JVM toolchains need Maven Central/dl.google.com punched through. Headless verification tiers: Robolectric offline (seconds), GMD with `swiftshader_indirect` (minutes), emulator+KVM (3–10 min boot). Real bottleneck at ~2–3 concurrent Gradle builds per machine (Block: 192.6s vs 32.6s when serialised).

## KEY FACTS
### Gradle's dependency cache is explicitly designed for concurrent multi-process access via file locking, but only when processes can communicate
Verbatim: "The Gradle dependency cache uses file-based locking to ensure that it can safely be used by multiple Gradle processes concurrently." and "This concurrent access is only supported if the different Gradle processes can communicate together. This is usually not the case for containerized builds." The lock "is held whenever the binary meta-data store is being read or written, but is released for slow operations such as downloading remote artifacts." => sharing ONE GRADLE_USER_HOME across git worktrees on ONE host is supported; sharing it across separate containers is not.
SRC: https://docs.gradle.org/current/userguide/dependency_caching.html

### For containers, Gradle ships a lock-free shared READ-ONLY dependency cache via GRADLE_RO_DEP_CACHE (incubating)
Layout: `$GRADLE_RO_DEP_CACHE/modules-2` (read-only, shared) alongside `$GRADLE_HOME/caches/modules-2` (container-specific writable). "Gradle looks for dependencies (artifacts or metadata) in both the writable cache in the local Gradle User Home directory and the shared read-only cache." Seed it by COPYING `$GRADLE_USER_HOME/caches/modules-<version>`; "Do not copy the *.lock or gc.properties files if they exist."
SRC: https://docs.gradle.org/current/userguide/dependency_caching.html

### The 'multiple worktrees on one machine is unnecessarily expensive and can be unsafe' quote is from dotnet/android#12149, and is about toolchain provisioning, not Gradle caches
Author simonrozsival, 2026-07-17. Verbatim: "Building dotnet/android from multiple Git worktrees on the same machine is unnecessarily expensive and can be unsafe." Cause: each worktree independently provisions tools while others install into shared but *partially unversioned* directories → repeated downloads, duplicated disk, version conflicts between branches, race conditions on parallel build/clean. Proposed fix: a configurable *versioned* cache (`MA_PREPARE_CACHE_DIR`) with cross-process locking, completion manifests, and atomic staging; branch-specific mutable outputs stay per-worktree while immutable SDKs/toolchains are shared. Measured there: Android toolchain ~11 GB + archive cache ~5 GB on one dev machine.
SRC: https://github.com/dotnet/android/issues/12149

### Concurrent unrelated Gradle builds on one machine DO fail on shared GRADLE_USER_HOME lock contention (open bug since Feb 2022)
gradle/gradle#20055: "Timeout waiting to lock Java compile cache (/home/ec2-user/.gradle/caches/7.4/javaCompile). It is currently in use by another Gradle instance." Still open. Same class of failure reported on Jenkins concurrent builds. This is the concrete cost of sharing GRADLE_USER_HOME across N simultaneous agent builds.
SRC: https://github.com/gradle/gradle/issues/20055

### Remote build cache gives a measured 7.2x on parallel worktree builds (2026-01-26 report)
zenn.dev/solenoid, published 2026/01/26. Single assembleDebug: 154.6s (no cache) → 16.9s (local cache only, 9.1x) → 16.1s (remote cache, 9.6x). Single testDebugUnitTest: 433.6s → 19.2s. FOUR worktrees running assembleDebug in parallel: 786s wall (13 min, each build 13 min) with local cache only → 109s wall (1m49s), individual builds 52s–1m47s. That is the 7.2x. No cache hit-rate figure and no machine spec/module count is given in the article.
SRC: https://zenn.dev/solenoid/articles/a656b2cc321c56

### --offline hard-disables the remote build cache (verified in the Gradle 9.4.1 binary, not just docs)
Extracted from gradle-core-9.4.1.jar in the local Gradle distribution: the literal string `Remote build cache is disabled when running with --offline.` The public build_cache.html page never mentions 'offline' at all, so this is undocumented-in-prose but present in the product. Consequence: you cannot combine `--offline` (for hermetic dependency resolution) with a remote cache; pick one per loop tier.
SRC: https://docs.gradle.org/current/userguide/build_cache.html

### Exact Gradle offline dependency-resolution failure strings (verified from gradle-dependency-management-9.4.1.jar)
`No cached version of %s available for offline mode.` / `No cached version available for offline mode` / `No cached resource '%s' available for offline mode.` / `No cached version listing for %s available for offline mode.` / `Cannot upload to '%s' in offline mode.` (and from gradle-version-control: `Cannot resolve %s from %s in offline mode.`). These are the (b)-class signatures: environment/cache miss, NOT your code.
SRC: https://docs.gradle.org/current/userguide/dependency_caching.html

### Exact Gradle daemon-death and OOM strings (verified from gradle-client-services-9.4.1.jar and gradle-launcher-9.4.1.jar)
Daemon death: `Gradle build daemon disappeared unexpectedly (it may have been killed or may have crashed)` (thrown as DaemonDisappearedException from org.gradle.launcher.daemon.client.DaemonClient); also `The message received from the daemon indicates that the daemon has disappeared.` Daemon churn: `Starting a Gradle Daemon, <N> incompatible and <M> stopped Daemons could not be reused, use --status for details`. Memory expiry fragments in gradle-launcher: `after running out of JVM heap space`, `after running out of JVM Metaspace`, `Daemon will be stopped at the end of the build `, `The currently configured max heap space is '`, `These settings can be adjusted by setting 'org.gradle.jvmargs' in 'gradle.properties'.`, `since the JVM garbage collector is thrashing`, `after being idle for `, `to reclaim system` — suppressible via `org.gradle.daemon.performance.disable-logging`.
SRC: https://github.com/gradle/gradle/issues/9371

### Daemon reuse is fingerprint-matched on JVM args + Java home, so N worktrees with identical gradle.properties share ONE daemon
Gradle reuses a daemon only if Java home/version and JVM arguments match exactly. Immutable JVM properties requiring exact match include: file.encoding, user.language/country/variant, java.io.tmpdir, SSL keystore/truststore props, -Xmx/-Xms, -Xbootclasspath, -ea. "Changing JVM args (like increasing memory) will spawn a new daemon." Practical implication: worktrees do NOT multiply daemons by themselves — but they DO serialise on that single daemon, and deliberately varying `org.gradle.jvmargs` per agent is how you force daemon isolation (at full RAM cost per daemon).
SRC: https://docs.gradle.org/current/userguide/gradle_daemon.html

### Gradle daemon defaults: 512 MB heap, 384 MB metaspace, 3-hour idle timeout
`org.gradle.jvmargs` default = `-Xmx512m -XX:MaxMetaspaceSize=384m`. `org.gradle.daemon.idletimeout` default = 10800000 ms (3 hours). `org.gradle.workers.max` default = number of CPU processors. `org.gradle.parallel` default false; `org.gradle.caching` default false; `org.gradle.configuration-cache` default false; `org.gradle.vfs.watch` default true. GRADLE_USER_HOME defaults to USER_HOME/.gradle. gradle.properties precedence: CLI -D > GRADLE_USER_HOME/gradle.properties > project root gradle.properties > GRADLE_HOME/gradle.properties.
SRC: https://docs.gradle.org/current/userguide/build_environment.html

### The Kotlin daemon is a SECOND JVM per build and inherits org.gradle.jvmargs unless overridden — budget 2x heap
Kotlin daemon is a separate process that inherits `-Xmx` from the launching JVM, i.e. from `org.gradle.jvmargs`, unless `kotlin.daemon.jvmargs` is set. Bitrise (2025-07-08) recommends `org.gradle.jvmargs=-Xmx4G -Xms512M -XX:MaxMetaspaceSize=1g -XX:+UseParallelGC` and explicitly warns Android builds run TWO JVMs (Gradle daemon + Kotlin daemon) so you must size for both concurrently. Escape hatch: `kotlin.compiler.execution.strategy=in-process`.
SRC: https://support.bitrise.io/en/articles/11196749-gradle-memory-fine-tuning-guide

### Kotlin daemons can multiply per Kotlin version in the graph — measured >4.5 GB for daemons alone
gradle/gradle#34755 (opened 2025-08-21, still open): THREE Kotlin daemons spawned (project Kotlin 2.1.20, Gradle 9.0 kotlin-dsl's 2.2, transitive 1.9.25), "each consuming 1GB+ heap memory (after JVM overhead) plus 512MB metaspace", "over 4.5GB of memory just for Kotlin compilation daemons" with only `org.gradle.jvmargs=-Xmx2g -XX:MaxMetaspaceSize=512m` configured. Workaround: set `kotlin.daemon.jvmargs` explicitly.
SRC: https://github.com/gradle/gradle/issues/34755

### Configuration cache entries are NOT relocatable — they never carry across worktrees
Gradle blog 'State of the Configuration Cache' (2025-03-14): "Configuration Cache entries are not relocatable because they contain many absolute file paths." Mitigation is "ensuring that all CI machines have an identical checkout directory and GRADLE_USER_HOME location." The cache lives at `.gradle/configuration-cache` in the PROJECT directory (so it is per-worktree by construction). Gradle encrypts CC data on disk with "a machine-specific key stored in [GRADLE_USER_HOME]", overridable with GRADLE_ENCRYPTION_KEY. Measured wins cited: AndroidX 3.75x CC size reduction (8.10); ~600-project build config time 2m4s → 55s (8.11 parallel config caching).
SRC: https://blog.gradle.org/road-to-configuration-cache

### Configuration cache invalidation inputs (official list)
Invalidated by changes to: init scripts, settings files, build scripts and included scripts; version catalogs, dependency verification files, lock files, gradle.properties; environment variables and system properties read at configuration time; presence/content of files read at configuration time; any ValueSource value. Gradle "compares the build's current configuration inputs against the entry's recorded fingerprint".
SRC: https://docs.gradle.org/current/userguide/configuration_cache.html

### Spotless/JGit still causes configuration-cache misses on branch switch as of Spotless 7.0.2 (open issue)
diffplug/spotless#2431 (opened 2025-02-24, open): `spotlessCheck` reads `.git/HEAD` via JGit, so switching branches prints `Calculating task graph as configuration cache cannot be reused because file '.git/HEAD' has changed.` CC report names `org.eclipse.jgit.util.io.SilentFileInputStream` touching `.git/HEAD` and `.git/config`. Earlier #1806 (closed) was the *harder* Gradle 8.1 failure: external processes `/usr/bin/git --version` and `/usr/bin/git config --system --show-origin --list -z` started at configuration time, unsupported by CC in Spotless <=6.17.0. NOTE for worktrees: every worktree has its own HEAD, so each worktree keeps its own CC entry — and any branch switch inside a worktree invalidates it.
SRC: https://github.com/diffplug/spotless/issues/2431

### Build cache misses across different checkout directories are a known, documented diagnosis path
"To discover these problems, first check out the same commit of your project in two different directories on your machine." Cause: "Tasks that should be relocatable but aren't are usually a result of absolute paths being present among the task's inputs" / "the task tracks absolute paths instead of relative paths and the location of the project directory changed on disk." Debug with `-Dorg.gradle.caching.debug=true`. This is EXACTLY the worktree scenario: worktree A and worktree B are two directories with the same commit.
SRC: https://docs.gradle.org/current/userguide/build_cache_debugging.html

### Remote build cache self-disables for the rest of the build on persistent transport errors
"Requests that fail during request transmission, after having established a TCP connection, will be retried automatically… If the problem persists, the cache operation will fail and the remote cache will be disabled for the remainder of the build." Defaults: local cache enabled with push enabled; remote cache push DISABLED by default (you must set isPush = true). Related open issues on error strategy: gradle/gradle#27644, #19338.
SRC: https://docs.gradle.org/current/userguide/build_cache.html

### rnett/gradle-mcp's query_build already provides typed failure classification with six kinds
query_build parameters: buildId (string|null), kind (enum), query (string|null), outputFile (string|null), pagination {offset, limit}, outcome (enum, filter by task/test result status), testIndex (int|null), taskPath (string|null, TESTS only). kind values: DASHBOARD (default; recent builds, detailed summary when buildId given), CONSOLE ("Console logs. query acts as a regex filter"), TASKS ("query acts as a prefix filter on the task path"), TESTS ("prefix filter on the test name"), FAILURES ("Build failures. query is the exact FailureId"), PROBLEMS ("Compilation/configuration problems. query is the exact ProblemId"). Behavior: "If a query for TASKS, TESTS, FAILURES, or PROBLEMS matches exactly one item, it auto-expands to full details. Otherwise, it returns a summary list." Companion tool `wait_build`. It separates FAILURES (build/task failures) from PROBLEMS (compile/config problems) but does NOT classify infra-vs-code.
SRC: https://gradle-mcp.rnett.dev/latest/tools/LOOKUP_TOOLS/

### gradle-mcp execution tool contract
Tool `gradle`: projectRoot (defaults to GRADLE_MCP_PROJECT_ROOT), commandLine (array of Gradle CLI args), background (bool → returns BuildId), stopBuildId, captureTaskOutput (isolated output for a specific task; not for tests), invocationArguments { additionalEnvVars, additionalSystemProps, additionalJvmArgs, additionalArguments, publishScan (Develocity Build Scan), envSource: NONE|INHERIT|SHELL, javaHome }. Install: `jbang run --quiet --fresh gradle-mcp@rnett` (snapshots: `gradle-mcp-snapshot@rnett`; GAV: `jbang run --fresh dev.rnett.gradle-mcp:gradle-mcp:+`). JDK 21+ required per README (docs elsewhere say JDK 25+ — verify). Add `--no-cds` if native JVMTI agents from security software break CDS.
SRC: https://github.com/rnett/gradle-mcp

### --console=plain and --continue are documented Gradle flags with the exact semantics an agent parser needs
`--console=plain`: "generate plain text only. This option disables all color and other rich output" (the default `auto` emits ANSI/rich status when attached to a console → unparseable). `--continue`: "Continue task execution after a task failure" — Gradle executes every task whose dependencies succeeded, so one run surfaces ALL failures instead of the first. `--offline`: "Specifies that the build should operate without accessing network resources." `--build-cache`/`--no-build-cache` default off. `--max-workers` default = number of processors. `--status` lists running/recently-stopped daemons of the same version; `--stop` stops all daemons of the same version.
SRC: https://docs.gradle.org/current/userguide/command_line_interface.html

### Claude Code's .worktreeinclude is real, uses .gitignore syntax, and only copies files that are BOTH matched and gitignored
Verbatim: "A worktree is a fresh checkout, so untracked files like .env or .env.local from your main repository are not present. To copy them automatically when Claude creates a worktree, add a `.worktreeinclude` file to your project root. The file uses `.gitignore` syntax. Only files that match a pattern and are also gitignored are copied, so tracked files are never duplicated." Applies to --worktree worktrees, subagent worktrees (`isolation: worktree` frontmatter), and desktop parallel sessions. NOT processed when a WorktreeCreate hook is configured — copy inside the hook instead.
SRC: https://code.claude.com/docs/en/worktrees

### worktree.baseRef accepts only "fresh" or "head"
"fresh" (default): branch from the repository's default branch on the remote (usually main). "head": branch from current local HEAD, carrying unpushed commits — "Use this when isolating subagents that need to operate on in-progress work." You CANNOT set it to a branch name; use `git worktree add` for that. For "fresh", Claude Code refreshes origin/HEAD if not fetched in 24h, capped at 5 seconds, falling back to the cached ref. Default worktree location: `.claude/worktrees/<name>/` on branch `worktree-<name>`.
SRC: https://code.claude.com/docs/en/worktrees

### Worktrees share .git, project-scope plugins, and permission approvals with the main checkout; the sandbox specifically allows writes to the shared .git
"git commands in a worktree write to the main repository's shared .git directory, and sandboxing allows those writes, so commands such as git commit work from inside a worktree with the sandbox enabled" — but "Writes to hooks/ and config inside that directory remain denied." Plugins installed at project scope load in worktrees (v2.1.200+). Permission approvals save to the MAIN checkout's .claude/settings.local.json and survive worktree removal (v2.1.211+).
SRC: https://code.claude.com/docs/en/sandboxing

### Concurrent git operations across worktrees are not safe even though worktrees are
kaeawc/auto-worktree#176 (2026-01-07): "Git client is meant to be run by a single process, not multiple processes at the same time, as it could lead to file/data corruption in the .git folder." Shared/vulnerable: .git/objects/, .git/refs/, .git/config, gc and pack files. Mitigation is serialisation (`auto-worktree exec --sequential …`). Worktrees isolate HEAD/index/logs but NOT the shared object database.
SRC: https://github.com/kaeawc/auto-worktree/issues/176

### MEASURED on this repo (63-module Android app, Gradle 8.14.3, AGP 8.x, Apple M1 Max / 10 cores / 32 GB, 2026-08): per-worktree incremental disk cost
Main checkout total 14.7 GB; .git 588 MB (SHARED — not duplicated per worktree); all build/ dirs 11.5 GB; project .gradle/ 1.1 GB; source+untracked remainder 268 MB; `git ls-files` tracked content only ~101 MB. An existing Claude worktree at .claude/worktrees/<name> measured 1.2 GB total after a partial build (app/build 415 MB, .gradle 56 MB, source ~221 MB); a build-free Cursor worktree measured 127 MB. => Fresh worktree ≈ 130–270 MB. Fully built worktree ≈ 12–13 GB. Shared host caches: ~/.gradle = 42 GB total (caches 38 GB, of which build-cache-1 = 10 GB, modules-2 = 4.1 GB, daemon logs 283 MB). KSP/kapt generated dirs were only ~34 MB — the 11.5 GB is dominated by app/build (3.9 GB) and per-module intermediates.
SRC: https://docs.gradle.org/current/userguide/dependency_caching.html

### Claude Code's Bash sandbox: OS primitives, defaults, and the escape hatch
macOS = Seatbelt (nothing to install); Linux/WSL2 = bubblewrap + socat (+ optional seccomp filter from `npm install -g @anthropic-ai/sandbox-runtime` for Unix-socket blocking); WSL1 and native Windows unsupported. Default write = CWD + session temp dir ($TMPDIR is redirected there). Default read = entire computer minus denied dirs — "this default still allows reading credential files such as ~/.aws/credentials and ~/.ssh/". Network: "no domains are pre-allowed by default"; first use of a domain prompts; `strictAllowlist: true` denies instead of prompting (v2.1.219+). Escape hatch: on sandbox-caused failure Claude may retry with `dangerouslyDisableSandbox`; kill it with `"allowUnsandboxedCommands": false` ("Strict sandbox mode"). `sandbox.failIfUnavailable: true` makes a missing dependency a hard failure instead of silently running unsandboxed.
SRC: https://code.claude.com/docs/en/sandboxing

### Documented sandbox incompatibilities that hit an Android/JVM loop directly
"`docker` commands fail: docker is incompatible with the sandbox. Add `docker *` to `excludedCommands`." "Go-based CLIs fail TLS verification on macOS: tools such as gh, gcloud, and terraform may fail TLS verification under Seatbelt. List these tools in excludedCommands." "Bubblewrap fails to start inside a container: in an unprivileged container, bubblewrap cannot mount a fresh /proc. Set `enableWeakerNestedSandbox` to true." "`--dangerously-skip-permissions` fails as root: blocked when running as root or via sudo on Linux and macOS… The check is skipped automatically inside a recognized sandbox." Also: `git merge/checkout` can fail `unable to unlink old` (Linux adds `Read-only file system`) when touching protected paths (.claude/skills, .claude/agents, .claude/hooks, .mcp.json, .git/hooks, .git/config).
SRC: https://code.claude.com/docs/en/sandboxing

### The Bash sandbox alone is explicitly NOT sufficient for unattended runs
"The sandboxed Bash tool on its own constrains only Bash, so it is not sufficient for fully unattended runs in either mode." "Always run --dangerously-skip-permissions sessions inside a container, a VM, or the sandbox runtime, so that file tools, MCP servers, and hooks are also inside the boundary." MCP servers and hooks "are separate processes that run unconstrained on the host" under the Bash sandbox. Layering is supported: Bash sandbox inside a container.
SRC: https://code.claude.com/docs/en/sandbox-environments

### What a container costs you: user-scope config is not present unless mounted, and personal skills do not transfer to remote sessions
Skill scopes: Personal `~/.claude/skills/<name>/SKILL.md` (all your projects), Project `.claude/skills/<name>/SKILL.md`, Plugin `<plugin>/skills/<name>/SKILL.md`. Devcontainer doc: "By default, the container's home directory is discarded on rebuild" — you must mount a named volume at ~/.claude AND set CLAUDE_CONFIG_DIR to it, because ~/.claude.json (OAuth account, personal MCP servers, per-project trust) lives OUTSIDE ~/.claude. Docs also state: "If a skill exists only in ~/.claude/skills/ on your machine, Claude Code reports that the skill was not found when a routine invokes it, because each routine run starts as a fresh remote session." Cloud/Cowork sessions "don't read ~/.claude/skills/ on your machine". Fix: commit skills to the repo's .claude/skills/ or ship them in a repo-declared plugin.
SRC: https://code.claude.com/docs/en/skills

### Anthropic's reference devcontainer firewall allowlist does NOT include any JVM/Android endpoints
.devcontainer/init-firewall.sh builds an ipset `allowed-domains` (hash:net) from: GitHub CIDRs fetched from api.github.com/meta (parsed with jq, regex-validated), registry.npmjs.org, api.anthropic.com, statsig.anthropic.com, sentry.io, statsig.com, marketplace.visualstudio.com, vscode.blob.core.windows.net, update.code.visualstudio.com, plus DNS/53, SSH/22, localhost and host /24. Default policy DROP with conntrack established. Verification: fails if it can reach https://example.com, passes if it can reach https://api.github.com. Requires NET_ADMIN and NET_RAW via runArgs. => For a Gradle/Android agent you must ADD repo.maven.apache.org, dl.google.com, plugins.gradle.org, services.gradle.org yourself.
SRC: https://github.com/anthropics/claude-code/blob/main/.devcontainer/init-firewall.sh

### MEASURED: the exact host allowlist this project's Gradle build actually needs (derived from ~/.gradle/caches/modules-2 metadata origins)
Counted artifact-origin hosts in the local dependency cache: repo.maven.apache.org (5752), dl.google.com (4872), plugins.gradle.org (548), maven.aliyun.com (473), repo.gradle.org (84), jitpack.io (68), devrepo.kakao.com (7), services.gradle.org (4), mobilesdk.useinsider.com (2), maven.lokalise.com (2), maven.apptimize.com (2). settings.gradle.kts declares google(), mavenCentral(), gradlePluginPortal(), https://plugins.gradle.org/m2/, https://jitpack.io, https://devrepo.kakao.com/nexus/content/groups/public/, https://maven.apptimize.com/artifactory/repo, https://maven.lokalise.com, https://mobilesdk.useinsider.com/android, plus flatDir("libs"), with RepositoriesMode.FAIL_ON_PROJECT_REPOS. Gradle's own built-in URL constants (verified in gradle-9.4.1 jars): https://repo1.maven.org/maven2/, https://plugins.gradle.org/m2, https://services.gradle.org/.
SRC: https://docs.gradle.org/current/userguide/declaring_repositories.html

### dagger/container-use: per-agent containers + per-agent git branch, wired as an MCP stdio server
Install: `brew install dagger/tap/container-use` or `curl -fsSL https://raw.githubusercontent.com/dagger/container-use/main/install.sh | bash`. Register: `claude mcp add container-use -- container-use stdio` (or `npx @anthropic-ai/claude-code mcp add container-use -- cu stdio`). "Each agent writes to its own container-use/<env_name> branch, so conflicts only surface when you merge those branches into your main branch." Environment creation can take a git ref (branch or SHA). `--single-tenant` experimental mode locks each MCP server process to a single environment, reducing per-tool-call tokens for CLI agents like Claude Code.
SRC: https://github.com/dagger/container-use

### reactivecircus/android-emulator-runner: current usage, defaults, and the mandatory KVM step
Pin as `reactivecircus/android-emulator-runner@v2` (latest tagged release v2.38.0, 2025-07-05, build tools 37.0.0; v2.37.0 2025-03-14 moved to Node 24 + build tools 36.0.0 + cmdline-tools 12.0). Defaults: target=default, arch=x86, cores=2, avd-name=test, channel=stable, disable-animations=true, force-avd-creation=true, emulator-options=`-no-window -gpu swiftshader_indirect -no-snapshot -noaudio -no-boot-anim`, emulator boot timeout default 600s. Mandatory Linux KVM step: `echo 'KERNEL=="kvm", GROUP="kvm", MODE="0666", OPTIONS+="static_node=kvm"' | sudo tee /etc/udev/rules.d/99-kvm4all.rules; sudo udevadm control --reload-rules; sudo udevadm trigger --name-match=kvm`. AVD caching via actions/cache@v5 on `~/.android/avd/*` and `~/.android/adb*`, keyed `avd-${{ matrix.api-level }}`, with a snapshot-creation step on cache miss and `-no-snapshot-save` on the test run.
SRC: https://github.com/ReactiveCircus/android-emulator-runner

### GitHub Actions KVM availability: larger Linux runners since Feb 2023, all ubuntu-latest since ~Jan 2024
GitHub changelog 2023-02-23: hardware acceleration for Android on larger hosted Linux runners; "Testing on a 4-core machine with hardware acceleration is around 2-3 times faster than not using hardware acceleration and around 2 times faster than using MacOS." Since a runner update in January 2024, /dev/kvm exists on free/non-larger ubuntu-latest runners too. Nested virtualization must be supported by the host VM — this is what breaks emulators inside Docker on most cloud CI. Reported emulator boot on GH Actions: ~3–4 minutes running-and-available; first run with SDK provisioning can exceed 5–10 minutes.
SRC: https://github.blog/changelog/2023-02-23-hardware-accelerated-android-virtualization-on-actions-windows-and-linux-larger-hosted-runners/

### GitHub-hosted larger-runner pricing (Aug 2026), and larger runners are never free
Linux x64: 2-core Advanced $0.006/min, 4-core $0.012, 8-core $0.022, 16-core $0.042, 32-core $0.082, 64-core $0.162, 96-core $0.252. Linux arm64: 2-core $0.005, 4-core $0.008, 8-core $0.014, 16-core $0.026. macOS 12-core $0.077/min; macOS 5-core M2 Pro $0.102/min. GPU Linux 4-core $0.052. "Included minutes cannot be used for larger runners" and "The larger runners are not free for public repositories." (Jan 2026 saw up to a 39% cut; the proposed $0.002/min self-hosted platform fee was postponed indefinitely — as of Aug 2026 self-hosted minutes remain free.)
SRC: https://github.com/github/docs/blob/main/content/billing/reference/actions-runner-pricing.md

### Gradle Managed Devices: exact task names, the CI GPU flag, sharding, and the ATD limits
Tasks: `./gradlew <device-name><BuildVariant>AndroidTest` (e.g. `pixel2api30DebugAndroidTest`) and `./gradlew <group-name>Group<BuildVariant>AndroidTest` (e.g. `phoneAndTabletGroupDebugAndroidTest`). Headless/CI: "When using build-managed devices on servers that don't support hardware rendering, such as GitHub Actions, you need to specify the following flag: `-Pandroid.testoptions.manageddevices.emulator.gpu=swiftshader_indirect`." Sharding: `android.experimental.androidTest.numManagedDeviceShards=<n>` in gradle.properties — 3 devices × 2 shards = 6 virtual devices provisioned; "can be resource intensive; may cause timeout failures if over-provisioned." GMD is available for API 27+. ATD (`aosp-atd` / `google-atd`) limits: "ATDs currently support only API level 30" and "Screenshot tests that depend on hardware rendering currently aren't supported when using ATDs." GMD uses emulator snapshots to improve startup time and restore a clean state between tests.
SRC: https://developer.android.com/studio/test/managed-devices

### Android emulator in Docker: KVM must be passed through explicitly; Linux hosts only
google/android-emulator-container-scripts: run with `--device /dev/kvm` (preferred over `--privileged`), `--publish 8554:8554/tcp` (gRPC) and `--publish 5555:5555/tcp` (ADB), e.g. `us-docker.pkg.dev/android-emulator-268719/images/30-google-x64:30.1.2`. "The Docker images require Linux only (launching on Windows or macOS is not supported)" and KVM must be available. In cloud, you must first obtain nested virtualization (AWS bare metal / Azure nested virt / GCE nested virt). => On an Apple Silicon dev machine there is NO /dev/kvm, so containerised x86 emulators and containerised GMD are simply unavailable locally.
SRC: https://github.com/google/android-emulator-container-scripts

### Robolectric hermetic offline: exact property names and defaults
`robolectric.offline` — "Set to true to disable runtime fetching of jars." default false. `robolectric.dependency.dir` — "When in offline mode, specifies a folder containing runtime dependencies." default null. `robolectric.dependency.repo.id` default `mavenCentral`; `robolectric.dependency.repo.url` default `https://repo1.maven.org/maven2`; also `.repo.username` / `.repo.password`. `robolectric.usePreinstrumentedJars` default true ("use instrumented jars to reduce instrumentation overhead"). Proxy since 4.9.1: `robolectric.dependency.proxy.host` / `.port`. Robolectric's MavenArtifactFetcher "does not use any proxies defined by the Gradle build system" — a Gradle-level proxy will NOT cover it.
SRC: https://robolectric.org/configuring/

### Block open-sourced an MCP task queue specifically because parallel agents thrash one machine with Gradle
Block Engineering blog, 2026-01-14: "When multiple agents decide to run a Gradle build, your machine grinds to a halt." Measured: Agent A build 192.6s, Agent B build 32.6s when queued behind it; estimated >10 minutes total and an unusable machine if both ran concurrently. A sub-3-minute build "could stretch to 15 minutes" under contention. Also: "When test output from multiple builds interleaves, agents can't tell which results are theirs," and multiple agents deploying to the same emulator clash. Implementation: ~600 lines of Python, SQLite in WAL mode, FIFO; delivered as an MCP server rather than a shell wrapper specifically to dodge agent tool-call timeouts ("Claude Code ~2 minutes, Cursor 30 seconds").
SRC: https://engineering.block.xyz/blog/the-missing-piece-for-local-ai-development

### AGP 9.0 (Jan 2026) hard-requires Gradle 9.1.0 and pins KGP/KSP versions
AGP 9.0.1, January 2026. Minimum AND default Gradle version: 9.1.0. Built-in Kotlin support is on by default — you no longer apply org.jetbrains.kotlin.android; opt out with `android.builtInKotlin=false` in gradle.properties, and "The ability to opt-out will be removed in AGP 10.0 (mid-2026)." Runtime dependency on KGP 2.2.10 (lower versions auto-upgraded); KSP below 2.2.10-2.0.2 auto-upgraded to match. AGP 9.0 uses new DSL interfaces exclusively and removes the old deprecated variant API. AGP 9.2.0 (April 2026) requires Gradle 8.11+. Release notes make NO claim that configuration cache is required or default-on in 9.0.1.
SRC: https://developer.android.com/build/releases/agp-9-0-0-release-notes

### gradle/build-cache-node is usable standalone but with 'restricted functionality'
Docker Hub gradle/build-cache-node: "The cache node can also be used without a Develocity installation with restricted functionality." Image ~191.7 MB. "Support for build cache node versions older than 14.0 is ending and images for those versions will not longer be available as of December 2024." The Zenn setup uses port 5071, `-v $HOME/gradle-build-cache:/data`, config `version: 5 / cache: accessControl: anonymousLevel: readwrite`, and retrieves the initial credentials with `docker logs gradle-cache | grep "username and password"`.
SRC: https://hub.docker.com/r/gradle/build-cache-node

### Jason Pearson's CI config-cache reuse: what to cache, and measured outcomes
June 2025. Directories to cache/restore for CC reuse: `./gradle/<gradle-version>`, `./gradle/configuration-cache`, `./your-convention-plugins/**/build`, `~/.gradle/caches/<gradle-version>/dependencies-accessors`, `.../generated-gradle-jars`, `.../groovy-dsl`, `.../kotlin-dsl`, `.../transforms`, `~/.gradle/caches/jars-9`, `~/.gradle/caches/modules-2`. Configuration phase was "3+ minutes" on his large projects; he reports ~95% cache hit rate (50% complete hits) by 2025. "Partial matches still resulted in some benefit as long as convention plugin sources hadn't changed." GitHub Actions network transfer 150–300 MB/s; zstd decompression ~13,000 MB/s; a dry-run optimization "cut the size of the transforms directory in half or more." CC encryption keystore in GRADLE_USER_HOME was added after GHSA-h3qr-39j9-4r5v (late 2024) and is not cached by default — supply the key via a CI secret.
SRC: https://www.jasonpearson.dev/gradle-config-cache-reuse-on-ci/

### Maestro has no headless mode for Android — --headless is web-only
`maestro test` flags: `--shards=<count>` ("Number of parallel shards to distribute tests across"), `--format=` JUNIT|HTML|NOOP (default NOOP), `--output=`, `--env=K=V`, `--device`, `--continuous`/`-c`, `--include-tags`/`--exclude-tags`, `--test-output-dir`. `--headless` is documented as "(Web only) Run the tests in headless mode". `maestro start-device` takes `--platform=android|ios|web`, `--device-os` (`--os-version` deprecated), `--device-locale` (e.g. de_DE), `--force-create`. So on Android, Maestro still needs a real emulator/device underneath — i.e. it inherits the KVM constraint.
SRC: https://docs.maestro.dev/maestro-cli/maestro-cli-commands-and-options

## EXAMPLES
### Remote build cache for parallel worktrees — the exact config behind the measured 7.2x
FILE: settings.gradle.kts (repo root; must be in settings, not build.gradle)
```
// settings.gradle.kts
buildCache {
    local {
        isEnabled = true
    }
    remote<HttpBuildCache> {
        url = uri("http://localhost:5071/cache/")
        isAllowInsecureProtocol = true
        isPush = true
    }
}
```
SRC: https://zenn.dev/solenoid/articles/a656b2cc321c56

### Dockerised Gradle build cache node + its config.yaml
FILE: $HOME/gradle-build-cache/conf/config.yaml (bind-mounted volume)
```
docker run -d \
  --name gradle-cache \
  -p 5071:5071 \
  -v $HOME/gradle-build-cache:/data \
  gradle/build-cache-node

# initial credentials:
docker logs gradle-cache | grep "username and password"

# /data/conf/config.yaml
version: 5
cache:
  accessControl:
    anonymousLevel: readwrite
```
SRC: https://zenn.dev/solenoid/articles/a656b2cc321c56

### Shared read-only dependency cache for containerised agents (avoids the 'processes must communicate' restriction)
FILE: env var GRADLE_RO_DEP_CACHE; docker run -v /srv/gradle-ro-cache:/ro-cache:ro
```
# 1. seed once from a normal build, then COPY (never symlink) it:
cp -r "$GRADLE_USER_HOME/caches/modules-2" /srv/gradle-ro-cache/modules-2
find /srv/gradle-ro-cache -name '*.lock' -delete
rm -f /srv/gradle-ro-cache/modules-2/gc.properties

# 2. per container:
export GRADLE_RO_DEP_CACHE=/srv/gradle-ro-cache
#   $GRADLE_RO_DEP_CACHE/modules-2  -> read-only shared cache
#   $GRADLE_HOME/caches/modules-2   -> container-specific writable cache
```
SRC: https://docs.gradle.org/current/userguide/dependency_caching.html

### .worktreeinclude for an Android repo (gitignored build inputs a fresh worktree lacks)
FILE: <repo-root>/.worktreeinclude — .gitignore syntax; only files that match AND are gitignored are copied. Verified on this repo: local.properties is gitignored and REQUIRED (contains sdk.dir, flutter.sdk); the keystore dir here is tracked so it needs no entry.
```
local.properties
keystore.properties
app/google-services.json
app/src/*/google-services.json
.env
.env.local
signing/*.jks
```
SRC: https://code.claude.com/docs/en/worktrees

### worktree.baseRef so agent worktrees branch from in-progress work instead of origin/main
FILE: .claude/settings.json or ~/.claude/settings.json — only "fresh" (default) and "head" are accepted; a branch name is invalid
```
{
  "worktree": {
    "baseRef": "head"
  }
}
```
SRC: https://code.claude.com/docs/en/worktrees

### WorktreeCreate hook that fully replaces git logic (note: .worktreeinclude is NOT processed once this exists, so copy config inside the hook)
FILE: .claude/settings.json — hook reads {name} JSON on stdin, prints the created directory path on stdout; pair with WorktreeRemove
```
{
  "hooks": {
    "WorktreeCreate": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash -c 'NAME=$(jq -r .name); DIR=\"$HOME/.claude/worktrees/$NAME\"; svn checkout https://svn.example.com/repo/trunk \"$DIR\" >&2 && echo \"$DIR\"'"
          }
        ]
      }
    ]
  }
}
```
SRC: https://code.claude.com/docs/en/worktrees

### Subagent that always runs in its own worktree
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
SRC: https://code.claude.com/docs/en/sub-agents

### Agent-parsable Gradle invocation (the two flags that are non-negotiable, plus per-worktree isolation knobs)
FILE: agent wrapper script, e.g. .claude/scripts/verify.sh
```
./gradlew \
  --console=plain \
  --continue \
  --stacktrace \
  -Dorg.gradle.caching.debug=false \
  --project-cache-dir "$PWD/.gradle" \
  :app:assembleDevelopDebug testDevelopDebugUnitTest

# force a DEDICATED daemon for this agent (daemon reuse is fingerprinted on JVM args):
#   -Dorg.gradle.jvmargs="-Xmx6g -XX:MaxMetaspaceSize=1g -Dagent.slot=2"
# force a dedicated GRADLE_USER_HOME (loses shared dep cache, use with GRADLE_RO_DEP_CACHE):
#   GRADLE_USER_HOME=/agents/2/gradle ./gradlew ...
```
SRC: https://docs.gradle.org/current/userguide/command_line_interface.html

### Failure-classification regexes (all strings verified against the Gradle 9.4.1 distribution jars on this machine)
FILE: .claude/skills/gradle-triage/classify.py or a hook script
```
# (b) ENVIRONMENT — offline dependency cache miss  => re-run WITHOUT --offline, do not touch code
'No cached version of .* available for offline mode\.'
'No cached version available for offline mode'
'No cached resource .* available for offline mode\.'
'No cached version listing for .* available for offline mode\.'
'Cannot upload to .* in offline mode\.'
'Cannot resolve .* from .* in offline mode\.'

# (b') CACHE TOPOLOGY (informational, not a failure)
'Remote build cache is disabled when running with --offline\.'

# (c) INFRASTRUCTURE — daemon death / OOM / lock contention => retry once, then escalate
'Gradle build daemon disappeared unexpectedly \(it may have been killed or may have crashed\)'
'The message received from the daemon indicates that the daemon has disappeared\.'
'Starting a Gradle Daemon, [0-9]+ incompatible and [0-9]+ stopped Daemons could not be reused'
'after running out of JVM heap space'
'after running out of JVM Metaspace'
'since the JVM garbage collector is thrashing'
'Daemon will be stopped at the end of the build'
'Timeout waiting to lock .*\. It is currently in use by another Gradle instance\.'
'java\.lang\.OutOfMemoryError'
'Expiring Daemon because JVM heap space is exhausted'

# (a) YOUR CODE — only classify here after (b) and (c) are excluded
'^e: file://.*\.kt:[0-9]+:[0-9]+ '            # Kotlin compile error
'> Compilation error\. See log for more details'
'^[0-9]+ tests completed, [0-9]+ failed'
'org\.opentest4j\.AssertionFailedError'

# (d) FLAKY — same command, different outcome across 2 runs with identical inputs;
#     needs a re-run, not a regex. Common tells: Robolectric jar download, emulator ADB timeout,
#     'Connection reset' / 'Read timed out' against a repo host.
```
SRC: https://github.com/gradle/gradle/issues/20055

### gradle-mcp: typed failure querying instead of regex-scraping stdout
FILE: .mcp.json (project scope, so it also loads inside worktrees and containers)
```
# install
jbang run --quiet --fresh gradle-mcp@rnett      # JDK 21+ (docs elsewhere say 25+)

# register
claude mcp add gradle -- jbang run --quiet --fresh gradle-mcp@rnett

# run in background, then query typed results
gradle(projectRoot="/repo", commandLine=[":app:assembleDevelopDebug"], background=true)
  -> BuildId
wait_build(buildId=...)
query_build(buildId=..., kind="FAILURES")   # query = exact FailureId
query_build(buildId=..., kind="PROBLEMS")   # compilation/configuration problems; query = exact ProblemId
query_build(buildId=..., kind="TESTS", taskPath=":app:testDevelopDebugUnitTest", outcome=...)
query_build(buildId=..., kind="CONSOLE", query="offline mode")   # query is a REGEX for CONSOLE
# single exact match auto-expands to full detail; otherwise you get a summary list
```
SRC: https://gradle-mcp.rnett.dev/latest/tools/LOOKUP_TOOLS/

### Sandbox settings for a Gradle/Android agent loop (macOS or Linux host)
FILE: ~/.claude/settings.json (user scope — strictAllowlist and filesystem.disabled are IGNORED from a repo's .claude/settings.json). Host list empirically derived from ~/.gradle/caches/modules-2 origins on this repo.
```
{
  "sandbox": {
    "enabled": true,
    "failIfUnavailable": true,
    "allowUnsandboxedCommands": false,
    "filesystem": {
      "allowWrite": [
        "~/.gradle",
        "~/.android",
        "~/.konan",
        "~/.m2",
        "/tmp"
      ]
    },
    "network": {
      "strictAllowlist": true,
      "allowedDomains": [
        "repo.maven.apache.org",
        "repo1.maven.org",
        "dl.google.com",
        "maven.google.com",
        "plugins.gradle.org",
        "services.gradle.org",
        "repo.gradle.org",
        "jitpack.io",
        "downloads.gradle.org",
        "api.anthropic.com",
        "claude.ai",
        "platform.claude.com",
        "code.claude.com"
      ]
    },
    "credentials": {
      "files": [
        { "path": "~/.ssh", "mode": "deny" },
        { "path": "~/.aws/credentials", "mode": "deny" }
      ],
      "envVars": [
        { "name": "ANDROID_KEYSTORE", "mode": "deny" },
        { "name": "ANDROID_STORE_PASSWORD", "mode": "deny" },
        { "name": "ANDROID_KEY_PASSWORD", "mode": "deny" }
      ]
    },
    "excludedCommands": ["docker *", "gh"]
  }
}
```
SRC: https://code.claude.com/docs/en/sandboxing

### Managed settings that force sandboxing org-wide
FILE: /etc/claude-code/managed-settings.json on Linux (or via MDM / server-managed settings). In a devcontainer: COPY managed-settings.json /etc/claude-code/managed-settings.json
```
{
  "sandbox": {
    "enabled": true,
    "failIfUnavailable": true,
    "allowUnsandboxedCommands": false,
    "allowManagedDomainsOnly": true,
    "allowManagedReadPathsOnly": true
  }
}
```
SRC: https://code.claude.com/docs/en/sandboxing

### Devcontainer bits that keep an agent's identity across rebuilds (otherwise you lose ~/.claude on every rebuild)
FILE: .devcontainer/devcontainer.json — CLAUDE_CONFIG_DIR is required because ~/.claude.json (OAuth account, personal MCP servers, trust) lives OUTSIDE ~/.claude
```
{
  "image": "mcr.microsoft.com/devcontainers/base:ubuntu",
  "features": {
    "ghcr.io/anthropics/devcontainer-features/claude-code:1.0": {}
  },
  "mounts": [
    "source=claude-code-config-${devcontainerId},target=/home/node/.claude,type=volume",
    "source=gradle-cache-${devcontainerId},target=/home/node/.gradle,type=volume"
  ],
  "containerEnv": {
    "CLAUDE_CONFIG_DIR": "/home/node/.claude",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "DISABLE_AUTOUPDATER": "1",
    "GRADLE_USER_HOME": "/home/node/.gradle"
  },
  "remoteUser": "node",
  "runArgs": ["--cap-add=NET_ADMIN", "--cap-add=NET_RAW"]
}
```
SRC: https://code.claude.com/docs/en/devcontainer

### sandbox-runtime: put the WHOLE Claude Code process (tools, hooks, MCP servers) behind Seatbelt/bubblewrap without Docker
FILE: ~/.srt-settings.json (or --settings <file>; the runtime refuses to start if an explicitly-passed file fails to load, but starts SILENTLY network-denied if ~/.srt-settings.json is invalid)
```
# Linux/WSL2 prerequisites
sudo apt-get install bubblewrap socat   # + ripgrep from your package manager

# create config paths first — on Linux write grants apply only to paths that already exist
mkdir -p ~/.claude && echo '{}' > ~/.claude.json

# settings live in ~/.srt-settings.json; allowWrite must include the project dir,
# ~/.claude, ~/.claude.json and /tmp; allowedDomains must include api.anthropic.com
# (plus claude.ai + platform.claude.com for OAuth sign-in/refresh)

npx @anthropic-ai/sandbox-runtime claude
```
SRC: https://code.claude.com/docs/en/sandbox-environments

### Block agent-task-queue — serialise expensive Gradle work across N agents on one machine
FILE: .mcp.json; server options: --data-dir (default /tmp/agent-task-queue), --max-output-files 50, --lock-timeout 120 (minutes), --queue-capacity scope=N (repeatable). Apache 2.0.
```
# install + register
uv tool install agent-task-queue
claude mcp add agent-task-queue -- uvx agent-task-queue@latest

# agent calls this instead of Bash for anything expensive
run_task(
    command="./gradlew connectedAndroidTest",
    working_directory="/repo",
    queue_name="android",
    env_vars="ANDROID_SERIAL=emulator-5560",
    timeout_seconds=1200      # default 1200; queue wait time does NOT count
)

# shared build step in its own queue, then fan out per-emulator with -x to skip rebuild
run_task(command="./gradlew assembleDebug assembleDebugAndroidTest",
         working_directory="/repo", queue_name="gradle/build")

# allow 2 concurrent gradle builds instead of 1
uvx agent-task-queue@latest --queue-capacity=gradle=2
```
SRC: https://github.com/block/agent-task-queue

### Robolectric hermetic offline (removes network from the fast tier and fixes parallel-execution flakiness)
FILE: app/build.gradle.kts + robolectric-jars/build.gradle.kts (pattern from utzcoz/robolectric-offline-sample). NOTE: Robolectric's MavenArtifactFetcher ignores Gradle's proxy config, so offline mode is the only reliable hermetic option.
```
android {
  testOptions {
    unitTests.all {
      it.systemProperty("robolectric.offline", "true")
      it.systemProperty("robolectric.dependency.dir",
          "${rootDir}/robolectric-jars/preinstrumented")
      it.systemProperty("robolectric.usePreinstrumentedJars", "true")
    }
  }
}

// pre-seed once (per Robolectric upgrade), then commit the task, not the jars:
// ./gradlew downloadAllRobolectricJars
// declares each org.robolectric:android-all-instrumented:<ver> in
// robolectric-jars/build.gradle.kts and copies into robolectric-jars/preinstrumented/
```
SRC: https://robolectric.org/blog/2023/11/11/improving-android-all-downloading/

### Gradle Managed Devices for a container/CI tier (no window, software GPU)
FILE: app/build.gradle.kts + gradle.properties. ATD = API 30 ONLY and no hardware-rendering screenshot tests. Task naming: <deviceName><Variant>AndroidTest, <groupName>Group<Variant>AndroidTest.
```
android {
  testOptions {
    managedDevices {
      localDevices {
        create("pixel2api30") {
          device = "Pixel 2"
          apiLevel = 30
          systemImageSource = "aosp-atd"   // or "google-atd" for Play Services
        }
      }
    }
  }
}

# gradle.properties
android.experimental.androidTest.numManagedDeviceShards=2

# invocation on a host with no hardware rendering (GitHub Actions, Docker)
./gradlew pixel2api30DebugAndroidTest \
  -Pandroid.testoptions.manageddevices.emulator.gpu=swiftshader_indirect
```
SRC: https://developer.android.com/studio/test/managed-devices

### Emulator on CI with KVM + AVD snapshot cache (the standard reactivecircus recipe)
FILE: .github/workflows/*.yml — run on ubuntu-latest (KVM present since ~Jan 2024) or a larger Linux runner
```
- name: Enable KVM group perms
  run: |
    echo 'KERNEL=="kvm", GROUP="kvm", MODE="0666", OPTIONS+="static_node=kvm"' | sudo tee /etc/udev/rules.d/99-kvm4all.rules
    sudo udevadm control --reload-rules
    sudo udevadm trigger --name-match=kvm

- name: AVD cache
  uses: actions/cache@v5
  id: avd-cache
  with:
    path: |
      ~/.android/avd/*
      ~/.android/adb*
    key: avd-${{ matrix.api-level }}

- name: Create AVD and generate snapshot for caching
  if: steps.avd-cache.outputs.cache-hit != 'true'
  uses: reactivecircus/android-emulator-runner@v2
  with:
    api-level: ${{ matrix.api-level }}
    force-avd-creation: false
    emulator-options: -no-window -gpu swiftshader_indirect -noaudio -no-boot-anim -camera-back none
    disable-animations: false
    script: echo "Generated AVD snapshot for caching."

- name: Run tests
  uses: reactivecircus/android-emulator-runner@v2
  with:
    api-level: ${{ matrix.api-level }}
    force-avd-creation: false
    emulator-options: -no-snapshot-save -no-window -gpu swiftshader_indirect -noaudio -no-boot-anim -camera-back none
    disable-animations: true
    script: ./gradlew connectedDevelopDebugAndroidTest --console=plain
```
SRC: https://github.com/ReactiveCircus/android-emulator-runner

### Verifying the offline/remote-cache interaction claim yourself (reproducible on any machine with a Gradle dist)
FILE: ad-hoc shell; useful because build_cache.html never documents the --offline interaction
```
D=$(find ~/.gradle/wrapper/dists/gradle-9.4.1-bin -maxdepth 2 -type d -name 'gradle-9.4.1')
unzip -p "$D/lib/gradle-core-9.4.1.jar" '*.class' | strings | grep -i 'offline'
#   -> Remote build cache is disabled when running with --offline.

unzip -p "$D/lib/plugins/gradle-dependency-management-9.4.1.jar" '*.class' | strings | grep 'offline mode'
#   -> No cached version of %s available for offline mode.
#   -> No cached version listing for %s available for offline mode.
#   -> No cached resource '%s' available for offline mode.
#   -> Cannot upload to '%s' in offline mode.
```
SRC: https://docs.gradle.org/current/userguide/build_cache.html

## GOTCHAS
- --offline and a remote build cache are mutually exclusive. Gradle silently logs `Remote build cache is disabled when running with --offline.` This is NOT in the public build_cache.html docs (that page contains no occurrence of 'offline' at all) — it is only in the binary. So the 'hermetic offline inner loop' and the 'remote-cache-accelerated worktree' strategies cannot be the same tier.
- Configuration cache NEVER transfers between worktrees. Entries "contain many absolute file paths", live in the per-project `.gradle/configuration-cache`, and are encrypted with a machine-specific key. Every new worktree pays the full configuration phase at least once (3+ minutes on large projects per Jason Pearson). Also gradle/gradle#16739: the config cache does not fully honour `--project-cache-dir`.
- Spotless still poisons the configuration cache on branch switch as of 7.0.2 (diffplug/spotless#2431, open). JGit's SilentFileInputStream reads `.git/HEAD` and `.git/config` → `Calculating task graph as configuration cache cannot be reused because file '.git/HEAD' has changed.` For agents that switch branches inside a worktree this converts every switch into a full reconfiguration.
- N worktrees do NOT give you N Gradle daemons. Daemon reuse is fingerprinted on JAVA_HOME + JVM args (including -Xmx/-Xms, file.encoding, java.io.tmpdir, SSL props). With identical gradle.properties across worktrees, all agents queue on ONE daemon and serialise. Forcing separate daemons (by varying org.gradle.jvmargs) costs full heap per daemon — and each Gradle daemon also spawns a Kotlin compile daemon that inherits -Xmx unless kotlin.daemon.jvmargs is set.
- This repo's gradle.properties sets `org.gradle.jvmargs=-Xmx8g`. With the Kotlin daemon inheriting it, ONE agent can reserve ~16 GB of heap headroom on a 32 GB machine. Two concurrent agents with dedicated daemons will swap. Fix: lower to -Xmx4g and set kotlin.daemon.jvmargs=-Xmx3g before going parallel.
- Kotlin daemons multiply per Kotlin version in the build graph. gradle/gradle#34755 (open, Aug 2025) measured THREE daemons at 1 GB+ heap + 512 MB metaspace each = >4.5 GB, purely from KGP version skew (project 2.1.20 vs kotlin-dsl 2.2 vs a transitive 1.9.25). AGP 9.0's auto-upgrade of KGP to 2.2.10 and KSP to 2.2.10-2.0.2 helps but does not fix third-party skew.
- Sharing GRADLE_USER_HOME across concurrent builds is safe-by-design but contended in practice: gradle/gradle#20055 `Timeout waiting to lock Java compile cache (…/caches/7.4/javaCompile). It is currently in use by another Gradle instance.` — open since Feb 2022. The failure looks like a build failure to a naive agent; it is infrastructure.
- Gradle's concurrent-cache locking only works "if the different Gradle processes can communicate together" — explicitly NOT the case for containerised builds. If you give each agent a container and bind-mount the SAME ~/.gradle, you are outside the supported model. Use GRADLE_RO_DEP_CACHE (lock-free, read-only) plus a small per-container writable cache instead.
- git itself is single-process. Worktrees isolate HEAD/index/logs but share .git/objects, .git/refs, .git/config and pack files. Concurrent `git commit`/`gc`/`fetch` across agents can corrupt the object store (kaeawc/auto-worktree#176). Serialise git write operations, or accept the risk.
- Anthropic's reference devcontainer firewall allowlists GitHub, npm, Anthropic, Sentry/Statsig and VS Code — and NOTHING for the JVM. A Gradle build inside it fails immediately on repo.maven.apache.org and dl.google.com. You must extend init-firewall.sh (or use sandbox allowedDomains) with the repo hosts your build actually resolves.
- `docker` is documented as incompatible with the Claude Code Bash sandbox ("Add `docker *` to excludedCommands to run it outside the sandbox"). So the sandbox cannot itself launch the containerised emulator or the build-cache node — those escape the boundary.
- `--dangerously-skip-permissions` is refused when running as root on Linux/macOS. Any container you build for unattended agents must set a non-root remoteUser, or the flag will not run at all.
- A container/sandbox costs you your user-scope setup: personal skills at ~/.claude/skills, ~/.claude/CLAUDE.md, and ~/.claude.json (OAuth account, personal MCP servers, per-project trust) are absent unless you mount a volume AND set CLAUDE_CONFIG_DIR. Docs are explicit that remote/cloud/routine sessions "don't read ~/.claude/skills/ on your machine". The durable fix is to move the skills your loop depends on into the repo's .claude/skills/ (which worktrees inherit) or a repo-declared plugin.
- sandbox-runtime fails OPEN in a specific way: "Without a valid ~/.srt-settings.json, the runtime starts anyway, blocks network access, and confines writes to built-in runtime paths… Don't take a clean start as proof your settings loaded." Pass --settings explicitly, which does hard-fail on load errors.
- The sandbox proxy does not terminate TLS by default, so `allowedDomains` decisions are made from the client-supplied hostname — domain fronting can reach hosts outside the allowlist. Allowing a broad entry like `github.com` is a documented exfiltration path.
- There is no /dev/kvm on Apple Silicon, and google/android-emulator-container-scripts is "Linux only (launching on Windows or macOS is not supported)". Containerised emulators and containerised Gradle Managed Devices are simply unavailable on a Mac dev box — your local mid-tier has to be Robolectric/JVM, with the emulator tier pushed to CI or a Linux host.
- GMD's ATD images are API 30 ONLY, and "Screenshot tests that depend on hardware rendering currently aren't supported when using ATDs." If your verification loop includes Compose screenshot tests, ATD is out; use Roborazzi/Paparazzi on the JVM instead.
- GMD sharding multiplies device count: 3 devices × 2 shards provisions 6 emulators. Android's own docs warn it "can be resource intensive; may cause timeout failures if over-provisioned."
- Maestro has no Android headless mode — `--headless` is documented as web-only. Android Maestro still needs a booted emulator, so it inherits every KVM/nested-virtualisation constraint.
- Robolectric's MavenArtifactFetcher "does not use any proxies defined by the Gradle build system." A network-restricted sandbox will break Robolectric's android-all download even when Gradle itself is fine. Only robolectric.offline + a pre-seeded robolectric.dependency.dir is genuinely hermetic.
- Gradle's default console is `auto`, which emits ANSI/rich progress when attached to a terminal. Without `--console=plain` an agent's regex parsing sees control sequences and rewritten lines. Without `--continue` it sees only the FIRST failure and will iterate one error at a time.
- Machine saturation arrives at 2–3 concurrent Gradle builds, not 5. Block measured a 192.6s build vs a 32.6s build when serialised, and estimated >10 minutes plus an unusable machine if both ran together; a sub-3-minute build "could stretch to 15 minutes" under contention. Interleaved stdout from concurrent builds also means "agents can't tell which results are theirs."
- GitHub-hosted larger runners are never free, even for public repos, and included minutes cannot be spent on them. At $0.012/min (Linux 4-core x64) a 15-minute emulator job is ~$0.18; a 5-agent matrix on every push adds up fast. Linux arm64 4-core at $0.008/min is 33% cheaper but has no x86 emulator images.
- AGP 9.0 hard-requires Gradle 9.1.0 and force-upgrades KGP to 2.2.10 / KSP to 2.2.10-2.0.2. This repo is on Gradle 8.14.3 with configuration cache explicitly disabled (`org.gradle.unsafe.configuration-cache=false`) — the AGP 9 migration and the configuration-cache-reuse strategy are coupled and should be sequenced together.
- The standalone gradle/build-cache-node runs "without a Develocity installation with restricted functionality" — Docker Hub does not spell out what is restricted or whether it is free for commercial use. Confirm licensing before making it load-bearing.
- `.worktreeinclude` copies only files that are BOTH pattern-matched AND gitignored. If someone accidentally commits local.properties, the entry silently stops working. And once you add a WorktreeCreate hook, .worktreeinclude stops being processed entirely.

## OPEN
- What exactly is 'restricted' about gradle/build-cache-node run standalone without Develocity, and is it licensed for commercial team use? Docker Hub only says "can also be used without a Develocity installation with restricted functionality"; docs.develocity.ai/build-cache-node/docker/ returned 404 at time of research.
- Does the Zenn 7.2x measurement share one GRADLE_USER_HOME across the 4 worktrees, or one per worktree? The article does not say, and it materially changes whether the 786s baseline includes lock contention. It also reports no cache hit rate and no machine spec / module count.
- gradle-mcp version requirements are inconsistent across sources: the README says "JDK 21 or higher is required", a directory listing says JDK 25+. Also unverified: whether query_build(kind=FAILURES) surfaces daemon-disappeared / OOM events at all, since those kill the build BEFORE the Tooling API can report structured failures — likely they only appear under kind=CONSOLE.
- No documented Gradle exit-code table exists. Gradle returns 1 for build failure generically; whether daemon-disappearance and OOM produce a distinguishable exit code (vs. compile failure) is undocumented and would need empirical testing per version.
- Precise per-daemon RSS for a 60-module Android build at -Xmx8g is not published anywhere credible. The only measured figures found were 140–177 MB (Gradle 2.5, historical/stale) and the >4.5 GB Kotlin-daemon aggregate from gradle/gradle#34755. This needs local measurement with `jcmd GC.heap_info` / `ps -o rss` during a real assemble.
- Whether GRADLE_RO_DEP_CACHE is still 'incubating' in Gradle 9.4 and whether it is compatible with dependency verification and lockfiles was not confirmed.
- No 2025–2026 primary benchmark was found for emulator boot + connectedAndroidTest wall clock on current ubuntu-latest runners. The 3–4 minute boot / 600s default timeout figures come from issue threads and the action's defaults, not a controlled benchmark. Latency budgets below should be treated as order-of-magnitude.
- Whether Gradle Managed Devices work at all inside an unprivileged Docker container given nested-virtualisation limits is not documented by Google; the only official CI guidance is the swiftshader_indirect GPU flag, which addresses rendering, not virtualisation.
- Whether `--project-cache-dir` fully isolates per-worktree state in Gradle 9.x (gradle/gradle#16739 says the configuration cache does not honour it) — needs re-testing on 9.4.
- Exact behaviour of Claude Code's sandbox when a Gradle daemon it spawned outlives the session: the daemon is a child process created under the sandbox, but survives 3 hours by default (org.gradle.daemon.idletimeout=10800000). Whether it retains sandbox restrictions across sessions is undocumented.

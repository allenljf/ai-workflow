# The Android verification toolchain as oracles for an AI agent loop (2026): Gradle/CLI invocations, latency tiers, error classes, offline/incremental behaviour, and machine-readable output

## SUMMARY
Industry practice in 2026 splits Android verification into three latency tiers. **Inner loop (<30s, agent-runnable every edit):** module-scoped `:mod:compileDebugKotlin --offline` (Kotlin compiler is the highest-signal oracle — type/null/override errors as `file:line:col: error:`), `spotlessApply`/`ktlintFormat` (auto-fix, no thinking required), and the plain `detekt` task (no type resolution). Google's new **Android CLI 1.0** (stable May 2026, `android studio analyze-file`) reroutes lint/inspection through a *running Android Studio instance*, bypassing Gradle entirely — Google claims >70% token reduction and 3x faster task completion vs. agents driving raw toolchains, largely because it returns structured JSON and a `--diff` mode instead of console logs. **Mid loop (30s–5min):** JVM unit tests (`testDebugUnitTest --tests`), Konsist architecture assertions (plain JUnit tests, no Gradle plugin — the standard way to enforce layering in Kotlin), Roborazzi/Paparazzi screenshot tests, `lintDebug`, `detektMain`/`detekt<Variant>` with type resolution. **CI only:** `buildHealth`, `dependencyGuard`, `assemble`, GMD/connected instrumentation, Maestro e2e, coverage, macrobenchmark.

For structured failure output, the durable formats are: **SARIF** (detekt, Android Lint via `sarifReport = true`, ktlint `--reporter=sarif`) — the one format that feeds both GitHub code scanning and reviewdog; **JUnit XML** at `build/test-results/<task>/TEST-*.xml`; **Checkstyle XML**; and tool-specific JSON (Roborazzi's `build/test-results/roborazzi/<variant>/results-summary.json` with a `{summary:{total,recorded,added,changed,unchanged}, results:[{type,golden_file_path,diff_percentage,...}]}` schema; DAGP writes advice as JSON). reviewdog is the standard glue for turning any of these into PR annotations (`-f=sarif -reporter=github-pr-review`).

The 2026 shift is toward MCP as the agent interface: the community `gradle-mcp` server exposes `gradle` + `query_build(kind=CONSOLE|TASKS|TESTS|FAILURES|PROBLEMS)` returning typed failures with auto-expanding detail, and Develocity ships an official MCP server (2025.3+) for build failure/flaky test analysis. Google's Lightbuild (trusted testers only) is a declarative YAML build config explicitly designed for agent parsing.

Biggest agent-loop traps: detekt 2.0 type resolution can explode from ~1min to ~24min on multi-module/KMP builds; Konsist has been unreleased since Dec 2024; dependency-guard since Feb 2024; Gradle's `--offline` fails hard on any unresolved dependency.

## KEY FACTS
### Kotlin compile is the cheapest high-signal oracle; module-scoped compile + incremental compilation is the inner-loop primitive
Kotlin incremental compilation is on by default for Kotlin/JVM (`kotlin.incremental=true`). KGP uses two classpath snapshot kinds: fine-grained (class member detail, recompiles only affected classes) and coarse-grained (class ABI hash only, recompiles all dependents). Default compiler execution strategy is `daemon`; alternatives are `in-process` and `out-of-process`. Kotlin daemon args via `kotlin.daemon.jvmargs=-Xmx1500m -Xms500m` (default `-XX:ReservedCodeCacheSize=320m`, `-XX:UseParallelGC`, `-ea`, `-Djava.awt.headless=true`). Gradle build cache for Kotlin tasks toggled with `kotlin.caching.enabled`. Errors emit as `file:line:column: error: <message>` — trivially regex-parseable, no extra config needed.
SRC: https://kotlinlang.org/docs/gradle-compilation-and-caches.html

### Google shipped Android CLI 1.0 (stable, May 2026) explicitly as an agent-facing oracle interface, claiming >70% token reduction and 3x faster task completion
Verbatim from the April 2026 announcement: Android CLI "improved project and environment setup by reducing LLM token usage by more than 70%" and "tasks were completed 3X faster than when agents attempted to navigate these tasks using only the standard toolsets." Described as "a lightweight interface for AI Agents to perform tasks and retrieve knowledge about Android development." Supported agents: Claude Code, OpenAI Codex, Gemini in Android Studio, Antigravity 2.0. Install via apt-get, winget (`winget install -e --id Google.AndroidCLI`), homebrew. Setup with `android init`. Version 0.7 was the April 2026 preview; 1.0 shipped at I/O May 2026.
SRC: https://android-developers.googleblog.com/2026/04/build-android-apps-3x-faster-using-any-agent.html

### `android studio analyze-file` gives agents IDE-quality lint/inspection results WITHOUT running Gradle — the single biggest inner-loop latency win available in 2026
`android studio analyze-file <path> [--pid=<pid>] [--project=<project>]` "Analyzes Kotlin/Java file for errors, warnings, lints using IDE's inspection engine" against a *running* Android Studio instance. Companion commands: `android studio check` (status of running Studio instances), `find-declaration`, `find-usages`, `render-compose-preview <path> <composable> [--print-semantics] [--output-image-file=]` (`--print-semantics` returns the accessibility semantics tree as JSON), `version-lookup`, `open-file`. Other JSON-emitting commands: `android layout [--pretty] [--output] [--diff]` (UI hierarchy as JSON; `--diff` returns only changed elements), `android describe [--project_dir=]` (project structure, build targets, output artifact paths as JSON), `android screen capture [--output] [--annotate]`, `android screen resolve --screenshot= --string=`. Persistent flags via `~/.androidrc`.
SRC: https://developer.android.com/tools/agents/android-cli

### detekt 2.0 changed the Gradle plugin ID from `io.gitlab.arturbosch.detekt` to `dev.detekt`; 2.0 is still alpha as of Aug 2026 while 1.23.8 is the last stable
Maven Central authoritative: `dev.detekt:detekt-cli` latest/release = 2.0.0-alpha.6, lastUpdated 20260804 (Aug 4 2026). `io.gitlab.arturbosch.detekt:detekt-cli` latest = 1.23.8, lastUpdated 20250221 (Feb 21 2025, built against Kotlin 2.0.21). 2.0.0-alpha.6 is built against Kotlin 2.4.10, Gradle 9.6.1, AGP 9.3.1, tested against JDK 25. New plugin block: `plugins { id("dev.detekt") version "2.0.0-alpha.6" }`. New extension option `failOnSeverity = dev.detekt.gradle.extensions.FailOnSeverity.Error`.
SRC: https://detekt.dev/docs/gettingstarted/gradle/

### detekt task taxonomy: `detekt` (fast, NO type resolution) vs `detektMain`/`detektTest`/`detekt<Variant>` (slow, WITH type resolution) — the agent inner loop should only ever run the former
Rules needing type resolution are annotated `@RequiresFullAnalysis` (e.g. `UnnecessarySafeCall`). Verbatim: "If you're running detekt without type resolution, all the rules that require type resolution will not run." The plain `detekt` task "doesn't have access to the types and symbols that are available to the compiler during the compilation." Type resolution requires `jvmTarget` and classpath on the task; on Android you must use `detekt<Variant>` tasks and cannot execute variant tasks simultaneously because classpaths differ. Other tasks: `detektGenerateConfig`, `detektBaseline`, `detektBaselineMain`, `detektBaselineTest`, `detektBaseline<Variant>`.
SRC: https://detekt.dev/docs/gettingstarted/type-resolution/

### detekt CLI (bypassing Gradle) has documented exit codes that let an agent distinguish 'findings' from 'tool broke' — Gradle cannot do this
Exit codes: 0 = no issues found; 1 = unexpected error; 2 = at least one issue detected; 3 = invalid configuration file. Flags: `--input/-i` (paths, ':'-separated on *nix), `--config/-c`, `--baseline/-b`, `--report/-r <report-id:path>` (checkstyle, html, md, sarif — combinable, e.g. `-r html:reports/detekt.html -r checkstyle:reports/detekt.xml`), `--auto-correct/-ac`, `--parallel`, `--build-upon-default-config`, `--classpath/-cp`, `--jvm-target` (default 1.8), `--excludes/-ex`.
SRC: https://detekt.dev/docs/gettingstarted/cli/

### detekt writes SARIF/checkstyle/HTML/Markdown and can merge SARIF across modules with a `ReportMergeTask` (needs Gradle 7.4+)
Default report locations `build/reports/detekt/detekt.[xml|html|md|sarif]`. SARIF is "a standard format for the output of static analysis tools" with "a defined schema", "currently supported by GitHub Code Scanning". Only Checkstyle and SARIF merging are supported across multi-module projects. Run merged: `./gradlew detekt reportMerge --continue`.
SRC: https://detekt.dev/docs/introduction/reporting/

### Android Lint supports SARIF output, and specifying `sarifOutput` implies `sarifReport = true`
`sarifReport` (true/false, default false) "determines whether lint should generate a SARIF report for use by, for example, GitHub"; location controlled by `sarifOutput`. Default path if unspecified: `<module>/build/reports/lint-results-<variant>.sarif`. Full DSL surface: abortOnError (default true), absolutePaths (default true), baseline (file), checkAllWarnings, checkDependencies, checkGeneratedSources, checkOnly, checkReleaseBuilds (default true), checkTestSources, disable, enable, error/fatal/warning/ignore/informational (issue-lists), explainIssues, htmlReport/htmlOutput, ignoreTestSources, ignoreWarnings, lintConfig, noLines (default false), quiet, showAll, textReport/textOutput (file/stdout/stderr), warningsAsErrors, xmlReport/xmlOutput. SARIF support landed in AGP 4.2.0.
SRC: https://googlesamples.github.io/android-custom-lint-rules/usage/agp-dsl.md.html

### Android Lint task names and baseline mechanics
Tasks: `lint`, `lintDebug`, `lintRelease`, `lint<Variant>`, `updateLintBaseline`, `lintFix`. Default outputs: `build/reports/lint-results-debug.html`, `build/reports/lint-results-debug.xml`. Baseline: `lint { baseline = file("lint-baseline.xml") }` — records all current issues on first run, then reports only new ones; must be manually deleted to recreate (or use `updateLintBaseline`). Regenerate with `./gradlew lintDebug -Dlint.baselines.continue=true`.
SRC: https://developer.android.com/studio/write/lint

### Konsist is the de-facto Kotlin layering/naming oracle — it is plain JUnit/Kotest tests, NOT a Gradle plugin, so it runs at unit-test speed inside `testDebugUnitTest`
`testImplementation("com.lemonappdev:konsist:0.17.3")`. "Konsist guards are written in the form of unit tests (JUnit / Kotest)." Two check types: declaration checks and architectural checks. Integrates with JUnit4, JUnit5 and Kotest. Scope APIs seen in docs: `Konsist.scopeFromProject()`, `Konsist.scopeFromProduction()`, `Konsist.scopeFromModule("featureX")`; scopes compose with `+` because KoScope overrides `plus`/`plusAssign`. Layer API: `Layer(name, packagePattern)`, `dependsOn(x)` (strict=false default), `dependsOn(x, strict = true)`, `dependsOnNothing()`, `doesNotDependOn()`, `include`. Architecture blocks are reusable via `val architecture = architecture { ... }` then `scope.assertArchitecture(architecture)`.
SRC: https://raw.githubusercontent.com/LemonAppDev/konsist/main/README.md

### Konsist has had NO release since 0.17.3 on 8 Dec 2024 — roughly 20 months stale as of Aug 2026
Authoritative Maven Central metadata for com.lemonappdev:konsist: 29 total versions, latest/release = 0.17.3, `<lastUpdated>20241208194313</lastUpdated>`. Version history: 0.17.0 (Nov 25 2024, generic type support, source declarations API), 0.17.1 (added `strict` parameter to layer dependencies), 0.17.2, 0.17.3 (layer package convention naming). Project won the Kotlin Foundation Grants Program 2024.
SRC: https://repo1.maven.org/maven2/com/lemonappdev/konsist/maven-metadata.xml

### Roborazzi emits a fully-specified JSON result file that an agent can parse directly — the best machine-readable screenshot oracle
Paths from `RoborazziReportConst`: summary at `build/test-results/roborazzi/<variant>/results-summary.json`, per-capture JSON in `build/test-results/roborazzi/<variant>/results/`, HTML at `build/reports/roborazzi/<variant>/index.html`. Schema: `CaptureResults(summary: ResultSummary, results: List<CaptureResult>)` where `ResultSummary(total, recorded, added, changed, unchanged)` and `CaptureResult` is a sealed interface with `type` ∈ {"recorded","added","changed","unchanged"} and SerialNames `golden_file_path`, `actual_file_path`, `compare_file_path`, `timestamp`, `context_data`, plus `diff_percentage: Float?` and `ai_assertion_results` on Changed/Added.
SRC: https://raw.githubusercontent.com/takahirom/roborazzi/main/include-build/roborazzi-core/src/commonMain/kotlin/com/github/takahirom/roborazzi/CaptureResult.kt

### Roborazzi tasks, property switches, and its own agent-skill distribution
Plugin id `io.github.takahirom.roborazzi`; latest 1.72.0 (Maven Central, 13 Aug 2026). Tasks: `recordRoborazziDebug`, `verifyRoborazziDebug`, `compareRoborazziDebug`, `verifyAndRecordRoborazziDebug`, `clearRoborazziDebug` (experimental). Properties: `-Proborazzi.test.record=true`, `-Proborazzi.test.verify=true`, `-Proborazzi.test.compare=true`, `roborazzi.record.resizeScale`, `roborazzi.record.namingStrategy`, `roborazzi.dumpUiTree=true` (machine-readable JSON sidecars `MyTest.uitree.json` / `MyTest_actual.uitree.json`), `roborazzi.cleanupOldScreenshots=true`. Ships its docs as an installable agent skill: `npx skills add takahirom/roborazzi`. Optional AI assertion modules `roborazzi-ai-gemini` / `roborazzi-ai-openai` with a custom `AiAssertionModel` interface.
SRC: https://raw.githubusercontent.com/takahirom/roborazzi/main/README.md

### Paparazzi is at 2.0.0-alpha05 (May 2026) — the LayoutLib-based alternative, single-frame only, no Activity/Fragment/interaction support
Plugin id `app.cash.paparazzi`, latest 2.0.0-alpha05 (Maven Central, 20 May 2026). Tasks: `recordPaparazziDebug` ("Saves snapshots as golden values to a predefined source-controlled location"), `verifyPaparazziDebug` ("Runs tests and verifies against previously-recorded golden values"). Golden snapshots default to `src/test/snapshots`; test reports `build/reports/paparazzi/`; failure diffs `build/paparazzi/failures`. README recommends Git LFS for snapshot PNGs.
SRC: https://raw.githubusercontent.com/cashapp/paparazzi/master/README.md

### Google's Compose Preview Screenshot Testing is still alpha after ~2 years (0.0.1-alpha16 as of Aug 2026) and now requires AGP 9.0+
Plugin id `com.android.compose.screenshot`, version 0.0.1-alpha15 documented, 0.0.1-alpha16 latest on Google Maven. Requires `android.experimental.enableScreenshotTest=true` in gradle.properties AND `android { experimentalProperties["android.experimental.enableScreenshotTest"] = true }`. Tasks: `./gradlew :{module}:update{Variant}ScreenshotTest` and `./gradlew :{module}:validate{Variant}ScreenshotTest`. Reference images at `{module}/src/screenshotTest{Variant}/reference/` named `<fqName>_<hash>_<hash>_0.png`. HTML report at `{module}/build/reports/screenshotTest/preview/{variant}/index.html`. Requires AGP 9.0+ (8.5.0 minimum for Gradle tasks only), Kotlin 2.2.10+, JDK 17+. "Experimental/Alpha phase — features and APIs are subject to change substantially."
SRC: https://developer.android.com/studio/preview/compose-screenshot-testing

### Spotless 8.9.0 (July 2026) has full configuration-cache support since 7.0 and `ratchetFrom` for git-diff-scoped formatting
`com.diffplug.spotless:spotless-plugin-gradle` latest 8.9.0, updated 20260727. Tasks: `spotlessCheck`, `spotlessApply`, plus per-format `spotlessKotlinCheck`/`spotlessKotlinApply`. `spotless { ratchetFrom 'origin/main' }` formats/checks only files changed since that git ref — the key speed lever for an agent loop. Spotless 7.0 provides "full, no-asterisk support for configuration cache"; 7.0.0 bumped default ktlint to 1.5.0 and default ktfmt to 0.53. Known caveat: JGit's access to `.git/HEAD` and `.git/config` has historically caused configuration-cache misses on branch switches.
SRC: https://raw.githubusercontent.com/diffplug/spotless/main/plugin-gradle/README.md

### ktlint 1.8.0 is current (Dec 2025); the CLI supports json/sarif/checkstyle reporters and a baseline
Authoritative Maven Central: com.pinterest.ktlint:ktlint-cli latest/release = 1.8.0, `<lastUpdated>20251215204517</lastUpdated>`. Built-in reporters: plain (default), plain_summary, json, sarif, checkstyle, html. Flags: `-F/--format` (fix deviations), `--baseline=<baselinePath>`, `--editorconfig=<path>`, `--disabled_rules=<list>`, reporter output redirection via `--reporter=<name>,output=<file>`. 1.8.0 added `--ignore-autocorrect-failures`. ktfmt is at 0.64 (Jun 2026).
SRC: https://repo1.maven.org/maven2/com/pinterest/ktlint/ktlint-cli/maven-metadata.xml

### compose-rules (io.nlopez.compose.rules) 0.6.4 is the actively-maintained Compose lint ruleset for BOTH ktlint and detekt (the old com.twitter.compose.rules is dead since Nov 2022)
`io.nlopez.compose.rules:ktlint` and `io.nlopez.compose.rules:detekt` both at 0.6.4, updated 20260805. Described as "a set of custom ktlint / detekt rules to ensure that your composables don't fall into common pitfalls that might be easy to miss in code reviews." `com.twitter.compose.rules:ktlint` last published 0.0.26 on 20221121. Wires into Spotless via `ktlint("1.x").customRuleSets(listOf("io.nlopez.compose.rules:ktlint:0.6.4"))`.
SRC: https://mrmans0n.github.io/compose-rules/latest/

### dependency-analysis-gradle-plugin (build-health) 3.18.0 writes advice to disk as JSON specifically for automation
Plugin ids `com.autonomousapps.dependency-analysis` (project) and `com.autonomousapps.build-health` (settings/global). Latest 3.18.0 (Maven Central, 27 Jul 2026). Tasks: `./gradlew buildHealth`, `./gradlew :app:projectHealth`, `./gradlew fixDependencies` (auto-remediate). Report at `build/reports/dependency-analysis/build-health-report.txt`; console output via `printBuildHealth(true)`. Verbatim: buildHealth "Prints that advice to disk as JSON for advanced users who want to automate post-processing the results." Advice JSON fields: dependency identifier/resolvedVersion/declared configuration, `fromConfiguration` (null if transitive), `toConfiguration` (null if removal advised), `usedTransitiveDependencies`, `parents`. Severity DSL: `issues { all { onUnusedDependencies { severity("fail"|"warn"|"ignore") } } }` plus onUsedTransitiveDependencies, onIncorrectConfiguration, onCompileOnly, onRuntimeOnly, onUnusedAnnotationProcessors, onRedundantPlugins.
SRC: https://github.com/autonomousapps/dependency-analysis-gradle-plugin

### The DAGP maintainer adopted a Strict No LLM / No AI policy in the project Code of Conduct after AI-generated PRs caused real defects
Reported in the May 2026 Gradle newsletter: Tony Robalik documented three incidents including "an AI-generated ClassCastException misdiagnosis that got nearly every claim wrong" and "a path-sensitivity PR that would have caused stochastic build failures" for remote-cache users. Relevant context for agents contributing upstream to build tooling.
SRC: https://newsletter.gradle.org/2026/05

### dependency-guard is a text-diff oracle for transitive dependency drift but has not been released since Feb 2024
`com.dropbox.dependency-guard:dependency-guard` latest 0.5.0, `updated=20240205180750`. Plugin: `id("com.dropbox.dependency-guard") version "0.5.0"`. Tasks: `dependencyGuard` ("Compare against the configured transitive dependency report baselines, or generate them if they don't exist") and `dependencyGuardBaseline` ("overwrites the dependencies in the `dependencies` directory in your module"). Baselines at `<module>/dependencies/${configurationName}.txt` (and `.tree.txt`). Failure output is a human-readable added/removed diff — parseable but not structured.
SRC: https://raw.githubusercontent.com/dropbox/dependency-guard/main/README.md

### modules-graph-assert 2.9.1 (Apr 2026) enforces module-graph shape declaratively — cheap and fast because it only reads the dependency graph, not source
`id "com.jraska.module.graph.assertion" version "2.9.1"` (Gradle Plugin Portal marker updated 20260412). DSL: `maxHeight` (int), `allowed` (array of `'regex -> regex'`), `restricted` (array of `'regex -X> regex'`), `configurations` (defaults to `['api','implementation']`), `assertOnAnyBuild` (runs on every build without explicit task invocation). Tasks: `assertModuleGraph`, `generateModulesGraphvizText`, `generateModulesGraphStatistics` (module count, edges, height, longest path).
SRC: https://github.com/jraska/modules-graph-assert

### Gradle writes JUnit XML per test task at a predictable path — the single most portable machine-readable test oracle
XML results at `build/test-results/test/` (one file per test class, `TEST-*.xml`); HTML at `build/reports/tests/test/`. For Android variants the task is `testDebugUnitTest` → `build/test-results/testDebugUnitTest/`. Overridable via `tasks.test { reports { junitXml.outputLocation = layout.buildDirectory.dir("test-junit-xml") } }`. Filtering: `./gradlew test --tests SomeTestClass`, `--tests org.gradle.SomeTestClass.someSpecificMethod`, `--tests '*IntegTest'`; patterns starting uppercase are treated as simple class names. JUnit 5 via `useJUnitPlatform()`.
SRC: https://docs.gradle.org/current/userguide/java_testing.html

### Gradle CLI flags that matter for an agent loop
`--offline` (no network), `--build-cache`/`--no-build-cache`, `--configuration-cache`/`--no-configuration-cache`, `--continue` ("Continue task execution after a task failure" — essential so an agent gets ALL failures in one pass, not just the first), `--parallel`, `--max-workers`, `-q/--quiet`, `--console=plain` (mandatory for agents: strips ANSI/rich progress), `--rerun-tasks`, `-m/--dry-run`, `-x/--exclude-task`, `--tests`, `--scan`, `-s/--stacktrace`, `--no-daemon`.
SRC: https://docs.gradle.org/current/userguide/command_line_interface.html

### Gradle 9.7.0 is current (6 Aug 2026); configuration cache is opt-in but becomes default in Gradle 10
services.gradle.org/versions/current: version 9.7.0, buildTime 20260806. Configuration cache enabled via `org.gradle.configuration-cache=true`, `--configuration-cache`, or `-Dorg.gradle.configuration-cache=true`. Problems downgraded to warnings with `--configuration-cache-problems=warn` / `-Dorg.gradle.configuration-cache.problems=warn`. HTML diagnostics at `build/reports/configuration-cache/<timestamp>/configuration-cache-report.html`. "This feature will be enabled by default in Gradle 10"; described as "the preferred mode of execution" since 9.0.0. Gradle 9.x also emits `build/reports/problems/problems-report.html` (incubating Problems API).
SRC: https://docs.gradle.org/current/userguide/configuration_cache.html

### Kover 0.9.9 (Jul 2026) is the Kotlin-native coverage oracle with programmable verification bounds
Plugin id `org.jetbrains.kotlinx.kover`, latest 0.9.9 (Maven Central, 17 Jul 2026). Tasks: `koverHtmlReport`, `koverXmlReport` (JaCoCo-compatible XML — parseable), `koverVerify`, `koverLog` (prints metrics to console), `koverBinaryReport`. Verify DSL: `kover { reports { verify { rule { minBound(50) } } } }`. Coverage units: LINE (default), BRANCH, INSTRUCTION. Aggregation: COVERED_PERCENTAGE (default), MISSED_PERCENTAGE, COVERED_COUNT, MISSED_COUNT. Grouping: APPLICATION, CLASS, PACKAGE. Multi-module aggregation via `dependencies { kover(project(":moduleA")) }`. An experimental Kover Aggregated Settings plugin exists but is "recommended only for testing".
SRC: https://kotlin.github.io/kotlinx-kover/gradle-plugin/

### binary-compatibility-validator is in maintenance mode; the Kotlin Gradle plugin now has built-in ABI validation with `checkLegacyAbi`/`updateLegacyAbi`
`org.jetbrains.kotlinx:binary-compatibility-validator` latest 0.18.1 (9 Jul 2025). Verbatim: the project is "in maintenance mode" with new features redirected toward "the experimental binary compatibility validation in the Kotlin Gradle plugin." Legacy tasks `apiDump`, `apiCheck`, `apiBuild`; dumps in `api/` (or `api/jvm`, `api/android` for MPP; `<project>.klib.api` for klibs). Options: ignoredPackages, ignoredClasses, nonPublicMarkers, ignoredProjects, validationDisabled, klib.enabled. KGP replacement: `kotlin { @OptIn(org.jetbrains.kotlin.gradle.dsl.abi.ExperimentalAbiValidation::class) abiValidation { enabled.set(true) } }`, then `./gradlew checkLegacyAbi` (generates ABI dump as UTF-8 text, diffs against reference, reports differences as errors) and `./gradlew updateLegacyAbi` (writes the `api/` folder). Stabilization tracked in KT-71172. Note: relevant to libraries, largely irrelevant to app modules.
SRC: https://kotlinlang.org/docs/gradle-binary-compatibility-validation.html

### Gradle Managed Devices give reproducible emulator runs with deterministic task names, but ATD images are API 30-only and cannot do screenshots
DSL under `android { testOptions { managedDevices { localDevices { create("pixel2api30") { device = "Pixel 2"; apiLevel = 30; systemImageSource = "aosp" } } ; groups { create("phoneAndTablet") { targetDevices.add(devices["pixel2api29"]) } } } } }`. Task naming: `{deviceName}{BuildVariant}AndroidTest` (e.g. `pixel2api30DebugAndroidTest`) and `{groupName}Group{BuildVariant}AndroidTest`. apiLevel must be ≥27. ATD images (`aosp-atd`/`google-atd`) "currently support only API level 30" and "Hardware rendering is disabled (screenshot tests not supported)". Sharding: `android.experimental.androidTest.numManagedDeviceShards=<n>` in gradle.properties — outputs results in `.proto` files per shard. Headless CI: `-Pandroid.testoptions.manageddevices.emulator.gpu=swiftshader_indirect`.
SRC: https://developer.android.com/studio/test/gradle-managed-devices

### Maestro CLI emits JUnit XML — the machine-readable hook for e2e in an agent loop
`maestro test` flags: `--format=<JUNIT|HTML|NOOP>` (default NOOP), `--output=<dest>`, `--shard-split=<n>` ("Run the tests across N connected devices, splitting tests evenly"), `--shard-all=<n>`, `--include-tags=<list>`, `--exclude-tags=<list>`, `-e/--env=<K=V>`, `-c/--continuous`, `--debug-output=<path>`, `--headless` (web only), `--analyze` ("[Beta] Enhance the test output analysis with AI Insights"). `maestro start-device` flags: `--platform=<android|ios|web>`, `--device-model`, `--device-os`, `--device-locale`, `--force-create`.
SRC: https://docs.maestro.dev/maestro-cli/maestro-cli-commands-and-options.md

### reviewdog is the standard adapter turning SARIF/checkstyle output into PR annotations
Input formats: errorformat (Vim-style, e.g. `%f:%l:%c: %m`), checkstyle XML, SARIF 2.1.0 JSON, rdjson/rdjsonl (Reviewdog Diagnostic Format — supports multiline comments, severity, and code suggestions), and unified diff (for formatters/fixers). Reporters: `local` (default, filters by diff), `github-pr-review`, `github-pr-check`, `github-check`, `github-annotations`, `gitlab-mr-discussion`, `bitbucket-code-report`. Filter modes: `added` (default), `diff_context`, `file`, `nofilter`. Pre-defined errorformats listed via `reviewdog -list`. Config in `.reviewdog.yml`.
SRC: https://raw.githubusercontent.com/reviewdog/reviewdog/master/README.md

### danger-kotlin 1.3.4 is the Kotlin-scripted PR-policy oracle
Dangerfile written as `Dangerfile.df.kts`. Commands: `danger-kotlin ci`, `danger-kotlin local`, `danger-kotlin pr [URL]`. Install: `brew install danger/tap/danger-kotlin`, a Linux bash script, a GitHub Action, or docker `ghcr.io/danger/danger-kotlin:1.3.4 danger-kotlin local`. Marked stable; ~541 stars.
SRC: https://github.com/danger/kotlin

### Turbine 1.2.1 uses wall-clock timeouts independent of runTest's virtual time — a subtle source of agent-confusing flakes
`app.cash.turbine:turbine:1.2.1` (Maven Central, 11 Jun 2025). API: `flow.test { }`, `awaitItem()`, `awaitComplete()`, `awaitError()`, `cancelAndIgnoreRemainingEvents()`, `turbineScope { }`, `testIn(scope)`. Verbatim: Turbine applies wall-clock timeouts (default 3 seconds) when awaiting events, independent of `runTest`'s virtual time; override via `test(timeout = ...)`, `testIn(timeout = ...)`, `Turbine(timeout = ...)`, or globally `withTurbineTimeout()`. It depends on the unstable `UnconfinedTestDispatcher` API: "Without this usage of Turbine with runTest would break."
SRC: https://raw.githubusercontent.com/cashapp/turbine/trunk/README.md

### Robolectric must be forced offline in a hermetic agent loop or it will silently fetch Android SDK jars at first test run
System properties: `robolectric.offline` ("Disables runtime jar fetching", default false), `robolectric.dependency.dir` (folder containing offline dependencies), `robolectric.dependency.repo.url`, `robolectric.dependency.repo.id`, `robolectric.logging.enabled`, `robolectric.dependency.proxy.host/port` (4.9.1+). Set from Gradle via `android.testOptions.unitTests.all { systemProperty "robolectric.offline", "true" }`. Config precedence: `@Config` annotation > `robolectric.properties` in `src/test/resources` (deeper packages override shallower) > `GlobalConfigProvider`. `@Config` params: sdk, application, qualifiers, minSdk/maxSdk (cannot combine with sdk). Latest Robolectric on Maven Central is 4.17-beta-2 (18 Jul 2026).
SRC: https://robolectric.org/configuring/

### Baseline profile generation is a GMD-driven Gradle task, and macrobenchmark emits JSON results
Plugin `androidx.baselineprofile` (androidx.benchmark 1.5.0-rc01 line as of Aug 2026). Tasks: `:app:generateBaselineProfile`, `:app:generate<Variant>BaselineProfile` (e.g. `generateReleaseBaselineProfile`). Output: `app/src/<variant>/generated/baselineProfiles/baseline-prof.txt`. DSL: `baselineProfile { managedDevices += "pixel6Api31"; useConnectedDevices = false }`. GMD must use `systemImageSource = "aosp"` for root, or API 33+ without root. Verify via `./gradlew :baseline-profile:connectedCheck`; benchmark results are output in JSON format.
SRC: https://developer.android.com/topic/performance/baselineprofiles/create-baselineprofile

### A community MCP server (rnett/gradle-mcp) exposes Gradle to agents with a typed failure-query API — this is the current state of the art for structured build feedback
Requires JDK 21+. Run: `jbang run --quiet --fresh gradle-mcp@rnett`. Key tools: `gradle` ("`./gradlew` replacement", params projectRoot, commandLine, background, stopBuildId, captureTaskOutput, invocationArguments{additionalEnvVars, additionalSystemProps, additionalJvmArgs, publishScan, envSource ∈ NONE|INHERIT|SHELL, javaHome}) and `query_build(buildId, kind, query)` with kinds CONSOLE (regex filter on logs), TASKS (prefix filter on task path), TESTS (prefix filter on test name), FAILURES (query = exact FailureId), PROBLEMS (compilation/configuration problems, query = exact ProblemId), DASHBOARD. "If a query for TASKS, TESTS, FAILURES, or PROBLEMS matches exactly one item, it auto-expands to full details. Otherwise, it returns a summary list with a hint to refine the query." Also `wait_build`. Ships built-in Agent Skills: using-gradle, authoring-gradle-builds, advanced-gradle-dependencies, interacting-with-project-runtime, verifying-compose-ui. Explicitly "Token Optimized: Compact data formats designed to keep context usage low."
SRC: https://raw.githubusercontent.com/rnett/gradle-mcp/main/docs/tools/LOOKUP_TOOLS.md

### Develocity ships two official MCP servers for build-failure and flaky-test analysis
Develocity MCP Server "gives an AI client direct access to build context: exception details, stack traces, test outcomes, cache performance, and more" — requires Develocity 2025.3+. Develocity Analytics MCP Server "gives an AI client access to aggregate build data across your organization" — requires Develocity 2025.4+ with Athena Data Export or Reporting Kit 2.1+. Uses Develocity's failure grouping to identify root causes and common failure patterns; can identify flaky tests and analyze test performance. Docker image published as `gradle/develocity-mcp-server`. Was under a Limited Availability program.
SRC: https://docs.develocity.ai/2026.1/integrations/mcp-servers/

### Google's Android Skills repo is the official agent-instruction library, installed via Android CLI
github.com/android/skills (Apache 2.0, ~6.8k stars, "Public contributions are not accepted at this time"). Top-level dirs: build-system, camera, device-ai, devtools (android-cli), identity, jetpack-compose, media, navigation, performance (R8 analyzer), play, profilers, security, system, testing (testing-setup), tv, wear, xr — plus `.agents/`, `.claude-plugin/`, `.codex-plugin/`. Install: `android skills add --skill=r8-analyzer --project=.`; options `--all`, `--agent`, `--project`. Follows the agentskills.io open standard. Other CLI skill commands: `android skills list`, `android skills find`, `android skills remove`.
SRC: https://github.com/android/skills

### Google's Lightbuild is a declarative YAML build config explicitly designed for AI-agent parsing, currently trusted-testers only
Verbatim: "Lightbuild provides a declarative abstraction on top of imperative build systems... When you run your project's build, Lightbuild converts your declarative config files to another build system, such as Gradle." And: "Lightbuild's YAML-based build config files are designed to enable AI agents to more efficiently parse your build config, update dependencies, and edit modules, all under your control." Will become a third option alongside Kotlin DSL and Groovy DSL in new-project creation. "Lightbuild is currently available only to a select group of trusted testers."
SRC: https://developer.android.com/tools/agents/lightbuild

### Current authoritative tool versions as of Aug 2026 (fetched from Maven Central / Google Maven / services.gradle.org)
Gradle 9.7.0 (6 Aug 2026). AGP stable 9.3.1; latest alpha 9.4.0-alpha08. Android Lint gradle 32.4.0-alpha08 line. detekt 1.23.8 stable / 2.0.0-alpha.6. ktlint-cli 1.8.0. ktfmt 0.64. Spotless gradle plugin 8.9.0. Konsist 0.17.3 (STALE, Dec 2024). Roborazzi 1.72.0. Paparazzi 2.0.0-alpha05. compose screenshot plugin 0.0.1-alpha16. Robolectric 4.17-beta-2. MockK 1.14.11. Turbine 1.2.1. kotlinx-coroutines-test 1.11.0. JUnit Jupiter 6.1.3. android-junit5 (de.mannodermaus) 2.0.1. Kover 0.9.9. binary-compatibility-validator 0.18.1. DAGP 3.18.0. dependency-guard 0.5.0 (STALE, Feb 2024). modules-graph-assert 2.9.1. androidx.benchmark/baselineprofile 1.5.0-rc01. compose ui-test-junit4 1.12.0. metalava 1.0.0-alpha15. compose-rules 0.6.4.
SRC: https://services.gradle.org/versions/current

### Now in Android's CI is the canonical reference ordering for Android verification tasks
Actual order in android/nowinandroid .github/workflows/Build.yaml on JDK 21 with gradle/actions/setup-gradle@v4: `:build-logic:convention:check` → `spotlessCheck` → `dependencyGuard` (with `dependencyGuardBaseline` auto-regen + auto-commit on PR failure) → `graphUpdate` (then `git diff --cached --quiet --exit-code -- "**/README.md"` to assert graphs are current) → `verifyRoborazziDemoDebug` (with `recordRoborazziDemoDebug` auto-regen on PR) → `testDemoDebug :lint:test` → `:app:assemble -PminifyWithR8=false` → `:app:lintProdRelease :app-nia-catalog:lintRelease :lint:lint` → SARIF uploaded per-module via `github/codeql-action/upload-sarif@v3` → `:app:checkProdReleaseBadging`. Separate matrix job: `connectedDemoDebugAndroidTest --daemon` via reactivecircus/android-emulator-runner@v2, then `testDemoDebugUnitTest -Proborazzi.test.verify=false` and `createDemoDebugCombinedCoverageReport`.
SRC: https://raw.githubusercontent.com/android/nowinandroid/main/.github/workflows/Build.yaml

## EXAMPLES
### Agent inner-loop Gradle invocation template — plain console, all failures at once, offline, no network stalls
FILE: run from repo root
```
# Fastest useful oracle. Scope to the module you touched.
./gradlew :feature:profile:compileDevelopDebugKotlin \
  --offline \
  --console=plain \
  --configuration-cache \
  --build-cache \
  --continue \
  -q

# Errors arrive as:  /abs/path/Foo.kt:42:17 error: type mismatch: inferred type is String but Int was expected
# Regex for an agent:  ^(?<file>[^:]+\.kts?):(?<line>\d+):(?<col>\d+):?\s+(?<sev>error|warning):\s+(?<msg>.*)$
```
SRC: https://docs.gradle.org/current/userguide/command_line_interface.html

### detekt Gradle config emitting SARIF + checkstyle, with baseline, for agent/CI parsing
FILE: build.gradle.kts (root or convention plugin)
```
plugins { id("dev.detekt") version "2.0.0-alpha.6" }   // 1.x: id("io.gitlab.arturbosch.detekt") version "1.23.8"

detekt {
    toolVersion = "2.0.0-alpha.6"
    parallel = true
    buildUponDefaultConfig = true
    config.setFrom("$rootDir/config/detekt/detekt.yml")
    baseline = file("$rootDir/config/detekt/baseline.xml")
    ignoreFailures = false
    failOnSeverity = dev.detekt.gradle.extensions.FailOnSeverity.Error
    basePath = rootProject.projectDir   // makes SARIF paths repo-relative
}

tasks.withType<dev.detekt.gradle.Detekt>().configureEach {
    reports {
        sarif.required.set(true)
        sarif.outputLocation.set(file("build/reports/detekt/detekt.sarif"))
        checkstyle.required.set(true)
        html.required.set(false)   // agents don't read HTML — turn it off, it costs time
        md.required.set(false)
    }
}
```
SRC: https://detekt.dev/docs/gettingstarted/gradle/

### Merging detekt SARIF across a multi-module build into one file an agent can read
FILE: root build.gradle.kts
```
val reportMerge by tasks.registering(dev.detekt.gradle.report.ReportMergeTask::class) {
   output.set(rootProject.layout.buildDirectory.file("reports/detekt/merge.sarif"))
}
subprojects {
  detekt { reports.sarif.required.set(true) }
  reportMerge {
    input.from(tasks.withType<dev.detekt.gradle.Detekt>().map { it.reports.sarif.outputLocation })
  }
}

// ./gradlew detekt reportMerge --continue      (requires Gradle 7.4+)
```
SRC: https://detekt.dev/docs/introduction/reporting/

### detekt CLI run bypassing Gradle entirely — distinguishable exit codes, sub-second startup on a small file set
FILE: detekt-cli distribution on PATH
```
detekt \
  --input feature/profile/src/main/kotlin \
  --config config/detekt/detekt.yml \
  --baseline config/detekt/baseline.xml \
  --build-upon-default-config \
  --parallel \
  --report sarif:build/detekt.sarif \
  --report checkstyle:build/detekt.xml

# exit 0 = clean | 1 = tool error | 2 = findings | 3 = bad config
# add --auto-correct to let formatting rules fix in place
```
SRC: https://detekt.dev/docs/gettingstarted/cli/

### Android Lint block configured for machine consumption + baseline
FILE: app/build.gradle.kts
```
android {
  lint {
    baseline = file("lint-baseline.xml")
    checkDependencies = true      // beware: much slower, CI-only
    abortOnError = true
    warningsAsErrors = false
    absolutePaths = false         // repo-relative paths in reports
    sarifReport = true            // or just set sarifOutput, which implies this
    sarifOutput = file("build/reports/lint-results.sarif")
    xmlReport = true
    htmlReport = false            // skip: pure cost for an agent
    textReport = true
    textOutput = file("stdout")
  }
}

// ./gradlew :app:lintDebug
// ./gradlew :app:updateLintBaseline     (regenerate baseline)
// ./gradlew lintFix                     (apply safe autofixes)
```
SRC: https://googlesamples.github.io/android-custom-lint-rules/usage/agp-dsl.md.html

### Konsist layering assertion — the recommended way to enforce Clean Architecture module boundaries at unit-test speed
FILE: app/src/test/kotlin/ArchitectureTest.kt (or a dedicated :konsist test module)
```
// libs.versions.toml -> konsist = "0.17.3"
// testImplementation("com.lemonappdev:konsist:0.17.3")

private val architecture = architecture {
    val domain       = Layer("Domain",       "com.kkday.domain..")
    val data         = Layer("Data",         "com.kkday.data..")
    val presentation = Layer("Presentation", "com.kkday.ui..")

    domain.dependsOnNothing()
    presentation.dependsOn(domain)
    data.dependsOn(domain)
}

class ArchitectureTest {
    @Test
    fun `clean architecture layers have correct dependencies`() {
        Konsist.scopeFromProduction().assertArchitecture(architecture)
    }

    @Test
    fun `classes with 'UseCase' suffix should reside in 'usecase' package`() {
        Konsist.scopeFromProject()
            .classes()
            .withNameEndingWith("UseCase")
            .assertTrue { it.resideInPackage("..usecase..") }
    }
}

// strict mode: presentation.dependsOn(domain, strict = true)  // REQUIRES the dependency to exist
// scopes compose:  val refactored = moduleAScope + moduleBScope
```
SRC: https://raw.githubusercontent.com/LemonAppDev/konsist/main/README.md

### Konsist Android-specific rules straight from the official snippet library (naming, logging ban, Compose preview naming)
FILE: src/test/kotlin/**/KonsistTest.kt
```
@Test
fun `classes extending 'ViewModel' should have 'ViewModel' suffix`() {
    Konsist.scopeFromProject().classes()
        .withParentClassOf(ViewModel::class)
        .assertTrue { it.name.endsWith("ViewModel") }
}

@Test
fun `Every 'ViewModel' public property has 'Flow' type`() {
    Konsist.scopeFromProject().classes()
        .withParentClassOf(ViewModel::class)
        .properties()
        .assertTrue {
            it.hasPublicOrDefaultModifier &&
              it.hasType { type -> type.name == "kotlinx.coroutines.flow.Flow" }
        }
}

@Test
fun `no class should use Android util logging`() {
    Konsist.scopeFromProject().files
        .assertFalse { it.hasImport { import -> import.name == "android.util.Log" } }
}

@Test
fun `All JetPack Compose previews contain 'Preview' in method name`() {
    Konsist.scopeFromProject().functions()
        .withAnnotationOf(Preview::class)
        .assertTrue { it.hasNameContaining("Preview") }
}
```
SRC: https://docs.konsist.lemonappdev.com/inspiration/snippets/android-snippets.md

### Spotless with ktlint + compose-rules + ratchetFrom (only formats files changed vs main — the key inner-loop speed lever)
FILE: build.gradle.kts
```
spotless {
  ratchetFrom = "origin/develop"        // only touch files changed since this ref
  kotlin {
    target("**/*.kt")
    targetExclude("**/build/**")
    ktlint("1.8.0")
      .setEditorConfigPath("$rootDir/.editorconfig")
      .editorConfigOverride(mapOf("indent_size" to "4"))
      .customRuleSets(listOf("io.nlopez.compose.rules:ktlint:0.6.4"))
  }
  kotlinGradle {
    target("*.gradle.kts")
    ktlint("1.8.0")
  }
}

// ./gradlew spotlessApply        <- agent should ALWAYS run this, never reason about formatting
// ./gradlew spotlessCheck        <- CI gate
// ./gradlew :app:spotlessKotlinApply   <- module-scoped
```
SRC: https://raw.githubusercontent.com/diffplug/spotless/main/plugin-gradle/README.md

### Spotless with ktfmt instead of ktlint (fewer knobs, faster, no rule config to argue about)
FILE: build.gradle.kts
```
spotless {
  kotlin {
    ktfmt("0.64").googleStyle().configure {
      it.setMaxWidth(100)
      it.setBlockIndent(4)
    }
    licenseHeader '/* (C)$YEAR */'
  }
}
```
SRC: https://raw.githubusercontent.com/diffplug/spotless/main/plugin-gradle/README.md

### Roborazzi screenshot verification + parsing the JSON result in an agent loop
FILE: build/test-results/roborazzi/<variant>/results-summary.json
```
# record baselines
./gradlew :feature:profile:recordRoborazziDevelopDebug
# verify (fails on diff)
./gradlew :feature:profile:verifyRoborazziDevelopDebug
# or run the test task with a property switch:
./gradlew :feature:profile:testDevelopDebugUnitTest -Proborazzi.test.verify=true

# Agent reads this, NOT the console:
jq '.summary, (.results[] | select(.type=="changed") | {golden_file_path, diff_percentage, compare_file_path})' \
  feature/profile/build/test-results/roborazzi/developDebug/results-summary.json

# Schema:
# { "summary": {"total":N,"recorded":N,"added":N,"changed":N,"unchanged":N},
#   "results": [ {"type":"changed","golden_file_path":"...","actual_file_path":"...",
#                 "compare_file_path":"...","timestamp":123,"diff_percentage":0.42,
#                 "ai_assertion_results":null,"context_data":{}} ] }
```
SRC: https://raw.githubusercontent.com/takahirom/roborazzi/main/include-build/roborazzi-core/src/commonMain/kotlin/com/github/takahirom/roborazzi/CaptureResult.kt

### Compose Preview Screenshot Testing (Google, alpha) wiring
FILE: module build.gradle.kts + gradle.properties
```
# gradle.properties
android.experimental.enableScreenshotTest=true

# libs.versions.toml
[versions]
screenshot = "0.0.1-alpha16"
[plugins]
screenshot = { id = "com.android.compose.screenshot", version.ref = "screenshot" }

# module build.gradle.kts
plugins { alias(libs.plugins.screenshot) }
android { experimentalProperties["android.experimental.enableScreenshotTest"] = true }
dependencies {
  screenshotTestImplementation(libs.screenshot.validation.api)
  screenshotTestImplementation(libs.androidx.ui.tooling)
}

# ./gradlew :feature:profile:updateDebugScreenshotTest     (record)
# ./gradlew :feature:profile:validateDebugScreenshotTest   (verify)
# refs:   feature/profile/src/screenshotTestDebug/reference/*.png
# report: feature/profile/build/reports/screenshotTest/preview/debug/index.html
```
SRC: https://developer.android.com/studio/preview/compose-screenshot-testing

### Robolectric forced fully offline + deterministic — required for a hermetic agent loop
FILE: module build.gradle.kts; src/test/resources/robolectric.properties
```
android {
  testOptions {
    unitTests {
      isIncludeAndroidResources = true
      all {
        it.systemProperty("robolectric.offline", "true")
        it.systemProperty("robolectric.dependency.dir", "$rootDir/robolectric-deps")
        it.systemProperty("robolectric.logging.enabled", "false")
        it.maxParallelForks = Runtime.getRuntime().availableProcessors() / 2
      }
    }
  }
}

// src/test/resources/robolectric.properties
// sdk=34
```
SRC: https://robolectric.org/configuring/

### dependency-guard baseline + check (module-graph / transitive dep drift oracle)
FILE: app/build.gradle.kts; baselines in app/dependencies/*.txt
```
plugins { id("com.dropbox.dependency-guard") version "0.5.0" }

dependencyGuard {
  configuration("developDebugRuntimeClasspath") {
    artifacts = true
    modules = false
    tree = false
    allowedFilter = { dependencyName: String -> !dependencyName.startsWith("com.evil") }
  }
}

# ./gradlew :app:dependencyGuard           <- fails on drift
# ./gradlew :app:dependencyGuardBaseline   <- accept the drift
# baseline file: app/dependencies/developDebugRuntimeClasspath.txt
```
SRC: https://raw.githubusercontent.com/dropbox/dependency-guard/main/README.md

### modules-graph-assert — declarative layering enforcement at graph level (complements Konsist's source-level rules)
FILE: root build.gradle.kts
```
plugins { id("com.jraska.module.graph.assertion") version "2.9.1" }

moduleGraphAssert {
  maxHeight = 5
  allowed = arrayOf(
    ":app -> :feature.*",
    ":feature.* -> :domain.*",
    ":feature.* -> :shared.*",
    ":data.* -> :domain.contract"
  )
  restricted = arrayOf(
    ":feature.[a-z]* -X> :feature.*",   // features must not depend on each other
    ":domain.* -X> :data.*"             // domain must not reach into data
  )
  configurations = setOf("api", "implementation")
  assertOnAnyBuild = false
}

# ./gradlew assertModuleGraph
# ./gradlew generateModulesGraphStatistics
```
SRC: https://github.com/jraska/modules-graph-assert

### dependency-analysis / buildHealth with fail-level severities
FILE: root build.gradle.kts
```
plugins { id("com.autonomousapps.dependency-analysis") version "3.18.0" }

dependencyAnalysis {
  issues {
    all {
      onUnusedDependencies        { severity("fail") }
      onUsedTransitiveDependencies{ severity("fail") }
      onIncorrectConfiguration    { severity("fail") }   // api vs implementation
      onCompileOnly               { severity("warn") }
      onRuntimeOnly               { severity("warn") }
      onUnusedAnnotationProcessors{ severity("fail") }
      onRedundantPlugins          { severity("warn") }
    }
  }
  structure { ignoreKtx(true) }
}

# ./gradlew buildHealth               -> build/reports/dependency-analysis/build-health-report.txt (+ JSON on disk)
# ./gradlew :app:projectHealth        -> single module, much faster
# ./gradlew fixDependencies           -> auto-remediate
# gradle.properties: dependency.analysis.autoapply=false
```
SRC: https://github.com/autonomousapps/dependency-analysis-gradle-plugin

### Kover coverage gate with machine-readable XML
FILE: app/build.gradle.kts (aggregating module)
```
plugins { id("org.jetbrains.kotlinx.kover") version "0.9.9" }

kover {
  reports {
    verify {
      rule {
        // groupBy = "APPLICATION" | "CLASS" | "PACKAGE"
        minBound(60)              // coverageUnits: LINE (default) | BRANCH | INSTRUCTION
      }
    }
  }
}
dependencies {
  kover(project(":feature:profile"))
  kover(project(":domain:usecase"))
}

# ./gradlew koverVerify        <- gate
# ./gradlew koverXmlReport     <- JaCoCo-compatible XML, parseable
# ./gradlew koverLog           <- prints metrics to console
```
SRC: https://kotlin.github.io/kotlinx-kover/gradle-plugin/

### Kotlin Gradle plugin built-in ABI validation (replacing binary-compatibility-validator)
FILE: build.gradle.kts; dumps in api/
```
kotlin {
  @OptIn(org.jetbrains.kotlin.gradle.dsl.abi.ExperimentalAbiValidation::class)
  abiValidation {
    enabled.set(true)
  }
}

# ./gradlew updateLegacyAbi    -> writes api/<module>.api  (the contract file)
# ./gradlew checkLegacyAbi     -> diffs current ABI vs api/, reports differences as errors

# Legacy plugin (maintenance mode):
# id("org.jetbrains.kotlinx.binary-compatibility-validator") version "0.18.1"
# ./gradlew apiDump / apiCheck
```
SRC: https://kotlinlang.org/docs/gradle-binary-compatibility-validation.html

### Gradle Managed Devices for reproducible instrumentation (deterministic task names, CI-safe GPU flag)
FILE: app/build.gradle.kts
```
android {
  testOptions {
    managedDevices {
      localDevices {
        create("pixel6api33") {
          device = "Pixel 6"
          apiLevel = 33
          systemImageSource = "aosp"        // "aosp-atd"/"google-atd" = faster but API 30 only, no screenshots
        }
      }
      groups {
        create("phoneAndTablet") { targetDevices.add(devices["pixel6api33"]) }
      }
    }
  }
}

# ./gradlew pixel6api33DevelopDebugAndroidTest
# ./gradlew phoneAndTabletGroupDevelopDebugAndroidTest
# headless CI: -Pandroid.testoptions.manageddevices.emulator.gpu=swiftshader_indirect
# gradle.properties: android.experimental.androidTest.numManagedDeviceShards=2
```
SRC: https://developer.android.com/studio/test/gradle-managed-devices

### Maestro e2e with JUnit XML output an agent can parse
FILE: .maestro/*.yaml
```
maestro test .maestro/ \
  --format=JUNIT \
  --output=build/maestro/report.xml \
  --include-tags=smoke \
  --exclude-tags=flaky \
  --env=BASE_URL=http://localhost:3000 \
  --debug-output=build/maestro/debug

# shard across devices:
maestro test .maestro/ --shard-split=3 --format=JUNIT --output=build/maestro/report.xml

# spin up a device first:
maestro start-device --platform=android --device-os=android-33 --device-locale=en_US --force-create
```
SRC: https://docs.maestro.dev/maestro-cli/maestro-cli-commands-and-options.md

### reviewdog turning any SARIF/checkstyle report into PR annotations
FILE: .reviewdog.yml or inline in CI
```
# Android Lint (SARIF) -> GitHub PR review comments, only on changed lines
reviewdog -f=sarif -name="android-lint" -reporter=github-pr-review -filter-mode=added -level=warning \
  < app/build/reports/lint-results-debug.sarif

# detekt (checkstyle XML)
reviewdog -f=checkstyle -name="detekt" -reporter=github-pr-check -filter-mode=file \
  < build/reports/detekt/detekt.xml

# ktlint (its own errorformat), or use --reporter=sarif and -f=sarif
ktlint --reporter=checkstyle | reviewdog -f=checkstyle -name=ktlint -reporter=github-pr-review

# spotless / formatters: feed the diff itself so reviewdog posts suggested fixes
./gradlew spotlessApply && git diff | reviewdog -f=diff -f.diff.strip=1 -reporter=github-pr-review
```
SRC: https://raw.githubusercontent.com/reviewdog/reviewdog/master/README.md

### gradle-mcp server config for Claude Code / Cursor — gives the agent typed build failures instead of console scrollback
FILE: ~/.claude.json or .mcp.json
```
{
  "mcpServers": {
    "gradle": {
      "command": "jbang",
      "args": ["run", "--quiet", "--fresh", "gradle-mcp@rnett"],
      "env": { "GRADLE_MCP_PROJECT_ROOT": "/Users/me/project" }
    }
  }
}

# Then the agent calls:
#   gradle(commandLine: [":app:testDevelopDebugUnitTest"])         -> returns BuildId
#   query_build(buildId, kind: "FAILURES")                          -> summary list of FailureIds
#   query_build(buildId, kind: "FAILURES", query: "<FailureId>")    -> auto-expands to full detail
#   query_build(buildId, kind: "TESTS",   query: "com.foo.BarTest") -> per-test logs + stack traces
#   query_build(buildId, kind: "PROBLEMS")                          -> compilation/configuration problems
#   query_build(buildId, kind: "CONSOLE", query: "<regex>")         -> filtered raw logs, last resort
# Requires JDK 21+.
```
SRC: https://raw.githubusercontent.com/rnett/gradle-mcp/main/README.md

### Android CLI as a Gradle-free inner-loop oracle (needs a running Android Studio instance)
FILE: repo root; persistent flags in ~/.androidrc
```
# one-time
brew install ...            # or: winget install -e --id Google.AndroidCLI ; apt-get install ...
android init
android skills add --skill=r8-analyzer --project=.
android skills list

# is Studio up and holding an indexed project?
android studio check
#   pid: 32942
#   version: Android Studio
#   Projects:
#       READY     JetSet /Users/adarshf/AndroidStudioProjects/jetset-main

# IDE-grade inspection of ONE file — no Gradle run at all
android studio analyze-file app/src/main/java/com/kkday/ui/ProfileScreen.kt

# render a Compose preview + get the semantics tree as JSON
android studio render-compose-preview \
  app/src/main/java/com/kkday/ui/ProfileScreen.kt ProfileScreenPreview \
  --print-semantics --output-image-file=build/preview.png

# project metadata as JSON (build targets + artifact paths)
android describe --project_dir=.

# runtime UI hierarchy as JSON; --diff sends only what changed
android layout --pretty --output=build/hierarchy.json
android layout --diff
```
SRC: https://developer.android.com/tools/agents/android-cli

### Turbine + runTest ViewModel state assertion (the standard MVVM+UDF unit oracle)
FILE: src/test/kotlin/**/ProfileViewModelTest.kt
```
@Test
fun `emits Loading then Content`() = runTest {
    val vm = ProfileViewModel(FakeProfileRepository())

    vm.uiState.test {
        assertEquals(ProfileUiState.Loading, awaitItem())
        assertEquals(ProfileUiState.Content(profile), awaitItem())
        cancelAndIgnoreRemainingEvents()
    }
}

// Turbine's default timeout is 3s WALL CLOCK, independent of runTest virtual time.
// Override: flow.test(timeout = 10.seconds) { ... } or withTurbineTimeout(10.seconds) { ... }
// Multiple flows at once: turbineScope { val a = flowA.testIn(backgroundScope); ... }
```
SRC: https://raw.githubusercontent.com/cashapp/turbine/trunk/README.md

### Now in Android's exact CI task ordering — a proven reference for what belongs in CI vs the inner loop
FILE: .github/workflows/Build.yaml
```
./gradlew :build-logic:convention:check
./gradlew spotlessCheck
./gradlew dependencyGuard                     # on failure in a PR -> dependencyGuardBaseline + auto-commit
./gradlew graphUpdate                         # then: git add -- "**/README.md" && git diff --cached --quiet --exit-code -- "**/README.md"
./gradlew verifyRoborazziDemoDebug            # on failure in a PR -> recordRoborazziDemoDebug + auto-commit
./gradlew testDemoDebug :lint:test
./gradlew :app:assemble -PminifyWithR8=false
./gradlew :app:lintProdRelease :app-nia-catalog:lintRelease :lint:lint
./gradlew :app:checkProdReleaseBadging

# separate emulator matrix job:
./gradlew connectedDemoDebugAndroidTest --daemon
./gradlew testDemoDebugUnitTest -Proborazzi.test.verify=false
./gradlew createDemoDebugCombinedCoverageReport

# SARIF fed to GitHub code scanning per module via github/codeql-action/upload-sarif@v3
```
SRC: https://raw.githubusercontent.com/android/nowinandroid/main/.github/workflows/Build.yaml

### Parsing JUnit XML results generically (works for unit tests, Konsist, Roborazzi, Paparazzi, Compose tests, Maestro)
FILE: **/build/test-results/<taskName>/TEST-*.xml
```
# Collect every failure across a multi-module build in one shot
find . -path '*/build/test-results/*' -name 'TEST-*.xml' -print0 \
 | xargs -0 python3 - <<'PY'
import sys, xml.etree.ElementTree as ET
for p in sys.argv[1:]:
    for tc in ET.parse(p).getroot().iter('testcase'):
        for f in list(tc.findall('failure')) + list(tc.findall('error')):
            print(f"{tc.get('classname')}.{tc.get('name')}\n  {f.get('message')}\n  {(f.text or '').splitlines()[0] if f.text else ''}")
PY
```
SRC: https://docs.gradle.org/current/userguide/java_testing.html

### gradle.properties baseline for a fast agent loop
FILE: gradle.properties
```
org.gradle.caching=true
org.gradle.configuration-cache=true
org.gradle.configuration-cache.problems=warn
org.gradle.parallel=true
org.gradle.jvmargs=-Xmx6g -XX:MaxMetaspaceSize=1g -Dfile.encoding=UTF-8
kotlin.incremental=true
kotlin.daemon.jvmargs=-Xmx3g -XX:ReservedCodeCacheSize=512m
android.experimental.enableScreenshotTest=true

# Disable per-run for a clean measurement:  --no-build-cache --rerun-tasks
```
SRC: https://kotlinlang.org/docs/gradle-compilation-and-caches.html

## GOTCHAS
- detekt 2.0 type resolution can be catastrophically slow on multi-module/KMP builds: issue #8882 (opened 28 Nov 2025) reports an ~80k-LOC KMP monorepo going from ~1 minute to ~24 minutes because enabling type resolution compiles every Android variant and flavor across all modules — including modules with no Android source set. The no-type-resolution `detekt` task ran the same code in ~20 seconds. NEVER put `detektMain`/`detekt<Variant>` in an agent inner loop.
- On Android you cannot run detekt variant tasks concurrently — each variant needs a different classpath for type solving. This silently limits parallelism and is a common source of wrong/missing findings.
- Konsist has not shipped a release since 0.17.3 on 8 Dec 2024 (~20 months stale as of Aug 2026), despite being the standard Kotlin architecture-assertion tool and a 2024 Kotlin Foundation grant winner. Konsist parses source only — it has no compiler type resolution, so rules relying on fully-qualified types, star imports, or typealiases can produce false negatives. Verify against a deliberately-broken file before trusting a rule.
- dependency-guard's last release is 0.5.0 from 5 Feb 2024 (~2.5 years stale). Its failure output is a human-readable text diff, not structured data, so agents must diff the baseline `.txt` themselves.
- `--offline` fails hard rather than degrading: any dependency not already in the Gradle cache aborts the build with a resolution error that looks like a code failure. An agent must be able to distinguish 'offline cache miss' from 'your code is wrong'. Run one online warm-up build before entering an offline loop.
- Robolectric silently downloads Android SDK jars over the network on first run unless `robolectric.offline=true` and `robolectric.dependency.dir` are set. In a sandboxed agent environment this manifests as an opaque test failure/hang, not a network error.
- Turbine applies a 3-second WALL-CLOCK timeout independent of `runTest`'s virtual time. On a loaded machine (which an agent loop always is — parallel Gradle workers), this produces flaky `TimeoutCancellationException` that looks like a real bug. Turbine also depends on the unstable `UnconfinedTestDispatcher` API and explicitly warns future coroutines updates may alter behaviour.
- Google's Compose Preview Screenshot Testing has been `0.0.1-alphaNN` for roughly two years (alpha16 as of Aug 2026) and now requires AGP 9.0+ / Kotlin 2.2.10+. It is not a safe foundation for a project pinned to AGP 8.x. Roborazzi (1.72.0, stable, active) or Paparazzi (2.0.0-alpha05) are the pragmatic choices — and only Roborazzi produces a documented JSON result schema.
- Gradle Managed Devices ATD images (`aosp-atd`/`google-atd`) are API 30 only AND have hardware rendering disabled, so screenshot tests silently cannot run on them. Sharding via `numManagedDeviceShards` is resource-hungry: a 3-device group with 2 shards provisions 6 VMs and can time out Gradle.
- Baseline profile generation needs either a rooted GMD (`systemImageSource = "aosp"`) or API 33+. Using `google` images at API <33 fails at generation time with a confusing permissions error.
- Gradle's default console is rich/ANSI and interleaves parallel task output. An agent parsing raw stdout without `--console=plain` will mis-attribute errors to the wrong module. Also, without `--continue`, Gradle stops at the first failing task — the agent fixes one thing per iteration instead of batching.
- Android Lint `checkDependencies = true` is dramatically slower because it analyses all dependency modules. NiA only runs full lint in CI (`:app:lintProdRelease`), never in the inner loop.
- Spotless historically caused Gradle configuration-cache misses via JGit touching `.git/HEAD` and `.git/config` when switching branches — exactly the churn an agent loop generates. Fixed in 7.0+ but worth verifying on your version.
- `binary-compatibility-validator` is officially in maintenance mode; new work goes to the KGP built-in ABI validation, which is still `@ExperimentalAbiValidation`. Neither matters for app modules — only libraries. Metalava (1.0.0-alpha15) has no official standalone documentation page on developer.android.com and is effectively an AndroidX-internal tool.
- The `com.twitter.compose.rules:ktlint` ruleset is abandoned (last published Nov 2022). The live fork is `io.nlopez.compose.rules:{ktlint,detekt}` 0.6.4. Copy-pasting older blog configs pulls in the dead artifact.
- The DAGP maintainer instituted a Strict No LLM / No AI policy in the project Code of Conduct (May 2026) after AI-generated PRs shipped a misdiagnosed ClassCastException and a path-sensitivity change that would have caused stochastic failures for remote-cache users. Agents should not open PRs against build tooling projects without checking their AI policy.
- `android studio analyze-file` and `render-compose-preview` require a RUNNING, fully-indexed Android Studio instance (`android studio check` shows `READY`). In headless CI or a fresh container this whole class of fast oracle is unavailable, so an agent must have a Gradle fallback path.
- Lightbuild — the YAML declarative build config Google is positioning as the agent-parseable future — is trusted-testers-only as of Aug 2026. Do not design a workflow around it yet.
- Published Android build-time benchmarks are stale: the Gradle 'Blazing Fast Android Builds' post is from May 2017 (AGP 3.0 era) and gradle/android-build-eval's last benchmark run was Feb 2021. Treat any cited seconds-per-build figure from those sources as historical, not current.
- Konsist/architecture tests placed in `app/src/test` run inside `testDebugUnitTest` alongside everything else — a failing architecture rule and a failing business-logic test look identical in the console. Put them in a dedicated module or use `--tests '*Konsist*'` / `--tests '*Architecture*'` so an agent can classify the failure.

## OPEN
- No credible published benchmark exists for wall-clock times of these tools on a 'medium multi-module Android project' (say 30-80 modules) in 2025-2026. The Gradle blog figures are from 2017 and gradle/android-build-eval last ran Feb 2021. Any latency tiering should be measured locally with `--profile` / build scans rather than taken from literature.
- Google's >70% token reduction / 3x speed claim for Android CLI comes from unspecified 'internal experiments' with no published methodology, task set, or baseline agent. The claim that structured JSON + `--diff` mode is the mechanism appears in secondary coverage (byteiota/InfoQ), not in the official blog text I fetched.
- Android CLI has no documented `build`, `lint`, or `test` subcommand — the documented surface is create/emulator/run/sdk/skills/studio/docs/describe/layout/screen. Whether Gradle build+test invocation is intended to stay outside Android CLI (delegated to `./gradlew` or Lightbuild) is unclear.
- The exact on-disk path and JSON schema of dependency-analysis-gradle-plugin's machine-readable advice output is not documented in the wiki pages I could fetch — the wiki confirms JSON is written 'to disk' but not where. Needs to be discovered empirically under `build/reports/dependency-analysis/`.
- Whether Gradle 9.x's incubating Problems API exposes a JSON (rather than HTML) artifact at `build/reports/problems/` — which would be the ideal generic agent oracle — could not be confirmed from the docs.
- Develocity MCP Server's exact tool names, docker run invocation, and AI-client JSON config are behind pages I could not retrieve; availability was previously a Limited Availability program and its current GA status for 2026.1 is unclear.
- Konsist's future: no release in 20 months. Whether it is maintained, and whether a JUnit5/Kotlin 2.x-era successor exists for Kotlin architecture assertions, is unresolved. ArchUnit (JVM/bytecode-based) is the fallback but loses Kotlin-language fidelity.
- ktlint 1.8.0's `--reporter=sarif` behaviour and whether it emits repo-relative paths by default (needed for reviewdog/GitHub annotation alignment) was not verified against primary docs — the ktlint docs site paths I tried returned 404.
- Whether `spotlessApply` is safe to run unattended inside an agent loop on a repo with `ratchetFrom` when the agent has uncommitted changes across many modules (interaction between JGit ratchet resolution and dirty working tree) is unverified.
- Real-world adoption data for the community `gradle-mcp` server (rnett) vs. agents just shelling out to `./gradlew` — no usage statistics found, and its README notes 'Source downloading and indexing tools will be moving to a dedicated MCP/cli soon', implying API churn.

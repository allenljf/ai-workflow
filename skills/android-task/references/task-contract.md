---
visibility: public
review_state: approved
---

# Task contract and checkpoint

TaskContract fields: `id`, `spec_hash`, `base_sha`, `depends_on`, `read_paths`, `write_paths`, `resource_locks`, `acceptance` (unique id + observable description), `validation_commands` (argument arrays), `max_attempts` (1–3), `time_budget_minutes`, `token_budget`, `checkpoint`, `handoff_summary`.

Keep the accepted specification immutable and hash its exact bytes. Bind base to an existing commit. Paths are repository-relative; directory ownership covers descendants. Read/write overlap and shared emulator, Gradle cache, port, or account locks serialize implementation. Independent reads may coexist.

A checkpoint records spec_hash, base_sha, head_sha, attempts_used, elapsed_minutes, tokens_used (null if unavailable), completed acceptance IDs, and the next action. If usage cannot be measured, report it unknown and preserve the time/attempt bounds. Start a new session from this record, then recheck the tree and resource reservations. A new budget requires an explicit revised contract; resuming is not a free retry.

TaskRecord stores contract, status, head_sha, integrated_sha, evidence_ids. The readiness gate expects dependencies' integrated_sha to identify the current integration snapshot; the integrator refreshes those attestations after verifying inclusion. This field is not an ancestry guess. `ready_for_review` and `accepted` without integration keep dependents waiting. A blocked task does not change the dependency graph.

Tools and JSON schemas are maintained in the platform repository. Install this document adapter alone into the target harness's skill directory; run validator/dispatcher tools from the reviewed platform checkout, not downloaded article commands.

An attempt starts when the dispatcher launches implementation or a validation command. A preflight blocker consumes no attempt. The wall-clock time budget starts with the first launch and includes subsequent waiting; checkpoints retain that original deadline.

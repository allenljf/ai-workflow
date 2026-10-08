---
name: android-task
description: Use when implementing an Android task with a declared task contract, resuming a checkpoint, or handing a patch to a reviewer.
metadata:
  visibility: public
  review_state: approved
---

# Android task adapter

Use the installed upstream planning/execution workflow for orchestration. This adapter defines one Android implementer's boundary; if upstream is unavailable, report the missing binding and use the team's declared workflow.

1. Read [task-contract](references/task-contract.md). Validate the contract and resolve project → company → Android → upstream policy. Continue when conflicts have explicit reasons. Use declared dependencies only; infer neither dependency edges nor acceptance.
2. Start from the contract's integration SHA. Begin implementation after every declared dependency is accepted and included in that integration snapshot. The dispatcher reserves write/read paths and shared resources; at most two implementers run concurrently.
3. Implement within declared writes and authorized argument-array commands. On resume, compare checkpoint spec/base/head to the working tree; a mismatch requires a revised contract or checkpoint. Record each attempt, elapsed time, and available token usage. At the first exhausted bound, emit `blocked` with the cause and checkpoint; attempts never exceed the contract limit (maximum three).
4. Before review, read [verification](references/verification.md). Emit a patch, evidence references, and a handoff containing task/spec/base/head, changed paths, acceptance results, attempt count, remaining budgets, checkpoint, blocker, and next action. Use `ready_for_review` only with valid evidence; reviewer acceptance and integration remain separate states.

Payment, login credentials, signing, and release actions require the responsible human's explicit decision and a sandbox binding. Keep credentials and private company evidence outside public artifacts. Fixture validation is a contract test, not Android effectiveness evidence.

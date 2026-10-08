---
name: fde-solution
description: Use when delivering a customer-specific enterprise AI solution, including discovery, authorized data or API integration, and production handoff.
metadata:
  visibility: public
  review_state: approved
  version: 0.1.0
---
# FDE solution

Produce an enterprise delivery contract and current evidence for the user's chosen scope. Preserve their stack and authorization; choose additional infrastructure only when a measured need supports it.

Read [delivery contract](references/delivery-contract.md) for every delivery. Start with problem, owner, baseline and acceptance. Separate unknowns that block release from assumptions that allow a bounded local experiment.

For document/model work, read [AI data and task boundaries](references/ai-boundaries.md). Match the chosen design to data freshness, access rights, context size, holdout outcomes and cost.

For handoff, bind each acceptance to the actual run artifact, hash, code/data/model versions and outcome. Record fixture, local observation and enterprise observation separately. Missing owner or current evidence yields a scoped prototype with open release conditions, rather than an enterprise completion claim.

---
visibility: public
review_state: approved
---

# Evidence before review

Bind evidence to task ID, immutable spec hash, base/head SHA, model and harness versions, and the Android environment. Record argument arrays, exit codes, actual executed/failed/skipped counts, acceptance IDs and results, artifact references, provenance, duration, human minutes, and cost when measured. Unmeasured values stay null.

Exit code zero with zero executed tests, all skipped tests, a failing test, an older head, or a missing acceptance result is incomplete. Keep the task blocked or implementing and identify the missing evidence. Fake dependencies may support a labeled fixture; they cannot establish implementation acceptance.

JVM/Gradle reports and explicit Maestro/manual observations cover different acceptance paths; compilation alone establishes neither. UI acceptance needs the declared empty/loading/content/error/retry behavior actually observed. A reviewer checks the relevant failure paths before `accepted`; an integrator then records inclusion in the integration snapshot.

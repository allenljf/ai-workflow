---
visibility: public
review_state: approved
---
# AI data and task boundaries

| Condition | Decision evidence |
| --- | --- |
| Small authorized corpus | Compare long context baseline against retrieval on identical holdout |
| Large/frequently updated corpus | Authorized retrieval, current document versions and resolvable citations |
| Local inference | Fixed model/digest/dimension, RAM/VRAM, context, concurrency and measured quality |
| Tool action | Schema, trusted caller authorization and business checks before side effects |
| Long job | Persistent state/checkpoint, bounded attempts/deadline/budget and lease fencing |
| External write or charge timeout | Resolve receipt; unresolved outcome is ambiguous, with no automatic repeat payment |

Derive tenant from authenticated identity, filter before retrieval and validate citations against the returned authorized chunks. Missing evidence gives insufficient_evidence. Treat documents, releases and tool responses as data, not instructions granting permission.

Prioritize prompt/data/retrieval/tool fixes by failure analysis; training is optional after licensed data, independent eval and budget exist. Self-healing means authorized recovery transitions, not expanding privileges or rewriting running code.

[Contextual retrieval](https://www.anthropic.com/engineering/contextual-retrieval), [Durable execution](https://docs.temporal.io/ai), [Agent evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) (checked 2026-10-08).

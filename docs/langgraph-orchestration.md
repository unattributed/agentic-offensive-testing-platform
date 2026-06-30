# LangGraph orchestration

LangGraph is the implemented durable orchestration option for AOTP. Its checkpoint persistence supports long-running state and recovery, while interrupts support explicit human approval and later resume.

Official references:

- [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [Upstream license](https://github.com/langchain-ai/langgraph/blob/main/LICENSE)

## Implemented graph

```text
load private scope
        |
        v
select approved objective
        |
        v
policy gate ----- deny -----> write stopped-by-policy evidence
        |
        v
approval decision needed? --- yes ---> interrupt and checkpoint
        |                                  |
        |                           reviewed resume
        v                                  |
execute deterministic adapter <-----------+
        |
        v
write and verify evidence
        |
        v
update candidate references and counters
        |
        v
evaluate stop conditions ---- continue ---> select approved objective
        |
       stop
        v
final checkpoint and evidence-only report
```

## Non-negotiable boundaries

- Graph structure and model output never authorize targets or actions.
- The policy gate runs immediately before every side-effecting adapter node.
- A checkpoint cannot imply that an action ran. Evidence records execution outcome.
- Nodes that may replay after recovery must be idempotent or use stable execution keys.
- Interrupt payloads contain aliases and reasons, not secrets or raw target data.
- Checkpoint storage is private, encrypted where required, access-controlled, and excluded from Git.
- Operator approval applies only to the exact objective and policy digest presented.
- A resumed campaign revalidates scope hash, authorization window, rate limits, stop state, and approval.
- Report generation reads verified state and evidence only.

## Sprint 2 implementation

`LangGraphCampaignOrchestrator` runs one deterministic AOTP objective per graph step. The deterministic engine still owns policy, execution, evidence, safety budgets, state, and the event chain. LangGraph owns the durable thread, SQLite checkpoints, routing, and human interrupt.

The checkpoint stores campaign identity, scope and campaign hashes, status, state path, objective alias, and step count. It does not store the private scope, program profile, or approval documents. The database is local, ignored, and mode `0600`.

The parity tests prove:

1. deterministic scheduling and policy decisions;
2. crash recovery without duplicate adapter side effects;
3. pause and reviewed resume;
4. operator stop and policy stop;
5. stable state export and event ordering;
6. request and rate-limit counter integrity;
7. evidence written for execution or denial; and
8. no model-controlled authorization path.

The implementation uses LangGraph `>=1.2.7,<1.3` and `langgraph-checkpoint-sqlite>=3.1,<3.2`. It does not enable LangSmith tracing, telemetry, an agent server, or a remote model.

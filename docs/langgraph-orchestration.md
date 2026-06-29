# LangGraph orchestration plan

LangGraph is the preferred future orchestration layer for AOTP. Its checkpoint persistence supports long-running state, recovery, and memory, while interrupts support explicit human approval and later resume. These capabilities match campaign checkpoints, stop conditions, approval queues, and durable evidence workflows.

Official references:

- [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [Upstream license](https://github.com/langchain-ai/langgraph/blob/main/LICENSE)

## Proposed graph

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

## Adoption slice

Sprint 2.7 will implement a prototype behind an orchestration interface. The current deterministic loop remains the reference behavior until parity tests prove:

1. deterministic scheduling and policy decisions;
2. crash recovery without duplicate adapter side effects;
3. pause and reviewed resume;
4. operator stop and policy stop;
5. stable state export and event ordering;
6. request and rate-limit counter integrity;
7. evidence written for execution or denial; and
8. no model-controlled authorization path.

LangGraph will be added as an optional dependency only after its direct and transitive license obligations, version policy, storage model, and operational failure modes are reviewed.

# Campaign state model

Campaign state is ignored JSON under `.aotp/state/`. It includes campaign identity and name, scope hash, authorization and rules-of-engagement references, start and update times, status, completed, pending, skipped, and stopped objectives, candidate references, evidence directories, request and rate-limit counters, stop history, and structured iteration events.

Valid operational outcomes include completion, policy stop, operator stop, budget stop, and pause for human review. Resume changes a reviewed pause to `ready_to_resume`; future adapter slices will continue execution from that checkpoint.

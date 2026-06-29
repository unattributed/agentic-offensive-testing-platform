# Architecture

AOTP separates authority, planning, execution, evidence, verification, and reporting.

```text
program profile -> private scope -> campaign parser -> scheduler
                                             |
AI advisory output --------------------------+
                                             v
                                        policy gate
                                     deny /       \ allow
                               stop record         adapter
                                                      |
                                             evidence writer
                                                      |
                                          verifier + lifecycle
                                                      |
                                              human approval
                                                      |
                                           evidence-only report
```

Program policy context and technical scope are separate. The policy gate is the sole execution authority. Planner output has no authority. Adapters declare supported, required, and denied actions. The executor is deterministic, and the foundational release is network-silent.

State and evidence are local, ignored artifacts. Reports read those artifacts and do not receive free-form facts from a model.

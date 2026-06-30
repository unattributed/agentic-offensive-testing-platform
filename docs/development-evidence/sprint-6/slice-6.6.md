# Sprint 6 Slice 6.6: instability stops and closeout

Bounded fuzzing campaigns require request, response-size, retry, runtime, target-instability, and
authentication-lockout stop conditions. Detected signals stop before execution and persist:

- the ordered stop signals;
- zero actual request and endpoint counters;
- rate-limit and consecutive-failure counters;
- a `campaign_stop` event;
- an integrity-verified evidence manifest.

No live fuzzing adapter, payload execution, or network traffic is introduced.

## Validation

- 27 focused Sprint 6 tests passed.
- 205 full project tests passed.
- Compile and repository safety gates passed.
- Corpus reference, campaign execution, evidence verification, and event-chain verification passed
  through the CLI.

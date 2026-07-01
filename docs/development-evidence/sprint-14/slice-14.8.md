# Slice 14.8: Three-Iteration Campaign Loop

Implemented exactly three unique objectives and four target requests: one root GET, one TLS
connection, robots.txt, and security.txt. State is committed after each accepted iteration.

Proof: unit tests complete all three iterations and deny a changed second target before execution.
The sanitized live proof records three completed iterations and four requests.

# Slice 14.4: Structured Model Proposals

Implemented strict Pydantic structured output for objective id, native tool name, target alias,
tool-specific arguments, and rationale. HTTP, TLS, and well-known argument schemas reject unknown
or weakly typed fields.

Proof: proposal tests cover valid JSON, non-object JSON, unknown tools, unsafe identifiers, empty
rationale, unknown fields, and tool-specific argument shape.

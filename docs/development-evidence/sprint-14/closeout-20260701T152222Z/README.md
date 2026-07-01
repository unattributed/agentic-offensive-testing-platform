# Sprint 14 Closeout

All ten Sprint 14 slices are implemented and accepted.

The live campaign used a local tool-capable model through LangChain Deep Agents, completed three
approved metadata iterations, used exactly four requests, wrote three hashed evidence artifacts,
returned classified summaries between iterations, and produced a due-diligence report.

An initial GPU-backed attempt failed closed after the local Ollama Vulkan runner reported device
loss. AOTP recorded the failure without continuing. The accepted reference bootstrap now defaults
to CPU inference and the complete rerun passed.

No target, authorization document, raw response, private campaign state, or report is tracked.
Private artifacts remain ignored under `.aotp/`.

The private local archive is
`.aotp/evidence/development/sprint-14/closeout-20260701T152222Z.tar.gz`. Its SHA256 is recorded in
`archive-sha256.txt`.

# ADR 0006: Expose reports to AI assistants through a read-only MCP server

Status: Proposed — post-v1 (CG-036, CG-037)

Date: 2026-09-27 (formalizes the design in CG-036, planned 2026-09-14)

## Context

Developers increasingly review pull requests from within AI assistants and
IDEs. Those clients speak the Model Context Protocol (MCP). Exposing
ChangeGuard as a general agent tool would conflict with the advisory,
no-execution boundary in ADR 0001.

## Decision

- Provide a custom, authenticated MCP server whose tools only read persisted
  reports, findings, evidence ranges, coverage limitations and
  citation-validation results.
- The server cannot trigger analysis, write to repositories, approve or merge,
  execute code or call models. Tool inputs are validated and responses are
  bounded.
- Report content remains untrusted data. Tool descriptions and responses must
  not act as instructions to the client.
- Tool use is evaluated in two layers. Deterministic offline replay of recorded,
  redacted transcripts runs by default in CI. An opt-in live run is scored with
  DeepEval's MCP metrics, and the judge model, thresholds and reasons are
  recorded. An LLM judge score is treated as evidence, not ground truth.

## Consequences

- Assistants get grounded, citable PR-impact context without being given new
  privileges.
- Changes to tool names or descriptions become regression-tested rather than
  judged by eye.
- It adds a second external interface to secure, which is why the work is
  scheduled after persistence, citation validation and telemetry are in place.

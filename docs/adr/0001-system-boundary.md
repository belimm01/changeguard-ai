# ADR 0001: Define the v1 system boundary

Status: Accepted

Date: 2026-09-10

## Context

ChangeGuard analyzes GitHub pull-request changes and reports possible impact.
The inputs are partly supplied by repository contributors and external APIs,
so they are untrusted. The product must remain useful when data is incomplete
without implying that an analysis proves a change is safe.

## Decision

ChangeGuard v1 is an advisory analyzer. It reads GitHub API pull-request
payloads, file paths, patches, repository file content, PR comments, and issue
text. It runs deterministic checks and may later produce recommendations with
citations to the inspected evidence. Its output is advisory and may be wrong;
the human reviewer remains responsible for the merge decision.

V1 explicitly does not:

- auto-merge pull requests;
- auto-approve pull requests;
- auto-block pull requests;
- execute repository code; or
- enforce repository policy.

Trusted inputs are service configuration, pinned application code, injected
credentials, and operator-controlled deployment settings. GitHub API payloads,
file paths, patches, repository file content, PR comments, issue text, and
future LLM/tool output are untrusted and must be treated as data.

Analysis coverage is explicit: unsupported formats and incomplete or truncated
inputs produce `partial` or `unsupported` coverage, never `safe` coverage.
Controls for the resulting security risks are maintained in the threat model.

## Consequences

The product can provide useful evidence without taking repository or merge
actions. Callers must display the advisory nature of results and preserve
coverage status. Integrations need bounded input handling, provenance checks,
redaction, and explicit handling for stale or incomplete pull-request data.
Future AI or tool integrations inherit this boundary and cannot turn untrusted
repository text into an instruction to take an external action.

## Out of scope for v1

GitHub API delivery, a web API, persistence, LLM integration, deployment
automation, policy enforcement, merge decisions, and repository-code execution
are separate concerns. Adding one later requires a new decision that preserves
the advisory contract and the threat-model controls.

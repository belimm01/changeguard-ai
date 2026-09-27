# ADR 0003: Read SHA-bound content through the GitHub API, never check out code

Status: Accepted

Date: 2026-09-10

## Context

Rules such as OpenAPI, Avro and Kubernetes compatibility need the base and head
versions of changed files, not only the patch. The usual approach is to clone
the repository and check out both revisions. For pull requests from untrusted
contributors this brings in repository code, hooks, submodules, symlinks and
large files, and leaves the analysis unclear about which revision it saw.

## Decision

- Content is fetched per file through the GitHub REST API with an async
  `httpx` client, addressed by the exact base and head commit SHAs of the PR.
- Every piece of evidence records its path, side (base/head), blob/commit SHA
  and line range. Diff-line evidence is bound to the same SHAs.
- Paths are validated (no traversal, absolute paths or symlinks). Per-file and
  aggregate byte budgets, pagination caps and timeouts are enforced.
- If the PR head moves during analysis, the result is marked stale rather than
  mixed across revisions.
- Deleted, binary, oversized or unfetchable files produce explicit `partial` or
  `unsupported` coverage instead of being skipped silently.
- Repository code is never cloned, installed or executed.

## Consequences

- No sandbox is needed for analysis, and the attack surface is limited to
  parsing bounded data.
- Findings are reproducible and citable, which the AI citation validator
  (ADR 0005) depends on.
- Whole-repository analysis (import graphs, builds) is out of scope for v1;
  cost scales with the number of changed files and is capped by budgets.

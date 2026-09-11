# ChangeGuard v1 threat model

## Security contract

ChangeGuard output is advisory and may be wrong. It does not auto-merge,
auto-approve, auto-block, or execute repository code, and it does not claim to
enforce repository policy. Coverage is `partial` or `unsupported` when the
input cannot be analyzed completely; it is never `safe` merely because no
finding was produced.

## Assets and trust boundaries

| Asset or boundary | Classification and protection |
| --- | --- |
| GitHub API payloads, file paths, patches, repository file content, PR comments, and issue text | Untrusted input; validate, bound, and treat as data. |
| Future LLM/tool output | Untrusted input; require structured validation and evidence provenance. |
| Service configuration and pinned application code | Trusted application inputs; review and pin changes. |
| Injected credentials | Trusted secrets; keep out of source, findings, and logs. |
| Operator-controlled deployment settings | Trusted operational input; restrict access and audit changes. |
| Findings, recommendations, and coverage status | Advisory output; preserve evidence and uncertainty for the human reviewer. |

The primary boundary is between operator-controlled application/runtime inputs
and contributor-controlled repository/API data. No repository content crosses
that boundary as executable instructions.

## Threats and mitigations

| Threat scenario | Required mitigation |
| --- | --- |
| A path such as `../../secret` or an absolute path escapes the repository root. | Normalize paths, reject traversal and absolute paths, and resolve only within the configured repository root. |
| A symlink points a requested file outside the repository. | Detect symlinks and verify the resolved target remains within the repository root before reading. |
| An oversized file or diff exhausts memory or processing time. | Enforce byte, file-count, patch-line, and request-size limits; return `partial` or `unsupported` when limits are exceeded. |
| Credentials or sensitive repository content appear in logs or findings. | Redact credentials, avoid logging raw payloads by default, and bound evidence excerpts. |
| The base or head SHA is stale, missing, or mismatched with the fetched data. | Pin and compare SHAs, verify the analyzed revision, and report stale or unverifiable state as `partial`/`unsupported`. |
| Prompt injection in repository content or issue text instructs a future model/tool to ignore controls or act. | Treat all repository text as untrusted data, isolate it from instructions, allow only cited recommendations, and never grant it execution or merge authority. |
| API pagination truncates files, comments, or issue text without being noticed. | Follow pagination to an explicit bounded limit, record truncation, and downgrade coverage to `partial` or `unsupported`. |
| An unsupported file format is silently treated as safe. | Classify format support explicitly and return `unsupported` or `partial`; never infer safety from absence of a rule. |

## Operational constraints

Deterministic checks must preserve the source path, revision, and bounded
evidence needed to explain a finding. Future recommendation providers must be
unable to merge, approve, block, execute code, or suppress deterministic
findings. A human owns the final decision.

## Follow-up

CG-008 should define versioned reports, evidence, and coverage fields. Later
GitHub integration and optional AI tickets must demonstrate these controls in
tests before they expand the boundary.

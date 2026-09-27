# ADR 0005: Optional, provider-neutral AI with deterministic citation validation

Status: Accepted — implementation planned (CG-016–CG-022)

Date: 2026-09-10

## Context

LLMs can turn findings into useful reviewer guidance (suggested tests,
migration and rollback notes), but they hallucinate, can be steered by prompt
injection hidden in repository text, and add cost, latency and a vendor
dependency. ADR 0001 requires that no output implies a change is safe.

## Decision

- **Deterministic first.** Rule findings are authoritative. AI enrichment is
  opt-in, disabled by default and never required for a valid report.
- **Provider-neutral boundary.** A Python `Protocol`
  (`complete_structured(request) -> result`) hides vendor SDKs. Requests carry
  a versioned prompt, a JSON output schema and hard budgets (input size,
  output tokens, timeout, cost ceiling). The model gets no tools, shell, file
  or network access.
- **Grounding.** Context is a bounded corpus of ADRs, documentation and schema
  chunks taken from SHA-bound content (ADR 0003). v1 retrieval is deterministic
  lexical and path-aware scoring with fixed budgets. Embeddings and a
  single-host vector store are an optional post-v1 extension, adopted only if
  offline evaluation shows a gain.
- **Validation.** Each AI claim must cite a source that exists in the allowed
  set, with matching path, side, SHA and range. Quotes must appear in the
  cited range. AI cannot create, upgrade, remove or contradict deterministic
  findings. Unsupported claims are rejected with a recorded reason.
- **Evaluation.** Offline golden sets and adversarial and data-leakage
  regression suites run in CI. A citation proves provenance, not correctness,
  and reports label it accordingly.

## Consequences

- The product still works, and can be released as deterministic-only, without
  credentials or model spend.
- Switching providers means adding one adapter and does not touch the
  application.
- Some useful but uncitable model insight is discarded; this trade-off is
  deliberate in favour of trust.

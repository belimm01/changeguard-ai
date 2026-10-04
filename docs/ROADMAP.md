# ChangeGuard AI — v1 roadmap and ticket board

Updated: 2026-10-04

## Start here

Open this file to see the entire project. Each row links to an implementation
ticket; `backlog.json` is the machine-readable copy of this board.
Architecture decisions that shape these tickets are recorded in
[`adr/`](adr/) and the [threat model](threat-model.md).

Next task: **CG-016** introduces a bounded repository context corpus for retrieval.
CG-001–CG-015 are done, including PostgreSQL persistence, reversible Alembic
migrations, concurrent duplicate handling and sanitized failure storage.

This is a proposed finite v1 backlog, not a claim that all future requirements
are known. CG-007 makes the release boundary explicit. Later tickets are
**Planned**, not automatically implementation-ready. Refine a ticket when its
dependencies land; add newly discovered work here instead of hiding it.

## What finished means

In an explicitly approved sandbox, an authorized GitHub App receives a signed
PR event, durably schedules analysis of the identified revision, fetches bounded
inputs, runs deterministic rules and optionally produces grounded AI advice,
and publishes an advisory GitHub Check attached to the correct commit.

The report includes risk level, evidence paths and valid line ranges where
available, input coverage/limitations, suggested tests and relevant migration
or rollback considerations. AI content is distinguished from deterministic
findings, may be unavailable, and never controls a merge decision. Missing or
unsupported inputs must not look like a clean bill of health.

v1 includes scoped Python dependency, OpenAPI, Avro and Kubernetes checks;
bounded ADR/documentation context retrieval; optional structured LLM output;
citation validation and reproducible evaluations; authenticated HTTP and GitHub
boundaries; PostgreSQL persistence via async SQLAlchemy and Alembic
migrations; crash recovery; telemetry; a reproducible single-host container
deployment; CI and an observed sandbox end-to-end acceptance run.
A citation proves source provenance, not that an AI interpretation is true.
Full AI-capable v1 acceptance also requires an approved live run of one concrete
provider adapter. If that verification is blocked, label the demonstrated
release deterministic-only rather than claiming the AI integration is verified.

## Deliberate non-goals

- Autonomous edits, execution of repository code, merge approval or merge blocking.
- An exhaustive compatibility/security scanner or a guarantee of no defects.
- SaaS billing, a web UI, enterprise multi-tenancy and arbitrary Git providers.
- Kubernetes hosting, agent framework, autonomous edits, or MCP merely to
  accumulate technologies. A scoped read-only ChangeGuard MCP server is allowed
  only as an opt-in post-core integration milestone with concrete report/evidence
  workflows, client smoke evidence, and the same advisory/no-execution boundary.
  Lexical retrieval is the v1 baseline. Embeddings and a single-host vector store
  are deferred to the opt-in post-v1 extensions (CG-031+), not v1 requirements;
  external managed vector databases stay out.
- Public deployment, spending on model calls or GitHub writes without explicit
  authorization at the relevant execution step.

These are optional post-v1 directions, not hidden release requirements.

## Board

Status meanings: Done = accepted implementation; In progress = local work,
not yet accepted; Planned = scoped future work; Blocked = an explicitly recorded
obstacle. Dependencies must be accepted before starting a ticket unless a
reviewed stacked dependency is recorded.

| Ticket | Goal | Status | Depends on | Milestone |
| --- | --- | --- | --- | --- |
| [CG-001](tickets/2026-09-06-CG-001.md) | Model and validate pull-request changes | Done | — | Foundation |
| [CG-002](tickets/2026-09-06-CG-002.md) | Detect Python dependency changes | Done | CG-001 | Foundation |
| [CG-003](tickets/2026-09-06-CG-003.md) | Validate and translate GitHub changed-file payloads | Done | CG-001 | Foundation |
| [CG-004](tickets/2026-09-08-CG-004.md) | Orchestrate deterministic analysis rules | Done | CG-002, CG-003 | Foundation |
| [CG-005](tickets/2026-09-09-CG-005.md) | Serialize deterministic analysis findings | Done | CG-004 | Foundation |
| [CG-006](tickets/2026-09-10-CG-006.md) | Local JSON analysis CLI | Done | CG-005 | Local vertical slice |
| [CG-007](tickets/2026-09-10-CG-007.md) | v1 boundaries and threat model | Done | CG-006 | Evidence-backed analysis |
| [CG-008](tickets/2026-09-10-CG-008.md) | Versioned reports, evidence and coverage | Done | CG-007 | Evidence-backed analysis |
| [CG-009](tickets/2026-09-10-CG-009.md) | Bounded asynchronous GitHub PR reader | Done | CG-008 | Evidence-backed analysis |
| [CG-010](tickets/2026-09-10-CG-010.md) | Safe SHA-bound content and diff evidence | Done | CG-009 | Evidence-backed analysis |
| [CG-011](tickets/2026-09-10-CG-011.md) | Scoped OpenAPI compatibility rule | Done | CG-010 | Evidence-backed analysis |
| [CG-012](tickets/2026-09-10-CG-012.md) | Scoped Avro compatibility rule | Done | CG-010 | Evidence-backed analysis |
| [CG-013](tickets/2026-09-10-CG-013.md) | Scoped Kubernetes manifest risk rule | Done | CG-010 | Evidence-backed analysis |
| [CG-014](tickets/2026-09-10-CG-014.md) | Authenticated analysis HTTP endpoint | Done | CG-008, CG-009, CG-010, CG-011, CG-012, CG-013 | Evidence-backed analysis |
| [CG-015](tickets/2026-09-10-CG-015.md) | Persistent analysis jobs and reports | Done | CG-014 | Evidence-backed analysis |
| [CG-016](tickets/2026-09-10-CG-016.md) | Bounded repository context corpus | Planned | CG-010 | Grounded AI |
| [CG-017](tickets/2026-09-10-CG-017.md) | Deterministic context retrieval | Planned | CG-016 | Grounded AI |
| [CG-018](tickets/2026-09-10-CG-018.md) | Optional structured LLM adapter | Planned | CG-008 | Grounded AI |
| [CG-019](tickets/2026-09-10-CG-019.md) | Citation and evidence validation | Planned | CG-008, CG-010, CG-018 | Grounded AI |
| [CG-020](tickets/2026-09-10-CG-020.md) | Optional advisory AI enrichment | Planned | CG-014, CG-017, CG-018, CG-019 | Grounded AI |
| [CG-021](tickets/2026-09-10-CG-021.md) | Reproducible offline evaluation | Planned | CG-011, CG-012, CG-013, CG-020 | Grounded AI |
| [CG-022](tickets/2026-09-10-CG-022.md) | Adversarial and data-leakage regressions | Planned | CG-020, CG-021 | Grounded AI |
| [CG-023](tickets/2026-09-10-CG-023.md) | GitHub App authentication and authorization | Planned | CG-009, CG-014 | GitHub delivery |
| [CG-024](tickets/2026-09-10-CG-024.md) | Verified webhook and durable inbox | Planned | CG-015, CG-023 | GitHub delivery |
| [CG-025](tickets/2026-09-10-CG-025.md) | Durable worker and crash recovery | Planned | CG-015, CG-020, CG-024 | GitHub delivery |
| [CG-026](tickets/2026-09-10-CG-026.md) | Idempotent advisory GitHub Checks | Planned | CG-023, CG-025 | GitHub delivery |
| [CG-027](tickets/2026-09-10-CG-027.md) | Privacy-safe telemetry and health | Planned | CG-025, CG-026 | Release |
| [CG-028](tickets/2026-09-10-CG-028.md) | Container deployment and recovery runbook | Planned | CG-022, CG-027 | Release |
| [CG-029](tickets/2026-09-10-CG-029.md) | CI quality, security and evaluation gates | Planned | CG-021, CG-022, CG-028 | Release |
| [CG-030](tickets/2026-09-10-CG-030.md) | v1 acceptance, sandbox demo and handoff | Planned | CG-011, CG-012, CG-013, CG-021, CG-022, CG-026, CG-027, CG-028, CG-029 | Release |
| [CG-031](tickets/2026-09-13-CG-031.md) | Optional embeddings-based semantic retrieval | Planned | CG-016, CG-017, CG-020 | Post-v1 extensions |
| [CG-032](tickets/2026-09-13-CG-032.md) | LLM observability and cost accounting | Planned | CG-020, CG-027 | Post-v1 extensions |
| [CG-033](tickets/2026-09-13-CG-033.md) | Resilient provider calls: retries, backoff, cache | Planned | CG-018 | Post-v1 extensions |
| [CG-034](tickets/2026-09-13-CG-034.md) | Streaming advisory output over SSE | Planned | CG-014, CG-020 | Post-v1 extensions |
| [CG-035](tickets/2026-09-13-CG-035.md) | LLM guardrails: redaction and prompt-injection defense | Planned | CG-018, CG-019, CG-022 | Post-v1 extensions |
| [CG-036](tickets/2026-09-14-CG-036.md) | Read-only MCP server for ChangeGuard reports and evidence | Planned | CG-015, CG-019, CG-027 | Post-v1 extensions |
| [CG-037](tickets/2026-09-27-CG-037.md) | Evaluate MCP tool use with DeepEval | Planned | CG-021, CG-036 | Post-v1 extensions |

## Milestone exit criteria

1. Local vertical slice — CG-006: actual subprocess input/output and exit codes.
2. Evidence-backed analysis — CG-007–CG-015: authenticated analysis of bounded
   GitHub inputs with explicit coverage, scoped rules and durable PostgreSQL
   reports using async SQLAlchemy models and Alembic migrations.
3. Grounded AI — CG-016–CG-022: optional evidence-validated advice, offline
   quality measurements and adversarial regression evidence, not a prompt demo.
4. GitHub delivery — CG-023–CG-026: authorized signed events, durable retries
   and revision-correct advisory Checks under duplicate/racing deliveries.
5. Release — CG-027–CG-030: observable deployment, tested recovery, green CI
   and a real approved sandbox run. No release-complete claim without this proof.
6. Post-v1 extensions (opt-in) — CG-031–CG-037: production AI depth
   (semantic RAG, LLM observability/cost, provider resilience, streaming,
   guardrails, read-only MCP integration for report/evidence consumption and its
   DeepEval-based tool-use evaluation). These
   require accepted v1 prerequisites, add no v1 obligations, and stay single-host
   with no external managed vector DB or agent framework.

Dependencies, not table position, determine what can run in parallel. For
example corpus/retrieval and authentication can proceed once their prerequisites
are accepted; they need not wait for every preceding row.

## How to use each ticket

- These documents are requirements, not a plan to implement the whole backlog at
  once; tickets are delivered one tested increment at a time.
- Future paths, libraries and interfaces are proposals until introduced by the
  named ticket. Check current vendor documentation and repository conventions
  before adding a dependency; do not assume a suggested library is installed.
- Write one failing test, run it, implement the smallest behavior, then add the
  next scenario. Preserve existing public contracts unless a versioned change is
  explicitly specified. Keep commits focused.
- Run focused tests and all quality gates, and review every change independently.
  New integration/evaluation commands become runnable only when introduced.
- Record verification evidence, then update both this board and `backlog.json`.
  Do not mark work done from a successful write or mock alone.
- Branch each increment from `main`; do not stack on unmerged work.

Existing baseline gates (not evidence that future work already passes):

```bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests
uv lock --check
git diff --check
```

## Planning assumptions

- GitHub is the first provider; one authorized sandbox installation is sufficient
  for v1, but installation/repository authorization must still be enforced.
- HTTP, a durable worker and PostgreSQL are sufficient; persistence uses async
  SQLAlchemy and Alembic migrations. No broker is required if database job claims,
  leases and transactional enqueue are correctly tested against a real database.
- AI is optional and repository data leaves the service only with an explicit
  configured policy. Choose the provider/model and budget before live calls.
- Single-host container deployment is the proposed first operational target;
  no particular cloud, account or paid service has been selected.
- Each schema rule promises a named supported subset and visible unsupported
  coverage, not full standards compliance.
- Numerical limits, service SLOs and AI quality thresholds are frozen in their
  tickets before measurements, not invented after observing a convenient result.

# ADR 0002: Framework-free domain with validation at the boundaries

Status: Accepted

Date: 2026-09-10

## Context

ChangeGuard consumes several untrusted input shapes (GitHub REST payloads,
repository file content, HTTP requests, later webhooks and model output) and
produces a versioned public report. Analysis rules must stay deterministic,
fast to test and independent of transport, persistence and vendor SDKs, so the
rule set can grow without touching integration code.

## Decision

The code is layered by dependency direction, inward only:

| Layer | Package | Responsibility |
| --- | --- | --- |
| Domain | `domain/` | Frozen, slotted dataclasses with `__post_init__` invariants (`ChangedFile`, `ChangeSet`, findings, evidence, jobs). No framework imports. |
| Rules | `rules/`, `parsing/` | Pure functions `ChangeSet -> findings`, plus bounded, safe parsers for OpenAPI, Avro and Kubernetes documents. |
| Application | `application/` | Orchestrates rules and content fetching; rules are injected as callables, so no DI container is needed. |
| Adapters | `adapters/`, `api/`, `db/`, `repositories/`, `cli.py` | GitHub client, FastAPI endpoint, async SQLAlchemy persistence and CLI. Pydantic v2 validates every external payload here. |
| Public contract | `dto/`, `serialization.py`, `reporting.py` | Frozen Pydantic DTOs with an explicit `schema_version`; dedicated mappers translate domain objects to the wire format. |

Pydantic stays at the edges; the domain never depends on it. Immutable
collections are `tuple[...]` inside the domain and `list[...]` only at JSON
boundaries. `mypy --strict` is treated as the compiler for every layer.

## Consequences

- Rules are unit-tested with plain values, no mocks or network.
- A new input channel (webhook, MCP) adds an adapter and reuses the pipeline.
- The public report shape changes only through the DTO layer and its schema
  version, never as a side effect of a domain refactor.
- Mapping code is explicit and slightly more verbose than sharing one model
  across layers; that cost buys a stable contract and a framework-free core.

# ADR 0004: PostgreSQL as system of record, job queue, inbox and outbox

Status: Accepted — persistence in progress (CG-015); inbox, worker and outbox planned (CG-024–CG-026)

Date: 2026-09-10

## Context

GitHub delivers webhooks at least once, and deliveries can be duplicated,
reordered or retried. Analysis can take seconds, and publishing a Check Run is
an external side effect that can time out ambiguously. The target is a
single-host deployment operated by one person, so each extra piece of
infrastructure has a real operational cost.

## Decision

Use PostgreSQL 16 for all durable state, accessed through async SQLAlchemy 2.0
(`asyncpg`) with schema changes managed by Alembic migrations. No message
broker is introduced.

- **Jobs.** An analysis job is unique per repository, PR, base SHA, head SHA
  and analysis version. The state machine is explicit
  (`queued -> running -> completed | partial | failed`), and failure reasons
  are sanitized and bounded before they are stored.
- **Inbox.** Webhook deliveries are verified (HMAC over the raw body), recorded
  by delivery id and enqueued in the same transaction. The endpoint never uses
  in-process background tasks for accepted work.
- **Worker.** Jobs are claimed atomically with row locks, leases and heartbeats.
  Stale leases are recovered after a crash, concurrency is bounded and
  shutdown is graceful. Processing is at-least-once, so repeated attempts are
  made safe by uniqueness and idempotent writes.
- **Outbox.** The report and its publishing intent commit together. Publishing
  to GitHub Checks uses a deterministic `external_id`, verifies that the PR head
  SHA has not moved, and reconciles ambiguous POST results by reading back
  before retrying.

## Consequences

- One stateful component to deploy, back up and restore; transactional
  guarantees span jobs, reports, inbox and outbox.
- Throughput is bounded by the database, which is acceptable for PR-event
  volumes. A broker can be introduced later behind the same repository
  interfaces if measurements justify it.
- Integration tests run against a real PostgreSQL instance rather than an
  in-memory substitute.

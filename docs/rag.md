# Grounded advisory pipeline

The RAG pipeline retrieves repository context before requesting a generated
advisory, then validates the returned citations. Retrieval is a deterministic
lexical baseline; embeddings and a vector database are not required.

```text
SHA-bound content → bounded corpus → ranked context → structured model output
                                                    ↓
unchanged deterministic findings + validated advisory and explicit AI status
```

## Run the example

The bundled input contains synthetic documents and illustrative source identifiers.
It includes a pagination contract, an OpenAPI file and an unrelated storage ADR.
It does not fetch a real pull request or run deterministic rules; its findings are
explicit example inputs. The existing analysis CLI remains unchanged.

Inspect actual retrieval without a model:

```bash
uv run python -m changeguard.rag < examples/rag/review.json
```

The result selects `api/openapi.yaml` and `docs/api-pagination.md`, omits the
unrelated storage ADR as unmatched, and reports `ai.status: unavailable` with
reason `disabled`. This is a retrieval run, not live generation evidence.

With an installed, running Ollama server and an already available local model:

```bash
uv run python -m changeguard.rag --provider ollama --model qwen3.5:4b < examples/rag/review.json
```

The runner neither installs nor downloads models. Use a local structured-output
capable model and review the [data policy](ai-data-policy.md) before activation.
A live local run was verified on 2026-10-05 with Ollama 0.34.4 and
`qwen3.5:4b` (Q4_K_M). Model digest:
`d8b0f5e9760cd1682034f292d7ef72ec46f432149be0df7574bf2d6e92e38c04`.
The server used loopback only, cloud disabled, and an 8,192-token context.
The synthetic pagination example returned `ai.status: available`, one accepted
advisory, zero rejected items and citations to both selected sources. It
recommended reusing a previous-version cursor and verifying rollback decoding.
The original deterministic finding remained `high`. This verifies the local
example, not production pull-request analysis or general model accuracy.

For a session-only server, start Ollama in a separate terminal:

```bash
OLLAMA_NO_CLOUD=1 OLLAMA_HOST=127.0.0.1:11434 OLLAMA_CONTEXT_LENGTH=8192 ollama serve
```

Stop that foreground server with Ctrl+C. The adapter unloads the model after
each request. No login service is required. Download the model once if absent:

```bash
ollama pull qwen3.5:4b
```

Inspect `retrieval.selected` for ranking scores, reasons, source IDs and line
ranges. Inspect `report.ai` for accepted advisories, rejected counts, source IDs,
context completeness and explicit failure reasons. A rejected model answer is
never substituted with a canned answer.

## Boundaries and budgets

- Corpus: at most 32 eligible source revisions, 128 chunks, 8 KiB per chunk and
  256 KiB total selected UTF-8 text. Ordering is path, side and SHA.
- Normal lines split losslessly into chunks. A line larger than 8 KiB retains a
  valid UTF-8 prefix and stops that file; truncation is explicit. Source line
  ranges count LF boundaries, including CRLF, rather than Unicode separators.
- Retrieval: at most 12 chunks total, 4 per changed path and 24 KiB of selected
  text. Question-only retrieval uses the report-level limit. Ties are stable.
- LLM boundary: 60,000 request characters including schema, at most 4,096 output
  tokens, timeout at most 120 seconds, at most 32,768 response characters and
  128 KiB HTTP response bytes. The default request uses 2,048 output tokens and
  a 30-second timeout.
- Empty context prevents a provider call. Missing provenance, malformed text,
  exclusions, truncation and budget omissions are explicit in corpus metadata.

`FileContent.sha` remains the requested commit SHA. The GitHub reader now also
preserves `path` and the API's distinct `blob_sha`. Old content records without
these fields are not accepted as citable corpus sources. The explicit JSON runner
trusts caller-supplied provenance; it does not authenticate the provided SHA.

For reports carrying base/head SHAs, mismatched context revisions are removed
before a model request. Manual reports without revision SHAs use their explicitly
supplied source identities and remain marked partial in the runner.

## Application and HTTP integration

`application.rag.run_rag` composes extraction, retrieval, optional generation and
citation validation over an existing immutable `AnalysisReport` and supplied
`FileContent` records. It returns a new report and preserves findings unchanged.
Callers retain responsibility for obtaining source content through the authorized
GitHub reader and for configuring the provider.

The existing injected FastAPI pipeline can return this enriched report. Its
serializer adds the optional `ai` field only when enrichment was requested;
reports without enrichment retain their original shape. API integration tests
exercise the complete RAG path with a fake adapter. Production GitHub-to-API
composition remains a separate wiring concern.

## Evaluation

```bash
uv run pytest tests/unit/test_context_retrieval.py tests/unit/test_ai_validation.py -q
uv run pytest tests/integration/test_llm_provider.py tests/integration/test_api_ai_enrichment.py -q
```

The retrieval test includes explicit pagination, dependency-installation and
storage queries with expected top-ranked paths. Its fixture accuracy is 1.0;
this small regression fixture is not a benchmark of general retrieval quality.
Citation tests reject unknown IDs, mismatched revisions, incorrect ranges,
invented quotes, invalid severities and unsupported certainty. Mechanical
validation does not detect every semantic contradiction or prompt injection.

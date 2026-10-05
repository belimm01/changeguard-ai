# AI data policy

AI enrichment is opt-in. With no adapter configured, no provider request is made;
the report exposes an explicit `ai.status` such as `unavailable` or `no_context`.
Deterministic findings remain available regardless of provider failures.

The adapter receives only the explicit question, deterministic findings and
retrieved source chunks. Each chunk includes its repository path, base/head side,
commit SHA, blob SHA, source ID, line range and selected text. Environment
variables, credentials, local configuration and repository checkout access are
not part of the request. No tools or function calls are exposed to the model.

Operators must supply only approved, non-secret repository data. Path selection
is a relevance filter, not a secret scanner. A document can contain secrets even
when its path is eligible; do not send such content. The runner never discovers
or reads local repository files automatically. It reads only explicit JSON input.

The provided adapter targets Ollama's loopback endpoint at port 11434. Activation
requires an explicit provider and model. Use a local model and configure the
Ollama daemon to disable cloud functionality. Model names containing `cloud`
are rejected, but aliases and daemon configuration are controlled by the operator;
a loopback address alone does not establish where the daemon runs inference.
No model download, server startup, cloud API or paid request occurs automatically.
A different external provider requires a separate adapter and explicit approval
of provider, data and spending.

Input, output and HTTP response sizes are bounded. Requests have a timeout and
an output-token limit; failures expose fixed reason codes rather than raw provider
errors. Prompts and raw rejected model responses are not logged or persisted.
Accepted advisory text and citations are returned to the caller, who controls
report storage and retention.

Every displayed advisory must pass schema, source membership, SHA, range and
quote checks. These checks establish provenance, not semantic truth. Advisory
severity is separate from deterministic severity. AI cannot overwrite the
findings, and model failure is not evidence that a change is safe.

Implementation references:
[Ollama chat API](https://docs.ollama.com/api/chat) and
[structured outputs](https://docs.ollama.com/capabilities/structured-outputs).

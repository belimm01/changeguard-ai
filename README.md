ChangeGuard AI

ChangeGuard AI is an advisory pull-request change-impact analyzer. It reports
evidence-backed risks and recommendations; a human remains responsible for the
merge decision.

## v1 product boundary

ChangeGuard v1 is advisory and may be wrong. It reads GitHub pull-request
metadata, file paths, patches, repository file content, PR comments, and issue
text, then runs deterministic checks and may later add cited recommendations.
Its output is advice for a human reviewer, not a claim that a change is safe
or ready to merge.

V1 does not auto-merge, auto-approve, or auto-block pull requests, and it does
not execute repository code. Unsupported input formats and incomplete data are
reported as `partial` or `unsupported`, never as `safe`. The complete boundary
decision and threat controls are documented in
[`docs/adr/0001-system-boundary.md`](docs/adr/0001-system-boundary.md) and
[`docs/threat-model.md`](docs/threat-model.md).

Project tracking: [v1 roadmap and all tickets](docs/ROADMAP.md).
The roadmap separates accepted implementation from current and planned work.

## Local JSON analysis

Run the analyzer with a GitHub-shaped JSON document supplied on standard input:

```bash
uv run python -m changeguard < changed-files.json
```

Example input:

```json
[
  {
    "filename": "pyproject.toml",
    "status": "modified",
    "additions": 3,
    "deletions": 2,
    "patch": null
  }
]
```

The command writes one JSON array to standard output. A successful analysis
returns exit code `0`, whether findings are present or not. Malformed JSON,
invalid changed-file data, and input read or decoding failures leave standard
output empty, write a short diagnostic to standard error, and return exit code
`2`. The `--help` option displays usage, and unknown arguments are rejected.

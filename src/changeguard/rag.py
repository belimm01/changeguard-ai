"""Opt-in RAG runner over explicit, SHA-bound JSON input."""

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict
from typing import TextIO

import httpx
from pydantic import ValidationError

from changeguard.adapters.llm_provider import OllamaAdapter
from changeguard.application.ai_enrichment import enrich_report
from changeguard.application.corpus import extract_corpus
from changeguard.application.llm import DisabledLlmAdapter
from changeguard.application.retrieval import retrieve_context
from changeguard.domain.content import FileContent
from changeguard.domain.findings import RiskFinding
from changeguard.domain.reports import (
    AnalysisReport,
    Coverage,
    CoverageState,
    ReportStatus,
)
from changeguard.dto.rag import RagInputDto
from changeguard.reporting import serialize_report


def main(
    argv: Sequence[str] | None = None,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider", choices=("disabled", "ollama"), default="disabled"
    )
    parser.add_argument("--model", default="disabled")
    args = parser.parse_args(argv)
    if args.provider == "ollama" and args.model == "disabled":
        parser.error("--model is required with --provider ollama")
    stdin, stdout, stderr = (
        stdin or sys.stdin,
        stdout or sys.stdout,
        stderr or sys.stderr,
    )
    try:
        raw = stdin.read(1_048_577)
        if len(raw.encode("utf-8")) > 1_048_576:
            raise ValueError("input budget")
        data = RagInputDto.model_validate_json(raw)
        contents = tuple(
            FileContent(
                s.commit_sha,
                s.text,
                s.side,
                len(s.text.encode("utf-8")),
                s.path,
                s.blob_sha,
            )
            for s in data.sources
        )
        corpus = extract_corpus(contents)
        findings = tuple(
            RiskFinding(f.rule_id, f.level, f.summary, tuple(f.evidence_paths))
            for f in data.findings
        )
        context = retrieve_context(
            corpus, tuple(data.changed_paths), findings, question=data.question
        )
        report = AnalysisReport(
            "rag-v1",
            "explicit-input",
            "manual",
            None,
            None,
            ReportStatus.PARTIAL,
            findings,
            (),
            (
                Coverage(
                    "explicit-input",
                    "manual",
                    CoverageState.PARTIAL,
                    "Caller-supplied example facts; no live pull request analysis",
                ),
            ),
        )

        async def generate() -> AnalysisReport:
            if args.provider == "disabled":
                return await enrich_report(
                    report,
                    context,
                    DisabledLlmAdapter(),
                    model=args.model,
                    question=data.question,
                )
            async with httpx.AsyncClient(trust_env=False) as client:
                return await enrich_report(
                    report,
                    context,
                    OllamaAdapter(client),
                    model=args.model,
                    question=data.question,
                )

        enriched = asyncio.run(generate())
        result = {
            "provider": args.provider,
            "corpus": {
                "chunks": len(corpus.chunks),
                "bytes": corpus.total_bytes,
                "partial": corpus.partial,
                "omitted_files": corpus.omitted_files,
                "excluded_files": corpus.excluded_files,
                "diagnostics": [asdict(d) for d in corpus.diagnostics],
            },
            "retrieval": {
                "selected": [
                    {
                        "source_id": i.chunk.source_id,
                        "path": i.chunk.path,
                        "start_line": i.chunk.start_line,
                        "end_line": i.chunk.end_line,
                        "score": i.score,
                        "reasons": i.reasons,
                    }
                    for i in context.items
                ],
                "omitted_chunks": context.omitted_chunks,
                "unmatched_chunks": context.unmatched_chunks,
                "bytes": context.total_bytes,
            },
            "report": serialize_report(enriched),
        }
    except (ValueError, UnicodeError, OSError, ValidationError):
        print("invalid RAG input", file=stderr)
        return 2
    json.dump(result, stdout, indent=2)
    stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from changeguard.application.ai_enrichment import enrich_report
from changeguard.application.corpus import extract_corpus
from changeguard.application.llm import LlmAdapter
from changeguard.application.retrieval import retrieve_context
from changeguard.domain.content import FileContent, RemoteContentResult
from changeguard.domain.reports import AnalysisReport


async def run_rag(
    report: AnalysisReport,
    contents: tuple[FileContent | RemoteContentResult, ...],
    adapter: LlmAdapter | None = None,
    *,
    changed_paths: tuple[str, ...] = (),
    question: str = "Explain the impact and suggest tests.",
    model: str = "disabled",
) -> AnalysisReport:
    corpus = extract_corpus(contents)
    context = retrieve_context(
        corpus, changed_paths, report.findings, question=question
    )
    return await enrich_report(report, context, adapter, model=model, question=question)

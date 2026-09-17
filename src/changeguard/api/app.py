"""FastAPI app factory for the authenticated analysis endpoint.

The HTTP layer only authenticates, validates, bounds and delegates. The analysis
pipeline is injected so tests use fakes without network or GitHub credentials.
This endpoint is not a GitHub webhook and verifies no webhook signatures.
"""

from collections.abc import Callable

from fastapi import Depends, FastAPI, HTTPException, Request, status

from changeguard.api.auth import make_api_key_auth
from changeguard.api.models import AnalysisRequest
from changeguard.config import ApiSettings
from changeguard.domain.reports import AnalysisReport
from changeguard.reporting import serialize_report

AnalysisPipeline = Callable[[AnalysisRequest], AnalysisReport]


def create_app(settings: ApiSettings, pipeline: AnalysisPipeline) -> FastAPI:
    app = FastAPI(title="ChangeGuard analysis API")
    require_api_key = make_api_key_auth(settings)

    def enforce_body_limit(request: Request) -> None:
        content_length = request.headers.get("content-length")
        if (
            content_length is not None
            and content_length.isdigit()
            and int(content_length) > settings.max_request_bytes
        ):
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="request body too large",
            )

    @app.post("/analyze")
    def analyze(
        payload: AnalysisRequest,
        _limit: None = Depends(enforce_body_limit),
        _auth: None = Depends(require_api_key),
    ) -> dict[str, object]:
        try:
            report = pipeline(payload)
        except HTTPException:
            raise
        except Exception:  # noqa: BLE001 -- boundary sanitizes all failures
            # Never leak tracebacks, tokens, patches or repository content.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal analysis error",
            ) from None
        return serialize_report(report)

    return app

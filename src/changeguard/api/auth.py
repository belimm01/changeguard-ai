"""Shared-secret authentication dependency for the analysis endpoint."""

import hmac
from collections.abc import Callable

from fastapi import Header, HTTPException, status

from changeguard.config import ApiSettings


def make_api_key_auth(settings: ApiSettings) -> Callable[[str | None], None]:
    """Build a FastAPI dependency that checks a configured shared secret.

    The secret is supplied via settings (outside source code) and is never
    echoed into responses or error details.
    """

    expected = settings.secret.get_secret_value()

    def require_api_key(
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    ) -> None:
        if x_api_key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="missing API key"
            )
        if not hmac.compare_digest(x_api_key, expected):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="invalid API key"
            )

    return require_api_key

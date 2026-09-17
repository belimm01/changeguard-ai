from pydantic import BaseModel, ConfigDict, SecretStr


class GitHubSettings(BaseModel):
    model_config = ConfigDict(frozen=True)
    base_url: str = "https://api.github.com"
    token: SecretStr
    timeout_s: float = 10.0
    max_pages: int = 10
    max_files: int = 300
    max_retries: int = 3


class ApiSettings(BaseModel):
    model_config = ConfigDict(frozen=True)
    secret: SecretStr
    max_request_bytes: int = 65_536
    timeout_s: float = 30.0
    max_findings: int = 100


class DatabaseSettings(BaseModel):
    model_config = ConfigDict(frozen=True)
    url: SecretStr
    pool_size: int = 5
    max_overflow: int = 10

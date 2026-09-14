from pydantic import BaseModel, ConfigDict, SecretStr


class GitHubSettings(BaseModel):
    model_config = ConfigDict(frozen=True)
    base_url: str = "https://api.github.com"
    token: SecretStr
    timeout_s: float = 10.0
    max_pages: int = 10
    max_files: int = 300
    max_retries: int = 3

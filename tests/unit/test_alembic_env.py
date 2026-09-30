import os
import subprocess
import sys
from pathlib import Path


def test_env_py() -> None:
    child_env = os.environ.copy()
    child_env["CHANGEGUARD_TEST_DB_URL"] = (
        "postgresql+asyncpg://fake:fake%40value@localhost/example"
    )
    project_root = Path(__file__).resolve().parents[2]

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        env=child_env,
        capture_output=True,
        cwd=project_root,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr

from pathlib import Path
import tomllib


def get_project_version() -> str:
    pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)
        version: str | None = pyproject.get("project", {}).get("version")
        if version is None:
            return "unknown"
        return version

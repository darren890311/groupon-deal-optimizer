import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_HTML_DIR = DATA_DIR / "raw_html"
OUTPUT_DIR = ROOT / "output"
DUCKDB_PATH = DATA_DIR / "groupon.duckdb"

DATA_DIR.mkdir(parents=True, exist_ok=True)
RAW_HTML_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Missing env var {name}. Copy .env.example to .env and fill it in."
        )
    return value


ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")

PROPOSAL_MODEL = "claude-opus-4-7"
RESEARCH_MODEL = "claude-sonnet-4-6"

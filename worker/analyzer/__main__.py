"""CLI for fast local iteration:

    cd worker && python -m analyzer <groupon-url> [--no-cache]

By default it reuses pre-scraped HTML under ../data/raw_html (keyed by slug),
so you can iterate on parsing/discount logic without hitting Groupon. Pass
--no-cache to force a live Playwright scrape.
"""

import json
import sys
from pathlib import Path

from .pipeline import analyze

# repo_root/worker/analyzer/__main__.py → repo_root/data/raw_html
_DEFAULT_CACHE = Path(__file__).resolve().parents[2] / "data" / "raw_html"


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--no-cache"]
    if not args:
        print("usage: python -m analyzer <groupon-url> [--no-cache]", file=sys.stderr)
        return 2

    url = args[0]
    cache_dir = None if "--no-cache" in sys.argv else _DEFAULT_CACHE

    result = analyze(url, cache_dir=cache_dir)
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

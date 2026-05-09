import argparse
import sys
from pathlib import Path

from src import pipeline
from src.config import ANTHROPIC_API_KEY, TAVILY_API_KEY


def main() -> int:
    parser = argparse.ArgumentParser(prog="src", description="Groupon deal-page optimizer")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_p = sub.add_parser("run", help="Process URLs end-to-end")
    run_p.add_argument("--urls", type=Path, default=Path("deals.txt"), help="Path to URL list")
    run_p.add_argument("--limit", type=int, default=None, help="Process at most N URLs")
    run_p.add_argument("--start", type=int, default=0, help="Start index in URL list (0-based)")
    run_p.add_argument("--force", action="store_true", help="Re-scrape and re-process even if outputs exist")
    run_p.add_argument("--no-skip", action="store_true", help="Don't skip URLs whose proposal.md already exists")

    one_p = sub.add_parser("one", help="Process a single URL")
    one_p.add_argument("url", help="Groupon deal URL")
    one_p.add_argument("--force", action="store_true")

    refresh_p = sub.add_parser(
        "refresh-audits",
        help="Re-parse cached desktop HTML, scrape mobile, re-render audit.json/md (no LLM calls)",
    )
    refresh_p.add_argument("--urls", type=Path, default=Path("deals.txt"))
    refresh_p.add_argument("--limit", type=int, default=None)
    refresh_p.add_argument("--no-mobile", action="store_true", help="Skip mobile fetch")

    args = parser.parse_args()

    if not ANTHROPIC_API_KEY:
        print("ERROR: ANTHROPIC_API_KEY not set (see .env.example)", file=sys.stderr)
        return 2
    if not TAVILY_API_KEY:
        print("WARNING: TAVILY_API_KEY not set — research stage will produce no findings", file=sys.stderr)

    if args.cmd == "refresh-audits":
        urls = pipeline.read_urls(args.urls)
        if args.limit:
            urls = urls[: args.limit]
        ok = errors = 0
        for url in urls:
            slug = url.split("?")[0].rstrip("/").split("/")[-1]
            print(f"[{slug}] refreshing audit (mobile={'no' if args.no_mobile else 'yes'})...")
            r = pipeline.refresh_audit(url, fetch_mobile=not args.no_mobile)
            if r["status"] == "ok":
                ok += 1
            else:
                errors += 1
                print(f"  ERROR: {r}")
        print(f"\n=== Refresh summary: {ok} ok, {errors} errors ===")
        return 0 if errors == 0 else 1

    if args.cmd == "one":
        result = pipeline.process_url(args.url, force=args.force, skip_existing=False)
        print(result)
        return 0 if result["status"] == "ok" else 1

    if args.cmd == "run":
        urls = pipeline.read_urls(args.urls)
        if args.start:
            urls = urls[args.start :]
        if args.limit:
            urls = urls[: args.limit]
        results = []
        for url in urls:
            try:
                r = pipeline.process_url(url, force=args.force, skip_existing=not args.no_skip)
            except Exception as e:
                r = {"slug": url, "status": "error", "stage": "pipeline", "error": str(e)}
                print(f"  ERROR: {e}")
            results.append(r)
        ok = sum(1 for r in results if r["status"] == "ok")
        skipped = sum(1 for r in results if r["status"] == "skipped")
        errors = [r for r in results if r["status"] == "error"]
        print(f"\n=== Summary: {ok} ok, {skipped} skipped, {len(errors)} errors ===")
        for r in errors:
            print(f"  {r.get('slug')}: {r.get('stage')} — {r.get('error')}")
        return 0 if not errors else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

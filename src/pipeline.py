from pathlib import Path

import anthropic

from src import render, research, scrape, storage, synthesize
from src.config import OUTPUT_DIR
from src.parse import parse_audit


def process_url(url: str, *, force: bool = False, skip_existing: bool = True) -> dict:
    slug = scrape.slug_from_url(url)
    out_dir = OUTPUT_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    if skip_existing and (out_dir / "proposal.md").exists() and not force:
        return {"slug": slug, "status": "skipped", "reason": "proposal.md exists"}

    print(f"\n[{slug}] {url}")
    print("  scraping...")
    try:
        html = scrape.fetch_html(url, slug, force=force)
    except Exception as e:
        return {"slug": slug, "status": "error", "stage": "scrape", "error": str(e)}

    print("  parsing...")
    try:
        audit = parse_audit(html, url)
    except Exception as e:
        return {"slug": slug, "status": "error", "stage": "parse", "error": str(e)}

    if not audit.get("title"):
        return {"slug": slug, "status": "error", "stage": "parse", "error": "no title — likely blocked or empty page"}

    with storage.connect() as conn:
        storage.upsert_deal(conn, slug, url, audit)
    render.write_audit(out_dir, audit)

    client = anthropic.Anthropic()

    print("  generating research queries...")
    queries = research.generate_queries(client, audit)

    print(f"  running Tavily searches ({len(queries)} queries)...")
    findings = research.run_tavily_searches(queries)

    print(f"  extracting review themes ({len(findings)} findings)...")
    themes = research.extract_review_themes(client, audit, findings)
    themes_dict = themes.model_dump() if themes else None

    with storage.connect() as conn:
        storage.insert_findings(conn, slug, findings)
    render.write_research(out_dir, findings, themes_dict)

    print("  synthesizing proposal...")
    proposal = synthesize.synthesize_proposal(client, audit, findings, themes_dict)

    with storage.connect() as conn:
        storage.insert_recommendations(
            conn, slug, [r.model_dump() for r in proposal.recommendations]
        )
    render.write_proposal(out_dir, proposal)

    return {
        "slug": slug,
        "status": "ok",
        "rec_count": len(proposal.recommendations),
        "findings_count": len(findings),
    }


def read_urls(path: Path) -> list[str]:
    urls = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        urls.append(s)
    return urls

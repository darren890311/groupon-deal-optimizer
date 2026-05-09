import json
from contextlib import contextmanager
from typing import Any, Iterator

import duckdb

from src.config import DUCKDB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS deals (
    slug VARCHAR PRIMARY KEY,
    url VARCHAR NOT NULL,
    title VARCHAR,
    subtitle VARCHAR,
    merchant_name VARCHAR,
    category VARCHAR,
    city VARCHAR,
    region VARCHAR,
    description TEXT,
    fine_print TEXT,
    rating DOUBLE,
    review_count INTEGER,
    bought_label VARCHAR,
    image_count INTEGER,
    raw_audit_json TEXT,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prices (
    slug VARCHAR,
    option_idx INTEGER,
    option_label VARCHAR,
    original_price DOUBLE,
    deal_price DOUBLE,
    discount_pct DOUBLE,
    PRIMARY KEY (slug, option_idx)
);

CREATE TABLE IF NOT EXISTS reviews (
    slug VARCHAR,
    review_idx INTEGER,
    rating DOUBLE,
    quote TEXT,
    author VARCHAR,
    review_date VARCHAR,
    PRIMARY KEY (slug, review_idx)
);

CREATE TABLE IF NOT EXISTS research_findings (
    slug VARCHAR,
    finding_idx INTEGER,
    category VARCHAR,
    query VARCHAR,
    source_url VARCHAR,
    source_title VARCHAR,
    snippet TEXT,
    PRIMARY KEY (slug, finding_idx)
);

CREATE TABLE IF NOT EXISTS recommendations (
    slug VARCHAR,
    rec_idx INTEGER,
    field VARCHAR,
    current_value TEXT,
    proposed_value TEXT,
    rationale TEXT,
    evidence TEXT,
    priority INTEGER,
    expected_impact VARCHAR,
    PRIMARY KEY (slug, rec_idx)
);
"""


@contextmanager
def connect() -> Iterator[duckdb.DuckDBPyConnection]:
    conn = duckdb.connect(str(DUCKDB_PATH))
    try:
        conn.execute(SCHEMA)
        yield conn
    finally:
        conn.close()


def upsert_deal(conn: duckdb.DuckDBPyConnection, slug: str, url: str, audit: dict[str, Any]) -> None:
    conn.execute("DELETE FROM deals WHERE slug = ?", [slug])
    conn.execute(
        """
        INSERT INTO deals (slug, url, title, subtitle, merchant_name, category, city, region,
                           description, fine_print, rating, review_count, bought_label,
                           image_count, raw_audit_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            slug,
            url,
            audit.get("title"),
            audit.get("subtitle"),
            audit.get("merchant_name"),
            audit.get("category"),
            audit.get("city"),
            audit.get("region"),
            audit.get("description"),
            audit.get("fine_print"),
            audit.get("rating"),
            audit.get("review_count"),
            audit.get("bought_label"),
            audit.get("image_count"),
            json.dumps(audit, ensure_ascii=False),
        ],
    )

    conn.execute("DELETE FROM prices WHERE slug = ?", [slug])
    for i, p in enumerate(audit.get("prices", []) or []):
        conn.execute(
            """
            INSERT INTO prices (slug, option_idx, option_label, original_price, deal_price, discount_pct)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [slug, i, p.get("label"), p.get("original_price"), p.get("deal_price"), p.get("discount_pct")],
        )

    conn.execute("DELETE FROM reviews WHERE slug = ?", [slug])
    for i, r in enumerate(audit.get("reviews", []) or []):
        conn.execute(
            """
            INSERT INTO reviews (slug, review_idx, rating, quote, author, review_date)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [slug, i, r.get("rating"), r.get("quote"), r.get("author"), r.get("date")],
        )


def insert_findings(
    conn: duckdb.DuckDBPyConnection, slug: str, findings: list[dict[str, Any]]
) -> None:
    conn.execute("DELETE FROM research_findings WHERE slug = ?", [slug])
    for i, f in enumerate(findings):
        conn.execute(
            """
            INSERT INTO research_findings (slug, finding_idx, category, query, source_url, source_title, snippet)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [slug, i, f.get("category"), f.get("query"), f.get("source_url"), f.get("source_title"), f.get("snippet")],
        )


def insert_recommendations(
    conn: duckdb.DuckDBPyConnection, slug: str, recs: list[dict[str, Any]]
) -> None:
    conn.execute("DELETE FROM recommendations WHERE slug = ?", [slug])
    for i, r in enumerate(recs):
        conn.execute(
            """
            INSERT INTO recommendations (slug, rec_idx, field, current_value, proposed_value,
                                         rationale, evidence, priority, expected_impact)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                slug, i,
                r.get("field"), r.get("current_value"), r.get("proposed_value"),
                r.get("rationale"), r.get("evidence"), r.get("priority"), r.get("expected_impact"),
            ],
        )

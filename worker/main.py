"""FastAPI wrapper around the analyzer pipeline.

    POST /analyze  { "url": "https://www.groupon.com/deals/<slug>" }  -> DealAnalysis
    GET  /healthz

The endpoint is a sync `def` on purpose: FastAPI runs sync routes in a worker
thread, which is where Playwright's sync API must live (it refuses to run inside
an asyncio event loop). Anthropic + Tavily clients are built once and shared.
"""

import os

import anthropic
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from tavily import TavilyClient

from analyzer.config import ANTHROPIC_API_KEY, TAVILY_API_KEY
from analyzer.models import DealAnalysis
from analyzer.pipeline import analyze

app = FastAPI(title="Groupon Deal Analyzer", version="2.0")

_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGIN", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Shared clients (None if the key is missing - the pipeline degrades gracefully).
_anthropic = anthropic.Anthropic() if ANTHROPIC_API_KEY else None
_tavily = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None


class AnalyzeRequest(BaseModel):
    url: str
    html: str | None = None  # extension supplies the rendered page; None → Playwright


@app.get("/healthz")
def healthz() -> dict:
    return {
        "status": "ok",
        "anthropic": _anthropic is not None,
        "tavily": _tavily is not None,
    }


@app.post("/analyze", response_model=DealAnalysis)
def analyze_deal(req: AnalyzeRequest) -> DealAnalysis:
    url = req.url.strip()
    if "groupon.com/deals/" not in url:
        raise HTTPException(status_code=422, detail="Not a Groupon deal URL (expected groupon.com/deals/<slug>).")

    try:
        result = analyze(url, html=req.html, anthropic_client=_anthropic, tavily_client=_tavily)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Analysis failed while fetching/parsing the deal: {e}")

    # A real deal page always yields a title plus at least prices or a rating.
    # If none of that came through, the scrape was almost certainly blocked or
    # served an empty/challenge page - surface an error so the gateway returns it
    # (and does NOT cache a "no data" result for 24h). A retry usually succeeds.
    no_signal = not result.deal.prices and result.reputation.groupon_rating is None
    if not result.deal.title or no_signal:
        raise HTTPException(
            status_code=502,
            detail="Could not read the deal page - it may be temporarily blocked. Please try again in a moment.",
        )
    return result

"""Worker config — env keys and model ids. Loaded from .env in dev."""

import os

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")

# Single-deal live tool: Sonnet everywhere (latency/cost over Opus).
SONNET_MODEL = "claude-sonnet-4-6"

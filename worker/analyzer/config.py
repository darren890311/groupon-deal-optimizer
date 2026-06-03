"""Worker config — env keys and model ids. Loaded from .env in dev."""

import os

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")
YELP_API_KEY = os.environ.get("YELP_API_KEY", "")

# Model split: Sonnet for the final verdict (the core product output); Haiku for
# the lighter judgments (competitor comparability, reputation summary) — it's much
# faster and these are simple structured calls, so it cuts end-to-end latency.
SONNET_MODEL = "claude-sonnet-4-6"
HAIKU_MODEL = "claude-haiku-4-5-20251001"

"""Advertised-vs-actual discount logic — the headline signal of the product.

Groupon titles routinely claim "Up to X% Off" while the displayed price tiers
discount far less (or not at all). We parse the claim, compute the real max
discount across tiers, and classify the gap.
"""

import re
from typing import Any

from .models import DiscountVerdict

_UP_TO_RE = re.compile(r"up\s+to\s+(\d{1,3})\s*%\s*off", re.IGNORECASE)

# How many percentage points the claim may exceed reality before it's "exaggerated".
EXAGGERATION_THRESHOLD_PP = 10.0


def parse_advertised_discount(title: str | None) -> float | None:
    """Pull the headline "Up to X% Off" claim from the title, if present."""
    if not title:
        return None
    m = _UP_TO_RE.search(title)
    return float(m.group(1)) if m else None


def actual_max_discount(prices: list[dict[str, Any]]) -> float | None:
    """The largest real discount across the displayed price tiers."""
    vals = [p.get("discount_pct") for p in prices if p.get("discount_pct") is not None]
    return max(vals) if vals else None


def classify(advertised: float | None, actual: float | None) -> DiscountVerdict:
    actual_v = actual or 0.0
    # An "Up to X%" claim that materially overshoots reality is the worst case —
    # check it before "none" so a 30%-claim-on-0%-actual reads as exaggerated.
    if advertised is not None and advertised - actual_v >= EXAGGERATION_THRESHOLD_PP:
        return "exaggerated"
    if actual_v < 1.0:
        return "none"
    return "honest"

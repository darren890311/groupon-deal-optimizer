"""The DealAnalysis contract — shared shape across Python worker → Go → Vue.

All free-text fields are produced in English (user-facing).
Sections beyond `deal` default to empty so early milestones can emit a valid
partial object before the later stages (competitors, reputation, verdict) land.
"""

from typing import Literal

from pydantic import BaseModel, Field

DiscountVerdict = Literal["honest", "exaggerated", "none"]
GapVerdict = Literal["external_higher", "external_lower", "consistent", "divergent", "insufficient"]
WorthBuying = Literal["yes", "caution", "no"]
BadgeStatus = Literal["ok", "warn", "bad"]


class PriceTier(BaseModel):
    label: str | None = None
    original: float | None = None
    deal: float | None = None
    discount_pct: float | None = None


class Deal(BaseModel):
    url: str
    title: str | None = None
    merchant: str | None = None
    city: str | None = None
    category: str | None = None
    advertised_discount_pct: float | None = None
    actual_max_discount_pct: float | None = None
    discount_verdict: DiscountVerdict = "none"
    prices: list[PriceTier] = Field(default_factory=list)


class Reputation(BaseModel):
    groupon_rating: float | None = None
    groupon_reviews: int | None = None
    google_rating: float | None = None
    google_reviews: int | None = None
    yelp_rating: float | None = None
    yelp_reviews: int | None = None
    # True when the merchant is a multi-location chain (e.g. AMC, Massage Envy):
    # there is no single external rating, so Google/Yelp vary by location.
    chain: bool = False
    gap_verdict: GapVerdict = "insufficient"  # Groupon vs the primary external (Google preferred)
    summary: str = ""


ServiceMatch = Literal["same", "similar", "different"]


class Competitor(BaseModel):
    merchant: str | None = None
    title: str | None = None
    price: float | None = None
    discount_pct: float | None = None
    url: str | None = None
    cheaper: bool | None = None
    # How comparable this competitor's service is to the analyzed deal.
    match: ServiceMatch | None = None
    difference_note: str = ""


class DirectBooking(BaseModel):
    cheaper_than_groupon: bool | None = None
    direct_price: float | None = None
    note: str = ""
    source_url: str | None = None


class Badge(BaseModel):
    type: str
    status: BadgeStatus
    label: str


class Verdict(BaseModel):
    badges: list[Badge] = Field(default_factory=list)
    worth_buying: WorthBuying = "caution"
    one_liner: str = ""
    recommended_action: str = ""


class Meta(BaseModel):
    analyzed_at: str
    cache_expires_at: str | None = None


class DealAnalysis(BaseModel):
    deal: Deal
    reputation: Reputation = Field(default_factory=Reputation)
    competitors: list[Competitor] = Field(default_factory=list)
    direct_booking: DirectBooking = Field(default_factory=DirectBooking)
    verdict: Verdict = Field(default_factory=Verdict)
    meta: Meta

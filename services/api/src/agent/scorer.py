"""
Weighted multi-criteria scoring for the autonomous buyer agent.

Evaluates each listing against a buyer's preferences and produces
a ScoreBreakdown with an overall weighted total.
"""

from typing import List, Optional, Tuple

from models.entities.couchbase.agent_runs import ScoreBreakdown
from models.entities.couchbase.listings import Listing
from models.entities.couchbase.users import BuyerProfile

# Scoring weights from spec
WEIGHTS = {
    "project_type_match": 0.30,
    "price_score": 0.25,
    "vintage_score": 0.20,
    "co_benefit_score": 0.15,
    "verification_score": 0.10,
}


def _score_project_type(
    listing: Listing, criteria: dict, profile: Optional[BuyerProfile]
) -> float:
    preferred = criteria.get("preferred_types", [])
    if not preferred and profile:
        preferred = profile.preferred_project_types
    if not preferred:
        return 0.5  # no preference → neutral
    return 1.0 if listing.data.project_type in preferred else 0.0


def _score_price(listing: Listing, criteria: dict) -> float:
    max_price = criteria.get("max_price_eur")
    if not max_price or max_price <= 0:
        return 0.5
    price = listing.data.price_per_tonne_eur
    if price > max_price:
        return 0.0
    # Linear: cheaper is better. At max_price → 0.5, at 0 → 1.0
    return 1.0 - (price / max_price) * 0.5


def _score_vintage(listing: Listing, criteria: dict) -> float:
    min_vintage = criteria.get("min_vintage_year", 2020)
    vintage = listing.data.vintage_year
    if not vintage:
        return 0.3  # unknown vintage → low-ish
    if vintage < min_vintage:
        return 0.0
    # Newer is better: scale from 2018 to 2025
    return min(1.0, (vintage - 2018) / 7)


def _score_co_benefits(
    listing: Listing, criteria: dict, profile: Optional[BuyerProfile]
) -> float:
    preferred = criteria.get("preferred_co_benefits", [])
    if not preferred:
        return 0.5  # no preference → neutral
    if not listing.data.co_benefits:
        return 0.0
    overlap = set(b.lower() for b in listing.data.co_benefits) & set(
        b.lower() for b in preferred
    )
    return len(overlap) / len(preferred)


def _score_verification(listing: Listing) -> float:
    status = listing.data.verification_status
    if status == "verified":
        return 1.0
    if status == "pending":
        return 0.3
    return 0.0


def _quantity_available(listing: Listing) -> float:
    return (
        listing.data.quantity_tonnes
        - listing.data.quantity_reserved
        - listing.data.quantity_sold
    )


def score_listing(
    listing: Listing,
    criteria: dict,
    profile: Optional[BuyerProfile] = None,
) -> ScoreBreakdown:
    """Score a single listing against buyer criteria."""
    pt = _score_project_type(listing, criteria, profile)
    pr = _score_price(listing, criteria)
    vi = _score_vintage(listing, criteria)
    cb = _score_co_benefits(listing, criteria, profile)
    ve = _score_verification(listing)
    avail = _quantity_available(listing)

    # Quantity fit: 1.0 if >= 100t available, scale down below
    qf = min(1.0, avail / 100.0) if avail > 0 else 0.0

    total = round(
        pt * WEIGHTS["project_type_match"]
        + pr * WEIGHTS["price_score"]
        + vi * WEIGHTS["vintage_score"]
        + cb * WEIGHTS["co_benefit_score"]
        + ve * WEIGHTS["verification_score"],
        4,
    )

    return ScoreBreakdown(
        listing_id=listing.id,
        project_type_match=round(pt, 4),
        price_score=round(pr, 4),
        vintage_score=round(vi, 4),
        co_benefit_score=round(cb, 4),
        verification_score=round(ve, 4),
        quantity_fit=round(qf, 4),
        total=total,
    )


def rank_listings(
    listings: List[Listing],
    criteria: dict,
    profile: Optional[BuyerProfile] = None,
) -> List[Tuple[Listing, ScoreBreakdown]]:
    """Score all listings and return sorted by total score descending."""
    scored = []
    for listing in listings:
        breakdown = score_listing(listing, criteria, profile)
        scored.append((listing, breakdown))
    scored.sort(key=lambda x: x[1].total, reverse=True)
    return scored

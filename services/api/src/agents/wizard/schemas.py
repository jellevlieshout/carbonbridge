"""
Strict Pydantic output schemas for the Pydantic AI wizard agent.

Tightened so that transition signals are boolean flags (not free-text strings)
wherever possible, reducing the model's ability to produce ambiguous values that
exhaust structured-output retries.
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


# ── Transition step literals ───────────────────────────────────────────────
WizardNextStep = Literal[
    "profile_check",
    "onboarding",
    "footprint_estimate",
    "preference_elicitation",
    "listing_search",
    "recommendation",
    "order_creation",
    "complete",
    "autobuy_waitlist",
]


class ProfileIntentOutput(BaseModel):
    """Returned by the agent during profile_check / onboarding steps."""

    response_text: str = Field(
        description=(
            "Plain-language reply. Max 3 sentences. "
            "If sector and employees are now known, end with: "
            "'If anything looks wrong, just let me know.'"
        )
    )
    sector: Optional[str] = Field(
        None,
        description="Sector slug (e.g. 'manufacturing', 'technology'). None if not yet determined.",
    )
    employees: Optional[int] = Field(
        None,
        description="Employee count if the buyer mentioned it. None if not yet known.",
    )
    motivation: Optional[Literal["compliance", "esg_reporting", "brand", "personal"]] = Field(
        None, description="Primary offset motivation if mentioned."
    )
    profile_complete: bool = Field(
        False,
        description=(
            "Set True when BOTH sector and employees are known, "
            "regardless of whether the buyer sent an explicit confirmation."
        ),
    )
    advance_to_footprint: bool = Field(
        False,
        description=(
            "Set True to advance to the footprint step. "
            "Should be True whenever profile_complete is True."
        ),
    )


class FootprintOutput(BaseModel):
    """Returned by the agent during footprint_estimate step."""

    response_text: str = Field(
        description=(
            "Plain-language footprint explanation with analogy. "
            "End with: 'Does that sound right, or would you like to adjust it?'"
        )
    )
    accepted_tonnes: Optional[float] = Field(
        None,
        description="Final tonne estimate the buyer accepted (from tool or override). None if still discussing.",
    )
    advance_to_preferences: bool = Field(
        False,
        description=(
            "Set True to move to the preference step. "
            "Set True when the buyer has confirmed the footprint estimate or shown willingness to proceed."
        ),
    )


class PreferenceOutput(BaseModel):
    """Returned by the agent during preference_elicitation step."""

    response_text: str = Field(
        description="Plain-language acknowledgement and transition sentence."
    )
    project_types: List[str] = Field(
        default_factory=list,
        description="Project types selected (e.g. 'forestry', 'renewable_energy', 'cookstoves').",
    )
    regions: List[str] = Field(
        default_factory=list,
        description="Preferred geographic regions; empty list means no preference.",
    )
    max_price_eur: Optional[float] = Field(
        None,
        description="Budget ceiling per tonne in EUR if stated.",
    )
    co_benefits: List[str] = Field(
        default_factory=list,
        description="Co-benefit keywords mentioned.",
    )
    advance_to_search: bool = Field(
        False,
        description=(
            "Set True to advance to listing search. "
            "Set True once at least one project type preference is captured."
        ),
    )


class RecommendationOutput(BaseModel):
    """Returned during listing_search / recommendation steps."""

    response_text: str = Field(
        description=(
            "Plain-language presentation of listings with a 'why we picked this' blurb per listing. "
            "If no listings were found, explain clearly and offer broadening search or a waitlist."
        )
    )
    listings_found: bool = Field(
        True,
        description="False when the tool returned zero results.",
    )
    selected_listing_id: Optional[str] = Field(
        None,
        description="Listing ID the buyer chose, if they made a selection.",
    )
    buyer_wants_broader_search: bool = Field(
        False,
        description="True when the buyer explicitly asks to see more or different options.",
    )
    buyer_declined_all: bool = Field(
        False,
        description="True when the buyer explicitly declines all shown options.",
    )
    buyer_wants_autobuy_waitlist: bool = Field(
        False,
        description="True when buyer agrees to be notified / have the autonomous agent buy later.",
    )
    advance_to_order: bool = Field(
        False,
        description="Set True when selected_listing_id is set.",
    )


class OrderOutput(BaseModel):
    """Returned during order_creation step."""

    response_text: str = Field(
        description="Order summary in plain language ready for buyer confirmation."
    )
    order_confirmed: bool = Field(
        False,
        description="True when the buyer explicitly confirms they want to proceed to payment.",
    )
    quantity_tonnes: Optional[float] = Field(
        None,
        description="Quantity of tonnes the buyer wants to purchase.",
    )

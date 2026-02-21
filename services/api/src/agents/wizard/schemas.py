"""
Strict Pydantic output schemas used by the Pydantic AI agent.

Each schema corresponds to what the LLM must return for a specific wizard
step so we can validate structure before persisting or streaming.
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class ProfileIntentOutput(BaseModel):
    """Returned by the agent during profile_check / onboarding steps."""

    response_text: str = Field(
        description="Plain-language reply to stream to the buyer. Max 3 sentences."
    )
    sector: Optional[str] = Field(
        None,
        description=(
            "Inferred sector slug (e.g. 'technology', 'manufacturing'). "
            "None if not yet determined."
        ),
    )
    employees: Optional[int] = Field(
        None,
        description="Estimated employee count if the buyer mentioned it.",
    )
    motivation: Optional[
        Literal["compliance", "esg_reporting", "brand", "personal"]
    ] = Field(None, description="Primary offset motivation if mentioned.")
    profile_complete: bool = Field(
        False,
        description=(
            "True once sector and employees are known and the buyer "
            "confirmed the summary."
        ),
    )
    next_step: Optional[str] = Field(
        None,
        description="Step to advance to. Use 'footprint_estimate' when profile_complete.",
    )


class FootprintOutput(BaseModel):
    """Returned by the agent during footprint_estimate step."""

    response_text: str = Field(
        description="Plain-language footprint explanation with analogy."
    )
    accepted_tonnes: Optional[float] = Field(
        None,
        description="Accepted annual tonne estimate (either from tool or buyer override).",
    )
    next_step: Optional[str] = Field(
        None,
        description="Step to advance to; use 'preference_elicitation' when buyer accepts.",
    )


class PreferenceOutput(BaseModel):
    """Returned by the agent during preference_elicitation step."""

    response_text: str = Field(
        description="Plain-language acknowledgement and transition sentence."
    )
    project_types: List[str] = Field(
        default_factory=list,
        description="Project types the buyer selected (e.g. 'forestry', 'renewable_energy').",
    )
    regions: List[str] = Field(
        default_factory=list,
        description="Preferred geographic regions or empty list for no preference.",
    )
    max_price_eur: Optional[float] = Field(
        None,
        description="Budget ceiling per tonne in EUR if stated.",
    )
    co_benefits: List[str] = Field(
        default_factory=list,
        description="Co-benefit keywords mentioned by the buyer.",
    )
    next_step: Optional[str] = Field(
        None,
        description="Use 'listing_search' once preferences are captured.",
    )


class RecommendationOutput(BaseModel):
    """Returned during listing_search / recommendation steps."""

    response_text: str = Field(
        description=(
            "Plain-language presentation of recommended listings. "
            "Include a 'why we picked this' blurb per listing."
        )
    )
    selected_listing_id: Optional[str] = Field(
        None,
        description="Listing ID the buyer chose, if they made a selection.",
    )
    next_step: Optional[str] = Field(
        None,
        description="Use 'order_creation' once a listing is selected.",
    )


class OrderOutput(BaseModel):
    """Returned during order_creation step."""

    response_text: str = Field(
        description="Order summary in plain language ready for buyer confirmation."
    )
    quantity_tonnes: Optional[float] = Field(
        None,
        description="Quantity of tonnes the buyer wants to purchase.",
    )
    next_step: Optional[str] = Field(
        None,
        description="Remains 'order_creation' until payment is confirmed.",
    )

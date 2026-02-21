"""
Strict Pydantic output schemas for the Pydantic AI wizard agent.

Design principles (from agent quality research):
1. Every schema has `response_text` with a validator enforcing non-empty string.
2. Every schema has `missing_fields` listing what still needs to be collected.
3. Transition flags are boolean with explicit docstrings on WHEN to set them.
4. No ambiguous "next_step" string — all transitions are explicit booleans.
5. Field descriptions tell the model exactly what to put in each field.
"""

from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


# ── Shared validator ─────────────────────────────────────────────────

def _nonempty_response(v: str) -> str:
    if not v or not v.strip():
        raise ValueError("response_text must be non-empty")
    return v.strip()


# ── Transition step literals ──────────────────────────────────────────

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


# ── Step 0: Profile / Onboarding ─────────────────────────────────────

class ProfileIntentOutput(BaseModel):
    """Returned by the agent during profile_check / onboarding steps."""

    response_text: str = Field(
        description=(
            "Your reply to the buyer. "
            "If sector AND employees are already known from context, do NOT ask for them — "
            "acknowledge them and tell the buyer you are calculating their footprint. "
            "If one is missing, ask for exactly that one missing piece. "
            "Max 3 warm, friendly sentences. "
            "Never use carbon-market jargon without explaining it."
        )
    )

    sector: Optional[str] = Field(
        None,
        description=(
            "The buyer's industry sector as a lowercase slug "
            "(e.g. 'technology', 'manufacturing', 'retail'). "
            "Extract from what they said or from context. None if truly unknown."
        ),
    )
    employees: Optional[int] = Field(
        None,
        description=(
            "Number of employees the buyer mentioned or confirmed. "
            "None if not mentioned. Must be a positive integer."
        ),
    )
    motivation: Optional[Literal["compliance", "esg_reporting", "brand", "personal"]] = Field(
        None,
        description="Primary reason for offsetting if the buyer mentioned it.",
    )
    profile_complete: bool = Field(
        False,
        description=(
            "Set True when BOTH sector AND employees are known from any source "
            "(current message, conversation history, or saved profile in context). "
            "Do NOT require the buyer to repeat information already in context."
        ),
    )
    advance_to_footprint: bool = Field(
        False,
        description=(
            "Set True to advance to the footprint estimation step. "
            "Must be True whenever profile_complete is True. "
            "Set this as soon as you have sector + employees — do not wait for an extra turn."
        ),
    )
    missing_fields: List[str] = Field(
        default_factory=list,
        description=(
            "List of fields still needed to complete this step. "
            "E.g. ['sector', 'employees']. Empty when profile_complete is True."
        ),
    )

    _validate_response = field_validator("response_text")(_nonempty_response)


# ── Step 1: Footprint Estimate ────────────────────────────────────────

class FootprintOutput(BaseModel):
    """Returned by the agent during footprint_estimate step."""

    response_text: str = Field(
        description=(
            "Plain-language footprint explanation using the tool's output. "
            "Include the tonne range and one real-world analogy. "
            "End with: 'Does that sound about right, or would you like to adjust it?' "
            "Never present a number without calling tool_estimate_footprint first. "
            "Max 4 sentences."
        )
    )
    accepted_tonnes: Optional[float] = Field(
        None,
        description=(
            "The final tonne estimate the buyer accepted (use tool midpoint). "
            "Set this when the buyer says anything like: yes, ok, sounds right, sure, "
            "that's fine, proceed, good, correct, next, that seems right. "
            "None only if buyer explicitly disagrees or provides a different number."
        ),
    )
    buyer_provided_tonnes: Optional[float] = Field(
        None,
        description=(
            "Set this if the buyer explicitly gave their own tonne number "
            "(e.g. 'we emit about 50 tonnes'). Use this instead of the estimate."
        ),
    )
    advance_to_preferences: bool = Field(
        False,
        description=(
            "Set True to move to project preference collection. "
            "Set True as soon as any of these is true: "
            "(a) buyer confirmed the estimate, (b) buyer gave their own number, "
            "(c) buyer said 'not sure' or 'I don't know' — use estimate and move on."
        ),
    )

    _validate_response = field_validator("response_text")(_nonempty_response)


# ── Step 2: Preference Elicitation ───────────────────────────────────

class PreferenceOutput(BaseModel):
    """Returned by the agent during preference_elicitation step."""

    response_text: str = Field(
        description=(
            "Warm acknowledgement of their choice and a brief, jargon-free description "
            "of each project type mentioned. "
            "If preferences are already saved in context, acknowledge them and say "
            "you are searching now — do NOT ask again. "
            "Max 3 sentences."
        )
    )
    project_types: List[str] = Field(
        default_factory=list,
        description=(
            "Project types the buyer selected or mentioned. "
            "Valid values: afforestation, renewable, cookstoves, methane_capture, "
            "fuel_switching, energy_efficiency, agriculture, other. "
            "Extract from their message AND from saved preferences in context."
        ),
    )
    regions: List[str] = Field(
        default_factory=list,
        description="Geographic regions mentioned or preferred. Empty = no preference.",
    )
    max_price_eur: Optional[float] = Field(
        None,
        description="Budget ceiling per tonne in EUR if stated by the buyer.",
    )
    co_benefits: List[str] = Field(
        default_factory=list,
        description="Co-benefit keywords mentioned (e.g. 'biodiversity', 'community', 'health').",
    )
    advance_to_search: bool = Field(
        False,
        description=(
            "Set True to search for listings. "
            "Set True as soon as at least one project type is known — from current "
            "message OR from saved preferences in context. "
            "Do NOT wait for the buyer to give multiple types."
        ),
    )

    _validate_response = field_validator("response_text")(_nonempty_response)


# ── Step 3a / 3b: Listing Search & Recommendation ────────────────────

class RecommendationOutput(BaseModel):
    """Returned during listing_search, recommendation, and autobuy_waitlist steps."""

    response_text: str = Field(
        description=(
            "Present listings clearly with a 'why we picked this for you' blurb per listing. "
            "Include: project name, country, price/tonne, total cost for their quantity. "
            "If no listings were found, explain clearly and ask: "
            "'Would you like our agent to monitor the market and automatically buy matching "
            "credits when they become available?' — this must be a clear yes/no question. "
            "Never invent listings. Max 5 sentences per listing."
        )
    )
    listings_found: bool = Field(
        True,
        description="Set False when tool_search_listings returned zero results.",
    )
    selected_listing_id: Optional[str] = Field(
        None,
        description=(
            "The exact listing ID the buyer chose. "
            "Set this when the buyer names, picks, selects, or says 'yes' to a specific listing. "
            "Must be one of the IDs returned by the search tool."
        ),
    )
    selected_quantity_tonnes: Optional[float] = Field(
        None,
        description=(
            "Quantity in tonnes the buyer wants to purchase. "
            "Default to their accepted footprint midpoint if they don't specify. "
            "Must be a positive number."
        ),
    )
    buyer_wants_broader_search: bool = Field(
        False,
        description="True when buyer explicitly asks to see more/different options.",
    )
    buyer_declined_all: bool = Field(
        False,
        description="True when buyer explicitly says they don't want any of the shown options.",
    )
    buyer_wants_autobuy_waitlist: bool = Field(
        False,
        description=(
            "True when buyer agrees to let the autonomous agent buy on their behalf later. "
            "Only set after explicitly asking and receiving an affirmative response "
            "(yes, sure, ok, please do, go ahead, etc.)."
        ),
    )
    buyer_declined_autobuy: bool = Field(
        False,
        description=(
            "True when buyer explicitly says no to the autonomous agent option "
            "(no, not now, maybe later, I'll come back, etc.)."
        ),
    )
    advance_to_order: bool = Field(
        False,
        description=(
            "Set True to create a draft order. "
            "Set True when selected_listing_id is set. "
            "IMPORTANT: when listings are available and buyer says yes/pick one, "
            "set selected_listing_id AND advance_to_order=True — do not ask again."
        ),
    )

    _validate_response = field_validator("response_text")(_nonempty_response)


# ── Step 4: Order Creation ────────────────────────────────────────────

class OrderOutput(BaseModel):
    """Returned during order_creation step."""

    response_text: str = Field(
        description=(
            "Clear order summary: project name, quantity in tonnes, price per tonne, total EUR. "
            "Use plain language: 'You are about to offset X tonnes of CO2 for €Y total.' "
            "End with: 'Shall I proceed to payment?' "
            "Max 4 sentences."
        )
    )
    order_confirmed: bool = Field(
        False,
        description=(
            "True when buyer explicitly confirms they want to proceed to payment. "
            "Accepted words: yes, confirm, proceed, pay, go ahead, do it, ok, let's do it."
        ),
    )
    quantity_tonnes: Optional[float] = Field(
        None,
        description="Quantity of tonnes being purchased in this order.",
    )
    order_id: Optional[str] = Field(
        None,
        description="Order ID from tool_create_order_draft if the draft was created.",
    )

    _validate_response = field_validator("response_text")(_nonempty_response)


# ── Buyer Agent Handoff ───────────────────────────────────────────────

class BuyerHandoffResult(BaseModel):
    """
    Communicates the outcome of a wizard→buyer agent handoff to the user.
    This is not an LLM output schema — it is constructed deterministically
    by the runner after the buyer agent completes.
    """
    action: Literal["purchased", "proposed_for_approval", "skipped", "failed"]
    listing_id: Optional[str] = None
    listing_name: Optional[str] = None
    quantity_tonnes: Optional[float] = None
    total_eur: Optional[float] = None
    rationale: Optional[str] = None
    run_id: Optional[str] = None
    error_message: Optional[str] = None

    def to_message(self) -> str:
        """Convert to a user-friendly plain-English summary message."""
        if self.action == "purchased":
            return (
                f"Our agent found and purchased {self.quantity_tonnes} tonnes of CO2 offsets "
                f"from '{self.listing_name}' for €{self.total_eur:.2f} total. "
                f"You'll receive a confirmation shortly. "
                f"Reason: {self.rationale or 'Best match for your criteria.'}"
            )
        elif self.action == "proposed_for_approval":
            return (
                f"Our agent found a great match: '{self.listing_name}' — "
                f"{self.quantity_tonnes} tonnes for €{self.total_eur:.2f}. "
                f"This purchase needs your approval since it's above your auto-approve threshold. "
                f"You can approve it from your dashboard. Reason: {self.rationale or ''}"
            )
        elif self.action == "skipped":
            return (
                "Our agent searched the market but couldn't find a listing that met all your criteria. "
                "You've been added to the autonomous monitoring list — "
                "the agent will try again when new listings appear."
            )
        else:
            return (
                "Something went wrong while our agent was processing your purchase. "
                "Your preferences have been saved and the agent will retry automatically. "
                f"Error: {self.error_message or 'Unknown error'}"
            )

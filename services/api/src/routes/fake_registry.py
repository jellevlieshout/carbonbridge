import asyncio
import hashlib
import re
from dataclasses import dataclass
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

import conf
from utils import log

logger = log.get_logger(__name__)

router = APIRouter(prefix="/fake-registry", tags=["fake-registry"])

SERIAL_RANGE_PATTERN = re.compile(
    r"^(?P<registry>V|GS|ACR)-[A-Z0-9]+-(?P<start>\d+)-(?P<end>\d+)$"
)


@dataclass
class CreditSerialState:
    total_quantity: int
    retired_quantity: int
    vintage_year: int

    @property
    def available_quantity(self) -> int:
        return max(0, self.total_quantity - self.retired_quantity)


class CreditsResponse(BaseModel):
    serial_range: str
    is_valid: bool
    available_quantity: int
    vintage_year: Optional[int]
    retirement_status: str


class RetireRequest(BaseModel):
    serial_range: str = Field(min_length=3)
    quantity: Optional[int] = Field(default=None, ge=1)


class RetireResponse(BaseModel):
    serial_range: str
    retirement_reference: str
    retired_quantity: int
    available_quantity: int
    retirement_status: str


_SERIAL_STATE: dict[str, CreditSerialState] = {
    "V-FOREST-0001-0100": CreditSerialState(total_quantity=100, retired_quantity=0, vintage_year=2022),
    "V-RENEW-0101-0200": CreditSerialState(total_quantity=100, retired_quantity=10, vintage_year=2021),
    "GS-COOK-0001-0150": CreditSerialState(total_quantity=150, retired_quantity=30, vintage_year=2020),
    "ACR-METHANE-0201-0300": CreditSerialState(total_quantity=100, retired_quantity=0, vintage_year=2023),
}


def _stable_hash_int(value: str) -> int:
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest(), 16)


def _normalize_serial_range(serial_range: str) -> str:
    return serial_range.strip().upper()


def _retirement_status(available_quantity: int) -> str:
    return "retired" if available_quantity == 0 else "active"


def _validate_serial_range(serial_range: str) -> Optional[re.Match[str]]:
    return SERIAL_RANGE_PATTERN.match(serial_range)


def _state_for_serial(serial_range: str) -> Optional[CreditSerialState]:
    if serial_range in _SERIAL_STATE:
        return _SERIAL_STATE[serial_range]

    match = _validate_serial_range(serial_range)
    if not match:
        return None

    start = int(match.group("start"))
    end = int(match.group("end"))
    if end < start:
        return None

    deterministic_key = f"seed:{serial_range}"
    seeded_hash = _stable_hash_int(deterministic_key)
    total_quantity = end - start + 1
    retired_quantity = seeded_hash % (max(total_quantity // 4, 1))
    vintage_year = 2016 + (seeded_hash % 10)

    _SERIAL_STATE[serial_range] = CreditSerialState(
        total_quantity=total_quantity,
        retired_quantity=retired_quantity,
        vintage_year=vintage_year,
    )
    return _SERIAL_STATE[serial_range]


def _should_fail(seed: str, failure_rate: float) -> bool:
    if failure_rate <= 0:
        return False
    if failure_rate >= 1:
        return True
    value = _stable_hash_int(seed) % 10_000
    return value < int(failure_rate * 10_000)


async def _simulate_latency(seed: str) -> None:
    cfg = conf.get_fake_registry_conf()
    min_ms = cfg.min_latency_ms
    max_ms = cfg.max_latency_ms
    spread = max_ms - min_ms
    latency_ms = min_ms if spread == 0 else min_ms + (_stable_hash_int(seed) % (spread + 1))
    await asyncio.sleep(latency_ms / 1000)


@router.get("/credits/{serial_range}", response_model=CreditsResponse)
async def credits_get(serial_range: str) -> CreditsResponse:
    normalized = _normalize_serial_range(serial_range)
    await _simulate_latency(f"credits:{normalized}")

    cfg = conf.get_fake_registry_conf()
    if _should_fail(f"credits:failure:{normalized}", cfg.failure_rate):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Fake registry temporary failure. Please retry.",
        )

    state = _state_for_serial(normalized)
    if not state:
        return CreditsResponse(
            serial_range=normalized,
            is_valid=False,
            available_quantity=0,
            vintage_year=None,
            retirement_status="invalid",
        )

    return CreditsResponse(
        serial_range=normalized,
        is_valid=True,
        available_quantity=state.available_quantity,
        vintage_year=state.vintage_year,
        retirement_status=_retirement_status(state.available_quantity),
    )


@router.post("/retire", response_model=RetireResponse)
async def retire_post(payload: RetireRequest) -> RetireResponse:
    normalized = _normalize_serial_range(payload.serial_range)
    await _simulate_latency(f"retire:{normalized}")

    cfg = conf.get_fake_registry_conf()
    if _should_fail(f"retire:failure:{normalized}", cfg.failure_rate):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Fake registry temporary failure. Please retry.",
        )

    state = _state_for_serial(normalized)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown serial range: {normalized}",
        )

    available = state.available_quantity
    if available <= 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Credits already fully retired for serial range {normalized}",
        )

    retire_quantity = payload.quantity if payload.quantity is not None else available
    if retire_quantity > available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Requested quantity {retire_quantity} exceeds available quantity {available}",
        )

    state.retired_quantity += retire_quantity
    post_available = state.available_quantity
    reference_seed = f"{normalized}:{state.retired_quantity}:{retire_quantity}"
    retirement_reference = f"RET-{hashlib.sha256(reference_seed.encode('utf-8')).hexdigest()[:12].upper()}"

    logger.info(
        "Retired %s credits for %s. Remaining=%s reference=%s",
        retire_quantity,
        normalized,
        post_available,
        retirement_reference,
    )

    return RetireResponse(
        serial_range=normalized,
        retirement_reference=retirement_reference,
        retired_quantity=retire_quantity,
        available_quantity=post_available,
        retirement_status=_retirement_status(post_available),
    )

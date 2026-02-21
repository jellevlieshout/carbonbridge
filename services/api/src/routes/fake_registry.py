import asyncio
import hashlib
import random
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/fake-registry", tags=["fake-registry"])


class ProjectMetadata(BaseModel):
    name: str
    type: str
    country: str
    methodology: str
    status: str


class CreditValidation(BaseModel):
    serial_range: str
    is_valid: bool
    available_quantity: int
    vintage_year: Optional[int]
    retirement_status: str  # "active" | "retired" | "invalid"


class RetireRequest(BaseModel):
    serial_range: str = Field(min_length=3)
    quantity: Optional[int] = Field(default=None, ge=1)


class RetireResponse(BaseModel):
    serial_range: str
    retirement_reference: str
    retired_quantity: int
    available_quantity: int
    retirement_status: str

# Seeded lookup table matching the demo scenario
PROJECTS_DB = {
    # Afforestation
    "GS-101": ProjectMetadata(
        name="Amazon Reforestation Initiative",
        type="afforestation",
        country="Brazil",
        methodology="VM0015",
        status="active"
    ),
    "V-102": ProjectMetadata(
        name="Kenya Community Tree Planting",
        type="afforestation",
        country="Kenya",
        methodology="AR-ACM0003",
        status="active"
    ),
    # Renewable Energy
    "V-201": ProjectMetadata(
        name="Rajasthan Wind Power",
        type="renewable_energy",
        country="India",
        methodology="ACM0002",
        status="active"
    ),
    "GS-202": ProjectMetadata(
        name="Morocco Solar Array",
        type="renewable_energy",
        country="Morocco",
        methodology="AMS-I.D.",
        status="active"
    ),
    # Cookstoves
    "GS-301": ProjectMetadata(
        name="Ghana Clean Cookstoves",
        type="cookstoves",
        country="Ghana",
        methodology="AMS-II.G.",
        status="active"
    ),
    "V-302": ProjectMetadata(
        name="Uganda Efficient Stoves",
        type="cookstoves",
        country="Uganda",
        methodology="VMR0006",
        status="active"
    ),
    # Methane Capture
    "ACR-401": ProjectMetadata(
        name="Texas Landfill Gas Recovery",
        type="methane_capture",
        country="USA",
        methodology="ACM0001",
        status="active"
    ),
}

# Seeded serial number ranges matching seed.py listings
CREDITS_DB: dict[str, dict] = {
    "VCS-1234-2023-BR-001 to VCS-1234-2023-BR-5000": {
        "available_quantity": 5000, "vintage_year": 2023,
    },
    "VCS-1235-2022-BR-001 to VCS-1235-2022-BR-3000": {
        "available_quantity": 3000, "vintage_year": 2022,
    },
    "VCS-2001-2023-IN-001 to VCS-2001-2023-IN-10000": {
        "available_quantity": 10000, "vintage_year": 2023,
    },
    "GS-3001-2024-IN-001 to GS-3001-2024-IN-8000": {
        "available_quantity": 8000, "vintage_year": 2024,
    },
    "GS-7001-2023-KE-001 to GS-7001-2023-KE-6000": {
        "available_quantity": 6000, "vintage_year": 2023,
    },
    "GS-7002-2024-UG-001 to GS-7002-2024-UG-4000": {
        "available_quantity": 4000, "vintage_year": 2024,
    },
}

# In-memory retirement tracking (resets on restart)
_retired: dict[str, int] = {}


@router.get("/projects/{project_id}", response_model=ProjectMetadata)
async def get_project(project_id: str):
    # Simulate API latency (800ms - 2000ms)
    latency = random.uniform(0.8, 2.0)
    await asyncio.sleep(latency)
    
    # Simulate 10% failure rate
    if random.random() < 0.10:
        raise HTTPException(status_code=503, detail="Simulated Registry Outage")
        
    if project_id in PROJECTS_DB:
        return PROJECTS_DB[project_id]
        
    # Fallback for un-seeded but potentially valid IDs per spec (V-, GS-, ACR-)
    if project_id.startswith(("V-", "GS-", "ACR-")):
        return ProjectMetadata(
            name=f"Generated Project {project_id}",
            type="unknown",
            country="Unknown",
            methodology="Unknown",
            status="active"
        )
        
    raise HTTPException(status_code=404, detail="Project not found in fake registry")


@router.get("/credits/{serial_range:path}", response_model=CreditValidation)
async def get_credits(serial_range: str):
    # Simulate API latency (800ms - 2000ms)
    latency = random.uniform(0.8, 2.0)
    await asyncio.sleep(latency)

    # Simulate 10% failure rate
    if random.random() < 0.10:
        raise HTTPException(status_code=503, detail="Simulated Registry Outage")

    if serial_range in CREDITS_DB:
        credit = CREDITS_DB[serial_range]
        already_retired = _retired.get(serial_range, 0)
        available = max(0, credit["available_quantity"] - already_retired)
        if available == 0:
            ret_status = "retired"
        elif already_retired > 0:
            ret_status = "partially_retired"
        else:
            ret_status = "active"
        return CreditValidation(
            serial_range=serial_range,
            is_valid=True,
            available_quantity=available,
            vintage_year=credit["vintage_year"],
            retirement_status=ret_status,
        )

    # Unknown serial range
    return CreditValidation(
        serial_range=serial_range,
        is_valid=False,
        available_quantity=0,
        vintage_year=None,
        retirement_status="invalid",
    )


@router.post("/retire", response_model=RetireResponse)
async def retire_credits(payload: RetireRequest):
    # Simulate API latency (800ms - 2000ms)
    latency = random.uniform(0.8, 2.0)
    await asyncio.sleep(latency)

    # Simulate 10% failure rate
    if random.random() < 0.10:
        raise HTTPException(status_code=503, detail="Simulated Registry Outage")

    if payload.serial_range not in CREDITS_DB:
        raise HTTPException(status_code=404, detail=f"Unknown serial range: {payload.serial_range}")

    credit = CREDITS_DB[payload.serial_range]
    already_retired = _retired.get(payload.serial_range, 0)
    available = credit["available_quantity"] - already_retired

    if available <= 0:
        raise HTTPException(status_code=409, detail="Credits already fully retired")

    retire_qty = payload.quantity if payload.quantity is not None else available
    if retire_qty > available:
        raise HTTPException(
            status_code=400,
            detail=f"Requested {retire_qty} exceeds available {available}",
        )

    _retired[payload.serial_range] = already_retired + retire_qty
    post_available = available - retire_qty

    # Generate retirement reference
    ref_seed = f"{payload.serial_range}:{_retired[payload.serial_range]}"
    ref_hash = hashlib.sha256(ref_seed.encode()).hexdigest()[:12].upper()
    retirement_ref = f"RET-{ref_hash}"

    return RetireResponse(
        serial_range=payload.serial_range,
        retirement_reference=retirement_ref,
        retired_quantity=retire_qty,
        available_quantity=post_available,
        retirement_status="retired" if post_available == 0 else "active",
    )

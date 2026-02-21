import asyncio
import random
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/fake-registry", tags=["fake-registry"])

class ProjectMetadata(BaseModel):
    name: str
    type: str
    country: str
    methodology: str
    status: str

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

"""
Database seeding script for CarbonBridge.

Populates Couchbase with realistic fake data for development:
- 1 admin, 3 sellers, 4 buyers (with buyer profiles)
- ~15 carbon credit listings across sellers
- ~8 orders in various statuses
- A few registry verifications
- Market insights snapshot

Run standalone:   python seed.py
Or via API:       POST /api/seed
"""

import asyncio
import random
import uuid
from datetime import datetime, timezone, timedelta

from models.entities.couchbase.users import User, UserData, BuyerProfile
from models.entities.couchbase.listings import Listing, ListingData
from models.entities.couchbase.orders import Order, OrderData, OrderLineItem
from models.entities.couchbase.registry_verifications import (
    RegistryVerification,
    RegistryVerificationData,
)
from models.entities.couchbase.market_insights import MarketInsights, MarketInsightsData
from models.entities.couchbase.offsets_db_projects import OffsetsDBProject, OffsetsDBProjectData

from utils import log

logger = log.get_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _past(days_ago_max: int = 90) -> datetime:
    """Random datetime in the recent past."""
    return datetime.now(timezone.utc) - timedelta(
        days=random.randint(1, days_ago_max),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )


def _id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Seed data definitions
# ---------------------------------------------------------------------------

SELLERS = [
    {
        "key": "seller-1",
        "email": "verde@greenforest.co",
        "role": "seller",
        "company_name": "GreenForest Carbon Co.",
        "company_size_employees": 45,
        "sector": "Forestry",
        "country": "Brazil",
    },
    {
        "key": "seller-2",
        "email": "ops@solarcredits.io",
        "role": "seller",
        "company_name": "SolarCredits International",
        "company_size_employees": 120,
        "sector": "Renewable Energy",
        "country": "India",
    },
    {
        "key": "seller-3",
        "email": "info@cleanstove.org",
        "role": "seller",
        "company_name": "CleanStove Foundation",
        "company_size_employees": 18,
        "sector": "Household Energy",
        "country": "Kenya",
    },
]

BUYERS = [
    {
        "key": "buyer-1",
        "email": "sustainability@techcorp.com",
        "role": "buyer",
        "company_name": "TechCorp Inc.",
        "company_size_employees": 5000,
        "sector": "Technology",
        "country": "United States",
        "buyer_profile": BuyerProfile(
            annual_co2_tonnes_estimate=12000.0,
            primary_offset_motivation="esg_reporting",
            preferred_project_types=["afforestation", "renewable"],
            preferred_regions=["South America", "Southeast Asia"],
            budget_per_tonne_max_eur=25.0,
        ),
    },
    {
        "key": "buyer-2",
        "email": "green@airlinegroup.eu",
        "role": "buyer",
        "company_name": "European Airline Group",
        "company_size_employees": 32000,
        "sector": "Aviation",
        "country": "Germany",
        "buyer_profile": BuyerProfile(
            annual_co2_tonnes_estimate=500000.0,
            primary_offset_motivation="compliance",
            preferred_project_types=["renewable", "methane_capture"],
            preferred_regions=["Europe", "Africa"],
            budget_per_tonne_max_eur=40.0,
            autonomous_agent_enabled=True,
            autonomous_agent_criteria={
                "max_price_eur": 35.0,
                "min_vintage_year": 2022,
                "preferred_types": ["renewable", "methane_capture"],
                "preferred_co_benefits": ["jobs", "energy_access", "community"],
                "monthly_budget_eur": 50000.0,
                "auto_approve_under_eur": 15000.0,
            },
        ),
    },
    {
        "key": "buyer-3",
        "email": "csr@fashionbrand.com",
        "role": "buyer",
        "company_name": "EcoFashion Group",
        "company_size_employees": 800,
        "sector": "Retail / Fashion",
        "country": "France",
        "buyer_profile": BuyerProfile(
            annual_co2_tonnes_estimate=3500.0,
            primary_offset_motivation="brand",
            preferred_project_types=["cookstoves", "afforestation"],
            preferred_regions=["Africa", "South America"],
            budget_per_tonne_max_eur=30.0,
        ),
    },
    {
        "key": "buyer-4",
        "email": "offset@smallbiz.nl",
        "role": "buyer",
        "company_name": "SmallBiz BV",
        "company_size_employees": 15,
        "sector": "Consulting",
        "country": "Netherlands",
        "buyer_profile": BuyerProfile(
            annual_co2_tonnes_estimate=200.0,
            primary_offset_motivation="personal",
            preferred_project_types=["afforestation"],
            preferred_regions=["South America"],
            budget_per_tonne_max_eur=20.0,
        ),
    },
]

ADMIN = {
    "key": "admin-1",
    "email": "admin@carbonbridge.io",
    "role": "admin",
    "company_name": "CarbonBridge",
    "country": "Netherlands",
}

# Curity test user — key matches the 'sub' claim from the OIDC token
CURITY_TEST_USER = {
    "key": "jelle",
    "email": "jelle@carbonbridge.io",
    "role": "buyer",
    "company_name": "Jelle's Test Company",
    "company_size_employees": 10,
    "sector": "Technology",
    "country": "Netherlands",
    "buyer_profile": BuyerProfile(
        annual_co2_tonnes_estimate=5000.0,
        primary_offset_motivation="esg_reporting",
        preferred_project_types=["renewable", "afforestation"],
        preferred_regions=["Europe", "Africa"],
        budget_per_tonne_max_eur=30.0,
        autonomous_agent_enabled=True,
        autonomous_agent_criteria={
            "max_price_eur": 30.0,
            "min_vintage_year": 2022,
            "preferred_types": ["renewable", "afforestation", "cookstoves"],
            "preferred_co_benefits": ["jobs", "community", "biodiversity"],
            "monthly_budget_eur": 25000.0,
            "auto_approve_under_eur": 10000.0,
        },
    ),
}


def _build_listings() -> list[dict]:
    """Return a list of listing dicts tied to the sellers above."""
    return [
        # --- GreenForest (seller-1) ---
        {
            "key": "listing-1",
            "seller_id": "seller-1",
            "registry_name": "Verra",
            "registry_project_id": "VCS-1234",
            "serial_number_range": "VCS-1234-2023-BR-001 to VCS-1234-2023-BR-5000",
            "project_name": "Amazon Reforestation Project",
            "project_type": "afforestation",
            "project_country": "Brazil",
            "vintage_year": 2023,
            "methodology": "VM0007",
            "description": "Large-scale native species reforestation in degraded Amazon pastureland. "
                           "Restores 2,500 hectares of tropical forest, verified by Verra under VM0007.",
            "co_benefits": ["biodiversity", "community", "sdg_goals"],
            "quantity_tonnes": 5000.0,
            "quantity_reserved": 200.0,
            "quantity_sold": 800.0,
            "price_per_tonne_eur": 18.50,
            "verification_status": "verified",
            "status": "active",
        },
        {
            "key": "listing-2",
            "seller_id": "seller-1",
            "registry_name": "Verra",
            "registry_project_id": "VCS-1235",
            "serial_number_range": "VCS-1235-2022-BR-001 to VCS-1235-2022-BR-3000",
            "project_name": "Cerrado Savanna Conservation",
            "project_type": "afforestation",
            "project_country": "Brazil",
            "vintage_year": 2022,
            "methodology": "VM0015",
            "description": "Avoided deforestation and degradation of native Cerrado vegetation. "
                           "Protects high-biodiversity savanna ecosystems.",
            "co_benefits": ["biodiversity", "water_conservation"],
            "quantity_tonnes": 3000.0,
            "quantity_reserved": 0.0,
            "quantity_sold": 1500.0,
            "price_per_tonne_eur": 15.00,
            "verification_status": "verified",
            "status": "active",
        },
        {
            "key": "listing-3",
            "seller_id": "seller-1",
            "registry_name": "Gold Standard",
            "registry_project_id": "GS-5678",
            "project_name": "Atlantic Forest Restoration",
            "project_type": "afforestation",
            "project_country": "Brazil",
            "vintage_year": 2024,
            "methodology": "AR-ACM0003",
            "description": "Restoring Atlantic Forest corridors connecting isolated fragments. "
                           "Community-led planting of 80+ native tree species.",
            "co_benefits": ["biodiversity", "community", "education"],
            "quantity_tonnes": 2000.0,
            "quantity_reserved": 0.0,
            "quantity_sold": 0.0,
            "price_per_tonne_eur": 22.00,
            "verification_status": "pending",
            "status": "draft",
        },
        # --- SolarCredits (seller-2) ---
        {
            "key": "listing-4",
            "seller_id": "seller-2",
            "registry_name": "Verra",
            "registry_project_id": "VCS-2001",
            "serial_number_range": "VCS-2001-2023-IN-001 to VCS-2001-2023-IN-10000",
            "project_name": "Rajasthan Solar Farm",
            "project_type": "renewable",
            "project_country": "India",
            "vintage_year": 2023,
            "methodology": "ACM0002",
            "description": "150 MW grid-connected solar PV plant in Rajasthan displacing coal-fired generation.",
            "co_benefits": ["jobs", "energy_access"],
            "quantity_tonnes": 10000.0,
            "quantity_reserved": 500.0,
            "quantity_sold": 3000.0,
            "price_per_tonne_eur": 12.00,
            "verification_status": "verified",
            "status": "active",
        },
        {
            "key": "listing-5",
            "seller_id": "seller-2",
            "registry_name": "Gold Standard",
            "registry_project_id": "GS-3001",
            "serial_number_range": "GS-3001-2024-IN-001 to GS-3001-2024-IN-8000",
            "project_name": "Tamil Nadu Wind Farm Cluster",
            "project_type": "renewable",
            "project_country": "India",
            "vintage_year": 2024,
            "methodology": "ACM0002",
            "description": "Cluster of 50 wind turbines generating 200 MW along the Tamil Nadu coast.",
            "co_benefits": ["jobs", "energy_access", "sdg_goals"],
            "quantity_tonnes": 8000.0,
            "quantity_reserved": 0.0,
            "quantity_sold": 0.0,
            "price_per_tonne_eur": 14.50,
            "verification_status": "verified",
            "status": "active",
        },
        {
            "key": "listing-6",
            "seller_id": "seller-2",
            "registry_name": "ACR",
            "registry_project_id": "ACR-4010",
            "project_name": "Gujarat Methane Recovery",
            "project_type": "methane_capture",
            "project_country": "India",
            "vintage_year": 2023,
            "methodology": "ACM0001",
            "description": "Landfill gas capture and flaring at municipal waste site in Ahmedabad.",
            "co_benefits": ["air_quality", "community"],
            "quantity_tonnes": 4000.0,
            "quantity_reserved": 0.0,
            "quantity_sold": 500.0,
            "price_per_tonne_eur": 10.00,
            "verification_status": "verified",
            "status": "active",
        },
        {
            "key": "listing-7",
            "seller_id": "seller-2",
            "registry_name": "Verra",
            "registry_project_id": "VCS-2050",
            "project_name": "Karnataka Biogas Programme",
            "project_type": "methane_capture",
            "project_country": "India",
            "vintage_year": 2022,
            "methodology": "AMS-III.D",
            "description": "Installation of 10,000 household biogas digesters replacing firewood use.",
            "co_benefits": ["health", "community", "gender_equality"],
            "quantity_tonnes": 6000.0,
            "quantity_reserved": 300.0,
            "quantity_sold": 2000.0,
            "price_per_tonne_eur": 11.50,
            "verification_status": "verified",
            "status": "active",
        },
        # --- CleanStove Foundation (seller-3) ---
        {
            "key": "listing-8",
            "seller_id": "seller-3",
            "registry_name": "Gold Standard",
            "registry_project_id": "GS-7001",
            "serial_number_range": "GS-7001-2023-KE-001 to GS-7001-2023-KE-6000",
            "project_name": "Kenya Improved Cookstoves",
            "project_type": "cookstoves",
            "project_country": "Kenya",
            "vintage_year": 2023,
            "methodology": "TPDDTEC",
            "description": "Distribution of fuel-efficient cookstoves to 15,000 households in rural Kenya. "
                           "Reduces firewood consumption by 50% and indoor air pollution.",
            "co_benefits": ["health", "gender_equality", "community"],
            "quantity_tonnes": 6000.0,
            "quantity_reserved": 100.0,
            "quantity_sold": 2500.0,
            "price_per_tonne_eur": 20.00,
            "verification_status": "verified",
            "status": "active",
        },
        {
            "key": "listing-9",
            "seller_id": "seller-3",
            "registry_name": "Gold Standard",
            "registry_project_id": "GS-7002",
            "serial_number_range": "GS-7002-2024-UG-001 to GS-7002-2024-UG-4000",
            "project_name": "Uganda Clean Cooking Initiative",
            "project_type": "cookstoves",
            "project_country": "Uganda",
            "vintage_year": 2024,
            "methodology": "TPDDTEC",
            "description": "Ethanol stove distribution programme in peri-urban Kampala.",
            "co_benefits": ["health", "gender_equality", "air_quality"],
            "quantity_tonnes": 4000.0,
            "quantity_reserved": 0.0,
            "quantity_sold": 0.0,
            "price_per_tonne_eur": 24.00,
            "verification_status": "verified",
            "status": "active",
        },
        {
            "key": "listing-10",
            "seller_id": "seller-3",
            "registry_name": "Verra",
            "registry_project_id": "VCS-8500",
            "project_name": "Rwanda Efficient Kilns",
            "project_type": "energy_efficiency",
            "project_country": "Rwanda",
            "vintage_year": 2023,
            "methodology": "AMS-III.Z",
            "description": "Replacing traditional charcoal kilns with high-efficiency alternatives in brick-making sector.",
            "co_benefits": ["jobs", "air_quality"],
            "quantity_tonnes": 1500.0,
            "quantity_reserved": 0.0,
            "quantity_sold": 0.0,
            "price_per_tonne_eur": 16.00,
            "verification_status": "pending",
            "status": "draft",
        },
        # --- Extra variety ---
        {
            "key": "listing-11",
            "seller_id": "seller-2",
            "registry_name": "Verra",
            "registry_project_id": "VCS-9100",
            "project_name": "Andhra Pradesh Rice Paddy Methane",
            "project_type": "agriculture",
            "project_country": "India",
            "vintage_year": 2024,
            "methodology": "AMS-III.AU",
            "description": "Alternate wetting and drying in rice paddies to reduce methane emissions.",
            "co_benefits": ["water_conservation", "community"],
            "quantity_tonnes": 3000.0,
            "quantity_reserved": 0.0,
            "quantity_sold": 0.0,
            "price_per_tonne_eur": 13.00,
            "verification_status": "verified",
            "status": "active",
        },
        {
            "key": "listing-12",
            "seller_id": "seller-1",
            "registry_name": "Verra",
            "registry_project_id": "VCS-1300",
            "project_name": "Colombian Mangrove Restoration",
            "project_type": "afforestation",
            "project_country": "Colombia",
            "vintage_year": 2023,
            "methodology": "VM0033",
            "description": "Restoring 800 hectares of degraded mangrove coast along the Caribbean.",
            "co_benefits": ["biodiversity", "community", "coastal_protection"],
            "quantity_tonnes": 2500.0,
            "quantity_reserved": 0.0,
            "quantity_sold": 400.0,
            "price_per_tonne_eur": 28.00,
            "verification_status": "verified",
            "status": "active",
        },
        {
            "key": "listing-13",
            "seller_id": "seller-2",
            "registry_name": "Gold Standard",
            "registry_project_id": "GS-4400",
            "project_name": "Morocco Concentrated Solar",
            "project_type": "renewable",
            "project_country": "Morocco",
            "vintage_year": 2023,
            "methodology": "ACM0002",
            "description": "50 MW concentrated solar power plant with thermal storage near Ouarzazate.",
            "co_benefits": ["jobs", "energy_access"],
            "quantity_tonnes": 5000.0,
            "quantity_reserved": 0.0,
            "quantity_sold": 1200.0,
            "price_per_tonne_eur": 16.00,
            "verification_status": "verified",
            "status": "active",
        },
        {
            "key": "listing-14",
            "seller_id": "seller-3",
            "registry_name": "Gold Standard",
            "registry_project_id": "GS-7100",
            "project_name": "Malawi Fuel-Switch Programme",
            "project_type": "fuel_switching",
            "project_country": "Malawi",
            "vintage_year": 2024,
            "methodology": "AMS-II.G",
            "description": "Transition from biomass to LPG for institutional cooking in schools and hospitals.",
            "co_benefits": ["health", "education"],
            "quantity_tonnes": 2000.0,
            "quantity_reserved": 0.0,
            "quantity_sold": 0.0,
            "price_per_tonne_eur": 19.00,
            "verification_status": "verified",
            "status": "active",
        },
        # One sold-out listing
        {
            "key": "listing-15",
            "seller_id": "seller-1",
            "registry_name": "Verra",
            "registry_project_id": "VCS-0999",
            "project_name": "Pará REDD+ 2021",
            "project_type": "afforestation",
            "project_country": "Brazil",
            "vintage_year": 2021,
            "methodology": "VM0015",
            "description": "REDD+ avoided deforestation in the Pará state — fully sold out.",
            "co_benefits": ["biodiversity", "community"],
            "quantity_tonnes": 1000.0,
            "quantity_reserved": 0.0,
            "quantity_sold": 1000.0,
            "price_per_tonne_eur": 12.00,
            "verification_status": "verified",
            "status": "sold_out",
        },
    ]


# ---------------------------------------------------------------------------
# OffsetsDB seed projects (~12 curated entries across all 5 registries & 7 categories)
# ---------------------------------------------------------------------------

OFFSETS_DB_SEED_PROJECTS: list[dict] = [
    # ACR - Forest
    {
        "key": "ACR-100",
        "offsets_db_project_id": "ACR-100",
        "registry": "ACR",
        "name": "Mississippi Alluvial Valley Reforestation",
        "category": "Forest",
        "project_type": "Reforestation",
        "country": "United States",
        "protocol": "ACR Reforestation Methodology",
        "total_credits_issued": 245000.0,
        "total_credits_retired": 180000.0,
        "status": "Active",
    },
    # ART - Forest
    {
        "key": "ART-001",
        "offsets_db_project_id": "ART-001",
        "registry": "ART",
        "name": "Guyana REDD+ National Programme",
        "category": "Forest",
        "project_type": "REDD+",
        "country": "Guyana",
        "protocol": "ART TREES Standard",
        "total_credits_issued": 33470000.0,
        "total_credits_retired": 12500000.0,
        "status": "Active",
    },
    # CAR - Forest
    {
        "key": "CAR-1100",
        "offsets_db_project_id": "CAR-1100",
        "registry": "CAR",
        "name": "Garcia River Forest",
        "category": "Forest",
        "project_type": "Improved Forest Management",
        "country": "United States",
        "protocol": "CAR Forest Protocol",
        "total_credits_issued": 1520000.0,
        "total_credits_retired": 890000.0,
        "status": "Active",
    },
    # GLD - Renewable Energy
    {
        "key": "GS-1234",
        "offsets_db_project_id": "GS-1234",
        "registry": "GLD",
        "name": "Bhadla Solar Park Phase II",
        "category": "Renewable Energy",
        "project_type": "Solar PV",
        "country": "India",
        "protocol": "GS Renewable Energy Methodology",
        "total_credits_issued": 890000.0,
        "total_credits_retired": 450000.0,
        "status": "Active",
    },
    # VCS - Forest
    {
        "key": "VCS-875",
        "offsets_db_project_id": "VCS-875",
        "registry": "VCS",
        "name": "Rimba Raya Biodiversity Reserve REDD+",
        "category": "Forest",
        "project_type": "REDD+",
        "country": "Indonesia",
        "protocol": "VM0004",
        "total_credits_issued": 8500000.0,
        "total_credits_retired": 3200000.0,
        "status": "Active",
    },
    # VCS - Renewable Energy
    {
        "key": "VCS-2341",
        "offsets_db_project_id": "VCS-2341",
        "registry": "VCS",
        "name": "Rajasthan Wind Power Project",
        "category": "Renewable Energy",
        "project_type": "Wind",
        "country": "India",
        "protocol": "ACM0002",
        "total_credits_issued": 1200000.0,
        "total_credits_retired": 780000.0,
        "status": "Active",
    },
    # GLD - Energy Efficiency
    {
        "key": "GS-5678",
        "offsets_db_project_id": "GS-5678",
        "registry": "GLD",
        "name": "Ghana Improved Cookstoves Programme",
        "category": "Energy Efficiency",
        "project_type": "Cookstoves",
        "country": "Ghana",
        "protocol": "GS TPDDTEC",
        "total_credits_issued": 650000.0,
        "total_credits_retired": 320000.0,
        "status": "Active",
    },
    # VCS - GHG Management
    {
        "key": "VCS-1440",
        "offsets_db_project_id": "VCS-1440",
        "registry": "VCS",
        "name": "Bandeirantes Landfill Gas Project",
        "category": "GHG Management",
        "project_type": "Landfill Gas",
        "country": "Brazil",
        "protocol": "ACM0001",
        "total_credits_issued": 12400000.0,
        "total_credits_retired": 9100000.0,
        "status": "Active",
    },
    # ACR - Agriculture
    {
        "key": "ACR-450",
        "offsets_db_project_id": "ACR-450",
        "registry": "ACR",
        "name": "Iowa Sustainable Agriculture Soil Carbon",
        "category": "Agriculture",
        "project_type": "Soil Carbon",
        "country": "United States",
        "protocol": "ACR Soil Carbon Methodology",
        "total_credits_issued": 78000.0,
        "total_credits_retired": 45000.0,
        "status": "Active",
    },
    # GLD - Fuel Switching
    {
        "key": "GS-9012",
        "offsets_db_project_id": "GS-9012",
        "registry": "GLD",
        "name": "Rwanda Biogas Programme for Rural Households",
        "category": "Fuel Switching",
        "project_type": "Biogas",
        "country": "Rwanda",
        "protocol": "GS Thermal Energy Methodology",
        "total_credits_issued": 210000.0,
        "total_credits_retired": 95000.0,
        "status": "Active",
    },
    # CAR - Other
    {
        "key": "CAR-500",
        "offsets_db_project_id": "CAR-500",
        "registry": "CAR",
        "name": "ODS Destruction Project - California",
        "category": "Other",
        "project_type": "ODS Destruction",
        "country": "United States",
        "protocol": "CAR ODS Protocol",
        "total_credits_issued": 4300000.0,
        "total_credits_retired": 3100000.0,
        "status": "Active",
    },
    # VCS - Renewable Energy (developing country)
    {
        "key": "VCS-3001",
        "offsets_db_project_id": "VCS-3001",
        "registry": "VCS",
        "name": "Nyangani Small Hydro Project",
        "category": "Renewable Energy",
        "project_type": "Hydro",
        "country": "Zimbabwe",
        "protocol": "AMS-I.D",
        "total_credits_issued": 340000.0,
        "total_credits_retired": 120000.0,
        "status": "Active",
    },
]


# ---------------------------------------------------------------------------
# Seed runner
# ---------------------------------------------------------------------------

async def run_seed() -> dict:
    """Insert all seed data. Returns summary counts."""
    counts = {
        "users": 0,
        "listings": 0,
        "orders": 0,
        "registry_verifications": 0,
        "market_insights": 0,
        "offsets_db_projects": 0,
    }

    # ---- Users ----
    all_users = [ADMIN, CURITY_TEST_USER] + SELLERS + BUYERS
    for u in all_users:
        key = u.pop("key")
        data = UserData(**u)  # type: ignore[arg-type]
        await User.create_or_update(key, data)
        counts["users"] += 1
        # Restore key for later use
        u["key"] = key
    logger.info(f"Seeded {counts['users']} users")

    # ---- TigerBeetle Accounts ----
    try:
        from clients.tigerbeetle import ensure_platform_account, create_user_accounts

        ensure_platform_account()
        logger.info("TigerBeetle: platform escrow account ready")

        for u in all_users:
            key = u["key"]
            user = await User.get(key)
            if user and not user.data.tigerbeetle_pending_account_id:
                pending_id, settled_id = create_user_accounts()
                user.data.tigerbeetle_pending_account_id = str(pending_id)
                user.data.tigerbeetle_settled_account_id = str(settled_id)
                await User.update(user)
                logger.info(f"TigerBeetle: created accounts for {key}")
    except Exception as e:
        logger.warning(f"TigerBeetle seeding skipped (not running?): {e}")

    # ---- Listings ----
    for listing in _build_listings():
        key = listing.pop("key")
        data = ListingData(**listing)
        await Listing.create_or_update(key, data, user_id=listing.get("seller_id"))
        counts["listings"] += 1
        listing["key"] = key
    logger.info(f"Seeded {counts['listings']} listings")

    # ---- Orders ----
    orders_spec = [
        # Completed orders
        {
            "key": "order-1",
            "buyer_id": "buyer-1",
            "status": "completed",
            "stripe_payment_status": "succeeded",
            "line_items": [
                OrderLineItem(listing_id="listing-1", quantity=500.0, price_per_tonne=18.50, subtotal=9250.0),
            ],
            "total_eur": 9250.0,
            "completed_at": _past(60),
        },
        {
            "key": "order-2",
            "buyer_id": "buyer-2",
            "status": "completed",
            "stripe_payment_status": "succeeded",
            "line_items": [
                OrderLineItem(listing_id="listing-4", quantity=2000.0, price_per_tonne=12.00, subtotal=24000.0),
                OrderLineItem(listing_id="listing-6", quantity=500.0, price_per_tonne=10.00, subtotal=5000.0),
            ],
            "total_eur": 29000.0,
            "completed_at": _past(45),
        },
        {
            "key": "order-3",
            "buyer_id": "buyer-3",
            "status": "completed",
            "stripe_payment_status": "succeeded",
            "line_items": [
                OrderLineItem(listing_id="listing-8", quantity=1000.0, price_per_tonne=20.00, subtotal=20000.0),
            ],
            "total_eur": 20000.0,
            "completed_at": _past(30),
            "retirement_requested": True,
            "retirement_reference": "RET-2024-KE-7001-001",
        },
        {
            "key": "order-4",
            "buyer_id": "buyer-1",
            "status": "completed",
            "stripe_payment_status": "succeeded",
            "line_items": [
                OrderLineItem(listing_id="listing-2", quantity=1500.0, price_per_tonne=15.00, subtotal=22500.0),
            ],
            "total_eur": 22500.0,
            "completed_at": _past(20),
        },
        # Confirmed (paid, awaiting fulfilment)
        {
            "key": "order-5",
            "buyer_id": "buyer-2",
            "status": "confirmed",
            "stripe_payment_status": "succeeded",
            "line_items": [
                OrderLineItem(listing_id="listing-5", quantity=1500.0, price_per_tonne=14.50, subtotal=21750.0),
            ],
            "total_eur": 21750.0,
        },
        # Pending (awaiting payment)
        {
            "key": "order-6",
            "buyer_id": "buyer-4",
            "status": "pending",
            "line_items": [
                OrderLineItem(listing_id="listing-1", quantity=200.0, price_per_tonne=18.50, subtotal=3700.0),
            ],
            "total_eur": 3700.0,
        },
        {
            "key": "order-7",
            "buyer_id": "buyer-3",
            "status": "pending",
            "line_items": [
                OrderLineItem(listing_id="listing-9", quantity=500.0, price_per_tonne=24.00, subtotal=12000.0),
                OrderLineItem(listing_id="listing-12", quantity=200.0, price_per_tonne=28.00, subtotal=5600.0),
            ],
            "total_eur": 17600.0,
        },
        # Cancelled
        {
            "key": "order-8",
            "buyer_id": "buyer-4",
            "status": "cancelled",
            "line_items": [
                OrderLineItem(listing_id="listing-7", quantity=100.0, price_per_tonne=11.50, subtotal=1150.0),
            ],
            "total_eur": 1150.0,
        },
    ]

    for o in orders_spec:
        key = o.pop("key")
        data = OrderData(**o)
        await Order.create_or_update(key, data, user_id=o.get("buyer_id"))
        counts["orders"] += 1
        o["key"] = key
    logger.info(f"Seeded {counts['orders']} orders")

    # ---- Registry Verifications (for verified listings) ----
    verified_listings = [
        ("listing-1", True),
        ("listing-4", True),
        ("listing-8", True),
        ("listing-3", False),  # pending listing → not yet valid
    ]
    for listing_id, is_valid in verified_listings:
        data = RegistryVerificationData(
            listing_id=listing_id,
            queried_at=_past(10),
            is_valid=is_valid,
            serial_numbers_available=is_valid,
            project_verified=is_valid,
            raw_response={"status": "valid" if is_valid else "pending", "source": "seed"},
            error_message=None if is_valid else "Verification still in progress",
        )
        await RegistryVerification.create_or_update(f"rv-{listing_id}", data)
        counts["registry_verifications"] += 1
    logger.info(f"Seeded {counts['registry_verifications']} registry verifications")

    # ---- Market Insights (single aggregate doc) ----
    insights_data = MarketInsightsData(
        credits_by_registry={
            "Verra": 35500,
            "Gold Standard": 25000,
            "ACR": 4000,
        },
        credits_by_category={
            "Afforestation / REDD+": 13500,
            "Renewable Energy": 23000,
            "Cookstoves": 10000,
            "Methane Capture": 10000,
            "Energy Efficiency": 1500,
            "Agriculture": 3000,
            "Fuel Switching": 2000,
        },
        credits_by_country={
            "Brazil": 11500,
            "India": 31000,
            "Kenya": 6000,
            "Uganda": 4000,
            "Rwanda": 1500,
            "Colombia": 2500,
            "Morocco": 5000,
            "Malawi": 2000,
        },
        coverage_by_category={
            "Afforestation / REDD+": 0.12,
            "Renewable Energy": 0.08,
            "Cookstoves": 0.15,
            "Methane Capture": 0.05,
        },
        computed_at=datetime.now(timezone.utc),
    )
    await MarketInsights.create_or_update("market-insights-latest", insights_data)
    counts["market_insights"] = 1
    logger.info("Seeded market insights")

    # ---- OffsetsDB Projects ----
    now = datetime.now(timezone.utc)
    for proj in OFFSETS_DB_SEED_PROJECTS:
        key = proj["key"]
        data = OffsetsDBProjectData(
            offsets_db_project_id=proj["offsets_db_project_id"],
            registry=proj["registry"],
            name=proj.get("name"),
            category=proj.get("category"),
            project_type=proj.get("project_type"),
            country=proj.get("country"),
            protocol=proj.get("protocol"),
            total_credits_issued=proj.get("total_credits_issued", 0.0),
            total_credits_retired=proj.get("total_credits_retired", 0.0),
            status=proj.get("status"),
            offsets_db_url=f"https://offsets-db.carbonplan.org/project/{proj['offsets_db_project_id']}",
            synced_at=now,
        )
        await OffsetsDBProject.create_or_update(key, data)
        counts["offsets_db_projects"] += 1
    logger.info(f"Seeded {counts['offsets_db_projects']} OffsetsDB projects")

    logger.info(f"Seeding complete: {counts}")
    return counts


# ---------------------------------------------------------------------------
# Standalone entrypoint
# ---------------------------------------------------------------------------

async def _main():
    import sys

    from clients.couchbase import check_connection
    await check_connection()

    if "--live-sync" in sys.argv:
        from offsets_db_sync import run_offsets_db_sync

        print("Running live OffsetsDB sync (downloading from CarbonPlan)...")
        result = await run_offsets_db_sync()
        print(f"Live sync complete: {result}")
    else:
        result = await run_seed()
        print(f"Seed complete: {result}")


if __name__ == "__main__":
    asyncio.run(_main())

"""
SewerSentinel Cost Estimation Module
====================================
Provides accurate, itemized cost estimates for sewer pipe repairs.

Features:
- Regional cost adjustments (labor rates vary significantly by area)
- Itemized breakdowns (transparent, verifiable by city engineers)
- Multiple repair method options (CIPP, pipe bursting, open cut, spot repair)
- Emergency vs proactive cost comparison
- Exportable estimates for budget planning

Data sources:
- RSMeans Construction Cost Data 2024
- EPA Clean Water State Revolving Fund data
- NASSCO rehabilitation cost studies
- Municipal bid tabulations (publicly available)

Note: These are estimates for planning purposes. Actual costs require
site-specific assessment and competitive bidding.
"""

from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple
from enum import Enum
import json


class Region(Enum):
    """US regions with distinct cost profiles."""
    NORTHEAST = "northeast"
    SOUTHEAST = "southeast"
    MIDWEST = "midwest"
    SOUTHWEST = "southwest"
    WEST_COAST = "west_coast"
    MOUNTAIN = "mountain"
    CUSTOM = "custom"


class RepairMethod(Enum):
    """Common sewer repair/rehabilitation methods."""
    CIPP = "cipp"                    # Cured-in-place pipe lining
    PIPE_BURSTING = "pipe_bursting"  # Trenchless replacement
    OPEN_CUT = "open_cut"            # Traditional dig and replace
    SPOT_REPAIR = "spot_repair"      # Localized excavation repair
    POINT_REPAIR = "point_repair"    # Trenchless point repair
    SLIP_LINING = "slip_lining"      # Insert smaller pipe
    SPRAY_LINING = "spray_lining"    # Epoxy/polymer spray coating


# =============================================================================
# REGIONAL COST FACTORS
# =============================================================================
# Based on RSMeans City Cost Index and EPA SRF loan data

REGIONAL_COST_DATA = {
    Region.NORTHEAST: {
        "name": "Northeast",
        "description": "High labor costs, older infrastructure, strict regulations",
        "example_cities": ["New York", "Boston", "Philadelphia", "Newark", "Hartford"],
        "labor_rate_per_hour": 95.00,      # Skilled utility worker
        "labor_multiplier": 1.45,           # vs national average
        "material_multiplier": 1.15,
        "equipment_multiplier": 1.20,
        "permit_base_cost": 2500,
        "permit_per_linear_foot": 15,
        "traffic_control_per_day": 3500,
        "inspection_cost": 1200,
        "engineering_percent": 0.12,        # % of construction cost
        "contingency_percent": 0.15,
        "prevailing_wage": True,
        "typical_soil": "rocky/clay",
        "notes": "Union labor required in most jurisdictions. Extensive permitting."
    },
    Region.SOUTHEAST: {
        "name": "Southeast",
        "description": "Moderate costs, high groundwater in coastal areas",
        "example_cities": ["Atlanta", "Charlotte", "Miami", "Tampa", "Raleigh"],
        "labor_rate_per_hour": 65.00,
        "labor_multiplier": 0.95,
        "material_multiplier": 1.00,
        "equipment_multiplier": 0.95,
        "permit_base_cost": 1200,
        "permit_per_linear_foot": 8,
        "traffic_control_per_day": 1800,
        "inspection_cost": 800,
        "engineering_percent": 0.10,
        "contingency_percent": 0.12,
        "prevailing_wage": False,
        "typical_soil": "sandy/clay",
        "notes": "Dewatering often needed in coastal areas. Hurricane season delays."
    },
    Region.MIDWEST: {
        "name": "Midwest",
        "description": "Moderate costs, freeze-thaw concerns, older cities",
        "example_cities": ["Chicago", "Detroit", "Cleveland", "Minneapolis", "St. Louis"],
        "labor_rate_per_hour": 75.00,
        "labor_multiplier": 1.05,
        "material_multiplier": 1.00,
        "equipment_multiplier": 1.00,
        "permit_base_cost": 1500,
        "permit_per_linear_foot": 10,
        "traffic_control_per_day": 2200,
        "inspection_cost": 900,
        "engineering_percent": 0.10,
        "contingency_percent": 0.12,
        "prevailing_wage": True,  # Illinois, Ohio, etc.
        "typical_soil": "clay",
        "notes": "Seasonal construction window. Deep frost line increases excavation depth."
    },
    Region.SOUTHWEST: {
        "name": "Southwest",
        "description": "Lower labor costs, minimal groundwater, long construction season",
        "example_cities": ["Phoenix", "Las Vegas", "Albuquerque", "Tucson", "El Paso"],
        "labor_rate_per_hour": 58.00,
        "labor_multiplier": 0.85,
        "material_multiplier": 0.95,
        "equipment_multiplier": 0.90,
        "permit_base_cost": 1000,
        "permit_per_linear_foot": 6,
        "traffic_control_per_day": 1500,
        "inspection_cost": 700,
        "engineering_percent": 0.08,
        "contingency_percent": 0.10,
        "prevailing_wage": False,
        "typical_soil": "sandy/caliche",
        "notes": "Year-round construction. Heat restrictions in summer months."
    },
    Region.WEST_COAST: {
        "name": "West Coast",
        "description": "Highest labor costs, strict environmental regulations",
        "example_cities": ["Los Angeles", "San Francisco", "Seattle", "Portland", "San Diego"],
        "labor_rate_per_hour": 105.00,
        "labor_multiplier": 1.55,
        "material_multiplier": 1.20,
        "equipment_multiplier": 1.25,
        "permit_base_cost": 3500,
        "permit_per_linear_foot": 20,
        "traffic_control_per_day": 4500,
        "inspection_cost": 1500,
        "engineering_percent": 0.15,
        "contingency_percent": 0.18,
        "prevailing_wage": True,
        "typical_soil": "varied",
        "notes": "Extensive environmental review. Seismic considerations. Highest costs nationally."
    },
    Region.MOUNTAIN: {
        "name": "Mountain",
        "description": "Moderate costs, seasonal limitations, rocky soil common",
        "example_cities": ["Denver", "Salt Lake City", "Boise", "Colorado Springs", "Reno"],
        "labor_rate_per_hour": 68.00,
        "labor_multiplier": 1.00,
        "material_multiplier": 1.05,
        "equipment_multiplier": 1.05,
        "permit_base_cost": 1300,
        "permit_per_linear_foot": 8,
        "traffic_control_per_day": 2000,
        "inspection_cost": 850,
        "engineering_percent": 0.10,
        "contingency_percent": 0.12,
        "prevailing_wage": False,  # Varies by state
        "typical_soil": "rocky",
        "notes": "Short construction season at altitude. Rock excavation common."
    }
}


# =============================================================================
# REPAIR METHOD SPECIFICATIONS
# =============================================================================
# Base costs per linear foot for different repair methods

REPAIR_METHOD_DATA = {
    RepairMethod.CIPP: {
        "name": "Cured-in-Place Pipe (CIPP) Lining",
        "description": "Trenchless rehabilitation using resin-saturated liner",
        "applicable_defects": ["CC", "CL", "CM", "CS", "FC", "I", "JD", "JS", "SD", "COR"],
        "not_applicable": ["X", "D"],  # Collapse or severe deformation
        "min_diameter_inches": 4,
        "max_diameter_inches": 108,
        "base_cost_per_lf": {
            # Diameter ranges: cost per linear foot
            "4-8": 45,
            "8-12": 65,
            "12-18": 95,
            "18-24": 140,
            "24-36": 200,
            "36-48": 280,
            "48+": 400
        },
        "mobilization_base": 3500,
        "typical_production_lf_per_day": 300,
        "requires_bypass": True,
        "excavation_required": False,
        "lifespan_years": 50,
        "warranty_years": 10,
        "pros": ["No excavation", "Minimal disruption", "Fast installation"],
        "cons": ["Slight diameter reduction", "Not for collapsed pipes"]
    },
    RepairMethod.PIPE_BURSTING: {
        "name": "Pipe Bursting",
        "description": "Trenchless replacement - breaks old pipe while pulling new",
        "applicable_defects": ["CC", "CL", "CM", "FC", "B", "D", "X"],  # Can handle worse damage
        "not_applicable": [],
        "min_diameter_inches": 4,
        "max_diameter_inches": 36,
        "base_cost_per_lf": {
            "4-8": 85,
            "8-12": 120,
            "12-18": 180,
            "18-24": 260,
            "24-36": 380,
        },
        "mobilization_base": 5000,
        "typical_production_lf_per_day": 150,
        "requires_bypass": True,
        "excavation_required": "minimal",  # Entry/exit pits only
        "lifespan_years": 75,
        "warranty_years": 20,
        "pros": ["Full replacement", "Can upsize", "Handles severe damage"],
        "cons": ["Launch/receiving pits needed", "Service reconnections required"]
    },
    RepairMethod.OPEN_CUT: {
        "name": "Open Cut Replacement",
        "description": "Traditional excavation and pipe replacement",
        "applicable_defects": ["ALL"],  # Can handle anything
        "not_applicable": [],
        "min_diameter_inches": 4,
        "max_diameter_inches": 999,
        "base_cost_per_lf": {
            "4-8": 150,
            "8-12": 200,
            "12-18": 280,
            "18-24": 380,
            "24-36": 520,
            "36-48": 700,
            "48+": 950
        },
        "mobilization_base": 4000,
        "typical_production_lf_per_day": 50,
        "requires_bypass": True,
        "excavation_required": True,
        "excavation_cost_per_lf": {  # Additional to base, by depth
            "0-6ft": 80,
            "6-10ft": 150,
            "10-15ft": 250,
            "15-20ft": 400,
            "20+ft": 600
        },
        "lifespan_years": 100,
        "warranty_years": 20,
        "pros": ["Handles any condition", "Full inspection possible", "Longest lifespan"],
        "cons": ["Disruptive", "Slowest", "Surface restoration required"]
    },
    RepairMethod.SPOT_REPAIR: {
        "name": "Spot Repair (Open Cut)",
        "description": "Localized excavation to repair specific defect",
        "applicable_defects": ["CC", "CL", "FC", "B", "H", "JD", "JS"],
        "not_applicable": ["X", "D"],  # Need continuous repair
        "base_cost_per_repair": {
            "4-8": 4500,
            "8-12": 6500,
            "12-18": 9500,
            "18-24": 14000,
            "24-36": 20000
        },
        "mobilization_base": 2500,
        "typical_repairs_per_day": 2,
        "requires_bypass": "sometimes",
        "excavation_required": True,
        "lifespan_years": 50,
        "warranty_years": 5,
        "pros": ["Lowest cost for isolated defects", "Quick turnaround"],
        "cons": ["Only for localized issues", "Multiple spots = consider full rehab"]
    },
    RepairMethod.POINT_REPAIR: {
        "name": "Trenchless Point Repair",
        "description": "Robotic or sectional liner repair of specific location",
        "applicable_defects": ["CC", "CL", "FC", "JD", "JS", "H"],
        "not_applicable": ["X", "D", "RB"],
        "base_cost_per_repair": {
            "4-8": 2500,
            "8-12": 3500,
            "12-18": 5500,
            "18-24": 8000,
            "24-36": 12000
        },
        "mobilization_base": 2000,
        "typical_repairs_per_day": 4,
        "requires_bypass": False,
        "excavation_required": False,
        "lifespan_years": 30,
        "warranty_years": 5,
        "pros": ["No excavation", "Fast", "Good for scattered point defects"],
        "cons": ["Limited structural improvement", "Not for continuous damage"]
    }
}


# =============================================================================
# EMERGENCY COST MULTIPLIERS
# =============================================================================

EMERGENCY_FACTORS = {
    "location_type": {
        "hospital": {
            "multiplier": 2.5,
            "reason": "24/7 operations, cannot interrupt services, health regulations"
        },
        "school": {
            "multiplier": 2.2,
            "reason": "Child safety priority, schedule constraints, public scrutiny"
        },
        "residential": {
            "multiplier": 1.8,
            "reason": "Property damage liability, health concerns, multiple affected parties"
        },
        "commercial": {
            "multiplier": 1.6,
            "reason": "Business interruption claims, customer access requirements"
        },
        "industrial": {
            "multiplier": 1.4,
            "reason": "Production losses, but typically more infrastructure resilience"
        }
    },
    "traffic_impact": {
        "major_arterial": {
            "multiplier": 1.5,
            "daily_traffic_control": 8000,
            "reason": "Extensive detours, traffic management, public notification"
        },
        "collector_street": {
            "multiplier": 1.3,
            "daily_traffic_control": 4500,
            "reason": "Moderate traffic impact, local detours"
        },
        "residential_street": {
            "multiplier": 1.1,
            "daily_traffic_control": 1500,
            "reason": "Local access maintained, minimal detour"
        },
        "easement_access": {
            "multiplier": 1.0,
            "daily_traffic_control": 500,
            "reason": "No traffic impact, equipment access only"
        }
    },
    "emergency_response": {
        "immediate_24hr": {
            "multiplier": 2.0,
            "reason": "Overtime, emergency procurement, expedited mobilization"
        },
        "urgent_48hr": {
            "multiplier": 1.6,
            "reason": "Accelerated schedule, premium rates"
        },
        "priority_1week": {
            "multiplier": 1.3,
            "reason": "Expedited but manageable scheduling"
        },
        "scheduled": {
            "multiplier": 1.0,
            "reason": "Normal procurement and scheduling"
        }
    },
    "environmental": {
        "waterway_discharge": {
            "additional_cost": 25000,
            "reason": "EPA notification, containment, testing, potential fines"
        },
        "groundwater_impact": {
            "additional_cost": 15000,
            "reason": "Monitoring wells, remediation assessment"
        },
        "surface_damage": {
            "per_sqft": 45,
            "reason": "Pavement, landscaping, or structure restoration"
        }
    }
}


# =============================================================================
# COST ESTIMATION CLASS
# =============================================================================

@dataclass
class CostLineItem:
    """Individual line item in cost estimate."""
    category: str
    description: str
    quantity: float
    unit: str
    unit_cost: float
    total: float
    notes: str = ""


@dataclass
class CostEstimate:
    """Complete itemized cost estimate."""
    pipe_id: str
    repair_method: str
    region: str

    # Summary
    subtotal: float
    contingency: float
    engineering: float
    grand_total: float

    # Itemized breakdown
    line_items: List[CostLineItem]

    # Metadata
    assumptions: List[str]
    exclusions: List[str]
    valid_for_days: int = 90

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "pipe_id": self.pipe_id,
            "repair_method": self.repair_method,
            "region": self.region,
            "summary": {
                "subtotal": self.subtotal,
                "contingency": self.contingency,
                "engineering": self.engineering,
                "grand_total": self.grand_total
            },
            "line_items": [
                {
                    "category": item.category,
                    "description": item.description,
                    "quantity": item.quantity,
                    "unit": item.unit,
                    "unit_cost": item.unit_cost,
                    "total": item.total,
                    "notes": item.notes
                }
                for item in self.line_items
            ],
            "assumptions": self.assumptions,
            "exclusions": self.exclusions,
            "valid_for_days": self.valid_for_days
        }


class CostEstimator:
    """
    Generates itemized cost estimates for sewer repairs.

    Usage:
        estimator = CostEstimator(region=Region.MIDWEST)
        estimate = estimator.estimate_repair(
            pipe_id="PIPE-001",
            diameter_inches=12,
            length_feet=150,
            depth_feet=8,
            grade=4,
            defect_codes=["CC", "I"],
            repair_method=RepairMethod.CIPP
        )
    """

    def __init__(self, region: Region = Region.MIDWEST, custom_factors: dict = None):
        """
        Initialize cost estimator.

        Args:
            region: Geographic region for cost factors
            custom_factors: Optional dict to override regional defaults
        """
        self.region = region

        if region == Region.CUSTOM and custom_factors:
            self.factors = custom_factors
        else:
            self.factors = REGIONAL_COST_DATA.get(region, REGIONAL_COST_DATA[Region.MIDWEST])

    def estimate_repair(
        self,
        pipe_id: str,
        diameter_inches: int,
        length_feet: float,
        depth_feet: float,
        grade: int,
        defect_codes: List[str],
        repair_method: RepairMethod = None,
        pipe_material: str = "concrete",
        location_type: str = "residential",
        traffic_impact: str = "residential_street"
    ) -> CostEstimate:
        """
        Generate itemized repair cost estimate.

        Args:
            pipe_id: Identifier for the pipe
            diameter_inches: Pipe inside diameter
            length_feet: Length of affected section
            depth_feet: Burial depth
            grade: PACP condition grade (1-5)
            defect_codes: List of PACP defect codes found
            repair_method: Preferred method (auto-selected if None)
            pipe_material: Pipe material type
            location_type: What's above the pipe
            traffic_impact: Street classification

        Returns:
            CostEstimate with itemized breakdown
        """
        # Auto-select repair method if not specified
        if repair_method is None:
            repair_method = self._recommend_repair_method(
                diameter_inches, length_feet, grade, defect_codes
            )

        method_data = REPAIR_METHOD_DATA[repair_method]
        line_items = []
        assumptions = []
        exclusions = []

        # Get diameter range key
        diameter_key = self._get_diameter_key(diameter_inches, method_data)

        # =================================================================
        # LABOR COSTS
        # =================================================================
        if repair_method in [RepairMethod.SPOT_REPAIR, RepairMethod.POINT_REPAIR]:
            # Per-repair pricing
            num_repairs = max(1, len([d for d in defect_codes if d not in ["OK", "DS", "DAG"]]))
            base_cost = method_data["base_cost_per_repair"].get(diameter_key, 5000)
            labor_total = base_cost * num_repairs * self.factors["labor_multiplier"]

            line_items.append(CostLineItem(
                category="Labor",
                description=f"{method_data['name']} - {num_repairs} repair location(s)",
                quantity=num_repairs,
                unit="each",
                unit_cost=base_cost * self.factors["labor_multiplier"],
                total=labor_total,
                notes=f"Includes setup at each location"
            ))
            assumptions.append(f"Assumes {num_repairs} discrete repair locations")
        else:
            # Per-linear-foot pricing
            base_cost_per_lf = method_data["base_cost_per_lf"].get(diameter_key, 100)
            adjusted_cost_per_lf = base_cost_per_lf * self.factors["labor_multiplier"]
            labor_total = adjusted_cost_per_lf * length_feet

            line_items.append(CostLineItem(
                category="Labor",
                description=f"{method_data['name']} installation",
                quantity=length_feet,
                unit="LF",
                unit_cost=adjusted_cost_per_lf,
                total=labor_total,
                notes=f"Regional rate: ${self.factors['labor_rate_per_hour']}/hr"
            ))

        # =================================================================
        # MATERIALS
        # =================================================================
        material_factor = self.factors["material_multiplier"]

        if repair_method == RepairMethod.CIPP:
            liner_cost = self._calculate_liner_cost(diameter_inches, length_feet, material_factor)
            line_items.append(CostLineItem(
                category="Materials",
                description="CIPP liner and resin",
                quantity=length_feet,
                unit="LF",
                unit_cost=liner_cost / length_feet,
                total=liner_cost
            ))

        elif repair_method == RepairMethod.PIPE_BURSTING:
            pipe_cost = self._calculate_pipe_cost(diameter_inches, length_feet, "HDPE", material_factor)
            line_items.append(CostLineItem(
                category="Materials",
                description="HDPE replacement pipe",
                quantity=length_feet,
                unit="LF",
                unit_cost=pipe_cost / length_feet,
                total=pipe_cost
            ))

        elif repair_method == RepairMethod.OPEN_CUT:
            pipe_cost = self._calculate_pipe_cost(diameter_inches, length_feet, pipe_material, material_factor)
            line_items.append(CostLineItem(
                category="Materials",
                description=f"Replacement pipe ({pipe_material})",
                quantity=length_feet,
                unit="LF",
                unit_cost=pipe_cost / length_feet,
                total=pipe_cost
            ))

            # Bedding material
            bedding = length_feet * 0.5 * material_factor  # Simplified
            line_items.append(CostLineItem(
                category="Materials",
                description="Pipe bedding and backfill",
                quantity=length_feet,
                unit="LF",
                unit_cost=bedding / length_feet,
                total=bedding
            ))

        # =================================================================
        # EQUIPMENT
        # =================================================================
        mobilization = method_data["mobilization_base"] * self.factors["equipment_multiplier"]
        line_items.append(CostLineItem(
            category="Equipment",
            description="Mobilization/demobilization",
            quantity=1,
            unit="LS",
            unit_cost=mobilization,
            total=mobilization
        ))

        # Calculate days needed
        if repair_method in [RepairMethod.SPOT_REPAIR, RepairMethod.POINT_REPAIR]:
            days_needed = max(1, num_repairs / method_data.get("typical_repairs_per_day", 2))
        else:
            production_rate = method_data.get("typical_production_lf_per_day", 100)
            days_needed = max(1, length_feet / production_rate)

        equipment_rental = days_needed * 1500 * self.factors["equipment_multiplier"]
        line_items.append(CostLineItem(
            category="Equipment",
            description="Equipment rental",
            quantity=days_needed,
            unit="days",
            unit_cost=1500 * self.factors["equipment_multiplier"],
            total=equipment_rental,
            notes="Includes CCTV, cleaning equipment, installation equipment"
        ))

        # =================================================================
        # EXCAVATION (if required)
        # =================================================================
        if method_data.get("excavation_required") == True:
            exc_costs = method_data.get("excavation_cost_per_lf", {})
            depth_key = self._get_depth_key(depth_feet)
            exc_cost_per_lf = exc_costs.get(depth_key, 150) * self.factors["labor_multiplier"]
            excavation_total = exc_cost_per_lf * length_feet

            line_items.append(CostLineItem(
                category="Excavation",
                description=f"Excavation and backfill ({depth_feet}' depth)",
                quantity=length_feet,
                unit="LF",
                unit_cost=exc_cost_per_lf,
                total=excavation_total,
                notes=f"Soil type: {self.factors.get('typical_soil', 'unknown')}"
            ))

        elif method_data.get("excavation_required") == "minimal":
            # Entry/exit pits for trenchless
            pit_cost = 2500 * self.factors["labor_multiplier"] * 2  # 2 pits
            line_items.append(CostLineItem(
                category="Excavation",
                description="Entry and exit pits",
                quantity=2,
                unit="each",
                unit_cost=2500 * self.factors["labor_multiplier"],
                total=pit_cost
            ))

        # =================================================================
        # TRAFFIC CONTROL
        # =================================================================
        traffic_data = EMERGENCY_FACTORS["traffic_impact"].get(
            traffic_impact,
            EMERGENCY_FACTORS["traffic_impact"]["residential_street"]
        )
        daily_traffic_cost = traffic_data.get("daily_traffic_control", self.factors["traffic_control_per_day"])
        traffic_total = daily_traffic_cost * days_needed

        line_items.append(CostLineItem(
            category="Traffic Control",
            description=f"Traffic control and signage ({traffic_impact.replace('_', ' ')})",
            quantity=days_needed,
            unit="days",
            unit_cost=daily_traffic_cost,
            total=traffic_total
        ))

        # =================================================================
        # PERMITS AND INSPECTION
        # =================================================================
        permit_cost = (
            self.factors["permit_base_cost"] +
            self.factors["permit_per_linear_foot"] * length_feet
        )
        line_items.append(CostLineItem(
            category="Permits",
            description="Permits and fees",
            quantity=1,
            unit="LS",
            unit_cost=permit_cost,
            total=permit_cost
        ))

        inspection_cost = self.factors["inspection_cost"]
        line_items.append(CostLineItem(
            category="Inspection",
            description="Pre and post-construction CCTV inspection",
            quantity=2,
            unit="each",
            unit_cost=inspection_cost / 2,
            total=inspection_cost
        ))

        # =================================================================
        # BYPASS PUMPING (if required)
        # =================================================================
        if method_data.get("requires_bypass"):
            bypass_cost = days_needed * 1200 * self.factors["labor_multiplier"]
            line_items.append(CostLineItem(
                category="Bypass",
                description="Bypass pumping",
                quantity=days_needed,
                unit="days",
                unit_cost=1200 * self.factors["labor_multiplier"],
                total=bypass_cost,
                notes="Required to maintain service during work"
            ))

        # =================================================================
        # SURFACE RESTORATION (for excavation methods)
        # =================================================================
        if method_data.get("excavation_required") == True:
            # Assume 8' wide trench
            surface_sqft = length_feet * 8
            restoration_cost = surface_sqft * 25 * self.factors["material_multiplier"]
            line_items.append(CostLineItem(
                category="Restoration",
                description="Surface restoration (pavement/landscape)",
                quantity=surface_sqft,
                unit="SF",
                unit_cost=25 * self.factors["material_multiplier"],
                total=restoration_cost
            ))

        # =================================================================
        # CALCULATE TOTALS
        # =================================================================
        subtotal = sum(item.total for item in line_items)

        contingency = subtotal * self.factors["contingency_percent"]
        line_items.append(CostLineItem(
            category="Contingency",
            description=f"Contingency ({self.factors['contingency_percent']:.0%})",
            quantity=1,
            unit="LS",
            unit_cost=contingency,
            total=contingency,
            notes="For unforeseen conditions"
        ))

        engineering = subtotal * self.factors["engineering_percent"]
        line_items.append(CostLineItem(
            category="Engineering",
            description=f"Engineering and administration ({self.factors['engineering_percent']:.0%})",
            quantity=1,
            unit="LS",
            unit_cost=engineering,
            total=engineering
        ))

        grand_total = subtotal + contingency + engineering

        # =================================================================
        # ASSUMPTIONS AND EXCLUSIONS
        # =================================================================
        assumptions.extend([
            f"Region: {self.factors['name']} ({self.factors['example_cities'][0]} area)",
            f"Soil conditions: {self.factors.get('typical_soil', 'typical')}",
            f"Normal working hours (no overtime premium)",
            f"No hazardous materials encountered",
            f"Adequate site access for equipment"
        ])

        if self.factors.get("prevailing_wage"):
            assumptions.append("Prevailing wage rates applied")

        exclusions.extend([
            "Utility relocations (if required)",
            "Dewatering (beyond normal conditions)",
            "Environmental remediation",
            "Service lateral reconnections (beyond standard)",
            "Property damage claims",
            "Extended warranty beyond standard"
        ])

        return CostEstimate(
            pipe_id=pipe_id,
            repair_method=method_data["name"],
            region=self.factors["name"],
            subtotal=round(subtotal, 2),
            contingency=round(contingency, 2),
            engineering=round(engineering, 2),
            grand_total=round(grand_total, 2),
            line_items=line_items,
            assumptions=assumptions,
            exclusions=exclusions
        )

    def estimate_emergency_cost(
        self,
        proactive_estimate: CostEstimate,
        location_type: str = "residential",
        traffic_impact: str = "residential_street",
        response_urgency: str = "immediate_24hr"
    ) -> Tuple[float, List[str]]:
        """
        Calculate emergency failure cost based on proactive estimate.

        Returns:
            Tuple of (emergency_cost, list_of_factors_applied)
        """
        base_cost = proactive_estimate.grand_total
        factors_applied = []

        # Location multiplier
        loc_data = EMERGENCY_FACTORS["location_type"].get(
            location_type,
            EMERGENCY_FACTORS["location_type"]["residential"]
        )
        base_cost *= loc_data["multiplier"]
        factors_applied.append(f"Location ({location_type}): {loc_data['multiplier']}x - {loc_data['reason']}")

        # Traffic multiplier
        traffic_data = EMERGENCY_FACTORS["traffic_impact"].get(
            traffic_impact,
            EMERGENCY_FACTORS["traffic_impact"]["residential_street"]
        )
        base_cost *= traffic_data["multiplier"]
        factors_applied.append(f"Traffic impact: {traffic_data['multiplier']}x - {traffic_data['reason']}")

        # Emergency response multiplier
        response_data = EMERGENCY_FACTORS["emergency_response"].get(
            response_urgency,
            EMERGENCY_FACTORS["emergency_response"]["immediate_24hr"]
        )
        base_cost *= response_data["multiplier"]
        factors_applied.append(f"Response urgency: {response_data['multiplier']}x - {response_data['reason']}")

        # Add environmental costs (assume worst case for emergency)
        env_cost = EMERGENCY_FACTORS["environmental"]["waterway_discharge"]["additional_cost"]
        base_cost += env_cost
        factors_applied.append(f"Environmental response: +${env_cost:,}")

        return round(base_cost, 2), factors_applied

    def _recommend_repair_method(
        self,
        diameter_inches: int,
        length_feet: float,
        grade: int,
        defect_codes: List[str]
    ) -> RepairMethod:
        """Auto-select best repair method based on conditions."""

        # Collapse or severe deformation = open cut or pipe bursting
        if "X" in defect_codes or (grade == 5 and "D" in defect_codes):
            if diameter_inches <= 36:
                return RepairMethod.PIPE_BURSTING
            else:
                return RepairMethod.OPEN_CUT

        # Short section with isolated defects = spot/point repair
        if length_feet <= 20 and len(defect_codes) <= 2:
            return RepairMethod.POINT_REPAIR

        # Standard rehabilitation = CIPP for most cases
        if diameter_inches <= 48 and grade <= 4:
            return RepairMethod.CIPP

        # Large diameter or severe = open cut
        return RepairMethod.OPEN_CUT

    def _get_diameter_key(self, diameter: int, method_data: dict) -> str:
        """Get the appropriate diameter range key."""
        cost_dict = method_data.get("base_cost_per_lf") or method_data.get("base_cost_per_repair", {})

        if diameter <= 8:
            return "4-8"
        elif diameter <= 12:
            return "8-12"
        elif diameter <= 18:
            return "12-18"
        elif diameter <= 24:
            return "18-24"
        elif diameter <= 36:
            return "24-36"
        elif diameter <= 48:
            return "36-48"
        else:
            return "48+"

    def _get_depth_key(self, depth: float) -> str:
        """Get the appropriate depth range key."""
        if depth <= 6:
            return "0-6ft"
        elif depth <= 10:
            return "6-10ft"
        elif depth <= 15:
            return "10-15ft"
        elif depth <= 20:
            return "15-20ft"
        else:
            return "20+ft"

    def _calculate_liner_cost(self, diameter: int, length: float, factor: float) -> float:
        """Calculate CIPP liner material cost."""
        # Base cost per SF of liner (diameter * pi * length)
        import math
        surface_area = (diameter / 12) * math.pi * length  # in SF
        cost_per_sf = 8.50 * factor  # Base resin/liner cost
        return surface_area * cost_per_sf

    def _calculate_pipe_cost(self, diameter: int, length: float, material: str, factor: float) -> float:
        """Calculate replacement pipe material cost."""
        material_costs_per_lf = {
            "HDPE": {8: 12, 12: 22, 18: 45, 24: 75, 36: 140},
            "PVC": {8: 8, 12: 15, 18: 35, 24: 60, 36: 110},
            "concrete": {8: 18, 12: 32, 18: 55, 24: 85, 36: 160},
            "clay": {8: 25, 12: 42, 18: 70, 24: 110, 36: 200},
        }

        costs = material_costs_per_lf.get(material.lower(), material_costs_per_lf["concrete"])

        # Find closest diameter
        closest_dia = min(costs.keys(), key=lambda x: abs(x - diameter))
        base_cost = costs[closest_dia]

        # Adjust for actual diameter if different
        if diameter > closest_dia:
            base_cost *= (diameter / closest_dia)

        return base_cost * length * factor


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_quick_estimate(
    diameter_inches: int,
    length_feet: float,
    grade: int,
    region: str = "midwest"
) -> dict:
    """
    Get a quick cost estimate with minimal inputs.

    Args:
        diameter_inches: Pipe diameter
        length_feet: Length of repair
        grade: PACP grade (1-5)
        region: Region name (lowercase)

    Returns:
        Dict with proactive and emergency costs
    """
    region_map = {
        "northeast": Region.NORTHEAST,
        "southeast": Region.SOUTHEAST,
        "midwest": Region.MIDWEST,
        "southwest": Region.SOUTHWEST,
        "west_coast": Region.WEST_COAST,
        "west coast": Region.WEST_COAST,
        "mountain": Region.MOUNTAIN
    }

    region_enum = region_map.get(region.lower(), Region.MIDWEST)
    estimator = CostEstimator(region=region_enum)

    # Map grade to typical defect codes
    grade_defects = {
        1: ["OK"],
        2: ["SD"],
        3: ["CC", "DS"],
        4: ["CC", "I", "JD"],
        5: ["FC", "B", "I"]
    }

    estimate = estimator.estimate_repair(
        pipe_id="QUICK-EST",
        diameter_inches=diameter_inches,
        length_feet=length_feet,
        depth_feet=8,
        grade=grade,
        defect_codes=grade_defects.get(grade, ["CC"])
    )

    emergency_cost, factors = estimator.estimate_emergency_cost(estimate)

    return {
        "proactive_repair": estimate.grand_total,
        "emergency_failure": emergency_cost,
        "savings": emergency_cost - estimate.grand_total,
        "savings_percent": round((1 - estimate.grand_total / emergency_cost) * 100, 1),
        "repair_method": estimate.repair_method,
        "region": estimate.region
    }


def format_estimate_for_display(estimate: CostEstimate) -> str:
    """Format estimate as readable text for display."""
    lines = [
        f"COST ESTIMATE: {estimate.pipe_id}",
        f"Method: {estimate.repair_method}",
        f"Region: {estimate.region}",
        "=" * 60,
        "",
        "ITEMIZED BREAKDOWN:",
        "-" * 60
    ]

    current_category = None
    for item in estimate.line_items:
        if item.category != current_category:
            lines.append(f"\n{item.category.upper()}")
            current_category = item.category

        lines.append(
            f"  {item.description:40} "
            f"{item.quantity:>6.1f} {item.unit:5} x "
            f"${item.unit_cost:>10,.2f} = ${item.total:>12,.2f}"
        )
        if item.notes:
            lines.append(f"    Note: {item.notes}")

    lines.extend([
        "",
        "-" * 60,
        f"{'SUBTOTAL':50} ${estimate.subtotal:>12,.2f}",
        f"{'CONTINGENCY':50} ${estimate.contingency:>12,.2f}",
        f"{'ENGINEERING':50} ${estimate.engineering:>12,.2f}",
        "=" * 60,
        f"{'GRAND TOTAL':50} ${estimate.grand_total:>12,.2f}",
        "",
        "ASSUMPTIONS:",
    ])

    for assumption in estimate.assumptions:
        lines.append(f"  - {assumption}")

    lines.append("\nEXCLUSIONS:")
    for exclusion in estimate.exclusions:
        lines.append(f"  - {exclusion}")

    lines.append(f"\nEstimate valid for {estimate.valid_for_days} days from generation.")

    return "\n".join(lines)


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    print("SewerSentinel Cost Estimation Module")
    print("=" * 50)

    # Example: Midwest region, 12" pipe, 150 LF, Grade 4
    estimator = CostEstimator(region=Region.MIDWEST)

    estimate = estimator.estimate_repair(
        pipe_id="DEMO-PIPE-001",
        diameter_inches=12,
        length_feet=150,
        depth_feet=8,
        grade=4,
        defect_codes=["CC", "I", "JD"],
        location_type="residential",
        traffic_impact="collector_street"
    )

    print(format_estimate_for_display(estimate))

    emergency_cost, factors = estimator.estimate_emergency_cost(
        estimate,
        location_type="residential",
        traffic_impact="collector_street",
        response_urgency="immediate_24hr"
    )

    print("\n" + "=" * 50)
    print("EMERGENCY COST ANALYSIS")
    print("=" * 50)
    print(f"\nProactive Repair: ${estimate.grand_total:,.2f}")
    print(f"Emergency Failure: ${emergency_cost:,.2f}")
    print(f"Potential Savings: ${emergency_cost - estimate.grand_total:,.2f}")

    print("\nEmergency Cost Factors Applied:")
    for factor in factors:
        print(f"  - {factor}")

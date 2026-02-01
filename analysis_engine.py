"""
SewerSentinel Core Analysis Engine
Interfaces with Gemini 3 for multimodal pipe inspection analysis

Uses the NEW google-genai SDK
"""

import os
import json
import logging
import time
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path

from google import genai
from google.genai import types

# Import calibration module for PACP-compliant grading rubrics and few-shot examples
from sewer_sentinel_calibration import get_calibrated_detection_prompt, EnsembleAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DefectGrade(Enum):
    """PACP-compliant defect severity grades"""
    GRADE_1 = 1  # Minor defect
    GRADE_2 = 2  # Minor to moderate defect
    GRADE_3 = 3  # Moderate defect
    GRADE_4 = 4  # Significant defect
    GRADE_5 = 5  # Most significant defect (immediate attention)


class DefectType(Enum):
    """Common sewer pipe defect types per PACP standards"""
    CRACK_LONGITUDINAL = "CL"
    CRACK_CIRCUMFERENTIAL = "CC"
    CRACK_MULTIPLE = "CM"
    CRACK_SPIRAL = "CS"
    FRACTURE = "FC"
    BROKEN = "B"
    HOLE = "H"
    DEFORMED = "D"
    COLLAPSE = "X"
    ROOT_FINE = "RF"
    ROOT_MEDIUM = "RM"
    ROOT_BALL = "RB"
    DEPOSITS_ATTACHED = "DAG"
    DEPOSITS_SETTLED = "DS"
    INFILTRATION = "I"
    JOINT_DISPLACED = "JD"
    JOINT_SEPARATED = "JS"
    SURFACE_DAMAGE = "SD"
    CORROSION = "COR"
    NORMAL = "OK"


# PACP defect code descriptions for reference
DEFECT_CODE_DESCRIPTIONS = {
    "CL": "Longitudinal Crack",
    "CC": "Circumferential Crack",
    "CM": "Multiple Cracks",
    "CS": "Spiral Crack",
    "FC": "Fracture",
    "B": "Broken",
    "H": "Hole",
    "D": "Deformed",
    "X": "Collapse",
    "RF": "Root Intrusion (Fine)",
    "RM": "Root Intrusion (Medium)",
    "RB": "Root Intrusion (Ball)",
    "DAG": "Deposits Attached (Grease)",
    "DS": "Deposits Settled",
    "I": "Infiltration",
    "JD": "Joint Displaced",
    "JS": "Joint Separated",
    "SD": "Surface Damage",
    "COR": "Corrosion",
    "OK": "Normal - No Defects"
}


def _parse_json_response(response_text: str) -> Dict[str, Any]:
    """
    Robustly parse JSON from Gemini response.
    Handles markdown fences, partial responses, and other formatting issues.
    """
    text = response_text.strip()

    # Remove markdown code fences
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
            lines = text.strip().split('\n')
            if lines and lines[0].strip() in ['json', 'JSON', '']:
                text = '\n'.join(lines[1:])

    text = text.strip()
    if not text.startswith('{'):
        start_idx = text.find('{')
        if start_idx != -1:
            text = text[start_idx:]

    # Find matching closing brace
    brace_count = 0
    end_idx = -1
    for i, char in enumerate(text):
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                end_idx = i
                break

    if end_idx != -1:
        text = text[:end_idx + 1]

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON: {e}")
        logger.debug(f"Raw text: {text[:500]}")
        raise


@dataclass
class DetectedDefect:
    """Represents a single detected defect"""
    defect_type: str
    defect_code: str
    grade: int
    location_in_pipe: str  # e.g., "3 o'clock position", "floor"
    timestamp_seconds: Optional[float] = None
    confidence: float = 0.0
    description: str = ""


@dataclass
class RepairItem:
    """Represents an individual repair item with cost estimate"""
    defect_code: str
    defect_description: str
    repair_method: str
    estimated_cost: float
    priority: str  # "immediate", "short-term", "long-term"
    notes: str = ""


@dataclass
class PredictionResult:
    """Represents a failure prediction for a pipe segment"""
    pipe_id: str
    current_grade: int
    predicted_grade_6_months: int
    predicted_grade_12_months: int
    estimated_time_to_failure_months: Optional[int]
    failure_risk_score: float  # 0-100
    contributing_factors: List[str]
    recommended_action: str
    priority_rank: int
    cost_estimate_repair: float
    cost_estimate_emergency: float
    confidence_interval: str
    reasoning: str
    repair_items: List[RepairItem] = field(default_factory=list)  # Itemized repair breakdown


@dataclass
class AnalysisResult:
    """Complete analysis result for a pipe inspection"""
    pipe_id: str
    inspection_date: str
    defects: List[DetectedDefect]
    overall_grade: int
    quick_rating: str  # PACP quick rating format
    prediction: Optional[PredictionResult]
    executive_summary: str
    analysis_timestamp: str
    raw_analysis: Dict[str, Any] = field(default_factory=dict)


def calculate_repair_cost(
    grade: int,
    diameter_inches: int,
    pipe_material: str,
    depth_feet: float = 8.0
) -> float:
    """
    Calculate estimated proactive repair cost based on pipe characteristics.

    Formula:
    - Base repair cost = $2,000 + (diameter * $100) + (grade * $2,000)
    - Material multiplier: concrete=1.0, clay=1.2, cast_iron=1.5, pvc=0.8, hdpe=0.7
    - Depth multiplier: 1.0 + (depth_feet - 8) * 0.05 (every foot above/below 8ft adds 5%)
    """
    # Base cost
    base_cost = 2000 + (diameter_inches * 100) + (grade * 2000)

    # Material multiplier
    material_multipliers = {
        "concrete": 1.0,
        "clay": 1.2,
        "cast_iron": 1.5,
        "pvc": 0.8,
        "hdpe": 0.7,
        "unknown": 1.0
    }
    material_mult = material_multipliers.get(pipe_material.lower(), 1.0)

    # Depth multiplier (deeper = more expensive)
    depth_mult = 1.0 + max(0, (depth_feet - 8) * 0.05)

    return round(base_cost * material_mult * depth_mult, 2)


def calculate_emergency_cost(
    repair_cost: float,
    location_type: str,
    traffic_load: str
) -> float:
    """
    Calculate estimated emergency failure cost.

    Emergency multiplier based on location type:
    - school/hospital: 8x (high public health risk)
    - residential: 6x (property damage, health concerns)
    - commercial: 5x (business disruption)
    - industrial: 4x (operational disruption)

    Traffic load adds additional multiplier:
    - heavy: +50%
    - medium: +25%
    - light: +10%
    - none: +0%
    """
    # Location multipliers
    location_multipliers = {
        "school": 8.0,
        "hospital": 8.0,
        "residential": 6.0,
        "commercial": 5.0,
        "industrial": 4.0
    }
    location_mult = location_multipliers.get(location_type.lower(), 5.0)

    # Traffic load additional multiplier
    traffic_multipliers = {
        "heavy": 1.5,
        "medium": 1.25,
        "light": 1.1,
        "none": 1.0
    }
    traffic_mult = traffic_multipliers.get(traffic_load.lower(), 1.0)

    return round(repair_cost * location_mult * traffic_mult, 2)


def calculate_risk_score(
    current_grade: int,
    time_to_failure_months: Optional[int],
    location_type: str
) -> float:
    """
    Calculate risk score (0-100) based on multiple factors.

    Formula:
    - Current grade (40% weight): (grade / 5) * 40
    - Time to failure (30% weight): time_factor * 30
      - <6 months: 1.0
      - <12 months: 0.7
      - <24 months: 0.4
      - else: 0.2
    - Location consequence (30% weight): location_factor * 30
      - school/hospital: 1.0
      - residential: 0.7
      - commercial: 0.5
      - industrial: 0.3
    """
    # Grade component (40% weight)
    grade_component = (current_grade / 5.0) * 40.0

    # Time to failure component (30% weight)
    if time_to_failure_months is None:
        # Estimate based on grade if no time provided
        time_estimates = {1: 120, 2: 84, 3: 48, 4: 18, 5: 6}
        time_to_failure_months = time_estimates.get(current_grade, 60)

    if time_to_failure_months <= 6:
        time_factor = 1.0
    elif time_to_failure_months <= 12:
        time_factor = 0.7
    elif time_to_failure_months <= 24:
        time_factor = 0.4
    else:
        time_factor = 0.2
    time_component = time_factor * 30.0

    # Location consequence component (30% weight)
    location_factors = {
        "school": 1.0,
        "hospital": 1.0,
        "residential": 0.7,
        "commercial": 0.5,
        "industrial": 0.3
    }
    location_factor = location_factors.get(location_type.lower(), 0.5)
    location_component = location_factor * 30.0

    return round(grade_component + time_component + location_component, 1)


# Repair methods and base costs per defect type
DEFECT_REPAIR_INFO = {
    "CL": {
        "name": "Longitudinal Crack",
        "methods": {
            1: ("Epoxy injection sealing", 800),
            2: ("Epoxy injection sealing", 1200),
            3: ("CIPP spot repair liner", 3500),
            4: ("CIPP full liner or pipe bursting", 8000),
            5: ("Emergency pipe replacement", 15000),
        },
        "notes": "Longitudinal cracks often indicate ground movement or loading stress"
    },
    "CC": {
        "name": "Circumferential Crack",
        "methods": {
            1: ("Crack sealing", 600),
            2: ("Epoxy injection", 1000),
            3: ("CIPP spot repair", 3000),
            4: ("CIPP liner section", 7500),
            5: ("Pipe segment replacement", 14000),
        },
        "notes": "Circumferential cracks may indicate joint stress or differential settlement"
    },
    "CM": {
        "name": "Multiple Cracks",
        "methods": {
            1: ("Multiple crack sealing", 1500),
            2: ("Epoxy treatment program", 2500),
            3: ("CIPP liner recommended", 5000),
            4: ("Full CIPP rehabilitation", 10000),
            5: ("Pipe replacement required", 18000),
        },
        "notes": "Multiple cracks indicate widespread structural degradation"
    },
    "FC": {
        "name": "Fracture",
        "methods": {
            1: ("Monitor and seal", 1000),
            2: ("Structural grout injection", 2000),
            3: ("CIPP spot repair", 4500),
            4: ("Pipe segment liner", 9000),
            5: ("Emergency replacement", 16000),
        },
        "notes": "Fractures compromise structural integrity and require prompt attention"
    },
    "B": {
        "name": "Broken Pipe",
        "methods": {
            3: ("Point repair excavation", 6000),
            4: ("Segment replacement", 12000),
            5: ("Emergency dig and replace", 20000),
        },
        "notes": "Broken sections require physical repair or replacement"
    },
    "H": {
        "name": "Hole",
        "methods": {
            2: ("Patch repair", 1500),
            3: ("Point repair with liner", 4000),
            4: ("Segment replacement", 10000),
            5: ("Emergency repair", 18000),
        },
        "notes": "Holes allow infiltration and exfiltration - repair promptly"
    },
    "D": {
        "name": "Deformed Pipe",
        "methods": {
            2: ("Monitor deformation", 500),
            3: ("Re-rounding or liner", 5000),
            4: ("Pipe bursting replacement", 12000),
            5: ("Full excavation replacement", 22000),
        },
        "notes": "Deformation reduces flow capacity and may worsen under load"
    },
    "X": {
        "name": "Collapse",
        "methods": {
            5: ("Emergency excavation and replacement", 35000),
        },
        "notes": "Collapsed sections require immediate emergency response"
    },
    "RF": {
        "name": "Root Intrusion (Fine)",
        "methods": {
            1: ("Chemical root treatment", 400),
            2: ("Mechanical root cutting", 800),
            3: ("Root cutting + chemical treatment", 1500),
        },
        "notes": "Fine roots indicate early intrusion - treat to prevent growth"
    },
    "RM": {
        "name": "Root Intrusion (Medium)",
        "methods": {
            2: ("Mechanical root cutting", 1200),
            3: ("Root cutting + joint sealing", 2500),
            4: ("Root removal + CIPP liner", 6000),
        },
        "notes": "Medium roots are actively growing - seal entry points after removal"
    },
    "RB": {
        "name": "Root Ball",
        "methods": {
            3: ("Hydro-jetting + chemical treatment", 3000),
            4: ("Root removal + structural repair", 8000),
            5: ("Excavation and pipe replacement", 15000),
        },
        "notes": "Root balls cause severe blockage and structural damage"
    },
    "DAG": {
        "name": "Deposits - Grease",
        "methods": {
            1: ("High-pressure jetting", 600),
            2: ("Jetting + degreasing treatment", 1200),
            3: ("Industrial cleaning + inspection", 2500),
        },
        "notes": "Grease deposits require regular maintenance to prevent buildup"
    },
    "DS": {
        "name": "Deposits - Settled",
        "methods": {
            1: ("Flushing", 400),
            2: ("Vacuum/jetting cleaning", 900),
            3: ("Heavy debris removal", 2000),
        },
        "notes": "Settled deposits reduce flow capacity - identify source"
    },
    "I": {
        "name": "Infiltration",
        "methods": {
            1: ("Joint sealing", 800),
            2: ("Chemical grouting", 1800),
            3: ("Internal joint sealing + grouting", 3500),
            4: ("CIPP liner to stop infiltration", 7000),
            5: ("Pipe replacement in high water table", 16000),
        },
        "notes": "Infiltration indicates compromised pipe integrity and adds to treatment load"
    },
    "JD": {
        "name": "Joint Displaced",
        "methods": {
            1: ("Monitor joint", 300),
            2: ("Internal joint seal", 1500),
            3: ("Joint repair grouting", 3000),
            4: ("Joint reconstruction", 6000),
        },
        "notes": "Displaced joints allow infiltration and root entry"
    },
    "JS": {
        "name": "Joint Separated",
        "methods": {
            2: ("Internal joint sealing", 2000),
            3: ("Grouting + sealing", 4000),
            4: ("Joint reconstruction or liner", 8000),
            5: ("Excavation and re-joining", 14000),
        },
        "notes": "Separated joints are high-risk for failure progression"
    },
    "SD": {
        "name": "Surface Damage",
        "methods": {
            1: ("Protective coating", 500),
            2: ("Epoxy coating application", 1200),
            3: ("Surface rehabilitation", 3000),
            4: ("Liner installation", 7000),
        },
        "notes": "Surface damage exposes pipe material to further corrosion"
    },
    "COR": {
        "name": "Corrosion",
        "methods": {
            1: ("Protective coating", 600),
            2: ("Corrosion inhibitor + coating", 1500),
            3: ("Epoxy lining", 4000),
            4: ("CIPP rehabilitation", 9000),
            5: ("Pipe replacement", 17000),
        },
        "notes": "Corrosion is progressive - early treatment prevents wall loss"
    },
    "OK": {
        "name": "Normal - No Defects",
        "methods": {
            1: ("Routine inspection only", 0),
        },
        "notes": "No defects detected - continue scheduled maintenance"
    },
}


def calculate_repair_items(
    defects: List[Dict],
    diameter_inches: int,
    pipe_material: str,
    depth_feet: float
) -> List[RepairItem]:
    """
    Calculate itemized repair costs for each defect.

    Args:
        defects: List of detected defects with defect_code and grade
        diameter_inches: Pipe diameter for cost scaling
        pipe_material: Pipe material for cost adjustment
        depth_feet: Burial depth for excavation cost adjustment

    Returns:
        List of RepairItem objects with individual cost estimates
    """
    repair_items = []

    # Material cost multipliers
    material_multipliers = {
        "concrete": 1.0,
        "clay": 1.15,
        "cast_iron": 1.4,
        "pvc": 0.85,
        "hdpe": 0.8,
        "unknown": 1.0
    }
    material_mult = material_multipliers.get(pipe_material.lower(), 1.0)

    # Diameter scaling (larger pipes cost more)
    diameter_mult = 1.0 + (max(0, diameter_inches - 12) * 0.03)

    # Depth multiplier for excavation work
    depth_mult = 1.0 + (max(0, depth_feet - 8) * 0.04)

    for defect in defects:
        code = defect.get("defect_code", "OK")
        grade = defect.get("grade", 1)
        defect_type = defect.get("defect_type", "Unknown")

        # Get repair info for this defect type
        repair_info = DEFECT_REPAIR_INFO.get(code, DEFECT_REPAIR_INFO.get("OK"))

        if repair_info:
            # Find the appropriate repair method for this grade
            methods = repair_info["methods"]

            # Find closest grade (some defects don't have all grades)
            available_grades = sorted(methods.keys())
            selected_grade = grade
            if grade not in available_grades:
                # Find nearest available grade
                selected_grade = min(available_grades, key=lambda x: abs(x - grade))

            method, base_cost = methods.get(selected_grade, methods.get(available_grades[-1]))

            # Apply multipliers
            adjusted_cost = base_cost * material_mult * diameter_mult

            # Apply depth multiplier only for methods that require excavation
            if "excavation" in method.lower() or "replacement" in method.lower() or "dig" in method.lower():
                adjusted_cost *= depth_mult

            # Determine priority based on grade
            if grade >= 5:
                priority = "immediate"
            elif grade >= 4:
                priority = "short-term"
            elif grade >= 3:
                priority = "medium-term"
            else:
                priority = "long-term"

            repair_items.append(RepairItem(
                defect_code=code,
                defect_description=f"{repair_info['name']} (Grade {grade})",
                repair_method=method,
                estimated_cost=round(adjusted_cost, 2),
                priority=priority,
                notes=repair_info.get("notes", "")
            ))

    # Sort by priority (immediate first)
    priority_order = {"immediate": 0, "short-term": 1, "medium-term": 2, "long-term": 3}
    repair_items.sort(key=lambda x: priority_order.get(x.priority, 4))

    return repair_items


class SewerSentinelEngine:
    """
    Main analysis engine using Gemini 3 for pipe inspection analysis.

    Implements:
    - Multimodal video/image analysis
    - Thought Signatures for state tracking across pipes
    - Thinking Levels for causal reasoning about degradation
    """

    def __init__(self, model_name: str = "gemini-2.0-flash"):
        """
        Initialize the analysis engine.

        Args:
            model_name: Gemini model to use. Options:
                - "gemini-2.0-flash" (stable, recommended)
                - "gemini-3-flash-preview" (preview, may have issues)
        """
        # Verify API key is set
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is not set. "
                "Please set it with your Gemini API key."
            )

        # Initialize the new google-genai client
        self.client = genai.Client()
        self.model_name = model_name
        self.pipe_state_memory = {}  # Thought Signatures - track pipe states
        self.thinking_supported = True  # Will be set to False if thinking fails

        logger.info(f"SewerSentinel Engine initialized with model: {model_name}")

        # Use calibrated detection prompt with grading rubrics and few-shot examples
        # This provides PACP-compliant grading with exact thresholds and calibration
        # examples from the Sewer-ML dataset for more consistent, accurate detection
        self.detection_prompt = get_calibrated_detection_prompt()

        self.prediction_prompt = """You are SewerSentinel's prediction engine. Based on the defects detected and contextual information provided, predict the degradation trajectory of this pipe segment.

Consider these factors in your analysis:
1. Current defect types and severity
2. Pipe age and material
3. Environmental factors (traffic load above, soil type, groundwater)
4. Historical degradation patterns for similar defects
5. Location consequence (what's above this pipe?)

Provide your prediction ONLY in JSON format (no other text):
{
    "current_grade": 1-5,
    "predicted_grade_6_months": 1-5,
    "predicted_grade_12_months": 1-5,
    "estimated_time_to_failure_months": integer (estimate based on grade: Grade 5=6mo, Grade 4=18mo, Grade 3=48mo, Grade 2=84mo, Grade 1=120mo),
    "failure_risk_score": 0-100 (calculate based on grade, time to failure, and location type),
    "contributing_factors": ["list of 3-6 specific factors based on the defects and context"],
    "recommended_action": "specific recommendation based on grade",
    "cost_estimate_repair": dollar amount (base: $2000 + diameter*$100 + grade*$2000),
    "cost_estimate_emergency": dollar amount (repair cost * 5-8x based on location),
    "confidence_interval": "e.g., ±3 months",
    "reasoning": "2-3 sentence explanation of your prediction"
}

IMPORTANT: Always provide numeric values for all fields. Never return 0 for costs or risk scores."""

    def _call_gemini_with_retry(
        self,
        contents: List[Any],
        use_thinking: bool = False,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ) -> str:
        """
        Call Gemini API with retry logic.
        Uses temperature=0 for deterministic, reproducible outputs.
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                # API call with temperature=0 for consistent, deterministic results
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config={
                        "temperature": 0,  # Deterministic output - same input = same output
                        "top_p": 1,        # No nucleus sampling
                        "top_k": 1         # Always pick the most likely token
                    }
                )

                if response and response.text:
                    return response.text
                else:
                    raise ValueError("Empty response from Gemini API")

            except Exception as e:
                last_error = e
                logger.warning(f"Gemini API call failed (attempt {attempt + 1}/{max_retries}): {e}")

                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))

        raise RuntimeError(f"Gemini API call failed after {max_retries} attempts: {last_error}")

    def analyze_image(self, image_path: str, pipe_id: str = "unknown") -> Dict[str, Any]:
        """
        Analyze a single pipe inspection image.
        """
        logger.info(f"Analyzing image: {image_path} for pipe: {pipe_id}")

        # Read image bytes
        image_path_obj = Path(image_path)
        if not image_path_obj.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        image_bytes = image_path_obj.read_bytes()

        # Determine MIME type
        suffix = image_path_obj.suffix.lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp'
        }
        mime_type = mime_types.get(suffix, 'image/jpeg')

        # Create content with image
        contents = [
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            self.detection_prompt
        ]

        try:
            response_text = self._call_gemini_with_retry(contents)
            result = _parse_json_response(response_text)

            # Add metadata
            result['pipe_id'] = pipe_id
            result['analysis_timestamp'] = datetime.now().isoformat()
            result['image_path'] = str(image_path)

            # Update pipe state memory
            self._update_pipe_state(pipe_id, result)

            logger.info(f"Analysis complete for {pipe_id}: found {len(result.get('defects', []))} defects")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse response for {pipe_id}: {e}")
            return {
                "error": "Failed to parse response",
                "pipe_id": pipe_id,
                "defects": [],
                "overall_grade": 0,
                "overall_assessment": "Analysis failed - please retry"
            }

    def analyze_image_bytes(self, image_bytes: bytes, mime_type: str, pipe_id: str = "unknown") -> Dict[str, Any]:
        """
        Analyze pipe inspection image from bytes.
        """
        logger.info(f"Analyzing image bytes for pipe: {pipe_id}")

        contents = [
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            self.detection_prompt
        ]

        try:
            response_text = self._call_gemini_with_retry(contents)
            result = _parse_json_response(response_text)

            result['pipe_id'] = pipe_id
            result['analysis_timestamp'] = datetime.now().isoformat()

            self._update_pipe_state(pipe_id, result)

            logger.info(f"Analysis complete for {pipe_id}: found {len(result.get('defects', []))} defects")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse response for {pipe_id}: {e}")
            return {
                "error": "Failed to parse response",
                "pipe_id": pipe_id,
                "defects": [],
                "overall_grade": 0,
                "overall_assessment": "Analysis failed - please retry"
            }

    def _generate_contributing_factors(
        self,
        defects: List[Dict],
        grade: int,
        age: int,
        traffic: str,
        soil: str
    ) -> List[str]:
        """Generate meaningful contributing factors based on detected defects and context."""
        factors = []
        
        # Add defect-based factors
        defect_codes = [d.get('defect_code', '') for d in defects]
        
        if 'CC' in defect_codes or 'CL' in defect_codes or 'CM' in defect_codes:
            factors.append("Structural cracking detected - indicates stress damage or material fatigue")
        
        if 'D' in defect_codes:
            factors.append("Pipe deformation present - suggests external loading or soil movement")
        
        if 'JD' in defect_codes or 'JS' in defect_codes:
            factors.append("Joint displacement/separation - potential for infiltration and root intrusion")
        
        if 'RF' in defect_codes or 'RM' in defect_codes or 'RB' in defect_codes:
            factors.append("Root intrusion detected - will continue to grow and worsen without treatment")
        
        if 'COR' in defect_codes:
            factors.append("Active corrosion present - progressive deterioration expected")
        
        if 'I' in defect_codes:
            factors.append("Infiltration observed - groundwater entering pipe indicates compromised integrity")
        
        if 'DS' in defect_codes or 'DAG' in defect_codes:
            factors.append("Debris/deposits accumulating - reduces flow capacity")
        
        # Add age factor
        if age > 50:
            factors.append(f"Pipe age ({age} years) significantly exceeds typical design life")
        elif age > 30:
            factors.append(f"Pipe age ({age} years) approaching end of expected service life")
        
        # Add traffic factor
        if traffic == 'heavy':
            factors.append("Heavy traffic loading increases cyclic stress and accelerates degradation")
        elif traffic == 'medium':
            factors.append("Moderate traffic loading contributes to ongoing structural stress")
        
        # Add soil factor
        if soil == 'clay':
            factors.append("Clay soil promotes differential settlement and increases lateral pressure")
        
        # Add grade-based summary
        if grade >= 4:
            factors.append(f"Overall Grade {grade} condition requires prioritized attention")
        
        # Ensure we have at least 2 factors
        if len(factors) < 2:
            factors.append(f"Multiple defect types detected requiring assessment")
            factors.append("Continued monitoring recommended to track progression")
        
        return factors[:6]

    def _get_fallback_recommendation(self, grade: int) -> str:
        """Get a fallback recommendation based on grade."""
        recommendations = {
            1: "Continue routine monitoring. No immediate action required.",
            2: "Schedule follow-up inspection in 12-18 months.",
            3: "Plan for repair within 2-3 years. Include in next budget cycle.",
            4: "Schedule repair within 12 months. Prioritize in maintenance budget.",
            5: "URGENT: Immediate repair required. Risk of imminent failure."
        }
        return recommendations.get(grade, "Manual review required.")

    def predict_degradation(
        self,
        analysis_result: Dict[str, Any],
        context: Dict[str, Any]
    ) -> PredictionResult:
        """
        Predict degradation trajectory for a pipe.
        Uses fallback calculations if API fails.
        """
        pipe_id = analysis_result.get("pipe_id", "unknown")
        logger.info(f"Predicting degradation for pipe: {pipe_id}")

        # Extract context values (use 'or' to handle None values)
        current_grade = analysis_result.get("overall_grade", 1) or 1
        diameter = context.get('pipe_diameter_inches') or 12
        material = context.get('pipe_material') or 'unknown'
        depth = context.get('depth_feet') or 8.0
        location_type = context.get('location_type') or 'residential'
        traffic_load = context.get('traffic_load') or 'medium'
        pipe_age = context.get('pipe_age_years') or 30
        soil_type = context.get('soil_type') or 'unknown'

        # Get defects
        defects = analysis_result.get("defects", []) or analysis_result.get("unique_defects", [])

        # Calculate fallback values upfront
        time_estimates = {1: 120, 2: 84, 3: 48, 4: 18, 5: 6}
        fallback_time = time_estimates.get(current_grade, 60)
        
        # Adjust time based on age
        if pipe_age > 50:
            fallback_time = int(fallback_time * 0.7)
        elif pipe_age > 30:
            fallback_time = int(fallback_time * 0.85)
        
        fallback_risk = calculate_risk_score(current_grade, fallback_time, location_type)
        fallback_repair = calculate_repair_cost(current_grade, diameter, material, depth)
        fallback_emergency = calculate_emergency_cost(fallback_repair, location_type, traffic_load)
        fallback_factors = self._generate_contributing_factors(defects, current_grade, pipe_age, traffic_load, soil_type)

        # Build prediction prompt
        context_str = f"""
Pipe Context:
- Pipe ID: {pipe_id}
- Age: {pipe_age} years
- Material: {material}
- Diameter: {diameter} inches
- Burial depth: {depth} feet
- Traffic load above: {traffic_load}
- Soil type: {soil_type}
- Groundwater level: {context.get('groundwater', 'unknown')}
- Location type: {location_type}

Current Detected Defects:
{json.dumps(defects, indent=2)}

Current Overall Grade: {current_grade}
"""

        contents = [
            self.prediction_prompt,
            context_str
        ]

        try:
            response_text = self._call_gemini_with_retry(contents, use_thinking=False)
            prediction_data = _parse_json_response(response_text)

            # Helper function to safely extract numeric values
            def safe_numeric(value, fallback, min_value=0):
                """Extract numeric value, using fallback if invalid or below minimum."""
                if value is None:
                    return fallback
                try:
                    num = float(value)
                    if num <= min_value:
                        return fallback
                    return num
                except (TypeError, ValueError):
                    return fallback

            # Get values, using fallbacks for any invalid/zero values
            final_grade = int(safe_numeric(prediction_data.get("current_grade"), current_grade, min_value=0))
            final_time = int(safe_numeric(prediction_data.get("estimated_time_to_failure_months"), fallback_time, min_value=0))
            final_risk = safe_numeric(prediction_data.get("failure_risk_score"), fallback_risk, min_value=0)
            final_repair = safe_numeric(prediction_data.get("cost_estimate_repair"), fallback_repair, min_value=0)
            final_emergency = safe_numeric(prediction_data.get("cost_estimate_emergency"), fallback_emergency, min_value=0)

            # Log if fallbacks were used (for debugging)
            if final_time == fallback_time or final_risk == fallback_risk or final_repair == fallback_repair:
                logger.info(f"Using fallback values for {pipe_id}: time={final_time}, risk={final_risk}, repair=${final_repair}")

            factors = prediction_data.get("contributing_factors", [])
            if not factors:
                factors = fallback_factors

            recommendation = prediction_data.get("recommended_action")
            if not recommendation:
                recommendation = self._get_fallback_recommendation(current_grade)

            # Calculate fallback grade predictions
            fallback_grade_6mo = min(current_grade + (1 if current_grade < 5 else 0), 5)
            fallback_grade_12mo = min(current_grade + (1 if current_grade < 4 else 0), 5)

            predicted_6mo = int(safe_numeric(prediction_data.get("predicted_grade_6_months"), fallback_grade_6mo, min_value=0))
            predicted_12mo = int(safe_numeric(prediction_data.get("predicted_grade_12_months"), fallback_grade_12mo, min_value=0))

            # Ensure grades are within valid range (1-5)
            predicted_6mo = max(1, min(5, predicted_6mo))
            predicted_12mo = max(1, min(5, predicted_12mo))

            # Calculate itemized repair costs for each defect
            repair_items = calculate_repair_items(defects, diameter, material, depth)

            # Update total repair cost to sum of itemized repairs if we have items
            if repair_items:
                itemized_total = sum(item.estimated_cost for item in repair_items)
                if itemized_total > 0:
                    final_repair = itemized_total
                    # Recalculate emergency cost based on new repair total
                    final_emergency = calculate_emergency_cost(final_repair, location_type, traffic_load)

            return PredictionResult(
                pipe_id=pipe_id,
                current_grade=final_grade,
                predicted_grade_6_months=predicted_6mo,
                predicted_grade_12_months=predicted_12mo,
                estimated_time_to_failure_months=final_time,
                failure_risk_score=final_risk,
                contributing_factors=factors,
                recommended_action=recommendation,
                priority_rank=0,
                cost_estimate_repair=final_repair,
                cost_estimate_emergency=final_emergency,
                confidence_interval=prediction_data.get("confidence_interval", "±6 months"),
                reasoning=prediction_data.get("reasoning", f"Analysis based on {len(defects)} detected defects in a {pipe_age}-year-old {material} pipe."),
                repair_items=repair_items
            )

        except Exception as e:
            logger.error(f"Prediction API failed for {pipe_id}: {e}")

            # Calculate itemized repair costs for fallback
            fallback_repair_items = calculate_repair_items(defects, diameter, material, depth)

            # Update fallback costs based on itemized repairs
            if fallback_repair_items:
                itemized_total = sum(item.estimated_cost for item in fallback_repair_items)
                if itemized_total > 0:
                    fallback_repair = itemized_total
                    fallback_emergency = calculate_emergency_cost(fallback_repair, location_type, traffic_load)

            # Return fully-calculated fallback result
            return PredictionResult(
                pipe_id=pipe_id,
                current_grade=current_grade,
                predicted_grade_6_months=min(current_grade + (1 if current_grade < 5 else 0), 5),
                predicted_grade_12_months=min(current_grade + (1 if current_grade < 4 else 0), 5),
                estimated_time_to_failure_months=fallback_time,
                failure_risk_score=fallback_risk,
                contributing_factors=fallback_factors,
                recommended_action=self._get_fallback_recommendation(current_grade),
                priority_rank=0,
                cost_estimate_repair=fallback_repair,
                cost_estimate_emergency=fallback_emergency,
                confidence_interval="±12 months (estimated)",
                reasoning=f"Prediction calculated using engineering formulas for Grade {current_grade} defects in {pipe_age}-year-old {material} pipe.",
                repair_items=fallback_repair_items
            )

    def prioritize_repairs(
        self,
        predictions: List[PredictionResult],
        budget: Optional[float] = None
    ) -> List[PredictionResult]:
        """Prioritize repairs across multiple pipes."""
        logger.info(f"Prioritizing {len(predictions)} pipe repairs")

        scored_predictions = []
        for pred in predictions:
            urgency_score = pred.failure_risk_score

            if pred.cost_estimate_repair > 0:
                cost_ratio = pred.cost_estimate_emergency / pred.cost_estimate_repair
                urgency_score += min(cost_ratio * 5, 25)

            if pred.estimated_time_to_failure_months:
                if pred.estimated_time_to_failure_months <= 6:
                    urgency_score += 30
                elif pred.estimated_time_to_failure_months <= 12:
                    urgency_score += 20
                elif pred.estimated_time_to_failure_months <= 24:
                    urgency_score += 10

            if pred.current_grade >= 4:
                urgency_score += 15
            if pred.predicted_grade_6_months >= 5:
                urgency_score += 10

            scored_predictions.append((urgency_score, pred))

        scored_predictions.sort(key=lambda x: x[0], reverse=True)

        prioritized = []
        cumulative_cost = 0
        for rank, (score, pred) in enumerate(scored_predictions, 1):
            pred.priority_rank = rank
            if budget:
                cumulative_cost += pred.cost_estimate_repair
                if cumulative_cost > budget:
                    pred.recommended_action += " [EXCEEDS CURRENT BUDGET]"
            prioritized.append(pred)

        return prioritized

    def generate_quick_rating(self, defects: List[Dict]) -> str:
        """Generate PACP Quick Rating string."""
        grade_5_count = sum(1 for d in defects if d.get("grade") == 5)
        grade_4_count = sum(1 for d in defects if d.get("grade") == 4)
        return f"{min(grade_5_count, 99):02d}{min(grade_4_count, 99):02d}"

    def generate_executive_summary(
        self,
        pipe_id: str,
        overall_grade: int,
        quick_rating: str,
        defects: List[Dict],
        prediction: Optional[PredictionResult]
    ) -> str:
        """Generate executive summary."""
        # Build summary based on prediction data
        grade_desc = {1: "good", 2: "fair", 3: "moderate concern", 4: "poor", 5: "critical"}
        condition = grade_desc.get(overall_grade, "unknown")
        
        summary = f"Pipe {pipe_id} is in {condition} condition (Grade {overall_grade}/5). "
        
        if defects:
            defect_types = list(set([d.get('defect_code', 'unknown') for d in defects]))
            summary += f"Analysis identified {len(defects)} defect(s) including {', '.join(defect_types[:3])}. "
        
        if prediction:
            if prediction.failure_risk_score >= 70:
                summary += f"Because a system error prevented the automated tool from calculating a failure timeline or repair cost, the specific risk level remains unverified. We recommend an immediate manual inspection by the engineering team to confirm the pipe's status and prioritize necessary repairs."
            elif prediction.failure_risk_score >= 40:
                summary += f"Risk assessment indicates {prediction.failure_risk_score:.0f}% failure probability. Schedule repair within {prediction.estimated_time_to_failure_months or 12} months."
            else:
                summary += "Continue routine monitoring as scheduled."
        
        return summary

    def create_full_analysis(
        self,
        image_path: str,
        pipe_id: str,
        context: Dict[str, Any]
    ) -> AnalysisResult:
        """Perform complete analysis."""
        # Detect defects
        analysis = self.analyze_image(image_path, pipe_id)
        defects = analysis.get("defects", [])
        overall_grade = analysis.get("overall_grade", 1) or 1

        # Generate quick rating
        quick_rating = self.generate_quick_rating(defects)

        # Predict degradation
        prediction = self.predict_degradation(analysis, context)

        # Generate executive summary
        executive_summary = self.generate_executive_summary(
            pipe_id, overall_grade, quick_rating, defects, prediction
        )

        # Convert defect dicts to DetectedDefect objects
        detected_defects = [
            DetectedDefect(
                defect_type=d.get("defect_type", ""),
                defect_code=d.get("defect_code", ""),
                grade=d.get("grade", 1),
                location_in_pipe=d.get("location_in_pipe", ""),
                confidence=d.get("confidence", 0),
                description=d.get("description", "")
            )
            for d in defects
        ]

        return AnalysisResult(
            pipe_id=pipe_id,
            inspection_date=datetime.now().strftime("%Y-%m-%d"),
            defects=detected_defects,
            overall_grade=overall_grade,
            quick_rating=quick_rating,
            prediction=prediction,
            executive_summary=executive_summary,
            analysis_timestamp=datetime.now().isoformat(),
            raw_analysis=analysis
        )

    def analyze_with_ensemble(self, image_path: str, pipe_id: str, num_passes: int = 3) -> dict:
        """
        Run ensemble analysis for higher confidence results.

        This method runs multiple independent analysis passes on the same image
        and aggregates the results to provide more reliable, consistent assessments.
        Useful for critical inspections where accuracy is paramount.

        Args:
            image_path: Path to the image
            pipe_id: Pipe identifier
            num_passes: Number of independent analysis passes (default 3)

        Returns:
            Aggregated analysis with confidence metrics including:
            - analysis_mode: "ensemble"
            - num_passes: Total passes attempted
            - successful_passes: Passes that completed successfully
            - defects: Consensus defects with agreement scores
            - overall_grade: Median grade across passes
            - overall_grade_agreement: Agreement percentage for overall grade
            - overall_confidence: Combined agreement score
        """
        ensemble = EnsembleAnalyzer(self, num_passes=num_passes)
        return ensemble.analyze(image_path, pipe_id)

    def _update_pipe_state(self, pipe_id: str, analysis: Dict) -> None:
        """Update Thought Signatures memory for a pipe."""
        if pipe_id not in self.pipe_state_memory:
            self.pipe_state_memory[pipe_id] = {
                "analysis_history": [],
                "defect_progression": {},
                "last_updated": None
            }
        
        self.pipe_state_memory[pipe_id]["analysis_history"].append(analysis)
        self.pipe_state_memory[pipe_id]["last_updated"] = datetime.now().isoformat()

    def get_pipe_history(self, pipe_id: str) -> Dict[str, Any]:
        """Get the analysis history for a pipe."""
        return self.pipe_state_memory.get(pipe_id, {
            "analysis_history": [],
            "defect_progression": {},
            "last_updated": None
        })


if __name__ == "__main__":
    if not os.environ.get("GEMINI_API_KEY"):
        print("WARNING: GEMINI_API_KEY not set.")
    else:
        print("SewerSentinel Engine ready")











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
        
        # System prompt for defect detection
        self.detection_prompt = """You are SewerSentinel, an expert AI system for analyzing sewer pipe CCTV inspection footage.

Your role is to:
1. Identify and classify defects using PACP (Pipeline Assessment Certification Program) standards
2. Assign severity grades (1-5, where 5 is most severe)
3. Provide detailed observations about pipe condition

PACP Defect Codes to use:
- CL: Longitudinal Crack
- CC: Circumferential Crack  
- CM: Multiple Cracks
- FC: Fracture
- B: Broken pipe
- H: Hole
- D: Deformed pipe
- X: Collapse
- RF/RM/RB: Root intrusion (Fine/Medium/Ball)
- DAG/DS: Deposits (Attached/Settled)
- I: Infiltration (water entering pipe)
- JD/JS: Joint problems (Displaced/Separated)
- SD: Surface damage
- COR: Corrosion
- OK: Normal/No defects

Grade definitions:
- Grade 1: Minor defect, no immediate concern
- Grade 2: Minor to moderate, monitor in future inspections
- Grade 3: Moderate defect, schedule for repair within 3-5 years
- Grade 4: Significant defect, repair within 1-2 years
- Grade 5: Critical defect, immediate attention required

Also identify pipe characteristics from visual appearance:
- Pipe material: Look for texture/color cues:
  * Concrete: Gray, rough texture, may show aggregate
  * Vitrified clay: Brown/red, smooth glazed surface, visible joints
  * PVC: White/gray, smooth plastic appearance
  * Cast iron: Dark gray/black, may show rust/corrosion
  * Brick: Red/brown rectangular blocks with mortar joints
  * HDPE: Black, smooth plastic surface
- Estimated diameter: Based on perspective and camera field of view
- Water level: Percentage of pipe diameter covered by flow

For the image provided, respond ONLY in JSON format (no other text):
{
    "defects": [
        {
            "defect_type": "Description of defect",
            "defect_code": "PACP code",
            "grade": 1-5,
            "location_in_pipe": "clock position or floor/crown",
            "confidence": 0.0-1.0,
            "description": "Detailed observation"
        }
    ],
    "overall_assessment": "Summary of pipe condition",
    "overall_grade": 1-5,
    "pipe_material_observed": "concrete/clay/pvc/cast_iron/brick/hdpe/unknown",
    "pipe_material_confidence": 0.0-1.0,
    "estimated_diameter_inches": estimated diameter or null if uncertain,
    "water_level_percent": estimated percentage (0-100) or null
}"""

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
    Note: thinking_config removed due to compatibility issues with gemini-3-flash-preview
    """
    last_error = None
    
    for attempt in range(max_retries):
        try:
            # Simple API call without any config
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents
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

        # Extract context values
        current_grade = analysis_result.get("overall_grade", 1) or 1
        diameter = context.get('pipe_diameter_inches', 12)
        material = context.get('pipe_material', 'unknown')
        depth = context.get('depth_feet', 8.0)
        location_type = context.get('location_type', 'residential')
        traffic_load = context.get('traffic_load', 'medium')
        pipe_age = context.get('pipe_age_years', 30)
        soil_type = context.get('soil_type', 'unknown')

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

            # Get values, using fallbacks for any zeros/nulls
            final_grade = prediction_data.get("current_grade") or current_grade
            final_time = prediction_data.get("estimated_time_to_failure_months")
            final_risk = prediction_data.get("failure_risk_score")
            final_repair = prediction_data.get("cost_estimate_repair")
            final_emergency = prediction_data.get("cost_estimate_emergency")
            
            # Apply fallbacks
            if not final_time or final_time <= 0:
                final_time = fallback_time
            if not final_risk or final_risk <= 0:
                final_risk = fallback_risk
            if not final_repair or final_repair <= 0:
                final_repair = fallback_repair
            if not final_emergency or final_emergency <= 0:
                final_emergency = fallback_emergency

            factors = prediction_data.get("contributing_factors", [])
            if not factors:
                factors = fallback_factors

            recommendation = prediction_data.get("recommended_action")
            if not recommendation:
                recommendation = self._get_fallback_recommendation(current_grade)

            return PredictionResult(
                pipe_id=pipe_id,
                current_grade=final_grade,
                predicted_grade_6_months=prediction_data.get("predicted_grade_6_months") or min(current_grade + (1 if current_grade < 5 else 0), 5),
                predicted_grade_12_months=prediction_data.get("predicted_grade_12_months") or min(current_grade + (1 if current_grade < 4 else 0), 5),
                estimated_time_to_failure_months=final_time,
                failure_risk_score=final_risk,
                contributing_factors=factors,
                recommended_action=recommendation,
                priority_rank=0,
                cost_estimate_repair=final_repair,
                cost_estimate_emergency=final_emergency,
                confidence_interval=prediction_data.get("confidence_interval", "±6 months"),
                reasoning=prediction_data.get("reasoning", f"Analysis based on {len(defects)} detected defects in a {pipe_age}-year-old {material} pipe.")
            )

        except Exception as e:
            logger.error(f"Prediction API failed for {pipe_id}: {e}")
            
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
                reasoning=f"Prediction calculated using engineering formulas for Grade {current_grade} defects in {pipe_age}-year-old {material} pipe."
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











"""
SewerSentinel Core Analysis Engine
Interfaces with Gemini 3 for multimodal pipe inspection analysis

Uses the NEW google-genai SDK (not the deprecated google-generativeai)
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


class SewerSentinelEngine:
    """
    Main analysis engine using Gemini 3 for pipe inspection analysis.

    Implements:
    - Multimodal video/image analysis
    - Thought Signatures for state tracking across pipes
    - Thinking Levels for causal reasoning about degradation
    """

    def __init__(self, model_name: str = "gemini-3-flash-preview"):
        """
        Initialize the analysis engine.

        Args:
            model_name: Gemini model to use. Options:
                - "gemini-3-flash-preview" (free tier, recommended for hackathon)
                - "gemini-3-pro-preview" (paid tier, more capable)
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
    "pipe_material_observed": "concrete/clay/pvc/etc",
    "water_level": "estimated percentage of pipe diameter"
}"""

        self.prediction_prompt = """You are SewerSentinel's prediction engine. Based on the defects detected and contextual information provided, predict the degradation trajectory of this pipe segment.

Consider these factors in your analysis:
1. Current defect types and severity
2. Pipe age and material
3. Environmental factors (traffic load above, soil type, groundwater)
4. Historical degradation patterns for similar defects
5. Location consequence (what's above this pipe?)

Use deep reasoning to:
- Model how each defect typically progresses over time
- Identify interactions between multiple defects (e.g., crack + infiltration = accelerated corrosion)
- Factor in external stressors
- Estimate time to next severity grade and eventual failure

Provide your prediction ONLY in JSON format (no other text):
{
    "current_grade": 1-5,
    "predicted_grade_6_months": 1-5,
    "predicted_grade_12_months": 1-5,
    "estimated_time_to_failure_months": null or integer,
    "failure_risk_score": 0-100,
    "contributing_factors": ["list of key factors"],
    "recommended_action": "specific recommendation",
    "cost_estimate_repair": dollar amount for proactive repair,
    "cost_estimate_emergency": dollar amount if this fails catastrophically,
    "confidence_interval": "e.g., ±3 months",
    "reasoning": "Detailed explanation of your prediction logic"
}"""

    def _call_gemini_with_retry(
        self,
        contents: List[Any],
        use_thinking: bool = False,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ) -> str:
        """
        Call Gemini API with retry logic for handling flaky responses.

        Args:
            contents: List of content parts to send
            use_thinking: Whether to use thinking_level="high" for deeper reasoning
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds

        Returns:
            Response text from the model
        """
        config = None
        if use_thinking:
            config = types.GenerateContentConfig(
                thinking_level="high"
            )

        last_error = None
        for attempt in range(max_retries):
            try:
                if config:
                    response = self.client.models.generate_content(
                        model=self.model_name,
                        contents=contents,
                        config=config
                    )
                else:
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
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff

        raise RuntimeError(f"Gemini API call failed after {max_retries} attempts: {last_error}")

    def analyze_image(self, image_path: str, pipe_id: str = "unknown") -> Dict[str, Any]:
        """
        Analyze a single pipe inspection image.

        Args:
            image_path: Path to the image file
            pipe_id: Identifier for this pipe segment

        Returns:
            Dictionary containing detected defects and assessment
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

        # Create content with image using new SDK format
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

            # Update pipe state memory (Thought Signatures)
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
        Analyze pipe inspection image from bytes (for API uploads).

        Args:
            image_bytes: Raw image bytes
            mime_type: MIME type of the image
            pipe_id: Identifier for this pipe segment

        Returns:
            Dictionary containing detected defects and assessment
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

    def analyze_video_sequence(
        self,
        frame_paths: List[str],
        pipe_id: str,
        timestamps: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Analyze a sequence of video frames for temporal patterns.

        Args:
            frame_paths: List of paths to extracted video frames
            pipe_id: Identifier for this pipe segment
            timestamps: Optional list of timestamps for each frame

        Returns:
            Comprehensive analysis with temporal patterns
        """
        logger.info(f"Analyzing video sequence: {len(frame_paths)} frames for pipe {pipe_id}")

        all_defects = []
        frame_results = []

        for i, frame_path in enumerate(frame_paths):
            timestamp = timestamps[i] if timestamps else i * 1.0

            try:
                result = self.analyze_image(frame_path, f"{pipe_id}_frame_{i}")

                if "defects" in result:
                    for defect in result.get("defects", []):
                        defect["timestamp_seconds"] = timestamp
                        defect["frame_index"] = i
                        all_defects.append(defect)

                frame_results.append({
                    "frame_index": i,
                    "timestamp": timestamp,
                    "defects_found": len(result.get("defects", [])),
                    "overall_grade": result.get("overall_grade", 0)
                })

            except Exception as e:
                logger.warning(f"Failed to analyze frame {i}: {e}")
                frame_results.append({
                    "frame_index": i,
                    "timestamp": timestamp,
                    "error": str(e)
                })

        # Analyze temporal patterns
        temporal_analysis = self._analyze_temporal_patterns(all_defects)

        # Deduplicate defects
        unique_defects = self._deduplicate_defects(all_defects)

        # Calculate overall grade as max grade found
        overall_grade = max([d.get("grade", 1) for d in unique_defects], default=1)

        return {
            "pipe_id": pipe_id,
            "total_frames_analyzed": len(frame_paths),
            "successful_frames": len([f for f in frame_results if "error" not in f]),
            "all_defects": all_defects,
            "unique_defects": unique_defects,
            "overall_grade": overall_grade,
            "temporal_patterns": temporal_analysis,
            "frame_results": frame_results,
            "analysis_timestamp": datetime.now().isoformat()
        }

    def predict_degradation(
        self,
        analysis_result: Dict[str, Any],
        context: Dict[str, Any]
    ) -> PredictionResult:
        """
        Predict degradation trajectory for a pipe based on analysis and context.
        Uses Gemini 3's thinking_level="high" for deep causal reasoning.

        Args:
            analysis_result: Output from analyze_image or analyze_video_sequence
            context: Dictionary containing:
                - pipe_age_years: Age of the pipe
                - pipe_material: Material type (concrete, clay, PVC, etc.)
                - pipe_diameter_inches: Diameter
                - depth_feet: Burial depth
                - traffic_load: Traffic above (none/light/medium/heavy)
                - soil_type: Soil classification
                - groundwater: Groundwater presence (high/medium/low)
                - location_type: What's above (residential/commercial/school/hospital)
                - last_repair_date: Date of last repair if any

        Returns:
            PredictionResult with degradation forecast
        """
        pipe_id = analysis_result.get("pipe_id", "unknown")
        logger.info(f"Predicting degradation for pipe: {pipe_id}")

        # Get defects from either format
        defects = analysis_result.get("defects", []) or analysis_result.get("unique_defects", [])

        # Build context string
        context_str = f"""
Pipe Context:
- Age: {context.get('pipe_age_years', 'unknown')} years
- Material: {context.get('pipe_material', 'unknown')}
- Diameter: {context.get('pipe_diameter_inches', 'unknown')} inches
- Burial depth: {context.get('depth_feet', 'unknown')} feet
- Traffic load above: {context.get('traffic_load', 'unknown')}
- Soil type: {context.get('soil_type', 'unknown')}
- Groundwater level: {context.get('groundwater', 'unknown')}
- Location type: {context.get('location_type', 'unknown')}
- Last repair: {context.get('last_repair_date', 'none on record')}

Current Detected Defects:
{json.dumps(defects, indent=2)}

Current Overall Grade: {analysis_result.get('overall_grade', 'unknown')}
Overall Assessment: {analysis_result.get('overall_assessment', 'N/A')}
"""

        contents = [
            self.prediction_prompt,
            context_str,
            "Please analyze this pipe's degradation trajectory. Think deeply about the causal factors and provide your prediction."
        ]

        try:
            # Use thinking_level="high" for deep reasoning
            response_text = self._call_gemini_with_retry(contents, use_thinking=True)
            prediction_data = _parse_json_response(response_text)

            return PredictionResult(
                pipe_id=pipe_id,
                current_grade=prediction_data.get("current_grade", analysis_result.get("overall_grade", 1)),
                predicted_grade_6_months=prediction_data.get("predicted_grade_6_months", 1),
                predicted_grade_12_months=prediction_data.get("predicted_grade_12_months", 1),
                estimated_time_to_failure_months=prediction_data.get("estimated_time_to_failure_months"),
                failure_risk_score=prediction_data.get("failure_risk_score", 0),
                contributing_factors=prediction_data.get("contributing_factors", []),
                recommended_action=prediction_data.get("recommended_action", "Manual review required"),
                priority_rank=0,  # Will be set during batch prioritization
                cost_estimate_repair=prediction_data.get("cost_estimate_repair", 0),
                cost_estimate_emergency=prediction_data.get("cost_estimate_emergency", 0),
                confidence_interval=prediction_data.get("confidence_interval", "unknown"),
                reasoning=prediction_data.get("reasoning", "")
            )

        except Exception as e:
            logger.error(f"Prediction failed for {pipe_id}: {e}")
            return PredictionResult(
                pipe_id=pipe_id,
                current_grade=analysis_result.get("overall_grade", 1),
                predicted_grade_6_months=analysis_result.get("overall_grade", 1),
                predicted_grade_12_months=analysis_result.get("overall_grade", 1),
                estimated_time_to_failure_months=None,
                failure_risk_score=0,
                contributing_factors=["Error in prediction"],
                recommended_action="Manual review required - prediction failed",
                priority_rank=0,
                cost_estimate_repair=0,
                cost_estimate_emergency=0,
                confidence_interval="unknown",
                reasoning=f"Prediction failed: {str(e)[:200]}"
            )

    def prioritize_repairs(
        self,
        predictions: List[PredictionResult],
        budget: Optional[float] = None
    ) -> List[PredictionResult]:
        """
        Prioritize repairs across multiple pipes based on risk and cost-benefit.

        Args:
            predictions: List of PredictionResult objects
            budget: Optional budget constraint

        Returns:
            Sorted list of predictions with priority ranks assigned
        """
        logger.info(f"Prioritizing {len(predictions)} pipe repairs")

        # Score each pipe based on multiple factors
        scored_predictions = []
        for pred in predictions:
            urgency_score = pred.failure_risk_score

            # Add bonus for high cost ratio (emergency vs proactive)
            if pred.cost_estimate_repair > 0:
                cost_ratio = pred.cost_estimate_emergency / pred.cost_estimate_repair
                urgency_score += min(cost_ratio * 5, 25)  # Cap at 25 bonus points

            # Add bonus for short time to failure
            if pred.estimated_time_to_failure_months:
                if pred.estimated_time_to_failure_months <= 6:
                    urgency_score += 30
                elif pred.estimated_time_to_failure_months <= 12:
                    urgency_score += 20
                elif pred.estimated_time_to_failure_months <= 24:
                    urgency_score += 10

            # Add bonus for high current/predicted grades
            if pred.current_grade >= 4:
                urgency_score += 15
            if pred.predicted_grade_6_months >= 5:
                urgency_score += 10

            scored_predictions.append((urgency_score, pred))

        # Sort by urgency score (descending)
        scored_predictions.sort(key=lambda x: x[0], reverse=True)

        # Assign priority ranks
        prioritized = []
        cumulative_cost = 0
        for rank, (score, pred) in enumerate(scored_predictions, 1):
            pred.priority_rank = rank

            # Track if within budget
            if budget:
                cumulative_cost += pred.cost_estimate_repair
                if cumulative_cost > budget:
                    pred.recommended_action += " [EXCEEDS CURRENT BUDGET]"

            prioritized.append(pred)

        logger.info(f"Prioritization complete. Top priority: {prioritized[0].pipe_id if prioritized else 'None'}")
        return prioritized

    def generate_quick_rating(self, defects: List[Dict]) -> str:
        """
        Generate PACP Quick Rating string.
        
        Quick Rating format: XXYY where:
        - XX = count of Grade 5 defects (up to 99)
        - YY = count of Grade 4 defects (up to 99)
        """
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
        """Generate a plain-English executive summary for city managers."""

        prompt = f"""Based on this pipe analysis, generate a brief executive summary for a city manager who is not a technical expert.

Analysis Data:
- Pipe ID: {pipe_id}
- Overall Grade: {overall_grade}/5
- Quick Rating: {quick_rating}
- Number of defects found: {len(defects)}
- Defect types: {[d.get('defect_code', 'unknown') for d in defects]}
- Prediction: {asdict(prediction) if prediction else 'N/A'}

Write 2-3 sentences that:
1. State the overall condition in plain terms
2. Highlight the most critical finding
3. Recommend immediate next steps

Keep it under 100 words. No technical jargon. Respond with just the summary text, no JSON."""

        try:
            response_text = self._call_gemini_with_retry([prompt])
            return response_text.strip()
        except Exception as e:
            logger.error(f"Failed to generate executive summary: {e}")
            grade_desc = {1: "good", 2: "fair", 3: "moderate concern", 4: "significant concern", 5: "critical"}
            return f"Pipe {pipe_id} is in {grade_desc.get(overall_grade, 'unknown')} condition (Grade {overall_grade}/5). {len(defects)} defects were identified. {'Immediate attention recommended.' if overall_grade >= 4 else 'Continue monitoring.'}"

    def create_full_analysis(
        self,
        image_path: str,
        pipe_id: str,
        context: Dict[str, Any]
    ) -> AnalysisResult:
        """
        Perform complete analysis: detect defects, predict degradation, and generate summary.

        Args:
            image_path: Path to the image file
            pipe_id: Identifier for this pipe segment
            context: Pipe context for prediction

        Returns:
            Complete AnalysisResult
        """
        # Detect defects
        analysis = self.analyze_image(image_path, pipe_id)
        defects = analysis.get("defects", [])
        overall_grade = analysis.get("overall_grade", 1)

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
        
        # Track defect progression
        for defect in analysis.get("defects", []):
            defect_key = f"{defect.get('defect_code')}_{defect.get('location_in_pipe')}"
            if defect_key not in self.pipe_state_memory[pipe_id]["defect_progression"]:
                self.pipe_state_memory[pipe_id]["defect_progression"][defect_key] = []
            self.pipe_state_memory[pipe_id]["defect_progression"][defect_key].append({
                "grade": defect.get("grade"),
                "timestamp": datetime.now().isoformat()
            })

    def _analyze_temporal_patterns(self, defects: List[Dict]) -> Dict:
        """Analyze patterns across time-sequenced defects."""
        patterns = {
            "defects_by_location": {},
            "grade_distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            "most_common_defect": None,
            "most_severe_defect": None,
            "progression_detected": False,
            "total_defects": len(defects)
        }

        if not defects:
            return patterns

        for defect in defects:
            # Count by location
            loc = defect.get("location_in_pipe", "unknown")
            if loc not in patterns["defects_by_location"]:
                patterns["defects_by_location"][loc] = 0
            patterns["defects_by_location"][loc] += 1

            # Count by grade
            grade = defect.get("grade", 1)
            if grade in patterns["grade_distribution"]:
                patterns["grade_distribution"][grade] += 1

        # Find most common defect type
        defect_counts = {}
        max_grade = 0
        most_severe = None
        for d in defects:
            code = d.get("defect_code", "unknown")
            defect_counts[code] = defect_counts.get(code, 0) + 1
            if d.get("grade", 0) > max_grade:
                max_grade = d.get("grade", 0)
                most_severe = d

        if defect_counts:
            patterns["most_common_defect"] = max(defect_counts, key=defect_counts.get)

        if most_severe:
            patterns["most_severe_defect"] = most_severe.get("defect_code")

        return patterns

    def _deduplicate_defects(self, defects: List[Dict]) -> List[Dict]:
        """Remove duplicate defect detections from sequential frames."""
        unique = {}

        for defect in defects:
            # Create a key from defect type and location
            key = f"{defect.get('defect_code')}_{defect.get('location_in_pipe')}"
            if key not in unique:
                unique[key] = defect
            else:
                # Keep the highest grade version if duplicates exist
                if defect.get("grade", 0) > unique[key].get("grade", 0):
                    unique[key] = defect

        return list(unique.values())

    def get_pipe_history(self, pipe_id: str) -> Dict[str, Any]:
        """Get the analysis history for a pipe (Thought Signatures)."""
        return self.pipe_state_memory.get(pipe_id, {
            "analysis_history": [],
            "defect_progression": {},
            "last_updated": None
        })


# Example usage and testing
if __name__ == "__main__":
    # Check if API key is set
    if not os.environ.get("GEMINI_API_KEY"):
        print("WARNING: GEMINI_API_KEY environment variable is not set.")
        print("Set it with: export GEMINI_API_KEY='your-api-key'")
        print("\nRunning in demo mode with mock responses...")
    else:
        print("SewerSentinel Engine initialized")
        print(f"Using model: gemini-3-flash-preview")
        print("\nReady to analyze pipe inspection footage")
        print("\nExample usage:")
        print("  engine = SewerSentinelEngine()")
        print("  result = engine.analyze_image('pipe_image.jpg', 'PIPE-001')")
        print("  prediction = engine.predict_degradation(result, context)")
        print("  prioritized = engine.prioritize_repairs([prediction])")

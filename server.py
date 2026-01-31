"""
SewerSentinel FastAPI Server
REST API for pipe inspection analysis
"""

import os
import uuid
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import asdict

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from analysis_engine import (
    SewerSentinelEngine,
    PredictionResult,
    AnalysisResult,
    DEFECT_CODE_DESCRIPTIONS
)
from video_processor import VideoProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="SewerSentinel API",
    description="Autonomous Underground Infrastructure Predictive Failure System",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances (lazy initialization)
_engine: Optional[SewerSentinelEngine] = None
_video_processor: Optional[VideoProcessor] = None


def get_engine() -> SewerSentinelEngine:
    """Get or create the analysis engine instance."""
    global _engine
    if _engine is None:
        try:
            _engine = SewerSentinelEngine()
            logger.info("SewerSentinel engine initialized")
        except ValueError as e:
            logger.warning(f"Engine initialization failed: {e}")
            raise HTTPException(
                status_code=503,
                detail="GEMINI_API_KEY environment variable not set. Please configure your API key."
            )
    return _engine


def get_video_processor() -> VideoProcessor:
    """Get or create the video processor instance."""
    global _video_processor
    if _video_processor is None:
        _video_processor = VideoProcessor(
            frames_per_second=1.0,
            max_dimension=1024
        )
        logger.info("Video processor initialized")
    return _video_processor


# Pydantic models for request/response
class PipeContext(BaseModel):
    """Context information about a pipe for prediction."""
    pipe_age_years: Optional[int] = None
    pipe_material: Optional[str] = None
    pipe_diameter_inches: Optional[int] = None
    depth_feet: Optional[float] = None
    traffic_load: Optional[str] = None  # none/light/medium/heavy
    soil_type: Optional[str] = None
    groundwater: Optional[str] = None  # high/medium/low
    location_type: Optional[str] = None  # residential/commercial/school/hospital
    last_repair_date: Optional[str] = None


class PredictionRequest(BaseModel):
    """Request for degradation prediction."""
    analysis_result: Dict[str, Any]
    context: PipeContext


class PrioritizeRequest(BaseModel):
    """Request for repair prioritization."""
    predictions: List[Dict[str, Any]]
    budget: Optional[float] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    api_key_configured: bool
    timestamp: str


# Sample analysis data for demo
SAMPLE_ANALYSIS = {
    "pipe_id": "DEMO-PIPE-001",
    "inspection_date": "2026-01-31",
    "overall_grade": 4,
    "quick_rating": "0102",
    "defects": [
        {
            "defect_type": "Circumferential Crack",
            "defect_code": "CC",
            "grade": 4,
            "location_in_pipe": "3 o'clock",
            "confidence": 0.92,
            "description": "Significant circumferential crack spanning approximately 40% of pipe circumference"
        },
        {
            "defect_type": "Infiltration",
            "defect_code": "I",
            "grade": 3,
            "location_in_pipe": "6 o'clock",
            "confidence": 0.87,
            "description": "Active water infiltration at joint, moderate flow rate"
        },
        {
            "defect_type": "Root Intrusion (Fine)",
            "defect_code": "RF",
            "grade": 2,
            "location_in_pipe": "12 o'clock",
            "confidence": 0.78,
            "description": "Fine root intrusion beginning at joint, early stage"
        }
    ],
    "prediction": {
        "pipe_id": "DEMO-PIPE-001",
        "current_grade": 4,
        "predicted_grade_6_months": 4,
        "predicted_grade_12_months": 5,
        "estimated_time_to_failure_months": 18,
        "failure_risk_score": 78,
        "contributing_factors": [
            "Active infiltration accelerating deterioration",
            "Circumferential crack compromising structural integrity",
            "Root intrusion likely to worsen with vegetation growth season"
        ],
        "recommended_action": "Schedule repair within 6 months. Prioritize addressing crack and infiltration to prevent collapse.",
        "priority_rank": 1,
        "cost_estimate_repair": 15000,
        "cost_estimate_emergency": 95000,
        "confidence_interval": "±4 months",
        "reasoning": "The combination of a grade 4 circumferential crack with active infiltration creates a high-risk scenario. Water ingress through the crack accelerates concrete deterioration and can lead to soil erosion around the pipe. The fine root intrusion, while currently minor, indicates joint vulnerability that will worsen. Without intervention, failure within 18 months is probable."
    },
    "executive_summary": "This pipe segment requires urgent attention. A significant crack combined with water infiltration poses a high risk of failure within the next 18 months. Proactive repair now would cost approximately $15,000, compared to an estimated $95,000 for emergency repairs after failure. Recommend scheduling repair within the next 6 months.",
    "analysis_timestamp": datetime.now().isoformat()
}


# API Endpoints
@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    api_key_configured = bool(os.environ.get("GEMINI_API_KEY"))
    return HealthResponse(
        status="healthy",
        api_key_configured=api_key_configured,
        timestamp=datetime.now().isoformat()
    )


@app.get("/api/sample-analysis")
async def get_sample_analysis():
    """Return pre-computed sample analysis for demo purposes."""
    return SAMPLE_ANALYSIS


@app.get("/api/defect-codes")
async def get_defect_codes():
    """Return PACP defect code definitions."""
    return {
        "defect_codes": DEFECT_CODE_DESCRIPTIONS,
        "grade_definitions": {
            1: "Minor defect, no immediate concern",
            2: "Minor to moderate, monitor in future inspections",
            3: "Moderate defect, schedule for repair within 3-5 years",
            4: "Significant defect, repair within 1-2 years",
            5: "Critical defect, immediate attention required"
        }
    }


@app.post("/api/analyze")
async def analyze_image(
    file: UploadFile = File(...),
    pipe_id: Optional[str] = Form(None)
):
    """
    Analyze a single pipe inspection image.

    Args:
        file: Image file (jpg, png, etc.)
        pipe_id: Optional pipe identifier

    Returns:
        Analysis result with detected defects
    """
    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Allowed: {', '.join(allowed_types)}"
        )

    # Generate pipe_id if not provided
    if not pipe_id:
        pipe_id = f"PIPE-{uuid.uuid4().hex[:8].upper()}"

    try:
        engine = get_engine()

        # Read image bytes
        image_bytes = await file.read()

        # Analyze image
        result = engine.analyze_image_bytes(
            image_bytes=image_bytes,
            mime_type=file.content_type,
            pipe_id=pipe_id
        )

        return result

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze-video")
async def analyze_video(
    file: UploadFile = File(...),
    pipe_id: Optional[str] = Form(None),
    frames_per_second: float = Form(1.0)
):
    """
    Analyze a pipe inspection video.

    Extracts frames and analyzes each for defects.

    Args:
        file: Video file (mp4, avi, mov, etc.)
        pipe_id: Optional pipe identifier
        frames_per_second: Frames to extract per second (default: 1.0)

    Returns:
        Comprehensive analysis with temporal patterns
    """
    # Validate file type
    allowed_types = {"video/mp4", "video/avi", "video/quicktime", "video/x-msvideo", "video/webm"}
    if file.content_type not in allowed_types and not file.filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: mp4, avi, mov, mkv, webm"
        )

    # Generate pipe_id if not provided
    if not pipe_id:
        pipe_id = f"PIPE-{uuid.uuid4().hex[:8].upper()}"

    temp_dir = None
    try:
        engine = get_engine()
        video_proc = get_video_processor()
        video_proc.frames_per_second = frames_per_second

        # Read video bytes
        video_bytes = await file.read()

        # Determine format from filename
        video_format = Path(file.filename).suffix.lstrip('.').lower() or 'mp4'

        # Extract frames
        temp_dir = tempfile.mkdtemp(prefix="sewersentinel_")
        frame_paths, timestamps = video_proc.extract_frames_from_bytes(
            video_bytes=video_bytes,
            video_format=video_format,
            output_dir=temp_dir
        )

        if not frame_paths:
            raise HTTPException(status_code=400, detail="No frames could be extracted from video")

        # Analyze video sequence
        result = engine.analyze_video_sequence(
            frame_paths=frame_paths,
            pipe_id=pipe_id,
            timestamps=timestamps
        )

        # Clean up frames
        video_proc.cleanup_frames(frame_paths)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Video analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temp directory
        if temp_dir:
            try:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass


@app.post("/api/predict")
async def predict_degradation(request: PredictionRequest):
    """
    Predict degradation trajectory for a pipe.

    Args:
        request: Analysis result and pipe context

    Returns:
        Prediction with failure timeline and recommendations
    """
    try:
        engine = get_engine()

        # Convert context to dict
        context = request.context.model_dump()

        # Run prediction
        prediction = engine.predict_degradation(
            analysis_result=request.analysis_result,
            context=context
        )

        return asdict(prediction)

    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/prioritize")
async def prioritize_repairs(request: PrioritizeRequest):
    """
    Prioritize repairs across multiple pipes.

    Args:
        request: List of predictions and optional budget constraint

    Returns:
        Prioritized list of pipes with repair recommendations
    """
    try:
        engine = get_engine()

        # Convert dicts to PredictionResult objects
        predictions = []
        for pred_dict in request.predictions:
            prediction = PredictionResult(
                pipe_id=pred_dict.get("pipe_id", "unknown"),
                current_grade=pred_dict.get("current_grade", 1),
                predicted_grade_6_months=pred_dict.get("predicted_grade_6_months", 1),
                predicted_grade_12_months=pred_dict.get("predicted_grade_12_months", 1),
                estimated_time_to_failure_months=pred_dict.get("estimated_time_to_failure_months"),
                failure_risk_score=pred_dict.get("failure_risk_score", 0),
                contributing_factors=pred_dict.get("contributing_factors", []),
                recommended_action=pred_dict.get("recommended_action", ""),
                priority_rank=pred_dict.get("priority_rank", 0),
                cost_estimate_repair=pred_dict.get("cost_estimate_repair", 0),
                cost_estimate_emergency=pred_dict.get("cost_estimate_emergency", 0),
                confidence_interval=pred_dict.get("confidence_interval", "unknown"),
                reasoning=pred_dict.get("reasoning", "")
            )
            predictions.append(prediction)

        # Prioritize
        prioritized = engine.prioritize_repairs(
            predictions=predictions,
            budget=request.budget
        )

        return [asdict(p) for p in prioritized]

    except Exception as e:
        logger.error(f"Prioritization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/full-analysis")
async def full_analysis(
    file: UploadFile = File(...),
    pipe_id: Optional[str] = Form(None),
    pipe_age_years: Optional[int] = Form(None),
    pipe_material: Optional[str] = Form(None),
    pipe_diameter_inches: Optional[int] = Form(None),
    depth_feet: Optional[float] = Form(None),
    traffic_load: Optional[str] = Form(None),
    soil_type: Optional[str] = Form(None),
    groundwater: Optional[str] = Form(None),
    location_type: Optional[str] = Form(None)
):
    """
    Perform complete analysis: detect defects, predict degradation, generate summary.

    Args:
        file: Image file
        pipe_id: Optional pipe identifier
        Context parameters for prediction

    Returns:
        Complete analysis result
    """
    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Allowed: {', '.join(allowed_types)}"
        )

    # Generate pipe_id if not provided
    if not pipe_id:
        pipe_id = f"PIPE-{uuid.uuid4().hex[:8].upper()}"

    temp_file = None
    try:
        engine = get_engine()

        # Save uploaded file temporarily
        image_bytes = await file.read()
        suffix = Path(file.filename).suffix or '.jpg'

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(image_bytes)
            temp_file = tmp.name

        # Build context
        context = {
            "pipe_age_years": pipe_age_years,
            "pipe_material": pipe_material,
            "pipe_diameter_inches": pipe_diameter_inches,
            "depth_feet": depth_feet,
            "traffic_load": traffic_load,
            "soil_type": soil_type,
            "groundwater": groundwater,
            "location_type": location_type
        }

        # Run full analysis
        result = engine.create_full_analysis(
            image_path=temp_file,
            pipe_id=pipe_id,
            context=context
        )

        # Convert to dict for JSON response
        result_dict = asdict(result)

        # Convert nested dataclasses
        if result.prediction:
            result_dict["prediction"] = asdict(result.prediction)
        result_dict["defects"] = [asdict(d) for d in result.defects]

        return result_dict

    except Exception as e:
        logger.error(f"Full analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temp file
        if temp_file:
            try:
                os.unlink(temp_file)
            except Exception:
                pass


# Mount static files for frontend (if build exists)
FRONTEND_BUILD_DIR = Path(__file__).parent / "frontend" / "build"
if FRONTEND_BUILD_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_BUILD_DIR), html=True), name="frontend")


# Run with: uvicorn server:app --reload
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    SewerSentinel API Server                  ║
╠══════════════════════════════════════════════════════════════╣
║  Autonomous Underground Infrastructure Prediction System      ║
║                                                              ║
║  Starting server on http://localhost:{port}                   ║
║                                                              ║
║  API Docs: http://localhost:{port}/docs                       ║
║  Health:   http://localhost:{port}/api/health                 ║
╚══════════════════════════════════════════════════════════════╝
""")

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )

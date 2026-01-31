"""
SewerSentinel - Streamlit App
Autonomous Underground Infrastructure Predictive Failure System

This standalone app is designed for Google AI Studio deployment.
It provides a complete demo of the SewerSentinel system using Gemini 3.

Usage: streamlit run aistudio_app.py
"""

import os
import io
import json
import tempfile
from datetime import datetime
from pathlib import Path
from dataclasses import asdict
from typing import Optional

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

import streamlit as st
from PIL import Image

# Load API key from Streamlit secrets (for cloud deployment) or environment variable
def get_api_key():
    """Get API key from Streamlit secrets or environment variable"""
    # Try Streamlit secrets first (for Streamlit Cloud)
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    # Fall back to environment variable
    return os.environ.get("GEMINI_API_KEY")

# Set the API key in environment for the analysis engine
api_key = get_api_key()
if api_key:
    os.environ["GEMINI_API_KEY"] = api_key

# Import our analysis engine
try:
    from analysis_engine import SewerSentinelEngine, DEFECT_CODE_DESCRIPTIONS
    ENGINE_AVAILABLE = True
except ImportError as e:
    ENGINE_AVAILABLE = False
    ENGINE_ERROR = str(e)

# Page configuration
st.set_page_config(
    page_title="SewerSentinel",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme
st.markdown("""
<style>
    /* Dark theme overrides */
    .stApp {
        background-color: #0a0a0f;
    }

    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #0f0f1a 100%);
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        border: 1px solid #2d3748;
    }

    .stat-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #2d3748;
        text-align: center;
    }

    .defect-card {
        background: #1a1a2e;
        padding: 15px;
        border-radius: 6px;
        margin: 10px 0;
        border-left: 4px solid #f97316;
    }

    .grade-badge {
        display: inline-block;
        padding: 8px 16px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 18px;
    }

    .grade-1 { background-color: #22c55e; color: white; }
    .grade-2 { background-color: #84cc16; color: white; }
    .grade-3 { background-color: #eab308; color: white; }
    .grade-4 { background-color: #f97316; color: white; }
    .grade-5 { background-color: #ef4444; color: white; }

    .risk-high { color: #ef4444; }
    .risk-medium { color: #f97316; }
    .risk-low { color: #22c55e; }

    .prediction-box {
        background: #0f172a;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #2d3748;
    }

    .cost-comparison {
        display: flex;
        gap: 20px;
    }

    .cost-box {
        flex: 1;
        padding: 15px;
        border-radius: 8px;
        background: #1a1a2e;
    }

    .cost-repair { border-left: 4px solid #22c55e; }
    .cost-emergency { border-left: 4px solid #ef4444; }
</style>
""", unsafe_allow_html=True)


def get_grade_color(grade: int) -> str:
    """Get color for PACP grade."""
    colors = {1: "#22c55e", 2: "#84cc16", 3: "#eab308", 4: "#f97316", 5: "#ef4444"}
    return colors.get(grade, "#6b7280")


def get_risk_color(score: float) -> str:
    """Get color for risk score."""
    if score >= 80:
        return "#ef4444"
    elif score >= 60:
        return "#f97316"
    elif score >= 40:
        return "#eab308"
    return "#22c55e"


def display_grade_badge(grade: int):
    """Display a colored grade badge."""
    color = get_grade_color(grade)
    st.markdown(
        f'<span style="background-color: {color}; color: white; padding: 8px 16px; '
        f'border-radius: 6px; font-weight: bold; font-size: 20px;">Grade {grade}</span>',
        unsafe_allow_html=True
    )


@st.cache_resource
def get_engine():
    """Initialize the analysis engine (cached)."""
    if not ENGINE_AVAILABLE:
        return None

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        return SewerSentinelEngine()
    except Exception as e:
        st.error(f"Failed to initialize engine: {e}")
        return None


def get_demo_result():
    """Generate a realistic demo analysis result for showcasing the UI."""
    from analysis_engine import AnalysisResult, DetectedDefect, PredictionResult

    # Create sample defects
    defects = [
        DetectedDefect(
            defect_type="Circumferential Crack",
            defect_code="CC",
            grade=4,
            location_in_pipe="12 o'clock position",
            confidence=0.92,
            description="Significant circumferential crack spanning approximately 40% of pipe circumference. Crack width estimated at 5-8mm with visible separation."
        ),
        DetectedDefect(
            defect_type="Root Intrusion (Medium)",
            defect_code="RM",
            grade=3,
            location_in_pipe="3 o'clock position",
            confidence=0.88,
            description="Medium root intrusion penetrating through joint at 3 o'clock. Roots extending approximately 15cm into pipe flow area."
        ),
        DetectedDefect(
            defect_type="Infiltration",
            defect_code="I",
            grade=3,
            location_in_pipe="12 o'clock position (at crack)",
            confidence=0.85,
            description="Active infiltration observed at crack location. Water seepage indicates high groundwater pressure."
        ),
        DetectedDefect(
            defect_type="Corrosion",
            defect_code="COR",
            grade=2,
            location_in_pipe="Floor (6 o'clock)",
            confidence=0.78,
            description="Moderate surface corrosion on pipe floor, likely due to hydrogen sulfide exposure. Approximately 10% wall loss observed."
        )
    ]

    # Create prediction result
    prediction = PredictionResult(
        pipe_id="DEMO-PIPE-001",
        current_grade=4,
        predicted_grade_6_months=4,
        predicted_grade_12_months=5,
        estimated_time_to_failure_months=14,
        failure_risk_score=78.5,
        contributing_factors=[
            "Grade 4 circumferential crack with active infiltration",
            "Root intrusion accelerating joint deterioration",
            "High groundwater pressure increasing stress on crack",
            "Pipe age (45 years) exceeding typical concrete lifespan",
            "Heavy traffic load causing cyclic stress",
            "Clay soil promoting differential settlement"
        ],
        recommended_action="Schedule repair within 6-9 months. Recommend CIPP lining for crack remediation and root cutting. Monitor infiltration monthly until repair.",
        priority_rank=1,
        cost_estimate_repair=18500.0,
        cost_estimate_emergency=142500.0,
        confidence_interval="±4 months",
        reasoning="""This pipe shows multiple interacting defects that create a compound failure risk.

The circumferential crack at 12 o'clock is the primary concern - at Grade 4 severity with 5-8mm width, it indicates significant structural compromise. The crack's location at the crown means it bears the full soil and traffic load above.

The active infiltration through this crack suggests the surrounding soil is saturated, which:
1. Increases hydrostatic pressure on the crack
2. May cause soil erosion and void formation around the pipe
3. Accelerates the freeze-thaw cycle damage in winter months

The medium root intrusion at 3 o'clock indicates a compromised joint that will worsen over time. Roots grow toward moisture, and the infiltration will accelerate root growth.

The floor corrosion, while currently Grade 2, indicates hydrogen sulfide attack which can progress rapidly if flow conditions change.

Given the 45-year pipe age, concrete strength has likely degraded 20-30% from original specifications. Combined with heavy traffic load creating cyclic stress, I predict progression to Grade 5 within 12-14 months if untreated.

Cost analysis: Proactive CIPP rehabilitation ($18,500) vs emergency dig-and-replace after collapse under roadway ($142,500 including traffic control, emergency response, environmental cleanup, and expedited materials)."""
    )

    # Create full analysis result
    return AnalysisResult(
        pipe_id="DEMO-PIPE-001",
        inspection_date=datetime.now().strftime("%Y-%m-%d"),
        defects=defects,
        overall_grade=4,
        quick_rating="0102",
        prediction=prediction,
        executive_summary="This 45-year-old concrete pipe shows significant structural damage requiring prompt attention. A Grade 4 crack at the crown combined with active water infiltration and root intrusion creates high failure risk. Without repair within 9 months, there is substantial risk of collapse under the roadway. Proactive repair will save an estimated $124,000 compared to emergency response.",
        analysis_timestamp=datetime.now().isoformat(),
        raw_analysis={
            "demo_mode": True,
            "auto_detected": {
                "material": "concrete",
                "material_confidence": 0.91,
                "diameter": 18,
                "water_level": 25
            }
        }
    )


def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1 style="margin: 0; color: #e2e8f0;">🔍 SewerSentinel</h1>
        <p style="margin: 5px 0 0 0; color: #94a3b8;">
            Autonomous Underground Infrastructure Predictive Failure System
        </p>
        <p style="margin: 5px 0 0 0; color: #64748b; font-size: 12px;">
            Powered by Google Gemini 3 | PACP Compliant
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Check API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        st.warning("""
        **GEMINI_API_KEY not configured.**

        Please set your Gemini API key to enable analysis:
        ```
        export GEMINI_API_KEY='your-api-key'
        ```

        Get your API key at: [Google AI Studio](https://aistudio.google.com/app/apikey)
        """)

    # Sidebar - Pipe Context
    with st.sidebar:
        st.header("Pipe Context")
        st.caption("Provide information about the pipe for better predictions")

        pipe_id = st.text_input("Pipe ID", value=f"PIPE-{datetime.now().strftime('%H%M%S')}")

        col1, col2 = st.columns(2)
        with col1:
            pipe_age = st.number_input("Age (years)", min_value=0, max_value=150, value=30)
        with col2:
            diameter = st.number_input("Diameter (in)", min_value=4, max_value=120, value=12)

        pipe_material = st.selectbox(
            "Material",
            ["concrete", "clay", "pvc", "cast_iron", "hdpe", "unknown"],
            index=0
        )

        depth = st.slider("Burial Depth (ft)", 0.0, 30.0, 8.0)

        traffic_load = st.selectbox(
            "Traffic Load Above",
            ["none", "light", "medium", "heavy"],
            index=2
        )

        soil_type = st.selectbox(
            "Soil Type",
            ["clay", "sandy", "loam", "rocky", "unknown"],
            index=0
        )

        groundwater = st.selectbox(
            "Groundwater Level",
            ["low", "medium", "high"],
            index=1
        )

        location_type = st.selectbox(
            "Location Type",
            ["residential", "commercial", "industrial", "school", "hospital"],
            index=0
        )

        st.divider()
        st.caption("About SewerSentinel")
        st.markdown("""
        SewerSentinel uses Google's **Gemini 3** to:
        - Detect defects in pipe inspection images
        - Predict failure timelines
        - Prioritize repairs by risk

        Built for the **Gemini 3 Hackathon 2026**.
        """)

    # Main content
    tab1, tab2, tab3 = st.tabs(["📸 Analyze Image", "📊 Results", "ℹ️ About PACP"])

    # Tab 1: Image Analysis
    with tab1:
        st.header("Upload Pipe Inspection Image")

        uploaded_file = st.file_uploader(
            "Drop an image or click to browse",
            type=["jpg", "jpeg", "png", "webp", "bmp"],
            help="Upload a CCTV pipe inspection image for analysis"
        )

        # Demo mode - show when no file is uploaded
        if not uploaded_file:
            st.divider()
            st.markdown("**No image? Try our demo to explore the features:**")

            demo_col1, demo_col2 = st.columns([1, 2])
            with demo_col1:
                if st.button("🎯 Try Demo", type="secondary", use_container_width=True):
                    try:
                        demo_result = get_demo_result()
                        st.session_state['analysis_result'] = demo_result
                        st.session_state['demo_mode'] = True
                        st.success("Demo loaded! Check the Results tab to explore.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to load demo: {e}")

            with demo_col2:
                st.caption(
                    "The demo shows a realistic analysis of a 45-year-old concrete pipe "
                    "with multiple defects, failure predictions, and cost-benefit analysis."
                )

            # Show demo indicator if in demo mode
            if st.session_state.get('demo_mode'):
                st.info("📋 **Demo Mode Active** - Viewing sample analysis data. Upload an image to analyze your own pipe.")

        if uploaded_file:
            # Clear demo mode when uploading a new file
            st.session_state.pop('demo_mode', None)
            col1, col2 = st.columns([1, 1])

            with col1:
                st.subheader("Uploaded Image")
                image = Image.open(uploaded_file)
                st.image(image, use_container_width=True)

            with col2:
                st.subheader("Analysis")

                if st.button("🔍 Analyze with Gemini 3", type="primary", use_container_width=True):
                    engine = get_engine()

                    if engine is None:
                        st.error("Analysis engine not available. Please check your GEMINI_API_KEY.")
                    else:
                        with st.spinner("Analyzing image with Gemini 3..."):
                            try:
                                # Save uploaded file temporarily
                                with tempfile.NamedTemporaryFile(
                                    suffix=Path(uploaded_file.name).suffix,
                                    delete=False
                                ) as tmp:
                                    tmp.write(uploaded_file.getvalue())
                                    tmp_path = tmp.name

                                # Build context
                                context = {
                                    "pipe_age_years": pipe_age,
                                    "pipe_material": pipe_material,
                                    "pipe_diameter_inches": diameter,
                                    "depth_feet": depth,
                                    "traffic_load": traffic_load,
                                    "soil_type": soil_type,
                                    "groundwater": groundwater,
                                    "location_type": location_type
                                }

                                # First, run detection to get pipe characteristics
                                detection_result = engine.analyze_image(tmp_path, pipe_id)

                                # Check for auto-detected pipe characteristics
                                auto_detected = []
                                detected_material = detection_result.get('pipe_material_observed', 'unknown')
                                material_confidence = detection_result.get('pipe_material_confidence', 0)
                                detected_diameter = detection_result.get('estimated_diameter_inches')
                                detected_water_level = detection_result.get('water_level_percent')

                                # Update context with detected values if confidence is high
                                if detected_material and detected_material != 'unknown' and material_confidence >= 0.7:
                                    # Map detected material to dropdown values
                                    material_map = {
                                        'concrete': 'concrete',
                                        'clay': 'clay',
                                        'vitrified clay': 'clay',
                                        'pvc': 'pvc',
                                        'cast_iron': 'cast_iron',
                                        'cast iron': 'cast_iron',
                                        'brick': 'concrete',  # Map brick to concrete for similar properties
                                        'hdpe': 'hdpe'
                                    }
                                    mapped_material = material_map.get(detected_material.lower(), pipe_material)
                                    if mapped_material in ['concrete', 'clay', 'pvc', 'cast_iron', 'hdpe']:
                                        context['pipe_material'] = mapped_material
                                        auto_detected.append(f"Material: {mapped_material} ({material_confidence:.0%} confidence)")

                                if detected_diameter and isinstance(detected_diameter, (int, float)) and detected_diameter > 0:
                                    context['pipe_diameter_inches'] = int(detected_diameter)
                                    auto_detected.append(f"Diameter: {int(detected_diameter)} inches")

                                # Run full analysis with potentially updated context
                                result = engine.create_full_analysis(
                                    image_path=tmp_path,
                                    pipe_id=pipe_id,
                                    context=context
                                )

                                # Store detected characteristics in result for display
                                result.raw_analysis['auto_detected'] = {
                                    'material': detected_material,
                                    'material_confidence': material_confidence,
                                    'diameter': detected_diameter,
                                    'water_level': detected_water_level
                                }

                                # Store result in session state
                                st.session_state['analysis_result'] = result
                                st.session_state['analysis_image'] = image

                                # Clean up temp file
                                os.unlink(tmp_path)

                                # Show success message with auto-detection info
                                if auto_detected:
                                    st.success(f"Analysis complete! Auto-detected: {', '.join(auto_detected)}")
                                else:
                                    st.success("Analysis complete! Go to Results tab to see details.")

                            except Exception as e:
                                error_msg = str(e).lower()

                                # Provide user-friendly error messages
                                if "api" in error_msg or "key" in error_msg or "authentication" in error_msg:
                                    st.error("""
                                    **API Authentication Error**

                                    Please check that your GEMINI_API_KEY is valid and has not expired.
                                    You can get a new API key at [Google AI Studio](https://aistudio.google.com/app/apikey).
                                    """)
                                elif "quota" in error_msg or "rate" in error_msg or "limit" in error_msg:
                                    st.error("""
                                    **Rate Limit Exceeded**

                                    The API rate limit has been reached. Please wait a moment and try again.
                                    If this persists, consider upgrading your API plan.
                                    """)
                                elif "timeout" in error_msg or "timed out" in error_msg:
                                    st.error("""
                                    **Request Timeout**

                                    The analysis request timed out. This can happen with large images or high API load.
                                    Please try again, or try with a smaller image.
                                    """)
                                elif "parse" in error_msg or "json" in error_msg:
                                    st.warning("""
                                    **Partial Analysis Complete**

                                    The AI response couldn't be fully parsed. This sometimes happens with complex images.
                                    Try analyzing again - results may vary between attempts.
                                    """)
                                else:
                                    st.error(f"""
                                    **Analysis Failed**

                                    Error: {str(e)[:200]}

                                    Please try again. If the problem persists, try:
                                    - Using a different image
                                    - Checking your internet connection
                                    - Verifying your API key
                                    """)

                # Quick stats if result exists
                if 'analysis_result' in st.session_state:
                    result = st.session_state['analysis_result']
                    st.divider()

                    st.metric("Overall Grade", f"{result.overall_grade}/5")

                    defect_count = len(result.defects)
                    st.metric("Defects Found", defect_count)

                    if result.prediction:
                        risk_score = result.prediction.failure_risk_score
                        color = get_risk_color(risk_score)
                        st.markdown(
                            f"**Risk Score:** <span style='color: {color}; font-size: 24px; font-weight: bold;'>{risk_score}%</span>",
                            unsafe_allow_html=True
                        )

    # Tab 2: Results
    with tab2:
        if 'analysis_result' not in st.session_state:
            st.info("No analysis results yet. Upload and analyze an image first.")
        else:
            result = st.session_state['analysis_result']

            # Header with grade
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.header(f"Analysis: {result.pipe_id}")
            with col2:
                display_grade_badge(result.overall_grade)
            with col3:
                st.metric("Quick Rating", result.quick_rating)

            # Executive Summary
            st.subheader("Executive Summary")
            st.info(result.executive_summary)

            # Defects
            st.subheader(f"Detected Defects ({len(result.defects)})")

            if not result.defects:
                st.success("No significant defects detected!")
            else:
                for defect in result.defects:
                    with st.expander(
                        f"**{defect.defect_code}** - {DEFECT_CODE_DESCRIPTIONS.get(defect.defect_code, defect.defect_type)} (Grade {defect.grade})",
                        expanded=True
                    ):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.markdown(f"**Grade:** {defect.grade}")
                        with col2:
                            st.markdown(f"**Location:** {defect.location_in_pipe}")
                        with col3:
                            st.markdown(f"**Confidence:** {defect.confidence:.0%}")

                        if defect.description:
                            st.markdown(f"*{defect.description}*")

            # Prediction
            if result.prediction:
                st.subheader("Failure Prediction")

                pred = result.prediction
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    color = get_risk_color(pred.failure_risk_score)
                    st.markdown(f"""
                    <div style="text-align: center;">
                        <div style="font-size: 48px; font-weight: bold; color: {color};">
                            {pred.failure_risk_score}%
                        </div>
                        <div style="color: #94a3b8;">Risk Score</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col2:
                    if pred.estimated_time_to_failure_months:
                        st.metric(
                            "Time to Failure",
                            f"{pred.estimated_time_to_failure_months} mo",
                            help=f"Confidence: {pred.confidence_interval}"
                        )
                    else:
                        st.metric("Time to Failure", "N/A")

                with col3:
                    st.metric("Current Grade", pred.current_grade)

                with col4:
                    st.metric(
                        "6-Month Prediction",
                        pred.predicted_grade_6_months,
                        delta=pred.predicted_grade_6_months - pred.current_grade if pred.predicted_grade_6_months > pred.current_grade else None,
                        delta_color="inverse"
                    )

                # Grade progression
                st.markdown("**Grade Progression:**")
                prog_col1, prog_col2, prog_col3 = st.columns(3)
                with prog_col1:
                    st.markdown(f"""
                    <div style="text-align: center; background: {get_grade_color(pred.current_grade)};
                         padding: 10px; border-radius: 6px; color: white;">
                        <div>Now</div>
                        <div style="font-size: 24px; font-weight: bold;">Grade {pred.current_grade}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with prog_col2:
                    st.markdown(f"""
                    <div style="text-align: center; background: {get_grade_color(pred.predicted_grade_6_months)};
                         padding: 10px; border-radius: 6px; color: white;">
                        <div>6 Months</div>
                        <div style="font-size: 24px; font-weight: bold;">Grade {pred.predicted_grade_6_months}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with prog_col3:
                    st.markdown(f"""
                    <div style="text-align: center; background: {get_grade_color(pred.predicted_grade_12_months)};
                         padding: 10px; border-radius: 6px; color: white;">
                        <div>12 Months</div>
                        <div style="font-size: 24px; font-weight: bold;">Grade {pred.predicted_grade_12_months}</div>
                    </div>
                    """, unsafe_allow_html=True)

                # Risk Level Explanation
                risk_score = pred.failure_risk_score
                if risk_score >= 80:
                    risk_level = "CRITICAL"
                    risk_explanation = "Immediate attention required. High probability of failure within the prediction window."
                    risk_icon = "🔴"
                elif risk_score >= 60:
                    risk_level = "HIGH"
                    risk_explanation = "Significant risk. Schedule repair as soon as possible to prevent emergency failure."
                    risk_icon = "🟠"
                elif risk_score >= 40:
                    risk_level = "MODERATE"
                    risk_explanation = "Notable concern. Plan for repair within the next budget cycle."
                    risk_icon = "🟡"
                else:
                    risk_level = "LOW"
                    risk_explanation = "Acceptable condition. Continue routine monitoring."
                    risk_icon = "🟢"

                st.markdown(f"""
                <div style="background: #0f172a; padding: 15px; border-radius: 8px; margin: 10px 0;">
                    <div style="font-size: 16px; color: {get_risk_color(risk_score)};">
                        {risk_icon} <strong>Risk Level: {risk_level}</strong>
                    </div>
                    <div style="color: #94a3b8; margin-top: 5px;">
                        {risk_explanation}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Time to Failure with Confidence
                if pred.estimated_time_to_failure_months:
                    st.markdown(f"""
                    <div style="background: #0f172a; padding: 15px; border-radius: 8px; margin: 10px 0;">
                        <div style="font-size: 14px; color: #94a3b8;">Estimated Time to Failure</div>
                        <div style="font-size: 28px; font-weight: bold; color: #e2e8f0;">
                            {pred.estimated_time_to_failure_months} months
                            <span style="font-size: 14px; color: #64748b;">({pred.confidence_interval})</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                # Contributing factors with better styling
                if pred.contributing_factors:
                    st.markdown("**Contributing Factors:**")
                    factors_html = ""
                    for i, factor in enumerate(pred.contributing_factors, 1):
                        factors_html += f"""
                        <div style="background: #1e293b; padding: 10px 15px; border-radius: 6px; margin: 5px 0; border-left: 3px solid #3b82f6;">
                            <span style="color: #60a5fa; font-weight: bold;">{i}.</span>
                            <span style="color: #e2e8f0;">{factor}</span>
                        </div>
                        """
                    st.markdown(factors_html, unsafe_allow_html=True)

                # Recommendation
                st.info(f"**Recommendation:** {pred.recommended_action}")

                # Cost Analysis
                st.subheader("Cost-Benefit Analysis")
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown(f"""
                    <div style="background: #1a1a2e; padding: 20px; border-radius: 8px; border-left: 4px solid #22c55e;">
                        <div style="color: #94a3b8; font-size: 14px;">Proactive Repair Cost</div>
                        <div style="color: #22c55e; font-size: 32px; font-weight: bold;">
                            ${pred.cost_estimate_repair:,.0f}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                with col2:
                    st.markdown(f"""
                    <div style="background: #1a1a2e; padding: 20px; border-radius: 8px; border-left: 4px solid #ef4444;">
                        <div style="color: #94a3b8; font-size: 14px;">Emergency Failure Cost</div>
                        <div style="color: #ef4444; font-size: 32px; font-weight: bold;">
                            ${pred.cost_estimate_emergency:,.0f}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                savings = pred.cost_estimate_emergency - pred.cost_estimate_repair
                if savings > 0:
                    savings_pct = (savings / pred.cost_estimate_emergency) * 100
                    st.success(f"💰 Proactive repair saves **${savings:,.0f}** ({savings_pct:.0f}% savings)")

                # Detailed Reasoning with better formatting
                if pred.reasoning:
                    with st.expander("📋 View Detailed AI Reasoning", expanded=False):
                        # Split reasoning into paragraphs for better readability
                        reasoning_text = pred.reasoning.strip()
                        paragraphs = reasoning_text.split('\n\n')

                        for para in paragraphs:
                            para = para.strip()
                            if para:
                                # Check if it's a numbered list item
                                if para[0].isdigit() and '.' in para[:3]:
                                    st.markdown(f"**{para}**")
                                else:
                                    st.markdown(para)
                                st.markdown("")  # Add spacing

    # Tab 3: PACP Reference
    with tab3:
        st.header("PACP Defect Codes Reference")
        st.markdown("""
        The Pipeline Assessment Certification Program (PACP) provides standardized
        defect codes for sewer pipe inspection. SewerSentinel uses these standards
        for consistent defect classification.
        """)

        st.subheader("Defect Codes")
        codes_col1, codes_col2 = st.columns(2)

        codes = list(DEFECT_CODE_DESCRIPTIONS.items()) if ENGINE_AVAILABLE else []
        mid = len(codes) // 2

        with codes_col1:
            for code, desc in codes[:mid]:
                st.markdown(f"**{code}** - {desc}")

        with codes_col2:
            for code, desc in codes[mid:]:
                st.markdown(f"**{code}** - {desc}")

        st.subheader("Grade Definitions")
        st.markdown("""
        | Grade | Severity | Description | Action |
        |-------|----------|-------------|--------|
        | 1 | Minor | Minimal defect, no structural impact | Monitor |
        | 2 | Minor-Moderate | Small defect, cosmetic concern | Future inspection |
        | 3 | Moderate | Noticeable defect, some degradation | Repair in 3-5 years |
        | 4 | Significant | Major defect, structural concern | Repair in 1-2 years |
        | 5 | Critical | Severe defect, imminent failure risk | Immediate action |
        """)

        st.subheader("About SewerSentinel")
        st.markdown("""
        **SewerSentinel** is an autonomous infrastructure prediction system that:

        1. **Detects** defects in CCTV pipe inspection footage using Gemini 3's multimodal vision
        2. **Predicts** degradation trajectories using deep reasoning (thinking_level="high")
        3. **Prioritizes** repairs based on risk scores and cost-benefit analysis

        ### Gemini 3 Features Used
        - **Multimodal Vision** - Analyzes pipe inspection images
        - **Thinking Levels** - Deep causal reasoning for predictions
        - **Large Context** - Processes detailed PACP standards
        - **JSON Mode** - Structured output for reliable parsing

        ### The Problem
        - 850 billion gallons of untreated sewage discharge into U.S. waterways annually
        - Current inspection requires humans to watch thousands of hours of footage
        - By the time problems are visible, they're often emergencies

        ### Our Solution
        SewerSentinel transforms **reactive** maintenance into **proactive** protection.

        ---
        Built for the **Google DeepMind Gemini 3 Hackathon 2026**
        """)


if __name__ == "__main__":
    main()

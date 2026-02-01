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
    from analysis_engine import AnalysisResult, DetectedDefect, PredictionResult, RepairItem

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

    # Create sample repair items for demo
    repair_items = [
        RepairItem(
            defect_code="CC",
            defect_description="Circumferential Crack (Grade 4)",
            repair_method="CIPP liner section",
            estimated_cost=7500.0,
            priority="short-term",
            notes="Circumferential cracks may indicate joint stress or differential settlement"
        ),
        RepairItem(
            defect_code="RM",
            defect_description="Root Intrusion (Medium) (Grade 3)",
            repair_method="Root cutting + joint sealing",
            estimated_cost=2500.0,
            priority="medium-term",
            notes="Medium roots are actively growing - seal entry points after removal"
        ),
        RepairItem(
            defect_code="I",
            defect_description="Infiltration (Grade 3)",
            repair_method="Internal joint sealing + grouting",
            estimated_cost=3500.0,
            priority="medium-term",
            notes="Infiltration indicates compromised pipe integrity and adds to treatment load"
        ),
        RepairItem(
            defect_code="COR",
            defect_description="Corrosion (Grade 2)",
            repair_method="Corrosion inhibitor + coating",
            estimated_cost=1500.0,
            priority="long-term",
            notes="Corrosion is progressive - early treatment prevents wall loss"
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
        cost_estimate_repair=15000.0,  # Sum of itemized repairs
        cost_estimate_emergency=112500.0,  # Emergency multiplier applied
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

Cost analysis: Proactive CIPP rehabilitation ($15,000) vs emergency dig-and-replace after collapse under roadway ($112,500 including traffic control, emergency response, environmental cleanup, and expedited materials).""",
        repair_items=repair_items
    )

    # Create full analysis result
    return AnalysisResult(
        pipe_id="DEMO-PIPE-001",
        inspection_date=datetime.now().strftime("%Y-%m-%d"),
        defects=defects,
        overall_grade=4,
        quick_rating="0102",
        prediction=prediction,
        executive_summary="This 45-year-old concrete pipe shows significant structural damage requiring prompt attention. A Grade 4 crack at the crown combined with active water infiltration and root intrusion creates high failure risk. Without repair within 9 months, there is substantial risk of collapse under the roadway. Proactive repair will save an estimated $97,500 compared to emergency response.",
        analysis_timestamp=datetime.now().isoformat(),
        raw_analysis={
            "demo_mode": True,
            "auto_detected": {
                "material": "concrete",
                "material_confidence": 0.91,
                "diameter": 18,
                "water_level": 25
            },
            "manual_context": {
                "pipe_age_years": 45,
                "pipe_material": "clay",  # Different from AI-detected to show comparison
                "pipe_diameter_inches": 12,  # Different from AI-detected
                "depth_feet": 10.0,
                "traffic_load": "heavy",
                "soil_type": "clay",
                "groundwater": "high",
                "location_type": "residential"
            },
            "used_context": {
                "pipe_age_years": 45,
                "pipe_material": "concrete",  # Used AI-detected value
                "pipe_diameter_inches": 18,  # Used AI-detected value
                "depth_feet": 10.0,
                "traffic_load": "heavy",
                "soil_type": "clay",
                "groundwater": "high",
                "location_type": "residential"
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

    # Initialize session state for manual context values
    if 'manual_context' not in st.session_state:
        st.session_state['manual_context'] = {
            'pipe_id': f"PIPE-{datetime.now().strftime('%H%M%S')}",
            'pipe_age_years': 30,
            'pipe_diameter_inches': 12,
            'pipe_material': 'concrete',
            'depth_feet': 8.0,
            'traffic_load': 'medium',
            'soil_type': 'clay',
            'groundwater': 'medium',
            'location_type': 'residential'
        }

    # Use variables from session state
    pipe_id = st.session_state['manual_context']['pipe_id']
    pipe_age = st.session_state['manual_context']['pipe_age_years']
    diameter = st.session_state['manual_context']['pipe_diameter_inches']
    pipe_material = st.session_state['manual_context']['pipe_material']
    depth = st.session_state['manual_context']['depth_feet']
    traffic_load = st.session_state['manual_context']['traffic_load']
    soil_type = st.session_state['manual_context']['soil_type']
    groundwater = st.session_state['manual_context']['groundwater']
    location_type = st.session_state['manual_context']['location_type']

    # Minimal sidebar - just branding
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 20px 0;">
            <div style="font-size: 48px;">🔍</div>
            <h2 style="margin: 10px 0 5px 0; color: #e2e8f0;">SewerSentinel</h2>
            <p style="color: #64748b; font-size: 12px; margin: 0;">
                AI-Powered Pipe Analysis
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        st.markdown("""
        <div style="color: #94a3b8; font-size: 13px;">
            <p><strong>How to use:</strong></p>
            <ol style="padding-left: 20px; margin: 10px 0;">
                <li>Upload a pipe image or try Demo</li>
                <li>View AI-detected defects</li>
                <li>Adjust data sources if needed</li>
                <li>Review predictions & costs</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # Location Settings for cost estimation
        st.subheader("Location Settings")
        region = st.selectbox(
            "Your Region",
            ["Midwest", "Northeast", "Southeast", "Southwest", "West Coast", "Mountain"],
            index=0,
            help="Affects labor rates, permits, and material costs"
        )
        st.session_state['region'] = region.lower().replace(" ", "_")

        st.divider()

        # Analysis Mode Selection
        st.subheader("Analysis Mode")
        use_ensemble = st.checkbox(
            "High-Confidence Mode",
            value=False,
            help="Runs 3 independent analyses and shows consensus results. Takes longer but more reliable."
        )

        if use_ensemble:
            st.info("High-Confidence Mode: Analysis will run 3 passes for better accuracy")

        # Store in session state for use during analysis
        st.session_state['use_ensemble'] = use_ensemble

        st.divider()

        st.caption("Built for Gemini 3 Hackathon 2026")
        st.caption("Powered by Google Gemini 3")

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

            # Show image
            st.subheader("Uploaded Image")
            image = Image.open(uploaded_file)
            st.image(image, width=400)

            st.divider()

            # Pre-analysis configuration
            st.subheader("⚙️ Analysis Configuration")
            st.markdown("Configure how the analysis should handle pipe characteristics:")

            # Detection mode selection
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Material Detection**")
                material_mode = st.radio(
                    "How to determine pipe material:",
                    options=['ai', 'manual'],
                    index=0,
                    key='material_mode_select',
                    format_func=lambda x: "🤖 Let AI detect from image" if x == 'ai' else "📝 I'll specify manually",
                    horizontal=True
                )

                if material_mode == 'manual':
                    pipe_material = st.selectbox(
                        "Pipe Material",
                        ["concrete", "clay", "pvc", "cast_iron", "hdpe", "unknown"],
                        index=["concrete", "clay", "pvc", "cast_iron", "hdpe", "unknown"].index(
                            st.session_state['manual_context'].get('pipe_material', 'concrete')
                        ),
                        key='config_material'
                    )
                    st.session_state['manual_context']['pipe_material'] = pipe_material

            with col2:
                st.markdown("**Diameter Detection**")
                diameter_mode = st.radio(
                    "How to determine pipe diameter:",
                    options=['ai', 'manual'],
                    index=0,
                    key='diameter_mode_select',
                    format_func=lambda x: "🤖 Let AI estimate from image" if x == 'ai' else "📝 I'll specify manually",
                    horizontal=True
                )

                if diameter_mode == 'manual':
                    diameter = st.number_input(
                        "Pipe Diameter (inches)",
                        min_value=4,
                        max_value=120,
                        value=st.session_state['manual_context'].get('pipe_diameter_inches', 12),
                        key='config_diameter'
                    )
                    st.session_state['manual_context']['pipe_diameter_inches'] = diameter

            # Additional context (always shown, collapsed by default)
            with st.expander("📋 Additional Pipe Context (improves prediction accuracy)", expanded=False):
                st.markdown("These values cannot be detected from images - provide them for better predictions:")

                col1, col2, col3 = st.columns(3)
                with col1:
                    new_age = st.number_input(
                        "Pipe Age (years)",
                        min_value=0, max_value=150,
                        value=st.session_state['manual_context'].get('pipe_age_years', 30),
                        key='config_age'
                    )
                    st.session_state['manual_context']['pipe_age_years'] = new_age

                with col2:
                    new_depth = st.number_input(
                        "Burial Depth (ft)",
                        min_value=0.0, max_value=30.0,
                        value=float(st.session_state['manual_context'].get('depth_feet', 8.0)),
                        key='config_depth'
                    )
                    st.session_state['manual_context']['depth_feet'] = new_depth

                with col3:
                    traffic_options = ["none", "light", "medium", "heavy"]
                    new_traffic = st.selectbox(
                        "Traffic Load Above",
                        traffic_options,
                        index=traffic_options.index(st.session_state['manual_context'].get('traffic_load', 'medium')),
                        key='config_traffic'
                    )
                    st.session_state['manual_context']['traffic_load'] = new_traffic

                col1, col2, col3 = st.columns(3)
                with col1:
                    soil_options = ["clay", "sandy", "loam", "rocky", "unknown"]
                    new_soil = st.selectbox(
                        "Soil Type",
                        soil_options,
                        index=soil_options.index(st.session_state['manual_context'].get('soil_type', 'clay')),
                        key='config_soil'
                    )
                    st.session_state['manual_context']['soil_type'] = new_soil

                with col2:
                    gw_options = ["low", "medium", "high"]
                    new_gw = st.selectbox(
                        "Groundwater Level",
                        gw_options,
                        index=gw_options.index(st.session_state['manual_context'].get('groundwater', 'medium')),
                        key='config_gw'
                    )
                    st.session_state['manual_context']['groundwater'] = new_gw

                with col3:
                    loc_options = ["residential", "commercial", "industrial", "school", "hospital"]
                    new_loc = st.selectbox(
                        "Location Type",
                        loc_options,
                        index=loc_options.index(st.session_state['manual_context'].get('location_type', 'residential')),
                        key='config_loc'
                    )
                    st.session_state['manual_context']['location_type'] = new_loc

            st.divider()

            # Analyze button
            if st.button("🔍 Analyze with Gemini 3", type="primary", use_container_width=True):
                # Store the chosen modes
                st.session_state['data_sources'] = {
                    'material': material_mode,
                    'diameter': diameter_mode
                }

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

                            # Get values from session state
                            manual_ctx = st.session_state['manual_context']

                            # Build context with manual values first
                            context = {
                                "pipe_age_years": manual_ctx.get('pipe_age_years', 30),
                                "pipe_material": manual_ctx.get('pipe_material', 'concrete'),
                                "pipe_diameter_inches": manual_ctx.get('pipe_diameter_inches', 12),
                                "depth_feet": manual_ctx.get('depth_feet', 8.0),
                                "traffic_load": manual_ctx.get('traffic_load', 'medium'),
                                "soil_type": manual_ctx.get('soil_type', 'clay'),
                                "groundwater": manual_ctx.get('groundwater', 'medium'),
                                "location_type": manual_ctx.get('location_type', 'residential'),
                                "region": st.session_state.get('region', 'midwest'),
                                "segment_length_feet": 100  # Default segment length for cost estimation
                            }

                            # Check if ensemble mode is enabled
                            use_ensemble = st.session_state.get('use_ensemble', False)

                            # First, run detection to get pipe characteristics
                            if use_ensemble:
                                # For ensemble mode, we run a single detection first for characteristics
                                # then the full ensemble for defect analysis
                                detection_result = engine.analyze_image(tmp_path, pipe_id + "_detect")
                            else:
                                detection_result = engine.analyze_image(tmp_path, pipe_id)

                            # Check for auto-detected pipe characteristics
                            auto_detected = []
                            detected_material = detection_result.get('pipe_material_observed', 'unknown')
                            material_confidence = detection_result.get('pipe_material_confidence', 0)
                            detected_diameter = detection_result.get('estimated_diameter_inches')
                            detected_water_level = detection_result.get('water_level_percent')

                            # Apply AI detection ONLY if user selected AI mode
                            if material_mode == 'ai' and detected_material and detected_material != 'unknown' and material_confidence >= 0.5:
                                # Map detected material to dropdown values
                                material_map = {
                                    'concrete': 'concrete',
                                    'clay': 'clay',
                                    'vitrified clay': 'clay',
                                    'pvc': 'pvc',
                                    'cast_iron': 'cast_iron',
                                    'cast iron': 'cast_iron',
                                    'brick': 'concrete',
                                    'hdpe': 'hdpe'
                                }
                                mapped_material = material_map.get(detected_material.lower(), context['pipe_material'])
                                if mapped_material in ['concrete', 'clay', 'pvc', 'cast_iron', 'hdpe']:
                                    context['pipe_material'] = mapped_material
                                    auto_detected.append(f"Material: {mapped_material} ({material_confidence:.0%} confidence)")

                            if diameter_mode == 'ai' and detected_diameter and isinstance(detected_diameter, (int, float)) and detected_diameter > 0:
                                context['pipe_diameter_inches'] = int(detected_diameter)
                                auto_detected.append(f"Diameter: {int(detected_diameter)} inches")

                            # Run full analysis with the configured context
                            if use_ensemble:
                                # Run ensemble analysis for higher confidence
                                with st.spinner("Running ensemble analysis (3 passes)..."):
                                    ensemble_result = engine.analyze_with_ensemble(
                                        image_path=tmp_path,
                                        pipe_id=pipe_id,
                                        num_passes=3
                                    )

                                    # Create a full analysis result from ensemble data
                                    # We still need prediction, so run that separately
                                    result = engine.create_full_analysis(
                                        image_path=tmp_path,
                                        pipe_id=pipe_id,
                                        context=context
                                    )

                                    # Override defects with ensemble consensus
                                    from analysis_engine import DetectedDefect
                                    ensemble_defects = [
                                        DetectedDefect(
                                            defect_type=d.get('defect_type', ''),
                                            defect_code=d.get('defect_code', ''),
                                            grade=d.get('grade', 1),
                                            location_in_pipe=d.get('location_in_pipe', ''),
                                            confidence=d.get('confidence', 0),
                                            description=d.get('description', '')
                                        )
                                        for d in ensemble_result.get('defects', [])
                                    ]
                                    result.defects = ensemble_defects
                                    result.overall_grade = ensemble_result.get('overall_grade', 1)

                                    # Store ensemble-specific metrics
                                    result.raw_analysis['ensemble_metrics'] = {
                                        'analysis_mode': 'ensemble',
                                        'num_passes': ensemble_result.get('num_passes', 3),
                                        'successful_passes': ensemble_result.get('successful_passes', 0),
                                        'overall_confidence': ensemble_result.get('overall_confidence', 'N/A'),
                                        'overall_grade_agreement': ensemble_result.get('overall_grade_agreement', 'N/A'),
                                        'material_agreement': ensemble_result.get('material_agreement', 'N/A'),
                                        'ensemble_summary': ensemble_result.get('ensemble_summary', ''),
                                        'defect_agreements': {
                                            d.get('defect_code', ''): {
                                                'agreement': d.get('ensemble_agreement', ''),
                                                'grade_range': d.get('grade_range', '')
                                            }
                                            for d in ensemble_result.get('defects', [])
                                        }
                                    }
                            else:
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

                            # Store manual context values for comparison
                            result.raw_analysis['manual_context'] = manual_ctx.copy()

                            # Store the context that was actually used
                            result.raw_analysis['used_context'] = context.copy()

                            # Store which modes were selected
                            result.raw_analysis['selected_modes'] = {
                                'material': material_mode,
                                'diameter': diameter_mode
                            }

                            # Store result in session state
                            st.session_state['analysis_result'] = result
                            st.session_state['analysis_image'] = image

                            # Clean up temp file
                            os.unlink(tmp_path)

                            # Show success message
                            mode_info = []
                            if use_ensemble:
                                ensemble_metrics = result.raw_analysis.get('ensemble_metrics', {})
                                mode_info.append(f"Ensemble ({ensemble_metrics.get('successful_passes', 3)}/3 passes)")
                                overall_conf = ensemble_metrics.get('overall_confidence', 'N/A')
                                st.success(f"Ensemble analysis complete! Agreement: {overall_conf}")
                            else:
                                if material_mode == 'ai' and auto_detected:
                                    mode_info.append(f"AI detected: {', '.join(auto_detected)}")
                                if material_mode == 'manual':
                                    mode_info.append(f"Using manual material: {context['pipe_material']}")
                                if diameter_mode == 'manual':
                                    mode_info.append(f"Using manual diameter: {context['pipe_diameter_inches']}\"")

                                if mode_info:
                                    st.success(f"Analysis complete! {' | '.join(mode_info)}")
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

            # Executive Summary (always visible - it's the key takeaway)
            st.info(f"**Executive Summary:** {result.executive_summary}")

            # Ensemble Analysis Results (if applicable)
            ensemble_metrics = result.raw_analysis.get('ensemble_metrics', {})
            if ensemble_metrics.get('analysis_mode') == 'ensemble':
                with st.expander("Ensemble Analysis Results", expanded=True):
                    st.markdown(f"""
                    **Ensemble Analysis Results**
                    - Passes completed: {ensemble_metrics.get('successful_passes')}/{ensemble_metrics.get('num_passes')}
                    - Overall agreement: {ensemble_metrics.get('overall_confidence')}
                    - Grade agreement: {ensemble_metrics.get('overall_grade_agreement')}
                    - Material agreement: {ensemble_metrics.get('material_agreement')}
                    """)

                    st.caption(ensemble_metrics.get('ensemble_summary', ''))

            # Data Sources Section - Show what was used (read-only summary)
            used_context = result.raw_analysis.get('used_context', {})
            selected_modes = result.raw_analysis.get('selected_modes', {})
            auto_detected = result.raw_analysis.get('auto_detected', {})

            # Only show if we have context data
            if used_context:
                with st.expander("⚙️ Analysis Configuration Used", expanded=False):
                    st.markdown("These values were used to generate predictions:")

                    # Show material and diameter with source indicator
                    col1, col2 = st.columns(2)

                    with col1:
                        material_mode = selected_modes.get('material', 'manual')
                        material_val = used_context.get('pipe_material', 'unknown')
                        material_conf = auto_detected.get('material_confidence', 0)
                        source_icon = "🤖" if material_mode == 'ai' else "📝"
                        source_label = f"AI ({material_conf:.0%})" if material_mode == 'ai' else "Manual"

                        st.markdown(f"""
                        <div style="background: #1e293b; padding: 12px; border-radius: 6px;">
                            <div style="color: #94a3b8; font-size: 12px;">{source_icon} {source_label}</div>
                            <div style="color: #e2e8f0; font-size: 14px; font-weight: bold;">Material: {material_val.replace('_', ' ').title()}</div>
                        </div>
                        """, unsafe_allow_html=True)

                    with col2:
                        diameter_mode = selected_modes.get('diameter', 'manual')
                        diameter_val = used_context.get('pipe_diameter_inches', 12)
                        source_icon = "🤖" if diameter_mode == 'ai' else "📝"
                        source_label = "AI Estimated" if diameter_mode == 'ai' else "Manual"

                        st.markdown(f"""
                        <div style="background: #1e293b; padding: 12px; border-radius: 6px;">
                            <div style="color: #94a3b8; font-size: 12px;">{source_icon} {source_label}</div>
                            <div style="color: #e2e8f0; font-size: 14px; font-weight: bold;">Diameter: {diameter_val}"</div>
                        </div>
                        """, unsafe_allow_html=True)

                    # Other context values
                    st.markdown("---")
                    st.markdown("**Additional Context:**")

                    context_html = f"""
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;">
                        <div style="background: #1e293b; padding: 8px; border-radius: 4px;">
                            <div style="color: #94a3b8; font-size: 11px;">AGE</div>
                            <div style="color: #e2e8f0;">{used_context.get('pipe_age_years', 'N/A')} years</div>
                        </div>
                        <div style="background: #1e293b; padding: 8px; border-radius: 4px;">
                            <div style="color: #94a3b8; font-size: 11px;">DEPTH</div>
                            <div style="color: #e2e8f0;">{used_context.get('depth_feet', 'N/A')} ft</div>
                        </div>
                        <div style="background: #1e293b; padding: 8px; border-radius: 4px;">
                            <div style="color: #94a3b8; font-size: 11px;">TRAFFIC</div>
                            <div style="color: #e2e8f0;">{used_context.get('traffic_load', 'N/A').title()}</div>
                        </div>
                        <div style="background: #1e293b; padding: 8px; border-radius: 4px;">
                            <div style="color: #94a3b8; font-size: 11px;">SOIL</div>
                            <div style="color: #e2e8f0;">{used_context.get('soil_type', 'N/A').title()}</div>
                        </div>
                        <div style="background: #1e293b; padding: 8px; border-radius: 4px;">
                            <div style="color: #94a3b8; font-size: 11px;">GROUNDWATER</div>
                            <div style="color: #e2e8f0;">{used_context.get('groundwater', 'N/A').title()}</div>
                        </div>
                        <div style="background: #1e293b; padding: 8px; border-radius: 4px;">
                            <div style="color: #94a3b8; font-size: 11px;">LOCATION</div>
                            <div style="color: #e2e8f0;">{used_context.get('location_type', 'N/A').title()}</div>
                        </div>
                    </div>
                    """
                    st.markdown(context_html, unsafe_allow_html=True)

                    st.caption("💡 To change these values, go back to the Analyze tab and reconfigure before running a new analysis.")

            # Defects Section - Collapsible
            defect_count = len(result.defects)
            max_grade = max([d.grade for d in result.defects], default=0) if result.defects else 0
            defect_summary = f"🔍 Detected Defects ({defect_count}) - Highest Grade: {max_grade}" if result.defects else "🔍 Detected Defects (0) - No issues found"

            with st.expander(defect_summary, expanded=True):
                if not result.defects:
                    st.success("No significant defects detected!")
                else:
                    for defect in result.defects:
                        grade_color = get_grade_color(defect.grade)

                        # Get ensemble agreement info if available
                        defect_agreements = ensemble_metrics.get('defect_agreements', {})
                        defect_agreement_info = defect_agreements.get(defect.defect_code, {})
                        ensemble_agreement = defect_agreement_info.get('agreement', '')
                        grade_range = defect_agreement_info.get('grade_range', '')

                        # Build ensemble info line if available
                        ensemble_line = ""
                        if ensemble_agreement and grade_range:
                            ensemble_line = f"""
                            <div style="color: #60a5fa; font-size: 12px; margin-top: 4px;">
                                Ensemble Agreement: {ensemble_agreement} | Grade range: {grade_range}
                            </div>
                            """

                        st.markdown(f"""
                        <div style="background: #1e293b; padding: 12px 15px; border-radius: 8px; margin: 8px 0; border-left: 4px solid {grade_color};">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <span style="color: {grade_color}; font-weight: bold;">{defect.defect_code}</span>
                                    <span style="color: #e2e8f0; margin-left: 8px;">{DEFECT_CODE_DESCRIPTIONS.get(defect.defect_code, defect.defect_type)}</span>
                                </div>
                                <span style="background: {grade_color}; color: white; padding: 2px 10px; border-radius: 4px; font-weight: bold;">Grade {defect.grade}</span>
                            </div>
                            <div style="color: #94a3b8; font-size: 13px; margin-top: 6px;">
                                📍 {defect.location_in_pipe} | Confidence: {defect.confidence:.0%}
                            </div>
                            <div style="color: #cbd5e1; font-size: 13px; margin-top: 4px; font-style: italic;">
                                {defect.description if defect.description else ''}
                            </div>
                            {ensemble_line}
                        </div>
                        """, unsafe_allow_html=True)

            # Prediction Section - Collapsible
            if result.prediction:
                pred = result.prediction
                risk_color = get_risk_color(pred.failure_risk_score)
                prediction_summary = f"📊 Failure Prediction - Risk: {pred.failure_risk_score:.0f}% | Time to Failure: {pred.estimated_time_to_failure_months} months"

                with st.expander(prediction_summary, expanded=True):
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        color = get_risk_color(pred.failure_risk_score)
                        st.markdown(f"""
                        <div style="text-align: center;">
                            <div style="font-size: 48px; font-weight: bold; color: {color};">
                                {pred.failure_risk_score:.0f}%
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

                # Cost Analysis Section - Collapsible
                cost_summary = f"💰 Cost-Benefit Analysis - Repair: ${pred.cost_estimate_repair:,.0f} vs Emergency: ${pred.cost_estimate_emergency:,.0f}"
                with st.expander(cost_summary, expanded=True):
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

                    # Detailed Itemized Cost Breakdown (from CostEstimator)
                    if hasattr(pred, 'detailed_estimate') and pred.detailed_estimate:
                        estimate = pred.detailed_estimate

                        with st.expander("📋 Itemized Cost Breakdown", expanded=False):
                            st.markdown(f"**Repair Method:** {estimate.repair_method}")
                            st.markdown(f"**Region:** {estimate.region}")
                            st.markdown("---")

                            # Group line items by category
                            current_category = None
                            for item in estimate.line_items:
                                if item.category != current_category:
                                    if current_category is not None:
                                        st.markdown("---")
                                    st.markdown(f"**{item.category.upper()}**")
                                    current_category = item.category

                                col1, col2 = st.columns([3, 1])
                                with col1:
                                    st.write(f"{item.description}")
                                    if item.notes:
                                        st.caption(f"_{item.notes}_")
                                with col2:
                                    st.write(f"**${item.total:,.0f}**")

                            # Summary totals
                            st.markdown("---")
                            st.markdown(f"""
                            <div style="background: #0f172a; padding: 15px; border-radius: 8px; margin-top: 10px;">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                                    <span style="color: #94a3b8;">Subtotal</span>
                                    <span style="color: #e2e8f0;">${estimate.subtotal:,.0f}</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                                    <span style="color: #94a3b8;">Contingency</span>
                                    <span style="color: #e2e8f0;">${estimate.contingency:,.0f}</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                                    <span style="color: #94a3b8;">Engineering</span>
                                    <span style="color: #e2e8f0;">${estimate.engineering:,.0f}</span>
                                </div>
                                <div style="display: flex; justify-content: space-between; border-top: 1px solid #374151; padding-top: 10px;">
                                    <span style="color: #22c55e; font-weight: bold; font-size: 18px;">Grand Total</span>
                                    <span style="color: #22c55e; font-weight: bold; font-size: 18px;">${estimate.grand_total:,.0f}</span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                            # Assumptions
                            st.markdown("**Assumptions:**")
                            for a in estimate.assumptions[:5]:
                                st.caption(f"• {a}")

                            # Exclusions
                            with st.expander("View Exclusions", expanded=False):
                                for e in estimate.exclusions:
                                    st.caption(f"• {e}")

                    # Emergency Cost Factors
                    if hasattr(pred, 'emergency_factors') and pred.emergency_factors:
                        with st.expander("⚠️ Emergency Cost Factors", expanded=False):
                            st.markdown("**Why emergency repairs cost more:**")
                            for factor in pred.emergency_factors:
                                st.markdown(f"""
                                <div style="background: #1e293b; padding: 10px 15px; border-radius: 6px; margin: 5px 0; border-left: 3px solid #ef4444;">
                                    <span style="color: #e2e8f0;">{factor}</span>
                                </div>
                                """, unsafe_allow_html=True)

                            st.caption("Emergency costs include overtime labor, expedited materials, environmental response, and service interruption penalties.")

                # Detailed Reasoning - Collapsible (already was)
                if pred.reasoning:
                    with st.expander("📋 AI Reasoning & Analysis Details", expanded=False):
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

        1. **Detects** defects in CCTV pipe inspection footage using Gemini's multimodal vision
        2. **Predicts** degradation trajectories using deep reasoning and engineering formulas
        3. **Prioritizes** repairs based on risk scores and cost-benefit analysis

        ### Gemini Features Used
        - **Multimodal Vision** - Analyzes pipe inspection images
        - **Deep Reasoning** - Causal reasoning for failure predictions
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

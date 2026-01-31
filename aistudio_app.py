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

        if uploaded_file:
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

                                # Run full analysis
                                result = engine.create_full_analysis(
                                    image_path=tmp_path,
                                    pipe_id=pipe_id,
                                    context=context
                                )

                                # Store result in session state
                                st.session_state['analysis_result'] = result
                                st.session_state['analysis_image'] = image

                                # Clean up temp file
                                os.unlink(tmp_path)

                                st.success("Analysis complete! Go to Results tab to see details.")

                            except Exception as e:
                                st.error(f"Analysis failed: {e}")

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

                # Contributing factors
                if pred.contributing_factors:
                    st.markdown("**Contributing Factors:**")
                    for factor in pred.contributing_factors:
                        st.markdown(f"- {factor}")

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

                # Reasoning
                if pred.reasoning:
                    with st.expander("View Detailed Reasoning"):
                        st.write(pred.reasoning)

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

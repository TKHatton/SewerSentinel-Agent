# SewerSentinel

## Autonomous Underground Infrastructure Predictive Failure System

**Google DeepMind Gemini 3 Hackathon 2026**

SewerSentinel is an AI-powered system that transforms reactive sewer maintenance into proactive infrastructure protection. Using Google's Gemini 3 multimodal capabilities, it analyzes pipe inspection footage, predicts failures before they happen, and generates optimized maintenance schedules.

### The Problem

- 850 billion gallons of untreated sewage discharge into U.S. waterways annually due to pipe failures
- Sinkholes cause property damage, injuries, and deaths
- Current inspection process: humans watch thousands of hours of footage, often missing subtle degradation
- By the time problems are visible, they're often emergencies

### The Solution

SewerSentinel doesn't just detect problems—it **predicts** them and **prioritizes** solutions.

**Detection** → **Prediction** → **Prioritization** → **Action**

## Gemini 3 Integration

SewerSentinel leverages Gemini 3's most advanced capabilities:

| Feature | Usage |
|---------|-------|
| **Multimodal Vision** | Analyze CCTV footage with spatial and temporal reasoning |
| **Deep Reasoning** | Causal reasoning about degradation factors and failure timelines |
| **Large Context** | Process detailed PACP standards and pipe inspection histories |
| **JSON Mode** | Structured output for reliable defect classification |

## Features

### Intelligent Defect Detection
- Classifies 16+ defect types (cracks, root intrusion, deposits, corrosion, etc.)
- PACP-compliant severity grading (1-5 scale)
- Temporal analysis across video sequences

### Predictive Analytics
- Degradation trajectory modeling
- Failure timeline estimation with confidence intervals
- Correlation with external factors (traffic load, weather patterns, soil type)

### Risk-Based Prioritization
- Consequence scoring by location (school zone vs. parking lot)
- Budget-constrained maintenance optimization
- Cost-benefit analysis for repairs

### Executive Dashboard
- Interactive pipe network visualization
- Real-time analysis status
- Exportable reports (PACP-compliant)

## Quick Start

### Prerequisites
- Python 3.10+
- Gemini 3 API access ([Get API Key](https://aistudio.google.com/app/apikey))

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/SewerSentinel-Agent.git
cd SewerSentinel-Agent

# Run setup script
chmod +x setup.sh
./setup.sh

# Set your API key
export GEMINI_API_KEY="your-gemini-api-key"
```

### Running the Application

**Option 1: Streamlit App (Recommended for Demo)**
```bash
./run.sh streamlit
# or
streamlit run aistudio_app.py
```

**Option 2: FastAPI Backend**
```bash
./run.sh api
# or
python -m uvicorn server:app --reload
```

**Option 3: Both**
```bash
./run.sh both
```

## Project Structure

```
SewerSentinel-Agent/
├── analysis_engine.py      # Core Gemini 3 analysis engine
├── server.py               # FastAPI REST API server
├── video_processor.py      # Video frame extraction (OpenCV)
├── aistudio_app.py         # Streamlit demo app (AI Studio deployment)
├── Dashboard.jsx           # React dashboard component
├── requirements.txt        # Python dependencies
├── setup.sh                # Environment setup script
├── run.sh                  # Application runner script
├── architecture.md         # System architecture diagrams
├── devpost_submission.md   # Hackathon submission text
└── data/                   # Inspection images (not in repo)
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check and API status |
| `/api/analyze` | POST | Analyze single pipe image |
| `/api/analyze-video` | POST | Analyze video (extracts frames) |
| `/api/predict` | POST | Predict degradation trajectory |
| `/api/prioritize` | POST | Prioritize repair queue |
| `/api/full-analysis` | POST | Complete analysis pipeline |
| `/api/sample-analysis` | GET | Get demo analysis data |
| `/api/defect-codes` | GET | PACP defect code reference |

## PACP Defect Codes

| Code | Defect Type | Code | Defect Type |
|------|-------------|------|-------------|
| CL | Longitudinal Crack | RF | Root (Fine) |
| CC | Circumferential Crack | RM | Root (Medium) |
| CM | Multiple Cracks | RB | Root (Ball) |
| FC | Fracture | I | Infiltration |
| B | Broken | JD | Joint Displaced |
| H | Hole | JS | Joint Separated |
| X | Collapse | DS | Deposits Settled |
| D | Deformed | DAG | Deposits Attached |
| SD | Surface Damage | COR | Corrosion |

## Grade Definitions

| Grade | Severity | Action Required |
|-------|----------|-----------------|
| 1 | Minor | Monitor only |
| 2 | Minor-Moderate | Future inspection |
| 3 | Moderate | Repair in 3-5 years |
| 4 | Significant | Repair in 1-2 years |
| 5 | Critical | Immediate attention |

## Dataset

SewerSentinel is designed to work with the [Sewer-ML Dataset](https://vap.aau.dk/sewer-ml/):
- 1.3 million images
- 75,618 inspection videos
- 9 years of professional annotations
- 16+ defect classes

The dataset is not included due to size and licensing (CC BY-NC-SA).

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     SEWERSENTINEL AGENT                       │
├──────────────────────────────────────────────────────────────┤
│  Input Layer          │  Gemini Analysis     │  Output Layer │
│  ├─ Video Ingestion   │  ├─ Multimodal       │  ├─ Dashboard │
│  ├─ Context Data      │  ├─ Deep Reasoning   │  ├─ Reports   │
│  └─ Image Upload      │  └─ JSON Parsing     │  └─ API       │
├──────────────────────────────────────────────────────────────┤
│  Prediction Engine    │  Prioritization      │               │
│  ├─ Degradation Model │  ├─ Risk Scoring     │               │
│  ├─ Timeline Estimate │  ├─ Cost-Benefit     │               │
│  └─ Confidence Bands  │  └─ Budget Aware     │               │
└──────────────────────────────────────────────────────────────┘
```

## Judging Criteria Alignment

| Criterion | Weight | How SewerSentinel Delivers |
|-----------|--------|---------------------------|
| Technical Execution | 40% | Gemini multimodal vision + engineering-based failure prediction |
| Innovation/Wow | 30% | First system to predict failure timelines, not just detect |
| Potential Impact | 20% | Prevents catastrophes, saves cities millions |
| Presentation | 10% | Professional dashboard, clear problem statement |

## Future Vision

SewerSentinel's technology transfers directly to:
- Levee monitoring
- Bridge inspection
- Dam safety
- Any aging infrastructure with visual inspection records

## License

MIT License - See LICENSE file

Dataset usage requires separate license from Aalborg University (CC BY-NC-SA).

## Acknowledgments

- Sewer-ML Dataset (Aalborg University)
- NASSCO for PACP standards documentation
- Google DeepMind for Gemini 3 access

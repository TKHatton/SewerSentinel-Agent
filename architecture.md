# SewerSentinel Architecture Documentation

## System Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           SEWERSENTINEL AGENT                                 │
│                    Autonomous Infrastructure Prediction System                │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
         ┌────────────────────────────┼────────────────────────────┐
         │                            │                            │
         ▼                            ▼                            ▼
┌─────────────────┐        ┌─────────────────┐        ┌─────────────────┐
│   DATA INPUTS   │        │   GEMINI 3 PRO   │        │    OUTPUTS      │
│                 │        │   ANALYSIS CORE  │        │                 │
│ • CCTV Videos   │───────▶│                  │───────▶│ • Dashboard     │
│ • Pipe Metadata │        │ • Multimodal     │        │ • PACP Reports  │
│ • GIS Data      │        │ • 1M Context     │        │ • Priority Queue│
│ • Weather API   │        │ • Thought Sigs   │        │ • Exec Summary  │
│ • Traffic Data  │        │ • Thinking Lvls  │        │ • Alerts        │
└─────────────────┘        └─────────────────┘        └─────────────────┘
```

## Detailed Component Architecture

### 1. Data Ingestion Layer

```
┌───────────────────────────────────────────────────────────────┐
│                    DATA INGESTION LAYER                        │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │
│  │   Video     │  │   Static    │  │   External APIs     │   │
│  │   Sources   │  │   Data      │  │                     │   │
│  ├─────────────┤  ├─────────────┤  ├─────────────────────┤   │
│  │ • Sewer-ML  │  │ • Pipe age  │  │ • Weather (NOAA)    │   │
│  │ • CCTV-Pipe │  │ • Material  │  │ • Traffic (DOT)     │   │
│  │ • Live Feed │  │ • Diameter  │  │ • Soil (USDA)       │   │
│  │ • Upload    │  │ • Location  │  │ • GIS coordinates   │   │
│  └─────────────┘  └─────────────┘  └─────────────────────┘   │
│         │                │                    │               │
│         └────────────────┼────────────────────┘               │
│                          ▼                                    │
│              ┌─────────────────────┐                         │
│              │  Unified Data Layer  │                         │
│              │  (Preprocessed for   │                         │
│              │   Gemini 3 input)    │                         │
│              └─────────────────────┘                         │
└───────────────────────────────────────────────────────────────┘
```

### 2. Gemini 3 Analysis Core

```
┌───────────────────────────────────────────────────────────────┐
│               GEMINI 3 PRO ANALYSIS CORE                       │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                 DEFECT DETECTION MODULE                  │ │
│  │                                                          │ │
│  │  Input: Video frames / Images                            │ │
│  │  Process: Multimodal analysis with PACP knowledge        │ │
│  │  Output: Defect type, code, grade, location, confidence  │ │
│  └─────────────────────────────────────────────────────────┘ │
│                          │                                    │
│                          ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              THOUGHT SIGNATURES (State Tracking)         │ │
│  │                                                          │ │
│  │  • Maintains memory of each pipe's inspection history    │ │
│  │  • Tracks defect progression over time                   │ │
│  │  • Updates confidence as new data arrives                │ │
│  │  • Enables cross-inspection pattern recognition          │ │
│  └─────────────────────────────────────────────────────────┘ │
│                          │                                    │
│                          ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              THINKING LEVELS (Causal Reasoning)          │ │
│  │                                                          │ │
│  │  Level 1: What defects exist?                            │ │
│  │  Level 2: Why did these defects form?                    │ │
│  │  Level 3: How will they progress?                        │ │
│  │  Level 4: When will failure occur?                       │ │
│  │  Level 5: What are the consequences?                     │ │
│  └─────────────────────────────────────────────────────────┘ │
│                          │                                    │
│                          ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │               PREDICTION ENGINE                          │ │
│  │                                                          │ │
│  │  Inputs:                                                 │ │
│  │  • Current defect analysis                               │ │
│  │  • Pipe context (age, material, location)                │ │
│  │  • Environmental factors                                 │ │
│  │  • Historical patterns from Thought Signatures           │ │
│  │                                                          │ │
│  │  Outputs:                                                │ │
│  │  • Degradation trajectory                                │ │
│  │  • Failure timeline estimate                             │ │
│  │  • Confidence intervals                                  │ │
│  │  • Contributing factors                                  │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### 3. Priority & Output Layer

```
┌───────────────────────────────────────────────────────────────┐
│                  PRIORITY & OUTPUT LAYER                       │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                 PRIORITIZATION ENGINE                    │ │
│  │                                                          │ │
│  │  Scoring Factors:                                        │ │
│  │  ┌─────────────────┬─────────────────┬────────────────┐ │ │
│  │  │  Risk Score     │  Cost Ratio     │  Time Factor   │ │ │
│  │  │  (40% weight)   │  (30% weight)   │  (30% weight)  │ │ │
│  │  │                 │                 │                │ │ │
│  │  │  Failure        │  Emergency $    │  Days until    │ │ │
│  │  │  probability    │  ───────────    │  predicted     │ │ │
│  │  │  × consequence  │  Repair $       │  failure       │ │ │
│  │  └─────────────────┴─────────────────┴────────────────┘ │ │
│  │                          │                               │ │
│  │                          ▼                               │ │
│  │              Ranked Priority Queue                       │ │
│  └─────────────────────────────────────────────────────────┘ │
│                          │                                    │
│         ┌────────────────┼────────────────┐                  │
│         ▼                ▼                ▼                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │  Dashboard  │  │    PACP     │  │  Executive  │          │
│  │   (React)   │  │   Reports   │  │  Summaries  │          │
│  │             │  │             │  │             │          │
│  │ • Live view │  │ • PDF/JSON  │  │ • Plain     │          │
│  │ • Priority  │  │ • Compliant │  │   English   │          │
│  │   queue     │  │ • Defect    │  │ • Action    │          │
│  │ • Analytics │  │   codes     │  │   items     │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

## Data Flow Diagram

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  VIDEO  │───▶│ EXTRACT │───▶│ ANALYZE │───▶│ PREDICT │───▶│PRIORITIZE│
│  INPUT  │    │ FRAMES  │    │ DEFECTS │    │ FAILURE │    │ REPAIRS │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
                                  │              │               │
                                  ▼              ▼               ▼
                            ┌─────────┐    ┌─────────┐    ┌─────────┐
                            │ THOUGHT │    │THINKING │    │ OUTPUT  │
                            │  SIGS   │◀──▶│ LEVELS  │    │ REPORTS │
                            │(memory) │    │(reason) │    │         │
                            └─────────┘    └─────────┘    └─────────┘
```

## Technology Stack

```
┌───────────────────────────────────────────────────────────────┐
│                      TECHNOLOGY STACK                          │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  FRONTEND          │  BACKEND           │  AI/ML              │
│  ──────────────    │  ──────────────    │  ──────────────     │
│  • React 18        │  • Python 3.11     │  • Gemini 3 Pro     │
│  • Tailwind CSS    │  • FastAPI         │  • 1M Context       │
│  • Recharts        │  • OpenCV          │  • Multimodal       │
│  • Framer Motion   │  • Pillow          │  • Tool Calling     │
│                    │  • Pandas          │                      │
│                                                               │
│  DATA              │  DEPLOYMENT        │  STANDARDS          │
│  ──────────────    │  ──────────────    │  ──────────────     │
│  • Sewer-ML        │  • AI Studio       │  • PACP v7          │
│  • CCTV-Pipe       │  • Vercel          │  • NASSCO           │
│  • Weather APIs    │  • GitHub          │  • WRc              │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

## Gemini 3 Feature Utilization

| Feature | Usage in SewerSentinel |
|---------|----------------------|
| 1M Token Context | Load entire inspection histories for temporal analysis |
| Multimodal Vision | Analyze CCTV video frames for defects |
| Thought Signatures | Track pipe state across multiple inspections |
| Thinking Levels | Deep causal reasoning about degradation |
| Tool Calling | Fetch weather, traffic, soil data |
| Streaming | Real-time analysis updates during video processing |

## Marathon Agent Design

SewerSentinel operates as an autonomous marathon agent:

```
┌────────────────────────────────────────────────────────────────────┐
│                    MARATHON AGENT LIFECYCLE                         │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  INIT ──▶ WATCH ──▶ ANALYZE ──▶ PREDICT ──▶ REPORT ──▶ SLEEP     │
│    │        │          │           │          │          │        │
│    │        │          │           │          │          │        │
│    │        ▼          ▼           ▼          ▼          │        │
│    │   New video   Defects    Degradation  Priority     │        │
│    │   detected    found      forecasted   updated      │        │
│    │                                                     │        │
│    └─────────────────────────────────────────────────────┘        │
│                     (Continuous Loop - Hours/Days)                 │
│                                                                    │
│  Self-Correction:                                                  │
│  • Updates predictions when new inspections arrive                 │
│  • Refines models based on actual vs. predicted failures          │
│  • Adjusts confidence intervals over time                          │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

This architecture document should be included in your GitHub repository and can be referenced in your demo video.

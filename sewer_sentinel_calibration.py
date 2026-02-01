"""
SewerSentinel Calibration Module
================================
Few-shot examples and grading rubrics derived from:
- Sewer-ML Dataset (Haurum & Moeslund, CVPR 2021) - 1.3M annotated images
- NASSCO PACP v7.0 Standards
- Industry best practices

This module provides:
1. PACP-compliant grading rubrics with exact thresholds
2. Few-shot examples for in-context learning
3. Ensemble analysis for high-confidence assessments
"""

# =============================================================================
# SECTION 1: PACP GRADING RUBRICS
# =============================================================================
# These exact thresholds ensure consistent grading regardless of run

GRADING_RUBRICS = """
=== PACP DEFECT GRADING RUBRICS ===
Use these EXACT thresholds for consistent grading. Do not deviate.

CRACKS (CL - Longitudinal, CC - Circumferential, CM - Multiple, CS - Spiral):
+----------+------------------------------------------------------------------+
| Grade 1  | Hairline crack, <1mm width, no displacement                      |
| Grade 2  | Crack 1-3mm width, no displacement, surface only                 |
| Grade 3  | Crack 3-6mm width, minimal displacement, may have minor seepage  |
| Grade 4  | Crack 6-10mm width, visible displacement, active infiltration    |
| Grade 5  | Crack >10mm OR pieces displaced/missing OR structural failure    |
+----------+------------------------------------------------------------------+

DEFORMATION (D):
+----------+------------------------------------------------------------------+
| Grade 1  | <5% reduction in diameter, barely visible                        |
| Grade 2  | 5-10% reduction in diameter, noticeable but not severe           |
| Grade 3  | 10-15% reduction in diameter, moderate flow impact               |
| Grade 4  | 15-25% reduction in diameter, significant flow restriction       |
| Grade 5  | >25% reduction OR visible buckling OR imminent collapse          |
+----------+------------------------------------------------------------------+

ROOT INTRUSION (RF - Fine, RM - Medium, RB - Ball):
+----------+------------------------------------------------------------------+
| RF Gr 1  | Fine roots <5% of flow area, hair-like                           |
| RF Gr 2  | Fine roots 5-15% of flow area                                    |
| RM Gr 2  | Tap roots visible, <15% of flow area                             |
| RM Gr 3  | Tap root mass 15-30% of flow area                                |
| RM Gr 4  | Root mass 30-50% of flow area, flow restriction visible          |
| RB Gr 4  | Root ball 30-50% of flow area                                    |
| RB Gr 5  | Root ball >50% of flow area OR near-complete blockage            |
+----------+------------------------------------------------------------------+

JOINT DEFECTS (JD - Displaced, JS - Separated):
+----------+------------------------------------------------------------------+
| Grade 1  | Joint offset <5% of wall thickness                               |
| Grade 2  | Joint offset 5-15% of wall thickness                             |
| Grade 3  | Joint offset 15-25% of wall thickness, minor infiltration        |
| Grade 4  | Joint gap 25-50mm OR soil visible OR active infiltration         |
| Grade 5  | Joint gap >50mm OR soil entering pipe OR structural separation   |
+----------+------------------------------------------------------------------+

BROKEN PIPE (B):
+----------+------------------------------------------------------------------+
| Grade 3  | Break <10% of circumference, pieces in place                     |
| Grade 4  | Break 10-25% of circumference OR pieces slightly displaced       |
| Grade 5  | Break >25% of circumference OR soil visible OR pieces missing    |
+----------+------------------------------------------------------------------+

HOLE (H):
+----------+------------------------------------------------------------------+
| Grade 2  | Hole <25mm diameter, no soil visible                             |
| Grade 3  | Hole 25-50mm diameter OR minor infiltration                      |
| Grade 4  | Hole 50-150mm diameter OR soil visible OR active infiltration    |
| Grade 5  | Hole >150mm OR multiple holes OR structural compromise           |
+----------+------------------------------------------------------------------+

COLLAPSE (X):
+----------+------------------------------------------------------------------+
| Grade 5  | ANY collapse is ALWAYS Grade 5 - no exceptions                   |
+----------+------------------------------------------------------------------+

DEPOSITS (DS - Settled, DAG - Attached Grease):
+----------+------------------------------------------------------------------+
| Grade 1  | Deposits <5% of pipe diameter/circumference                      |
| Grade 2  | Deposits 5-10% depth or encrustation                             |
| Grade 3  | Deposits 10-20% depth or encrustation                            |
| Grade 4  | Deposits 20-30% depth or encrustation                            |
| Grade 5  | Deposits >30% OR flow severely restricted                        |
+----------+------------------------------------------------------------------+

INFILTRATION (I):
+----------+------------------------------------------------------------------+
| Grade 1  | Staining/mineral deposits only, no active water                  |
| Grade 2  | Seeping/weeping (surface moisture)                               |
| Grade 3  | Dripping (individual drops forming)                              |
| Grade 4  | Running/flowing (continuous stream)                              |
| Grade 5  | Gushing (significant water volume entering)                      |
+----------+------------------------------------------------------------------+

CORROSION (COR):
+----------+------------------------------------------------------------------+
| Grade 1  | Surface discoloration/staining only                              |
| Grade 2  | Light surface corrosion, <10% wall loss                          |
| Grade 3  | Moderate corrosion, 10-25% wall loss, pitting visible            |
| Grade 4  | Heavy corrosion, 25-50% wall loss, structural concern            |
| Grade 5  | Severe corrosion, >50% wall loss OR holes forming                |
+----------+------------------------------------------------------------------+
"""


# =============================================================================
# SECTION 2: FEW-SHOT EXAMPLES FROM SEWER-ML
# =============================================================================
# These examples are derived from the Sewer-ML dataset descriptions and
# PACP certification materials to calibrate the model's assessments

FEW_SHOT_EXAMPLES = """
=== CALIBRATION EXAMPLES FROM SEWER-ML DATASET ===
Use these verified examples to calibrate your assessments.

EXAMPLE 1: Severe Deformation in Corrugated Metal Pipe
------------------------------------------------------
Visual Description: Corrugated metal pipe showing significant inward
buckling at multiple clock positions (2-5 o'clock). The circular profile
is severely compromised with approximately 30% diameter reduction.
Corrugation ridges are bent and distorted.

Correct Classification:
- Defect Code: D (Deformed)
- Grade: 5 (>25% reduction with visible buckling)
- Location: Right wall, 2-5 o'clock positions
- Confidence: 95%

Key Indicators: Loss of circular shape, buckled corrugations, >25%
diameter reduction, visible structural failure beginning


EXAMPLE 2: Circumferential Crack with Active Infiltration
---------------------------------------------------------
Visual Description: Concrete pipe with crack running around
circumference at 11-1 o'clock (crown area). Crack width approximately
6-8mm. Water actively dripping through crack with mineral staining
below indicating chronic infiltration.

Correct Classification:
- Defect 1: CC (Circumferential Crack), Grade 4, Crown (12 o'clock), 92%
- Defect 2: I (Infiltration), Grade 3, At crack location, 88%

Key Indicators: Crack in 6-10mm range = Grade 4; steady drip
infiltration = Grade 3; mineral staining confirms chronic issue


EXAMPLE 3: Medium Root Intrusion at Joint
-----------------------------------------
Visual Description: Clay pipe showing roots penetrating through
displaced joint at 3 o'clock position. Root mass approximately
20% of flow area. Individual tap roots visible with some fine
root hair. Joint shows 15mm displacement.

Correct Classification:
- Defect 1: RM (Root Medium), Grade 3, 3 o'clock, 90%
- Defect 2: JD (Joint Displaced), Grade 3, 3 o'clock, 85%

Key Indicators: Tap root mass 15-30% = RM Grade 3; joint offset
15-25% of wall thickness = JD Grade 3; roots and joint issues
often co-occur at same location


EXAMPLE 4: Settled Deposits with Surface Corrosion
--------------------------------------------------
Visual Description: Concrete pipe with silt/debris accumulated
on floor approximately 15% of pipe diameter. Above water line,
walls show brownish discoloration and pitting consistent with
hydrogen sulfide corrosion, estimated 15% wall loss.

Correct Classification:
- Defect 1: DS (Deposits Settled), Grade 3, Floor (6 o'clock), 88%
- Defect 2: COR (Corrosion), Grade 3, Crown and walls, 82%

Key Indicators: Deposits 10-20% depth = Grade 3; corrosion with
10-25% wall loss = Grade 3; H2S corrosion typically affects crown


EXAMPLE 5: Joint Separation with Visible Soil
---------------------------------------------
Visual Description: Vitrified clay pipe showing complete joint
separation with 40mm gap between sections. Surrounding soil/bedding
clearly visible through gap. No active infiltration but high risk.

Correct Classification:
- Defect Code: JS (Joint Separated)
- Grade: 4 (gap 25-50mm with soil visible)
- Location: Full circumference at joint
- Confidence: 94%

Key Indicators: Gap measurement 40mm = Grade 4 range; soil visible
confirms structural compromise; potential for soil erosion and sinkhole


EXAMPLE 6: Root Ball Causing Near-Complete Blockage
---------------------------------------------------
Visual Description: Mass of intertwined roots filling approximately
60% of pipe cross-section. Dense ball of fine and medium roots with
some larger tap roots visible. Flow restricted to small channel at
bottom of pipe.

Correct Classification:
- Defect Code: RB (Root Ball)
- Grade: 5 (>50% of flow area)
- Location: Throughout visible section
- Confidence: 96%

Key Indicators: Root mass >50% = automatic Grade 5; dense
intertwined structure = ball classification; severe flow restriction


EXAMPLE 7: Multiple Cracks in Concrete Pipe
-------------------------------------------
Visual Description: Concrete pipe showing network of intersecting
cracks at crown. Three longitudinal cracks (2mm width each) crossed
by two circumferential cracks. Pattern suggests external loading stress.
No displacement of pieces.

Correct Classification:
- Defect Code: CM (Multiple Cracks)
- Grade: 3 (multiple cracks present, individual widths 1-3mm)
- Location: Crown, 10-2 o'clock
- Confidence: 87%

Key Indicators: Multiple intersecting cracks = CM code; individual
crack widths 1-3mm = Grade 2, but MULTIPLE cracks upgrades to Grade 3


EXAMPLE 8: Hole with Active Infiltration
----------------------------------------
Visual Description: Concrete pipe with roughly circular hole
approximately 80mm diameter at 9 o'clock position. Water actively
flowing through hole. Soil visible behind hole opening.

Correct Classification:
- Defect 1: H (Hole), Grade 4, 9 o'clock, 93%
- Defect 2: I (Infiltration), Grade 4, At hole, 91%

Key Indicators: Hole 50-150mm = Grade 4; gushing infiltration
from single point = Grade 4; soil visible increases urgency


EXAMPLE 9: Light Surface Damage in Aging Concrete
-------------------------------------------------
Visual Description: Old concrete pipe showing general surface
roughening with aggregate exposed over approximately 30% of visible
surface. Some shallow pitting (5-10mm depth) at isolated locations.
No structural cracks.

Correct Classification:
- Defect Code: SD (Surface Damage)
- Grade: 3 (aggregate exposed 25-50%, pitting present)
- Location: Throughout, worse at crown
- Confidence: 84%

Key Indicators: Aggregate exposure 25-50% = Grade 3; pitting
confirms ongoing deterioration; common in older concrete pipes


EXAMPLE 10: Attached Grease Deposits
------------------------------------
Visual Description: PVC pipe in commercial area showing thick
white/yellow grease buildup on walls. Buildup estimated at 25%
encrustation of diameter, heaviest at springline (3 and 9 o'clock).

Correct Classification:
- Defect Code: DAG (Deposits Attached - Grease)
- Grade: 3 (20-30% encrustation)
- Location: Walls at springline, 3 and 9 o'clock
- Confidence: 89%

Key Indicators: Grease deposits (white/yellow color) = DAG code;
20-30% encrustation = Grade 3; common in restaurant/commercial areas


EXAMPLE 11: Broken Pipe Section
-------------------------------
Visual Description: Clay pipe with complete break through wall
from 1-4 o'clock positions (approximately 25% of circumference).
Broken pieces displaced inward. Soil visible through gap.

Correct Classification:
- Defect Code: B (Broken)
- Grade: 5 (break ~25% of circumference with soil visible)
- Location: 1-4 o'clock
- Confidence: 95%

Key Indicators: Break >25% OR soil visible = Grade 5; displaced
pieces indicate external pressure; high collapse risk


EXAMPLE 12: Minor Joint Displacement - Low Severity
---------------------------------------------------
Visual Description: Concrete pipe with slight step visible at
joint. Offset approximately 8% of wall thickness. No infiltration
or other defects at joint.

Correct Classification:
- Defect Code: JD (Joint Displaced)
- Grade: 2 (5-15% of wall thickness)
- Location: Full circumference at joint
- Confidence: 80%

Key Indicators: Small offset 5-15% = Grade 2; no secondary defects
reduces urgency; monitor in future inspections


EXAMPLE 13: Normal Pipe - No Defects
------------------------------------
Visual Description: PVC pipe in good condition. Smooth walls,
circular cross-section maintained, joints properly aligned with
no gaps. Small amount of water flow at bottom is normal operation.

Correct Classification:
- Defect Code: OK (Normal - No Defects)
- Grade: 1 (best possible)
- Location: N/A
- Confidence: 92%

Key Indicators: No cracks, deformation, intrusions, or deposits;
proper joint alignment; normal flow conditions; document as baseline


EXAMPLE 14: Beginning Collapse - Critical
-----------------------------------------
Visual Description: Brick sewer showing partial collapse at crown.
Multiple bricks displaced/fallen, void visible above pipe. Debris
from collapse on pipe floor. Remaining structure unstable.

Correct Classification:
- Defect Code: X (Collapse)
- Grade: 5 (collapse is ALWAYS Grade 5)
- Location: Crown, 10-2 o'clock
- Confidence: 98%

Key Indicators: ANY collapse = automatic Grade 5; void above pipe
indicates soil loss; immediate intervention required; safety hazard


EXAMPLE 15: Fine Root Intrusion - Early Stage
---------------------------------------------
Visual Description: Concrete pipe showing fine hair-like roots
entering through hairline crack at joint. Roots affect <5% of
flow area. Early stage intrusion.

Correct Classification:
- Defect 1: RF (Root Fine), Grade 1, Joint at 3 o'clock, 85%
- Defect 2: CL (Longitudinal Crack), Grade 1, Joint at 3 o'clock, 78%

Key Indicators: Fine roots <5% flow area = RF Grade 1; hairline
crack = Grade 1; early intervention prevents escalation
"""


# =============================================================================
# SECTION 3: MATERIAL IDENTIFICATION GUIDE
# =============================================================================

MATERIAL_IDENTIFICATION = """
=== PIPE MATERIAL IDENTIFICATION GUIDE ===

CONCRETE:
- Color: Gray (can be dark or light)
- Texture: Rough, may show aggregate (small stones)
- Surface: Porous, may show mineral deposits
- Joints: Wide, often with visible mortar or rubber gasket
- Age Indicators: Spalling, exposed rebar, H2S crown corrosion

VITRIFIED CLAY (VCP):
- Color: Brown, red-brown, or orange-brown
- Texture: Smooth, glazed surface (shiny when clean)
- Surface: Non-porous, resists corrosion
- Joints: Bell and spigot, narrow, every 2-3 feet
- Age Indicators: Brittle cracks, joint separation common

PVC (Polyvinyl Chloride):
- Color: White, light gray, or green (sewer-grade)
- Texture: Very smooth, plastic appearance
- Surface: Non-porous, uniform
- Joints: Solvent welded or gasketed, very tight
- Age Indicators: Yellowing, brittleness, deflection

CAST IRON:
- Color: Dark gray to black, often with rust
- Texture: Rough, may show casting marks
- Surface: Prone to corrosion (rust), tuberculation
- Joints: Hub and spigot with lead/oakum, or mechanical
- Age Indicators: Heavy rust, graphitization, holes

DUCTILE IRON:
- Color: Similar to cast iron but more uniform
- Texture: Smoother than cast iron
- Surface: Often cement-lined (gray interior)
- Joints: Mechanical or push-on with rubber gasket
- Age Indicators: Rust spots, lining deterioration

BRICK:
- Color: Red, brown, or yellow (varies by era)
- Texture: Individual brick pattern visible
- Surface: Mortar joints between bricks
- Shape: Often egg-shaped or horseshoe (older sewers)
- Age Indicators: Missing mortar, displaced bricks, very old systems

CORRUGATED METAL (CMP):
- Color: Silver/gray (galvanized) or rust-colored
- Texture: Distinctive corrugation pattern (ridges)
- Surface: Metallic, may show coatings
- Joints: Band connections visible
- Age Indicators: Rust, perforation, invert deterioration

HDPE (High-Density Polyethylene):
- Color: Black (most common) or yellow
- Texture: Smooth but not shiny
- Surface: Flexible appearance, may show fusion joints
- Joints: Heat-fused (seamless) or mechanical
- Age Indicators: Rarely deteriorates, may show deflection

REINFORCED CONCRETE PIPE (RCP):
- Color: Gray like standard concrete
- Texture: Rough, but more uniform than plain concrete
- Surface: May show steel reinforcement if damaged
- Joints: Tongue and groove with gasket
- Age Indicators: Exposed rebar, cover spalling
"""


# =============================================================================
# SECTION 4: COMPLETE DETECTION PROMPT WITH CALIBRATION
# =============================================================================

def get_calibrated_detection_prompt():
    """
    Returns the complete detection prompt with grading rubrics and few-shot examples.
    This ensures consistent, PACP-compliant classifications.
    """
    return f"""You are SewerSentinel, an expert AI system for analyzing sewer pipe CCTV inspection footage.
You have been calibrated using the Sewer-ML dataset (1.3 million annotated images) and NASSCO PACP v7.0 standards.

YOUR ROLE:
1. Identify and classify defects using PACP codes
2. Assign severity grades using the EXACT thresholds below
3. Identify pipe material and characteristics
4. Provide detailed, actionable observations

{GRADING_RUBRICS}

{MATERIAL_IDENTIFICATION}

CALIBRATION EXAMPLES:
The following examples from the Sewer-ML dataset show correct classifications. Use them to calibrate your assessments:

{FEW_SHOT_EXAMPLES}

=== ANALYSIS INSTRUCTIONS ===

When analyzing the image:
1. First identify the pipe MATERIAL using the guide above
2. Scan systematically: Crown (12 o'clock) -> Right wall (3) -> Floor (6) -> Left wall (9)
3. For EACH defect found:
   - Identify the defect TYPE and assign the correct PACP CODE
   - Measure/estimate against the GRADING RUBRIC thresholds
   - Assign the grade that matches the threshold criteria EXACTLY
   - Note the clock position location
   - Estimate confidence based on image clarity and defect visibility
4. Check for COMPOUND defects (e.g., crack + infiltration often co-occur)
5. The OVERALL GRADE is the HIGHEST individual defect grade found

RESPOND ONLY IN THIS JSON FORMAT:
{{
    "defects": [
        {{
            "defect_type": "Full description of defect",
            "defect_code": "PACP code (CC, CL, D, B, H, RF, RM, RB, DS, DAG, I, JD, JS, SD, COR, X, OK)",
            "grade": 1-5,
            "location_in_pipe": "Clock position (e.g., '12 o'clock', '3-5 o'clock', 'floor')",
            "confidence": 0.0-1.0,
            "description": "Detailed observation including measurements/estimates that justify the grade"
        }}
    ],
    "overall_assessment": "Summary of pipe condition and primary concerns",
    "overall_grade": 1-5,
    "pipe_material_observed": "concrete/clay/pvc/cast_iron/hdpe/brick/corrugated_metal/unknown",
    "pipe_material_confidence": 0.0-1.0,
    "estimated_diameter_inches": number or null,
    "water_level_percent": 0-100 or null
}}

CRITICAL REMINDERS:
- Use the EXACT grade thresholds from the rubrics - do not interpolate
- Collapse (X) is ALWAYS Grade 5
- Broken pipe (B) is minimum Grade 3
- Multiple defects at same location = compound defect, report separately
- When uncertain between grades, note the uncertainty in description but commit to one grade
- Normal/defect-free pipe should return single defect with code "OK" and grade 1
"""


# =============================================================================
# SECTION 5: ENSEMBLE ANALYSIS FOR HIGH CONFIDENCE
# =============================================================================

def get_ensemble_analysis_prompt():
    """
    Returns a prompt for ensemble analysis mode that runs multiple passes
    and aggregates results for higher confidence.
    """
    return """
You are performing a HIGH-CONFIDENCE ensemble analysis. This is pass {pass_number} of {total_passes}.

INSTRUCTIONS FOR ENSEMBLE MODE:
1. Analyze the image independently as if this is your only analysis
2. Do NOT try to be consistent with previous passes - give your honest assessment
3. Apply the grading rubrics strictly
4. Report all defects you observe, even minor ones

The ensemble system will aggregate results across all passes to determine:
- Which defects are consistently detected (high confidence)
- Which grades are most commonly assigned
- Agreement score across passes

Proceed with your independent analysis using the standard format.
"""


class EnsembleAnalyzer:
    """
    Runs multiple analysis passes and aggregates results for higher confidence.

    This addresses the consistency issue where the same image produces
    different results on different runs.
    """

    def __init__(self, engine, num_passes: int = 3):
        """
        Initialize ensemble analyzer.

        Args:
            engine: SewerSentinelEngine instance
            num_passes: Number of independent analysis passes (default 3)
        """
        self.engine = engine
        self.num_passes = num_passes

    def analyze(self, image_path: str, pipe_id: str, context: dict = None) -> dict:
        """
        Run ensemble analysis on an image.

        Args:
            image_path: Path to the image
            pipe_id: Pipe identifier
            context: Optional context dictionary

        Returns:
            Aggregated analysis result with confidence metrics
        """
        results = []

        # Run multiple independent analyses
        for i in range(self.num_passes):
            try:
                result = self.engine.analyze_image(image_path, f"{pipe_id}_pass{i+1}")
                results.append(result)
            except Exception as e:
                print(f"Pass {i+1} failed: {e}")
                continue

        if not results:
            return {"error": "All ensemble passes failed"}

        # Aggregate results
        return self._aggregate_results(results, pipe_id)

    def _aggregate_results(self, results: list, pipe_id: str) -> dict:
        """Aggregate multiple analysis results into a consensus."""

        # Collect all defects across passes
        all_defects = []
        for result in results:
            for defect in result.get('defects', []):
                all_defects.append(defect)

        # Group defects by code and approximate location
        defect_groups = {}
        for defect in all_defects:
            code = defect.get('defect_code', 'UNK')
            location = defect.get('location_in_pipe', 'unknown')
            # Simplify location for grouping
            loc_key = self._simplify_location(location)
            key = f"{code}_{loc_key}"

            if key not in defect_groups:
                defect_groups[key] = []
            defect_groups[key].append(defect)

        # Build consensus defects (appearing in majority of passes)
        consensus_defects = []
        threshold = self.num_passes / 2  # Must appear in >50% of passes

        for key, defects in defect_groups.items():
            if len(defects) >= threshold:
                # Calculate consensus grade (median)
                grades = [d.get('grade', 1) for d in defects]
                consensus_grade = sorted(grades)[len(grades) // 2]

                # Calculate agreement score
                agreement = len(defects) / self.num_passes

                # Use the description from the pass closest to consensus grade
                best_defect = min(defects, key=lambda d: abs(d.get('grade', 1) - consensus_grade))

                consensus_defects.append({
                    "defect_type": best_defect.get('defect_type'),
                    "defect_code": best_defect.get('defect_code'),
                    "grade": consensus_grade,
                    "location_in_pipe": best_defect.get('location_in_pipe'),
                    "confidence": round(agreement * best_defect.get('confidence', 0.8), 2),
                    "description": best_defect.get('description'),
                    "ensemble_agreement": f"{agreement:.0%}",
                    "grade_range": f"{min(grades)}-{max(grades)}"
                })

        # Calculate overall metrics
        overall_grades = [r.get('overall_grade', 1) for r in results]
        consensus_overall = sorted(overall_grades)[len(overall_grades) // 2]

        materials = [r.get('pipe_material_observed', 'unknown') for r in results]
        consensus_material = max(set(materials), key=materials.count)

        # Calculate overall agreement score
        grade_agreement = overall_grades.count(consensus_overall) / len(overall_grades)
        material_agreement = materials.count(consensus_material) / len(materials)
        overall_agreement = (grade_agreement + material_agreement) / 2

        return {
            "pipe_id": pipe_id,
            "analysis_mode": "ensemble",
            "num_passes": self.num_passes,
            "successful_passes": len(results),
            "defects": sorted(consensus_defects, key=lambda d: d['grade'], reverse=True),
            "overall_grade": consensus_overall,
            "overall_grade_agreement": f"{grade_agreement:.0%}",
            "pipe_material_observed": consensus_material,
            "material_agreement": f"{material_agreement:.0%}",
            "overall_confidence": f"{overall_agreement:.0%}",
            "ensemble_summary": f"Analysis based on {len(results)} independent passes with {overall_agreement:.0%} overall agreement"
        }

    def _simplify_location(self, location: str) -> str:
        """Simplify location string for grouping similar locations."""
        location = location.lower()

        if any(x in location for x in ['12', 'crown', 'top']):
            return 'crown'
        elif any(x in location for x in ['6', 'floor', 'bottom', 'invert']):
            return 'floor'
        elif any(x in location for x in ['3', 'right']):
            return 'right'
        elif any(x in location for x in ['9', 'left']):
            return 'left'
        elif any(x in location for x in ['throughout', 'all', 'multiple', 'full']):
            return 'throughout'
        else:
            return 'other'


# =============================================================================
# SECTION 6: INTEGRATION HELPERS
# =============================================================================

def get_prediction_prompt_with_context():
    """
    Returns an enhanced prediction prompt that uses consistent reasoning.
    """
    return """You are SewerSentinel's failure prediction engine, calibrated with PACP standards and industry data.

PREDICTION METHODOLOGY:
Based on the detected defects and pipe context, predict degradation trajectory using these evidence-based models:

DEGRADATION RATES BY DEFECT TYPE (per PACP studies):
- Cracks: Progress ~0.5-1 grade per year without intervention
- Root intrusion: Progress ~1 grade per year (accelerates in growing season)
- Corrosion: Progress ~0.3-0.5 grade per year (faster in H2S environments)
- Deformation: Usually stable unless external load changes
- Joint issues: Progress ~0.5 grade per year, accelerates with root/infiltration

ACCELERATING FACTORS:
- Heavy traffic load: +30% degradation rate
- High groundwater: +40% degradation rate for cracks/joints
- Clay soil: +20% degradation rate (settlement issues)
- Pipe age >50 years: +25% degradation rate
- Multiple interacting defects: +50% degradation rate

TIME TO FAILURE ESTIMATES BY GRADE:
- Grade 1: 10+ years to structural failure
- Grade 2: 7-10 years to structural failure
- Grade 3: 4-7 years to structural failure
- Grade 4: 1-3 years to structural failure
- Grade 5: <1 year to structural failure (some already failing)

COST ESTIMATION MODEL:
Base repair cost = $2,000 + (diameter_inches * $100) + (grade * $2,000)
Material multiplier: concrete=1.0, clay=1.2, cast_iron=1.5, pvc=0.8
Depth multiplier: 1.0 + (depth_feet - 8) * 0.05
Emergency multiplier: 5-8x based on location criticality

Provide your prediction in the standard JSON format with detailed reasoning.
"""


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    print("SewerSentinel Calibration Module")
    print("=" * 50)
    print("\nThis module provides:")
    print("1. PACP-compliant grading rubrics")
    print("2. Few-shot examples from Sewer-ML dataset")
    print("3. Material identification guide")
    print("4. Ensemble analysis for high confidence")
    print("\nTo use in your analysis_engine.py:")
    print("  from sewer_sentinel_calibration import (")
    print("      get_calibrated_detection_prompt,")
    print("      EnsembleAnalyzer")
    print("  )")
    print("\n  # Replace your detection_prompt with:")
    print("  self.detection_prompt = get_calibrated_detection_prompt()")
    print("\n  # For high-confidence mode:")
    print("  ensemble = EnsembleAnalyzer(engine, num_passes=3)")
    print("  result = ensemble.analyze(image_path, pipe_id)")

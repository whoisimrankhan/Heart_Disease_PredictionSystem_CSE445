import os
import json
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from openai import AzureOpenAI

# Load environment variables
load_dotenv()

# Initialize Azure OpenAI client
client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

# Get deployment name
DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

# Mapping dictionaries based on feature_enginnering.md
SEX_MAP = {0: "female", 1: "male"}
CHEST_PAIN_MAP = {0: "typical angina", 1: "atypical angina", 2: "non-anginal pain", 3: "asymptomatic"}
FASTING_BLOOD_SUGAR_MAP = {0: "normal", 1: "elevated"}
RESTING_ECG_MAP = {0: "normal ECG", 1: "ST-T wave abnormality", 2: "left ventricular hypertrophy"}
EXERCISE_ANGINA_MAP = {0: "No", 1: "Yes"}
ST_SLOPE_MAP = {0: "upsloping", 1: "flat", 2: "downsloping"}
TARGET_MAP = {0: "No heart Disease", 1: "Heart Disease"}

# List of all fields for validation
FIELDS = ["age", "sex", "chest_pain_type", "resting_bp", "cholesterol", 
          "fasting_blood_sugar", "resting_ecg", "max_heart_rate", 
          "exercise_angina", "oldpeak", "ST_slope"]


# =============================================================================
# STEP 2.1: Validation & Correction - Check for missing/contradictions
# =============================================================================
def step2_1_validate_and_correct(free_text, original_row):
    """
    STEP 2.1: Ask LLM to check if the free-text description is missing any 
    important clinical information or contains contradictions compared to 
    the original data. Correct if needed while keeping language natural.
    
    Uses Azure OpenAI.
    """
    # Prepare original values with mappings
    sex = SEX_MAP.get(int(original_row['sex']), str(original_row['sex']))
    chest_pain = CHEST_PAIN_MAP.get(int(original_row['chest pain type']), str(original_row['chest pain type']))
    fbs = FASTING_BLOOD_SUGAR_MAP.get(int(original_row['fasting blood sugar']), str(original_row['fasting blood sugar']))
    ecg = RESTING_ECG_MAP.get(int(original_row['resting ecg']), str(original_row['resting ecg']))
    exercise_angina = EXERCISE_ANGINA_MAP.get(int(original_row['exercise angina']), str(original_row['exercise angina']))
    st_slope = ST_SLOPE_MAP.get(int(original_row['ST slope']), str(original_row['ST slope']))
    
    validation_prompt = f"""
ORIGINAL PATIENT DATA (Ground Truth):
- Age: {original_row['age']} years
- Sex: {sex}
- Chest Pain Type: {chest_pain}
- Resting Blood Pressure: {original_row['resting bp s']} mm Hg
- Serum Cholesterol: {original_row['cholesterol']} mg/dL
- Fasting Blood Sugar: {fbs}
- Resting ECG: {ecg}
- Maximum Heart Rate Achieved: {original_row['max heart rate']} bpm
- Exercise-Induced Angina: {exercise_angina}
- ST Depression (Oldpeak): {original_row['oldpeak']}
- ST Slope at Peak Exercise: {st_slope}

GENERATED FREE-TEXT DESCRIPTION:
{free_text}
"""
    
    try:
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": """You are a medical data validator. Your task is to:

1. COMPARE the generated free-text description with the original patient data
2. CHECK for:
   - Missing clinical information (any value not mentioned in the text)
   - Contradictions (values that don't match the original data)
   - Incorrect medical terminology or values
3. If there are issues, CORRECT the text to accurately reflect ALL original data
4. Keep the corrected text natural, flowing, and medically appropriate

Output format (JSON):
{
    "has_issues": true/false,
    "issues_found": ["list of specific issues found"],
    "corrected_text": "the corrected free-text (or original if no issues)"
}

Return ONLY valid JSON, nothing else."""
                },
                {
                    "role": "user",
                    "content": validation_prompt
                }
            ],
            max_tokens=700,
            temperature=0
        )
        
        result = response.choices[0].message.content.strip()
        # Clean up potential markdown formatting
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        result = result.strip()
        
        return json.loads(result)
    except json.JSONDecodeError as e:
        print(f"  [Step 2.1] JSON parse error: {e}")
        return {"has_issues": False, "issues_found": [], "corrected_text": free_text}
    except Exception as e:
        print(f"  [Step 2.1] Azure OpenAI API error: {e}")
        return {"has_issues": False, "issues_found": [], "corrected_text": free_text}


# =============================================================================
# STEP 2.2: Reverse-Mapping Verification
# =============================================================================
def step2_2_reverse_map(corrected_text):
    """
    STEP 2.2: Given ONLY the corrected free-text description, ask LLM to 
    re-generate the original clinical values. This tests if the text 
    accurately represents the data.
    
    Uses Azure OpenAI.
    """
    try:
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[
                {
                    "role": "system",
                    "content": """You are a medical data extractor. Given ONLY a clinical free-text description, extract the patient's clinical values.

Use these mappings to convert text descriptions to numeric codes:
- sex: female=0, male=1
- chest pain type: typical angina=0, atypical angina=1, non-anginal pain=2, asymptomatic=3
- fasting blood sugar: normal/≤120=0, elevated/>120=1
- resting ecg: normal ECG/normal=0, ST-T wave abnormality=1, left ventricular hypertrophy=2
- exercise angina: No=0, Yes=1
- ST slope: upsloping=0, flat=1, downsloping=2

Extract and return ONLY these values in JSON format:
{
    "age": <number>,
    "sex": <0 or 1>,
    "chest_pain_type": <0-3>,
    "resting_bp": <number>,
    "cholesterol": <number>,
    "fasting_blood_sugar": <0 or 1>,
    "resting_ecg": <0-2>,
    "max_heart_rate": <number>,
    "exercise_angina": <0 or 1>,
    "oldpeak": <number>,
    "ST_slope": <0-2>
}

Return ONLY valid JSON, nothing else."""
                },
                {
                    "role": "user",
                    "content": f"Extract clinical values from this medical report:\n\n{corrected_text}"
                }
            ],
            max_tokens=300,
            temperature=0
        )
        
        result = response.choices[0].message.content.strip()
        # Clean up potential markdown formatting
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        result = result.strip()
        
        return json.loads(result)
    except json.JSONDecodeError as e:
        print(f"  [Step 2.2] JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"  [Step 2.2] Azure OpenAI API error: {e}")
        return None


def compare_values(original_row, regenerated_values):
    """
    Compare original values with regenerated values and calculate consistency score.
    """
    if regenerated_values is None:
        return {"consistency_score": 0, "field_matches": {}, "total_matches": 0, "total_fields": len(FIELDS)}
    
    field_matches = {}
    
    # Map original row keys to our field names
    original_mapping = {
        "age": float(original_row['age']),
        "sex": int(original_row['sex']),
        "chest_pain_type": int(original_row['chest pain type']),
        "resting_bp": float(original_row['resting bp s']),
        "cholesterol": float(original_row['cholesterol']),
        "fasting_blood_sugar": int(original_row['fasting blood sugar']),
        "resting_ecg": int(original_row['resting ecg']),
        "max_heart_rate": float(original_row['max heart rate']),
        "exercise_angina": int(original_row['exercise angina']),
        "oldpeak": float(original_row['oldpeak']),
        "ST_slope": int(original_row['ST slope'])
    }
    
    total_matches = 0
    for field in FIELDS:
        original_val = original_mapping.get(field)
        regen_val = regenerated_values.get(field)
        
        # Handle numeric comparison with tolerance for floats
        if original_val is not None and regen_val is not None:
            if isinstance(original_val, float) and isinstance(regen_val, (int, float)):
                match = abs(float(original_val) - float(regen_val)) < 0.5
            else:
                match = int(original_val) == int(regen_val)
        else:
            match = False
        
        field_matches[field] = {
            "original": original_val,
            "regenerated": regen_val,
            "match": match
        }
        
        if match:
            total_matches += 1
    
    consistency_score = (total_matches / len(FIELDS)) * 100
    
    return {
        "consistency_score": round(consistency_score, 2),
        "field_matches": field_matches,
        "total_matches": total_matches,
        "total_fields": len(FIELDS)
    }


# =============================================================================
# MAIN VALIDATION PIPELINE (PHASE 2)
# =============================================================================
def validate_dataset(input_file, original_data_file, output_prefix="output"):
    """
    Validate the generated Free-Text from Phase 1.
    
    This is Phase 2 of the pipeline:
    - Step 2.1: Check for missing content/contradictions in Free-Text
    - Step 2.2: Reverse-mapping verification
    
    Args:
        input_file: CSV from Phase 1 (heart_disease_freetext_step1_generated.csv)
                    Contains: Feature, Free_Text, Target
        original_data_file: Original dataset (Heart_Disease.csv) for validation comparison
        output_prefix: Prefix for output files
    
    Outputs:
    1. {output_prefix}_final.csv - Final dataset with validated free-text
    2. {output_prefix}_validation_report.csv - Full audit trail
    3. {output_prefix}_validation_summary.txt - Statistics summary
    """
    # Read the Phase 1 output
    print(f"\n{'='*70}")
    print(f"FREE-TEXT VALIDATION PIPELINE (PHASE 2)")
    print(f"Using Azure OpenAI: {DEPLOYMENT_NAME}")
    print(f"{'='*70}")
    
    print(f"\nReading Phase 1 output from: {input_file}")
    phase1_df = pd.read_csv(input_file)
    
    print(f"Reading original data from: {original_data_file}")
    original_df = pd.read_csv(original_data_file)
    
    print(f"Phase 1 dataset shape: {phase1_df.shape}")
    print(f"Original dataset shape: {original_df.shape}")
    
    total_rows = len(phase1_df)
    
    if len(phase1_df) != len(original_df):
        print("WARNING: Row count mismatch between Phase 1 output and original data!")
    
    # =========================================================================
    # PHASE 2: Validation & Verification for Free-Text ONLY
    # =========================================================================
    print(f"\n{'='*70}")
    print("PHASE 2: FREE-TEXT VALIDATION & VERIFICATION")
    print("  - Step 2.1: Check for missing content/contradictions")
    print("  - Step 2.2: Reverse-mapping verification")
    print(f"{'='*70}")
    
    results = []
    for idx in range(total_rows):
        row = original_df.iloc[idx]
        feature_text = phase1_df.iloc[idx]['Feature']
        free_text = phase1_df.iloc[idx]['Free_Text']
        target = phase1_df.iloc[idx]['Target']
        
        print(f"\n[Row {idx + 1}/{total_rows}] Validating Free-Text...")
        
        # Step 2.1: Validate and correct Free-Text
        print(f"  Step 2.1: Checking for missing content/contradictions...")
        validation_result = step2_1_validate_and_correct(free_text, row)
        corrected_free_text = validation_result.get("corrected_text", free_text)
        has_issues = validation_result.get("has_issues", False)
        issues_found = validation_result.get("issues_found", [])
        
        if has_issues:
            print(f"    → Issues found: {len(issues_found)}")
        else:
            print(f"    → No issues found")
        
        # Step 2.2: Reverse-map and compare
        print(f"  Step 2.2: Reverse-mapping for verification...")
        regenerated_values = step2_2_reverse_map(corrected_free_text)
        comparison = compare_values(row, regenerated_values)
        
        print(f"  ✓ Consistency Score: {comparison['consistency_score']}% ({comparison['total_matches']}/{comparison['total_fields']} fields)")
        
        results.append({
            "row_index": idx,
            "feature_text": feature_text,
            "original_free_text": free_text,
            "has_issues": has_issues,
            "issues_found": issues_found,
            "corrected_free_text": corrected_free_text,
            "regenerated_values": regenerated_values,
            "comparison": comparison,
            "target": target
        })
    
    print(f"\n{'='*70}")
    print(f"✓ PHASE 2 COMPLETE: Validated {total_rows} rows")
    print(f"{'='*70}")
    
    # ==========================================================================
    # Generate Output 1: final.csv (Feature + Validated Free_Text + Target + Score)
    # ==========================================================================
    final_data = []
    for r in results:
        final_data.append({
            "Feature": r["feature_text"],
            "Free_Text": r["corrected_free_text"],
            "Target": r["target"],
            "consistency_score": r["comparison"]["consistency_score"]
        })
    
    final_df = pd.DataFrame(final_data)
    final_file = f"{output_prefix}_final.csv"
    final_df.to_csv(final_file, index=False)
    print(f"\n✓ Final dataset saved: {final_file}")
    
    # ==========================================================================
    # Generate Output 2: validation_report.csv
    # ==========================================================================
    report_data = []
    for r in results:
        field_details = []
        if r["comparison"]["field_matches"]:
            for field, data in r["comparison"]["field_matches"].items():
                field_details.append(f"{field}: orig={data['original']}, regen={data['regenerated']}, match={data['match']}")
        
        report_data.append({
            "row_index": r["row_index"],
            "feature_text": r["feature_text"],
            "original_free_text": r["original_free_text"],
            "had_issues": r["has_issues"],
            "issues_found": "; ".join(r["issues_found"]) if r["issues_found"] else "None",
            "corrected_free_text": r["corrected_free_text"],
            "regenerated_values": json.dumps(r["regenerated_values"]) if r["regenerated_values"] else "Failed",
            "consistency_score": r["comparison"]["consistency_score"],
            "matches": f"{r['comparison']['total_matches']}/{r['comparison']['total_fields']}",
            "field_details": " | ".join(field_details),
            "target": r["target"]
        })
    
    report_df = pd.DataFrame(report_data)
    report_file = f"{output_prefix}_validation_report.csv"
    report_df.to_csv(report_file, index=False)
    print(f"✓ Validation report saved: {report_file}")
    
    # ==========================================================================
    # Generate Output 3: validation_summary.txt
    # ==========================================================================
    scores = [r["comparison"]["consistency_score"] for r in results]
    avg_score = sum(scores) / len(scores) if scores else 0
    perfect_matches = sum(1 for s in scores if s == 100)
    high_consistency = sum(1 for s in scores if s >= 90)
    low_consistency = sum(1 for s in scores if s < 90)
    issues_count = sum(1 for r in results if r["has_issues"])
    
    # Calculate per-field accuracy
    field_accuracy = {field: 0 for field in FIELDS}
    for r in results:
        if r["comparison"]["field_matches"]:
            for field, data in r["comparison"]["field_matches"].items():
                if data["match"]:
                    field_accuracy[field] += 1
    
    for field in field_accuracy:
        field_accuracy[field] = round((field_accuracy[field] / total_rows) * 100, 2)
    
    summary_content = f"""
================================================================================
FREE-TEXT VALIDATION SUMMARY REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================================================

INPUT FILES:
- Phase 1 Output: {input_file}
- Original Data:  {original_data_file}

TOTAL ROWS PROCESSED: {total_rows}

LLM USED: Azure OpenAI ({DEPLOYMENT_NAME})

================================================================================
PHASE 2: FREE-TEXT VALIDATION RESULTS
================================================================================

STEP 2.1 - Missing Content/Contradiction Check:
-----------------------------------------------
Rows with issues found:    {issues_count} ({(issues_count/total_rows)*100:.1f}%)
Rows without issues:       {total_rows - issues_count} ({((total_rows-issues_count)/total_rows)*100:.1f}%)

STEP 2.2 - Reverse-Mapping Consistency:
-----------------------------------------------
Average Consistency Score: {avg_score:.2f}%
Perfect Matches (100%):    {perfect_matches} rows ({(perfect_matches/total_rows)*100:.1f}%)
High Consistency (>=90%):  {high_consistency} rows ({(high_consistency/total_rows)*100:.1f}%)
Low Consistency (<90%):    {low_consistency} rows ({(low_consistency/total_rows)*100:.1f}%)

--------------------------------------------------------------------------------
PER-FIELD ACCURACY (Reverse-Mapping Verification)
--------------------------------------------------------------------------------
"""
    
    for field, accuracy in sorted(field_accuracy.items(), key=lambda x: x[1], reverse=True):
        bar_filled = int(accuracy / 5)
        bar_empty = 20 - bar_filled
        bar = "=" * bar_filled + "-" * bar_empty
        summary_content += f"{field:20s}: [{bar}] {accuracy:6.2f}%\n"
    
    summary_content += f"""
--------------------------------------------------------------------------------
CONSISTENCY SCORE DISTRIBUTION
--------------------------------------------------------------------------------
100%:     {"#" * min(perfect_matches, 50)} ({perfect_matches})
90-99%:   {"#" * min(high_consistency - perfect_matches, 50)} ({high_consistency - perfect_matches})
<90%:     {"#" * min(low_consistency, 50)} ({low_consistency})

--------------------------------------------------------------------------------
INTERPRETATION
--------------------------------------------------------------------------------
"""
    
    if avg_score >= 95:
        summary_content += "EXCELLENT: The free-text generation is highly reliable.\n"
        summary_content += "   The generated narratives accurately reflect the original clinical data.\n"
    elif avg_score >= 90:
        summary_content += "GOOD: The free-text generation is reliable.\n"
        summary_content += "   Minor discrepancies exist but overall quality is acceptable.\n"
    elif avg_score >= 80:
        summary_content += "FAIR: The free-text generation needs improvement.\n"
        summary_content += "   Review low-scoring rows and consider prompt refinement.\n"
    else:
        summary_content += "POOR: The free-text generation requires significant improvement.\n"
        summary_content += "   Many rows have inconsistencies. Review and refine the approach.\n"
    
    summary_content += f"""
================================================================================
OUTPUT FILES GENERATED
================================================================================
1. {output_prefix}_final.csv              - Final dataset with validated free-text
2. {output_prefix}_validation_report.csv  - Full audit trail for each row
3. {output_prefix}_validation_summary.txt - This summary report

================================================================================
"""
    
    summary_file = f"{output_prefix}_validation_summary.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(summary_content)
    print(f"✓ Validation summary saved: {summary_file}")
    
    # Print summary to console
    print(f"\n{'='*70}")
    print("VALIDATION COMPLETE - SUMMARY")
    print(f"{'='*70}")
    print(f"Total rows processed: {total_rows}")
    print(f"Rows with issues in Step 2.1: {issues_count} ({(issues_count/total_rows)*100:.1f}%)")
    print(f"Average consistency score: {avg_score:.2f}%")
    print(f"Perfect matches (100%): {perfect_matches} ({(perfect_matches/total_rows)*100:.1f}%)")
    print(f"High consistency (>=90%): {high_consistency} ({(high_consistency/total_rows)*100:.1f}%)")
    
    return final_df, report_df


def main():
    # File paths
    phase1_output = "heart_disease_freetext_step1_generated.csv"  # Output from transform_dataset_freetext.py
    original_data = "Heart_Disease.csv"
    output_prefix = "heart_disease_freetext"
    
    # Run the validation pipeline
    final_df, report_df = validate_dataset(phase1_output, original_data, output_prefix)
    
    print("\n✅ Validation complete!")


if __name__ == "__main__":
    main()

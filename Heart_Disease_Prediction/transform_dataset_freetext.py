import os
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Mapping dictionaries based on feature_enginnering.md
SEX_MAP = {0: "female", 1: "male"}
CHEST_PAIN_MAP = {0: "typical angina", 1: "atypical angina", 2: "non-anginal pain", 3: "asymptomatic"}
FASTING_BLOOD_SUGAR_MAP = {0: "normal", 1: "elevated"}
RESTING_ECG_MAP = {0: "normal ECG", 1: "ST-T wave abnormality", 2: "left ventricular hypertrophy"}
EXERCISE_ANGINA_MAP = {0: "No", 1: "Yes"}
ST_SLOPE_MAP = {0: "upsloping", 1: "flat", 2: "downsloping"}
TARGET_MAP = {0: "No heart Disease", 1: "Heart Disease"}


def transform_row_to_feature_text(row):
    """
    Transform a single row of data into structured feature text (fallback/manual).
    """
    feature_parts = [
        f"age-{int(row['age'])}",
        f"sex-{SEX_MAP.get(int(row['sex']), row['sex'])}",
        f"chest pain type-{CHEST_PAIN_MAP.get(int(row['chest pain type']), row['chest pain type'])}",
        f"resting bp-{int(row['resting bp s'])}mm Hg",
        f"cholesterol-{int(row['cholesterol'])} mg/dL",
        f"fasting blood sugar-{FASTING_BLOOD_SUGAR_MAP.get(int(row['fasting blood sugar']), row['fasting blood sugar'])}",
        f"resting ecg-{RESTING_ECG_MAP.get(int(row['resting ecg']), row['resting ecg'])}",
        f"Maximum Heart Rate-{int(row['max heart rate'])}",
        f"Exercise Angina-{EXERCISE_ANGINA_MAP.get(int(row['exercise angina']), row['exercise angina'])}",
        f"oldpeak-{row['oldpeak']}",
        f"ST slope-{ST_SLOPE_MAP.get(int(row['ST slope']), row['ST slope'])}"
    ]
    return ", ".join(feature_parts)


def transform_target(target_value):
    """Transform target value to human-readable text."""
    return TARGET_MAP.get(int(target_value), str(target_value))


# =============================================================================
# STEP 1A: Generate Feature (Structured Clinical Data) using LLM
# =============================================================================
def step1_generate_feature_text(row_data):
    """
    STEP 1A: Use GPT-4o to transform raw row data into structured feature text.
    """
    raw_data = f"""
    age: {row_data['age']}
    sex: {row_data['sex']}
    chest pain type: {row_data['chest pain type']}
    resting bp s: {row_data['resting bp s']}
    cholesterol: {row_data['cholesterol']}
    fasting blood sugar: {row_data['fasting blood sugar']}
    resting ecg: {row_data['resting ecg']}
    max heart rate: {row_data['max heart rate']}
    exercise angina: {row_data['exercise angina']}
    oldpeak: {row_data['oldpeak']}
    ST slope: {row_data['ST slope']}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """You are a medical data transformer. Convert the given patient data into a descriptive text format.

Use these mappings:
- sex: 0=female, 1=male
- chest pain type: 0=typical angina, 1=atypical angina, 2=non-anginal pain, 3=asymptomatic
- fasting blood sugar: 0=normal, 1=elevated
- resting ecg: 0=normal ECG, 1=ST-T wave abnormality, 2=left ventricular hypertrophy
- exercise angina: 0=No, 1=Yes
- ST slope: 0=upsloping, 1=flat, 2=downsloping

Output format (single line, comma-separated):
age-[value], sex-[mapped], chest pain type-[mapped], resting bp-[value]mm Hg, cholesterol-[value] mg/dL, fasting blood sugar-[mapped], resting ecg-[mapped], Maximum Heart Rate-[value], Exercise Angina-[mapped], oldpeak-[value], ST slope-[mapped]

Return ONLY the formatted text, nothing else."""
                },
                {
                    "role": "user",
                    "content": raw_data
                }
            ],
            max_tokens=300,
            temperature=0
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"  [Step 1A] OpenAI API error: {e}")
        return transform_row_to_feature_text(row_data)


# =============================================================================
# STEP 1B: Generate Free-Text (Medical Report Style) using LLM
# =============================================================================
def step1_generate_free_text(row_data):
    """
    STEP 1B: Use GPT-4o to generate a natural language medical report style
    free-text description from raw patient data.
    """
    # Prepare mapped values for the prompt
    sex = SEX_MAP.get(int(row_data['sex']), str(row_data['sex']))
    chest_pain = CHEST_PAIN_MAP.get(int(row_data['chest pain type']), str(row_data['chest pain type']))
    fbs = FASTING_BLOOD_SUGAR_MAP.get(int(row_data['fasting blood sugar']), str(row_data['fasting blood sugar']))
    ecg = RESTING_ECG_MAP.get(int(row_data['resting ecg']), str(row_data['resting ecg']))
    exercise_angina = EXERCISE_ANGINA_MAP.get(int(row_data['exercise angina']), str(row_data['exercise angina']))
    st_slope = ST_SLOPE_MAP.get(int(row_data['ST slope']), str(row_data['ST slope']))
    
    patient_data = f"""
Patient Clinical Data:
- Age: {row_data['age']} years
- Sex: {sex}
- Chest Pain Type: {chest_pain}
- Resting Blood Pressure: {row_data['resting bp s']} mm Hg
- Serum Cholesterol: {row_data['cholesterol']} mg/dL
- Fasting Blood Sugar: {fbs} (≤120 mg/dL is normal)
- Resting ECG: {ecg}
- Maximum Heart Rate Achieved: {row_data['max heart rate']} bpm
- Exercise-Induced Angina: {exercise_angina}
- ST Depression (Oldpeak): {row_data['oldpeak']}
- ST Slope at Peak Exercise: {st_slope}
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": """You are a medical professional writing a clinical report. Generate a natural, flowing free-text medical report based on the patient's clinical data.

Guidelines:
1. Write in MEDICAL REPORT style (third person, professional tone)
2. Include ALL clinical values naturally in the narrative
3. Use proper medical terminology
4. Make it read like a real clinical EHR note
5. Include observations about risk factors where appropriate
6. Keep it to 1-2 paragraphs (150-250 words)

Example style:
"The patient is a 54-year-old male who presented for cardiac evaluation. Clinical examination revealed a resting blood pressure of 140 mm Hg and serum cholesterol level of 239 mg/dL, both of which are elevated and represent cardiovascular risk factors. The patient reported experiencing atypical angina-type chest pain. Fasting blood sugar was within normal limits (≤120 mg/dL). Resting electrocardiogram showed normal results. During stress testing, the patient achieved a maximum heart rate of 160 bpm and did not experience exercise-induced angina. ST segment analysis revealed an oldpeak depression of 1.2 with a flat slope pattern at peak exercise, which may warrant further evaluation for potential ischemic changes."

Return ONLY the free-text narrative, nothing else."""
                },
                {
                    "role": "user",
                    "content": patient_data
                }
            ],
            max_tokens=500,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"  [Step 1B] OpenAI API error: {e}")
        return f"Medical report generation failed for this patient. Raw data: Age {row_data['age']}, Sex {sex}."


# =============================================================================
# MAIN PIPELINE - PHASE 1 ONLY (Text Generation)
# =============================================================================
def transform_dataset(input_file, output_prefix="output"):
    """
    Transform the entire dataset - PHASE 1 ONLY.
    
    Generates:
    - Structured Feature text (LLM generated - GPT-4o)
    - Free-text narrative (LLM generated - GPT-4o)
    
    Output:
    - {output_prefix}_step1_generated.csv - Feature + Free_Text + Target
    
    NOTE: Run validation.py separately for Phase 2 (validation & verification)
    """
    # Read the original dataset
    print(f"\n{'='*70}")
    print(f"HEART DISEASE DATA TRANSFORMATION PIPELINE")
    print(f"PHASE 1: SYNTHETIC TEXT GENERATION")
    print(f"{'='*70}")
    print(f"\nReading dataset from: {input_file}")
    df = pd.read_csv(input_file)
    
    print(f"Original dataset shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    
    total_rows = len(df)
    
    # =========================================================================
    # PHASE 1: Generate Feature (structured) + Free-Text for ALL rows
    # =========================================================================
    print(f"\n{'='*70}")
    print("GENERATING SYNTHETIC TEXT:")
    print("  - Feature: Structured clinical data (GPT-4o)")
    print("  - Free_Text: Medical report narrative (GPT-4o)")
    print(f"{'='*70}")
    
    generated_data = []
    for idx, row in df.iterrows():
        print(f"\n[Row {idx + 1}/{total_rows}] Generating texts...")
        
        # Generate structured Feature using LLM
        print(f"  → Generating structured Feature (LLM)...")
        feature_text = step1_generate_feature_text(row)
        
        # Generate Free-Text narrative (LLM)
        print(f"  → Generating Free-Text narrative (LLM)...")
        free_text = step1_generate_free_text(row)
        
        # Get target
        target = transform_target(row['target'])
        
        generated_data.append({
            "Feature": feature_text,
            "Free_Text": free_text,
            "Target": target
        })
        
        print(f"  ✓ Done")
    
    print(f"\n{'='*70}")
    print(f"✓ PHASE 1 COMPLETE: Generated texts for {total_rows} rows")
    print(f"{'='*70}")
    
    # =========================================================================
    # Save output
    # =========================================================================
    output_df = pd.DataFrame(generated_data)
    output_file = f"{output_prefix}_step1_generated.csv"
    output_df.to_csv(output_file, index=False)
    
    print(f"\n✓ Output saved: {output_file}")
    print(f"\n{'='*70}")
    print("PHASE 1 SUMMARY")
    print(f"{'='*70}")
    print(f"Total rows processed: {total_rows}")
    print(f"Feature (structured): Generated for all {total_rows} rows (GPT-4o)")
    print(f"Free_Text (narrative): Generated for all {total_rows} rows (GPT-4o)")
    print(f"\nOutput file: {output_file}")
    print(f"\n{'='*70}")
    print("NEXT STEP:")
    print("  Run validation.py to perform Phase 2 (validation & verification)")
    print("  Command: python validation.py")
    print(f"{'='*70}")
    
    return output_df


def main():
    # File paths
    input_file = "Heart_Disease.csv"
    output_prefix = "heart_disease_freetext"
    
    # Run Phase 1 (text generation only)
    output_df = transform_dataset(input_file, output_prefix)
    
    print("\n✅ Phase 1 complete! Run validation.py for Phase 2.")


if __name__ == "__main__":
    main()

# Validation Pipeline Documentation

## Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Data Flow](#data-flow)
- [Pipeline Stages](#pipeline-stages)
- [Code Structure](#code-structure)
- [Examples](#examples)
- [Output Files](#output-files)
- [Quality Metrics](#quality-metrics)

---

## Overview

### Purpose
The validation pipeline (`validation.py`) is **Phase 2** of a two-phase medical AI dataset generation system. It validates AI-generated free-text clinical narratives to ensure they accurately and completely represent the original structured heart disease patient data.

### Problem It Solves
When converting structured clinical data to natural language descriptions:
- **Missing Information**: AI might omit critical clinical values
- **Contradictions**: Generated text might conflict with source data
- **Ambiguity**: Text might not be precise enough to reconstruct original values

### Solution Approach
Two-step validation using Azure OpenAI:
1. **Forward Validation**: Compare text against original data
2. **Reverse Validation**: Reconstruct data from text (bidirectional consistency)

---

## Architecture

### High-Level System Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         COMPLETE PIPELINE                        │
└─────────────────────────────────────────────────────────────────┘

PHASE 1: Generation (transform_dataset_freetext.py)
┌──────────────────┐
│ Heart_Disease.csv│  ←── Original structured data
│ (Structured Data)│
└────────┬─────────┘
         │
         ▼
    ┌────────┐
    │   LLM  │  ←── Generate free-text descriptions
    └────┬───┘
         │
         ▼
┌─────────────────────────────────────────┐
│ heart_disease_freetext_step1_generated  │
│ [Feature | Free_Text | Target]          │
└──────────────────┬──────────────────────┘
                   │
                   │
═══════════════════╪═══════════════════════════════════════════
PHASE 2: VALIDATION (validation.py) ← YOU ARE HERE
═══════════════════╪═══════════════════════════════════════════
                   │
                   ▼
         ┌─────────────────────┐
         │   Step 2.1 Check    │
         │  Missing Content &  │
         │   Contradictions    │
         └──────────┬──────────┘
                    │
                    ▼
              ┌──────────┐
              │   LLM    │  Compare text vs original data
              └─────┬────┘
                    │
                    ▼
         ┌──────────────────────┐
         │  Corrected Free-Text │
         └──────────┬───────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  Step 2.2 Reverse   │
         │  Mapping Verification│
         └──────────┬──────────┘
                    │
                    ▼
              ┌──────────┐
              │   LLM    │  Extract values from text only
              └─────┬────┘
                    │
                    ▼
         ┌──────────────────────┐
         │ Regenerated Values   │
         └──────────┬───────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │ Consistency Scoring  │
         │  (Field Comparison)  │
         └──────────┬───────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│              OUTPUT FILES               │
├─────────────────────────────────────────┤
│ 1. final.csv                            │
│ 2. validation_report.csv                │
│ 3. validation_summary.txt               │
└─────────────────────────────────────────┘
```

---

## Data Flow

### Input Data Structure

#### Input 1: Phase 1 Output (`heart_disease_freetext_step1_generated.csv`)
```
┌─────────────────────────────────────────────────────────────────┐
│ Feature                  │ Free_Text               │ Target     │
├──────────────────────────┼─────────────────────────┼────────────┤
│ 45,1,3,110,264,0,0,132...│ A 45-year-old male...   │ 1          │
│ 52,0,2,125,212,1,1,168...│ A 52-year-old female... │ 0          │
└─────────────────────────────────────────────────────────────────┘
```

#### Input 2: Original Data (`Heart_Disease.csv`)
```
┌──────────────────────────────────────────────────────────────────────┐
│ age│sex│chest pain│resting bp│cholesterol│...│target│                │
├────┼───┼──────────┼──────────┼───────────┼───┼──────┤                │
│ 45 │ 1 │    3     │   110    │    264    │...│  1   │                │
│ 52 │ 0 │    2     │   125    │    212    │...│  0   │                │
└──────────────────────────────────────────────────────────────────────┘
```

### Validation Process Flow

```
┌───────────────────────────────────────────────────────────────────────┐
│                    ROW-BY-ROW PROCESSING                              │
└───────────────────────────────────────────────────────────────────────┘

For each row:

Original Row Data          Phase 1 Free-Text
┌──────────────┐          ┌──────────────────────────────┐
│ age: 45      │          │ "A 45-year-old male patient  │
│ sex: 1       │          │  presented with asymptomatic │
│ chest: 3     │          │  chest discomfort. Resting   │
│ bp: 110      │    +     │  blood pressure was 110 mmHg.│
│ chol: 264    │          │  Cholesterol level 264 mg/dL.│
│ fbs: 0       │          │  Normal fasting blood sugar. │
│ ...          │          │  ..."                        │
└──────────────┘          └──────────────────────────────┘
       │                               │
       │                               │
       └───────────────┬───────────────┘
                       │
                       ▼
        ╔══════════════════════════════╗
        ║       STEP 2.1 CHECK         ║
        ║  Missing Content/Conflicts   ║
        ╚══════════════════════════════╝
                       │
          ┌────────────┴────────────┐
          │                         │
          │   Azure OpenAI LLM      │
          │   System Prompt:        │
          │   "You are a medical    │
          │    data validator..."   │
          │                         │
          └────────────┬────────────┘
                       │
                       ▼
              JSON Response:
        ┌──────────────────────────┐
        │ {                        │
        │   "has_issues": false,   │
        │   "issues_found": [],    │
        │   "corrected_text": "..." │
        │ }                        │
        └────────────┬─────────────┘
                     │
                     ▼
        ┌─────────────────────────┐
        │  Corrected Free-Text    │
        │  (or original if OK)    │
        └────────────┬────────────┘
                     │
                     ▼
        ╔══════════════════════════════╗
        ║      STEP 2.2 REVERSE        ║
        ║     MAPPING VERIFICATION     ║
        ╚══════════════════════════════╝
                     │
          ┌──────────┴──────────┐
          │                     │
          │   Azure OpenAI LLM  │
          │   System Prompt:    │
          │   "Extract clinical │
          │    values from text"│
          │                     │
          │   Input: TEXT ONLY  │
          │   (no original data)│
          └──────────┬──────────┘
                     │
                     ▼
            JSON Response:
        ┌──────────────────────┐
        │ {                    │
        │   "age": 45,         │
        │   "sex": 1,          │
        │   "chest_pain": 3,   │
        │   "resting_bp": 110, │
        │   "cholesterol": 264,│
        │   ...                │
        │ }                    │
        └──────────┬───────────┘
                   │
                   ▼
        ╔══════════════════════╗
        ║  FIELD COMPARISON    ║
        ╚══════════════════════╝
                   │
     ┌─────────────┼─────────────┐
     │             │             │
     ▼             ▼             ▼
  Original    Regenerated    Compare
   Value        Value         Match?
  ┌─────┐     ┌─────┐       ┌─────┐
  │ 45  │  vs │ 45  │   →   │  ✓  │
  │  1  │  vs │  1  │   →   │  ✓  │
  │  3  │  vs │  3  │   →   │  ✓  │
  │ 110 │  vs │ 110 │   →   │  ✓  │
  │ 264 │  vs │ 264 │   →   │  ✓  │
  └─────┘     └─────┘       └─────┘
     │             │             │
     └─────────────┴─────────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │ Consistency Score:   │
        │      100%            │
        │   (11/11 matches)    │
        └──────────────────────┘
```

---

## Pipeline Stages

### Stage 1: Data Mappings

**Purpose**: Convert numeric codes to human-readable descriptions

```python
# Clinical Value Mappings
SEX_MAP = {
    0: "female",
    1: "male"
}

CHEST_PAIN_MAP = {
    0: "typical angina",
    1: "atypical angina",
    2: "non-anginal pain",
    3: "asymptomatic"
}

FASTING_BLOOD_SUGAR_MAP = {
    0: "normal (≤120 mg/dL)",
    1: "elevated (>120 mg/dL)"
}

# ... and more
```

**Usage Flow**:
```
Input: sex = 1
  ↓
Lookup: SEX_MAP[1]
  ↓
Output: "male"
```

---

### Stage 2: Step 2.1 - Missing Content & Contradiction Check

**Function**: `step2_1_validate_and_correct()`

**Input Structure**:
```
┌──────────────────────────────────────┐
│ ORIGINAL DATA (Ground Truth)         │
│ ------------------------------------ │
│ Age: 45 years                        │
│ Sex: male                            │
│ Chest Pain: asymptomatic             │
│ BP: 110 mmHg                         │
│ Cholesterol: 264 mg/dL               │
│ ...                                  │
├──────────────────────────────────────┤
│ GENERATED FREE-TEXT                  │
│ ------------------------------------ │
│ "A 45-year-old male patient..."      │
└──────────────────────────────────────┘
```

**LLM Prompt Structure**:
```
System Role:
┌────────────────────────────────────────┐
│ "You are a medical data validator.    │
│  Compare free-text with original data. │
│  Check for:                            │
│  1. Missing clinical information       │
│  2. Contradictions                     │
│  3. Incorrect terminology              │
│  Output JSON with corrections."        │
└────────────────────────────────────────┘

User Message:
┌────────────────────────────────────────┐
│ ORIGINAL PATIENT DATA:                 │
│ [mapped clinical values]               │
│                                        │
│ GENERATED FREE-TEXT:                   │
│ [narrative text]                       │
└────────────────────────────────────────┘
```

**Output Schema**:
```json
{
    "has_issues": true/false,
    "issues_found": [
        "Missing cholesterol value",
        "Contradiction: text says female but data shows male"
    ],
    "corrected_text": "Corrected narrative with all values..."
}
```

**Decision Tree**:
```
                    LLM Response
                         │
          ┌──────────────┴──────────────┐
          │                             │
    has_issues: true            has_issues: false
          │                             │
          ▼                             ▼
    Use corrected_text            Use original text
          │                             │
          └──────────────┬──────────────┘
                         │
                         ▼
              Proceed to Step 2.2
```

---

### Stage 3: Step 2.2 - Reverse Mapping Verification

**Function**: `step2_2_reverse_map()`

**Critical Design**: LLM receives **ONLY** the free-text, no original data

**Input**:
```
┌────────────────────────────────────────┐
│ FREE-TEXT ONLY (Blind Test)           │
│ ────────────────────────────────────── │
│ "A 45-year-old male patient presented  │
│  with asymptomatic chest discomfort.   │
│  Resting blood pressure measured       │
│  110 mmHg. Cholesterol level was       │
│  264 mg/dL. Normal fasting blood       │
│  sugar..."                             │
│                                        │
│ NO ACCESS TO ORIGINAL DATA ❌          │
└────────────────────────────────────────┘
```

**LLM Prompt**:
```
System Role:
┌────────────────────────────────────────┐
│ "Extract clinical values from text.   │
│  Use these mappings:                   │
│  - sex: female=0, male=1              │
│  - chest pain: typical=0, atypical=1, │
│    non-anginal=2, asymptomatic=3      │
│  ...                                   │
│  Return JSON with numeric codes."      │
└────────────────────────────────────────┘
```

**Output Schema**:
```json
{
    "age": 45,
    "sex": 1,
    "chest_pain_type": 3,
    "resting_bp": 110,
    "cholesterol": 264,
    "fasting_blood_sugar": 0,
    "resting_ecg": 0,
    "max_heart_rate": 132,
    "exercise_angina": 0,
    "oldpeak": 2.5,
    "ST_slope": 1
}
```

---

### Stage 4: Consistency Scoring

**Function**: `compare_values()`

**Comparison Logic**:

```
For each of 11 clinical fields:

Original Value    Regenerated Value    Match?
┌────────────┐   ┌────────────┐      ┌──────┐
│    45      │ = │    45      │  →   │  ✓   │ Integer comparison
│    1       │ = │    1       │  →   │  ✓   │ Integer comparison
│  110.0     │ ≈ │  110.2     │  →   │  ✓   │ Float tolerance (±0.5)
│  264       │ = │  260       │  →   │  ✗   │ Outside tolerance
└────────────┘   └────────────┘      └──────┘

Consistency Score = (Matches / Total Fields) × 100
                  = (10 / 11) × 100
                  = 90.91%
```

**Score Interpretation**:
```
┌─────────────┬──────────────────────────────────────┐
│   Score     │           Meaning                    │
├─────────────┼──────────────────────────────────────┤
│   100%      │ Perfect - All fields match           │
│  90-99%     │ Excellent - Minor discrepancies      │
│  80-89%     │ Good - Acceptable quality            │
│  70-79%     │ Fair - Needs review                  │
│   <70%      │ Poor - Significant issues            │
└─────────────┴──────────────────────────────────────┘
```

---

## Code Structure

### Module Organization

```
validation.py
├── Imports & Setup
│   ├── pandas, json, datetime
│   ├── dotenv (environment variables)
│   └── AzureOpenAI client
│
├── Configuration
│   ├── Azure OpenAI credentials
│   ├── Data mappings (SEX_MAP, CHEST_PAIN_MAP, etc.)
│   └── Field list (11 clinical fields)
│
├── Core Functions
│   ├── step2_1_validate_and_correct()
│   │   ├── Input: free_text, original_row
│   │   ├── Process: LLM validation
│   │   └── Output: corrected_text, issues_found
│   │
│   ├── step2_2_reverse_map()
│   │   ├── Input: corrected_text
│   │   ├── Process: LLM extraction
│   │   └── Output: regenerated_values
│   │
│   └── compare_values()
│       ├── Input: original_row, regenerated_values
│       ├── Process: Field-by-field comparison
│       └── Output: consistency_score, field_matches
│
├── Main Pipeline
│   └── validate_dataset()
│       ├── Load input files
│       ├── Loop through rows
│       ├── Apply Steps 2.1 & 2.2
│       ├── Generate reports
│       └── Save output files
│
└── Entry Point
    └── main()
```

### Function Call Flow

```
main()
  │
  ├─→ validate_dataset()
  │     │
  │     ├─→ Load CSVs (Phase 1 output + Original data)
  │     │
  │     ├─→ For each row:
  │     │     │
  │     │     ├─→ step2_1_validate_and_correct()
  │     │     │     │
  │     │     │     ├─→ Azure OpenAI API call
  │     │     │     └─→ Return corrected_text
  │     │     │
  │     │     ├─→ step2_2_reverse_map()
  │     │     │     │
  │     │     │     ├─→ Azure OpenAI API call
  │     │     │     └─→ Return regenerated_values
  │     │     │
  │     │     └─→ compare_values()
  │     │           │
  │     │           └─→ Return consistency_score
  │     │
  │     └─→ Generate 3 output files
  │
  └─→ Print completion message
```

---

## Examples

### Example 1: Perfect Match (100% Consistency)

**Original Data**:
```
age: 45, sex: 1 (male), chest_pain: 3 (asymptomatic),
resting_bp: 110, cholesterol: 264, fbs: 0 (normal), ...
```

**Generated Free-Text**:
```
"A 45-year-old male patient presented with asymptomatic chest 
discomfort. Resting blood pressure was 110 mmHg. Serum cholesterol 
measured 264 mg/dL with normal fasting blood sugar levels..."
```

**Step 2.1 Result**:
```json
{
    "has_issues": false,
    "issues_found": [],
    "corrected_text": "[original text - unchanged]"
}
```

**Step 2.2 Result**:
```json
{
    "age": 45, "sex": 1, "chest_pain_type": 3,
    "resting_bp": 110, "cholesterol": 264, ...
}
```

**Comparison**:
```
✓ age: 45 = 45
✓ sex: 1 = 1
✓ chest_pain_type: 3 = 3
✓ resting_bp: 110 = 110
✓ cholesterol: 264 = 264
... (all fields match)

Consistency Score: 100%
```

---

### Example 2: Missing Information Detected

**Original Data**:
```
age: 52, sex: 0 (female), chest_pain: 2 (non-anginal),
resting_bp: 125, cholesterol: 212, max_hr: 168, ...
```

**Generated Free-Text (Incomplete)**:
```
"A 52-year-old female with non-anginal chest pain. 
Blood pressure was 125 mmHg."
```
↑ Missing: cholesterol, max heart rate, etc.

**Step 2.1 Result**:
```json
{
    "has_issues": true,
    "issues_found": [
        "Missing cholesterol value (212 mg/dL)",
        "Missing maximum heart rate (168 bpm)",
        "Missing ECG results"
    ],
    "corrected_text": "A 52-year-old female with non-anginal 
    chest pain. Blood pressure was 125 mmHg. Cholesterol level 
    measured 212 mg/dL. Maximum heart rate achieved was 168 bpm..."
}
```

**Step 2.2 Result** (using corrected text):
```json
{
    "age": 52, "sex": 0, "cholesterol": 212,
    "max_heart_rate": 168, ...
}
```

**Comparison**:
```
✓ All fields now match after correction
Consistency Score: 100%
```

---

### Example 3: Contradiction Detected

**Original Data**:
```
sex: 1 (male), exercise_angina: 0 (No)
```

**Generated Free-Text (Contradictory)**:
```
"A female patient who experienced angina during exercise..."
```
↑ Contradictions: sex is wrong, exercise angina is wrong

**Step 2.1 Result**:
```json
{
    "has_issues": true,
    "issues_found": [
        "Contradiction: text says female but data shows male",
        "Contradiction: text says angina present but data shows absent"
    ],
    "corrected_text": "A male patient who did not experience 
    angina during exercise..."
}
```

---

## Output Files

### Output 1: `heart_disease_freetext_final.csv`

**Purpose**: Clean, validated dataset ready for ML use

**Structure**:
```
┌──────────────────────────────────────────────────────────────────┐
│ Feature              │ Free_Text            │ Target│ Score     │
├──────────────────────┼──────────────────────┼───────┼───────────┤
│ 45,1,3,110,264,...   │ A 45-year-old male...│   1   │  100.00   │
│ 52,0,2,125,212,...   │ A 52-year-old female │   0   │  100.00   │
│ 58,1,0,140,211,...   │ A 58-year-old male...│   1   │   90.91   │
└──────────────────────────────────────────────────────────────────┘
```

**Use Case**: 
- Training ML models with validated free-text
- Filtering rows by consistency score
- Final production dataset

---

### Output 2: `heart_disease_freetext_validation_report.csv`

**Purpose**: Detailed audit trail for quality assurance

**Structure**:
```
┌──────────────────────────────────────────────────────────────────────┐
│ row_index                               │ 0                          │
├─────────────────────────────────────────┼────────────────────────────┤
│ feature_text                            │ 45,1,3,110,264,...         │
├─────────────────────────────────────────┼────────────────────────────┤
│ original_free_text                      │ A 45-year-old male...      │
├─────────────────────────────────────────┼────────────────────────────┤
│ had_issues                              │ False                      │
├─────────────────────────────────────────┼────────────────────────────┤
│ issues_found                            │ None                       │
├─────────────────────────────────────────┼────────────────────────────┤
│ corrected_free_text                     │ A 45-year-old male...      │
├─────────────────────────────────────────┼────────────────────────────┤
│ regenerated_values                      │ {"age":45,"sex":1,...}     │
├─────────────────────────────────────────┼────────────────────────────┤
│ consistency_score                       │ 100.00                     │
├─────────────────────────────────────────┼────────────────────────────┤
│ matches                                 │ 11/11                      │
├─────────────────────────────────────────┼────────────────────────────┤
│ field_details                           │ age: orig=45, regen=45,... │
├─────────────────────────────────────────┼────────────────────────────┤
│ target                                  │ 1                          │
└──────────────────────────────────────────────────────────────────────┘
```

**Use Cases**:
- Debug low-scoring rows
- Identify systematic issues
- Track corrections made
- Compliance documentation

---

### Output 3: `heart_disease_freetext_validation_summary.txt`

**Purpose**: Executive summary with statistics

**Content Structure**:
```
================================================================================
FREE-TEXT VALIDATION SUMMARY REPORT
Generated: 2026-02-04 10:30:45
================================================================================

INPUT FILES:
- Phase 1 Output: heart_disease_freetext_step1_generated.csv
- Original Data:  Heart_Disease.csv

TOTAL ROWS PROCESSED: 100

LLM USED: Azure OpenAI (gpt-4)

================================================================================
PHASE 2: FREE-TEXT VALIDATION RESULTS
================================================================================

STEP 2.1 - Missing Content/Contradiction Check:
-----------------------------------------------
Rows with issues found:    12 (12.0%)
Rows without issues:       88 (88.0%)

STEP 2.2 - Reverse-Mapping Consistency:
-----------------------------------------------
Average Consistency Score: 97.45%
Perfect Matches (100%):    85 rows (85.0%)
High Consistency (>=90%):  95 rows (95.0%)
Low Consistency (<90%):    5 rows (5.0%)

--------------------------------------------------------------------------------
PER-FIELD ACCURACY (Reverse-Mapping Verification)
--------------------------------------------------------------------------------
age                 : [====================]  100.00%
sex                 : [====================]  100.00%
chest_pain_type     : [=================== ]   98.00%
resting_bp          : [=================== ]   97.00%
cholesterol         : [==================  ]   96.00%
max_heart_rate      : [==================  ]   96.00%
fasting_blood_sugar : [=================== ]   99.00%
resting_ecg         : [=================== ]   98.00%
exercise_angina     : [=================== ]   99.00%
oldpeak             : [=================   ]   94.00%
ST_slope            : [=================   ]   95.00%

--------------------------------------------------------------------------------
CONSISTENCY SCORE DISTRIBUTION
--------------------------------------------------------------------------------
100%:     ############################################### (85)
90-99%:   ########## (10)
<90%:     ##### (5)

--------------------------------------------------------------------------------
INTERPRETATION
--------------------------------------------------------------------------------
EXCELLENT: The free-text generation is highly reliable.
   The generated narratives accurately reflect the original clinical data.

================================================================================
OUTPUT FILES GENERATED
================================================================================
1. heart_disease_freetext_final.csv              - Final validated dataset
2. heart_disease_freetext_validation_report.csv  - Full audit trail
3. heart_disease_freetext_validation_summary.txt - This summary

================================================================================
```

**Use Cases**:
- Quick quality assessment
- Stakeholder reporting
- Identify weakest fields
- Decision making (accept/reject dataset)

---

## Quality Metrics

### Key Performance Indicators

```
┌─────────────────────────────────────────────────────────────────┐
│                    QUALITY METRICS DASHBOARD                    │
└─────────────────────────────────────────────────────────────────┘

1. AVERAGE CONSISTENCY SCORE
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Mean of all row scores
   Target: ≥95%
   
   97.45% [====================] ✓ EXCELLENT

2. PERFECT MATCH RATE
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Rows with 100% consistency
   Target: ≥80%
   
   85% [==================  ] ✓ GOOD

3. ISSUE DETECTION RATE (Step 2.1)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Rows requiring correction
   Lower is better
   
   12% [==                  ] ✓ LOW

4. PER-FIELD ACCURACY
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Individual field match rates
   Target: All fields ≥90%
   
   Lowest: oldpeak (94%) ✓ ACCEPTABLE
```

### Quality Threshold Guidelines

```
┌──────────────┬─────────────────┬──────────────────────────────┐
│   Metric     │   Threshold     │        Action                │
├──────────────┼─────────────────┼──────────────────────────────┤
│ Avg Score    │     ≥95%        │ Accept dataset               │
│              │   90-95%        │ Review low-scoring rows      │
│              │     <90%        │ Reject - improve generation  │
├──────────────┼─────────────────┼──────────────────────────────┤
│ Perfect Rate │     ≥80%        │ Excellent quality            │
│              │   70-80%        │ Acceptable                   │
│              │     <70%        │ Needs improvement            │
├──────────────┼─────────────────┼──────────────────────────────┤
│ Field Acc.   │  All ≥90%       │ Pass                         │
│              │  Any <90%       │ Investigate that field       │
└──────────────┴─────────────────┴──────────────────────────────┘
```

---

## Technical Details

### Environment Variables Required

```bash
# .env file
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
```

### Dependencies

```
- pandas: Data manipulation
- python-dotenv: Environment variables
- openai: Azure OpenAI Python SDK
```

### LLM Configuration

```python
# Consistent settings for both steps
model = DEPLOYMENT_NAME
temperature = 0          # Deterministic output
max_tokens = 300-700     # Sufficient for medical text
response_format = "json" # Structured output
```

### Error Handling

```
Azure API Call
      │
      ├─→ Success → Parse JSON
      │                │
      │                ├─→ Valid JSON → Continue
      │                └─→ Invalid JSON → Return default
      │
      └─→ Failure → Log error, return default

Default behavior ensures pipeline never crashes
```

---

## Best Practices

### When to Use This Pipeline

✅ **Good Use Cases**:
- Validating AI-generated clinical narratives
- Ensuring data fidelity in synthetic datasets
- Quality assurance for medical ML training data
- Compliance documentation for healthcare AI

❌ **Not Suitable For**:
- Real-time applications (too slow)
- Unstructured text without ground truth
- Non-medical domains (mappings are specific)

### Optimization Tips

1. **Batch Processing**: Process in smaller batches if dataset is large
2. **Parallel Execution**: Can parallelize row processing (add threading)
3. **Caching**: Cache LLM responses to avoid redundant API calls
4. **Cost Control**: Monitor Azure OpenAI token usage

### Extending the Pipeline

```python
# Add new fields
FIELDS.append("new_clinical_field")

# Add new mappings
NEW_FIELD_MAP = {0: "value1", 1: "value2"}

# Modify prompts
# Edit system/user messages in step2_1 and step2_2 functions
```

---

## Troubleshooting

### Common Issues

**Issue 1: Low Consistency Scores**
```
Symptom: Many rows <90%
Cause: Phase 1 generation prompts need improvement
Solution: Review and refine free-text generation prompts
```

**Issue 2: High JSON Parse Errors**
```
Symptom: Frequent "JSON parse error" messages
Cause: LLM not following output format
Solution: Strengthen system prompts, add examples
```

**Issue 3: Specific Field Always Fails**
```
Symptom: One field (e.g., oldpeak) consistently low accuracy
Cause: Ambiguous terminology or missing from text
Solution: Ensure Phase 1 always includes that field explicitly
```

---

## Conclusion

This validation pipeline provides **bidirectional consistency testing** to ensure AI-generated medical narratives are:
- ✅ Complete (no missing information)
- ✅ Accurate (no contradictions)
- ✅ Unambiguous (can reconstruct original data)

The two-step approach (forward validation + reverse mapping) creates a robust quality assurance system for synthetic medical text generation.

---

## Appendix: File Dependencies

```
Project Structure:
.
├── Heart_Disease.csv                          [Input - Original]
├── heart_disease_freetext_step1_generated.csv [Input - Phase 1]
├── validation.py                              [This Script]
├── .env                                       [Configuration]
│
└── Outputs:
    ├── heart_disease_freetext_final.csv
    ├── heart_disease_freetext_validation_report.csv
    └── heart_disease_freetext_validation_summary.txt
```

---

**Last Updated**: February 4, 2026  
**Version**: 1.0  
**Author**: AI Dataset Validation Pipeline

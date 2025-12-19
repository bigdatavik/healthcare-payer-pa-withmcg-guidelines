# Databricks notebook source
# MAGIC %md
# MAGIC # Setup 03: Generate MCG and InterQual Guidelines
# MAGIC
# MAGIC This notebook generates synthetic MCG, InterQual, and Medicare guidelines for Vector Store 2.
# MAGIC
# MAGIC **Guidelines Generated:**
# MAGIC - **MCG Care Guidelines** (outpatient procedures)
# MAGIC - **InterQual Criteria** (inpatient level of care)
# MAGIC - **Medicare LCD/NCD** policies
# MAGIC
# MAGIC **Purpose:** Agent will search these to determine appropriate questionnaire and validate decisions

# COMMAND ----------

# MAGIC %md
# MAGIC ## Imports and Setup

# COMMAND ----------

import json
import pandas as pd
from datetime import datetime, timedelta
import random

random.seed(42)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Get Parameters

# COMMAND ----------

dbutils.widgets.text("catalog_name", "healthcare_payer_pa_withmcg_guidelines_dev", "Catalog Name")
dbutils.widgets.text("schema_name", "main", "Schema Name")

catalog_name = dbutils.widgets.get("catalog_name")
schema_name = dbutils.widgets.get("schema_name")

print(f"Catalog: {catalog_name}")
print(f"Schema: {schema_name}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## MCG Care Guidelines (Outpatient Procedures)

# COMMAND ----------

mcg_guidelines = [
    {
        "guideline_id": "MCG-A-0458",
        "platform": "MCG",
        "category": "OUTPATIENT_IMAGING",
        "procedure_code": "73721",  # MRI knee
        "diagnosis_code": "M25.561",  # Pain in right knee
        "title": "Knee MRI - Medical Necessity Criteria",
        "content": """MCG CARE GUIDELINES: KNEE MRI (A-0458)

OVERVIEW:
MRI of the knee is indicated when clinical findings suggest internal derangement and results will alter treatment decisions.

INDICATIONS (Medical Necessity Criteria):

1. PATIENT AGE & SYMPTOM DURATION
   - Patient age ≥ 18 years
   - Symptoms present for ≥ 4 weeks despite conservative therapy
   OR
   - Acute traumatic injury with mechanical symptoms

2. CONSERVATIVE THERAPY COMPLETED
   - Physical therapy: Minimum 4 weeks (8-12 sessions)
   - NSAIDs or other anti-inflammatory medication
   - Activity modification
   OR
   - Contraindication to conservative therapy documented

3. CLINICAL FINDINGS (at least ONE of the following)
   - Mechanical symptoms: locking, catching, giving way
   - Joint line tenderness on examination
   - Positive McMurray test or Apley compression test
   - Suspected meniscal tear based on history and physical
   - Persistent effusion despite treatment

4. FUNCTIONAL IMPACT
   - Significant interference with daily activities or work
   - Pain level ≥ 5/10 despite conservative treatment
   - Limited range of motion documented

5. IMAGING PREREQUISITE
   - X-ray of knee completed within past 6 months
   - X-ray shows no contraindication to MRI
   - No prior MRI of same knee within 6 months (unless new injury)

EXCLUSIONS (MRI NOT indicated):
   - Symptoms < 4 weeks duration (unless acute trauma)
   - Conservative therapy not attempted
   - Asymptomatic patient
   - Recent MRI (< 6 months) with same symptoms

APPROVAL CRITERIA:
   ✅ APPROVE if: ≥ 3 of the above indications are met
   ⏸️ PEND if: 2 indications met, request additional documentation
   ❌ DENY if: < 2 indications met

EVIDENCE BASIS: Level 1A evidence from American Academy of Orthopaedic Surgeons (AAOS) clinical practice guidelines.

EFFECTIVE DATE: 2024-01-01
REVIEW DATE: 2024-12-31
""",
        "questionnaire": json.dumps([
            {"question": "Is patient age 18 years or older?", "answer_type": "yes/no", "required": True},
            {"question": "Have symptoms been present for 4+ weeks?", "answer_type": "yes/no", "required": True},
            {"question": "Has patient completed 4+ weeks of physical therapy?", "answer_type": "yes/no", "required": True},
            {"question": "Does patient have mechanical symptoms (locking/catching/giving way)?", "answer_type": "yes/no", "required": False},
            {"question": "Is there documented joint line tenderness on examination?", "answer_type": "yes/no", "required": False},
            {"question": "Has knee X-ray been completed within past 6 months?", "answer_type": "yes/no", "required": True},
            {"question": "Is pain level 5/10 or greater despite treatment?", "answer_type": "yes/no", "required": False},
            {"question": "Is there significant functional impairment documented?", "answer_type": "yes/no", "required": False}
        ]),
        "decision_criteria": "APPROVE if ≥ 5 YES answers including all required questions; PEND if 3-4 YES; DENY if < 3 YES",
        "effective_date": datetime(2024, 1, 1).date(),
        "tags": "imaging,mri,knee,orthopedic,musculoskeletal"
    },
    {
        "guideline_id": "MCG-A-1234",
        "platform": "MCG",
        "category": "OUTPATIENT_PROCEDURE",
        "procedure_code": "93458",  # Cardiac catheterization
        "diagnosis_code": "I25.10",  # Atherosclerotic heart disease
        "title": "Cardiac Catheterization - Medical Necessity",
        "content": """MCG CARE GUIDELINES: CARDIAC CATHETERIZATION (A-1234)

OVERVIEW:
Left heart catheterization is indicated for diagnosis and treatment planning in patients with suspected or known coronary artery disease.

INDICATIONS (Medical Necessity Criteria):

1. CLINICAL PRESENTATION (at least ONE)
   - Chest pain with high pretest probability of CAD
   - Abnormal stress test (nuclear, echo, or exercise ECG)
   - NSTEMI or unstable angina
   - Heart failure with suspected ischemic etiology
   - Life-threatening ventricular arrhythmia
   - Syncope with suspected cardiac cause

2. NON-INVASIVE TESTING COMPLETED
   - Stress test (exercise or pharmacologic) with abnormal results
   OR
   - High-risk features making stress test unnecessary:
     * ST elevation on ECG
     * Elevated troponin with chest pain
     * New wall motion abnormality on echo
     * High TIMI risk score (≥ 5)

3. RISK FACTORS (at least TWO)
   - Diabetes mellitus
   - Hypertension
   - Hyperlipidemia
   - Current smoker or quit < 10 years
   - Family history of premature CAD (male < 55, female < 65)
   - Age: male ≥ 45, female ≥ 55

4. SYMPTOM SEVERITY
   - CCS Class II-IV angina despite medical therapy
   - NYHA Class III-IV heart failure symptoms
   - Symptoms limiting daily activities

5. MEDICAL OPTIMIZATION
   - On appropriate antiplatelet therapy
   - On statin if indicated
   - Beta blocker trial unless contraindicated

EXCLUSIONS:
   - Asymptomatic patient with normal stress test
   - Stress test not performed (unless acute indication)
   - Severe comorbidities making revascularization not feasible
   - Patient declines intervention regardless of findings

APPROVAL CRITERIA:
   ✅ APPROVE if: Meets clinical presentation + (abnormal stress test OR high-risk features)
   ⏸️ PEND if: Need stress test results or additional clinical information
   ❌ DENY if: No clinical indication or stress test normal

EFFECTIVE DATE: 2024-01-01
""",
        "questionnaire": json.dumps([
            {"question": "Does patient have chest pain or angina?", "answer_type": "yes/no", "required": True},
            {"question": "Has patient had an abnormal stress test (nuclear/echo/exercise)?", "answer_type": "yes/no", "required": True},
            {"question": "Does patient have ≥ 2 cardiac risk factors (DM, HTN, smoking, FHx)?", "answer_type": "yes/no", "required": True},
            {"question": "Are symptoms CCS Class II or higher (limiting activities)?", "answer_type": "yes/no", "required": False},
            {"question": "Is patient on appropriate medical therapy (antiplatelet, statin)?", "answer_type": "yes/no", "required": False},
            {"question": "Are there high-risk features (elevated troponin, ST changes, arrhythmia)?", "answer_type": "yes/no", "required": False}
        ]),
        "decision_criteria": "APPROVE if abnormal stress test + chest pain + risk factors; PEND if stress test pending; DENY if normal stress test",
        "effective_date": datetime(2024, 1, 1).date(),
        "tags": "cardiac,catheterization,cad,coronary,cardiology"
    },
    {
        "guideline_id": "MCG-A-7890",
        "platform": "MCG",
        "category": "DME",
        "procedure_code": "E0260",  # Hospital bed
        "diagnosis_code": "I50.9",  # Heart failure
        "title": "Hospital Bed (Home Use) - Medical Necessity",
        "content": """MCG CARE GUIDELINES: HOSPITAL BED - HOME USE (A-7890)

OVERVIEW:
Hospital bed for home use is medically necessary when patient's condition requires positioning not achievable with standard bed.

INDICATIONS (Medical Necessity Criteria):

1. MEDICAL CONDITION (at least ONE)
   - Congestive heart failure requiring elevated head positioning
   - GERD with aspiration risk requiring head elevation
   - Respiratory condition requiring elevated positioning (COPD, pulmonary edema)
   - Immobility requiring frequent repositioning
   - Post-surgical condition requiring specific positioning

2. FUNCTIONAL REQUIREMENT
   - Patient requires head-of-bed elevation > 30 degrees for symptom relief
   - Patient unable to achieve required positioning with standard bed + pillows
   - Documented functional impairment without hospital bed

3. PHYSICIAN DOCUMENTATION
   - Written order from treating physician
   - Medical necessity clearly documented
   - Specific positioning requirements stated
   - Expected duration of need documented

4. ALTERNATIVES TRIED
   - Standard bed with extra pillows inadequate
   - Wedge pillows insufficient
   - Recliner chair not feasible for sleep

EXCLUSIONS:
   - Patient preference without medical necessity
   - Standard bed with pillows adequate
   - Short-term need < 3 months (consider rental)

APPROVAL CRITERIA:
   ✅ APPROVE if: Medical condition + functional requirement + physician order
   ⏸️ PEND if: Need physician documentation or trial of alternatives
   ❌ DENY if: No documented medical necessity

DURATION: Typically 6-12 months, renewable based on ongoing need

EFFECTIVE DATE: 2024-01-01
""",
        "questionnaire": json.dumps([
            {"question": "Does patient have CHF, GERD with aspiration risk, or respiratory condition?", "answer_type": "yes/no", "required": True},
            {"question": "Is head-of-bed elevation > 30 degrees required for symptom relief?", "answer_type": "yes/no", "required": True},
            {"question": "Has physician documented medical necessity in written order?", "answer_type": "yes/no", "required": True},
            {"question": "Have standard bed + pillows been tried and found inadequate?", "answer_type": "yes/no", "required": True},
            {"question": "Is expected duration of need ≥ 3 months?", "answer_type": "yes/no", "required": False}
        ]),
        "decision_criteria": "APPROVE if all 4 required questions YES; PEND if documentation incomplete; DENY if < 3 YES",
        "effective_date": datetime(2024, 1, 1).date(),
        "tags": "dme,hospital bed,home health,equipment"
    }
]

print(f"✅ Created {len(mcg_guidelines)} MCG guidelines")

# COMMAND ----------

# MAGIC %md
# MAGIC ## InterQual Criteria (Inpatient Level of Care)

# COMMAND ----------

interqual_guidelines = [
    {
        "guideline_id": "IQ-ACUTE-CHF",
        "platform": "InterQual",
        "category": "INPATIENT_ADMISSION",
        "procedure_code": None,
        "diagnosis_code": "I50.9",  # Heart failure
        "title": "Acute Decompensated Heart Failure - Admission Criteria",
        "content": """INTERQUAL LEVEL OF CARE CRITERIA: ACUTE CHF ADMISSION

OVERVIEW:
Acute inpatient level of care is appropriate for patients with decompensated heart failure requiring IV therapy and intensive monitoring.

SEVERITY OF ILLNESS (at least ONE required):

1. RESPIRATORY DISTRESS
   - Respiratory rate > 24 despite oxygen
   - Oxygen saturation < 90% on room air
   - Requiring BiPAP or CPAP
   - Rales > 1/3 up lung fields bilaterally

2. HEMODYNAMIC INSTABILITY
   - Systolic BP < 90 mmHg or > 180 mmHg
   - New or worsening renal dysfunction (Cr increase > 0.5 mg/dL)
   - BNP > 1000 or NT-proBNP > 3000
   - Signs of end-organ hypoperfusion

3. VOLUME OVERLOAD
   - Weight gain > 5 lbs in 48 hours or > 10 lbs in 1 week
   - Severe peripheral edema (3+ or greater)
   - Ascites requiring paracentesis
   - JVD with hepatojugular reflux

INTENSITY OF SERVICE (at least ONE required):

1. IV DIURETIC THERAPY
   - Requires IV furosemide or other loop diuretic
   - Inadequate response to maximum oral diuretics
   - Diuretic resistance requiring continuous infusion

2. VASOACTIVE MEDICATIONS
   - Requiring IV inotropes (dobutamine, milrinone)
   - Requiring IV vasodilators (nitroglycerin, nitroprusside)
   - Requiring IV vasopressors

3. INTENSIVE MONITORING
   - Telemetry monitoring required for arrhythmias
   - Frequent vital sign monitoring (Q2-4H)
   - Daily weights and strict I/O monitoring
   - Serial BMP monitoring for electrolyte management

DISCHARGE SCREENING (ALL required for discharge):

   - No IV medications for ≥ 24 hours
   - Stable on oral diuretic regimen
   - Weight stable or decreasing
   - Oxygen saturation stable on home oxygen or room air
   - Follow-up arranged within 7 days
   - Patient/family education completed

ADMISSION CRITERIA:
   ✅ APPROVE ADMISSION if: ≥ 1 Severity criterion + ≥ 1 Intensity criterion
   ⏸️ OBSERVATION if: Borderline criteria, trial of IV diuretics
   ❌ OUTPATIENT if: No severity criteria, stable on oral medications

CONTINUED STAY CRITERIA (Day 2+):
   ✅ CONTINUE if: Still requiring IV therapy or not meeting discharge criteria
   ❌ DISCHARGE if: All discharge criteria met

EFFECTIVE DATE: 2024-01-01
""",
        "questionnaire": json.dumps([
            {"question": "Is respiratory rate > 24 or oxygen sat < 90% on room air?", "answer_type": "yes/no", "required": False},
            {"question": "Is systolic BP < 90 or > 180 mmHg?", "answer_type": "yes/no", "required": False},
            {"question": "Is BNP > 1000 or NT-proBNP > 3000?", "answer_type": "yes/no", "required": False},
            {"question": "Does patient require IV diuretic therapy?", "answer_type": "yes/no", "required": True},
            {"question": "Does patient require IV inotropes or vasodilators?", "answer_type": "yes/no", "required": False},
            {"question": "Is telemetry monitoring required?", "answer_type": "yes/no", "required": False}
        ]),
        "decision_criteria": "APPROVE admission if ≥ 1 severity criterion + requires IV therapy; DISCHARGE if stable on oral meds ≥ 24 hours",
        "effective_date": datetime(2024, 1, 1).date(),
        "tags": "inpatient,chf,heart failure,admission,level of care"
    },
    {
        "guideline_id": "IQ-ACUTE-PNEUMONIA",
        "platform": "InterQual",
        "category": "INPATIENT_ADMISSION",
        "procedure_code": None,
        "diagnosis_code": "J18.9",  # Pneumonia
        "title": "Community-Acquired Pneumonia - Admission Criteria",
        "content": """INTERQUAL LEVEL OF CARE CRITERIA: PNEUMONIA ADMISSION

OVERVIEW:
Acute inpatient admission for pneumonia based on severity scoring and need for IV antibiotics.

SEVERITY OF ILLNESS (at least ONE required):

1. VITAL SIGN ABNORMALITIES (PORT Score / CURB-65)
   - Respiratory rate ≥ 30 breaths/min
   - Oxygen saturation < 90% on room air
   - Systolic BP < 90 mmHg
   - Heart rate > 125 bpm
   - Temperature < 95°F or > 104°F

2. LABORATORY ABNORMALITIES
   - WBC < 4,000 or > 30,000
   - Creatinine > 1.5 mg/dL (or acute increase)
   - Glucose > 250 mg/dL (non-diabetic)
   - Arterial pH < 7.35
   - PaO2 < 60 mmHg or PaO2/FiO2 < 250

3. RADIOGRAPHIC FINDINGS
   - Multilobar infiltrates
   - Pleural effusion (moderate to large)
   - Cavitation or abscess formation
   - Rapidly progressive infiltrates

INTENSITY OF SERVICE (at least ONE required):

1. IV ANTIBIOTIC THERAPY
   - Cannot tolerate oral antibiotics (vomiting, NPO)
   - Requires IV antibiotics for severity
   - Multi-drug resistant organism requiring IV therapy

2. SUPPLEMENTAL OXYGEN
   - Requires ≥ 2L O2 to maintain sat > 90%
   - Requires BiPAP or CPAP
   - Risk of respiratory failure

3. SUPPORTIVE CARE
   - IV fluid resuscitation needed
   - Vasopressor support required
   - Unable to maintain oral intake

RISK FACTORS (Increase admission threshold):
   - Age > 65
   - Nursing home resident
   - Chronic lung disease (COPD, asthma)
   - Immunocompromised
   - Recent hospitalization (< 90 days)

ADMISSION CRITERIA:
   ✅ ADMIT if: PORT Score ≥ IV OR CURB-65 ≥ 2 OR requires IV antibiotics
   ⏸️ OBSERVATION if: Borderline criteria, trial of oral antibiotics
   ❌ OUTPATIENT if: PORT I-III, CURB-65 0-1, tolerating oral antibiotics

DISCHARGE CRITERIA:
   - Afebrile ≥ 24 hours
   - Tolerating oral antibiotics
   - Oxygen saturation stable on room air or home O2
   - Clinically improving
   - Safe discharge disposition

EFFECTIVE DATE: 2024-01-01
""",
        "questionnaire": json.dumps([
            {"question": "Is respiratory rate ≥ 30 or oxygen sat < 90% on room air?", "answer_type": "yes/no", "required": False},
            {"question": "Is systolic BP < 90 mmHg?", "answer_type": "yes/no", "required": False},
            {"question": "Are multilobar infiltrates present on chest X-ray?", "answer_type": "yes/no", "required": False},
            {"question": "Does patient require IV antibiotics?", "answer_type": "yes/no", "required": True},
            {"question": "Does patient require supplemental oxygen ≥ 2L?", "answer_type": "yes/no", "required": False},
            {"question": "Is PORT score ≥ IV or CURB-65 ≥ 2?", "answer_type": "yes/no", "required": True}
        ]),
        "decision_criteria": "APPROVE admission if PORT ≥ IV OR requires IV antibiotics + oxygen; DISCHARGE if afebrile 24h + stable on oral meds",
        "effective_date": datetime(2024, 1, 1).date(),
        "tags": "inpatient,pneumonia,infection,respiratory,admission"
    }
]

print(f"✅ Created {len(interqual_guidelines)} InterQual criteria")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Medicare LCD/NCD Policies

# COMMAND ----------

medicare_policies = [
    {
        "guideline_id": "LCD-L38061",
        "platform": "Medicare",
        "category": "IMAGING",
        "procedure_code": "73721",
        "diagnosis_code": "M25.561",
        "title": "MRI Lower Extremity - Medicare LCD",
        "content": """MEDICARE LOCAL COVERAGE DETERMINATION (LCD): MRI Lower Extremity

LCD ID: L38061
Contractor: National

COVERAGE INDICATIONS:

MRI of the knee is covered when medically reasonable and necessary to:
1. Evaluate suspected meniscal or ligamentous injury
2. Assess articular cartilage damage
3. Evaluate for occult fracture not visible on X-ray
4. Assess for osteonecrosis
5. Evaluate masses or tumors
6. Pre-surgical planning

COVERAGE LIMITATIONS:

1. X-ray must be performed first (within 6 months)
2. Conservative therapy trial required for non-traumatic conditions
3. Not covered for routine follow-up of stable conditions
4. Not covered more frequently than once per 6 months for same condition

DOCUMENTATION REQUIREMENTS:

1. Clinical indication clearly stated
2. X-ray results documented
3. Physical examination findings documented
4. Conservative therapy documented (if applicable)
5. How results will affect treatment plan

ICD-10 CODES COVERED:
- M25.5xx (Pain in joint)
- S83.2xx (Tear of meniscus, current injury)
- M23.2xx (Derangement of meniscus due to old tear)
- M22.xx (Disorders of patella)

EFFECTIVE DATE: 2024-01-01
REVIEW DATE: Annually
""",
        "questionnaire": json.dumps([
            {"question": "Has knee X-ray been completed within past 6 months?", "answer_type": "yes/no", "required": True},
            {"question": "Is there clinical suspicion of meniscal or ligamentous injury?", "answer_type": "yes/no", "required": True},
            {"question": "For non-traumatic conditions, has conservative therapy been tried?", "answer_type": "yes/no", "required": True},
            {"question": "Is this more than 6 months since last MRI of same knee?", "answer_type": "yes/no", "required": True},
            {"question": "Is there clear documentation of how MRI will affect treatment?", "answer_type": "yes/no", "required": True}
        ]),
        "decision_criteria": "APPROVE if all required criteria met; DENY if X-ray not done or < 6 months since prior MRI",
        "effective_date": datetime(2024, 1, 1).date(),
        "tags": "medicare,lcd,mri,knee,imaging"
    },
    {
        "guideline_id": "NCD-210.3",
        "platform": "Medicare",
        "category": "CARDIAC",
        "procedure_code": "93458",
        "diagnosis_code": "I25.10",
        "title": "Cardiac Catheterization - Medicare NCD",
        "content": """MEDICARE NATIONAL COVERAGE DETERMINATION (NCD): Cardiac Catheterization

NCD ID: 210.3
Category: Cardiovascular Procedures

COVERAGE:

Diagnostic cardiac catheterization is covered when:
1. Patient has symptoms suggestive of coronary artery disease
2. Non-invasive testing suggests CAD
3. Patient is a candidate for revascularization
4. Results will guide treatment decisions

INDICATIONS:

A. DIAGNOSTIC (at least ONE):
   - Chest pain with abnormal stress test
   - Suspected coronary anomaly
   - Evaluation before valvular surgery
   - Cardiomyopathy of unclear etiology
   - Heart failure with suspected ischemic cause

B. THERAPEUTIC:
   - PCI (percutaneous coronary intervention)
   - Thrombus aspiration in STEMI
   - Balloon valvuloplasty

NON-COVERED:
- Screening in asymptomatic patients
- Repeat catheterization < 3 months without clear indication
- When patient not a revascularization candidate

EFFECTIVE DATE: 2024-01-01
""",
        "questionnaire": json.dumps([
            {"question": "Does patient have chest pain or anginal equivalent symptoms?", "answer_type": "yes/no", "required": True},
            {"question": "Has non-invasive testing (stress test) been abnormal?", "answer_type": "yes/no", "required": True},
            {"question": "Is patient a candidate for revascularization if needed?", "answer_type": "yes/no", "required": True},
            {"question": "Will results guide treatment decisions?", "answer_type": "yes/no", "required": True}
        ]),
        "decision_criteria": "APPROVE if symptoms + abnormal stress test + candidate for intervention; DENY if screening only",
        "effective_date": datetime(2024, 1, 1).date(),
        "tags": "medicare,ncd,cardiac,catheterization,cad"
    }
]

print(f"✅ Created {len(medicare_policies)} Medicare policies")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Combine All Guidelines

# COMMAND ----------

all_guidelines = mcg_guidelines + interqual_guidelines + medicare_policies

print(f"\n📊 Total Guidelines Summary:")
print(f"   MCG: {len(mcg_guidelines)}")
print(f"   InterQual: {len(interqual_guidelines)}")
print(f"   Medicare: {len(medicare_policies)}")
print(f"   TOTAL: {len(all_guidelines)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Convert to DataFrame and Write to Table

# COMMAND ----------

# Convert to Pandas DataFrame
df_pandas = pd.DataFrame(all_guidelines)
print(f"Guidelines shape: {df_pandas.shape}")
print(f"\nColumns: {df_pandas.columns.tolist()}")

# Convert to Spark DataFrame
df = spark.createDataFrame(df_pandas)

# Write to table
df.write.format("delta").mode("overwrite").saveAsTable(f"{catalog_name}.{schema_name}.clinical_guidelines")

print(f"\n✅ Written {df.count()} guidelines to {catalog_name}.{schema_name}.clinical_guidelines")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Data

# COMMAND ----------

# Check guideline counts by platform
display(spark.sql(f"""
SELECT 
    platform,
    category,
    COUNT(*) as count
FROM {catalog_name}.{schema_name}.clinical_guidelines
GROUP BY platform, category
ORDER BY platform, category
"""))

# COMMAND ----------

# Sample guidelines
display(spark.sql(f"""
SELECT 
    guideline_id,
    platform,
    category,
    procedure_code,
    title,
    SUBSTRING(content, 1, 200) as content_preview
FROM {catalog_name}.{schema_name}.clinical_guidelines
ORDER BY platform, category
"""))

# COMMAND ----------

# Show MCG questionnaires
display(spark.sql(f"""
SELECT 
    guideline_id,
    title,
    questionnaire
FROM {catalog_name}.{schema_name}.clinical_guidelines
WHERE platform = 'MCG'
"""))

# COMMAND ----------

print("✅ Setup 03 Complete: Guidelines data generated successfully!")
print("   - MCG Care Guidelines (outpatient procedures)")
print("   - InterQual Criteria (inpatient level of care)")
print("   - Medicare LCD/NCD policies")


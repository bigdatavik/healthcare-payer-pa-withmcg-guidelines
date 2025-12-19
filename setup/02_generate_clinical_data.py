# Databricks notebook source
# MAGIC %md
# MAGIC # Setup 02: Generate Synthetic Clinical Data
# MAGIC
# MAGIC This notebook generates realistic synthetic patient clinical records for Vector Store 1.
# MAGIC
# MAGIC **Data Generated:**
# MAGIC - Clinical notes from office visits
# MAGIC - Lab results (A1C, lipid panels, metabolic panels)
# MAGIC - Imaging reports (X-rays, MRIs, CT scans)
# MAGIC - Physical therapy notes
# MAGIC - Medication histories
# MAGIC
# MAGIC **Purpose:** These records will be searched by the AI agent to answer MCG/InterQual questions

# COMMAND ----------

# MAGIC %md
# MAGIC ## Imports and Setup

# COMMAND ----------

from faker import Faker
from datetime import datetime, timedelta
import random
import json
import pandas as pd
from pyspark.sql.functions import col

fake = Faker()
Faker.seed(42)
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
# MAGIC ## Generate Patient IDs

# COMMAND ----------

# Generate 50 patients
NUM_PATIENTS = 50
patient_ids = [f"PT{str(i+1).zfill(5)}" for i in range(NUM_PATIENTS)]

print(f"Generated {len(patient_ids)} patient IDs")
print(f"Sample: {patient_ids[:5]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Clinical Note Templates

# COMMAND ----------

CLINICAL_NOTE_TEMPLATES = [
    """SUBJECTIVE:
Patient is a {age}-year-old {gender} presenting with {chief_complaint}.
Pain level: {pain_level}/10
Duration: {duration}
Previous treatment: {previous_treatment}

OBJECTIVE:
Vital Signs: BP {bp}, HR {hr}, Temp {temp}F
Examination: {examination_findings}

ASSESSMENT:
{diagnosis}

PLAN:
{treatment_plan}
Follow-up in {followup_weeks} weeks.
""",
    """Chief Complaint: {chief_complaint}

HPI: Patient reports {symptom_description} for the past {duration}. {pain_description}. No relief with {failed_treatment}.

Physical Exam:
- General: {general_appearance}
- {body_system}: {examination_findings}

Impression: {diagnosis}

Plan:
1. {treatment_1}
2. {treatment_2}
3. Follow-up: {followup_weeks} weeks
4. {additional_orders}
""",
]

# COMMAND ----------

# MAGIC %md
# MAGIC ## Lab Result Templates

# COMMAND ----------

def generate_lab_results(patient_id, record_date, condition=None):
    """Generate realistic lab results"""
    
    labs = []
    
    # A1C (diabetes marker)
    if condition == "diabetes" or random.random() < 0.3:
        a1c_value = random.uniform(7.5, 10.5) if condition == "diabetes" else random.uniform(4.5, 6.4)
        labs.append({
            "record_id": f"{patient_id}_LAB_{record_date.strftime('%Y%m%d')}_A1C",
            "patient_id": patient_id,
            "record_date": record_date,
            "record_type": "LAB_RESULT",
            "content": f"""HEMOGLOBIN A1C
Result: {a1c_value:.1f}%
Reference Range: 4.0-5.6%
Status: {"HIGH - Poorly controlled diabetes" if a1c_value > 7.0 else "NORMAL"}
Performed: {record_date.strftime('%Y-%m-%d')}
""",
            "source_system": "Epic Labs",
            "provider_id": f"DR{random.randint(1000,9999)}",
            "metadata": json.dumps({"test_type": "A1C", "value": a1c_value, "unit": "percent"})
        })
    
    # Lipid Panel
    if random.random() < 0.4:
        total_chol = random.randint(180, 280)
        ldl = random.randint(100, 180)
        hdl = random.randint(30, 70)
        trig = random.randint(100, 300)
        
        labs.append({
            "record_id": f"{patient_id}_LAB_{record_date.strftime('%Y%m%d')}_LIPID",
            "patient_id": patient_id,
            "record_date": record_date,
            "record_type": "LAB_RESULT",
            "content": f"""LIPID PANEL
Total Cholesterol: {total_chol} mg/dL (Ref: <200)
LDL Cholesterol: {ldl} mg/dL (Ref: <100)
HDL Cholesterol: {hdl} mg/dL (Ref: >40)
Triglycerides: {trig} mg/dL (Ref: <150)
Interpretation: {"Elevated cholesterol, recommend statin therapy" if total_chol > 240 else "Borderline lipid levels"}
Date: {record_date.strftime('%Y-%m-%d')}
""",
            "source_system": "Epic Labs",
            "provider_id": f"DR{random.randint(1000,9999)}",
            "metadata": json.dumps({"test_type": "LIPID_PANEL", "total_chol": total_chol, "ldl": ldl})
        })
    
    return labs

# COMMAND ----------

# MAGIC %md
# MAGIC ## Imaging Report Templates

# COMMAND ----------

IMAGING_REPORTS = {
    "KNEE_XRAY": """X-RAY KNEE AP AND LATERAL
Clinical Indication: Knee pain, rule out arthritis
Technique: Standard AP and lateral views of the {side} knee

FINDINGS:
- Joint space: {joint_space_finding}
- Bone alignment: {alignment}
- Soft tissue: {soft_tissue}
- Osteophytes: {osteophytes}

IMPRESSION:
{impression}

Recommendation: {recommendation}
""",
    "KNEE_MRI": """MRI KNEE WITHOUT CONTRAST
Clinical Indication: {indication}
Technique: Multiplanar, multisequence MRI

FINDINGS:
- Meniscus: {meniscus_finding}
- ACL/PCL: {ligament_finding}
- Cartilage: {cartilage}
- Joint effusion: {effusion}
- Bone marrow: {bone_marrow}

IMPRESSION:
{impression}

""",
    "LUMBAR_MRI": """MRI LUMBAR SPINE WITHOUT CONTRAST
Clinical Indication: Low back pain, radiculopathy
Technique: Sagittal and axial T1, T2 sequences

FINDINGS:
- Disc spaces: {disc_finding}
- Spinal canal: {canal_finding}
- Neural foramina: {foraminal_finding}
- Facet joints: {facet_finding}

IMPRESSION:
{impression}
""",
}

# COMMAND ----------

# MAGIC %md
# MAGIC ## Physical Therapy Notes

# COMMAND ----------

PT_NOTE_TEMPLATE = """PHYSICAL THERAPY EVALUATION
Patient: {age} y/o {gender}
Diagnosis: {diagnosis}
Date: {date}

SUBJECTIVE:
Patient reports {pain_level}/10 pain in {body_part}.
Functional limitations: {limitations}

OBJECTIVE:
ROM: {rom_findings}
Strength: {strength_findings}
Gait: {gait_findings}

ASSESSMENT:
{assessment}

PLAN:
Treatment: {treatment_plan}
Frequency: {frequency} visits per week for {duration} weeks
Progress: {progress_note}
"""

# COMMAND ----------

# MAGIC %md
# MAGIC ## Generate Records for Each Patient

# COMMAND ----------

all_records = []

for patient_id in patient_ids:
    patient_age = random.randint(35, 85)
    patient_gender = random.choice(["male", "female"])
    
    # Assign a primary condition (affects what clinical data they have)
    primary_condition = random.choice([
        "knee_osteoarthritis",
        "diabetes",
        "cardiac",
        "back_pain",
        "general"
    ])
    
    # Generate 5-15 records per patient over the past 2 years
    num_records = random.randint(5, 15)
    
    for i in range(num_records):
        # Random date within past 2 years
        days_ago = random.randint(1, 730)
        record_date = datetime.now() - timedelta(days=days_ago)
        
        record_type = random.choice(["CLINICAL_NOTE", "CLINICAL_NOTE", "LAB_RESULT", "IMAGING_REPORT", "PT_NOTE"])
        
        if record_type == "CLINICAL_NOTE":
            # Generate clinical note based on condition
            if primary_condition == "knee_osteoarthritis":
                content = CLINICAL_NOTE_TEMPLATES[0].format(
                    age=patient_age,
                    gender=patient_gender,
                    chief_complaint="right knee pain",
                    pain_level=random.randint(5, 8),
                    duration=f"{random.randint(4, 24)} months",
                    previous_treatment=random.choice([
                        "NSAIDs, ice, rest",
                        "physical therapy (12 weeks completed)",
                        "cortisone injection 6 months ago",
                        "home exercises, weight loss"
                    ]),
                    bp=f"{random.randint(110,140)}/{random.randint(70,90)}",
                    hr=random.randint(60, 90),
                    temp=round(random.uniform(97.5, 98.8), 1),
                    examination_findings=random.choice([
                        "tenderness along medial joint line, crepitus with range of motion, limited flexion to 110 degrees",
                        "joint line tenderness, positive McMurray test, effusion present",
                        "decreased ROM, pain with weight bearing, antalgic gait"
                    ]),
                    diagnosis="Right knee osteoarthritis, moderate severity",
                    treatment_plan=random.choice([
                        "Continue PT, consider viscosupplementation if no improvement",
                        "NSAIDs, activity modification, MRI ordered to assess cartilage",
                        "Home exercise program, weight loss counseling, follow-up 6 weeks"
                    ]),
                    followup_weeks=random.choice([4, 6, 8, 12])
                )
            
            elif primary_condition == "diabetes":
                content = CLINICAL_NOTE_TEMPLATES[1].format(
                    chief_complaint="diabetes follow-up",
                    symptom_description=random.choice([
                        "polyuria and polydipsia",
                        "fatigue and blurred vision",
                        "foot numbness bilaterally"
                    ]),
                    duration=f"{random.randint(6, 36)} months",
                    pain_description="Denies chest pain or shortness of breath",
                    failed_treatment="diet modification alone",
                    general_appearance="well-appearing, no acute distress",
                    body_system="Cardiovascular",
                    examination_findings="regular rate and rhythm, no murmurs",
                    diagnosis="Type 2 Diabetes Mellitus, poorly controlled (A1C 8.5%)",
                    treatment_1="Increase metformin to 1000mg BID",
                    treatment_2="Add empagliflozin 10mg daily",
                    followup_weeks=12,
                    additional_orders="Repeat A1C in 3 months, referral to dietitian"
                )
            
            else:  # general/other conditions
                content = CLINICAL_NOTE_TEMPLATES[0].format(
                    age=patient_age,
                    gender=patient_gender,
                    chief_complaint=random.choice(["fatigue", "headache", "joint pain", "annual checkup"]),
                    pain_level=random.randint(2, 6),
                    duration=f"{random.randint(1, 12)} weeks",
                    previous_treatment="rest, hydration, OTC medication",
                    bp=f"{random.randint(110,135)}/{random.randint(70,85)}",
                    hr=random.randint(65, 85),
                    temp=round(random.uniform(97.8, 98.6), 1),
                    examination_findings="unremarkable, no acute findings",
                    diagnosis="Benign symptoms, no concerning features",
                    treatment_plan="Reassurance, continue current management",
                    followup_weeks=random.choice([4, 8, 12, 26])
                )
            
            all_records.append({
                "record_id": f"{patient_id}_NOTE_{record_date.strftime('%Y%m%d')}_{i}",
                "patient_id": patient_id,
                "record_date": record_date,
                "record_type": "CLINICAL_NOTE",
                "content": content,
                "source_system": random.choice(["Epic", "Cerner"]),
                "provider_id": f"DR{random.randint(1000,9999)}",
                "metadata": json.dumps({"condition": primary_condition})
            })
        
        elif record_type == "LAB_RESULT":
            labs = generate_lab_results(patient_id, record_date, primary_condition if primary_condition == "diabetes" else None)
            all_records.extend(labs)
        
        elif record_type == "IMAGING_REPORT":
            if primary_condition == "knee_osteoarthritis":
                content = IMAGING_REPORTS["KNEE_XRAY"].format(
                    side=random.choice(["right", "left"]),
                    joint_space_finding=random.choice([
                        "Moderate narrowing of medial compartment",
                        "Severe narrowing with bone-on-bone contact medially",
                        "Mild to moderate joint space narrowing"
                    ]),
                    alignment="Normal femorotibial alignment",
                    soft_tissue="No significant effusion",
                    osteophytes=random.choice([
                        "Small osteophytes at joint margins",
                        "Moderate osteophytic lipping",
                        "Large osteophytes with subchondral sclerosis"
                    ]),
                    impression=random.choice([
                        "Moderate degenerative changes consistent with osteoarthritis",
                        "Advanced osteoarthritis with significant joint space loss",
                        "Mild to moderate osteoarthritic changes"
                    ]),
                    recommendation=random.choice([
                        "Clinical correlation. MRI if meniscal tear suspected.",
                        "Consider advanced imaging if symptoms persist.",
                        "Weight bearing films if varus/valgus deformity suspected."
                    ])
                )
                imaging_type = "X-RAY"
            else:
                content = IMAGING_REPORTS["LUMBAR_MRI"].format(
                    disc_finding=random.choice([
                        "Mild disc desiccation L4-L5 and L5-S1",
                        "Disc bulge at L4-L5 without significant stenosis",
                        "Disc height preserved at all levels"
                    ]),
                    canal_finding="Patent, no significant stenosis",
                    foraminal_finding=random.choice([
                        "Mild bilateral foraminal narrowing L4-L5",
                        "Patent at all levels",
                        "Moderate left foraminal stenosis L5-S1"
                    ]),
                    facet_finding="Mild degenerative changes",
                    impression=random.choice([
                        "Mild degenerative disc disease without significant stenosis",
                        "Disc bulge L4-L5, mild foraminal narrowing",
                        "No acute findings"
                    ])
                )
                imaging_type = "MRI"
            
            all_records.append({
                "record_id": f"{patient_id}_IMG_{record_date.strftime('%Y%m%d')}_{imaging_type}",
                "patient_id": patient_id,
                "record_date": record_date,
                "record_type": "IMAGING_REPORT",
                "content": content,
                "source_system": "Radiology PACS",
                "provider_id": f"DR{random.randint(1000,9999)}",
                "metadata": json.dumps({"imaging_type": imaging_type})
            })
        
        elif record_type == "PT_NOTE":
            weeks_completed = random.randint(4, 16)
            content = PT_NOTE_TEMPLATE.format(
                age=patient_age,
                gender=patient_gender,
                diagnosis=random.choice([
                    "Right knee osteoarthritis",
                    "Low back pain",
                    "Shoulder impingement",
                    "Post-op knee replacement"
                ]),
                date=record_date.strftime('%Y-%m-%d'),
                pain_level=random.randint(3, 7),
                body_part=random.choice(["right knee", "low back", "left shoulder"]),
                limitations=random.choice([
                    "difficulty with stairs, prolonged standing",
                    "cannot lift objects from floor",
                    "limited overhead reach"
                ]),
                rom_findings=random.choice([
                    "Flexion 0-110 degrees (limited), extension 0 degrees",
                    "Forward flexion 0-140 degrees, abduction 0-120 degrees",
                    "WNL all planes"
                ]),
                strength_findings=random.choice([
                    "4/5 quadriceps, 4+/5 hamstrings",
                    "3+/5 hip abductors, 4/5 hip extensors",
                    "5/5 throughout"
                ]),
                gait_findings=random.choice([
                    "Antalgic gait favoring right side",
                    "Normal gait pattern",
                    "Reduced stride length"
                ]),
                assessment=f"Patient improving with therapy. Completed {weeks_completed} weeks of treatment.",
                treatment_plan="Therapeutic exercise, manual therapy, modalities",
                frequency=random.choice([2, 3]),
                duration=random.choice([4, 6, 8]),
                progress_note=random.choice([
                    "Good progress, advancing exercises",
                    "Moderate progress, continue current program",
                    "Excellent progress, preparing for discharge"
                ])
            )
            
            all_records.append({
                "record_id": f"{patient_id}_PT_{record_date.strftime('%Y%m%d')}",
                "patient_id": patient_id,
                "record_date": record_date,
                "record_type": "PT_NOTE",
                "content": content,
                "source_system": "PT Documentation System",
                "provider_id": f"PT{random.randint(1000,9999)}",
                "metadata": json.dumps({"weeks_completed": weeks_completed})
            })

print(f"✅ Generated {len(all_records)} clinical records for {len(patient_ids)} patients")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Convert to DataFrame and Write to Table

# COMMAND ----------

# Convert to Pandas DataFrame first
df_pandas = pd.DataFrame(all_records)
print(f"Records shape: {df_pandas.shape}")
print(f"\nSample records:")
print(df_pandas.head(3))

# Convert to Spark DataFrame
df = spark.createDataFrame(df_pandas)

# Write to table
df.write.format("delta").mode("overwrite").saveAsTable(f"{catalog_name}.{schema_name}.patient_clinical_records")

print(f"\n✅ Written {df.count()} records to {catalog_name}.{schema_name}.patient_clinical_records")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Data

# COMMAND ----------

# Check record counts by type
display(spark.sql(f"""
SELECT 
    record_type,
    COUNT(*) as count,
    COUNT(DISTINCT patient_id) as unique_patients
FROM {catalog_name}.{schema_name}.patient_clinical_records
GROUP BY record_type
ORDER BY count DESC
"""))

# COMMAND ----------

# Sample records
display(spark.sql(f"""
SELECT 
    record_id,
    patient_id,
    record_date,
    record_type,
    SUBSTRING(content, 1, 200) as content_preview
FROM {catalog_name}.{schema_name}.patient_clinical_records
ORDER BY record_date DESC
LIMIT 10
"""))

# COMMAND ----------

print("✅ Setup 02 Complete: Clinical data generated successfully!")


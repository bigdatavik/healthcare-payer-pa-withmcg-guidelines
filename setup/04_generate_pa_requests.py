# Databricks notebook source
# MAGIC %md
# MAGIC # Setup 04: Generate Prior Authorization Requests - Demo Quality
# MAGIC
# MAGIC Generates 10 demo PA requests matching our 10 demo patients.
# MAGIC Each request is aligned with the clinical documentation.

# COMMAND ----------

import random
import pandas as pd
from datetime import datetime, timedelta
import json

random.seed(42)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Import Configuration

# COMMAND ----------

import sys
import os
sys.path.append(os.path.abspath('..'))
from shared.config import get_config, print_config

cfg = get_config()
print_config(cfg)

# COMMAND ----------

# Use config values
catalog_name = cfg.catalog
schema_name = cfg.schema

print(f"📊 Generating PA requests:")
print(f"   Target table: {cfg.auth_requests_table}")
print(f"   Number of demo requests: 10")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Demo PA Requests (10 High-Quality Cases)

# COMMAND ----------

# ============================================================================
# 10 DEMO PA REQUESTS - Aligned with clinical documentation
# ============================================================================

demo_requests = [
    # ========================================
    # APPROVED CASES (4 patients)
    # ========================================
    {
        "request_id": "PA000001",
        "patient_id": "PT00001",
        "provider_id": "DR1234",
        "procedure_code": "29881",
        "procedure_description": "Arthroscopic Knee Meniscectomy",
        "diagnosis_code": "M23.205",
        "diagnosis_description": "Derangement of medial meniscus due to old tear, right knee",
        "clinical_notes": "58M with right knee medial meniscus tear. MRI CONFIRMED complex tear posterior horn. Completed 14 weeks conservative treatment: 12 PT sessions (2x/week), NSAIDs 14 weeks, activity modification. FAILED conservative management - persistent pain 6/10, mechanical symptoms (clicking, giving way). Grade 2 chondromalacia (NOT severe OA). Functional limitations: cannot squat, difficulty stairs. All MCG criteria met. EXPECTED: APPROVED ✓",
        "urgency_level": "ROUTINE",
        "insurance_plan": "Commercial PPO",
        "request_date": datetime.now() - timedelta(days=5),
        "request_status": "PENDING"
    },
    {
        "request_id": "PA000002",
        "patient_id": "PT00016",
        "provider_id": "DR5678",
        "procedure_code": "27447",
        "procedure_description": "Total Knee Arthroplasty (TKA)",
        "diagnosis_code": "M17.11",
        "diagnosis_description": "Unilateral primary osteoarthritis, right knee",
        "clinical_notes": "68F with END-STAGE right knee osteoarthritis. X-ray: Grade 4 OA, BONE-ON-BONE medial compartment, complete joint space loss. Completed 12 weeks conservative treatment: 8 weeks PT (limited by pain), NSAIDs max dose, intra-articular steroid injection (3-week relief only). SEVERE functional impairment: cannot walk >1 block, cannot climb stairs, uses cane. Varus deformity 8 degrees. All TKA criteria met. EXPECTED: APPROVED ✓",
        "urgency_level": "URGENT",
        "insurance_plan": "Medicare Advantage",
        "request_date": datetime.now() - timedelta(days=3),
        "request_status": "PENDING"
    },
    {
        "request_id": "PA000003",
        "patient_id": "PT00025",
        "provider_id": "DR9012",
        "procedure_code": "93015",
        "procedure_description": "Cardiovascular Stress Test with ECG",
        "diagnosis_code": "I25.10",
        "diagnosis_description": "Atherosclerotic heart disease of native coronary artery",
        "clinical_notes": "62M with exertional chest discomfort. MULTIPLE cardiac risk factors: HTN, Type 2 DM, dyslipidemia (LDL 165), former smoker (30 pack-years), family history (father MI age 58). ECG shows non-specific ST changes V4-V6, old inferior Q waves (possible prior silent MI). Troponin negative. Chest X-ray: cardiomegaly present. HIGH pre-test probability for CAD. Stress test indicated for risk stratification. EXPECTED: APPROVED ✓",
        "urgency_level": "URGENT",
        "insurance_plan": "Commercial HMO",
        "request_date": datetime.now() - timedelta(days=2),
        "request_status": "PENDING"
    },
    {
        "request_id": "PA000004",
        "patient_id": "PT00003",
        "provider_id": "DR3456",
        "procedure_code": "72148",
        "procedure_description": "MRI Lumbar Spine Without Contrast",
        "diagnosis_code": "M54.5",
        "diagnosis_description": "Low back pain with radiculopathy",
        "clinical_notes": "45F with severe lumbar radiculopathy L5 distribution. RED FLAGS: PROGRESSIVE motor weakness - ankle dorsiflexion 4/5 → 3/5, FOOT DROP developing. Numbness L5 distribution, diminished ankle reflex, positive SLR 30 degrees. Completed 6 weeks PT - NO improvement, WORSENING weakness. URGENT MRI needed to evaluate for nerve compression requiring surgical decompression. Neurological emergency. EXPECTED: APPROVED ✓",
        "urgency_level": "URGENT",
        "insurance_plan": "Commercial PPO",
        "request_date": datetime.now() - timedelta(days=1),
        "request_status": "PENDING"
    },
    
    # ========================================
    # MANUAL_REVIEW CASES (3 patients)
    # ========================================
    {
        "request_id": "PA000005",
        "patient_id": "PT00005",
        "provider_id": "DR7890",
        "procedure_code": "73221",
        "procedure_description": "MRI Shoulder Without Contrast",
        "diagnosis_code": "M75.100",
        "diagnosis_description": "Unspecified rotator cuff tear or rupture, shoulder",
        "clinical_notes": "52M with right shoulder pain, suspected rotator cuff tear. Positive Hawkins/Neer tests. Completed ONLY 4 weeks PT with partial improvement (pain 6/10 → 4/10, ROM improved). Patient requesting MRI now due to work demands, cannot wait for full 6-week conservative treatment. ISSUE: MCG typically requires 6 weeks conservative treatment, patient only completed 4 weeks. EXPECTED: MANUAL_REVIEW ⚠️",
        "urgency_level": "ROUTINE",
        "insurance_plan": "Commercial PPO",
        "request_date": datetime.now() - timedelta(days=4),
        "request_status": "PENDING"
    },
    {
        "request_id": "PA000006",
        "patient_id": "PT00007",
        "provider_id": "DR2468",
        "procedure_code": "29914",
        "procedure_description": "Hip Arthroscopy with Labral Repair",
        "diagnosis_code": "M24.051",
        "diagnosis_description": "Loose body in left hip",
        "clinical_notes": "35F with left hip pain, clicking, suspected labral tear. Positive FABER/impingement tests. Completed 8 weeks PT with persistent mechanical symptoms. X-ray shows mild hip dysplasia, no fracture. ISSUE: No MRI confirmation of labral tear - only clinical suspicion and plain X-ray. Most guidelines require MRI confirmation before arthroscopy. EXPECTED: MANUAL_REVIEW ⚠️",
        "urgency_level": "ROUTINE",
        "insurance_plan": "Commercial HMO",
        "request_date": datetime.now() - timedelta(days=6),
        "request_status": "PENDING"
    },
    {
        "request_id": "PA000007",
        "patient_id": "PT00010",
        "provider_id": "DR1357",
        "procedure_code": "73721",
        "procedure_description": "MRI Knee Without Contrast",
        "diagnosis_code": "S83.511A",
        "diagnosis_description": "Sprain of anterior cruciate ligament of right knee, initial encounter",
        "clinical_notes": "28M with ACUTE left knee injury 2 weeks ago (basketball). Heard 'pop', immediate swelling. Physical exam: positive Lachman (2+ laxity), positive anterior drawer, positive pivot shift. X-ray negative for fracture. ISSUE: This is ACUTE injury (2 weeks old), NO conservative treatment attempted yet. Patient requesting MRI for surgical planning. No red flags for urgent imaging (no fracture, no locked knee). MCG typically requires trial of conservative treatment for knee MRI in non-acute setting. EXPECTED: MANUAL_REVIEW ⚠️",
        "urgency_level": "ROUTINE",
        "insurance_plan": "Commercial PPO",
        "request_date": datetime.now() - timedelta(days=7),
        "request_status": "PENDING"
    },
    
    # ========================================
    # DENIED CASES (3 patients)
    # ========================================
    {
        "request_id": "PA000008",
        "patient_id": "PT00012",
        "provider_id": "DR9753",
        "procedure_code": "22630",
        "procedure_code_2": "22614",
        "procedure_description": "Lumbar Spine Fusion L4-L5",
        "diagnosis_code": "M51.26",
        "diagnosis_description": "Other intervertebral disc displacement, lumbar region",
        "clinical_notes": "40M with chronic low back pain (5 years, stable). NO radiculopathy, NO leg pain, NO weakness, NO numbness. Neurological exam: COMPLETELY NORMAL (motor 5/5, sensory intact, reflexes symmetric, negative SLR). MRI (self-paid): Mild disc bulge L4-L5, NO nerve compression, NO stenosis. Patient requesting fusion surgery per chiropractor recommendation. ISSUES: (1) NO neurological deficits, (2) NO nerve compression on imaging, (3) NO conservative treatment attempted (no PT, no structured program). NOT A SURGICAL CANDIDATE. EXPECTED: DENIED ✗",
        "urgency_level": "ROUTINE",
        "insurance_plan": "Commercial PPO",
        "request_date": datetime.now() - timedelta(days=8),
        "request_status": "PENDING"
    },
    {
        "request_id": "PA000009",
        "patient_id": "PT00018",
        "provider_id": "DR8642",
        "procedure_code": "15830",
        "procedure_description": "Excision of Excessive Skin and Subcutaneous Tissue (Abdominoplasty)",
        "diagnosis_code": "L90.6",
        "diagnosis_description": "Striae atrophicae (stretch marks)",
        "clinical_notes": "33F requesting panniculectomy/abdominoplasty. Moderate abdominal skin laxity post-pregnancy (2 children, youngest age 3). Striae distensae present. ISSUES: (1) NO functional impairment, (2) NO recurrent skin infections, (3) NO intertrigo/rashes, (4) NO hygiene issues, (5) NO back pain from pannus, (6) Patient EXPLICITLY states purely COSMETIC motivation ('want to look better in clothes'). This is COSMETIC SURGERY, NOT medically necessary. EXPECTED: DENIED ✗",
        "urgency_level": "ROUTINE",
        "insurance_plan": "Commercial HMO",
        "request_date": datetime.now() - timedelta(days=9),
        "request_status": "PENDING"
    },
    {
        "request_id": "PA000010",
        "patient_id": "PT00020",
        "provider_id": "DR7531",
        "procedure_code": "73721",
        "procedure_description": "MRI Knee Without Contrast",
        "diagnosis_code": "M25.561",
        "diagnosis_description": "Pain in right knee",
        "clinical_notes": "50F with NEW onset left knee pain (3 weeks total duration). Started after gardening. Pain 4/10, no trauma, no locking, no instability. Exam: Mild tenderness, full ROM, no effusion, normal gait. Patient demanding MRI after 'reading online about meniscus tears'. ISSUES: (1) NO conservative treatment attempted (no PT, no formal NSAID trial), (2) Only 3 weeks of symptoms, (3) NO red flags (no mechanical symptoms, no instability, no trauma, normal exam), (4) Does NOT meet MCG criteria for knee MRI. Should complete 6 weeks conservative treatment first. EXPECTED: DENIED ✗",
        "urgency_level": "ROUTINE",
        "insurance_plan": "Commercial PPO",
        "request_date": datetime.now() - timedelta(days=10),
        "request_status": "PENDING"
    }
]

print(f"✅ Created {len(demo_requests)} demo PA requests")
print(f"   - APPROVED: 4 requests (PA000001-PA000004)")
print(f"   - MANUAL_REVIEW: 3 requests (PA000005-PA000007)")
print(f"   - DENIED: 3 requests (PA000008-PA000010)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load into DataFrame and Write to Table

# COMMAND ----------

# Convert to DataFrame
pa_df = pd.DataFrame(demo_requests)

# DON'T convert datetime to string - keep as datetime for TIMESTAMP column
# The table schema expects TIMESTAMP, not STRING

# Add default values for optional fields
pa_df['decision'] = None
pa_df['decision_date'] = None
pa_df['explanation'] = None
pa_df['confidence_score'] = None
pa_df['processing_time_seconds'] = None

# Convert to Spark DataFrame
spark_df = spark.createDataFrame(pa_df)

# COMMAND ----------

# Write to table (overwrite mode to ensure clean data)
table_name = f"{catalog_name}.{schema_name}.authorization_requests"

# Use overwriteSchema to replace the table schema with our new schema
spark_df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(table_name)

print(f"✅ Loaded {spark_df.count()} PA requests into table: {table_name}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verification

# COMMAND ----------

# Verify data
result_df = spark.sql(f"""
SELECT 
    request_id,
    patient_id,
    procedure_code,
    procedure_description,
    request_status,
    SUBSTRING(clinical_notes, 1, 100) as notes_preview
FROM {table_name}
ORDER BY request_id
""")

display(result_df)

# COMMAND ----------

# Summary by expected outcome (extracted from clinical_notes)
summary_df = spark.sql(f"""
SELECT 
    CASE 
        WHEN clinical_notes LIKE '%EXPECTED: APPROVED%' THEN 'APPROVED'
        WHEN clinical_notes LIKE '%EXPECTED: MANUAL_REVIEW%' THEN 'MANUAL_REVIEW'
        WHEN clinical_notes LIKE '%EXPECTED: DENIED%' THEN 'DENIED'
        ELSE 'UNKNOWN'
    END as expected_outcome,
    COUNT(*) as count,
    COLLECT_LIST(request_id) as request_ids
FROM {table_name}
GROUP BY expected_outcome
ORDER BY expected_outcome
""")

print("\n📊 Summary by Expected Outcome:")
display(summary_df)

# COMMAND ----------

print("=" * 80)
print("PA REQUESTS LOADED!")
print("=" * 80)
print(f"✅ Table: {table_name}")
print(f"✅ Total Requests: 10")
print()
print("Expected Outcomes:")
print(f"   APPROVED: 4 requests (PT00001, PT00016, PT00025, PT00003)")
print(f"   MANUAL_REVIEW: 3 requests (PT00005, PT00007, PT00010)")
print(f"   DENIED: 3 requests (PT00012, PT00018, PT00020)")
print()
print(f"All requests are in PENDING status and ready for processing in the app.")
print("=" * 80)

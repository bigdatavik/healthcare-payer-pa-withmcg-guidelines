# Databricks notebook source
# MAGIC %md
# MAGIC # Setup 04: Generate Prior Authorization Requests
# MAGIC
# MAGIC Generates synthetic PA requests that reference existing patients and guidelines.

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
NUM_REQUESTS = cfg.num_pa_requests

print(f"📊 Generating PA requests:")
print(f"   Target table: {cfg.auth_requests_table}")
print(f"   Number of requests: {NUM_REQUESTS}")

# COMMAND ----------

# Get existing patients
patients_df = spark.sql(f"SELECT DISTINCT patient_id FROM {catalog_name}.{schema_name}.patient_clinical_records")
patient_ids = [row.patient_id for row in patients_df.collect()]

# Get existing guidelines (filter out None values)
guidelines_df = spark.sql(f"""
SELECT guideline_id, platform, procedure_code, diagnosis_code, title 
FROM {catalog_name}.{schema_name}.clinical_guidelines
WHERE procedure_code IS NOT NULL AND diagnosis_code IS NOT NULL
""")
guidelines = [row.asDict() for row in guidelines_df.collect()]

print(f"Patients: {len(patient_ids)}, Guidelines: {len(guidelines)}")

# COMMAND ----------

# Generate PA requests (uses NUM_REQUESTS from config)
pa_requests = []

# Common procedure/diagnosis codes as fallback
common_procedures = [
    ("29881", "M23.205", "Knee arthroscopy with meniscectomy"),
    ("93000", "I10", "Electrocardiogram"),
    ("70553", "G43.909", "MRI brain with contrast"),
    ("97110", "M54.5", "Physical therapy therapeutic exercises"),
    ("99214", "E11.9", "Office visit, established patient"),
    ("73721", "M25.561", "MRI joint of right knee"),
    ("93015", "I25.10", "Cardiovascular stress test"),
    ("77057", "N63.00", "Screening mammography"),
    ("95810", "G47.33", "Polysomnography"),
    ("20610", "M25.571", "Arthrocentesis, major joint")
]

for i in range(NUM_REQUESTS):
    patient_id = random.choice(patient_ids)
    
    # Use guideline if available, otherwise use common codes
    if guidelines:
        guideline = random.choice(guidelines)
        procedure_code = guideline['procedure_code']
        diagnosis_code = guideline['diagnosis_code']
        procedure_description = guideline.get('title', 'Medical procedure')
    else:
        # Fall back to common procedures
        proc_code, diag_code, proc_desc = random.choice(common_procedures)
        procedure_code = proc_code
        diagnosis_code = diag_code
        procedure_description = proc_desc
    
    request_date = datetime.now() - timedelta(days=random.randint(1, 90))
    
    pa_requests.append({
        "request_id": f"PA{str(i+1).zfill(6)}",
        "patient_id": patient_id,
        "provider_id": f"DR{random.randint(1000,9999)}",
        "procedure_code": procedure_code,
        "procedure_description": procedure_description,
        "diagnosis_code": diagnosis_code,
        "diagnosis_description": "See procedure description",
        "clinical_notes": f"Patient presents for {procedure_description}. See attached clinical records.",
        "urgency_level": random.choice(["ROUTINE", "ROUTINE", "ROUTINE", "URGENT", "STAT"]),
        "insurance_plan": random.choice(["Medicare Advantage", "Commercial PPO", "Commercial HMO"]),
        "request_date": request_date,
        "decision": None,
        "decision_date": None,
        "confidence_score": None,
        "mcg_code": None,
        "explanation": None,
        "reviewed_by": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    })

# COMMAND ----------

df_pandas = pd.DataFrame(pa_requests)
df = spark.createDataFrame(df_pandas)
df.write.format("delta").mode("overwrite").saveAsTable(f"{catalog_name}.{schema_name}.authorization_requests")

print(f"✅ Generated {len(pa_requests)} PA requests")

# COMMAND ----------

display(spark.sql(f"SELECT * FROM {catalog_name}.{schema_name}.authorization_requests LIMIT 10"))

# COMMAND ----------

print("✅ Setup 04 Complete: PA requests generated!")

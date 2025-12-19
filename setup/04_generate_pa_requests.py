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

dbutils.widgets.text("catalog_name", "healthcare_payer_pa_withmcg_guidelines_dev", "Catalog Name")
dbutils.widgets.text("schema_name", "main", "Schema Name")

catalog_name = dbutils.widgets.get("catalog_name")
schema_name = dbutils.widgets.get("schema_name")

# COMMAND ----------

# Get existing patients
patients_df = spark.sql(f"SELECT DISTINCT patient_id FROM {catalog_name}.{schema_name}.patient_clinical_records")
patient_ids = [row.patient_id for row in patients_df.collect()]

# Get existing guidelines
guidelines_df = spark.sql(f"SELECT guideline_id, platform, procedure_code, diagnosis_code, title FROM {catalog_name}.{schema_name}.clinical_guidelines")
guidelines = [row.asDict() for row in guidelines_df.collect()]

print(f"Patients: {len(patient_ids)}, Guidelines: {len(guidelines)}")

# COMMAND ----------

# Generate 30 PA requests
pa_requests = []

for i in range(30):
    patient_id = random.choice(patient_ids)
    guideline = random.choice(guidelines)
    
    request_date = datetime.now() - timedelta(days=random.randint(1, 90))
    
    pa_requests.append({
        "request_id": f"PA{str(i+1).zfill(6)}",
        "patient_id": patient_id,
        "provider_id": f"DR{random.randint(1000,9999)}",
        "procedure_code": guideline['procedure_code'],
        "procedure_description": guideline['title'],
        "diagnosis_code": guideline['diagnosis_code'],
        "diagnosis_description": "See procedure description",
        "clinical_notes": f"Patient presents for {guideline['title']}. See attached clinical records.",
        "urgency_level": random.choice(["ROUTINE", "ROUTINE", "ROUTINE", "URGENT", "STAT"]),
        "insurance_plan": random.choice(["Medicare Advantage", "Commercial PPO", "Commercial HMO"]),
        "request_date": request_date,
        "decision": None,
        "decision_date": None,
        "confidence_score": None,
        "mcg_code": None,
        "explanation": None,
        "reviewed_by": None
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


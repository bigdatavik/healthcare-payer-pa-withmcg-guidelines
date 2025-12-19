# Databricks notebook source
# MAGIC %md
# MAGIC # Setup 01: Create Catalog and Schema
# MAGIC
# MAGIC This notebook creates the Unity Catalog and schema for the Prior Authorization Agent.
# MAGIC
# MAGIC **Resources Created:**
# MAGIC - Unity Catalog: `healthcare_payer_pa_withmcg_guidelines_dev`
# MAGIC - Schema: `main`
# MAGIC - Tables: `authorization_requests`, `patient_clinical_records`, `clinical_guidelines`

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
# MAGIC ## Create Catalog

# COMMAND ----------

# Create catalog if not exists
spark.sql(f"""
CREATE CATALOG IF NOT EXISTS {catalog_name}
COMMENT 'Prior Authorization Agent - Healthcare Payer'
""")

print(f"✅ Catalog '{catalog_name}' created/verified")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Schema

# COMMAND ----------

# Create schema
spark.sql(f"""
CREATE SCHEMA IF NOT EXISTS {catalog_name}.{schema_name}
COMMENT 'Main schema for PA agent data'
""")

print(f"✅ Schema '{catalog_name}.{schema_name}' created/verified")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Tables

# COMMAND ----------

# MAGIC %md
# MAGIC ### Table 1: authorization_requests

# COMMAND ----------

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {catalog_name}.{schema_name}.authorization_requests (
  request_id STRING NOT NULL,
  patient_id STRING NOT NULL,
  provider_id STRING,
  procedure_code STRING NOT NULL COMMENT 'CPT code',
  procedure_description STRING,
  diagnosis_code STRING NOT NULL COMMENT 'ICD-10 code',
  diagnosis_description STRING,
  clinical_notes STRING COMMENT 'Unstructured clinical notes from provider',
  urgency_level STRING COMMENT 'STAT, URGENT, ROUTINE',
  insurance_plan STRING,
  request_date TIMESTAMP NOT NULL,
  decision STRING COMMENT 'APPROVED, DENIED, MANUAL_REVIEW',
  decision_date TIMESTAMP,
  confidence_score DOUBLE COMMENT 'AI confidence 0-1',
  mcg_code STRING COMMENT 'MCG guideline code used',
  explanation STRING COMMENT 'Human-readable decision explanation',
  reviewed_by STRING COMMENT 'Nurse ID if manual review',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
USING DELTA
COMMENT 'Prior authorization requests and decisions'
""")

print(f"✅ Table 'authorization_requests' created")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Table 2: patient_clinical_records (Vector Store 1)

# COMMAND ----------

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {catalog_name}.{schema_name}.patient_clinical_records (
  record_id STRING NOT NULL,
  patient_id STRING NOT NULL,
  record_date TIMESTAMP NOT NULL,
  record_type STRING NOT NULL COMMENT 'CLINICAL_NOTE, LAB_RESULT, IMAGING_REPORT, PT_NOTE, MEDICATION',
  content STRING NOT NULL COMMENT 'Full text content for vector embedding',
  source_system STRING COMMENT 'Epic, Cerner, etc',
  provider_id STRING,
  metadata STRING COMMENT 'JSON metadata',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
USING DELTA
COMMENT 'Patient clinical documents for Vector Store 1 (semantic search)'
""")

print(f"✅ Table 'patient_clinical_records' created")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Table 3: clinical_guidelines (Vector Store 2)

# COMMAND ----------

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {catalog_name}.{schema_name}.clinical_guidelines (
  guideline_id STRING NOT NULL,
  platform STRING NOT NULL COMMENT 'MCG, InterQual, Medicare',
  category STRING NOT NULL COMMENT 'OUTPATIENT_PROCEDURE, INPATIENT_ADMISSION, IMAGING, DME',
  procedure_code STRING COMMENT 'CPT code if applicable',
  diagnosis_code STRING COMMENT 'ICD-10 code if applicable',
  title STRING NOT NULL,
  content STRING NOT NULL COMMENT 'Full guideline text including questionnaire',
  questionnaire STRING COMMENT 'JSON array of MCG/InterQual questions',
  decision_criteria STRING COMMENT 'Approval/denial logic',
  effective_date DATE,
  tags STRING COMMENT 'Comma-separated tags',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
USING DELTA
COMMENT 'MCG, InterQual, and Medicare guidelines for Vector Store 2'
""")

print(f"✅ Table 'clinical_guidelines' created")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Setup

# COMMAND ----------

# Show tables
display(spark.sql(f"SHOW TABLES IN {catalog_name}.{schema_name}"))

# COMMAND ----------

# Show table details
for table in ["authorization_requests", "patient_clinical_records", "clinical_guidelines"]:
    print(f"\n{'='*60}")
    print(f"Table: {catalog_name}.{schema_name}.{table}")
    print(f"{'='*60}")
    df = spark.sql(f"DESCRIBE TABLE {catalog_name}.{schema_name}.{table}")
    df.show(50, truncate=False)

# COMMAND ----------

print("✅ Setup 01 Complete: Catalog and Schema created successfully!")


# Databricks notebook source
# MAGIC %md
# MAGIC # Setup 01: Create Catalog and Schema
# MAGIC
# MAGIC This notebook creates the Unity Catalog and schema for the Prior Authorization Agent.
# MAGIC
# MAGIC **Configuration:** Reads from config.yaml via shared.config module
# MAGIC
# MAGIC **Resources Created:**
# MAGIC - Unity Catalog
# MAGIC - Schema
# MAGIC - Tables: `authorization_requests`, `patient_clinical_records`, `clinical_guidelines`

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

print(f"📊 Creating catalog and schema:")
print(f"   Catalog: {catalog_name}")
print(f"   Schema: {schema_name}")

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
# MAGIC ## Create Volumes for Raw Documents

# COMMAND ----------

# Create volume for clinical records (before chunking)
spark.sql(f"""
CREATE VOLUME IF NOT EXISTS {catalog_name}.{schema_name}.{cfg.volume_clinical}
COMMENT 'Raw clinical documents before chunking for vector search'
""")

print(f"✅ Volume '{cfg.volume_clinical}' created")
print(f"   Path: {cfg.clinical_volume_path}")

# COMMAND ----------

# Create volume for guidelines (before chunking)
spark.sql(f"""
CREATE VOLUME IF NOT EXISTS {catalog_name}.{schema_name}.{cfg.volume_guidelines}
COMMENT 'Raw MCG/InterQual guideline documents before chunking'
""")

print(f"✅ Volume '{cfg.volume_guidelines}' created")
print(f"   Path: {cfg.guidelines_volume_path}")

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
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)
USING DELTA
COMMENT 'Prior authorization requests and decisions'
""")

print(f"✅ Table 'authorization_requests' created")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Table 1b: pa_audit_trail (Audit Trail for Q&A)

# COMMAND ----------

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {catalog_name}.{schema_name}.pa_audit_trail (
  audit_id STRING NOT NULL COMMENT 'Unique identifier: request_id_Q1, request_id_Q2, etc',
  request_id STRING NOT NULL COMMENT 'Links to authorization_requests.request_id',
  question_number INT NOT NULL COMMENT 'Sequential number: 1, 2, 3, 4...',
  question_text STRING NOT NULL COMMENT 'MCG/InterQual question text',
  answer STRING NOT NULL COMMENT 'YES or NO',
  evidence STRING COMMENT 'Clinical evidence used to answer',
  evidence_source STRING COMMENT 'CLINICAL_NOTE, LAB_RESULT, XRAY, PT_NOTE, etc',
  confidence DOUBLE COMMENT 'AI confidence for this answer (0.0-1.0)',
  created_at TIMESTAMP COMMENT 'When this Q&A was recorded'
)
USING DELTA
COMMENT 'Detailed audit trail showing MCG Q&A breakdown with evidence for each PA request'
""")

print(f"✅ Table 'pa_audit_trail' created")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Table 2: patient_clinical_records (Full Records - Operational)

# COMMAND ----------

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {catalog_name}.{schema_name}.patient_clinical_records (
  record_id STRING NOT NULL,
  patient_id STRING NOT NULL,
  record_date TIMESTAMP NOT NULL,
  record_type STRING NOT NULL COMMENT 'CLINICAL_NOTE, LAB_RESULT, IMAGING_REPORT, PT_NOTE, MEDICATION',
  content STRING NOT NULL COMMENT 'FULL TEXT - complete clinical note (no chunking)',
  source_system STRING COMMENT 'Epic, Cerner, etc',
  provider_id STRING,
  metadata STRING COMMENT 'JSON metadata',
  created_at TIMESTAMP
)
USING DELTA
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')
COMMENT 'Full patient clinical records - used by PA review for complete context'
""")

print(f"✅ Table 'patient_clinical_records' created (full records)")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Table 2b: patient_clinical_records_chunks (For Vector Search)

# COMMAND ----------

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {catalog_name}.{schema_name}.patient_clinical_records_chunks (
  chunk_id STRING NOT NULL,
  record_id STRING NOT NULL COMMENT 'Foreign key to patient_clinical_records.record_id',
  patient_id STRING NOT NULL,
  record_type STRING NOT NULL,
  chunk_index INT NOT NULL COMMENT 'Position in original document (0-based)',
  chunk_text STRING NOT NULL COMMENT 'Chunked text (500-1000 tokens)',
  keywords ARRAY<STRING>,
  char_count INT,
  created_at TIMESTAMP
)
USING DELTA
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')
COMMENT 'Chunked clinical records for vector search index'
""")

print(f"✅ Table 'patient_clinical_records_chunks' created (search chunks)")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Table 3: clinical_guidelines (Full Guidelines - Operational)

# COMMAND ----------

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {catalog_name}.{schema_name}.clinical_guidelines (
  guideline_id STRING NOT NULL,
  platform STRING NOT NULL COMMENT 'MCG, InterQual, Medicare',
  category STRING NOT NULL COMMENT 'OUTPATIENT_PROCEDURE, INPATIENT_ADMISSION, IMAGING, DME',
  procedure_code STRING COMMENT 'CPT code if applicable',
  diagnosis_code STRING COMMENT 'ICD-10 code if applicable',
  title STRING NOT NULL,
  content STRING NOT NULL COMMENT 'FULL GUIDELINE TEXT (no chunking)',
  questionnaire STRING COMMENT 'JSON array of MCG/InterQual questions',
  decision_criteria STRING COMMENT 'Approval/denial logic',
  effective_date DATE,
  tags STRING COMMENT 'Comma-separated tags',
  created_at TIMESTAMP
)
USING DELTA
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')
COMMENT 'Full MCG, InterQual, and Medicare guidelines - used by PA review for complete context'
""")

print(f"✅ Table 'clinical_guidelines' created (full guidelines)")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Table 3b: clinical_guidelines_chunks (For Vector Search)

# COMMAND ----------

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {catalog_name}.{schema_name}.clinical_guidelines_chunks (
  chunk_id STRING NOT NULL,
  guideline_id STRING NOT NULL COMMENT 'Foreign key to clinical_guidelines.guideline_id',
  procedure_code STRING,
  diagnosis_code STRING,
  chunk_index INT NOT NULL COMMENT 'Position in original guideline (0-based)',
  chunk_text STRING NOT NULL COMMENT 'Chunked text (500-1000 tokens)',
  tags ARRAY<STRING>,
  char_count INT,
  created_at TIMESTAMP
)
USING DELTA
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')
COMMENT 'Chunked guidelines for vector search index'
""")

print(f"✅ Table 'clinical_guidelines_chunks' created (search chunks)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Setup

# COMMAND ----------

# Show tables
display(spark.sql(f"SHOW TABLES IN {catalog_name}.{schema_name}"))

# COMMAND ----------

# Show table details
for table in ["authorization_requests", "pa_audit_trail", "patient_clinical_records", "patient_clinical_records_chunks", "clinical_guidelines", "clinical_guidelines_chunks"]:
    print(f"\n{'='*60}")
    print(f"Table: {catalog_name}.{schema_name}.{table}")
    print(f"{'='*60}")
    df = spark.sql(f"DESCRIBE TABLE {catalog_name}.{schema_name}.{table}")
    df.show(50, truncate=False)

# COMMAND ----------

print("✅ Setup 01 Complete: Catalog and Schema created successfully!")


# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Setup

# COMMAND ----------

# Show tables
display(spark.sql(f"SHOW TABLES IN {catalog_name}.{schema_name}"))

# COMMAND ----------

# Show table details
for table in ["authorization_requests", "pa_audit_trail", "patient_clinical_records", "patient_clinical_records_chunks", "clinical_guidelines", "clinical_guidelines_chunks"]:
    print(f"\n{'='*60}")
    print(f"Table: {catalog_name}.{schema_name}.{table}")
    print(f"{'='*60}")
    df = spark.sql(f"DESCRIBE TABLE {catalog_name}.{schema_name}.{table}")
    df.show(50, truncate=False)

# COMMAND ----------

print("✅ Setup 01 Complete: Catalog and Schema created successfully!")

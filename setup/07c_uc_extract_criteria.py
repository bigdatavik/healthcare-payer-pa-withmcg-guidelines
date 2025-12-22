# Databricks notebook source
# MAGIC %md
# MAGIC # UC Function: extract_clinical_criteria
# MAGIC
# MAGIC Extracts structured clinical criteria from unstructured notes using AI.
# MAGIC All configuration from config.yaml.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Import Configuration

# COMMAND ----------

import sys
import os
sys.path.append(os.path.abspath('..'))
from shared.config import get_config

cfg = get_config()
print(f"Creating function in: {cfg.catalog}.{cfg.schema}")
print(f"Using LLM: {cfg.llm_endpoint}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Drop Existing Function

# COMMAND ----------

spark.sql(f"DROP FUNCTION IF EXISTS {cfg.catalog}.{cfg.schema}.extract_clinical_criteria")
print("✅ Dropped existing function (if any)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create UC Function
# MAGIC
# MAGIC Using SQL AI_QUERY pattern (matches fraud template exactly)

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE FUNCTION {cfg.catalog}.{cfg.schema}.extract_clinical_criteria(
  clinical_notes STRING COMMENT 'Unstructured clinical notes'
)
RETURNS STRUCT<
  age: STRING,
  chief_complaint: STRING,
  symptom_duration: STRING,
  prior_treatments: STRING,
  physical_exam: STRING,
  diagnostic_tests: STRING,
  medications: STRING
>
COMMENT 'Extract structured clinical criteria from unstructured notes using AI'
RETURN 
  FROM_JSON(
    TRIM(REGEXP_REPLACE(REGEXP_REPLACE(
      AI_QUERY(
        '{cfg.llm_endpoint}',
        CONCAT(
          'Extract structured clinical information from the notes. Return ONLY a JSON object.\\n\\n',
          'NOTES: ', clinical_notes, '\\n\\n',
          'Return this JSON: {{"age": "patient age", "chief_complaint": "complaint", "symptom_duration": "duration", "prior_treatments": "treatments attempted", "physical_exam": "exam findings", "diagnostic_tests": "test results", "medications": "current meds"}}\\n\\n',
          'If any field is not mentioned, use "Not documented".\\n\\n',
          'Return ONLY the JSON object, no other text.'
        )
      ), '```json', ''), '```', '')),
    'STRUCT<age:STRING,chief_complaint:STRING,symptom_duration:STRING,prior_treatments:STRING,physical_exam:STRING,diagnostic_tests:STRING,medications:STRING>'
  )
""")

print(f"✅ Function created: {cfg.catalog}.{cfg.schema}.extract_clinical_criteria")
print(f"✅ Using LLM: {cfg.llm_endpoint}")
print(f"✅ Includes markdown stripping (removes ```json and ``` wrappers)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Function

# COMMAND ----------

# Test with sample clinical notes
print("\n🔍 Testing with realistic clinical scenario...")
test_result = spark.sql(f"""
SELECT {cfg.catalog}.{cfg.schema}.extract_clinical_criteria(
  'Patient: 58-year-old male. Chief complaint: Right knee pain for 6 months. Failed conservative treatment including NSAIDs and 8 weeks of physical therapy. Physical exam shows medial joint line tenderness, positive McMurray test. MRI shows medial meniscus tear. Currently on ibuprofen 600mg TID.'
) as extracted_criteria
""").collect()[0]

print("✅ Test Result:")
print("=" * 70)
print(f"Age: {test_result.extracted_criteria.age}")
print(f"Chief Complaint: {test_result.extracted_criteria.chief_complaint}")
print(f"Symptom Duration: {test_result.extracted_criteria.symptom_duration}")
print(f"Prior Treatments: {test_result.extracted_criteria.prior_treatments}")
print(f"Physical Exam: {test_result.extracted_criteria.physical_exam}")
print(f"Diagnostic Tests: {test_result.extracted_criteria.diagnostic_tests}")
print(f"Medications: {test_result.extracted_criteria.medications}")
print("=" * 70)
print("\n💡 This function extracts structured data from unstructured clinical notes.")
print("   It's used by the PA agent to understand patient information.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("=" * 80)
print("✅ UC FUNCTION CREATED SUCCESSFULLY!")
print("=" * 80)
print(f"Function: {cfg.catalog}.{cfg.schema}.extract_clinical_criteria")
print(f"LLM: databricks-meta-llama-3-1-405b-instruct")
print(f"Purpose: Extract structured data from unstructured clinical notes")
print("=" * 80)



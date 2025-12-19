# Databricks notebook source
# MAGIC %md
# MAGIC # Setup 08: Test Agent Workflow
# MAGIC
# MAGIC Tests the complete PA workflow end-to-end.

# COMMAND ----------

dbutils.widgets.text("catalog_name", "healthcare_payer_pa_withmcg_guidelines_dev", "Catalog Name")
dbutils.widgets.text("schema_name", "main", "Schema Name")

catalog_name = dbutils.widgets.get("catalog_name")
schema_name = dbutils.widgets.get("schema_name")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 1: Search Clinical Records

# COMMAND ----------

result = spark.sql(f"""
SELECT {catalog_name}.{schema_name}.search_clinical_records(
  'PT00001',
  'knee pain physical therapy'
) AS search_result
""").collect()[0]['search_result']

print("✅ Search Clinical Records:")
print(result[:500])

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 2: Search Guidelines

# COMMAND ----------

result = spark.sql(f"""
SELECT {catalog_name}.{schema_name}.search_guidelines(
  '73721',
  'MCG'
) AS guideline_result
""").collect()[0]['guideline_result']

print("✅ Search Guidelines:")
print(result[:500])

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 3: Full Authorization Workflow

# COMMAND ----------

# Get a sample PA request
pa_request = spark.sql(f"""
SELECT * FROM {catalog_name}.{schema_name}.authorization_requests LIMIT 1
""").collect()[0]

print(f"Testing PA Request: {pa_request['request_id']}")
print(f"Patient: {pa_request['patient_id']}")
print(f"Procedure: {pa_request['procedure_code']}")

# COMMAND ----------

# Run authorization
import json

result = spark.sql(f"""
SELECT {catalog_name}.{schema_name}.authorize_request(
  '{pa_request['procedure_code']}',
  '{pa_request['diagnosis_code']}',
  '{pa_request['patient_id']}',
  '{pa_request['clinical_notes']}'
) AS auth_result
""").collect()[0]['auth_result']

decision_data = json.loads(result)

print("\n✅ Authorization Decision:")
print(json.dumps(decision_data, indent=2))

# COMMAND ----------

print("✅ Setup 08 Complete: All systems tested and operational!")


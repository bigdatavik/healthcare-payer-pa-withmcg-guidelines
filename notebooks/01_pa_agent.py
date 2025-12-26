# Databricks notebook source
# MAGIC %md
# MAGIC # ✨✨✨ VERSION 1.0 - CREATED December 21, 2025 ✨✨✨
# MAGIC
# MAGIC # Prior Authorization AI Agent - Interactive Demo
# MAGIC
# MAGIC **🎯 Purpose:** Interactive notebook to test and demonstrate the PA agent workflow
# MAGIC
# MAGIC **📅 Last Updated:** December 21, 2025
# MAGIC **🔧 Version:** 1.0
# MAGIC **👤 Author:** Vik Malhotra

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

import sys
import os
sys.path.append(os.path.abspath('..'))
from shared.config import get_config, print_config

cfg = get_config()
print_config(cfg)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Import Agent

# COMMAND ----------

from src.agent.pa_agent import PriorAuthorizationAgent
import json

# Initialize agent
agent = PriorAuthorizationAgent(
    catalog_name=cfg.catalog,
    schema_name=cfg.schema,
    warehouse_id=cfg.warehouse_id
)

print("✅ Agent initialized")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 1: Simple PA Request

# COMMAND ----------

# Example: Knee MRI for patient with chronic pain
result = agent.process_pa_request(
    patient_id="PT00001",
    procedure_code="73721",  # MRI knee
    diagnosis_code="M25.561",  # Pain in right knee
    clinical_notes="Patient presents with chronic right knee pain for 8 months. Failed conservative therapy including 12 weeks of physical therapy and NSAIDs."
)

print(json.dumps(result, indent=2))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 2: Review Decision Details

# COMMAND ----------

print(f"Decision: {result['decision']}")
print(f"Confidence: {result['confidence']:.0%}")
print(f"MCG Code: {result['mcg_code']}")
print(f"\nExplanation:\n{result['explanation']}")

if result.get('mcg_answers'):
    print(f"\nMCG Questionnaire Answers:")
    for question, answer_data in result['mcg_answers'].items():
        print(f"\nQ: {question}")
        print(f"A: {answer_data['answer']}")
        print(f"Evidence: {answer_data['explanation'][:100]}...")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 3: Query All Pending Requests

# COMMAND ----------

pending_df = spark.sql(f"""
SELECT 
    request_id,
    patient_id,
    procedure_code,
    procedure_description,
    urgency_level,
    request_date
FROM {cfg.auth_requests_table}
WHERE decision IS NULL
ORDER BY request_date DESC
LIMIT 10
""")

display(pending_df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 4: Process Multiple Requests

# COMMAND ----------

pending_requests = pending_df.collect()

results = []
for req in pending_requests[:3]:  # Process first 3
    print(f"\n{'='*60}")
    print(f"Processing: {req.request_id}")
    print(f"{'='*60}")
    
    result = agent.process_pa_request(
        patient_id=req.patient_id,
        procedure_code=req.procedure_code,
        diagnosis_code="M25.561",  # Simplified for demo
        clinical_notes=req.procedure_description
    )
    
    results.append({
        'request_id': req.request_id,
        'decision': result['decision'],
        'confidence': result['confidence'],
        'mcg_code': result['mcg_code']
    })

# Display results
import pandas as pd
results_df = pd.DataFrame(results)
display(results_df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 5: Search Clinical Records

# COMMAND ----------

# Test vector search directly
clinical_search_result = spark.sql(f"""
SELECT {cfg.catalog}.{cfg.schema}.search_clinical_records(
  'PT00001',
  'knee pain physical therapy treatment'
) AS search_results
""").collect()[0]['search_results']

print("Clinical Records Search Results:")
print(clinical_search_result[:500])

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 6: Search Guidelines

# COMMAND ----------

guidelines_result = spark.sql(f"""
SELECT {cfg.catalog}.{cfg.schema}.search_guidelines(
  '73721',
  'MCG'
) AS guideline_results
""").collect()[0]['guideline_results']

print("MCG Guidelines Search Results:")
print(guidelines_result[:500])

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary Statistics

# COMMAND ----------

stats_df = spark.sql(f"""
SELECT 
    decision,
    COUNT(*) as count,
    ROUND(AVG(confidence_score), 2) as avg_confidence,
    MIN(request_date) as first_request,
    MAX(request_date) as last_request
FROM {cfg.auth_requests_table}
WHERE decision IS NOT NULL
GROUP BY decision
ORDER BY count DESC
""")

display(stats_df)

# COMMAND ----------

print("✅ Agent testing complete!")



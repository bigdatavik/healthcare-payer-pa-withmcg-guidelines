# Databricks notebook source
# MAGIC %md
# MAGIC # UC Function: answer_mcg_question (ORIGINAL VERSION - BACKUP)
# MAGIC
# MAGIC **This is the ORIGINAL simple prompt version**
# MAGIC Saved before implementing smart temporal prompt
# MAGIC
# MAGIC To restore this version:
# MAGIC 1. Copy this file to setup/07e_uc_answer_mcg.py
# MAGIC 2. Deploy and run

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

spark.sql(f"DROP FUNCTION IF EXISTS {cfg.catalog}.{cfg.schema}.answer_mcg_question")
print("✅ Dropped existing function (if any)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create UC Function - ORIGINAL SIMPLE PROMPT

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE FUNCTION {cfg.catalog}.{cfg.schema}.answer_mcg_question(
  clinical_evidence STRING COMMENT 'Clinical evidence from patient records',
  question STRING COMMENT 'MCG question to answer'
)
RETURNS STRING
COMMENT 'Answer MCG questionnaire questions using provided clinical evidence - ORIGINAL VERSION'
RETURN SELECT AI_QUERY(
  '{cfg.llm_endpoint}',
  CONCAT(
    'You are a medical reviewer answering MCG questionnaire questions.\\n\\n',
    'Use ONLY the provided clinical records to answer. Answer with YES or NO followed by brief evidence.\\n\\n',
    'Clinical Records:\\n', clinical_evidence, '\\n\\n',
    'Question: ', question, '\\n\\n',
    'Answer format: YES/NO - [brief evidence from records]'
  )
) as answer
""")

print(f"✅ Function created: {cfg.catalog}.{cfg.schema}.answer_mcg_question")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Function

# COMMAND ----------

# Test with sample question and clinical evidence
print("\n🔍 Testing with realistic MCG question...")

sample_evidence = """
[CLINICAL_NOTE] Patient: 58-year-old male. Chief complaint: Right knee pain for 6 months. 
Failed conservative treatment including NSAIDs and 8 weeks of physical therapy. 
Physical exam shows medial joint line tenderness, positive McMurray test. 
MRI shows medial meniscus tear. Currently on ibuprofen 600mg TID.

[PT_NOTE] Patient completed 8 sessions of physical therapy over 8 weeks. 
Focused on quadriceps strengthening and range of motion. 
Patient reports minimal improvement in pain and function.
"""

test_question = "Has the patient completed at least 6 weeks of physical therapy?"

test_result = spark.sql(f"""
SELECT {cfg.catalog}.{cfg.schema}.answer_mcg_question(
  '{sample_evidence.replace("'", "''")}',
  '{test_question}'
) as answer
""").collect()[0]

print("✅ Test Result:")
print("=" * 70)
print(f"Question: {test_question}")
print(f"Answer: {test_result.answer}")
print("=" * 70)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("=" * 80)
print("✅ UC FUNCTION CREATED - ORIGINAL SIMPLE PROMPT")
print("=" * 80)
print(f"Function: {cfg.catalog}.{cfg.schema}.answer_mcg_question")
print(f"LLM: {cfg.llm_endpoint}")
print(f"Prompt: Basic prompt without temporal awareness")
print("=" * 80)


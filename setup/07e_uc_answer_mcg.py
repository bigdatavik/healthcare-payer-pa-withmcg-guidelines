# Databricks notebook source
# MAGIC %md
# MAGIC # UC Function: answer_mcg_question
# MAGIC
# MAGIC Answers MCG questionnaire questions using patient clinical records.
# MAGIC Combines Vector Search + LLM for intelligent Q&A.
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
print(f"Using vector endpoint: {cfg.vector_endpoint}")
print(f"Using LLM: {cfg.llm_endpoint}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Drop Existing Function

# COMMAND ----------

spark.sql(f"DROP FUNCTION IF EXISTS {cfg.catalog}.{cfg.schema}.answer_mcg_question")
print("✅ Dropped existing function (if any)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create UC Function
# MAGIC
# MAGIC Takes clinical evidence as input (agent does vector search separately)

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE FUNCTION {cfg.catalog}.{cfg.schema}.answer_mcg_question(
  clinical_evidence STRING COMMENT 'Clinical evidence from patient records',
  question STRING COMMENT 'MCG question to answer'
)
RETURNS STRING
COMMENT 'Answer MCG questionnaire questions using provided clinical evidence'
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
print("\n💡 This function is called by the agent AFTER it does vector search.")
print("   The agent searches patient records and passes the relevant evidence here.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("=" * 80)
print("✅ UC FUNCTION CREATED SUCCESSFULLY!")
print("=" * 80)
print(f"Function: {cfg.catalog}.{cfg.schema}.answer_mcg_question")
print(f"LLM: {cfg.llm_endpoint}")
print(f"Purpose: Answer MCG questions using provided clinical evidence")
print(f"Note: Agent does vector search separately and passes evidence to this function")
print("=" * 80)



# Databricks notebook source
# MAGIC %md
# MAGIC # UC Function: explain_decision
# MAGIC
# MAGIC Generates human-readable explanation for authorization decision.
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

spark.sql(f"DROP FUNCTION IF EXISTS {cfg.catalog}.{cfg.schema}.explain_decision")
print("✅ Dropped existing function (if any)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create UC Function
# MAGIC
# MAGIC Using SQL AI_QUERY pattern (matches fraud template exactly)

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE FUNCTION {cfg.catalog}.{cfg.schema}.explain_decision(
  decision STRING COMMENT 'APPROVED or DENIED',
  clinical_summary STRING COMMENT 'Clinical evidence summary',
  guideline_summary STRING COMMENT 'MCG guideline summary'
)
RETURNS STRUCT<
  explanation: STRING,
  evidence: ARRAY<STRING>,
  recommendations: ARRAY<STRING>
>
COMMENT 'Generate human-readable explanation for authorization decision'
RETURN 
  FROM_JSON(
    TRIM(REGEXP_REPLACE(REGEXP_REPLACE(
      AI_QUERY(
        '{cfg.llm_endpoint}',
        CONCAT(
          'You are a medical reviewer explaining prior authorization decisions to providers.\\n\\n',
          'Decision: ', decision, '\\n',
          'Clinical Evidence: ', clinical_summary, '\\n',
          'MCG Guideline: ', guideline_summary, '\\n\\n',
          'Generate a clear, professional explanation that:\\n',
          '1. States the decision clearly\\n',
          '2. References specific clinical evidence\\n',
          '3. Cites relevant MCG guideline criteria\\n',
          '4. If denied, explains what documentation is needed\\n',
          '5. Maintains a helpful, non-adversarial tone\\n\\n',
          'Return ONLY JSON: {{"explanation": "summary under 200 words", "evidence": ["fact1", "fact2"], "recommendations": ["action1", "action2"]}}\\n\\n',
          'Return ONLY the JSON object.'
        )
      ), '```json', ''), '```', '')),
    'STRUCT<explanation:STRING,evidence:ARRAY<STRING>,recommendations:ARRAY<STRING>>'
  )
""")

print(f"✅ Function created: {cfg.catalog}.{cfg.schema}.explain_decision")
print(f"✅ Using LLM: {cfg.llm_endpoint}")
print(f"✅ Includes markdown stripping (removes ```json and ``` wrappers)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Function

# COMMAND ----------

# Test with sample decision
print("\n🔍 Testing with realistic PA decision scenario...")
test_result = spark.sql(f"""
SELECT {cfg.catalog}.{cfg.schema}.explain_decision(
  'APPROVED',
  'Patient: 58yo male. Right knee pain x6 months. Failed conservative treatment: NSAIDs, 8 weeks PT. MRI shows medial meniscus tear. Physical exam: medial joint line tenderness, positive McMurray.',
  'MCG requires: 1) Conservative treatment failure (NSAIDs + PT ≥6 weeks), 2) Imaging confirmation of tear, 3) Physical exam findings consistent with meniscal pathology. All criteria met.'
) as result
""").collect()[0]

print("✅ Test Result:")
print("=" * 70)
print(f"Explanation: {test_result.result.explanation}")
print(f"\nEvidence: {test_result.result.evidence}")
print(f"\nRecommendations: {test_result.result.recommendations}")
print("=" * 70)
print("\n💡 This function generates human-readable explanations for PA decisions.")
print("   It's used at the end of the authorization workflow.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("=" * 80)
print("✅ UC FUNCTION CREATED SUCCESSFULLY!")
print("=" * 80)
print(f"Function: {cfg.catalog}.{cfg.schema}.explain_decision")
print(f"LLM: {cfg.llm_endpoint}")
print(f"Purpose: Generate professional explanation for PA decision")
print("=" * 80)



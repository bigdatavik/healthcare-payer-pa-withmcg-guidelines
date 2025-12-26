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
COMMENT 'Answer MCG questionnaire questions using provided clinical evidence with smart temporal and contextual analysis'
RETURN SELECT AI_QUERY(
  '{cfg.llm_endpoint}',
  CONCAT(
    '# MEDICAL REVIEWER - MCG QUESTIONNAIRE ANALYSIS\\n\\n',
    
    '## YOUR TASK\\n',
    'Answer MCG criteria questions by analyzing clinical documentation.\\n\\n',
    
    '## CRITICAL INSTRUCTIONS\\n',
    '1. TEMPORAL DATA: When records show progression over time, use the MOST RECENT or FINAL value\\n',
    '   - Example: If Week 4 shows "4 sessions" and Week 12 shows "12 sessions", the answer is 12\\n',
    '   - Look for: "completed", "total", "to date", "final" to identify cumulative values\\n\\n',
    
    '2. CUMULATIVE COUNTS: For treatment duration, PT sessions, etc., find the HIGHEST/LATEST count\\n',
    '   - PT notes often show session count per visit - look for the LAST mention\\n',
    '   - Conservative treatment duration: Count weeks from FIRST to LAST visit\\n\\n',
    
    '3. CONFIRMATION KEYWORDS: For diagnostic questions, look for explicit confirmations:\\n',
    '   - MRI/imaging: "confirms", "shows", "demonstrates", "consistent with"\\n',
    '   - Severity: Look for grades (Grade 1-4), "mild", "moderate", "severe"\\n\\n',
    
    '4. NEGATION: Watch for "NO", "not", "without", "negative for"\\n',
    '   - "NO severe osteoarthritis" = severity is NOT Grade 3-4\\n',
    '   - "Grade 2 chondromalacia" = NOT severe (severe is Grade 3-4)\\n\\n',
    
    '5. ANSWER FORMAT:\\n',
    '   - Start with YES or NO (uppercase)\\n',
    '   - Follow with specific evidence FROM THE RECORDS\\n',
    '   - Cite the record type and key values\\n\\n',
    
    '## COMMON MCG QUESTION TYPES & HOW TO ANSWER\\n\\n',
    
    '### Conservative Treatment Duration\\n',
    'Question pattern: "Has patient completed at least X weeks..."\\n',
    'Look for: Timeline from initial visit to latest visit, "X weeks of treatment"\\n',
    'Evidence: PT notes, follow-up visits showing duration\\n\\n',
    
    '### Physical Therapy Sessions\\n',
    'Question pattern: "Has patient completed at least X PT sessions..."\\n',
    'Look for: "sessions completed", "session X of Y", FINAL session count\\n',
    'Evidence: PT discharge note or most recent PT note with total\\n\\n',
    
    '### Imaging Confirmation\\n',
    'Question pattern: "Is MRI/X-ray confirming [condition] present..."\\n',
    'Look for: Radiology report with explicit findings\\n',
    'Evidence: "MRI shows", "confirmed", specific pathology mentioned\\n\\n',
    
    '### Severity/Grade Questions\\n',
    'Question pattern: "Is there severe/Grade 3-4 [condition]..."\\n',
    'Look for: Specific grades, severity descriptors\\n',
    'Evidence: Grade numbers, "mild/moderate/severe" classification\\n\\n',
    
    '## CLINICAL RECORDS PROVIDED\\n',
    'The records below are ordered by date. Later records contain more recent information.\\n\\n',
    clinical_evidence, '\\n\\n',
    
    '## MCG QUESTION TO ANSWER\\n',
    question, '\\n\\n',
    
    '## YOUR ANSWER\\n',
    'Format: YES/NO - [specific evidence with record type and key values]\\n',
    'Example: "YES - PT discharge note (Week 12) shows 12 total sessions completed, exceeding 8-session requirement"\\n',
    'Answer:'
  )
) as answer
""")

print(f"✅ Function created: {cfg.catalog}.{cfg.schema}.answer_mcg_question")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Function with Realistic Temporal Data

# COMMAND ----------

# Test with sample question and clinical evidence showing progression over time
print("\n🔍 Testing with realistic temporal MCG question...")
print("=" * 80)

# Realistic sample: Multiple PT notes showing progression
sample_evidence = """
[CLINICAL_NOTE - Week 0] Patient: 58-year-old male. Chief complaint: Right knee pain for 6 months. 
Plan: Prescribe ibuprofen. Refer to physical therapy for 12 sessions. Conservative treatment initiated.

[PT_NOTE - Week 4] Patient PT00001. Session: 4 of 12. 
TREATMENT DURATION: 4 weeks. SESSIONS COMPLETED: 4 sessions (1x/week protocol).
Patient reports persistent right knee pain. Minimal improvement.

[PT_NOTE - Week 8] Patient PT00001. Session: 8 of 12.
TREATMENT DURATION: 8 weeks. SESSIONS COMPLETED: 8 sessions (1x/week protocol).
Patient reports ongoing right knee pain 6-7/10. Minimal improvement from physical therapy.

[IMAGING_REPORT - Week 10] MRI RIGHT KNEE: Complex tear of the posterior horn of the medial meniscus confirmed.
Grade 2 chondromalacia of the medial femoral condyle. NOT Grade 3 or Grade 4 osteoarthritis.

[PT_NOTE - Week 12] Patient PT00001. Session: 12 of 12 (FINAL).
TREATMENT DURATION: 12 weeks. SESSIONS COMPLETED: 12 sessions (2x/week protocol).
STATUS: TREATMENT COMPLETED. Patient has FAILED conservative management despite 12 weeks.
Recommend SURGICAL EVALUATION for arthroscopic meniscectomy.

[CLINICAL_NOTE - Week 14] ORTHOPEDIC CONSULTATION. Patient completed 14 weeks of conservative treatment.
MRI confirms meniscal tear. X-ray shows Grade 2 chondromalacia (NOT severe osteoarthritis).
RECOMMEND: Arthroscopic right knee meniscectomy.
"""

print("\n📋 TEST 1: PT Sessions (Should find '12 sessions' from final note)")
test_q1 = "Has patient completed at least 8 PT sessions?"
result1 = spark.sql(f"""
SELECT {cfg.catalog}.{cfg.schema}.answer_mcg_question(
  '{sample_evidence.replace("'", "''")}',
  '{test_q1}'
) as answer
""").collect()[0]

print(f"Question: {test_q1}")
print(f"Answer: {result1.answer}")
print()

print("📋 TEST 2: Conservative Treatment Duration (Should find '14 weeks')")
test_q2 = "Has patient completed at least 6 weeks conservative treatment?"
result2 = spark.sql(f"""
SELECT {cfg.catalog}.{cfg.schema}.answer_mcg_question(
  '{sample_evidence.replace("'", "''")}',
  '{test_q2}'
) as answer
""").collect()[0]

print(f"Question: {test_q2}")
print(f"Answer: {result2.answer}")
print()

print("📋 TEST 3: MRI Confirmation (Should find 'confirms' in imaging report)")
test_q3 = "Is MRI confirming meniscal tear present?"
result3 = spark.sql(f"""
SELECT {cfg.catalog}.{cfg.schema}.answer_mcg_question(
  '{sample_evidence.replace("'", "''")}',
  '{test_q3}'
) as answer
""").collect()[0]

print(f"Question: {test_q3}")
print(f"Answer: {result3.answer}")
print()

print("📋 TEST 4: Severe OA (Should recognize 'Grade 2' is NOT severe)")
test_q4 = "Is there severe (Grade 3-4) osteoarthritis?"
result4 = spark.sql(f"""
SELECT {cfg.catalog}.{cfg.schema}.answer_mcg_question(
  '{sample_evidence.replace("'", "''")}',
  '{test_q4}'
) as answer
""").collect()[0]

print(f"Question: {test_q4}")
print(f"Answer: {result4.answer}")

print()
print("=" * 80)
print("💡 EXPECTED RESULTS:")
print("   Q1: YES - Should find 12 sessions (not 4 or 8)")
print("   Q2: YES - Should find 14 weeks duration")
print("   Q3: YES - Should find MRI confirms tear")
print("   Q4: NO  - Should recognize Grade 2 is NOT severe (severe = Grade 3-4)")
print("=" * 80)
print("\n✅ If all answers match expected, the smart prompt is working!")

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



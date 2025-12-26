# Databricks notebook source
# MAGIC %md
# MAGIC # UC Function: check_mcg_guidelines
# MAGIC
# MAGIC Retrieves MCG questionnaire for specific procedure.
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

# COMMAND ----------

# MAGIC %md
# MAGIC ## Drop Existing Function

# COMMAND ----------

spark.sql(f"DROP FUNCTION IF EXISTS {cfg.catalog}.{cfg.schema}.check_mcg_guidelines")
print("✅ Dropped existing function (if any)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create UC Function

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE FUNCTION {cfg.catalog}.{cfg.schema}.check_mcg_guidelines(
  proc_code STRING COMMENT 'CPT code',
  diag_code STRING COMMENT 'ICD-10 code'
)
RETURNS STRUCT<
  guideline_id: STRING,
  platform: STRING,
  title: STRING,
  questionnaire: STRING,
  decision_criteria: STRING,
  content: STRING
>
COMMENT 'Retrieve guideline with questionnaire and decision criteria for PA review'
RETURN SELECT 
  STRUCT(
    guideline_id,
    platform,
    title,
    questionnaire,
    decision_criteria,
    SUBSTRING(content, 1, 1000) AS content
  ) AS guideline_data
FROM {cfg.catalog}.{cfg.schema}.clinical_guidelines
WHERE procedure_code = proc_code
  AND diagnosis_code = diag_code
LIMIT 1
""")

print(f"✅ Function created: {cfg.catalog}.{cfg.schema}.check_mcg_guidelines")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Function

# COMMAND ----------

# Test with sample procedure - using common knee arthroscopy code
print("\n🔍 Testing with CPT 29881 (Knee Arthroscopy, Meniscectomy)...")
test_result = spark.sql(f"""
SELECT {cfg.catalog}.{cfg.schema}.check_mcg_guidelines(
  '29881',
  'M23.205'
) as guideline_data
""").collect()

if test_result and test_result[0].guideline_data:
    data = test_result[0].guideline_data
    print("✅ Test Result:")
    print("=" * 70)
    print(f"Guideline ID: {data.guideline_id}")
    print(f"Platform: {data.platform}")
    print(f"Title: {data.title}")
    print(f"\nQuestionnaire: {data.questionnaire[:200]}..." if data.questionnaire else "\nQuestionnaire: None")
    print(f"\nDecision Criteria: {data.decision_criteria[:200]}..." if data.decision_criteria else "\nDecision Criteria: None")
    print("=" * 70)
else:
    print("⚠️  No MCG guideline found for CPT 29881")
    print("This is expected if you haven't run the setup notebooks yet:")
    print("  1. Run 03_generate_guidelines_documents.py")
    print("  2. Run 03a_chunk_guidelines.py")
    print("\n💡 Checking if clinical_guidelines table has any data...")
    
    count_result = spark.sql(f"""
        SELECT COUNT(*) as cnt FROM {cfg.catalog}.{cfg.schema}.clinical_guidelines
    """).collect()[0]
    
    print(f"   Records in clinical_guidelines: {count_result.cnt}")
    
    if count_result.cnt > 0:
        sample = spark.sql(f"""
            SELECT procedure_code, diagnosis_code, title
            FROM {cfg.catalog}.{cfg.schema}.clinical_guidelines
            LIMIT 5
        """).collect()
        print("\n📋 Sample guidelines in table:")
        for row in sample:
            print(f"   - CPT {row.procedure_code}, ICD {row.diagnosis_code}: {row.title}")
    else:
        print("   ⚠️  Table is empty! Please run the guidelines generation notebooks.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Function with Real Data

# COMMAND ----------

# Test 1: MCG Knee Arthroscopy (rows 16-21 in table)
print("\n🔍 Test 1: CPT 29881 + ICD M23.205 (MCG: Knee Arthroscopy with Meniscectomy)")
print("=" * 70)
test1 = spark.sql(f"""
SELECT {cfg.catalog}.{cfg.schema}.check_mcg_guidelines('29881', 'M23.205') as guideline_data
""").collect()

if test1 and test1[0].guideline_data:
    data = test1[0].guideline_data
    print(f"✅ Guideline ID: {data.guideline_id}")
    print(f"   Platform: {data.platform}")
    print(f"   Title: {data.title}")
    print(f"   Has Questionnaire: {'Yes' if data.questionnaire else 'No'}")
    print(f"   Has Decision Criteria: {'Yes' if data.decision_criteria else 'No'}")
    if data.questionnaire:
        import json
        try:
            questions = json.loads(data.questionnaire)
            print(f"   Number of Questions: {len(questions)}")
        except:
            print(f"   Questionnaire Preview: {data.questionnaire[:100]}...")
else:
    print("❌ NOT FOUND")

print()

# COMMAND ----------

# Test 2: InterQual Total Knee Arthroplasty (rows 1-5 in table)
print("\n🔍 Test 2: CPT 27447 + ICD M17.11 (InterQual: Total Knee Arthroplasty)")
print("=" * 70)
test2 = spark.sql(f"""
SELECT {cfg.catalog}.{cfg.schema}.check_mcg_guidelines('27447', 'M17.11') as guideline_data
""").collect()

if test2 and test2[0].guideline_data:
    data = test2[0].guideline_data
    print(f"✅ Guideline ID: {data.guideline_id}")
    print(f"   Platform: {data.platform}")
    print(f"   Title: {data.title}")
    print(f"   Has Questionnaire: {'Yes' if data.questionnaire else 'No'}")
    print(f"   Has Decision Criteria: {'Yes' if data.decision_criteria else 'No'}")
    if data.questionnaire:
        import json
        try:
            questions = json.loads(data.questionnaire)
            print(f"   Number of Questions: {len(questions)}")
        except:
            print(f"   Questionnaire Preview: {data.questionnaire[:100]}...")
else:
    print("❌ NOT FOUND")

print()

# COMMAND ----------

# Test 3: MCG Cardiovascular Stress Test (rows 22-23 in table)
print("\n🔍 Test 3: CPT 93015 + ICD I25.10 (MCG: Cardiovascular Stress Test)")
print("=" * 70)
test3 = spark.sql(f"""
SELECT {cfg.catalog}.{cfg.schema}.check_mcg_guidelines('93015', 'I25.10') as guideline_data
""").collect()

if test3 and test3[0].guideline_data:
    data = test3[0].guideline_data
    print(f"✅ Guideline ID: {data.guideline_id}")
    print(f"   Platform: {data.platform}")
    print(f"   Title: {data.title}")
    print(f"   Has Questionnaire: {'Yes' if data.questionnaire else 'No'}")
    print(f"   Has Decision Criteria: {'Yes' if data.decision_criteria else 'No'}")
    if data.questionnaire:
        import json
        try:
            questions = json.loads(data.questionnaire)
            print(f"   Number of Questions: {len(questions)}")
        except:
            print(f"   Questionnaire Preview: {data.questionnaire[:100]}...")
else:
    print("❌ NOT FOUND")

print()

# COMMAND ----------

# Test 4: Medicare CPM Device (rows 6-10 in table)
print("\n🔍 Test 4: CPT E0601 + ICD M15.0 (Medicare LCD: Continuous Passive Motion Device)")
print("=" * 70)
test4 = spark.sql(f"""
SELECT {cfg.catalog}.{cfg.schema}.check_mcg_guidelines('E0601', 'M15.0') as guideline_data
""").collect()

if test4 and test4[0].guideline_data:
    data = test4[0].guideline_data
    print(f"✅ Guideline ID: {data.guideline_id}")
    print(f"   Platform: {data.platform}")
    print(f"   Title: {data.title}")
    print(f"   Has Questionnaire: {'Yes' if data.questionnaire else 'No'}")
    print(f"   Has Decision Criteria: {'Yes' if data.decision_criteria else 'No'}")
    if data.questionnaire:
        import json
        try:
            questions = json.loads(data.questionnaire)
            print(f"   Number of Questions: {len(questions)}")
        except:
            print(f"   Questionnaire Preview: {data.questionnaire[:100]}...")
else:
    print("❌ NOT FOUND")

print()

# COMMAND ----------

# Test 5: MCG MRI of Knee (rows 11-15 in table)
print("\n🔍 Test 5: CPT 73721 + ICD M25.561 (MCG: MRI of Joint - Knee)")
print("=" * 70)
test5 = spark.sql(f"""
SELECT {cfg.catalog}.{cfg.schema}.check_mcg_guidelines('73721', 'M25.561') as guideline_data
""").collect()

if test5 and test5[0].guideline_data:
    data = test5[0].guideline_data
    print(f"✅ Guideline ID: {data.guideline_id}")
    print(f"   Platform: {data.platform}")
    print(f"   Title: {data.title}")
    print(f"   Has Questionnaire: {'Yes' if data.questionnaire else 'No'}")
    print(f"   Has Decision Criteria: {'Yes' if data.decision_criteria else 'No'}")
    if data.questionnaire:
        import json
        try:
            questions = json.loads(data.questionnaire)
            print(f"   Number of Questions: {len(questions)}")
        except:
            print(f"   Questionnaire Preview: {data.questionnaire[:100]}...")
else:
    print("❌ NOT FOUND")

print()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("=" * 80)
print("✅ UC FUNCTION CREATED SUCCESSFULLY!")
print("=" * 80)
print(f"Function: {cfg.catalog}.{cfg.schema}.check_mcg_guidelines")
print(f"Source Table: {cfg.guidelines_table}")
print(f"Purpose: Retrieve MCG questionnaire for procedure/diagnosis combination")
print("=" * 80)



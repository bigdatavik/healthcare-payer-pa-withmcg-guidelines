# Databricks notebook source
# MAGIC %md
# MAGIC # Setup 07: Create Unity Catalog AI Functions
# MAGIC
# MAGIC Creates 7 Unity Catalog AI Functions for the Prior Authorization Agent:
# MAGIC 1. `search_clinical_records` - Search Vector Store 1 (clinical documents)
# MAGIC 2. `search_guidelines` - Search Vector Store 2 (MCG/InterQual guidelines)
# MAGIC 3. `extract_clinical_criteria` - Extract structured data from notes
# MAGIC 4. `check_mcg_guidelines` - Retrieve MCG questionnaire for procedure
# MAGIC 5. `answer_mcg_question` - Answer specific MCG question using clinical search
# MAGIC 6. `explain_decision` - Generate human-readable explanation
# MAGIC 7. `authorize_request` - Make final approval decision

# COMMAND ----------

dbutils.widgets.text("catalog_name", "healthcare_payer_pa_withmcg_guidelines_dev", "Catalog Name")
dbutils.widgets.text("schema_name", "main", "Schema Name")
dbutils.widgets.text("warehouse_id", "148ccb90800933a1", "SQL Warehouse ID")
dbutils.widgets.text("vector_endpoint_clinical", "pa_clinical_records_endpoint", "Clinical Vector Endpoint")
dbutils.widgets.text("vector_endpoint_guidelines", "pa_guidelines_endpoint", "Guidelines Vector Endpoint")

catalog_name = dbutils.widgets.get("catalog_name")
schema_name = dbutils.widgets.get("schema_name")
warehouse_id = dbutils.widgets.get("warehouse_id")
clinical_endpoint = dbutils.widgets.get("vector_endpoint_clinical")
guidelines_endpoint = dbutils.widgets.get("vector_endpoint_guidelines")

print(f"Creating UC Functions in: {catalog_name}.{schema_name}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Function 1: search_clinical_records

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE FUNCTION {catalog_name}.{schema_name}.search_clinical_records(
  patient_id STRING COMMENT 'Patient ID to search',
  query STRING COMMENT 'Semantic search query'
)
RETURNS STRING
COMMENT 'Search patient clinical records using Vector Store 1'
RETURN SELECT ai_query(
  '{clinical_endpoint}.{catalog_name}.{schema_name}.patient_clinical_records_index',
  CONCAT('Patient: ', patient_id, ' - ', query),
  NAMED_STRUCT(
    'num_results', 5,
    'filters', NAMED_STRUCT('patient_id', patient_id)
  )
) AS search_results
""")

print("✅ Created: search_clinical_records")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Function 2: search_guidelines

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE FUNCTION {catalog_name}.{schema_name}.search_guidelines(
  procedure_code STRING COMMENT 'CPT procedure code',
  platform STRING COMMENT 'MCG, InterQual, or Medicare'
)
RETURNS STRING
COMMENT 'Search clinical guidelines using Vector Store 2'
RETURN SELECT ai_query(
  '{guidelines_endpoint}.{catalog_name}.{schema_name}.clinical_guidelines_index',
  CONCAT(platform, ' guideline for procedure ', procedure_code),
  NAMED_STRUCT(
    'num_results', 3,
    'filters', NAMED_STRUCT('platform', platform, 'procedure_code', procedure_code)
  )
) AS guideline_results
""")

print("✅ Created: search_guidelines")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Function 3: extract_clinical_criteria

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE FUNCTION {catalog_name}.{schema_name}.extract_clinical_criteria(
  clinical_notes STRING COMMENT 'Unstructured clinical notes'
)
RETURNS STRING
LANGUAGE PYTHON
COMMENT 'Extract structured clinical criteria from unstructured notes using AI'
AS $$
  from databricks.sdk import WorkspaceClient
  from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
  
  w = WorkspaceClient()
  
  system_prompt = '''Extract structured clinical information from the notes:
  - Patient age and demographics
  - Chief complaint
  - Symptom duration
  - Prior treatments attempted
  - Physical examination findings
  - Diagnostic test results
  - Current medications
  
  Return as JSON with these fields.'''
  
  messages = [
    ChatMessage(role=ChatMessageRole.SYSTEM, content=system_prompt),
    ChatMessage(role=ChatMessageRole.USER, content=clinical_notes)
  ]
  
  response = w.serving_endpoints.query(
    name="databricks-meta-llama-3-1-405b-instruct",
    messages=messages,
    max_tokens=500
  )
  
  return response.choices[0].message.content
$$
""")

print("✅ Created: extract_clinical_criteria")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Function 4: check_mcg_guidelines

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE FUNCTION {catalog_name}.{schema_name}.check_mcg_guidelines(
  procedure_code STRING COMMENT 'CPT code',
  diagnosis_code STRING COMMENT 'ICD-10 code'
)
RETURNS STRING
COMMENT 'Retrieve MCG questionnaire for specific procedure'
RETURN SELECT 
  CONCAT(
    'MCG Guideline: ', guideline_id, '\\n',
    'Title: ', title, '\\n',
    'Questionnaire: ', questionnaire, '\\n',
    'Decision Criteria: ', decision_criteria
  ) AS mcg_guideline
FROM {catalog_name}.{schema_name}.clinical_guidelines
WHERE platform = 'MCG'
  AND procedure_code = procedure_code
LIMIT 1
""")

print("✅ Created: check_mcg_guidelines")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Function 5: answer_mcg_question

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE FUNCTION {catalog_name}.{schema_name}.answer_mcg_question(
  patient_id STRING COMMENT 'Patient ID',
  question STRING COMMENT 'MCG questionnaire question'
)
RETURNS STRING
LANGUAGE PYTHON
COMMENT 'Answer a specific MCG question by searching clinical records'
AS $$
  from databricks.vector_search.client import VectorSearchClient
  from databricks.sdk import WorkspaceClient
  from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
  import json
  
  # Search clinical records for relevant information
  vsc = VectorSearchClient(disable_notice=True)
  search_results = vsc.get_index(
    f"{clinical_endpoint}.{catalog_name}.{schema_name}.patient_clinical_records_index"
  ).similarity_search(
    query_text=f"Patient {patient_id}: {question}",
    columns=["content"],
    filters={"patient_id": patient_id},
    num_results=3
  )
  
  # Extract content from search results
  clinical_context = ""
  if search_results.get('result', {}).get('data_array'):
    for result in search_results['result']['data_array']:
      clinical_context += result.get('content', '') + "\\n\\n"
  
  # Use LLM to answer the question based on clinical context
  w = WorkspaceClient()
  
  system_prompt = f'''You are a clinical reviewer answering MCG guideline questions.
  Based on the clinical records provided, answer the question with YES, NO, or INSUFFICIENT_DATA.
  Provide a brief explanation citing specific evidence from the records.'''
  
  user_prompt = f'''Question: {question}

Clinical Records:
{clinical_context[:2000]}

Answer the question (YES/NO/INSUFFICIENT_DATA) with supporting evidence:'''
  
  messages = [
    ChatMessage(role=ChatMessageRole.SYSTEM, content=system_prompt),
    ChatMessage(role=ChatMessageRole.USER, content=user_prompt)
  ]
  
  response = w.serving_endpoints.query(
    name="databricks-meta-llama-3-1-405b-instruct",
    messages=messages,
    max_tokens=300
  )
  
  return response.choices[0].message.content
$$
""")

print("✅ Created: answer_mcg_question")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Function 6: explain_decision

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE FUNCTION {catalog_name}.{schema_name}.explain_decision(
  decision STRING COMMENT 'APPROVED, DENIED, or MANUAL_REVIEW',
  mcg_code STRING COMMENT 'MCG guideline code',
  answers STRING COMMENT 'JSON of MCG question answers',
  confidence DOUBLE COMMENT 'Confidence score 0-1'
)
RETURNS STRING
LANGUAGE PYTHON
COMMENT 'Generate human-readable explanation of PA decision'
AS $$
  from databricks.sdk import WorkspaceClient
  from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
  
  w = WorkspaceClient()
  
  system_prompt = '''You are a clinical prior authorization specialist.
  Generate a clear, professional explanation for the authorization decision.
  Include:
  1. Final decision (Approved/Denied/Manual Review Required)
  2. MCG guideline code and criteria
  3. Summary of how clinical evidence supported each criterion
  4. Confidence level
  5. Next steps if manual review needed
  
  Keep it concise (3-5 sentences) but complete.'''
  
  user_prompt = f'''Decision: {decision}
MCG Code: {mcg_code}
Answers to MCG Criteria: {answers}
Confidence: {confidence:.1%}

Generate the explanation:'''
  
  messages = [
    ChatMessage(role=ChatMessageRole.SYSTEM, content=system_prompt),
    ChatMessage(role=ChatMessageRole.USER, content=user_prompt)
  ]
  
  response = w.serving_endpoints.query(
    name="databricks-meta-llama-3-1-405b-instruct",
    messages=messages,
    max_tokens=400
  )
  
  return response.choices[0].message.content
$$
""")

print("✅ Created: explain_decision")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Function 7: authorize_request

# COMMAND ----------

spark.sql(f"""
CREATE OR REPLACE FUNCTION {catalog_name}.{schema_name}.authorize_request(
  procedure_code STRING COMMENT 'CPT code',
  diagnosis_code STRING COMMENT 'ICD-10 code',
  patient_id STRING COMMENT 'Patient ID',
  clinical_notes STRING COMMENT 'Provider notes'
)
RETURNS STRING
LANGUAGE PYTHON
COMMENT 'Main authorization function - determines approval decision'
AS $$
  from databricks.sdk import WorkspaceClient
  from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
  from databricks.vector_search.client import VectorSearchClient
  import json
  
  w = WorkspaceClient()
  vsc = VectorSearchClient(disable_notice=True)
  
  # Step 1: Get MCG guideline
  guidelines = vsc.get_index(
    f"{guidelines_endpoint}.{catalog_name}.{schema_name}.clinical_guidelines_index"
  ).similarity_search(
    query_text=f"MCG guideline for procedure {procedure_code}",
    columns=["guideline_id", "questionnaire", "decision_criteria"],
    filters={"platform": "MCG", "procedure_code": procedure_code},
    num_results=1
  )
  
  if not guidelines.get('result', {}).get('data_array'):
    return json.dumps({
      "decision": "MANUAL_REVIEW",
      "reason": "No MCG guideline found for procedure",
      "confidence": 0.0
    })
  
  guideline = guidelines['result']['data_array'][0]
  questionnaire = json.loads(guideline.get('questionnaire', '[]'))
  
  # Step 2: Answer each MCG question
  answers = {}
  for q in questionnaire[:5]:  # Limit to first 5 questions for performance
    question = q['question']
    
    # Search clinical records
    search_results = vsc.get_index(
      f"{clinical_endpoint}.{catalog_name}.{schema_name}.patient_clinical_records_index"
    ).similarity_search(
      query_text=f"Patient {patient_id}: {question}",
      columns=["content"],
      filters={"patient_id": patient_id},
      num_results=2
    )
    
    # Use LLM to answer
    clinical_context = ""
    if search_results.get('result', {}).get('data_array'):
      for result in search_results['result']['data_array'][:2]:
        clinical_context += result.get('content', '')[:500] + "\\n"
    
    messages = [
      ChatMessage(
        role=ChatMessageRole.SYSTEM,
        content="Answer YES or NO based on clinical evidence. Be conservative."
      ),
      ChatMessage(
        role=ChatMessageRole.USER,
        content=f"Question: {question}\\n\\nEvidence:\\n{clinical_context}\\n\\nAnswer (YES/NO):"
      )
    ]
    
    response = w.serving_endpoints.query(
      name="databricks-meta-llama-3-1-405b-instruct",
      messages=messages,
      max_tokens=50
    )
    
    answer = response.choices[0].message.content.strip().upper()
    answers[question] = "YES" if "YES" in answer else "NO"
  
  # Step 3: Determine decision
  yes_count = sum(1 for a in answers.values() if a == "YES")
  total_count = len(answers)
  confidence = yes_count / total_count if total_count > 0 else 0.0
  
  if confidence >= 0.8:  # 80%+ criteria met
    decision = "APPROVED"
  elif confidence >= 0.6:  # 60-80% criteria met
    decision = "MANUAL_REVIEW"
  else:  # < 60% criteria met
    decision = "DENIED"
  
  return json.dumps({
    "decision": decision,
    "mcg_code": guideline.get('guideline_id'),
    "confidence": round(confidence, 2),
    "criteria_met": yes_count,
    "total_criteria": total_count,
    "answers": answers
  })
$$
""")

print("✅ Created: authorize_request")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify All Functions

# COMMAND ----------

functions_df = spark.sql(f"""
SHOW FUNCTIONS IN {catalog_name}.{schema_name}
""")

display(functions_df.filter("function LIKE '%search%' OR function LIKE '%authorize%' OR function LIKE '%mcg%'"))

# COMMAND ----------

# Show function details
for func in ["search_clinical_records", "search_guidelines", "extract_clinical_criteria", 
             "check_mcg_guidelines", "answer_mcg_question", "explain_decision", "authorize_request"]:
    print(f"\n{'='*60}")
    print(f"Function: {catalog_name}.{schema_name}.{func}")
    print(f"{'='*60}")
    display(spark.sql(f"DESCRIBE FUNCTION {catalog_name}.{schema_name}.{func}"))

# COMMAND ----------

print("✅ Setup 07 Complete: All 7 Unity Catalog AI Functions created!")
print("   1. search_clinical_records - Vector Store 1 search")
print("   2. search_guidelines - Vector Store 2 search")
print("   3. extract_clinical_criteria - Parse unstructured notes")
print("   4. check_mcg_guidelines - Get MCG questionnaire")
print("   5. answer_mcg_question - Answer specific MCG questions")
print("   6. explain_decision - Generate explanations")
print("   7. authorize_request - Main authorization workflow")


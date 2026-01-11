# Databricks notebook source
# MAGIC %md
# MAGIC # Create Genie Space for Prior Authorization Analytics
# MAGIC
# MAGIC Creates Genie Space programmatically using Databricks Genie API.
# MAGIC All configuration from config.yaml.
# MAGIC
# MAGIC Reference: https://docs.databricks.com/api/workspace/genie/createspace

# COMMAND ----------

# MAGIC %md
# MAGIC ## Import Configuration

# COMMAND ----------

import sys
import os
sys.path.append(os.path.abspath('..'))
from shared.config import get_config, print_config

from databricks.sdk import WorkspaceClient
import json
import uuid

cfg = get_config()
print_config(cfg)

w = WorkspaceClient()

print(f"Using workspace: {cfg.workspace_host}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Check for Existing Genie Space

# COMMAND ----------

print("Checking for existing Genie spaces...")

try:
    # List spaces using WorkspaceClient API
    response = w.api_client.do(
        'GET',
        '/api/2.0/genie/spaces'
    )
    existing_spaces = response.get('spaces', [])
    
    # Look for space with matching title and DELETE it
    for space in existing_spaces:
        if space.get('title') == cfg.genie_display_name:
            old_space_id = space.get('space_id')
            print(f"🗑️  Found existing space: {old_space_id}")
            print(f"   Title: {space.get('title')}")
            print(f"   Deleting to create fresh...")
            
            # Delete the existing space using Trash API
            try:
                w.api_client.do(
                    'DELETE',
                    f'/api/2.0/genie/spaces/{old_space_id}'
                )
                print(f"✅ Deleted existing space: {old_space_id}")
            except Exception as delete_error:
                print(f"⚠️  Could not delete space: {delete_error}")
                print(f"   You may need to manually delete it from the UI")
    
    print("✅ Ready to create new Genie space")
        
except Exception as e:
    print(f"Error checking/deleting spaces: {e}")
    print("Will proceed with creation...")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Fresh Genie Space

# COMMAND ----------

print(f"Creating new Genie Space: {cfg.genie_display_name}")

try:
    # Create minimal serialized space configuration
    # Point to authorization_requests table (main PA requests table)
    serialized_space = {
        "version": 1,
        "config": {
            "sample_questions": [
                {
                    "id": str(uuid.uuid4()).replace('-', ''),  # UUID without hyphens
                    "question": ["Show me all prior authorization requests"]
                },
                {
                    "id": str(uuid.uuid4()).replace('-', ''),  # UUID without hyphens
                    "question": ["What is the approval rate by procedure type?"]
                },
                {
                    "id": str(uuid.uuid4()).replace('-', ''),  # UUID without hyphens
                    "question": ["Which requests are pending manual review?"]
                },
                {
                    "id": str(uuid.uuid4()).replace('-', ''),  # UUID without hyphens
                    "question": ["Show MCG questions that were answered NO for denied requests"]
                },
                {
                    "id": str(uuid.uuid4()).replace('-', ''),  # UUID without hyphens
                    "question": ["What clinical evidence types are most commonly cited in approvals?"]
                },
                {
                    "id": str(uuid.uuid4()).replace('-', ''),  # UUID without hyphens
                    "question": ["Which providers have the highest manual review rate?"]
                },
                {
                    "id": str(uuid.uuid4()).replace('-', ''),  # UUID without hyphens
                    "question": ["Show approval trends by urgency level over time"]
                },
                {
                    "id": str(uuid.uuid4()).replace('-', ''),  # UUID without hyphens
                    "question": ["What percentage of diabetes patients get approved for procedures?"]
                }
            ],
            "instructions": f"""This space analyzes prior authorization (PA) requests across 4 tables:
1. {cfg.auth_requests_table} - PA requests with decisions (decision: APPROVED/DENIED/MANUAL_REVIEW)
2. {cfg.catalog}.{cfg.schema}.pa_audit_trail - MCG Q&A audit trail (join on request_id, answers: YES/NO, evidence_source types)
3. {cfg.clinical_records_table} - Patient clinical records (join on patient_id, record_type: CLINICAL_NOTE/LAB_RESULT/IMAGING_REPORT)
4. {cfg.guidelines_table} - Clinical guidelines (MCG/InterQual codes and criteria text)

Use these relationships:
- authorization_requests.request_id = pa_audit_trail.request_id (1:many)
- authorization_requests.patient_id = patient_clinical_records.patient_id (1:many)
- authorization_requests.mcg_code = clinical_guidelines.guideline_code (1:1)

Common filters:
- WHERE decision IN ('APPROVED', 'DENIED', 'MANUAL_REVIEW')
- WHERE answer = 'NO' (for audit trail - criteria not met)
- WHERE evidence_source IN ('CLINICAL_NOTE', 'XRAY', 'LAB_RESULT', 'PT_NOTE')
- WHERE urgency_level IN ('STAT', 'URGENT', 'ROUTINE')"""
        },
        "data_sources": {
            "tables": [
                {"identifier": cfg.auth_requests_table},                           # authorization_requests
                {"identifier": f"{cfg.catalog}.{cfg.schema}.pa_audit_trail"},     # audit trail
                {"identifier": cfg.clinical_records_table},                        # patient_clinical_records
                {"identifier": cfg.guidelines_table}                               # clinical_guidelines
            ]
        }
    }
    
    # Create space using WorkspaceClient API
    payload = {
        "title": cfg.genie_display_name,
        "description": cfg.genie_description,
        "warehouse_id": cfg.warehouse_id,
        "serialized_space": json.dumps(serialized_space)
    }
    
    response = w.api_client.do(
        'POST',
        '/api/2.0/genie/spaces',
        body=payload
    )
    
    GENIE_SPACE_ID = response.get('space_id')
    print(f"✅ Genie Space created: {GENIE_SPACE_ID}")
    print(f"   Title: {cfg.genie_display_name}")
    
except Exception as e:
    print(f"❌ Error creating space: {e}")
    raise e

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configure Genie Space

# COMMAND ----------

print(f"Configuring Genie Space {GENIE_SPACE_ID}...")

try:
    # Update space with warehouse using WorkspaceClient API
    payload = {
        "title": cfg.genie_display_name,
        "description": cfg.genie_description,
        "warehouse_id": cfg.warehouse_id
    }
    
    response = w.api_client.do(
        'PATCH',
        f'/api/2.0/genie/spaces/{GENIE_SPACE_ID}',
        body=payload
    )
    
    print(f"✅ Space configured with SQL Warehouse: {cfg.warehouse_id}")
    
except Exception as e:
    print(f"⚠️  Could not update space config: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Save Genie Space ID to Config Table

# COMMAND ----------

# Create config table if it doesn't exist
spark.sql(f"""
CREATE TABLE IF NOT EXISTS {cfg.config_table} (
  config_key STRING NOT NULL,
  config_value STRING NOT NULL,
  updated_at TIMESTAMP NOT NULL,
  CONSTRAINT config_pk PRIMARY KEY(config_key)
)
USING DELTA
COMMENT 'Configuration values for prior authorization system'
""")

# Save Genie Space ID
spark.sql(f"""
MERGE INTO {cfg.config_table} t
USING (
  SELECT 
    'genie_space_id' as config_key,
    '{GENIE_SPACE_ID}' as config_value,
    current_timestamp() as updated_at
) s
ON t.config_key = s.config_key
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
""")

print(f"✅ Genie Space ID saved to {cfg.config_table}")

# Verify
saved_id = spark.sql(f"""
SELECT config_value 
FROM {cfg.config_table} 
WHERE config_key = 'genie_space_id'
""").collect()[0][0]

print(f"   Verified saved ID: {saved_id}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Grant Service Principal Permissions (MANUAL STEP)

# COMMAND ----------

print("=" * 80)
print("GRANT SERVICE PRINCIPAL PERMISSIONS (ONE-TIME MANUAL STEP)")
print("=" * 80)
print("")
print("ℹ️  NOTE: Databricks does not provide a programmatic API to grant")
print("   Genie Space permissions. This is a one-time manual step.")
print("")
print("🎯 WHAT YOU'RE DOING:")
print("   Granting your Databricks APP permission to query this Genie Space.")
print("   The app runs as a SERVICE PRINCIPAL (like a robot user).")
print("")
print("📋 STEP-BY-STEP INSTRUCTIONS:")
print("")
print(f"1. Open Genie Space in your browser:")
print(f"   {cfg.workspace_host}/#genie/{GENIE_SPACE_ID}")
print("")
print(f"2. Click the 'Share' button (top-right corner)")
print("")
print(f"3. In the search box, type: {cfg.app_name}")
print(f"   ☝️  This is your APP'S SERVICE PRINCIPAL name")
print("")
print(f"4. Select '{cfg.app_name}' from the dropdown")
print(f"   (It will show as a service principal, not a user)")
print("")
print(f"5. Set permission level to: 'Can Run'")
print(f"   (NOT 'Can Use' - select 'Can Run' from the dropdown)")
print("")
print(f"6. Click 'Add' or 'Save'")
print("")
print(f"✅ DONE! The PA Insights page will now be able to query Genie.")
print(f"   This is a ONE-TIME setup per environment (dev/staging/prod).")
print("")
print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Genie Space Instructions

# COMMAND ----------

instructions = f"""
# Prior Authorization Analytics - Data Guide

## Available Data

**Main Tables:**
- {cfg.auth_requests_table} - Prior authorization requests and decisions
- {cfg.clinical_records_table} - Patient clinical records
- {cfg.guidelines_table} - Clinical guidelines and criteria

## Schema - authorization_requests

- **request_id**: Unique PA request identifier (STRING)
- **patient_id**: Patient identifier (STRING)
- **procedure_code**: CPT/HCPCS procedure code (STRING)
- **procedure_name**: Human-readable procedure name (STRING)
- **diagnosis_code**: ICD-10 diagnosis code (STRING)
- **diagnosis_name**: Human-readable diagnosis (STRING)
- **provider_npi**: Provider National Provider Identifier (STRING)
- **request_date**: When PA was requested (TIMESTAMP)
- **urgency**: Request urgency level (STRING)
- **status**: Decision outcome (APPROVED/DENIED/MANUAL_REVIEW)
- **decision_reason**: Explanation of decision (STRING)
- **criteria_met**: Which guidelines were satisfied (ARRAY<STRING>)
- **criteria_missing**: Which guidelines were not met (ARRAY<STRING>)

## Common Queries

### Approval Statistics
- "What percentage of PA requests are approved?"
- "Show approval rate by procedure type"
- "How many requests were auto-approved vs manual review?"
- "What's the denial rate by diagnosis?"

### Trend Analysis
- "Show PA request trends over last 6 months"
- "Which procedures have highest approval rates?"
- "Trend of manual reviews over time"
- "Monthly approval rates by urgency"

### Provider Analysis
- "Which providers have most PA requests?"
- "Show provider approval rates"
- "List top 10 providers by request volume"
- "Providers with highest denial rates"

### Criteria Analysis
- "Most common criteria met"
- "Most common reasons for denial"
- "Requests missing multiple criteria"
- "Guidelines most frequently satisfied"

### Urgency Analysis
- "How many urgent PA requests?"
- "Approval rate by urgency level"
- "Average time to decision by urgency"
- "Urgent requests pending review"

## SQL Tips
- Use `WHERE status = 'APPROVED'` for approved requests
- Filter by `procedure_code` or `procedure_name` for specific procedures
- Use `urgency IN ('URGENT', 'STAT')` for high-priority requests
- Array functions for `criteria_met` and `criteria_missing` analysis
- Join with `{cfg.clinical_records_table}` for patient context

## Example Queries

```sql
-- Approval rate by procedure type
SELECT 
  procedure_name,
  COUNT(*) as total_requests,
  SUM(CASE WHEN status = 'APPROVED' THEN 1 ELSE 0 END) as approved,
  ROUND(100.0 * SUM(CASE WHEN status = 'APPROVED' THEN 1 ELSE 0 END) / COUNT(*), 2) as approval_rate_pct
FROM {cfg.auth_requests_table}
GROUP BY procedure_name
ORDER BY total_requests DESC
LIMIT 10;

-- Requests pending manual review
SELECT 
  request_id, 
  patient_id, 
  procedure_name, 
  diagnosis_name,
  urgency,
  request_date
FROM {cfg.auth_requests_table}
WHERE status = 'MANUAL_REVIEW'
ORDER BY 
  CASE urgency 
    WHEN 'STAT' THEN 1
    WHEN 'URGENT' THEN 2
    WHEN 'ROUTINE' THEN 3
    ELSE 4
  END,
  request_date ASC;
```
"""

print("=" * 80)
print("GENIE SPACE INSTRUCTIONS")
print("=" * 80)
print(instructions)
print("=" * 80)
print("\n💡 TIP: You can add these instructions to the Genie Space via the UI")
print(f"   Open: {cfg.workspace_host}/#genie/{GENIE_SPACE_ID}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verification

# COMMAND ----------

print("=" * 80)
print("GENIE SPACE SETUP COMPLETE!")
print("=" * 80)
print(f"✅ Space ID:       {GENIE_SPACE_ID}")
print(f"✅ Title:          {cfg.genie_display_name}")
print(f"✅ Warehouse ID:   {cfg.warehouse_id}")
print(f"✅ Source Table:   {cfg.auth_requests_table}")
print(f"✅ Saved to:       {cfg.config_table}")
print(f"⚠️  Permissions:    MANUAL STEP REQUIRED (see above)")
print("=" * 80)
print("\n🎉 Next Steps:")
print(f"1. Complete the manual permission grant (instructions above)")
print(f"2. Refresh PA Insights page in your app")
print(f"3. Try asking Genie: 'Show me all prior authorization requests'")
print(f"4. (Optional) Add more sample questions in Genie UI:")
print(f"   {cfg.workspace_host}/#genie/{GENIE_SPACE_ID}")
print("=" * 80)

# Store as output for downstream tasks
try:
    dbutils.jobs.taskValues.set("genie_space_id", GENIE_SPACE_ID)
    print(f"\n✅ Set task value: genie_space_id = {GENIE_SPACE_ID}")
except:
    pass



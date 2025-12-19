# Databricks notebook source
# MAGIC %md
# MAGIC # CLEANUP - Remove All Prior Authorization Resources
# MAGIC
# MAGIC **WARNING:** This will delete:
# MAGIC - Catalog and Schema (from config.yaml)
# MAGIC - Vector Search Indexes (both clinical and guidelines)
# MAGIC - All tables (authorization_requests, patient_clinical_records, clinical_guidelines)
# MAGIC - All UC functions (7 PA functions)
# MAGIC
# MAGIC All configuration loaded from config.yaml via shared.config module.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Import Configuration

# COMMAND ----------

import sys
import os
sys.path.append(os.path.abspath('..'))
from shared.config import get_config, print_config

cfg = get_config()

print("🗑️  PRIOR AUTHORIZATION CLEANUP SCRIPT")
print("=" * 70)
print(f"Will delete:")
print(f"  - Catalog: {cfg.catalog}")
print(f"  - Schema: {cfg.schema}")
print(f"  - Vector Indexes: {cfg.clinical_vector_index}, {cfg.guidelines_vector_index}")
print("=" * 70)
print("\n⚠️  WARNING: This is IRREVERSIBLE!")
print()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Drop Vector Search Indexes

# COMMAND ----------

from databricks.sdk import WorkspaceClient

print("\n🔍 Dropping vector search indexes...")
w = WorkspaceClient()

# Delete clinical records index
try:
    print(f"   Deleting: {cfg.clinical_vector_index}")
    w.vector_search_indexes.delete_index(index_name=cfg.clinical_vector_index)
    print(f"   ✅ Deleted clinical vector index")
except Exception as e:
    print(f"   ⚠️  Clinical index deletion: {e}")

# Delete guidelines index
try:
    print(f"   Deleting: {cfg.guidelines_vector_index}")
    w.vector_search_indexes.delete_index(index_name=cfg.guidelines_vector_index)
    print(f"   ✅ Deleted guidelines vector index")
except Exception as e:
    print(f"   ⚠️  Guidelines index deletion: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Drop UC Functions

# COMMAND ----------

print("\n🔧 Dropping UC Functions...")

functions = [
    "search_clinical_records",
    "search_guidelines",
    "extract_clinical_criteria",
    "check_mcg_guidelines",
    "answer_mcg_question",
    "explain_decision",
    "authorize_request"
]

for func in functions:
    try:
        spark.sql(f"DROP FUNCTION IF EXISTS {cfg.catalog}.{cfg.schema}.{func}")
        print(f"   ✅ Dropped function: {func}")
    except Exception as e:
        print(f"   ⚠️  Function {func} deletion: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Drop Tables

# COMMAND ----------

print("\n📊 Dropping tables...")

tables = [
    "authorization_requests",
    "patient_clinical_records",
    "clinical_guidelines"
]

for table in tables:
    try:
        spark.sql(f"DROP TABLE IF EXISTS {cfg.catalog}.{cfg.schema}.{table}")
        print(f"   ✅ Dropped table: {table}")
    except Exception as e:
        print(f"   ⚠️  Table {table} deletion: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Drop Schema

# COMMAND ----------

print("\n📁 Dropping schema...")

try:
    spark.sql(f"DROP SCHEMA IF EXISTS {cfg.catalog}.{cfg.schema} CASCADE")
    print(f"   ✅ Dropped schema: {cfg.catalog}.{cfg.schema}")
except Exception as e:
    print(f"   ⚠️  Schema deletion: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Drop Catalog

# COMMAND ----------

print("\n🗂️  Dropping catalog...")

try:
    spark.sql(f"DROP CATALOG IF EXISTS {cfg.catalog} CASCADE")
    print(f"   ✅ Dropped catalog: {cfg.catalog}")
except Exception as e:
    print(f"   ⚠️  Catalog deletion: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Delete Vector Search Endpoint (Optional)

# COMMAND ----------

print("\n🔌 Deleting vector search endpoint (optional)...")

try:
    endpoint_name = cfg.vector_endpoint
    print(f"   Deleting endpoint: {endpoint_name}")
    w.vector_search_endpoints.delete_endpoint(endpoint_name=endpoint_name)
    print(f"   ✅ Deleted vector search endpoint: {endpoint_name}")
except Exception as e:
    print(f"   ⚠️  Endpoint deletion: {e}")
    print(f"   Note: Endpoint may be shared, skipping is OK")

# COMMAND ----------

print("\n" + "=" * 70)
print("✅ CLEANUP COMPLETE!")
print("=" * 70)
print("\nAll Prior Authorization resources have been deleted.")
print("You can now redeploy from scratch using:")
print("  ./deploy_with_config.sh dev")
print("=" * 70)


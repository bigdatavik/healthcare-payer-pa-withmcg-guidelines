# Databricks notebook source
# MAGIC %md
# MAGIC # Setup 05: Create Vector Search Index - Clinical Records (Vector Store 1)
# MAGIC
# MAGIC Creates vector search index for patient clinical documents.
# MAGIC
# MAGIC **Configuration:** Reads from config.yaml via shared.config module

# COMMAND ----------

# MAGIC %md
# MAGIC ## Import Configuration

# COMMAND ----------

import sys
import os
sys.path.append(os.path.abspath('..'))
from shared.config import get_config, print_config

cfg = get_config()
print_config(cfg)

# COMMAND ----------

from databricks.vector_search.client import VectorSearchClient

# COMMAND ----------

# Use config values
catalog_name = cfg.catalog
schema_name = cfg.schema
endpoint_name = cfg.vector_endpoint

source_table = cfg.clinical_records_table
index_name = cfg.clinical_vector_index

print(f"📊 Creating vector index:")
print(f"   Source table: {source_table}")
print(f"   Index name: {index_name}")
print(f"   Endpoint: {endpoint_name}")

# COMMAND ----------

# Initialize Vector Search Client
vsc = VectorSearchClient(disable_notice=True)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Vector Search Endpoint

# COMMAND ----------

# Check if endpoint exists
try:
    endpoint = vsc.get_endpoint(endpoint_name)
    print(f"✅ Endpoint '{endpoint_name}' already exists")
except Exception:
    # Create endpoint
    endpoint = vsc.create_endpoint(
        name=endpoint_name,
        endpoint_type="STANDARD"
    )
    print(f"✅ Created endpoint '{endpoint_name}'")
    
    # Wait for endpoint to be ready
    import time
    while True:
        endpoint = vsc.get_endpoint(endpoint_name)
        status = endpoint.get("endpoint_status") if isinstance(endpoint, dict) else getattr(endpoint, "endpoint_status", None)
        if status == "ONLINE":
            break
        print(f"   Status: {status}")
        time.sleep(30)

print(f"✅ Endpoint '{endpoint_name}' is ONLINE")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Vector Index

# COMMAND ----------

import time

print(f"Checking if vector search index exists: {index_name}")

# Check if index already exists
index_exists = False
try:
    existing_index = vsc.get_index(index_name=index_name)
    if existing_index:
        index_exists = True
        status = existing_index.get('status', {}).get('detailed_state', 'UNKNOWN')
        print(f"✅ Index already exists: {index_name}")
        print(f"   Status: {status}")
        print(f"   Source: {source_table}")
        print("\nℹ️  Skipping index creation (already exists)")
        
        # Trigger sync on existing index to get latest data
        print("\nTriggering sync on existing index...")
        try:
            vsc.get_index(index_name=index_name).sync()
            print("✅ Sync triggered successfully - index will update with latest data")
        except Exception as e:
            print(f"⚠️  Could not trigger sync: {e}")
except Exception as get_error:
    print(f"Index does not exist, will create it")

# COMMAND ----------

# Create delta sync index (only if doesn't exist)
if not index_exists:
    index = vsc.create_delta_sync_index(
        endpoint_name=endpoint_name,
        source_table_name=source_table,
        index_name=index_name,
        pipeline_type=cfg.sync_type,
        primary_key="record_id",
        embedding_source_column="content",
        embedding_model_endpoint_name=cfg.embedding_model
    )
    
    print(f"✅ Index creation started: {index_name}")
    print(f"   Endpoint: {endpoint_name}")
    print(f"   Source: {source_table}")
    print(f"   Embedding model: {cfg.embedding_model}")
else:
    print(f"\n✅ Vector index handling complete (existing index reused)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Wait for Index to be Ready

# COMMAND ----------

# Only wait if we just created a new index
if not index_exists:
    # Wait for index to be ready
    print("\nWaiting for index to be ready (this takes 2-5 minutes)...")
    max_wait = 300  # 5 minutes
    wait_time = 0
    while wait_time < max_wait:
        try:
            index_info = vsc.get_index(index_name=index_name)
            status = index_info.get('status', {}).get('detailed_state', 'UNKNOWN')
            if status == 'ONLINE_TRIGGERED_UPDATE' or status == 'ONLINE':
                print(f"✅ Index is ready: {status}")
                break
            print(f"   Status: {status} (waited {wait_time}s)")
            time.sleep(20)
            wait_time += 20
        except Exception as e:
            print(f"   Waiting... ({wait_time}s)")
            time.sleep(20)
            wait_time += 20

    # Trigger initial sync
    print("\nTriggering initial sync...")
    vsc.get_index(index_name=index_name).sync()
    time.sleep(10)
else:
    print("\n✅ Using existing index (already ready)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Vector Search

# COMMAND ----------

# Test semantic search
results = vsc.get_index(index_name=index_name).similarity_search(
    query_text="patient knee pain physical therapy",
    columns=["record_id", "patient_id", "record_type", "content"],
    num_results=5
)

print(f"✅ Test search returned {len(results.get('result', {}).get('data_array', []))} results")
print("\nSample result:")
if results.get('result', {}).get('data_array'):
    print(results['result']['data_array'][0])

# COMMAND ----------

print(f"✅ Setup 05 Complete!")
print(f"   Vector Store 1 (Clinical Records) is ready for semantic search")


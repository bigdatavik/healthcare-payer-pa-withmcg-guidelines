# Databricks notebook source
# MAGIC %md
# MAGIC # Setup 05: Create Vector Search Index - Clinical Records CHUNKS
# MAGIC
# MAGIC Creates vector search index on the CHUNKS table (patient_clinical_records_chunks).
# MAGIC
# MAGIC **Configuration:** Reads from config.yaml via shared.config module

# COMMAND ----------

# MAGIC %md
# MAGIC ## Install Dependencies

# COMMAND ----------

# MAGIC %pip install databricks-vectorsearch --quiet
dbutils.library.restartPython()

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

# CHANGED: Point to CHUNKS table (not full records table)
source_table = f"{catalog_name}.{schema_name}.patient_clinical_records_chunks"
index_name = cfg.clinical_vector_index

print(f"📊 Creating vector index:")
print(f"   Source table: {source_table} (CHUNKS)")
print(f"   Index name: {index_name}")
print(f"   Endpoint: {endpoint_name}")

# COMMAND ----------

# Initialize Vector Search Client
vsc = VectorSearchClient(disable_notice=True)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Vector Search Endpoint (If Needed)

# COMMAND ----------

import time

# Check if endpoint exists and is ready
endpoint_ready = False
try:
    endpoint = vsc.get_endpoint(endpoint_name)
    # Extract status correctly - handle both dict and object
    if isinstance(endpoint, dict):
        status_info = endpoint.get("endpoint_status", {})
        if isinstance(status_info, dict):
            status = status_info.get("state", "UNKNOWN")
        else:
            status = status_info
    else:
        status = getattr(endpoint, "endpoint_status", "UNKNOWN")
    
    print(f"✅ Endpoint '{endpoint_name}' exists")
    print(f"   Status: {status}")
    
    # Only wait if NOT already ONLINE
    if status == "ONLINE":
        endpoint_ready = True
        print(f"✅ Endpoint is already ONLINE - no waiting needed!")
    else:
        print(f"\n⏳ Waiting for endpoint to become ONLINE (current: {status})...")
        max_wait = 600  # 10 minutes
        wait_time = 0
        while wait_time < max_wait:
            time.sleep(30)
            wait_time += 30
            endpoint = vsc.get_endpoint(endpoint_name)
            # Extract status
            if isinstance(endpoint, dict):
                status_info = endpoint.get("endpoint_status", {})
                if isinstance(status_info, dict):
                    status = status_info.get("state", "UNKNOWN")
                else:
                    status = status_info
            else:
                status = getattr(endpoint, "endpoint_status", "UNKNOWN")
            
            print(f"   Waiting... ({wait_time}s) Status: {status}")
            if status == "ONLINE":
                endpoint_ready = True
                break
        
        if not endpoint_ready:
            raise Exception(f"Endpoint did not become ONLINE within {max_wait} seconds. Current status: {status}")
        
        print(f"✅ Endpoint is now ONLINE")
    
except Exception as e:
    if "does not exist" in str(e).lower() or "not found" in str(e).lower():
        # Endpoint doesn't exist, create it
        print(f"⚠️  Endpoint '{endpoint_name}' not found")
        print(f"📝 Creating new endpoint: {endpoint_name}")
        endpoint = vsc.create_endpoint(
            name=endpoint_name,
            endpoint_type="STANDARD"
        )
        print(f"✅ Created endpoint '{endpoint_name}'")
        
        # Wait for new endpoint to be ready
        print("\n⏳ Waiting for new endpoint to become ONLINE...")
        max_wait = 600
        wait_time = 0
        while wait_time < max_wait:
            time.sleep(30)
            wait_time += 30
            endpoint = vsc.get_endpoint(endpoint_name)
            # Extract status
            if isinstance(endpoint, dict):
                status_info = endpoint.get("endpoint_status", {})
                if isinstance(status_info, dict):
                    status = status_info.get("state", "UNKNOWN")
                else:
                    status = status_info
            else:
                status = getattr(endpoint, "endpoint_status", "UNKNOWN")
            
            print(f"   Waiting... ({wait_time}s) Status: {status}")
            if status == "ONLINE":
                endpoint_ready = True
                break
        
        if not endpoint_ready:
            raise Exception(f"New endpoint did not become ONLINE within {max_wait} seconds")
        
        print(f"✅ New endpoint is ONLINE")
    else:
        # Some other error
        raise e

if not endpoint_ready:
    raise Exception(f"Endpoint '{endpoint_name}' is not ready")

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
        primary_key="chunk_id",  # CHANGED: chunk_id (not record_id)
        embedding_source_column="chunk_text",  # CHANGED: chunk_text (not content)
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

# Test semantic search on CHUNKS table
results = vsc.get_index(index_name=index_name).similarity_search(
    query_text="patient knee pain physical therapy",
    columns=["chunk_id", "patient_id", "record_type", "chunk_text"],  # CHUNKS table columns
    num_results=5
)

print(f"✅ Test search returned {len(results.get('result', {}).get('data_array', []))} results")
print("\nSample result:")
if results.get('result', {}).get('data_array'):
    print(results['result']['data_array'][0])

# COMMAND ----------

print(f"✅ Setup 05 Complete!")
print(f"   Vector Store 1 (Clinical Records CHUNKS) is ready for semantic search")



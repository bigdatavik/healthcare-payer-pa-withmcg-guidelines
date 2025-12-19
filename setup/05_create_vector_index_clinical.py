# Databricks notebook source
# MAGIC %md
# MAGIC # Setup 05: Create Vector Search Index - Clinical Records (Vector Store 1)
# MAGIC
# MAGIC Creates vector search index for patient clinical documents.

# COMMAND ----------

from databricks.vector_search.client import VectorSearchClient

# COMMAND ----------

dbutils.widgets.text("catalog_name", "healthcare_payer_pa_withmcg_guidelines_dev", "Catalog Name")
dbutils.widgets.text("schema_name", "main", "Schema Name")
dbutils.widgets.text("endpoint_name", "pa_clinical_records_endpoint", "Vector Endpoint Name")

catalog_name = dbutils.widgets.get("catalog_name")
schema_name = dbutils.widgets.get("schema_name")
endpoint_name = dbutils.widgets.get("endpoint_name")

source_table = f"{catalog_name}.{schema_name}.patient_clinical_records"
index_name = f"{catalog_name}.{schema_name}.patient_clinical_records_index"

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
    while endpoint.endpoint_status != "ONLINE":
        time.sleep(30)
        endpoint = vsc.get_endpoint(endpoint_name)
        print(f"   Status: {endpoint.endpoint_status}")

print(f"✅ Endpoint '{endpoint_name}' is ONLINE")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Vector Index

# COMMAND ----------

# Delete index if exists (for clean deployment)
try:
    vsc.delete_index(index_name)
    print(f"Deleted existing index: {index_name}")
    import time
    time.sleep(30)  # Wait for deletion
except Exception as e:
    print(f"No existing index to delete: {e}")

# COMMAND ----------

# Create delta sync index
index = vsc.create_delta_sync_index(
    endpoint_name=endpoint_name,
    source_table_name=source_table,
    index_name=index_name,
    pipeline_type="TRIGGERED",
    primary_key="record_id",
    embedding_source_column="content",
    embedding_model_endpoint_name="databricks-gte-large-en"
)

print(f"✅ Created vector index: {index_name}")

# COMMAND ----------

# Wait for index to be ready
import time
while True:
    index_status = vsc.get_index(index_name)
    if hasattr(index_status, 'status') and index_status.status.ready:
        print("✅ Index is READY")
        break
    print(f"   Index status: {getattr(index_status, 'status', 'UNKNOWN')}")
    time.sleep(30)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Vector Search

# COMMAND ----------

# Test semantic search
results = vsc.get_index(endpoint_name, index_name).similarity_search(
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


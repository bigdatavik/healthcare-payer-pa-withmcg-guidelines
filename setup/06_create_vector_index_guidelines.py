# Databricks notebook source
# MAGIC %md
# MAGIC # Setup 06: Create Vector Search Index - Guidelines (Vector Store 2)
# MAGIC
# MAGIC Creates vector search index for MCG, InterQual, and Medicare guidelines.

# COMMAND ----------

from databricks.vector_search.client import VectorSearchClient

# COMMAND ----------

dbutils.widgets.text("catalog_name", "healthcare_payer_pa_withmcg_guidelines_dev", "Catalog Name")
dbutils.widgets.text("schema_name", "main", "Schema Name")
dbutils.widgets.text("endpoint_name", "pa_guidelines_endpoint", "Vector Endpoint Name")

catalog_name = dbutils.widgets.get("catalog_name")
schema_name = dbutils.widgets.get("schema_name")
endpoint_name = dbutils.widgets.get("endpoint_name")

source_table = f"{catalog_name}.{schema_name}.clinical_guidelines"
index_name = f"{catalog_name}.{schema_name}.clinical_guidelines_index"

# COMMAND ----------

vsc = VectorSearchClient(disable_notice=True)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Vector Search Endpoint

# COMMAND ----------

try:
    endpoint = vsc.get_endpoint(endpoint_name)
    print(f"✅ Endpoint '{endpoint_name}' already exists")
except Exception:
    endpoint = vsc.create_endpoint(
        name=endpoint_name,
        endpoint_type="STANDARD"
    )
    print(f"✅ Created endpoint '{endpoint_name}'")
    
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

try:
    vsc.delete_index(index_name)
    print(f"Deleted existing index: {index_name}")
    import time
    time.sleep(30)
except Exception as e:
    print(f"No existing index to delete: {e}")

# COMMAND ----------

index = vsc.create_delta_sync_index(
    endpoint_name=endpoint_name,
    source_table_name=source_table,
    index_name=index_name,
    pipeline_type="TRIGGERED",
    primary_key="guideline_id",
    embedding_source_column="content",
    embedding_model_endpoint_name="databricks-gte-large-en"
)

print(f"✅ Created vector index: {index_name}")

# COMMAND ----------

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

# Test MCG guideline search
results = vsc.get_index(endpoint_name, index_name).similarity_search(
    query_text="MCG criteria for knee MRI imaging",
    columns=["guideline_id", "platform", "procedure_code", "title"],
    num_results=3
)

print(f"✅ Test search returned {len(results.get('result', {}).get('data_array', []))} results")
print("\nSample MCG guideline:")
if results.get('result', {}).get('data_array'):
    print(results['result']['data_array'][0])

# COMMAND ----------

print(f"✅ Setup 06 Complete!")
print(f"   Vector Store 2 (Guidelines) is ready for semantic search")
print(f"   Contains: MCG, InterQual, and Medicare policies")


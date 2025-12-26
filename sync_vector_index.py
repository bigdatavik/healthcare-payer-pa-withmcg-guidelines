from databricks.vector_search.client import VectorSearchClient
from databricks.sdk import WorkspaceClient
import yaml

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

env = config['environments']['dev']
catalog = env['catalog']
schema = env['schema']
vector_endpoint = config['vector_search']['endpoint']

# Initialize clients
w = WorkspaceClient()
vsc = VectorSearchClient(workspace_client=w)

# Sync clinical records index
clinical_index = f"{catalog}.{schema}.patient_clinical_records_index"
print(f"🔄 Syncing vector index: {clinical_index}")

try:
    index = vsc.get_index(index_name=clinical_index)
    
    # Trigger sync
    vsc.get_index(index_name=clinical_index).sync()
    print(f"✅ Sync triggered for {clinical_index}")
    print(f"   Status: {index.status.indexed_row_count} rows indexed")
    print(f"   Pending: {index.status.pending_indexed_row_count} rows pending")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print(f"   Try running: databricks vector-search index sync {clinical_index}")

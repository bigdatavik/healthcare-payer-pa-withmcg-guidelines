# Prior Authorization Agent - Cheatsheet

Quick reference for common commands and workflows.

---

## 🚀 Quick Start (First Time Setup)

```bash
# 1. Edit config.yaml (set your environment variables)
vim config.yaml

# 2. Deploy everything
./deploy_with_config.sh dev

# 3. Wait for setup job to complete (~30 minutes)
#    Monitor at: Databricks UI → Workflows → pa_setup_job

# 4. Deploy Streamlit app
./deploy_app_source.sh dev

# 5. Grant permissions
./grant_permissions.sh

# 6. Get app URL
databricks apps get pa-dashboard-dev --profile DEFAULT_azure
```

---

## 📋 Common Commands

### Configuration

```bash
# View current config
cat config.yaml

# Generate app.yaml for environment
python generate_app_yaml.py dev
python generate_app_yaml.py staging
python generate_app_yaml.py prod
```

### Deployment

```bash
# Deploy bundle only (no job run)
databricks bundle deploy --profile DEFAULT_azure --target dev

# Deploy bundle + run setup job
./deploy_with_config.sh dev

# Deploy app
./deploy_app_source.sh dev

# Grant permissions
./grant_permissions.sh
```

### Jobs

```bash
# List jobs
databricks jobs list --profile DEFAULT_azure

# Run setup job manually
databricks bundle run pa_setup_job --profile DEFAULT_azure

# Get job run status
databricks runs get <run-id> --profile DEFAULT_azure
```

### Apps

```bash
# List apps
databricks apps list --profile DEFAULT_azure

# Get app details
databricks apps get pa-dashboard-dev --profile DEFAULT_azure

# Get app logs
databricks apps logs pa-dashboard-dev --profile DEFAULT_azure

# Delete app
databricks apps delete pa-dashboard-dev --profile DEFAULT_azure
```

### Testing UC Functions

```sql
-- Test clinical records search
SELECT healthcare_payer_pa_withmcg_guidelines_dev.main.search_clinical_records(
  'PT00001',
  'knee pain physical therapy'
);

-- Test guidelines search
SELECT healthcare_payer_pa_withmcg_guidelines_dev.main.search_guidelines(
  '73721',
  'MCG'
);

-- Test full authorization
SELECT healthcare_payer_pa_withmcg_guidelines_dev.main.authorize_request(
  '73721',     -- procedure_code
  'M25.561',   -- diagnosis_code
  'PT00001',   -- patient_id
  'Patient presents with chronic knee pain'  -- clinical_notes
);
```

---

## 🔧 Development Workflow

### Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Test config loading
python -c "from shared.config import get_config, print_config; cfg = get_config('dev'); print_config(cfg)"

# Run agent locally (not in Streamlit)
cd src/agent
python pa_agent.py
```

### Notebooks

```bash
# All setup notebooks read from config.yaml automatically
# Just run them in Databricks UI or via bundle

# Test a specific notebook
databricks workspace export /Workspace/Users/<you>/.bundle/healthcare-payer-pa-withmcg-guidelines/dev/files/setup/01_create_catalog_schema.py
```

---

## 🐛 Troubleshooting

### App Shows "Database connection error"

**Problem:** Service principal doesn't have permissions

**Fix:**
```bash
./grant_permissions.sh
```

### Vector indexes not syncing

**Problem:** Indexes take 15-30 minutes to populate

**Check status:**
```sql
-- In SQL Warehouse
DESCRIBE EXTENDED healthcare_payer_pa_withmcg_guidelines_dev.main.patient_clinical_records_index;
DESCRIBE EXTENDED healthcare_payer_pa_withmcg_guidelines_dev.main.clinical_guidelines_index;
```

### UC Functions not found

**Problem:** Setup notebook 07 didn't complete

**Fix:**
```bash
# Re-run function creation
databricks workspace export /Workspace/.../.bundle/.../setup/07_create_uc_functions.py
# Run in Databricks
```

### Config not loading in notebooks

**Problem:** `shared/config.py` not in Python path

**Fix:** Add to notebook:
```python
import sys
sys.path.append('/Workspace/Users/<you>/.bundle/healthcare-payer-pa-withmcg-guidelines/dev/files')
from shared.config import get_config
cfg = get_config()
```

---

## 📊 Monitoring

### Check PA Request Status

```sql
SELECT 
    decision,
    COUNT(*) as count,
    AVG(confidence_score) as avg_confidence
FROM healthcare_payer_pa_withmcg_guidelines_dev.main.authorization_requests
WHERE decision IS NOT NULL
GROUP BY decision;
```

### Check Vector Index Stats

```sql
-- Clinical records count
SELECT COUNT(*) FROM healthcare_payer_pa_withmcg_guidelines_dev.main.patient_clinical_records;

-- Guidelines count
SELECT COUNT(*) FROM healthcare_payer_pa_withmcg_guidelines_dev.main.clinical_guidelines;

-- PA requests by urgency
SELECT urgency_level, COUNT(*) 
FROM healthcare_payer_pa_withmcg_guidelines_dev.main.authorization_requests
GROUP BY urgency_level;
```

---

## 🗑️ Cleanup

### Delete Everything

```bash
# Delete app
databricks apps delete pa-dashboard-dev --profile DEFAULT_azure

# Delete catalog (⚠️ DESTRUCTIVE)
databricks catalogs delete healthcare_payer_pa_withmcg_guidelines_dev --profile DEFAULT_azure

# Delete vector endpoints (⚠️ DESTRUCTIVE)
databricks vector-search delete-endpoint pa_clinical_records_endpoint --profile DEFAULT_azure
databricks vector-search delete-endpoint pa_guidelines_endpoint --profile DEFAULT_azure
```

### Soft Reset (Keep data, re-run setup)

```bash
# Just re-run setup job
databricks bundle run pa_setup_job --profile DEFAULT_azure
```

---

## 📚 File Structure

```
healthcare-payer-pa-withmcg-guidelines/
├── config.yaml              ← Edit this for your environment
├── shared/
│   └── config.py            ← Config loader (don't edit)
├── setup/                   ← 8 setup notebooks
├── src/agent/               ← LangGraph agent
├── dashboard/               ← Streamlit app
│   ├── app.yaml             ← Auto-generated (don't edit)
│   └── app.py               ← Main app
├── deploy_with_config.sh    ← Deploy everything
├── deploy_app_source.sh     ← Deploy app only
└── grant_permissions.sh     ← Grant permissions
```

---

## 🔗 Useful Links

- **Databricks Workspace:** https://adb-984752964297111.11.azuredatabricks.net
- **SQL Warehouse:** /sql/warehouses/148ccb90800933a1
- **Vector Search Docs:** https://docs.databricks.com/generative-ai/vector-search.html
- **LangGraph Docs:** https://langchain-ai.github.io/langgraph/
- **Databricks Apps Docs:** https://docs.databricks.com/aws/dev-tools/databricks-apps/

---

**Last Updated:** December 19, 2024


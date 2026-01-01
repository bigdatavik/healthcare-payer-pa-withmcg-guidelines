# Service Principal Permissions Architecture

**Date:** 2026-01-01  
**Status:** ✅ IMPLEMENTED

---

## 🎯 Overview

The **Databricks Apps service principal** is the identity used by the PA Dashboard application to access Unity Catalog resources. This document explains:

- What permissions are needed and why
- How service principal authentication works
- Permission granting workflow
- Troubleshooting permission issues

---

## 🔑 Service Principal Identity

### **Application Details:**

| Property | Value |
|----------|-------|
| **App Name** | `pa-dashboard-dev` |
| **Service Principal Name** | `app-7hspbl pa-dashboard-dev` |
| **Service Principal ID** | `149155025556583` |
| **Client ID** | `d72a75e1-c8ab-4249-b225-d0fdf194bc62` |
| **Type** | Databricks Apps Service Principal |

### **How Authentication Works:**

When the Streamlit app runs inside **Databricks Apps**, the `WorkspaceClient()` with no parameters automatically authenticates as the app's service principal:

```python
from databricks.sdk import WorkspaceClient

# In Databricks Apps - uses service principal automatically
w = WorkspaceClient()  # ← Authenticates as app-7hspbl pa-dashboard-dev

# Outside Databricks Apps - uses profile
w = WorkspaceClient(profile="DEFAULT_azure")  # ← Authenticates as user
```

**Key Points:**
- ✅ No credentials hardcoded in code
- ✅ Automatic authentication via Databricks runtime
- ✅ Permissions managed centrally via Unity Catalog
- ✅ Follows principle of least privilege

---

## 📋 Required Permissions

### **1. Catalog Level:**

```sql
GRANT USE_CATALOG ON CATALOG healthcare_payer_pa_withmcg_guidelines_dev 
TO SERVICE_PRINCIPAL `d72a75e1-c8ab-4249-b225-d0fdf194bc62`;
```

**Why Needed:**
- Access catalog to query tables
- Required before any schema or table access

---

### **2. Schema Level:**

```sql
GRANT USE_SCHEMA, SELECT, MODIFY ON SCHEMA healthcare_payer_pa_withmcg_guidelines_dev.main
TO SERVICE_PRINCIPAL `d72a75e1-c8ab-4249-b225-d0fdf194bc62`;
```

**Permissions Explained:**

| Permission | Why Needed |
|------------|------------|
| `USE_SCHEMA` | Access schema objects |
| `SELECT` | Read tables in schema |
| `MODIFY` | Create/replace tables, insert records |

**Why MODIFY at Schema Level:**
- Required for `CREATE OR REPLACE TABLE` operations
- Allows recreating tables during reset operations
- Needed for the "Reset pa_audit_trail Table" button

---

### **3. Table: `authorization_requests`:**

```sql
GRANT SELECT, MODIFY ON TABLE healthcare_payer_pa_withmcg_guidelines_dev.main.authorization_requests
TO SERVICE_PRINCIPAL `d72a75e1-c8ab-4249-b225-d0fdf194bc62`;
```

**Operations:**

| Operation | Permission | Use Case |
|-----------|------------|----------|
| Read pending requests | `SELECT` | Load queue |
| Update decision | `MODIFY` | Save PA decision |
| Reset to pending | `MODIFY` | Demo reset |

---

### **4. Table: `pa_audit_trail`:**

```sql
GRANT ALL_PRIVILEGES ON TABLE healthcare_payer_pa_withmcg_guidelines_dev.main.pa_audit_trail
TO SERVICE_PRINCIPAL `d72a75e1-c8ab-4249-b225-d0fdf194bc62`;
```

**Why ALL_PRIVILEGES:**
- `SELECT` - Read audit trail for UI display
- `MODIFY` - Insert Q&A records
- `CREATE` - Recreate table during reset
- `DELETE` - (Not currently used, but included for completeness)

**Operations:**

| Operation | Permission | SQL Statement | Use Case |
|-----------|------------|---------------|----------|
| Read audit records | `SELECT` | `SELECT * FROM pa_audit_trail WHERE request_id = ?` | Display Q&A breakdown |
| Save Q&A entry | `MODIFY` | `INSERT INTO pa_audit_trail VALUES (...)` | Record agent answers |
| Reset table | `CREATE`/`MODIFY` | `CREATE OR REPLACE TABLE pa_audit_trail (...)` | Clear all records for testing |

---

### **5. Table: `patient_clinical_records`:**

```sql
GRANT SELECT ON TABLE healthcare_payer_pa_withmcg_guidelines_dev.main.patient_clinical_records
TO SERVICE_PRINCIPAL `d72a75e1-c8ab-4249-b225-d0fdf194bc62`;
```

**Why Needed:**
- Read-only access to load patient clinical notes
- Agent uses full records for PA review

---

### **6. Table: `clinical_guidelines`:**

```sql
GRANT SELECT ON TABLE healthcare_payer_pa_withmcg_guidelines_dev.main.clinical_guidelines
TO SERVICE_PRINCIPAL `d72a75e1-c8ab-4249-b225-d0fdf194bc62`;
```

**Why Needed:**
- Read-only access to load MCG guidelines
- Agent uses full guidelines for questionnaire

---

### **7. SQL Warehouse:**

```sql
-- Via Databricks CLI or UI
databricks permissions set warehouse 148ccb90800933a1 
  service_principal d72a75e1-c8ab-4249-b225-d0fdf194bc62 CAN_USE
```

**Why Needed:**
- Execute SQL statements via Statement Execution API
- Required for all table operations

---

### **8. Unity Catalog Functions:**

```sql
GRANT EXECUTE ON FUNCTION healthcare_payer_pa_withmcg_guidelines_dev.main.extract_mcg_criteria
TO SERVICE_PRINCIPAL `d72a75e1-c8ab-4249-b225-d0fdf194bc62`;

GRANT EXECUTE ON FUNCTION healthcare_payer_pa_withmcg_guidelines_dev.main.check_mcg_criteria
TO SERVICE_PRINCIPAL `d72a75e1-c8ab-4249-b225-d0fdf194bc62`;

GRANT EXECUTE ON FUNCTION healthcare_payer_pa_withmcg_guidelines_dev.main.answer_mcg_question
TO SERVICE_PRINCIPAL `d72a75e1-c8ab-4249-b225-d0fdf194bc62`;

GRANT EXECUTE ON FUNCTION healthcare_payer_pa_withmcg_guidelines_dev.main.explain_pa_decision
TO SERVICE_PRINCIPAL `d72a75e1-c8ab-4249-b225-d0fdf194bc62`;
```

**Why Needed:**
- Agent calls UC functions for MCG evaluation
- Functions use Foundation Model APIs

---

## 🛠️ Grant Permissions Script

### **Script: `grant_permissions.sh`**

**Location:** `/Users/vik.malhotra/healthcare-payer-pa-withmcg-guidelines/grant_permissions.sh`

**Usage:**
```bash
./grant_permissions.sh dev
```

**What It Does:**

1. Reads config from `config.yaml` (catalog, schema, warehouse ID)
2. Gets app service principal client ID
3. Grants catalog permission (`USE_CATALOG`)
4. Grants schema permissions (`USE_SCHEMA`, `SELECT`, `MODIFY`)
5. Grants table permissions (`SELECT`, `MODIFY`, `ALL_PRIVILEGES`)
6. Grants warehouse permission (`CAN_USE`)
7. Grants UC function permissions (`EXECUTE`)

**Script Content:**
```bash
#!/bin/bash
set -e

ENVIRONMENT=${1:-dev}
PROFILE="DEFAULT_azure"

# Get config values
CATALOG=$(yq eval ".environments.${ENVIRONMENT}.catalog" config.yaml)
SCHEMA=$(yq eval ".environments.${ENVIRONMENT}.schema" config.yaml)
WAREHOUSE_ID=$(yq eval ".environments.${ENVIRONMENT}.warehouse_id" config.yaml)
APP_NAME="pa-dashboard-${ENVIRONMENT}"

# Get service principal client ID
SP_CLIENT_ID=$(databricks apps get $APP_NAME --profile $PROFILE --output json | jq -r '.service_principal_client_id')

echo "🔐 Granting Service Principal Permissions"
echo "=========================================
echo "App Name: $APP_NAME"
echo "Catalog: $CATALOG"
echo "Schema: $SCHEMA"
echo "Warehouse: $WAREHOUSE_ID"
echo ""

# 1. Grant catalog permissions
databricks grants update catalog $CATALOG --profile $PROFILE \
  --json "{\"changes\": [{\"principal\": \"$SP_CLIENT_ID\", \"add\": [\"USE_CATALOG\"]}]}"

# 2. Grant schema permissions
databricks grants update schema $CATALOG.$SCHEMA --profile $PROFILE \
  --json "{\"changes\": [{\"principal\": \"$SP_CLIENT_ID\", \"add\": [\"USE_SCHEMA\", \"SELECT\", \"MODIFY\"]}]}"

# 3. Grant table permissions - authorization_requests
databricks grants update table $CATALOG.$SCHEMA.authorization_requests --profile $PROFILE \
  --json "{\"changes\": [{\"principal\": \"$SP_CLIENT_ID\", \"add\": [\"MODIFY\", \"SELECT\"]}]}"

# 4. Grant table permissions - pa_audit_trail
databricks grants update table $CATALOG.$SCHEMA.pa_audit_trail --profile $PROFILE \
  --json "{\"changes\": [{\"principal\": \"$SP_CLIENT_ID\", \"add\": [\"ALL_PRIVILEGES\"]}]}"

# 5. Grant warehouse permissions
databricks permissions update warehouses $WAREHOUSE_ID --profile $PROFILE \
  --json "{\"access_control_list\": [{\"service_principal_name\": \"$SP_CLIENT_ID\", \"permission_level\": \"CAN_USE\"}]}"

# 6. Grant UC function permissions
./grant_function_permissions.sh $ENVIRONMENT

echo "✅ All permissions granted successfully!"
```

---

## 🚫 What Service Principals CANNOT Do

### **Limitations:**

1. **DELETE operations may fail in some contexts**
   - Databricks Apps service principals have restrictions on `DELETE FROM` statements
   - **Workaround:** Use `CREATE OR REPLACE TABLE` to clear data
   - This is why the audit trail reset uses `CREATE OR REPLACE` instead of `DELETE`

2. **User-level operations**
   - Cannot impersonate users
   - Cannot access user-specific resources
   - No access to user credentials

3. **Write to ignored files**
   - Cannot modify `.gitignore`d files
   - Cannot write to certain system directories

### **Best Practices:**

✅ **DO:**
- Use `CREATE OR REPLACE TABLE` for bulk deletes
- Use `INSERT INTO` for adding records
- Use `UPDATE` for modifying records
- Use `MERGE` (upsert) to avoid duplicates

❌ **DON'T:**
- Use `DELETE FROM` in app code (may fail)
- Use `TRUNCATE TABLE` (restricted)
- Assume same permissions as user credentials

---

## 🔍 Troubleshooting

### **Issue 1: "Permission Denied" on Table**

**Symptoms:**
```
Error: Permission denied: Cannot read table 'pa_audit_trail'
```

**Solution:**
```bash
# Re-grant permissions
./grant_permissions.sh dev

# Verify permissions
databricks grants get table healthcare_payer_pa_withmcg_guidelines_dev.main.pa_audit_trail --profile DEFAULT_azure
```

**Check:**
- Service principal has `SELECT` on table
- Service principal has `USE_SCHEMA` on schema
- Service principal has `USE_CATALOG` on catalog

---

### **Issue 2: "Cannot Execute Statement" on Warehouse**

**Symptoms:**
```
Error: User does not have permission to use warehouse
```

**Solution:**
```bash
# Grant warehouse access
databricks permissions update warehouses 148ccb90800933a1 --profile DEFAULT_azure \
  --json '{"access_control_list": [{"service_principal_name": "d72a75e1-c8ab-4249-b225-d0fdf194bc62", "permission_level": "CAN_USE"}]}'
```

---

### **Issue 3: "Cannot Create Table"**

**Symptoms:**
```
Error: Permission denied: Cannot create table in schema
```

**Solution:**
- Ensure `MODIFY` permission on **schema level** (not just table level)
- `CREATE OR REPLACE TABLE` requires schema-level `MODIFY`

```bash
databricks grants update schema healthcare_payer_pa_withmcg_guidelines_dev.main --profile DEFAULT_azure \
  --json '{"changes": [{"principal": "d72a75e1-c8ab-4249-b225-d0fdf194bc62", "add": ["MODIFY"]}]}'
```

---

### **Issue 4: "Function Not Found"**

**Symptoms:**
```
Error: Function 'extract_mcg_criteria' does not exist
```

**Solution:**
```bash
# Grant function permissions
./grant_function_permissions.sh dev
```

---

### **Issue 5: "Table Was Recreated, Permissions Lost"**

**Symptoms:**
After running "Reset pa_audit_trail Table", app cannot access table.

**Root Cause:**
`CREATE OR REPLACE TABLE` drops and recreates the table, which clears all grants.

**Solution:**
Always re-grant permissions after recreating tables:

```bash
# After reset button clicked
./grant_permissions.sh dev
```

**Better Approach:**
Build re-granting into the reset button code:

```python
# After CREATE OR REPLACE TABLE
w.statement_execution.execute_statement(
    statement=f"GRANT ALL_PRIVILEGES ON TABLE {CATALOG}.{SCHEMA}.pa_audit_trail TO SERVICE_PRINCIPAL `{SP_CLIENT_ID}`"
)
```

---

## 🔐 Security Best Practices

### **1. Principle of Least Privilege:**
- Only grant permissions actually needed
- Use `SELECT` where read-only access suffices
- Use `MODIFY` only for tables that need writes
- Avoid `ALL_PRIVILEGES` unless necessary

### **2. Audit Permissions Regularly:**
```bash
# List all permissions for service principal
databricks grants get catalog healthcare_payer_pa_withmcg_guidelines_dev --profile DEFAULT_azure

databricks grants get schema healthcare_payer_pa_withmcg_guidelines_dev.main --profile DEFAULT_azure

databricks grants get table healthcare_payer_pa_withmcg_guidelines_dev.main.pa_audit_trail --profile DEFAULT_azure
```

### **3. Separate Dev/Prod:**
- Use different service principals for dev and prod
- Grant more permissions in dev (for testing)
- Restrict prod permissions tightly

### **4. Monitor Access:**
- Enable Unity Catalog audit logs
- Monitor for unauthorized access attempts
- Review service principal activity

---

## 📊 Permission Matrix

| Resource | Permission | Reason |
|----------|------------|--------|
| **Catalog** | `USE_CATALOG` | Access catalog |
| **Schema** | `USE_SCHEMA` | Access schema objects |
| **Schema** | `SELECT` | Read tables |
| **Schema** | `MODIFY` | Create/replace tables |
| **authorization_requests** | `SELECT` | Load PA queue |
| **authorization_requests** | `MODIFY` | Save decisions, reset |
| **pa_audit_trail** | `ALL_PRIVILEGES` | Full control for Q&A tracking and reset |
| **patient_clinical_records** | `SELECT` | Read clinical notes |
| **clinical_guidelines** | `SELECT` | Read MCG guidelines |
| **SQL Warehouse** | `CAN_USE` | Execute SQL statements |
| **UC Functions** | `EXECUTE` | Call MCG evaluation functions |

---

## ✅ Verification Checklist

After granting permissions, verify:

- [ ] App can load pending PA requests
- [ ] App can save PA decisions
- [ ] App can insert audit trail records
- [ ] App can load audit trail for display
- [ ] App can reset PA requests
- [ ] App can recreate audit trail table
- [ ] App can call UC functions
- [ ] App can query clinical records
- [ ] App can query guidelines

**Test Script:**
```sql
-- Run as service principal (via app)
SELECT COUNT(*) FROM authorization_requests;
SELECT COUNT(*) FROM pa_audit_trail;
SELECT COUNT(*) FROM patient_clinical_records;
SELECT COUNT(*) FROM clinical_guidelines;

-- Test write
INSERT INTO pa_audit_trail VALUES (...);

-- Test reset
CREATE OR REPLACE TABLE pa_audit_trail (...);
```

---

## 🔗 Related Documentation

- [PA_AUDIT_TRAIL_ARCHITECTURE.md](PA_AUDIT_TRAIL_ARCHITECTURE.md) - Audit trail design
- [TWO_TABLE_IMPLEMENTATION_COMPLETE.md](TWO_TABLE_IMPLEMENTATION_COMPLETE.md) - Data architecture
- [README.md](README.md) - Architecture overview

---

*Last Updated: January 1, 2026*


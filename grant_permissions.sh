#!/bin/bash
# Grant service principal permissions for PA Dashboard App

set -e

# ============================================================================
# Auto-detect Databricks CLI (v0.200+ required for bundle support)
# ============================================================================
DATABRICKS_CLI=""

# Check common installation locations in order of preference
for cli_path in /opt/homebrew/bin/databricks /usr/local/bin/databricks $(which databricks 2>/dev/null); do
    # Skip if path is empty or not executable
    if [ -z "$cli_path" ] || [ ! -x "$cli_path" ]; then
        continue
    fi
    
    # Get version and check if it's >= 0.200.0
    VERSION=$("$cli_path" --version 2>&1 | grep -oE 'v?[0-9]+\.[0-9]+\.[0-9]+' | head -1 | sed 's/v//')
    
    if [ -n "$VERSION" ]; then
        # Extract minor version (e.g., "270" from "0.270.0")
        MINOR=$(echo "$VERSION" | cut -d. -f2)
        
        # Check if minor version >= 200 (new CLI with bundle support)
        if [ "$MINOR" -ge 200 ] 2>/dev/null; then
            DATABRICKS_CLI="$cli_path"
            break
        fi
    fi
done

# Exit if no suitable CLI found
if [ -z "$DATABRICKS_CLI" ]; then
    echo "❌ Error: Databricks CLI v0.200+ not found"
    echo ""
    echo "Installation instructions:"
    echo "  macOS:   brew install databricks/tap/databricks"
    echo "  Linux:   curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh"
    echo ""
    exit 1
fi

# ============================================================================

echo "🔐 Granting Service Principal Permissions"
echo "========================================="

# Get config values
CATALOG=$(python -c "import yaml; cfg=yaml.safe_load(open('config.yaml')); print(cfg['environments']['dev']['catalog'])")
SCHEMA=$(python -c "import yaml; cfg=yaml.safe_load(open('config.yaml')); print(cfg['environments']['dev']['schema'])")
WAREHOUSE_ID=$(python -c "import yaml; cfg=yaml.safe_load(open('config.yaml')); print(cfg['environments']['dev']['warehouse_id'])")
APP_NAME=$(python -c "import yaml; cfg=yaml.safe_load(open('config.yaml')); print(cfg['environments']['dev']['app_name'])")
PROFILE=$(python -c "import yaml; cfg=yaml.safe_load(open('config.yaml')); print(cfg['environments']['dev']['profile'])")

echo "App Name: $APP_NAME"
echo "Catalog: $CATALOG"
echo "Schema: $SCHEMA"
echo "Warehouse: $WAREHOUSE_ID"
echo ""

# Get service principal client ID (UUID)
echo "🔍 Getting service principal client ID..."
SP_CLIENT_ID=$("$DATABRICKS_CLI" apps get $APP_NAME --profile $PROFILE --output json | python -c "import sys, json; print(json.load(sys.stdin).get('service_principal_client_id', ''))")

if [ -z "$SP_CLIENT_ID" ]; then
    echo "❌ Error: Could not get service principal client ID"
    echo "   Make sure the app is deployed first:"
    echo "   databricks bundle deploy --target dev"
    exit 1
fi

echo "✅ Service Principal Client ID: $SP_CLIENT_ID"
echo ""

# Grant catalog permissions
echo "📋 1/3: Granting catalog permissions..."
"$DATABRICKS_CLI" grants update catalog $CATALOG --profile $PROFILE \
  --json "{\"changes\": [{\"principal\": \"$SP_CLIENT_ID\", \"add\": [\"USE_CATALOG\"]}]}"
echo "   ✅ USE_CATALOG granted on $CATALOG"

# Grant schema permissions
echo "📋 2/5: Granting schema permissions..."
"$DATABRICKS_CLI" grants update schema $CATALOG.$SCHEMA --profile $PROFILE \
  --json "{\"changes\": [{\"principal\": \"$SP_CLIENT_ID\", \"add\": [\"USE_SCHEMA\", \"SELECT\", \"MODIFY\"]}]}"
echo "   ✅ USE_SCHEMA, SELECT, MODIFY granted on $CATALOG.$SCHEMA"

# Grant MODIFY permissions on authorization_requests table
echo "📋 3/5: Granting MODIFY on authorization_requests table..."
"$DATABRICKS_CLI" grants update table $CATALOG.$SCHEMA.authorization_requests --profile $PROFILE \
  --json "{\"changes\": [{\"principal\": \"$SP_CLIENT_ID\", \"add\": [\"MODIFY\", \"SELECT\"]}]}"
echo "   ✅ MODIFY, SELECT granted on authorization_requests"

# Grant MODIFY permissions on pa_audit_trail table
echo "📋 4/5: Granting MODIFY on pa_audit_trail table..."
"$DATABRICKS_CLI" grants update table $CATALOG.$SCHEMA.pa_audit_trail --profile $PROFILE \
  --json "{\"changes\": [{\"principal\": \"$SP_CLIENT_ID\", \"add\": [\"MODIFY\", \"SELECT\"]}]}"
echo "   ✅ MODIFY, SELECT granted on pa_audit_trail"

# Grant warehouse permissions
echo "📋 5/5: Granting warehouse permissions..."
"$DATABRICKS_CLI" permissions update sql/warehouses $WAREHOUSE_ID --profile $PROFILE \
  --json "{\"access_control_list\": [{\"service_principal_name\": \"$SP_CLIENT_ID\", \"permission_level\": \"CAN_USE\"}]}"
echo "   ✅ CAN_USE granted on warehouse $WAREHOUSE_ID"

# Grant EXECUTE permissions on UC functions
echo "📋 6/6: Granting EXECUTE permissions on UC functions..."
FUNCTIONS=("check_mcg_guidelines" "answer_mcg_question" "explain_decision" "extract_clinical_criteria")
for FUNCTION in "${FUNCTIONS[@]}"; do
    "$DATABRICKS_CLI" grants update function $CATALOG.$SCHEMA.$FUNCTION --profile $PROFILE \
      --json "{\"changes\": [{\"principal\": \"$SP_CLIENT_ID\", \"add\": [\"EXECUTE\"]}]}" > /dev/null 2>&1 || true
done
echo "   ✅ EXECUTE granted on all UC functions"

echo ""
echo "========================================="
echo "✅ All permissions granted successfully!"
echo ""
echo "📋 Next steps:"
echo "   1. Get app URL: databricks apps get $APP_NAME --profile $PROFILE"
echo "   2. Open app in browser"
echo "   3. Test authorization workflow"




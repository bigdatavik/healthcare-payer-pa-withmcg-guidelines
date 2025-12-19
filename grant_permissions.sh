#!/bin/bash
# Grant service principal permissions for PA Dashboard App

set -e

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

# Get service principal ID
echo "🔍 Getting service principal ID..."
SP_ID=$(databricks apps get $APP_NAME --profile $PROFILE --output json | python -c "import sys, json; print(json.load(sys.stdin).get('service_principal_id', ''))")

if [ -z "$SP_ID" ]; then
    echo "❌ Error: Could not get service principal ID"
    echo "   Make sure the app is deployed first:"
    echo "   ./deploy_app_source.sh dev"
    exit 1
fi

echo "✅ Service Principal ID: $SP_ID"
echo ""

# Grant catalog permissions
echo "📋 1/3: Granting catalog permissions..."
databricks grants update catalog $CATALOG --profile $PROFILE \
  --json "{\"changes\": [{\"principal\": \"$SP_ID\", \"add\": [\"USE_CATALOG\"]}]}"
echo "   ✅ USE_CATALOG granted on $CATALOG"

# Grant schema permissions
echo "📋 2/3: Granting schema permissions..."
databricks grants update schema $CATALOG.$SCHEMA --profile $PROFILE \
  --json "{\"changes\": [{\"principal\": \"$SP_ID\", \"add\": [\"USE_SCHEMA\", \"SELECT\"]}]}"
echo "   ✅ USE_SCHEMA, SELECT granted on $CATALOG.$SCHEMA"

# Grant warehouse permissions
echo "📋 3/3: Granting warehouse permissions..."
databricks permissions update sql/warehouses/$WAREHOUSE_ID --profile $PROFILE \
  --json "{\"access_control_list\": [{\"service_principal_name\": \"$SP_ID\", \"permission_level\": \"CAN_USE\"}]}"
echo "   ✅ CAN_USE granted on warehouse $WAREHOUSE_ID"

echo ""
echo "========================================="
echo "✅ All permissions granted successfully!"
echo ""
echo "📋 Next steps:"
echo "   1. Get app URL: databricks apps get $APP_NAME --profile $PROFILE"
echo "   2. Open app in browser"
echo "   3. Test authorization workflow"


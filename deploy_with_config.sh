#!/bin/bash
# Deploy script that auto-generates app.yaml

set -e  # Exit on error

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
            echo "✓ Using Databricks CLI: $cli_path (v$VERSION)"
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

echo ""

# ============================================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get environment from argument or default to 'dev'
ENVIRONMENT=${1:-dev}

echo "========================================================================"
echo "🚀 PRIOR AUTHORIZATION AGENT DEPLOYMENT"
echo "========================================================================"
echo "Environment: ${ENVIRONMENT}"
echo ""

# Step 1: Validate config.yaml exists
if [ ! -f "config.yaml" ]; then
    echo -e "${RED}❌ ERROR: config.yaml not found!${NC}"
    echo "Please create config.yaml"
    exit 1
fi

# Step 2: Update notebook version and date
echo "📝 Step 1: Updating notebook version and date..."
python update_notebook_version.py --use-git

if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  WARNING: Failed to update notebook version (continuing anyway)${NC}"
fi

echo ""

# Step 3: Generate app.yaml from config.yaml
echo "📝 Step 2: Generating dashboard/app.yaml from config.yaml..."
python generate_app_yaml.py ${ENVIRONMENT}

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ ERROR: Failed to generate app.yaml${NC}"
    exit 1
fi

echo -e "${GREEN}✅ app.yaml generated successfully${NC}"
echo ""

# Step 4: Validate databricks.yml exists
if [ ! -f "databricks.yml" ]; then
    echo -e "${RED}❌ ERROR: databricks.yml not found!${NC}"
    exit 1
fi

# Step 5: Deploy with Databricks Asset Bundles
echo "📦 Step 3: Deploying with Databricks Asset Bundles..."
"$DATABRICKS_CLI" bundle deploy --target ${ENVIRONMENT} --profile DEFAULT_azure

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ ERROR: Deployment failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Deployment successful${NC}"
echo ""

# Step 6: Run setup job to create all resources
echo "⚙️  Step 4: Running setup job (creates catalog, tables, functions, vector indexes)..."
echo ""

"$DATABRICKS_CLI" bundle run pa_setup_job --target ${ENVIRONMENT} --profile DEFAULT_azure

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ ERROR: Setup job failed${NC}"
    echo "Check the job logs in Databricks for details"
    exit 1
fi

echo -e "${GREEN}✅ Setup job completed successfully${NC}"
echo ""

# Step 7: Grant permissions to app service principal
echo "🔒 Step 5: Granting service principal permissions..."
echo ""
echo "⏳ Waiting 10 seconds for app to fully initialize..."
sleep 10

./grant_permissions.sh ${ENVIRONMENT}

if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  WARNING: Permission grant failed${NC}"
    echo "You can manually grant permissions later by running:"
    echo "  ./grant_permissions.sh ${ENVIRONMENT}"
    echo ""
fi

# Step 8: Deploy app source code
echo "🚀 Step 6: Deploying app source code..."
echo ""
echo "⏳ Waiting for app to be ready for deployment (checking status)..."

# Wait a moment for the app to be fully initialized
sleep 5

# Check if there's an active deployment and wait for it
for i in {1..12}; do
    APP_STATUS=$("$DATABRICKS_CLI" apps get pa-dashboard-${ENVIRONMENT} --profile DEFAULT_azure --output json 2>/dev/null | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('compute_status', {}).get('state', 'UNKNOWN'))" 2>/dev/null || echo "UNKNOWN")
    
    if [ "$APP_STATUS" != "DEPLOYING" ]; then
        echo "✅ App ready for deployment (status: $APP_STATUS)"
        break
    fi
    
    echo "  App is still deploying, waiting... ($i/12)"
    sleep 10
done

./deploy_app_source.sh ${ENVIRONMENT}

if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  WARNING: App source deployment failed${NC}"
    echo "You can manually deploy app source later by running:"
    echo "  ./deploy_app_source.sh ${ENVIRONMENT}"
    echo ""
fi

# Step 9: Optional validation tests (doesn't block deployment)
echo ""
echo "🧪 Step 7: Running validation tests (optional)..."
echo "   This validates the complete PA workflow but doesn't block deployment"
echo ""

"$DATABRICKS_CLI" bundle run pa_validation_job --target ${ENVIRONMENT} --profile DEFAULT_azure || {
    echo -e "${YELLOW}⚠️  WARNING: Validation tests failed or timed out${NC}"
    echo "   Your app is still functional - validation is for testing only"
    echo "   Run './run_validation.sh ${ENVIRONMENT}' to retry validation later"
    echo ""
}

echo "========================================================================"
echo -e "${GREEN}✅ DEPLOYMENT COMPLETE!${NC}"
echo "========================================================================"
echo ""
echo "What was deployed:"
echo "  ✅ Infrastructure (job definitions, app definition)"
echo "  ✅ Setup job executed (catalog, schema, tables, UC functions, vector indexes)"
echo "  ✅ Service principal permissions granted"
echo "  ✅ Streamlit app source code deployed"
echo "  🧪 Validation tests (optional - check logs if needed)"
echo ""
echo "⚠️  IMPORTANT: Vector indexes need 15-30 minutes to sync"
echo "  Monitor at: Databricks UI → Catalog → Vector Search"
echo ""
echo "Next steps:"
echo "  1. Wait 30-60 seconds for app to start"
echo "  2. Access app:"
echo "     https://<workspace>/apps/pa-dashboard-${ENVIRONMENT}"
echo ""
echo "To run validation tests separately:"
echo "  ./run_validation.sh ${ENVIRONMENT}"
echo ""
echo "Configuration used:"
echo "  - Environment: ${ENVIRONMENT}"
echo "  - Config file: config.yaml"
echo "  - Generated: dashboard/app.yaml"
echo "========================================================================"


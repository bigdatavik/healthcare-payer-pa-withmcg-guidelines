#!/bin/bash
# Deploy App Source Code
# This script deploys the Streamlit app source code to Databricks Apps

set -e

ENVIRONMENT=${1:-dev}

echo "🚀 Deploying Streamlit App"
echo "Environment: $ENVIRONMENT"
echo ""

# Load config
APP_NAME=$(python -c "import yaml; cfg=yaml.safe_load(open('config.yaml')); print(cfg['environments']['$ENVIRONMENT']['app_name'])")
PROFILE=$(python -c "import yaml; cfg=yaml.safe_load(open('config.yaml')); print(cfg['environments']['$ENVIRONMENT']['profile'])")

echo "App Name: $APP_NAME"
echo "Profile: $PROFILE"
echo ""

# Get current Databricks username
CURRENT_USER=$(databricks current-user me --profile "$PROFILE" --output json 2>/dev/null | python -c "import sys, json; print(json.load(sys.stdin)['userName'])" 2>&1)

if [ $? -ne 0 ] || [ -z "$CURRENT_USER" ]; then
    echo "❌ ERROR: Could not determine current Databricks user"
    echo "Please ensure Databricks CLI is configured properly"
    exit 1
fi

# Construct the bundle workspace path where source code is deployed
# Pattern: /Workspace/Users/<username>/.bundle/<bundle-name>/<environment>/files/dashboard
BUNDLE_NAME="healthcare-payer-pa-withmcg-guidelines"
BUNDLE_SOURCE_PATH="/Workspace/Users/${CURRENT_USER}/.bundle/${BUNDLE_NAME}/${ENVIRONMENT}/files/dashboard"

echo "Current user: $CURRENT_USER"
echo "Bundle source path: $BUNDLE_SOURCE_PATH"
echo ""

# Deploy app from the bundle workspace path
echo "📤 Deploying app from bundle workspace location..."
databricks apps deploy "$APP_NAME" --source-code-path "$BUNDLE_SOURCE_PATH" --profile "$PROFILE"

if [ $? -ne 0 ]; then
    echo "❌ ERROR: App deployment failed"
    exit 1
fi

echo ""
echo "✅ App deployed successfully!"
echo ""
echo "📋 Next steps:"
echo "   1. Get app URL: databricks apps get $APP_NAME --profile $PROFILE"
echo "   2. Open app in browser"
echo "   3. Test authorization workflow"



#!/bin/bash
# Deploy Streamlit app to Databricks Apps

set -e

if [ "$#" -ne 1 ]; then
    echo "Usage: ./deploy_app_source.sh <environment>"
    echo "Example: ./deploy_app_source.sh dev"
    exit 1
fi

ENVIRONMENT=$1

# Load config
APP_NAME=$(python -c "import yaml; cfg=yaml.safe_load(open('config.yaml')); print(cfg['environments']['$ENVIRONMENT']['app_name'])")
PROFILE=$(python -c "import yaml; cfg=yaml.safe_load(open('config.yaml')); print(cfg['environments']['$ENVIRONMENT']['profile'])")

echo "🚀 Deploying Streamlit App"
echo "Environment: $ENVIRONMENT"
echo "App Name: $APP_NAME"
echo "Profile: $PROFILE"
echo "================================"

# Deploy app
echo "📤 Deploying to Databricks Apps..."
databricks apps deploy $APP_NAME \
  --source-code-path dashboard \
  --profile $PROFILE

echo ""
echo "✅ App deployed successfully!"
echo ""
echo "📋 Next steps:"
echo "   1. Get app URL: databricks apps get $APP_NAME --profile $PROFILE"
echo "   2. Grant permissions: ./grant_permissions.sh"
echo "   3. Test the app in your browser"


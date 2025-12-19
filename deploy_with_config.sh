#!/bin/bash
# Deploy Prior Authorization Agent with config.yaml environment

set -e

# Check arguments
if [ "$#" -ne 1 ]; then
    echo "Usage: ./deploy_with_config.sh <environment>"
    echo "Example: ./deploy_with_config.sh dev"
    exit 1
fi

ENVIRONMENT=$1

echo "🚀 Deploying Prior Authorization Agent"
echo "Environment: $ENVIRONMENT"
echo "================================"

# 1. Generate app.yaml
echo "📝 Step 1: Generating app.yaml..."
python generate_app_yaml.py $ENVIRONMENT

# 2. Deploy bundle
echo "📦 Step 2: Deploying Databricks bundle..."
databricks bundle deploy --profile DEFAULT_azure --target $ENVIRONMENT

# 3. Get job ID
echo "🔍 Step 3: Getting setup job ID..."
JOB_ID=$(databricks bundle run pa_setup_job --profile DEFAULT_azure 2>&1 | grep -oP 'Run URL:.*runs/\K[0-9]+' || echo "")

if [ -n "$JOB_ID" ]; then
    echo "✅ Setup job started: $JOB_ID"
    echo "   Monitor at: https://adb-984752964297111.11.azuredatabricks.net/#job/runs/$JOB_ID"
else
    echo "⚠️  Could not extract job ID - check manually"
fi

echo ""
echo "================================"
echo "✅ Deployment complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Wait for setup job to complete (~15-30 minutes)"
echo "   2. Deploy app: ./deploy_app_source.sh $ENVIRONMENT"
echo "   3. Grant permissions: ./grant_permissions.sh"


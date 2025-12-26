#!/bin/bash
set -e

ENVIRONMENT=${1:-dev}
APP_NAME="pa-dashboard-${ENVIRONMENT}"
CATALOG="healthcare_payer_pa_withmcg_guidelines_${ENVIRONMENT}"
SCHEMA="main"

echo "🔐 Granting EXECUTE Permissions on UC Functions"
echo "========================================="
echo "App Name: $APP_NAME"
echo "Catalog: $CATALOG"
echo "Schema: $SCHEMA"
echo ""

# Get service principal client ID
echo "🔍 Getting service principal client ID..."
SERVICE_PRINCIPAL_CLIENT_ID=$(databricks apps get $APP_NAME --profile DEFAULT_azure | jq -r '.service_principal_client_id')
echo "✅ Service Principal Client ID: $SERVICE_PRINCIPAL_CLIENT_ID"
echo ""

# List of UC functions to grant EXECUTE on
FUNCTIONS=(
    "check_mcg_guidelines"
    "answer_mcg_question"
    "explain_decision"
    "extract_clinical_criteria"
)

# Grant EXECUTE on each function
for FUNCTION in "${FUNCTIONS[@]}"; do
    echo "📋 Granting EXECUTE on ${CATALOG}.${SCHEMA}.${FUNCTION}..."
    databricks grants update function ${CATALOG}.${SCHEMA}.${FUNCTION} \
        --json "{\"changes\": [{\"principal\": \"${SERVICE_PRINCIPAL_CLIENT_ID}\", \"add\": [\"EXECUTE\"]}]}" \
        --profile DEFAULT_azure
    echo "   ✅ EXECUTE granted on ${FUNCTION}"
done

echo ""
echo "========================================="
echo "✅ All function permissions granted!"

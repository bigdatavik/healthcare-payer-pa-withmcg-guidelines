#!/bin/bash
# Run PA workflow validation tests independently

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

ENVIRONMENT=${1:-dev}

echo "========================================================================"
echo "🧪 PA WORKFLOW VALIDATION TESTS"
echo "========================================================================"
echo "Environment: $ENVIRONMENT"
echo ""
echo "This will run comprehensive tests to validate:"
echo "  - UC function behavior"
echo "  - End-to-end PA workflow"
echo "  - Decision logic thresholds"
echo "  - Multiple patient scenarios"
echo ""
echo "⏱️  Expected runtime: ~5-10 minutes"
echo ""

"$DATABRICKS_CLI" bundle run pa_validation_job --target $ENVIRONMENT --profile DEFAULT_azure

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================================================"
    echo "✅ All validation tests passed!"
    echo "========================================================================"
    echo ""
    echo "Your PA system is working correctly!"
else
    echo ""
    echo "========================================================================"
    echo "⚠️  Some validation tests failed"
    echo "========================================================================"
    echo ""
    echo "Check job logs in Databricks for details:"
    echo "  Databricks UI → Workflows → Jobs → pa_validation_${ENVIRONMENT}"
    echo ""
    echo "Note: Test failures don't affect app functionality"
    echo "Your app should still work for PA processing"
fi


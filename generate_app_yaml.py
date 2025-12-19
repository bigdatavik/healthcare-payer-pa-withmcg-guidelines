#!/usr/bin/env python3
"""
Generate app.yaml from config.yaml

Usage:
    python generate_app_yaml.py dev
    python generate_app_yaml.py staging
    python generate_app_yaml.py prod
"""

import sys
import yaml
from pathlib import Path


def generate_app_yaml(environment: str):
    """Generate app.yaml for specified environment"""
    
    # Load config.yaml
    config_path = Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        print(f"❌ Error: config.yaml not found at {config_path}")
        sys.exit(1)
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Validate environment
    if environment not in config['environments']:
        available = ', '.join(config['environments'].keys())
        print(f"❌ Error: Environment '{environment}' not found in config.yaml")
        print(f"   Available environments: {available}")
        sys.exit(1)
    
    env_config = config['environments'][environment]
    common_config = config['common']
    
    # Extract hostname (remove https://)
    workspace_host = env_config['workspace_host'].replace('https://', '')
    
    # Generate app.yaml content
    app_yaml_content = f"""# ✅ CORRECT - Official Microsoft Pattern (per MY_ENVIRONMENT)
# 🤖 AUTO-GENERATED from config.yaml - DO NOT EDIT DIRECTLY!
# Run: python generate_app_yaml.py {environment}
#
# To use these values in your code:
#   import os
#   catalog = os.getenv("CATALOG_NAME")
#   schema = os.getenv("SCHEMA_NAME")

command: ['streamlit', 'run', 'app.py']

env:
  # Core Databricks connection
  - name: 'DATABRICKS_HOST'
    value: '{workspace_host}'
  - name: 'DATABRICKS_WAREHOUSE_ID'
    value: '{env_config['warehouse_id']}'
  
  # Unity Catalog configuration
  - name: 'CATALOG_NAME'
    value: '{env_config['catalog']}'
  - name: 'SCHEMA_NAME'
    value: '{env_config['schema']}'
  
  # Vector Search configuration
  - name: 'VECTOR_ENDPOINT_CLINICAL'
    value: '{env_config['vector_endpoint_clinical']}'
  - name: 'VECTOR_ENDPOINT_GUIDELINES'
    value: '{env_config['vector_endpoint_guidelines']}'
  
  # LLM configuration
  - name: 'LLM_ENDPOINT'
    value: '{env_config['llm_endpoint']}'
  
  # Environment identifier
  - name: 'ENVIRONMENT'
    value: '{environment}'
  
  # Embedding model for vector search
  - name: 'EMBEDDING_MODEL'
    value: '{common_config['embedding_model']}'
  
  # Decision thresholds
  - name: 'AUTO_APPROVE_THRESHOLD'
    value: '{common_config['auto_approve_threshold']}'
  - name: 'MANUAL_REVIEW_THRESHOLD'
    value: '{common_config['manual_review_threshold']}'
"""
    
    # Write to dashboard/app.yaml
    output_path = Path(__file__).parent / "dashboard" / "app.yaml"
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, 'w') as f:
        f.write(app_yaml_content)
    
    print(f"✅ Generated {output_path}")
    print(f"   Environment: {environment}")
    print(f"   Catalog: {env_config['catalog']}")
    print(f"   App Name: {env_config['app_name']}")
    print(f"\n📋 Next steps:")
    print(f"   1. Review dashboard/app.yaml")
    print(f"   2. Deploy: databricks apps deploy {env_config['app_name']} --source-code-path dashboard --profile {env_config['profile']}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python generate_app_yaml.py <environment>")
        print("Example: python generate_app_yaml.py dev")
        sys.exit(1)
    
    environment = sys.argv[1]
    generate_app_yaml(environment)


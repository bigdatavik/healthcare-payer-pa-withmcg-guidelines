"""
Prior Authorization Agent - Shared Configuration Module

This module reads config.yaml and provides configuration to:
- Setup notebooks (interactive or DAB)
- Agent notebooks
- Streamlit app

ALL configuration comes from config.yaml - change once, works everywhere!

Usage in notebooks:
    from shared.config import get_config, print_config
    cfg = get_config()
    CATALOG = cfg.catalog
    SCHEMA = cfg.schema

Usage in Streamlit app:
    from shared.config import get_config
    cfg = get_config()
    connection = sql.connect(
        server_hostname=cfg.workspace_host,
        http_path=f"/sql/1.0/warehouses/{cfg.warehouse_id}",
        ...
    )
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class PAAgentConfig:
    """Configuration container with all settings"""
    
    def __init__(self, env_config: Dict[str, Any], common_config: Dict[str, Any]):
        # Environment-specific settings
        self.workspace_host = env_config['workspace_host']
        self.profile = env_config['profile']
        self.catalog = env_config['catalog']
        self.schema = env_config['schema']
        self.warehouse_id = env_config['warehouse_id']
        self.vector_endpoint = env_config['vector_endpoint']
        self.llm_endpoint = env_config['llm_endpoint']
        self.app_name = env_config['app_name']
        self.volume_clinical = env_config['volume_clinical']
        self.volume_guidelines = env_config['volume_guidelines']
        
        # Common settings
        self.spark_version = common_config['spark_version']
        self.node_type = common_config['node_type']
        self.num_workers = common_config['num_workers']
        self.num_patients = common_config['num_patients']
        self.num_pa_requests = common_config['num_pa_requests']
        self.embedding_model = common_config['embedding_model']
        self.sync_type = common_config['sync_type']
        self.auto_approve_threshold = common_config['auto_approve_threshold']
        self.manual_review_threshold = common_config['manual_review_threshold']
        
        # Genie AI settings
        self.genie_display_name = common_config.get('genie_display_name', 'Prior Authorization Analytics')
        self.genie_description = common_config.get('genie_description', 'Natural language queries for PA requests')
        
        # Chunking settings
        self.min_chunk_size = common_config['min_chunk_size']
        self.max_chunk_size = common_config['max_chunk_size']
        
        # Computed values (automatically derived)
        self.auth_requests_table = f"{self.catalog}.{self.schema}.authorization_requests"
        self.clinical_records_table = f"{self.catalog}.{self.schema}.patient_clinical_records"
        self.guidelines_table = f"{self.catalog}.{self.schema}.clinical_guidelines"
        self.clinical_vector_index = f"{self.catalog}.{self.schema}.patient_clinical_records_index"
        self.guidelines_vector_index = f"{self.catalog}.{self.schema}.clinical_guidelines_index"
        self.clinical_volume_path = f"/Volumes/{self.catalog}/{self.schema}/{self.volume_clinical}"
        self.guidelines_volume_path = f"/Volumes/{self.catalog}/{self.schema}/{self.volume_guidelines}"
        self.config_table = f"{self.catalog}.{self.schema}.pa_config"  # For storing Genie Space ID, etc.
    
    def __repr__(self):
        return f"PAAgentConfig(env={self.catalog}, warehouse={self.warehouse_id})"


def get_config(environment: Optional[str] = None) -> PAAgentConfig:
    """
    Load configuration from config.yaml
    
    Environment resolution priority:
    1. Parameter passed to function
    2. DAB widget 'environment' (if running in notebook via DAB)
    3. Environment variable PA_ENV
    4. Default environment from config.yaml
    
    Args:
        environment: Environment name (dev/staging/prod). If None, auto-detects.
    
    Returns:
        PAAgentConfig object with all settings
    
    Example:
        cfg = get_config()  # Auto-detects environment
        cfg = get_config('staging')  # Force staging environment
    """
    
    # Find config.yaml (search up directory tree)
    current_dir = Path(__file__).parent
    config_path = None
    
    for parent in [current_dir] + list(current_dir.parents):
        candidate = parent / "config.yaml"
        if candidate.exists():
            config_path = candidate
            break
    
    if not config_path:
        raise FileNotFoundError(
            "config.yaml not found! Expected in project root.\n"
            "Make sure config.yaml exists and you're running from correct directory."
        )
    
    # Load config.yaml
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Determine environment
    if environment is None:
        # Try DAB widget (only works in Databricks notebooks)
        try:
            environment = dbutils.widgets.get("environment")  # type: ignore
            print(f"✅ Using environment from DAB widget: {environment}")
        except:
            pass
    
    if environment is None:
        # Try environment variable
        environment = os.getenv("PA_ENV")
        if environment:
            print(f"✅ Using environment from PA_ENV: {environment}")
    
    if environment is None:
        # Use default from config
        environment = config.get('default_environment', 'dev')
        print(f"✅ Using default environment: {environment}")
    
    # Validate environment exists
    if environment not in config['environments']:
        available = ', '.join(config['environments'].keys())
        raise ValueError(
            f"Environment '{environment}' not found in config.yaml!\n"
            f"Available environments: {available}"
        )
    
    # Create config object
    env_config = config['environments'][environment]
    common_config = config['common']
    
    return PAAgentConfig(env_config, common_config)


def print_config(cfg: PAAgentConfig):
    """Pretty-print configuration for debugging"""
    print("=" * 80)
    print("PRIOR AUTHORIZATION AGENT CONFIGURATION")
    print("=" * 80)
    print(f"Catalog:                 {cfg.catalog}")
    print(f"Schema:                  {cfg.schema}")
    print(f"Warehouse ID:            {cfg.warehouse_id}")
    print(f"Vector Endpoint:         {cfg.vector_endpoint}")
    print(f"LLM Endpoint:            {cfg.llm_endpoint}")
    print(f"App Name:                {cfg.app_name}")
    print(f"Auth Requests Table:     {cfg.auth_requests_table}")
    print(f"Clinical Records Table:  {cfg.clinical_records_table}")
    print(f"Guidelines Table:        {cfg.guidelines_table}")
    print(f"Clinical Vector Index:   {cfg.clinical_vector_index}")
    print(f"Guidelines Vector Index: {cfg.guidelines_vector_index}")
    print(f"Clinical Volume Path:    {cfg.clinical_volume_path}")
    print(f"Guidelines Volume Path:  {cfg.guidelines_volume_path}")
    print(f"Min Chunk Size:          {cfg.min_chunk_size}")
    print(f"Max Chunk Size:          {cfg.max_chunk_size}")
    print(f"Genie Display Name:      {cfg.genie_display_name}")
    print(f"Genie Description:       {cfg.genie_description}")
    print("=" * 80)


    print(f"Min Chunk Size:          {cfg.min_chunk_size}")
    print(f"Max Chunk Size:          {cfg.max_chunk_size}")
    print(f"Genie Display Name:      {cfg.genie_display_name}")
    print(f"Genie Description:       {cfg.genie_description}")
    print("=" * 80)


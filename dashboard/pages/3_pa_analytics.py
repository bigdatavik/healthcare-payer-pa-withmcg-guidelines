"""
PA Analytics Dashboard
Displays analytics and trends from prior authorization decisions
Includes natural language queries via Databricks Genie
"""

import streamlit as st
import os
from databricks import sql
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time

# Page configuration
st.set_page_config(
    page_title="PA Analytics | Prior Authorization",
    page_icon="📈",
    layout="wide"
)

st.title("📈 PA Analytics")
st.markdown("*Analytics and trends from prior authorization decisions*")

# Configuration
CATALOG = os.getenv("CATALOG_NAME", "healthcare_payer_pa_withmcg_guidelines_dev")
SCHEMA = os.getenv("SCHEMA_NAME", "main")
WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID")

# Initialize clients
@st.cache_resource
def get_workspace_client():
    """Initialize Databricks WorkspaceClient"""
    try:
        return WorkspaceClient()
    except Exception as e:
        st.error(f"Failed to initialize Databricks client: {e}")
        return None

def get_sql_connection():
    """Create Databricks SQL connection - called lazily when needed"""
    try:
        cfg = Config()
        return sql.connect(
            server_hostname=cfg.host,
            http_path=f"/sql/1.0/warehouses/{WAREHOUSE_ID}",
            credentials_provider=lambda: cfg.authenticate,
        )
    except Exception as e:
        st.error(f"SQL Connection error: {e}")
        return None

w = get_workspace_client()

# Get Genie Space ID - DATABASE-FIRST with config.yaml override
def get_genie_space_id():
    """
    Get Genie Space ID from multiple sources (in priority order):
    1. Environment variable (manual override from config.yaml)
    2. pa_config table (automatic discovery - PRIMARY SOURCE)
    
    This allows automatic discovery without manual config updates.
    """
    # Try environment variable first (manual override)
    env_genie_id = os.getenv("GENIE_SPACE_ID")
    if env_genie_id:
        return env_genie_id
    
    # Fall back to querying pa_config table (PRIMARY SOURCE)
    try:
        sql_conn = get_sql_connection()
        if sql_conn:
            with sql_conn.cursor() as cursor:
                cursor.execute(f"""
                    SELECT config_value 
                    FROM {CATALOG}.{SCHEMA}.pa_config 
                    WHERE config_key = 'genie_space_id'
                """)
                result = cursor.fetchone()
                if result and result[0]:
                    return result[0]
    except Exception as e:
        # Silently fail - will show warning in UI
        pass
    
    return None

GENIE_SPACE_ID = get_genie_space_id()

# SQL Query Functions
@st.cache_data(ttl=300)
def get_pa_statistics():
    """Get overall PA statistics"""
    sql_conn = get_sql_connection()
    if not sql_conn:
        return None
    
    try:
        with sql_conn.cursor() as cursor:
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_requests,
                    SUM(CASE WHEN decision = 'APPROVED' THEN 1 ELSE 0 END) as approved,
                    SUM(CASE WHEN decision = 'DENIED' THEN 1 ELSE 0 END) as denied,
                    SUM(CASE WHEN decision = 'MANUAL_REVIEW' THEN 1 ELSE 0 END) as manual_review,
                    ROUND(AVG(confidence_score) * 100, 2) as avg_confidence,
                    ROUND(100.0 * SUM(CASE WHEN decision = 'APPROVED' THEN 1 ELSE 0 END) / COUNT(*), 2) as approval_rate
                FROM {CATALOG}.{SCHEMA}.authorization_requests
            """)
            result = cursor.fetchone()
            if result:
                return {
                    "total_requests": result[0],
                    "approved": result[1],
                    "denied": result[2],
                    "manual_review": result[3],
                    "avg_confidence": result[4],
                    "approval_rate": result[5]
                }
    except Exception as e:
        st.error(f"Error fetching statistics: {e}")
    return None

@st.cache_data(ttl=300)
def get_decisions_breakdown():
    """Get PA decisions breakdown"""
    sql_conn = get_sql_connection()
    if not sql_conn:
        return None
    
    try:
        with sql_conn.cursor() as cursor:
            cursor.execute(f"""
                SELECT 
                    decision,
                    COUNT(*) as count
                FROM {CATALOG}.{SCHEMA}.authorization_requests
                GROUP BY decision
                ORDER BY count DESC
            """)
            results = cursor.fetchall()
            if results:
                return pd.DataFrame(results, columns=["Decision", "Count"])
    except Exception as e:
        st.error(f"Error fetching decisions breakdown: {e}")
    return None

@st.cache_data(ttl=300)
def get_decisions_by_procedure():
    """Get decisions by procedure type"""
    sql_conn = get_sql_connection()
    if not sql_conn:
        return None
    
    try:
        with sql_conn.cursor() as cursor:
            cursor.execute(f"""
                SELECT 
                    procedure_description,
                    COUNT(*) as total,
                    SUM(CASE WHEN decision = 'APPROVED' THEN 1 ELSE 0 END) as approved,
                    SUM(CASE WHEN decision = 'DENIED' THEN 1 ELSE 0 END) as denied,
                    ROUND(100.0 * SUM(CASE WHEN decision = 'APPROVED' THEN 1 ELSE 0 END) / COUNT(*), 2) as approval_rate
                FROM {CATALOG}.{SCHEMA}.authorization_requests
                GROUP BY procedure_description
                HAVING COUNT(*) >= 2
                ORDER BY total DESC
                LIMIT 10
            """)
            results = cursor.fetchall()
            if results:
                return pd.DataFrame(results, columns=["Procedure", "Total", "Approved", "Denied", "Approval Rate %"])
    except Exception as e:
        st.error(f"Error fetching procedure breakdown: {e}")
    return None

@st.cache_data(ttl=300)
def get_confidence_distribution():
    """Get confidence score distribution"""
    sql_conn = get_sql_connection()
    if not sql_conn:
        return None
    
    try:
        with sql_conn.cursor() as cursor:
            cursor.execute(f"""
                SELECT 
                    ROUND(confidence_score * 100, 0) as confidence_pct,
                    COUNT(*) as count
                FROM {CATALOG}.{SCHEMA}.authorization_requests
                GROUP BY ROUND(confidence_score * 100, 0)
                ORDER BY confidence_pct
            """)
            results = cursor.fetchall()
            if results:
                return pd.DataFrame(results, columns=["Confidence %", "Count"])
    except Exception as e:
        st.error(f"Error fetching confidence distribution: {e}")
    return None

@st.cache_data(ttl=300)
def get_urgency_breakdown():
    """Get PA breakdown by urgency level"""
    sql_conn = get_sql_connection()
    if not sql_conn:
        return None
    
    try:
        with sql_conn.cursor() as cursor:
            cursor.execute(f"""
                SELECT 
                    urgency_level,
                    COUNT(*) as total,
                    SUM(CASE WHEN decision = 'APPROVED' THEN 1 ELSE 0 END) as approved,
                    ROUND(100.0 * SUM(CASE WHEN decision = 'APPROVED' THEN 1 ELSE 0 END) / COUNT(*), 2) as approval_rate
                FROM {CATALOG}.{SCHEMA}.authorization_requests
                GROUP BY urgency_level
                ORDER BY 
                    CASE urgency_level
                        WHEN 'STAT' THEN 1
                        WHEN 'URGENT' THEN 2
                        WHEN 'ROUTINE' THEN 3
                        ELSE 4
                    END
            """)
            results = cursor.fetchall()
            if results:
                return pd.DataFrame(results, columns=["Urgency Level", "Total", "Approved", "Approval Rate %"])
    except Exception as e:
        st.error(f"Error fetching urgency breakdown: {e}")
    return None

# Main Dashboard
st.markdown("---")

# Key Metrics
stats = get_pa_statistics()
if stats:
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total PA Requests",
            f"{stats['total_requests']:,}",
            help="Total number of PA requests processed"
        )
    
    with col2:
        st.metric(
            "Approval Rate",
            f"{stats['approval_rate']:.1f}%",
            help="Percentage of requests approved"
        )
    
    with col3:
        st.metric(
            "Manual Review",
            f"{stats['manual_review']:,}",
            help="Requests requiring manual review"
        )
    
    with col4:
        st.metric(
            "Avg AI Confidence",
            f"{stats['avg_confidence']:.1f}%",
            help="Average AI confidence across all decisions"
        )

st.markdown("---")

# Charts Section
st.subheader("📊 Decision Analytics")

col1, col2 = st.columns(2)

with col1:
    # Decision Breakdown
    st.markdown("### Decision Breakdown")
    decisions = get_decisions_breakdown()
    if decisions is not None and not decisions.empty:
        fig = px.pie(
            decisions,
            values="Count",
            names="Decision",
            title="PA Decisions Distribution",
            hole=0.4,
            color="Decision",
            color_discrete_map={
                "APPROVED": "#28a745",
                "DENIED": "#dc3545",
                "MANUAL_REVIEW": "#ffc107"
            }
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No decision data available yet.")

with col2:
    # Urgency Level Breakdown
    st.markdown("### Approval by Urgency Level")
    urgency = get_urgency_breakdown()
    if urgency is not None and not urgency.empty:
        fig = px.bar(
            urgency,
            x="Urgency Level",
            y="Approval Rate %",
            title="Approval Rate by Urgency",
            labels={"Approval Rate %": "Approval Rate (%)"},
            color="Approval Rate %",
            color_continuous_scale="RdYlGn"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No urgency data available yet.")

# Procedure Analysis
st.markdown("### 🏥 Top Procedures (by Volume)")
procedures = get_decisions_by_procedure()
if procedures is not None and not procedures.empty:
    fig = px.bar(
        procedures,
        x="Total",
        y="Procedure",
        orientation='h',
        title="PA Requests by Procedure Type",
        labels={"Total": "Number of Requests", "Procedure": "Procedure Type"},
        color="Approval Rate %",
        color_continuous_scale="RdYlGn",
        hover_data=["Approved", "Denied"]
    )
    fig.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No procedure data available yet.")

# Confidence Distribution
st.markdown("### 🎯 AI Confidence Distribution")
confidence = get_confidence_distribution()
if confidence is not None and not confidence.empty:
    fig = px.bar(
        confidence,
        x="Confidence %",
        y="Count",
        title="Distribution of AI Confidence Scores",
        labels={"Confidence %": "Confidence Score (%)", "Count": "Number of PAs"}
    )
    fig.update_traces(marker_color='#0066cc')
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No confidence data available yet.")

st.markdown("---")

# Genie Natural Language Interface
st.subheader("💬 Ask Genie - Natural Language Queries")

if GENIE_SPACE_ID:
    st.markdown("""
    Ask questions about your PA data in plain English. Genie will automatically generate SQL and return results.
    """)
    
    # Example questions (synced with Genie Space sample_questions)
    example_questions = [
        "Show me all prior authorization requests",
        "What is the approval rate by procedure type?",
        "Which requests are pending manual review?",
        "Show MCG questions that were answered NO for denied requests",
        "What clinical evidence types are most commonly cited in approvals?",
        "Which providers have the highest manual review rate?",
        "Show approval trends by urgency level over time",
        "What percentage of diabetes patients get approved for procedures?"
    ]
    
    # User input
    user_question = st.text_input(
        "Your question:",
        placeholder="e.g., Show me all approved prior authorizations",
        help="Ask any question about your PA data"
    )
    
    # Quick question buttons in a grid
    st.markdown("**Quick Questions:**")
    col1, col2, col3 = st.columns(3)
    
    for i, question in enumerate(example_questions):
        col_idx = i % 3
        with [col1, col2, col3][col_idx]:
            if st.button(question, key=f"q_{i}", use_container_width=True):
                user_question = question
    
    if user_question:
        with st.spinner("🤔 Genie is thinking..."):
            try:
                # Start conversation using official Genie API pattern
                start_response = w.api_client.do(
                    'POST',
                    f'/api/2.0/genie/spaces/{GENIE_SPACE_ID}/start-conversation',
                    body={'content': user_question}
                )
                
                conversation_id = start_response.get('conversation_id')
                message_id = start_response.get('message_id')
                
                if not conversation_id or not message_id:
                    st.error("Failed to start Genie conversation")
                else:
                    # Poll for result
                    max_attempts = 30  # 30 * 2 = 60 seconds max
                    attempt = 0
                    
                    while attempt < max_attempts:
                        time.sleep(2)  # Wait 2 seconds between polls
                        attempt += 1
                        
                        # Get message status
                        message_response = w.api_client.do(
                            'GET',
                            f'/api/2.0/genie/spaces/{GENIE_SPACE_ID}/conversations/{conversation_id}/messages/{message_id}'
                        )
                        
                        status = message_response.get('status')
                        
                        if status == 'COMPLETED':
                            # Extract results
                            attachments = message_response.get('attachments', [])
                            
                            if attachments:
                                attachment = attachments[0]
                                text_response = attachment.get('text', {}).get('content', '')
                                query = attachment.get('query', {}).get('query', '')
                                
                                # Display text response
                                if text_response:
                                    st.success("**Genie's Response:**")
                                    st.markdown(text_response)
                                
                                # Display generated SQL
                                if query:
                                    with st.expander("🔍 View Generated SQL"):
                                        st.code(query, language="sql")
                                    
                                    # Get query results
                                    try:
                                        attachment_id = attachment.get('query', {}).get('attachment_id') or attachment.get('attachment_id')
                                        if attachment_id:
                                            result_response = w.api_client.do(
                                                'GET',
                                                f'/api/2.0/genie/spaces/{GENIE_SPACE_ID}/conversations/{conversation_id}/messages/{message_id}/query-result/{attachment_id}'
                                            )
                                            
                                            # Extract data from statement_response
                                            stmt_response = result_response.get('statement_response', {})
                                            
                                            if stmt_response:
                                                # Get schema from manifest
                                                manifest = stmt_response.get('manifest', {})
                                                schema = manifest.get('schema', {})
                                                columns = schema.get('columns', [])
                                                column_names = [col.get('name') for col in columns]
                                                
                                                # Get data rows from result
                                                result_obj = stmt_response.get('result', {})
                                                data_array = result_obj.get('data_array', [])
                                                
                                                if data_array and column_names:
                                                    # Create DataFrame
                                                    df = pd.DataFrame(data_array, columns=column_names)
                                                    
                                                    st.success(f"✅ Found {len(df)} results")
                                                    st.dataframe(df, use_container_width=True)
                                                    
                                                    # Auto-generate chart if applicable
                                                    if len(df.columns) == 2 and len(df) > 1 and len(df) < 50:
                                                        st.markdown("**📊 Visualization:**")
                                                        fig = px.bar(df, x=df.columns[0], y=df.columns[1])
                                                        st.plotly_chart(fig, use_container_width=True)
                                                else:
                                                    st.info("Query executed successfully but returned no results.")
                                            else:
                                                st.warning("No statement_response in query result")
                                    except Exception as e:
                                        st.warning(f"Could not fetch query results: {e}")
                            else:
                                st.info("Query completed but no results available.")
                            break
                            
                        elif status == 'FAILED':
                            error = message_response.get('error', {})
                            st.error(f"Query failed: {error}")
                            break
                        elif status == 'CANCELLED':
                            st.warning("Query was cancelled")
                            break
                    
                    if attempt >= max_attempts:
                        st.warning("Query timed out. Please try a simpler question.")
                    
            except Exception as e:
                st.error(f"Error executing Genie query: {e}")
                st.info("💡 Make sure you've granted **Can Run** permissions to the app's service principal on the Genie Space.")
else:
    st.warning("⚠️ Genie Space not configured. The Genie natural language interface is currently unavailable.")
    st.markdown("""
    **To enable Genie:**
    1. Genie Space is automatically created during setup
    2. Grant **Can Run** permission to your app's service principal on the Genie Space
    3. See README for detailed instructions
    """)

st.markdown("---")
st.caption("💡 **Tip:** Process more PA requests to see richer insights and trends!")

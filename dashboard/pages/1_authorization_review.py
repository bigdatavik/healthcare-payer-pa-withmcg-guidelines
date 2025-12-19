"""
Page 1: Authorization Review
Real-time PA processing with AI agent
"""

import streamlit as st
import sys
from pathlib import Path
import json
import pandas as pd
from databricks import sql
from databricks.sdk.core import Config
import os

# Configuration
CATALOG = os.getenv("CATALOG_NAME", "healthcare_payer_pa_withmcg_guidelines_dev")
SCHEMA = os.getenv("SCHEMA_NAME", "main")
WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID", "148ccb90800933a1")

st.set_page_config(page_title="Authorization Review", page_icon="🔍", layout="wide")

st.title("🔍 Prior Authorization Review")
st.markdown("Process individual PA requests with real-time AI analysis")
st.markdown("---")

# Database connection
@st.cache_resource
def get_databricks_connection():
    """Create Databricks SQL connection"""
    try:
        cfg = Config()
        return sql.connect(
            server_hostname=cfg.host,
            http_path=f"/sql/1.0/warehouses/{WAREHOUSE_ID}",
            credentials_provider=lambda: cfg.authenticate
        )
    except Exception as e:
        st.error(f"Connection error: {e}")
        return None

def fetch_pa_requests():
    """Fetch pending PA requests"""
    conn = get_databricks_connection()
    if conn is None:
        return pd.DataFrame()
    
    query = f"""
    SELECT 
        request_id,
        patient_id,
        procedure_code,
        procedure_description,
        diagnosis_code,
        urgency_level,
        insurance_plan,
        request_date
    FROM {CATALOG}.{SCHEMA}.authorization_requests
    WHERE decision IS NULL
    ORDER BY request_date DESC
    LIMIT 50
    """
    
    cursor = conn.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    cursor.close()
    
    return pd.DataFrame(results, columns=columns)

def fetch_patient_records(patient_id):
    """Fetch patient clinical records"""
    conn = get_databricks_connection()
    if conn is None:
        return pd.DataFrame()
    
    query = f"""
    SELECT 
        record_id,
        record_date,
        record_type,
        SUBSTRING(content, 1, 200) as content_preview
    FROM {CATALOG}.{SCHEMA}.patient_clinical_records
    WHERE patient_id = '{patient_id}'
    ORDER BY record_date DESC
    LIMIT 20
    """
    
    cursor = conn.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    cursor.close()
    
    return pd.DataFrame(results, columns=columns)

def process_authorization(request_id, patient_id, procedure_code, diagnosis_code, clinical_notes):
    """Process PA request using UC function"""
    conn = get_databricks_connection()
    if conn is None:
        return None
    
    # Call the authorize_request UC function
    query = f"""
    SELECT {CATALOG}.{SCHEMA}.authorize_request(
        '{procedure_code}',
        '{diagnosis_code}',
        '{patient_id}',
        '{clinical_notes}'
    ) AS result
    """
    
    cursor = conn.cursor()
    cursor.execute(query)
    result = cursor.fetchone()[0]
    cursor.close()
    
    # Parse JSON result
    return json.loads(result)

# Main UI
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📋 Pending PA Requests")
    
    # Fetch requests
    with st.spinner("Loading PA requests..."):
        pa_requests_df = fetch_pa_requests()
    
    if pa_requests_df.empty:
        st.info("No pending PA requests")
    else:
        # Display as table with selection
        selected_idx = st.selectbox(
            "Select PA Request to Review:",
            range(len(pa_requests_df)),
            format_func=lambda i: f"{pa_requests_df.iloc[i]['request_id']} - {pa_requests_df.iloc[i]['procedure_description']}"
        )
        
        if selected_idx is not None:
            selected_request = pa_requests_df.iloc[selected_idx]
            
            st.markdown("### Request Details")
            
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("Request ID", selected_request['request_id'])
                st.metric("Patient ID", selected_request['patient_id'])
            with col_b:
                st.metric("Procedure", selected_request['procedure_code'])
                st.text(selected_request['procedure_description'][:50])
            with col_c:
                st.metric("Urgency", selected_request['urgency_level'])
                st.metric("Plan", selected_request['insurance_plan'])

with col2:
    st.subheader("⚙️ Processing Options")
    
    auto_process = st.checkbox("Auto-process if confidence > 90%", value=True)
    show_details = st.checkbox("Show detailed MCG answers", value=True)
    
    if st.button("🚀 Process Authorization", type="primary", use_container_width=True):
        if not pa_requests_df.empty:
            selected_request = pa_requests_df.iloc[selected_idx]
            
            with st.spinner("🤖 AI Agent processing..."):
                result = process_authorization(
                    selected_request['request_id'],
                    selected_request['patient_id'],
                    selected_request['procedure_code'],
                    selected_request['diagnosis_code'],
                    f"PA request for {selected_request['procedure_description']}"
                )
                
                if result:
                    st.session_state['last_result'] = result
                    st.success("✅ Processing complete!")
                else:
                    st.error("❌ Processing failed")

st.markdown("---")

# Display results
if 'last_result' in st.session_state:
    result = st.session_state['last_result']
    
    st.subheader("🎯 Authorization Decision")
    
    # Decision with color coding
    decision = result.get('decision', 'UNKNOWN')
    confidence = result.get('confidence', 0.0)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if decision == "APPROVED":
            st.markdown(f'<div class="approved" style="font-size: 2rem;">✅ {decision}</div>', unsafe_allow_html=True)
        elif decision == "DENIED":
            st.markdown(f'<div class="denied" style="font-size: 2rem;">❌ {decision}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="manual-review" style="font-size: 2rem;">⚠️ {decision}</div>', unsafe_allow_html=True)
    
    with col2:
        st.metric("Confidence Score", f"{confidence:.0%}")
        st.progress(confidence)
    
    with col3:
        st.metric("MCG Code", result.get('mcg_code', 'N/A'))
        criteria_met = result.get('criteria_met', 0)
        total_criteria = result.get('total_criteria', 0)
        st.metric("Criteria Met", f"{criteria_met}/{total_criteria}")
    
    # Explanation
    st.markdown("### 📝 Explanation")
    st.info(result.get('explanation', 'No explanation available'))
    
    # MCG Answers (if show_details)
    if show_details and result.get('answers'):
        st.markdown("### 📋 MCG Questionnaire Answers")
        
        answers_df = pd.DataFrame([
            {
                "Question": q[:80] + "..." if len(q) > 80 else q,
                "Answer": a['answer'],
                "Evidence": a['explanation'][:100] + "..." if len(a['explanation']) > 100 else a['explanation']
            }
            for q, a in result.get('answers', {}).items()
        ])
        
        st.dataframe(answers_df, use_container_width=True)
    
    # Action buttons
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("✅ Approve & Close", use_container_width=True):
            st.success("Request approved and closed")
    
    with col2:
        if st.button("👥 Send to Manual Review", use_container_width=True):
            st.info("Request routed to clinical reviewer")
    
    with col3:
        if st.button("📄 Export Report", use_container_width=True):
            st.download_button(
                "Download JSON",
                data=json.dumps(result, indent=2),
                file_name=f"pa_decision_{selected_request['request_id']}.json",
                mime="application/json"
            )

# Patient clinical history sidebar
st.sidebar.title("📊 Patient Clinical History")

if not pa_requests_df.empty and selected_idx is not None:
    patient_id = pa_requests_df.iloc[selected_idx]['patient_id']
    
    with st.sidebar:
        with st.spinner("Loading patient records..."):
            records_df = fetch_patient_records(patient_id)
        
        if not records_df.empty:
            st.markdown(f"**{len(records_df)} records found**")
            
            for idx, record in records_df.iterrows():
                with st.expander(f"{record['record_type']} - {record['record_date']}"):
                    st.text(record['content_preview'])
        else:
            st.info("No clinical records found")


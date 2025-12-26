"""
Prior Authorization Review Page - AI-Powered PA Processing with LangGraph Agent

This page allows reviewers to process PA requests using an intelligent LangGraph agent
that orchestrates multiple AI tools to evaluate clinical evidence against MCG guidelines.

Architecture:
- Config from environment (no hardcoding)
- WorkspaceClient for UC function calls and vector search
- LangGraph ReAct agent with specialized tools
- Complete PA queue workflow with traceability
"""

import streamlit as st
import os
import json
import time
import pandas as pd
from datetime import datetime
from databricks.sdk import WorkspaceClient

st.set_page_config(page_title="PA Review", page_icon="🏥", layout="wide")
st.title("🏥 Prior Authorization Review")

st.markdown("""
**Intelligent PA Processing:** Uses LangGraph AI Agent to evaluate clinical evidence against MCG guidelines.
The agent autonomously orchestrates multiple tools to gather evidence, answer MCG questions, and make authorization decisions.
""")

# ============================================
# SECTION 1: CONFIGURATION FROM ENVIRONMENT
# ============================================

# Core configuration (set via app.yaml from config.yaml)
CATALOG = os.getenv("CATALOG_NAME", "healthcare_payer_pa_withmcg_guidelines_dev")
SCHEMA = os.getenv("SCHEMA_NAME", "main")
WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID", "148ccb90800933a1")
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")

# Vector Search indexes (fully qualified names)
CLINICAL_INDEX = f"{CATALOG}.{SCHEMA}.patient_clinical_records_index"
GUIDELINES_INDEX = f"{CATALOG}.{SCHEMA}.clinical_guidelines_index"

# LLM endpoint for agent
LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "databricks-claude-sonnet-4-5")

# Tables
REQUESTS_TABLE = f"{CATALOG}.{SCHEMA}.authorization_requests"
CLINICAL_TABLE = f"{CATALOG}.{SCHEMA}.patient_clinical_records"
AUDIT_TRAIL_TABLE = f"{CATALOG}.{SCHEMA}.pa_audit_trail"

# Decision thresholds (from app.yaml environment variables)
AUTO_APPROVE_THRESHOLD = float(os.getenv("AUTO_APPROVE_THRESHOLD", "0.75"))
MANUAL_REVIEW_THRESHOLD = float(os.getenv("MANUAL_REVIEW_THRESHOLD", "0.50"))

# ============================================
# SECTION 2: DATABRICKS CLIENT
# ============================================

@st.cache_resource
def get_workspace_client():
    """Initialize Databricks WorkspaceClient (automatically authenticated in Databricks Apps)"""
    try:
        return WorkspaceClient()
    except Exception as e:
        st.error(f"❌ Failed to initialize Databricks client: {e}")
        return None

w = get_workspace_client()

if not w:
    st.error("""
    **Setup Required:**
    1. Ensure app is deployed to Databricks Apps
    2. Run `databricks bundle deploy --target dev`
    3. Run `./deploy_app_source.sh dev` to deploy app source code
    4. Verify config in `config.yaml`
    """)
    st.stop()

# ============================================
# SECTION 3: HELPER FUNCTIONS
# ============================================

def call_uc_function(function_name, *args, timeout=50, show_debug=False):
    """
    Call a Unity Catalog function using Statement Execution API
    
    Args:
        function_name: Name of the UC function (without catalog.schema prefix)
        *args: Arguments to pass to the function
        timeout: Query timeout in seconds
        show_debug: Whether to show debug info in UI
    
    Returns:
        Function result (parsed JSON if applicable)
    """
    try:
        # Escape single quotes in string arguments for SQL
        escaped_args = []
        for arg in args:
            if isinstance(arg, str):
                # Escape single quotes by doubling them
                escaped_arg = arg.replace("'", "''")
                escaped_args.append(f"'{escaped_arg}'")
            elif isinstance(arg, bool):
                # Convert Python bool to SQL boolean
                escaped_args.append('true' if arg else 'false')
            elif arg is None:
                escaped_args.append('null')
            else:
                escaped_args.append(str(arg))
        
        args_str = ', '.join(escaped_args)
        query = f"SELECT {CATALOG}.{SCHEMA}.{function_name}({args_str}) as result"
        
        if show_debug:
            st.info(f"🔍 Executing: {function_name}(...)")
        
        # Execute via Statement Execution API
        result = w.statement_execution.execute_statement(
            warehouse_id=WAREHOUSE_ID,
            statement=query,
            wait_timeout=f"{timeout}s"
        )
        
        if result.status.state.value == "SUCCEEDED":
            if result.result and result.result.data_array:
                data = result.result.data_array[0][0]
                
                # Try to parse as JSON if it's a string
                if isinstance(data, str):
                    try:
                        parsed = json.loads(data)
                        return parsed
                    except:
                        return data
                elif isinstance(data, dict):
                    return data
                elif isinstance(data, (list, tuple)):
                    # Handle STRUCT return types (returned as arrays)
                    # For check_mcg_guidelines which returns STRUCT
                    if function_name == "check_mcg_guidelines" and len(data) >= 5:
                        # Questionnaire might be a string (JSON) or already parsed list
                        questionnaire = data[3]
                        if isinstance(questionnaire, str):
                            try:
                                questionnaire = json.loads(questionnaire)
                            except:
                                questionnaire = []
                        elif not isinstance(questionnaire, list):
                            questionnaire = []
                        
                        # Convert questionnaire back to JSON string for consistency
                        return {
                            'guideline_id': data[0],
                            'platform': data[1],
                            'title': data[2],
                            'questionnaire': json.dumps(questionnaire) if isinstance(questionnaire, list) else questionnaire,
                            'decision_criteria': data[4],
                            'content': data[5] if len(data) > 5 else None
                        }
                    return data
                else:
                    return data
            return None
        else:
            if show_debug:
                st.error(f"❌ Query failed: {result.status.state.value}")
                if result.status.error:
                    st.error(f"Error: {result.status.error.message}")
            return None
    
    except Exception as e:
        if show_debug:
            st.error(f"❌ Error calling UC function {function_name}: {e}")
        return None

def load_pending_requests():
    """
    Load all pending PA requests from authorization_requests table
    
    Returns:
        List of dicts with request details
    """
    try:
        query = f"""
        SELECT 
            request_id,
            patient_id,
            procedure_code,
            diagnosis_code,
            urgency_level as urgency,
            request_date
        FROM {REQUESTS_TABLE}
        WHERE decision IS NULL
        ORDER BY 
            CASE 
                WHEN urgency_level = 'STAT' THEN 1
                WHEN urgency_level = 'URGENT' THEN 2
                ELSE 3
            END,
            request_date ASC
        """
        
        result = w.statement_execution.execute_statement(
            warehouse_id=WAREHOUSE_ID,
            statement=query,
            wait_timeout="30s"
        )
        
        if result.status.state.value == "SUCCEEDED":
            if result.result and result.result.data_array:
                # Convert to list of dicts
                pending = []
                for row in result.result.data_array:
                    pending.append({
                        'request_id': row[0],
                        'patient_id': row[1],
                        'procedure_code': row[2],
                        'diagnosis_code': row[3],
                        'urgency': row[4],
                        'created_at': row[5]  # Using request_date as created_at
                    })
                return pending
        return []
    
    except Exception as e:
        st.error(f"❌ Error loading pending requests: {e}")
        return []

def load_patient_clinical_notes(patient_id):
    """
    Load all clinical notes for a patient from patient_clinical_records table
    
    Args:
        patient_id: Patient ID
    
    Returns:
        String with all clinical notes concatenated
    """
    try:
        query = f"""
        SELECT content
        FROM {CLINICAL_TABLE}
        WHERE patient_id = '{patient_id}'
        ORDER BY record_date DESC
        LIMIT 10
        """
        
        result = w.statement_execution.execute_statement(
            warehouse_id=WAREHOUSE_ID,
            statement=query,
            wait_timeout="30s"
        )
        
        if result.status.state.value == "SUCCEEDED":
            if result.result and result.result.data_array:
                notes = []
                for row in result.result.data_array:
                    notes.append(row[0])
                return "\n\n---\n\n".join(notes)
        return "No clinical notes found."
    
    except Exception as e:
        st.error(f"❌ Error loading clinical notes: {e}")
        return "Error loading clinical notes."

def update_pa_decision(request_id, decision, mcg_code, explanation, confidence_score):
    """
    Update authorization_requests table with final decision
    
    Args:
        request_id: PA request ID
        decision: APPROVED | DENIED | MANUAL_REVIEW
        mcg_code: MCG guideline code
        explanation: Human-readable explanation
        confidence_score: Overall confidence (0.0-1.0)
    """
    try:
        # Escape single quotes in explanation
        explanation_escaped = explanation.replace("'", "''")
        
        query = f"""
        UPDATE {REQUESTS_TABLE}
        SET 
            decision = '{decision}',
            mcg_code = '{mcg_code}',
            explanation = '{explanation_escaped}',
            confidence_score = {confidence_score},
            decision_date = current_timestamp(),
            reviewed_by = 'AI_AGENT'
        WHERE request_id = '{request_id}'
        """
        
        result = w.statement_execution.execute_statement(
            warehouse_id=WAREHOUSE_ID,
            statement=query,
            wait_timeout="30s"
        )
        
        return result.status.state.value == "SUCCEEDED"
    
    except Exception as e:
        st.error(f"❌ Error updating PA decision: {e}")
        return False

def save_audit_trail_entry(request_id, question_number, question_text, answer, 
                           evidence, evidence_source, confidence):
    """
    Insert a single Q&A entry into pa_audit_trail table
    
    Args:
        request_id: PA request ID (links to authorization_requests)
        question_number: Question number (1, 2, 3, ...)
        question_text: MCG question text
        answer: YES or NO
        evidence: Clinical evidence used
        evidence_source: Source type (CLINICAL_NOTE, XRAY, etc.)
        confidence: AI confidence for this answer (0.0-1.0)
    """
    try:
        # Escape single quotes
        question_escaped = question_text.replace("'", "''")
        evidence_escaped = evidence.replace("'", "''") if evidence else ''
        
        audit_id = f"{request_id}_Q{question_number}"
        
        query = f"""
        INSERT INTO {AUDIT_TRAIL_TABLE} VALUES (
            '{audit_id}',
            '{request_id}',
            {question_number},
            '{question_escaped}',
            '{answer}',
            '{evidence_escaped}',
            '{evidence_source}',
            {confidence},
            current_timestamp()
        )
        """
        
        result = w.statement_execution.execute_statement(
            warehouse_id=WAREHOUSE_ID,
            statement=query,
            wait_timeout="30s"
        )
        
        return result.status.state.value == "SUCCEEDED"
    
    except Exception as e:
        st.error(f"❌ Error saving audit trail entry: {e}")
        return False

# ============================================
# SECTION 4: LANGCHAIN TOOLS FOR AGENT
# ============================================

try:
    from langchain_core.tools import Tool, StructuredTool
    from pydantic import BaseModel, Field
    from langgraph.graph import StateGraph, END
    from langgraph.prebuilt import ToolNode
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
    from databricks_langchain import ChatDatabricks
    from typing import TypedDict, Annotated, List, Dict, Any
    import operator
    
    LANGCHAIN_AVAILABLE = True
    
    # Tool input schemas (Pydantic models)
    class CheckMCGInput(BaseModel):
        procedure_code: str = Field(description="CPT procedure code (e.g., '29881')")
        diagnosis_code: str = Field(description="ICD-10 diagnosis code (e.g., 'M23.205')")
    
    class SearchClinicalInput(BaseModel):
        patient_id: str = Field(description="Patient ID to search records for")
        query: str = Field(description="Search query (e.g., MCG question text)")
    
    class AnswerMCGInput(BaseModel):
        clinical_evidence: str = Field(description="Clinical evidence text from vector search")
        question: str = Field(description="MCG question to answer")
    
    # Tool wrapper functions
    def check_mcg_wrapper(procedure_code: str, diagnosis_code: str) -> str:
        """Retrieves MCG guideline and questionnaire for a procedure/diagnosis"""
        result = call_uc_function("check_mcg_guidelines", procedure_code, diagnosis_code, show_debug=False)
        return json.dumps(result, indent=2) if result else json.dumps({"error": "No guideline found"})
    
    def load_all_patient_records(patient_id: str) -> str:
        """
        Load ALL clinical records for a patient DIRECTLY from Delta table.
        This bypasses vector search to test if data quality is the issue.
        """
        try:
            if not w:
                return "WorkspaceClient not initialized"
            
            # Query Delta table directly via SQL
            query = f"""
            SELECT patient_id, record_type, content
            FROM {CLINICAL_TABLE}
            WHERE patient_id = '{patient_id}'
            ORDER BY record_date DESC
            """
            
            print(f"🔍 Loading ALL records for patient {patient_id} from DELTA TABLE")
            print(f"   Table: {CLINICAL_TABLE}")
            
            result = w.statement_execution.execute_statement(
                warehouse_id=WAREHOUSE_ID,
                statement=query,
                wait_timeout="30s"
            )
            
            if result.status.state.value == "SUCCEEDED":
                if result.result and result.result.data_array:
                    data_array = result.result.data_array
                    print(f"📊 Found {len(data_array)} records in Delta table")
                    
                    # Format records
                    records_text = []
                    for i, row in enumerate(data_array, 1):
                        patient_id_col = row[0]
                        record_type = row[1]
                        content = row[2]
                        records_text.append(f"Record {i} [{record_type}]:\n{content}")
                        
                        # DEBUG: Print first 200 chars of each record
                        print(f"   Record {i} [{record_type}]: {content[:200]}...")
                    
                    full_text = "\n\n---\n\n".join(records_text)
                    print(f"✅ Total content length: {len(full_text)} chars")
                    return full_text
                else:
                    print(f"⚠️ No records found for patient {patient_id} in Delta table")
                    return f"No records found for patient {patient_id} in Delta table"
            else:
                error_msg = f"Query failed: {result.status.state.value}"
                print(f"❌ {error_msg}")
                return error_msg
                
        except Exception as e:
            error_msg = f"Error loading patient records: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg
    
    def search_clinical_wrapper(patient_id: str, query: str) -> str:
        """
        DEPRECATED: Use cached patient records instead.
        This function is kept for backward compatibility but should not be called.
        """
        # This should no longer be used - we load all records once
        return json.dumps({"error": "Use cached patient records instead of per-question search"})
    
    def answer_mcg_wrapper(clinical_evidence: str, question: str) -> str:
        """Answers an MCG question using clinical evidence and LLM"""
        result = call_uc_function("answer_mcg_question", clinical_evidence, question, show_debug=False)
        return json.dumps(result, indent=2) if result else json.dumps({"error": "Answer generation failed"})
    
    # Create LangChain Tools (use StructuredTool for multi-arg functions)
    check_mcg_tool = StructuredTool.from_function(
        func=check_mcg_wrapper,
        name="check_mcg_guidelines",
        description="Retrieves the MCG guideline and questionnaire for a given procedure code and diagnosis code. Use this FIRST to get the list of questions that need to be answered. Returns JSON with guideline_id, platform, title, questionnaire (array of questions), decision_criteria.",
        args_schema=CheckMCGInput
    )
    
    search_clinical_tool = StructuredTool.from_function(
        func=search_clinical_wrapper,
        name="search_clinical_records",
        description="Searches the patient's clinical records using semantic vector search. Use this to find evidence for each MCG question. Pass the patient_id and the question text as the query. Returns JSON array with patient_id, record_type, content.",
        args_schema=SearchClinicalInput
    )
    
    answer_mcg_tool = StructuredTool.from_function(
        func=answer_mcg_wrapper,
        name="answer_mcg_question",
        description="Answers an MCG question (YES/NO) using clinical evidence and AI reasoning. REQUIRES clinical evidence from search_clinical_records first. Pass the evidence text and the question. Returns JSON with answer (YES/NO), reasoning, confidence.",
        args_schema=AnswerMCGInput
    )
    
    # ============================================
    # SECTION 5: LANGGRAPH CUSTOM WORKFLOW
    # ============================================
    
    # Define state for our PA workflow
    class PAWorkflowState(TypedDict):
        """State that flows through the LangGraph workflow"""
        patient_id: str
        procedure_code: str
        diagnosis_code: str
        patient_clinical_records: str  # ALL patient records loaded once
        mcg_guideline: Dict[str, Any]
        questions: List[Dict[str, str]]
        current_question_idx: int
        mcg_answers: Annotated[List[Dict], operator.add]  # Accumulate answers
        decision: str
        confidence: float
        messages: Annotated[List[Any], operator.add]  # For logging/debugging
    
    # Workflow nodes (each is a function that takes state and returns updates)
    def load_patient_data_node(state: PAWorkflowState) -> Dict:
        """Node 0: Load ALL patient clinical records once"""
        st.write(f"📂 Loading all clinical records for patient {state['patient_id']}...")
        
        patient_records = load_all_patient_records(state['patient_id'])
        
        # Count records
        if "No records found" in patient_records or "Error" in patient_records:
            record_count = 0
            st.warning(f"⚠️ {patient_records}")
        else:
            record_count = patient_records.count("Record ")
            st.success(f"✅ Loaded {record_count} clinical records")
            
            # DISPLAY RECORDS so user can see them
            with st.expander(f"📄 View {record_count} Clinical Records", expanded=False):
                # Split by separator and show each record
                records = patient_records.split("\n\n---\n\n")
                for i, record in enumerate(records[:5], 1):  # Show first 5
                    st.text_area(f"Record {i}", record, height=150, key=f"record_{i}")
                if len(records) > 5:
                    st.info(f"... and {len(records) - 5} more records")
        
        return {
            "patient_clinical_records": patient_records,
            "messages": [f"Loaded {record_count} clinical records for {state['patient_id']}"]
        }
    
    def get_guideline_node(state: PAWorkflowState) -> Dict:
        """Node 1: Get MCG guideline and questions"""
        try:
            result = call_uc_function("check_mcg_guidelines", state['procedure_code'], state['diagnosis_code'], show_debug=True)
            
            if not result:
                return {
                    "mcg_guideline": {},
                    "questions": [],
                    "messages": [f"❌ No guideline found for {state['procedure_code']} + {state['diagnosis_code']}"]
                }
            
            # Handle questionnaire - might be string or already parsed
            questionnaire_data = result.get('questionnaire', '[]')
            if isinstance(questionnaire_data, str):
                questions = json.loads(questionnaire_data)
            elif isinstance(questionnaire_data, list):
                questions = questionnaire_data
            else:
                questions = []
            
            return {
                "mcg_guideline": result,
                "questions": questions,
                "current_question_idx": 0,
                "messages": [f"✅ Found guideline {result.get('guideline_id')} with {len(questions)} questions"]
            }
        except Exception as e:
            return {
                "mcg_guideline": {},
                "questions": [],
                "messages": [f"❌ Error in get_guideline_node: {str(e)}"]
            }
    
    def answer_question_node(state: PAWorkflowState) -> Dict:
        """Node 2: Answer ONE question using cached patient records"""
        idx = state['current_question_idx']
        questions = state['questions']
        
        if idx >= len(questions):
            return {"messages": ["All questions answered"]}
        
        question = questions[idx].get('question', str(questions[idx]))
        
        # Use ALL patient records (already loaded in state)
        patient_records = state.get('patient_clinical_records', 'No clinical records available')
        
        # Truncate if too long (keep first 5000 chars for context)
        if len(patient_records) > 5000:
            evidence_text = patient_records[:5000] + "\n\n... (additional records truncated)"
        else:
            evidence_text = patient_records
        
        # Answer the question using the UC function
        answer_result = call_uc_function("answer_mcg_question", evidence_text, question, show_debug=False)
        answer_text = str(answer_result) if answer_result else "ERROR"
        answer_clean = "YES" if "YES" in answer_text.upper() else "NO" if "NO" in answer_text.upper() else "UNCLEAR"
        
        return {
            "mcg_answers": [{
                "question_num": idx + 1,
                "question": question,
                "answer": answer_clean,
                "evidence": evidence_text[:200] + "..." if len(evidence_text) > 200 else evidence_text,
                "reasoning": answer_text,
                "confidence": 0.9 if answer_clean in ["YES", "NO"] else 0.5
            }],
            "current_question_idx": idx + 1,
            "messages": [f"Q{idx+1}: {answer_clean}"]
        }
    
    def should_continue(state: PAWorkflowState) -> str:
        """Router: Check if we should answer another question or calculate decision"""
        if state['current_question_idx'] >= len(state['questions']):
            return "calculate_decision"
        return "answer_question"
    
    def calculate_decision_node(state: PAWorkflowState) -> Dict:
        """Node 3: Calculate final decision based on answers"""
        answers = state['mcg_answers']
        yes_count = sum(1 for a in answers if a['answer'] == "YES")
        total = len(state['questions'])
        confidence = yes_count / total if total > 0 else 0.0
        
        # DEBUG: Print thresholds
        approve_threshold = float(AUTO_APPROVE_THRESHOLD)
        manual_threshold = float(MANUAL_REVIEW_THRESHOLD)
        
        if confidence >= approve_threshold:
            decision = "APPROVED"
        elif confidence >= manual_threshold:
            decision = "MANUAL_REVIEW"
        else:
            decision = "DENIED"
        
        return {
            "decision": decision,
            "confidence": confidence,
            "messages": [
                f"Decision: {decision} ({confidence*100:.0f}%)",
                f"[DEBUG] Thresholds: APPROVE={approve_threshold}, MANUAL={manual_threshold}"
            ]
        }
    
    # Temporarily disabled cache to force fresh workflow creation
    # @st.cache_resource
    def create_pa_workflow(_version="v5"):
        """Create the LangGraph StateGraph workflow"""
        try:
            # Build the graph
            workflow = StateGraph(PAWorkflowState)
            
            # Add nodes
            workflow.add_node("load_patient_data", load_patient_data_node)
            workflow.add_node("get_guideline", get_guideline_node)
            workflow.add_node("answer_question", answer_question_node)
            workflow.add_node("calculate_decision", calculate_decision_node)
            
            # Define flow
            workflow.set_entry_point("load_patient_data")
            workflow.add_edge("load_patient_data", "get_guideline")
            workflow.add_edge("get_guideline", "answer_question")
            workflow.add_conditional_edges(
                "answer_question",
                should_continue,
                {
                    "answer_question": "answer_question",  # Loop back
                    "calculate_decision": "calculate_decision"
                }
            )
            workflow.add_edge("calculate_decision", END)
            
            # Compile
            app = workflow.compile()
            return app
        except Exception as e:
            st.error(f"❌ Error creating workflow: {e}")
            import traceback
            st.error(traceback.format_exc())
            return None

except ImportError as e:
    LANGCHAIN_AVAILABLE = False
    st.error(f"❌ LangChain/LangGraph not available: {e}")
    st.stop()

# ============================================
# SECTION 6: SAMPLE PA REQUESTS FOR TESTING
# ============================================

SAMPLE_REQUESTS = {
    "Knee Arthroscopy (SHOULD APPROVE - 100%)": {
        "patient_id": "PT00001",
        "procedure_code": "29881",
        "diagnosis_code": "M23.205",
        "urgency": "ROUTINE",
        "notes": "58-year-old male with right knee medial meniscus tear. MRI confirms tear. Failed 8 weeks of physical therapy and NSAIDs. Pain limits daily activities. Cleared by cardiologist for surgery."
    },
    "Total Knee Replacement (MANUAL REVIEW - 50%)": {
        "patient_id": "PT00016",
        "procedure_code": "27447",
        "diagnosis_code": "M17.11",
        "urgency": "URGENT",
        "notes": "68-year-old female with severe osteoarthritis right knee. X-ray shows complete loss of joint space. Failed 12 weeks conservative management including PT, injections, NSAIDs. Unable to climb stairs or walk >100 feet. BMI 28."
    },
    "Lumbar Fusion (SHOULD MANUAL REVIEW - 70%)": {
        "patient_id": "PT00025",
        "procedure_code": "22630",
        "diagnosis_code": "M51.26",
        "urgency": "URGENT",
        "notes": "52-year-old with chronic low back pain, L4-L5 disc degeneration. MRI shows moderate stenosis. Tried physical therapy 6 weeks and NSAIDs. Pain impacts work. No red flag symptoms."
    }
}

# ============================================
# SECTION 7: UI - PA REQUEST FORM
# ============================================

st.markdown("---")
st.markdown("### 📋 PA Request Input")

# Three-source tabs for PA requests
tab1, tab2, tab3 = st.tabs(["📊 From Queue", "🧪 Sample Cases", "✍️ Custom"])

# Initialize session state for selected request
if 'selected_request' not in st.session_state:
    st.session_state.selected_request = None

# TAB 1: FROM QUEUE (Production workflow)
with tab1:
    st.markdown("**Load pending PA requests from database**")
    
    if st.button("🔄 Refresh Queue", key="refresh_queue"):
        st.session_state.pending_requests = load_pending_requests()
    
    # Load on first view
    if 'pending_requests' not in st.session_state:
        st.session_state.pending_requests = load_pending_requests()
    
    if st.session_state.pending_requests:
        st.success(f"✅ {len(st.session_state.pending_requests)} pending requests found")
        
        # Display with urgency indicators
        for req in st.session_state.pending_requests:
            urgency_icon = "🔴" if req['urgency'] == "STAT" else "🟡" if req['urgency'] == "URGENT" else "🟢"
            label = f"{urgency_icon} {req['request_id']} - {req['patient_id']} - CPT {req['procedure_code']}"
            
            if st.button(label, key=f"queue_{req['request_id']}"):
                # Load full request data
                st.session_state.selected_request = {
                    'source': 'queue',
                    'request_id': req['request_id'],
                    'patient_id': req['patient_id'],
                    'procedure_code': req['procedure_code'],
                    'diagnosis_code': req['diagnosis_code'],
                    'urgency': req['urgency'],
                    'notes': load_patient_clinical_notes(req['patient_id'])
                }
                st.success(f"✅ Loaded {req['request_id']}")
                st.rerun()
    else:
        st.info("ℹ️ No pending PA requests in queue. Try Sample Cases tab to test the system.")

# TAB 2: SAMPLE CASES (Demo/testing)
with tab2:
    st.markdown("**Pre-built test cases with expected outcomes**")
    
    for sample_name, sample_data in SAMPLE_REQUESTS.items():
        if st.button(sample_name, key=f"sample_{sample_name}"):
            st.session_state.selected_request = {
                'source': 'sample',
                'request_id': f"SAMPLE_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                **sample_data
            }
            st.success(f"✅ Loaded sample: {sample_name}")
            st.rerun()

# TAB 3: CUSTOM (Edge case testing)
with tab3:
    st.markdown("**Enter custom PA request details**")
    st.info("💡 **Tip:** Fields are pre-filled with a sample case for convenience. Modify as needed!")
    
    col1, col2 = st.columns(2)
    
    with col1:
        custom_patient_id = st.text_input("Patient ID", value="PT00001", key="custom_patient")
        custom_procedure = st.text_input("Procedure Code (CPT)", value="29881", key="custom_proc")
    
    with col2:
        custom_diagnosis = st.text_input("Diagnosis Code (ICD-10)", value="M23.205", key="custom_diag")
        custom_urgency = st.selectbox("Urgency", ["ROUTINE", "URGENT", "STAT"], key="custom_urgency")
    
    custom_notes = st.text_area(
        "Clinical Notes",
        value="58-year-old male with right knee medial meniscus tear. MRI confirms tear. Failed 8 weeks of physical therapy and NSAIDs. Pain limits daily activities. Cleared by cardiologist for surgery.",
        height=150,
        key="custom_notes"
    )
    
    if st.button("📝 Use Custom Request", key="use_custom"):
        st.session_state.selected_request = {
            'source': 'custom',
            'request_id': f"CUSTOM_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'patient_id': custom_patient_id,
            'procedure_code': custom_procedure,
            'diagnosis_code': custom_diagnosis,
            'urgency': custom_urgency,
            'notes': custom_notes
        }
        st.success("✅ Custom request loaded")
        st.rerun()

# Display selected request
if st.session_state.selected_request:
    st.markdown("---")
    st.markdown("### 📄 Current PA Request")
    
    req = st.session_state.selected_request
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Request ID", req['request_id'])
    col2.metric("Patient ID", req['patient_id'])
    col3.metric("Procedure (CPT)", req['procedure_code'])
    col4.metric("Diagnosis (ICD-10)", req['diagnosis_code'])
    
    with st.expander("📋 Clinical Notes", expanded=False):
        st.text_area("Notes", value=req['notes'], height=200, disabled=True, label_visibility="collapsed")
    
    # ============================================
    # SECTION 8: AGENT EXECUTION
    # ============================================
    
    st.markdown("---")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        analyze_btn = st.button("🤖 Review PA Request", type="primary", use_container_width=True)
    with col2:
        st.caption(f"The AI agent will evaluate clinical evidence against MCG guidelines using {LLM_ENDPOINT}")
    
    if analyze_btn:
        st.markdown("---")
        st.markdown("### 🤖 LangGraph PA Workflow")
        
        total_start = time.time()
        
        # Create the LangGraph workflow
        workflow = create_pa_workflow(_version="v5")
        
        if not workflow:
            st.error("❌ Failed to create LangGraph workflow")
        else:
            # Initialize state
            initial_state = {
                "patient_id": req['patient_id'],
                "procedure_code": req['procedure_code'],
                "diagnosis_code": req['diagnosis_code'],
                "patient_clinical_records": "",  # Will be populated by load_patient_data_node
                "mcg_guideline": {},
                "questions": [],
                "current_question_idx": 0,
                "mcg_answers": [],
                "decision": "MANUAL_REVIEW",
                "confidence": 0.5,
                "messages": []
            }
            
            # Execute workflow with streaming
            st.markdown("#### 🔄 LangGraph Execution")
            progress_placeholder = st.empty()
            log_placeholder = st.empty()
            
            try:
                with st.spinner("🤖 LangGraph workflow executing..."):
                    # Run workflow (streams state after each node)
                    final_state = None
                    logs = []
                    
                    for state_update in workflow.stream(initial_state):
                        # state_update is a dict with node name as key
                        for node_name, node_output in state_update.items():
                            logs.append(f"**Node: {node_name}**")
                            if 'messages' in node_output:
                                for msg in node_output['messages']:
                                    logs.append(f"  {msg}")
                            
                            # Update progress
                            if 'current_question_idx' in node_output and 'questions' in initial_state:
                                questions = node_output.get('questions', initial_state.get('questions', []))
                                idx = node_output['current_question_idx']
                                if questions:
                                    progress = idx / len(questions)
                                    progress_placeholder.progress(min(progress, 1.0))
                        
                        # Merge state
                        if not final_state:
                            final_state = initial_state.copy()
                        for node_name, node_output in state_update.items():
                            for key, value in node_output.items():
                                if key == 'mcg_answers' or key == 'messages':
                                    # Accumulate lists
                                    if key not in final_state:
                                        final_state[key] = []
                                    if isinstance(value, list):
                                        final_state[key].extend(value)
                                else:
                                    final_state[key] = value
                    
                    # Show execution log
                    with st.expander("📝 LangGraph Execution Log", expanded=True):
                        for log in logs:
                            st.markdown(log)
                    
                    elapsed_time = (time.time() - total_start) * 1000
                    st.success(f"✅ LangGraph workflow complete in {elapsed_time:.0f}ms")
                    
                    # Extract results from final state
                    decision = final_state.get('decision', 'MANUAL_REVIEW')
                    confidence = final_state.get('confidence', 0.5)
                    mcg_code = final_state.get('mcg_guideline', {}).get('guideline_id', 'UNKNOWN')
                    mcg_answers = final_state.get('mcg_answers', [])
                    yes_count = sum(1 for a in mcg_answers if a['answer'] == "YES")
                    total_questions = len(final_state.get('questions', []))
                    
                    # Store in session state for display section
                    st.session_state['pa_decision'] = decision
                    st.session_state['pa_confidence'] = confidence
                    st.session_state['pa_mcg_code'] = mcg_code
                    st.session_state['pa_mcg_answers'] = mcg_answers
                    st.session_state['pa_yes_count'] = yes_count
                    st.session_state['pa_total_questions'] = total_questions
                    
            except Exception as e:
                st.error(f"❌ LangGraph workflow error: {e}")
                import traceback
                st.error(traceback.format_exc())
        
        # ============================================
        # SECTION 9: RESULTS DISPLAY WITH TRACEABILITY
        # ============================================
        
        st.markdown("---")
        st.markdown("### 📊 PA Decision")
        
        # Display decision badge (data from session state)
        decision = st.session_state.get('pa_decision', 'MANUAL_REVIEW')
        confidence = st.session_state.get('pa_confidence', 0.0)
        mcg_code = st.session_state.get('pa_mcg_code', 'UNKNOWN')
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if decision == "APPROVED":
                st.success(f"### ✅ {decision}")
            elif decision == "DENIED":
                st.error(f"### ❌ {decision}")
            else:
                st.warning(f"### ⚠️ {decision}")
        
        with col2:
            st.metric("Confidence", f"{confidence*100:.0f}%")
        
        with col3:
            st.metric("MCG Code", mcg_code)
        
        # Traceability Table
        st.markdown("#### 📋 MCG Question Traceability")
        
        mcg_answers = st.session_state.get('pa_mcg_answers', [])
        
        if mcg_answers:
            # Convert to DataFrame for display
            trace_data = []
            for i, qa in enumerate(mcg_answers, 1):
                trace_data.append({
                    'Q#': i,
                    'Question': qa.get('question', 'N/A'),
                    'Answer': qa.get('answer', 'N/A'),
                    'Evidence': qa.get('evidence', 'N/A')[:200] + '...' if len(qa.get('evidence', '')) > 200 else qa.get('evidence', 'N/A'),
                    'Confidence': f"{qa.get('confidence', 0)*100:.0f}%"
                })
            
            trace_df = pd.DataFrame(trace_data)
            st.dataframe(trace_df, use_container_width=True, height=300)
            
            # Download audit trail
            csv = trace_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Audit Trail (CSV)",
                data=csv,
                file_name=f"pa_audit_{req['request_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.info("ℹ️ No detailed Q&A traceability available.")
        
        # ============================================
        # SECTION 10: SAVE DECISION TO DATABASE
        # ============================================
        
        st.markdown("---")
        
        # Only allow saving for queue requests (not samples or custom)
        if req['source'] == 'queue':
            st.markdown("### 💾 Save Decision")
            
            col1, col2 = st.columns([1, 3])
            
            with col1:
                save_btn = st.button("💾 Save to Database", type="primary", use_container_width=True)
            
            with col2:
                st.caption("This will update the authorization_requests table and create audit trail entries.")
            
            if save_btn:
                with st.spinner("💾 Saving decision..."):
                    # Generate explanation
                    yes_count = st.session_state.get('pa_yes_count', 0)
                    total_q = st.session_state.get('pa_total_questions', 0)
                    explanation = f"Answered {yes_count} of {total_questions} MCG questions affirmatively. Confidence: {confidence*100:.0f}%."
                    
                    # Save main decision
                    success = update_pa_decision(
                        req['request_id'],
                        decision,
                        mcg_code,
                        explanation,
                        confidence
                    )
                    
                    if success:
                        # Save each Q&A to audit trail
                        for i, qa in enumerate(mcg_answers, 1):
                            save_audit_trail_entry(
                                req['request_id'],
                                i,
                                qa.get('question', ''),
                                qa.get('answer', ''),
                                qa.get('evidence', ''),
                                'CLINICAL_RECORD',  # Default source
                                qa.get('confidence', 0.0)
                            )
                        
                        st.success(f"✅ Decision saved successfully for {req['request_id']}!")
                        st.balloons()
                        
                        # Clear selected request and refresh queue
                        st.session_state.selected_request = None
                        st.session_state.pending_requests = load_pending_requests()
                        
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("❌ Failed to save decision. Check logs for details.")
        else:
            st.info(f"ℹ️ This is a {req['source']} request. Only queue requests can be saved to the database.")

else:
    st.info("👆 Select a PA request from one of the tabs above to begin analysis.")

# Footer
st.markdown("---")
st.caption(f"🔧 Environment: {ENVIRONMENT} | Catalog: {CATALOG} | LLM: {LLM_ENDPOINT}")

"""
Prior Authorization Agent - LangGraph ReAct Agent

This module implements the LangGraph agent that orchestrates PA decisions using 7 UC AI Functions.
"""

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_databricks import ChatDatabricks
from typing import TypedDict, Annotated, Sequence
from databricks.sdk import WorkspaceClient
from databricks import sql
import json
import os


class PAAgentState(TypedDict):
    """State for the PA Agent workflow"""
    messages: Annotated[Sequence[dict], "The messages in the conversation"]
    patient_id: str
    procedure_code: str
    diagnosis_code: str
    clinical_notes: str
    mcg_guideline: dict | None
    mcg_answers: dict | None
    decision: str | None
    confidence: float | None
    explanation: str | None


class PriorAuthorizationAgent:
    """
    LangGraph ReAct Agent for Prior Authorization decisions.
    
    Workflow:
    1. Extract clinical criteria from request
    2. Search for appropriate MCG/InterQual guideline
    3. Answer each guideline question by searching clinical records
    4. Make authorization decision based on answers
    5. Generate human-readable explanation
    """
    
    def __init__(self, catalog_name: str, schema_name: str, warehouse_id: str):
        self.catalog = catalog_name
        self.schema = schema_name
        self.warehouse_id = warehouse_id
        self.w = WorkspaceClient()
        
        # Initialize LangChain Databricks LLM
        self.llm = ChatDatabricks(
            endpoint="databricks-meta-llama-3-1-405b-instruct",
            max_tokens=1000
        )
        
        # Build the agent graph
        self.graph = self._build_graph()
    
    def _get_sql_connection(self):
        """Get Databricks SQL connection"""
        from databricks.sdk.core import Config
        cfg = Config()
        
        return sql.connect(
            server_hostname=cfg.host,
            http_path=f"/sql/1.0/warehouses/{self.warehouse_id}",
            credentials_provider=lambda: cfg.authenticate
        )
    
    def _call_uc_function(self, function_name: str, *args) -> str:
        """Call a Unity Catalog AI function"""
        conn = self._get_sql_connection()
        cursor = conn.cursor()
        
        # Build SQL call
        args_str = ", ".join([f"'{arg}'" if isinstance(arg, str) else str(arg) for arg in args])
        sql_query = f"SELECT {self.catalog}.{self.schema}.{function_name}({args_str}) AS result"
        
        cursor.execute(sql_query)
        result = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        return result
    
    def _extract_criteria_node(self, state: PAAgentState) -> PAAgentState:
        """Node 1: Extract clinical criteria from notes"""
        print("🔍 Extracting clinical criteria...")
        
        extracted_data = self._call_uc_function(
            "extract_clinical_criteria",
            state["clinical_notes"]
        )
        
        state["messages"].append({
            "role": "assistant",
            "content": f"Extracted clinical criteria: {extracted_data[:200]}..."
        })
        
        return state
    
    def _get_guideline_node(self, state: PAAgentState) -> PAAgentState:
        """Node 2: Retrieve appropriate MCG/InterQual guideline"""
        print(f"📋 Retrieving guideline for procedure {state['procedure_code']}...")
        
        # Determine platform (MCG for outpatient, InterQual for inpatient)
        platform = "MCG"  # Default to MCG for this MVP
        
        guideline_result = self._call_uc_function(
            "check_mcg_guidelines",
            state["procedure_code"],
            state["diagnosis_code"]
        )
        
        # Parse guideline
        try:
            if "MCG Guideline:" in guideline_result:
                lines = guideline_result.split("\\n")
                mcg_code = lines[0].replace("MCG Guideline:", "").strip()
                
                # Extract questionnaire JSON
                questionnaire_start = guideline_result.find("Questionnaire:")
                questionnaire_end = guideline_result.find("Decision Criteria:")
                
                if questionnaire_start > 0 and questionnaire_end > 0:
                    questionnaire_json = guideline_result[questionnaire_start+14:questionnaire_end].strip()
                    questionnaire = json.loads(questionnaire_json)
                else:
                    questionnaire = []
                
                state["mcg_guideline"] = {
                    "code": mcg_code,
                    "questionnaire": questionnaire,
                    "content": guideline_result
                }
            else:
                state["mcg_guideline"] = None
        except Exception as e:
            print(f"⚠️ Error parsing guideline: {e}")
            state["mcg_guideline"] = None
        
        state["messages"].append({
            "role": "assistant",
            "content": f"Retrieved guideline: {state['mcg_guideline']['code'] if state['mcg_guideline'] else 'NOT FOUND'}"
        })
        
        return state
    
    def _answer_questions_node(self, state: PAAgentState) -> PAAgentState:
        """Node 3: Answer MCG questionnaire questions"""
        print("❓ Answering MCG questionnaire...")
        
        if not state["mcg_guideline"] or not state["mcg_guideline"].get("questionnaire"):
            print("⚠️ No questionnaire found, skipping to manual review")
            state["mcg_answers"] = {}
            return state
        
        answers = {}
        questionnaire = state["mcg_guideline"]["questionnaire"]
        
        # Answer each question
        for q in questionnaire[:6]:  # Limit to first 6 questions for performance
            question = q.get("question", "")
            print(f"   Answering: {question[:60]}...")
            
            answer_result = self._call_uc_function(
                "answer_mcg_question",
                state["patient_id"],
                question
            )
            
            # Parse YES/NO from result
            answer = "YES" if "YES" in answer_result.upper() else "NO"
            answers[question] = {
                "answer": answer,
                "explanation": answer_result
            }
        
        state["mcg_answers"] = answers
        state["messages"].append({
            "role": "assistant",
            "content": f"Answered {len(answers)} MCG questions"
        })
        
        return state
    
    def _make_decision_node(self, state: PAAgentState) -> PAAgentState:
        """Node 4: Make authorization decision"""
        print("✅ Making authorization decision...")
        
        if not state["mcg_answers"]:
            state["decision"] = "MANUAL_REVIEW"
            state["confidence"] = 0.0
            state["explanation"] = "No MCG guideline found - requires manual clinical review"
            return state
        
        # Count YES answers
        yes_count = sum(1 for a in state["mcg_answers"].values() if a["answer"] == "YES")
        total_count = len(state["mcg_answers"])
        confidence = yes_count / total_count if total_count > 0 else 0.0
        
        # Determine decision
        if confidence >= 0.80:  # 80%+ criteria met
            decision = "APPROVED"
        elif confidence >= 0.60:  # 60-80% criteria met
            decision = "MANUAL_REVIEW"
        else:  # < 60% criteria met
            decision = "DENIED"
        
        state["decision"] = decision
        state["confidence"] = confidence
        
        print(f"   Decision: {decision} (Confidence: {confidence:.0%})")
        
        state["messages"].append({
            "role": "assistant",
            "content": f"Decision: {decision} with {confidence:.0%} confidence ({yes_count}/{total_count} criteria met)"
        })
        
        return state
    
    def _explain_decision_node(self, state: PAAgentState) -> PAAgentState:
        """Node 5: Generate human-readable explanation"""
        print("📝 Generating explanation...")
        
        answers_json = json.dumps(state["mcg_answers"] if state["mcg_answers"] else {})
        mcg_code = state["mcg_guideline"]["code"] if state["mcg_guideline"] else "UNKNOWN"
        
        explanation = self._call_uc_function(
            "explain_decision",
            state["decision"],
            mcg_code,
            answers_json,
            state["confidence"]
        )
        
        state["explanation"] = explanation
        state["messages"].append({
            "role": "assistant",
            "content": f"Explanation: {explanation}"
        })
        
        return state
    
    def _should_continue(self, state: PAAgentState) -> str:
        """Router: Determine if workflow should continue"""
        if state.get("explanation"):
            return "end"
        return "continue"
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(PAAgentState)
        
        # Add nodes
        workflow.add_node("extract_criteria", self._extract_criteria_node)
        workflow.add_node("get_guideline", self._get_guideline_node)
        workflow.add_node("answer_questions", self._answer_questions_node)
        workflow.add_node("make_decision", self._make_decision_node)
        workflow.add_node("explain_decision", self._explain_decision_node)
        
        # Add edges
        workflow.set_entry_point("extract_criteria")
        workflow.add_edge("extract_criteria", "get_guideline")
        workflow.add_edge("get_guideline", "answer_questions")
        workflow.add_edge("answer_questions", "make_decision")
        workflow.add_edge("make_decision", "explain_decision")
        workflow.add_edge("explain_decision", END)
        
        return workflow.compile()
    
    def process_pa_request(
        self,
        patient_id: str,
        procedure_code: str,
        diagnosis_code: str,
        clinical_notes: str
    ) -> dict:
        """
        Process a prior authorization request.
        
        Args:
            patient_id: Patient identifier
            procedure_code: CPT procedure code
            diagnosis_code: ICD-10 diagnosis code
            clinical_notes: Unstructured clinical notes
            
        Returns:
            dict with decision, confidence, explanation, and details
        """
        print(f"\n{'='*60}")
        print(f"Processing PA Request")
        print(f"{'='*60}")
        print(f"Patient: {patient_id}")
        print(f"Procedure: {procedure_code}")
        print(f"Diagnosis: {diagnosis_code}")
        print(f"{'='*60}\n")
        
        # Initialize state
        initial_state = {
            "messages": [{"role": "system", "content": "Processing prior authorization request"}],
            "patient_id": patient_id,
            "procedure_code": procedure_code,
            "diagnosis_code": diagnosis_code,
            "clinical_notes": clinical_notes,
            "mcg_guideline": None,
            "mcg_answers": None,
            "decision": None,
            "confidence": None,
            "explanation": None
        }
        
        # Run the graph
        final_state = self.graph.invoke(initial_state)
        
        # Return result
        return {
            "decision": final_state["decision"],
            "confidence": final_state["confidence"],
            "mcg_code": final_state["mcg_guideline"]["code"] if final_state["mcg_guideline"] else None,
            "explanation": final_state["explanation"],
            "mcg_answers": final_state["mcg_answers"],
            "requires_manual_review": final_state["decision"] == "MANUAL_REVIEW" or final_state["confidence"] < 0.90
        }


# Example usage
if __name__ == "__main__":
    agent = PriorAuthorizationAgent(
        catalog_name="healthcare_payer_pa_withmcg_guidelines_dev",
        schema_name="main",
        warehouse_id="148ccb90800933a1"
    )
    
    result = agent.process_pa_request(
        patient_id="PT00001",
        procedure_code="73721",
        diagnosis_code="M25.561",
        clinical_notes="Patient presents with chronic right knee pain for 8 months. Failed conservative therapy including PT and NSAIDs."
    )
    
    print(f"\n{'='*60}")
    print("FINAL RESULT")
    print(f"{'='*60}")
    print(json.dumps(result, indent=2))


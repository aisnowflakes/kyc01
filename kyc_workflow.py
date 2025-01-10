from typing import Dict, List, TypedDict
from langgraph.graph import Graph
from openai import OpenAI
import json

# Initialize OpenAI client
client = OpenAI()

# Hardcoded user database
USER_DATABASE = {
    "user-1": {
        "name": "John Doe",
        "id": "ID-123",
        "address": "123 Main St, NYC",
        "payslip": "available",
        "fico_score": 750
    },
    "user-2": {
        "name": "Jane Smith",
        "id": "ID-456",
        "address": "456 Oak Ave, LA",
        "payslip": "missing",
        "fico_score": 680
    },
    "user-3": {
        "name": "Bob Johnson",
        "id": "ID-789",
        "address": "789 Pine Rd, CHI",
        "payslip": "available",
        "fico_score": 820
    }
}

# Define our state type
class KYCState(TypedDict):
    user_id: str
    document_status: str
    eligibility_status: str
    supervisor_message: str
    history: List[str]

# Supervisor Agent
def supervisor_agent(state: KYCState) -> KYCState:
    user_id = state["user_id"]
    
    if "document_status" not in state:
        # Initial state - pass to document analysis
        state["history"].append(f"Supervisor: Initiating document analysis for {user_id}")
        return state
    
    if "document_status" in state and "eligibility_status" not in state:
        # Handle document analysis response
        if state["document_status"] == "NOT OKAY":
            state["supervisor_message"] = "More Information Required"
            state["history"].append(f"Supervisor: Requesting more information from {user_id}")
            return state
        elif state["document_status"] == "OKAY":
            state["history"].append(f"Supervisor: Initiating eligibility check for {user_id}")
            return state
    
    if "eligibility_status" in state:
        # Handle eligibility response
        if state["eligibility_status"] == "PROCEED":
            state["supervisor_message"] = "Loan Approved"
        else:
            state["supervisor_message"] = "Loan cannot be processed"
        state["history"].append(f"Supervisor: Final decision - {state['supervisor_message']}")
    
    return state

# Document Analysis Agent
def document_analysis_agent(state: KYCState) -> KYCState:
    user_id = state["user_id"]
    user_data = USER_DATABASE.get(user_id)
    
    if not user_data:
        state["document_status"] = "NOT OKAY"
        state["history"].append(f"Document Analysis: User {user_id} not found")
        return state
    
    # Check all required documents
    if (user_data["id"] and 
        user_data["address"] and 
        user_data["payslip"] == "available"):
        state["document_status"] = "OKAY"
        state["history"].append(f"Document Analysis: All documents verified for {user_id}")
    else:
        state["document_status"] = "NOT OKAY"
        state["history"].append(f"Document Analysis: Missing documents for {user_id}")
    
    return state

# Eligibility Agent
def eligibility_agent(state: KYCState) -> KYCState:
    if state["document_status"] != "OKAY":
        return state
    
    user_id = state["user_id"]
    user_data = USER_DATABASE.get(user_id)
    
    if user_data["fico_score"] >= 700:
        state["eligibility_status"] = "PROCEED"
        state["history"].append(f"Eligibility: FICO score {user_data['fico_score']} meets criteria")
    else:
        state["eligibility_status"] = "NOT PROCEED"
        state["history"].append(f"Eligibility: FICO score {user_data['fico_score']} below requirement")
    
    return state

# Create the workflow
def create_kyc_workflow() -> Graph:
    workflow = Graph()

    # Add nodes
    workflow.add_node("supervisor", supervisor_agent)
    workflow.add_node("document_analysis", document_analysis_agent)
    workflow.add_node("eligibility", eligibility_agent)

    # Define the edges with conditional routing
    def route_from_supervisor(state):
        if "supervisor_message" in state:
            return "end"
        if "document_status" not in state:
            return "document_analysis"
        if state["document_status"] == "OKAY" and "eligibility_status" not in state:
            return "eligibility"
        return "supervisor"

    workflow.add_edge("supervisor", route_from_supervisor)
    workflow.add_edge("document_analysis", "supervisor")
    workflow.add_edge("eligibility", "supervisor")

    return workflow.compile()

# Function to run the KYC process
def run_kyc_process(user_id: str) -> Dict:
    workflow = create_kyc_workflow()
    
    initial_state: KYCState = {
        "user_id": user_id,
        "history": [f"Process started for user {user_id}"]
    }
    
    final_state = workflow.run(initial_state)
    return final_state 
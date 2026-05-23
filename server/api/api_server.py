from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import random
from datetime import datetime
from core.master_orchestrator import MasterOrchestrator
import pandas as pd
import os

# Initialize APIRouter
router = APIRouter()

# Request Models
class FeedbackRequest(BaseModel):
    action: str  # "CONFIRM" or "FALSE_ALARM"

class ExplainRequest(BaseModel):
    emp_id: Optional[str] = None
    cbsi: Optional[float] = None
    action_type: Optional[str] = None
    amount: Optional[float] = None
    transfer_channel: Optional[str] = None
    timestamp: Optional[str] = None
    remarks: Optional[str] = None
    transaction_id: Optional[str] = None

class TransactionRequest(BaseModel):
    transaction_id: str
    emp_id: str
    destination_account: str
    action_type: str
    amount: float
    transfer_channel: str
    timestamp: str
    emp_class: str = "CLERK"
    remarks: str = ""
    dwell_time_seconds: float = 0
    records_accessed: int = 0
    login_hour: int = 9
    account_touched: str = ""

# Initialize Orchestrator
orchestrator = MasterOrchestrator()

# ---------------------------------------------------------
# ENDPOINT 1: Top KPIs
# ---------------------------------------------------------
@router.get("/dashboard/kpis")
def get_kpis():
    return {
        "transactions_scanned": 48021,
        "critical_alerts": 12,
        "high_risk_flags": 34,
        "confirmed_fraud": 4,
        "avg_cbsi_score": 15.1
    }

# ---------------------------------------------------------
# ENDPOINT 2: Kafka Live Stream Simulation
# ---------------------------------------------------------
@router.get("/stream/kafka-sim")
def get_live_stream():
    # Simulated live data coming from Orchestrator
    return [
        {"emp_id": "EMP_1412", "type": "ATM_Withdrawal", "amount": 34739, "cbsi": 15, "time": datetime.now().strftime("%H:%M:%S")},
        {"emp_id": "EMP_1024", "type": "NEFT_Transfer", "amount": 5000000, "cbsi": 100, "time": datetime.now().strftime("%H:%M:%S")}
    ]

# ---------------------------------------------------------
# ENDPOINT 3: Agent 2 Graph Fund Flow
# ---------------------------------------------------------
@router.get("/graph/fundflow")
def get_graph_data():
    return {
        "nodes": [
            {"id": "EMP_1024", "label": "EMP_1024", "group": "critical"},
            {"id": "ACC_GHOST_99", "label": "ACC_GHOST_99", "group": "honeypot"},
            {"id": "EMP_1099", "label": "EMP_1099", "group": "watch"}
        ],
        "edges": [
            {"from": "EMP_1024", "to": "ACC_GHOST_99", "label": "Rs.50,00,000"}
        ]
    }

# ---------------------------------------------------------
# ENDPOINT 4: Glass-Box Explainability (Dynamic LLM Mock)
# ---------------------------------------------------------
@router.post("/explain/{emp_id}")
def generate_explanation(emp_id: str, payload: Optional[ExplainRequest] = None):
    # Asli system mein yahan Gemini AI ka call jayega.
    cbsi = payload.cbsi if payload and payload.cbsi is not None else None
    action_type = payload.action_type if payload else None
    amount = payload.amount if payload else None
    channel = payload.transfer_channel if payload else None
    remarks = payload.remarks if payload else None

    if emp_id == "EMP_1024":
        explanation = (
            f"VaultMind flagged {emp_id} due to a direct interaction with a DeceptionGuard Honeypot account. "
            "Agent 4 also detected privilege escalation 12 mins prior."
        )
    elif cbsi is None:
        explanation = (
            f"AI baseline active for {emp_id}. Insufficient telemetry to derive risk context. "
            "Awaiting more signals for deeper analysis."
        )
    elif cbsi >= 80:
        explanation = (
            f"High-risk anomaly detected for {emp_id}. CBSI {cbsi:.1f} exceeds critical threshold. "
            f"Action '{action_type or 'UNKNOWN'}' and channel '{channel or 'UNKNOWN'}' deviate from baseline. "
            f"{'Transaction amount Rs.' + f'{amount:,.2f}' if amount else 'Amount signal unavailable.'}"
        )
    elif cbsi >= 50:
        explanation = (
            f"Elevated risk for {emp_id}. CBSI {cbsi:.1f} shows abnormal behavior. "
            f"Action '{action_type or 'UNKNOWN'}' and channel '{channel or 'UNKNOWN'}' require review. "
            f"{'Remarks flag: ' + remarks[:80] + '...' if remarks else 'No NLP flags detected.'}"
        )
    else:
        explanation = (
            f"Normal behavior observed for {emp_id}. CBSI {cbsi:.1f} within baseline. "
            f"Action '{action_type or 'UNKNOWN'}' aligns with typical patterns. "
            "No abnormal NLP signals detected."
        )

    return {"explanation": explanation}

# ---------------------------------------------------------
# ENDPOINT 5: Human-in-the-Loop Feedback
# ---------------------------------------------------------
@router.post("/feedback/{emp_id}")
def submit_feedback(emp_id: str, feedback: FeedbackRequest):
    if feedback.action == "CONFIRM":
        return {"status": "success", "message": f"Incident confirmed. Locking {emp_id} terminal and drafting FIU-STR."}
    else:
        return {"status": "success", "message": f"False alarm logged. Recalibrating AI baseline for {emp_id}."}

# ---------------------------------------------------------
# ENDPOINT 7: Orchestrator Transaction Scan (with Debug Logs)
# ---------------------------------------------------------
@router.post("/orchestrator/scan")
def orchestrator_scan(tx: TransactionRequest):
    tx_dict = tx.dict()
    
    print(f"\n{'='*70}")
    print(f"🔵 Backend received transaction: {tx_dict['transaction_id']}")
    print(f"   Employee: {tx_dict['emp_id']} | Amount: Rs. {tx_dict['amount']}")
    print(f"{'='*70}")
    
    # Run orchestrator models
    result = orchestrator.process_transaction(tx_dict)
    
    predicted_score = result.get('risk_score', 15)
    print(f"\n{'='*70}")
    print(f"✅ Model predicted score: {predicted_score}/100")
    print(f"   Risk Level: {'🔴 CRITICAL' if predicted_score >= 70 else '🟡 HIGH' if predicted_score >= 50 else '🟢 NORMAL'}")
    print(f"{'='*70}\n")
    
    return {
        "transaction_id": tx_dict['transaction_id'],
        "emp_id": tx_dict['emp_id'],
        "cbsi_score": predicted_score,
        "risk_level": "CRITICAL" if predicted_score >= 70 else "HIGH" if predicted_score >= 50 else "NORMAL",
        "signals_triggered": result.get('signals_triggered', [])
    }

# ---------------------------------------------------------
# ENDPOINT 8: Employee Roster with Metadata
# ---------------------------------------------------------
@router.get("/roster/employees")
def get_employee_roster():
    """
    Returns employee metadata (emp_id, emp_class, branch_id, etc.)
    Used by React frontend to display Employee Roster with Role and Branch columns
    """
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        emp_csv = os.path.join(base_dir, "Testing_data", "employees_master.csv")
        
        if not os.path.exists(emp_csv):
            return {"employees": [], "error": "Employee data not found"}
        
        emp_df = pd.read_csv(emp_csv)
        
        # Select relevant columns for frontend
        cols_to_return = ["emp_id", "emp_class", "branch_id"]
        cols_available = [c for c in cols_to_return if c in emp_df.columns]
        
        if not cols_available:
            return {"employees": [], "error": "Required columns not found in employee data"}
        
        roster_data = emp_df[cols_available].drop_duplicates(subset=["emp_id"]).fillna("").to_dict('records')
        return {
            "employees": roster_data,
            "total": len(roster_data),
            "columns": cols_available
        }
    except Exception as e:
        return {"employees": [], "error": str(e), "total": 0}

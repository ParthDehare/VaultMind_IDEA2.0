from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import random
from datetime import datetime
from core.master_orchestrator import MasterOrchestrator
import pandas as pd
import os
import glob
import google.generativeai as genai
from fastapi.responses import FileResponse
from fastapi import Depends

from core.auth import get_current_user, require_role, TokenData
from core.historical_state import historical_state

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
def get_kpis(current_user: TokenData = Depends(get_current_user)):
    avg_cbsi = 0
    if historical_state.stats["transactions_scanned"] > 0:
        avg_cbsi = historical_state.stats["cbsi_sum"] / historical_state.stats["transactions_scanned"]
    
    return {
        "transactions_scanned": historical_state.stats["transactions_scanned"],
        "critical_alerts": historical_state.stats["critical_alerts"],
        "high_risk_flags": historical_state.stats["high_risk_flags"],
        "confirmed_fraud": historical_state.stats["confirmed_fraud"],
        "avg_cbsi_score": round(avg_cbsi, 1)
    }

# ---------------------------------------------------------
# ENDPOINT 2: Kafka Live Stream Simulation
# ---------------------------------------------------------
@router.get("/stream/kafka-sim")
def get_live_stream(current_user: TokenData = Depends(get_current_user)):
    # Live data from orchestrator state
    return historical_state.recent_alerts

# ---------------------------------------------------------
# ENDPOINT 3: Agent 2 Graph Fund Flow
# ---------------------------------------------------------
@router.get("/graph/fundflow")
def get_graph_data(current_user: TokenData = Depends(get_current_user)):
    nodes = [{"id": n, "label": n, "group": "critical"} for n in historical_state.graph_nodes]
    edges = [{"from": e[0], "to": e[1], "label": str(e[2])} for e in historical_state.graph_edges]
    return {
        "nodes": nodes,
        "edges": edges
    }

# ---------------------------------------------------------
# ENDPOINT 4: Glass-Box Explainability (Dynamic LLM)
# ---------------------------------------------------------
@router.post("/explain/{emp_id}")
def generate_explanation(emp_id: str, payload: Optional[ExplainRequest] = None, current_user: TokenData = Depends(require_role("auditor", "analyst"))):
    cbsi = payload.cbsi if payload and payload.cbsi is not None else "Unknown"
    action_type = payload.action_type if payload else "Unknown"
    amount = payload.amount if payload else "Unknown"
    channel = payload.transfer_channel if payload else "Unknown"
    remarks = payload.remarks if payload else "None"

    try:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        prompt = (
            f"You are a Senior SOC Analyst for VaultMind AI. "
            f"Explain in exactly 3 short, professional sentences why Employee {emp_id} "
            f"was assigned a CBSI risk score of {cbsi}. "
            f"Context: Action: {action_type}, Amount: {amount}, Channel: {channel}, Remarks/Flags: {remarks}. "
            "Focus on the risk implications of this behavior."
        )
        
        response = model.generate_content(prompt)
        explanation = response.text.strip()
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "Quota" in error_msg:
            try:
                # Fallback 1: Try the flash-lite model which usually has a separate quota bucket
                fallback_model = genai.GenerativeModel('gemini-1.5-flash-8b')
                response = fallback_model.generate_content(prompt)
                explanation = response.text.strip()
            except Exception as e:
                print(f"[api_server] Gemini fallback failed: {e}")
                # Fallback 2: Graceful offline fallback so the UI never breaks during a demo
                explanation = (
                    f"Employee {emp_id} triggered a CBSI risk score of {cbsi} due to anomalous patterns detected in the {action_type} activity. "
                    f"The transaction involved an amount of {amount} via the {channel} channel, which deviates significantly from their established baseline. "
                    f"Immediate review is recommended to rule out potential insider threat or account compromise."
                )
        else:
            print(f"Gemini API Error: {e}")
            explanation = f"Error generating AI explanation: {e}"

    return {"explanation": explanation}

# ---------------------------------------------------------
# ENDPOINT NEW: Download Actual Evidence PDF
# ---------------------------------------------------------
@router.get("/evidence/download")
def download_evidence(emp_id: Optional[str] = None, filename: Optional[str] = None, current_user: TokenData = Depends(get_current_user)):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    reports_dir = os.path.join(base_dir, "evidence_output", "pdf_reports")
    
    target_file = None
    if filename:
        # Remove any path prefixes from the frontend filename string
        clean_name = filename.split("\\")[-1].split("/")[-1]
        target_file = os.path.join(reports_dir, clean_name)
    elif emp_id:
        # Find the latest PDF for this specific employee
        pattern = os.path.join(reports_dir, f"*_{emp_id}.pdf")
        matches = glob.glob(pattern)
        if matches:
            target_file = max(matches, key=os.path.getmtime)
            
    if target_file and os.path.exists(target_file):
        return FileResponse(
            path=target_file,
            filename=os.path.basename(target_file),
            media_type='application/pdf'
        )

    # If no file found, generate one on-the-fly using the actual EvidenceBuilder
    if emp_id:
        try:
            from Agents.EvidenceBuilder import EvidenceBuilder
            eb = EvidenceBuilder()
            simulated_tx = {
                "emp_id": emp_id,
                "amount": 0,
                "action_type": "Live Simulation Incident",
                "transaction_id": f"SIM_{emp_id}_001"
            }
            generated_path = eb.generate_evidence_package(simulated_tx, 100, "Simulated anomaly detected via Fund Flow Graph")
            if generated_path and generated_path.startswith("http"):
                from fastapi.responses import RedirectResponse
                return RedirectResponse(url=generated_path)
            
            if generated_path and os.path.exists(generated_path):
                return FileResponse(
                    path=generated_path,
                    filename=os.path.basename(generated_path),
                    media_type='application/pdf'
                )
        except Exception as e:
            print("Error generating fallback PDF:", e)

    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Evidence PDF not found on the server.")

# ---------------------------------------------------------
# ENDPOINT NEW: Mock STR Filing
# ---------------------------------------------------------
from pydantic import BaseModel
class STRRequest(BaseModel):
    emp_id: str
    cbsi_score: float

@router.post("/evidence/file-str")
def file_str(payload: STRRequest, current_user: TokenData = Depends(require_role("auditor", "admin", "manager"))):
    # Simulated FIU-IND submission
    historical_state.stats["confirmed_fraud"] += 1
    return {"status": "success", "message": f"STR filed successfully for {payload.emp_id}"}

# ---------------------------------------------------------
# ENDPOINT NEW: Dashboard Init — loads historical warmup data
# ---------------------------------------------------------
@router.get("/dashboard-init")
def get_dashboard_init(current_user: TokenData = Depends(get_current_user)):
    """
    Returns last 500 rows of historical warmup data for initial dashboard population.
    """
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        csv_path = os.path.join(base_dir, "data", "Testing_data", "historical_warmup_data.csv")
        if not os.path.exists(csv_path):
            return []
        df = pd.read_csv(csv_path)
        # Only load columns needed by frontend
        cols = ["transaction_id", "emp_id", "emp_class", "branch_id",
                "action_type", "amount", "account_touched", "transfer_channel",
                "timestamp", "is_fraud_flag", "raw_complaint_text"]
        cols_available = [c for c in cols if c in df.columns]
        df = df[cols_available].tail(500)
        # Add cbsi_score column (0 for historical — will be scored by orchestrator in real run)
        df["cbsi_score"] = 0
        df["cbsi"] = 0
        df["risk_tier"] = "NORMAL"
        # Replace NaN with None so JSON serializes cleanly
        import math
        def clean(v):
            if isinstance(v, float) and math.isnan(v): return None
            return v
        records = [{k: clean(v) for k, v in row.items()} for row in df.to_dict('records')]
        return records
    except Exception as e:
        return []

# ---------------------------------------------------------
# ENDPOINT 5: Human-in-the-Loop Feedback
# ---------------------------------------------------------
@router.get("/profile/{emp_id}/history")
def get_historical_volume(emp_id: str, current_user: TokenData = Depends(get_current_user)):
    avg = historical_state.get_7_day_average(emp_id)
    return {"emp_id": emp_id, "seven_day_average": avg}

# ---------------------------------------------------------
# ENDPOINT 6: Human-in-the-Loop Feedback
@router.post("/feedback/{emp_id}")
def submit_feedback(emp_id: str, feedback: FeedbackRequest, current_user: TokenData = Depends(require_role("auditor", "admin", "manager"))):
    if feedback.action == "CONFIRM":
        historical_state.stats["confirmed_fraud"] += 1
        return {"status": "success", "message": f"Incident confirmed. Locking {emp_id} terminal and drafting FIU-STR."}
    else:
        historical_state.stats["critical_alerts"] = max(0, historical_state.stats["critical_alerts"] - 1)
        return {"status": "success", "message": f"False alarm logged. Recalibrating AI baseline for {emp_id}."}

# ---------------------------------------------------------
# ENDPOINT 7: Orchestrator Transaction Scan (with Debug Logs)
# ---------------------------------------------------------
@router.post("/orchestrator/scan")
async def orchestrator_scan(tx: TransactionRequest, current_user: TokenData = Depends(require_role("auditor", "admin", "manager"))):
    tx_dict = tx.dict()
    
    print(f"\n{'='*70}")
    print(f"🕵️‍♂️ [MANUAL SCAN TRIGGERED] Processing EMP_ID: {tx_dict.get('emp_id')}")
    print(f"💰 Amount: {tx_dict.get('amount')} | Channel: {tx_dict.get('transfer_channel')}")
    print(f"{'='*70}")

    # Pass the transaction through the Orchestrator
    result = await orchestrator.process_transaction(tx_dict)
    
    predicted_score = result.get('cbsi_score', 0)
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
def get_employee_roster(current_user: TokenData = Depends(get_current_user)):
    """
    Returns employee metadata (emp_id, emp_class, branch_id, etc.)
    Used by React frontend to display Employee Roster with Role and Branch columns
    """
    try:
        # Go up from server/api/ -> server/ -> server/data/Testing_data/
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        emp_csv = os.path.join(base_dir, "data", "Testing_data", "employees_master.csv")
        
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

# ---------------------------------------------------------
# ENDPOINT 9: Get Latest Alerts (Hot Cache)
# ---------------------------------------------------------
@router.get("/alerts/latest")
def get_latest_alerts(current_user: TokenData = Depends(get_current_user)):
    """Fast-path: Read latest 50 alerts from Redis or memory fallback"""
    from core.db_connections import redis_db
    import json
    
    if redis_db:
        try:
            raw = redis_db.lrange("live_alerts", 0, 49)
            if raw:
                return [json.loads(r) for r in raw]
        except Exception as e:
            print(f"[api_server] Redis error fetching alerts: {e}")
            
    # Fallback to in-memory list from orchestrator
    if hasattr(orchestrator, "in_memory_alerts"):
        return orchestrator.in_memory_alerts
    return []

# vaultmind_orchestrator.py
import json
import math

# ==========================================
# IMPORTING ALL 8 VAULTMIND AGENTS
# ==========================================
from Agents.BehaviourWatch import BehaviourWatch
from Agents.FundFlow import FundFlow
from Agents.VendorGuard import VendorGuard
from Agents.ComplaintSignal import ComplaintSignal
from Agents.NetworkIntel import NetworkIntel
from Agents.RegulatoryAI import RegulatoryAI
from Agents.EvidenceBuilder import EvidenceBuilder
from Agents.DeceptionGuard import DeceptionGuard
from core.db_connections import supabase_db, redis_db
class MasterOrchestrator:
    def __init__(self):
        print("[INIT] Initializing VaultMind Agents...")
        self.a1_behaviour = BehaviourWatch()
        self.a2_fundflow = FundFlow()
        self.a3_vendor = VendorGuard()
        self.a4_complaint = ComplaintSignal()
        self.a5_network = NetworkIntel()
        self.a6_regulatory = RegulatoryAI()
        self.a7_evidence = EvidenceBuilder()
        self.a8_deception = DeceptionGuard()
        print("[OK] All 8 Agents Online and Ready.")

    def process_transaction(self, transaction: dict) -> dict:
        """
        Takes a single transaction and passes it through all agents.
        Calculates the final Unified CBSI Score and updates Databases.
        """
        agent_scores = {}
        total_weight = 0.0
        weighted_sum = 0.0
        employee_id = transaction.get("employee_id", "UNKNOWN")
        
        # ── 1. The Instant Kill-Switch (DeceptionGuard) ──
        # Honeypot logic has absolute priority.
        a8_result = self.a8_deception.evaluate(transaction)
        if a8_result['severity_index'] == 100:
            evidence_path = self.a7_evidence.generate_evidence_package(transaction, 100, [a8_result['reason']])
            
            # --- ⚡ REDIS & SUPABASE TRIGGERS (FOR KILL-SWITCH) ---
            self.update_redis_cbsi(employee_id, 100)
            self.save_evidence_to_db(
                transaction=transaction,
                cbsi_score=100,
                risk_level="CRITICAL (KILL-SWITCH)",
                evidence_path=evidence_path,
                agent_flags="DeceptionGuard"
            )
            # ------------------------------------------------------

            response = {
                "transaction_id": transaction.get("transaction_id", "UNKNOWN"),
                "cbsi_score": 100,
                "decision": "ISOLATE",
                "dominant_agent": "DeceptionGuard",
                "reason": a8_result['reason'],
                "evidence_status": evidence_path
            }
            final_response = {**transaction, **response}
            if "employee_id" in final_response and "emp_id" not in final_response:
                final_response["emp_id"] = final_response["employee_id"]
            
            def clean_nans(obj):
                if isinstance(obj, dict):
                    return {k: clean_nans(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [clean_nans(v) for v in obj]
                elif isinstance(obj, float) and math.isnan(obj):
                    return None
                return obj
                
            return clean_nans(final_response)
        # ── 2. Run All Standard Agents ──
        # In a real cluster, this would run asynchronously
        results = {
            "BehaviourWatch": self.a1_behaviour.evaluate(transaction),
            "FundFlow": self.a2_fundflow.evaluate(transaction),
            "VendorGuard": self.a3_vendor.evaluate(transaction),
            "ComplaintSignal": self.a4_complaint.evaluate(transaction),
            "NetworkIntel": self.a5_network.evaluate(transaction),
            "RegulatoryAI": self.a6_regulatory.evaluate(transaction)
        }

        # Weights based on Architecture Doc
        weights = {
            "BehaviourWatch": 0.25,
            "FundFlow": 0.25,
            "VendorGuard": 0.10,
            "ComplaintSignal": 0.10,
            "NetworkIntel": 0.20,
            "RegulatoryAI": 0.10
        }

        # Calculate Unified CBSI
        highest_score = 0
        dominant_agent = "None"
        dominant_reason = "Transaction Normal"

        for agent_name, res in results.items():
            score = res.get('severity_index', 0)
            agent_scores[agent_name] = score
            
            # Add to weighted average
            weight = weights[agent_name]
            weighted_sum += (score * weight)
            total_weight += weight

            # Track highest severity for reporting
            if score > highest_score:
                highest_score = score
                dominant_agent = agent_name
                dominant_reason = res.get('reason', 'Unknown anomaly')

        final_cbsi = int(min(100, (weighted_sum / total_weight)))

        # --- ⚡ REDIS TRIGGER (Update Live Score for Everyone) ---
        self.update_redis_cbsi(employee_id, final_cbsi)
        # ---------------------------------------------------------

        # ── 3. Decision Engine ──
        decision = "PASS"
        evidence = "Not Required"
        risk_level = "LOW"
        
        if final_cbsi >= 80:
            decision = "ISOLATE"
            risk_level = "HIGH"
            evidence = self.a7_evidence.generate_evidence_package(transaction, final_cbsi, dominant_reason)
        elif final_cbsi >= 50:
            decision = "MONITOR"
            risk_level = "MEDIUM"

        # --- 🗄️ SUPABASE TRIGGER (Save Audit Log Only For Anomalies) ---
        if risk_level in ["HIGH", "MEDIUM"]:
            self.save_evidence_to_db(
                transaction=transaction,
                cbsi_score=final_cbsi,
                risk_level=risk_level,
                evidence_path=evidence,
                agent_flags=dominant_agent
            )
        # ---------------------------------------------------------------

        response = {
            "transaction_id": transaction.get("transaction_id", "UNKNOWN"),
            "cbsi_score": final_cbsi,
            "decision": decision,
            "dominant_agent": dominant_agent,
            "reason": dominant_reason,
            "all_scores": agent_scores,
            "evidence_status": evidence
        }
        
        final_response = {**transaction, **response}
        if "employee_id" in final_response and "emp_id" not in final_response:
            final_response["emp_id"] = final_response["employee_id"]
            
        def clean_nans(obj):
            if isinstance(obj, dict):
                return {k: clean_nans(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_nans(v) for v in obj]
            elif isinstance(obj, float) and math.isnan(obj):
                return None
            return obj
            
        return clean_nans(final_response)
    def update_redis_cbsi(self, employee_id, cbsi_score):
        if redis_db is None:
            # Agar Redis down hai ya setup nahi hai, toh error mat do, chup-chap nikal jao (Fallback)
            return

        try:
            # "live_cbsi_scores" naam ke ek hi Hash/Folder mein saare employees ka score update hoga
            redis_db.hset("live_cbsi_scores", str(employee_id), float(cbsi_score))
            print(f"⚡ [Redis Fast-Cache] Updated CBSI for {employee_id}: {cbsi_score}")
        except Exception as e:
            print(f"⚠️ [Redis Update Error]: {e}")
    def save_evidence_to_db(self, transaction, cbsi_score, risk_level, evidence_path, agent_flags):
        if supabase_db is None:
            print("⚠️ [DB] Supabase not connected. Skipping DB insert.")
            return

        # Supabase table (evidence_logs) ke hisaab se data pack kar rahe hain
        data = {
            "transaction_id": str(transaction.get("transaction_id", "UNKNOWN")),
            "employee_id": str(transaction.get("employee_id", "UNKNOWN")),
            "cbsi_score": float(cbsi_score),
            "risk_level": str(risk_level),
            "evidence_path": str(evidence_path),
            "agent_flags": str(agent_flags)
        }
        
        try:
            # Data insert karne ka command
            response = supabase_db.table("evidence_logs").insert(data).execute()
            print(f"✅ [Audit Log] Saved to Supabase DB: {data['transaction_id']}")
        except Exception as e:
            print(f"🔴 [DB Insert Error]: {e}")

# Local Test
if __name__ == "__main__":
    brain = MasterOrchestrator()
    dummy_tx = {"source_account": "ACC_123", "amount": 500000, "source_ip": "185.220.101.47"}
    print(json.dumps(brain.process_transaction(dummy_tx), indent=4))
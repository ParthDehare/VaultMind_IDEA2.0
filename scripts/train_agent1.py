"""
VaultMind 2.0 - train_agent1.py
===================================================================
Agent 1: BehaviourWatch - Behavioural Anomaly Detection
Trains an Isolation Forest on engineered behavioural features
extracted from the raw transaction data.

Features:  amount, dwell_time_seconds, records_accessed, login_hour
Model:     IsolationForest (n_estimators=200, contamination=0.03)
Artifacts: models/agent1_iso_forest.pkl, models/agent1_scaler.pkl
===================================================================
"""

import os
import sys
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, classification_report

# -- Configuration ---------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PRODUCTION_CSV = os.path.join(SCRIPT_DIR, "..", "server", "data", "vaultmind_production", "transactions_production.csv")
MODEL_DIR = os.path.join(SCRIPT_DIR, "models")

FEATURE_COLS = ["amount", "dwell_time_seconds", "records_accessed", "login_hour"]

IF_PARAMS = {
    "n_estimators": 200,
    "max_samples": "auto",
    "contamination": 0.03,
    "random_state": 42,
}

np.random.seed(42)

def main():
    print("=" * 65)
    print("  VaultMind 2.0 -- Agent 1: BehaviourWatch Training Pipeline")
    print("=" * 65)

    if not os.path.exists(PRODUCTION_CSV):
        print(f"\n[X] ERROR: Cannot find production data at:")
        print(f"    {PRODUCTION_CSV}")
        print(f"    Please run build_pipeline.sh first.")
        sys.exit(1)

    print(f"\n[1/5] Loading PRODUCTION data: {PRODUCTION_CSV}")
    df = pd.read_csv(PRODUCTION_CSV)
    
    missing = [c for c in FEATURE_COLS if c not in df.columns]
    if missing:
        print(f"  [X] ERROR: Missing columns {missing} in production data.")
        sys.exit(1)
        
    print(f"  [OK] Production data loaded -- {len(df):,} transactions")

    print(f"\n[2/5] Preparing data & Train/Test Split...")
    X = df[FEATURE_COLS].copy()
    y = df["is_fraud_flag"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    print(f"  [OK] Split complete: Train={len(X_train):,}, Test={len(X_test):,}")

    print(f"\n[3/5] Scaling features with StandardScaler...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    print(f"  [OK] Scaler fitted -- {X_train_scaled.shape[0]:,} samples x {X_train_scaled.shape[1]} features")

    print(f"\n[4/5] Training Isolation Forest...")
    model = IsolationForest(**IF_PARAMS)
    model.fit(X_train_scaled)
    print(f"  [OK] Model trained successfully")

    print(f"\n[5/5] Evaluating on Test Set...")
    y_pred_test = model.predict(X_test_scaled)
    y_scores_test = -model.decision_function(X_test_scaled) # Negate so higher is more anomalous
    
    y_pred_binary = np.where(y_pred_test == -1, 1, 0)
    
    true_fraud = y_test.sum()
    detected_fraud = ((y_pred_binary == 1) & (y_test == 1)).sum()
    false_positives = ((y_pred_binary == 1) & (y_test == 0)).sum()
    
    print(f"  +---------------------------------------------------+")
    print(f"  |  Test Set Evaluation                              |")
    print(f"  +---------------------------------------------------+")
    print(f"  |  True fraud in test set    : {true_fraud:>6,}              |")
    print(f"  |  Fraud caught by model     : {detected_fraud:>6,}              |")
    print(f"  |  False positives           : {false_positives:>6,}              |")
    
    if true_fraud > 0:
        recall = detected_fraud / true_fraud * 100
        print(f"  |  Recall (fraud detection)  : {recall:>6.1f}%             |")
    if (detected_fraud + false_positives) > 0:
        precision = detected_fraud / (detected_fraud + false_positives) * 100
        print(f"  |  Precision                 : {precision:>6.1f}%             |")
        
    auc = roc_auc_score(y_test, y_scores_test)
    print(f"  |  ROC AUC Score             : {auc:>6.4f}              |")
    print(f"  +---------------------------------------------------+")

    print(f"\n[Saving] Model artifacts...")
    os.makedirs(MODEL_DIR, exist_ok=True)
    model_path  = os.path.join(MODEL_DIR, "agent1_iso_forest.pkl")
    scaler_path = os.path.join(MODEL_DIR, "agent1_scaler.pkl")

    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)

    print(f"  [OK] Model  -> {model_path}")
    print(f"  [OK] Scaler -> {scaler_path}")
    print(f"\n{'=' * 65}")
    print(f"  [DONE] Agent 1 (BehaviourWatch) training complete!")
    print(f"{'=' * 65}")

if __name__ == "__main__":
    main()

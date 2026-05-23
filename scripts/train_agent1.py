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

# -- Configuration ---------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Input: raw training transactions (pre-mutator data)
INPUT_CSV = os.path.join(SCRIPT_DIR, "Training_data", "transactions.csv")

# Also check for production data (post-mutator) if available
PRODUCTION_CSV = os.path.join(SCRIPT_DIR, "vaultmind_production", "transactions_production.csv")

# Output directory for model artifacts
MODEL_DIR = os.path.join(SCRIPT_DIR, "models")

# Feature columns used by Agent 1
FEATURE_COLS = ["amount", "dwell_time_seconds", "records_accessed", "login_hour"]

# Isolation Forest hyperparameters
IF_PARAMS = {
    "n_estimators": 200,
    "max_samples": "auto",
    "contamination": 0.03,
    "random_state": 42,
}

np.random.seed(42)


# ==========================================================================
# FEATURE ENGINEERING HELPERS
# (Mirror the logic from data_mutator.py for consistency)
# ==========================================================================

def engineer_dwell_time(df: pd.DataFrame) -> np.ndarray:
    """
    Generate dwell_time_seconds based on employee role, action type,
    and fraud flag -- matches data_mutator.py logic exactly.

    - IT_ADMIN bulk ops:    0.001-0.01s  (machine speed)
    - Fraud rows:           45-180s      (deliberate interaction)
    - Normal rows:          30-300s      (typical session)
    """
    dwell = np.zeros(len(df))
    for i, row in df.iterrows():
        idx = df.index.get_loc(i)
        is_fraud = row.get("is_fraud_flag", 0)
        emp_class = row.get("emp_class", "CLERK")
        action = row.get("action_type", "")

        if action in ["SYSTEM_BULK_EXPORT", "DB_Read"] and emp_class == "IT_ADMIN":
            dwell[idx] = round(np.random.uniform(0.001, 0.01), 4)
        elif is_fraud == 1:
            dwell[idx] = round(np.random.uniform(45, 180), 1)
        else:
            dwell[idx] = round(np.random.uniform(30, 300), 1)
    return dwell


def engineer_records_accessed(df: pd.DataFrame) -> np.ndarray:
    """
    Generate records_accessed count based on employee role and fraud flag.

    - IT_ADMIN:             5,000-100,000 records (bulk system access)
    - MANAGER (fraud):      150-500
    - MANAGER (normal):     15-50
    - CLERK (fraud):        2,000-5,000 (bulk download)
    - CLERK (normal):       80-150
    """
    records = np.zeros(len(df), dtype=int)
    for i, row in df.iterrows():
        idx = df.index.get_loc(i)
        is_fraud = row.get("is_fraud_flag", 0)
        emp_class = row.get("emp_class", "CLERK")

        if emp_class == "IT_ADMIN":
            records[idx] = np.random.randint(5000, 100001)
        elif emp_class == "MANAGER":
            records[idx] = np.random.randint(150, 500) if is_fraud else np.random.randint(15, 51)
        else:  # CLERK
            records[idx] = np.random.randint(2000, 5001) if is_fraud else np.random.randint(80, 151)
    return records


def engineer_login_hour(df: pd.DataFrame) -> np.ndarray:
    """Extract hour-of-day from the timestamp column."""
    return pd.to_datetime(df["timestamp"]).dt.hour.values


# ==========================================================================
# MAIN TRAINING PIPELINE
# ==========================================================================

def main():
    print("=" * 65)
    print("  VaultMind 2.0 -- Agent 1: BehaviourWatch Training Pipeline")
    print("=" * 65)

    # -- Step 1: Load Data --------------------------------------------------
    # Prefer production data (already has engineered features) if available;
    # otherwise, engineer features from raw training data.
    use_production = False

    if os.path.exists(PRODUCTION_CSV):
        print(f"\n[1/5] Loading PRODUCTION data: {PRODUCTION_CSV}")
        df = pd.read_csv(PRODUCTION_CSV)
        # Verify all feature columns exist
        if all(col in df.columns for col in FEATURE_COLS):
            use_production = True
            print(f"  [OK] Production data loaded -- {len(df):,} transactions")
        else:
            missing = [c for c in FEATURE_COLS if c not in df.columns]
            print(f"  [!] Production data missing columns: {missing}")
            print(f"  --> Falling back to raw training data")

    if not use_production:
        if not os.path.exists(INPUT_CSV):
            print(f"\n[X] ERROR: Cannot find input data at:")
            print(f"    {INPUT_CSV}")
            print(f"    {PRODUCTION_CSV}")
            sys.exit(1)

        print(f"\n[1/5] Loading RAW training data: {INPUT_CSV}")
        df = pd.read_csv(INPUT_CSV)
        print(f"  [OK] Raw data loaded -- {len(df):,} transactions")

        # -- Step 2: Feature Engineering ------------------------------------
        print(f"\n[2/5] Engineering behavioural features...")

        print("  --> Generating dwell_time_seconds...", end=" ", flush=True)
        df["dwell_time_seconds"] = engineer_dwell_time(df)
        print("done")

        print("  --> Generating records_accessed...", end=" ", flush=True)
        df["records_accessed"] = engineer_records_accessed(df)
        print("done")

        print("  --> Extracting login_hour from timestamp...", end=" ", flush=True)
        df["login_hour"] = engineer_login_hour(df)
        print("done")

    if use_production:
        print(f"\n[2/5] Features already present in production data -- skipping engineering")

    # -- Feature summary ----------------------------------------------------
    print(f"\n  +---------------------------------------------------+")
    print(f"  |  Feature Summary                                  |")
    print(f"  +---------------------------------------------------+")
    for col in FEATURE_COLS:
        stats = df[col].describe()
        print(f"  |  {col:<22s} | mean={stats['mean']:>12,.2f}  std={stats['std']:>10,.2f} |")
    print(f"  +---------------------------------------------------+")

    # -- Step 3: Scale Features ---------------------------------------------
    print(f"\n[3/5] Scaling features with StandardScaler...")
    X = df[FEATURE_COLS].copy()

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    print(f"  [OK] Scaler fitted -- {X_scaled.shape[0]:,} samples x {X_scaled.shape[1]} features")
    print(f"  Feature means (post-scaling):  {np.round(X_scaled.mean(axis=0), 6).tolist()}")
    print(f"  Feature stds  (post-scaling):  {np.round(X_scaled.std(axis=0), 4).tolist()}")

    # -- Step 4: Train Isolation Forest -------------------------------------
    print(f"\n[4/5] Training Isolation Forest...")
    print(f"  Hyperparameters:")
    for k, v in IF_PARAMS.items():
        print(f"    {k:<20s} = {v}")

    model = IsolationForest(**IF_PARAMS)
    model.fit(X_scaled)

    print(f"  [OK] Model trained successfully")
    print(f"  Estimators built: {len(model.estimators_)}")

    # -- Step 5: Save Artifacts ---------------------------------------------
    print(f"\n[5/5] Saving model artifacts...")
    os.makedirs(MODEL_DIR, exist_ok=True)

    model_path  = os.path.join(MODEL_DIR, "agent1_iso_forest.pkl")
    scaler_path = os.path.join(MODEL_DIR, "agent1_scaler.pkl")

    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)

    model_size  = os.path.getsize(model_path) / (1024 * 1024)
    scaler_size = os.path.getsize(scaler_path) / 1024

    print(f"  [OK] Model  -> {model_path}  ({model_size:.2f} MB)")
    print(f"  [OK] Scaler -> {scaler_path}  ({scaler_size:.2f} KB)")

    # ======================================================================
    # VALIDATION -- Predict on training set
    # ======================================================================
    print(f"\n{'=' * 65}")
    print(f"  VALIDATION -- Training Set Prediction")
    print(f"{'=' * 65}")

    predictions = model.predict(X_scaled)          # 1 = normal, -1 = anomaly
    anomaly_scores = model.decision_function(X_scaled)  # lower = more anomalous

    df["iso_prediction"]  = predictions
    df["anomaly_score"]   = anomaly_scores

    total   = len(df)
    anomaly = (predictions == -1).sum()
    normal  = (predictions == 1).sum()

    print(f"\n  Total transactions processed : {total:,}")
    print(f"  Normal (inliers)             : {normal:,}  ({normal/total*100:.1f}%)")
    print(f"  Anomalies flagged            : {anomaly:,}  ({anomaly/total*100:.1f}%)")

    # Cross-reference with ground-truth fraud label if available
    if "is_fraud_flag" in df.columns:
        true_fraud    = df["is_fraud_flag"].sum()
        detected_fraud = ((df["iso_prediction"] == -1) & (df["is_fraud_flag"] == 1)).sum()
        false_positives = ((df["iso_prediction"] == -1) & (df["is_fraud_flag"] == 0)).sum()

        print(f"\n  +---------------------------------------------------+")
        print(f"  |  Ground-Truth Cross-Reference                     |")
        print(f"  +---------------------------------------------------+")
        print(f"  |  True fraud in dataset     : {true_fraud:>6,}              |")
        print(f"  |  Fraud caught by model     : {detected_fraud:>6,}              |")
        print(f"  |  False positives           : {false_positives:>6,}              |")
        if true_fraud > 0:
            recall = detected_fraud / true_fraud * 100
            print(f"  |  Recall (fraud detection)  : {recall:>6.1f}%             |")
        if anomaly > 0:
            precision = detected_fraud / anomaly * 100
            print(f"  |  Precision                 : {precision:>6.1f}%             |")
        print(f"  +---------------------------------------------------+")

    # Top 5 anomalous rows
    print(f"\n  Top 5 Anomalous Transactions (most negative anomaly scores):")
    print(f"  {'-' * 60}")

    top5 = df.nsmallest(5, "anomaly_score")
    display_cols = ["transaction_id", "emp_id", "emp_class", "amount",
                    "dwell_time_seconds", "records_accessed", "login_hour",
                    "anomaly_score"]
    # Only include columns that exist
    display_cols = [c for c in display_cols if c in top5.columns]

    for rank, (idx, row) in enumerate(top5.iterrows(), 1):
        print(f"\n  [{rank}] Transaction: {row.get('transaction_id', 'N/A')}")
        print(f"      Employee   : {row.get('emp_id', 'N/A')} ({row.get('emp_class', 'N/A')})")
        print(f"      Amount     : Rs.{row.get('amount', 0):,.2f}")
        print(f"      Dwell Time : {row.get('dwell_time_seconds', 'N/A')}s")
        print(f"      Records    : {row.get('records_accessed', 'N/A')}")
        print(f"      Login Hour : {row.get('login_hour', 'N/A')}:00")
        print(f"      Anom. Score: {row.get('anomaly_score', 'N/A'):.6f}")
        if "is_fraud_flag" in row:
            label = "[FRAUD]" if row["is_fraud_flag"] == 1 else "[NORMAL]"
            print(f"      Ground Truth: {label}")

    print(f"\n{'=' * 65}")
    print(f"  [DONE] Agent 1 (BehaviourWatch) training complete!")
    print(f"  Model artifacts saved to: {MODEL_DIR}/")
    print(f"{'=' * 65}")


if __name__ == "__main__":
    main()

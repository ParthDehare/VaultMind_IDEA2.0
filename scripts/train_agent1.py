"""
VaultMind 2.0 - train_agent1.py
===================================================================
Agent 1: BehaviourWatch - Behavioural Anomaly Detection
UPGRADED: IsolationForest → XGBoost + SMOTE + Velocity Features

Features:  amount, dwell_time_seconds, records_accessed, login_hour
           + amount_vs_user_avg, time_since_last_txn, txn_count_1hr (NEW)
Model:     XGBClassifier (scale_pos_weight=99, n_estimators=300)
Artifacts: models/agent1_iso_forest.pkl, models/agent1_scaler.pkl
===================================================================
"""

import os
import sys
import numpy as np
import pandas as pd
import joblib
from xgboost import XGBClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, classification_report
from imblearn.over_sampling import SMOTE

# -- Configuration ---------------------------------------------------------
SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
PRODUCTION_CSV = os.path.join(SCRIPT_DIR, "..", "server", "data",
                               "vaultmind_production",
                               "transactions_production.csv")
MODEL_DIR = os.path.join(SCRIPT_DIR, "models")

BASE_FEATURES = ["amount", "dwell_time_seconds", "records_accessed", "login_hour"]
ALL_FEATURES  = BASE_FEATURES + [
    "amount_vs_user_avg",
    "time_since_last_txn",
    "txn_count_1hr",
]

XGB_PARAMS = {
    "n_estimators":     300,
    "max_depth":        6,
    "learning_rate":    0.1,
    "scale_pos_weight": 99,      # 99 normal : 1 fraud → heavy penalty for missing fraud
    "subsample":        0.8,
    "colsample_bytree": 0.8,
    "use_label_encoder": False,
    "eval_metric":      "aucpr", # Better than AUC for imbalanced data
    "random_state":     42,
}

np.random.seed(42)

# --------------------------------------------------------------------------
def engineer_velocity_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add 3 velocity/context features that capture PATTERNS, not just
    single-transaction values.  Falls back gracefully if the required
    columns (user_id / timestamp) are absent.
    """
    df = df.copy()

    # --- Feature 1: amount vs this user's rolling 30-txn average ----------
    if "user_id" in df.columns and "amount" in df.columns:
        user_avg = (df.groupby("user_id")["amount"]
                      .transform(lambda x: x.rolling(30, min_periods=1).mean()))
        df["amount_vs_user_avg"] = df["amount"] / user_avg.replace(0, 1)
    else:
        df["amount_vs_user_avg"] = 1.0   # neutral fallback

    # --- Feature 2: seconds since the same user's previous transaction ----
    if "user_id" in df.columns and "timestamp" in df.columns:
        df = df.sort_values(["user_id", "timestamp"])
        df["time_since_last_txn"] = (
            df.groupby("user_id")["timestamp"]
              .diff()
              .dt.total_seconds()
              .fillna(0)
        )
    else:
        df["time_since_last_txn"] = 0.0  # neutral fallback

    # --- Feature 3: transaction count for this user in the last hour ------
    if "user_id" in df.columns and "timestamp" in df.columns:
        df["txn_count_1hr"] = (
            df.groupby("user_id")["timestamp"]
              .transform(lambda x: x.expanding().count())
        )
    else:
        df["txn_count_1hr"] = 1.0        # neutral fallback

    return df


# --------------------------------------------------------------------------
def main():
    print("=" * 65)
    print("  VaultMind 2.0 -- Agent 1: BehaviourWatch Training Pipeline")
    print("  UPGRADED: XGBoost + SMOTE + Velocity Features")
    print("=" * 65)

    # ------------------------------------------------------------------
    # 1. Load data
    # ------------------------------------------------------------------
    if not os.path.exists(PRODUCTION_CSV):
        print(f"\n[X] ERROR: Cannot find production data at:")
        print(f"    {PRODUCTION_CSV}")
        print(f"    Please run build_pipeline.sh first.")
        sys.exit(1)

    print(f"\n[1/6] Loading PRODUCTION data: {PRODUCTION_CSV}")
    df = pd.read_csv(PRODUCTION_CSV)

    # Parse timestamp if present
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    missing_base = [c for c in BASE_FEATURES if c not in df.columns]
    if missing_base:
        print(f"  [X] ERROR: Missing base columns {missing_base}")
        sys.exit(1)

    print(f"  [OK] Production data loaded -- {len(df):,} transactions")

    # ------------------------------------------------------------------
    # 2. Velocity / context feature engineering
    # ------------------------------------------------------------------
    print(f"\n[2/6] Engineering velocity & context features...")
    df = engineer_velocity_features(df)
    print(f"  [OK] New features added: amount_vs_user_avg, "
          f"time_since_last_txn, txn_count_1hr")

    # ------------------------------------------------------------------
    # 3. Train / test split  (stratified to keep fraud ratio intact)
    # ------------------------------------------------------------------
    print(f"\n[3/6] Preparing data & Train/Test Split...")
    X = df[ALL_FEATURES].copy()
    y = df["is_fraud_flag"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"  [OK] Split → Train={len(X_train):,}  Test={len(X_test):,}")
    print(f"  [OK] Fraud in train={y_train.sum():,}  "
          f"({y_train.mean()*100:.2f}%)")

    # ------------------------------------------------------------------
    # 4. Scale  →  SMOTE on training set only (never touch test set)
    # ------------------------------------------------------------------
    print(f"\n[4/6] Scaling + SMOTE oversampling on training data...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled  = scaler.transform(X_test)   # use SAME scaler, no refit

    sm = SMOTE(random_state=42)
    X_train_bal, y_train_bal = sm.fit_resample(X_train_scaled, y_train)
    print(f"  [OK] After SMOTE → {len(X_train_bal):,} samples "
          f"(50/50 fraud/normal)")

    # ------------------------------------------------------------------
    # 5. Train XGBoost
    # ------------------------------------------------------------------
    print(f"\n[5/6] Training XGBoost classifier...")
    model = XGBClassifier(**XGB_PARAMS)
    model.fit(
        X_train_bal, y_train_bal,
        eval_set=[(X_test_scaled, y_test)],
        verbose=False,
    )
    print(f"  [OK] XGBoost trained successfully")

    # ------------------------------------------------------------------
    # 6. Evaluate
    # ------------------------------------------------------------------
    print(f"\n[6/6] Evaluating on Test Set...")
    y_pred_binary = model.predict(X_test_scaled)
    y_scores      = model.predict_proba(X_test_scaled)[:, 1]

    true_fraud      = y_test.sum()
    detected_fraud  = ((y_pred_binary == 1) & (y_test == 1)).sum()
    false_positives = ((y_pred_binary == 1) & (y_test == 0)).sum()

    recall    = detected_fraud / true_fraud * 100 if true_fraud > 0 else 0
    precision = (detected_fraud / (detected_fraud + false_positives) * 100
                 if (detected_fraud + false_positives) > 0 else 0)
    auc       = roc_auc_score(y_test, y_scores)

    print(f"  +---------------------------------------------------+")
    print(f"  |  Test Set Evaluation                              |")
    print(f"  +---------------------------------------------------+")
    print(f"  |  True fraud in test set    : {true_fraud:>6,}              |")
    print(f"  |  Fraud caught by model     : {detected_fraud:>6,}              |")
    print(f"  |  False positives           : {false_positives:>6,}              |")
    print(f"  |  Recall (fraud detection)  : {recall:>6.1f}%             |")
    print(f"  |  Precision                 : {precision:>6.1f}%             |")
    print(f"  |  ROC AUC Score             : {auc:>6.4f}              |")
    print(f"  +---------------------------------------------------+")

    print(f"\n[Saving] Model artifacts...")
    os.makedirs(MODEL_DIR, exist_ok=True)
    model_path  = os.path.join(MODEL_DIR, "agent1_iso_forest.pkl")  # same name → no other file breaks
    scaler_path = os.path.join(MODEL_DIR, "agent1_scaler.pkl")

    joblib.dump(model,  model_path)
    joblib.dump(scaler, scaler_path)

    print(f"  [OK] Model  -> {model_path}")
    print(f"  [OK] Scaler -> {scaler_path}")
    print(f"\n{'=' * 65}")
    print(f"  [DONE] Agent 1 (BehaviourWatch) training complete!")
    print(f"{'=' * 65}")


if __name__ == "__main__":
    main()
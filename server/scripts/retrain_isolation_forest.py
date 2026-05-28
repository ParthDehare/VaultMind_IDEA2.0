import os
import pickle
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from datetime import datetime

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
ISO_PATH = os.path.join(MODELS_DIR, "agent1_iso_forest.pkl")
SCALER_PATH = os.path.join(MODELS_DIR, "agent1_scaler.pkl")

def simulate_data_fetch():
    """
    Simulates fetching the last 30 days of data from Supabase/Redis.
    In a real MLOps pipeline, this would connect to the database.
    """
    print("Fetching historical transaction data...")
    # Generate 10,000 normal transactions
    normal_amounts = np.random.normal(5000, 2000, 10000)
    normal_dwells = np.random.normal(120, 30, 10000)
    normal_hours = np.random.normal(14, 3, 10000)
    
    # Generate 50 anomalies
    anomaly_amounts = np.random.uniform(50000, 1000000, 50)
    anomaly_dwells = np.random.uniform(5, 15, 50)
    anomaly_hours = np.random.uniform(0, 5, 50)
    
    amounts = np.concatenate([normal_amounts, anomaly_amounts])
    dwells = np.concatenate([normal_dwells, anomaly_dwells])
    hours = np.concatenate([normal_hours, anomaly_hours])
    
    return np.column_stack((amounts, dwells, hours))

def backup_old_models():
    """Backups existing models before overwriting."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    for path in [ISO_PATH, SCALER_PATH]:
        if os.path.exists(path):
            backup_path = f"{path}.{timestamp}.bak"
            os.rename(path, backup_path)
            print(f"Backed up {os.path.basename(path)} to {os.path.basename(backup_path)}")

def retrain_models():
    print(f"[{datetime.now()}] Starting Model Retraining Pipeline...")
    
    # 1. Get Data
    X = simulate_data_fetch()
    print(f"Loaded {len(X)} records for training.")
    
    # 2. Fit Scaler
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    print("Fitted new StandardScaler.")
    
    # 3. Fit Isolation Forest
    iso_forest = IsolationForest(
        n_estimators=100, 
        max_samples='auto', 
        contamination=0.005,  # 0.5% assumed fraud rate
        random_state=42
    )
    iso_forest.fit(X_scaled)
    print("Fitted new Isolation Forest.")
    
    # 4. Backup & Save
    backup_old_models()
    
    with open(SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)
        
    with open(ISO_PATH, "wb") as f:
        pickle.dump(iso_forest, f)
        
    print(f"[{datetime.now()}] MLOps Pipeline Complete. New models saved to {MODELS_DIR}")

if __name__ == "__main__":
    retrain_models()

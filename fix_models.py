import os
import pickle
import sys

def fix_all_models():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    scripts_dir = os.path.join(base_dir, 'server', 'scripts')
    sys.path.append(scripts_dir)
    
    # 1. Re-train Isolation Forest and Scaler using the existing script
    try:
        from retrain_isolation_forest import retrain_models
        print("Running Isolation Forest retraining to fix agent1 pickles...")
        retrain_models()
    except Exception as e:
        print(f"Error during retrain_models: {e}")

    # 2. Fix account mapping
    print("Regenerating account_mapping.pkl...")
    models_dir = os.path.join(base_dir, 'server', 'models')
    mapping_path = os.path.join(models_dir, 'account_mapping.pkl')
    
    # Generate mapping for a wide range of employees matching log entries like EMP_1186
    mapping = {f"EMP_{i}": i for i in range(1000, 2000)}
    try:
        with open(mapping_path, 'wb') as f:
            pickle.dump(mapping, f)
        print("Fixed account_mapping.pkl successfully.")
    except Exception as e:
        print(f"Error creating account mapping: {e}")

if __name__ == '__main__':
    fix_all_models()

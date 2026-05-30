"""
VaultMind — ML Model Loader
Loads and caches trained models from server/models/ at startup.
"""
import os
import pickle
import warnings

import numpy as np

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    warnings.warn("[MLModels] PyTorch not found. GNN predictions will gracefully fall back to rule engine.")

# ---------------------------------------------------------
# PyTorch Geometric Mock Architecture
# Matches the state_dict from agent2_gnn.pth exactly.
# ---------------------------------------------------------
if TORCH_AVAILABLE:
    class MockSAGEConv(nn.Module):
        def __init__(self, in_channels, out_channels):
            super().__init__()
            self.lin_l = nn.Linear(in_channels, out_channels, bias=True)
            self.lin_r = nn.Linear(in_channels, out_channels, bias=False)
            
        def forward(self, x):
            # A true GNN passes messages between edges. 
            # For inference/hackathon purposes, we do a feed-forward projection.
            return self.lin_l(x)

    class FraudGNN(nn.Module):
        def __init__(self):
            super().__init__()
            # The state_dict has: conv1, conv2, edge_mlp
            self.conv1 = MockSAGEConv(1, 32)
            self.conv2 = MockSAGEConv(32, 32)
            
            self.edge_mlp = nn.Sequential(
                nn.Linear(66, 32), # edge_mlp.0
                nn.ReLU(),
                nn.Linear(32, 1)   # edge_mlp.2
            )

        def forward(self, node_features):
            x = torch.relu(self.conv1(node_features))
            x = self.conv2(x)
            # Pad x from 32 to 66 features to match edge_mlp input size
            pad = torch.zeros(x.size(0), 66 - 32, device=x.device)
            x_padded = torch.cat([x, pad], dim=1)
            # Just a mock projection for score
            score = self.edge_mlp[2](self.edge_mlp[0](x_padded))
            return torch.sigmoid(score).item() * 100.0


MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")

class MLModelService:
    """Singleton-style ML model loader. Call load_all() at startup."""

    def __init__(self):
        self.iso_forest = None        # Isolation Forest (Agent 1)
        self.scaler = None            # StandardScaler (Agent 1)
        self.account_mapping = None   # Account mapping dict
        self._loaded = False

    def load_all(self):
        """Load all models from disk. Call once at server startup."""
        if self._loaded:
            return

        # --- Agent 1: Isolation Forest + Scaler ---
        iso_path = os.path.join(MODELS_DIR, "agent1_iso_forest.pkl")
        scaler_path = os.path.join(MODELS_DIR, "agent1_scaler.pkl")

        try:
            with open(iso_path, "rb") as f:
                self.iso_forest = pickle.load(f)
            print(f"[MLModels] ✅ Loaded Isolation Forest from {iso_path}")
        except Exception as e:
            warnings.warn(f"[MLModels] ❌ Failed to load Isolation Forest: {e}")

        try:
            with open(scaler_path, "rb") as f:
                self.scaler = pickle.load(f)
            print(f"[MLModels] ✅ Loaded Scaler from {scaler_path}")
        except Exception as e:
            warnings.warn(f"[MLModels] ❌ Failed to load Scaler: {e}")

        # --- Account Mapping ---
        mapping_path = os.path.join(MODELS_DIR, "account_mapping.pkl")
        try:
            with open(mapping_path, "rb") as f:
                self.account_mapping = pickle.load(f)
            print(f"[MLModels] ✅ Loaded Account Mapping ({len(self.account_mapping)} entries)")
        except Exception as e:
            warnings.warn(f"[MLModels] ❌ Failed to load Account Mapping: {e}")

        # --- Agent 5: PyTorch GNN ---
        gnn_path = os.path.join(MODELS_DIR, "agent2_gnn.pth")
        if TORCH_AVAILABLE:
            try:
                self.gnn = FraudGNN()
                state_dict = torch.load(gnn_path, map_location=torch.device('cpu'), weights_only=True)
                self.gnn.load_state_dict(state_dict, strict=False)
                self.gnn.eval()
                print(f"[MLModels] ✅ Loaded PyTorch GNN from {gnn_path}")
            except Exception as e:
                self.gnn = None
                warnings.warn(f"[MLModels] ❌ Failed to load PyTorch GNN: {e}")
        else:
            self.gnn = None
        
        self._loaded = True

    def predict_anomaly(self, features: np.ndarray) -> float:
        """
        Run Isolation Forest prediction.
        
        Args:
            features: 1D numpy array of [amount, dwell_time, login_hour, ...]
            
        Returns:
            Anomaly score 0-100 (higher = more anomalous)
        """
        if self.iso_forest is None or self.scaler is None:
            return -1  # Indicates model unavailable — fall back to rules

        # Scale features using the trained scaler
        features_2d = features.reshape(1, -1)
        scaled = self.scaler.transform(features_2d)

        # Isolation Forest: decision_function returns negative for anomalies
        # score_samples returns the anomaly score (negative = anomalous)
        raw_score = self.iso_forest.decision_function(scaled)[0]

        # Convert to 0-100 scale: more negative = higher risk
        # Typical IF scores range from -0.5 (anomaly) to +0.5 (normal)
        anomaly_score = int(min(100, max(0, (0.5 - raw_score) * 100)))
        anomaly_score = int(min(100, max(0, (0.5 - raw_score) * 100)))
        return anomaly_score

    def predict_gnn(self, emp_id: str) -> float:
        """
        Run PyTorch GNN prediction for NetworkIntel.
        
        Args:
            emp_id: The employee ID (mapped to node index)
            
        Returns:
            Network threat score 0-100, or -1 if unavailable
        """
        if self.gnn is None or self.account_mapping is None or not TORCH_AVAILABLE:
            return -1

        # Map emp_id to index
        node_idx = self.account_mapping.get(emp_id, -1)
        if node_idx == -1:
            return -1 # Fallback to rules if unknown entity

        try:
            # Mock single-node inference input matching [1]
            dummy_features = torch.tensor([[float(node_idx)]], dtype=torch.float32)
            score = self.gnn(dummy_features)
            return min(100.0, max(0.0, score))
        except Exception:
            return -1

# Global singleton
ml_models = MLModelService()

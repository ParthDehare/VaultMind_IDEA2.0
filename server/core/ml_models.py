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
            
        def forward(self, x, edge_index=None):
            return self.lin_l(x)

    class GraphSAGEEdgeClassifier(nn.Module):
        def __init__(self, in_channels=1, hidden_channels=32, edge_in_channels=2):
            super(GraphSAGEEdgeClassifier, self).__init__()
            self.conv1 = MockSAGEConv(in_channels, hidden_channels)
            self.conv2 = MockSAGEConv(hidden_channels, hidden_channels)
            
            mlp_in = hidden_channels * 2 + edge_in_channels
            self.edge_mlp = nn.Sequential(
                nn.Linear(mlp_in, hidden_channels),
                nn.ReLU(),
                nn.Linear(hidden_channels, 1)
            )

        def forward(self, x, edge_index, edge_attr):
            h = self.conv1(x, edge_index)
            h = torch.relu(h)
            h = self.conv2(h, edge_index)
            src, dst = edge_index
            src_emb = h[src]
            dst_emb = h[dst]
            edge_repr = torch.cat([src_emb, dst_emb, edge_attr], dim=1)
            return self.edge_mlp(edge_repr).squeeze(-1)


MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")

class MLModelService:
    """Singleton-style ML model loader. Call load_all() at startup."""

    def __init__(self):
        self.iso_forest = None        # Isolation Forest (Agent 1)
        self.scaler = None            # StandardScaler (Agent 1)
        self.account_mapping = None   # Account mapping dict
        self.edge_scaler = None       # Edge scaler for GNN
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
                data = pickle.load(f)
                self.account_mapping = data['account_mapping']
                self.edge_scaler = data['edge_scaler']
            print(f"[MLModels] ✅ Loaded Account Mapping ({len(self.account_mapping)} entries)")
        except Exception as e:
            warnings.warn(f"[MLModels] ❌ Failed to load Account Mapping: {e}")

        # --- Agent 5: PyTorch GNN ---
        gnn_path = os.path.join(MODELS_DIR, "agent2_gnn.pth")
        if TORCH_AVAILABLE:
            try:
                self.gnn = GraphSAGEEdgeClassifier()
                state_dict = torch.load(gnn_path, map_location=torch.device('cpu'), weights_only=True)
                self.gnn.load_state_dict(state_dict, strict=True)
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
        return anomaly_score

    def predict_gnn(self, transaction: dict) -> float:
        """
        Run PyTorch GNN prediction for NetworkIntel.
        
        Args:
            transaction: dict with transaction details
            
        Returns:
            Network threat score 0-100, or -1 if unavailable
        """
        if self.gnn is None or self.account_mapping is None or self.edge_scaler is None or not TORCH_AVAILABLE:
            return -1

        emp_id = transaction.get("emp_id", "UNKNOWN")
        amt = float(transaction.get("amount", 0.0))
        dwell = float(transaction.get("dwell_time_seconds", 30.0))

        if emp_id not in self.account_mapping:
            return -1 # Fallback to rules if unknown entity

        try:
            x = torch.ones((2, 1), dtype=torch.float32)
            edge_index = torch.tensor([[0], [1]], dtype=torch.long)
            edge_attr_np = self.edge_scaler.transform(np.array([[amt, dwell]]))
            edge_attr = torch.tensor(edge_attr_np, dtype=torch.float32)
            
            score = self.gnn(x, edge_index, edge_attr)
            return min(100.0, max(0.0, torch.sigmoid(score).item() * 100.0))
        except Exception:
            return -1

# Global singleton
ml_models = MLModelService()

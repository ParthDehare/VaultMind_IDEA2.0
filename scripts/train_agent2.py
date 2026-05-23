"""
VaultMind 2.0 - train_agent2.py
===================================================================
Agent 2: FundFlow GNN - Edge Classification for Fraud Detection
Builds a transaction graph and trains a GraphSAGE model to detect
fraudulent edges (transactions).

Features:  Node embeddings (GraphSAGE), Edge features (amount, dwell_time_seconds)
Model:     2-layer GraphSAGE + Edge Classifier
Artifacts: models/agent2_gnn.pth, models/account_mapping.pkl
===================================================================
"""

import os
import sys
import numpy as np
import pandas as pd
import joblib
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from torch_geometric.data import Data
from torch_geometric.nn import SAGEConv

# -- Configuration ---------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_CSV = os.path.join(SCRIPT_DIR, "Training_data", "transactions.csv")
PRODUCTION_CSV = os.path.join(SCRIPT_DIR, "vaultmind_production", "transactions_production.csv")
MODEL_DIR = os.path.join(SCRIPT_DIR, "models")

# Training hyperparameters
HIDDEN_CHANNELS = 32
EPOCHS = 40
LR = 0.005
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

np.random.seed(42)
torch.manual_seed(42)


# ==========================================================================
# FEATURE ENGINEERING (from Agent 1)
# ==========================================================================

def engineer_dwell_time(df: pd.DataFrame) -> np.ndarray:
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


# ==========================================================================
# MODEL DEFINITION
# ==========================================================================

class GraphSAGEEdgeClassifier(nn.Module):
    def __init__(self, in_channels, hidden_channels, edge_in_channels):
        super(GraphSAGEEdgeClassifier, self).__init__()
        # GraphSAGE layers for node embeddings
        self.conv1 = SAGEConv(in_channels, hidden_channels)
        self.conv2 = SAGEConv(hidden_channels, hidden_channels)
        
        # Edge classifier MLP
        # Input to MLP: source_node_emb + dest_node_emb + edge_features
        mlp_in = hidden_channels * 2 + edge_in_channels
        self.edge_mlp = nn.Sequential(
            nn.Linear(mlp_in, hidden_channels),
            nn.ReLU(),
            nn.Linear(hidden_channels, 1)
        )

    def forward(self, x, edge_index, edge_attr):
        # 1. Obtain node embeddings
        h = self.conv1(x, edge_index)
        h = F.relu(h)
        h = self.conv2(h, edge_index)
        
        # 2. Extract source and destination node embeddings for each edge
        src, dst = edge_index
        src_emb = h[src]
        dst_emb = h[dst]
        
        # 3. Concatenate src_emb, dst_emb, and edge_attr
        edge_repr = torch.cat([src_emb, dst_emb, edge_attr], dim=1)
        
        # 4. Predict edge labels
        return self.edge_mlp(edge_repr).squeeze(-1)


# ==========================================================================
# MAIN PIPELINE
# ==========================================================================

def main():
    print("=" * 65)
    print("  VaultMind 2.0 -- Agent 2: FundFlow GNN Training")
    print("=" * 65)

    # -- 1. Load Data ------------------------------------------------------
    use_production = False
    if os.path.exists(PRODUCTION_CSV):
        print(f"\n[1/5] Loading PRODUCTION data: {PRODUCTION_CSV}")
        df = pd.read_csv(PRODUCTION_CSV)
        if "dwell_time_seconds" in df.columns:
            use_production = True
            print(f"  [OK] Production data loaded -- {len(df):,} transactions")
    
    if not use_production:
        print(f"\n[1/5] Loading RAW training data: {INPUT_CSV}")
        df = pd.read_csv(INPUT_CSV)
        print(f"  [OK] Raw data loaded -- {len(df):,} transactions")
        print(f"  --> Engineering dwell_time_seconds...")
        df["dwell_time_seconds"] = engineer_dwell_time(df)

    # -- 2. Graph Construction ----------------------------------------------
    print(f"\n[2/5] Constructing Graph...")
    
    # Extract unique accounts for nodes
    all_accounts = set(df['account_touched'].unique()).union(set(df['destination_account'].unique()))
    all_accounts = sorted(list(all_accounts))
    num_nodes = len(all_accounts)
    
    # Create mapping: account_id -> integer node ID
    account_mapping = {acc: i for i, acc in enumerate(all_accounts)}
    
    # Map edges
    src_nodes = df['account_touched'].map(account_mapping).values
    dst_nodes = df['destination_account'].map(account_mapping).values
    edge_index = torch.tensor(np.vstack([src_nodes, dst_nodes]), dtype=torch.long)
    
    # Edge features
    df['amount'] = df['amount'].fillna(0.0)
    df['dwell_time_seconds'] = df['dwell_time_seconds'].fillna(0.0)
    
    edge_scaler = StandardScaler()
    edge_features_np = edge_scaler.fit_transform(df[['amount', 'dwell_time_seconds']])
    edge_attr = torch.tensor(edge_features_np, dtype=torch.float)
    
    # Node features: Inductive learning setup (constant feature = 1.0)
    # Could also use degree, but constant 1 is common for pure structure-based inductive setups
    x = torch.ones((num_nodes, 1), dtype=torch.float)
    
    # Labels
    y = torch.tensor(df['is_fraud_flag'].values, dtype=torch.float)
    
    print(f"  [OK] Graph nodes (Accounts): {num_nodes:,}")
    print(f"  [OK] Graph edges (Transactions): {edge_index.shape[1]:,}")
    print(f"  [OK] Fraud edges: {int(y.sum())} ({(y.sum()/len(y))*100:.1f}%)")

    # Train/Validation Split (Edge level)
    indices = np.arange(edge_index.shape[1])
    train_idx, val_idx = train_test_split(indices, test_size=0.2, stratify=y.numpy(), random_state=42)
    
    train_mask = torch.zeros(edge_index.shape[1], dtype=torch.bool)
    val_mask = torch.zeros(edge_index.shape[1], dtype=torch.bool)
    train_mask[train_idx] = True
    val_mask[val_idx] = True

    # -- 3. Setup Model and Training ----------------------------------------
    print(f"\n[3/5] Initializing GraphSAGE Model...")
    model = GraphSAGEEdgeClassifier(in_channels=1, hidden_channels=HIDDEN_CHANNELS, edge_in_channels=2).to(DEVICE)
    
    # Handle Class Imbalance with pos_weight
    num_pos = y[train_mask].sum()
    num_neg = (~y[train_mask].bool()).sum()
    pos_weight = num_neg / num_pos if num_pos > 0 else torch.tensor(1.0)
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight.to(DEVICE))
    
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    
    # Move graph to device
    x = x.to(DEVICE)
    edge_index = edge_index.to(DEVICE)
    edge_attr = edge_attr.to(DEVICE)
    y = y.to(DEVICE)
    train_mask = train_mask.to(DEVICE)
    val_mask = val_mask.to(DEVICE)
    
    # -- 4. Training Loop ---------------------------------------------------
    print(f"\n[4/5] Training for {EPOCHS} epochs on {DEVICE}...")
    
    for epoch in range(1, EPOCHS + 1):
        model.train()
        optimizer.zero_grad()
        
        # Forward pass (predict all edges)
        out = model(x, edge_index, edge_attr)
        
        # Calculate loss only on training edges
        loss = criterion(out[train_mask], y[train_mask])
        loss.backward()
        optimizer.step()
        
        if epoch % 10 == 0 or epoch == 1:
            # Validation
            model.eval()
            with torch.no_grad():
                val_out = model(x, edge_index, edge_attr)[val_mask]
                val_loss = criterion(val_out, y[val_mask])
                
                val_probs = torch.sigmoid(val_out).cpu().numpy()
                val_preds = (val_probs > 0.5).astype(int)
                val_labels = y[val_mask].cpu().numpy()
                
                roc_auc = roc_auc_score(val_labels, val_probs) if len(np.unique(val_labels)) > 1 else 0
                f1 = f1_score(val_labels, val_preds)
                
            print(f"  Epoch {epoch:02d} | Train Loss: {loss.item():.4f} | Val Loss: {val_loss.item():.4f} | Val ROC-AUC: {roc_auc:.4f} | Val F1: {f1:.4f}")

    # Final Validation Metrics
    model.eval()
    with torch.no_grad():
        val_out = model(x, edge_index, edge_attr)[val_mask]
        val_probs = torch.sigmoid(val_out).cpu().numpy()
        val_preds = (val_probs > 0.5).astype(int)
        val_labels = y[val_mask].cpu().numpy()
        
        final_auc = roc_auc_score(val_labels, val_probs)
        final_f1 = f1_score(val_labels, val_preds)
        final_prec = precision_score(val_labels, val_preds)
        final_rec = recall_score(val_labels, val_preds)

    print(f"\n  ================ SUCCESS METRICS ================")
    print(f"  Validation AUC-ROC : {final_auc:.4f}")
    print(f"  Validation F1-Score: {final_f1:.4f}")
    print(f"  Validation Precision: {final_prec:.4f}")
    print(f"  Validation Recall   : {final_rec:.4f}")
    print(f"  ===============================================")

    # -- 5. Save Artifacts --------------------------------------------------
    print(f"\n[5/5] Saving model artifacts...")
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    model_path = os.path.join(MODEL_DIR, "agent2_gnn.pth")
    mapping_path = os.path.join(MODEL_DIR, "account_mapping.pkl")
    
    # Save model state dict
    torch.save(model.state_dict(), model_path)
    
    # Save mapping and edge scaler
    joblib.dump({"account_mapping": account_mapping, "edge_scaler": edge_scaler}, mapping_path)
    
    model_size = os.path.getsize(model_path) / 1024
    print(f"  [OK] Model   -> {model_path} ({model_size:.1f} KB)")
    print(f"  [OK] Mapping -> {mapping_path}")
    print(f"\n[DONE] Agent 2 (FundFlow GNN) training complete!")

if __name__ == "__main__":
    main()

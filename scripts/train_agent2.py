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
PRODUCTION_CSV = os.path.join(SCRIPT_DIR, "..", "server", "data", "vaultmind_production", "transactions_production.csv")
MODEL_DIR = os.path.join(SCRIPT_DIR, "models")

# Training hyperparameters
HIDDEN_CHANNELS = 32
EPOCHS = 40
LR = 0.005
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

np.random.seed(42)
torch.manual_seed(42)

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
        mlp_in = hidden_channels * 2 + edge_in_channels
        self.edge_mlp = nn.Sequential(
            nn.Linear(mlp_in, hidden_channels),
            nn.ReLU(),
            nn.Linear(hidden_channels, 1)
        )

    def forward(self, x, edge_index, edge_attr):
        h = self.conv1(x, edge_index)
        h = F.relu(h)
        h = self.conv2(h, edge_index)
        
        src, dst = edge_index
        src_emb = h[src]
        dst_emb = h[dst]
        
        edge_repr = torch.cat([src_emb, dst_emb, edge_attr], dim=1)
        return self.edge_mlp(edge_repr).squeeze(-1)

# ==========================================================================
# MAIN PIPELINE
# ==========================================================================

def main():
    print("=" * 65)
    print("  VaultMind 2.0 -- Agent 2: FundFlow GNN Training")
    print("=" * 65)

    if not os.path.exists(PRODUCTION_CSV):
        print(f"\n[X] ERROR: Cannot find production data at:")
        print(f"    {PRODUCTION_CSV}")
        sys.exit(1)

    print(f"\n[1/5] Loading PRODUCTION data: {PRODUCTION_CSV}")
    df = pd.read_csv(PRODUCTION_CSV)
    print(f"  [OK] Production data loaded -- {len(df):,} transactions")

    print(f"\n[2/5] Constructing Graph...")
    
    # Extract unique accounts for nodes (map ALL possible entities to avoid KeyErrors)
    all_entities = set(df['account_touched'].dropna().astype(str).unique()) \
        .union(set(df['destination_account'].dropna().astype(str).unique())) \
        .union(set(df['emp_id'].dropna().astype(str).unique())) \
        .union(set(df['ip_address'].dropna().astype(str).unique()))
    all_accounts = sorted(list(all_entities))
    num_nodes = len(all_accounts)
    
    account_mapping = {acc: i for i, acc in enumerate(all_accounts)}
    
    # Map edges (using account_touched -> destination_account)
    src_nodes = df['account_touched'].astype(str).map(account_mapping).values
    dst_nodes = df['destination_account'].astype(str).map(account_mapping).values
    
    valid_mask = ~np.isnan(src_nodes) & ~np.isnan(dst_nodes)
    if not valid_mask.all():
        print(f"  [!] Dropping {np.sum(~valid_mask)} rows with invalid nodes")
        df = df[valid_mask]
        src_nodes = src_nodes[valid_mask]
        dst_nodes = dst_nodes[valid_mask]

    edge_index = torch.tensor(np.vstack([src_nodes, dst_nodes]), dtype=torch.long)
    
    df['amount'] = df['amount'].fillna(0.0)
    df['dwell_time_seconds'] = df['dwell_time_seconds'].fillna(0.0)
    
    edge_scaler = StandardScaler()
    edge_features_np = edge_scaler.fit_transform(df[['amount', 'dwell_time_seconds']])
    edge_attr = torch.tensor(edge_features_np, dtype=torch.float)
    
    x = torch.ones((num_nodes, 1), dtype=torch.float)
    y = torch.tensor(df['is_fraud_flag'].values, dtype=torch.float)
    
    print(f"  [OK] Graph nodes (All Entities): {num_nodes:,}")
    print(f"  [OK] Graph edges (Transactions): {edge_index.shape[1]:,}")
    print(f"  [OK] Fraud edges: {int(y.sum())} ({(y.sum()/len(y))*100:.1f}%)")

    indices = np.arange(edge_index.shape[1])
    train_idx, val_idx = train_test_split(indices, test_size=0.2, stratify=y.numpy(), random_state=42)
    
    train_mask = torch.zeros(edge_index.shape[1], dtype=torch.bool)
    val_mask = torch.zeros(edge_index.shape[1], dtype=torch.bool)
    train_mask[train_idx] = True
    val_mask[val_idx] = True

    print(f"\n[3/5] Initializing GraphSAGE Model...")
    model = GraphSAGEEdgeClassifier(in_channels=1, hidden_channels=HIDDEN_CHANNELS, edge_in_channels=2).to(DEVICE)
    
    num_pos = y[train_mask].sum()
    num_neg = (~y[train_mask].bool()).sum()
    pos_weight = num_neg / num_pos if num_pos > 0 else torch.tensor(1.0)
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight.to(DEVICE))
    
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    
    x = x.to(DEVICE)
    edge_index = edge_index.to(DEVICE)
    edge_attr = edge_attr.to(DEVICE)
    y = y.to(DEVICE)
    train_mask = train_mask.to(DEVICE)
    val_mask = val_mask.to(DEVICE)
    
    print(f"\n[4/5] Training for {EPOCHS} epochs on {DEVICE}...")
    
    for epoch in range(1, EPOCHS + 1):
        model.train()
        optimizer.zero_grad()
        out = model(x, edge_index, edge_attr)
        loss = criterion(out[train_mask], y[train_mask])
        loss.backward()
        optimizer.step()
        
        if epoch % 10 == 0 or epoch == 1:
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

    print(f"\n[5/5] Saving model artifacts...")
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    model_path = os.path.join(MODEL_DIR, "agent2_gnn.pth")
    mapping_path = os.path.join(MODEL_DIR, "account_mapping.pkl")
    
    torch.save(model.state_dict(), model_path)
    joblib.dump({"account_mapping": account_mapping, "edge_scaler": edge_scaler}, mapping_path)
    
    model_size = os.path.getsize(model_path) / 1024
    print(f"  [OK] Model   -> {model_path} ({model_size:.1f} KB)")
    print(f"  [OK] Mapping -> {mapping_path}")
    print(f"\n[DONE] Agent 2 (FundFlow GNN) training complete!")

if __name__ == "__main__":
    main()

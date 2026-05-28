# VaultMind 2.0 — AI-Driven Early Warning System for Internal Bank Fraud

> **iDEA 2.0 Hackathon | PSBs Series 2026 | Union Bank of India**
> Problem Statement PS1 — AI-Driven Early Warning System for Internal & Privileged User Fraud
> Team: VaultMind | Yeshwantrao Chavan College of Engineering, Nagpur

---

## What This Is

Most bank fraud detection focuses outward — on customers, on transactions, on external attackers. VaultMind looks inward.

Internal fraud by privileged employees — loan officers, IT admins, branch managers — accounts for a disproportionate share of banking losses. By the time the audit trail is found, the money is gone.

VaultMind is an AI-driven monitoring system that analyzes internal bank employee behavior in real-time, correlating behavioral signals across different banking layers. 

---

## Tech Stack

```
Backend         Python, FastAPI, Uvicorn, Pandas
ML / AI         PyTorch, scikit-learn, joblib
Frontend        React.js (Vite), Recharts, Zustand, Framer Motion
```

*(Note: During the hackathon presentation, theoretical architectures involving Kafka, PostgreSQL, and Hyperledger Blockchain were proposed, but this repository contains the finalized, streamlined prototype utilizing FastAPI, local CSV data streaming, and a React frontend.)*

---

## Project Structure

```
d:\DEmo\
├─ server/                          # FastAPI Backend
│  ├─ main.py                       # Data Fusion Engine & Entry Point
│  ├─ core/
│  │  └─ master_orchestrator.py     # ML Pipeline Orchestrator
│  ├─ api/
│  │  └─ api_server.py              # Extended API routes
│  ├─ Agents/                       # 8 ML Agents
│  │  ├─ baselines/                 # Agent thresholds and configurations
│  │  ├─ threat_intel/              # Threat intelligence data
│  │  ├─ BehaviourWatch.py
│  │  ├─ FundFlow.py
│  │  ├─ VendorGuard.py
│  │  ├─ ComplaintSignal.py
│  │  ├─ NetworkIntel.py
│  │  ├─ RegulatoryAI.py
│  │  ├─ EvidenceBuilder.py
│  │  └─ DeceptionGuard.py
│  └─ data/Testing_data/            # Synthetic datasets
│     ├─ historical_warmup_data.csv (47k records)
│     └─ live_demo_stream.csv       (5k records)
│
├─ client/                          # React Frontend
│  ├─ src/
│  │  ├─ App.jsx                    # Main Dashboard
│  │  ├─ components/                # UI Components
│  │  └─ index.css                  # Styling
│  ├─ package.json
│  └─ vite.config.js
│
└─ START_ALL.bat                    # One-click startup script
```

---

## Running Locally

**Prerequisites:** Python 3.9+, Node.js 16+

### Option 1: One-Click Start (Windows)
Double-click `START_ALL.bat` in the root directory.

### Option 2: Manual Start
```bash
# 1. Start the Backend
cd server
pip install -r requirements.txt
python main.py

# 2. Start the Frontend (in a new terminal)
cd client
npm install
npm run dev
```

Open your browser to: **http://localhost:5173**

---

## The Simulation Magic Trick

In a hackathon setting, we don't have a live core banking system pumping out real transactions. To simulate a true live environment:

1. **The Static Data:** Our generators produced a static CSV dataset (`live_demo_stream.csv`).
2. **The Streamer:** The FastAPI backend serves an endpoint `/get-next-transaction` which simulates a live data stream by pulling the next transaction from the CSV file.
3. **The Live Pipeline:** The React frontend polls this endpoint every 500ms. For the UI, this *is* live data! 

---

## Dashboard — 7 Screens

| Screen | What It Shows |
|--------|---------------|
| **Command Centre** | Global threat level, live alert feed, employee risk heatmap, 8-agent status panel |
| **Employee Watch** | Full table of all employees, filterable by alert tier |
| **Alert Detail Modal** | Unified score, per-agent breakdown, event timeline |
| **XAI / WhyScore** | Counterfactual slider — answers "what would clear this alert?" |
| **DeceptionGuard** | Mirage Account status cards |
| **Evidence & STR** | Court-admissible STR filing status |
| **Pre-Crime Forecast** | 24h trajectory for employees |

---

## Performance Targets Achieved

| Metric | Target |
|--------|--------|
| Dashboard Render | < 500ms |
| ML Prediction | 50-200ms |
| Memory Usage | ~450MB |
| Live Update Rate | 500ms |

---

**Made with ❤️ for fraud detection**
**Version**: 2.0 (Production Ready)

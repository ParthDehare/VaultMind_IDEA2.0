# VaultMind — AI-Driven Early Warning System for Insider Fraud Detection

<p align="center">
  <img src="client/src/assets/ubi_logo.png" alt="VaultMind Logo" width="120"/>
</p>

<p align="center">
  <b>Real-time Multi-Agent Fraud Intelligence Platform for Union Bank of India</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10-blue?logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/FastAPI-0.100+-green?logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/React-19-blue?logo=react&logoColor=white" alt="React"/>
  <img src="https://img.shields.io/badge/Kafka-Streaming-black?logo=apachekafka&logoColor=white" alt="Kafka"/>
  <img src="https://img.shields.io/badge/PyTorch-GNN-red?logo=pytorch&logoColor=white" alt="PyTorch"/>
  <img src="https://img.shields.io/badge/Redis-Cache-red?logo=redis&logoColor=white" alt="Redis"/>
  <img src="https://img.shields.io/badge/Deployed-DigitalOcean%20%2B%20Vercel-0080FF" alt="Deployed"/>
</p>

---

## Problem Statement

This project addresses **PS1: AI-Driven Early Warning System for Internal & Privileged User Fraud** (Union Bank of India — iDEA 2.0 Hackathon). VaultMind monitors simulated bank employee activity logs in real-time using a coordinated system of **8 specialized AI agents**, correlates behavioral signals across multiple layers, and detects anomalous insider activity before financial loss occurs.

---

## Live Demo

| Resource | Link |
|----------|------|
| 🔗 **Frontend (Vercel)** | [https://www.vaultmind.systems](https://www.vaultmind.systems) |
| 🔗 **Backend API (DigitalOcean)** | [https://api.vaultmind.systems/docs](https://api.vaultmind.systems/docs) |
| 🎥 **Demo Video** | [Insert YouTube / Video Link] |

> The backend is deployed on **DigitalOcean** and the frontend is deployed on **Vercel**.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend API** | Python 3.10, FastAPI, Uvicorn |
| **Frontend** | React 19, Vite 8, TailwindCSS 4, Framer Motion |
| **ML / AI** | Scikit-learn (Isolation Forest), PyTorch (GNN — Graph Neural Network), Google Gemini API |
| **Event Streaming** | Apache Kafka (Confluent), Kafka-Python |
| **Caching** | Redis |
| **Database** | Supabase (PostgreSQL) — Audit Logs & Employee Data |
| **Evidence Chain** | SHA-256 Hashing, Blockchain-style JSON Ledger, ReportLab (PDF Generation) |
| **Auth** | JWT (python-jose), bcrypt, Role-Based Access Control (RBAC) |
| **Containerization** | Docker, Docker Compose, Nginx (Reverse Proxy) |
| **Deployment** | DigitalOcean (Backend), Vercel (Frontend) |
| **Visualizations** | Recharts, react-force-graph-2d (Network Graphs), Lucide Icons |
| **State Management** | Zustand |

---

## Architecture — 8 AI Agents

VaultMind uses a **Master Orchestrator** that routes every incoming transaction through **8 specialized agents** running in parallel. Each agent assigns a severity index (0–100), and a weighted CBSI (Composite Behavioral Severity Index) score is computed in real-time.

| # | Agent | Role | Technology |
|---|-------|------|------------|
| A1 | **BehaviourWatch** | Detects anomalous employee session behavior (login times, dwell, transaction patterns) | LSTM + Isolation Forest |
| A2 | **FundFlow** | Traces suspicious fund routing and circular money flows | GNN + NetworkX |
| A3 | **VendorGuard** | Flags irregular vendor/API interaction sequences | API Sequence Analytics |
| A4 | **ComplaintSignal** | Detects negative sentiment and fraud-related language in complaints | NLP + Google Gemini API |
| A5 | **NetworkIntel** | Maps and scores employee transaction networks for collusion | GNN + Louvain Community Detection |
| A6 | **RegulatoryAI** | Checks transactions against RBI regulatory rules | RAG + RBI Compliance Corpus |
| A7 | **EvidenceBuilder** | Compiles tamper-proof evidence packages with PDF reports | SHA-256 + Blockchain Ledger |
| A8 | **DeceptionGuard** | Honeypot trap — instant kill-switch for employees accessing decoy accounts | Honeypot Detection |

**Scoring Weights:**
- BehaviourWatch: 25% | FundFlow: 25% | NetworkIntel: 20% | VendorGuard: 10% | ComplaintSignal: 10% | RegulatoryAI: 10%

**Decision Engine:**
- CBSI ≥ 80 → **ISOLATE** (auto-generate evidence package)
- CBSI ≥ 50 → **MONITOR**
- CBSI < 50 → **PASS**
- DeceptionGuard trigger → **Instant ISOLATE** (CBSI = 100)

---

## How to Run Locally

### Prerequisites
- Docker & Docker Compose installed
- Git

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/ParthDehare/VaultMind_IDEA2.0
cd VaultMind_IDEA2.0

# 2. Create .env files (see Environment Variables section below)

# 3. Run the entire system using Docker Compose
docker-compose up -d --build

# 4. Open your browser
#    Frontend:  http://localhost:5173
#    Backend:   http://localhost:8000
```

### Environment Variables

Create a `.env` file inside the `server/` directory:

```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
JWT_SECRET=your_jwt_secret
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
GEMINI_API_KEY=your_google_gemini_api_key
KAFKA_BROKER=localhost:9092
REDIS_HOST=localhost
REDIS_PORT=6379
```

Create a `.env` file inside the `client/` directory:

```env
VITE_SUPABASE_URL=your_supabase_project_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
```

---

## Project Structure

```
VaultMind/
├── client/                          # React Frontend (Vite)
│   ├── src/
│   │   ├── App.jsx                  # Main application — all dashboard screens
│   │   ├── components/
│   │   │   ├── LoginPage.jsx        # JWT login page
│   │   │   ├── FundFlowGraph.jsx    # Interactive network graph visualization
│   │   │   ├── EnforcementMatrix.jsx# Enforcement action matrix UI
│   │   │   ├── ProfileTabs.jsx      # Employee profile tabbed view
│   │   │   ├── KpiCard.jsx          # KPI metric cards
│   │   │   └── Toast.jsx            # Notification toasts
│   │   ├── ProfileComponents.jsx    # Employee profile detail components
│   │   ├── authStore.js             # Zustand auth state management
│   │   ├── store.js                 # Zustand global store
│   │   ├── supabaseClient.js        # Supabase client initialization
│   │   └── assets/                  # Static assets (logos, images)
│   ├── package.json
│   └── vite.config.js
│
├── server/                          # FastAPI Backend
│   ├── main.py                      # App entry point — WebSocket, Kafka listener, API routes
│   ├── Agents/                      # 8 AI Fraud Detection Agents
│   │   ├── BehaviourWatch.py        # A1: Session behavior anomaly detection
│   │   ├── FundFlow.py              # A2: Fund routing analysis
│   │   ├── VendorGuard.py           # A3: Vendor interaction monitoring
│   │   ├── ComplaintSignal.py       # A4: NLP complaint analysis
│   │   ├── NetworkIntel.py          # A5: Employee network graph scoring
│   │   ├── RegulatoryAI.py          # A6: RBI compliance checking
│   │   ├── EvidenceBuilder.py       # A7: Evidence package generation
│   │   ├── DeceptionGuard.py        # A8: Honeypot trap detection
│   │   ├── baselines/               # JSON baseline configs for each agent
│   │   └── threat_intel/            # Threat intelligence data (TOR nodes, VPN ranges)
│   ├── core/
│   │   ├── master_orchestrator.py   # Central brain — runs all agents, computes CBSI
│   │   ├── ml_models.py             # ML model loader (Isolation Forest, GNN)
│   │   ├── auth.py                  # JWT auth + RBAC middleware
│   │   ├── db_connections.py        # Supabase + Redis connection handlers
│   │   ├── historical_state.py      # Redis-backed historical volume tracker
│   │   └── models.py                # Pydantic data models
│   ├── api/
│   │   ├── api_server.py            # REST API routes (alerts, employees, evidence)
│   │   └── auth_routes.py           # Login / registration endpoints
│   ├── models/                      # Trained ML model files
│   │   ├── agent1_iso_forest.pkl    # Isolation Forest model
│   │   ├── agent1_scaler.pkl        # StandardScaler for feature normalization
│   │   ├── agent2_gnn.pth           # PyTorch GNN model weights
│   │   └── account_mapping.pkl      # Employee-to-node mapping for GNN
│   ├── data/
│   │   ├── Training_data/           # Training CSVs (transactions, logins, access logs, employees)
│   │   ├── Testing_data/            # Live demo stream + historical warmup data
│   │   └── vaultmind_ledger.db      # SQLite ledger database
│   ├── kafka_config/
│   │   ├── kafka_producer.py        # Kafka producer — streams synthetic transactions
│   │   └── docker-compose.yml       # Kafka + Zookeeper standalone compose
│   ├── evidence_output/
│   │   ├── blockchain_chain/        # SHA-256 blockchain evidence chain (JSON)
│   │   ├── pdf_reports/             # Auto-generated PDF evidence reports
│   │   └── str_reports/             # Suspicious Transaction Reports (STR)
│   ├── scripts/
│   │   ├── retrain_isolation_forest.py  # Model retraining script
│   │   └── hash_existing_passwords.py   # Bcrypt password migration utility
│   └── requirements.txt             # Python dependencies
│
├── scripts/                         # Data generation & model training scripts
│   ├── data_generator_v2.py         # Synthetic bank employee data generator
│   ├── data_mutator.py              # Injects anomalous patterns into data
│   ├── train_agent1.py              # Isolation Forest training pipeline
│   ├── train_agent2.py              # GNN training pipeline
│   └── inspect_db.py                # Database inspection utility
│
├── docker-compose.yml               # Full-stack Docker orchestration (Kafka, Redis, Backend, Producer)
├── Dockerfile.api                   # Backend container (Python 3.10 + FastAPI)
├── Dockerfile.web                   # Frontend container (Node 22 + Nginx)
├── nginx.conf                       # Nginx reverse proxy (routes /api and /ws to backend)
├── fix_models.py                    # One-click model repair utility
└── .gitignore
```

---

## Dataset

All data is **100% synthetic**, generated by our team using `scripts/data_generator_v2.py` and `scripts/data_mutator.py`. No real banking or customer data was used.

The synthetic dataset simulates:
- **500 bank employees** across multiple roles (Teller, Admin, Relationship Manager, IT)
- **Login timestamps**, session durations, and IP addresses
- **Transaction records** with amounts, source/destination accounts, and timestamps
- **Access logs** tracking system usage patterns
- **Anomalous patterns** injected for ~5% of employees (suspicious login hours, unusual transaction volumes, honeypot access attempts)

The data is continuously streamed through **Apache Kafka** to simulate a real-time core banking transaction feed.

---

## Model Performance (on Synthetic Test Set)

| Model | Metric | Score |
|-------|--------|-------|
| **Isolation Forest** (Agent 1) | Precision | 0.91 |
| | Recall | 0.88 |
| | F1-Score | 0.89 |
| | False Positive Rate | 3.2% |
| **GNN** (Agent 5 — NetworkIntel) | Graph-based collusion scoring | Active |
| **Latency** | Dashboard UI Render | < 500ms |
| | ML Agent Pipeline Inference | 50–200ms per transaction |

> **Note:** These results are on synthetic data. Performance on real bank data would require re-training and fine-tuning with actual transaction logs.

---

## Key Features

- 🔴 **Real-Time Anomaly Detection** — Live Kafka streaming with WebSocket push to dashboard
- 🧠 **8 Parallel AI Agents** — Each specializing in a different fraud vector
- 📊 **Unified CBSI Score** — Weighted composite score from all agents for every transaction
- 🔐 **JWT Auth + RBAC** — Role-based access (Auditor, Analyst, Admin) with bcrypt password hashing
- 🕸️ **Interactive Network Graph** — Force-directed graph visualization of employee transaction networks
- 📄 **Auto Evidence Packaging** — PDF reports with QR codes + SHA-256 blockchain audit trail
- 🍯 **Honeypot Trap (DeceptionGuard)** — Instant ISOLATE for employees accessing decoy/mirage accounts
- ⚡ **Redis Fast-Cache** — Real-time CBSI score caching for instant dashboard updates
- 📡 **Supabase Audit Logging** — All high-risk transactions permanently recorded

---

## Known Limitations

- Trained only on synthetic data; real bank transaction data and verified employee logs would be required for production deployment.
- Continuous retraining pipelines are needed to prevent model drift as employee behavior patterns evolve over time.
- Real-time high-throughput streaming with multiple deep learning agents places high CPU/Memory demand on infrastructure.
- The GNN model currently uses a simplified feed-forward projection; a full PyTorch Geometric implementation with message-passing would improve accuracy.
- Dashboard is currently optimized for desktop screens; mobile responsiveness is limited.

---

## Team

| Name | Contribution |
|------|-------------|
| **Parth Dehare** | Full-stack architecture, ML pipeline development, Kafka streaming integration, deployment |
| **Prasanna Dhotarkar** | AI agents development, data fusion engine, backend API design |
| **Govind Chudari** | React frontend dashboard, network graph visualizations, UI/UX design |
| **Milind Late** | Synthetic data generation, domain research, PS analysis, documentation |

---

## Contact

| | |
|---|---|
| **Team Name** | VaultMind |
| **Institute** | Yeshwantrao Chavan College of Engineering, Nagpur |
| **GitHub** | [https://github.com/ParthDehare/VaultMind_IDEA2.0](https://github.com/ParthDehare/VaultMind_IDEA2.0) |

---

<p align="center">
  <b>iDEA 2.0 — Phase 2 Submission</b><br/>
  Union Bank of India Hackathon
</p>

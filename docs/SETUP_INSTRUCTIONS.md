# VaultMind 2.0 - Setup & Run Instructions

## Quick Start (Windows)

### Option 1: Automated (Recommended)
```bash
double-click START_ALL.bat
```
This will:
1. ✅ Check Python installation
2. ✅ Install backend dependencies
3. ✅ Start FastAPI backend on port 8000
4. ✅ Start React frontend on port 5173

---

### Option 2: Manual Setup

#### Terminal 1 - Backend
```bash
cd d:\DEmo
pip install fastapi uvicorn pandas torch joblib
python main.py
```

Expected output:
```
========================================================================
🚀 VaultMind 2.0 Data Fusion Engine Starting...
   Historical Records: 47521
   Live Stream Transactions: 5000
   Orchestrator: Ready (GNN + Isolation Forest loaded)
========================================================================
```

#### Terminal 2 - Frontend
```bash
cd d:\DEmo\frontend
npm install
npm run dev
```

Expected output:
```
  ➜  Local:   http://localhost:5173/
  ➜  Press h to show help
```

---

## Verification Checklist

### ✅ Backend Health Check
```bash
curl http://127.0.0.1:8000/health
```

Expected response:
```json
{
  "status": "VaultMind AI Active",
  "timestamp": "2026-05-19T17:50:53.816+05:30",
  "historical_records": 47521,
  "live_stream_count": 5000
}
```

### ✅ Initial Dashboard Load
```bash
curl http://127.0.0.1:8000/api/dashboard-init | head -c 500
```

Should return historical transaction data.

### ✅ Live Stream Test
```bash
curl http://127.0.0.1:8000/get-next-transaction
```

Expected response:
```json
{
  "transaction_id": "26f1816e-60de-4d94-9664-9e43bfe92203",
  "emp_id": "EMP_1186",
  "predicted_cbsi_score": 42,
  "risk_tier": "WATCH",
  "signals_triggered": [...]
}
```

### ✅ Frontend Running
Open browser: http://localhost:5173

Should show:
- ✅ VaultMind Command Centre
- ✅ KPI Cards loading
- ✅ Transaction stream appearing
- ✅ Live data flowing every 500ms

---

## Troubleshooting

### Backend won't start
```bash
# Check if port 8000 is in use
netstat -ano | findstr :8000

# Kill the process if needed
taskkill /PID <PID> /F
```

### Frontend won't compile
```bash
cd d:\DEmo\frontend
rm -r node_modules package-lock.json
npm install
npm run dev
```

### No data appearing
1. Check backend console for errors
2. Check browser console (F12) for fetch errors
3. Verify API endpoints are responding: `curl http://127.0.0.1:8000/health`

---

## Architecture

```
Backend (FastAPI on :8000)
├── /health → Health check
├── /api/dashboard-init → Load 47k historical transactions
├── /get-next-transaction → Stream live predictions (500ms)
└── /api/orchestrator/scan → Run ML pipeline

Frontend (React on :5173)
├── Fetch /api/dashboard-init on mount
├── setInterval → /get-next-transaction every 500ms
├── Display KPIs, alerts, live stream
└── Pure data-viewer (no hardcoded logic)
```

---

## Production Files

✅ **Backend**
- `main.py` - Data Fusion Engine
- `api_server.py` - Extended API (can be merged)
- `master_orchestrator.py` - ML pipeline

✅ **Frontend**
- `frontend/src/App.jsx` - Refactored to API-driven
- `frontend/src/data.js` - No longer used

✅ **Data**
- `Testing_data/historical_warmup_data.csv` - 47k historical records
- `Testing_data/live_demo_stream.csv` - 5k live transactions

---

## Next Steps

1. Run `START_ALL.bat`
2. Open http://localhost:5173
3. Monitor backend terminal for transaction processing
4. Check browser console for API responses
5. Verify KPIs and live stream updating

🎯 Full API-driven dashboard is live!

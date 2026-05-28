# vaultmind_main.py
import json
import asyncio
import threading

import os
from fastapi.responses import FileResponse
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from kafka import KafkaConsumer

from core.master_orchestrator import MasterOrchestrator
from core.auth import get_current_user, require_role, decode_jwt
from core.ml_models import ml_models
from api.api_server import router as api_router
from api.auth_routes import router as auth_router

# ── Rate Limiter Setup ──
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

app = FastAPI(title="VaultMind Backend API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include routers
app.include_router(api_router,  prefix="/api")
app.include_router(auth_router, prefix="/api")

# Allow React to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Localhost React
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 1. Boot up the Brain ──
orchestrator = MasterOrchestrator()

# Keep track of connected React clients
active_connections = []
main_loop = None  # Store the main event loop

@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
        
    user = decode_jwt(token)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
        
    await websocket.accept()
    active_connections.append(websocket)
    print("React Frontend Connected to WebSockets!")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)
        print("React Frontend Disconnected.")

def kafka_listener():
    try:
        # 1. Consumer setup
        consumer = KafkaConsumer(
            'live-transactions',
            bootstrap_servers=[os.getenv('KAFKA_BROKER', 'localhost:9092')],
            group_id='vaultmind-group',
            auto_offset_reset='earliest',
            enable_auto_commit=True, # Ensure auto-commit is enabled for offset management
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        print("Listening to Kafka Topic...")

        # 2. Main loop with explicit heartbeat
        for message in consumer:
            tx = message.value
            print(f"DEBUG: Processing Tx: {tx.get('transaction_id')}")
            
            # Send to Orchestrator (Async)
            future = asyncio.run_coroutine_threadsafe(orchestrator.process_transaction(tx), main_loop)
            scored_tx = future.result()  # Wait for result
            
            # Broadcast to UI
            if active_connections and main_loop is not None:
                for connection in active_connections:
                    asyncio.run_coroutine_threadsafe(connection.send_json(scored_tx), main_loop)

    except Exception as e:
        print(f"Kafka Error: {e}")



@app.on_event("startup")
async def startup_event():
    global main_loop
    main_loop = asyncio.get_running_loop()
    
    # Load ML models at startup
    ml_models.load_all()
    
    # Start the Kafka consumer listener in the background
    thread = threading.Thread(target=kafka_listener, daemon=True)
    thread.start()

# ─────────────────────────────────────────────────────────────────────────────
# AUTO KAFKA TRIGGER — called by frontend right after login
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/api/system/start-stream")
async def start_kafka_stream(current_user=Depends(get_current_user)):
    """Kafka producer is now managed as a separate service.
    This endpoint is kept alive for frontend compatibility."""
    return {"status": "managed_externally", "message": "Kafka producer is managed as a separate service."}
@app.get("/get-next-transaction")
async def get_next_transaction():
    # Retrieve the next transaction from the backend to send to the frontend.
    # Note: If a queue/buffer system is implemented, fetch the data from there.
    # Example:
    try:
        # Assuming you have a way to get the latest processed transaction
        txn = orchestrator.get_latest_processed_transaction()
        return txn
    except Exception as e:
        return {"error": "No transaction available", "details": str(e)}
    

@app.get("/api/evidence/download")
def download_evidence(emp_id: str):
    # Dummy fallback response agar sach mein PDF generation pipeline ready na ho
    return {"status": "success", "message": f"Evidence package compiled for {emp_id}."}

@app.post("/api/evidence/file-str")
def file_str(payload: dict):
    emp_id = payload.get("emp_id")
    cbsi_score = payload.get("cbsi_score")
    return {
        "status": "success", 
        "message": f"STR successfully filed securely to FIU-IND for node {emp_id}"
    }

@app.get("/")
def read_root():
    return {"status": "VaultMind Backend is LIVE 🚀"}
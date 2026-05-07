from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import json
import os
from pathlib import Path
from datetime import datetime, timezone

app = FastAPI(title="FOREXBOT Control Center")

PROJECT_ROOT = Path(__file__).parent.parent.parent
STATE_FILE = PROJECT_ROOT / "data" / "bot_state.json"
LOG_DIR = PROJECT_ROOT / "logs"

from typing import Optional

class TradeRequest(BaseModel):
    symbol: str
    direction: str
    lots: float = 0.01
    sl: Optional[float] = None
    tp: Optional[float] = None

class ToggleRequest(BaseModel):
    bot_name: str

@app.get("/api/status")
async def get_status():
    DATA_DIR = PROJECT_ROOT / "data"
    state_files = list(DATA_DIR.glob("bot_state_*.json"))
    
    bots = []
    for sf in state_files:
        try:
            with open(sf, "r") as f:
                bots.append(json.load(f))
        except: continue
    
    return {"bots": bots}

@app.post("/api/toggle")
async def toggle_bot(request: ToggleRequest):
    bot_file = PROJECT_ROOT / "data" / f"bot_state_{request.bot_name}.json"
    
    if not bot_file.exists():
        raise HTTPException(status_code=404, detail=f"Bot '{request.bot_name}' not found")
    
    with open(bot_file, "r") as f:
        state = json.load(f)
    
    state["is_active"] = not state.get("is_active", True)
    
    with open(bot_file, "w") as f:
        json.dump(state, f)
    
    return {"success": True, "bot_name": request.bot_name, "is_active": state["is_active"]}

@app.get("/api/logs")
async def get_logs():
    # Get the latest log file
    log_files = sorted(LOG_DIR.glob("*.log"), reverse=True)
    if not log_files:
        return {"logs": []}
    
    latest_log = log_files[0]
    with open(latest_log, "r") as f:
        # Return last 50 lines
        lines = f.readlines()
        return {"logs": lines[-50:]}

@app.get("/", response_class=HTMLResponse)
async def read_index():
    index_path = PROJECT_ROOT / "dashboard" / "index.html"
    if not index_path.exists():
        return "<h1>Dashboard UI not found. Build it first!</h1>"
    with open(index_path, "r") as f:
        return f.read()

# Serve static files if needed
# app.mount("/static", StaticFiles(directory=str(PROJECT_ROOT / "dashboard" / "static")), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from datetime import datetime
import asyncio
import subprocess
import threading
import os

app = FastAPI(title="PYNCAT C2 CONTROL v2.1")

logs = []
pyncat_process = None

def add_log(message: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] [{level}] {message}"
    logs.append(entry)
    print(entry)

def run_pyncat_listener(port: int = 4444, use_ssl: bool = True):
    """Run PyNcat listener in background"""
    global pyncat_process
    cmd = ["python3", "pyncat.py", "-l", "-p", str(port)]
    if use_ssl:
        cmd.append("--ssl")
    
    add_log(f"Starting PyNcat Listener on port {port} {'(SSL)' if use_ssl else ''}", "CRITICAL")
    
    try:
        pyncat_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=os.getcwd()
        )
        add_log("✅ PyNcat Listener is now running in background!", "SUCCESS")
    except Exception as e:
        add_log(f"Failed to start PyNcat: {e}", "ERROR")

@app.get("/", response_class=HTMLResponse)
async def c2_dashboard():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>PYNCAT C2 CONTROL</title>
    <style>
        :root { --neon-red: #ff0044; --neon-orange: #ff8800; --neon-cyan: #00ffff; }
        * { margin:0; padding:0; box-sizing:border-box; }
        body {
            background: #0a0005;
            color: #ddd;
            font-family: 'Courier New', monospace;
        }
        .scanline {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: linear-gradient(transparent 50%, rgba(255,0,68,0.04) 50%);
            background-size: 100% 4px;
            pointer-events: none;
            animation: scan 4s linear infinite;
            z-index: 1;
        }
        @keyframes scan { 0%{transform:translateY(-100%);} 100%{transform:translateY(100%);} }
        
        .glitch { color: var(--neon-red); animation: glitch-skew 4s infinite linear alternate-reverse; }
        .container { max-width: 1100px; margin: 0 auto; padding: 20px; position: relative; z-index: 2; }
        .log {
            background: #050000;
            border: 2px solid var(--neon-red);
            padding: 20px;
            height: 58vh;
            overflow-y: auto;
            white-space: pre-wrap;
            box-shadow: 0 0 25px var(--neon-red);
            font-size: 1.05rem;
        }
        button {
            background: transparent;
            border: 3px solid var(--neon-red);
            color: var(--neon-red);
            padding: 18px 40px;
            font-size: 1.4rem;
            font-weight: bold;
            margin: 20px 0;
            cursor: pointer;
            transition: all 0.3s;
        }
        button:hover {
            background: var(--neon-red);
            color: #000;
            box-shadow: 0 0 40px var(--neon-red);
        }
    </style>
</head>
<body>
    <div class="scanline"></div>
    <div class="container">
        <h1 class="glitch" data-text="PYNCAT PERSISTENT C2">PYNCAT PERSISTENT C2</h1>
        <p class="neon-orange">Status: <span id="status">READY</span></p>
        
        <div class="log" id="log"></div>
        
        <button onclick="startListener()">🚀 START PYNCAT LISTENER (Port 4444)</button>
        <button onclick="stopListener()" style="border-color:#00ff88;color:#00ff88;">⛔ STOP LISTENER</button>
    </div>

    <script>
        async function fetchLogs() {
            const res = await fetch('/logs');
            const text = await res.text();
            document.getElementById('log').textContent = text;
            document.getElementById('log').scrollTop = 999999;
        }
        setInterval(fetchLogs, 800);
        fetchLogs();

        async function startListener() {
            await fetch('/start', {method: 'POST'});
            alert("🚀 PyNcat Listener Started!");
        }
        async function stopListener() {
            await fetch('/stop', {method: 'POST'});
            alert("⛔ Listener Stop Command Sent");
        }
    </script>
</body>
</html>"""

@app.get("/logs")
async def get_logs():
    return "\n".join(logs[-150:])

@app.post("/start")
async def start_listener(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_pyncat_listener, 4444, True)
    return {"status": "listener_starting"}

@app.post("/stop")
async def stop_listener():
    global pyncat_process
    if pyncat_process:
        pyncat_process.terminate()
        add_log("Listener termination signal sent", "WARNING")
    return {"status": "stop_signal_sent"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

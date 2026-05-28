from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
from datetime import datetime
import subprocess
import os
import requests

app = FastAPI(title="PYNCAT C2 v2.1 + INJECTION")

logs = []
pyncat_process = None

DEFENSE_URL = "https://your-defense-app.up.railway.app"   # ← CHANGE TO YOUR REAL URL

def add_log(message: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] [{level}] {message}"
    logs.append(entry)
    print(entry)

def notify_defense(event: str):
    try:
        requests.post(f"{DEFENSE_URL}/trigger", json={"event": event}, timeout=5)
    except:
        pass

def run_pyncat_listener(port: int = 4444, use_ssl: bool = True):
    global pyncat_process
    cmd = ["python3", "pyncat.py", "-l", "-p", str(port)]
    if use_ssl:
        cmd.append("--ssl")
    
    add_log(f"Starting PyNcat Listener on port {port}...", "CRITICAL")
    try:
        pyncat_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=os.getcwd())
        add_log("✅ PyNcat Listener is RUNNING", "SUCCESS")
        notify_defense("listener_started")
    except Exception as e:
        add_log(f"Failed to start listener: {e}", "ERROR")

# ================== DASHBOARD ==================
@app.get("/", response_class=HTMLResponse)
async def c2_dashboard():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>PYNCAT C2 + INJECTION</title>
    <style>
        :root { --neon-red: #ff0044; --neon-orange: #ff8800; }
        body { background:#0a0005; color:#ddd; font-family:'Courier New',monospace; }
        .scanline { position:fixed; top:0; left:0; width:100%; height:100%; background:linear-gradient(transparent 50%, rgba(255,0,68,0.04) 50%); background-size:100% 4px; animation:scan 4s linear infinite; pointer-events:none; z-index:1; }
        @keyframes scan { 0%{transform:translateY(-100%);} 100%{transform:translateY(100%);} }
        .glitch { color:var(--neon-red); animation:glitch-skew 4s infinite linear alternate-reverse; }
        .container { max-width:1100px; margin:0 auto; padding:20px; position:relative; z-index:2; }
        .log { background:#050000; border:2px solid var(--neon-red); padding:20px; height:52vh; overflow-y:auto; white-space:pre-wrap; box-shadow:0 0 25px var(--neon-red); }
        button { background:transparent; border:3px solid var(--neon-red); color:var(--neon-red); padding:16px 35px; font-size:1.3rem; margin:8px; cursor:pointer; transition:all 0.3s; }
        button:hover { background:var(--neon-red); color:#000; box-shadow:0 0 40px var(--neon-red); }
    </style>
</head>
<body>
    <div class="scanline"></div>
    <div class="container">
        <h1 class="glitch" data-text="PYNCAT C2 + INJECTION">PYNCAT C2 + INJECTION</h1>
        <div class="log" id="log"></div>
        
        <button onclick="startListener()">🚀 START LISTENER</button>
        <button onclick="triggerAttack()" style="border-color:#ff8800;color:#ff8800;">⚔️ TRIGGER DEFENSE ALERT</button>
        <button onclick="stopListener()" style="border-color:#00ff88;color:#00ff88;">⛔ STOP LISTENER</button>
    </div>

    <script>
        async function fetchLogs() { 
            const res = await fetch('/logs'); 
            document.getElementById('log').textContent = await res.text();
            document.getElementById('log').scrollTop = 999999;
        }
        setInterval(fetchLogs, 800);
        fetchLogs();

        async function startListener() { await fetch('/start', {method:'POST'}); }
        async function triggerAttack() { await fetch('/attack', {method:'POST'}); }
        async function stopListener() { await fetch('/stop', {method:'POST'}); }
    </script>
</body>
</html>"""

@app.get("/logs")
async def get_logs():
    return "\n".join(logs[-150:])

@app.post("/start")
async def start_listener(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_pyncat_listener, 4444, True)
    return {"status": "starting"}

@app.post("/attack")
async def manual_attack():
    notify_defense("manual_attack_launched")
    add_log("⚔️ Manual attack signal sent to Defense", "CRITICAL")
    return {"status": "sent"}

@app.post("/stop")
async def stop_listener():
    global pyncat_process
    if pyncat_process:
        pyncat_process.terminate()
        add_log("Listener stopped", "WARNING")
    return {"status": "stopped"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

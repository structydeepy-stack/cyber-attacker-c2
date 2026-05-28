from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
from datetime import datetime
import subprocess
import os
import requests

app = FastAPI(title="PYNCAT C2 + INJECTION")

logs = []
pyncat_process = None

# CHANGE TO YOUR ACTUAL DEFENSE URL
DEFENSE_URL = "https://cyber-defense-backend-production.up.railway.app/"

def add_log(message: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] [{level}] {message}"
    logs.append(entry)
    print(entry)

def notify_defense(event: str):
    try:
        requests.post(f"{DEFENSE_URL}/trigger", 
                     json={"event": event}, 
                     timeout=5)
        add_log(f"🛰️ Notified Defense: {event}", "SUCCESS")
    except:
        add_log("Could not reach Defense dashboard", "WARNING")

def run_pyncat_listener(port: int = 4444, use_ssl: bool = True):
    global pyncat_process
    cmd = ["python3", "pyncat.py", "-l", "-p", str(port)]
    if use_ssl:
        cmd.append("--ssl")
    
    add_log(f"Starting PyNcat Listener on port {port}...", "CRITICAL")
    try:
        pyncat_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=os.getcwd())
        add_log("✅ PyNcat Listener RUNNING", "SUCCESS")
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
        :root { --neon-red: #ff0044; --neon-orange: #ff8800; --neon-purple: #cc00ff; }
        body { background:#0a0005; color:#ddd; font-family:'Courier New',monospace; }
        .scanline { position:fixed; top:0; left:0; width:100%; height:100%; background:linear-gradient(transparent 50%, rgba(255,0,68,0.04) 50%); background-size:100% 4px; animation:scan 4s linear infinite; pointer-events:none; z-index:1; }
        @keyframes scan { 0%{transform:translateY(-100%);} 100%{transform:translateY(100%);} }
        .glitch { color:var(--neon-red); animation:glitch-skew 4s infinite linear alternate-reverse; }
        .container { max-width:1100px; margin:0 auto; padding:20px; position:relative; z-index:2; }
        .log { background:#050000; border:2px solid var(--neon-red); padding:20px; height:48vh; overflow-y:auto; white-space:pre-wrap; box-shadow:0 0 25px var(--neon-red); }
        button { 
            background:transparent; 
            border:3px solid var(--neon-red); 
            color:var(--neon-red); 
            padding:16px 35px; 
            font-size:1.25rem; 
            margin:8px; 
            cursor:pointer; 
            transition:all 0.3s; 
        }
        button:hover { background:var(--neon-red); color:#000; box-shadow:0 0 40px var(--neon-red); }
        .injection-btn { border-color: var(--neon-purple); color: var(--neon-purple); }
        .injection-btn:hover { background:var(--neon-purple); color:#000; }
    </style>
</head>
<body>
    <div class="scanline"></div>
    <div class="container">
        <h1 class="glitch" data-text="PYNCAT C2 + INJECTION">PYNCAT C2 + INJECTION</h1>
        <div class="log" id="log"></div>
        
        <button onclick="startListener()">🚀 START LISTENER</button>
        <button onclick="triggerAttack()" style="border-color:#ff8800;color:#ff8800;">⚔️ TRIGGER NORMAL ATTACK</button>
        <button onclick="launchInjection()" class="injection-btn">💉 LAUNCH PROCESS INJECTION</button>
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
        async function launchInjection() { 
            await fetch('/injection', {method:'POST'}); 
            alert("💉 Process Injection Attack Launched!");
        }
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
    add_log("⚔️ Normal attack triggered", "CRITICAL")
    return {"status": "sent"}

@app.post("/injection")
async def launch_injection():
    notify_defense("process_injection_detected")
    add_log("💉 PROCESS INJECTION ATTACK SIMULATED", "CRITICAL")
    add_log("Technique: CreateRemoteThread + VirtualAllocEx", "ALERT")
    add_log("Target: High-privilege process", "WARNING")
    return {"status": "injection_launched"}

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

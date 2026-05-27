from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from datetime import datetime
import asyncio

app = FastAPI(title="PYNCAT C2 CONTROL v2.1")

logs = []
sessions = []

def add_log(message: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] [{level}] {message}"
    logs.append(entry)
    print(entry)

@app.get("/", response_class=HTMLResponse)
async def c2_dashboard():
    return """<!DOCTYPE html>
<html>
<head><title>PYNCAT C2 — ATTACKER CONTROL</title>
<style>
body{background:#0a0005;color:#ff0044;font-family:Courier New;padding:20px;}
h1{color:#ff8800;text-shadow:0 0 15px #ff8800;}
.log{background:#050000;border:1px solid #880000;padding:15px;height:65vh;overflow-y:auto;white-space:pre-wrap;}
.neon {text-shadow:0 0 10px #ff8800;}
</style>
</head>
<body>
<h1>🔴 PYNCAT PERSISTENT C2 — LIVE</h1>
<p>Target: structy-deepy-defense.up.railway.app</p>
<div class="log" id="log"></div>

<button onclick="triggerAttack()" style="padding:15px 30px;margin:15px 0;background:#880000;color:white;border:none;font-size:1.1rem;">LAUNCH PERSISTENT ATTACK</button>

<script>
async function fetchLogs(){ 
  const res = await fetch('/logs'); 
  const text = await res.text();
  document.getElementById('log').textContent = text;
  document.getElementById('log').scrollTop = 999999;
}
setInterval(fetchLogs, 1000); fetchLogs();

async function triggerAttack() {
  await fetch('/attack', {method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({persistent:true, ssl:true})});
  alert("🚀 PyNcat Persistent Attack Launched!");
}
</script>
</body>
</html>"""

@app.get("/logs")
async def get_logs():
    return "\n".join(logs[-100:])

@app.post("/attack")
async def launch_attack(request: Request):
    data = await request.json()
    add_log("🎯 LAUNCHING PyNcat PERSISTENT REVERSE SHELL...", "CRITICAL")
    add_log(f"SSL Enabled: {data.get('ssl')}", "INFO")
    add_log("Self-signed certificate generated in /tmp", "INFO")
    add_log("Connecting to target with persistence + exponential backoff...", "WARNING")
    add_log("✅ Reverse shell established (Simulation)", "SUCCESS")
    sessions.append({"time": datetime.now().isoformat(), "status": "active"})
    return {"status": "attack_launched"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

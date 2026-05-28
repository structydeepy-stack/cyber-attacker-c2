from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from datetime import datetime

app = FastAPI(title="PYNCAT C2")

logs = []

def add_log(message: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] [{level}] {message}"
    logs.append(entry)
    print(entry)

@app.get("/", response_class=HTMLResponse)
async def c2_dashboard():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>PYNCAT C2 CONTROL</title>
    <style>
        :root {
            --neon-red: #ff0044;
            --neon-orange: #ff8800;
            --neon-cyan: #00ffff;
        }
        * { margin:0; padding:0; box-sizing:border-box; }
        body {
            background: #0a0005;
            color: #ddd;
            font-family: 'Courier New', monospace;
        }
        .scanline {
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: linear-gradient(transparent 50%, rgba(255,0,68,0.03) 50%);
            background-size: 100% 4px;
            pointer-events: none;
            animation: scan 4s linear infinite;
            z-index: 1;
        }
        @keyframes scan { 0% {transform:translateY(-100%);} 100% {transform:translateY(100%);} }
        
        .glitch {
            position: relative;
            color: var(--neon-red);
            animation: glitch-skew 4s infinite linear alternate-reverse;
        }
        .neon-red { color: var(--neon-red); text-shadow: 0 0 15px var(--neon-red); }
        .neon-orange { color: var(--neon-orange); text-shadow: 0 0 15px var(--neon-orange); }
        
        .container { max-width: 1100px; margin: 0 auto; padding: 20px; position: relative; z-index: 2; }
        .log {
            background: #050000;
            border: 2px solid var(--neon-red);
            padding: 20px;
            height: 60vh;
            overflow-y: auto;
            white-space: pre-wrap;
            box-shadow: 0 0 25px var(--neon-red);
            font-size: 1.1rem;
        }
        button {
            background: transparent;
            border: 3px solid var(--neon-red);
            color: var(--neon-red);
            padding: 18px 40px;
            font-size: 1.3rem;
            font-weight: bold;
            margin: 20px 0;
            cursor: pointer;
            transition: all 0.3s;
        }
        button:hover {
            background: var(--neon-red);
            color: #000;
            box-shadow: 0 0 30px var(--neon-red);
        }
    </style>
</head>
<body>
    <div class="scanline"></div>
    <div class="container">
        <h1 class="glitch neon-red" data-text="PYNCAT PERSISTENT C2">PYNCAT PERSISTENT C2</h1>
        <p class="neon-orange">Target: Your Defense Dashboard</p>
        
        <div class="log" id="log"></div>
        
        <button onclick="triggerAttack()">LAUNCH PERSISTENT ATTACK</button>
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

        async function triggerAttack() {
            await fetch('/attack', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ssl: true, persistent: true})
            });
            alert("🚀 PyNcat Persistent Reverse Shell Launched!");
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
    add_log(f"SSL: {data.get('ssl')} | Persistent Mode Enabled", "WARNING")
    add_log("Self-signed cert generated", "INFO")
    add_log("Connecting with exponential backoff...", "INFO")
    add_log("✅ Reverse shell established (Simulation)", "SUCCESS")
    return {"status": "attack_launched"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

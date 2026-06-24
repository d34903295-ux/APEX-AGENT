"""Optional real-time dashboard (FastAPI + Plotly).

Serves a lightweight page that polls /api/state for the live portfolio
snapshot, recent alerts and PnL/drawdown. Reads state from Redis heartbeat so
it works against the distributed deployment too.

Run:  uvicorn apex.dashboard.app:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import asyncio
import contextlib

from apex.bus.events import Channels
from apex.bus.redis_bus import make_bus
from apex.core.logging import get_logger

log = get_logger("apex.dashboard")

try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, JSONResponse
except ImportError:  # pragma: no cover
    FastAPI = None

_STATE = {"heartbeat": {}, "alerts": []}

INDEX_HTML = """<!doctype html><html><head><meta charset=utf-8>
<title>APEX-AGENT PRO</title>
<script src="https://cdn.plot.ly/plotly-2.30.0.min.js"></script>
<style>body{font-family:system-ui;background:#0b0e14;color:#d6e1ff;margin:0;padding:20px}
.card{background:#141a26;border-radius:12px;padding:16px;margin:10px 0;box-shadow:0 4px 20px #0006}
h1{font-weight:600} .kpi{display:inline-block;margin-right:24px}.kpi b{font-size:1.6em}
pre{white-space:pre-wrap}</style></head><body>
<h1>🚀 APEX-AGENT PRO</h1>
<div class=card id=kpis></div>
<div class=card><div id=chart style="height:320px"></div></div>
<div class=card><h3>Alerts</h3><pre id=alerts></pre></div>
<script>
let eq=[];
async function tick(){
 const r=await fetch('/api/state');const s=await r.json();
 const snap=(s.heartbeat&&s.heartbeat.snapshot)||{};
 document.getElementById('kpis').innerHTML=
  `<span class=kpi>Equity<br><b>${snap.equity??'-'}</b></span>`+
  `<span class=kpi>Cash<br><b>${snap.cash??'-'}</b></span>`+
  `<span class=kpi>PnL<br><b>${snap.realized_pnl??'-'}</b></span>`+
  `<span class=kpi>Drawdown<br><b>${((snap.drawdown||0)*100).toFixed(2)}%</b></span>`+
  `<span class=kpi>Paused<br><b>${s.heartbeat.paused??'-'}</b></span>`;
 if(snap.equity){eq.push(snap.equity);if(eq.length>300)eq.shift();
  Plotly.react('chart',[{y:eq,type:'scatter',line:{color:'#4f9dff'}}],
   {margin:{t:10},paper_bgcolor:'#141a26',plot_bgcolor:'#141a26',font:{color:'#d6e1ff'}});}
 document.getElementById('alerts').textContent=(s.alerts||[]).slice(-15).join('\\n');
}
setInterval(tick,2000);tick();
</script></body></html>"""


def create_app():
    if FastAPI is None:
        raise RuntimeError("fastapi not installed")
    app = FastAPI(title="APEX-AGENT PRO")

    @app.on_event("startup")
    async def _startup():
        from apex.obs.collector import collect
        app.state.task = asyncio.create_task(_consume())
        app.state.metrics_task = asyncio.create_task(collect())

    @app.on_event("shutdown")
    async def _shutdown():
        for t in (app.state.task, getattr(app.state, "metrics_task", None)):
            if t:
                t.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await t

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return INDEX_HTML

    @app.get("/api/state")
    async def state():
        return JSONResponse(_STATE)

    @app.get("/metrics")
    async def metrics():
        from apex.obs.metrics import REGISTRY
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(REGISTRY.render(),
                                 media_type="text/plain; version=0.0.4")

    @app.get("/health")
    async def health():
        return {"ok": True}

    return app


async def _consume():
    bus = await make_bus()

    async def hb():
        async for msg in bus.subscribe(Channels.HEARTBEAT):
            _STATE["heartbeat"] = msg

    async def al():
        async for msg in bus.subscribe(Channels.ALERTS):
            _STATE["alerts"].append(msg.get("text", ""))
            _STATE["alerts"] = _STATE["alerts"][-100:]

    await asyncio.gather(hb(), al())


app = create_app() if FastAPI is not None else None

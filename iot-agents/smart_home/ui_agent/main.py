from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from smart_home.common.config import SERVICE_URLS
from smart_home.common.messaging import BaseBusService, new_trace_id


class CommandRequest(BaseModel):
    text: str = Field(..., examples=["allume la lampe du salon"])


class UIAgentService(BaseBusService):
    def __init__(self) -> None:
        super().__init__(service_name="ui-agent")
        self.pending: dict[str, asyncio.Future[dict[str, Any]]] = {}

    async def handle_message(self, message: dict[str, Any]) -> bool:
        if message.get("to") != self.service_name:
            return False

        trace_id = message.get("trace_id")
        if not trace_id:
            return False

        future = self.pending.get(trace_id)
        if future and not future.done():
            future.set_result(message)
            self.record_event(
                "ui.response_received",
                trace_id=trace_id,
                topic=message.get("topic"),
            )
            return True
        return False

    async def send_command(self, text: str) -> dict[str, Any]:
        loop = asyncio.get_running_loop()
        trace_id = new_trace_id()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()
        self.pending[trace_id] = future
        self.record_event("ui.command_received", text=text, trace_id=trace_id)
        try:
            await self.publish(
                target="coordinator",
                topic="nl.command",
                content={"text": text, "reply_to": self.service_name},
                trace_id=trace_id,
            )
            return await asyncio.wait_for(future, timeout=8)
        finally:
            self.pending.pop(trace_id, None)


service = UIAgentService()


def fetch_json(url: str) -> dict[str, Any]:
    with urlopen(url, timeout=3) as response:
        return json.loads(response.read().decode("utf-8"))


async def collect_service_snapshot(name: str, base_url: str) -> dict[str, Any]:
    try:
        health, metrics = await asyncio.gather(
            asyncio.to_thread(fetch_json, f"{base_url}/healthz"),
            asyncio.to_thread(fetch_json, f"{base_url}/metrics"),
        )
        state = None
        if name in {"lamp-agent", "plug-agent", "thermostat-agent"}:
            state = await asyncio.to_thread(fetch_json, f"{base_url}/state")
        return {
            "service": name,
            "status": "ok",
            "base_url": base_url,
            "health": health,
            "metrics": metrics,
            "state": state["state"] if state else None,
        }
    except (TimeoutError, URLError, OSError, ValueError) as exc:
        return {
            "service": name,
            "status": "error",
            "base_url": base_url,
            "error": str(exc),
        }


async def build_dashboard_payload() -> dict[str, Any]:
    snapshots = await asyncio.gather(
        *(collect_service_snapshot(name, url) for name, url in SERVICE_URLS.items())
    )
    aggregated_events: list[dict[str, Any]] = []
    aggregated_logs: list[dict[str, Any]] = []
    for snapshot in snapshots:
        metrics = snapshot.get("metrics", {})
        aggregated_events.extend(metrics.get("recent_events", []))
        aggregated_logs.extend(metrics.get("recent_logs", []))
    aggregated_events.sort(key=lambda item: item.get("ts", ""), reverse=True)
    aggregated_logs.sort(key=lambda item: item.get("ts", ""), reverse=True)
    return {
        "summary": {
            "service_count": len(snapshots),
            "healthy_count": sum(1 for item in snapshots if item["status"] == "ok"),
            "pending_commands": len(service.pending),
            "bus_messages_seen": len(service.seen_messages),
        },
        "services": snapshots,
        "recent_commands": list(service.seen_messages)[:12],
        "recent_events": aggregated_events[:20],
        "recent_logs": aggregated_logs[:20],
    }


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Smart Home Dashboard</title>
  <style>
    :root {
      --bg: #f4efe7;
      --panel: rgba(255,255,255,0.82);
      --panel-strong: #fffdf9;
      --ink: #1d2a33;
      --muted: #5f6b73;
      --line: rgba(29,42,51,0.12);
      --accent: #cc5a2f;
      --accent-2: #1f7a8c;
      --ok: #1f8a4c;
      --error: #b42318;
      --shadow: 0 22px 60px rgba(35, 32, 28, 0.12);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", "Trebuchet MS", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(204,90,47,0.18), transparent 28%),
        radial-gradient(circle at top right, rgba(31,122,140,0.16), transparent 24%),
        linear-gradient(135deg, #f8f2ea 0%, #f2f5f7 48%, #edf3ef 100%);
      min-height: 100vh;
    }
    .shell { width: min(1180px, calc(100% - 32px)); margin: 24px auto 40px; }
    .hero {
      background: linear-gradient(135deg, rgba(255,253,249,0.95), rgba(255,255,255,0.72));
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
      border-radius: 28px;
      padding: 28px;
      display: grid;
      gap: 18px;
    }
    .hero-top, .stats, .grid, .panel-grid { display: grid; gap: 16px; }
    .hero-top { grid-template-columns: 1.5fr 1fr; align-items: start; }
    h1, h2, h3, p { margin: 0; }
    h1 { font-size: clamp(2rem, 4vw, 3.6rem); line-height: 0.95; letter-spacing: -0.03em; }
    h2 { font-size: 1.1rem; margin-bottom: 12px; }
    .lede { color: var(--muted); max-width: 60ch; line-height: 1.5; }
    .badge {
      display: inline-flex; align-items: center; gap: 8px; padding: 8px 12px;
      border-radius: 999px; background: rgba(31,122,140,0.08); color: var(--accent-2);
      font-weight: 700; font-size: 0.92rem;
    }
    .stats { grid-template-columns: repeat(4, minmax(0, 1fr)); }
    .card, .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 18px;
      backdrop-filter: blur(10px);
    }
    .stat-value { font-size: 2rem; font-weight: 800; margin-top: 10px; }
    .stat-label, .meta, .small { color: var(--muted); }
    .grid { grid-template-columns: repeat(3, minmax(0, 1fr)); margin-top: 20px; }
    .panel-grid { grid-template-columns: 1.2fr 1fr; margin-top: 20px; }
    .service-head, .row {
      display: flex; align-items: center; justify-content: space-between; gap: 12px;
    }
    .status-ok, .status-error {
      font-size: 0.8rem; font-weight: 700; text-transform: uppercase;
      letter-spacing: 0.08em; padding: 7px 10px; border-radius: 999px;
    }
    .status-ok { color: var(--ok); background: rgba(31,138,76,0.12); }
    .status-error { color: var(--error); background: rgba(180,35,24,0.12); }
    .service-state { margin-top: 14px; display: grid; gap: 8px; }
    .state-pill {
      display: inline-flex; padding: 6px 10px; border-radius: 999px;
      background: rgba(29,42,51,0.06); margin-right: 6px; margin-bottom: 6px; font-size: 0.9rem;
    }
    form { display: grid; gap: 12px; }
    textarea {
      width: 100%; min-height: 110px; resize: vertical; border-radius: 16px;
      border: 1px solid var(--line); padding: 14px; font: inherit; background: #fffdfa;
    }
    button {
      border: 0; border-radius: 14px; padding: 13px 16px; cursor: pointer;
      background: linear-gradient(135deg, var(--accent), #e08a3a);
      color: white; font-weight: 700; font-size: 1rem;
    }
    .result {
      margin-top: 12px; padding: 14px; border-radius: 16px; background: #fffdfa;
      border: 1px solid var(--line); white-space: pre-wrap;
    }
    .log-list, .event-list { display: grid; gap: 10px; margin-top: 10px; }
    .item {
      border: 1px solid var(--line); border-radius: 16px; padding: 12px; background: var(--panel-strong);
    }
    .mono { font-family: Consolas, "SFMono-Regular", monospace; font-size: 0.9rem; }
    .footer { margin-top: 18px; color: var(--muted); font-size: 0.9rem; }
    @media (max-width: 980px) {
      .hero-top, .grid, .panel-grid, .stats { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="hero-top">
        <div>
          <div class="badge">Dashboard domotique multi-agents</div>
          <h1>Commandes, etats et observabilite dans une seule vue.</h1>
          <p class="lede">Cette interface pilote la maison connectee simulee, affiche la sante des services, remonte les etats des objets et expose les evenements recents pour une demo plus convaincante.</p>
        </div>
        <div class="card">
          <h2>Commande rapide</h2>
          <form id="command-form">
            <textarea id="command-text" placeholder="Exemple: regle le thermostat a 23 degres"></textarea>
            <button type="submit">Envoyer la commande</button>
          </form>
          <div class="result mono" id="command-result">En attente de commande...</div>
        </div>
      </div>
      <div class="stats" id="summary"></div>
    </section>

    <section class="grid" id="services"></section>

    <section class="panel-grid">
      <div class="panel">
        <h2>Evenements recents</h2>
        <div class="event-list" id="events"></div>
      </div>
      <div class="panel">
        <h2>Logs recents</h2>
        <div class="log-list" id="logs"></div>
      </div>
    </section>

    <div class="footer">Rafraichissement automatique toutes les 5 secondes.</div>
  </div>

  <script>
    const summary = document.getElementById("summary");
    const services = document.getElementById("services");
    const events = document.getElementById("events");
    const logs = document.getElementById("logs");
    const form = document.getElementById("command-form");
    const commandText = document.getElementById("command-text");
    const commandResult = document.getElementById("command-result");

    function metricCard(label, value, help) {
      return `<div class="card"><div class="stat-label">${label}</div><div class="stat-value">${value}</div><div class="small">${help}</div></div>`;
    }

    function renderState(state) {
      if (!state) return `<div class="small">Aucun etat expose pour ce service.</div>`;
      return Object.entries(state)
        .map(([key, value]) => `<span class="state-pill"><strong>${key}</strong>&nbsp;${value}</span>`)
        .join("");
    }

    function renderServices(items) {
      services.innerHTML = items.map((item) => {
        const ok = item.status === "ok";
        const metrics = item.metrics || {};
        return `
          <article class="card">
            <div class="service-head">
              <div>
                <h2>${item.service}</h2>
                <div class="meta">${item.base_url}</div>
              </div>
              <span class="${ok ? "status-ok" : "status-error"}">${ok ? "healthy" : "error"}</span>
            </div>
            <div class="service-state">${ok ? renderState(item.state) : `<div class="small">${item.error}</div>`}</div>
            <div class="small" style="margin-top:12px;">published=${metrics.published_messages ?? "-"} | consumed=${metrics.consumed_messages ?? "-"} | failed=${metrics.failed_messages ?? "-"}</div>
          </article>`;
      }).join("");
    }

    function renderList(target, items, fallback) {
      if (!items.length) {
        target.innerHTML = `<div class="item small">${fallback}</div>`;
        return;
      }
      target.innerHTML = items.map((item) => `
        <div class="item">
          <div class="row">
            <strong>${item.event || item.level || item.topic || "entry"}</strong>
            <span class="small">${item.ts || ""}</span>
          </div>
          <div class="small mono">${JSON.stringify(item, null, 2)}</div>
        </div>`).join("");
    }

    async function loadDashboard() {
      const response = await fetch("/dashboard/data");
      const data = await response.json();
      summary.innerHTML = [
        metricCard("Services suivis", data.summary.service_count, "micro-services relies au bus"),
        metricCard("Services sains", data.summary.healthy_count, "etat instantane de la plateforme"),
        metricCard("Commandes en attente", data.summary.pending_commands, "futures ouvertes cote UI"),
        metricCard("Messages visibles", data.summary.bus_messages_seen, "historique recent local"),
      ].join("");
      renderServices(data.services);
      renderList(events, data.recent_events, "Aucun evenement recent.");
      renderList(logs, data.recent_logs, "Aucun log recent.");
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      commandResult.textContent = "Commande en cours...";
      const response = await fetch("/command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: commandText.value })
      });
      const data = await response.json();
      commandResult.textContent = JSON.stringify(data, null, 2);
      await loadDashboard();
    });

    loadDashboard();
    setInterval(loadDashboard, 5000);
  </script>
</body>
</html>
"""


@asynccontextmanager
async def lifespan(_: FastAPI):
    await service.connect()
    service.reader_task = asyncio.create_task(service.read_forever())
    yield
    await service.disconnect()


app = FastAPI(title="ui-agent", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
async def dashboard() -> str:
    return DASHBOARD_HTML


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "service": service.service_name, "started_at": service.started_at}


@app.get("/metrics")
async def metrics() -> dict[str, Any]:
    return service.get_metrics_snapshot()


@app.get("/dashboard/data")
async def dashboard_data() -> dict[str, Any]:
    return await build_dashboard_payload()


@app.get("/monitoring/overview")
async def monitoring_overview() -> dict[str, Any]:
    return await build_dashboard_payload()


@app.post("/command")
async def command(request: CommandRequest) -> dict[str, Any]:
    try:
        message = await service.send_command(request.text)
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Timeout en attendant la reponse d'un agent.") from exc

    return {
        "trace_id": message["trace_id"],
        "topic": message["topic"],
        "response": message["content"],
    }


@app.get("/dump")
async def dump() -> dict[str, Any]:
    return {
        "service": service.service_name,
        "messages": list(service.seen_messages),
        "events": list(service.recent_events),
    }

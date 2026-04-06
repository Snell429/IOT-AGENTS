from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from smart_home.common.messaging import BaseBusService


class DeviceAgentService(BaseBusService):
    def __init__(self, service_name: str, initial_state: dict[str, Any]) -> None:
        super().__init__(service_name=service_name)
        self.state = initial_state

    async def handle_message(self, message: dict[str, Any]) -> bool:
        if message.get("to") != self.service_name:
            return False

        topic = message.get("topic")
        content = message.get("content", {})
        if topic != "device.command":
            return False

        reply_to = content.get("reply_to", "ui-agent")
        action = content.get("action")
        payload = content.get("parameters", {})
        self.record_event(
            "device.command_received",
            action=action,
            reply_to=reply_to,
            trace_id=message.get("trace_id"),
        )
        result = self.apply_action(action, payload)
        await self.publish(
            target=reply_to,
            topic="device.result",
            trace_id=message.get("trace_id"),
            content={
                "device": self.service_name,
                "action": action,
                "result": result,
                "state": self.state,
            },
        )
        self.record_event(
            "device.command_applied",
            action=action,
            success=result.get("ok"),
            state=self.state.copy(),
        )
        return True

    def apply_action(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        if action == "turn_on":
            self.state["power"] = "on"
            return {"ok": True, "message": f"{self.service_name} allume."}
        if action == "turn_off":
            self.state["power"] = "off"
            return {"ok": True, "message": f"{self.service_name} eteint."}
        if action == "get_state":
            return {"ok": True, "message": f"Etat courant de {self.service_name}."}
        if action == "set_target_temperature":
            target = payload.get("target_temperature")
            if target is None:
                return {"ok": False, "message": "Temperature cible manquante."}
            self.state["target_temperature"] = target
            return {"ok": True, "message": f"Temperature cible reglee a {target}C."}
        return {"ok": False, "message": f"Action inconnue: {action}"}


def create_device_app(service: DeviceAgentService) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await service.connect()
        service.reader_task = asyncio.create_task(service.read_forever())
        yield
        await service.disconnect()

    app = FastAPI(title=service.service_name, lifespan=lifespan)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "service": service.service_name, "started_at": service.started_at}

    @app.get("/state")
    async def state() -> dict[str, Any]:
        return {"service": service.service_name, "state": service.state}

    @app.get("/metrics")
    async def metrics() -> dict[str, Any]:
        snapshot = service.get_metrics_snapshot()
        snapshot["state"] = service.state
        return snapshot

    @app.get("/dump")
    async def dump() -> dict[str, Any]:
        return {
            "service": service.service_name,
            "messages": list(service.seen_messages),
            "events": list(service.recent_events),
        }

    return app

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from smart_home.common.messaging import BaseBusService
from smart_home.common.parsing import parse_user_command


class CoordinatorService(BaseBusService):
    def __init__(self) -> None:
        super().__init__(service_name="coordinator")

    async def handle_message(self, message: dict[str, Any]) -> bool:
        if message.get("to") != self.service_name:
            return False

        topic = message.get("topic")
        content = message.get("content", {})
        if topic != "nl.command":
            return False

        text = content.get("text", "")
        reply_to = content.get("reply_to", "ui-agent")
        parsed = parse_user_command(text)
        self.record_event(
            "coordinator.command_parsed",
            text=text,
            reply_to=reply_to,
            parse_ok=parsed["ok"],
        )

        if not parsed["ok"]:
            await self.publish(
                target=reply_to,
                topic="device.result",
                trace_id=message.get("trace_id"),
                content={
                    "device": None,
                    "action": "parse_error",
                    "result": parsed,
                    "state": None,
                },
            )
            return True

        await self.publish(
            target=parsed["target"],
            topic="device.command",
            trace_id=message.get("trace_id"),
            content={
                "action": parsed["action"],
                "parameters": parsed["parameters"],
                "reply_to": reply_to,
                "original_text": text,
            },
        )
        return True


service = CoordinatorService()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await service.connect()
    service.reader_task = asyncio.create_task(service.read_forever())
    yield
    await service.disconnect()


app = FastAPI(title="coordinator", lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "service": service.service_name, "started_at": service.started_at}


@app.get("/metrics")
async def metrics() -> dict[str, Any]:
    return service.get_metrics_snapshot()


@app.get("/dump")
async def dump() -> dict[str, Any]:
    return {
        "service": service.service_name,
        "messages": list(service.seen_messages),
        "events": list(service.recent_events),
    }

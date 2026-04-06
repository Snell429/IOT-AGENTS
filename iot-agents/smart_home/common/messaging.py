from __future__ import annotations

import asyncio
import json
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from redis.asyncio import Redis

from smart_home.common.config import BUS_STREAM, MESSAGE_SCHEMA_VERSION, REDIS_URL
from smart_home.common.observability import InMemoryLogHandler, configure_logging, log_event


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def build_message(
    *,
    sender: str,
    target: str,
    topic: str,
    content: dict[str, Any],
    trace_id: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": MESSAGE_SCHEMA_VERSION,
        "msg_id": str(uuid4()),
        "trace_id": trace_id or str(uuid4()),
        "from": sender,
        "to": target,
        "topic": topic,
        "content": content,
        "ts": utc_now_iso(),
    }


def new_trace_id() -> str:
    return str(uuid4())


async def publish_message(redis: Redis, message: dict[str, Any]) -> str:
    return await redis.xadd(BUS_STREAM, {"data": json.dumps(message)})


@dataclass
class BaseBusService:
    service_name: str
    redis_url: str = REDIS_URL
    stream_name: str = BUS_STREAM
    redis: Redis | None = None
    reader_task: asyncio.Task[None] | None = None
    stop_event: asyncio.Event = field(default_factory=asyncio.Event)
    seen_messages: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=50))
    recent_events: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=100))
    processed_message_ids: set[str] = field(default_factory=set)
    last_stream_id: str = "$"
    started_at: str = field(default_factory=utc_now_iso)
    published_messages: int = 0
    consumed_messages: int = 0
    handled_messages: int = 0
    failed_messages: int = 0
    logger: logging.Logger = field(init=False)
    log_buffer: InMemoryLogHandler = field(init=False)

    def __post_init__(self) -> None:
        self.log_buffer = configure_logging(self.service_name)
        self.logger = logging.getLogger(self.service_name)
        self.record_event("service.initialized", stream_name=self.stream_name)

    def record_event(self, event: str, **details: Any) -> None:
        payload = {"ts": utc_now_iso(), "event": event, **details}
        self.recent_events.appendleft(payload)
        log_event(self.logger, event, service=self.service_name, **details)

    async def connect(self) -> None:
        self.redis = Redis.from_url(self.redis_url, decode_responses=True)
        await self.redis.ping()
        self.record_event("redis.connected", redis_url=self.redis_url)

    async def disconnect(self) -> None:
        self.stop_event.set()
        if self.reader_task:
            self.reader_task.cancel()
            try:
                await self.reader_task
            except asyncio.CancelledError:
                pass
        if self.redis:
            await self.redis.aclose()
        self.record_event("redis.disconnected")

    async def publish(
        self,
        *,
        target: str,
        topic: str,
        content: dict[str, Any],
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        if not self.redis:
            raise RuntimeError("Redis connection not initialized")

        message = build_message(
            sender=self.service_name,
            target=target,
            topic=topic,
            content=content,
            trace_id=trace_id,
        )
        await publish_message(self.redis, message)
        self.published_messages += 1
        self.record_event(
            "message.published",
            topic=topic,
            target=target,
            trace_id=message["trace_id"],
            msg_id=message["msg_id"],
        )
        return message

    async def read_forever(self) -> None:
        if not self.redis:
            raise RuntimeError("Redis connection not initialized")

        while not self.stop_event.is_set():
            entries = await self.redis.xread(
                {self.stream_name: self.last_stream_id},
                count=10,
                block=1000,
            )
            if not entries:
                continue

            for _, messages in entries:
                for stream_id, fields in messages:
                    self.last_stream_id = stream_id
                    raw_payload = fields.get("data")
                    if not raw_payload:
                        continue

                    message = json.loads(raw_payload)
                    self.seen_messages.appendleft(message)
                    self.consumed_messages += 1
                    msg_id = message.get("msg_id")
                    if msg_id and msg_id in self.processed_message_ids:
                        self.record_event("message.duplicate_skipped", msg_id=msg_id)
                        continue
                    if msg_id:
                        self.processed_message_ids.add(msg_id)

                    self.record_event(
                        "message.received",
                        topic=message.get("topic"),
                        sender=message.get("from"),
                        trace_id=message.get("trace_id"),
                        msg_id=msg_id,
                    )
                    try:
                        handled = await self.handle_message(message)
                        if handled:
                            self.handled_messages += 1
                    except Exception:
                        self.failed_messages += 1
                        self.record_event(
                            "message.handler_failed",
                            topic=message.get("topic"),
                            trace_id=message.get("trace_id"),
                            msg_id=msg_id,
                        )
                        raise

    def get_metrics_snapshot(self) -> dict[str, Any]:
        return {
            "service": self.service_name,
            "stream": self.stream_name,
            "started_at": self.started_at,
            "published_messages": self.published_messages,
            "consumed_messages": self.consumed_messages,
            "handled_messages": self.handled_messages,
            "failed_messages": self.failed_messages,
            "recent_events": list(self.recent_events)[:20],
            "recent_logs": list(self.log_buffer.records)[:20],
        }

    async def handle_message(self, message: dict[str, Any]) -> bool:
        raise NotImplementedError

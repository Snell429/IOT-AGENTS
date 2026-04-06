import os


def get_env(name: str, default: str) -> str:
    return os.getenv(name, default)


REDIS_URL = get_env("REDIS_URL", "redis://redis:6379/0")
BUS_STREAM = get_env("BUS_STREAM", "a2a_bus")
MESSAGE_SCHEMA_VERSION = "1.0"
UI_AGENT_BASE_URL = get_env("UI_AGENT_BASE_URL", "http://ui-agent:8000")
COORDINATOR_BASE_URL = get_env("COORDINATOR_BASE_URL", "http://coordinator:8000")
LAMP_AGENT_BASE_URL = get_env("LAMP_AGENT_BASE_URL", "http://lamp-agent:8000")
PLUG_AGENT_BASE_URL = get_env("PLUG_AGENT_BASE_URL", "http://plug-agent:8000")
THERMOSTAT_AGENT_BASE_URL = get_env("THERMOSTAT_AGENT_BASE_URL", "http://thermostat-agent:8000")

SERVICE_URLS = {
    "ui-agent": UI_AGENT_BASE_URL,
    "coordinator": COORDINATOR_BASE_URL,
    "lamp-agent": LAMP_AGENT_BASE_URL,
    "plug-agent": PLUG_AGENT_BASE_URL,
    "thermostat-agent": THERMOSTAT_AGENT_BASE_URL,
}

from smart_home.common.device_agent import DeviceAgentService, create_device_app


service = DeviceAgentService(
    service_name="thermostat-agent",
    initial_state={
        "power": "on",
        "current_temperature": 20,
        "target_temperature": 21,
        "label": "Thermostat principal",
    },
)

app = create_device_app(service)

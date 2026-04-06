from smart_home.common.device_agent import DeviceAgentService, create_device_app


service = DeviceAgentService(
    service_name="lamp-agent",
    initial_state={"power": "off", "label": "Lampe du salon"},
)

app = create_device_app(service)

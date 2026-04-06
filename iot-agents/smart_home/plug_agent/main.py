from smart_home.common.device_agent import DeviceAgentService, create_device_app


service = DeviceAgentService(
    service_name="plug-agent",
    initial_state={"power": "off", "label": "Prise bureau"},
)

app = create_device_app(service)

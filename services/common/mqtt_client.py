import logging

import paho.mqtt.client as mqtt

from .config import MQTT_SETTINGS

logger = logging.getLogger(__name__)


def build_client(
    client_id: str,
    on_connect=None,
    on_message=None,
) -> mqtt.Client:

    client_kwargs = {
        "client_id": client_id,
        "protocol": mqtt.MQTTv5,
    }

    callback_api = getattr(mqtt, "CallbackAPIVersion", None)
    if callback_api is not None:
        client_kwargs["callback_api_version"] = mqtt.CallbackAPIVersion.VERSION2

    client_kwargs["clean_session"] = None

    client = mqtt.Client(**client_kwargs)
    client.reconnect_delay_set(min_delay=2, max_delay=30)

    if MQTT_SETTINGS.username:
        client.username_pw_set(MQTT_SETTINGS.username, MQTT_SETTINGS.password)

    if on_connect:
        client.on_connect = on_connect

    if on_message:
        client.on_message = on_message

    logger.info(
        "Connecting MQTT client '%s' to %s:%s",
        client_id,
        MQTT_SETTINGS.broker_host,
        MQTT_SETTINGS.broker_port,
    )
    client.connect(MQTT_SETTINGS.broker_host, MQTT_SETTINGS.broker_port, MQTT_SETTINGS.keepalive)
    return client

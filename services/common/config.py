import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class MQTTConfig:
    broker_host: str = os.getenv("MQTT_BROKER_HOST", "localhost")
    broker_port: int = int(os.getenv("MQTT_BROKER_PORT", "1883"))
    username: str | None = os.getenv("MQTT_USERNAME")
    password: str | None = os.getenv("MQTT_PASSWORD")
    keepalive: int = int(os.getenv("MQTT_KEEPALIVE", "60"))
    factory_root_topic: str = os.getenv("FACTORY_ROOT_TOPIC", "factory").rstrip("/")
    temperature_topic: str = os.getenv("FACTORY_TEMPERATURE_TOPIC", "factory/temperature").rstrip("/")
    cat_average_topic: str = os.getenv("FACTORY_CAT_AVERAGE_TOPIC", "factory/cat/average").rstrip("/")
    rapid_change_topic: str = os.getenv("FACTORY_RAPID_CHANGE_TOPIC", "factory/events/rapid_change").rstrip("/")
    high_average_topic: str = os.getenv("FACTORY_HIGH_AVERAGE_TOPIC", "factory/events/high_average").rstrip("/")
    small_change_topic: str = os.getenv("FACTORY_SMALL_CHANGE_TOPIC", "factory/events/small_change").rstrip("/")


MQTT_SETTINGS = MQTTConfig()

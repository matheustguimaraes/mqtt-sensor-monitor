import json
import logging
import queue
import threading
import time
from dataclasses import dataclass

from ..common.config import MQTT_SETTINGS
from ..common.mqtt_client import build_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("alarm-service")


@dataclass
class AlarmMessage:
    topic: str
    event: str
    payload: dict
    received_at: float


class AlarmDisplay(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.queue = queue.Queue()
        self._running = True

    def run(self):
        while self._running:
            try:
                message = self.queue.get(timeout=0.5)
                self._render(message)
            except queue.Empty:
                continue

    def stop(self):
        self._running = False

    def enqueue(self, message: AlarmMessage):
        self.queue.put(message)

    @staticmethod
    def _render(message: AlarmMessage):
        print("\n================ ALARM ================")
        print(f"Time: {time.strftime('%H:%M:%S', time.localtime(message.received_at))}")
        print(f"Topic: {message.topic}")
        print(f"Event: {message.event}")
        print("---------------------------------------")
        print(json.dumps(message.payload, indent=2))
        print("=======================================\n")


class AlarmService:
    def __init__(self):
        self.display = AlarmDisplay()
        self.client = build_client(
            client_id="alarm-service",
            on_connect=self._on_connect,
            on_message=self._on_message,
        )

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        logger.info("Connected to broker (%s)", reason_code)
        client.subscribe(MQTT_SETTINGS.high_average_topic)
        client.subscribe(MQTT_SETTINGS.rapid_change_topic)
        client.subscribe(MQTT_SETTINGS.small_change_topic)
        logger.info(
            "Subscribed to %s, %s, and %s",
            MQTT_SETTINGS.high_average_topic,
            MQTT_SETTINGS.rapid_change_topic,
            MQTT_SETTINGS.small_change_topic,
        )

    def _on_message(self, client, userdata, msg):
        logger.debug("Received message on topic: %s", msg.topic)
        try:
            payload = json.loads(msg.payload.decode())
        except Exception as exc:
            logger.error("Invalid alarm payload on %s: %s", msg.topic, exc)
            return

        event_name = payload.get("event", "unknown")
        logger.info("Received %s event on %s", event_name, msg.topic)
        message = AlarmMessage(topic=msg.topic, event=event_name, payload=payload, received_at=time.time())
        self.display.enqueue(message)

    def start(self):
        self.display.start()
        logger.info(
            "Alarm service started. Waiting for events on %s, %s, and %s",
            MQTT_SETTINGS.high_average_topic,
            MQTT_SETTINGS.rapid_change_topic,
            MQTT_SETTINGS.small_change_topic,
        )
        try:
            self.client.loop_forever()
        finally:
            self.display.stop()


def main():
    service = AlarmService()
    try:
        service.start()
    except KeyboardInterrupt:
        logger.info("Alarm service interrupted, shutting down...")


if __name__ == "__main__":
    main()

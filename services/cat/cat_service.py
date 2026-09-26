import json
import logging
from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Deque

from ..common.config import MQTT_SETTINGS
from ..common.mqtt_client import build_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("cat-service")

WINDOW_SECONDS = 120


@dataclass
class Reading:
    timestamp: float
    value: float
    sensor_id: str


class RollingAverage:
    def __init__(self, window_seconds: int):
        self.window_seconds = window_seconds
        self.readings: Deque[Reading] = deque[Reading]()

    def add(self, reading: Reading) -> float:
        self.readings.append(reading)
        self._trim(reading.timestamp)
        return self.current_average()

    def current_average(self) -> float:
        if not self.readings:
            return 0.0
        total = sum(r.value for r in self.readings)
        return round(total / len(self.readings), 2)

    def _trim(self, now: float) -> None:
        while self.readings and (now - self.readings[0].timestamp) > self.window_seconds:
            self.readings.popleft()

    def sensors_in_window(self) -> dict[str, int]:
        counter = Counter[str](r.sensor_id for r in self.readings)
        return dict[str, int](counter)


class CatService:
    def __init__(self):
        self.average_tracker = RollingAverage(WINDOW_SECONDS)
        self.previous_average: float | None = None
        self.client = build_client(
            client_id="cat-service",
            on_connect=self._on_connect,
            on_message=self._on_message,
        )

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        logger.info("Connected to broker with code %s", reason_code)
        client.subscribe(f"{MQTT_SETTINGS.temperature_topic}/#")
        logger.info("Subscribed to %s/#", MQTT_SETTINGS.temperature_topic)

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            timestamp = float(payload.get("epochSeconds") or 0.0)
            if not timestamp:
                timestamp = datetime.now(timezone.utc).timestamp()
            reading = Reading(
                timestamp=timestamp,
                value=float(payload.get("value")),
                sensor_id=payload.get("sensorId", "unknown"),
            )
        except Exception as exc:
            logger.error("Invalid payload on %s: %s", msg.topic, exc)
            return

        average = self.average_tracker.add(reading)
        logger.info(
            "Updated average: %.2f°C (%s readings)",
            average,
            len(self.average_tracker.readings),
        )

        metadata = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "windowSeconds": WINDOW_SECONDS,
            "sensorCounts": self.average_tracker.sensors_in_window(),
            "reading": payload,
            "average": average,
        }
        self.client.publish(MQTT_SETTINGS.cat_average_topic, json.dumps(metadata), qos=1, retain=False)

        self._check_alerts(average, metadata)
        self.previous_average = average

    def _check_alerts(self, average: float, metadata: dict):
        if average >= 200:
            self._publish_event(MQTT_SETTINGS.high_average_topic, "high_average", metadata)

        if self.previous_average is not None:
            diff = abs(average - self.previous_average)
            if diff >= 5:
                metadata_with_diff = {**metadata, "difference": round(diff, 2)}
                self._publish_event(MQTT_SETTINGS.rapid_change_topic, "rapid_change", metadata_with_diff)
            elif diff >= 0.1:
                metadata_with_diff = {**metadata, "difference": round(diff, 2)}
                self._publish_event(MQTT_SETTINGS.small_change_topic, "small_change", metadata_with_diff)

    def _publish_event(self, topic: str, event_type: str, payload: dict):
        event = {
            "event": event_type,
            **payload,
        }
        logger.warning("Publishing %s event: %s", event_type, event)
        self.client.publish(topic, json.dumps(event), qos=1, retain=False)

    def start(self):
        self.client.loop_forever()


def main():
    service = CatService()
    try:
        service.start()
    except KeyboardInterrupt:
        logger.info("CAT service interrupted, shutting down...")


if __name__ == "__main__":
    main()

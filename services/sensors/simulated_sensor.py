import argparse
import json
import logging
import random
import signal
import time
from datetime import datetime, timezone

from ..common.config import MQTT_SETTINGS
from ..common.mqtt_client import build_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("simulated-sensor")

stop_requested = False


def _handle_stop(signum, frame):
    global stop_requested
    logger.info("Received signal %s, shutting down ...", signum)
    stop_requested = True


for sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(sig, _handle_stop)


def parse_args():
    parser = argparse.ArgumentParser(description="Simulated MQTT temperature sensor")
    parser.add_argument("--sensor-id", default="sensor-sim-1", help="Sensor identifier")
    parser.add_argument(
        "--base-temp",
        type=float,
        default=180.0,
        help="Baseline temperature in Celsius",
    )
    parser.add_argument(
        "--variance",
        type=float,
        default=5.0,
        help="Standard deviation for temp noise",
    )
    parser.add_argument(
        "--spike-chance",
        type=float,
        default=0.1,
        help="Probability (0-1) of a spike event per reading",
    )
    parser.add_argument(
        "--spike-boost",
        type=float,
        default=25.0,
        help="Degrees added during a spike",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Seconds between readings",
    )
    return parser.parse_args()


def generate_temperature(base_temp: float, variance: float, spike_chance: float, spike_boost: float) -> float:
    value = random.gauss(base_temp, variance)
    if random.random() <= spike_chance:
        logger.debug("Spike triggered (+%.1f)", spike_boost)
        value += spike_boost
    return round(value, 2)


def main():
    args = parse_args()
    client = build_client(client_id=f"{args.sensor_id}-publisher")
    client.loop_start()

    topic = f"{MQTT_SETTINGS.temperature_topic}/{args.sensor_id}"
    logger.info("Publishing temperature data to %s", topic)

    try:
        while not stop_requested:
            payload = {
                "sensorId": args.sensor_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "epochSeconds": time.time(),
                "value": generate_temperature(args.base_temp, args.variance, args.spike_chance, args.spike_boost),
                "unit": "C",
                "source": "simulated",
            }
            client.publish(topic, json.dumps(payload), qos=1, retain=False)
            logger.info("Published reading: %.2f°C", payload["value"])
            time.sleep(args.interval)
    except KeyboardInterrupt:
        logger.info("Interrupted by user, exiting.")
    finally:
        client.loop_stop()
        client.disconnect()
        logger.info("Sensor stopped.")


if __name__ == "__main__":
    main()

# Changelog

## 2026-09-26

- Moved the project into its own repository; the Python package is now `services/` and runs from the repository root.
- Fixed the simulated sensor crashing on start: `build_client` now treats the connect and message callbacks as optional.
- Added the missing `FACTORY_SMALL_CHANGE_TOPIC` to `.env.example`.
- Added README with architecture, message formats and run steps, and this changelog.

## 2025-11

- Expo / React Native app that turns the phone's accelerometer into a temperature reading and publishes it over MQTT WebSockets every 2 seconds, with auto-publish toggle and a manual send button.
- Mosquitto config with TCP (1883) and WebSocket (9001) listeners, and a compose file to run it.
- CAT service: 120-second rolling average across all sensors, publishes the average plus `high_average` (>= 200 °C), `rapid_change` (>= 5 °C between consecutive averages) and `small_change` events.
- Alarm service: subscribes to the event topics and prints each alarm from a background display thread.
- Simulated sensors with configurable baseline, noise, spike chance and interval.

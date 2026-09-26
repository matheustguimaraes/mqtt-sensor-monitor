export const MQTT_WS_URL =
  process.env.EXPO_PUBLIC_MQTT_WS_URL ?? "ws://localhost:9001";
export const MQTT_USERNAME =
  process.env.EXPO_PUBLIC_MQTT_USERNAME?.trim() ?? "";
export const MQTT_PASSWORD =
  process.env.EXPO_PUBLIC_MQTT_PASSWORD?.trim() ?? "";
export const MQTT_TEMPERATURE_TOPIC =
  process.env.EXPO_PUBLIC_MQTT_TEMPERATURE_TOPIC ?? "factory/temperature";
export const PUBLISH_INTERVAL_MS = Number(
  process.env.EXPO_PUBLIC_PUBLISH_INTERVAL_MS ?? 2000,
);


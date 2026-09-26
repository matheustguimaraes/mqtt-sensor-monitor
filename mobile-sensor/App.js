import 'react-native-get-random-values';
import { Buffer } from 'buffer';
import process from 'process';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { StatusBar } from 'expo-status-bar';
import { Accelerometer } from 'expo-sensors';
import mqttImport from 'mqtt';

import {
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';

import {
  MQTT_PASSWORD,
  MQTT_TEMPERATURE_TOPIC,
  MQTT_USERNAME,
  MQTT_WS_URL,
  PUBLISH_INTERVAL_MS,
} from './src/config';

if (!global.Buffer) {
  global.Buffer = Buffer;
}
if (!global.process) {
  global.process = process;
}

const useAccelerometer = () => {
  const [data, setData] = useState({ x: 0, y: 0, z: 0 });

  useEffect(() => {
    Accelerometer.setUpdateInterval(500);
    const subscription = Accelerometer.addListener((reading) => {
      setData(reading);
    });
    return () => subscription?.remove();
  }, []);

  return data;
};

const resolveMqttConnect = () => {
  if (typeof mqttImport === 'function') {
    return mqttImport;
  }
  if (typeof mqttImport.connect === 'function') {
    return mqttImport.connect;
  }
  if (typeof mqttImport.default === 'function') {
    return mqttImport.default;
  }
  if (typeof mqttImport.default?.connect === 'function') {
    return mqttImport.default.connect;
  }
  throw new Error('Unable to resolve MQTT connect function');
};

const mqttConnect = resolveMqttConnect();

export default function App() {
  const clientRef = useRef(null);
  const latestReadingRef = useRef(null);
  const [status, setStatus] = useState('connecting');
  const [autoPublish, setAutoPublish] = useState(true);
  const [lastPayload, setLastPayload] = useState(null);
  const accelerometer = useAccelerometer();

  const deviceId = useMemo(
    () => `mobile-${Math.floor(Math.random() * 1_000_000)}`,
    [],
  );

  const temperature = useMemo(() => {
    const magnitude = Math.sqrt(
      (accelerometer.x ?? 0) ** 2 +
      (accelerometer.y ?? 0) ** 2 +
      (accelerometer.z ?? 0) ** 2,
    );
    return Number((190 + magnitude * 18).toFixed(2));
  }, [accelerometer]);

  useEffect(() => {
    latestReadingRef.current = {
      temperature,
      accelerometer,
    };
  }, [accelerometer, temperature]);

  useEffect(() => {
    const client = mqttConnect(MQTT_WS_URL, {
      clientId: `mobile-sensor-${deviceId}`,
      username: MQTT_USERNAME || undefined,
      password: MQTT_PASSWORD || undefined,
      reconnectPeriod: 3000,
    });
    clientRef.current = client;

    client.on('connect', () => {
      console.log('[MQTT] Connected as', `mobile-sensor-${deviceId}`);
      setStatus('connected');
    });
    client.on('reconnect', () => {
      console.log('[MQTT] Reconnecting…');
      setStatus('reconnecting');
    });
    client.on('close', () => {
      console.log('[MQTT] Connection closed');
      setStatus('disconnected');
    });
    client.on('error', (err) => {
      console.warn('MQTT error', err);
      setStatus('error');
    });

    return () => client.end(true);
  }, [deviceId]);

  const publishReading = useCallback(() => {
    if (!clientRef.current || status !== 'connected') {
      return;
    }
    const snapshot = latestReadingRef.current;
    if (!snapshot) {
      return;
    }

    const payload = {
      sensorId: deviceId,
      source: 'mobile',
      timestamp: new Date().toISOString(),
      epochSeconds: Date.now() / 1000,
      unit: 'C',
      value: snapshot.temperature,
      accelerometer: snapshot.accelerometer,
    };
    const topic = `${MQTT_TEMPERATURE_TOPIC}/${deviceId}`;
    console.log('[MQTT] Publishing payload', {
      topic,
      payload,
    });
    clientRef.current.publish(
      topic,
      JSON.stringify(payload),
      {
        qos: 1,
      },
      (err) => {
        if (err) {
          console.warn('[MQTT] Publish failed', err);
        } else {
          console.log('[MQTT] Publish acknowledged for', topic);
        }
      },
    );
    setLastPayload(payload);
  }, [deviceId, status]);

  useEffect(() => {
    if (!autoPublish) {
      return undefined;
    }
    const interval = setInterval(publishReading, PUBLISH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [autoPublish, publishReading]);

  return (
    <View style={styles.container}>
      <StatusBar style="light" />
      <View style={styles.card}>
        <Text style={styles.title}>Mobile</Text>
        <Text style={styles.subtitle}>ID: {deviceId}</Text>
        <Text style={styles.label}>MQTT status:</Text>
        <Text
          style={[
            styles.value,
            status === 'connected' ? styles.ok : styles.warn,
          ]}
        >
          {status}
        </Text>
        <Text style={styles.label}>Broker (WS):</Text>
        <Text style={styles.small}>{MQTT_WS_URL}</Text>
        <Text style={styles.label}>Topic:</Text>
        <Text style={styles.small}>
          {MQTT_TEMPERATURE_TOPIC}/{deviceId}
        </Text>
        <View style={styles.reading}>
          <Text style={styles.temp}>{temperature.toFixed(2)} °C</Text>
          <Text style={styles.small}>
            |x| {accelerometer.x?.toFixed(2) ?? '0.00'} · |y|{' '}
            {accelerometer.y?.toFixed(2) ?? '0.00'} · |z|{' '}
            {accelerometer.z?.toFixed(2) ?? '0.00'}
          </Text>
        </View>

        <TouchableOpacity
          style={[styles.button, autoPublish ? styles.buttonActive : null]}
          onPress={() => setAutoPublish((prev) => !prev)}
        >
          <Text style={styles.buttonText}>
            {autoPublish ? 'Auto publish ON' : 'Auto publish OFF'}
          </Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.button} onPress={publishReading}>
          <Text style={styles.buttonText}>Send now</Text>
        </TouchableOpacity>

        {lastPayload && (
          <View style={styles.lastPayload}>
            <Text style={styles.label}>Last publish:</Text>
            <Text style={styles.small}>{lastPayload.timestamp}</Text>
            <Text style={styles.small}>{lastPayload.value} °C</Text>
          </View>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0E1116',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
  },
  card: {
    width: '100%',
    backgroundColor: '#1C2431',
    borderRadius: 16,
    padding: 20,
    gap: 8,
  },
  title: {
    color: '#FFFFFF',
    fontSize: 22,
    fontWeight: '600',
  },
  subtitle: {
    color: '#8DA2C0',
    marginBottom: 8,
  },
  label: {
    color: '#8DA2C0',
    fontSize: 12,
  },
  value: {
    fontSize: 18,
    marginBottom: 4,
  },
  ok: {
    color: '#4ADE80',
  },
  warn: {
    color: '#FACC15',
  },
  small: {
    color: '#CBD5F5',
    fontSize: 13,
  },
  reading: {
    marginVertical: 12,
  },
  temp: {
    fontSize: 42,
    fontWeight: 'bold',
    color: '#F97316',
  },
  button: {
    backgroundColor: '#334155',
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: 'center',
  },
  buttonActive: {
    backgroundColor: '#2563EB',
  },
  buttonText: {
    color: '#FFFFFF',
    fontWeight: '600',
  },
  lastPayload: {
    marginTop: 12,
    padding: 12,
    backgroundColor: '#0E1724',
    borderRadius: 10,
  },
});

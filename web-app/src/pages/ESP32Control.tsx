import { useState, useEffect, useCallback } from 'react';

// ============================================
// Types
// ============================================
interface DeviceHealth {
  device_id: string;
  type: string;
  ip: string;
  online: boolean;
  firmware: string;
  last_seen: number;
  age_seconds: number;
  capabilities: string[];
}

interface ServerHeartbeat {
  device: string;
  firmware: string;
  uptime: number;
  free_heap: number;
  rssi: number;
  ip: string;
  door: string;
  lock: string;
  boot_count: number;
  relays: number;
  temperature: number;
  humidity: number;
  motion: boolean;
  voltage: number;
  current: number;
  light: number;
  schedules: number;
}

interface CameraStatus {
  device: string;
  firmware: string;
  uptime: number;
  streaming: boolean;
  fps: number;
  night_mode: boolean;
  patrol: boolean;
  intruder_mode: boolean;
  persons: number;
  motion_events: number;
  captures: number;
  detections: number;
  ambient: number;
}

interface MqttStats {
  messages_received: number;
  messages_sent: number;
  events_routed: number;
  reconnections: number;
  errors: number;
  connected: boolean;
  devices_online: number;
}

// ============================================
// API Base
// ============================================
const JARVIS_API = 'http://localhost:8100';

async function apiGet<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${JARVIS_API}${path}`);
    if (res.ok) return await res.json();
  } catch (err) {
    console.error(`API GET ${path} failed:`, err);
  }
  return null;
}

async function apiPost<T>(path: string, params?: Record<string, string>): Promise<T | null> {
  try {
    const url = new URL(`${JARVIS_API}${path}`);
    if (params) Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
    const res = await fetch(url.toString(), { method: 'POST' });
    if (res.ok) return await res.json();
  } catch (err) {
    console.error(`API POST ${path} failed:`, err);
  }
  return null;
}

// ============================================
// Components
// ============================================
function StatusBadge({ online }: { online: boolean }) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${online ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
      <span className={`w-2 h-2 rounded-full mr-1.5 ${online ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
      {online ? 'Online' : 'Offline'}
    </span>
  );
}

function SensorCard({ label, value, unit, icon }: { label: string; value: string | number; unit?: string; icon: string }) {
  return (
    <div className="bg-gray-800 rounded-lg p-3 flex items-center gap-3">
      <span className="text-2xl">{icon}</span>
      <div>
        <div className="text-gray-400 text-xs">{label}</div>
        <div className="text-white font-semibold">{value}{unit && <span className="text-gray-400 text-sm ml-1">{unit}</span>}</div>
      </div>
    </div>
  );
}

function RelayButton({ index, active, room, onToggle }: { index: number; active: boolean; room: string; onToggle: () => void }) {
  return (
    <button
      onClick={onToggle}
      className={`rounded-lg p-3 text-center transition-all ${active ? 'bg-yellow-600 hover:bg-yellow-700 text-white' : 'bg-gray-700 hover:bg-gray-600 text-gray-300'}`}
    >
      <div className="text-lg">{active ? '💡' : '⚫'}</div>
      <div className="text-xs mt-1">{room}</div>
      <div className="text-xs opacity-60">R{index}</div>
    </button>
  );
}

// ============================================
// Main ESP32 Control Panel Page
// ============================================
export default function ESP32ControlPanel() {
  const [devices, setDevices] = useState<Record<string, DeviceHealth>>({});
  const [heartbeat, setHeartbeat] = useState<ServerHeartbeat | null>(null);
  const [camStatus, setCamStatus] = useState<CameraStatus | null>(null);
  const [mqttStats, setMqttStats] = useState<MqttStats | null>(null);
  const [relays, setRelays] = useState<boolean[]>(Array(8).fill(false));
  const [activeTab, setActiveTab] = useState<'server' | 'camera' | 'mqtt'>('server');
  const [loading, setLoading] = useState(false);

  const rooms = ['Living Room', 'Bedroom', 'Kitchen', 'Bathroom', 'Garage', 'Porch', 'Study', 'Spare'];

  const refresh = useCallback(async () => {
    setLoading(true);
    const [devData, hbData, camData, mqData] = await Promise.all([
      apiGet<Record<string, DeviceHealth>>('/api/esp32/devices'),
      apiGet<ServerHeartbeat>('/api/esp32/server/heartbeat'),
      apiGet<CameraStatus>('/api/esp32/camera/jarvis'),
      apiGet<MqttStats>('/api/esp32/mqtt/stats'),
    ]);
    if (devData) setDevices(devData);
    if (hbData) {
      setHeartbeat(hbData);
      // Parse relay bitmask into boolean array
      const bitmask = hbData.relays || 0;
      setRelays(Array.from({ length: 8 }, (_, i) => Boolean(bitmask & (1 << i))));
    }
    if (camData) setCamStatus(camData);
    if (mqData) setMqttStats(mqData);
    setLoading(false);
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 10000);
    return () => clearInterval(interval);
  }, [refresh]);

  const toggleRelay = async (i: number) => {
    const newState = !relays[i];
    await apiPost('/api/esp32/mqtt/relay', { relay: String(i), state: newState ? 'true' : 'false' });
    setRelays(prev => prev.map((v, idx) => idx === i ? newState : v));
  };

  const toggleLock = async () => {
    const newState = heartbeat?.lock !== 'locked';
    await apiPost('/api/esp32/mqtt/lock', { locked: String(newState) });
    setTimeout(refresh, 1000);
  };

  const triggerCapture = async () => {
    await apiPost('/api/esp32/mqtt/capture', { context: 'dashboard' });
  };

  const togglePatrol = async () => {
    const enabled = !camStatus?.patrol;
    await apiPost('/api/esp32/mqtt/patrol', { enabled: String(enabled) });
    setTimeout(refresh, 1000);
  };

  const toggleIntruder = async () => {
    const enabled = !camStatus?.intruder_mode;
    await apiPost('/api/esp32/mqtt/intruder-mode', { enabled: String(enabled) });
    setTimeout(refresh, 1000);
  };

  const triggerBuzz = async () => {
    await apiPost('/api/esp32/mqtt/buzz', { pattern: 'alert' });
  };

  const allRelays = async (state: boolean) => {
    await apiPost('/api/esp32/server/relays/all', { state: state ? 'true' : 'false' });
    setRelays(Array(8).fill(state));
  };

  const formatUptime = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h}h ${m}m ${s}s`;
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">ESP32 Control Panel</h1>
          <p className="text-gray-400 text-sm">Vision-AI Jarvis - Hardware Management</p>
        </div>
        <div className="flex gap-3">
          <button onClick={refresh} disabled={loading} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm disabled:opacity-50">
            {loading ? '...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Device Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {/* Server Card */}
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <div className="flex justify-between items-center mb-3">
            <h3 className="font-semibold">ESP32 Server</h3>
            <StatusBadge online={!!heartbeat?.device} />
          </div>
          <div className="text-sm text-gray-400 space-y-1">
            <div>IP: {heartbeat?.ip || 'N/A'}</div>
            <div>FW: {heartbeat?.firmware || 'N/A'}</div>
            <div>Uptime: {heartbeat ? formatUptime(heartbeat.uptime) : 'N/A'}</div>
            <div>RSSI: {heartbeat?.rssi || 'N/A'} dBm</div>
          </div>
        </div>

        {/* Camera Card */}
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <div className="flex justify-between items-center mb-3">
            <h3 className="font-semibold">ESP32-CAM</h3>
            <StatusBadge online={!!camStatus?.device} />
          </div>
          <div className="text-sm text-gray-400 space-y-1">
            <div>FPS: {camStatus?.fps?.toFixed(1) || 'N/A'}</div>
            <div>FW: {camStatus?.firmware || 'N/A'}</div>
            <div>Uptime: {camStatus ? formatUptime(camStatus.uptime) : 'N/A'}</div>
            <div>Captures: {camStatus?.captures || 0}</div>
          </div>
        </div>

        {/* MQTT Card */}
        <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
          <div className="flex justify-between items-center mb-3">
            <h3 className="font-semibold">MQTT Bridge</h3>
            <StatusBadge online={mqttStats?.connected || false} />
          </div>
          <div className="text-sm text-gray-400 space-y-1">
            <div>Received: {mqttStats?.messages_received || 0}</div>
            <div>Sent: {mqttStats?.messages_sent || 0}</div>
            <div>Events Routed: {mqttStats?.events_routed || 0}</div>
            <div>Devices: {mqttStats?.devices_online || 0}</div>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-2 mb-4">
        {(['server', 'camera', 'mqtt'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${activeTab === tab ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'}`}
          >
            {tab === 'server' ? 'Server Control' : tab === 'camera' ? 'Camera Control' : 'MQTT Monitor'}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'server' && (
        <div className="space-y-6">
          {!heartbeat && (
            <div className="bg-gray-800 rounded-xl p-8 text-center border border-gray-700">
              <div className="text-4xl mb-4">📡</div>
              <h3 className="text-lg font-semibold mb-2">ESP32 Server Offline</h3>
              <p className="text-gray-400 text-sm">No heartbeat received. The ESP32 server is not connected or the MQTT broker is not running.</p>
              <p className="text-gray-500 text-xs mt-2">Relay controls and sensor data will appear once the device connects.</p>
            </div>
          )}
          {heartbeat && (<div className="space-y-6">
          {/* Sensors */}
          <div>
            <h3 className="text-lg font-semibold mb-3">Sensors</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
              <SensorCard icon="🌡️" label="Temperature" value={heartbeat.temperature?.toFixed(1) || '—'} unit="°C" />
              <SensorCard icon="💧" label="Humidity" value={heartbeat.humidity?.toFixed(1) || '—'} unit="%" />
              <SensorCard icon="⚡" label="Voltage" value={heartbeat.voltage?.toFixed(1) || '—'} unit="V" />
              <SensorCard icon="🔌" label="Current" value={heartbeat.current?.toFixed(2) || '—'} unit="A" />
              <SensorCard icon="💡" label="Light" value={heartbeat.light || '—'} />
              <SensorCard icon="🚶" label="Motion" value={heartbeat.motion ? 'Yes' : 'No'} />
            </div>
          </div>

          {/* Door & Lock */}
          <div>
            <h3 className="text-lg font-semibold mb-3">Door & Lock</h3>
            <div className="flex gap-4 items-center">
              <div className={`rounded-xl p-4 flex items-center gap-3 ${heartbeat.door === 'open' ? 'bg-red-900/50 border border-red-700' : 'bg-green-900/50 border border-green-700'}`}>
                <span className="text-3xl">{heartbeat.door === 'open' ? '🚪' : '🔒'}</span>
                <div>
                  <div className="font-semibold">Door: {heartbeat.door?.toUpperCase()}</div>
                  <div className="text-sm text-gray-400">Reed switch sensor</div>
                </div>
              </div>
              <button
                onClick={toggleLock}
                className={`rounded-xl p-4 flex items-center gap-3 cursor-pointer transition-all ${heartbeat.lock === 'locked' ? 'bg-green-700 hover:bg-green-800' : 'bg-orange-700 hover:bg-orange-800'}`}
              >
                <span className="text-3xl">{heartbeat.lock === 'locked' ? '🔐' : '🔓'}</span>
                <div>
                  <div className="font-semibold">{heartbeat.lock === 'locked' ? 'LOCKED' : 'UNLOCKED'}</div>
                  <div className="text-sm opacity-75">Click to toggle</div>
                </div>
              </button>
              <button onClick={triggerBuzz} className="rounded-xl p-4 bg-red-700 hover:bg-red-800 transition-all">
                <span className="text-3xl">🔔</span>
                <div className="text-sm mt-1">Buzz Alert</div>
              </button>
            </div>
          </div>

          {/* Relays */}
          <div>
            <h3 className="text-lg font-semibold mb-3">Relay Control</h3>
            <div className="flex gap-2 mb-3">
              <button onClick={() => allRelays(true)} className="px-3 py-1 bg-yellow-600 hover:bg-yellow-700 rounded text-sm">All ON</button>
              <button onClick={() => allRelays(false)} className="px-3 py-1 bg-gray-600 hover:bg-gray-700 rounded text-sm">All OFF</button>
            </div>
            <div className="grid grid-cols-4 md:grid-cols-8 gap-3">
              {relays.map((on, i) => (
                <RelayButton key={i} index={i} active={on} room={rooms[i]} onToggle={() => toggleRelay(i)} />
              ))}
            </div>
          </div>

          {/* System Info */}
          <div>
            <h3 className="text-lg font-semibold mb-3">System Info</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <SensorCard icon="💾" label="Free Heap" value={(heartbeat.free_heap / 1024).toFixed(0)} unit="KB" />
              <SensorCard icon="📶" label="WiFi RSSI" value={heartbeat.rssi} unit="dBm" />
              <SensorCard icon="🔄" label="Boot Count" value={heartbeat.boot_count} />
              <SensorCard icon="📋" label="Schedules" value={heartbeat.schedules} />
            </div>
          </div>
        </div>)}
        </div>
      )}

      {activeTab === 'camera' && (
        <div className="space-y-6">
          {/* Camera Controls */}
          <div>
            <h3 className="text-lg font-semibold mb-3">Camera Actions</h3>
            <div className="flex flex-wrap gap-3">
              <button onClick={triggerCapture} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg">📸 Capture + Detect</button>
              <button onClick={togglePatrol} className={`px-4 py-2 rounded-lg ${camStatus?.patrol ? 'bg-green-600 hover:bg-green-700' : 'bg-gray-600 hover:bg-gray-700'}`}>
                🛡️ Patrol: {camStatus?.patrol ? 'ON' : 'OFF'}
              </button>
              <button onClick={toggleIntruder} className={`px-4 py-2 rounded-lg ${camStatus?.intruder_mode ? 'bg-red-600 hover:bg-red-700' : 'bg-gray-600 hover:bg-gray-700'}`}>
                🚨 Intruder Mode: {camStatus?.intruder_mode ? 'ON' : 'OFF'}
              </button>
              <button onClick={() => apiPost('/api/esp32/mqtt/identify')} className="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg">
                👤 Identify Face
              </button>
            </div>
          </div>

          {/* Camera Stats */}
          {camStatus && (
            <div>
              <h3 className="text-lg font-semibold mb-3">Camera Status</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
                <SensorCard icon="🎥" label="Streaming" value={camStatus.streaming ? 'Yes' : 'No'} />
                <SensorCard icon="📊" label="FPS" value={camStatus.fps?.toFixed(1) || '0'} />
                <SensorCard icon="🌙" label="Night Mode" value={camStatus.night_mode ? 'ON' : 'OFF'} />
                <SensorCard icon="☀️" label="Ambient" value={camStatus.ambient} />
                <SensorCard icon="👥" label="Persons" value={camStatus.persons} />
                <SensorCard icon="🚶" label="Motion Events" value={camStatus.motion_events} />
                <SensorCard icon="📸" label="Captures" value={camStatus.captures} />
                <SensorCard icon="🤖" label="AI Detections" value={camStatus.detections} />
              </div>
            </div>
          )}

          {/* Camera Stream */}
          <div>
            <h3 className="text-lg font-semibold mb-3">Live Stream</h3>
            <div className="bg-black rounded-xl overflow-hidden max-w-2xl">
              <img
                src={`http://${camStatus?.device ? '192.168.1.102' : 'localhost'}:81/stream`}
                alt="Camera Stream"
                className="w-full"
                onError={(e) => {
                  (e.target as HTMLImageElement).src = '';
                  (e.target as HTMLImageElement).alt = 'Stream unavailable';
                }}
              />
            </div>
          </div>
        </div>
      )}

      {activeTab === 'mqtt' && (
        <div className="space-y-6">
          {!mqttStats && (
            <div className="bg-gray-800 rounded-xl p-8 text-center border border-gray-700">
              <div className="text-4xl mb-4">🔌</div>
              <h3 className="text-lg font-semibold mb-2">MQTT Bridge Offline</h3>
              <p className="text-gray-400 text-sm">The MQTT bridge service is not connected. Stats and device data will appear once the broker is available.</p>
            </div>
          )}
          {mqttStats && (<div className="space-y-6">
          <div>
            <h3 className="text-lg font-semibold mb-3">MQTT Bridge Statistics</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <SensorCard icon="📥" label="Received" value={mqttStats.messages_received} />
              <SensorCard icon="📤" label="Sent" value={mqttStats.messages_sent} />
              <SensorCard icon="🔀" label="Routed" value={mqttStats.events_routed} />
              <SensorCard icon="❌" label="Errors" value={mqttStats.errors} />
            </div>
          </div>

          {/* Device List */}
          <div>
            <h3 className="text-lg font-semibold mb-3">Connected Devices</h3>
            <div className="bg-gray-800 rounded-xl overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-700">
                  <tr>
                    <th className="px-4 py-2 text-left">Device ID</th>
                    <th className="px-4 py-2 text-left">Type</th>
                    <th className="px-4 py-2 text-left">IP</th>
                    <th className="px-4 py-2 text-left">Status</th>
                    <th className="px-4 py-2 text-left">Firmware</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.values(devices).map((dev) => (
                    <tr key={dev.device_id} className="border-t border-gray-700">
                      <td className="px-4 py-2 font-mono">{dev.device_id}</td>
                      <td className="px-4 py-2">{dev.type}</td>
                      <td className="px-4 py-2">{dev.ip}</td>
                      <td className="px-4 py-2"><StatusBadge online={dev.online} /></td>
                      <td className="px-4 py-2">{dev.firmware}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>)}
        </div>
      )}
    </div>
  );
}

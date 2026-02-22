import { useState } from 'react';
import { Activity, Wifi, Cpu, HardDrive, Thermometer, MemoryStick, Clock, RefreshCw, CheckCircle, AlertTriangle, XCircle, Zap } from 'lucide-react';

// Feature 75: System Health Dashboard - comprehensive system monitoring

interface ServiceHealth {
  name: string;
  status: 'healthy' | 'degraded' | 'down';
  uptime: string;
  latency: number;
  cpu: number;
  memory: number;
  version: string;
}

interface DeviceHealth {
  name: string;
  type: string;
  status: 'online' | 'warning' | 'offline';
  rssi: number;
  temperature: number;
  uptime: string;
  freeHeap: number;
  lastSeen: string;
}

const SERVICES: ServiceHealth[] = [
  { name: 'AI Engine', status: 'healthy', uptime: '99.9%', latency: 12, cpu: 45, memory: 62, version: '3.0.0' },
  { name: 'Jarvis API', status: 'healthy', uptime: '99.8%', latency: 8, cpu: 22, memory: 38, version: '3.0.0' },
  { name: 'Web App', status: 'healthy', uptime: '100%', latency: 3, cpu: 5, memory: 15, version: '1.0.0' },
  { name: 'Database', status: 'healthy', uptime: '100%', latency: 2, cpu: 8, memory: 45, version: 'SQLite 3.40' },
  { name: 'MQTT Broker', status: 'degraded', uptime: '98.5%', latency: 45, cpu: 15, memory: 20, version: '2.0.18' },
  { name: 'Redis Cache', status: 'down', uptime: '0%', latency: 0, cpu: 0, memory: 0, version: '7.2' },
];

const DEVICES: DeviceHealth[] = [
  { name: 'ESP32-CAM-01', type: 'Camera', status: 'online', rssi: -52, temperature: 42, uptime: '5d 12h', freeHeap: 45000, lastSeen: '2s ago' },
  { name: 'ESP32-CAM-02', type: 'Camera', status: 'online', rssi: -68, temperature: 38, uptime: '3d 8h', freeHeap: 52000, lastSeen: '1s ago' },
  { name: 'ESP32-Server', type: 'Controller', status: 'online', rssi: -45, temperature: 35, uptime: '12d 4h', freeHeap: 78000, lastSeen: '0s ago' },
  { name: 'ESP32-CAM-03', type: 'Camera', status: 'offline', rssi: 0, temperature: 0, uptime: '-', freeHeap: 0, lastSeen: '2h ago' },
  { name: 'Sensor Hub', type: 'Sensor', status: 'warning', rssi: -78, temperature: 55, uptime: '1d 2h', freeHeap: 12000, lastSeen: '30s ago' },
];

const STATUS_CONFIG = {
  healthy: { icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-500/10' },
  degraded: { icon: AlertTriangle, color: 'text-yellow-400', bg: 'bg-yellow-500/10' },
  down: { icon: XCircle, color: 'text-red-400', bg: 'bg-red-500/10' },
  online: { icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-500/10' },
  warning: { icon: AlertTriangle, color: 'text-yellow-400', bg: 'bg-yellow-500/10' },
  offline: { icon: XCircle, color: 'text-red-400', bg: 'bg-red-500/10' },
};

function HealthBar({ value, max = 100, color = 'bg-primary-500', warn = 70, danger = 90 }: { value: number; max?: number; color?: string; warn?: number; danger?: number }) {
  const pct = (value / max) * 100;
  const barColor = pct >= danger ? 'bg-red-500' : pct >= warn ? 'bg-yellow-500' : color;
  return (
    <div className="w-full bg-dark-700 rounded-full h-1.5">
      <div className={`${barColor} h-1.5 rounded-full transition-all`} style={{ width: `${Math.min(pct, 100)}%` }} />
    </div>
  );
}

export default function SystemHealth() {
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval] = useState(5);

  const overallHealth = SERVICES.every(s => s.status === 'healthy') ? 'All Systems Operational' :
    SERVICES.some(s => s.status === 'down') ? 'System Outage Detected' : 'Degraded Performance';
  const overallColor = SERVICES.every(s => s.status === 'healthy') ? 'text-green-400' :
    SERVICES.some(s => s.status === 'down') ? 'text-red-400' : 'text-yellow-400';

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2"><Activity size={24} /> System Health</h1>
          <p className={`text-sm mt-1 ${overallColor}`}>{overallHealth}</p>
        </div>
        <button onClick={() => setAutoRefresh(!autoRefresh)}
          className={`btn ${autoRefresh ? 'btn-primary' : 'btn-secondary'} flex items-center gap-1`}>
          <RefreshCw size={14} className={autoRefresh ? 'animate-spin' : ''} />
          {autoRefresh ? `Auto (${refreshInterval}s)` : 'Manual'}
        </button>
      </div>

      {/* System Overview */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {SERVICES.map(svc => {
          const cfg = STATUS_CONFIG[svc.status];
          const Icon = cfg.icon;
          return (
            <div key={svc.name} className={`card p-4 border ${svc.status === 'down' ? 'border-red-500/30' : svc.status === 'degraded' ? 'border-yellow-500/30' : 'border-transparent'}`}>
              <div className="flex items-center gap-2 mb-2">
                <Icon size={14} className={cfg.color} />
                <span className={`text-xs font-medium ${cfg.color}`}>{svc.status}</span>
              </div>
              <div className="font-semibold text-white text-sm">{svc.name}</div>
              <div className="text-xs text-dark-400 mt-1">v{svc.version}</div>
              {svc.status !== 'down' && (
                <div className="mt-2 text-xs text-dark-400">
                  <span>{svc.latency}ms</span> &middot; <span>{svc.uptime}</span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Service Details */}
      <div className="card overflow-hidden">
        <div className="p-4 border-b border-dark-700">
          <h2 className="font-semibold text-white flex items-center gap-2"><Cpu size={16} /> Service Resources</h2>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-dark-700 text-dark-400">
              <th className="px-4 py-3 text-left">Service</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">CPU</th>
              <th className="px-4 py-3 text-left">Memory</th>
              <th className="px-4 py-3 text-left">Latency</th>
              <th className="px-4 py-3 text-left">Uptime</th>
            </tr>
          </thead>
          <tbody>
            {SERVICES.map(svc => {
              const cfg = STATUS_CONFIG[svc.status];
              const Icon = cfg.icon;
              return (
                <tr key={svc.name} className="border-b border-dark-800 hover:bg-dark-700/20">
                  <td className="px-4 py-3 text-white font-medium">{svc.name}</td>
                  <td className="px-4 py-3">
                    <span className={`flex items-center gap-1 text-xs ${cfg.color}`}><Icon size={12} /> {svc.status}</span>
                  </td>
                  <td className="px-4 py-3 w-32">
                    <div className="flex items-center gap-2">
                      <HealthBar value={svc.cpu} color="bg-blue-500" />
                      <span className="text-xs text-dark-400 w-8">{svc.cpu}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 w-32">
                    <div className="flex items-center gap-2">
                      <HealthBar value={svc.memory} color="bg-purple-500" />
                      <span className="text-xs text-dark-400 w-8">{svc.memory}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-dark-300">{svc.latency > 0 ? `${svc.latency}ms` : '-'}</td>
                  <td className="px-4 py-3 text-dark-300">{svc.uptime}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Device Health */}
      <div className="card overflow-hidden">
        <div className="p-4 border-b border-dark-700">
          <h2 className="font-semibold text-white flex items-center gap-2"><Wifi size={16} /> Device Health</h2>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-dark-700 text-dark-400">
              <th className="px-4 py-3 text-left">Device</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">WiFi Signal</th>
              <th className="px-4 py-3 text-left">Temperature</th>
              <th className="px-4 py-3 text-left">Free Heap</th>
              <th className="px-4 py-3 text-left">Uptime</th>
              <th className="px-4 py-3 text-left">Last Seen</th>
            </tr>
          </thead>
          <tbody>
            {DEVICES.map(dev => {
              const cfg = STATUS_CONFIG[dev.status];
              const Icon = cfg.icon;
              return (
                <tr key={dev.name} className="border-b border-dark-800 hover:bg-dark-700/20">
                  <td className="px-4 py-3">
                    <div className="text-white font-medium">{dev.name}</div>
                    <div className="text-xs text-dark-400">{dev.type}</div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`flex items-center gap-1 text-xs ${cfg.color}`}><Icon size={12} /> {dev.status}</span>
                  </td>
                  <td className="px-4 py-3">
                    {dev.rssi !== 0 ? (
                      <div className="flex items-center gap-2">
                        <Wifi size={12} className={dev.rssi > -60 ? 'text-green-400' : dev.rssi > -70 ? 'text-yellow-400' : 'text-red-400'} />
                        <span className="text-dark-300 text-xs">{dev.rssi} dBm</span>
                      </div>
                    ) : <span className="text-dark-500">-</span>}
                  </td>
                  <td className="px-4 py-3">
                    {dev.temperature > 0 ? (
                      <span className={`text-xs ${dev.temperature > 50 ? 'text-red-400' : dev.temperature > 40 ? 'text-yellow-400' : 'text-green-400'}`}>
                        {dev.temperature}°C
                      </span>
                    ) : <span className="text-dark-500">-</span>}
                  </td>
                  <td className="px-4 py-3 text-dark-300 text-xs">{dev.freeHeap > 0 ? `${(dev.freeHeap / 1024).toFixed(1)} KB` : '-'}</td>
                  <td className="px-4 py-3 text-dark-300 text-xs">{dev.uptime}</td>
                  <td className="px-4 py-3 text-dark-300 text-xs">{dev.lastSeen}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

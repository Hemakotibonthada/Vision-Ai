import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { deviceApi } from '../services/api';
import toast from 'react-hot-toast';
import {
  Cpu, Wifi, WifiOff, Plus, Settings2, Terminal, Thermometer,
  Droplets, Activity, Battery, Trash2, RefreshCw, Send, Eye
} from 'lucide-react';

export default function Devices() {
  const queryClient = useQueryClient();
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [newDevice, setNewDevice] = useState({ device_id: '', name: '', device_type: 'esp32', ip_address: '' });
  const [command, setCommand] = useState('');

  const { data: devices, isLoading } = useQuery({
    queryKey: ['devices'],
    queryFn: () => deviceApi.list(),
    refetchInterval: 15000,
  });

  const { data: deviceStatus } = useQuery({
    queryKey: ['deviceStatus', selectedDevice],
    queryFn: () => selectedDevice ? deviceApi.getStatus(selectedDevice) : null,
    enabled: !!selectedDevice,
    refetchInterval: 10000,
  });

  const { data: sensorData } = useQuery({
    queryKey: ['sensors', selectedDevice],
    queryFn: () => selectedDevice ? deviceApi.getSensors(selectedDevice, 24) : null,
    enabled: !!selectedDevice,
  });

  const registerMutation = useMutation({
    mutationFn: (data: any) => deviceApi.register(data),
    onSuccess: () => {
      toast.success('Device registered!');
      queryClient.invalidateQueries({ queryKey: ['devices'] });
      setShowAdd(false);
      setNewDevice({ device_id: '', name: '', device_type: 'esp32', ip_address: '' });
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Failed to register'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deviceApi.delete(id),
    onSuccess: () => {
      toast.success('Device removed');
      queryClient.invalidateQueries({ queryKey: ['devices'] });
      setSelectedDevice(null);
    },
  });

  const sendCommandMutation = useMutation({
    mutationFn: ({ deviceId, cmd }: { deviceId: string; cmd: any }) => deviceApi.sendCommand(deviceId, cmd),
    onSuccess: () => toast.success('Command sent!'),
    onError: () => toast.error('Failed to send command'),
  });

  const devs = devices?.data || [];
  const status = deviceStatus?.data;
  const sensors = sensorData?.data || [];

  const quickCommands = [
    { label: 'Restart', cmd: { action: 'restart' }, color: 'btn-danger' },
    { label: 'Status', cmd: { action: 'status' }, color: 'btn-secondary' },
    { label: 'Capture', cmd: { action: 'capture' }, color: 'btn-primary' },
    { label: 'Flash On', cmd: { action: 'flash', value: 255 }, color: 'btn-secondary' },
    { label: 'Flash Off', cmd: { action: 'flash', value: 0 }, color: 'btn-secondary' },
    { label: 'LED On', cmd: { action: 'led', r: 0, g: 255, b: 0 }, color: 'btn-success' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Device Management</h2>
          <p className="text-sm text-dark-400">{devs.length} devices registered, {devs.filter((d: any) => d.is_active).length} online</p>
        </div>
        <button onClick={() => setShowAdd(true)} className="btn-primary flex items-center gap-2">
          <Plus size={16} /> Add Device
        </button>
      </div>

      {/* Add Device Modal */}
      {showAdd && (
        <div className="card border-primary-500/30">
          <h3 className="font-semibold mb-3">Register New Device</h3>
          <div className="grid grid-cols-2 gap-3">
            <input className="input" placeholder="Device ID" value={newDevice.device_id} onChange={(e) => setNewDevice({ ...newDevice, device_id: e.target.value })} />
            <input className="input" placeholder="Name" value={newDevice.name} onChange={(e) => setNewDevice({ ...newDevice, name: e.target.value })} />
            <select className="select" value={newDevice.device_type} onChange={(e) => setNewDevice({ ...newDevice, device_type: e.target.value })}>
              <option value="esp32">ESP32 Server</option>
              <option value="esp32-cam">ESP32-CAM</option>
              <option value="sensor">Sensor Node</option>
            </select>
            <input className="input" placeholder="IP Address" value={newDevice.ip_address} onChange={(e) => setNewDevice({ ...newDevice, ip_address: e.target.value })} />
          </div>
          <div className="flex gap-2 mt-3">
            <button onClick={() => registerMutation.mutate(newDevice)} className="btn-primary">Register</button>
            <button onClick={() => setShowAdd(false)} className="btn-secondary">Cancel</button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Device List */}
        <div className="space-y-3">
          {isLoading ? (
            <div className="card text-center py-8 text-dark-400">Loading devices...</div>
          ) : devs.length === 0 ? (
            <div className="card text-center py-8">
              <Cpu size={40} className="mx-auto text-dark-600 mb-3" />
              <p className="text-dark-400">No devices registered</p>
            </div>
          ) : (
            devs.map((dev: any) => (
              <div
                key={dev.device_id}
                onClick={() => setSelectedDevice(dev.device_id)}
                className={`card-hover cursor-pointer ${selectedDevice === dev.device_id ? 'border-primary-500/50' : ''}`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      dev.is_active ? 'bg-green-500/10' : 'bg-red-500/10'
                    }`}>
                      {dev.is_active ? <Wifi size={20} className="text-green-400" /> : <WifiOff size={20} className="text-red-400" />}
                    </div>
                    <div>
                      <h4 className="font-medium text-sm">{dev.name}</h4>
                      <p className="text-xs text-dark-400">{dev.device_type} | {dev.ip_address || 'No IP'}</p>
                    </div>
                  </div>
                  <span className={dev.is_active ? 'badge-success' : 'badge-danger'}>
                    {dev.is_active ? 'Online' : 'Offline'}
                  </span>
                </div>
                {dev.firmware_version && (
                  <div className="mt-2 text-xs text-dark-500">Firmware: {dev.firmware_version}</div>
                )}
              </div>
            ))
          )}
        </div>

        {/* Device Details */}
        <div className="lg:col-span-2 space-y-4">
          {selectedDevice ? (
            <>
              {/* Status */}
              <div className="card">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold">Device Status</h3>
                  <div className="flex gap-2">
                    <button onClick={() => queryClient.invalidateQueries({ queryKey: ['deviceStatus'] })} className="btn-secondary p-2">
                      <RefreshCw size={14} />
                    </button>
                    <button onClick={() => deleteMutation.mutate(selectedDevice)} className="btn-danger p-2">
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
                {status && (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <StatusItem label="Status" value={status.online ? 'Online' : 'Offline'} color={status.online ? 'text-green-400' : 'text-red-400'} />
                    <StatusItem label="Name" value={status.device?.name} />
                    <StatusItem label="Firmware" value={status.device?.firmware || 'N/A'} />
                    <StatusItem label="Last Seen" value={status.device?.last_seen?.split('T')[1]?.slice(0, 8) || 'N/A'} />
                  </div>
                )}
              </div>

              {/* Quick Commands */}
              <div className="card">
                <h3 className="font-semibold mb-3">Quick Commands</h3>
                <div className="flex flex-wrap gap-2 mb-3">
                  {quickCommands.map(({ label, cmd, color }) => (
                    <button
                      key={label}
                      onClick={() => sendCommandMutation.mutate({ deviceId: selectedDevice, cmd })}
                      className={`${color} text-sm`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                <div className="flex gap-2">
                  <input
                    className="input flex-1"
                    placeholder='Custom command JSON: {"action": "..."}'
                    value={command}
                    onChange={(e) => setCommand(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && command) {
                        try {
                          sendCommandMutation.mutate({ deviceId: selectedDevice, cmd: JSON.parse(command) });
                          setCommand('');
                        } catch { toast.error('Invalid JSON'); }
                      }
                    }}
                  />
                  <button
                    onClick={() => {
                      try {
                        sendCommandMutation.mutate({ deviceId: selectedDevice, cmd: JSON.parse(command) });
                        setCommand('');
                      } catch { toast.error('Invalid JSON'); }
                    }}
                    className="btn-primary"
                  >
                    <Send size={16} />
                  </button>
                </div>
              </div>

              {/* Sensor Data */}
              <div className="card">
                <h3 className="font-semibold mb-3">Recent Sensor Data</h3>
                <div className="max-h-64 overflow-y-auto space-y-2">
                  {sensors.length === 0 ? (
                    <p className="text-dark-400 text-sm">No sensor data</p>
                  ) : (
                    sensors.slice(0, 20).map((s: any) => (
                      <div key={s.id} className="flex items-center justify-between p-2 bg-dark-900 rounded-lg text-sm">
                        <div className="flex items-center gap-2">
                          <SensorIcon type={s.sensor_type} />
                          <span>{s.sensor_type}</span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="font-mono text-white">{s.value}{s.unit ? ` ${s.unit}` : ''}</span>
                          <span className="text-dark-500 text-xs">{s.created_at?.split('T')[1]?.slice(0, 8)}</span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="card text-center py-20">
              <Eye size={48} className="mx-auto text-dark-600 mb-4" />
              <h3 className="text-lg font-semibold text-dark-300">Select a Device</h3>
              <p className="text-dark-500 mt-1">Click on a device to view details and controls</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatusItem({ label, value, color = 'text-white' }: { label: string; value: string; color?: string }) {
  return (
    <div className="p-3 bg-dark-900 rounded-lg">
      <div className="text-xs text-dark-400">{label}</div>
      <div className={`text-sm font-medium ${color}`}>{value}</div>
    </div>
  );
}

function SensorIcon({ type }: { type: string }) {
  switch (type) {
    case 'temperature': return <Thermometer size={14} className="text-red-400" />;
    case 'humidity': return <Droplets size={14} className="text-blue-400" />;
    case 'battery': return <Battery size={14} className="text-yellow-400" />;
    default: return <Activity size={14} className="text-dark-400" />;
  }
}

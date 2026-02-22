import { useState } from 'react';
import { Map, Layers, Eye, ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';

// Feature 55: Heatmap Visualization - shows detection density overlay
// Feature 61: Device Map - floor plan with device positions

const ZONES = [
  { id: 1, name: 'Living Room', x: 10, y: 10, w: 35, h: 40, detections: 45, color: 'rgba(255,100,100,' },
  { id: 2, name: 'Kitchen', x: 50, y: 10, w: 25, h: 25, detections: 23, color: 'rgba(255,180,50,' },
  { id: 3, name: 'Bedroom', x: 10, y: 55, w: 30, h: 35, detections: 8, color: 'rgba(50,180,255,' },
  { id: 4, name: 'Bathroom', x: 50, y: 40, w: 18, h: 20, detections: 5, color: 'rgba(100,255,100,' },
  { id: 5, name: 'Hallway', x: 45, y: 60, w: 10, h: 30, detections: 30, color: 'rgba(255,150,50,' },
  { id: 6, name: 'Garage', x: 75, y: 10, w: 20, h: 45, detections: 12, color: 'rgba(180,100,255,' },
  { id: 7, name: 'Porch', x: 75, y: 60, w: 20, h: 30, detections: 35, color: 'rgba(255,80,80,' },
];

const DEVICES = [
  { id: 'd1', name: 'ESP32-CAM-01', type: 'camera', x: 25, y: 20, status: 'online' },
  { id: 'd2', name: 'ESP32-CAM-02', type: 'camera', x: 80, y: 70, status: 'online' },
  { id: 'd3', name: 'ESP32-Server', type: 'server', x: 55, y: 15, status: 'online' },
  { id: 'd4', name: 'Temp Sensor 1', type: 'sensor', x: 20, y: 65, status: 'online' },
  { id: 'd5', name: 'Door Sensor', type: 'sensor', x: 48, y: 75, status: 'warning' },
  { id: 'd6', name: 'Motion PIR', type: 'sensor', x: 35, y: 30, status: 'online' },
  { id: 'd7', name: 'ESP32-CAM-03', type: 'camera', x: 82, y: 25, status: 'offline' },
];

const STATUS_COLORS = { online: '#10b981', warning: '#f59e0b', offline: '#ef4444' };
const DEVICE_SHAPES = { camera: '🎥', server: '🖥️', sensor: '📡' };

export default function HeatmapView() {
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [showDevices, setShowDevices] = useState(true);
  const [showLabels, setShowLabels] = useState(true);
  const [zoom, setZoom] = useState(1);
  const [selectedZone, setSelectedZone] = useState<number | null>(null);
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null);
  const maxDet = Math.max(...ZONES.map(z => z.detections));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2"><Map size={24} /> Heatmap & Device Map</h1>
          <p className="text-dark-400 text-sm mt-1">Detection density and device positions</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setZoom(Math.min(zoom + 0.2, 2))} className="btn btn-secondary p-2"><ZoomIn size={16} /></button>
          <button onClick={() => setZoom(Math.max(zoom - 0.2, 0.5))} className="btn btn-secondary p-2"><ZoomOut size={16} /></button>
          <button onClick={() => setZoom(1)} className="btn btn-secondary p-2"><RotateCcw size={16} /></button>
        </div>
      </div>

      {/* Controls */}
      <div className="card p-4 flex flex-wrap gap-4">
        <label className="flex items-center gap-2 text-sm text-dark-300 cursor-pointer">
          <input type="checkbox" checked={showHeatmap} onChange={() => setShowHeatmap(!showHeatmap)} className="rounded" />
          <Layers size={14} /> Heatmap Overlay
        </label>
        <label className="flex items-center gap-2 text-sm text-dark-300 cursor-pointer">
          <input type="checkbox" checked={showDevices} onChange={() => setShowDevices(!showDevices)} className="rounded" />
          <Eye size={14} /> Devices
        </label>
        <label className="flex items-center gap-2 text-sm text-dark-300 cursor-pointer">
          <input type="checkbox" checked={showLabels} onChange={() => setShowLabels(!showLabels)} className="rounded" />
          Labels
        </label>
        <div className="ml-auto flex items-center gap-4 text-xs text-dark-400">
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-green-500" /> Online</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-yellow-500" /> Warning</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-red-500" /> Offline</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Floor Plan */}
        <div className="lg:col-span-3 card p-6">
          <div className="relative bg-dark-800 rounded-xl overflow-hidden" style={{ paddingBottom: '60%', transform: `scale(${zoom})`, transformOrigin: 'top left' }}>
            <div className="absolute inset-0">
              {/* Grid lines */}
              <svg className="absolute inset-0 w-full h-full" xmlns="http://www.w3.org/2000/svg">
                {Array.from({ length: 10 }, (_, i) => (
                  <line key={`h${i}`} x1="0" y1={`${(i + 1) * 10}%`} x2="100%" y2={`${(i + 1) * 10}%`} stroke="#333" strokeWidth="0.5" strokeDasharray="4" />
                ))}
                {Array.from({ length: 10 }, (_, i) => (
                  <line key={`v${i}`} x1={`${(i + 1) * 10}%`} y1="0" x2={`${(i + 1) * 10}%`} y2="100%" stroke="#333" strokeWidth="0.5" strokeDasharray="4" />
                ))}
              </svg>

              {/* Heatmap zones */}
              {showHeatmap && ZONES.map(zone => {
                const opacity = 0.15 + (zone.detections / maxDet) * 0.45;
                return (
                  <div key={zone.id}
                    onClick={() => setSelectedZone(selectedZone === zone.id ? null : zone.id)}
                    className={`absolute rounded-lg cursor-pointer transition-all border ${selectedZone === zone.id ? 'border-white ring-2 ring-white/30' : 'border-white/10'}`}
                    style={{ left: `${zone.x}%`, top: `${zone.y}%`, width: `${zone.w}%`, height: `${zone.h}%`, background: `${zone.color}${opacity})` }}>
                    {showLabels && (
                      <div className="absolute inset-0 flex flex-col items-center justify-center">
                        <span className="text-xs font-medium text-white/80">{zone.name}</span>
                        <span className="text-xs text-white/60">{zone.detections} detections</span>
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Devices */}
              {showDevices && DEVICES.map(dev => (
                <div key={dev.id}
                  onClick={() => setSelectedDevice(selectedDevice === dev.id ? null : dev.id)}
                  className={`absolute transform -translate-x-1/2 -translate-y-1/2 cursor-pointer transition-all ${selectedDevice === dev.id ? 'scale-150 z-20' : 'z-10 hover:scale-125'}`}
                  style={{ left: `${dev.x}%`, top: `${dev.y}%` }}>
                  <div className="relative">
                    <span className="text-lg">{DEVICE_SHAPES[dev.type as keyof typeof DEVICE_SHAPES]}</span>
                    <span className="absolute -bottom-1 -right-1 w-2.5 h-2.5 rounded-full border border-dark-800"
                      style={{ backgroundColor: STATUS_COLORS[dev.status as keyof typeof STATUS_COLORS] }} />
                  </div>
                  {showLabels && (
                    <div className="absolute top-full left-1/2 -translate-x-1/2 mt-1 whitespace-nowrap text-[9px] text-white/70 bg-dark-900/80 px-1 rounded">
                      {dev.name}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Detail Panel */}
        <div className="space-y-4">
          {selectedZone && (
            <div className="card p-4">
              <h3 className="font-semibold text-white mb-2">Zone Details</h3>
              {(() => { const z = ZONES.find(z => z.id === selectedZone)!; return (
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between"><span className="text-dark-400">Name</span><span className="text-white">{z.name}</span></div>
                  <div className="flex justify-between"><span className="text-dark-400">Detections</span><span className="text-white">{z.detections}</span></div>
                  <div className="flex justify-between"><span className="text-dark-400">Density</span>
                    <span className={`${z.detections > 30 ? 'text-red-400' : z.detections > 15 ? 'text-yellow-400' : 'text-green-400'}`}>
                      {z.detections > 30 ? 'High' : z.detections > 15 ? 'Medium' : 'Low'}
                    </span>
                  </div>
                  <div className="w-full bg-dark-700 rounded-full h-2 mt-2">
                    <div className="bg-primary-500 h-2 rounded-full" style={{ width: `${(z.detections / maxDet) * 100}%` }} />
                  </div>
                </div>
              );})()}
            </div>
          )}
          {selectedDevice && (
            <div className="card p-4">
              <h3 className="font-semibold text-white mb-2">Device Details</h3>
              {(() => { const d = DEVICES.find(d => d.id === selectedDevice)!; return (
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between"><span className="text-dark-400">Name</span><span className="text-white">{d.name}</span></div>
                  <div className="flex justify-between"><span className="text-dark-400">Type</span><span className="text-white capitalize">{d.type}</span></div>
                  <div className="flex justify-between"><span className="text-dark-400">Status</span>
                    <span style={{ color: STATUS_COLORS[d.status as keyof typeof STATUS_COLORS] }} className="capitalize">{d.status}</span>
                  </div>
                  <div className="flex justify-between"><span className="text-dark-400">Position</span><span className="text-white">({d.x}, {d.y})</span></div>
                </div>
              );})()}
            </div>
          )}
          <div className="card p-4">
            <h3 className="font-semibold text-white mb-3">Summary</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between text-dark-300"><span>Total Zones</span><span>{ZONES.length}</span></div>
              <div className="flex justify-between text-dark-300"><span>Total Devices</span><span>{DEVICES.length}</span></div>
              <div className="flex justify-between text-dark-300"><span>Online</span><span className="text-green-400">{DEVICES.filter(d => d.status === 'online').length}</span></div>
              <div className="flex justify-between text-dark-300"><span>Offline</span><span className="text-red-400">{DEVICES.filter(d => d.status === 'offline').length}</span></div>
              <div className="flex justify-between text-dark-300"><span>Total Detections</span><span>{ZONES.reduce((a, z) => a + z.detections, 0)}</span></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

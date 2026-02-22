import { useState, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { deviceApi } from '../services/api';
import { wsService } from '../services/websocket';
import { useDetectionStore } from '../store';
import {
  Camera, Maximize2, Grid3X3, Settings2, Pause, Play, Volume2, VolumeX,
  ZoomIn, ZoomOut, RotateCw, Download, Sun, Moon, Crosshair, FlipHorizontal
} from 'lucide-react';

export default function LiveFeed() {
  const [selectedCamera, setSelectedCamera] = useState<string | null>(null);
  const [gridMode, setGridMode] = useState(false);
  const [playing, setPlaying] = useState(true);
  const [showOverlay, setShowOverlay] = useState(true);
  const [zoom, setZoom] = useState(1);
  const [brightness, setBrightness] = useState(100);
  const [contrast, setContrast] = useState(100);
  const [showSettings, setShowSettings] = useState(false);
  const { liveDetections, setLiveDetections } = useDetectionStore();
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const { data: devices } = useQuery({
    queryKey: ['devices'],
    queryFn: () => deviceApi.list({ device_type: 'esp32-cam' }),
  });

  const cameras = devices?.data || [];

  useEffect(() => {
    wsService.connect('detections');
    const off = wsService.on('detection_result', (data: any) => {
      setLiveDetections(data.data?.detections || []);
    });
    return () => { off(); };
  }, []);

  const getStreamUrl = (deviceId: string) => {
    const device = cameras.find((c: any) => c.device_id === deviceId);
    return device?.ip_address ? `http://${device.ip_address}:81/stream` : '';
  };

  const captureFrame = (deviceId: string) => {
    deviceApi.sendCommand(deviceId, { action: 'capture' });
  };

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="card flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Camera size={20} className="text-primary-400" />
            <select
              className="select w-48"
              value={selectedCamera || ''}
              onChange={(e) => setSelectedCamera(e.target.value || null)}
            >
              <option value="">All Cameras</option>
              {cameras.map((c: any) => (
                <option key={c.device_id} value={c.device_id}>{c.name}</option>
              ))}
            </select>
          </div>
          <button onClick={() => setGridMode(!gridMode)} className={`btn-secondary ${gridMode ? '!bg-primary-600 !text-white' : ''}`}>
            <Grid3X3 size={18} />
          </button>
          <button onClick={() => setPlaying(!playing)} className="btn-secondary">
            {playing ? <Pause size={18} /> : <Play size={18} />}
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button onClick={() => setZoom(Math.max(0.5, zoom - 0.25))} className="btn-secondary p-2"><ZoomOut size={16} /></button>
          <span className="text-sm text-dark-300 w-12 text-center">{(zoom * 100).toFixed(0)}%</span>
          <button onClick={() => setZoom(Math.min(3, zoom + 0.25))} className="btn-secondary p-2"><ZoomIn size={16} /></button>
          <button onClick={() => setShowOverlay(!showOverlay)} className={`btn-secondary p-2 ${showOverlay ? '!text-primary-400' : ''}`}>
            <Crosshair size={16} />
          </button>
          <button onClick={() => setShowSettings(!showSettings)} className="btn-secondary p-2"><Settings2 size={16} /></button>
        </div>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div className="card grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <label className="text-sm text-dark-400">Brightness</label>
            <input type="range" min={50} max={200} value={brightness} onChange={(e) => setBrightness(+e.target.value)} className="w-full mt-1" />
            <span className="text-xs text-dark-500">{brightness}%</span>
          </div>
          <div>
            <label className="text-sm text-dark-400">Contrast</label>
            <input type="range" min={50} max={200} value={contrast} onChange={(e) => setContrast(+e.target.value)} className="w-full mt-1" />
            <span className="text-xs text-dark-500">{contrast}%</span>
          </div>
          <div className="flex items-end gap-2">
            <button className="btn-secondary text-sm" onClick={() => { setBrightness(100); setContrast(100); setZoom(1); }}>Reset</button>
          </div>
          <div className="flex items-end gap-2">
            {selectedCamera && <button className="btn-primary text-sm" onClick={() => captureFrame(selectedCamera)}>
              <Download size={14} className="inline mr-1" /> Capture
            </button>}
          </div>
        </div>
      )}

      {/* Video Grid */}
      <div className={`grid gap-4 ${gridMode ? 'grid-cols-2 lg:grid-cols-3' : 'grid-cols-1'}`}>
        {cameras.length === 0 ? (
          <div className="card col-span-full text-center py-20">
            <Camera size={48} className="mx-auto text-dark-600 mb-4" />
            <h3 className="text-lg font-semibold text-dark-300">No Cameras Connected</h3>
            <p className="text-dark-500 mt-2">Connect an ESP32-CAM device to start streaming</p>
          </div>
        ) : (
          cameras
            .filter((c: any) => !selectedCamera || c.device_id === selectedCamera)
            .map((camera: any) => (
              <div key={camera.device_id} className="card-hover relative group overflow-hidden">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${camera.is_active ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
                    <span className="text-sm font-medium">{camera.name}</span>
                  </div>
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button className="p-1 hover:bg-dark-600 rounded" onClick={() => captureFrame(camera.device_id)}>
                      <Download size={14} />
                    </button>
                    <button className="p-1 hover:bg-dark-600 rounded">
                      <Maximize2 size={14} />
                    </button>
                  </div>
                </div>
                <div
                  className="relative bg-dark-900 rounded-lg overflow-hidden"
                  style={{
                    filter: `brightness(${brightness}%) contrast(${contrast}%)`,
                    transform: `scale(${zoom})`,
                    transformOrigin: 'center',
                  }}
                >
                  {camera.is_active && playing ? (
                    <img
                      src={getStreamUrl(camera.device_id)}
                      alt={camera.name}
                      className="w-full aspect-video object-cover"
                      onError={(e) => { (e.target as HTMLImageElement).src = ''; }}
                    />
                  ) : (
                    <div className="w-full aspect-video flex items-center justify-center text-dark-500">
                      <Camera size={40} />
                    </div>
                  )}
                  {/* Detection Overlay */}
                  {showOverlay && liveDetections.length > 0 && camera.device_id === selectedCamera && (
                    <svg className="absolute inset-0 w-full h-full pointer-events-none">
                      {liveDetections.map((det: any, i: number) => (
                        <g key={i}>
                          <rect
                            x={`${det.x1}%`} y={`${det.y1}%`}
                            width={`${det.x2 - det.x1}%`} height={`${det.y2 - det.y1}%`}
                            fill="none" stroke="#22c55e" strokeWidth={2}
                          />
                          <text x={`${det.x1}%`} y={`${det.y1 - 1}%`} fill="#22c55e" fontSize={12}>
                            {det.class} ({(det.confidence * 100).toFixed(0)}%)
                          </text>
                        </g>
                      ))}
                    </svg>
                  )}
                </div>
                <div className="flex items-center justify-between mt-2 text-xs text-dark-500">
                  <span>{camera.ip_address}</span>
                  <span>{camera.firmware_version || 'v1.0'}</span>
                </div>
              </div>
            ))
        )}
      </div>

      {/* Live Detection Info */}
      {liveDetections.length > 0 && (
        <div className="card">
          <h3 className="text-sm font-semibold mb-3">Live Detections</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
            {liveDetections.map((det: any, i: number) => (
              <div key={i} className="p-2 bg-dark-900 rounded-lg text-sm">
                <span className="text-white font-medium">{det.class}</span>
                <span className="text-dark-400 ml-1">({(det.confidence * 100).toFixed(0)}%)</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

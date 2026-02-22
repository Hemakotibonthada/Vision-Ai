import { useState, useEffect, useRef } from 'react';
import { Grid, Maximize2, Minimize2, Camera, RefreshCw, Volume2, VolumeX } from 'lucide-react';

// Feature 52: Multi-Camera Grid View & Feature 53: Event Timeline

interface CameraFeed {
  id: string;
  name: string;
  url: string;
  status: 'online' | 'offline';
  location: string;
}

const MOCK_CAMERAS: CameraFeed[] = [
  { id: 'cam-1', name: 'Front Door', url: '', status: 'offline', location: 'Entrance' },
  { id: 'cam-2', name: 'Living Room', url: '', status: 'offline', location: 'Living Room' },
  { id: 'cam-3', name: 'Backyard', url: '', status: 'offline', location: 'Outdoor' },
  { id: 'cam-4', name: 'Garage', url: '', status: 'offline', location: 'Garage' },
  { id: 'cam-5', name: 'Kitchen', url: '', status: 'offline', location: 'Kitchen' },
  { id: 'cam-6', name: 'Baby Room', url: '', status: 'offline', location: 'Bedroom' },
];

export default function CameraGrid() {
  const [cameras, setCameras] = useState(MOCK_CAMERAS);
  const [layout, setLayout] = useState<'2x2' | '3x2' | '1x1'>('2x2');
  const [selectedCamera, setSelectedCamera] = useState<string | null>(null);
  const [audioEnabled, setAudioEnabled] = useState(false);

  const gridClass = {
    '2x2': 'grid-cols-2 grid-rows-2',
    '3x2': 'grid-cols-3 grid-rows-2',
    '1x1': 'grid-cols-1 grid-rows-1',
  }[layout];

  const displayedCameras = selectedCamera
    ? cameras.filter(c => c.id === selectedCamera)
    : cameras.slice(0, layout === '2x2' ? 4 : layout === '3x2' ? 6 : 1);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Camera Grid</h1>
          <p className="text-dark-400 text-sm mt-1">{cameras.filter(c => c.status === 'online').length}/{cameras.length} cameras online</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setAudioEnabled(!audioEnabled)}
            className="p-2 hover:bg-dark-700 rounded-lg transition-colors">
            {audioEnabled ? <Volume2 size={20} className="text-green-400" /> : <VolumeX size={20} className="text-dark-400" />}
          </button>
          {selectedCamera && (
            <button onClick={() => setSelectedCamera(null)}
              className="p-2 hover:bg-dark-700 rounded-lg">
              <Minimize2 size={20} />
            </button>
          )}
          <div className="flex bg-dark-800 rounded-lg overflow-hidden">
            {(['2x2', '3x2', '1x1'] as const).map(l => (
              <button key={l} onClick={() => { setLayout(l); setSelectedCamera(null); }}
                className={`px-3 py-2 text-xs ${layout === l ? 'bg-primary-600 text-white' : 'text-dark-400 hover:bg-dark-700'}`}>
                {l}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className={`grid ${gridClass} gap-2 h-[calc(100vh-200px)]`}>
        {displayedCameras.map(cam => (
          <div key={cam.id} className="relative bg-dark-800 rounded-lg overflow-hidden group">
            {/* Camera Feed Placeholder */}
            <div className="absolute inset-0 flex items-center justify-center bg-dark-900">
              <div className="text-center">
                <Camera size={48} className="text-dark-600 mx-auto mb-2" />
                <p className="text-dark-500 text-sm">{cam.name}</p>
                <p className="text-dark-600 text-xs">{cam.status === 'online' ? 'Live' : 'Offline'}</p>
              </div>
            </div>

            {/* Overlay */}
            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-3 opacity-0 group-hover:opacity-100 transition-opacity">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-white text-sm font-medium">{cam.name}</p>
                  <p className="text-dark-400 text-xs">{cam.location}</p>
                </div>
                <div className="flex gap-1">
                  <button onClick={() => setSelectedCamera(cam.id)}
                    className="p-1.5 bg-dark-700/80 rounded hover:bg-dark-600">
                    <Maximize2 size={14} className="text-white" />
                  </button>
                </div>
              </div>
            </div>

            {/* Status indicator */}
            <div className={`absolute top-2 right-2 w-2.5 h-2.5 rounded-full ${cam.status === 'online' ? 'bg-green-400 animate-pulse' : 'bg-red-500'}`} />
            <div className="absolute top-2 left-2 px-2 py-0.5 bg-black/60 rounded text-xs text-white">
              {cam.name}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

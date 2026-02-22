import { useState } from 'react';
import { Shield, Eye, EyeOff, Plus, Save, Trash2, Camera, Square, Circle } from 'lucide-react';

// Feature 65: Privacy Settings - configure privacy masks and data retention

interface PrivacyZone {
  id: number;
  name: string;
  camera: string;
  shape: 'rectangle' | 'ellipse';
  x: number;
  y: number;
  width: number;
  height: number;
  blurLevel: number;
  enabled: boolean;
}

const MOCK_ZONES: PrivacyZone[] = [
  { id: 1, name: 'Neighbor Window', camera: 'ESP32-CAM-01', shape: 'rectangle', x: 60, y: 10, width: 30, height: 25, blurLevel: 20, enabled: true },
  { id: 2, name: 'Street View', camera: 'ESP32-CAM-01', shape: 'rectangle', x: 0, y: 70, width: 100, height: 30, blurLevel: 15, enabled: true },
  { id: 3, name: 'Sensitive Area', camera: 'ESP32-CAM-02', shape: 'ellipse', x: 30, y: 20, width: 40, height: 35, blurLevel: 25, enabled: false },
];

interface RetentionPolicy {
  id: string;
  label: string;
  days: number;
  enabled: boolean;
}

const RETENTION_POLICIES: RetentionPolicy[] = [
  { id: 'recordings', label: 'Video Recordings', days: 30, enabled: true },
  { id: 'snapshots', label: 'Snapshots', days: 14, enabled: true },
  { id: 'logs', label: 'System Logs', days: 90, enabled: true },
  { id: 'detections', label: 'Detection Data', days: 60, enabled: true },
  { id: 'faces', label: 'Face Embeddings', days: 365, enabled: true },
  { id: 'analytics', label: 'Analytics Data', days: 180, enabled: true },
];

export default function PrivacySettings() {
  const [zones, setZones] = useState(MOCK_ZONES);
  const [retention, setRetention] = useState(RETENTION_POLICIES);
  const [faceBlur, setFaceBlur] = useState(true);
  const [plateBlur, setPlateBlur] = useState(true);
  const [dataEncryption, setDataEncryption] = useState(true);
  const [auditLog, setAuditLog] = useState(true);
  const [consentRequired, setConsentRequired] = useState(false);
  const [selectedCamera, setSelectedCamera] = useState('ESP32-CAM-01');

  const toggleZone = (id: number) => setZones(zs => zs.map(z => z.id === id ? { ...z, enabled: !z.enabled } : z));
  const removeZone = (id: number) => setZones(zs => zs.filter(z => z.id !== id));
  const updateRetention = (id: string, days: number) => setRetention(rs => rs.map(r => r.id === id ? { ...r, days } : r));

  const cameraZones = zones.filter(z => z.camera === selectedCamera);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2"><Shield size={24} /> Privacy Settings</h1>
          <p className="text-dark-400 text-sm mt-1">Configure privacy masks, data retention, and compliance settings</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Privacy Masks */}
        <div className="card p-5">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2"><EyeOff size={18} /> Privacy Masks</h2>
          <div className="mb-4">
            <select className="input-field" value={selectedCamera} onChange={e => setSelectedCamera(e.target.value)}>
              <option value="ESP32-CAM-01">ESP32-CAM-01 (Front Door)</option>
              <option value="ESP32-CAM-02">ESP32-CAM-02 (Garage)</option>
              <option value="ESP32-CAM-03">ESP32-CAM-03 (Backyard)</option>
            </select>
          </div>

          {/* Preview area */}
          <div className="relative bg-dark-800 rounded-lg overflow-hidden mb-4" style={{ paddingBottom: '56.25%' }}>
            <div className="absolute inset-0 flex items-center justify-center text-dark-600">
              <Camera size={48} />
            </div>
            {cameraZones.filter(z => z.enabled).map(zone => (
              <div key={zone.id}
                className="absolute border-2 border-red-500/50 bg-red-500/20 flex items-center justify-center"
                style={{
                  left: `${zone.x}%`, top: `${zone.y}%`, width: `${zone.width}%`, height: `${zone.height}%`,
                  borderRadius: zone.shape === 'ellipse' ? '50%' : '4px',
                  backdropFilter: `blur(${zone.blurLevel}px)`,
                }}>
                <span className="text-[9px] text-red-400 bg-dark-900/80 px-1 rounded">{zone.name}</span>
              </div>
            ))}
          </div>

          {/* Zone list */}
          <div className="space-y-2">
            {cameraZones.map(zone => (
              <div key={zone.id} className={`flex items-center gap-3 p-2 rounded-lg ${zone.enabled ? 'bg-dark-700' : 'bg-dark-800 opacity-60'}`}>
                {zone.shape === 'rectangle' ? <Square size={14} className="text-red-400" /> : <Circle size={14} className="text-red-400" />}
                <span className="text-sm text-white flex-1">{zone.name}</span>
                <span className="text-xs text-dark-400">Blur: {zone.blurLevel}px</span>
                <button onClick={() => toggleZone(zone.id)}
                  className={`w-8 h-4 rounded-full transition-all ${zone.enabled ? 'bg-primary-500' : 'bg-dark-600'}`}>
                  <div className={`w-3 h-3 rounded-full bg-white transition-all ${zone.enabled ? 'translate-x-4' : 'translate-x-0.5'}`} />
                </button>
                <button onClick={() => removeZone(zone.id)} className="text-dark-400 hover:text-red-400"><Trash2 size={12} /></button>
              </div>
            ))}
          </div>
        </div>

        {/* General Privacy Settings */}
        <div className="space-y-4">
          <div className="card p-5">
            <h2 className="text-lg font-semibold text-white mb-4">Auto-Privacy Features</h2>
            <div className="space-y-4">
              {[
                { label: 'Auto-blur Faces', desc: 'Automatically blur detected faces in recordings', value: faceBlur, set: setFaceBlur },
                { label: 'Auto-blur License Plates', desc: 'Blur detected vehicle plates', value: plateBlur, set: setPlateBlur },
                { label: 'Data Encryption', desc: 'Encrypt stored recordings and detection data', value: dataEncryption, set: setDataEncryption },
                { label: 'Audit Logging', desc: 'Log all data access and modifications', value: auditLog, set: setAuditLog },
                { label: 'Consent Required', desc: 'Require consent before face registration', value: consentRequired, set: setConsentRequired },
              ].map(item => (
                <div key={item.label} className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium text-white">{item.label}</div>
                    <div className="text-xs text-dark-400">{item.desc}</div>
                  </div>
                  <button onClick={() => item.set(!item.value)}
                    className={`w-10 h-5 rounded-full transition-all ${item.value ? 'bg-primary-500' : 'bg-dark-600'}`}>
                    <div className={`w-4 h-4 rounded-full bg-white transition-all ${item.value ? 'translate-x-5' : 'translate-x-0.5'}`} />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Data Retention */}
          <div className="card p-5">
            <h2 className="text-lg font-semibold text-white mb-4">Data Retention Policies</h2>
            <div className="space-y-3">
              {retention.map(policy => (
                <div key={policy.id} className="flex items-center gap-3">
                  <span className="text-sm text-dark-300 flex-1">{policy.label}</span>
                  <input type="number" min="1" max="365" className="input-field w-20 text-center text-sm"
                    value={policy.days} onChange={e => updateRetention(policy.id, parseInt(e.target.value) || 1)} />
                  <span className="text-xs text-dark-400">days</span>
                </div>
              ))}
            </div>
            <button className="btn btn-primary w-full mt-4 flex items-center justify-center gap-1"><Save size={14} /> Save Policies</button>
          </div>
        </div>
      </div>
    </div>
  );
}

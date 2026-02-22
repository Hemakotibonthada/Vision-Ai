import { useState } from 'react';
import { Layers, CheckSquare, Square, Play, Trash2, Settings, RefreshCw, Filter, Zap, Camera, Download, Upload } from 'lucide-react';

// Feature 74: Batch Operations - bulk device/model/recording operations

type BatchTarget = 'devices' | 'models' | 'recordings' | 'faces' | 'rules';

interface BatchItem {
  id: string;
  name: string;
  type: string;
  status: string;
  selected: boolean;
}

const MOCK_ITEMS: Record<BatchTarget, BatchItem[]> = {
  devices: [
    { id: 'd1', name: 'ESP32-CAM-01', type: 'Camera', status: 'online', selected: false },
    { id: 'd2', name: 'ESP32-CAM-02', type: 'Camera', status: 'online', selected: false },
    { id: 'd3', name: 'ESP32-CAM-03', type: 'Camera', status: 'offline', selected: false },
    { id: 'd4', name: 'ESP32-Server', type: 'Controller', status: 'online', selected: false },
    { id: 'd5', name: 'Sensor Hub', type: 'Sensor', status: 'warning', selected: false },
  ],
  models: [
    { id: 'm1', name: 'YOLOv8n', type: 'Detection', status: 'active', selected: false },
    { id: 'm2', name: 'YOLOv8s', type: 'Detection', status: 'active', selected: false },
    { id: 'm3', name: 'FaceNet', type: 'Recognition', status: 'active', selected: false },
    { id: 'm4', name: 'MobileNet-SSD', type: 'Detection', status: 'inactive', selected: false },
    { id: 'm5', name: 'DeepSORT', type: 'Tracking', status: 'active', selected: false },
  ],
  recordings: [
    { id: 'r1', name: 'recording_2026-02-22_14-30.mp4', type: 'Video', status: '2.3 GB', selected: false },
    { id: 'r2', name: 'recording_2026-02-22_12-00.mp4', type: 'Video', status: '1.8 GB', selected: false },
    { id: 'r3', name: 'recording_2026-02-21_20-00.mp4', type: 'Video', status: '3.1 GB', selected: false },
    { id: 'r4', name: 'snapshot_batch_feb22.zip', type: 'Images', status: '456 MB', selected: false },
    { id: 'r5', name: 'recording_2026-02-21_08-00.mp4', type: 'Video', status: '2.4 GB', selected: false },
  ],
  faces: [
    { id: 'f1', name: 'John Doe', type: 'Family', status: '5 embeddings', selected: false },
    { id: 'f2', name: 'Jane Doe', type: 'Family', status: '3 embeddings', selected: false },
    { id: 'f3', name: 'Bob Smith', type: 'Friend', status: '2 embeddings', selected: false },
    { id: 'f4', name: 'Delivery Person', type: 'Service', status: '1 embedding', selected: false },
  ],
  rules: [
    { id: 'a1', name: 'Night Mode', type: 'Schedule', status: 'enabled', selected: false },
    { id: 'a2', name: 'Motion Alert', type: 'Trigger', status: 'enabled', selected: false },
    { id: 'a3', name: 'Welcome Home', type: 'Trigger', status: 'enabled', selected: false },
    { id: 'a4', name: 'Energy Saver', type: 'Schedule', status: 'disabled', selected: false },
    { id: 'a5', name: 'Intruder Alert', type: 'Security', status: 'enabled', selected: false },
  ],
};

const BATCH_ACTIONS: Record<BatchTarget, { id: string; label: string; icon: any; danger?: boolean }[]> = {
  devices: [
    { id: 'restart', label: 'Restart', icon: RefreshCw },
    { id: 'update', label: 'Firmware Update', icon: Upload },
    { id: 'configure', label: 'Configure', icon: Settings },
    { id: 'disable', label: 'Disable', icon: Zap },
  ],
  models: [
    { id: 'activate', label: 'Activate', icon: Play },
    { id: 'deactivate', label: 'Deactivate', icon: Zap },
    { id: 'export', label: 'Export', icon: Download },
    { id: 'delete', label: 'Delete', icon: Trash2, danger: true },
  ],
  recordings: [
    { id: 'download', label: 'Download', icon: Download },
    { id: 'archive', label: 'Archive', icon: Layers },
    { id: 'delete', label: 'Delete', icon: Trash2, danger: true },
  ],
  faces: [
    { id: 'retrain', label: 'Retrain', icon: RefreshCw },
    { id: 'export', label: 'Export', icon: Download },
    { id: 'delete', label: 'Delete', icon: Trash2, danger: true },
  ],
  rules: [
    { id: 'enable', label: 'Enable', icon: Play },
    { id: 'disable', label: 'Disable', icon: Zap },
    { id: 'export', label: 'Export', icon: Download },
    { id: 'delete', label: 'Delete', icon: Trash2, danger: true },
  ],
};

export default function BatchOperations() {
  const [target, setTarget] = useState<BatchTarget>('devices');
  const [items, setItems] = useState(MOCK_ITEMS);
  const [executing, setExecuting] = useState(false);
  const [searchFilter, setSearchFilter] = useState('');

  const currentItems = items[target].filter(i => i.name.toLowerCase().includes(searchFilter.toLowerCase()));
  const selectedCount = items[target].filter(i => i.selected).length;

  const toggleItem = (id: string) => {
    setItems({ ...items, [target]: items[target].map(i => i.id === id ? { ...i, selected: !i.selected } : i) });
  };

  const toggleAll = () => {
    const allSelected = currentItems.every(i => i.selected);
    setItems({ ...items, [target]: items[target].map(i => ({ ...i, selected: !allSelected })) });
  };

  const executeAction = (actionId: string) => {
    setExecuting(true);
    setTimeout(() => {
      if (actionId === 'delete') {
        setItems({ ...items, [target]: items[target].filter(i => !i.selected) });
      } else {
        setItems({ ...items, [target]: items[target].map(i => i.selected ? { ...i, selected: false } : i) });
      }
      setExecuting(false);
    }, 2000);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2"><Layers size={24} /> Batch Operations</h1>
          <p className="text-dark-400 text-sm mt-1">Perform bulk actions on multiple items</p>
        </div>
        {selectedCount > 0 && (
          <span className="text-primary-400 text-sm font-medium">{selectedCount} item{selectedCount > 1 ? 's' : ''} selected</span>
        )}
      </div>

      {/* Target Type Tabs */}
      <div className="flex gap-2">
        {(['devices', 'models', 'recordings', 'faces', 'rules'] as BatchTarget[]).map(t => (
          <button key={t} onClick={() => { setTarget(t); setSearchFilter(''); }}
            className={`px-4 py-2 rounded-lg text-sm capitalize ${target === t ? 'bg-primary-500 text-white' : 'bg-dark-700 text-dark-400 hover:text-white'}`}>
            {t} ({items[t].length})
          </button>
        ))}
      </div>

      {/* Actions Bar */}
      {selectedCount > 0 && (
        <div className="card p-3 flex items-center gap-3">
          <span className="text-sm text-dark-300">{selectedCount} selected:</span>
          <div className="flex gap-2">
            {BATCH_ACTIONS[target].map(action => {
              const Icon = action.icon;
              return (
                <button key={action.id} onClick={() => executeAction(action.id)}
                  disabled={executing}
                  className={`btn text-xs py-1.5 flex items-center gap-1 ${action.danger ? 'btn-secondary text-red-400 hover:bg-red-500/20' : 'btn-secondary'}`}>
                  <Icon size={12} className={executing ? 'animate-spin' : ''} />
                  {executing ? 'Executing...' : action.label}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Search */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <Filter size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-400" />
          <input type="text" placeholder={`Filter ${target}...`} className="input-field w-full pl-9 text-sm"
            value={searchFilter} onChange={e => setSearchFilter(e.target.value)} />
        </div>
        <button onClick={toggleAll}
          className="btn btn-secondary text-xs flex items-center gap-1">
          {currentItems.every(i => i.selected) ? <CheckSquare size={14} /> : <Square size={14} />}
          {currentItems.every(i => i.selected) ? 'Deselect All' : 'Select All'}
        </button>
      </div>

      {/* Items List */}
      <div className="space-y-2">
        {currentItems.map(item => (
          <div key={item.id}
            onClick={() => toggleItem(item.id)}
            className={`card p-3 cursor-pointer transition-all flex items-center gap-3 ${item.selected ? 'ring-2 ring-primary-500 bg-primary-500/5' : 'hover:bg-dark-700/30'}`}>
            <div className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${item.selected ? 'border-primary-500 bg-primary-500' : 'border-dark-500'}`}>
              {item.selected && <span className="text-white text-xs">✓</span>}
            </div>
            <div className="flex-1">
              <div className="font-medium text-white text-sm">{item.name}</div>
              <div className="text-xs text-dark-400">{item.type}</div>
            </div>
            <span className={`text-xs px-2 py-0.5 rounded ${
              item.status === 'online' || item.status === 'active' || item.status === 'enabled' ? 'text-green-400 bg-green-500/10' :
              item.status === 'offline' || item.status === 'inactive' || item.status === 'disabled' ? 'text-red-400 bg-red-500/10' :
              'text-dark-300 bg-dark-700'
            }`}>{item.status}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

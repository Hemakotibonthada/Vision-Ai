import { useState } from 'react';
import { HardDrive, Download, Upload, Trash2, Clock, Check, AlertTriangle, RefreshCw, Plus, Shield } from 'lucide-react';

// Feature 66: Backup Management - create, restore, and manage system backups

interface Backup {
  id: number;
  name: string;
  timestamp: string;
  size: string;
  type: 'full' | 'config' | 'data' | 'models';
  status: 'completed' | 'failed' | 'in_progress';
  components: string[];
}

const MOCK_BACKUPS: Backup[] = [
  { id: 1, name: 'Full System Backup', timestamp: '2026-02-22T14:00:00', size: '2.4 GB', type: 'full', status: 'completed', components: ['config', 'database', 'models', 'recordings'] },
  { id: 2, name: 'Config Only', timestamp: '2026-02-22T12:00:00', size: '12 MB', type: 'config', status: 'completed', components: ['config', 'automation_rules'] },
  { id: 3, name: 'AI Models Backup', timestamp: '2026-02-21T20:00:00', size: '456 MB', type: 'models', status: 'completed', components: ['yolov8', 'facenet', 'custom_models'] },
  { id: 4, name: 'Detection Data', timestamp: '2026-02-21T08:00:00', size: '890 MB', type: 'data', status: 'completed', components: ['detections', 'face_embeddings', 'analytics'] },
  { id: 5, name: 'Scheduled Full Backup', timestamp: '2026-02-20T02:00:00', size: '2.3 GB', type: 'full', status: 'completed', components: ['config', 'database', 'models', 'recordings'] },
  { id: 6, name: 'Emergency Backup', timestamp: '2026-02-19T15:30:00', size: '0 MB', type: 'full', status: 'failed', components: [] },
];

const TYPE_COLORS = { full: 'bg-primary-500/10 text-primary-400', config: 'bg-green-500/10 text-green-400', data: 'bg-yellow-500/10 text-yellow-400', models: 'bg-purple-500/10 text-purple-400' };
const STATUS_ICONS = { completed: Check, failed: AlertTriangle, in_progress: RefreshCw };
const STATUS_COLORS_ = { completed: 'text-green-400', failed: 'text-red-400', in_progress: 'text-yellow-400' };

export default function BackupManagement() {
  const [backups, setBackups] = useState(MOCK_BACKUPS);
  const [showCreate, setShowCreate] = useState(false);
  const [createType, setCreateType] = useState<Backup['type']>('full');
  const [autoBackup, setAutoBackup] = useState(true);
  const [autoInterval, setAutoInterval] = useState('daily');
  const [restoring, setRestoring] = useState<number | null>(null);
  const [components, setComponents] = useState(['config', 'database', 'models', 'recordings']);

  const COMPONENT_OPTIONS = ['config', 'database', 'models', 'recordings', 'automation_rules', 'face_embeddings', 'detections', 'analytics'];

  const createBackup = () => {
    const newBackup: Backup = {
      id: Date.now(), name: `${createType.charAt(0).toUpperCase() + createType.slice(1)} Backup`,
      timestamp: new Date().toISOString(), size: 'Calculating...', type: createType, status: 'in_progress', components,
    };
    setBackups([newBackup, ...backups]);
    setShowCreate(false);
    setTimeout(() => {
      setBackups(bs => bs.map(b => b.id === newBackup.id ? { ...b, status: 'completed', size: createType === 'full' ? '2.5 GB' : '150 MB' } : b));
    }, 3000);
  };

  const restore = (id: number) => {
    setRestoring(id);
    setTimeout(() => setRestoring(null), 5000);
  };

  const deleteBackup = (id: number) => setBackups(bs => bs.filter(b => b.id !== id));

  const totalSize = backups.filter(b => b.status === 'completed').reduce((acc, b) => {
    const num = parseFloat(b.size);
    return acc + (b.size.includes('GB') ? num * 1024 : num);
  }, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2"><HardDrive size={24} /> Backup Management</h1>
          <p className="text-dark-400 text-sm mt-1">{backups.length} backups &middot; {(totalSize / 1024).toFixed(1)} GB used</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn btn-primary flex items-center gap-1"><Plus size={14} /> Create Backup</button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Total Backups', value: backups.length, color: 'text-white' },
          { label: 'Successful', value: backups.filter(b => b.status === 'completed').length, color: 'text-green-400' },
          { label: 'Failed', value: backups.filter(b => b.status === 'failed').length, color: 'text-red-400' },
          { label: 'Storage Used', value: `${(totalSize / 1024).toFixed(1)} GB`, color: 'text-primary-400' },
        ].map(s => (
          <div key={s.label} className="card p-4 text-center">
            <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
            <div className="text-xs text-dark-400 mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Auto Backup Settings */}
      <div className="card p-4 flex items-center gap-4">
        <Shield size={18} className="text-primary-400" />
        <div className="flex-1">
          <div className="font-medium text-white text-sm">Automatic Backups</div>
          <div className="text-xs text-dark-400">Schedule automatic backups</div>
        </div>
        <select className="input-field" value={autoInterval} onChange={e => setAutoInterval(e.target.value)} disabled={!autoBackup}>
          <option value="hourly">Hourly</option>
          <option value="daily">Daily</option>
          <option value="weekly">Weekly</option>
        </select>
        <button onClick={() => setAutoBackup(!autoBackup)}
          className={`w-10 h-5 rounded-full transition-all ${autoBackup ? 'bg-primary-500' : 'bg-dark-600'}`}>
          <div className={`w-4 h-4 rounded-full bg-white transition-all ${autoBackup ? 'translate-x-5' : 'translate-x-0.5'}`} />
        </button>
      </div>

      {/* Backups List */}
      <div className="space-y-3">
        {backups.map(backup => {
          const StatusIcon = STATUS_ICONS[backup.status];
          return (
            <div key={backup.id} className={`card p-4 ${backup.status === 'failed' ? 'border border-red-500/20' : ''}`}>
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-lg bg-dark-700 flex items-center justify-center">
                  <HardDrive size={18} className="text-dark-400" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-white">{backup.name}</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] ${TYPE_COLORS[backup.type]}`}>{backup.type}</span>
                    <StatusIcon size={14} className={`${STATUS_COLORS_[backup.status]} ${backup.status === 'in_progress' ? 'animate-spin' : ''}`} />
                  </div>
                  <div className="flex items-center gap-3 text-xs text-dark-400 mt-1">
                    <span className="flex items-center gap-1"><Clock size={10} /> {new Date(backup.timestamp).toLocaleString()}</span>
                    <span>{backup.size}</span>
                    <span>{backup.components.join(', ')}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {backup.status === 'completed' && (
                    <>
                      <button onClick={() => restore(backup.id)}
                        className={`btn btn-secondary text-xs py-1 flex items-center gap-1 ${restoring === backup.id ? 'animate-pulse' : ''}`}>
                        <Upload size={12} /> {restoring === backup.id ? 'Restoring...' : 'Restore'}
                      </button>
                      <button className="btn btn-secondary text-xs py-1 flex items-center gap-1"><Download size={12} /> Download</button>
                    </>
                  )}
                  <button onClick={() => deleteBackup(backup.id)} className="p-1.5 rounded hover:bg-dark-700 text-dark-400 hover:text-red-400">
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="card p-6 w-full max-w-md">
            <h2 className="text-lg font-bold text-white mb-4">Create Backup</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-dark-300 mb-1">Backup Type</label>
                <div className="grid grid-cols-4 gap-2">
                  {(['full', 'config', 'data', 'models'] as const).map(t => (
                    <button key={t} onClick={() => setCreateType(t)}
                      className={`p-2 rounded-lg text-xs text-center capitalize ${createType === t ? 'bg-primary-500 text-white' : 'bg-dark-700 text-dark-400'}`}>
                      {t}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm text-dark-300 mb-1">Components</label>
                <div className="grid grid-cols-2 gap-2">
                  {COMPONENT_OPTIONS.map(c => (
                    <label key={c} className="flex items-center gap-2 text-xs text-dark-300 cursor-pointer">
                      <input type="checkbox" checked={components.includes(c)}
                        onChange={e => e.target.checked ? setComponents([...components, c]) : setComponents(components.filter(x => x !== c))} />
                      {c}
                    </label>
                  ))}
                </div>
              </div>
              <div className="flex gap-2 justify-end">
                <button onClick={() => setShowCreate(false)} className="btn btn-secondary">Cancel</button>
                <button onClick={createBackup} className="btn btn-primary">Create Backup</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

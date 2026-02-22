import { useState } from 'react';
import { Hand, Settings, Plus, Trash2, Save, Camera, Zap, Volume2, Lock, Bell } from 'lucide-react';

// Feature 64: Gesture Control Panel - configure gesture-to-action mappings

interface GestureMapping {
  id: number;
  gesture: string;
  action: string;
  actionTarget: string;
  enabled: boolean;
  confidence: number;
  cooldown: number;
}

const GESTURES = [
  { id: 'wave', label: '👋 Wave', description: 'Open palm side-to-side' },
  { id: 'thumbs_up', label: '👍 Thumbs Up', description: 'Thumb pointing upward' },
  { id: 'thumbs_down', label: '👎 Thumbs Down', description: 'Thumb pointing downward' },
  { id: 'peace', label: '✌️ Peace', description: 'Index and middle fingers raised' },
  { id: 'fist', label: '✊ Fist', description: 'Closed hand' },
  { id: 'open_palm', label: '🖐️ Open Palm', description: 'All fingers extended' },
  { id: 'point', label: '👆 Point', description: 'Index finger pointing' },
  { id: 'ok_sign', label: '👌 OK Sign', description: 'Thumb and index forming O' },
  { id: 'swipe_left', label: '👈 Swipe Left', description: 'Hand sweeping left' },
  { id: 'swipe_right', label: '👉 Swipe Right', description: 'Hand sweeping right' },
];

const ACTIONS = [
  { id: 'toggle_relay', label: 'Toggle Relay', icon: Zap },
  { id: 'capture_photo', label: 'Capture Photo', icon: Camera },
  { id: 'play_sound', label: 'Play Sound', icon: Volume2 },
  { id: 'lock_door', label: 'Lock/Unlock Door', icon: Lock },
  { id: 'send_notification', label: 'Send Notification', icon: Bell },
  { id: 'activate_scene', label: 'Activate Scene', icon: Settings },
  { id: 'trigger_alarm', label: 'Trigger Alarm', icon: Bell },
  { id: 'custom_api', label: 'Call Custom API', icon: Zap },
];

const INITIAL_MAPPINGS: GestureMapping[] = [
  { id: 1, gesture: 'wave', action: 'toggle_relay', actionTarget: 'Relay 1 - Lights', enabled: true, confidence: 0.8, cooldown: 3 },
  { id: 2, gesture: 'thumbs_up', action: 'capture_photo', actionTarget: 'Front Camera', enabled: true, confidence: 0.85, cooldown: 5 },
  { id: 3, gesture: 'fist', action: 'lock_door', actionTarget: 'Front Door', enabled: true, confidence: 0.9, cooldown: 10 },
  { id: 4, gesture: 'peace', action: 'activate_scene', actionTarget: 'Night Mode', enabled: false, confidence: 0.8, cooldown: 5 },
  { id: 5, gesture: 'open_palm', action: 'trigger_alarm', actionTarget: 'Security Alarm', enabled: false, confidence: 0.95, cooldown: 30 },
];

export default function GestureControl() {
  const [mappings, setMappings] = useState(INITIAL_MAPPINGS);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ gesture: 'wave', action: 'toggle_relay', actionTarget: '', confidence: 0.8, cooldown: 5 });

  const toggle = (id: number) => setMappings(ms => ms.map(m => m.id === id ? { ...m, enabled: !m.enabled } : m));
  const remove = (id: number) => setMappings(ms => ms.filter(m => m.id !== id));
  const add = () => {
    setMappings([...mappings, { id: Date.now(), ...form, enabled: true }]);
    setShowForm(false);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2"><Hand size={24} /> Gesture Control</h1>
          <p className="text-dark-400 text-sm mt-1">Map hand gestures to actions</p>
        </div>
        <button onClick={() => setShowForm(true)} className="btn btn-primary flex items-center gap-1"><Plus size={14} /> New Mapping</button>
      </div>

      {/* Available Gestures */}
      <div className="card p-4">
        <h3 className="text-sm font-semibold text-white mb-3">Available Gestures</h3>
        <div className="flex flex-wrap gap-2">
          {GESTURES.map(g => {
            const used = mappings.some(m => m.gesture === g.id);
            return (
              <div key={g.id} className={`px-3 py-1.5 rounded-lg text-sm ${used ? 'bg-primary-500/20 text-primary-400 border border-primary-500/30' : 'bg-dark-700 text-dark-400'}`}
                title={g.description}>
                {g.label}
              </div>
            );
          })}
        </div>
      </div>

      {/* Mappings */}
      <div className="space-y-3">
        {mappings.map(mapping => {
          const gesture = GESTURES.find(g => g.id === mapping.gesture);
          const action = ACTIONS.find(a => a.id === mapping.action);
          const ActionIcon = action?.icon || Zap;
          return (
            <div key={mapping.id} className={`card p-4 border transition-all ${mapping.enabled ? 'border-primary-500/30' : 'border-transparent opacity-60'}`}>
              <div className="flex items-center gap-4">
                {/* Gesture */}
                <div className="flex-1 flex items-center gap-3">
                  <div className="text-3xl">{gesture?.label.split(' ')[0]}</div>
                  <div>
                    <div className="font-medium text-white">{gesture?.label.split(' ').slice(1).join(' ')}</div>
                    <div className="text-xs text-dark-400">{gesture?.description}</div>
                  </div>
                </div>

                {/* Arrow */}
                <div className="text-dark-500 text-lg">→</div>

                {/* Action */}
                <div className="flex-1 flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-primary-500/10 flex items-center justify-center">
                    <ActionIcon size={18} className="text-primary-400" />
                  </div>
                  <div>
                    <div className="font-medium text-white">{action?.label}</div>
                    <div className="text-xs text-dark-400">{mapping.actionTarget}</div>
                  </div>
                </div>

                {/* Settings */}
                <div className="flex items-center gap-4 text-xs text-dark-400">
                  <div title="Min confidence">
                    <span className="text-dark-500">Conf: </span>
                    <span className="text-white">{(mapping.confidence * 100).toFixed(0)}%</span>
                  </div>
                  <div title="Cooldown seconds">
                    <span className="text-dark-500">CD: </span>
                    <span className="text-white">{mapping.cooldown}s</span>
                  </div>
                </div>

                {/* Controls */}
                <div className="flex items-center gap-2">
                  <button onClick={() => toggle(mapping.id)}
                    className={`w-10 h-5 rounded-full transition-all ${mapping.enabled ? 'bg-primary-500' : 'bg-dark-600'}`}>
                    <div className={`w-4 h-4 rounded-full bg-white transition-all ${mapping.enabled ? 'translate-x-5' : 'translate-x-0.5'}`} />
                  </button>
                  <button onClick={() => remove(mapping.id)} className="p-1.5 rounded hover:bg-dark-700 text-dark-400 hover:text-red-400">
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Add Form Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="card p-6 w-full max-w-md">
            <h2 className="text-lg font-bold text-white mb-4">New Gesture Mapping</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-dark-300 mb-1">Gesture</label>
                <select className="input-field w-full" value={form.gesture} onChange={e => setForm({ ...form, gesture: e.target.value })}>
                  {GESTURES.map(g => <option key={g.id} value={g.id}>{g.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm text-dark-300 mb-1">Action</label>
                <select className="input-field w-full" value={form.action} onChange={e => setForm({ ...form, action: e.target.value })}>
                  {ACTIONS.map(a => <option key={a.id} value={a.id}>{a.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm text-dark-300 mb-1">Target</label>
                <input className="input-field w-full" placeholder="e.g., Living Room Lights" value={form.actionTarget}
                  onChange={e => setForm({ ...form, actionTarget: e.target.value })} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-dark-300 mb-1">Min Confidence ({(form.confidence * 100).toFixed(0)}%)</label>
                  <input type="range" min="0.5" max="1" step="0.05" className="w-full" value={form.confidence}
                    onChange={e => setForm({ ...form, confidence: parseFloat(e.target.value) })} />
                </div>
                <div>
                  <label className="block text-sm text-dark-300 mb-1">Cooldown ({form.cooldown}s)</label>
                  <input type="range" min="1" max="60" step="1" className="w-full" value={form.cooldown}
                    onChange={e => setForm({ ...form, cooldown: parseInt(e.target.value) })} />
                </div>
              </div>
              <div className="flex gap-2 justify-end">
                <button onClick={() => setShowForm(false)} className="btn btn-secondary">Cancel</button>
                <button onClick={add} className="btn btn-primary flex items-center gap-1"><Save size={14} /> Save</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

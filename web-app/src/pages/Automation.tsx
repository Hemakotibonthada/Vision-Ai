import { useState, useCallback } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Plus, Trash2, Play, Pause, Zap, Clock, ToggleLeft, ToggleRight } from 'lucide-react';
import api from '../services/api';

// Feature 51: Visual Automation Rules Builder

interface AutomationRule {
  id: number;
  name: string;
  trigger: { type: string; condition: string; value: string };
  actions: { type: string; target: string; params: Record<string, any> }[];
  enabled: boolean;
  last_triggered?: string;
}

const TRIGGERS = [
  { type: 'motion', label: 'Motion Detected' },
  { type: 'face', label: 'Face Recognized' },
  { type: 'time', label: 'Time Schedule' },
  { type: 'temperature', label: 'Temperature Threshold' },
  { type: 'humidity', label: 'Humidity Threshold' },
  { type: 'door', label: 'Door Open/Close' },
  { type: 'geofence', label: 'Geofence Enter/Exit' },
  { type: 'voice', label: 'Voice Command' },
];

const ACTIONS = [
  { type: 'relay', label: 'Toggle Relay' },
  { type: 'light', label: 'Set Light' },
  { type: 'lock', label: 'Lock/Unlock Door' },
  { type: 'buzzer', label: 'Sound Buzzer' },
  { type: 'capture', label: 'Take Photo' },
  { type: 'notify', label: 'Send Notification' },
  { type: 'scene', label: 'Activate Scene' },
  { type: 'thermostat', label: 'Set Temperature' },
];

export default function Automation() {
  const [rules, setRules] = useState<AutomationRule[]>([
    {
      id: 1, name: 'Night Security', enabled: true,
      trigger: { type: 'time', condition: 'equals', value: '22:00' },
      actions: [
        { type: 'lock', target: 'front_door', params: { state: 'locked' } },
        { type: 'light', target: 'hallway', params: { brightness: 10 } },
      ]
    },
    {
      id: 2, name: 'Welcome Home', enabled: true,
      trigger: { type: 'face', condition: 'recognized', value: 'owner' },
      actions: [
        { type: 'light', target: 'living_room', params: { brightness: 80 } },
        { type: 'relay', target: 'relay_1', params: { state: 'on' } },
      ]
    },
    {
      id: 3, name: 'High Temp Alert', enabled: false,
      trigger: { type: 'temperature', condition: 'above', value: '35' },
      actions: [
        { type: 'relay', target: 'fan', params: { state: 'on' } },
        { type: 'notify', target: 'admin', params: { message: 'High temperature!' } },
      ]
    },
  ]);

  const [showBuilder, setShowBuilder] = useState(false);
  const [newRule, setNewRule] = useState({
    name: '',
    trigger: { type: 'motion', condition: 'detected', value: '' },
    actions: [{ type: 'relay', target: '', params: {} }],
  });

  const toggleRule = (id: number) => {
    setRules(rules.map(r => r.id === id ? { ...r, enabled: !r.enabled } : r));
  };

  const deleteRule = (id: number) => {
    setRules(rules.filter(r => r.id !== id));
  };

  const addRule = () => {
    setRules([...rules, {
      id: Date.now(),
      name: newRule.name || 'New Rule',
      trigger: newRule.trigger,
      actions: newRule.actions,
      enabled: true,
    }]);
    setShowBuilder(false);
    setNewRule({
      name: '',
      trigger: { type: 'motion', condition: 'detected', value: '' },
      actions: [{ type: 'relay', target: '', params: {} }],
    });
  };

  const addAction = () => {
    setNewRule({
      ...newRule,
      actions: [...newRule.actions, { type: 'relay', target: '', params: {} }]
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Automation Rules</h1>
          <p className="text-dark-400 text-sm mt-1">Create visual automation workflows</p>
        </div>
        <button onClick={() => setShowBuilder(!showBuilder)}
          className="btn-primary flex items-center gap-2">
          <Plus size={16} /> New Rule
        </button>
      </div>

      {/* Rule Builder */}
      {showBuilder && (
        <div className="card p-6 border-2 border-primary-500/30">
          <h3 className="text-lg font-semibold text-white mb-4">Rule Builder</h3>
          <div className="space-y-4">
            <input type="text" placeholder="Rule Name..."
              className="input-field w-full" value={newRule.name}
              onChange={e => setNewRule({ ...newRule, name: e.target.value })} />
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="text-sm text-dark-400 mb-1 block">When (Trigger)</label>
                <select className="input-field w-full" value={newRule.trigger.type}
                  onChange={e => setNewRule({ ...newRule, trigger: { ...newRule.trigger, type: e.target.value } })}>
                  {TRIGGERS.map(t => <option key={t.type} value={t.type}>{t.label}</option>)}
                </select>
              </div>
              <div>
                <label className="text-sm text-dark-400 mb-1 block">Condition</label>
                <select className="input-field w-full" value={newRule.trigger.condition}
                  onChange={e => setNewRule({ ...newRule, trigger: { ...newRule.trigger, condition: e.target.value } })}>
                  <option value="detected">Is Detected</option>
                  <option value="above">Above</option>
                  <option value="below">Below</option>
                  <option value="equals">Equals</option>
                  <option value="recognized">Recognized</option>
                </select>
              </div>
              <div>
                <label className="text-sm text-dark-400 mb-1 block">Value</label>
                <input type="text" className="input-field w-full" placeholder="Threshold value..."
                  value={newRule.trigger.value}
                  onChange={e => setNewRule({ ...newRule, trigger: { ...newRule.trigger, value: e.target.value } })} />
              </div>
            </div>

            <h4 className="text-sm font-semibold text-white">Then (Actions)</h4>
            {newRule.actions.map((action, i) => (
              <div key={i} className="grid grid-cols-2 gap-4">
                <select className="input-field" value={action.type}
                  onChange={e => {
                    const updated = [...newRule.actions];
                    updated[i] = { ...updated[i], type: e.target.value };
                    setNewRule({ ...newRule, actions: updated });
                  }}>
                  {ACTIONS.map(a => <option key={a.type} value={a.type}>{a.label}</option>)}
                </select>
                <input type="text" className="input-field" placeholder="Target device..."
                  value={action.target}
                  onChange={e => {
                    const updated = [...newRule.actions];
                    updated[i] = { ...updated[i], target: e.target.value };
                    setNewRule({ ...newRule, actions: updated });
                  }} />
              </div>
            ))}
            <button onClick={addAction} className="text-sm text-primary-400 hover:text-primary-300">
              + Add Action
            </button>

            <div className="flex gap-3 pt-2">
              <button onClick={addRule} className="btn-primary">Create Rule</button>
              <button onClick={() => setShowBuilder(false)} className="btn-ghost">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {/* Existing Rules */}
      <div className="space-y-3">
        {rules.map(rule => (
          <div key={rule.id} className={`card p-4 flex items-center justify-between ${rule.enabled ? 'border-l-4 border-l-green-500' : 'opacity-60 border-l-4 border-l-dark-600'}`}>
            <div className="flex-1">
              <div className="flex items-center gap-3">
                <Zap size={16} className={rule.enabled ? 'text-yellow-400' : 'text-dark-500'} />
                <h3 className="font-semibold text-white">{rule.name}</h3>
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                <span className="px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 text-xs">
                  {TRIGGERS.find(t => t.type === rule.trigger.type)?.label} {rule.trigger.condition} {rule.trigger.value}
                </span>
                {rule.actions.map((a, i) => (
                  <span key={i} className="px-2 py-0.5 rounded-full bg-green-500/20 text-green-300 text-xs">
                    {ACTIONS.find(ac => ac.type === a.type)?.label}: {a.target}
                  </span>
                ))}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => toggleRule(rule.id)} className="p-2 hover:bg-dark-700 rounded-lg">
                {rule.enabled ? <ToggleRight size={24} className="text-green-400" /> : <ToggleLeft size={24} className="text-dark-500" />}
              </button>
              <button onClick={() => deleteRule(rule.id)} className="p-2 hover:bg-dark-700 rounded-lg text-red-400">
                <Trash2 size={16} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

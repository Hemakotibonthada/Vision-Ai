import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { alertsApi, eventsApi, zonesApi } from '../services/api';
import toast from 'react-hot-toast';
import {
  Bell, AlertTriangle, Plus, CheckCircle, Eye, Shield,
  Trash2, Clock, Filter, MapPin
} from 'lucide-react';

export default function Alerts() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<'events' | 'rules' | 'zones'>('events');
  const [showNewRule, setShowNewRule] = useState(false);
  const [newRule, setNewRule] = useState({
    name: '', event_type: 'detection', condition_field: 'confidence',
    condition_op: '>', condition_value: '0.8', channels: ['webhook'],
    cooldown: 60
  });

  const { data: events } = useQuery({
    queryKey: ['events'],
    queryFn: () => eventsApi.list({ limit: 100 }),
    refetchInterval: 15000,
  });
  const { data: rules } = useQuery({ queryKey: ['alertRules'], queryFn: () => alertsApi.getRules() });
  const { data: alertHistory } = useQuery({ queryKey: ['alertHistory'], queryFn: () => alertsApi.getHistory() });
  const { data: alertStats } = useQuery({ queryKey: ['alertStats'], queryFn: () => alertsApi.getStats() });
  const { data: zones } = useQuery({ queryKey: ['zones'], queryFn: () => zonesApi.list() });

  const ackMutation = useMutation({
    mutationFn: (id: number) => eventsApi.acknowledge(id),
    onSuccess: () => { toast.success('Acknowledged'); queryClient.invalidateQueries({ queryKey: ['events'] }); },
  });

  const createRuleMutation = useMutation({
    mutationFn: (rule: any) => alertsApi.createRule(rule),
    onSuccess: () => {
      toast.success('Rule created');
      queryClient.invalidateQueries({ queryKey: ['alertRules'] });
      setShowNewRule(false);
    },
  });

  const createZoneMutation = useMutation({
    mutationFn: (zone: any) => zonesApi.create(zone),
    onSuccess: () => { toast.success('Zone created'); queryClient.invalidateQueries({ queryKey: ['zones'] }); },
  });

  const evts = events?.data || [];
  const stats = alertStats?.data || {};

  const severityColor = (s: number) =>
    s >= 4 ? 'text-red-500' : s >= 3 ? 'text-orange-400' : s >= 2 ? 'text-yellow-400' : 'text-blue-400';
  const severityBg = (s: number) =>
    s >= 4 ? 'bg-red-500/10' : s >= 3 ? 'bg-orange-500/10' : s >= 2 ? 'bg-yellow-500/10' : 'bg-blue-500/10';

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="stat-card">
          <Bell size={20} className="text-blue-400" />
          <div className="stat-value">{stats.total_alerts || 0}</div>
          <div className="stat-label">Total Alerts</div>
        </div>
        <div className="stat-card">
          <AlertTriangle size={20} className="text-red-400" />
          <div className="stat-value">{stats.critical || 0}</div>
          <div className="stat-label">Critical</div>
        </div>
        <div className="stat-card">
          <Shield size={20} className="text-green-400" />
          <div className="stat-value">{(rules?.data || []).length}</div>
          <div className="stat-label">Active Rules</div>
        </div>
        <div className="stat-card">
          <MapPin size={20} className="text-purple-400" />
          <div className="stat-value">{(zones?.data || []).length}</div>
          <div className="stat-label">Zones</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-dark-800 rounded-lg w-fit">
        {[
          { key: 'events', label: 'Events', icon: Bell },
          { key: 'rules', label: 'Alert Rules', icon: Shield },
          { key: 'zones', label: 'Zones', icon: MapPin },
        ].map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key as any)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-colors ${
              tab === key ? 'bg-primary-600 text-white' : 'text-dark-400 hover:text-white hover:bg-dark-700'
            }`}
          >
            <Icon size={16} /> {label}
          </button>
        ))}
      </div>

      {/* Events Tab */}
      {tab === 'events' && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold">Event Log</h3>
            <span className="text-sm text-dark-400">{evts.length} events</span>
          </div>
          <div className="space-y-2 max-h-[600px] overflow-y-auto">
            {evts.map((evt: any) => (
              <div key={evt.id} className={`flex items-start justify-between p-3 rounded-lg ${severityBg(evt.severity)}`}>
                <div className="flex items-start gap-3">
                  <AlertTriangle size={16} className={`mt-0.5 ${severityColor(evt.severity)}`} />
                  <div>
                    <h4 className="text-sm font-medium">{evt.title}</h4>
                    <p className="text-xs text-dark-400">{evt.description}</p>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-xs text-dark-500">{evt.type}</span>
                      <span className="text-xs text-dark-500"><Clock size={10} className="inline mr-1" />{evt.created_at}</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {evt.acknowledged ? (
                    <span className="badge-success"><CheckCircle size={12} className="mr-1" /> Ack</span>
                  ) : (
                    <button onClick={() => ackMutation.mutate(evt.id)} className="btn-secondary text-xs py-1 px-2">
                      Acknowledge
                    </button>
                  )}
                </div>
              </div>
            ))}
            {evts.length === 0 && (
              <div className="text-center py-12 text-dark-500">
                <CheckCircle size={40} className="mx-auto mb-3" />
                <p>No events to display</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Rules Tab */}
      {tab === 'rules' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <button onClick={() => setShowNewRule(true)} className="btn-primary flex items-center gap-2">
              <Plus size={16} /> New Rule
            </button>
          </div>

          {showNewRule && (
            <div className="card border-primary-500/30">
              <h3 className="font-semibold mb-3">Create Alert Rule</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <input className="input" placeholder="Rule name" value={newRule.name} onChange={(e) => setNewRule({ ...newRule, name: e.target.value })} />
                <select className="select" value={newRule.event_type} onChange={(e) => setNewRule({ ...newRule, event_type: e.target.value })}>
                  <option value="detection">Detection</option>
                  <option value="motion">Motion</option>
                  <option value="sensor">Sensor</option>
                  <option value="system">System</option>
                </select>
                <input className="input" placeholder="Field (e.g., confidence)" value={newRule.condition_field} onChange={(e) => setNewRule({ ...newRule, condition_field: e.target.value })} />
                <select className="select" value={newRule.condition_op} onChange={(e) => setNewRule({ ...newRule, condition_op: e.target.value })}>
                  <option value=">">Greater than</option>
                  <option value="<">Less than</option>
                  <option value="==">Equals</option>
                  <option value="!=">Not equals</option>
                  <option value="contains">Contains</option>
                </select>
                <input className="input" placeholder="Value" value={newRule.condition_value} onChange={(e) => setNewRule({ ...newRule, condition_value: e.target.value })} />
                <input className="input" placeholder="Cooldown (sec)" type="number" value={newRule.cooldown} onChange={(e) => setNewRule({ ...newRule, cooldown: +e.target.value })} />
              </div>
              <div className="flex gap-2 mt-3">
                <button onClick={() => createRuleMutation.mutate(newRule)} className="btn-primary">Create</button>
                <button onClick={() => setShowNewRule(false)} className="btn-secondary">Cancel</button>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {(rules?.data || []).map((rule: any, i: number) => (
              <div key={i} className="card-hover">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">{rule.name}</span>
                  <span className="badge-info">{rule.event_type}</span>
                </div>
                <p className="text-sm text-dark-400">
                  If <span className="text-white">{rule.condition_field}</span>{' '}
                  <span className="text-yellow-400">{rule.condition_op}</span>{' '}
                  <span className="text-white">{rule.condition_value}</span>
                </p>
                <div className="flex items-center gap-2 mt-2 text-xs text-dark-500">
                  <span>Channels: {rule.channels?.join(', ')}</span>
                  <span>Cooldown: {rule.cooldown}s</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Zones Tab */}
      {tab === 'zones' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <button
              onClick={() => createZoneMutation.mutate({ name: `Zone ${Date.now()}`, zone_type: 'intrusion', points: [], color: '#ff0000' })}
              className="btn-primary flex items-center gap-2"
            >
              <Plus size={16} /> New Zone
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {(zones?.data || []).map((zone: any) => (
              <div key={zone.id} className="card-hover">
                <div className="flex items-center gap-3">
                  <div className="w-4 h-4 rounded-full" style={{ backgroundColor: zone.color || '#ff0000' }} />
                  <div>
                    <h4 className="font-medium">{zone.name}</h4>
                    <p className="text-xs text-dark-400">{zone.zone_type} | {zone.is_active ? 'Active' : 'Inactive'}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

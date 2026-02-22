import { useState } from 'react';
import { Activity, Clock, Camera, User, Shield, Zap, Bell, Settings, Eye, MessageSquare } from 'lucide-react';

// Feature 68: Activity Feed - real-time activity stream with live updates

interface ActivityItem {
  id: number;
  type: 'detection' | 'security' | 'automation' | 'user' | 'system' | 'device' | 'ai';
  actor: string;
  action: string;
  target?: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

const MOCK_ACTIVITIES: ActivityItem[] = [
  { id: 1, type: 'detection', actor: 'AI Engine', action: 'detected 2 persons', target: 'Front Door Camera', timestamp: '2026-02-22T14:30:05' },
  { id: 2, type: 'security', actor: 'Security System', action: 'door opened', target: 'Front Door', timestamp: '2026-02-22T14:29:58' },
  { id: 3, type: 'automation', actor: 'Jarvis', action: 'triggered rule "Welcome Home"', timestamp: '2026-02-22T14:29:55', metadata: { actions: ['lights_on', 'thermostat_22'] }  },
  { id: 4, type: 'ai', actor: 'FaceNet', action: 'recognized face', target: 'John Doe (confidence: 97.2%)', timestamp: '2026-02-22T14:29:50' },
  { id: 5, type: 'device', actor: 'ESP32-Server', action: 'relay 1 turned ON', target: 'Living Room Lights', timestamp: '2026-02-22T14:29:48' },
  { id: 6, type: 'device', actor: 'ESP32-Server', action: 'thermostat set to 22°C', timestamp: '2026-02-22T14:29:47' },
  { id: 7, type: 'detection', actor: 'YOLOv8', action: 'detected car', target: 'Garage Camera', timestamp: '2026-02-22T14:25:30' },
  { id: 8, type: 'user', actor: 'admin', action: 'logged in', timestamp: '2026-02-22T14:20:00', metadata: { ip: '192.168.1.100' } },
  { id: 9, type: 'system', actor: 'System', action: 'scheduled backup completed', timestamp: '2026-02-22T14:00:00', metadata: { size: '2.4 GB' } },
  { id: 10, type: 'ai', actor: 'AI Engine', action: 'model inference latency spike', target: '45ms (avg: 12ms)', timestamp: '2026-02-22T13:55:00' },
  { id: 11, type: 'automation', actor: 'Scheduler', action: 'executed task "Morning Routine"', timestamp: '2026-02-22T07:00:00' },
  { id: 12, type: 'security', actor: 'Security', action: 'system armed', target: 'Night Mode', timestamp: '2026-02-22T23:00:00' },
];

const TYPE_CONFIG: Record<string, { icon: any; color: string; label: string }> = {
  detection: { icon: Eye, color: 'text-blue-400 bg-blue-500/10', label: 'Detection' },
  security: { icon: Shield, color: 'text-red-400 bg-red-500/10', label: 'Security' },
  automation: { icon: Zap, color: 'text-yellow-400 bg-yellow-500/10', label: 'Automation' },
  user: { icon: User, color: 'text-green-400 bg-green-500/10', label: 'User' },
  system: { icon: Settings, color: 'text-purple-400 bg-purple-500/10', label: 'System' },
  device: { icon: Zap, color: 'text-cyan-400 bg-cyan-500/10', label: 'Device' },
  ai: { icon: Camera, color: 'text-primary-400 bg-primary-500/10', label: 'AI' },
};

export default function ActivityFeed() {
  const [activities] = useState(MOCK_ACTIVITIES);
  const [filter, setFilter] = useState<string>('all');
  const [live, setLive] = useState(true);

  const filtered = filter === 'all' ? activities : activities.filter(a => a.type === filter);

  const formatTime = (ts: string) => {
    const diff = Date.now() - new Date(ts).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'Just now';
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    return new Date(ts).toLocaleDateString();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2"><Activity size={24} /> Activity Feed</h1>
          <p className="text-dark-400 text-sm mt-1">Real-time system activity stream</p>
        </div>
        <button onClick={() => setLive(!live)}
          className={`btn ${live ? 'btn-primary' : 'btn-secondary'} flex items-center gap-1`}>
          <span className={`w-2 h-2 rounded-full ${live ? 'bg-green-400 animate-pulse' : 'bg-dark-400'}`} />
          {live ? 'Live' : 'Paused'}
        </button>
      </div>

      {/* Type Filters */}
      <div className="flex flex-wrap gap-2">
        <button onClick={() => setFilter('all')}
          className={`px-3 py-1.5 rounded-lg text-sm ${filter === 'all' ? 'bg-primary-500 text-white' : 'bg-dark-700 text-dark-400'}`}>
          All ({activities.length})
        </button>
        {Object.entries(TYPE_CONFIG).map(([key, cfg]) => {
          const count = activities.filter(a => a.type === key).length;
          if (count === 0) return null;
          return (
            <button key={key} onClick={() => setFilter(key)}
              className={`px-3 py-1.5 rounded-lg text-sm flex items-center gap-1 ${filter === key ? 'bg-primary-500 text-white' : 'bg-dark-700 text-dark-400'}`}>
              {cfg.label} ({count})
            </button>
          );
        })}
      </div>

      {/* Feed */}
      <div className="relative">
        <div className="absolute left-5 top-0 bottom-0 w-0.5 bg-dark-700" />
        <div className="space-y-1">
          {filtered.map(activity => {
            const cfg = TYPE_CONFIG[activity.type];
            const Icon = cfg.icon;
            return (
              <div key={activity.id} className="relative flex items-start gap-3 py-3 pl-1 hover:bg-dark-700/20 rounded-lg px-2 transition-all">
                <div className={`relative z-10 w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${cfg.color}`}>
                  <Icon size={14} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-dark-200">
                    <span className="font-medium text-white">{activity.actor}</span>{' '}
                    {activity.action}
                    {activity.target && <span className="text-primary-400"> {activity.target}</span>}
                  </p>
                  {activity.metadata && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {Object.entries(activity.metadata).map(([k, v]) => (
                        <span key={k} className="px-1.5 py-0.5 bg-dark-700 rounded text-[10px] text-dark-300">
                          {k}: {Array.isArray(v) ? v.join(', ') : v}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <span className="text-xs text-dark-500 flex-shrink-0 flex items-center gap-1">
                  <Clock size={10} /> {formatTime(activity.timestamp)}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

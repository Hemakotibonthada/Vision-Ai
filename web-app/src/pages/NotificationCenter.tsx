import { useState, useEffect } from 'react';
import { Bell, CheckCircle, AlertTriangle, Info, Trash2, Check, Filter, Volume2, VolumeX, X } from 'lucide-react';

// Feature 58: Notification Center - real-time notification panel

type NotifType = 'success' | 'warning' | 'error' | 'info';

interface Notification {
  id: number;
  type: NotifType;
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  source: string;
  actionUrl?: string;
}

const MOCK_NOTIFS: Notification[] = [
  { id: 1, type: 'error', title: 'Intruder Detected', message: 'Unknown person detected at front door camera. Alarm triggered.', timestamp: '2026-02-22T14:30:00', read: false, source: 'Security' },
  { id: 2, type: 'warning', title: 'High Temperature', message: 'Server room temperature reached 38°C. Cooling activated.', timestamp: '2026-02-22T14:25:00', read: false, source: 'Environment' },
  { id: 3, type: 'success', title: 'Face Registered', message: 'New face "John Doe" successfully registered in the database.', timestamp: '2026-02-22T14:20:00', read: false, source: 'AI Engine' },
  { id: 4, type: 'info', title: 'System Update', message: 'Vision-AI Engine v3.0.1 is ready to install.', timestamp: '2026-02-22T14:15:00', read: true, source: 'System' },
  { id: 5, type: 'warning', title: 'Low Storage', message: 'Storage usage at 87%. Consider clearing old recordings.', timestamp: '2026-02-22T14:10:00', read: true, source: 'System' },
  { id: 6, type: 'success', title: 'Automation Triggered', message: '"Night Mode" scene activated. 5 devices configured.', timestamp: '2026-02-22T14:05:00', read: true, source: 'Jarvis' },
  { id: 7, type: 'info', title: 'Model Training Complete', message: 'Custom YOLOv8 model training finished. Accuracy: 94.2%', timestamp: '2026-02-22T14:00:00', read: true, source: 'AI Engine' },
  { id: 8, type: 'error', title: 'Device Offline', message: 'ESP32-CAM-03 in garage went offline. Last seen 5 minutes ago.', timestamp: '2026-02-22T13:55:00', read: true, source: 'Devices' },
];

const TYPE_ICONS = { success: CheckCircle, warning: AlertTriangle, error: Bell, info: Info };
const TYPE_COLORS = {
  success: 'text-green-400 bg-green-500/10 border-green-500/30',
  warning: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
  error: 'text-red-400 bg-red-500/10 border-red-500/30',
  info: 'text-blue-400 bg-blue-500/10 border-blue-500/30',
};

export default function NotificationCenter() {
  const [notifications, setNotifications] = useState(MOCK_NOTIFS);
  const [filter, setFilter] = useState<NotifType | 'all' | 'unread'>('all');
  const [soundEnabled, setSoundEnabled] = useState(true);

  const unread = notifications.filter(n => !n.read).length;
  const filtered = notifications.filter(n => {
    if (filter === 'unread') return !n.read;
    if (filter !== 'all') return n.type === filter;
    return true;
  });

  const markRead = (id: number) => setNotifications(ns => ns.map(n => n.id === id ? { ...n, read: true } : n));
  const markAllRead = () => setNotifications(ns => ns.map(n => ({ ...n, read: true })));
  const deleteNotif = (id: number) => setNotifications(ns => ns.filter(n => n.id !== id));
  const clearAll = () => setNotifications([]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="relative">
            <Bell size={24} className="text-white" />
            {unread > 0 && (
              <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full text-[10px] text-white flex items-center justify-center font-bold">
                {unread}
              </span>
            )}
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Notifications</h1>
            <p className="text-dark-400 text-sm">{unread} unread</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setSoundEnabled(!soundEnabled)} className="btn btn-secondary p-2">
            {soundEnabled ? <Volume2 size={14} /> : <VolumeX size={14} />}
          </button>
          <button onClick={markAllRead} className="btn btn-secondary flex items-center gap-1"><Check size={14} /> Mark All Read</button>
          <button onClick={clearAll} className="btn btn-secondary flex items-center gap-1 text-red-400"><Trash2 size={14} /> Clear All</button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2">
        {(['all', 'unread', 'error', 'warning', 'success', 'info'] as const).map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-lg text-sm capitalize transition-all ${filter === f ? 'bg-primary-500 text-white' : 'bg-dark-700 text-dark-400 hover:text-white'}`}>
            {f} {f === 'unread' && unread > 0 && <span className="ml-1 text-xs">({unread})</span>}
          </button>
        ))}
      </div>

      {/* Notification List */}
      <div className="space-y-3">
        {filtered.length === 0 && (
          <div className="card p-12 text-center">
            <Bell size={48} className="mx-auto text-dark-600 mb-3" />
            <p className="text-dark-400">No notifications</p>
          </div>
        )}
        {filtered.map(n => {
          const Icon = TYPE_ICONS[n.type];
          return (
            <div key={n.id}
              className={`card p-4 border transition-all ${!n.read ? TYPE_COLORS[n.type] : 'border-transparent opacity-70'}`}
              onClick={() => markRead(n.id)}>
              <div className="flex items-start gap-3">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${TYPE_COLORS[n.type]}`}>
                  <Icon size={18} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className={`font-semibold ${!n.read ? 'text-white' : 'text-dark-300'}`}>{n.title}</h3>
                    {!n.read && <span className="w-2 h-2 rounded-full bg-primary-500" />}
                  </div>
                  <p className="text-sm text-dark-400 mt-0.5">{n.message}</p>
                  <div className="flex items-center gap-3 mt-2 text-xs text-dark-500">
                    <span>{n.source}</span>
                    <span>&middot;</span>
                    <span>{new Date(n.timestamp).toLocaleString()}</span>
                  </div>
                </div>
                <button onClick={e => { e.stopPropagation(); deleteNotif(n.id); }}
                  className="p-1 rounded hover:bg-dark-700 text-dark-500 hover:text-red-400">
                  <X size={14} />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

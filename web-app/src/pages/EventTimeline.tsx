import { useState } from 'react';
import { Clock, Filter, Search, Camera, User, Shield, Thermometer, AlertTriangle, Info, Eye, Zap } from 'lucide-react';

// Feature 53: Visual Event Timeline with filters
// Feature 54: System Logs Viewer

type EventType = 'motion' | 'face' | 'alert' | 'system' | 'security' | 'sensor' | 'detection';

interface TimelineEvent {
  id: number;
  type: EventType;
  title: string;
  description: string;
  timestamp: string;
  severity: 'info' | 'warning' | 'critical';
  device?: string;
  image?: string;
}

const MOCK_EVENTS: TimelineEvent[] = [
  { id: 1, type: 'motion', title: 'Motion Detected', description: 'Motion in living room area', timestamp: '2026-02-22T14:30:00', severity: 'info', device: 'ESP32-CAM-01' },
  { id: 2, type: 'face', title: 'Face Recognized', description: 'Owner identified at front door', timestamp: '2026-02-22T14:28:00', severity: 'info', device: 'ESP32-CAM-01' },
  { id: 3, type: 'alert', title: 'High Temperature', description: 'Temperature exceeded 35°C in server room', timestamp: '2026-02-22T14:25:00', severity: 'warning', device: 'ESP32-Server-01' },
  { id: 4, type: 'security', title: 'Door Opened', description: 'Front door opened while armed', timestamp: '2026-02-22T14:20:00', severity: 'critical', device: 'ESP32-Server-01' },
  { id: 5, type: 'system', title: 'System Startup', description: 'Vision-AI Engine started successfully', timestamp: '2026-02-22T14:15:00', severity: 'info' },
  { id: 6, type: 'detection', title: 'Person Detected', description: '2 persons detected in parking area', timestamp: '2026-02-22T14:10:00', severity: 'info', device: 'ESP32-CAM-02' },
  { id: 7, type: 'sensor', title: 'Humidity Spike', description: 'Humidity rose to 85% in bathroom', timestamp: '2026-02-22T14:05:00', severity: 'warning', device: 'ESP32-Server-01' },
  { id: 8, type: 'security', title: 'Intruder Alert', description: 'Unknown person detected in restricted zone', timestamp: '2026-02-22T14:00:00', severity: 'critical', device: 'ESP32-CAM-01' },
  { id: 9, type: 'motion', title: 'Motion Stopped', description: 'No motion for 5 minutes in kitchen', timestamp: '2026-02-22T13:55:00', severity: 'info', device: 'ESP32-CAM-01' },
  { id: 10, type: 'system', title: 'Model Updated', description: 'YOLOv8 model retrained with 500 new images', timestamp: '2026-02-22T13:50:00', severity: 'info' },
];

const EVENT_ICONS: Record<EventType, any> = {
  motion: Eye, face: User, alert: AlertTriangle, system: Info,
  security: Shield, sensor: Thermometer, detection: Camera,
};

const SEVERITY_COLORS = {
  info: 'text-blue-400 bg-blue-500/10 border-blue-500/30',
  warning: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
  critical: 'text-red-400 bg-red-500/10 border-red-500/30',
};

export default function EventTimeline() {
  const [events] = useState(MOCK_EVENTS);
  const [filter, setFilter] = useState<EventType | 'all'>('all');
  const [search, setSearch] = useState('');
  const [severity, setSeverity] = useState<'all' | 'info' | 'warning' | 'critical'>('all');

  const filteredEvents = events.filter(e => {
    if (filter !== 'all' && e.type !== filter) return false;
    if (severity !== 'all' && e.severity !== severity) return false;
    if (search && !e.title.toLowerCase().includes(search.toLowerCase()) && !e.description.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Event Timeline</h1>
          <p className="text-dark-400 text-sm mt-1">{filteredEvents.length} events</p>
        </div>
      </div>

      {/* Filters */}
      <div className="card p-4">
        <div className="flex flex-wrap gap-3">
          <div className="relative flex-1 min-w-[200px]">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-400" />
            <input type="text" placeholder="Search events..." className="input-field w-full pl-10"
              value={search} onChange={e => setSearch(e.target.value)} />
          </div>
          <select className="input-field" value={filter} onChange={e => setFilter(e.target.value as any)}>
            <option value="all">All Types</option>
            <option value="motion">Motion</option>
            <option value="face">Face</option>
            <option value="alert">Alert</option>
            <option value="security">Security</option>
            <option value="sensor">Sensor</option>
            <option value="detection">Detection</option>
            <option value="system">System</option>
          </select>
          <select className="input-field" value={severity} onChange={e => setSeverity(e.target.value as any)}>
            <option value="all">All Severity</option>
            <option value="info">Info</option>
            <option value="warning">Warning</option>
            <option value="critical">Critical</option>
          </select>
        </div>
      </div>

      {/* Timeline */}
      <div className="relative">
        <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-dark-700" />
        <div className="space-y-4">
          {filteredEvents.map((event, i) => {
            const Icon = EVENT_ICONS[event.type] || Info;
            const colorClass = SEVERITY_COLORS[event.severity];
            return (
              <div key={event.id} className="relative flex gap-4 ml-1">
                <div className={`relative z-10 w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 border ${colorClass}`}>
                  <Icon size={16} />
                </div>
                <div className={`card p-4 flex-1 border ${SEVERITY_COLORS[event.severity].split(' ').slice(2).join(' ')}`}>
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-semibold text-white">{event.title}</h3>
                      <p className="text-sm text-dark-400 mt-1">{event.description}</p>
                      {event.device && (
                        <span className="inline-block mt-2 px-2 py-0.5 rounded bg-dark-700 text-xs text-dark-300">
                          {event.device}
                        </span>
                      )}
                    </div>
                    <div className="text-right flex-shrink-0">
                      <div className="flex items-center gap-1 text-xs text-dark-400">
                        <Clock size={12} />
                        {new Date(event.timestamp).toLocaleTimeString()}
                      </div>
                      <span className={`text-xs px-2 py-0.5 rounded-full mt-1 inline-block ${colorClass}`}>
                        {event.severity}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

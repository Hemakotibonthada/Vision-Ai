import { useState } from 'react';
import { FileText, Search, Download, RefreshCw, Filter, AlertTriangle, Info, Bug, Zap, Trash2 } from 'lucide-react';

// Feature 54: System Logs Viewer with search & filtering

type LogLevel = 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';

interface LogEntry {
  id: number;
  timestamp: string;
  level: LogLevel;
  source: string;
  message: string;
  details?: string;
}

const MOCK_LOGS: LogEntry[] = [
  { id: 1, timestamp: '2026-02-22T14:30:15.234', level: 'INFO', source: 'ai-engine', message: 'Detection pipeline initialized successfully' },
  { id: 2, timestamp: '2026-02-22T14:30:10.123', level: 'DEBUG', source: 'esp32-cam', message: 'Frame captured: 640x480 @ 15fps' },
  { id: 3, timestamp: '2026-02-22T14:30:05.456', level: 'WARNING', source: 'jarvis', message: 'Temperature reading above threshold: 38.5°C', details: 'sensor_id=DHT22_01, threshold=35.0' },
  { id: 4, timestamp: '2026-02-22T14:29:58.789', level: 'ERROR', source: 'ai-engine', message: 'Model inference timeout after 5000ms', details: 'model=yolov8n, input_size=640x640' },
  { id: 5, timestamp: '2026-02-22T14:29:50.012', level: 'INFO', source: 'jarvis', message: 'Automation rule triggered: "Night Mode"' },
  { id: 6, timestamp: '2026-02-22T14:29:45.345', level: 'CRITICAL', source: 'esp32-server', message: 'Relay board communication failure', details: 'i2c_addr=0x20, retry=3/3' },
  { id: 7, timestamp: '2026-02-22T14:29:40.678', level: 'INFO', source: 'web-app', message: 'User admin logged in from 192.168.1.100' },
  { id: 8, timestamp: '2026-02-22T14:29:35.901', level: 'DEBUG', source: 'ai-engine', message: 'Face embedding computed: 128-dim vector, confidence=0.95' },
  { id: 9, timestamp: '2026-02-22T14:29:30.234', level: 'WARNING', source: 'esp32-cam', message: 'WiFi signal weak: RSSI=-75dBm', details: 'ssid=HomeNetwork, channel=6' },
  { id: 10, timestamp: '2026-02-22T14:29:25.567', level: 'INFO', source: 'jarvis', message: 'Energy report generated: 2.4 kWh today' },
  { id: 11, timestamp: '2026-02-22T14:29:20.890', level: 'ERROR', source: 'ai-engine', message: 'CUDA out of memory during batch inference', details: 'allocated=1.2GB, requested=0.5GB' },
  { id: 12, timestamp: '2026-02-22T14:29:15.123', level: 'INFO', source: 'esp32-server', message: 'Door sensor: CLOSED -> OPEN transition' },
];

const LEVEL_COLORS: Record<LogLevel, string> = {
  DEBUG: 'text-gray-400 bg-gray-500/10',
  INFO: 'text-blue-400 bg-blue-500/10',
  WARNING: 'text-yellow-400 bg-yellow-500/10',
  ERROR: 'text-red-400 bg-red-500/10',
  CRITICAL: 'text-red-500 bg-red-600/20 font-bold',
};

const LEVEL_ICONS: Record<LogLevel, any> = {
  DEBUG: Bug, INFO: Info, WARNING: AlertTriangle, ERROR: Zap, CRITICAL: AlertTriangle,
};

export default function SystemLogs() {
  const [logs] = useState(MOCK_LOGS);
  const [search, setSearch] = useState('');
  const [levelFilter, setLevelFilter] = useState<LogLevel | 'ALL'>('ALL');
  const [sourceFilter, setSourceFilter] = useState<string>('all');
  const [expandedLog, setExpandedLog] = useState<number | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);

  const sources = Array.from(new Set(logs.map(l => l.source)));
  const filtered = logs.filter(l => {
    if (levelFilter !== 'ALL' && l.level !== levelFilter) return false;
    if (sourceFilter !== 'all' && l.source !== sourceFilter) return false;
    if (search && !l.message.toLowerCase().includes(search.toLowerCase()) && !l.source.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const levelCounts = logs.reduce((acc, l) => { acc[l.level] = (acc[l.level] || 0) + 1; return acc; }, {} as Record<string, number>);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2"><FileText size={24} /> System Logs</h1>
          <p className="text-dark-400 text-sm mt-1">{filtered.length} entries shown</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setAutoRefresh(!autoRefresh)}
            className={`btn ${autoRefresh ? 'btn-primary' : 'btn-secondary'} flex items-center gap-1`}>
            <RefreshCw size={14} className={autoRefresh ? 'animate-spin' : ''} /> {autoRefresh ? 'Auto' : 'Manual'}
          </button>
          <button className="btn btn-secondary flex items-center gap-1"><Download size={14} /> Export</button>
          <button className="btn btn-secondary flex items-center gap-1 text-red-400"><Trash2 size={14} /> Clear</button>
        </div>
      </div>

      {/* Level Summary */}
      <div className="grid grid-cols-5 gap-3">
        {(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] as LogLevel[]).map(level => (
          <button key={level} onClick={() => setLevelFilter(levelFilter === level ? 'ALL' : level)}
            className={`card p-3 text-center cursor-pointer transition-all ${levelFilter === level ? 'ring-2 ring-primary-500' : ''}`}>
            <div className={`text-2xl font-bold ${LEVEL_COLORS[level].split(' ')[0]}`}>{levelCounts[level] || 0}</div>
            <div className="text-xs text-dark-400 mt-1">{level}</div>
          </button>
        ))}
      </div>

      {/* Filters */}
      <div className="card p-4 flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-400" />
          <input type="text" placeholder="Search logs..." className="input-field w-full pl-10"
            value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <select className="input-field" value={sourceFilter} onChange={e => setSourceFilter(e.target.value)}>
          <option value="all">All Sources</option>
          {sources.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      {/* Log Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-dark-700 text-dark-400">
                <th className="px-4 py-3 text-left">Time</th>
                <th className="px-4 py-3 text-left">Level</th>
                <th className="px-4 py-3 text-left">Source</th>
                <th className="px-4 py-3 text-left">Message</th>
              </tr>
            </thead>
            <tbody className="font-mono text-xs">
              {filtered.map(log => {
                const LvlIcon = LEVEL_ICONS[log.level];
                return (
                  <>
                    <tr key={log.id} onClick={() => setExpandedLog(expandedLog === log.id ? null : log.id)}
                      className="border-b border-dark-800 hover:bg-dark-700/30 cursor-pointer transition-colors">
                      <td className="px-4 py-2 text-dark-400 whitespace-nowrap">{new Date(log.timestamp).toLocaleTimeString()}.{log.timestamp.split('.')[1]?.slice(0, 3)}</td>
                      <td className="px-4 py-2">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs ${LEVEL_COLORS[log.level]}`}>
                          <LvlIcon size={10} /> {log.level}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-primary-400">{log.source}</td>
                      <td className="px-4 py-2 text-dark-200">{log.message}</td>
                    </tr>
                    {expandedLog === log.id && log.details && (
                      <tr key={`${log.id}-details`} className="border-b border-dark-800">
                        <td colSpan={4} className="px-4 py-3 bg-dark-800/50">
                          <div className="text-dark-400">
                            <span className="text-dark-500">Details: </span>
                            {log.details}
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

import { useState } from 'react';
import { BarChart2, Download, FileText, Calendar, Printer, PieChart, Table, TrendingUp } from 'lucide-react';

// Feature 62: Stats Dashboard Widgets
// Feature 63: Export/Report Generator

interface Widget {
  id: string;
  title: string;
  type: 'number' | 'chart' | 'list' | 'progress';
  value: string | number;
  change?: number;
  data?: any[];
}

const WIDGETS: Widget[] = [
  { id: 'w1', title: 'Total Detections Today', type: 'number', value: 1247, change: 12.5 },
  { id: 'w2', title: 'Active Cameras', type: 'number', value: '4/6', change: 0 },
  { id: 'w3', title: 'Avg Inference Time', type: 'number', value: '18ms', change: -5.2 },
  { id: 'w4', title: 'Storage Used', type: 'progress', value: 67 },
  { id: 'w5', title: 'Faces Registered', type: 'number', value: 23, change: 4.3 },
  { id: 'w6', title: 'Alerts Today', type: 'number', value: 7, change: -15.0 },
  { id: 'w7', title: 'Uptime', type: 'number', value: '99.7%', change: 0.1 },
  { id: 'w8', title: 'Energy Usage', type: 'number', value: '2.4 kWh', change: -8.3 },
  { id: 'w9', title: 'Top Detected Objects', type: 'list', value: '', data: [
    { label: 'Person', count: 456 }, { label: 'Car', count: 234 }, { label: 'Dog', count: 89 },
    { label: 'Package', count: 45 }, { label: 'Cat', count: 23 },
  ]},
  { id: 'w10', title: 'Detection by Camera', type: 'list', value: '', data: [
    { label: 'Front Door', count: 520 }, { label: 'Garage', count: 310 },
    { label: 'Living Room', count: 280 }, { label: 'Backyard', count: 137 },
  ]},
];

const REPORT_TYPES = [
  { id: 'daily', label: 'Daily Summary', icon: Calendar, description: 'Detection counts, alerts, and system status for today' },
  { id: 'weekly', label: 'Weekly Analytics', icon: TrendingUp, description: 'Trends, patterns, and insights for the past 7 days' },
  { id: 'security', label: 'Security Report', icon: FileText, description: 'Intrusion attempts, face recognition, and access logs' },
  { id: 'energy', label: 'Energy Report', icon: PieChart, description: 'Power consumption, optimization suggestions, cost analysis' },
  { id: 'model', label: 'Model Performance', icon: BarChart2, description: 'AI model accuracy, latency, and resource usage metrics' },
  { id: 'custom', label: 'Custom Report', icon: Table, description: 'Build a custom report with selected metrics and date range' },
];

export default function StatsWidgets() {
  const [visibleWidgets, setVisibleWidgets] = useState(WIDGETS.map(w => w.id));
  const [reportFormat, setReportFormat] = useState<'pdf' | 'csv' | 'json'>('pdf');
  const [dateRange, setDateRange] = useState({ from: '2026-02-15', to: '2026-02-22' });
  const [generating, setGenerating] = useState<string | null>(null);

  const generate = (type: string) => {
    setGenerating(type);
    setTimeout(() => setGenerating(null), 2000);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2"><BarChart2 size={24} /> Statistics & Reports</h1>
          <p className="text-dark-400 text-sm mt-1">Dashboard widgets and report generation</p>
        </div>
      </div>

      {/* Widgets Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {WIDGETS.filter(w => visibleWidgets.includes(w.id)).map(widget => (
          <div key={widget.id} className="card p-4">
            <div className="text-xs text-dark-400 mb-2">{widget.title}</div>
            {widget.type === 'number' && (
              <div>
                <div className="text-2xl font-bold text-white">{widget.value}</div>
                {widget.change !== undefined && widget.change !== 0 && (
                  <div className={`text-xs mt-1 flex items-center gap-1 ${widget.change > 0 ? 'text-green-400' : 'text-red-400'}`}>
                    <TrendingUp size={10} className={widget.change < 0 ? 'rotate-180' : ''} />
                    {Math.abs(widget.change)}%
                  </div>
                )}
              </div>
            )}
            {widget.type === 'progress' && (
              <div>
                <div className="text-2xl font-bold text-white">{widget.value}%</div>
                <div className="w-full bg-dark-700 rounded-full h-2 mt-2">
                  <div className={`h-2 rounded-full ${Number(widget.value) > 80 ? 'bg-red-500' : Number(widget.value) > 60 ? 'bg-yellow-500' : 'bg-green-500'}`}
                    style={{ width: `${widget.value}%` }} />
                </div>
              </div>
            )}
            {widget.type === 'list' && widget.data && (
              <div className="space-y-1.5">
                {widget.data.map((item: any, i: number) => (
                  <div key={i} className="flex items-center justify-between text-xs">
                    <span className="text-dark-300">{item.label}</span>
                    <span className="text-white font-medium">{item.count}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Report Generator */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2"><FileText size={18} /> Report Generator</h2>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-sm">
              <label className="text-dark-400">From</label>
              <input type="date" className="input-field" value={dateRange.from} onChange={e => setDateRange({ ...dateRange, from: e.target.value })} />
              <label className="text-dark-400">To</label>
              <input type="date" className="input-field" value={dateRange.to} onChange={e => setDateRange({ ...dateRange, to: e.target.value })} />
            </div>
            <div className="flex items-center gap-1">
              {(['pdf', 'csv', 'json'] as const).map(fmt => (
                <button key={fmt} onClick={() => setReportFormat(fmt)}
                  className={`px-2 py-1 rounded text-xs uppercase ${reportFormat === fmt ? 'bg-primary-500 text-white' : 'bg-dark-700 text-dark-400'}`}>{fmt}</button>
              ))}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {REPORT_TYPES.map(report => {
            const Icon = report.icon;
            return (
              <div key={report.id} className="bg-dark-800 rounded-xl p-4 border border-dark-700 hover:border-primary-500/30 transition-all">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-lg bg-primary-500/10 flex items-center justify-center flex-shrink-0">
                    <Icon size={18} className="text-primary-400" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-medium text-white text-sm">{report.label}</h3>
                    <p className="text-xs text-dark-400 mt-1">{report.description}</p>
                    <button onClick={() => generate(report.id)}
                      className="mt-3 btn btn-secondary text-xs py-1 flex items-center gap-1">
                      {generating === report.id ? <span className="animate-spin">⏳</span> : <Download size={12} />}
                      {generating === report.id ? 'Generating...' : `Export ${reportFormat.toUpperCase()}`}
                    </button>
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

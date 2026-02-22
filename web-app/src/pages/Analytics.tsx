import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '../services/api';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  ScatterChart, Scatter, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import {
  BarChart3, TrendingUp, Clock, CalendarDays, PieChart as PieIcon,
  Activity, Target, Download, Filter
} from 'lucide-react';

const COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316'];

export default function Analytics() {
  const [timeRange, setTimeRange] = useState(24);
  const [period, setPeriod] = useState<'hourly' | 'daily' | 'weekly' | 'monthly'>('daily');
  const [days, setDays] = useState(30);

  const { data: timeline } = useQuery({
    queryKey: ['timeline', timeRange],
    queryFn: () => analyticsApi.getTimeline(timeRange, Math.max(5, Math.floor(timeRange / 24) * 60 || 60)),
  });
  const { data: peakHours } = useQuery({ queryKey: ['peakHours'], queryFn: () => analyticsApi.getPeakHours(7) });
  const { data: trends } = useQuery({ queryKey: ['trends', period, days], queryFn: () => analyticsApi.getTrends(period, days) });
  const { data: dashboard } = useQuery({ queryKey: ['dashboard'], queryFn: () => analyticsApi.getDashboard() });
  const { data: report } = useQuery({ queryKey: ['report'], queryFn: () => analyticsApi.getReport('daily') });

  const tl = timeline?.data || [];
  const ph = peakHours?.data || [];
  const tr = trends?.data || [];
  const db = dashboard?.data || {};
  const rp = report?.data || {};

  // Simulated class distribution for pie chart
  const classData = Object.entries(db.class_distribution || {}).map(([name, value]) => ({
    name, value: value as number,
  }));

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="card flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Filter size={16} className="text-dark-400" />
            <select className="select w-32" value={timeRange} onChange={(e) => setTimeRange(+e.target.value)}>
              <option value={6}>6 Hours</option>
              <option value={12}>12 Hours</option>
              <option value={24}>24 Hours</option>
              <option value={48}>48 Hours</option>
              <option value={168}>7 Days</option>
              <option value={720}>30 Days</option>
            </select>
          </div>
          <div className="flex items-center gap-2">
            <CalendarDays size={16} className="text-dark-400" />
            <select className="select w-32" value={period} onChange={(e) => setPeriod(e.target.value as any)}>
              <option value="hourly">Hourly</option>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </div>
        </div>
        <button className="btn-secondary flex items-center gap-2">
          <Download size={16} /> Export Report
        </button>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        {[
          { label: 'Total Detections', value: db.total_detections || 0, icon: Target },
          { label: 'Avg per Hour', value: db.avg_per_hour?.toFixed(1) || 0, icon: Clock },
          { label: 'Peak Hour', value: db.peak_hour || 'N/A', icon: TrendingUp },
          { label: 'Unique Classes', value: db.unique_classes || 0, icon: PieIcon },
          { label: 'Active Zones', value: db.active_zones || 0, icon: Activity },
          { label: 'Events Today', value: db.events_today || 0, icon: BarChart3 },
        ].map(({ label, value, icon: Icon }) => (
          <div key={label} className="stat-card">
            <Icon size={20} className="text-primary-400" />
            <div className="stat-value text-lg">{value}</div>
            <div className="stat-label">{label}</div>
          </div>
        ))}
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Detection Timeline */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Detection Timeline</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={tl}>
              <defs>
                <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="time" stroke="#64748b" fontSize={11} />
              <YAxis stroke="#64748b" fontSize={11} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} />
              <Area type="monotone" dataKey="count" stroke="#3b82f6" fill="url(#colorCount)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Peak Hours */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Peak Detection Hours</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={ph}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="hour" stroke="#64748b" fontSize={11} />
              <YAxis stroke="#64748b" fontSize={11} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} />
              <Bar dataKey="count" fill="#22c55e" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Trends */}
        <div className="card col-span-2">
          <h3 className="text-lg font-semibold mb-4">Trends ({period})</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={tr}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="period" stroke="#64748b" fontSize={11} />
              <YAxis stroke="#64748b" fontSize={11} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} />
              <Legend />
              <Line type="monotone" dataKey="count" stroke="#3b82f6" strokeWidth={2} name="Detections" />
              <Line type="monotone" dataKey="avg_confidence" stroke="#22c55e" strokeWidth={2} name="Avg Confidence" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Class Distribution */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Class Distribution</h3>
          {classData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie data={classData} cx="50%" cy="50%" innerRadius={60} outerRadius={100} paddingAngle={5} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                  {classData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-64 text-dark-500">
              <p>No class data yet</p>
            </div>
          )}
        </div>
      </div>

      {/* Report Summary */}
      {rp && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Daily Report Summary</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 bg-dark-900 rounded-lg">
              <div className="text-2xl font-bold text-blue-400">{rp.total_detections || 0}</div>
              <div className="text-sm text-dark-400">Total Detections</div>
            </div>
            <div className="p-4 bg-dark-900 rounded-lg">
              <div className="text-2xl font-bold text-green-400">{rp.unique_objects || 0}</div>
              <div className="text-sm text-dark-400">Unique Objects</div>
            </div>
            <div className="p-4 bg-dark-900 rounded-lg">
              <div className="text-2xl font-bold text-yellow-400">{rp.alerts_triggered || 0}</div>
              <div className="text-sm text-dark-400">Alerts Triggered</div>
            </div>
            <div className="p-4 bg-dark-900 rounded-lg">
              <div className="text-2xl font-bold text-purple-400">{rp.avg_response_ms?.toFixed(0) || 0}ms</div>
              <div className="text-sm text-dark-400">Avg Response Time</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

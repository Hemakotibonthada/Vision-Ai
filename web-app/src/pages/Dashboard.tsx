import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { analyticsApi, deviceApi, systemApi, detectionApi } from '../services/api';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { Activity, Cpu, HardDrive, Thermometer, Eye, Clock, Zap, Users, Camera, AlertTriangle, TrendingUp, CheckCircle } from 'lucide-react';

const COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316'];

export default function Dashboard() {
  const { data: health } = useQuery({ queryKey: ['health'], queryFn: () => systemApi.health(), refetchInterval: 10000 });
  const { data: dashboard } = useQuery({ queryKey: ['dashboard'], queryFn: () => analyticsApi.getDashboard(), refetchInterval: 30000 });
  const { data: timeline } = useQuery({ queryKey: ['timeline'], queryFn: () => analyticsApi.getTimeline(24, 60) });
  const { data: devices } = useQuery({ queryKey: ['devices'], queryFn: () => deviceApi.list() });
  const { data: detStats } = useQuery({ queryKey: ['detStats'], queryFn: () => detectionApi.getStats() });
  const { data: trends } = useQuery({ queryKey: ['trends'], queryFn: () => analyticsApi.getTrends('daily', 7) });

  const h = health?.data;
  const d = dashboard?.data;
  const tl = timeline?.data || [];
  const devs = devices?.data || [];
  const ds = detStats?.data;
  const tr = trends?.data || [];

  const stats = [
    { label: 'Total Detections', value: d?.total_detections || 0, icon: Eye, color: 'text-blue-400', bg: 'bg-blue-500/10' },
    { label: 'Active Devices', value: devs.length, icon: Cpu, color: 'text-green-400', bg: 'bg-green-500/10' },
    { label: 'Alert Events', value: d?.total_events || 0, icon: AlertTriangle, color: 'text-yellow-400', bg: 'bg-yellow-500/10' },
    { label: 'Models Loaded', value: ds?.models_loaded || 1, icon: Brain, color: 'text-purple-400', bg: 'bg-purple-500/10' },
    { label: 'Avg Inference', value: `${ds?.avg_inference_ms?.toFixed(0) || 0}ms`, icon: Zap, color: 'text-cyan-400', bg: 'bg-cyan-500/10' },
    { label: 'Uptime', value: h ? `${(h.cpu_percent || 0).toFixed(0)}%` : 'N/A', icon: Activity, color: 'text-pink-400', bg: 'bg-pink-500/10' },
  ];

  return (
    <div className="space-y-6">
      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {stats.map(({ label, value, icon: Icon, color, bg }) => (
          <div key={label} className="card-hover">
            <div className={`w-10 h-10 rounded-lg ${bg} flex items-center justify-center mb-3`}>
              <Icon size={20} className={color} />
            </div>
            <div className="stat-value text-xl">{value}</div>
            <div className="stat-label">{label}</div>
          </div>
        ))}
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Detection Timeline */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Detection Timeline (24h)</h3>
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={tl}>
              <defs>
                <linearGradient id="colorDet" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="time" stroke="#64748b" fontSize={12} />
              <YAxis stroke="#64748b" fontSize={12} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} />
              <Area type="monotone" dataKey="count" stroke="#3b82f6" fill="url(#colorDet)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Weekly Trends */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Weekly Trends</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={tr}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="period" stroke="#64748b" fontSize={12} />
              <YAxis stroke="#64748b" fontSize={12} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} />
              <Bar dataKey="count" fill="#22c55e" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* System Health */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">System Health</h3>
          <div className="space-y-4">
            <HealthBar label="CPU" value={h?.cpu_percent || 0} color="bg-blue-500" />
            <HealthBar label="Memory" value={h?.memory?.percent || 0} color="bg-green-500" />
            <HealthBar label="Disk" value={h?.disk?.percent || 0} color="bg-yellow-500" />
            <div className="flex items-center justify-between text-sm mt-4">
              <span className="text-dark-400">GPU</span>
              <span className={h?.gpu?.available ? 'badge-success' : 'badge-danger'}>
                {h?.gpu?.available ? h.gpu.name || 'Available' : 'Not Available'}
              </span>
            </div>
          </div>
        </div>

        {/* Device Status */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Devices</h3>
          <div className="space-y-3 max-h-64 overflow-y-auto">
            {devs.length === 0 ? (
              <p className="text-dark-400 text-sm">No devices registered</p>
            ) : (
              devs.map((dev: any) => (
                <div key={dev.device_id} className="flex items-center justify-between p-3 bg-dark-900 rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className={`w-2 h-2 rounded-full ${dev.is_active ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
                    <div>
                      <p className="text-sm font-medium">{dev.name}</p>
                      <p className="text-xs text-dark-400">{dev.device_type} | {dev.ip_address || 'N/A'}</p>
                    </div>
                  </div>
                  <span className={dev.is_active ? 'badge-success' : 'badge-danger'}>
                    {dev.is_active ? 'Online' : 'Offline'}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Recent Events */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Recent Events</h3>
          <div className="space-y-3 max-h-64 overflow-y-auto">
            {(d?.recent_events || []).length === 0 ? (
              <p className="text-dark-400 text-sm">No recent events</p>
            ) : (
              (d?.recent_events || []).map((evt: any, i: number) => (
                <div key={i} className="flex items-start gap-3 p-3 bg-dark-900 rounded-lg">
                  <div className={`w-2 h-2 rounded-full mt-1.5 ${
                    evt.severity >= 3 ? 'bg-red-500' : evt.severity >= 2 ? 'bg-yellow-500' : 'bg-blue-500'
                  }`} />
                  <div>
                    <p className="text-sm font-medium">{evt.title}</p>
                    <p className="text-xs text-dark-400">{evt.type} | {evt.created_at}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function HealthBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-dark-300">{label}</span>
        <span className="text-white font-medium">{value.toFixed(1)}%</span>
      </div>
      <div className="h-2 bg-dark-700 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all duration-500`} style={{ width: `${Math.min(value, 100)}%` }} />
      </div>
    </div>
  );
}

// Needed for stats - import missing
import { Brain } from 'lucide-react';

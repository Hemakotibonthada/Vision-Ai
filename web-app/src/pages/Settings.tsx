import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { authApi, systemApi, adminApi } from '../services/api';
import { useAuthStore, useAppStore } from '../store';
import toast from 'react-hot-toast';
import {
  User, Shield, Database, Server, Palette, Bell, Key, Globe,
  Save, RefreshCw, Users, Activity, Cpu, HardDrive, Trash2
} from 'lucide-react';

export default function Settings() {
  const { user, updateUser } = useAuthStore();
  const { theme, toggleTheme } = useAppStore();
  const [tab, setTab] = useState<'profile' | 'system' | 'admin' | 'about'>('profile');
  const [profile, setProfile] = useState({ email: user?.email || '', preferences: user?.preferences || {} });
  const [passwords, setPasswords] = useState({ current_password: '', new_password: '', confirm: '' });

  const { data: health } = useQuery({ queryKey: ['health'], queryFn: () => systemApi.health() });
  const { data: sysConfig } = useQuery({ queryKey: ['sysConfig'], queryFn: () => systemApi.getConfig() });
  const { data: users } = useQuery({ queryKey: ['adminUsers'], queryFn: () => adminApi.getUsers(), enabled: user?.role === 'admin' });
  const { data: activity } = useQuery({ queryKey: ['activity'], queryFn: () => adminApi.getActivity(50), enabled: user?.role === 'admin' });

  const updateProfile = useMutation({
    mutationFn: (data: any) => authApi.updateProfile(data),
    onSuccess: () => { toast.success('Profile updated'); },
  });

  const changePassword = useMutation({
    mutationFn: (data: any) => authApi.changePassword(data),
    onSuccess: () => { toast.success('Password changed'); setPasswords({ current_password: '', new_password: '', confirm: '' }); },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Failed'),
  });

  const h = health?.data;

  const tabs = [
    { key: 'profile', label: 'Profile', icon: User },
    { key: 'system', label: 'System', icon: Server },
    ...(user?.role === 'admin' ? [{ key: 'admin', label: 'Admin', icon: Shield }] : []),
    { key: 'about', label: 'About', icon: Globe },
  ];

  return (
    <div className="space-y-6">
      <div className="flex gap-1 p-1 bg-dark-800 rounded-lg w-fit">
        {tabs.map(({ key, label, icon: Icon }: any) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-colors ${
              tab === key ? 'bg-primary-600 text-white' : 'text-dark-400 hover:text-white hover:bg-dark-700'
            }`}
          >
            <Icon size={16} /> {label}
          </button>
        ))}
      </div>

      {tab === 'profile' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="card">
            <h3 className="font-semibold mb-4">Profile Settings</h3>
            <div className="space-y-4">
              <div>
                <label className="text-sm text-dark-400">Username</label>
                <input className="input mt-1" value={user?.username || ''} disabled />
              </div>
              <div>
                <label className="text-sm text-dark-400">Email</label>
                <input className="input mt-1" value={profile.email} onChange={(e) => setProfile({ ...profile, email: e.target.value })} />
              </div>
              <div>
                <label className="text-sm text-dark-400">Role</label>
                <input className="input mt-1" value={user?.role || ''} disabled />
              </div>
              <div>
                <label className="text-sm text-dark-400">Theme</label>
                <button onClick={toggleTheme} className="btn-secondary w-full mt-1 flex items-center justify-center gap-2">
                  <Palette size={16} /> {theme === 'dark' ? 'Switch to Light' : 'Switch to Dark'}
                </button>
              </div>
              <button onClick={() => updateProfile.mutate(profile)} className="btn-primary w-full flex items-center justify-center gap-2">
                <Save size={16} /> Save Changes
              </button>
            </div>
          </div>

          <div className="card">
            <h3 className="font-semibold mb-4">Change Password</h3>
            <div className="space-y-4">
              <div>
                <label className="text-sm text-dark-400">Current Password</label>
                <input type="password" className="input mt-1" value={passwords.current_password} onChange={(e) => setPasswords({ ...passwords, current_password: e.target.value })} />
              </div>
              <div>
                <label className="text-sm text-dark-400">New Password</label>
                <input type="password" className="input mt-1" value={passwords.new_password} onChange={(e) => setPasswords({ ...passwords, new_password: e.target.value })} />
              </div>
              <div>
                <label className="text-sm text-dark-400">Confirm Password</label>
                <input type="password" className="input mt-1" value={passwords.confirm} onChange={(e) => setPasswords({ ...passwords, confirm: e.target.value })} />
              </div>
              <button
                onClick={() => {
                  if (passwords.new_password !== passwords.confirm) { toast.error('Passwords do not match'); return; }
                  changePassword.mutate(passwords);
                }}
                className="btn-primary w-full flex items-center justify-center gap-2"
              >
                <Key size={16} /> Change Password
              </button>
            </div>
          </div>
        </div>
      )}

      {tab === 'system' && (
        <div className="space-y-4">
          <div className="card">
            <h3 className="font-semibold mb-4">System Information</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <InfoCard icon={Cpu} label="CPU" value={`${h?.cpu_percent?.toFixed(1) || 0}%`} />
              <InfoCard icon={HardDrive} label="Memory" value={`${h?.memory?.percent?.toFixed(1) || 0}%`} />
              <InfoCard icon={Database} label="Disk" value={`${h?.disk?.percent?.toFixed(1) || 0}%`} />
              <InfoCard icon={Activity} label="GPU" value={h?.gpu?.available ? h.gpu.name : 'N/A'} />
            </div>
          </div>
          <div className="card">
            <h3 className="font-semibold mb-4">System Configuration</h3>
            <div className="space-y-2">
              {Object.entries(sysConfig?.data || {}).map(([key, val]: any) => (
                <div key={key} className="flex items-center justify-between p-3 bg-dark-900 rounded-lg">
                  <div>
                    <span className="text-sm font-medium">{key}</span>
                    {val.description && <p className="text-xs text-dark-500">{val.description}</p>}
                  </div>
                  <span className="text-sm text-dark-300 font-mono">{JSON.stringify(val.value)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {tab === 'admin' && (
        <div className="space-y-4">
          <div className="card">
            <h3 className="font-semibold mb-4">User Management</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-dark-400 border-b border-dark-700">
                    <th className="p-3">User</th><th className="p-3">Email</th><th className="p-3">Role</th><th className="p-3">Status</th><th className="p-3">Last Login</th>
                  </tr>
                </thead>
                <tbody>
                  {(users?.data || []).map((u: any) => (
                    <tr key={u.id} className="table-row">
                      <td className="p-3 font-medium">{u.username}</td>
                      <td className="p-3 text-dark-400">{u.email || '-'}</td>
                      <td className="p-3"><span className={u.role === 'admin' ? 'badge-danger' : 'badge-info'}>{u.role}</span></td>
                      <td className="p-3"><span className={u.is_active ? 'badge-success' : 'badge-danger'}>{u.is_active ? 'Active' : 'Disabled'}</span></td>
                      <td className="p-3 text-dark-400">{u.last_login?.split('T')[0] || 'Never'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card">
            <h3 className="font-semibold mb-4">Activity Log</h3>
            <div className="max-h-64 overflow-y-auto space-y-2">
              {(activity?.data || []).map((a: any) => (
                <div key={a.id} className="flex items-center justify-between p-2 bg-dark-900 rounded-lg text-sm">
                  <div className="flex items-center gap-2">
                    <Activity size={14} className="text-dark-500" />
                    <span>{a.action}</span>
                  </div>
                  <span className="text-dark-500 text-xs">{a.created_at}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {tab === 'about' && (
        <div className="card max-w-2xl">
          <div className="text-center">
            <div className="w-20 h-20 mx-auto rounded-2xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center text-white font-bold text-3xl mb-4">VA</div>
            <h2 className="text-2xl font-bold">Vision-AI</h2>
            <p className="text-dark-400 mt-1">Intelligent IoT Vision System</p>
            <p className="text-dark-500 text-sm mt-2">Version 1.0.0</p>
          </div>
          <div className="mt-8 space-y-3 text-sm">
            <div className="flex justify-between p-3 bg-dark-900 rounded-lg"><span className="text-dark-400">Features</span><span>325+</span></div>
            <div className="flex justify-between p-3 bg-dark-900 rounded-lg"><span className="text-dark-400">ESP32 Support</span><span>Server + CAM</span></div>
            <div className="flex justify-between p-3 bg-dark-900 rounded-lg"><span className="text-dark-400">AI Models</span><span>YOLOv8, ResNet, EfficientNet</span></div>
            <div className="flex justify-between p-3 bg-dark-900 rounded-lg"><span className="text-dark-400">Communication</span><span>MQTT, WebSocket, REST API</span></div>
            <div className="flex justify-between p-3 bg-dark-900 rounded-lg"><span className="text-dark-400">Training</span><span>Self-Train, Transfer, Active Learning</span></div>
            <div className="flex justify-between p-3 bg-dark-900 rounded-lg"><span className="text-dark-400">License</span><span>MIT</span></div>
          </div>
        </div>
      )}
    </div>
  );
}

function InfoCard({ icon: Icon, label, value }: { icon: any; label: string; value: string }) {
  return (
    <div className="p-4 bg-dark-900 rounded-lg">
      <Icon size={20} className="text-primary-400 mb-2" />
      <div className="text-sm font-medium">{value}</div>
      <div className="text-xs text-dark-400">{label}</div>
    </div>
  );
}

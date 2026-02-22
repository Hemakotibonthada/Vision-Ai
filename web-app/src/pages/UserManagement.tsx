import { useState } from 'react';
import { Users, Plus, Edit2, Trash2, Shield, CheckCircle, XCircle, Key, Mail, Clock } from 'lucide-react';

// Feature 57: User Management - admin user CRUD with roles

interface UserProfile {
  id: number;
  username: string;
  email: string;
  role: 'admin' | 'operator' | 'viewer' | 'api_user';
  status: 'active' | 'inactive' | 'locked';
  lastLogin: string;
  created: string;
  permissions: string[];
}

const MOCK_USERS: UserProfile[] = [
  { id: 1, username: 'admin', email: 'admin@visionai.local', role: 'admin', status: 'active', lastLogin: '2026-02-22T14:30:00', created: '2026-01-01', permissions: ['all'] },
  { id: 2, username: 'operator1', email: 'op1@visionai.local', role: 'operator', status: 'active', lastLogin: '2026-02-22T12:00:00', created: '2026-01-15', permissions: ['view', 'control_devices', 'manage_cameras'] },
  { id: 3, username: 'viewer1', email: 'viewer@visionai.local', role: 'viewer', status: 'active', lastLogin: '2026-02-20T09:00:00', created: '2026-02-01', permissions: ['view'] },
  { id: 4, username: 'api_bot', email: 'bot@visionai.local', role: 'api_user', status: 'active', lastLogin: '2026-02-22T14:29:00', created: '2026-02-10', permissions: ['api_read', 'api_write'] },
  { id: 5, username: 'johndoe', email: 'john@example.com', role: 'operator', status: 'inactive', lastLogin: '2026-02-15T08:00:00', created: '2026-01-20', permissions: ['view', 'control_devices'] },
  { id: 6, username: 'locked_user', email: 'locked@example.com', role: 'viewer', status: 'locked', lastLogin: '2026-02-10T10:00:00', created: '2026-01-25', permissions: ['view'] },
];

const ROLE_COLORS = { admin: 'bg-red-500/10 text-red-400', operator: 'bg-blue-500/10 text-blue-400', viewer: 'bg-green-500/10 text-green-400', api_user: 'bg-purple-500/10 text-purple-400' };
const STATUS_ICONS = { active: CheckCircle, inactive: XCircle, locked: Shield };
const STATUS_COLORS_ = { active: 'text-green-400', inactive: 'text-dark-400', locked: 'text-red-400' };

const PERMISSIONS = ['view', 'control_devices', 'manage_cameras', 'manage_users', 'manage_models', 'api_read', 'api_write', 'system_config', 'view_logs', 'all'];

export default function UserManagement() {
  const [users, setUsers] = useState(MOCK_USERS);
  const [showForm, setShowForm] = useState(false);
  const [editUser, setEditUser] = useState<UserProfile | null>(null);
  const [form, setForm] = useState({ username: '', email: '', role: 'viewer' as UserProfile['role'], permissions: ['view'] as string[] });

  const openNew = () => { setEditUser(null); setForm({ username: '', email: '', role: 'viewer', permissions: ['view'] }); setShowForm(true); };
  const openEdit = (u: UserProfile) => { setEditUser(u); setForm({ username: u.username, email: u.email, role: u.role, permissions: [...u.permissions] }); setShowForm(true); };
  const save = () => {
    if (editUser) {
      setUsers(users.map(u => u.id === editUser.id ? { ...u, ...form } : u));
    } else {
      setUsers([...users, { id: Date.now(), ...form, status: 'active', lastLogin: 'Never', created: new Date().toISOString().split('T')[0] } as UserProfile]);
    }
    setShowForm(false);
  };
  const deleteUser = (id: number) => setUsers(users.filter(u => u.id !== id));
  const toggleStatus = (id: number) => setUsers(users.map(u => u.id === id ? { ...u, status: u.status === 'active' ? 'inactive' : 'active' } : u));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2"><Users size={24} /> User Management</h1>
          <p className="text-dark-400 text-sm mt-1">{users.length} users configured</p>
        </div>
        <button onClick={openNew} className="btn btn-primary flex items-center gap-1"><Plus size={14} /> Add User</button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Total Users', value: users.length, color: 'text-white' },
          { label: 'Active', value: users.filter(u => u.status === 'active').length, color: 'text-green-400' },
          { label: 'Admins', value: users.filter(u => u.role === 'admin').length, color: 'text-red-400' },
          { label: 'Locked', value: users.filter(u => u.status === 'locked').length, color: 'text-yellow-400' },
        ].map(s => (
          <div key={s.label} className="card p-4 text-center">
            <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
            <div className="text-xs text-dark-400 mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Users Table */}
      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-dark-700 text-dark-400">
              <th className="px-4 py-3 text-left">User</th>
              <th className="px-4 py-3 text-left">Role</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Last Login</th>
              <th className="px-4 py-3 text-left">Permissions</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map(u => {
              const StatusIcon = STATUS_ICONS[u.status];
              return (
                <tr key={u.id} className="border-b border-dark-800 hover:bg-dark-700/20">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-primary-500/20 flex items-center justify-center text-primary-400 font-semibold text-xs">
                        {u.username[0].toUpperCase()}
                      </div>
                      <div>
                        <div className="text-white font-medium">{u.username}</div>
                        <div className="text-xs text-dark-400 flex items-center gap-1"><Mail size={10} /> {u.email}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3"><span className={`px-2 py-0.5 rounded text-xs ${ROLE_COLORS[u.role]}`}>{u.role}</span></td>
                  <td className="px-4 py-3">
                    <button onClick={() => toggleStatus(u.id)} className={`flex items-center gap-1 text-xs ${STATUS_COLORS_[u.status]}`}>
                      <StatusIcon size={12} /> {u.status}
                    </button>
                  </td>
                  <td className="px-4 py-3 text-dark-400 text-xs flex items-center gap-1"><Clock size={10} /> {new Date(u.lastLogin).toLocaleDateString()}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {u.permissions.slice(0, 3).map(p => <span key={p} className="px-1.5 py-0.5 bg-dark-700 rounded text-[10px] text-dark-300">{p}</span>)}
                      {u.permissions.length > 3 && <span className="text-[10px] text-dark-400">+{u.permissions.length - 3}</span>}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center gap-1 justify-end">
                      <button onClick={() => openEdit(u)} className="p-1.5 rounded hover:bg-dark-700 text-dark-400 hover:text-white"><Edit2 size={14} /></button>
                      <button className="p-1.5 rounded hover:bg-dark-700 text-dark-400 hover:text-yellow-400"><Key size={14} /></button>
                      <button onClick={() => deleteUser(u.id)} className="p-1.5 rounded hover:bg-dark-700 text-dark-400 hover:text-red-400"><Trash2 size={14} /></button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Add/Edit Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="card p-6 w-full max-w-md">
            <h2 className="text-lg font-bold text-white mb-4">{editUser ? 'Edit User' : 'Add User'}</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-dark-300 mb-1">Username</label>
                <input className="input-field w-full" value={form.username} onChange={e => setForm({ ...form, username: e.target.value })} />
              </div>
              <div>
                <label className="block text-sm text-dark-300 mb-1">Email</label>
                <input className="input-field w-full" type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} />
              </div>
              <div>
                <label className="block text-sm text-dark-300 mb-1">Role</label>
                <select className="input-field w-full" value={form.role} onChange={e => setForm({ ...form, role: e.target.value as any })}>
                  <option value="admin">Admin</option>
                  <option value="operator">Operator</option>
                  <option value="viewer">Viewer</option>
                  <option value="api_user">API User</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-dark-300 mb-1">Permissions</label>
                <div className="grid grid-cols-2 gap-2">
                  {PERMISSIONS.map(p => (
                    <label key={p} className="flex items-center gap-1 text-xs text-dark-300 cursor-pointer">
                      <input type="checkbox" checked={form.permissions.includes(p)}
                        onChange={e => setForm({ ...form, permissions: e.target.checked ? [...form.permissions, p] : form.permissions.filter(x => x !== p) })} />
                      {p}
                    </label>
                  ))}
                </div>
              </div>
              <div className="flex gap-2 justify-end">
                <button onClick={() => setShowForm(false)} className="btn btn-secondary">Cancel</button>
                <button onClick={save} className="btn btn-primary">{editUser ? 'Update' : 'Create'}</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

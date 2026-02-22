import { ReactNode, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAppStore, useAuthStore } from '../store';
import { wsService } from '../services/websocket';
import {
  LayoutDashboard, Video, Search, Brain, BarChart3, Cpu, Bell, Settings,
  Menu, X, LogOut, Sun, Moon, Wifi, WifiOff, CircuitBoard
} from 'lucide-react';

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/live', label: 'Live Feed', icon: Video },
  { path: '/detection', label: 'Detection', icon: Search },
  { path: '/training', label: 'Training', icon: Brain },
  { path: '/analytics', label: 'Analytics', icon: BarChart3 },
  { path: '/devices', label: 'Devices', icon: Cpu },
  { path: '/esp32', label: 'ESP32 Control', icon: CircuitBoard },
  { path: '/alerts', label: 'Alerts', icon: Bell },
  { path: '/settings', label: 'Settings', icon: Settings },
];

export default function Layout({ children }: { children: ReactNode }) {
  const location = useLocation();
  const { sidebarOpen, toggleSidebar, theme, toggleTheme, notifications } = useAppStore();
  const { user, logout } = useAuthStore();

  useEffect(() => {
    wsService.connect('default');
    return () => wsService.disconnect();
  }, []);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside
        className={`${
          sidebarOpen ? 'w-64' : 'w-16'
        } bg-dark-900 border-r border-dark-700 flex flex-col transition-all duration-300 flex-shrink-0`}
      >
        {/* Logo */}
        <div className="h-16 flex items-center px-4 border-b border-dark-700">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center text-white font-bold text-sm">
              VA
            </div>
            {sidebarOpen && (
              <div>
                <h1 className="text-sm font-bold text-white">Vision-AI</h1>
                <p className="text-[10px] text-dark-400">IoT Intelligence</p>
              </div>
            )}
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto">
          {navItems.map(({ path, label, icon: Icon }) => {
            const active = location.pathname === path;
            return (
              <Link
                key={path}
                to={path}
                className={active ? 'sidebar-link-active' : 'sidebar-link'}
                title={label}
              >
                <Icon size={20} />
                {sidebarOpen && <span className="text-sm">{label}</span>}
              </Link>
            );
          })}
        </nav>

        {/* Status */}
        <div className="p-3 border-t border-dark-700">
          <div className="flex items-center gap-2 text-xs text-dark-400">
            {wsService.isConnected ? (
              <><Wifi size={14} className="text-green-400" /> {sidebarOpen && 'Connected'}</>
            ) : (
              <><WifiOff size={14} className="text-red-400" /> {sidebarOpen && 'Offline'}</>
            )}
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-16 bg-dark-900/80 backdrop-blur-sm border-b border-dark-700 flex items-center justify-between px-4 flex-shrink-0">
          <div className="flex items-center gap-4">
            <button onClick={toggleSidebar} className="p-2 hover:bg-dark-700 rounded-lg transition-colors">
              {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
            <h2 className="text-lg font-semibold text-white">
              {navItems.find((n) => n.path === location.pathname)?.label || 'Vision-AI'}
            </h2>
          </div>

          <div className="flex items-center gap-3">
            {/* Notifications */}
            <button className="relative p-2 hover:bg-dark-700 rounded-lg transition-colors">
              <Bell size={20} />
              {notifications.length > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full text-[10px] flex items-center justify-center">
                  {notifications.length}
                </span>
              )}
            </button>

            {/* Theme */}
            <button onClick={toggleTheme} className="p-2 hover:bg-dark-700 rounded-lg transition-colors">
              {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
            </button>

            {/* User */}
            <div className="flex items-center gap-2 pl-3 border-l border-dark-700">
              <div className="w-8 h-8 rounded-full bg-primary-600 flex items-center justify-center text-white text-sm font-medium">
                {user?.username?.[0]?.toUpperCase() || 'U'}
              </div>
              <span className="text-sm text-dark-300 hidden md:block">{user?.username || 'User'}</span>
              <button onClick={logout} className="p-2 hover:bg-dark-700 rounded-lg transition-colors text-dark-400 hover:text-red-400" title="Logout">
                <LogOut size={18} />
              </button>
            </div>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto p-6 bg-dark-950">
          <div className="animate-fade-in">{children}</div>
        </main>
      </div>
    </div>
  );
}

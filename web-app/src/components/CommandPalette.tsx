import { useState, useEffect, useRef, useCallback } from 'react';
import { Search, Command, ArrowRight, Clock, Zap, Settings, Camera, Shield, Activity, X } from 'lucide-react';

// Feature 59: Quick Command Palette - keyboard shortcut command palette (Ctrl+K)
// Feature 70: Keyboard Shortcuts system

interface CommandItem {
  id: string;
  label: string;
  category: string;
  icon: any;
  shortcut?: string;
  action: () => void;
}

const COMMANDS: Omit<CommandItem, 'action'>[] = [
  { id: 'nav-dashboard', label: 'Go to Dashboard', category: 'Navigation', icon: Activity, shortcut: 'G D' },
  { id: 'nav-detection', label: 'Go to Detection', category: 'Navigation', icon: Camera, shortcut: 'G T' },
  { id: 'nav-cameras', label: 'Go to Cameras', category: 'Navigation', icon: Camera, shortcut: 'G C' },
  { id: 'nav-automation', label: 'Go to Automation', category: 'Navigation', icon: Zap, shortcut: 'G A' },
  { id: 'nav-settings', label: 'Go to Settings', category: 'Navigation', icon: Settings, shortcut: 'G S' },
  { id: 'nav-logs', label: 'Go to System Logs', category: 'Navigation', icon: Activity, shortcut: 'G L' },
  { id: 'nav-security', label: 'Go to Security', category: 'Navigation', icon: Shield },
  { id: 'act-capture', label: 'Capture Screenshot', category: 'Actions', icon: Camera, shortcut: 'Alt+C' },
  { id: 'act-detect', label: 'Run Detection Now', category: 'Actions', icon: Zap, shortcut: 'Alt+D' },
  { id: 'act-refresh', label: 'Refresh All Data', category: 'Actions', icon: Activity, shortcut: 'Alt+R' },
  { id: 'act-toggle-theme', label: 'Toggle Dark/Light Theme', category: 'Actions', icon: Settings, shortcut: 'Alt+T' },
  { id: 'act-toggle-sidebar', label: 'Toggle Sidebar', category: 'Actions', icon: Settings, shortcut: 'Alt+B' },
  { id: 'act-fullscreen', label: 'Toggle Fullscreen', category: 'Actions', icon: Camera, shortcut: 'F11' },
  { id: 'act-export', label: 'Export Data', category: 'Actions', icon: Activity },
  { id: 'act-clear-notif', label: 'Clear Notifications', category: 'Actions', icon: Activity },
  { id: 'dev-relay-on', label: 'Turn On All Relays', category: 'Devices', icon: Zap },
  { id: 'dev-relay-off', label: 'Turn Off All Relays', category: 'Devices', icon: Zap },
  { id: 'dev-lock', label: 'Lock All Doors', category: 'Devices', icon: Shield },
  { id: 'dev-unlock', label: 'Unlock All Doors', category: 'Devices', icon: Shield },
  { id: 'dev-arm', label: 'Arm Security System', category: 'Devices', icon: Shield, shortcut: 'Alt+A' },
  { id: 'dev-disarm', label: 'Disarm Security System', category: 'Devices', icon: Shield },
];

export default function CommandPalette({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const [search, setSearch] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [recentCommands, setRecentCommands] = useState<string[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const commands: CommandItem[] = COMMANDS.map(c => ({
    ...c,
    action: () => {
      setRecentCommands(prev => [c.id, ...prev.filter(x => x !== c.id)].slice(0, 5));
      if (c.id.startsWith('nav-')) {
        const path = c.id.replace('nav-', '/');
        window.location.hash = path;
      }
      onClose();
    },
  }));

  const filtered = search
    ? commands.filter(c => c.label.toLowerCase().includes(search.toLowerCase()) || c.category.toLowerCase().includes(search.toLowerCase()))
    : recentCommands.length > 0
    ? [
        ...recentCommands.map(id => commands.find(c => c.id === id)!).filter(Boolean),
        ...commands.filter(c => !recentCommands.includes(c.id)),
      ]
    : commands;

  const categories = Array.from(new Set(filtered.map(c => c.category)));

  useEffect(() => {
    if (isOpen) { setSearch(''); setSelectedIndex(0); setTimeout(() => inputRef.current?.focus(), 50); }
  }, [isOpen]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setSelectedIndex(i => Math.min(i + 1, filtered.length - 1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setSelectedIndex(i => Math.max(i - 1, 0)); }
    else if (e.key === 'Enter' && filtered[selectedIndex]) { filtered[selectedIndex].action(); }
    else if (e.key === 'Escape') { onClose(); }
  }, [filtered, selectedIndex, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]" onClick={onClose}>
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div className="relative bg-dark-800 border border-dark-600 rounded-xl w-full max-w-lg shadow-2xl overflow-hidden"
        onClick={e => e.stopPropagation()}>
        {/* Search */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-dark-700">
          <Command size={16} className="text-dark-400" />
          <input ref={inputRef} type="text" placeholder="Type a command..." className="flex-1 bg-transparent text-white outline-none text-sm"
            value={search} onChange={e => { setSearch(e.target.value); setSelectedIndex(0); }} onKeyDown={handleKeyDown} />
          <kbd className="text-[10px] bg-dark-700 text-dark-400 px-1.5 py-0.5 rounded">ESC</kbd>
        </div>

        {/* Results */}
        <div className="max-h-[50vh] overflow-y-auto p-2">
          {categories.map(cat => (
            <div key={cat}>
              <div className="text-[10px] uppercase text-dark-500 px-3 py-1.5 font-semibold tracking-wider">{cat}</div>
              {filtered.filter(c => c.category === cat).map((cmd, i) => {
                const globalIndex = filtered.indexOf(cmd);
                const Icon = cmd.icon;
                return (
                  <button key={cmd.id}
                    className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all ${globalIndex === selectedIndex ? 'bg-primary-500/20 text-white' : 'text-dark-300 hover:bg-dark-700'}`}
                    onClick={cmd.action} onMouseEnter={() => setSelectedIndex(globalIndex)}>
                    <Icon size={14} className="text-dark-400" />
                    <span className="flex-1 text-left">{cmd.label}</span>
                    {recentCommands.includes(cmd.id) && <Clock size={10} className="text-dark-500" />}
                    {cmd.shortcut && <kbd className="text-[10px] bg-dark-700 text-dark-500 px-1.5 py-0.5 rounded">{cmd.shortcut}</kbd>}
                    <ArrowRight size={12} className="text-dark-600" />
                  </button>
                );
              })}
            </div>
          ))}
          {filtered.length === 0 && (
            <div className="text-center py-8 text-dark-400 text-sm">No commands found for "{search}"</div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-dark-700 px-4 py-2 flex items-center justify-between text-[10px] text-dark-500">
          <div className="flex items-center gap-3">
            <span>↑↓ Navigate</span>
            <span>↵ Select</span>
            <span>ESC Close</span>
          </div>
          <span>{filtered.length} commands</span>
        </div>
      </div>
    </div>
  );
}

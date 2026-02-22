import { create } from 'zustand';

// ---- Auth Store ----
interface AuthState {
  user: any | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (user: any, token: string) => void;
  logout: () => void;
  updateUser: (user: any) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem('vision-ai-token'),
  isAuthenticated: !!localStorage.getItem('vision-ai-token'),
  login: (user, token) => {
    localStorage.setItem('vision-ai-token', token);
    set({ user, token, isAuthenticated: true });
  },
  logout: () => {
    localStorage.removeItem('vision-ai-token');
    set({ user: null, token: null, isAuthenticated: false });
  },
  updateUser: (user) => set({ user }),
}));

// ---- App Store ----
interface AppState {
  sidebarOpen: boolean;
  theme: 'dark' | 'light';
  notifications: any[];
  toggleSidebar: () => void;
  toggleTheme: () => void;
  addNotification: (n: any) => void;
  clearNotifications: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  sidebarOpen: true,
  theme: (localStorage.getItem('vision-ai-theme') as 'dark' | 'light') || 'dark',
  notifications: [],
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  toggleTheme: () =>
    set((s) => {
      const next = s.theme === 'dark' ? 'light' : 'dark';
      localStorage.setItem('vision-ai-theme', next);
      document.documentElement.classList.toggle('dark', next === 'dark');
      return { theme: next };
    }),
  addNotification: (n) => set((s) => ({ notifications: [n, ...s.notifications].slice(0, 100) })),
  clearNotifications: () => set({ notifications: [] }),
}));

// ---- Device Store ----
interface DeviceState {
  devices: any[];
  selectedDevice: string | null;
  setDevices: (devices: any[]) => void;
  selectDevice: (id: string | null) => void;
  updateDevice: (id: string, data: any) => void;
}

export const useDeviceStore = create<DeviceState>((set) => ({
  devices: [],
  selectedDevice: null,
  setDevices: (devices) => set({ devices }),
  selectDevice: (id) => set({ selectedDevice: id }),
  updateDevice: (id, data) =>
    set((s) => ({
      devices: s.devices.map((d) => (d.device_id === id ? { ...d, ...data } : d)),
    })),
}));

// ---- Detection Store ----
interface DetectionState {
  recentDetections: any[];
  liveDetections: any[];
  isDetecting: boolean;
  addDetection: (d: any) => void;
  setLiveDetections: (d: any[]) => void;
  setDetecting: (v: boolean) => void;
}

export const useDetectionStore = create<DetectionState>((set) => ({
  recentDetections: [],
  liveDetections: [],
  isDetecting: false,
  addDetection: (d) =>
    set((s) => ({ recentDetections: [d, ...s.recentDetections].slice(0, 200) })),
  setLiveDetections: (d) => set({ liveDetections: d }),
  setDetecting: (v) => set({ isDetecting: v }),
}));

// ---- Training Store ----
interface TrainingState {
  isTraining: boolean;
  progress: number;
  currentEpoch: number;
  totalEpochs: number;
  metrics: any;
  history: any[];
  setTraining: (v: boolean) => void;
  setProgress: (p: number) => void;
  setMetrics: (m: any) => void;
  setHistory: (h: any[]) => void;
  updateTrainingState: (data: any) => void;
}

export const useTrainingStore = create<TrainingState>((set) => ({
  isTraining: false,
  progress: 0,
  currentEpoch: 0,
  totalEpochs: 0,
  metrics: {},
  history: [],
  setTraining: (v) => set({ isTraining: v }),
  setProgress: (p) => set({ progress: p }),
  setMetrics: (m) => set({ metrics: m }),
  setHistory: (h) => set({ history: h }),
  updateTrainingState: (data) =>
    set({
      isTraining: data.is_training,
      progress: data.progress || 0,
      currentEpoch: data.current_epoch || 0,
      totalEpochs: data.total_epochs || 0,
      metrics: data.metrics || {},
    }),
}));

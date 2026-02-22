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

// ---- Vision AI Store (Features 1-25) ----
interface VisionState {
  anomalies: any[];
  emotionHistory: any[];
  gestureResults: any[];
  sceneResults: any[];
  qualityScores: any[];
  safetyAlerts: any[];
  addAnomaly: (a: any) => void;
  addEmotion: (e: any) => void;
  addGesture: (g: any) => void;
  addSceneResult: (s: any) => void;
  addQualityScore: (q: any) => void;
  addSafetyAlert: (s: any) => void;
  clearAnomalies: () => void;
}

export const useVisionStore = create<VisionState>((set) => ({
  anomalies: [],
  emotionHistory: [],
  gestureResults: [],
  sceneResults: [],
  qualityScores: [],
  safetyAlerts: [],
  addAnomaly: (a) => set((s) => ({ anomalies: [a, ...s.anomalies].slice(0, 100) })),
  addEmotion: (e) => set((s) => ({ emotionHistory: [e, ...s.emotionHistory].slice(0, 50) })),
  addGesture: (g) => set((s) => ({ gestureResults: [g, ...s.gestureResults].slice(0, 50) })),
  addSceneResult: (s_) => set((s) => ({ sceneResults: [s_, ...s.sceneResults].slice(0, 50) })),
  addQualityScore: (q) => set((s) => ({ qualityScores: [q, ...s.qualityScores].slice(0, 50) })),
  addSafetyAlert: (a) => set((s) => ({ safetyAlerts: [a, ...s.safetyAlerts].slice(0, 100) })),
  clearAnomalies: () => set({ anomalies: [] }),
}));

// ---- Smart Home Store (Features 26-50) ----
interface SmartHomeState {
  weather: any | null;
  energy: any | null;
  scenes: any[];
  guests: any[];
  habits: any[];
  emergencyActive: boolean;
  geofences: any[];
  tasks: any[];
  setWeather: (w: any) => void;
  setEnergy: (e: any) => void;
  setScenes: (s: any[]) => void;
  addGuest: (g: any) => void;
  setGuests: (g: any[]) => void;
  setHabits: (h: any[]) => void;
  setEmergencyActive: (v: boolean) => void;
  setGeofences: (g: any[]) => void;
  setTasks: (t: any[]) => void;
}

export const useSmartHomeStore = create<SmartHomeState>((set) => ({
  weather: null,
  energy: null,
  scenes: [],
  guests: [],
  habits: [],
  emergencyActive: false,
  geofences: [],
  tasks: [],
  setWeather: (w) => set({ weather: w }),
  setEnergy: (e) => set({ energy: e }),
  setScenes: (s) => set({ scenes: s }),
  addGuest: (g) => set((s) => ({ guests: [...s.guests, g] })),
  setGuests: (g) => set({ guests: g }),
  setHabits: (h) => set({ habits: h }),
  setEmergencyActive: (v) => set({ emergencyActive: v }),
  setGeofences: (g) => set({ geofences: g }),
  setTasks: (t) => set({ tasks: t }),
}));

// ---- Automation Store (Features 51-75) ----
interface AutomationState {
  rules: any[];
  events: any[];
  logs: any[];
  backups: any[];
  privacySettings: any;
  addRule: (r: any) => void;
  setRules: (r: any[]) => void;
  setEvents: (e: any[]) => void;
  addLog: (l: any) => void;
  setLogs: (l: any[]) => void;
  setBackups: (b: any[]) => void;
  setPrivacySettings: (p: any) => void;
}

export const useAutomationStore = create<AutomationState>((set) => ({
  rules: [],
  events: [],
  logs: [],
  backups: [],
  privacySettings: { faceBlur: true, plateBlur: true, encryption: false, retention: 30 },
  addRule: (r) => set((s) => ({ rules: [...s.rules, r] })),
  setRules: (r) => set({ rules: r }),
  setEvents: (e) => set({ events: e }),
  addLog: (l) => set((s) => ({ logs: [l, ...s.logs].slice(0, 500) })),
  setLogs: (l) => set({ logs: l }),
  setBackups: (b) => set({ backups: b }),
  setPrivacySettings: (p) => set({ privacySettings: p }),
}));

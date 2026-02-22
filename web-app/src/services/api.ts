import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// Auth interceptor
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('vision-ai-token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !window.location.pathname.includes('/login')) {
      localStorage.removeItem('vision-ai-token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// ---- Auth API ----
export const authApi = {
  login: (username: string, password: string) => api.post('/auth/login', { username, password }),
  register: (data: any) => api.post('/auth/register', data),
  logout: () => api.post('/auth/logout'),
  getMe: () => api.get('/auth/me'),
  updateProfile: (data: any) => api.put('/auth/me', data),
  changePassword: (data: any) => api.put('/auth/me/password', data),
};

// ---- Detection API ----
export const detectionApi = {
  detect: (formData: FormData) => api.post('/detect', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  detectBatch: (formData: FormData) => api.post('/detect/batch', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  count: (formData: FormData) => api.post('/detect/count', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  track: (formData: FormData) => api.post('/detect/track', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  getModels: () => api.get('/detect/models'),
  getStats: () => api.get('/detect/stats'),
  getHistory: (limit = 50) => api.get(`/detect/history?limit=${limit}`),
  loadModel: (path: string) => api.post('/detect/models/load', { model_path: path }),
  getHeatmap: (formData: FormData) => api.post('/detect/heatmap', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  getGradcam: (formData: FormData) => api.post('/detect/gradcam', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
};

// ---- Training API ----
export const trainingApi = {
  start: (config: any) => api.post('/training/start', config),
  transferLearn: (config: any) => api.post('/training/transfer-learn', config),
  selfTrain: (config: any) => api.post('/training/self-train', config),
  activeLearn: (config: any) => api.post('/training/active-learn', config),
  compress: (config: any) => api.post('/training/compress', config),
  tune: (config: any) => api.post('/training/tune', config),
  augment: (config: any) => api.post('/training/augment', config),
  getStatus: () => api.get('/training/status'),
  getHistory: () => api.get('/training/history'),
  // Datasets
  createDataset: (data: any) => api.post('/training/datasets', data),
  getDatasets: () => api.get('/training/datasets'),
  uploadImages: (datasetId: number, formData: FormData) => api.post(`/training/datasets/${datasetId}/upload`, formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  // Models
  getModels: () => api.get('/training/models'),
  registerModel: (data: any) => api.post('/training/models', data),
};

// ---- Analytics API ----
export const analyticsApi = {
  getDashboard: () => api.get('/analytics/dashboard'),
  getTimeline: (hours = 24, interval = 60) => api.get(`/analytics/timeline?hours=${hours}&interval=${interval}`),
  getPeakHours: (days = 7) => api.get(`/analytics/peak-hours?days=${days}`),
  getTrends: (period = 'daily', days = 30) => api.get(`/analytics/trends?period=${period}&days=${days}`),
  comparePeriods: (params: any) => api.get('/analytics/compare', { params }),
  getZoneAnalytics: (zoneId: number, hours = 24) => api.get(`/analytics/zones/${zoneId}?hours=${hours}`),
  getConfusionMatrix: (data: any) => api.post('/analytics/confusion-matrix', data),
  getPrecisionRecall: (data: any) => api.post('/analytics/precision-recall', data),
  getDatasetStats: (datasetId: number) => api.get(`/analytics/datasets/${datasetId}/stats`),
  getReport: (type = 'daily') => api.get(`/analytics/report?report_type=${type}`),
};

// ---- Device API ----
export const deviceApi = {
  list: (params?: any) => api.get('/devices', { params }),
  get: (deviceId: string) => api.get(`/devices/${deviceId}`),
  register: (data: any) => api.post('/devices', data),
  update: (deviceId: string, data: any) => api.put(`/devices/${deviceId}`, data),
  delete: (deviceId: string) => api.delete(`/devices/${deviceId}`),
  heartbeat: (deviceId: string, data?: any) => api.post(`/devices/${deviceId}/heartbeat`, data || {}),
  sendCommand: (deviceId: string, cmd: any) => api.post(`/devices/${deviceId}/command`, cmd),
  getSensors: (deviceId: string, hours = 24) => api.get(`/devices/${deviceId}/sensors?hours=${hours}`),
  pushSensors: (deviceId: string, data: any) => api.post(`/devices/${deviceId}/sensors`, data),
  getStatus: (deviceId: string) => api.get(`/devices/${deviceId}/status`),
};

// ---- Events API ----
export const eventsApi = {
  list: (params?: any) => api.get('/events', { params }),
  create: (data: any) => api.post('/events', data),
  acknowledge: (eventId: number) => api.put(`/events/${eventId}/acknowledge`),
};

// ---- Alerts API ----
export const alertsApi = {
  getRules: () => api.get('/alerts/rules'),
  createRule: (rule: any) => api.post('/alerts/rules', rule),
  getHistory: (limit = 50) => api.get(`/alerts/history?limit=${limit}`),
  getStats: () => api.get('/alerts/stats'),
};

// ---- Zones API ----
export const zonesApi = {
  list: () => api.get('/zones'),
  create: (data: any) => api.post('/zones', data),
};

// ---- System API ----
export const systemApi = {
  health: () => api.get('/system/health'),
  getConfig: () => api.get('/system/config'),
  setConfig: (key: string, data: any) => api.put(`/system/config/${key}`, data),
  info: () => api.get('/info'),
  wsStatus: () => api.get('/ws/status'),
};

// ---- Admin API ----
export const adminApi = {
  getUsers: () => api.get('/admin/users'),
  updateUser: (userId: number, data: any) => api.put(`/admin/users/${userId}`, data),
  deleteUser: (userId: number) => api.delete(`/admin/users/${userId}`),
  getActivity: (limit = 100) => api.get(`/admin/activity?limit=${limit}`),
};

export default api;

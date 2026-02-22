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

// ---- Vision AI API (Features 1-25) ----
export const visionApi = {
  // Anomaly Detection (Features 1-5)
  detectAnomaly: (data: any) => api.post('/vision/anomaly/detect', data),
  getAnomalyStatus: () => api.get('/vision/anomaly/status'),
  getAnomalyHistory: () => api.get('/vision/anomaly/history'),
  resetAnomalyBaseline: () => api.post('/vision/anomaly/reset'),

  // Gesture Recognition (Feature 6)
  detectGesture: (formData: FormData) => api.post('/vision/gesture/detect', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),

  // Emotion Detection (Feature 7)
  detectEmotion: (formData: FormData) => api.post('/vision/emotion/detect', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  getEmotionHistory: () => api.get('/vision/emotion/history'),

  // Scene Classification (Feature 8)
  classifyScene: (formData: FormData) => api.post('/vision/scene/classify', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),

  // OCR (Feature 9)
  extractText: (formData: FormData) => api.post('/vision/ocr/extract', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),

  // Color Analysis (Feature 10)
  analyzeColors: (formData: FormData) => api.post('/vision/color/analyze', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),

  // Image Quality (Feature 11)
  assessQuality: (formData: FormData) => api.post('/vision/quality/assess', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),

  // Crowd Counting (Feature 12)
  estimateCrowd: (formData: FormData) => api.post('/vision/crowd/estimate', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),

  // Safety Detection (Features 13-14)
  detectSafety: (formData: FormData) => api.post('/vision/safety/fire-smoke', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  detectPPE: (formData: FormData) => api.post('/vision/safety/ppe', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),

  // Motion Analysis (Feature 15)
  analyzeMotion: (formData: FormData) => api.post('/vision/motion/analyze', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),

  // Privacy Mask (Feature 16)
  applyPrivacyMask: (formData: FormData) => api.post('/vision/privacy/mask', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),

  // Image Enhancement (Features 17-18)
  enhanceImage: (formData: FormData) => api.post('/vision/enhance/auto', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  applyStyle: (formData: FormData) => api.post('/vision/enhance/style', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),

  // Model Ensemble (Feature 19)
  ensemblePredict: (data: any) => api.post('/vision/ensemble/predict', data),

  // Notifications (Feature 20)
  getNotificationTemplates: () => api.get('/vision/notifications/templates'),
  renderNotification: (data: any) => api.post('/vision/notifications/render', data),

  // License Plate (Feature 21)
  detectLicensePlate: (formData: FormData) => api.post('/vision/lpr/detect', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),

  // Person Re-ID (Feature 22)
  extractPersonFeatures: (formData: FormData) => api.post('/vision/person-reid/extract', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  matchPerson: (formData: FormData) => api.post('/vision/person-reid/match', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),

  // Activity Recognition (Feature 23)
  classifyActivity: (formData: FormData) => api.post('/vision/activity/classify', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),

  // Package Detection (Feature 24)
  detectPackage: (formData: FormData) => api.post('/vision/package/detect', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),

  // Abandoned Object (Feature 25)
  detectAbandoned: (formData: FormData) => api.post('/vision/abandoned/detect', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),

  // Vehicle Classification
  classifyVehicle: (formData: FormData) => api.post('/vision/vehicle/classify', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
};

// ---- Smart Home / Jarvis API (Features 26-50) ----
const jarvisBase = import.meta.env.VITE_JARVIS_URL || 'http://localhost:8100';
const jarvisApi = axios.create({ baseURL: jarvisBase, timeout: 30000, headers: { 'Content-Type': 'application/json' } });

export const smartApi = {
  // Weather (Features 26-27)
  getWeather: () => jarvisApi.get('/api/smart/weather'),
  updateWeather: (data: any) => jarvisApi.post('/api/smart/weather/update', data),
  addWeatherRule: (rule: any) => jarvisApi.post('/api/smart/weather/rules', rule),

  // Energy (Features 28-29)
  getEnergy: () => jarvisApi.get('/api/smart/energy'),
  updatePower: (data: any) => jarvisApi.post('/api/smart/energy/update', data),
  getEnergyTips: () => jarvisApi.get('/api/smart/energy/tips'),

  // Scene Memory (Feature 30)
  saveScene: (data: any) => jarvisApi.post('/api/smart/scenes/save', data),
  getScenes: () => jarvisApi.get('/api/smart/scenes'),
  recallScene: (room: string) => jarvisApi.get(`/api/smart/scenes/${room}`),

  // Predictive Automation (Feature 31)
  getPredictions: () => jarvisApi.get('/api/smart/predictions'),
  recordAction: (data: any) => jarvisApi.post('/api/smart/predictions/record', data),

  // Calendar (Feature 32)
  getCalendarEvents: () => jarvisApi.get('/api/smart/calendar'),
  addCalendarEvent: (data: any) => jarvisApi.post('/api/smart/calendar', data),

  // Guest Management (Feature 33)
  getGuests: () => jarvisApi.get('/api/smart/guests'),
  registerGuest: (data: any) => jarvisApi.post('/api/smart/guests', data),
  revokeGuest: (guestId: string) => jarvisApi.post(`/api/smart/guests/${guestId}/revoke`),

  // Sleep Monitor (Feature 34)
  getSleep: () => jarvisApi.get('/api/smart/sleep'),
  updateSleep: (data: any) => jarvisApi.post('/api/smart/sleep/update', data),

  // NLU (Feature 36)
  processNLU: (text: string) => jarvisApi.post('/api/smart/nlu/process', { text }),

  // Conversation (Feature 37)
  chat: (data: any) => jarvisApi.post('/api/smart/conversation/message', data),
  getConversation: (sessionId: string) => jarvisApi.get(`/api/smart/conversation/${sessionId}`),

  // Habits (Feature 38)
  getHabits: () => jarvisApi.get('/api/smart/habits'),
  trackHabit: (data: any) => jarvisApi.post('/api/smart/habits/track', data),

  // Emergency (Feature 39)
  triggerEmergency: (type: string) => jarvisApi.post('/api/smart/emergency/trigger', { type }),
  getEmergencyStatus: () => jarvisApi.get('/api/smart/emergency/status'),

  // Geofence (Feature 40)
  getGeofences: () => jarvisApi.get('/api/smart/geofences'),
  addGeofence: (data: any) => jarvisApi.post('/api/smart/geofences', data),
  checkLocation: (data: any) => jarvisApi.post('/api/smart/geofences/check', data),

  // Device Health (Feature 41)
  getDeviceHealth: () => jarvisApi.get('/api/smart/device-health'),
  updateDeviceHealth: (data: any) => jarvisApi.post('/api/smart/device-health/update', data),

  // Timelapse (Feature 42)
  getTimelapses: () => jarvisApi.get('/api/smart/timelapse'),
  captureTimelapse: (data: any) => jarvisApi.post('/api/smart/timelapse/capture', data),

  // Notification Priority (Feature 43)
  getNotificationSettings: () => jarvisApi.get('/api/smart/notification-priority'),
  updateNotificationPriority: (data: any) => jarvisApi.put('/api/smart/notification-priority', data),

  // Backup/Restore (Feature 44)
  createBackup: () => jarvisApi.post('/api/smart/backup/create'),
  getBackups: () => jarvisApi.get('/api/smart/backup'),
  restoreBackup: (backupId: string) => jarvisApi.post(`/api/smart/backup/${backupId}/restore`),

  // Task Scheduler (Feature 47)
  getTasks: () => jarvisApi.get('/api/smart/tasks'),
  addTask: (data: any) => jarvisApi.post('/api/smart/tasks', data),

  // Smart Lighting (Feature 48)
  getLighting: () => jarvisApi.get('/api/smart/lighting'),
  updateLighting: (data: any) => jarvisApi.post('/api/smart/lighting/update', data),
};

export default api;

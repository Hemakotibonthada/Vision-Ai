import { useState, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './store';
import Layout from './components/Layout';
import CommandPalette from './components/CommandPalette';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import LiveFeed from './pages/LiveFeed';
import Detection from './pages/Detection';
import Training from './pages/Training';
import Analytics from './pages/Analytics';
import Devices from './pages/Devices';
import Alerts from './pages/Alerts';
import Settings from './pages/Settings';
import ESP32Control from './pages/ESP32Control';
// Feature 51-75: New pages
import Automation from './pages/Automation';
import CameraGrid from './pages/CameraGrid';
import EventTimeline from './pages/EventTimeline';
import SystemLogs from './pages/SystemLogs';
import HeatmapView from './pages/HeatmapView';
import ModelComparison from './pages/ModelComparison';
import UserManagement from './pages/UserManagement';
import NotificationCenter from './pages/NotificationCenter';
import StatsWidgets from './pages/StatsWidgets';
import GestureControl from './pages/GestureControl';
import PrivacySettings from './pages/PrivacySettings';
import BackupManagement from './pages/BackupManagement';
import ActivityFeed from './pages/ActivityFeed';
import ImageAnnotation from './pages/ImageAnnotation';
import BatchOperations from './pages/BatchOperations';
import SystemHealth from './pages/SystemHealth';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
}

export default function App() {
  const [cmdPaletteOpen, setCmdPaletteOpen] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setCmdPaletteOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <>
      <CommandPalette isOpen={cmdPaletteOpen} onClose={() => setCmdPaletteOpen(false)} />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <Layout>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/live" element={<LiveFeed />} />
                  <Route path="/detection" element={<Detection />} />
                  <Route path="/training" element={<Training />} />
                  <Route path="/analytics" element={<Analytics />} />
                  <Route path="/devices" element={<Devices />} />
                  <Route path="/alerts" element={<Alerts />} />
                  <Route path="/settings" element={<Settings />} />
                  <Route path="/esp32" element={<ESP32Control />} />
                  {/* Feature 51-75: New routes */}
                  <Route path="/automation" element={<Automation />} />
                  <Route path="/cameras" element={<CameraGrid />} />
                  <Route path="/timeline" element={<EventTimeline />} />
                  <Route path="/logs" element={<SystemLogs />} />
                  <Route path="/heatmap" element={<HeatmapView />} />
                  <Route path="/models" element={<ModelComparison />} />
                  <Route path="/users" element={<UserManagement />} />
                  <Route path="/notifications" element={<NotificationCenter />} />
                  <Route path="/stats" element={<StatsWidgets />} />
                  <Route path="/gestures" element={<GestureControl />} />
                  <Route path="/privacy" element={<PrivacySettings />} />
                  <Route path="/backups" element={<BackupManagement />} />
                  <Route path="/activity" element={<ActivityFeed />} />
                  <Route path="/annotate" element={<ImageAnnotation />} />
                  <Route path="/batch" element={<BatchOperations />} />
                  <Route path="/health" element={<SystemHealth />} />
                </Routes>
              </Layout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </>
  );
}

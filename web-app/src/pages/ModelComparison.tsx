import { useState } from 'react';
import { BarChart3, TrendingUp, Clock, Cpu, Zap, CheckCircle, XCircle, RefreshCw } from 'lucide-react';

// Feature 56: AI Model Comparison - side-by-side model metrics

interface ModelMetrics {
  id: string;
  name: string;
  version: string;
  type: string;
  accuracy: number;
  precision: number;
  recall: number;
  f1Score: number;
  inferenceTime: number; // ms
  modelSize: number; // MB
  fps: number;
  totalDetections: number;
  falsePositives: number;
  falseNegatives: number;
  status: 'active' | 'inactive' | 'training';
}

const MOCK_MODELS: ModelMetrics[] = [
  { id: 'm1', name: 'YOLOv8n', version: '8.0.1', type: 'Object Detection', accuracy: 0.924, precision: 0.931, recall: 0.917, f1Score: 0.924, inferenceTime: 12, modelSize: 6.2, fps: 83, totalDetections: 15420, falsePositives: 234, falseNegatives: 187, status: 'active' },
  { id: 'm2', name: 'YOLOv8s', version: '8.0.1', type: 'Object Detection', accuracy: 0.951, precision: 0.958, recall: 0.944, f1Score: 0.951, inferenceTime: 28, modelSize: 22.5, fps: 36, totalDetections: 15620, falsePositives: 156, falseNegatives: 132, status: 'active' },
  { id: 'm3', name: 'EfficientDet-D0', version: '1.2', type: 'Object Detection', accuracy: 0.893, precision: 0.901, recall: 0.885, f1Score: 0.893, inferenceTime: 35, modelSize: 15.6, fps: 29, totalDetections: 14890, falsePositives: 312, falseNegatives: 245, status: 'inactive' },
  { id: 'm4', name: 'FaceNet', version: '3.1', type: 'Face Recognition', accuracy: 0.978, precision: 0.982, recall: 0.974, f1Score: 0.978, inferenceTime: 8, modelSize: 92.0, fps: 125, totalDetections: 8930, falsePositives: 45, falseNegatives: 67, status: 'active' },
  { id: 'm5', name: 'MobileNet-SSD', version: '2.0', type: 'Object Detection', accuracy: 0.867, precision: 0.872, recall: 0.862, f1Score: 0.867, inferenceTime: 8, modelSize: 4.3, fps: 125, totalDetections: 14200, falsePositives: 456, falseNegatives: 389, status: 'inactive' },
  { id: 'm6', name: 'DeepSORT', version: '1.0', type: 'Object Tracking', accuracy: 0.912, precision: 0.920, recall: 0.904, f1Score: 0.912, inferenceTime: 18, modelSize: 45.0, fps: 56, totalDetections: 12500, falsePositives: 180, falseNegatives: 210, status: 'active' },
];

function MetricBar({ label, value, max = 1, format = 'percent', color = 'bg-primary-500' }: { label: string; value: number; max?: number; format?: 'percent' | 'ms' | 'mb' | 'fps' | 'number'; color?: string }) {
  const pct = (value / max) * 100;
  const display = format === 'percent' ? `${(value * 100).toFixed(1)}%` : format === 'ms' ? `${value}ms` : format === 'mb' ? `${value}MB` : format === 'fps' ? `${value} fps` : value.toLocaleString();
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs"><span className="text-dark-400">{label}</span><span className="text-white">{display}</span></div>
      <div className="w-full bg-dark-700 rounded-full h-1.5">
        <div className={`${color} h-1.5 rounded-full transition-all`} style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
    </div>
  );
}

export default function ModelComparison() {
  const [models] = useState(MOCK_MODELS);
  const [compareIds, setCompareIds] = useState<string[]>(['m1', 'm2']);
  const [sortBy, setSortBy] = useState<keyof ModelMetrics>('accuracy');
  const [filterType, setFilterType] = useState('all');

  const toggle = (id: string) => {
    setCompareIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : prev.length < 4 ? [...prev, id] : prev);
  };

  const types = Array.from(new Set(models.map(m => m.type)));
  const filtered = models.filter(m => filterType === 'all' || m.type === filterType);
  const compared = models.filter(m => compareIds.includes(m.id));

  const STATUS_COLORS = { active: 'text-green-400', inactive: 'text-dark-400', training: 'text-yellow-400' };
  const STATUS_ICONS = { active: CheckCircle, inactive: XCircle, training: RefreshCw };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2"><BarChart3 size={24} /> Model Comparison</h1>
          <p className="text-dark-400 text-sm mt-1">Compare AI model performance metrics</p>
        </div>
        <select className="input-field" value={filterType} onChange={e => setFilterType(e.target.value)}>
          <option value="all">All Types</option>
          {types.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>

      {/* Model Selection */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {filtered.map(m => {
          const StatusIcon = STATUS_ICONS[m.status];
          return (
            <button key={m.id} onClick={() => toggle(m.id)}
              className={`card p-3 text-left transition-all ${compareIds.includes(m.id) ? 'ring-2 ring-primary-500 bg-primary-500/5' : ''}`}>
              <div className="flex items-center gap-1 mb-1">
                <StatusIcon size={12} className={STATUS_COLORS[m.status]} />
                <span className="text-xs text-dark-400">{m.status}</span>
              </div>
              <div className="font-semibold text-white text-sm">{m.name}</div>
              <div className="text-xs text-dark-400">{m.type}</div>
              <div className="text-xs text-primary-400 mt-1">{(m.accuracy * 100).toFixed(1)}% acc</div>
            </button>
          );
        })}
      </div>

      {/* Comparison Table */}
      {compared.length > 0 && (
        <div className="card overflow-hidden">
          <div className="p-4 border-b border-dark-700">
            <h3 className="font-semibold text-white">Side-by-Side Comparison ({compared.length} models)</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-dark-700 text-dark-400">
                  <th className="px-4 py-3 text-left">Metric</th>
                  {compared.map(m => <th key={m.id} className="px-4 py-3 text-center">{m.name} <span className="text-xs text-dark-500">v{m.version}</span></th>)}
                </tr>
              </thead>
              <tbody>
                {[
                  { key: 'accuracy', label: 'Accuracy', fmt: (v: number) => `${(v * 100).toFixed(1)}%`, better: 'higher' },
                  { key: 'precision', label: 'Precision', fmt: (v: number) => `${(v * 100).toFixed(1)}%`, better: 'higher' },
                  { key: 'recall', label: 'Recall', fmt: (v: number) => `${(v * 100).toFixed(1)}%`, better: 'higher' },
                  { key: 'f1Score', label: 'F1 Score', fmt: (v: number) => `${(v * 100).toFixed(1)}%`, better: 'higher' },
                  { key: 'inferenceTime', label: 'Inference Time', fmt: (v: number) => `${v}ms`, better: 'lower' },
                  { key: 'fps', label: 'FPS', fmt: (v: number) => `${v}`, better: 'higher' },
                  { key: 'modelSize', label: 'Model Size', fmt: (v: number) => `${v} MB`, better: 'lower' },
                  { key: 'totalDetections', label: 'Total Detections', fmt: (v: number) => v.toLocaleString(), better: 'higher' },
                  { key: 'falsePositives', label: 'False Positives', fmt: (v: number) => v.toLocaleString(), better: 'lower' },
                  { key: 'falseNegatives', label: 'False Negatives', fmt: (v: number) => v.toLocaleString(), better: 'lower' },
                ].map(metric => {
                  const values = compared.map(m => (m as any)[metric.key] as number);
                  const best = metric.better === 'higher' ? Math.max(...values) : Math.min(...values);
                  return (
                    <tr key={metric.key} className="border-b border-dark-800 hover:bg-dark-700/20">
                      <td className="px-4 py-3 text-dark-300 font-medium">{metric.label}</td>
                      {compared.map(m => {
                        const val = (m as any)[metric.key] as number;
                        const isBest = val === best && compared.length > 1;
                        return (
                          <td key={m.id} className={`px-4 py-3 text-center ${isBest ? 'text-green-400 font-semibold' : 'text-white'}`}>
                            {metric.fmt(val)} {isBest && '✓'}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Individual Model Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {compared.map(m => (
          <div key={m.id} className="card p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="font-semibold text-white text-lg">{m.name}</h3>
                <p className="text-xs text-dark-400">{m.type} &middot; v{m.version}</p>
              </div>
              <div className="flex items-center gap-2">
                <Cpu size={14} className="text-dark-400" />
                <span className="text-sm text-dark-300">{m.modelSize}MB</span>
              </div>
            </div>
            <div className="space-y-3">
              <MetricBar label="Accuracy" value={m.accuracy} color="bg-green-500" />
              <MetricBar label="Precision" value={m.precision} color="bg-blue-500" />
              <MetricBar label="Recall" value={m.recall} color="bg-purple-500" />
              <MetricBar label="F1 Score" value={m.f1Score} color="bg-yellow-500" />
              <MetricBar label="Inference" value={m.inferenceTime} max={50} format="ms" color="bg-red-500" />
              <MetricBar label="FPS" value={m.fps} max={150} format="fps" color="bg-cyan-500" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

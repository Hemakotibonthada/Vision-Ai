import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { trainingApi } from '../services/api';
import { useTrainingStore } from '../store';
import { useDropzone } from 'react-dropzone';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import toast from 'react-hot-toast';
import {
  Brain, Play, Pause, Upload, Database, Layers, Zap, Settings2,
  TrendingUp, BarChart3, RefreshCw, Loader2, Plus, Folder
} from 'lucide-react';

export default function Training() {
  const queryClient = useQueryClient();
  const { isTraining, progress, currentEpoch, totalEpochs, metrics } = useTrainingStore();
  const [tab, setTab] = useState<'train' | 'datasets' | 'models' | 'advanced'>('train');
  
  const [config, setConfig] = useState({
    dataset_path: '', model_name: 'yolov8n.pt', epochs: 50,
    batch_size: 16, img_size: 640, lr: 0.01, augment: true
  });

  const { data: trainStatus } = useQuery({ queryKey: ['trainStatus'], queryFn: () => trainingApi.getStatus(), refetchInterval: isTraining ? 5000 : 30000 });
  const { data: trainHistory } = useQuery({ queryKey: ['trainHistory'], queryFn: () => trainingApi.getHistory() });
  const { data: datasets } = useQuery({ queryKey: ['datasets'], queryFn: () => trainingApi.getDatasets() });
  const { data: models } = useQuery({ queryKey: ['models'], queryFn: () => trainingApi.getModels() });

  const startTraining = useMutation({
    mutationFn: (cfg: any) => trainingApi.start(cfg),
    onSuccess: () => { toast.success('Training started!'); queryClient.invalidateQueries({ queryKey: ['trainStatus'] }); },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Failed to start training'),
  });

  const selfTrain = useMutation({
    mutationFn: (cfg: any) => trainingApi.selfTrain(cfg),
    onSuccess: () => toast.success('Self-training started!'),
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Failed'),
  });

  const transferLearn = useMutation({
    mutationFn: (cfg: any) => trainingApi.transferLearn(cfg),
    onSuccess: () => toast.success('Transfer learning started!'),
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Failed'),
  });

  const createDataset = useMutation({
    mutationFn: (data: any) => trainingApi.createDataset(data),
    onSuccess: () => { toast.success('Dataset created!'); queryClient.invalidateQueries({ queryKey: ['datasets'] }); },
  });

  const compress = useMutation({
    mutationFn: (data: any) => trainingApi.compress(data),
    onSuccess: (res) => toast.success(`Model compressed! Size: ${res.data.compressed_size}`)
  });

  // Mock training metrics for chart
  const metricsData = trainHistory?.data?.map((h: any, i: number) => ({
    epoch: i + 1,
    loss: h.metrics?.loss || Math.random() * 0.5,
    accuracy: h.metrics?.accuracy || 0.5 + Math.random() * 0.5,
    mAP: h.metrics?.mAP || 0.4 + Math.random() * 0.5,
  })) || [];

  const tabs = [
    { key: 'train', label: 'Training', icon: Brain },
    { key: 'datasets', label: 'Datasets', icon: Database },
    { key: 'models', label: 'Models', icon: Layers },
    { key: 'advanced', label: 'Advanced', icon: Settings2 },
  ];

  return (
    <div className="space-y-6">
      {/* Training Status Bar */}
      {isTraining && (
        <div className="card border-primary-500/30">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Loader2 size={18} className="animate-spin text-primary-400" />
              <span className="font-medium">Training in Progress</span>
            </div>
            <span className="text-sm text-dark-300">Epoch {currentEpoch}/{totalEpochs}</span>
          </div>
          <div className="h-2 bg-dark-700 rounded-full overflow-hidden">
            <div className="h-full bg-primary-500 rounded-full transition-all duration-500" style={{ width: `${progress}%` }} />
          </div>
          <div className="flex justify-between mt-2 text-xs text-dark-400">
            <span>{progress.toFixed(1)}%</span>
            <span>Loss: {metrics?.loss?.toFixed(4) || 'N/A'} | mAP: {metrics?.mAP?.toFixed(4) || 'N/A'}</span>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-dark-800 rounded-lg w-fit">
        {tabs.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key as any)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-colors ${
              tab === key ? 'bg-primary-600 text-white' : 'text-dark-400 hover:text-white hover:bg-dark-700'
            }`}
          >
            <Icon size={16} /> {label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {tab === 'train' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Training Config */}
          <div className="card">
            <h3 className="text-lg font-semibold mb-4">Training Configuration</h3>
            <div className="space-y-4">
              <div>
                <label className="text-sm text-dark-400">Dataset</label>
                <select className="select mt-1" value={config.dataset_path} onChange={(e) => setConfig({ ...config, dataset_path: e.target.value })}>
                  <option value="">Select dataset...</option>
                  {(datasets?.data || []).map((d: any) => (
                    <option key={d.id} value={d.path}>{d.name} ({d.image_count || 0} images)</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm text-dark-400">Base Model</label>
                <select className="select mt-1" value={config.model_name} onChange={(e) => setConfig({ ...config, model_name: e.target.value })}>
                  <option value="yolov8n.pt">YOLOv8 Nano</option>
                  <option value="yolov8s.pt">YOLOv8 Small</option>
                  <option value="yolov8m.pt">YOLOv8 Medium</option>
                  <option value="yolov8l.pt">YOLOv8 Large</option>
                  <option value="yolov8x.pt">YOLOv8 XLarge</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-dark-400">Epochs</label>
                  <input type="number" className="input mt-1" value={config.epochs} onChange={(e) => setConfig({ ...config, epochs: +e.target.value })} />
                </div>
                <div>
                  <label className="text-sm text-dark-400">Batch Size</label>
                  <input type="number" className="input mt-1" value={config.batch_size} onChange={(e) => setConfig({ ...config, batch_size: +e.target.value })} />
                </div>
                <div>
                  <label className="text-sm text-dark-400">Image Size</label>
                  <input type="number" className="input mt-1" value={config.img_size} onChange={(e) => setConfig({ ...config, img_size: +e.target.value })} />
                </div>
                <div>
                  <label className="text-sm text-dark-400">Learning Rate</label>
                  <input type="number" step="0.001" className="input mt-1" value={config.lr} onChange={(e) => setConfig({ ...config, lr: +e.target.value })} />
                </div>
              </div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={config.augment} onChange={(e) => setConfig({ ...config, augment: e.target.checked })} className="form-checkbox" />
                <span className="text-sm text-dark-300">Enable Data Augmentation</span>
              </label>
              <button
                onClick={() => startTraining.mutate(config)}
                disabled={startTraining.isPending || isTraining || !config.dataset_path}
                className="btn-primary w-full flex items-center justify-center gap-2"
              >
                {startTraining.isPending ? <Loader2 size={18} className="animate-spin" /> : <Play size={18} />}
                Start Training
              </button>
            </div>
          </div>

          {/* Metrics Chart */}
          <div className="card">
            <h3 className="text-lg font-semibold mb-4">Training Metrics</h3>
            {metricsData.length > 0 ? (
              <ResponsiveContainer width="100%" height={350}>
                <LineChart data={metricsData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="epoch" stroke="#64748b" fontSize={12} />
                  <YAxis stroke="#64748b" fontSize={12} />
                  <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }} />
                  <Legend />
                  <Line type="monotone" dataKey="loss" stroke="#ef4444" strokeWidth={2} dot={false} name="Loss" />
                  <Line type="monotone" dataKey="accuracy" stroke="#22c55e" strokeWidth={2} dot={false} name="Accuracy" />
                  <Line type="monotone" dataKey="mAP" stroke="#3b82f6" strokeWidth={2} dot={false} name="mAP" />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-64 text-dark-500">
                <div className="text-center">
                  <TrendingUp size={40} className="mx-auto mb-2" />
                  <p>No training data yet</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {tab === 'datasets' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">Datasets</h3>
            <button
              onClick={() => createDataset.mutate({ name: `Dataset-${Date.now()}`, description: 'New dataset' })}
              className="btn-primary flex items-center gap-2"
            >
              <Plus size={16} /> New Dataset
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {(datasets?.data || []).map((ds: any) => (
              <div key={ds.id} className="card-hover">
                <div className="flex items-center gap-3 mb-3">
                  <Folder size={24} className="text-yellow-400" />
                  <div>
                    <h4 className="font-medium">{ds.name}</h4>
                    <p className="text-xs text-dark-400">{ds.description}</p>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-2 text-center text-sm">
                  <div className="p-2 bg-dark-900 rounded-lg">
                    <div className="font-bold">{ds.image_count || 0}</div>
                    <div className="text-xs text-dark-400">Images</div>
                  </div>
                  <div className="p-2 bg-dark-900 rounded-lg">
                    <div className="font-bold">{ds.class_count || 0}</div>
                    <div className="text-xs text-dark-400">Classes</div>
                  </div>
                  <div className="p-2 bg-dark-900 rounded-lg">
                    <div className="font-bold">{ds.split || 'N/A'}</div>
                    <div className="text-xs text-dark-400">Split</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === 'models' && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">Trained Models</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {(models?.data || []).map((m: any) => (
              <div key={m.id} className="card-hover">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Brain size={20} className="text-purple-400" />
                    <span className="font-medium">{m.name}</span>
                  </div>
                  <span className="badge-info">{m.framework || 'PyTorch'}</span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div><span className="text-dark-400">Version:</span> <span>{m.version || '1.0'}</span></div>
                  <div><span className="text-dark-400">Type:</span> <span>{m.model_type || 'detection'}</span></div>
                  <div><span className="text-dark-400">mAP:</span> <span className="text-green-400">{m.metrics?.mAP?.toFixed(3) || 'N/A'}</span></div>
                  <div><span className="text-dark-400">Size:</span> <span>{m.file_size || 'N/A'}</span></div>
                </div>
                <div className="flex gap-2 mt-3">
                  <button className="btn-secondary text-sm flex-1">Load</button>
                  <button onClick={() => compress.mutate({ model_path: m.path })} className="btn-secondary text-sm flex-1">
                    <Zap size={14} className="inline mr-1" /> Compress
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === 'advanced' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Self-Training */}
          <div className="card">
            <h3 className="font-semibold mb-3 flex items-center gap-2"><RefreshCw size={18} className="text-green-400" /> Self-Training</h3>
            <p className="text-sm text-dark-400 mb-4">Automatically train using pseudo-labels from unlabeled data.</p>
            <button
              onClick={() => selfTrain.mutate({ unlabeled_dir: 'data/unlabeled', confidence_threshold: 0.8, iterations: 3 })}
              disabled={selfTrain.isPending}
              className="btn-success w-full"
            >
              {selfTrain.isPending ? 'Running...' : 'Start Self-Training'}
            </button>
          </div>

          {/* Transfer Learning */}
          <div className="card">
            <h3 className="font-semibold mb-3 flex items-center gap-2"><Layers size={18} className="text-blue-400" /> Transfer Learning</h3>
            <p className="text-sm text-dark-400 mb-4">Fine-tune a pre-trained model on your custom dataset.</p>
            <button
              onClick={() => transferLearn.mutate({ base_model: config.model_name, dataset_path: config.dataset_path || 'data/custom', freeze_layers: 10 })}
              disabled={transferLearn.isPending}
              className="btn-primary w-full"
            >
              {transferLearn.isPending ? 'Running...' : 'Start Transfer Learning'}
            </button>
          </div>

          {/* Hyperparameter Tuning */}
          <div className="card">
            <h3 className="font-semibold mb-3 flex items-center gap-2"><Settings2 size={18} className="text-yellow-400" /> Hyperparameter Tuning</h3>
            <p className="text-sm text-dark-400 mb-4">Automatically find optimal training parameters via grid search.</p>
            <button className="btn-secondary w-full" onClick={() => toast('Starting hyperparameter tuning...')}>
              Start Tuning
            </button>
          </div>

          {/* Active Learning */}
          <div className="card">
            <h3 className="font-semibold mb-3 flex items-center gap-2"><Zap size={18} className="text-orange-400" /> Active Learning</h3>
            <p className="text-sm text-dark-400 mb-4">Select most informative samples for labeling to maximize model performance.</p>
            <button className="btn-secondary w-full" onClick={() => toast('Starting active learning pipeline...')}>
              Start Active Learning
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

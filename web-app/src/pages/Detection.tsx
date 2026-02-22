import { useState, useCallback } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { detectionApi } from '../services/api';
import { useDropzone } from 'react-dropzone';
import toast from 'react-hot-toast';
import { Upload, Search, Image, Box, Hash, Layers, Eye, Trash2, Download, Loader2 } from 'lucide-react';

export default function Detection() {
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [preview, setPreview] = useState<string>('');
  const [results, setResults] = useState<any>(null);
  const [mode, setMode] = useState<'detect' | 'count' | 'track' | 'heatmap'>('detect');
  const [confidence, setConfidence] = useState(0.5);

  const { data: stats } = useQuery({ queryKey: ['detStats'], queryFn: () => detectionApi.getStats() });
  const { data: history } = useQuery({ queryKey: ['detHistory'], queryFn: () => detectionApi.getHistory(20) });
  const { data: models } = useQuery({ queryKey: ['detModels'], queryFn: () => detectionApi.getModels() });

  const detectMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('confidence', confidence.toString());
      
      switch (mode) {
        case 'count': return (await detectionApi.count(formData)).data;
        case 'track': return (await detectionApi.track(formData)).data;
        case 'heatmap': return (await detectionApi.getHeatmap(formData)).data;
        default: return (await detectionApi.detect(formData)).data;
      }
    },
    onSuccess: (data) => {
      setResults(data);
      toast.success(`Detection complete: ${data?.detections?.length || data?.total || 0} objects found`);
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Detection failed'),
  });

  const onDrop = useCallback((files: File[]) => {
    if (files[0]) {
      setSelectedImage(files[0]);
      setPreview(URL.createObjectURL(files[0]));
      setResults(null);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpg', '.jpeg', '.png', '.bmp', '.webp'] },
    maxFiles: 1,
    maxSize: 20 * 1024 * 1024,
  });

  const handleDetect = () => {
    if (selectedImage) detectMutation.mutate(selectedImage);
  };

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="stat-card">
          <div className="stat-label">Total Inferences</div>
          <div className="stat-value">{stats?.data?.total_inferences || 0}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Avg Inference Time</div>
          <div className="stat-value">{stats?.data?.avg_inference_ms?.toFixed(0) || 0}ms</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Objects Detected</div>
          <div className="stat-value">{stats?.data?.total_objects || 0}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Models Loaded</div>
          <div className="stat-value">{stats?.data?.models_loaded || 0}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Upload & Controls */}
        <div className="space-y-4">
          <div className="card">
            <h3 className="text-lg font-semibold mb-4">Image Detection</h3>
            
            {/* Mode Selection */}
            <div className="flex gap-2 mb-4">
              {[
                { key: 'detect', label: 'Detect', icon: Search },
                { key: 'count', label: 'Count', icon: Hash },
                { key: 'track', label: 'Track', icon: Layers },
                { key: 'heatmap', label: 'Heatmap', icon: Eye },
              ].map(({ key, label, icon: Icon }) => (
                <button
                  key={key}
                  onClick={() => setMode(key as any)}
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm transition-colors ${
                    mode === key ? 'bg-primary-600 text-white' : 'bg-dark-700 text-dark-300 hover:bg-dark-600'
                  }`}
                >
                  <Icon size={16} /> {label}
                </button>
              ))}
            </div>

            {/* Confidence Slider */}
            <div className="mb-4">
              <label className="text-sm text-dark-400">Confidence: {(confidence * 100).toFixed(0)}%</label>
              <input
                type="range" min={0.1} max={1} step={0.05}
                value={confidence}
                onChange={(e) => setConfidence(+e.target.value)}
                className="w-full mt-1"
              />
            </div>

            {/* Drop Zone */}
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
                isDragActive ? 'border-primary-500 bg-primary-500/5' : 'border-dark-600 hover:border-dark-400'
              }`}
            >
              <input {...getInputProps()} />
              {preview ? (
                <img src={preview} alt="Preview" className="max-h-64 mx-auto rounded-lg" />
              ) : (
                <div>
                  <Upload size={40} className="mx-auto text-dark-500 mb-3" />
                  <p className="text-dark-300">Drop an image here or click to upload</p>
                  <p className="text-dark-500 text-sm mt-1">JPG, PNG, BMP, WebP up to 20MB</p>
                </div>
              )}
            </div>

            {/* Detect Button */}
            <button
              onClick={handleDetect}
              disabled={!selectedImage || detectMutation.isPending}
              className="btn-primary w-full mt-4 flex items-center justify-center gap-2"
            >
              {detectMutation.isPending ? (
                <><Loader2 size={18} className="animate-spin" /> Processing...</>
              ) : (
                <><Search size={18} /> Run Detection</>
              )}
            </button>
          </div>

          {/* Model Selection */}
          <div className="card">
            <h3 className="text-sm font-semibold mb-3">Loaded Models</h3>
            <div className="space-y-2">
              {(Array.isArray(models?.data) ? models.data : []).map((m: any, i: number) => (
                <div key={i} className="flex items-center justify-between p-2 bg-dark-900 rounded-lg text-sm">
                  <span className="text-dark-200">{m.name || m}</span>
                  <span className="badge-info">{m.type || 'YOLO'}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Results */}
        <div className="space-y-4">
          <div className="card">
            <h3 className="text-lg font-semibold mb-4">Results</h3>
            {results ? (
              <div className="space-y-4">
                {/* Summary */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="p-3 bg-dark-900 rounded-lg text-center">
                    <div className="text-xl font-bold text-primary-400">{results.detections?.length || results.total || 0}</div>
                    <div className="text-xs text-dark-400">Objects</div>
                  </div>
                  <div className="p-3 bg-dark-900 rounded-lg text-center">
                    <div className="text-xl font-bold text-green-400">{results.inference_ms?.toFixed(0) || 0}ms</div>
                    <div className="text-xs text-dark-400">Inference</div>
                  </div>
                  <div className="p-3 bg-dark-900 rounded-lg text-center">
                    <div className="text-xl font-bold text-yellow-400">{Object.keys(results.class_counts || {}).length}</div>
                    <div className="text-xs text-dark-400">Classes</div>
                  </div>
                </div>

                {/* Class Counts */}
                {results.class_counts && (
                  <div>
                    <h4 className="text-sm text-dark-400 mb-2">Class Distribution</h4>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(results.class_counts || {}).map(([cls, count]: any) => (
                        <span key={cls} className="badge-info">{cls}: {count}</span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Detection List */}
                {results.detections && (
                  <div className="max-h-64 overflow-y-auto space-y-2">
                    {results.detections.map((det: any, i: number) => (
                      <div key={i} className="flex items-center justify-between p-2 bg-dark-900 rounded-lg">
                        <div className="flex items-center gap-2">
                          <Box size={14} className="text-primary-400" />
                          <span className="text-sm font-medium">{det.class}</span>
                        </div>
                        <span className="text-sm text-dark-400">{(det.confidence * 100).toFixed(1)}%</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-16 text-dark-500">
                <Image size={48} className="mx-auto mb-3" />
                <p>Upload an image and run detection to see results</p>
              </div>
            )}
          </div>

          {/* History */}
          <div className="card">
            <h3 className="text-sm font-semibold mb-3">Recent History</h3>
            <div className="max-h-48 overflow-y-auto space-y-2">
              {(history?.data || []).map((h: any, i: number) => (
                <div key={i} className="flex items-center justify-between p-2 bg-dark-900 rounded-lg text-sm">
                  <span className="text-dark-300">{h.objects} objects</span>
                  <span className="text-dark-500">{h.inference_ms?.toFixed(0)}ms | {h.timestamp}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

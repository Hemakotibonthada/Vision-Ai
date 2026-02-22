import { useState } from 'react';
import { Image, Square, Circle, Type, Crosshair, Undo2, Redo2, Save, Trash2, Palette, Download, ZoomIn, ZoomOut } from 'lucide-react';

// Feature 73: Image Annotation Tool - annotate detection results

interface Annotation {
  id: number;
  type: 'rectangle' | 'circle' | 'text' | 'arrow';
  x: number;
  y: number;
  width?: number;
  height?: number;
  radius?: number;
  text?: string;
  color: string;
  label?: string;
  confidence?: number;
}

const MOCK_ANNOTATIONS: Annotation[] = [
  { id: 1, type: 'rectangle', x: 15, y: 20, width: 18, height: 45, color: '#10b981', label: 'Person', confidence: 0.95 },
  { id: 2, type: 'rectangle', x: 45, y: 35, width: 25, height: 35, color: '#3b82f6', label: 'Car', confidence: 0.88 },
  { id: 3, type: 'rectangle', x: 75, y: 15, width: 12, height: 20, color: '#f59e0b', label: 'Package', confidence: 0.72 },
  { id: 4, type: 'circle', x: 60, y: 65, radius: 8, color: '#ef4444', label: 'Alert Zone' },
];

const TOOLS = [
  { id: 'select', icon: Crosshair, label: 'Select' },
  { id: 'rectangle', icon: Square, label: 'Rectangle' },
  { id: 'circle', icon: Circle, label: 'Circle' },
  { id: 'text', icon: Type, label: 'Text Label' },
];

const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#ffffff'];

const LABELS = ['Person', 'Car', 'Dog', 'Cat', 'Package', 'Bicycle', 'Truck', 'Bird', 'Fire', 'Smoke', 'Custom'];

export default function ImageAnnotation() {
  const [annotations, setAnnotations] = useState(MOCK_ANNOTATIONS);
  const [activeTool, setActiveTool] = useState('select');
  const [activeColor, setActiveColor] = useState('#10b981');
  const [activeLabel, setActiveLabel] = useState('Person');
  const [selected, setSelected] = useState<number | null>(null);
  const [zoom, setZoom] = useState(1);
  const [showLabels, setShowLabels] = useState(true);
  const [showConfidence, setShowConfidence] = useState(true);

  const deleteAnnotation = (id: number) => {
    setAnnotations(as => as.filter(a => a.id !== id));
    setSelected(null);
  };

  const addAnnotation = () => {
    const newAnn: Annotation = {
      id: Date.now(),
      type: activeTool as any,
      x: 30 + Math.random() * 30,
      y: 30 + Math.random() * 30,
      width: activeTool === 'rectangle' ? 15 : undefined,
      height: activeTool === 'rectangle' ? 20 : undefined,
      radius: activeTool === 'circle' ? 10 : undefined,
      text: activeTool === 'text' ? activeLabel : undefined,
      color: activeColor,
      label: activeLabel,
    };
    setAnnotations([...annotations, newAnn]);
    setSelected(newAnn.id);
  };

  const selectedAnn = annotations.find(a => a.id === selected);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2"><Image size={24} /> Image Annotation</h1>
          <p className="text-dark-400 text-sm mt-1">{annotations.length} annotations</p>
        </div>
        <div className="flex items-center gap-2">
          <button className="btn btn-secondary flex items-center gap-1"><Undo2 size={14} /> Undo</button>
          <button className="btn btn-secondary flex items-center gap-1"><Redo2 size={14} /> Redo</button>
          <button className="btn btn-secondary flex items-center gap-1"><Download size={14} /> Export</button>
          <button className="btn btn-primary flex items-center gap-1"><Save size={14} /> Save</button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left Panel - Tools */}
        <div className="space-y-4">
          {/* Drawing Tools */}
          <div className="card p-4">
            <h3 className="text-sm font-semibold text-white mb-3">Tools</h3>
            <div className="grid grid-cols-2 gap-2">
              {TOOLS.map(tool => {
                const Icon = tool.icon;
                return (
                  <button key={tool.id} onClick={() => setActiveTool(tool.id)}
                    className={`p-2 rounded-lg text-xs flex flex-col items-center gap-1 ${activeTool === tool.id ? 'bg-primary-500 text-white' : 'bg-dark-700 text-dark-400 hover:text-white'}`}>
                    <Icon size={16} />
                    {tool.label}
                  </button>
                );
              })}
            </div>
            {activeTool !== 'select' && (
              <button onClick={addAnnotation} className="btn btn-primary w-full mt-3 text-xs">Add {activeTool}</button>
            )}
          </div>

          {/* Colors */}
          <div className="card p-4">
            <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-1"><Palette size={14} /> Color</h3>
            <div className="flex flex-wrap gap-2">
              {COLORS.map(color => (
                <button key={color} onClick={() => setActiveColor(color)}
                  className={`w-7 h-7 rounded-full border-2 transition-all ${activeColor === color ? 'border-white scale-110' : 'border-dark-600'}`}
                  style={{ backgroundColor: color }} />
              ))}
            </div>
          </div>

          {/* Labels */}
          <div className="card p-4">
            <h3 className="text-sm font-semibold text-white mb-3">Label</h3>
            <select className="input-field w-full text-sm" value={activeLabel} onChange={e => setActiveLabel(e.target.value)}>
              {LABELS.map(l => <option key={l} value={l}>{l}</option>)}
            </select>
          </div>

          {/* Display Options */}
          <div className="card p-4">
            <h3 className="text-sm font-semibold text-white mb-3">Display</h3>
            <div className="space-y-2">
              <label className="flex items-center justify-between text-sm text-dark-300 cursor-pointer">
                <span>Show Labels</span>
                <input type="checkbox" checked={showLabels} onChange={() => setShowLabels(!showLabels)} />
              </label>
              <label className="flex items-center justify-between text-sm text-dark-300 cursor-pointer">
                <span>Show Confidence</span>
                <input type="checkbox" checked={showConfidence} onChange={() => setShowConfidence(!showConfidence)} />
              </label>
            </div>
          </div>
        </div>

        {/* Canvas / Image */}
        <div className="lg:col-span-2">
          <div className="card p-2">
            <div className="flex items-center gap-2 mb-2 px-2">
              <button onClick={() => setZoom(Math.min(zoom + 0.2, 3))} className="p-1 rounded hover:bg-dark-700 text-dark-400"><ZoomIn size={14} /></button>
              <button onClick={() => setZoom(Math.max(zoom - 0.2, 0.5))} className="p-1 rounded hover:bg-dark-700 text-dark-400"><ZoomOut size={14} /></button>
              <span className="text-xs text-dark-400">{(zoom * 100).toFixed(0)}%</span>
            </div>
            <div className="relative bg-dark-800 rounded-lg overflow-hidden" style={{ paddingBottom: '66.67%', transform: `scale(${zoom})`, transformOrigin: 'top left' }}>
              <div className="absolute inset-0 flex items-center justify-center text-dark-600">
                <div className="text-center">
                  <Image size={64} className="mx-auto mb-2" />
                  <span className="text-sm">Camera Feed / Image</span>
                </div>
              </div>
              {/* Annotations */}
              {annotations.map(ann => (
                <div key={ann.id}
                  onClick={e => { e.stopPropagation(); setSelected(ann.id); }}
                  className={`absolute cursor-pointer transition-all ${selected === ann.id ? 'ring-2 ring-white' : ''}`}
                  style={{
                    left: `${ann.x}%`,
                    top: `${ann.y}%`,
                    width: ann.width ? `${ann.width}%` : ann.radius ? `${ann.radius * 2}%` : 'auto',
                    height: ann.height ? `${ann.height}%` : ann.radius ? `${ann.radius * 2}%` : 'auto',
                    border: `2px solid ${ann.color}`,
                    borderRadius: ann.type === 'circle' ? '50%' : '4px',
                    backgroundColor: `${ann.color}15`,
                  }}>
                  {showLabels && ann.label && (
                    <div className="absolute -top-5 left-0 text-[10px] px-1 rounded whitespace-nowrap"
                      style={{ backgroundColor: ann.color, color: '#000' }}>
                      {ann.label}
                      {showConfidence && ann.confidence && ` ${(ann.confidence * 100).toFixed(0)}%`}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Panel - Annotation List */}
        <div className="card p-4">
          <h3 className="text-sm font-semibold text-white mb-3">Annotations ({annotations.length})</h3>
          <div className="space-y-2 max-h-[500px] overflow-y-auto">
            {annotations.map(ann => (
              <div key={ann.id}
                onClick={() => setSelected(ann.id)}
                className={`p-2 rounded-lg cursor-pointer transition-all flex items-center gap-2 ${selected === ann.id ? 'bg-primary-500/20 border border-primary-500/30' : 'bg-dark-700 hover:bg-dark-600 border border-transparent'}`}>
                <div className="w-3 h-3 rounded-sm flex-shrink-0" style={{ backgroundColor: ann.color }} />
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-white truncate">{ann.label || ann.type}</div>
                  <div className="text-[10px] text-dark-400">{ann.type} @ ({ann.x.toFixed(0)}, {ann.y.toFixed(0)})</div>
                </div>
                {ann.confidence && <span className="text-[10px] text-dark-400">{(ann.confidence * 100).toFixed(0)}%</span>}
                <button onClick={e => { e.stopPropagation(); deleteAnnotation(ann.id); }}
                  className="p-0.5 rounded hover:bg-dark-600 text-dark-400 hover:text-red-400">
                  <Trash2 size={10} />
                </button>
              </div>
            ))}
          </div>

          {/* Selected Annotation Details */}
          {selectedAnn && (
            <div className="mt-4 pt-4 border-t border-dark-700 space-y-2">
              <h4 className="text-xs font-semibold text-white">Selected: {selectedAnn.label || selectedAnn.type}</h4>
              <div className="text-xs text-dark-400 space-y-1">
                <div className="flex justify-between"><span>Type</span><span className="text-white capitalize">{selectedAnn.type}</span></div>
                <div className="flex justify-between"><span>Position</span><span className="text-white">({selectedAnn.x.toFixed(1)}, {selectedAnn.y.toFixed(1)})</span></div>
                {selectedAnn.width && <div className="flex justify-between"><span>Size</span><span className="text-white">{selectedAnn.width.toFixed(1)} x {selectedAnn.height?.toFixed(1)}</span></div>}
                {selectedAnn.confidence && <div className="flex justify-between"><span>Confidence</span><span className="text-white">{(selectedAnn.confidence * 100).toFixed(1)}%</span></div>}
              </div>
              <button onClick={() => deleteAnnotation(selectedAnn.id)} className="btn btn-secondary w-full text-xs text-red-400 mt-2">
                <Trash2 size={12} className="inline mr-1" /> Delete
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

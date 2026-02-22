import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store';
import { authApi } from '../services/api';
import toast from 'react-hot-toast';
import { Eye, EyeOff, LogIn, UserPlus } from 'lucide-react';

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuthStore();
  const [isRegister, setIsRegister] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ username: '', password: '', email: '' });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (isRegister) {
        await authApi.register(form);
        toast.success('Account created! Please login.');
        setIsRegister(false);
      } else {
        const { data } = await authApi.login(form.username, form.password);
        login(data.user, data.token);
        toast.success(`Welcome back, ${data.user.username}!`);
        navigate('/');
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-dark-950 p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center text-white font-bold text-2xl mb-4">
            VA
          </div>
          <h1 className="text-2xl font-bold text-white">Vision-AI</h1>
          <p className="text-dark-400 mt-1">Intelligent IoT Vision System</p>
        </div>

        {/* Form */}
        <div className="card">
          <h2 className="text-lg font-semibold text-white mb-6">
            {isRegister ? 'Create Account' : 'Sign In'}
          </h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm text-dark-300 mb-1">Username</label>
              <input
                type="text"
                className="input"
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
                placeholder="Enter username"
                required
              />
            </div>
            {isRegister && (
              <div>
                <label className="block text-sm text-dark-300 mb-1">Email</label>
                <input
                  type="email"
                  className="input"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  placeholder="Enter email"
                />
              </div>
            )}
            <div>
              <label className="block text-sm text-dark-300 mb-1">Password</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  className="input pr-10"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  placeholder="Enter password"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-dark-400 hover:text-white"
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>
            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : isRegister ? (
                <><UserPlus size={18} /> Create Account</>
              ) : (
                <><LogIn size={18} /> Sign In</>
              )}
            </button>
          </form>
          <div className="mt-4 text-center">
            <button
              onClick={() => setIsRegister(!isRegister)}
              className="text-sm text-primary-400 hover:text-primary-300"
            >
              {isRegister ? 'Already have an account? Sign in' : "Don't have an account? Register"}
            </button>
          </div>
          <div className="mt-4 p-3 bg-dark-900 rounded-lg text-xs text-dark-400">
            <p>Default credentials: <span className="text-dark-200">admin / admin123</span></p>
          </div>
        </div>
      </div>
    </div>
  );
}

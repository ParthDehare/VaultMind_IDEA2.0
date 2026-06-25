import React, { useState } from 'react';
import { Loader2 } from 'lucide-react';
import ubiLogo from '../assets/ubi_logo.png';
import { fetchWithAuth } from '../apiService';
import { authStore } from '../authStore';

export default function LoginPage({ onLogin, t }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      const res = await fetchWithAuth('api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
        headers: { 'Content-Type': 'application/json' }
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || 'Login failed. Please check your credentials.');
      }
      
      // Start Kafka Stream in background after successful login
      try {
        await fetchWithAuth('api/system/start-stream', {
          method: 'POST'
        });
      } catch (streamErr) {
        console.warn("Failed to start stream:", streamErr);
      }
      
      authStore.setAuth(data.user);
      onLogin(data.access_token, data.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden" style={{ background: '#0a0a0a' }}>
      {/* Background Mesh */}
      <div className="absolute inset-0 opacity-20" style={{ background: 'radial-gradient(circle at 50% 50%, #E50914 0%, transparent 50%)' }}></div>
      <div className="absolute inset-0 opacity-10" style={{ backgroundImage: 'linear-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px)', backgroundSize: '40px 40px' }}></div>
      
      <div className="relative z-10 w-full max-w-md p-8 rounded-2xl border border-[#333]" style={{ background: 'rgba(18, 18, 18, 0.8)', backdropFilter: 'blur(16px)', boxShadow: '0 20px 50px rgba(0,0,0,0.5)' }}>
        <div className="text-center mb-8">
          <img src={ubiLogo} alt="Union Bank of India" className="h-16 mx-auto mb-6 object-contain rounded-lg px-4 py-2" style={{ background: 'rgba(255,255,255,0.95)' }} />
          <h2 className="text-xl font-bold tracking-[3px] text-white mb-2 uppercase">VaultMind</h2>
          <p className="text-[10px] text-gray-400 tracking-[2px] uppercase">Fraud Intelligence Platform 2.0</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-[10px] font-mono text-gray-400 uppercase tracking-wider mb-2">Employee Email</label>
            <input 
              type="email" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-[#111] border border-[#333] text-white px-4 py-3 rounded-lg text-sm font-mono focus:outline-none focus:border-[#E50914] transition-colors"
              placeholder="analyst@ubi.com"
              required
            />
          </div>
          <div>
            <label className="block text-[10px] font-mono text-gray-400 uppercase tracking-wider mb-2">Password</label>
            <input 
              type="password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-[#111] border border-[#333] text-white px-4 py-3 rounded-lg text-sm font-mono focus:outline-none focus:border-[#E50914] transition-colors"
              placeholder="••••••••"
              required
            />
          </div>

          {error && (
            <div className="text-[#E50914] text-xs font-mono text-center animate-pulse bg-red-900/20 py-2 rounded">
              {error}
            </div>
          )}

          <button 
            type="submit" 
            disabled={loading}
            className="w-full bg-[#E50914] hover:bg-red-700 text-white font-bold py-3 rounded-lg text-sm tracking-widest uppercase transition-colors flex items-center justify-center gap-2 mt-4 disabled:opacity-50"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : "Secure Login"}
          </button>
        </form>

        {/* Demo Credentials for Judges */}
        <div className="mt-8 pt-6 border-t border-[#333] text-center bg-black/30 p-4 rounded-lg">
          <div className="text-[10px] text-gray-400 uppercase tracking-widest mb-3">Judge Credentials</div>
          <div className="flex flex-col gap-2">
            <div className="flex justify-between items-center text-[10px] font-mono">
              <span className="text-blue-400">Analyst (Read-Only)</span>
              <span className="text-gray-300">analyst@ubi.com / analyst123</span>
            </div>
            <div className="flex justify-between items-center text-[10px] font-mono">
              <span className="text-red-400">Auditor (Full Action)</span>
              <span className="text-gray-300">auditor@ubi.com / auditor123</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

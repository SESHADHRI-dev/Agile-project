import React, { useState } from 'react';
import { BrainCircuit, ShieldCheck, UserCheck, Lock, Mail, AlertCircle } from 'lucide-react';
import { api } from '../api';

export default function LoginModal({ onLoginSuccess }) {
  const [username, setUsername] = useState('admin@intellistock.in');
  const [password, setPassword] = useState('Password123!');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async (e) => {
    if (e) e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await api.login(username, password);
      onLoginSuccess(res.user);
    } catch (err) {
      setError(err.message || 'Invalid credentials');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = (userEmail) => {
    setUsername(userEmail);
    setPassword('Password123!');
    setTimeout(() => {
      api.login(userEmail, 'Password123!')
        .then(res => onLoginSuccess(res.user))
        .catch(err => setError(err.message));
    }, 100);
  };

  return (
    <div className="modal-overlay" style={{ background: 'rgba(5, 8, 15, 0.92)' }}>
      <div className="modal-content" style={{ maxWidth: '440px' }}>
        <div style={{ padding: '2rem', textAlign: 'center', borderBottom: '1px solid var(--border-color)' }}>
          <div style={{
            width: '56px',
            height: '56px',
            borderRadius: '16px',
            background: 'var(--accent-gradient)',
            color: 'white',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 1rem',
            boxShadow: '0 8px 24px var(--accent-glow)'
          }}>
            <BrainCircuit size={32} />
          </div>
          <h2 style={{ fontSize: '1.35rem', fontWeight: 800 }}>IntelliStock India</h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            Intelligent Inventory & ML Stock Prediction &bull; Katpadi, Vellore (Tamil Nadu)
          </p>
        </div>

        <form onSubmit={handleLogin} style={{ padding: '1.75rem' }}>
          {error && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'var(--danger-bg)', color: 'var(--danger)', padding: '0.75rem', borderRadius: 'var(--radius-md)', marginBottom: '1.25rem', fontSize: '0.85rem' }}>
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          <div className="form-group">
            <label className="form-label">Email / Username</label>
            <div style={{ position: 'relative' }}>
              <Mail size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                type="email"
                required
                className="form-input"
                style={{ paddingLeft: '2.4rem' }}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>
          </div>

          <div className="form-group" style={{ marginBottom: '1.5rem' }}>
            <label className="form-label">Password</label>
            <div style={{ position: 'relative' }}>
              <Lock size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                type="password"
                required
                className="form-input"
                style={{ paddingLeft: '2.4rem' }}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn btn-primary"
            style={{ width: '100%', padding: '0.75rem' }}
          >
            {loading ? 'Authenticating...' : 'Sign In to Portal'}
          </button>

          {/* Quick Demo Logins for Faculty */}
          <div style={{ marginTop: '1.5rem', paddingTop: '1.25rem', borderTop: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textAlign: 'center', marginBottom: '0.75rem', fontWeight: 600 }}>
              ONE-CLICK FACULTY EVALUATION PROFILES:
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
              <button
                type="button"
                onClick={() => handleQuickLogin('admin@intellistock.in')}
                className="btn btn-secondary btn-sm"
                style={{ fontSize: '0.75rem' }}
              >
                <ShieldCheck size={14} color="var(--accent-primary)" />
                <span>Admin (Dr. Sharma)</span>
              </button>
              <button
                type="button"
                onClick={() => handleQuickLogin('staff@intellistock.in')}
                className="btn btn-secondary btn-sm"
                style={{ fontSize: '0.75rem' }}
              >
                <UserCheck size={14} color="var(--info)" />
                <span>Staff (Seshadhri)</span>
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

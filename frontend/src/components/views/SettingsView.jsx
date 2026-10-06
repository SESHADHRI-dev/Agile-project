import React, { useState } from 'react';
import { Settings, ShieldCheck, UserCheck, Database, RefreshCw, CheckCircle2, Cloud, Server, AlertCircle } from 'lucide-react';
import { api } from '../../api';

export default function SettingsView({ user, onSwitchUser, onRefreshAll }) {
  const [seeding, setSeeding] = useState(false);
  const [seedMessage, setSeedMessage] = useState('');

  const handleReseed = async () => {
    if (confirm('Reseed database? This will reset all demo products, suppliers, and historical transactions.')) {
      setSeeding(true);
      setSeedMessage('');
      try {
        const res = await api.seedDatabase();
        setSeedMessage(res.message);
        onRefreshAll();
      } catch (err) {
        alert(err.message || 'Error reseeding database');
      } finally {
        setSeeding(false);
      }
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', maxWidth: '900px' }}>
      <div>
        <h2 style={{ fontSize: '1.1rem', fontWeight: 800 }}>System Configuration & Demonstration Settings</h2>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          Manage user session roles, examine AWS cloud architectural bindings, and reseed evaluation data.
        </p>
      </div>

      {/* Role Switcher */}
      <div className="glass-card" style={{ padding: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
          <ShieldCheck size={18} color="var(--accent-primary)" />
          <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>Role-Based Access Control (RBAC)</h3>
        </div>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
          Switch between <strong>Admin</strong> (full CRUD permissions) and <strong>Staff</strong> (operational recording permissions) to demonstrate role enforcement to faculty.
        </p>

        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          <button
            id="btn-switch-admin"
            onClick={() => onSwitchUser('admin@intellistock.in')}
            className={`btn ${user?.role === 'Admin' ? 'btn-primary' : 'btn-secondary'}`}
          >
            <ShieldCheck size={16} />
            <span>Switch to Administrator (Dr. S. Sharma)</span>
          </button>

          <button
            id="btn-switch-staff"
            onClick={() => onSwitchUser('staff@intellistock.in')}
            className={`btn ${user?.role === 'Staff' ? 'btn-primary' : 'btn-secondary'}`}
          >
            <UserCheck size={16} />
            <span>Switch to Operations Staff (Seshadhri)</span>
          </button>
        </div>
      </div>

      {/* Demo Seeding */}
      <div className="glass-card" style={{ padding: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
          <RefreshCw size={18} color="var(--warning)" />
          <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>Academic Dataset Reseeding</h3>
        </div>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
          Restores the 15 standard Indian products across 5 categories, 5 verified Tamil Nadu suppliers, and 45 days of historical sales data in INR for demand forecasting evaluation.
        </p>

        {seedMessage && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'var(--success-bg)', color: 'var(--success)', padding: '0.75rem', borderRadius: 'var(--radius-md)', marginBottom: '1rem', fontSize: '0.85rem' }}>
            <CheckCircle2 size={16} />
            <span>{seedMessage}</span>
          </div>
        )}

        {user?.role !== 'Admin' ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            <AlertCircle size={15} color="var(--warning)" />
            <span>Dataset reseeding is restricted to Administrator role (Dr. S. Sharma).</span>
          </div>
        ) : (
          <button
            id="btn-reseed-data"
            onClick={handleReseed}
            disabled={seeding}
            className="btn btn-secondary"
          >
            <RefreshCw size={15} className={seeding ? "spin-animation" : ""} />
            <span>{seeding ? 'Reseeding Data...' : 'Reset & Reseed Demo Data'}</span>
          </button>
        )}
      </div>

      {/* Cloud & Architecture Details */}
      <div className="glass-card" style={{ padding: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
          <Cloud size={18} color="#8b5cf6" />
          <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>AWS Architecture & Regional Mapping</h3>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', fontSize: '0.825rem' }}>
          <div style={{ background: 'rgba(0,0,0,0.2)', padding: '0.75rem', borderRadius: '8px' }}>
            <div style={{ color: 'var(--text-muted)' }}>Target AWS Region</div>
            <div style={{ fontWeight: 700, marginTop: '0.2rem', color: 'var(--accent-primary)' }}>ap-south-1 (Mumbai, India)</div>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.2)', padding: '0.75rem', borderRadius: '8px' }}>
            <div style={{ color: 'var(--text-muted)' }}>DynamoDB Table</div>
            <div style={{ fontWeight: 700, marginTop: '0.2rem' }}>inventory-management-table-dev</div>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.2)', padding: '0.75rem', borderRadius: '8px' }}>
            <div style={{ color: 'var(--text-muted)' }}>Cognito User Pool</div>
            <div style={{ fontWeight: 700, marginTop: '0.2rem' }}>inventory-user-pool-dev</div>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.2)', padding: '0.75rem', borderRadius: '8px' }}>
            <div style={{ color: 'var(--text-muted)' }}>Lambda Handler</div>
            <div style={{ fontWeight: 700, marginTop: '0.2rem' }}>lambda.lambda_handler</div>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.2)', padding: '0.75rem', borderRadius: '8px' }}>
            <div style={{ color: 'var(--text-muted)' }}>S3 Reports Bucket</div>
            <div style={{ fontWeight: 700, marginTop: '0.2rem' }}>inventory-reports-mtech-storage</div>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.2)', padding: '0.75rem', borderRadius: '8px' }}>
            <div style={{ color: 'var(--text-muted)' }}>Registered Entity</div>
            <div style={{ fontWeight: 700, marginTop: '0.2rem' }}>IntelliStock India (Vellore, TN)</div>
          </div>
        </div>
      </div>
    </div>
  );
}

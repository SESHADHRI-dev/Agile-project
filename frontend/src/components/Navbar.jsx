import React from 'react';
import { Sun, Moon, ShieldCheck, UserCheck, Database, LogOut, RefreshCw, KeyRound, Cloud, Menu, Clock } from 'lucide-react';

export default function Navbar({
  activeTitle,
  alertCount,
  theme,
  toggleTheme,
  onRefresh,
  onLogout,
  authConfig,
  user,
  onToggleMobileMenu,
  isSyncing = false,
  lastSyncTime = ''
}) {
  const isLocalAuth = !authConfig || authConfig.is_local;
  const isLocalStorage = !authConfig || authConfig.storage_mode === 'local';

  // Parse clean display name for header
  const displayName = user?.name
    ? user.name.replace(/\s*\([^)]*\)/, '')
    : (user?.role === 'Admin' ? 'Dr. S. Sharma' : 'Seshadhri');

  return (
    <header style={{
      height: '70px',
      borderBottom: '1px solid var(--border-color)',
      background: 'var(--bg-secondary)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 1.5rem',
      position: 'sticky',
      top: 0,
      zIndex: 10
    }}>
      {/* Title & Breadcrumbs & Mobile Trigger */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <button
          onClick={onToggleMobileMenu}
          className="mobile-menu-btn btn btn-secondary btn-sm"
          style={{ padding: '0.4rem', display: 'none' }}
          title="Open menu"
        >
          <Menu size={18} />
        </button>

        <div>
          <h1 style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-primary)' }}>
            {activeTitle}
          </h1>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            IntelliStock India &bull; Katpadi, Vellore &bull; <span style={{ color: 'var(--accent-primary)' }}>Active Session (IST)</span>
          </div>
        </div>
      </div>

      {/* Action Toolbar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        {/* Auth Mode Indicator */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.4rem',
          padding: '0.35rem 0.75rem',
          borderRadius: 'var(--radius-full)',
          background: isLocalAuth ? 'rgba(16, 185, 129, 0.12)' : 'rgba(59, 130, 246, 0.12)',
          border: `1px solid ${isLocalAuth ? 'rgba(16, 185, 129, 0.3)' : 'rgba(59, 130, 246, 0.3)'}`,
          fontSize: '0.75rem',
          fontWeight: 700,
          color: isLocalAuth ? 'var(--success)' : 'var(--accent-primary)'
        }} title={isLocalAuth ? "Running in zero-friction Local Dev Auth mode" : "Secured with Amazon Cognito User Pools"}>
          <KeyRound size={13} />
          <span>AUTH: {isLocalAuth ? 'LOCAL DEV' : 'AWS COGNITO'}</span>
        </div>

        {/* Storage Mode Pill */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.4rem',
          padding: '0.35rem 0.75rem',
          borderRadius: 'var(--radius-full)',
          background: 'rgba(139, 92, 246, 0.12)',
          border: '1px solid rgba(139, 92, 246, 0.3)',
          fontSize: '0.75rem',
          fontWeight: 700,
          color: '#8b5cf6'
        }}>
          {isLocalStorage ? <Database size={13} /> : <Cloud size={13} />}
          <span>DB: {isLocalStorage ? 'LOCAL SQLITE' : 'DYNAMODB'}</span>
        </div>

        {/* Active User & Role Pill */}
        <div id="navbar-user-badge" style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.35rem',
          padding: '0.35rem 0.75rem',
          borderRadius: 'var(--radius-full)',
          background: user?.role === 'Admin' ? 'rgba(59, 130, 246, 0.15)' : 'rgba(6, 182, 212, 0.15)',
          border: `1px solid ${user?.role === 'Admin' ? 'rgba(59, 130, 246, 0.3)' : 'rgba(6, 182, 212, 0.3)'}`,
          fontSize: '0.75rem',
          fontWeight: 700,
          color: user?.role === 'Admin' ? 'var(--accent-primary)' : 'var(--info)'
        }}>
          {user?.role === 'Admin' ? <ShieldCheck size={14} /> : <UserCheck size={14} />}
          <span>{displayName} ({user?.role || 'Admin'})</span>
        </div>

        {/* Last Sync Indicator */}
        {lastSyncTime && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.3rem',
            fontSize: '0.7rem',
            color: 'var(--text-muted)',
            fontFamily: 'var(--font-mono)'
          }} title="Last successful synchronization with local SQLite & in-memory state in Indian Standard Time">
            <Clock size={12} />
            <span>{lastSyncTime}</span>
          </div>
        )}

        {/* Sync Button */}
        <button
          id="btn-sync-data"
          onClick={onRefresh}
          disabled={isSyncing}
          className="btn btn-secondary btn-sm"
          title={`Click to synchronize with backend • Last synced: ${lastSyncTime || 'Pending'}`}
          style={{ padding: '0.45rem 0.7rem' }}
        >
          <RefreshCw size={14} className={isSyncing ? "spin-animation" : ""} />
          <span>{isSyncing ? 'Syncing...' : 'Sync'}</span>
        </button>

        {/* Theme Toggle */}
        <button
          id="btn-toggle-theme"
          onClick={toggleTheme}
          className="btn btn-secondary btn-sm"
          title="Toggle Dark/Light Mode"
          style={{ padding: '0.45rem' }}
        >
          {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
        </button>

        {/* Logout */}
        <button
          id="btn-logout"
          onClick={onLogout}
          className="btn btn-secondary btn-sm"
          title="Log Out"
          style={{ color: 'var(--danger)', borderColor: 'rgba(239, 68, 68, 0.3)', padding: '0.45rem 0.7rem' }}
        >
          <LogOut size={14} />
          <span>Exit</span>
        </button>
      </div>
    </header>
  );
}

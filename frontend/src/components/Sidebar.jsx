import React from 'react';
import {
  LayoutDashboard,
  Package,
  Boxes,
  Truck,
  ShoppingBag,
  TrendingUp,
  AlertTriangle,
  BrainCircuit,
  ClipboardCheck,
  FileText,
  Settings,
  ShieldCheck,
  UserCheck,
  X
} from 'lucide-react';

export default function Sidebar({ activeTab, setActiveTab, alertCount = 0, user, mobileOpen = false, onClose }) {
  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'inventory', label: 'Inventory Status', icon: Package },
    { id: 'products', label: 'Products Catalog', icon: Boxes },
    { id: 'suppliers', label: 'Suppliers', icon: Truck },
    { id: 'purchases', label: 'Purchases (Inbound)', icon: ShoppingBag },
    { id: 'sales', label: 'Sales (Outbound)', icon: TrendingUp },
    { id: 'alerts', label: 'Low-Stock Alerts', icon: AlertTriangle, badge: alertCount },
    { id: 'prediction', label: 'Demand Forecasting', icon: BrainCircuit },
    { id: 'recommendations', label: 'Restock Orders', icon: ClipboardCheck },
    { id: 'reports', label: 'Audit Reports', icon: FileText },
    { id: 'settings', label: 'Settings & Demo', icon: Settings },
  ];

  return (
    <aside className={`sidebar ${mobileOpen ? 'mobile-open' : ''}`} style={{
      width: '270px',
      background: 'var(--bg-secondary)',
      borderRight: '1px solid var(--border-color)',
      display: 'flex',
      flexDirection: 'column',
      flexShrink: 0
    }}>
      {/* Brand Header */}
      <div style={{
        padding: '1.5rem',
        borderBottom: '1px solid var(--border-color)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '0.75rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: '12px',
            background: 'var(--accent-gradient)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            boxShadow: '0 4px 12px var(--accent-glow)'
          }}>
            <BrainCircuit size={24} />
          </div>
          <div>
            <h2 style={{ fontSize: '1.05rem', fontWeight: 800, letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
              IntelliStock India
            </h2>
            <span style={{ fontSize: '0.7rem', color: 'var(--accent-primary)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 700 }}>
              Katpadi, Vellore &bull; TN
            </span>
          </div>
        </div>

        {onClose && (
          <button
            onClick={onClose}
            className="mobile-menu-btn"
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '0.25rem'
            }}
            title="Close navigation"
          >
            <X size={20} />
          </button>
        )}
      </div>

      {/* Navigation List */}
      <nav style={{ flex: 1, padding: '1rem 0.75rem', overflowY: 'auto' }}>
        <ul style={{ listStyle: 'none' }}>
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <li key={item.id} style={{ marginBottom: '0.25rem' }}>
                <button
                  id={`nav-tab-${item.id}`}
                  data-tab={item.id}
                  onClick={() => {
                    setActiveTab(item.id);
                    if (onClose) onClose();
                  }}
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.7rem 0.9rem',
                    borderRadius: 'var(--radius-md)',
                    border: 'none',
                    background: isActive ? 'var(--accent-gradient)' : 'transparent',
                    color: isActive ? 'white' : 'var(--text-secondary)',
                    fontWeight: isActive ? 700 : 500,
                    fontSize: '0.85rem',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                    textAlign: 'left'
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) e.currentTarget.style.background = 'var(--bg-card-hover)';
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) e.currentTarget.style.background = 'transparent';
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <Icon size={18} />
                    <span>{item.label}</span>
                  </div>
                  {item.badge > 0 && (
                    <span style={{
                      background: 'var(--danger)',
                      color: 'white',
                      padding: '0.15rem 0.5rem',
                      borderRadius: 'var(--radius-full)',
                      fontSize: '0.7rem',
                      fontWeight: 700
                    }}>
                      {item.badge}
                    </span>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* User Footer Profile */}
      <div style={{
        padding: '1.25rem',
        borderTop: '1px solid var(--border-color)',
        background: 'rgba(0,0,0,0.15)',
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem'
      }}>
        <div style={{
          width: '36px',
          height: '36px',
          borderRadius: '50%',
          background: user?.role === 'Admin' ? 'var(--accent-primary)' : 'var(--info)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'white'
        }}>
          {user?.role === 'Admin' ? <ShieldCheck size={20} /> : <UserCheck size={20} />}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {user?.name || 'Administrator'}
          </div>
          <div style={{ fontSize: '0.725rem', color: 'var(--text-muted)' }}>
            Role: <strong style={{ color: user?.role === 'Admin' ? 'var(--accent-primary)' : 'var(--info)' }}>{user?.role || 'Admin'}</strong>
          </div>
        </div>
      </div>
    </aside>
  );
}

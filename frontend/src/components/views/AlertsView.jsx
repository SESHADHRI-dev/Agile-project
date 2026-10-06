import React from 'react';
import { AlertTriangle, XCircle, ArrowRight, BrainCircuit, ShoppingBag, RefreshCw } from 'lucide-react';

export default function AlertsView({ alerts = [], onNavigate, onRefresh, isSyncing = false }) {
  const critical = alerts.filter(a => a.severity === 'CRITICAL');
  const warnings = alerts.filter(a => a.severity === 'WARNING');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 800 }}>Active Low-Stock & Out-of-Stock Alerts</h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Automated rule engine detects when Current Stock &le; Minimum Stock Level or equals zero.
          </p>
        </div>
        {onRefresh && (
          <button
            id="btn-refresh-alerts"
            onClick={onRefresh}
            disabled={isSyncing}
            className="btn btn-secondary btn-sm"
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
            title="Fetch latest stock balances and recalculate active alerts from backend"
          >
            <RefreshCw size={14} className={isSyncing ? "spin-animation" : ""} />
            <span>{isSyncing ? 'Syncing...' : 'Sync Alerts'}</span>
          </button>
        )}
      </div>

      {/* Summary Counts */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        <div id="card-critical-stockouts" className="glass-card" style={{ borderLeft: '4px solid var(--danger)', padding: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--danger)', marginBottom: '0.25rem' }}>
            <XCircle size={18} />
            <strong style={{ fontSize: '0.85rem' }}>CRITICAL STOCKOUTS</strong>
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800 }}>{critical.length} Items</div>
        </div>

        <div id="card-low-stock-warnings" className="glass-card" style={{ borderLeft: '4px solid var(--warning)', padding: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--warning)', marginBottom: '0.25rem' }}>
            <AlertTriangle size={18} />
            <strong style={{ fontSize: '0.85rem' }}>LOW STOCK WARNINGS</strong>
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800 }}>{warnings.length} Items</div>
        </div>
      </div>

      {/* Alerts Feed */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
        {alerts.map((alt) => {
          const isCritical = alt.severity === 'CRITICAL';
          const deficit = Math.max(0, alt.min_stock_level - alt.current_stock);
          return (
            <div
              key={alt.id}
              id={`alert-card-${alt.product_id}`}
              className="glass-card alert-card-item"
              style={{
                borderLeft: `4px solid ${isCritical ? 'var(--danger)' : 'var(--warning)'}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '1.25rem',
                gap: '1rem',
                flexWrap: 'wrap'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <div style={{
                  width: '42px',
                  height: '42px',
                  borderRadius: '50%',
                  background: isCritical ? 'var(--danger-bg)' : 'var(--warning-bg)',
                  color: isCritical ? 'var(--danger)' : 'var(--warning)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  {isCritical ? <XCircle size={22} /> : <AlertTriangle size={22} />}
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span className={`badge ${isCritical ? 'badge-out-of-stock' : 'badge-low-stock'}`}>
                      {alt.severity}
                    </span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      {alt.product_id}
                    </span>
                  </div>
                  <h4 style={{ fontSize: '1rem', fontWeight: 800, marginTop: '0.2rem' }}>
                    {alt.product_name}
                  </h4>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                    {alt.message}
                  </p>
                  <div style={{ display: 'flex', gap: '1rem', marginTop: '0.35rem', fontSize: '0.8rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    <span>Current Stock: <strong style={{ color: isCritical ? 'var(--danger)' : 'var(--warning)' }}>{alt.current_stock}</strong></span>
                    <span>&bull;</span>
                    <span>Reorder Threshold: <strong>{alt.min_stock_level}</strong></span>
                    <span>&bull;</span>
                    <span>Deficit: <strong style={{ color: 'var(--danger)' }}>{deficit} units</strong></span>
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button
                  onClick={() => onNavigate('prediction')}
                  className="btn btn-secondary btn-sm"
                >
                  <BrainCircuit size={14} />
                  <span>Forecast Demand</span>
                </button>
                <button
                  id={`btn-replenish-${alt.product_id}`}
                  onClick={() => {
                    const suggestedQty = Math.max(deficit + 20, 30);
                    onNavigate('purchases', {
                      product_id: alt.product_id,
                      quantity: suggestedQty
                    });
                  }}
                  className="btn btn-primary btn-sm"
                  title={`Replenish ${alt.product_name}`}
                >
                  <ShoppingBag size={14} />
                  <span>Order Replenishment</span>
                </button>
              </div>
            </div>
          );
        })}

        {alerts.length === 0 && (
          <div id="alerts-empty-state" className="glass-card" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
            All inventory levels are healthy! No active stockout alerts.
          </div>
        )}
      </div>
    </div>
  );
}

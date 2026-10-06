import React from 'react';
import {
  Package,
  IndianRupee,
  AlertTriangle,
  XCircle,
  TrendingUp,
  ShoppingBag,
  ArrowUpRight,
  ArrowDownRight,
  BrainCircuit,
  CheckCircle2
} from 'lucide-react';
import { formatINR, formatIndianNumber, formatIndianDate } from '../../utils/formatters';

export default function DashboardView({
  inventorySummary,
  recentSales = [],
  recentPurchases = [],
  alerts = [],
  onNavigate
}) {
  const {
    total_products = 0,
    total_units = 0,
    total_inventory_value = 0,
    low_stock_count = 0,
    out_of_stock_count = 0
  } = inventorySummary || {};

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {/* Critical Alert Banner if Out of Stock exists */}
      {out_of_stock_count > 0 && (
        <div style={{
          background: 'linear-gradient(90deg, rgba(239, 68, 68, 0.15) 0%, rgba(245, 158, 11, 0.1) 100%)',
          border: '1px solid rgba(239, 68, 68, 0.35)',
          borderRadius: 'var(--radius-lg)',
          padding: '1rem 1.5rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          boxShadow: 'var(--shadow-sm)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '50%',
              background: 'var(--danger)',
              color: 'white',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <AlertTriangle size={20} />
            </div>
            <div>
              <h4 style={{ fontSize: '0.95rem', fontWeight: 800, color: 'var(--danger)' }}>
                Attention Required: {out_of_stock_count} Product(s) Out of Stock & {low_stock_count} Below Minimum
              </h4>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Automated inventory guardrails have flagged high-priority stockout risks. Review alerts or run demand forecasting.
              </p>
            </div>
          </div>
          <button
            onClick={() => onNavigate('alerts')}
            className="btn btn-sm btn-danger"
          >
            Review Alerts
          </button>
        </div>
      )}

      {/* KPI Cards Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))',
        gap: '1.25rem'
      }}>
        {/* Card 1: Total Products */}
        <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)' }}>CATALOG ITEMS</span>
            <div style={{ padding: '0.4rem', borderRadius: '8px', background: 'rgba(59, 130, 246, 0.15)', color: 'var(--accent-primary)' }}>
              <Package size={18} />
            </div>
          </div>
          <div style={{ fontSize: '1.85rem', fontWeight: 800 }}>{total_products}</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
            Active managed SKUs in DynamoDB
          </div>
        </div>

        {/* Card 2: Total Units */}
        <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)' }}>TOTAL STOCK BALANCE</span>
            <div style={{ padding: '0.4rem', borderRadius: '8px', background: 'rgba(16, 185, 129, 0.15)', color: 'var(--success)' }}>
              <CheckCircle2 size={18} />
            </div>
          </div>
          <div style={{ fontSize: '1.85rem', fontWeight: 800 }}>{formatIndianNumber(total_units)} <span style={{ fontSize: '1rem', fontWeight: 500, color: 'var(--text-muted)' }}>units</span></div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
            Current physical warehouse inventory
          </div>
        </div>

        {/* Card 3: Inventory Valuation */}
        <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)' }}>₹ INVENTORY VALUE</span>
            <div style={{ padding: '0.4rem', borderRadius: '8px', background: 'rgba(139, 92, 246, 0.15)', color: '#8b5cf6' }}>
              <IndianRupee size={18} />
            </div>
          </div>
          <div style={{ fontSize: '1.85rem', fontWeight: 800 }}>{formatINR(total_inventory_value)}</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
            Total value of inventory held in INR (₹)
          </div>
        </div>

        {/* Card 4: Low Stock Products */}
        <div id="kpi-card-low-stock" className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)' }}>LOW STOCK DEFICIT</span>
            <div style={{ padding: '0.4rem', borderRadius: '8px', background: 'var(--warning-bg)', color: 'var(--warning)' }}>
              <AlertTriangle size={18} />
            </div>
          </div>
          <div className="kpi-metric-val" style={{ fontSize: '1.85rem', fontWeight: 800, color: 'var(--warning)' }}>{low_stock_count}</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
            Current stock &le; configured minimum
          </div>
        </div>

        {/* Card 5: Out of Stock */}
        <div id="kpi-card-out-of-stock" className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)' }}>OUT OF STOCK</span>
            <div style={{ padding: '0.4rem', borderRadius: '8px', background: 'var(--danger-bg)', color: 'var(--danger)' }}>
              <XCircle size={18} />
            </div>
          </div>
          <div className="kpi-metric-val" style={{ fontSize: '1.85rem', fontWeight: 800, color: 'var(--danger)' }}>{out_of_stock_count}</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
            Zero available units &bull; Sales blocked
          </div>
        </div>
      </div>

      {/* Intelligent Prediction Spotlight */}
      <div className="glass-card" style={{
        background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.08) 0%, rgba(139, 92, 246, 0.12) 100%)',
        border: '1px solid rgba(139, 92, 246, 0.3)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '1.5rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
          <div style={{
            width: '54px',
            height: '54px',
            borderRadius: '16px',
            background: 'var(--accent-gradient)',
            color: 'white',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 8px 20px var(--accent-glow)'
          }}>
            <BrainCircuit size={30} />
          </div>
          <div>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 800 }}>
              AI/ML Demand Forecasting & Restocking Engine
            </h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', maxWidth: '650px' }}>
              Utilizes historical sales time-series to calculate daily demand rate via Exponential Smoothing (SES),
              evaluates lead-time safety stock, and dynamically generates procurement replenishment orders.
            </p>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button
            onClick={() => onNavigate('prediction')}
            className="btn btn-primary"
          >
            Launch Forecaster
          </button>
          <button
            onClick={() => onNavigate('recommendations')}
            className="btn btn-secondary"
          >
            View Reorder Sheet
          </button>
        </div>
      </div>

      {/* Two-Column Grid: Recent Sales & Purchases */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(450px, 1fr))',
        gap: '1.5rem'
      }}>
        {/* Recent Sales */}
        <div className="glass-card" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <TrendingUp size={18} color="var(--success)" />
              <h3 style={{ fontSize: '0.95rem', fontWeight: 700 }}>Recent Sales (Outbound)</h3>
            </div>
            <button
              onClick={() => onNavigate('sales')}
              className="btn btn-secondary btn-sm"
            >
              Record Sale
            </button>
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Qty</th>
                  <th>Total</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {recentSales.slice(0, 5).map((sale) => (
                  <tr key={sale.id}>
                    <td style={{ fontWeight: 600 }}>{sale.product_name || sale.product_id}</td>
                    <td><span className="badge badge-info">-{sale.quantity}</span></td>
                    <td style={{ fontWeight: 700, color: 'var(--success)' }}>{formatINR(sale.total_revenue)}</td>
                    <td style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>{formatIndianDate(sale.sale_date)}</td>
                  </tr>
                ))}
                {recentSales.length === 0 && (
                  <tr>
                    <td colSpan="4" style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No sales recorded yet.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Recent Purchases */}
        <div className="glass-card" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <ShoppingBag size={18} color="var(--accent-primary)" />
              <h3 style={{ fontSize: '0.95rem', fontWeight: 700 }}>Recent Purchases (Inbound)</h3>
            </div>
            <button
              onClick={() => onNavigate('purchases')}
              className="btn btn-secondary btn-sm"
            >
              Record Purchase
            </button>
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Supplier</th>
                  <th>Qty</th>
                  <th>Total Cost</th>
                </tr>
              </thead>
              <tbody>
                {recentPurchases.slice(0, 5).map((pur) => (
                  <tr key={pur.id}>
                    <td style={{ fontWeight: 600 }}>{pur.product_name || pur.product_id}</td>
                    <td style={{ color: 'var(--text-secondary)' }}>{pur.supplier_name || 'Vendor'}</td>
                    <td><span className="badge badge-in-stock">+{pur.quantity}</span></td>
                    <td style={{ fontWeight: 700 }}>{formatINR(pur.total_cost)}</td>
                  </tr>
                ))}
                {recentPurchases.length === 0 && (
                  <tr>
                    <td colSpan="4" style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No purchases recorded yet.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

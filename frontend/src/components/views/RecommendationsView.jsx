import React, { useState, useEffect } from 'react';
import { ClipboardCheck, RefreshCw, ShoppingBag, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { api } from '../../api';
import { formatINR, formatIndianNumber } from '../../utils/formatters';

export default function RecommendationsView({ onNavigate }) {
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [method, setMethod] = useState('exponential_smoothing');

  const fetchRecommendations = async () => {
    setLoading(true);
    try {
      const res = await api.getRecommendations(method);
      setRecommendations(res.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecommendations();
  }, [method]);

  const totalRestockUnits = recommendations.reduce((acc, r) => acc + (r.recommended_restock || 0), 0);
  const totalEstimatedCost = recommendations.reduce((acc, r) => acc + ((r.recommended_restock || 0) * (r.unit_price || 0)), 0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 800 }}>Prioritized Restocking Order Sheet</h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Batch replenishment plan generated across all SKUs using dynamic demand velocity and safety stock buffers.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <select
            id="recom-method-select"
            className="form-select"
            style={{ width: 'auto' }}
            value={method}
            onChange={(e) => setMethod(e.target.value)}
          >
            <option value="exponential_smoothing">Exponential Smoothing (SES)</option>
            <option value="weighted_moving_average">Weighted Moving Average (WMA)</option>
            <option value="moving_average">Simple Moving Average (SMA)</option>
          </select>

          <button id="btn-recalc-recom" onClick={fetchRecommendations} disabled={loading} className="btn btn-secondary">
            <RefreshCw size={15} />
            <span>{loading ? 'Calculating...' : 'Recalculate'}</span>
          </button>
        </div>
      </div>

      {/* Summary KPI */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
        <div className="glass-card" style={{ padding: '1rem' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>TOTAL RESTOCK REQUIRED</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: 'var(--accent-primary)' }}>
            {formatIndianNumber(totalRestockUnits)} units
          </div>
        </div>
        <div className="glass-card" style={{ padding: '1rem' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>ESTIMATED CAPITAL NEEDED</div>
          <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#8b5cf6' }}>
            {formatINR(totalEstimatedCost)}
          </div>
        </div>
      </div>

      {/* Recommendations Table */}
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>SKU / ID</th>
              <th>Product Name</th>
              <th>Current Stock</th>
              <th>Predicted Demand</th>
              <th>Safety Stock</th>
              <th>Recommended Order</th>
              <th>Urgency Priority</th>
              <th style={{ textAlign: 'right' }}>Procurement Action</th>
            </tr>
          </thead>
          <tbody>
            {recommendations.map((rec) => {
              let badge = 'badge-in-stock';
              if (rec.urgency_status === 'CRITICAL_OUT_OF_STOCK') badge = 'badge-out-of-stock';
              if (rec.urgency_status === 'URGENT_RESTOCK_REQUIRED') badge = 'badge-low-stock';
              if (rec.urgency_status === 'REORDER_RECOMMENDED') badge = 'badge-info';

              return (
                <tr key={rec.product_id}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    {rec.product_id}
                  </td>
                  <td style={{ fontWeight: 700 }}>{rec.product_name}</td>
                  <td style={{ fontWeight: 800 }}>{rec.current_stock}</td>
                  <td>{rec.predicted_demand} units</td>
                  <td>{rec.safety_stock} units</td>
                  <td style={{ fontWeight: 900, color: rec.recommended_restock > 0 ? 'var(--success)' : 'var(--text-muted)', fontSize: '1rem' }}>
                    {rec.recommended_restock} units
                  </td>
                  <td><span className={`badge ${badge}`}>{rec.urgency_status}</span></td>
                  <td style={{ textAlign: 'right' }}>
                    {rec.recommended_restock > 0 ? (
                      <button
                        onClick={() => onNavigate('purchases', { product_id: rec.product_id, quantity: rec.recommended_restock })}
                        className="btn btn-primary btn-sm"
                      >
                        <ShoppingBag size={13} />
                        <span>Order Now</span>
                      </button>
                    ) : (
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Optimal</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

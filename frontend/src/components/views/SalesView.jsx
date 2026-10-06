import React, { useState } from 'react';
import { Plus, TrendingUp, X, CheckCircle2, AlertCircle, AlertTriangle } from 'lucide-react';
import { api } from '../../api';
import { formatINR, formatIndianDateTime } from '../../utils/formatters';

export default function SalesView({ sales = [], products = [], onRefresh }) {
  const [modalOpen, setModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const [formData, setFormData] = useState({
    product_id: '',
    customer_name: 'Sri Ganesh Traders',
    quantity: '',
    unit_price: ''
  });

  const handleOpenModal = () => {
    // Pick first in-stock product
    const availableProd = products.find(p => p.quantity > 0) || products[0];
    setFormData({
      product_id: availableProd?.id || '',
      customer_name: 'Sri Ganesh Traders',
      quantity: 1,
      unit_price: availableProd ? availableProd.price : 120.00
    });
    setError('');
    setMessage('');
    setModalOpen(true);
  };

  const selectedProduct = products.find(p => p.id === formData.product_id);
  const currentStock = selectedProduct ? selectedProduct.quantity : 0;
  const saleQty = parseInt(formData.quantity, 10) || 0;
  const projectedStock = currentStock - saleQty;
  const isOverSale = saleQty > currentStock;

  const handleProductChange = (productId) => {
    const prod = products.find(p => p.id === productId);
    setFormData({
      ...formData,
      product_id: productId,
      unit_price: prod ? prod.price : formData.unit_price
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (isOverSale) {
      setError(`Cannot record sale! Requested quantity (${saleQty}) exceeds available stock (${currentStock}).`);
      return;
    }

    setError('');
    setMessage('');
    setLoading(true);

    try {
      const res = await api.recordSale({
        product_id: formData.product_id,
        customer_name: formData.customer_name || 'Retail Counter',
        quantity: saleQty,
        unit_price: parseFloat(formData.unit_price)
      });
      setMessage(res.message);
      if (onRefresh) {
        await onRefresh();
      }
      setTimeout(() => {
        setModalOpen(false);
      }, 1200);
    } catch (err) {
      setError(err.message || 'Error processing sales transaction');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 800 }}>Outbound Sales Ledger</h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Record customer orders across Indian clients. Feeds historical time-series data into the demand prediction engine.
          </p>
        </div>
        <button id="btn-open-record-sale" onClick={handleOpenModal} className="btn btn-primary">
          <Plus size={16} />
          <span>Record Customer Sale</span>
        </button>
      </div>

      {/* Sales Table */}
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Sale ID</th>
              <th>Product</th>
              <th>Customer</th>
              <th>Quantity</th>
              <th>Unit Price</th>
              <th>Total Revenue</th>
              <th>Sale Date (IST)</th>
              <th>Recorded By</th>
            </tr>
          </thead>
          <tbody>
            {sales.map((s) => (
              <tr key={s.id}>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  {s.id}
                </td>
                <td style={{ fontWeight: 700 }}>{s.product_name || s.product_id}</td>
                <td style={{ color: 'var(--text-secondary)' }}>{s.customer_name || 'Retail Counter'}</td>
                <td><span className="badge badge-info">-{s.quantity} units</span></td>
                <td>{formatINR(s.unit_price)}</td>
                <td style={{ fontWeight: 700, color: 'var(--success)' }}>{formatINR(s.total_revenue)}</td>
                <td style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>{formatIndianDateTime(s.sale_date)}</td>
                <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{s.created_by}</td>
              </tr>
            ))}
            {sales.length === 0 && (
              <tr>
                <td colSpan="8" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                  No customer sales recorded yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Record Sale Modal */}
      {modalOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3 style={{ fontSize: '1.1rem', fontWeight: 800 }}>Record Customer Sale</h3>
              <button id="btn-close-sale-modal" onClick={() => setModalOpen(false)} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                {message && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'var(--success-bg)', color: 'var(--success)', padding: '0.75rem', borderRadius: 'var(--radius-md)', marginBottom: '1rem', fontSize: '0.85rem' }}>
                    <CheckCircle2 size={16} />
                    <span>{message}</span>
                  </div>
                )}

                {error && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'var(--danger-bg)', color: 'var(--danger)', padding: '0.75rem', borderRadius: 'var(--radius-md)', marginBottom: '1rem', fontSize: '0.85rem' }}>
                    <AlertCircle size={16} />
                    <span>{error}</span>
                  </div>
                )}

                <div className="form-group">
                  <label className="form-label">Select Product *</label>
                  <select
                    id="sale-product-select"
                    className="form-select"
                    value={formData.product_id}
                    onChange={(e) => handleProductChange(e.target.value)}
                    required
                  >
                    {products.map(p => (
                      <option key={p.id} value={p.id} disabled={p.quantity === 0}>
                        {p.name} — Current Stock: {p.quantity} ({formatINR(p.price)}) {p.quantity === 0 ? '(OUT OF STOCK)' : ''}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Customer / Client Name</label>
                  <input
                    id="sale-customer-name"
                    type="text"
                    className="form-input"
                    value={formData.customer_name}
                    onChange={(e) => setFormData({ ...formData, customer_name: e.target.value })}
                    placeholder="e.g. Sri Ganesh Traders, Priya Enterprises, Vellore Tech Solutions"
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div className="form-group">
                    <label className="form-label">Sale Quantity *</label>
                    <input
                      id="sale-quantity"
                      type="number"
                      min="1"
                      required
                      className="form-input"
                      value={formData.quantity}
                      onChange={(e) => setFormData({ ...formData, quantity: e.target.value })}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Unit Selling Price (₹) *</label>
                    <input
                      id="sale-unit-price"
                      type="number"
                      step="0.01"
                      min="0.01"
                      required
                      className="form-input"
                      value={formData.unit_price}
                      onChange={(e) => setFormData({ ...formData, unit_price: e.target.value })}
                    />
                  </div>
                </div>

                {/* Over-sale Warning or Stock Deduction Preview */}
                {isOverSale ? (
                  <div style={{
                    background: 'var(--danger-bg)',
                    border: '1px solid rgba(239, 68, 68, 0.4)',
                    borderRadius: 'var(--radius-md)',
                    padding: '0.85rem',
                    color: 'var(--danger)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem',
                    fontSize: '0.825rem'
                  }}>
                    <AlertTriangle size={18} />
                    <div>
                      <strong>Insufficient Stock Guardrail:</strong> Cannot sell {saleQty} units. Only {currentStock} units available. Transaction will be rejected.
                    </div>
                  </div>
                ) : (
                  <div style={{
                    background: 'rgba(16, 185, 129, 0.08)',
                    border: '1px solid rgba(16, 185, 129, 0.25)',
                    borderRadius: 'var(--radius-md)',
                    padding: '0.85rem',
                    fontSize: '0.825rem'
                  }}>
                    <div style={{ fontWeight: 700, color: 'var(--success)', marginBottom: '0.25rem' }}>
                      Formula: New Stock = Current Stock - Quantity Sold
                    </div>
                    <div>
                      {currentStock} (Available) - {saleQty} (Sale) = <strong style={{ color: 'var(--text-primary)' }}>{projectedStock} units remaining</strong>
                    </div>
                  </div>
                )}
              </div>

              <div className="modal-footer">
                <button id="btn-cancel-sale" type="button" onClick={() => setModalOpen(false)} className="btn btn-secondary">
                  Cancel
                </button>
                <button
                  id="btn-submit-sale"
                  type="submit"
                  disabled={loading || isOverSale}
                  className="btn btn-primary"
                >
                  {loading ? 'Processing...' : 'Confirm & Deduct Stock'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

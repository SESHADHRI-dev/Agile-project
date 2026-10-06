import React, { useState } from 'react';
import { Plus, ShoppingBag, X, CheckCircle2, AlertCircle } from 'lucide-react';
import { api } from '../../api';
import { formatINR, formatIndianDateTime } from '../../utils/formatters';

export default function PurchasesView({
  purchases = [],
  products = [],
  suppliers = [],
  onRefresh,
  user,
  replenishTarget = null,
  onClearReplenishTarget
}) {
  const [modalOpen, setModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const [formData, setFormData] = useState({
    product_id: '',
    supplier_id: '',
    quantity: '',
    unit_cost: ''
  });

  const handleOpenModal = (targetProductId = null, suggestedQty = null) => {
    const pId = targetProductId || products[0]?.id || '';
    const prodObj = products.find(p => p.id === pId) || products[0];
    const defaultSup = prodObj?.supplier_id || suppliers[0]?.id || '';
    setFormData({
      product_id: pId,
      supplier_id: defaultSup,
      quantity: suggestedQty || 50,
      unit_cost: prodObj ? prodObj.price : 120.00
    });
    setError('');
    setMessage('');
    setModalOpen(true);
  };

  // Watch for pre-selected replenishment target from Low-Stock Alerts or Dashboard
  React.useEffect(() => {
    if (replenishTarget && replenishTarget.product_id) {
      handleOpenModal(replenishTarget.product_id, replenishTarget.quantity);
      if (onClearReplenishTarget) {
        onClearReplenishTarget();
      }
    }
  }, [replenishTarget]);

  const handleProductChange = (pId) => {
    const prod = products.find(p => p.id === pId);
    setFormData({
      ...formData,
      product_id: pId,
      supplier_id: prod?.supplier_id || formData.supplier_id,
      unit_cost: prod ? prod.price : formData.unit_cost
    });
  };

  const selectedProduct = products.find(p => p.id === formData.product_id);
  const previousStock = selectedProduct ? selectedProduct.quantity : 0;
  const purchaseQty = parseInt(formData.quantity, 10) || 0;
  const projectedStock = previousStock + purchaseQty;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setMessage('');
    setLoading(true);

    try {
      const res = await api.recordPurchase({
        product_id: formData.product_id,
        supplier_id: formData.supplier_id,
        quantity: purchaseQty,
        unit_cost: parseFloat(formData.unit_cost)
      });
      setMessage(res.message);
      if (onRefresh) {
        await onRefresh();
      }
      setTimeout(() => {
        setModalOpen(false);
      }, 1200);
    } catch (err) {
      setError(err.message || 'Error recording purchase order');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 800 }}>Inbound Purchase Management</h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Record replenishment orders from suppliers. Automatically increments inventory stock balance.
          </p>
        </div>
        {user?.role === 'Admin' && (
          <button id="btn-open-purchase-modal" onClick={handleOpenModal} className="btn btn-primary">
            <Plus size={16} />
            <span>Record New Purchase</span>
          </button>
        )}
      </div>

      {/* Purchases Table */}
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Purchase ID</th>
              <th>Product</th>
              <th>Supplier</th>
              <th>Quantity</th>
              <th>Unit Cost</th>
              <th>Total Amount</th>
              <th>Purchase Date (IST)</th>
              <th>Logged By</th>
            </tr>
          </thead>
          <tbody>
            {purchases.map((pur) => (
              <tr key={pur.id}>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  {pur.id}
                </td>
                <td style={{ fontWeight: 700 }}>{pur.product_name || pur.product_id}</td>
                <td style={{ color: 'var(--text-secondary)' }}>{pur.supplier_name || pur.supplier_id}</td>
                <td><span className="badge badge-in-stock">+{pur.quantity} units</span></td>
                <td>{formatINR(pur.unit_cost)}</td>
                <td style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{formatINR(pur.total_cost)}</td>
                <td style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>{formatIndianDateTime(pur.purchase_date)}</td>
                <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{pur.created_by}</td>
              </tr>
            ))}
            {purchases.length === 0 && (
              <tr>
                <td colSpan="8" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                  No purchases recorded yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Record Purchase Modal */}
      {modalOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3 style={{ fontSize: '1.1rem', fontWeight: 800 }}>Record Inbound Purchase Order</h3>
              <button onClick={() => setModalOpen(false)} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
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
                    id="purchase-select-product"
                    className="form-select"
                    value={formData.product_id}
                    onChange={(e) => handleProductChange(e.target.value)}
                    required
                  >
                    {products.map(p => (
                      <option key={p.id} value={p.id}>
                        {p.name} (Stock: {p.quantity} | {formatINR(p.price)})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Select Supplier *</label>
                  <select
                    id="purchase-select-supplier"
                    className="form-select"
                    value={formData.supplier_id}
                    onChange={(e) => setFormData({ ...formData, supplier_id: e.target.value })}
                    required
                  >
                    {suppliers.map(s => (
                      <option key={s.id} value={s.id}>{s.name} ({s.state || 'Tamil Nadu'})</option>
                    ))}
                  </select>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div className="form-group">
                    <label className="form-label">Purchase Quantity *</label>
                    <input
                      id="purchase-input-quantity"
                      type="number"
                      min="1"
                      required
                      className="form-input"
                      value={formData.quantity}
                      onChange={(e) => setFormData({ ...formData, quantity: e.target.value })}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Unit Cost (₹) *</label>
                    <input
                      id="purchase-input-cost"
                      type="number"
                      step="0.01"
                      min="0.01"
                      required
                      className="form-input"
                      value={formData.unit_cost}
                      onChange={(e) => setFormData({ ...formData, unit_cost: e.target.value })}
                    />
                  </div>
                </div>

                {/* Live Formula Preview */}
                <div style={{
                  background: 'rgba(59, 130, 246, 0.08)',
                  border: '1px solid rgba(59, 130, 246, 0.2)',
                  borderRadius: 'var(--radius-md)',
                  padding: '0.85rem',
                  marginTop: '0.5rem',
                  fontSize: '0.825rem'
                }}>
                  <div style={{ fontWeight: 700, color: 'var(--accent-primary)', marginBottom: '0.25rem' }}>
                    Formula: Current Stock = Previous Stock + Purchase
                  </div>
                  <div>
                    {previousStock} (Previous) + {purchaseQty} (Purchased) = <strong style={{ color: 'var(--success)' }}>{projectedStock} units</strong>
                  </div>
                </div>
              </div>

              <div className="modal-footer">
                <button id="btn-cancel-purchase" type="button" onClick={() => setModalOpen(false)} className="btn btn-secondary">
                  Cancel
                </button>
                <button id="btn-submit-purchase" type="submit" disabled={loading} className="btn btn-primary">
                  {loading ? 'Processing...' : 'Confirm & Increment Stock'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

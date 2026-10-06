import React, { useState } from 'react';
import { Plus, Search, Filter, Edit, Trash2, X, AlertCircle, CheckCircle2, ShieldAlert } from 'lucide-react';
import { api } from '../../api';
import { formatINR, INDIAN_PRODUCT_CATEGORIES } from '../../utils/formatters';

export default function ProductsView({ products = [], suppliers = [], onRefresh, user }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('ALL');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState('');

  // Delete Confirmation Modal State
  const [deletingProduct, setDeletingProduct] = useState(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [feedback, setFeedback] = useState({ type: '', message: '' });

  const [formData, setFormData] = useState({
    name: '',
    category: 'Electrical Components',
    price: '',
    quantity: '',
    min_stock_level: '',
    supplier_id: '',
    hsn_code: '8536',
    gst_rate: 18.0
  });

  const categories = ['ALL', ...INDIAN_PRODUCT_CATEGORIES];

  // Self-heal / fetch data on mount if products list is currently empty
  React.useEffect(() => {
    if (products.length === 0 && onRefresh) {
      onRefresh();
    }
  }, []);

  const cleanSearch = searchTerm.trim().toLowerCase();
  const cleanCat = categoryFilter.trim().toLowerCase();

  const filteredProducts = products.filter((p) => {
    if (!p) return false;
    const pName = (p.name || '').toLowerCase();
    const pId = (p.id || '').toLowerCase();
    const pHsn = (p.hsn_code || '').toLowerCase();
    const pCat = (p.category || '').toLowerCase();
    const pSupplier = (p.supplier_name || '').toLowerCase();

    const matchesSearch = !cleanSearch ||
      pName.includes(cleanSearch) ||
      pId.includes(cleanSearch) ||
      pHsn.includes(cleanSearch) ||
      pSupplier.includes(cleanSearch) ||
      pCat.includes(cleanSearch);

    const matchesCat = cleanCat === 'all' || pCat === cleanCat;
    return matchesSearch && matchesCat;
  });

  const handleOpenAdd = () => {
    setEditingProduct(null);
    setFormData({
      name: '',
      category: 'Electrical Components',
      price: '',
      quantity: '',
      min_stock_level: '',
      supplier_id: suppliers[0]?.id || '',
      hsn_code: '8536',
      gst_rate: 18.0
    });
    setFormError('');
    setModalOpen(true);
  };

  const handleOpenEdit = (prod) => {
    setEditingProduct(prod);
    setFormData({
      name: prod.name,
      category: prod.category,
      price: prod.price,
      quantity: prod.quantity,
      min_stock_level: prod.min_stock_level,
      supplier_id: prod.supplier_id || '',
      hsn_code: prod.hsn_code || '8536',
      gst_rate: prod.gst_rate || 18.0
    });
    setFormError('');
    setModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError('');
    setLoading(true);

    try {
      const payload = {
        name: formData.name.trim(),
        category: formData.category,
        price: parseFloat(formData.price),
        quantity: parseInt(formData.quantity, 10),
        min_stock_level: parseInt(formData.min_stock_level, 10),
        supplier_id: formData.supplier_id || undefined,
        hsn_code: formData.hsn_code || '8536',
        gst_rate: parseFloat(formData.gst_rate) || 18.0
      };

      if (editingProduct) {
        await api.updateProduct(editingProduct.id, payload);
        setFeedback({ type: 'success', message: `Product '${payload.name}' updated successfully.` });
      } else {
        await api.createProduct(payload);
        setFeedback({ type: 'success', message: `Product '${payload.name}' created successfully.` });
      }
      setModalOpen(false);
      onRefresh();
      setTimeout(() => setFeedback({ type: '', message: '' }), 4000);
    } catch (err) {
      setFormError(err.message || 'Failed to save product');
    } finally {
      setLoading(false);
    }
  };

  const handleRequestDelete = (prod) => {
    setDeletingProduct(prod);
  };

  const handleConfirmDelete = async () => {
    if (!deletingProduct) return;
    setDeleteLoading(true);
    try {
      const res = await api.deleteProduct(deletingProduct.id);
      setFeedback({
        type: 'success',
        message: res.message || `Product '${deletingProduct.name}' deactivated successfully.`
      });
      setDeletingProduct(null);
      onRefresh();
      setTimeout(() => setFeedback({ type: '', message: '' }), 4000);
    } catch (err) {
      setFeedback({
        type: 'error',
        message: err.message || 'Error deactivating product'
      });
    } finally {
      setDeleteLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Top Header & Actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flex: 1, minWidth: '280px' }}>
          {/* Search Box */}
          <div style={{ position: 'relative', flex: 1, maxWidth: '360px' }}>
            <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input
              id="product-search-input"
              type="text"
              className="form-input"
              style={{ paddingLeft: '2.4rem' }}
              placeholder="Search by name or product ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          {/* Category Filter */}
          <select
            id="product-category-filter"
            className="form-select"
            style={{ maxWidth: '200px' }}
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
          >
            {categories.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        {/* Add Product Button (Admin Only) */}
        {user?.role === 'Admin' && (
          <button id="btn-open-add-product" onClick={handleOpenAdd} className="btn btn-primary">
            <Plus size={16} />
            <span>Add Product</span>
          </button>
        )}
      </div>

      {/* Staff Notice if in Staff Role */}
      {user?.role !== 'Admin' && (
        <div style={{
          padding: '0.75rem 1rem',
          borderRadius: 'var(--radius-md)',
          background: 'rgba(6, 182, 212, 0.1)',
          border: '1px solid rgba(6, 182, 212, 0.3)',
          color: 'var(--info)',
          fontSize: '0.85rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          <ShieldAlert size={16} />
          <span><strong>Staff Operational Mode:</strong> You are viewing the product catalogue in read-only mode. Adding new SKUs, editing attributes, and deactivating products require Administrator privileges.</span>
        </div>
      )}

      {/* Feedback Banner */}
      {feedback.message && (
        <div style={{
          padding: '0.75rem 1rem',
          borderRadius: 'var(--radius-md)',
          background: feedback.type === 'success' ? 'var(--success-bg)' : 'var(--danger-bg)',
          border: `1px solid ${feedback.type === 'success' ? 'rgba(16, 185, 129, 0.4)' : 'rgba(239, 68, 68, 0.4)'}`,
          color: feedback.type === 'success' ? 'var(--success)' : 'var(--danger)',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          fontSize: '0.85rem'
        }}>
          {feedback.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
          <span>{feedback.message}</span>
        </div>
      )}

      {/* Products Table */}
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>SKU / ID</th>
              <th>Product Name</th>
              <th>Category</th>
              <th>Unit Price (₹)</th>
              <th>Stock</th>
              <th>Min Threshold</th>
              <th>GST Rate</th>
              <th>Default Supplier</th>
              {user?.role === 'Admin' && <th style={{ textAlign: 'right' }}>Actions</th>}
            </tr>
          </thead>
          <tbody>
            {filteredProducts.map((p) => {
              let badge = 'badge-in-stock';
              if (p.quantity === 0) badge = 'badge-out-of-stock';
              else if (p.quantity <= p.min_stock_level) badge = 'badge-low-stock';

              return (
                <tr key={p.id}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    {p.id}
                  </td>
                  <td>
                    <div style={{ fontWeight: 700 }}>{p.name}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>HSN: {p.hsn_code || '8536'}</div>
                  </td>
                  <td>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                      {p.category}
                    </span>
                  </td>
                  <td style={{ fontWeight: 700 }}>{formatINR(p.price)}</td>
                  <td>
                    <span className={`badge ${badge}`}>
                      {p.quantity} units
                    </span>
                  </td>
                  <td style={{ color: 'var(--text-muted)' }}>{p.min_stock_level} units</td>
                  <td><span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>{p.gst_rate || 18}%</span></td>
                  <td style={{ color: 'var(--text-secondary)' }}>{p.supplier_name || '—'}</td>
                  {user?.role === 'Admin' && (
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: '0.5rem' }}>
                        <button
                          id={`btn-edit-product-${p.id}`}
                          onClick={() => handleOpenEdit(p)}
                          className="btn btn-secondary btn-sm"
                          title="Edit Product"
                        >
                          <Edit size={14} />
                        </button>
                        <button
                          id={`btn-delete-product-${p.id}`}
                          onClick={() => handleRequestDelete(p)}
                          className="btn btn-danger btn-sm"
                          title="Deactivate Product"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  )}
                </tr>
              );
            })}
            {filteredProducts.length === 0 && (
              <tr>
                <td colSpan={user?.role === 'Admin' ? 9 : 8} style={{ textAlign: 'center', padding: '3rem 1.5rem', color: 'var(--text-muted)' }}>
                  {products.length === 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.75rem' }}>
                      <AlertCircle size={32} style={{ color: 'var(--text-muted)' }} />
                      <div style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        No Products Currently Loaded
                      </div>
                      <div style={{ fontSize: '0.85rem', maxWidth: '400px', color: 'var(--text-secondary)' }}>
                        The catalog has no active products loaded in memory. Click the button below to synchronize with the local database.
                      </div>
                      {onRefresh && (
                        <button
                          type="button"
                          id="btn-retry-catalog-sync"
                          onClick={onRefresh}
                          className="btn btn-secondary"
                          style={{ marginTop: '0.5rem' }}
                        >
                          Synchronize Catalog Now
                        </button>
                      )}
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.75rem' }}>
                      <Search size={32} style={{ color: 'var(--text-muted)' }} />
                      <div style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        No products found matching your search and filter criteria.
                      </div>
                      <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        No products match your search term "{searchTerm}" and category "{categoryFilter}".
                      </div>
                      <button
                        type="button"
                        id="btn-clear-catalog-filters"
                        onClick={() => { setSearchTerm(''); setCategoryFilter('ALL'); }}
                        className="btn btn-secondary btn-sm"
                        style={{ marginTop: '0.5rem' }}
                      >
                        Clear Search & Filter
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Add / Edit Product Modal */}
      {modalOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3 style={{ fontSize: '1.1rem', fontWeight: 800 }}>
                {editingProduct ? 'Edit Catalog Product' : 'Add New Indian SKU'}
              </h3>
              <button
                id="btn-close-product-modal"
                onClick={() => setModalOpen(false)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="modal-body">
                {formError && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'var(--danger-bg)', color: 'var(--danger)', padding: '0.75rem', borderRadius: 'var(--radius-md)', marginBottom: '1rem', fontSize: '0.85rem' }}>
                    <AlertCircle size={16} />
                    <span>{formError}</span>
                  </div>
                )}

                <div className="form-group">
                  <label className="form-label">Product Name *</label>
                  <input
                    id="prod-name"
                    type="text"
                    required
                    className="form-input"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g. Havells Industrial LED High-Bay 100W"
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div className="form-group">
                    <label className="form-label">Category *</label>
                    <select
                      className="form-select"
                      value={formData.category}
                      onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    >
                      {INDIAN_PRODUCT_CATEGORIES.map(c => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Unit Price (₹ INR) *</label>
                    <input
                      id="prod-price"
                      type="number"
                      step="0.01"
                      min="0.01"
                      required
                      className="form-input"
                      value={formData.price}
                      onChange={(e) => setFormData({ ...formData, price: e.target.value })}
                    />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div className="form-group">
                    <label className="form-label">Initial Physical Stock *</label>
                    <input
                      id="prod-qty"
                      type="number"
                      min="0"
                      required
                      className="form-input"
                      value={formData.quantity}
                      onChange={(e) => setFormData({ ...formData, quantity: e.target.value })}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Minimum Stock Threshold *</label>
                    <input
                      id="prod-min-qty"
                      type="number"
                      min="0"
                      required
                      className="form-input"
                      value={formData.min_stock_level}
                      onChange={(e) => setFormData({ ...formData, min_stock_level: e.target.value })}
                    />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div className="form-group">
                    <label className="form-label">HSN Code</label>
                    <input
                      type="text"
                      className="form-input"
                      value={formData.hsn_code}
                      onChange={(e) => setFormData({ ...formData, hsn_code: e.target.value })}
                      placeholder="e.g. 8536"
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Applicable GST Rate (%)</label>
                    <select
                      className="form-select"
                      value={formData.gst_rate}
                      onChange={(e) => setFormData({ ...formData, gst_rate: e.target.value })}
                    >
                      <option value="5.0">5% (Essential Goods)</option>
                      <option value="12.0">12% (Standard Low)</option>
                      <option value="18.0">18% (Standard Electronics/Electrical)</option>
                      <option value="28.0">28% (Luxury / High Power)</option>
                    </select>
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Default Supplier</label>
                  <select
                    className="form-select"
                    value={formData.supplier_id}
                    onChange={(e) => setFormData({ ...formData, supplier_id: e.target.value })}
                  >
                    <option value="">— Select Supplier —</option>
                    {suppliers.map(s => (
                      <option key={s.id} value={s.id}>{s.name} ({s.contact_person})</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="modal-footer">
                <button
                  id="btn-cancel-product"
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  id="btn-submit-product"
                  type="submit"
                  disabled={loading}
                  className="btn btn-primary"
                >
                  {loading ? 'Saving...' : editingProduct ? 'Update Product' : 'Create Product'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deletingProduct && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '460px' }}>
            <div className="modal-header">
              <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--danger)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <AlertCircle size={20} />
                <span>Confirm Product Deactivation</span>
              </h3>
              <button
                id="btn-close-delete-modal"
                onClick={() => setDeletingProduct(null)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>
            <div className="modal-body">
              <p style={{ fontSize: '0.9rem', color: 'var(--text-primary)', marginBottom: '0.75rem' }}>
                Are you sure you want to deactivate <strong>{deletingProduct.name}</strong> (<span style={{ fontFamily: 'var(--font-mono)' }}>{deletingProduct.id}</span>)?
              </p>
              <div style={{
                background: 'rgba(239, 68, 68, 0.08)',
                border: '1px solid rgba(239, 68, 68, 0.25)',
                borderRadius: 'var(--radius-md)',
                padding: '0.75rem',
                fontSize: '0.8rem',
                color: 'var(--text-secondary)'
              }}>
                This SKU will be hidden from the active catalog and inventory operations. All historical procurement batches and sales transactions referencing this SKU will remain completely preserved in the ledger.
              </div>
            </div>
            <div className="modal-footer">
              <button
                id="btn-cancel-delete-product"
                type="button"
                onClick={() => setDeletingProduct(null)}
                disabled={deleteLoading}
                className="btn btn-secondary"
              >
                Cancel
              </button>
              <button
                id="btn-confirm-delete-product"
                type="button"
                onClick={handleConfirmDelete}
                disabled={deleteLoading}
                className="btn btn-danger"
              >
                {deleteLoading ? 'Deactivating...' : 'Confirm Deactivation'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

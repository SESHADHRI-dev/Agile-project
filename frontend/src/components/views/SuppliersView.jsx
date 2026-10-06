import React, { useState } from 'react';
import { Plus, Search, Edit, Trash2, X, Phone, Mail, MapPin, AlertCircle, Building2, CheckCircle2, ShieldAlert } from 'lucide-react';
import { api } from '../../api';
import { INDIAN_STATES, formatIndianPhone, isValidIndianPhone } from '../../utils/formatters';

export default function SuppliersView({ suppliers = [], onRefresh, user }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingSupplier, setEditingSupplier] = useState(null);
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState('');

  // Delete Confirmation Modal State
  const [deletingSupplier, setDeletingSupplier] = useState(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [feedback, setFeedback] = useState({ type: '', message: '' });

  const [formData, setFormData] = useState({
    name: '',
    contact_person: '',
    phone: '',
    email: '',
    address: '',
    state: 'Tamil Nadu',
    pin_code: '632007',
    gstin: '',
    supplied_categories: 'Electrical Components, Hardware'
  });

  const filteredSuppliers = suppliers.filter((s) => {
    return s.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
           s.contact_person.toLowerCase().includes(searchTerm.toLowerCase()) ||
           (s.address && s.address.toLowerCase().includes(searchTerm.toLowerCase())) ||
           (s.state && s.state.toLowerCase().includes(searchTerm.toLowerCase())) ||
           s.email.toLowerCase().includes(searchTerm.toLowerCase());
  });

  const handleOpenAdd = () => {
    setEditingSupplier(null);
    setFormData({
      name: '',
      contact_person: '',
      phone: '',
      email: '',
      address: '',
      state: 'Tamil Nadu',
      pin_code: '632007',
      gstin: '',
      supplied_categories: 'Electrical Components, Hardware'
    });
    setFormError('');
    setModalOpen(true);
  };

  const handleOpenEdit = (sup) => {
    setEditingSupplier(sup);
    setFormData({
      name: sup.name,
      contact_person: sup.contact_person,
      phone: sup.phone,
      email: sup.email,
      address: sup.address,
      state: sup.state || 'Tamil Nadu',
      pin_code: sup.pin_code || '632007',
      gstin: sup.gstin || '',
      supplied_categories: sup.supplied_categories || 'General'
    });
    setFormError('');
    setModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError('');

    if (formData.pin_code && !/^[1-9][0-9]{5}$/.test(formData.pin_code.trim())) {
      setFormError('Please enter a valid 6-digit Indian PIN code (e.g., 632007).');
      return;
    }

    setLoading(true);

    try {
      if (editingSupplier) {
        await api.updateSupplier(editingSupplier.id, formData);
        setFeedback({ type: 'success', message: `Supplier '${formData.name}' updated successfully.` });
      } else {
        await api.createSupplier(formData);
        setFeedback({ type: 'success', message: `Supplier '${formData.name}' registered successfully.` });
      }
      setModalOpen(false);
      onRefresh();
      setTimeout(() => setFeedback({ type: '', message: '' }), 4000);
    } catch (err) {
      setFormError(err.message || 'Failed to save supplier');
    } finally {
      setLoading(false);
    }
  };

  const handleRequestDelete = (sup) => {
    setDeletingSupplier(sup);
  };

  const handleConfirmDelete = async () => {
    if (!deletingSupplier) return;
    setDeleteLoading(true);
    try {
      const res = await api.deleteSupplier(deletingSupplier.id);
      setFeedback({
        type: 'success',
        message: res.message || `Supplier '${deletingSupplier.name}' deactivated successfully.`
      });
      setDeletingSupplier(null);
      onRefresh();
      setTimeout(() => setFeedback({ type: '', message: '' }), 4000);
    } catch (err) {
      setFeedback({
        type: 'error',
        message: err.message || 'Error deactivating supplier'
      });
    } finally {
      setDeleteLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Top Action Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ position: 'relative', width: '100%', maxWidth: '380px' }}>
          <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input
            id="input-supplier-search"
            type="text"
            className="form-input"
            style={{ paddingLeft: '2.4rem' }}
            placeholder="Search suppliers by name, city, contact..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        {user?.role === 'Admin' && (
          <button id="btn-add-supplier" onClick={handleOpenAdd} className="btn btn-primary">
            <Plus size={16} />
            <span>Add Indian Supplier</span>
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
          <span><strong>Staff Operational Mode:</strong> Supplier directory is in read-only mode for Staff. Registering new procurement vendors or deactivating suppliers requires Administrator credentials.</span>
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

      {/* Suppliers Grid / Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))',
        gap: '1.25rem'
      }}>
        {filteredSuppliers.map((sup) => (
          <div key={sup.id} className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {sup.id}
                </span>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 800, marginTop: '0.2rem' }}>{sup.name}</h3>
                <span style={{ fontSize: '0.8rem', color: 'var(--accent-primary)', fontWeight: 600 }}>
                  Contact: {sup.contact_person}
                </span>
              </div>
              {user?.role === 'Admin' && (
                <div style={{ display: 'flex', gap: '0.35rem' }}>
                  <button
                    id={`btn-edit-supplier-${sup.id}`}
                    onClick={() => handleOpenEdit(sup)}
                    className="btn btn-secondary btn-sm"
                    title="Edit"
                  >
                    <Edit size={14} />
                  </button>
                  <button
                    id={`btn-delete-supplier-${sup.id}`}
                    onClick={() => handleRequestDelete(sup)}
                    className="btn btn-danger btn-sm"
                    title="Deactivate Supplier"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              )}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Phone size={14} color="var(--text-muted)" />
                <span style={{ fontFamily: 'var(--font-mono)' }}>{formatIndianPhone(sup.phone)}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Mail size={14} color="var(--text-muted)" />
                <span>{sup.email}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem' }}>
                <MapPin size={14} color="var(--text-muted)" style={{ marginTop: '0.2rem', flexShrink: 0 }} />
                <span>{sup.address}, {sup.state} - {sup.pin_code}</span>
              </div>
            </div>

            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              paddingTop: '0.75rem',
              borderTop: '1px solid var(--border-color)',
              fontSize: '0.75rem'
            }}>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>GSTIN: </span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{sup.gstin || 'Unregistered'}</span>
              </div>
              <span className="badge badge-info" style={{ fontSize: '0.7rem' }}>
                {sup.supplied_categories || 'Electrical'}
              </span>
            </div>
          </div>
        ))}

        {filteredSuppliers.length === 0 && (
          <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
            No suppliers found matching your search.
          </div>
        )}
      </div>

      {/* Add / Edit Supplier Modal */}
      {modalOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3 style={{ fontSize: '1.1rem', fontWeight: 800 }}>
                {editingSupplier ? 'Edit Indian Supplier' : 'Register New Indian Supplier'}
              </h3>
              <button
                id="btn-close-supplier-modal"
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
                  <label className="form-label">Business / Enterprise Name *</label>
                  <input
                    id="supplier-input-name"
                    type="text"
                    required
                    className="form-input"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g. Sri Lakshmi Electricals & Co."
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div className="form-group">
                    <label className="form-label">Contact Person *</label>
                    <input
                      id="supplier-input-contact"
                      type="text"
                      required
                      className="form-input"
                      value={formData.contact_person}
                      onChange={(e) => setFormData({ ...formData, contact_person: e.target.value })}
                      placeholder="e.g. R. Subramanian"
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Indian Phone (+91) *</label>
                    <input
                      id="supplier-input-phone"
                      type="tel"
                      required
                      className="form-input"
                      value={formData.phone}
                      onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                      placeholder="e.g. +91 98401 23456"
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Email Address *</label>
                  <input
                    id="supplier-input-email"
                    type="email"
                    required
                    className="form-input"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    placeholder="e.g. contact@srilakshmielectricals.in"
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Physical Address</label>
                  <input
                    id="supplier-input-address"
                    type="text"
                    className="form-input"
                    value={formData.address}
                    onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                    placeholder="e.g. 142 Anna Salai, Guindy Industrial Estate"
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1rem' }}>
                  <div className="form-group">
                    <label className="form-label">State / UT (Determines GST: CGST+SGST vs IGST)</label>
                    <select
                      id="supplier-select-state"
                      className="form-select"
                      value={formData.state}
                      onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                    >
                      {INDIAN_STATES.map(st => (
                        <option key={st} value={st}>{st}</option>
                      ))}
                    </select>
                  </div>

                  <div className="form-group">
                    <label className="form-label">6-Digit PIN Code</label>
                    <input
                      id="supplier-input-pincode"
                      type="text"
                      maxLength="6"
                      className="form-input"
                      value={formData.pin_code}
                      onChange={(e) => setFormData({ ...formData, pin_code: e.target.value })}
                      placeholder="632007"
                    />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div className="form-group">
                    <label className="form-label">Supplier GSTIN (15 Alphanumeric)</label>
                    <input
                      id="supplier-input-gstin"
                      type="text"
                      maxLength="15"
                      className="form-input"
                      value={formData.gstin}
                      onChange={(e) => setFormData({ ...formData, gstin: e.target.value.toUpperCase() })}
                      placeholder="e.g. 33AAAAA0000A1Z5"
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Supplied Categories</label>
                    <input
                      id="supplier-input-categories"
                      type="text"
                      className="form-input"
                      value={formData.supplied_categories}
                      onChange={(e) => setFormData({ ...formData, supplied_categories: e.target.value })}
                      placeholder="e.g. Electrical Components, Hardware"
                    />
                  </div>
                </div>
              </div>

              <div className="modal-footer">
                <button
                  id="btn-cancel-supplier"
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  id="btn-submit-supplier"
                  type="submit"
                  disabled={loading}
                  className="btn btn-primary"
                >
                  {loading ? 'Saving...' : editingSupplier ? 'Update Supplier' : 'Save Supplier'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deletingSupplier && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: '460px' }}>
            <div className="modal-header">
              <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--danger)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <AlertCircle size={20} />
                <span>Confirm Supplier Deactivation</span>
              </h3>
              <button
                id="btn-close-delete-supplier-modal"
                onClick={() => setDeletingSupplier(null)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>
            <div className="modal-body">
              <p style={{ fontSize: '0.9rem', color: 'var(--text-primary)', marginBottom: '0.75rem' }}>
                Are you sure you want to deactivate <strong>{deletingSupplier.name}</strong> (<span style={{ fontFamily: 'var(--font-mono)' }}>{deletingSupplier.id}</span>)?
              </p>
              <div style={{
                background: 'rgba(239, 68, 68, 0.08)',
                border: '1px solid rgba(239, 68, 68, 0.25)',
                borderRadius: 'var(--radius-md)',
                padding: '0.75rem',
                fontSize: '0.8rem',
                color: 'var(--text-secondary)'
              }}>
                This supplier will be removed from future inbound purchase options. All existing purchase transaction history and GST invoices referencing this supplier will remain completely intact in the ledger.
              </div>
            </div>
            <div className="modal-footer">
              <button
                id="btn-cancel-delete-supplier"
                type="button"
                onClick={() => setDeletingSupplier(null)}
                disabled={deleteLoading}
                className="btn btn-secondary"
              >
                Cancel
              </button>
              <button
                id="btn-confirm-delete-supplier"
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

import React, { useState, useEffect } from 'react';
import { FileText, Download, FileSpreadsheet, CheckCircle2, TrendingUp, IndianRupee, AlertCircle } from 'lucide-react';
import { api } from '../../api';
import { formatINR } from '../../utils/formatters';

export default function ReportsView() {
  const [summary, setSummary] = useState(null);
  const [downloading, setDownloading] = useState('');
  const [feedback, setFeedback] = useState({ type: '', message: '' });

  const timerRef = React.useRef(null);

  useEffect(() => {
    api.getReportsSummary().then(setSummary).catch(console.error);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const handleDownload = async (reportType, format = 'csv') => {
    const actionKey = `${reportType}-${format}`;
    if (timerRef.current) clearTimeout(timerRef.current);
    setDownloading(actionKey);
    setFeedback({ type: '', message: '' });

    try {
      const blob = await api.downloadReport(reportType, format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const ext = (format === 'excel' || format === 'xlsx') ? 'xlsx' : format;
      const dateStr = new Date().toISOString().slice(0, 10);
      a.download = `report_${reportType}_${dateStr}.${ext}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      setFeedback({
        type: 'success',
        message: `Generated and downloaded ${reportType.toUpperCase()} report in ${ext.toUpperCase()} format successfully.`
      });
      timerRef.current = setTimeout(() => setFeedback({ type: '', message: '' }), 4000);
    } catch (err) {
      setFeedback({
        type: 'error',
        message: err.message || `Failed to generate ${format.toUpperCase()} report`
      });
    } finally {
      setDownloading('');
    }
  };

  const reportsList = [
    {
      id: 'inventory',
      title: 'Current Inventory Valuation Report',
      description: 'Comprehensive audit of all warehouse SKUs, holding values, HSN codes, and current stock status in INR.',
      filenamePattern: 'report_inventory_*.{xlsx, pdf, csv}'
    },
    {
      id: 'low_stock',
      title: 'Low-Stock & Deficit Alert Audit',
      description: 'Isolates all products whose current balance is at or below configured minimum reorder threshold.',
      filenamePattern: 'report_low_stock_*.{xlsx, pdf, csv}'
    },
    {
      id: 'sales',
      title: 'Historical Sales Transaction Ledger',
      description: 'Complete record of customer transactions, GST tax breakdowns (CGST/SGST/IGST), and Indian buyer records.',
      filenamePattern: 'report_sales_*.{xlsx, pdf, csv}'
    },
    {
      id: 'purchases',
      title: 'Supplier Purchase & Inbound Ledger',
      description: 'Inbound replenishment batches, Tamil Nadu supplier references, GSTINs, and unit acquisition costs in INR.',
      filenamePattern: 'report_purchases_*.{xlsx, pdf, csv}'
    },
    {
      id: 'predictions',
      title: 'Demand Prediction & Restock Analysis',
      description: 'Forecasting output, daily sales velocities, safety stock buffers, and recommended replenishment orders.',
      filenamePattern: 'report_predictions_*.{xlsx, pdf, csv}'
    }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div>
        <h2 style={{ fontSize: '1.1rem', fontWeight: 800 }}>Audit Reports & Data Export Center</h2>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          Export multi-format audit datasets as Excel (.xlsx), PDF, or CSV for executive presentations, BI dashboards, or cloud archival. Localized for IntelliStock India (Katpadi, Vellore, TN).
        </p>
      </div>

      {/* Feedback Alert */}
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

      {/* KPI Overview */}
      {summary && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '1rem'
        }}>
          <div className="glass-card" style={{ padding: '1rem' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>TOTAL REVENUE LOGGED</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--success)' }}>
              {formatINR(summary.total_sales_revenue)}
            </div>
          </div>

          <div className="glass-card" style={{ padding: '1rem' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>TOTAL PROCUREMENT SPEND</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 800 }}>
              {formatINR(summary.total_purchase_spend)}
            </div>
          </div>

          <div className="glass-card" style={{ padding: '1rem' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>CURRENT ASSET VALUATION</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--accent-primary)' }}>
              {formatINR(summary.total_inventory_value)}
            </div>
          </div>
        </div>
      )}

      {/* Reports Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))',
        gap: '1.25rem'
      }}>
        {reportsList.map((rep) => {
          const isDownloadingExcel = downloading === `${rep.id}-xlsx`;
          const isDownloadingPdf = downloading === `${rep.id}-pdf`;
          const isDownloadingCsv = downloading === `${rep.id}-csv`;

          return (
            <div key={rep.id} className="glass-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '1.25rem' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                  <div style={{
                    padding: '0.4rem',
                    borderRadius: '8px',
                    background: 'rgba(59, 130, 246, 0.15)',
                    color: 'var(--accent-primary)'
                  }}>
                    <FileText size={18} />
                  </div>
                  <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>{rep.title}</h3>
                </div>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  {rep.description}
                </p>
                <div style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.725rem',
                  color: 'var(--text-muted)',
                  marginTop: '0.75rem'
                }}>
                  Formats: Excel (.xlsx), PDF (.pdf), CSV (.csv)
                </div>
              </div>

              {/* Action Buttons: Excel, PDF, CSV */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                  {/* Excel Button */}
                  <button
                    id={`btn-download-excel-${rep.id}`}
                    onClick={() => handleDownload(rep.id, 'xlsx')}
                    disabled={!!downloading}
                    className="btn btn-primary btn-sm"
                    style={{ justifyContent: 'center' }}
                  >
                    <FileSpreadsheet size={14} />
                    <span>{isDownloadingExcel ? 'Exporting...' : 'Excel (.xlsx)'}</span>
                  </button>

                  {/* PDF Button */}
                  <button
                    id={`btn-download-pdf-${rep.id}`}
                    onClick={() => handleDownload(rep.id, 'pdf')}
                    disabled={!!downloading}
                    className="btn btn-secondary btn-sm"
                    style={{ justifyContent: 'center' }}
                  >
                    <FileText size={14} />
                    <span>{isDownloadingPdf ? 'Generating...' : 'PDF (.pdf)'}</span>
                  </button>
                </div>

                {/* CSV Button */}
                <button
                  id={`btn-download-report-${rep.id}`}
                  onClick={() => handleDownload(rep.id, 'csv')}
                  disabled={!!downloading}
                  className="btn btn-secondary btn-sm"
                  style={{ justifyContent: 'center', opacity: 0.85 }}
                >
                  <Download size={14} />
                  <span>{isDownloadingCsv ? 'Generating...' : 'CSV (.csv)'}</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

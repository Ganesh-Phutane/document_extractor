/**
 * pages/MasterDataPage.jsx
 * ─────────────────────────
 * Master Data page — shows a KPI table with multi-period matrix view.
 */
import React, { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import {
  ArrowLeft,
  BarChart3,
  XCircle,
  AlertTriangle,
  RefreshCw,
  ThumbsUp,
  TrendingUp,
  ChevronDown,
  ChevronUp,
  X,
  MousePointerClick,
  CheckCircle2,
  Database,
  Plus,
  Sparkles,
  Settings,
} from "lucide-react";
import { processMasterData, getMasterData, approveMasterData } from "../api/masterData";
import { getExtractionResult } from "../api/extractions";
import { getFieldTrace } from "../api/trace";
import DocumentViewer from "../components/DocumentViewer";
import ValidationReview from "../components/ValidationReview"; // NEW
import "../styles/pages/MasterData.css";

// ── KPI fields (dedicated table) ────────────────────────────
const KPI_FIELDS = [
  { id: "company_name", label: "Company Name", color: "#a5b4fc" },
  { id: "period_row",   label: "Period",       color: "#94a3b8" },
  { id: "frequency",    label: "Frequency",    color: "#818cf8" },
  { id: "gross_sales",  label: "Gross Sales",  color: "#6366f1" },
  { id: "ebita",        label: "EBITDA",        color: "#8b5cf6" },
  { id: "net_revenue",  label: "Net Revenue",   color: "#06b6d4" },
  { id: "gross_profit", label: "Gross Profit",  color: "#10b981" },
  { id: "total_debt",   label: "Total Debt",    color: "#f59e0b" },
];

const MasterDataPage = () => {
  const { documentId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  const [masterData, setMasterData]       = useState(null);
  const [pageState, setPageState]         = useState("loading"); // loading|idle|data|processing|error
  const [processError, setProcessError]   = useState(null);
  const [approving, setApproving]         = useState(false);
  const [showRaw, setShowRaw]             = useState(false);
  const [toast, setToast]                 = useState(null);
  const [extraColumns, setExtraColumns]   = useState(""); // comma-separated field names

  const [extractionMeta, setExtractionMeta] = useState(null);
  const [viewerOpen, setViewerOpen]       = useState(false);
  const [activeHighlight, setActiveHighlight] = useState(null);
  const [activeRowId, setActiveRowId]     = useState(null);
  const [showConfigModal, setShowConfigModal] = useState(false);

  const showToast = useCallback((msg, type = "success") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3500);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [masterResult, extractResult] = await Promise.allSettled([
        getMasterData(documentId),
        getExtractionResult(documentId),
      ]);
      if (cancelled) return;

      if (extractResult.status === "fulfilled") {
        const e = extractResult.value;
        setExtractionMeta({
          extraction_id: e.extraction_id,
          document_url:  e.document_url,
          doc_type:      e.doc_type,
          filename:      e.filename,
        });
      }

      if (masterResult.status === "fulfilled") {
        setMasterData(masterResult.value);
        setPageState("data");
      } else {
        const status = masterResult.reason?.response?.status;
        if (status === 404) setPageState("idle");
        else {
          setProcessError(masterResult.reason?.response?.data?.detail || "Failed to load.");
          setPageState("error");
        }
      }
    })();
    return () => { cancelled = true; };
  }, [documentId]);

  const refreshData = async () => {
    try {
      const refresh = await getMasterData(documentId);
      setMasterData(refresh);
    } catch (err) {
      console.error("Failed to refresh data", err);
    }
  };

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (params.get("autoprocess") === "true" && pageState === "idle") {
      setShowConfigModal(true); // Open modal instead of processing directly
    }
  }, [pageState]);

  const handleProcess = async () => {
    setShowConfigModal(false); // Close modal before starting
    setPageState("processing");
    setProcessError(null);
    try {
      const result = await processMasterData(documentId, extraColumns);
      setMasterData(result);
      setPageState("data");
      showToast("Master data extracted successfully!");
    } catch (err) {
      setProcessError(err?.response?.data?.detail || "Processing failed.");
      setPageState("error");
    }
  };

  const handleApprove = async () => {
    setApproving(true);
    try {
      if (!masterData) return;
      await approveMasterData(documentId);
      const refresh = await getMasterData(documentId);
      setMasterData(refresh);
      showToast("Record approved.", "success");
    } catch (err) {
      showToast("Approval failed.", "error");
    } finally {
      setApproving(false);
    }
  };

  const handleRowClick = useCallback(async (fieldId, fieldValue, period) => {
    // Skip trace for metadata rows unless it's a KPI cell
    if (!extractionMeta?.extraction_id && !masterData?.extraction_id) return;
    
    // Prioritize the extraction_id from master data (the shadow one)
    const traceId = masterData?.extraction_id || extractionMeta?.extraction_id;
    if (!traceId) return;

    setActiveRowId(`${fieldId}-${period}`);
    
    // Construct path: either financials.gross_sales.FY 2024 OR extra_fields.field.FY 2024
    const path = fieldId.startsWith('extra_fields') 
      ? `${fieldId}.${period}` 
      : `financials.${fieldId}.${period}`;

    try {
      const trace = await getFieldTrace(traceId, path);
      if (trace && trace.trace_found !== false) {
        setActiveHighlight(trace);
        setViewerOpen(true);
      } else {
        setActiveHighlight({ trace_found: false, matched_text: String(fieldValue ?? "") });
        setViewerOpen(true);
      }
    } catch (e) {
      setViewerOpen(true);
    }
  }, [extractionMeta, masterData]);

  const handleCancel = () => {
    // If we have no data, cancellation should send us back to the list
    if (pageState === "idle" || pageState === "error") {
      navigate("/master");
    } else {
      setShowConfigModal(false);
    }
  };

  const isProcessing = pageState === "processing";
  const hasData      = pageState === "data" && masterData;
  const confidence   = masterData?.confidence_score ?? 0;
  const confColor    = confidence >= 80 ? "#10b981" : confidence >= 50 ? "#f59e0b" : "#ef4444";

  if (pageState === "loading") {
    return (
      <div className="md-page-root">
        <div className="md-main-pane" style={{ justifyContent: 'center', alignItems: 'center' }}>
          <div className="md-spinner" />
          <p style={{ marginTop: '1rem', color: '#64748b', fontSize: '0.85rem' }}>Preparing extraction dashboard...</p>
        </div>
      </div>
    );
  }

  // Hide the background if we're auto-showing the modal on an empty doc
  const hideBackground = showConfigModal && !hasData;

  return (
    <div className={`md-page-root ${viewerOpen ? "md-split" : ""}`}>
      <div 
        className="md-main-pane custom-scrollbar" 
        style={{ 
          opacity: hideBackground ? 0 : 1,
          pointerEvents: hideBackground ? 'none' : 'auto',
          transition: 'opacity 0.2s ease'
        }}
      >
        <div className="md-page-header">
          <button className="md-btn-back" onClick={() => navigate("/master")}>
            <ArrowLeft size={16} />
          </button>
          <div className="md-header-info">
            <BarChart3 size={18} color="#6366f1" />
            <h1>Master Data</h1>
            {extractionMeta?.filename && <span className="md-doc-chip">{extractionMeta.filename}</span>}
          </div>
          <div className="md-header-actions">
            {masterData?.confidence_score !== undefined && (
              <div className="md-confidence-box">
                <span className="md-conf-label">Confidence</span>
                <span className="md-conf-value" style={{ color: masterData.confidence_score >= 90 ? '#10b981' : '#f59e0b' }}>
                  {masterData.confidence_score}%
                </span>
              </div>
            )}

            {/* ── Extra columns input ── */}
            <div className="md-extra-input-group">
              <label htmlFor="extra-cols">Extra Columns</label>
              <input
                id="extra-cols"
                type="text"
                placeholder="e.g. Operating Income, EPS"
                value={extraColumns}
                disabled={isProcessing}
                onChange={e => setExtraColumns(e.target.value)}
                title="Enter comma-separated column names to extract specifically"
              />
            </div>

            <button
              className="md-btn-header-secondary"
              onClick={handleProcess}
              disabled={isProcessing}
            >
              <RefreshCw size={14} className={isProcessing ? "md-spin" : ""} />
              {isProcessing ? "Processing…" : hasData ? "Re-extract" : "Extract Data"}
            </button>

            {hasData && (masterData.is_approved ? (
              <span className="md-approved-badge"><CheckCircle2 size={13} /> Approved</span>
            ) : (
              <button className="md-btn-approve" onClick={handleApprove} disabled={approving}>
                <ThumbsUp size={14} /> {approving ? "Approving…" : "Approve"}
              </button>
            ))}
          </div>
        </div>

        {processError && <div className="md-error-banner"><XCircle size={14} /> {processError}</div>}

        {isProcessing && (
          <div className="md-processing-state">
            <div className="md-spinner" />
            <p>Running multi-period pipeline…</p>
          </div>
        )}

        {hasData && (
          <>
            {masterData.requires_review && !masterData.validation_status?.includes('failed') && !masterData.validation_status?.includes('conflict') && (
              <div className="md-review-banner">
                <AlertTriangle size={15} /> <strong>Requires Review</strong> — incomplete data.
              </div>
            )}

            {/* ── Validation Review Component (NEW) ── */}
            <ValidationReview 
              masterData={masterData}
              documentId={documentId}
              onResolved={refreshData}
              showToast={showToast}
            />


            {/* ── KPI TABLE (Pivot View) ── */}
            <div className="md-table-section glass">
              <div className="md-table-header">
                <h2>Financial Master Data — Pivot View</h2>
                <span className="md-trace-hint"><MousePointerClick size={12} /> Click cells to trace source</span>
              </div>
              <div className="md-table-scroll custom-scrollbar">
                <table className="md-kpi-table md-pivot-table">
                  <thead>
                    <tr>
                      <th style={{ minWidth: '140px' }}>Company</th>
                      <th style={{ minWidth: '120px' }}>Period</th>
                      <th style={{ minWidth: '100px' }}>Frequency</th>
                      {KPI_FIELDS.filter(f => !["company_name", "period_row", "frequency"].includes(f.id)).map(kpi => (
                        <th key={kpi.id} style={{ textAlign: 'right', minWidth: '130px' }}>{kpi.label}</th>
                      ))}
                      {/* Dynamic extra-field column headers */}
                      {masterData.extra_fields && Object.keys(masterData.extra_fields).map(ef => (
                        <th
                          key={ef}
                          style={{ textAlign: 'right', minWidth: '130px', opacity: 0.65, fontStyle: 'italic' }}
                          title="Dynamically discovered extra field"
                        >
                          {ef.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(() => {
                      const periods     = masterData.periods || [];
                      const financials  = masterData.financials || {};
                      const company     = masterData.company_name || "—";
                      const kpis        = KPI_FIELDS.filter(f => !["company_name", "period_row", "frequency"].includes(f.id));
                      // Collect extra field names (keys from extra_fields that are period-maps)
                      const extraFields = masterData.extra_fields || {};
                      const extraKeys   = Object.keys(extraFields);

                      if (periods.length === 0) {
                        return (
                          <tr>
                            <td colSpan={5 + kpis.length} className="md-val-null" style={{ textAlign: 'center', padding: '2rem' }}>
                              No data found.
                            </td>
                          </tr>
                        );
                      }

                      return periods.map((p) => (
                        <tr key={p} className="md-kpi-row">
                          <td className="md-cell-company">{company}</td>
                          <td className="md-cell-period">{p}</td>
                          <td className="md-cell-freq">
                            <span className={`md-frequency-badge ${(financials.frequency?.[p]?.value || masterData.frequency || "").toLowerCase()}`}>
                              {financials.frequency?.[p]?.value || masterData.frequency || "—"}
                            </span>
                          </td>
                          {kpis.map(kpi => {
                            const node = financials[kpi.id]?.[p];
                            const val  = node?.value;
                            return (
                              <td
                                key={kpi.id}
                                className={`md-value-cell cell-kpi-val ${val != null ? 'clickable' : ''}`}
                                style={{ textAlign: 'right' }}
                                onClick={() => val != null && handleRowClick(kpi.id, val, p)}
                              >
                                {val != null ? (
                                  <span className="md-val-number">
                                    {typeof val === 'number' ? val.toLocaleString("en-IN") : val}
                                  </span>
                                ) : <span className="md-val-null">—</span>}
                              </td>
                            );
                          })}
                          {/* Extra dynamic columns — one cell per field, aligned after fixed KPIs */}
                          {extraKeys.map(ef => {
                            const node = extraFields[ef]?.[p];
                            const val  = (typeof node === 'object' && node !== null && 'value' in node)
                              ? node.value
                              : node;

                            return (
                              <td
                                key={ef}
                                className={`md-value-cell cell-extra-val ${val != null ? 'clickable' : ''}`}
                                style={{ textAlign: 'right', opacity: 0.85 }}
                                onClick={() => val != null && handleRowClick(`extra_fields.${ef}`, val, p)}
                              >
                                <span className={`md-cell-value ${val === null ? 'md-val-null' : ''}`}>
                                  {val !== null ? val : "—"}
                                </span>
                              </td>
                            );
                          })}
                        </tr>
                      ));
                    })()}
                  </tbody>
                </table>
              </div>
            </div>

            <button className="md-raw-toggle" onClick={() => setShowRaw(!showRaw)}>
              {showRaw ? "Hide" : "View"} Raw JSON
            </button>
            {showRaw && <pre className="md-raw-json custom-scrollbar">{JSON.stringify(masterData, null, 2)}</pre>}
          </>
        )}

        {pageState === "idle" && !isProcessing && (
          <div className="md-idle-hint">
            <BarChart3 size={40} color="#6366f1" style={{ opacity: 0.4 }} />
            <p>No master data found. Click "Extract Data" above.</p>
          </div>
        )}
      </div>

      {viewerOpen && (
        <div className="md-viewer-pane fade-in">
          <div className="md-viewer-controls">
            <span>Source Viewer</span>
            <button className="md-btn-close-viewer" onClick={() => setViewerOpen(false)}>
              <X size={16} />
            </button>
          </div>
          <DocumentViewer
            documentId={documentId}
            fileType={extractionMeta?.doc_type}
            highlight={activeHighlight}
            externalUrl={extractionMeta?.document_url}
            filename={extractionMeta?.filename}
            hideHeader={true}
            hideBorder={true}
          />
        </div>
      )}

      {toast && <div className={`app-toast glass ${toast.type}`}>{toast.msg}</div>}

      {/* ── Extraction Configuration Modal ── */}
      {showConfigModal && (
        <div className="md-modal-overlay" onClick={handleCancel}>
          <div className="md-modal-card" onClick={e => e.stopPropagation()}>
            <header className="md-modal-header">
              <h2><Settings size={20} color="#6366f1" /> Extraction Settings</h2>
              <button className="md-btn-close-viewer" onClick={handleCancel}>
                <X size={18} />
              </button>
            </header>
            
            <div className="md-modal-body custom-scrollbar">
              <span className="md-modal-section-title">Predefined Data Points</span>
              <div className="md-predefined-grid">
                {KPI_FIELDS.map(f => (
                  <div key={f.id} className="md-predefined-item">
                    <div className="md-predefined-label">
                      <Database size={14} color={f.color} />
                      <span>{f.label}</span>
                    </div>
                    <span className="md-predefined-tag">Default</span>
                  </div>
                ))}
              </div>

              <div className="md-modal-extra-section">
                <div className="md-modal-extra-label">
                  <Plus size={16} color="#6366f1" />
                  <span>Custom Extraction Fields</span>
                </div>
                <input
                  type="text"
                  className="md-modal-extra-input"
                  placeholder="e.g. Operating Income, Net Margin, Debt Ratio..."
                  value={extraColumns}
                  onChange={e => setExtraColumns(e.target.value)}
                  autoFocus
                />
                <p style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.75rem', lineHeight: '1.4' }}>
                  Enter additional fields separated by commas. Gemini will attempt to locate and extract these specifically for all periods.
                </p>
              </div>
            </div>

            <footer className="md-modal-footer">
              <button className="md-modal-btn-cancel" onClick={handleCancel}>
                Cancel
              </button>
              <button className="md-modal-btn-start" onClick={handleProcess}>
                <Sparkles size={16} /> Start Extraction
              </button>
            </footer>
          </div>
        </div>
      )}
    </div>
  );
};

export default MasterDataPage;

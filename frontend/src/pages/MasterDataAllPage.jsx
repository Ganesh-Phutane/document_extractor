import React, { useState, useEffect } from "react";
import { 
  BarChart3, 
  Search, 
  Database,
  ArrowLeft,
  Download,
  Filter,
  MousePointerClick,
  ChevronLeft,
  ChevronRight,
  X
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { getMasterDataOnly } from "../api/masterData";
import { getFieldTrace } from "../api/trace";
import DocumentViewer from "../components/DocumentViewer";
import "../styles/pages/MasterDataAll.css";

const MasterDataAllPage = () => {
  const navigate = useNavigate();
  const [dataRecords, setDataRecords] = useState([]);
  const [loading, setLoading]         = useState(true);
  const [searchTerm, setSearchTerm]   = useState("");
  
  // Selected Record for Viewer
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [activeHighlight, setActiveHighlight] = useState(null);

  // Pagination State
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage] = useState(10);

  useEffect(() => {
    fetchData();
  }, []);

  // Reset to page 1 on search
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const data = await getMasterDataOnly();
      setDataRecords(data);
    } catch (err) {
      console.error("Failed to fetch master database:", err);
    } finally {
      setLoading(false);
    }
  };

  const filteredRecords = dataRecords.filter(r => 
    `${r.company_name} ${r.period}`.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Pagination Logic
  const indexOfLastRow = currentPage * rowsPerPage;
  const indexOfFirstRow = indexOfLastRow - rowsPerPage;
  const currentRows = filteredRecords.slice(indexOfFirstRow, indexOfLastRow);
  const totalPages = Math.ceil(filteredRecords.length / rowsPerPage);

  const paginate = (pageNumber) => setCurrentPage(pageNumber);

  const handleRowClick = (record) => {
    if (selectedRecord && selectedRecord.document_id === record.document_id) {
      setSelectedRecord(null);
      setActiveHighlight(null);
    } else {
      setSelectedRecord(record);
      setActiveHighlight(null);
    }
  };

  const handleCellClick = async (e, record, fieldId) => {
    e.stopPropagation(); // prevent row click
    
    // Select the record first if not already
    if (selectedRecord?.document_id !== record.document_id) {
      setSelectedRecord(record);
    }

    if (!record.extraction_id) return;

    // Use the period-aware path
    const path = `financials.${fieldId}.${record.period}`;

    try {
      const trace = await getFieldTrace(record.extraction_id, path);
      if (trace && trace.trace_found !== false) {
        setActiveHighlight(trace);
      } else {
        setActiveHighlight({ trace_found: false, matched_text: String(record[fieldId] ?? "") });
      }
    } catch (err) {
      console.error("Trace failed", err);
    }
  };

  if (loading) {
    return (
      <div className="mda-page-root" style={{ justifyContent: 'center', alignItems: 'center' }}>
        <div className="mda-spinner-full" />
        <p style={{ marginTop: '1rem', color: '#64748b', fontSize: '0.85rem', fontWeight: 500 }}>
          Accessing consolidated database...
        </p>
      </div>
    );
  }

  return (
    <div className={`mda-page-root fade-in ${selectedRecord ? 'mda-split' : ''}`}>
      <div className="mda-main-pane">
        <header className="mda-page-header">
          <div className="mda-header-left">
            <button className="mda-btn-back" onClick={() => navigate(-1)}>
              <ArrowLeft size={18} />
            </button>
            <div className="mda-header-info">
              <h1>All Master Data</h1>
              <div className="mda-doc-chip">Consolidated Financial Database</div>
            </div>
          </div>

          <div className="mda-header-actions">
            <div className="mda-search-wrapper glass">
              <Search size={16} />
              <input 
                type="text" 
                placeholder="Search company or period..." 
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
              />
            </div>
            <button className="mda-btn-export" onClick={() => alert("Export coming soon!")}>
              <Download size={16} />
              <span>Export CSV</span>
            </button>
          </div>
        </header>

        <section className="mda-table-section glass">
          <div className="mda-table-header">
            <h2>Financial Master Data — Consolidated Pivot View</h2>
            <div className="mda-trace-hint">
              <MousePointerClick size={12} />
              <span>Click any row to view source document</span>
            </div>
          </div>

          <div className="mda-table-scroll">
            {loading ? (
              <div className="mda-loading-state">
                <div className="mda-spinner"></div>
                <p>Accessing database records...</p>
              </div>
            ) : filteredRecords.length === 0 ? (
              <div className="mda-empty-state">
                <Filter size={44} color="var(--text-muted)" />
                <p>No master data records found matching your filters.</p>
              </div>
            ) : (
              <table className="mda-kpi-table mda-pivot-table">
                <thead>
                  <tr>
                    <th>Company</th>
                    <th>Period</th>
                    <th>Frequency</th>
                    <th className="text-right">Gross Sales</th>
                    <th className="text-right">EBITDA</th>
                    <th className="text-right">Net Revenue</th>
                    <th className="text-right">Gross Profit</th>
                    <th className="text-right">Total Debt</th>
                  </tr>
                </thead>
                <tbody>
                  {currentRows.map((r, idx) => {
                    const isActive = selectedRecord?.document_id === r.document_id;
                    return (
                      <tr 
                        key={idx} 
                        className={`mda-kpi-row standout-row ${isActive ? 'active-row' : ''}`}
                        onClick={() => handleRowClick(r)}
                      >
                        <td className="mda-cell-company">{r.company_name}</td>
                        <td className="mda-cell-period">{r.period}</td>
                        <td>
                          <span className={`mda-badge ${(r.frequency || "").toLowerCase()}`}>
                            {r.frequency}
                          </span>
                        </td>
                        <td className="text-right mda-value-cell clickable" onClick={(e) => handleCellClick(e, r, "gross_sales")}>
                          <span className="mda-val-number">{r.gross_sales?.toLocaleString("en-IN") || "—"}</span>
                        </td>
                        <td className="text-right mda-value-cell clickable" onClick={(e) => handleCellClick(e, r, "ebita")}>
                          <span className="mda-val-number">{r.ebita?.toLocaleString("en-IN") || "—"}</span>
                        </td>
                        <td className="text-right mda-value-cell clickable" onClick={(e) => handleCellClick(e, r, "net_revenue")}>
                          <span className="mda-val-number">{r.net_revenue?.toLocaleString("en-IN") || "—"}</span>
                        </td>
                        <td className="text-right mda-value-cell clickable" onClick={(e) => handleCellClick(e, r, "gross_profit")}>
                          <span className="mda-val-number">{r.gross_profit?.toLocaleString("en-IN") || "—"}</span>
                        </td>
                        <td className="text-right mda-value-cell clickable" onClick={(e) => handleCellClick(e, r, "total_debt")}>
                          <span className="mda-val-number">{r.total_debt?.toLocaleString("en-IN") || "—"}</span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </section>

        <footer className="mda-footer-meta">
          <div className="mda-stats">
            Showing <strong>{indexOfFirstRow + 1}-{Math.min(indexOfLastRow, filteredRecords.length)}</strong> of <strong>{filteredRecords.length}</strong> records
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="mda-pagination glass">
              <button 
                className="mda-pag-btn" 
                disabled={currentPage === 1}
                onClick={(e) => { e.stopPropagation(); paginate(currentPage - 1); }}
              >
                <ChevronLeft size={16} />
              </button>
              
              <div className="mda-pag-info">
                Page <strong>{currentPage}</strong> of <strong>{totalPages}</strong>
              </div>

              <button 
                className="mda-pag-btn" 
                disabled={currentPage === totalPages}
                onClick={(e) => { e.stopPropagation(); paginate(currentPage + 1); }}
              >
                <ChevronRight size={16} />
              </button>
            </div>
          )}
        </footer>
      </div>

      {/* Source Viewer Pane */}
      {selectedRecord && (
        <div className="mda-viewer-pane">
          <header className="mda-viewer-header">
            <div className="mda-vh-left">
              <Database size={16} />
              <span>Source: {selectedRecord.filename}</span>
            </div>
            <button className="mda-btn-close-viewer" onClick={() => setSelectedRecord(null)}>
              <X size={18} />
            </button>
          </header>
          <div className="mda-viewer-body">
            <DocumentViewer 
              documentId={selectedRecord.document_id} 
              filename={selectedRecord.filename}
              highlight={activeHighlight}
              onClose={() => setSelectedRecord(null)}
              hideCloseButton={true}
              hideHeader={true}
              hideBorder={true}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default MasterDataAllPage;

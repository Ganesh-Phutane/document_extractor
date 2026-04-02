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
  X,
  Settings
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
  
  // Column Visibility Drawer
  const [showColumnDrawer, setShowColumnDrawer] = useState(false);
  const [visibleColumns, setVisibleColumns] = useState({});
  const [extraColumnsDetected, setExtraColumnsDetected] = useState([]);

  // Standard Columns Definition
  const STANDARD_COLUMNS = [
    { id: "company_name", label: "Company", isStandard: true },
    { id: "period", label: "Period", isStandard: true },
    { id: "frequency", label: "Frequency", isStandard: true },
    { id: "gross_sales", label: "Gross Sales", isStandard: true, isNumber: true },
    { id: "ebita", label: "EBITDA", isStandard: true, isNumber: true },
    { id: "net_revenue", label: "Net Revenue", isStandard: true, isNumber: true },
    { id: "gross_profit", label: "Gross Profit", isStandard: true, isNumber: true },
    { id: "total_debt", label: "Total Debt", isStandard: true, isNumber: true },
  ];
  
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
      
      // Auto-detect extra columns from the data
      if (data && data.length > 0) {
        const standardIds = STANDARD_COLUMNS.map(c => c.id);
        const allKeys = new Set();
        data.forEach(rec => {
          Object.keys(rec).forEach(key => {
            if (!standardIds.includes(key) && 
                !["document_id", "filename", "extraction_id"].includes(key)) {
              allKeys.add(key);
            }
          });
        });
        
        const extras = Array.from(allKeys).sort();
        setExtraColumnsDetected(extras);
        
        // Initialize visibility state if not already set
        setVisibleColumns(prev => {
          const newState = { ...prev };
          // Standard columns true by default
          STANDARD_COLUMNS.forEach(col => {
            if (newState[col.id] === undefined) newState[col.id] = true;
          });
          // Extra columns false by default if newly detected
          extras.forEach(colId => {
            if (newState[colId] === undefined) newState[colId] = false;
          });
          return newState;
        });
      }
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

  const renderCellValue = (val) => {
    if (val === null || val === undefined || val === "") return "—";
    
    // Handle object structure {value, source_ref} from Gemini
    if (typeof val === 'object' && val !== null) {
      const displayVal = val.value !== undefined ? val.value : val;
      if (displayVal === null || displayVal === undefined || displayVal === "") return "—";
      return typeof displayVal === 'number' 
        ? displayVal.toLocaleString("en-IN") 
        : String(displayVal);
    }
    
    return typeof val === 'number' ? val.toLocaleString("en-IN") : String(val);
  };

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
        // Handle object values for cell display during trace
        const rawVal = record[fieldId];
        const displayVal = (typeof rawVal === 'object' && rawVal !== null) ? rawVal.value : rawVal;
        setActiveHighlight({ trace_found: false, matched_text: String(displayVal ?? "") });
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
            <button className="mda-btn-columns" onClick={() => setShowColumnDrawer(true)}>
              <Settings size={16} />
              <span>Columns</span>
            </button>
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
                    {STANDARD_COLUMNS.map(col => visibleColumns[col.id] && (
                      <th key={col.id} className={col.isNumber ? "text-right" : ""}>
                        {col.label}
                      </th>
                    ))}
                    {extraColumnsDetected.map(colId => visibleColumns[colId] && (
                      <th key={colId} className="text-right" style={{ textTransform: 'capitalize' }}>
                        {colId.replace(/_/g, ' ')}
                      </th>
                    ))}
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
                        {/* Render Standard Columns */}
                        {STANDARD_COLUMNS.map(col => {
                          if (!visibleColumns[col.id]) return null;

                          if (col.id === "company_name") {
                            return <td key={col.id} className="mda-cell-company">{r.company_name}</td>;
                          }
                          if (col.id === "period") {
                            return <td key={col.id} className="mda-cell-period">{r.period}</td>;
                          }
                          if (col.id === "frequency") {
                            return (
                              <td key={col.id}>
                                <span className={`mda-badge ${(r.frequency || "").toLowerCase()}`}>
                                  {r.frequency}
                                </span>
                              </td>
                            );
                          }
                          
                          // Numeric Standard KPIs
                          return (
                            <td 
                              key={col.id} 
                              className="text-right mda-value-cell clickable" 
                              onClick={(e) => handleCellClick(e, r, col.id)}
                            >
                              <span className="mda-val-number">
                                {renderCellValue(r[col.id])}
                              </span>
                            </td>
                          );
                        })}

                        {/* Render Extra Columns */}
                        {extraColumnsDetected.map(colId => {
                          if (!visibleColumns[colId]) return null;
                          return (
                            <td 
                              key={colId} 
                              className="text-right mda-value-cell clickable"
                              onClick={(e) => handleCellClick(e, r, colId)}
                            >
                              <span className="mda-val-number">
                                {renderCellValue(r[colId])}
                              </span>
                            </td>
                          );
                        })}
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

      {/* Column Visibility Drawer */}
      {showColumnDrawer && (
        <>
          <div className="mda-drawer-overlay" onClick={() => setShowColumnDrawer(false)} />
          <div className="mda-column-drawer fade-in-right">
            <header className="mda-drawer-header">
              <div className="mda-dh-left">
                <Settings size={18} />
                <h3>Column Settings</h3>
              </div>
              <button className="mda-btn-close-drawer" onClick={() => setShowColumnDrawer(false)}>
                <X size={18} />
              </button>
            </header>

            <div className="mda-drawer-body">
              <div className="mda-section-label">Main Columns</div>
              <div className="mda-checkbox-group">
                {STANDARD_COLUMNS.map(col => (
                  <label key={col.id} className="mda-checkbox-item">
                    <input 
                      type="checkbox" 
                      checked={!!visibleColumns[col.id]} 
                      onChange={() => setVisibleColumns(prev => ({ ...prev, [col.id]: !prev[col.id] }))}
                    />
                    <span className="mda-checkbox-label">{col.label}</span>
                  </label>
                ))}
              </div>

              {extraColumnsDetected.length > 0 && (
                <>
                  <div className="mda-section-label" style={{ marginTop: '1.5rem' }}>Extra Columns</div>
                  <div className="mda-checkbox-group">
                    {extraColumnsDetected.map(colId => (
                      <label key={colId} className="mda-checkbox-item">
                        <input 
                          type="checkbox" 
                          checked={!!visibleColumns[colId]} 
                          onChange={() => setVisibleColumns(prev => ({ ...prev, [colId]: !prev[colId] }))}
                        />
                        <span className="mda-checkbox-label" style={{ textTransform: 'capitalize' }}>
                          {colId.replace(/_/g, ' ')}
                        </span>
                      </label>
                    ))}
                  </div>
                </>
              )}
            </div>

            <footer className="mda-drawer-footer">
              <button className="mda-btn-apply" onClick={() => setShowColumnDrawer(false)}>
                Done
              </button>
            </footer>
          </div>
        </>
      )}
    </div>
  );
};

export default MasterDataAllPage;

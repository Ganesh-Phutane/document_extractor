import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  X,
  Activity,
  AlertCircle,
  FileJson,
  BarChart3
} from "lucide-react";
import useDocumentStore from "../store/useDocumentStore";
import { getExtractionResult } from "../api/extractions";
import { getFieldTrace } from "../api/trace";
import DataVisualization from "../components/DataVisualization";
import DocumentViewer from "../components/DocumentViewer";
import "../styles/pages/DocumentDetails.css";

const DocumentDetailsPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const {
    vizData,
    setVizData,
    loading,
    setLoading,
    error,
    setError,
    viewerOpen,
    setViewerOpen,
    activeHighlight,
    setActiveHighlight,
    resetViz,
  } = useDocumentStore();

  const [toast, setToast] = useState(null);
  const [showLoading, setShowLoading] = useState(false);

  // Delay loading state to prevent flickering on fast fetches
  useEffect(() => {
    let timer;
    if (loading && !vizData) {
      timer = setTimeout(() => setShowLoading(true), 200);
    } else {
      setShowLoading(false);
    }
    return () => clearTimeout(timer);
  }, [loading, vizData]);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await getExtractionResult(id);
        setVizData(result);
      } catch (err) {
        console.error("Failed to fetch extraction result:", err);
        setError("Could not load extraction data.");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    return () => resetViz(); // Cleanup on unmount
  }, [id, setVizData, setLoading, setError, resetViz]);

  const handleCellClick = async (path) => {
    if (!vizData || !vizData.extraction_id) return;

    const tryTrace = async (p) => {
      try {
        const trace = await getFieldTrace(vizData.extraction_id, p);
        return trace && trace.trace_found !== false ? trace : null;
      } catch (err) {
        console.error("Trace error:", err);
        return null;
      }
    };

    let trace = await tryTrace(path);

    // If path is a row/object and it fails, try the first few child fields
    if (!trace && vizData?.data) {
      const segments = path.split(/[.[\]]+/).filter(Boolean);
      let current = vizData.data.extracted_fields || vizData.data;

      try {
        for (const seg of segments) {
          if (current) current = current[seg];
        }

        if (current && typeof current === "object") {
          const keys = Object.keys(current).filter(
            (k) => typeof current[k] !== "object",
          );
          for (const k of keys.slice(0, 3)) {
            // Try first 3 primitive fields
            trace = await tryTrace(`${path}.${k}`);
            if (trace) break;
          }
        }
      } catch (e) {
        console.debug("Fallback trace resolution skipped", e);
      }
    }

    if (trace && trace.trace_found !== false) {
      setActiveHighlight(trace);
      // Only show page toast for PDFs
      if (trace.file_type === 'pdf') {
        showToast(`Navigating to Page ${trace.page || 1}`);
      } else {
        showToast("Source highlighted");
      }
    } else {
      setActiveHighlight({ page: 1 }); // Default to page 1 if no trace
      // Show info toast
      showToast("Source location shown in viewer", "info");
    }

    setViewerOpen(true); // Always open viewer on click
  };

  const showToast = (message, type = "success") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  if (showLoading && !vizData) {
    return (
      <div className="status-container centered">
        <Activity size={48} className="text-primary animate-pulse" />
        <p>Loading document analysis...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="status-container centered">
        <AlertCircle size={48} className="text-error" />
        <h3>Error</h3>
        <p>{error}</p>
        <button
          className="btn-primary"
          onClick={() => navigate("/documents")}
        >
          Back to List
        </button>
      </div>
    );
  }

  return (
    <div className={`details-page ${viewerOpen ? "split-view" : "full-view"}`}>
      <div className="details-header">
        <button className="btn-back" onClick={() => navigate("/documents")} title="Back to Documents">
          <ArrowLeft size={18} />
        </button>
        <div className="header-info">
          <h1>{vizData?.filename || "Document Analysis"}</h1>
        </div>
        <div className="header-actions">
          {/* Master Data — next step after extraction */}
          <button
            className="btn-secondary"
            onClick={() => navigate(`/master/${id}`)}
            title="Process Master Data"
          >
            <BarChart3 size={18} />
            <span>Master Data</span>
          </button>
          <button
            className={`btn-secondary ${viewerOpen ? "active" : ""}`}
            onClick={() => setViewerOpen(!viewerOpen)}
          >
            <FileJson size={18} />
            <span>{viewerOpen ? "Hide Viewer" : "Show Viewer"}</span>
          </button>
        </div>
      </div>

      <div className="details-container">
        <div className="data-pane custom-scrollbar">
          {vizData && (
            <DataVisualization
              data={vizData.data}
              confidence={vizData.confidence}
              onCellClick={handleCellClick}
            />
          )}
        </div>

        {viewerOpen && (
          <div className="viewer-pane fade-in">
            <div className="viewer-controls">
              <span>Source Viewer</span>
              <button
                className="btn-close-viewer"
                onClick={() => setViewerOpen(false)}
              >
                <X size={18} />
              </button>
            </div>
            <DocumentViewer
              documentId={id}
              fileType={vizData?.doc_type}
              highlight={activeHighlight}
              externalUrl={vizData?.document_url}
              filename={vizData?.filename}
            />
          </div>
        )}
      </div>

      {toast && (
        <div className={`app-toast glass ${toast.type}`}>{toast.message}</div>
      )}
    </div>
  );
};

export default DocumentDetailsPage;

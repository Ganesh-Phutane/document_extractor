import React, { useState, useEffect } from "react";
import {
  Database,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Columns,
  ChevronRight,
  FileJson,
  Activity,
  ArrowRight,
  MessageSquare,
  Sparkles,
  Download,
  TrendingUp,
  Layers,
} from "lucide-react";
import {
  getTemplates,
  runGeminiExtraction,
} from "../api/extractions";
import { 
  listDocuments,
  downloadOriginal, 
  downloadMarkdown,
  getMarkdownPreview,
  getOriginalBlob
} from "../api/documents";
import CustomDropdown from "./CustomDropdown";
import "../styles/components/ExtractionMapping.css";

const ExtractionMapping = ({ onComplete }) => {
  const [documents, setDocuments] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState("");
  const [selectedTemplateId, setSelectedTemplateId] = useState("");

  const [loading, setLoading] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  // Preview States
  const [showPreview, setShowPreview] = useState(false);
  const [activeTab, setActiveTab] = useState("data"); // 'data', 'markdown', 'original'
  const [markdownPreview, setMarkdownPreview] = useState("");
  const [originalFileUrl, setOriginalFileUrl] = useState("");
  const [originalFileText, setOriginalFileText] = useState("");
  const [fetchingPreview, setFetchingPreview] = useState(false);

  useEffect(() => {
    // Reset preview states when document changes
    setShowPreview(false);
    setActiveTab("data");
    setMarkdownPreview("");
    setOriginalFileUrl("");
    setOriginalFileText("");
  }, [selectedDocId]);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const [docs, temps] = await Promise.all([
          listDocuments(),
          getTemplates(),
        ]);
        setDocuments(
          docs.filter(
            (d) =>
              d.status === "di_processed" ||
              d.status === "verified" ||
              d.status === "extracted" ||
              d.status === "manual_review_required",
          ),
        );
        setTemplates(temps);
      } catch (err) {
        setError("Failed to load initial data");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleRunExtraction = async () => {
    if (!selectedDocId) {
      setError(
        "Please select a document.",
      );
      return;
    }

    setExtracting(true);
    setError("");
    setResult(null);

    try {
      const extractionResult = await runGeminiExtraction(
        selectedDocId,
        null, // Backend will now use template mapping as default
        null, // No template_id passed, backend will use default
      );
      setResult(extractionResult);
      if (onComplete) onComplete();
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail) || "Extraction loop failed");
    } finally {
      setExtracting(false);
    }
  };

  const handleDownloadJSON = () => {
    if (!result || !result.data) return;
    const dataStr = JSON.stringify(result.data, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    const doc = documents.find(d => d.id === selectedDocId);
    const filename = doc ? `${doc.filename.split('.')[0]}_extracted.json` : 'extracted_data.json';
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  const handleDownloadOriginal = () => {
    const doc = documents.find(d => d.id === selectedDocId);
    if (doc) downloadOriginal(doc.id, doc.filename);
  };

  const handleDownloadMarkdown = () => {
    const doc = documents.find(d => d.id === selectedDocId);
    if (doc) downloadMarkdown(doc.id, doc.filename);
  };

  const handleTogglePreview = async (tab) => {
    if (activeTab === tab && showPreview) {
      setShowPreview(false);
      setActiveTab("data");
      return;
    }

    setShowPreview(true);
    setActiveTab(tab);

    if (tab === "data") return;

    // Fetch content if not already available
    if (tab === "markdown" && !markdownPreview) {
      setFetchingPreview(true);
      try {
        const data = await getMarkdownPreview(selectedDocId);
        setMarkdownPreview(data.content);
      } catch (err) {
        console.error("Failed to fetch markdown preview", err);
      } finally {
        setFetchingPreview(false);
      }
    } else if (tab === "original" && !originalFileUrl) {
      setFetchingPreview(true);
      try {
        const blob = await getOriginalBlob(selectedDocId);
        const url = window.URL.createObjectURL(blob);
        setOriginalFileUrl(url);

        const fileName = documents.find(d => d.id === selectedDocId)?.filename?.toLowerCase() || "";
        if (fileName.endsWith(".csv") || fileName.endsWith(".xml")) {
          const reader = new FileReader();
          reader.onload = (e) => setOriginalFileText(e.target.result);
          reader.readAsText(blob);
        }
      } catch (err) {
        console.error("Failed to fetch original file preview", err);
      } finally {
        setFetchingPreview(false);
      }
    }
  };

  const renderResult = () => {
    if (!result) return null;

    const confidenceColor =
      result.confidence >= 0.9
        ? "confidence-high"
        : result.confidence >= 0.7
          ? "confidence-med"
          : "confidence-low";

    const isComplex = (val) => typeof val === "object" && val !== null;

    return (
      <div
        className="extraction-result fade-in"
        style={{ marginTop: "2.5rem" }}
      >
        <div className="section-header" style={{ marginBottom: "1.5rem" }}>
          <div className="header-with-icon">
            <CheckCircle2 className="text-success" size={28} />
            <h3 style={{ fontSize: "1.5rem" }}>Final Extracted Data</h3>
          </div>
          <div
            className={`doc-status ${result.confidence >= 0.9 ? "di_processed" : "failed"}`}
            style={{ padding: "0.5rem 1rem" }}
          >
            <span className={confidenceColor} style={{ fontWeight: 700 }}>
              {Math.round(result.confidence * 100)}% Confidence
            </span>
          </div>
          <div className="preview-actions" style={{ marginLeft: "auto", display: "flex", gap: "0.75rem" }}>
            <button 
              className={`btn-secondary ${activeTab === 'original' && showPreview ? 'active' : ''}`} 
              onClick={() => handleTogglePreview('original')} 
              title="Preview Original"
            >
              <Download size={16} />
              <span>Original</span>
            </button>
            <button 
              className={`btn-secondary ${activeTab === 'markdown' && showPreview ? 'active' : ''}`} 
              onClick={() => handleTogglePreview('markdown')} 
              title="Preview Markdown"
            >
              <Download size={16} />
              <span>Markdown</span>
            </button>
            <button className="btn-secondary btn-primary-lite" onClick={handleDownloadJSON} title="Download JSON Result">
              <FileJson size={16} />
              <span>Result JSON</span>
            </button>
          </div>
        </div>

        <div className="iteration-stats" style={{ marginBottom: "2rem" }}>
          <div className="stat-box">
            <span className="label">Iterations</span>
            <span className="value">{result.iteration}</span>
          </div>
          <div className="stat-box">
            <span className="label">Fields Found</span>
            <span className="value">
              {Object.keys(result.data || {}).length}
            </span>
          </div>
          <div className="stat-box">
            <span className="label">Verification Status</span>
            <span className={`value ${confidenceColor}`}>
              {result.confidence >= 0.9 ? "Verified" : "Review Needed"}
            </span>
          </div>
        </div>

        <div className="preview-tabs">
          <button 
            className={`preview-tab ${activeTab === 'data' ? 'active' : ''}`}
            onClick={() => handleTogglePreview('data')}
          >
            Data View
          </button>
          <button 
            className={`preview-tab ${activeTab === 'markdown' ? 'active' : ''}`}
            onClick={() => handleTogglePreview('markdown')}
          >
            Markdown Preview
          </button>
          <button 
            className={`preview-tab ${activeTab === 'original' ? 'active' : ''}`}
            onClick={() => handleTogglePreview('original')}
          >
            Original Document
          </button>
        </div>

        <div className="preview-content-area">
          {fetchingPreview ? (
            <div className="fetching-preview-loader">
              <Loader2 className="animate-spin text-primary" size={32} />
              <p>Fetching content...</p>
            </div>
          ) : activeTab === "data" ? (
            <div className="preview-grid">
              {Array.isArray(result.data) ? (
                <div className="preview-card glass">
                  <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1rem", paddingBottom: "0.75rem", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                    <div style={{ padding: "0.5rem", borderRadius: "8px", background: "rgba(99, 102, 241, 0.1)", color: "var(--primary)" }}>
                      <FileJson size={16} />
                    </div>
                    <h4 style={{ margin: 0, textTransform: "uppercase", fontSize: "0.8rem", letterSpacing: "0.1em" }}>Extracted Items</h4>
                  </div>
                  <div className="value">
                    <pre style={{ margin: 0 }}>{JSON.stringify(result.data, null, 2)}</pre>
                  </div>
                </div>
              ) : (
                <div className="preview-grid-unified">
                  {(() => {
                const data = result.data || {};
                const entries = Object.entries(data);
                
                if (entries.length === 0) return <div className="text-muted p-8 text-center">No data found.</div>;

                return entries.map(([key, val]) => {
                  const isArray = Array.isArray(val);
                  const isObj = typeof val === "object" && val !== null && !isArray;
                  const isComplex = isArray || isObj;
                  
                  return (
                    <div 
                      key={key} 
                      className={`preview-card glass ${isComplex ? 'complex-card full-width' : 'simple-card'}`}
                    >
                      <div className="card-header-compact">
                        <div className="card-icon-box">
                          {isArray ? <TrendingUp size={14} /> : isObj ? <Layers size={14} /> : <FileJson size={14} />}
                        </div>
                        <h4 className="card-label">{key.replace(/_/g, " ")}</h4>
                      </div>
                      
                      <div className="card-value">
                        {isComplex ? (
                          <pre style={{ margin: 0, fontSize: '0.85rem', overflowX: 'auto' }}>
                            {JSON.stringify(val, null, 2)}
                          </pre>
                        ) : (
                          <div className="simple-value-text">
                            {String(val ?? "—")}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                });
              })()}
            </div>
              )}
            </div>
          ) : activeTab === "markdown" ? (
            <div className="preview-card glass">
              <pre className="markdown-preview-box">
                {markdownPreview || "Processing Markdown content..."}
              </pre>
            </div>
          ) : (
            <div className="preview-card glass original-preview-container">
                {documents.find(d => d.id === selectedDocId)?.filename?.toLowerCase().endsWith(".pdf") ? (
                  <iframe src={originalFileUrl} className="original-preview-iframe" title="Original Document Preview" />
                ) : documents.find(d => d.id === selectedDocId)?.filename?.toLowerCase().match(/\.(jpg|jpeg|png)$/) ? (
                  <img src={originalFileUrl} className="original-preview-img" alt="Original Content" />
                ) : documents.find(d => d.id === selectedDocId)?.filename?.toLowerCase().match(/\.(csv|xml)$/) ? (
                  <pre className="markdown-preview-box original-text-preview">{originalFileText || "Loading content..."}</pre>
                ) : (
                  <div className="preview-not-available">
                    <AlertCircle size={32} className="text-muted" />
                    <p>Preview limited for this file type.</p>
                  </div>
                )}
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="mapping-container">
      <div className="extraction-controls glass p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          <CustomDropdown
            label="Select Processed Document"
            options={documents}
            value={selectedDocId}
            onChange={setSelectedDocId}
            placeholder="-- Select Document --"
            loading={loading}
            disabled={extracting}
            getSublabel={(doc) =>
              doc.file_size
                ? `${(doc.file_size / 1024 / 1024).toFixed(2)} MB`
                : ""
            }
          />
        </div>

        {/* Extraction Goal is now handled automatically via config */}

        <div className="flex justify-end mt-6">
          <button
            className="btn-primary w-auto px-8"
            onClick={handleRunExtraction}
            disabled={
              !selectedDocId || extracting
            }
          >
            {extracting ? (
              <>
                <Loader2 className="animate-spin" size={20} />
                <span>Refining & Extracting...</span>
              </>
            ) : (
              <>
                <Play size={20} />
                <span>Run Extraction</span>
              </>
            )}
          </button>
        </div>
      </div>

      {extracting && (
        <div className="loading-section glass p-12 mt-6">
          <Activity
            className="animate-pulse text-primary mx-auto mb-4"
            size={48}
          />
          <h3>Intelligent Processing in Progress</h3>
          <p className="text-muted mt-2">
            First, we're optimizing your extraction instructions.
            <br />
            Then, we'll perform iterative extraction and self-correction.
          </p>
        </div>
      )}

      {error && (
        <div className="error-message mt-4">
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      {renderResult()}
    </div>
  );
};

export default ExtractionMapping;

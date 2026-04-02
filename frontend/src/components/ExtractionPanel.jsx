import React, { useState, useEffect } from "react";
import {
  Cpu,
  Loader2,
  CheckCircle2,
  AlertCircle,
  FileText,
} from "lucide-react";
import CustomDropdown from "./CustomDropdown";
import { triggerExtraction } from "../api/extractions";
import {
  listDocuments,
  getMarkdownPreview,
  getOriginalBlob,
  downloadOriginal,
  downloadMarkdown,
} from "../api/documents";
import { Download, Eye, FileJson, FileText as FileIcon } from "lucide-react";
import "../styles/components/ExtractionPanel.css";

const ExtractionPanel = ({ onExtractionTriggered }) => {
  const [documents, setDocuments] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState("");
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [markdownPreview, setMarkdownPreview] = useState("");
  const [originalFileUrl, setOriginalFileUrl] = useState("");
  const [originalFileText, setOriginalFileText] = useState("");
  const [activeTab, setActiveTab] = useState("extracted"); // 'extracted' or 'original'
  const [showPreview, setShowPreview] = useState(false);
  const [fetchingPreview, setFetchingPreview] = useState(false);

  const fetchDocs = async () => {
    setLoading(true);
    try {
      const data = await listDocuments();
      setDocuments(data);
    } catch (err) {
      console.error("Failed to fetch documents", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, []);

  useEffect(() => {
    return () => {
      if (originalFileUrl) {
        window.URL.revokeObjectURL(originalFileUrl);
      }
    };
  }, [originalFileUrl]);

  const handleTrigger = async () => {
    if (!selectedDocId) return;

    setProcessing(true);
    setError("");
    setSuccess(false);

    try {
      await triggerExtraction(selectedDocId);
      setSuccess(true);
      if (onExtractionTriggered) onExtractionTriggered();
      fetchDocs(); // Refresh list

      // Fetch preview after success
      handleFetchPreview(selectedDocId);
    } catch (err) {
      setError(
        err.response?.data?.detail || "Extraction failed. Please try again.",
      );
    } finally {
      setProcessing(false);
    }
  };

  const handleFetchPreview = async (docId) => {
    setFetchingPreview(true);
    try {
      // Fetch Markdown
      const mdData = await getMarkdownPreview(docId);
      setMarkdownPreview(mdData.content);

      // Fetch Original Blob for preview
      const blob = await getOriginalBlob(docId);
      const url = window.URL.createObjectURL(blob);
      setOriginalFileUrl(url);

      // Read as text if CSV or XML
      const fileName = documents.find(d => d.id === docId)?.filename?.toLowerCase() || "";
      if (fileName.endsWith(".csv") || fileName.endsWith(".xml")) {
        const reader = new FileReader();
        reader.onload = (e) => setOriginalFileText(e.target.result);
        reader.readAsText(blob);
      } else {
        setOriginalFileText("");
      }

      setShowPreview(true);
    } catch (err) {
      console.error("Failed to fetch preview", err);
    } finally {
      setFetchingPreview(false);
    }
  };

  const handleDownloadOriginal = () => {
    if (selectedDoc) {
      downloadOriginal(selectedDoc.id, selectedDoc.filename);
    }
  };

  const handleDownloadMarkdown = () => {
    if (selectedDoc) {
      downloadMarkdown(selectedDoc.id, selectedDoc.filename);
    }
  };

  // Removed local isOpen state, handled by CustomDropdown component
  const selectedDoc = documents.find((d) => d.id === selectedDocId);

  return (
    <div className="extraction-panel glass">
      <div className="section-header">
        <div className="header-with-icon">
          <Cpu className="text-primary" size={24} />
          <h3>AI Document Extraction</h3>
        </div>
        <button className="btn-text" onClick={fetchDocs} disabled={loading}>
          Refresh List
        </button>
      </div>

      <p className="section-description">
        Select an uploaded document to process it with Azure Document
        Intelligence. This will extract text, tables, and structures into
        Markdown format.
      </p>

      <div className="extraction-controls">
        <CustomDropdown
          label="Select Document"
          options={documents}
          value={selectedDocId}
          onChange={setSelectedDocId}
          placeholder="-- Choose a document --"
          loading={loading}
          disabled={processing}
          getSublabel={(doc) =>
            doc.file_size
              ? `${(doc.file_size / 1024 / 1024).toFixed(2)} MB`
              : ""
          }
        />

        <button
          className="btn-primary"
          onClick={handleTrigger}
          disabled={!selectedDocId || processing}
        >
          {processing ? (
            <>
              <Loader2 className="animate-spin" size={18} />
              <span>Processing with Document Intelligence...</span>
            </>
          ) : (
            <>
              <Cpu size={18} />
              <span>Run Azure Extraction</span>
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="error-message">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="success-message">
          <CheckCircle2 size={16} />
          <span>
            Extraction completed successfully! You can now preview and download
            the results.
          </span>
        </div>
      )}

      {showPreview && (
        <div className="preview-section fade-in">
          <div className="preview-header">
            <div className="preview-tabs">
              <button
                className={`tab-btn ${activeTab === "extracted" ? "active" : ""}`}
                onClick={() => setActiveTab("extracted")}
              >
                <FileText size={16} />
                <span>Extracted Markdown</span>
              </button>
              <button
                className={`tab-btn ${activeTab === "original" ? "active" : ""}`}
                onClick={() => setActiveTab("original")}
              >
                <FileIcon size={16} />
                <span>Original File</span>
              </button>
            </div>
            <div className="preview-actions">
              <button
                className="btn-secondary"
                onClick={handleDownloadOriginal}
                title="Download Original"
              >
                <Download size={16} />
                <span>Original</span>
              </button>
              <button
                className="btn-secondary"
                onClick={handleDownloadMarkdown}
                title="Download Markdown"
              >
                <Download size={16} />
                <span>Markdown</span>
              </button>
            </div>
          </div>

          <div className="markdown-container">
            {fetchingPreview ? (
              <div className="preview-loader">
                <Loader2 className="animate-spin text-primary" size={24} />
                <span>Loading preview...</span>
              </div>
            ) : activeTab === "extracted" ? (
              <pre className="markdown-preview-box">
                {markdownPreview || "No content extracted."}
              </pre>
            ) : (
              <div className="original-preview-container">
                {selectedDoc?.filename?.toLowerCase().endsWith(".pdf") ? (
                  <iframe
                    src={originalFileUrl}
                    className="original-preview-iframe"
                    title="Original Document Preview"
                  />
                ) : selectedDoc?.filename
                    ?.toLowerCase()
                    .match(/\.(jpg|jpeg|png)$/) ? (
                  <img
                    src={originalFileUrl}
                    className="original-preview-img"
                    alt="Original Content"
                  />
                ) : selectedDoc?.filename?.toLowerCase().match(/\.(csv|xml)$/) ? (
                  <pre className="markdown-preview-box original-text-preview">
                    {originalFileText || "Loading content..."}
                  </pre>
                ) : selectedDoc?.filename?.toLowerCase().endsWith(".xlsx") ? (
                  <div className="preview-not-available">
                    <FileJson size={48} className="text-primary mb-2" />
                    <p>Excel preview is optimized for visualization after extraction.</p>
                    <p className="text-xs opacity-60">You can download the raw file below.</p>
                    <button
                      className="btn-text"
                      onClick={handleDownloadOriginal}
                    >
                      Download Excel
                    </button>
                  </div>
                ) : (
                  <div className="preview-not-available">
                    <AlertCircle size={32} className="text-muted" />
                    <p>Preview limited for this file type.</p>
                    <button
                      className="btn-text"
                      onClick={handleDownloadOriginal}
                    >
                      Download to view
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      <div className="info-box glass">
        <FileText size={18} className="text-muted" />
        <p>
          Azure DI uses the <code>prebuilt-layout</code> model for maximum
          accuracy.
        </p>
      </div>
    </div>
  );
};

export default ExtractionPanel;

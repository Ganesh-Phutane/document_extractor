import React, { useState, useEffect } from "react";
import {
  Play,
  Loader2,
  CheckCircle,
  AlertCircle,
  Clock,
  FileText,
  RefreshCw,
} from "lucide-react";
import FileUpload from "../components/FileUpload";
import { listDocuments } from "../api/documents";
import { triggerExtraction, runGeminiExtraction } from "../api/extractions";
import "../styles/components/Dashboard.css";

const UploadAndExtractPage = () => {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [processingDocs, setProcessingDocs] = useState({});

  const fetchDocuments = async () => {
    setLoading(true);
    try {
      const data = await listDocuments();
      // Only show recently uploaded or untracked docs?
      // For now, show all but focus on the "Queue"
      setDocuments(data);
    } catch (err) {
      console.error("Failed to fetch documents:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleExtract = async (docId) => {
    setProcessingDocs((prev) => ({ ...prev, [docId]: "processing" }));

    try {
      // 1. Trigger Azure Extraction
      console.log(`Starting Azure Extraction for ${docId}...`);
      await triggerExtraction(docId);

      // 2. Trigger Gemini Extraction
      console.log(`Starting AI Extraction for ${docId}...`);
      await runGeminiExtraction(docId, null);

      setProcessingDocs((prev) => ({ ...prev, [docId]: "completed" }));
      // Refresh to update statuses
      setTimeout(() => {
        fetchDocuments();
        setProcessingDocs((prev) => {
          const next = { ...prev };
          delete next[docId];
          return next;
        });
      }, 2000);
    } catch (err) {
      console.error(`Extraction failed for ${docId}:`, err);
      setProcessingDocs((prev) => ({ ...prev, [docId]: "failed" }));
    }
  };

  const getStatusDisplay = (docId, currentStatus) => {
    const processingStatus = processingDocs[docId];

    if (processingStatus === "processing") {
      return (
        <div className="doc-status di_processing">
          <Loader2 size={14} className="animate-spin" />
          <span>PROCESSING...</span>
        </div>
      );
    }

    if (processingStatus === "completed") {
      return (
        <div className="doc-status verified">
          <CheckCircle size={14} className="text-success" />
          <span>COMPLETED</span>
        </div>
      );
    }

    if (processingStatus === "failed") {
      return (
        <div className="doc-status failed">
          <AlertCircle size={14} className="text-error" />
          <span>FAILED</span>
        </div>
      );
    }

    // Status 'uploaded' is shown as NEW
    const isNew = currentStatus === "uploaded";
    return (
      <div className={`doc-status ${currentStatus}`}>
        {isNew ? (
          <Clock size={14} className="text-warning" />
        ) : (
          <CheckCircle size={14} />
        )}
        <span>
          {isNew ? "NEW" : currentStatus.replace("_", " ").toUpperCase()}
        </span>
      </div>
    );
  };

  return (
    <div
      className="container"
      style={{ display: "flex", flexDirection: "column", height: "100%" }}
    >
      <header className="page-header compact">
        <div className="header-main">
          <h1>Upload & Extract</h1>
          <p>Process your documents using the automated AI pipeline.</p>
        </div>
        <div className="header-actions">
          <FileUpload onUploadSuccess={fetchDocuments} variant="button" />
        </div>
      </header>

      <div className="documents-container glass compact fade-in">
        <div className="section-header">
          <h3 className="header-with-icon">
            <FileText className="text-primary" />
            Document Queue
          </h3>
          <button
            className="btn-text"
            onClick={fetchDocuments}
            disabled={loading}
          >
            <RefreshCw
              size={14}
              className={loading ? "animate-spin mr-2" : "mr-2"}
            />{" "}
            Refresh
          </button>
        </div>

        {loading && documents.length === 0 ? (
          <div className="loading-state">Loading document queue...</div>
        ) : (
          <div className="table-responsive">
            <table className="doc-table">
              <thead>
                <tr>
                  <th>Document</th>
                  <th className="text-center">Date</th>
                  <th>Status</th>
                  <th className="text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr key={doc.id} className="doc-row">
                    <td>
                      <div className="doc-cell-main">
                        <FileText size={18} className="text-muted" />
                        <span className="doc-name-text">{doc.filename}</span>
                      </div>
                    </td>
                    <td className="text-center">
                      {new Date(doc.uploaded_at).toLocaleDateString()}
                    </td>
                    <td>{getStatusDisplay(doc.id, doc.status)}</td>
                    <td className="text-right">
                      <button
                        className="btn-primary btn-sm"
                        onClick={() => handleExtract(doc.id)}
                        style={{
                          margin: 0,
                          width: "fit-content",
                          marginLeft: "auto",
                        }}
                        disabled={processingDocs[doc.id] === "processing"}
                      >
                        {processingDocs[doc.id] === "processing" ? (
                          <Loader2 size={14} className="animate-spin" />
                        ) : (
                          <RefreshCw size={14} />
                        )}
                        <span>
                          {doc.status === "uploaded" ? "Extract" : "Re-extract"}
                        </span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default UploadAndExtractPage;

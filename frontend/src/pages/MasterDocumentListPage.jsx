import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  BarChart3,
  Sparkles,
  Eye,
  TrendingUp,
  ChevronRight,
} from "lucide-react";
import { listDocuments } from "../api/documents";
import { getMasterData } from "../api/masterData";
import DocumentTable from "../components/DocumentTable";
import "../styles/components/Dashboard.css";
import "../styles/pages/MasterDocumentList.css";
import "../styles/SharedTable.css";

// Statuses that allow master data processing
const PROCESSABLE = new Set([
  "extracted", "verified", "manual_review_required", "reextracting",
]);

const MasterDocumentListPage = () => {
  const navigate = useNavigate();
  const [documents, setDocuments]     = useState([]);
  const [loading, setLoading]         = useState(true);
  const [masterStatus, setMasterStatus] = useState({}); // { [docId]: 'exists' | 'none' }

  useEffect(() => {
    (async () => {
      try {
        const data = await listDocuments();
        setDocuments(data);

        // Check which docs already have master data (parallel, non-blocking)
        const processable = data.filter(d => PROCESSABLE.has(d.status));
        const checks = await Promise.allSettled(
          processable.map(d => getMasterData(d.id).then(() => [d.id, "exists"]))
        );
        const statusMap = {};
        checks.forEach(r => {
          if (r.status === "fulfilled") {
            const [id, s] = r.value;
            statusMap[id] = s;
          }
        });
        setMasterStatus(statusMap);
      } catch (err) {
        console.error("Failed to fetch documents:", err);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const canProcess = (status) => PROCESSABLE.has(status);

  if (loading) {
    return (
      <div className="container" style={{ display: 'flex', flexDirection: 'column', height: '100%', justifyContent: 'center', alignItems: 'center' }}>
        <div className="md-spinner" />
        <p style={{ marginTop: '1rem', color: '#64748b', fontSize: '0.85rem', fontWeight: 500 }}>
          Preparing documents list...
        </p>
      </div>
    );
  }

  return (
    <div className="container" style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Page header */}
      <header className="page-header">
        <div className="mdl-title-row">
          <BarChart3 size={22} color="#6366f1" />
          <div>
            <h1>Master Data</h1>
            <p>Select a document to extract and view its validated financial KPIs.</p>
          </div>
        </div>
      </header>

      {/* Instruction banner */}
      <div className="mdl-info-banner glass">
        <Sparkles size={15} color="#6366f1" />
        <span>
          Click <strong>"Process Master Data"</strong> on any extracted document to pull
          Gross Sales, EBITDA, Net Revenue and Gross Profit into a validated master record.
        </span>
      </div>

      {/* Document table */}
      <div className="documents-container glass compact fade-in" style={{ flex: 1 }}>
        <DocumentTable 
          documents={documents}
          loading={loading}
          actions={(doc) => {
            const processable = canProcess(doc.status);
            if (!processable) return <span className="mdl-no-action">Complete extraction first</span>;

            if (masterStatus[doc.id] === "exists") {
              return (
                <button className="mdl-view-btn" onClick={() => navigate(`/master/${doc.id}`)}>
                  <Eye size={14} />
                  <span>View Master Data</span>
                  <ChevronRight size={13} />
                </button>
              );
            }
            
            return (
              <button className="mdl-process-btn" onClick={() => navigate(`/master/${doc.id}?autoprocess=true`)}>
                <TrendingUp size={14} />
                <span>Process Master Data</span>
                <ChevronRight size={13} />
              </button>
            );
          }}
        />
      </div>
    </div>
  );
};

export default MasterDocumentListPage;

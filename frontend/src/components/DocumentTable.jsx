import React from 'react';
import { FileText, Eye, CheckCircle, AlertCircle, Clock, Activity, ChevronRight, TrendingUp } from 'lucide-react';

const getStatusIcon = (status) => {
  switch (status) {
    case 'verified': return <CheckCircle size={14} className="text-success" />;
    case 'failed': return <AlertCircle size={14} className="text-error" />;
    case 'di_processing':
    case 'extracting':
    case 'reextracting':
      return <Activity size={14} className="text-primary animate-pulse" />;
    default: return <Clock size={14} className="text-warning" />;
  }
};

const DocumentTable = ({ 
  documents, 
  loading, 
  onRowClick, 
  actions, 
  emptyMessage = "No documents found." 
}) => {
  if (loading) {
    return <div className="loading-state">Loading documents...</div>;
  }

  if (!documents || documents.length === 0) {
    return (
      <div className="empty-state">
        <FileText size={48} color="var(--text-muted)" />
        <p>{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="table-responsive">
      <table className="doc-table">
        <thead>
          <tr>
            <th>Document</th>
            <th>Date</th>
            <th>Status</th>
            <th>{actions ? "Action" : ""}</th>
          </tr>
        </thead>
        <tbody>
          {documents.map((doc) => (
            <tr 
              key={doc.id} 
              className={`doc-row ${onRowClick ? 'clickable' : ''}`}
              onClick={() => onRowClick && onRowClick(doc)}
            >
              <td>
                <div className="doc-cell-main">
                  <FileText size={18} className="text-muted" />
                  <span className="doc-name-text">{doc.filename}</span>
                </div>
              </td>
              <td>{new Date(doc.uploaded_at).toLocaleDateString()}</td>
              <td>
                <div className={`doc-status ${doc.status}`}>
                  {getStatusIcon(doc.status)}
                  <span>{doc.status.replace('_', ' ')}</span>
                </div>
              </td>
              <td>
                {actions && actions(doc)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default DocumentTable;

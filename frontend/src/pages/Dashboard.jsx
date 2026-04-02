import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { 
  FileText, 
  Settings, 
  Clock, 
  CheckCircle, 
  AlertCircle,
  TrendingUp,
  Activity,
  Eye
} from 'lucide-react';
import FileUpload from '../components/FileUpload';
import ExtractionPanel from '../components/ExtractionPanel';
import ExtractionMapping from '../components/ExtractionMapping';
import DataVisualization from '../components/DataVisualization';
import { listDocuments } from '../api/documents';
import { getExtractionResult } from '../api/extractions';
import { useNavigate, Navigate, useOutletContext } from 'react-router-dom';
import '../styles/components/Dashboard.css';

const Dashboard = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const outletContext = useOutletContext();
  
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Use activeView from Layout if possible, allowing Sidebar to control Dashboard sub-views
  const [localActiveView, setLocalActiveView] = useState('overview');
  const activeView = outletContext?.activeView || localActiveView;
  const setActiveView = outletContext?.setActiveView || setLocalActiveView;

  const fetchDocuments = async () => {
    try {
      const data = await listDocuments();
      setDocuments(data);
    } catch (err) {
      console.error('Failed to fetch documents:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const getStatusIcon = (status) => {
    switch (status) {
      case 'verified': return <CheckCircle size={14} className="text-success" />;
      case 'failed': return <AlertCircle size={14} className="text-error" />;
      case 'di_processing': return <Activity size={14} className="text-primary animate-pulse" />;
      default: return <Clock size={14} className="text-warning" />;
    }
  };

  const handleDocumentClick = (doc) => {
    navigate(`/documents/${doc.id}`);
  };

  const renderOverview = () => (
    <div className="view-content fade-in">
      <header className="page-header">
        <h1>Dashboard Overview</h1>
        <p>Welcome back! Here's what's happening in your extraction pipeline.</p>
      </header>

      <div className="stats-grid">
        <div className="stat-card glass">
          <div className="stat-icon"><FileText size={24} /></div>
          <div className="stat-info">
            <span className="stat-value">{documents.length}</span>
            <span className="stat-label">Total Documents</span>
          </div>
        </div>
        <div className="stat-card glass">
          <div className="stat-icon success"><TrendingUp size={24} /></div>
          <div className="stat-info">
            <span className="stat-value">
              {documents.length > 0 
                ? Math.round((documents.filter(d => d.status === 'verified' || d.status === 'di_processed').length / documents.length) * 100) 
                : 0}%
            </span>
            <span className="stat-label">Efficiency</span>
          </div>
        </div>
        <div className="stat-card glass">
          <div className="stat-icon warning"><Settings size={24} /></div>
          <div className="stat-info">
            <span className="stat-value">{documents.filter(d => d.status === 'manual_review').length}</span>
            <span className="stat-label">Pending Review</span>
          </div>
        </div>
      </div>

      <div className="dashboard-content-grid">
        <div className="documents-container full-width glass">
          <div className="section-header">
            <h3>Recent Documents</h3>
            <button className="btn-text" onClick={fetchDocuments}>Refresh</button>
          </div>
          
          {loading ? (
            <div className="loading-state">Loading documents...</div>
          ) : documents.length === 0 ? (
            <div className="empty-state">
              <FileText size={48} color="var(--text-muted)" />
              <p>No documents found.</p>
              <button className="btn-primary" onClick={() => navigate('/upload')}>Upload Now</button>
            </div>
          ) : (
            <div className="document-list">
              {documents.slice(0, 5).map((doc) => (
                <div 
                  key={doc.id} 
                  className="document-item clickable"
                  onClick={() => handleDocumentClick(doc)}
                >
                  <div className="doc-icon">
                    <FileText size={20} />
                  </div>
                  <div className="doc-details">
                    <span className="doc-name">{doc.filename}</span>
                    <span className="doc-meta">
                      {new Date(doc.uploaded_at).toLocaleDateString()} • {doc.doc_type || 'Unknown Type'}
                    </span>
                  </div>
                  <div className="doc-col-status">
                    <div className="view-data-hint">
                      <Eye size={14} />
                      <span>Analyze</span>
                    </div>
                    <div className={`doc-status ${doc.status}`}>
                      {getStatusIcon(doc.status)}
                      <span>{doc.status.replace('_', ' ')}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );

  const renderUpload = () => (
    <div className="view-content fade-in">
      <header className="page-header">
        <h1>Upload Documents</h1>
        <p>Add new documents to the platform for AI processing.</p>
      </header>
      <div className="centered-form-container">
        <FileUpload onUploadSuccess={fetchDocuments} variant="full" />
      </div>
    </div>
  );

  const renderExtraction = () => (
    <div className="view-content fade-in">
      <header className="page-header">
        <h1>Azure Extraction</h1>
        <p>Run Azure Document Intelligence on your files.</p>
      </header>
      <div className="centered-form-container">
        <ExtractionPanel onExtractionTriggered={fetchDocuments} />
      </div>
    </div>
  );

  const renderAIExtraction = () => (
    <div className="view-content fade-in">
      <header className="page-header">
        <h1>Modular AI Extraction</h1>
        <p>Intelligent, self-correcting data extraction using Gemini.</p>
      </header>
      <div className="centered-form-container full-width">
        <ExtractionMapping onComplete={fetchDocuments} />
      </div>
    </div>
  );

  return (
    <>
      {activeView === 'overview' && renderOverview()}
      {activeView === 'upload' && renderUpload()}
      {activeView === 'extraction' && renderExtraction()}
      {activeView === 'ai_extraction' && renderAIExtraction()}
      {activeView === 'documents' && <Navigate to="/documents" />}
    </>
  );
};

export default Dashboard;

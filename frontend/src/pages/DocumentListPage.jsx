import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import useDocumentStore from '../store/useDocumentStore';
import { listDocuments } from '../api/documents';
import DocumentTable from '../components/DocumentTable';
import { Eye } from 'lucide-react';
import '../styles/components/Dashboard.css';
import '../styles/SharedTable.css';

const DocumentListPage = () => {
  const navigate = useNavigate();
  const { documents, setDocuments, loading, setLoading } = useDocumentStore();

  useEffect(() => {
    const fetchDocs = async () => {
      setLoading(true);
      try {
        const data = await listDocuments();
        setDocuments(data);
      } catch (err) {
        console.error("Failed to fetch documents:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchDocs();
  }, [setDocuments, setLoading]);

  return (
    <div className="container" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <header className="page-header">
        <h1>All Documents</h1>
        <p>Manage and analyze your processed document library.</p>
      </header>

      <div className="documents-container glass compact fade-in">
        <DocumentTable 
          documents={documents}
          loading={loading}
          onRowClick={(doc) => navigate(`/documents/${doc.id}`)}
          actions={() => (
            <div className="view-data-hint">
              <Eye size={16} />
              <span>View</span>
            </div>
          )}
        />
      </div>
    </div>
  );
};

export default DocumentListPage;

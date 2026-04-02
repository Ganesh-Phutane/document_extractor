import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import './styles/globals.css';


// Basic Error Boundary
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, errorInfo) {
    console.error("React Error Boundary caught:", error, errorInfo);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '20px', color: 'white', background: '#1e1b4b', minHeight: '100vh' }}>
          <h1>Something went wrong.</h1>
          <pre style={{ background: 'rgba(0,0,0,0.5)', padding: '10px' }}>{this.state.error?.toString()}</pre>
          <button onClick={() => window.location.reload()} style={{ padding: '10px 20px', cursor: 'pointer' }}>Reload Page</button>
        </div>
      );
    }
    return this.props.children;
  }
}

import MainLayout from './components/MainLayout';
import DocumentListPage from './pages/DocumentListPage';
import DocumentDetailsPage from './pages/DocumentDetailsPage';
import UploadAndExtractPage from './pages/UploadAndExtractPage';
import MasterDataPage from './pages/MasterDataPage';
import MasterDocumentListPage from './pages/MasterDocumentListPage';
import MasterDataAllPage from './pages/MasterDataAllPage';

function App() {
  React.useEffect(() => {
    window.onerror = (msg, url, lineNo, columnNo, error) => {
      console.error('Global Error:', msg, 'at', url, ':', lineNo);
      return false;
    };
    window.onunhandledrejection = (event) => {
      console.error('Unhandled Promise Rejection:', event.reason);
    };
  }, []);

  return (
    <ErrorBoundary>
      <AuthProvider>
        <Router>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            
            {/* Protected Routes with Persistent Sidebar Layout */}
            <Route element={<ProtectedRoute><MainLayout /></ProtectedRoute>}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/upload-extract" element={<UploadAndExtractPage />} />
              <Route path="/documents" element={<DocumentListPage />} />
              <Route path="/documents/:id" element={<DocumentDetailsPage />} />
              {/* Master Data — global view + list page + individual doc page */}
              <Route path="/master/all" element={<MasterDataAllPage />} />
              <Route path="/master" element={<MasterDocumentListPage />} />
              <Route path="/master/:documentId" element={<MasterDataPage />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Router>
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;

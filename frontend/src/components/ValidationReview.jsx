import React, { useState } from 'react';
import { 
  AlertTriangle, 
  CheckCircle2, 
  XSquare, 
  ArrowRightLeft, 
  Edit3, 
  Save, 
  X, 
  CheckCircle,
  HelpCircle,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { resolveMasterData } from '../api/masterData';

const ValidationReview = ({ masterData, documentId, onResolved, showToast }) => {
  const [resolving, setResolving] = useState(false);
  const [editedData, setEditedData] = useState(JSON.parse(JSON.stringify(masterData)));
  const [isEditing, setIsEditing] = useState(false);

  // Issues grouped by type
  const issues = masterData.validation_issues || [];
  const status = masterData.validation_status;

  if (status === 'validation_passed' || !status) return null;

  const handleResolveAction = async (action, finalData = null) => {
    setResolving(true);
    try {
      // If rejecting, we need to clear the local state status so the UI can hide it
      // but the backend resolve handles the source of truth
      await resolveMasterData(documentId, action, finalData);
      showToast(`Record resolved via ${action}`, "success");
      onResolved();
    } catch (err) {
      showToast("Resolution failed", "error");
    } finally {
      setResolving(false);
    }
  };

  const handleEditValue = (path, value) => {
    const newData = { ...editedData };
    const parts = path.split('.');
    let current = newData;
    for (let i = 0; i < parts.length - 1; i++) {
        if (!current[parts[i]]) current[parts[i]] = {};
        current = current[parts[i]];
    }
    const lastPart = parts[parts.length - 1];
    
    if (typeof current[lastPart] === 'object' && current[lastPart] !== null) {
        current[lastPart].value = value;
        current[lastPart].source_col = 'manual_edit';
    } else {
        current[lastPart] = value;
    }
    setEditedData(newData);
  };

  const renderIssueDetails = (issue) => {
    const path = issue.is_extra 
        ? `extra_fields.${issue.field}.${issue.period}`
        : `financials.${issue.field}.${issue.period}`;

    // Helper to get nested value safely
    const getVal = (p) => {
        const segs = p.split('.');
        let curr = editedData;
        for (const s of segs) {
            if (!curr || !curr[s]) return '';
            curr = curr[s];
        }
        return typeof curr === 'object' ? curr.value : curr;
    };

    switch (issue.type) {
      case 'total_mismatch':
        return (
          <div className="md-issue-detail-inline">
            <div className="md-issue-val-box">
                <span className="md-issue-label">Calculated Sum:</span> 
                <span className="md-issue-val-old">{issue.actual.toLocaleString()}</span>
            </div>
            <ArrowRightLeft size={14} className="md-issue-icon" /> 
            <div className="md-issue-val-box">
                <span className="md-issue-label">Reported Total:</span> 
                {isEditing ? (
                    <input 
                        type="number" 
                        className="md-inline-input"
                        value={getVal(path) ?? ''} 
                        onChange={(e) => handleEditValue(path, parseFloat(e.target.value))}
                    />
                ) : (
                    <span className="md-issue-val-new">{issue.expected.toLocaleString()}</span>
                )}
            </div>
          </div>
        );
      case 'conflict':
        return (
          <div className="md-issue-detail-inline">
             <div className="md-issue-val-box">
                <span className="md-issue-label">Existing:</span> 
                <span className="md-issue-val-old">{issue.old_value}</span>
             </div>
             <ArrowRightLeft size={14} className="md-issue-icon" /> 
             <div className="md-issue-val-box">
                <span className="md-issue-label">New Extracted:</span> 
                {isEditing ? (
                    <input 
                        type="number" 
                        className="md-inline-input"
                        value={getVal(path) ?? ''} 
                        onChange={(e) => handleEditValue(path, parseFloat(e.target.value))}
                    />
                ) : (
                    <span className="md-issue-val-new">{issue.new_value}</span>
                )}
             </div>
          </div>
        );
      default:
        return <div className="md-issue-detail-inline">{issue.message}</div>;
    }
  };

  return (
    <div className={`md-val-review-banner-inline glass ${status} ${isEditing ? 'editing' : ''}`}>
      <div className="md-val-review-main-header">
        <div className="md-val-review-title">
          {status === 'conflict_detected' ? (
            <><ArrowRightLeft size={20} color="#f59e0b" /> <div className="md-title-text"><h3>Data Conflicts Detected</h3><p>Extracted values differ from existing database records.</p></div></>
          ) : (
            <><AlertTriangle size={20} color="#ef4444" /> <div className="md-title-text"><h3>Validation Failed</h3><p>Critical errors found in the extracted financial data.</p></div></>
          )}
        </div>
        <div className="md-val-review-global-actions">
           {!isEditing ? (
             <>
                <button className="md-btn-accept" onClick={() => handleResolveAction('accept')} disabled={resolving}>
                    <CheckCircle2 size={15} /> Accept New Data
                </button>
                <button className="md-btn-edit" onClick={() => setIsEditing(true)}>
                    <Edit3 size={15} /> Manual Edit
                </button>
                <button className="md-btn-cancel-review" onClick={() => handleResolveAction('reject')} disabled={resolving}>
                    <XSquare size={15} /> Reject
                </button>
             </>
           ) : (
             <>
                <button className="md-btn-save" onClick={() => handleResolveAction('edit', editedData)} disabled={resolving}>
                    <Save size={15} /> {resolving ? 'Saving...' : 'Save & Resolve'}
                </button>
                <button className="md-btn-cancel-edit" onClick={() => setIsEditing(false)}>
                    <X size={15} /> Cancel
                </button>
             </>
           )}
        </div>
      </div>

      <div className="md-val-conflict-list-wrapper">
         <div className="md-val-issues-grid">
            {issues.map((issue, idx) => (
                <div key={idx} className={`md-issue-card-inline ${issue.type}`}>
                    <div className="md-issue-meta">
                        <span className="md-issue-type-tag">{issue.type.replace('_', ' ')}</span>
                        <span className="md-issue-field-name">{issue.field}</span>
                        {issue.period && <span className="md-issue-period-tag">{issue.period}</span>}
                    </div>
                    {renderIssueDetails(issue)}
                </div>
            ))}
         </div>
      </div>
    </div>
  );
};

export default ValidationReview;

import React, { useEffect, useState } from "react";
import { FileText, Image as ImageIcon, ExternalLink, AlertCircle, Loader, FileCode, FileSpreadsheet, Code } from 'lucide-react';
import axios from "axios";
import apiClient from "../api/client";
import * as XLSX from 'xlsx';
import "../styles/components/DocumentViewer.css";

const DocumentViewer = ({
  documentId,
  fileType,
  highlight,
  externalUrl,
  filename,
  hideHeader = false,
  hideBorder = false,
}) => {
  const [loading, setLoading] = useState(false);
  const [url, setUrl] = useState("");
  const [error, setError] = useState(null);
  const [csvContent, setCsvContent] = useState("");
  const [xlsxData, setXlsxData] = useState([]); // [{ name: 'Sheet1', data: [[]] }]
  const [activeSheet, setActiveSheet] = useState(0);

  const inferFileType = (fType, docUrl, fName) => {
    if (fType) return fType.toLowerCase();
    if (fName) {
      const nameLower = fName.toLowerCase();
      if (nameLower.endsWith('.pdf')) return 'pdf';
      if (nameLower.endsWith('.csv')) return 'csv';
      if (nameLower.endsWith('.xlsx')) return 'xlsx';
      if (nameLower.endsWith('.xml')) return 'xml';
      if (nameLower.match(/\.(png|jpg|jpeg|webp)$/)) return 'image';
    }
    const docUrlToCheck = docUrl || externalUrl || "";
    if (!docUrlToCheck) return '';
    const cleanUrl = docUrlToCheck.split('?')[0].toLowerCase();
    if (cleanUrl.includes('.pdf')) return 'pdf';
    if (cleanUrl.includes('.csv')) return 'csv';
    if (cleanUrl.includes('.xlsx')) return 'xlsx';
    if (cleanUrl.includes('.xml')) return 'xml';
    if (cleanUrl.includes('.png') || cleanUrl.includes('.jpg') || cleanUrl.includes('.jpeg') || cleanUrl.includes('.webp')) return 'image';
    return '';
  };

  const effectiveFileType = inferFileType(fileType, url || externalUrl, filename);
  const isImage = ['png', 'jpg', 'jpeg', 'image', 'webp'].includes(effectiveFileType);
  const isPDF = effectiveFileType === 'pdf';
  const isCSV = effectiveFileType === 'csv';
  const isXLSX = effectiveFileType === 'xlsx';
  const isXML = effectiveFileType === 'xml';

  useEffect(() => {
    // For PDFs and Images with a direct URL, we can use the URL directly
    if (externalUrl && (isPDF || isImage)) {
      setUrl(externalUrl);
      setLoading(false);
      return;
    }

    let objectUrl = "";
    const fetchDocument = async () => {
      if (!documentId && !externalUrl) return;

      setLoading(true);
      setError(null);

      try {
        const downloadUrl = `/documents/${documentId}/download/original`;
        
        if (isCSV || isXML) {
          // Try to fetch text content. Start with backend proxy to avoid CORS issues with SAS
          try {
            const res = await apiClient.get(downloadUrl);
            setCsvContent(typeof res.data === 'string' ? res.data : JSON.stringify(res.data, null, 2));
          } catch (e) {
            console.warn("Backend proxy failed, trying externalUrl...", e);
            const res = await axios.get(externalUrl);
            setCsvContent(typeof res.data === 'string' ? res.data : JSON.stringify(res.data, null, 2));
          }
          setUrl(externalUrl || `${apiClient.defaults.baseURL}${downloadUrl}`);
        } else if (isXLSX) {
          // Fetch as arraybuffer for SheetJS
          const response = await apiClient.get(externalUrl || downloadUrl, { responseType: 'arraybuffer' });
          const workbook = XLSX.read(new Uint8Array(response.data), { type: 'array' });
          const sheets = workbook.SheetNames.map(name => ({
            name,
            data: XLSX.utils.sheet_to_json(workbook.Sheets[name], { header: 1 })
          }));
          setXlsxData(sheets);
          setUrl(externalUrl || `${apiClient.defaults.baseURL}${downloadUrl}`);
        } else {
          // Fetch as blob (for PDF/Image)
          // Note: If using externalUrl (direct SAS), apiClient might still try prepending baseURL if it's not absolute
          const response = await apiClient.get(
            externalUrl || downloadUrl,
            { responseType: "blob" }
          );
          objectUrl = URL.createObjectURL(response.data);
          setUrl(objectUrl);
        }
      } catch (err) {
        console.error("Failed to fetch document:", err);
        setError("Could not load original document. Please check your connection.");
      } finally {
        setLoading(false);
      }
    };

    fetchDocument();

    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [documentId, externalUrl, isCSV, isXML, isPDF, isImage]);

  // Auto-scroll to highlight
  useEffect(() => {
    if (!highlight || loading) return;
    
    // Small timeout to ensure DOM is updated
    const timer = setTimeout(() => {
      // Prioritize .scroll-target (unique cell/text)
      const element = document.querySelector('.scroll-target') || 
                     document.querySelector('.cell-highlight') || 
                     document.querySelector('.text-highlight');
      
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });
      }
    }, 150);
    
    return () => clearTimeout(timer);
  }, [highlight, csvContent, xlsxData, loading]);

  const escapeHTML = (str) => {
    return str.replace(/[&<>"']/g, (m) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    }[m]));
  };

  const renderHighlight = () => {
    if (
      !highlight ||
      (!isPDF && !isImage && !isXLSX && !isCSV)
    )
      return null;

    if (isXLSX || isCSV) return null; // Logic handled in table rendering

    // Azure polygon is [x1, y1, x2, y2, x3, y3, x4, y4]
    // We'll simplify to a bounding box for now
    const p = highlight.bbox;
    const minX = Math.min(p[0], p[2], p[4], p[6]) * 100;
    const minY = Math.min(p[1], p[3], p[5], p[7]) * 100;
    const maxX = Math.max(p[0], p[2], p[4], p[6]) * 100;
    const maxY = Math.max(p[1], p[3], p[5], p[7]) * 100;

    return (
      <div
        className="source-highlight"
        style={{
          left: `${minX}%`,
          top: `${minY}%`,
          width: `${maxX - minX}%`,
          height: `${maxY - minY}%`,
        }}
      />
    );
  };

  if (!documentId)
    return (
      <div className="viewer-empty glass">
        <FileText size={48} /> <p>Select a field to see source</p>
      </div>
    );

  return (
    <div className={`document-viewer-container glass ${hideBorder ? 'no-border' : ''}`}>
      {!hideHeader && (
        <div className="viewer-header">
          <div className="viewer-title">
            {isPDF ? <FileText size={18} /> : 
             isCSV || isXLSX ? <FileSpreadsheet size={18} /> : 
             isXML ? <Code size={18} /> : 
             <ImageIcon size={18} />}
            <span>Source Viewer</span>
          </div>
          <a
            href={externalUrl || `${apiClient.defaults.baseURL}/documents/${documentId}/download/original`}
            target="_blank"
            rel="noreferrer"
            className="btn-icon-text"
            download={isCSV || isXLSX}
          >
            <ExternalLink size={14} /> Open
          </a>
        </div>
      )}

      <div className="viewer-content">
        {loading ? (
          <div className="viewer-loading">
            <Loader className="animate-spin" size={32} />
            <p>Loading document...</p>
          </div>
        ) : error ? (
          <div className="viewer-error">
            <AlertCircle size={32} className="text-error" />
            <p>{error}</p>
          </div>
        ) : isPDF ? (
          <div className="pdf-wrapper">
            <iframe
              key={`${url}-${highlight?.page || 1}`}
              src={`${url}#view=FitH&page=${highlight?.page || 1}`}
              title="Source PDF"
            />
            {highlight && (
              <div className="highlight-hint">
                Showing Page {highlight.page}
              </div>
            )}
          </div>
        ) : isImage ? (
          <div className="image-wrapper">
            <img src={url} alt="Source" />
            {renderHighlight()}
          </div>
        ) : isCSV ? (
          <div className="csv-wrapper custom-scrollbar">
            {highlight?.matched_text ? (
              <pre dangerouslySetInnerHTML={{ 
                __html: escapeHTML(csvContent).replace(
                  new RegExp(`(${escapeHTML(highlight.matched_text)})`, 'gi'), 
                  '<span class="text-highlight scroll-target">$1</span>'
                ) 
              }} />
            ) : (
              <pre>{csvContent}</pre>
            )}
          </div>
        ) : isXML ? (
          <div className="xml-wrapper custom-scrollbar">
            {highlight?.matched_text ? (
              <pre 
                className="syntax-xml"
                dangerouslySetInnerHTML={{ 
                  __html: escapeHTML(csvContent).replace(
                    new RegExp(`(${escapeHTML(highlight.matched_text)})`, 'gi'), 
                    '<span class="text-highlight scroll-target">$1</span>'
                  ) 
                }} 
              />
            ) : (
              <pre className="syntax-xml">{csvContent}</pre>
            )}
          </div>
        ) : isXLSX ? (
          <div className="xlsx-preview-container custom-scrollbar">
            {xlsxData.length > 1 && (
              <div className="sheet-tabs">
                {xlsxData.map((sheet, idx) => (
                  <button 
                    key={idx} 
                    className={`sheet-tab ${activeSheet === idx ? 'active' : ''}`}
                    onClick={() => setActiveSheet(idx)}
                  >
                    {sheet.name}
                  </button>
                ))}
              </div>
            )}
            <div className="xlsx-table-wrapper">
              <table className="xlsx-table">
                <tbody>
                  {xlsxData[activeSheet]?.data.map((row, rIdx) => (
                    <tr key={rIdx}>
                      {row.map((cell, cIdx) => {
                        const isRowMatch = highlight?.row === rIdx;
                        const isColMatch = highlight?.column === cIdx;
                        const isDirectMatch = isRowMatch && isColMatch;
                        
                        // Fallback to text match if no direct match found
                        const isTextMatch = highlight?.matched_text && 
                                          String(cell).toLowerCase().includes(highlight.matched_text.toLowerCase());
                        
                        // We highlight if it's a direct match OR if it's a text match AND we don't have a better direct match nearby
                        const shouldHighlight = isDirectMatch || (!isDirectMatch && isTextMatch);

                        return (
                          <td 
                            key={cIdx} 
                            className={shouldHighlight ? 'cell-highlight scroll-target' : ''}
                          >
                            {cell}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="other-wrapper">
            <AlertCircle size={32} />
            <p>
              Native preview not available for{" "}
              {effectiveFileType || "this file type"}.
            </p>
            {highlight && (
              <div className="trace-info-box">
                <strong>Source Info:</strong>
                {highlight.row !== null && (
                  <div>
                    Row: {highlight.row}, Col: {highlight.column}
                  </div>
                )}
                {highlight.xpath && (
                  <div className="xpath">XPath: {highlight.xpath}</div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default DocumentViewer;

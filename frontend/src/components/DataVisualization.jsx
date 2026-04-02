import React from "react";
import {
  Layers,
  CheckCircle,
  AlertCircle,
  Info,
  FileJson,
  TrendingUp,
} from "lucide-react";
import "../styles/components/DataVisualization.css";

const DataVisualization = ({ data, title, confidence, onCellClick }) => {
  if (!data)
    return (
      <div className="data-viz-empty glass">
        <Info size={48} className="text-muted" />
        <p>No extraction data available for this document.</p>
      </div>
    );

  // The LLM returns { extracted_fields: { ... }, confidence_scores: { ... } }
  // We want to visualize the extracted_fields part
  const displayData = data.extracted_fields || data;

  const renderValue = (val, isNested = false, path = "") => {
    if (val === null || val === undefined)
      return <span className="value-null">N/A</span>;
    if (typeof val === "boolean")
      return <span className={`value-bool ${val}`}>{val ? "Yes" : "No"}</span>;

    if (Array.isArray(val)) {
      if (val.length === 0) return <span className="value-empty">Empty</span>;

      // If it's an array of objects, render a sub-table
      if (typeof val[0] === "object" && val[0] !== null) {
        const headers = Object.keys(val[0]);
        return (
          <div className="nested-table-scroll custom-scrollbar">
            <table className="nested-table">
              <thead>
                <tr>
                  {headers.map((h) => (
                    <th key={h}>{h.replace(/_/g, " ")}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {val.map((item, idx) => (
                  <tr
                    key={idx}
                    className={onCellClick ? "traceable-row" : ""}
                    onClick={(e) => {
                      if (onCellClick) {
                        e.stopPropagation();
                        onCellClick(`${path}[${idx}]`);
                      }
                    }}
                  >
                    {headers.map((h) => (
                      <td key={h}>
                        {renderValue(item[h], true, `${path}[${idx}].${h}`)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      }
      return (
        <div className="value-tags">
          {val.map((item, i) => (
            <span key={i} className="tag">
              {item}
            </span>
          ))}
        </div>
      );
    }

    if (typeof val === "object" && val !== null) {
      return (
        <div className={`nested-object ${isNested ? "compact" : ""}`}>
          {Object.entries(val).map(([k, v]) => (
            <div key={k} className="nested-kv">
              <span className="nested-key">{k.replace(/_/g, " ")}:</span>
              <div className="nested-val-block">
                {renderValue(v, true, path ? `${path}.${k}` : k)}
              </div>
            </div>
          ))}
        </div>
      );
    }

    return (
      <span
        className={`value-text ${onCellClick ? "traceable" : ""}`}
        onClick={() => onCellClick && onCellClick(path)}
      >
        {String(val)}
      </span>
    );
  };

  const keys = Object.keys(displayData);
  const isLargeObject = keys.length > 8;

  return (
    <div className="data-viz-container">
      <div className="viz-header">
        <div className="viz-info">
          <Layers className="text-primary" size={24} />
          <div>
            <h3>{title || "Extracted Results"}</h3>
          </div>
        </div>

        {confidence !== undefined && (
          <div
            className={`viz-confidence ${confidence >= 0.9 ? "high" : "low"}`}
          >
            {confidence >= 0.9 ? (
              <CheckCircle size={16} />
            ) : (
              <AlertCircle size={16} />
            )}
            <span>{Math.round(confidence * 100)}% Confidence</span>
          </div>
        )}
      </div>

      <div className="viz-body">
        <div className="data-sections">
          {(() => {
            const summaryFields = [];
            const detailedFields = [];

            Object.entries(displayData).forEach(([key, value]) => {
              const isComplex = typeof value === "object" && value !== null;
              if (isComplex) {
                detailedFields.push([key, value]);
              } else {
                summaryFields.push([key, value]);
              }
            });

            return (
              <>
                {summaryFields.length > 0 && (
                  <div className="data-section summary-section glass full-width-section">
                    <div className="section-header-compact">
                      <div className="section-icon-box">
                        <TrendingUp size={14} />
                      </div>
                      <div className="section-label">Document Overview</div>
                    </div>
                    <div className="summary-grid-viz">
                      {summaryFields.map(([key, value]) => (
                        <div key={key} className="summary-item-viz">
                          <span className="summary-label-viz">
                            {key.replace(/_/g, " ")}
                          </span>
                          <span className="summary-value-viz">
                            {renderValue(value, true, key)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {detailedFields.map(([key, value]) => (
                  <div
                    key={key}
                    className={`data-section glass complex ${Array.isArray(value) ? "full-width-section" : ""}`}
                  >
                    <div className="section-header-compact">
                      <div className="section-icon-box">
                        {Array.isArray(value) ? (
                          <TrendingUp size={14} />
                        ) : (
                          <FileJson size={14} />
                        )}
                      </div>
                      <div className="section-label">
                        {key.replace(/_/g, " ")}
                      </div>
                    </div>
                    <div className="section-value">
                      {renderValue(value, false, key)}
                    </div>
                  </div>
                ))}
              </>
            );
          })()}
        </div>
      </div>
    </div>
  );
};

export default DataVisualization;

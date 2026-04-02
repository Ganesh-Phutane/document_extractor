import React, { useState, useRef } from "react";
import { Upload, File, X, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { uploadDocument } from "../api/documents";

const FileUpload = ({ onUploadSuccess, variant = "button" }) => {
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragging(true);
  };

  const handleDragLeave = () => {
    setDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      validateAndSetFile(files[0]);
    }
  };

  const handleFileChange = (e) => {
    const files = e.target.files;
    if (files.length > 0) {
      validateAndSetFile(files[0]);
    }
  };

  const validateAndSetFile = (selectedFile) => {
    setError("");
    setSuccess(false);

    // Size limit: 10MB
    if (selectedFile.size > 10 * 1024 * 1024) {
      setError("File size too large. Maximum 10MB.");
      return;
    }

    // Supported types
    const allowedTypes = [".pdf", ".docx", ".jpg", ".jpeg", ".png", ".csv", ".xlsx", ".xml"];
    const ext = selectedFile.name
      .substring(selectedFile.name.lastIndexOf("."))
      .toLowerCase();
    if (!allowedTypes.includes(ext)) {
      setError("Unsupported file type.");
      return;
    }

    if (variant === "button") {
      // For button variant, upload immediately
      processUpload(selectedFile);
    } else {
      setFile(selectedFile);
    }
  };

  const processUpload = async (fileToUpload) => {
    setUploading(true);
    setError("");
    setSuccess(false);

    try {
      await uploadDocument(fileToUpload);
      setSuccess(true);
      setFile(null);
      if (onUploadSuccess) onUploadSuccess();
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      setError("Upload failed");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const removeFile = () => {
    setFile(null);
    setError("");
    setSuccess(false);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  if (variant === "button") {
    return (
      <div className="compact-upload">
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          style={{ display: "none" }}
          accept=".pdf,.docx,.jpg,.jpeg,.png,.csv,.xlsx,.xml"
        />
        <button 
          className="btn-primary" 
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
        >
          {uploading ? (
            <Loader2 size={16} className="animate-spin" />
          ) : success ? (
            <CheckCircle2 size={16} />
          ) : (
            <Upload size={16} />
          )}
          <span>{uploading ? "Uploading..." : success ? "Uploaded!" : "Add Document"}</span>
        </button>
        {error && <span className="upload-error-mini">{error}</span>}
      </div>
    );
  }

  return (
    <div className="upload-section glass">
      <div
        className={`drop-zone ${dragging ? "dragging" : ""} ${file ? "has-file" : ""}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !file && fileInputRef.current?.click()}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          style={{ display: "none" }}
          accept=".pdf,.docx,.jpg,.jpeg,.png,.csv,.xlsx,.xml"
        />

        {!file ? (
          <div className="drop-zone-content">
            <div className="upload-icon">
              <Upload size={32} />
            </div>
            <h4>
              Drag & drop or <span>browse</span>
            </h4>
            <p>Support PDF, DOCX, Images, CSV, XLSX, XML (Max 10MB)</p>
          </div>
        ) : (
          <div className="file-preview">
            <File className="file-icon" size={24} />
            <div className="file-info">
              <span className="file-name">{file.name}</span>
              <span className="file-size">
                {(file.size / 1024 / 1024).toFixed(2)} MB
              </span>
            </div>
            <button
              className="remove-btn"
              onClick={(e) => {
                e.stopPropagation();
                removeFile();
              }}
            >
              <X size={18} />
            </button>
          </div>
        )}
      </div>

      {error && (
        <div className="upload-error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="upload-success">
          <CheckCircle2 size={16} />
          <span>Document uploaded successfully!</span>
        </div>
      )}

      <button
        className="btn-primary upload-btn"
        onClick={() => processUpload(file)}
        disabled={!file || uploading}
      >
        {uploading ? (
          <>
            <Loader2 className="animate-spin" size={18} />
            <span>Uploading...</span>
          </>
        ) : (
          "Upload"
        )}
      </button>
    </div>
  );
};

export default FileUpload;

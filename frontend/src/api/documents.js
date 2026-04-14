import apiClient from './client';

export const uploadDocument = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await apiClient.post('/documents/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const listDocuments = async () => {
  const response = await apiClient.get('/documents/');
  return response.data;
};

export const getDocumentStatus = async (docId) => {
  const response = await apiClient.get(`/documents/${docId}`);
  return response.data;
};

export const getMarkdownPreview = async (docId) => {
  const response = await apiClient.get(`/documents/${docId}/preview/markdown`);
  return response.data;
};

export const getOriginalBlob = async (docId) => {
  const response = await apiClient.get(`/documents/${docId}/download/original`, {
    responseType: 'blob'
  });
  return response.data;
};

export const downloadOriginal = async (docId, filename) => {
  const response = await apiClient.get(`/documents/${docId}/download/original`, {
    responseType: 'blob'
  });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
};

export const downloadMarkdown = async (docId, filename) => {
  const response = await apiClient.get(`/documents/${docId}/download/markdown`, {
    responseType: 'blob'
  });
  const mdFilename = filename.split('.').slice(0, -1).join('.') + '.md';
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', mdFilename);
  document.body.appendChild(link);
  link.click();
  link.remove();
};

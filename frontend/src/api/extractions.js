import apiClient from './client';

export const triggerExtraction = async (documentId) => {
  const response = await apiClient.post(`/extractions/trigger/${documentId}`);
  return response.data;
};

export const runGeminiExtraction = async (documentId, userGoal = null, templateId = null) => {
  const response = await apiClient.post(`/extractions/${documentId}/run`, {
    user_goal: userGoal,
    template_id: templateId
  });
  return response.data;
};

export const updateDocumentTemplate = async (documentId, templateId) => {
  const response = await apiClient.patch(`/extractions/${documentId}/template?template_id=${templateId}`);
  return response.data;
};

export const getExtractionResult = async (documentId) => {
  const response = await apiClient.get(`/extractions/${documentId}/result`);
  return response.data;
};

export const getTemplates = async () => {
  // Assuming a generic templates endpoint exists or matches the task
  const response = await apiClient.get('/templates');
  return response.data;
};

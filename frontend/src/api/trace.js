import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/extractions';

export const getFieldTrace = async (extractionId, fieldPath) => {
  const token = localStorage.getItem('token');
  const response = await axios.get(`${API_BASE_URL}/${extractionId}/trace`, {
    params: { field_path: fieldPath },
    headers: { Authorization: `Bearer ${token}` }
  });
  return response.data;
};

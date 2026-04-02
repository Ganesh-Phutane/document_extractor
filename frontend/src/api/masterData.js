/**
 * api/masterData.js
 * -----------------
 * API client functions for the Master Data Processing Engine.
 * Follows the same pattern as extractions.js and documents.js.
 */
import apiClient from './client';

/** Triggers the full master data pipeline (MD convert → extract → validate → verify → save).
 *  @param {string}  documentId
 *  @param {string}  extraColumns  Comma-separated list of additional fields to extract.
 */
export const processMasterData = async (documentId, extraColumns = "") => {
  const response = await apiClient.post(
    `/master/${documentId}/process`,
    null,
    { params: { extra_columns: extraColumns } },
  );
  return response.data;
};

/** Fetches pure financial data (flattened, no IDs) */
export const getMasterDataOnly = async () => {
  const response = await apiClient.get('/master/data');
  return response.data;
};

/** Retrieves the latest saved master data result from blob storage */
export const getMasterData = async (documentId) => {
  const response = await apiClient.get(`/master/${documentId}/latest`);
  return response.data;
};

/** Marks the current master data result as approved (becomes verification baseline) */
export const approveMasterData = async (documentId) => {
  const response = await apiClient.patch(`/master/${documentId}/approve`);
  return response.data;
};

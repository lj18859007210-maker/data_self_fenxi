import axios from 'axios';
import type { ApiResponse, UploadResponse, FieldInfo, FieldType, DashboardOverview, FieldAnalysis, CorrelationResult, ChartConfig, AnalysisProgress, Insight, KeyDriver } from '../types';

const api = axios.create({ baseURL: '/api' });

export async function uploadFile(file: File): Promise<ApiResponse<UploadResponse>> {
  const form = new FormData();
  form.append('file', file);
  const { data } = await api.post('/upload', form);
  return data;
}

export async function getPreview(sessionId: string): Promise<ApiResponse<{ filename: string; fields: FieldInfo[]; preview: Record<string, unknown>[]; row_count: number; column_count: number }>> {
  const { data } = await api.get(`/sessions/${sessionId}/preview`);
  return data;
}

export async function updateFields(sessionId: string, updates: { name: string; display_type: FieldType }[]): Promise<ApiResponse<{ fields: FieldInfo[] }>> {
  const { data } = await api.put(`/sessions/${sessionId}/fields`, updates);
  return data;
}

export async function triggerAnalysis(sessionId: string): Promise<ApiResponse<{ session_id: string; state: string }>> {
  const { data } = await api.post(`/sessions/${sessionId}/analyze`);
  return data;
}

export async function getProgress(sessionId: string): Promise<ApiResponse<AnalysisProgress>> {
  const { data } = await api.get(`/sessions/${sessionId}/progress`);
  return data;
}

export async function getOverview(sessionId: string): Promise<ApiResponse<DashboardOverview>> {
  const { data } = await api.get(`/sessions/${sessionId}/overview`);
  return data;
}

export async function getFieldAnalysis(sessionId: string, fieldName: string): Promise<ApiResponse<FieldAnalysis>> {
  const { data } = await api.get(`/sessions/${sessionId}/fields/${fieldName}`);
  return data;
}

export async function getCorrelation(sessionId: string): Promise<ApiResponse<CorrelationResult>> {
  const { data } = await api.get(`/sessions/${sessionId}/correlation`);
  return data;
}

export async function getCharts(sessionId: string): Promise<ApiResponse<ChartConfig[]>> {
  const { data } = await api.get(`/sessions/${sessionId}/charts`);
  return data;
}

export async function getSamples(): Promise<ApiResponse<Record<string, { name: string; description: string; rows: number }>>> {
  const { data } = await api.get('/samples');
  return data;
}

export async function loadSample(sampleId: string): Promise<ApiResponse<UploadResponse>> {
  const { data } = await api.post(`/samples/${sampleId}/load`);
  return data;
}

export async function getInsights(sessionId: string): Promise<ApiResponse<Insight[]>> {
  const { data } = await api.get(`/sessions/${sessionId}/insights`);
  return data;
}

export async function getKeyDrivers(sessionId: string, target: string): Promise<ApiResponse<KeyDriver[]>> {
  const { data } = await api.get(`/sessions/${sessionId}/drivers`, { params: { target } });
  return data;
}

export async function getHistory(): Promise<ApiResponse<{ id: string; filename: string; file_size: number; row_count: number; column_count: number; state: string; created_at: string }[]>> {
  const { data } = await api.get('/history');
  return data;
}

export async function deleteSession(sessionId: string): Promise<ApiResponse<null>> {
  const { data } = await api.delete(`/sessions/${sessionId}`);
  return data;
}

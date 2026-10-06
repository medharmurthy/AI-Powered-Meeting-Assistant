import type { HealthResponse, RunState, RunSummary } from './types';

const API_BASE = '/api';

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) {
    throw new Error(`Failed to fetch health: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchRuns(): Promise<RunSummary[]> {
  const res = await fetch(`${API_BASE}/runs`);
  if (!res.ok) {
    throw new Error(`Failed to list runs: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchRun(id: string): Promise<RunState> {
  const res = await fetch(`${API_BASE}/runs/${id}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch run ${id}: ${res.statusText}`);
  }
  return res.json();
}

export async function createRun(
  file: File,
  glossary?: string[],
  participants?: string[]
): Promise<{ run_id: string }> {
  const formData = new FormData();
  formData.append('file', file);
  if (glossary && glossary.length > 0) {
    formData.append('glossary', JSON.stringify(glossary));
  }
  if (participants && participants.length > 0) {
    formData.append('participants', JSON.stringify(participants));
  }

  const res = await fetch(`${API_BASE}/runs`, {
    method: 'POST',
    body: formData,
  });

  const data = await res.json();
  if (!res.ok) {
    throw data.error || new Error(res.statusText);
  }
  return data;
}

export async function createSampleRun(): Promise<{ run_id: string }> {
  const res = await fetch(`${API_BASE}/runs/sample`, {
    method: 'POST',
  });
  const data = await res.json();
  if (!res.ok) {
    throw data.error || new Error(res.statusText);
  }
  return data;
}

export async function patchCorrection(
  runId: string,
  cid: string,
  applied: boolean
): Promise<{ status: string; record_stale: boolean }> {
  const res = await fetch(`${API_BASE}/runs/${runId}/corrections/${cid}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ applied }),
  });
  if (!res.ok) {
    throw new Error(`Failed to patch correction: ${res.statusText}`);
  }
  return res.json();
}

export async function rerunStage(
  runId: string,
  fromStage: 'refine' | 'document'
): Promise<{ run_id: string }> {
  const res = await fetch(`${API_BASE}/runs/${runId}/rerun`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ from_stage: fromStage }),
  });
  const data = await res.json();
  if (!res.ok) {
    throw data.error || new Error(res.statusText);
  }
  return data;
}

export async function deleteRun(runId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/runs/${runId}`, {
    method: 'DELETE',
  });
  if (!res.ok && res.status !== 204) {
    throw new Error(`Failed to delete run: ${res.statusText}`);
  }
}

export function getExportUrl(runId: string, filename: string): string {
  return `${API_BASE}/runs/${runId}/export/${filename}`;
}

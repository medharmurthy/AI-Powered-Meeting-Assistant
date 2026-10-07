export interface Word {
  w: string;
  start: number;
  end: number;
  p?: number | null;
}

export interface Segment {
  id: number;
  start: number;
  end: number;
  text: string;
  speaker?: string | null;
  words?: Word[];
}

export interface RawTranscript {
  segments: Segment[];
  duration: number;
  language: string;
  model: string;
  device: string;
}

export interface DomainProfile {
  topic: string;
  domain: string;
  likely_terms: string[];
  names: string[];
}

export type CorrectionStatus = 'applied' | 'reverted' | 'blocked';
export type CorrectionSource = 'model' | 'propagated';

export interface Correction {
  id: string;
  segment_id: number;
  original: string;
  corrected: string;
  reason: string;
  status: CorrectionStatus;
  block_reason?: string | null;
  source?: CorrectionSource;
}

export interface Span {
  start: number;
  end: number;
  correction_id: string;
}

export interface RefinedSegment {
  id: number;
  start: number;
  end: number;
  text: string;
  spans: Span[];
}

export interface RefinedTranscript {
  segments: RefinedSegment[];
  corrections: Correction[];
  profile: DomainProfile;
  model: string;
}

export interface Point {
  text: string;
  segment_ids: number[];
}

export interface MinutesTopic {
  title: string;
  points: Point[];
}

export interface Decision {
  id: string;
  text: string;
  rationale?: string | null;
  segment_ids: number[];
  quote?: string | null;
}

export type UnresolvedKind = 'proposal' | 'question' | 'deferred' | 'possible_task';

export interface Unresolved {
  id: string;
  kind: UnresolvedKind;
  text: string;
  segment_ids: number[];
}

export interface ActionItem {
  id: string;
  task: string;
  owner?: string | null;
  deadline?: string | null;
  segment_ids: number[];
  quote?: string | null;
}

export interface Dropped {
  section: string;
  text: string;
  reason: string;
}

export interface MeetingRecord {
  schema_version: string;
  title: string;
  summary: string;
  attendees: string[];
  minutes: MinutesTopic[];
  decisions: Decision[];
  unresolved: Unresolved[];
  action_items: ActionItem[];
  models: Record<string, string>;
  source_file: string;
  generated_at: string;
  dropped: Dropped[];
}

export interface AppError {
  code: string;
  title: string;
  detail: string;
  fix?: string | null;
  stage?: string | null;
  retryable: boolean;
}

export interface ModelInfo {
  model: string;
  installed: boolean;
}

export interface HealthResponse {
  profile: string;
  gpu: {
    available: boolean;
    name?: string | null;
    vram_gb?: number | null;
  };
  stt: {
    model: string;
    device: string;
  };
  llm: {
    reachable: boolean;
    refiner: ModelInfo;
    documenter: ModelInfo;
  };
  issues: AppError[];
}

export interface RunSummary {
  id: string;
  filename: string;
  created_at: string;
  duration?: number | null;
  status: string;
  title?: string | null;
}

export type Stage = 'ingest' | 'transcribe' | 'refine' | 'document';

export interface RunState {
  id: string;
  filename: string;
  fake?: boolean;
  status: 'queued' | 'running' | 'done' | 'failed';
  stage: Stage | null;
  queuePosition?: number;
  duration?: number;
  audioUrl?: string;
  peaks?: number[];
  models: { stt?: string; refiner?: string; documenter?: string };
  timings: Partial<Record<Stage, number>>;
  progress: Partial<Record<Stage, { done: number; total: number; label: string }>>;
  raw: Segment[];
  refined: RefinedSegment[] | null;
  corrections: Correction[];
  profile?: DomainProfile;
  record: {
    title?: string;
    summary?: string;
    attendees?: string[];
    minutes?: MinutesTopic[];
    decisions?: Decision[];
    unresolved?: Unresolved[];
    action_items?: ActionItem[];
    dropped?: Dropped[];
  };
  recordStale: boolean;
  warnings: AppError[];
  error?: AppError;
  exportParity?: {
    decisions: number;
    tasks: number;
    ok: boolean;
  };
}

export interface RunEvent {
  seq: number;
  type: string;
  data: any;
  t: number;
}

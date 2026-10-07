from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class Word(BaseModel):
    w: str
    start: float
    end: float
    p: float | None = None


class Segment(BaseModel):
    id: int
    start: float
    end: float
    text: str
    speaker: str | None = None  # null unless optional diarization is on
    words: list[Word] = Field(default_factory=list)


class RawTranscript(BaseModel):
    segments: list[Segment]
    duration: float
    language: str
    model: str
    device: str


class DomainProfile(BaseModel):
    topic: str
    domain: str
    likely_terms: list[str]
    names: list[str]


class Proposal(BaseModel):
    segment_id: int
    original: str
    corrected: str
    reason: str


class ProposalList(BaseModel):
    corrections: list[Proposal] = Field(default_factory=list)


class Correction(BaseModel):
    id: str  # "c1", "c2", ...
    segment_id: int
    original: str
    corrected: str
    reason: str
    status: Literal["applied", "reverted", "blocked"]  # reverted = user turned it off
    block_reason: str | None = None  # plain-language, shown in UI
    source: Literal["model", "propagated"] = "model"


class Span(BaseModel):
    start: int
    end: int
    correction_id: str  # offsets into refined text


class RefinedSegment(BaseModel):
    id: int
    start: float
    end: float
    text: str
    spans: list[Span] = Field(default_factory=list)


class RefinedTranscript(BaseModel):
    segments: list[RefinedSegment]
    corrections: list[Correction]
    profile: DomainProfile
    model: str


class Point(BaseModel):
    text: str
    segment_ids: list[int]


class MinutesTopic(BaseModel):
    title: str
    points: list[Point]


class Decision(BaseModel):
    id: str
    text: str
    rationale: str | None = None
    segment_ids: list[int]
    quote: str | None = None


class Unresolved(BaseModel):
    id: str
    kind: Literal["proposal", "question", "deferred", "possible_task"]
    text: str
    segment_ids: list[int]


class ActionItem(BaseModel):
    id: str
    task: str
    owner: str | None = None  # null => "Unspecified"
    deadline: str | None = None  # null => "Unspecified"
    segment_ids: list[int]
    quote: str | None = None


class Dropped(BaseModel):
    section: str
    text: str
    reason: str


class MeetingRecord(BaseModel):
    schema_version: str = "1.0"
    title: str
    summary: str
    attendees: list[str]
    minutes: list[MinutesTopic]
    decisions: list[Decision]
    unresolved: list[Unresolved]
    action_items: list[ActionItem]
    models: dict[str, str]  # stt, refiner, documenter
    source_file: str
    generated_at: str
    dropped: list[Dropped] = Field(default_factory=list)


class AppError(BaseModel):
    code: str
    title: str
    detail: str
    fix: str | None = None
    stage: str | None = None
    retryable: bool = False


# Health & System schemas
class GpuInfo(BaseModel):
    available: bool
    name: str | None = None
    vram_gb: float | None = None


class SttInfo(BaseModel):
    model: str
    device: str


class ModelInfo(BaseModel):
    model: str
    installed: bool


class LlmInfo(BaseModel):
    reachable: bool
    refiner: ModelInfo
    documenter: ModelInfo


class HealthResponse(BaseModel):
    profile: str
    gpu: GpuInfo
    stt: SttInfo
    llm: LlmInfo
    issues: list[AppError] = Field(default_factory=list)


# Run & Workspace schemas
class RunSummary(BaseModel):
    id: str
    filename: str
    created_at: str
    duration: float | None = None
    status: str
    title: str | None = None


class RunState(BaseModel):
    id: str
    filename: str
    fake: bool = False
    status: Literal["queued", "running", "done", "failed"] = "queued"
    stage: Literal["ingest", "transcribe", "refine", "document"] | None = None
    queuePosition: int | None = None
    duration: float | None = None
    audioUrl: str | None = None
    peaks: list[float] | None = None
    models: dict[str, str] = Field(default_factory=dict)
    timings: dict[str, float] = Field(default_factory=dict)
    progress: dict[str, Any] = Field(default_factory=dict)
    raw: list[Segment] = Field(default_factory=list)
    refined: list[RefinedSegment] | None = None
    corrections: list[Correction] = Field(default_factory=list)
    profile: DomainProfile | None = None
    record: dict[str, Any] = Field(default_factory=dict)
    recordStale: bool = False
    warnings: list[AppError] = Field(default_factory=list)
    error: AppError | None = None
    exportParity: dict[str, Any] | None = None

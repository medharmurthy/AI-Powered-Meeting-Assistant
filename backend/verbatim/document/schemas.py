from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field

from verbatim.schemas import MinutesTopic, Point


class SummaryResponse(BaseModel):
    title: str
    summary: str
    attendees: list[str] = Field(default_factory=list)


class MinutesResponse(BaseModel):
    topics: list[MinutesTopic] = Field(default_factory=list)


class RawDecisionItem(BaseModel):
    text: str
    rationale: str | None = None
    segment_ids: list[int] = Field(default_factory=list)
    quote: str | None = None


class RawUnresolvedItem(BaseModel):
    kind: Literal["proposal", "question", "deferred", "possible_task"]
    text: str
    segment_ids: list[int] = Field(default_factory=list)


class DecisionsResponse(BaseModel):
    decisions: list[RawDecisionItem] = Field(default_factory=list)
    unresolved: list[RawUnresolvedItem] = Field(default_factory=list)


class RawActionItem(BaseModel):
    task: str
    owner: str | None = None
    deadline: str | None = None
    segment_ids: list[int] = Field(default_factory=list)
    quote: str | None = None


class RawPossibleTask(BaseModel):
    text: str
    segment_ids: list[int] = Field(default_factory=list)


class ActionsResponse(BaseModel):
    actions: list[RawActionItem] = Field(default_factory=list)
    possible_tasks: list[RawPossibleTask] = Field(default_factory=list)


class VerifyItemResult(BaseModel):
    id: str
    verdict: Literal["agreed", "proposal_only", "unsupported", "committed", "tentative"]
    owner_stated: bool = True
    deadline_stated: bool = True


class VerifyResponse(BaseModel):
    results: list[VerifyItemResult] = Field(default_factory=list)

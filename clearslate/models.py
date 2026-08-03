"""
Core Pydantic models for ClearSlate.
Spec 3.3 element record, 9-category enum, run state machine.
"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ElementCategory(str, Enum):
    CHARACTER_NAME = "character_name"
    BUSINESS_ORG = "business_org"
    LOCATION_ADDRESS = "location_address"
    PHONE_URL_EMAIL = "phone_url_email"
    PRODUCT_BRAND = "product_brand"
    REFERENCED_WORK = "referenced_work"
    REAL_PERSON = "real_person"
    ON_SCREEN_TEXT = "on_screen_text"
    VEHICLE_IDENTIFIER = "vehicle_identifier"


class ElementStatus(str, Enum):
    PENDING = "pending"
    RESEARCHING = "researching"
    RESEARCHED = "researched"
    RESEARCH_INCOMPLETE = "research_incomplete"
    GRADED = "graded"


class Grade(str, Enum):
    CLEAR = "CLEAR"
    CAUTION = "CAUTION"
    CONFLICT = "CONFLICT"


class Finding(BaseModel):
    source: Literal["parallel_search", "parallel_task", "uspto", "code_rule"]
    query: str
    url: str | None = None
    excerpt: str | None = None
    published: str | None = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Alternative(BaseModel):
    text: str
    verified_clean: bool = False
    verified_at: datetime | None = None


class Element(BaseModel):
    """Spec 3.3 element record — stable shape for Firestore docs and API JSON."""

    id: str
    category: ElementCategory
    text: str
    normalized_text: str
    pages: list[int]
    scene: str | None = None
    context_snippet: str
    status: ElementStatus = ElementStatus.PENDING
    findings: list[Finding] = Field(default_factory=list)
    grade: Grade | None = None
    rule_citation: str | None = None
    alternatives: list[Alternative] = Field(default_factory=list)


class PageText(BaseModel):
    page: int  # 1-indexed absolute
    text: str


class ParsedScript(BaseModel):
    source_format: Literal["pdf", "fountain", "text"]
    pages: list[PageText]
    page_count: int
    scene_headings: list[tuple[int, str]] = Field(default_factory=list)


class RunState(str, Enum):
    PENDING = "PENDING"
    BREAKDOWN = "BREAKDOWN"
    AWAITING_START = "AWAITING_START"
    RESEARCH = "RESEARCH"
    GRADING = "GRADING"
    REPORT = "REPORT"
    DONE = "DONE"
    FAILED = "FAILED"


class CostEstimate(BaseModel):
    element_count: int
    search_requests: int
    task_runs: int
    gemini_usd: float
    parallel_usd: float
    total_usd: float
    basis: Literal["pages", "elements"]


class RunRecord(BaseModel):
    run_id: str
    state: RunState
    created_at: datetime
    source_format: str
    page_count: int
    element_count: int | None = None
    counts_by_category: dict[ElementCategory, int] | None = None
    cost_estimate: CostEstimate | None = None
    error: str | None = None

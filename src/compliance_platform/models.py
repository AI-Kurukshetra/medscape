from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class Lesson:
    title: str
    content: str
    estimated_minutes: int


@dataclass(frozen=True)
class TrainingModule:
    module_id: str
    code: str
    title: str
    description: str
    regulation: str
    lessons: Sequence[Lesson]


@dataclass(frozen=True)
class User:
    user_id: str
    full_name: str
    email: str


@dataclass(frozen=True)
class UserProgress:
    progress_id: str
    user_id: str
    module_id: str
    lessons_completed: int
    total_lessons: int
    completion_rate: float
    assessment_score: float | None
    time_spent_minutes: int
    completed_at: str | None
    updated_at: str


@dataclass(frozen=True)
class Certification:
    certification_id: str
    certificate_number: str
    user_id: str
    module_id: str
    issued_at: str
    expires_at: str
    status: str


@dataclass(frozen=True)
class AssessmentQuestion:
    question_id: str
    assessment_id: str
    question_order: int
    prompt: str
    options: Sequence[str]
    correct_option: str


@dataclass(frozen=True)
class Assessment:
    assessment_id: str
    module_id: str
    title: str
    pass_score: float
    questions: Sequence[AssessmentQuestion]


@dataclass(frozen=True)
class AssessmentAttempt:
    attempt_id: str
    user_id: str
    assessment_id: str
    score: float
    passed: bool
    correct_answers: int
    total_questions: int
    submitted_at: str


@dataclass(frozen=True)
class Notification:
    notification_id: str
    user_id: str
    notification_type: str
    title: str
    message: str
    status: str
    metadata_json: str
    created_at: str


@dataclass(frozen=True)
class Organization:
    organization_id: str
    name: str
    slug: str
    branding_json: str
    created_at: str


@dataclass(frozen=True)
class MobileDevice:
    device_id: str
    user_id: str
    platform: str
    app_version: str
    push_enabled: bool
    last_seen_at: str


@dataclass(frozen=True)
class OfflineSyncRecord:
    sync_id: str
    user_id: str
    module_id: str
    status: str
    progress_snapshot_json: str
    last_synced_at: str


@dataclass(frozen=True)
class AuditLog:
    audit_id: str
    event_type: str
    actor_user_id: str | None
    organization_slug: str | None
    entity_type: str
    entity_id: str
    action: str
    metadata_json: str
    created_at: str

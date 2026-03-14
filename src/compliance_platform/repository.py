from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List

from .models import (
    Assessment,
    AssessmentAttempt,
    AssessmentQuestion,
    AuditLog,
    Certification,
    Lesson,
    Notification,
    MobileDevice,
    OfflineSyncRecord,
    Organization,
    TrainingModule,
    User,
    UserProgress,
)


class TrainingModuleRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._initialize()

    @contextmanager
    def _connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.commit()
            conn.close()

    def _initialize(self) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS organizations (
                    organization_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    slug TEXT UNIQUE NOT NULL,
                    branding_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    full_name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS training_modules (
                    module_id TEXT PRIMARY KEY,
                    code TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    regulation TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS lessons (
                    lesson_id TEXT PRIMARY KEY,
                    module_id TEXT NOT NULL REFERENCES training_modules(module_id) ON DELETE CASCADE,
                    lesson_order INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    estimated_minutes INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_lessons_module_id ON lessons(module_id)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_progress (
                    progress_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    module_id TEXT NOT NULL REFERENCES training_modules(module_id) ON DELETE CASCADE,
                    lessons_completed INTEGER NOT NULL,
                    total_lessons INTEGER NOT NULL,
                    completion_rate REAL NOT NULL,
                    assessment_score REAL,
                    time_spent_minutes INTEGER NOT NULL,
                    completed_at TEXT,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, module_id)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_progress_user_id ON user_progress(user_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_progress_module_id ON user_progress(module_id)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS certifications (
                    certification_id TEXT PRIMARY KEY,
                    certificate_number TEXT UNIQUE NOT NULL,
                    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    module_id TEXT NOT NULL REFERENCES training_modules(module_id) ON DELETE CASCADE,
                    issued_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    UNIQUE(user_id, module_id)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_certifications_user_id ON certifications(user_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_certifications_module_id ON certifications(module_id)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS assessments (
                    assessment_id TEXT PRIMARY KEY,
                    module_id TEXT NOT NULL REFERENCES training_modules(module_id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    pass_score REAL NOT NULL,
                    UNIQUE(module_id, title)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS assessment_questions (
                    question_id TEXT PRIMARY KEY,
                    assessment_id TEXT NOT NULL REFERENCES assessments(assessment_id) ON DELETE CASCADE,
                    question_order INTEGER NOT NULL,
                    prompt TEXT NOT NULL,
                    options_json TEXT NOT NULL,
                    correct_option TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS assessment_attempts (
                    attempt_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    assessment_id TEXT NOT NULL REFERENCES assessments(assessment_id) ON DELETE CASCADE,
                    score REAL NOT NULL,
                    passed INTEGER NOT NULL,
                    correct_answers INTEGER NOT NULL,
                    total_questions INTEGER NOT NULL,
                    submitted_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_assessments_module_id ON assessments(module_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_assessment_questions_assessment_id ON assessment_questions(assessment_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_assessment_attempts_user_id ON assessment_attempts(user_id)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_roles (
                    user_id TEXT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
                    role_name TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS role_training_paths (
                    role_name TEXT NOT NULL,
                    module_id TEXT NOT NULL REFERENCES training_modules(module_id) ON DELETE CASCADE,
                    path_order INTEGER NOT NULL,
                    PRIMARY KEY(role_name, module_id)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_role_training_paths_role ON role_training_paths(role_name)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notifications (
                    notification_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    notification_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    status TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_notifications_user_created ON notifications(user_id, created_at DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(notification_type)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS organization_users (
                    organization_id TEXT NOT NULL REFERENCES organizations(organization_id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    PRIMARY KEY (organization_id, user_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS organization_modules (
                    organization_id TEXT NOT NULL REFERENCES organizations(organization_id) ON DELETE CASCADE,
                    module_id TEXT NOT NULL REFERENCES training_modules(module_id) ON DELETE CASCADE,
                    PRIMARY KEY (organization_id, module_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS organization_user_roles (
                    organization_id TEXT NOT NULL REFERENCES organizations(organization_id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    role_name TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (organization_id, user_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS organization_role_training_paths (
                    organization_id TEXT NOT NULL REFERENCES organizations(organization_id) ON DELETE CASCADE,
                    role_name TEXT NOT NULL,
                    module_id TEXT NOT NULL REFERENCES training_modules(module_id) ON DELETE CASCADE,
                    path_order INTEGER NOT NULL,
                    PRIMARY KEY (organization_id, role_name, module_id)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_organization_users_user ON organization_users(user_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_organization_modules_module ON organization_modules(module_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_org_role_paths_role ON organization_role_training_paths(organization_id, role_name)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS mobile_devices (
                    device_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    platform TEXT NOT NULL,
                    app_version TEXT NOT NULL,
                    push_enabled INTEGER NOT NULL,
                    last_seen_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS offline_sync_records (
                    sync_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    module_id TEXT NOT NULL REFERENCES training_modules(module_id) ON DELETE CASCADE,
                    status TEXT NOT NULL,
                    progress_snapshot_json TEXT NOT NULL,
                    last_synced_at TEXT NOT NULL,
                    UNIQUE(user_id, module_id)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mobile_devices_user_id ON mobile_devices(user_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_offline_sync_user_id ON offline_sync_records(user_id)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    audit_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    actor_user_id TEXT,
                    organization_slug TEXT,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_logs_actor_user_id ON audit_logs(actor_user_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_logs_organization_slug ON audit_logs(organization_slug)"
            )
            self._ensure_default_organization(conn)

    def create_module(
        self,
        *,
        code: str,
        title: str,
        description: str,
        regulation: str,
        lessons: Iterable[Lesson],
    ) -> TrainingModule:
        module_id = str(uuid.uuid4())
        normalized_lessons = list(lessons)
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO training_modules (module_id, code, title, description, regulation)
                VALUES (?, ?, ?, ?, ?)
                """,
                (module_id, code, title, description, regulation),
            )
            conn.executemany(
                """
                INSERT INTO lessons (lesson_id, module_id, lesson_order, title, content, estimated_minutes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        str(uuid.uuid4()),
                        module_id,
                        order,
                        lesson.title,
                        lesson.content,
                        lesson.estimated_minutes,
                    )
                    for order, lesson in enumerate(normalized_lessons, start=1)
                ],
            )
        return TrainingModule(
            module_id=module_id,
            code=code,
            title=title,
            description=description,
            regulation=regulation,
            lessons=normalized_lessons,
        )

    def create_organization(
        self, *, name: str, slug: str, branding: Dict[str, object] | None = None
    ) -> Organization:
        now = datetime.now(timezone.utc).isoformat()
        branding_json = json.dumps(branding or {})
        with self._connection() as conn:
            existing = conn.execute(
                """
                SELECT organization_id, name, slug, branding_json, created_at
                FROM organizations
                WHERE slug = ?
                """,
                (slug,),
            ).fetchone()
            if existing is not None:
                return self._row_to_organization(existing)

            org_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO organizations (organization_id, name, slug, branding_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (org_id, name, slug, branding_json, now),
            )
            created = conn.execute(
                """
                SELECT organization_id, name, slug, branding_json, created_at
                FROM organizations
                WHERE organization_id = ?
                """,
                (org_id,),
            ).fetchone()
            if created is None:
                raise ValueError("Failed to create organization.")
            return self._row_to_organization(created)

    def list_organizations(self) -> List[Organization]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT organization_id, name, slug, branding_json, created_at
                FROM organizations
                ORDER BY created_at ASC
                """
            ).fetchall()
            return [self._row_to_organization(row) for row in rows]

    def set_organization_branding(
        self, *, slug: str, branding: Dict[str, object]
    ) -> Organization:
        with self._connection() as conn:
            conn.execute(
                "UPDATE organizations SET branding_json = ? WHERE slug = ?",
                (json.dumps(branding), slug),
            )
            row = conn.execute(
                """
                SELECT organization_id, name, slug, branding_json, created_at
                FROM organizations
                WHERE slug = ?
                """,
                (slug,),
            ).fetchone()
            if row is None:
                raise ValueError(f"Organization not found: {slug}")
            return self._row_to_organization(row)

    def add_user_to_organization(self, *, user_id: str, organization_slug: str) -> None:
        with self._connection() as conn:
            organization_id = self._get_organization_id(conn, organization_slug)
            conn.execute(
                """
                INSERT OR IGNORE INTO organization_users (organization_id, user_id)
                VALUES (?, ?)
                """,
                (organization_id, user_id),
            )

    def add_module_to_organization(self, *, module_code: str, organization_slug: str) -> None:
        with self._connection() as conn:
            organization_id = self._get_organization_id(conn, organization_slug)
            module = conn.execute(
                "SELECT module_id FROM training_modules WHERE code = ?",
                (module_code,),
            ).fetchone()
            if module is None:
                raise ValueError(f"Module not found for code: {module_code}")
            conn.execute(
                """
                INSERT OR IGNORE INTO organization_modules (organization_id, module_id)
                VALUES (?, ?)
                """,
                (organization_id, module["module_id"]),
            )

    def list_modules_by_organization(self, organization_slug: str) -> List[TrainingModule]:
        with self._connection() as conn:
            organization_id = self._get_organization_id(conn, organization_slug)
            rows = conn.execute(
                """
                SELECT tm.module_id, tm.code, tm.title, tm.description, tm.regulation
                FROM organization_modules om
                JOIN training_modules tm ON tm.module_id = om.module_id
                WHERE om.organization_id = ?
                ORDER BY tm.code
                """,
                (organization_id,),
            ).fetchall()
            return [self._build_module(conn, row["module_id"], row) for row in rows]

    def assign_user_role_in_organization(
        self, *, user_id: str, organization_slug: str, role_name: str
    ) -> Dict[str, str]:
        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            organization_id = self._get_organization_id(conn, organization_slug)
            conn.execute(
                """
                INSERT INTO organization_user_roles (organization_id, user_id, role_name, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(organization_id, user_id) DO UPDATE SET
                    role_name = excluded.role_name,
                    updated_at = excluded.updated_at
                """,
                (organization_id, user_id, role_name, now),
            )
            return {
                "organization_slug": organization_slug,
                "user_id": user_id,
                "role_name": role_name,
                "updated_at": now,
            }

    def set_role_training_path_in_organization(
        self, *, organization_slug: str, role_name: str, module_codes: List[str]
    ) -> Dict[str, object]:
        if not module_codes:
            raise ValueError("Role training path must include at least one module.")
        with self._connection() as conn:
            organization_id = self._get_organization_id(conn, organization_slug)
            rows = conn.execute(
                """
                SELECT tm.module_id, tm.code
                FROM organization_modules om
                JOIN training_modules tm ON tm.module_id = om.module_id
                WHERE om.organization_id = ?
                  AND tm.code IN ({})
                """.format(",".join(["?"] * len(module_codes))),
                (organization_id, *module_codes),
            ).fetchall()
            found = {r["code"] for r in rows}
            missing = [c for c in module_codes if c not in found]
            if missing:
                raise ValueError(
                    f"Modules must be linked to organization before path assignment: {missing}"
                )
            by_code = {r["code"]: r["module_id"] for r in rows}
            conn.execute(
                """
                DELETE FROM organization_role_training_paths
                WHERE organization_id = ? AND role_name = ?
                """,
                (organization_id, role_name),
            )
            for idx, code in enumerate(module_codes, start=1):
                conn.execute(
                    """
                    INSERT INTO organization_role_training_paths (
                        organization_id, role_name, module_id, path_order
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (organization_id, role_name, by_code[code], idx),
                )
            return {
                "organization_slug": organization_slug,
                "role_name": role_name,
                "module_codes": module_codes,
            }

    def get_user_training_path_in_organization(
        self, *, user_id: str, organization_slug: str
    ) -> Dict[str, object]:
        with self._connection() as conn:
            organization_id = self._get_organization_id(conn, organization_slug)
            role_row = conn.execute(
                """
                SELECT role_name
                FROM organization_user_roles
                WHERE organization_id = ? AND user_id = ?
                """,
                (organization_id, user_id),
            ).fetchone()
            if role_row is None:
                raise ValueError("User role is not assigned for organization.")
            role_name = role_row["role_name"]
            rows = conn.execute(
                """
                SELECT tm.code, tm.title, tm.regulation, ortp.path_order
                FROM organization_role_training_paths ortp
                JOIN training_modules tm ON tm.module_id = ortp.module_id
                WHERE ortp.organization_id = ? AND ortp.role_name = ?
                ORDER BY ortp.path_order
                """,
                (organization_id, role_name),
            ).fetchall()
            return {
                "organization_slug": organization_slug,
                "user_id": user_id,
                "role_name": role_name,
                "modules": [
                    {
                        "code": row["code"],
                        "title": row["title"],
                        "regulation": row["regulation"],
                        "path_order": int(row["path_order"]),
                    }
                    for row in rows
                ],
            }

    def get_organization_dashboard(self, organization_slug: str) -> Dict[str, object]:
        with self._connection() as conn:
            organization_id = self._get_organization_id(conn, organization_slug)
            users = conn.execute(
                "SELECT user_id FROM organization_users WHERE organization_id = ?",
                (organization_id,),
            ).fetchall()
            modules = conn.execute(
                "SELECT module_id FROM organization_modules WHERE organization_id = ?",
                (organization_id,),
            ).fetchall()
            user_ids = [row["user_id"] for row in users]
            module_ids = [row["module_id"] for row in modules]
            if not user_ids or not module_ids:
                return {
                    "organization_slug": organization_slug,
                    "overview": {
                        "total_users": len(user_ids),
                        "total_modules": len(module_ids),
                        "progress_records": 0,
                        "avg_completion_rate": 0.0,
                    },
                }
            progress = conn.execute(
                """
                SELECT COUNT(*) AS c, AVG(completion_rate) AS avg_rate
                FROM user_progress
                WHERE user_id IN ({}) AND module_id IN ({})
                """.format(",".join(["?"] * len(user_ids)), ",".join(["?"] * len(module_ids))),
                (*user_ids, *module_ids),
            ).fetchone()
            return {
                "organization_slug": organization_slug,
                "overview": {
                    "total_users": len(user_ids),
                    "total_modules": len(module_ids),
                    "progress_records": int(progress["c"]) if progress else 0,
                    "avg_completion_rate": round(float(progress["avg_rate"]), 2)
                    if progress and progress["avg_rate"] is not None
                    else 0.0,
                },
            }

    def register_mobile_device(
        self,
        *,
        user_id: str,
        device_id: str,
        platform: str,
        app_version: str,
        push_enabled: bool = True,
    ) -> MobileDevice:
        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO mobile_devices (
                    device_id, user_id, platform, app_version, push_enabled, last_seen_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(device_id) DO UPDATE SET
                    user_id = excluded.user_id,
                    platform = excluded.platform,
                    app_version = excluded.app_version,
                    push_enabled = excluded.push_enabled,
                    last_seen_at = excluded.last_seen_at
                """,
                (device_id, user_id, platform, app_version, 1 if push_enabled else 0, now),
            )
            row = conn.execute(
                """
                SELECT device_id, user_id, platform, app_version, push_enabled, last_seen_at
                FROM mobile_devices
                WHERE device_id = ?
                """,
                (device_id,),
            ).fetchone()
            if row is None:
                raise ValueError("Failed to register mobile device.")
            return self._row_to_mobile_device(row)

    def list_mobile_devices(self, *, user_id: str) -> List[MobileDevice]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT device_id, user_id, platform, app_version, push_enabled, last_seen_at
                FROM mobile_devices
                WHERE user_id = ?
                ORDER BY last_seen_at DESC
                """,
                (user_id,),
            ).fetchall()
            return [self._row_to_mobile_device(row) for row in rows]

    def upsert_offline_sync(
        self,
        *,
        user_id: str,
        module_code: str,
        status: str,
        progress_snapshot: Dict[str, object] | None = None,
    ) -> OfflineSyncRecord:
        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            module = conn.execute(
                "SELECT module_id FROM training_modules WHERE code = ?",
                (module_code,),
            ).fetchone()
            if module is None:
                raise ValueError(f"Module not found for code: {module_code}")
            module_id = module["module_id"]
            payload = json.dumps(progress_snapshot or {})
            existing = conn.execute(
                """
                SELECT sync_id FROM offline_sync_records
                WHERE user_id = ? AND module_id = ?
                """,
                (user_id, module_id),
            ).fetchone()
            if existing is None:
                sync_id = str(uuid.uuid4())
                conn.execute(
                    """
                    INSERT INTO offline_sync_records (
                        sync_id, user_id, module_id, status, progress_snapshot_json, last_synced_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (sync_id, user_id, module_id, status, payload, now),
                )
            else:
                sync_id = existing["sync_id"]
                conn.execute(
                    """
                    UPDATE offline_sync_records
                    SET status = ?, progress_snapshot_json = ?, last_synced_at = ?
                    WHERE sync_id = ?
                    """,
                    (status, payload, now, sync_id),
                )
            row = conn.execute(
                """
                SELECT sync_id, user_id, module_id, status, progress_snapshot_json, last_synced_at
                FROM offline_sync_records
                WHERE sync_id = ?
                """,
                (sync_id,),
            ).fetchone()
            if row is None:
                raise ValueError("Failed to upsert offline sync record.")
            return self._row_to_offline_sync(row)

    def list_offline_sync_records(self, *, user_id: str) -> List[Dict[str, object]]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT osr.sync_id, osr.user_id, osr.module_id, osr.status, osr.progress_snapshot_json, osr.last_synced_at,
                       tm.code AS module_code, tm.title AS module_title
                FROM offline_sync_records osr
                JOIN training_modules tm ON tm.module_id = osr.module_id
                WHERE osr.user_id = ?
                ORDER BY osr.last_synced_at DESC
                """,
                (user_id,),
            ).fetchall()
            return [
                {
                    "sync_id": row["sync_id"],
                    "user_id": row["user_id"],
                    "module_id": row["module_id"],
                    "module_code": row["module_code"],
                    "module_title": row["module_title"],
                    "status": row["status"],
                    "progress_snapshot_json": row["progress_snapshot_json"],
                    "last_synced_at": row["last_synced_at"],
                }
                for row in rows
            ]

    def get_mobile_learning_feed(self, *, user_id: str, limit: int = 10) -> List[Dict[str, object]]:
        due_modules = self.get_due_modules_for_user(user_id)
        with self._connection() as conn:
            progress_rows = conn.execute(
                """
                SELECT tm.code, tm.title, tm.regulation, up.completion_rate, up.updated_at
                FROM user_progress up
                JOIN training_modules tm ON tm.module_id = up.module_id
                WHERE up.user_id = ?
                ORDER BY up.updated_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
            feed: List[Dict[str, object]] = []
            due_codes = {item["module_code"] for item in due_modules}
            for row in progress_rows:
                feed.append(
                    {
                        "module_code": row["code"],
                        "title": row["title"],
                        "regulation": row["regulation"],
                        "completion_rate": float(row["completion_rate"]),
                        "priority": "due" if row["code"] in due_codes else "in_progress",
                        "updated_at": row["updated_at"],
                    }
                )
            for due in due_modules:
                if len(feed) >= limit:
                    break
                if due["module_code"] in {item["module_code"] for item in feed}:
                    continue
                feed.append(
                    {
                        "module_code": due["module_code"],
                        "title": due["module_title"],
                        "regulation": None,
                        "completion_rate": 0.0,
                        "priority": "due",
                        "updated_at": None,
                    }
                )
            return feed[:limit]

    def create_audit_log(
        self,
        *,
        event_type: str,
        actor_user_id: str | None,
        organization_slug: str | None,
        entity_type: str,
        entity_id: str,
        action: str,
        metadata: Dict[str, object] | None = None,
    ) -> AuditLog:
        now = datetime.now(timezone.utc).isoformat()
        audit_id = str(uuid.uuid4())
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO audit_logs (
                    audit_id, event_type, actor_user_id, organization_slug, entity_type,
                    entity_id, action, metadata_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_id,
                    event_type,
                    actor_user_id,
                    organization_slug,
                    entity_type,
                    entity_id,
                    action,
                    json.dumps(metadata or {}),
                    now,
                ),
            )
            row = conn.execute(
                """
                SELECT audit_id, event_type, actor_user_id, organization_slug, entity_type,
                       entity_id, action, metadata_json, created_at
                FROM audit_logs
                WHERE audit_id = ?
                """,
                (audit_id,),
            ).fetchone()
            if row is None:
                raise ValueError("Failed to create audit log.")
            return self._row_to_audit_log(row)

    def list_audit_logs(
        self,
        *,
        limit: int = 200,
        actor_user_id: str | None = None,
        organization_slug: str | None = None,
        action: str | None = None,
    ) -> List[AuditLog]:
        query = """
            SELECT audit_id, event_type, actor_user_id, organization_slug, entity_type,
                   entity_id, action, metadata_json, created_at
            FROM audit_logs
            WHERE 1=1
        """
        params: List[object] = []
        if actor_user_id is not None:
            query += " AND actor_user_id = ?"
            params.append(actor_user_id)
        if organization_slug is not None:
            query += " AND organization_slug = ?"
            params.append(organization_slug)
        if action is not None:
            query += " AND action = ?"
            params.append(action)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self._connection() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
            return [self._row_to_audit_log(row) for row in rows]

    def list_modules(self) -> List[TrainingModule]:
        with self._connection() as conn:
            module_rows = conn.execute(
                """
                SELECT module_id, code, title, description, regulation
                FROM training_modules
                ORDER BY code
                """
            ).fetchall()
            return [self._build_module(conn, row["module_id"], row) for row in module_rows]

    def get_module_by_code(self, code: str) -> TrainingModule | None:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT module_id, code, title, description, regulation
                FROM training_modules
                WHERE code = ?
                """,
                (code,),
            ).fetchone()
            if row is None:
                return None
            return self._build_module(conn, row["module_id"], row)

    def upsert_user(self, *, full_name: str, email: str) -> User:
        with self._connection() as conn:
            existing = conn.execute(
                "SELECT user_id, full_name, email FROM users WHERE email = ?",
                (email,),
            ).fetchone()
            if existing is not None:
                conn.execute(
                    "UPDATE users SET full_name = ? WHERE user_id = ?",
                    (full_name, existing["user_id"]),
                )
                return User(
                    user_id=existing["user_id"], full_name=full_name, email=existing["email"]
                )

            user_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO users (user_id, full_name, email) VALUES (?, ?, ?)",
                (user_id, full_name, email),
            )
            return User(user_id=user_id, full_name=full_name, email=email)

    def upsert_progress(
        self,
        *,
        user_id: str,
        module_code: str,
        lessons_completed: int,
        assessment_score: float | None,
        time_spent_minutes: int,
    ) -> UserProgress:
        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            module_row = conn.execute(
                "SELECT module_id FROM training_modules WHERE code = ?",
                (module_code,),
            ).fetchone()
            if module_row is None:
                raise ValueError(f"Module not found for code: {module_code}")

            module_id = module_row["module_id"]
            total_lessons_row = conn.execute(
                "SELECT COUNT(*) AS lesson_count FROM lessons WHERE module_id = ?",
                (module_id,),
            ).fetchone()
            total_lessons = int(total_lessons_row["lesson_count"]) if total_lessons_row else 0
            bounded_lessons = min(max(lessons_completed, 0), total_lessons)
            completion_rate = (
                round((bounded_lessons / total_lessons) * 100, 2) if total_lessons > 0 else 0.0
            )
            completed_at = now if bounded_lessons == total_lessons and total_lessons > 0 else None

            existing = conn.execute(
                """
                SELECT progress_id, completed_at
                FROM user_progress
                WHERE user_id = ? AND module_id = ?
                """,
                (user_id, module_id),
            ).fetchone()
            if existing is None:
                progress_id = str(uuid.uuid4())
                conn.execute(
                    """
                    INSERT INTO user_progress (
                        progress_id, user_id, module_id, lessons_completed, total_lessons,
                        completion_rate, assessment_score, time_spent_minutes, completed_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        progress_id,
                        user_id,
                        module_id,
                        bounded_lessons,
                        total_lessons,
                        completion_rate,
                        assessment_score,
                        time_spent_minutes,
                        completed_at,
                        now,
                    ),
                )
            else:
                progress_id = existing["progress_id"]
                effective_completed_at = existing["completed_at"] or completed_at
                conn.execute(
                    """
                    UPDATE user_progress
                    SET lessons_completed = ?,
                        total_lessons = ?,
                        completion_rate = ?,
                        assessment_score = ?,
                        time_spent_minutes = ?,
                        completed_at = ?,
                        updated_at = ?
                    WHERE progress_id = ?
                    """,
                    (
                        bounded_lessons,
                        total_lessons,
                        completion_rate,
                        assessment_score,
                        time_spent_minutes,
                        effective_completed_at,
                        now,
                        progress_id,
                    ),
                )

            return self._get_progress_by_id(conn, progress_id)

    def list_user_progress(self, user_id: str) -> List[UserProgress]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT progress_id, user_id, module_id, lessons_completed, total_lessons,
                       completion_rate, assessment_score, time_spent_minutes, completed_at, updated_at
                FROM user_progress
                WHERE user_id = ?
                ORDER BY updated_at DESC
                """,
                (user_id,),
            ).fetchall()
            return [self._row_to_progress(row) for row in rows]

    def get_module_progress_summary(self, module_code: str) -> Dict[str, float | int]:
        with self._connection() as conn:
            module_row = conn.execute(
                "SELECT module_id FROM training_modules WHERE code = ?",
                (module_code,),
            ).fetchone()
            if module_row is None:
                raise ValueError(f"Module not found for code: {module_code}")

            module_id = module_row["module_id"]
            summary = conn.execute(
                """
                SELECT
                    COUNT(*) AS tracked_users,
                    AVG(completion_rate) AS avg_completion_rate,
                    AVG(assessment_score) AS avg_assessment_score,
                    SUM(time_spent_minutes) AS total_time_spent_minutes,
                    SUM(CASE WHEN completed_at IS NOT NULL THEN 1 ELSE 0 END) AS completed_users
                FROM user_progress
                WHERE module_id = ?
                """,
                (module_id,),
            ).fetchone()
            tracked_users = int(summary["tracked_users"]) if summary and summary["tracked_users"] else 0
            completed_users = int(summary["completed_users"]) if summary and summary["completed_users"] else 0
            return {
                "tracked_users": tracked_users,
                "completed_users": completed_users,
                "avg_completion_rate": round(float(summary["avg_completion_rate"]), 2)
                if summary and summary["avg_completion_rate"] is not None
                else 0.0,
                "avg_assessment_score": round(float(summary["avg_assessment_score"]), 2)
                if summary and summary["avg_assessment_score"] is not None
                else 0.0,
                "total_time_spent_minutes": int(summary["total_time_spent_minutes"])
                if summary and summary["total_time_spent_minutes"] is not None
                else 0,
            }

    def create_assessment(
        self,
        *,
        module_code: str,
        title: str,
        pass_score: float,
        questions: List[Dict[str, object]],
    ) -> Assessment:
        if not questions:
            raise ValueError("Assessment must include at least one question.")
        with self._connection() as conn:
            module = conn.execute(
                "SELECT module_id FROM training_modules WHERE code = ?",
                (module_code,),
            ).fetchone()
            if module is None:
                raise ValueError(f"Module not found for code: {module_code}")
            module_id = module["module_id"]

            existing = conn.execute(
                """
                SELECT assessment_id FROM assessments WHERE module_id = ? AND title = ?
                """,
                (module_id, title),
            ).fetchone()
            if existing is not None:
                return self._get_assessment_by_id(conn, existing["assessment_id"])

            assessment_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO assessments (assessment_id, module_id, title, pass_score)
                VALUES (?, ?, ?, ?)
                """,
                (assessment_id, module_id, title, pass_score),
            )
            for idx, question in enumerate(questions, start=1):
                options = question.get("options")
                correct_option = question.get("correct_option")
                prompt = question.get("prompt")
                if (
                    not isinstance(options, list)
                    or not options
                    or not isinstance(correct_option, str)
                    or correct_option not in options
                    or not isinstance(prompt, str)
                ):
                    raise ValueError("Invalid question payload.")
                conn.execute(
                    """
                    INSERT INTO assessment_questions (
                        question_id, assessment_id, question_order, prompt, options_json, correct_option
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        assessment_id,
                        idx,
                        prompt,
                        json.dumps(options),
                        correct_option,
                    ),
                )
            return self._get_assessment_by_id(conn, assessment_id)

    def get_assessment(self, *, module_code: str, title: str) -> Assessment | None:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT a.assessment_id
                FROM assessments a
                JOIN training_modules m ON m.module_id = a.module_id
                WHERE m.code = ? AND a.title = ?
                """,
                (module_code, title),
            ).fetchone()
            if row is None:
                return None
            return self._get_assessment_by_id(conn, row["assessment_id"])

    def submit_assessment(
        self,
        *,
        user_id: str,
        module_code: str,
        title: str,
        answers: Dict[str, str],
    ) -> AssessmentAttempt:
        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            assessment = self.get_assessment(module_code=module_code, title=title)
            if assessment is None:
                raise ValueError("Assessment not found.")
            correct = 0
            for question in assessment.questions:
                selected = answers.get(question.question_id)
                if selected == question.correct_option:
                    correct += 1
            total = len(assessment.questions)
            score = round((correct / total) * 100, 2) if total else 0.0
            passed = score >= assessment.pass_score
            attempt_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO assessment_attempts (
                    attempt_id, user_id, assessment_id, score, passed, correct_answers, total_questions, submitted_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attempt_id,
                    user_id,
                    assessment.assessment_id,
                    score,
                    1 if passed else 0,
                    correct,
                    total,
                    now,
                ),
            )
            return AssessmentAttempt(
                attempt_id=attempt_id,
                user_id=user_id,
                assessment_id=assessment.assessment_id,
                score=score,
                passed=passed,
                correct_answers=correct,
                total_questions=total,
                submitted_at=now,
            )

    def list_assessment_attempts(self, *, user_id: str) -> List[AssessmentAttempt]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT attempt_id, user_id, assessment_id, score, passed, correct_answers, total_questions, submitted_at
                FROM assessment_attempts
                WHERE user_id = ?
                ORDER BY submitted_at DESC
                """,
                (user_id,),
            ).fetchall()
            return [
                AssessmentAttempt(
                    attempt_id=row["attempt_id"],
                    user_id=row["user_id"],
                    assessment_id=row["assessment_id"],
                    score=float(row["score"]),
                    passed=bool(row["passed"]),
                    correct_answers=int(row["correct_answers"]),
                    total_questions=int(row["total_questions"]),
                    submitted_at=row["submitted_at"],
                )
                for row in rows
            ]

    def assign_user_role(self, *, user_id: str, role_name: str) -> Dict[str, str]:
        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO user_roles (user_id, role_name, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    role_name = excluded.role_name,
                    updated_at = excluded.updated_at
                """,
                (user_id, role_name, now),
            )
            return {"user_id": user_id, "role_name": role_name, "updated_at": now}

    def set_role_training_path(self, *, role_name: str, module_codes: List[str]) -> Dict[str, object]:
        if not module_codes:
            raise ValueError("Role training path must include at least one module.")
        with self._connection() as conn:
            modules = conn.execute(
                """
                SELECT module_id, code
                FROM training_modules
                WHERE code IN ({})
                """.format(",".join(["?"] * len(module_codes))),
                tuple(module_codes),
            ).fetchall()
            if len(modules) != len(set(module_codes)):
                found_codes = {m["code"] for m in modules}
                missing = [code for code in module_codes if code not in found_codes]
                raise ValueError(f"Unknown module codes in role path: {missing}")

            conn.execute("DELETE FROM role_training_paths WHERE role_name = ?", (role_name,))
            module_id_by_code = {row["code"]: row["module_id"] for row in modules}
            for idx, code in enumerate(module_codes, start=1):
                conn.execute(
                    """
                    INSERT INTO role_training_paths (role_name, module_id, path_order)
                    VALUES (?, ?, ?)
                    """,
                    (role_name, module_id_by_code[code], idx),
                )
            return {"role_name": role_name, "module_codes": module_codes}

    def get_user_training_path(self, *, user_id: str) -> Dict[str, object]:
        with self._connection() as conn:
            role_row = conn.execute(
                "SELECT role_name FROM user_roles WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if role_row is None:
                raise ValueError("User role is not assigned.")
            role_name = role_row["role_name"]
            rows = conn.execute(
                """
                SELECT m.code, m.title, m.regulation, rtp.path_order
                FROM role_training_paths rtp
                JOIN training_modules m ON m.module_id = rtp.module_id
                WHERE rtp.role_name = ?
                ORDER BY rtp.path_order
                """,
                (role_name,),
            ).fetchall()
            modules = [
                {
                    "code": row["code"],
                    "title": row["title"],
                    "regulation": row["regulation"],
                    "path_order": int(row["path_order"]),
                }
                for row in rows
            ]
            return {"user_id": user_id, "role_name": role_name, "modules": modules}

    def get_compliance_dashboard(self) -> Dict[str, object]:
        with self._connection() as conn:
            user_count_row = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()
            module_count_row = conn.execute("SELECT COUNT(*) AS c FROM training_modules").fetchone()
            progress_row = conn.execute(
                """
                SELECT
                    COUNT(*) AS progress_records,
                    AVG(completion_rate) AS avg_completion_rate,
                    SUM(CASE WHEN completed_at IS NOT NULL THEN 1 ELSE 0 END) AS completed_records,
                    SUM(time_spent_minutes) AS total_time_spent_minutes
                FROM user_progress
                """
            ).fetchone()
            cert_row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total_certifications,
                    SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS active_certifications
                FROM certifications
                """
            ).fetchone()
            assess_row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total_attempts,
                    AVG(score) AS avg_score,
                    SUM(CASE WHEN passed = 1 THEN 1 ELSE 0 END) AS passed_attempts
                FROM assessment_attempts
                """
            ).fetchone()
            role_rows = conn.execute(
                """
                SELECT role_name, COUNT(*) AS user_count
                FROM user_roles
                GROUP BY role_name
                ORDER BY user_count DESC, role_name ASC
                """
            ).fetchall()
            module_rows = conn.execute(
                """
                SELECT
                    m.code AS module_code,
                    m.regulation AS regulation,
                    COUNT(up.progress_id) AS tracked_users,
                    AVG(up.completion_rate) AS avg_completion_rate
                FROM training_modules m
                LEFT JOIN user_progress up ON up.module_id = m.module_id
                GROUP BY m.module_id, m.code, m.regulation
                ORDER BY avg_completion_rate DESC, tracked_users DESC, m.code ASC
                """
            ).fetchall()

            user_count = int(user_count_row["c"]) if user_count_row else 0
            module_count = int(module_count_row["c"]) if module_count_row else 0
            progress_records = int(progress_row["progress_records"]) if progress_row else 0
            completed_records = int(progress_row["completed_records"]) if progress_row and progress_row["completed_records"] is not None else 0

            overview = {
                "total_users": user_count,
                "total_modules": module_count,
                "progress_records": progress_records,
                "completed_records": completed_records,
                "completion_record_rate": round((completed_records / progress_records) * 100, 2)
                if progress_records > 0
                else 0.0,
                "avg_completion_rate": round(float(progress_row["avg_completion_rate"]), 2)
                if progress_row and progress_row["avg_completion_rate"] is not None
                else 0.0,
                "total_time_spent_minutes": int(progress_row["total_time_spent_minutes"])
                if progress_row and progress_row["total_time_spent_minutes"] is not None
                else 0,
            }
            certifications = {
                "total_certifications": int(cert_row["total_certifications"])
                if cert_row and cert_row["total_certifications"] is not None
                else 0,
                "active_certifications": int(cert_row["active_certifications"])
                if cert_row and cert_row["active_certifications"] is not None
                else 0,
            }
            assessments = {
                "total_attempts": int(assess_row["total_attempts"])
                if assess_row and assess_row["total_attempts"] is not None
                else 0,
                "avg_score": round(float(assess_row["avg_score"]), 2)
                if assess_row and assess_row["avg_score"] is not None
                else 0.0,
                "pass_rate": round(
                    (int(assess_row["passed_attempts"]) / int(assess_row["total_attempts"])) * 100, 2
                )
                if assess_row
                and assess_row["total_attempts"] is not None
                and int(assess_row["total_attempts"]) > 0
                else 0.0,
            }
            role_distribution = [
                {"role_name": row["role_name"], "user_count": int(row["user_count"])}
                for row in role_rows
            ]
            module_performance = [
                {
                    "module_code": row["module_code"],
                    "regulation": row["regulation"],
                    "tracked_users": int(row["tracked_users"]),
                    "avg_completion_rate": round(float(row["avg_completion_rate"]), 2)
                    if row["avg_completion_rate"] is not None
                    else 0.0,
                }
                for row in module_rows
            ]
            return {
                "overview": overview,
                "certifications": certifications,
                "assessments": assessments,
                "role_distribution": role_distribution,
                "module_performance": module_performance,
            }

    def create_notification(
        self,
        *,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        metadata: Dict[str, object] | None = None,
    ) -> Notification:
        now = datetime.now(timezone.utc).isoformat()
        notification_id = str(uuid.uuid4())
        metadata_json = json.dumps(metadata or {})
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO notifications (
                    notification_id, user_id, notification_type, title, message, status, metadata_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    notification_id,
                    user_id,
                    notification_type,
                    title,
                    message,
                    "unread",
                    metadata_json,
                    now,
                ),
            )
            row = conn.execute(
                """
                SELECT notification_id, user_id, notification_type, title, message, status, metadata_json, created_at
                FROM notifications WHERE notification_id = ?
                """,
                (notification_id,),
            ).fetchone()
            if row is None:
                raise ValueError("Failed to create notification.")
            return self._row_to_notification(row)

    def list_notifications(self, *, user_id: str, limit: int = 50) -> List[Notification]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT notification_id, user_id, notification_type, title, message, status, metadata_json, created_at
                FROM notifications
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
            return [self._row_to_notification(row) for row in rows]

    def mark_notification_as_read(self, notification_id: str) -> Notification:
        with self._connection() as conn:
            conn.execute(
                "UPDATE notifications SET status = 'read' WHERE notification_id = ?",
                (notification_id,),
            )
            row = conn.execute(
                """
                SELECT notification_id, user_id, notification_type, title, message, status, metadata_json, created_at
                FROM notifications WHERE notification_id = ?
                """,
                (notification_id,),
            ).fetchone()
            if row is None:
                raise ValueError("Notification not found.")
            return self._row_to_notification(row)

    def get_due_modules_for_user(self, user_id: str) -> List[Dict[str, object]]:
        with self._connection() as conn:
            role_row = conn.execute(
                "SELECT role_name FROM user_roles WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if role_row is None:
                return []
            rows = conn.execute(
                """
                SELECT m.module_id, m.code, m.title
                FROM role_training_paths rtp
                JOIN training_modules m ON m.module_id = rtp.module_id
                LEFT JOIN user_progress up ON up.module_id = m.module_id AND up.user_id = ?
                WHERE rtp.role_name = ?
                  AND (up.progress_id IS NULL OR up.completion_rate < 100)
                ORDER BY rtp.path_order
                """,
                (user_id, role_row["role_name"]),
            ).fetchall()
            return [
                {
                    "module_id": row["module_id"],
                    "module_code": row["code"],
                    "module_title": row["title"],
                }
                for row in rows
            ]

    def get_users_with_failed_assessments(self, pass_threshold: float = 70.0) -> List[Dict[str, object]]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                WITH latest_attempt AS (
                    SELECT
                        aa.user_id,
                        aa.assessment_id,
                        aa.score,
                        aa.submitted_at,
                        ROW_NUMBER() OVER (
                            PARTITION BY aa.user_id, aa.assessment_id
                            ORDER BY aa.submitted_at DESC
                        ) AS rn
                    FROM assessment_attempts aa
                )
                SELECT
                    la.user_id,
                    a.title AS assessment_title,
                    m.code AS module_code,
                    la.score
                FROM latest_attempt la
                JOIN assessments a ON a.assessment_id = la.assessment_id
                JOIN training_modules m ON m.module_id = a.module_id
                WHERE la.rn = 1
                  AND la.score < ?
                """,
                (pass_threshold,),
            ).fetchall()
            return [
                {
                    "user_id": row["user_id"],
                    "assessment_title": row["assessment_title"],
                    "module_code": row["module_code"],
                    "score": float(row["score"]),
                }
                for row in rows
            ]

    def get_certifications_expiring_within_days(self, days: int) -> List[Dict[str, object]]:
        now = datetime.now(timezone.utc)
        end = now + timedelta(days=days)
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT c.user_id, c.certificate_number, c.expires_at, m.code AS module_code
                FROM certifications c
                JOIN training_modules m ON m.module_id = c.module_id
                WHERE c.status = 'active'
                """
            ).fetchall()
            expiring: List[Dict[str, object]] = []
            for row in rows:
                exp_at = datetime.fromisoformat(row["expires_at"])
                if now <= exp_at <= end:
                    expiring.append(
                        {
                            "user_id": row["user_id"],
                            "certificate_number": row["certificate_number"],
                            "module_code": row["module_code"],
                            "expires_at": row["expires_at"],
                        }
                    )
            return expiring

    def list_user_ids(self) -> List[str]:
        with self._connection() as conn:
            rows = conn.execute("SELECT user_id FROM users ORDER BY user_id").fetchall()
            return [row["user_id"] for row in rows]

    def list_user_ids_by_organization(self, organization_slug: str) -> List[str]:
        with self._connection() as conn:
            organization_id = self._get_organization_id(conn, organization_slug)
            rows = conn.execute(
                """
                SELECT user_id
                FROM organization_users
                WHERE organization_id = ?
                ORDER BY user_id
                """,
                (organization_id,),
            ).fetchall()
            return [row["user_id"] for row in rows]

    def issue_certification(
        self, *, user_id: str, module_code: str, valid_for_days: int = 365
    ) -> Certification:
        now = datetime.now(timezone.utc)
        issued_at = now.isoformat()
        expires_at = (now + timedelta(days=valid_for_days)).isoformat()
        with self._connection() as conn:
            module = conn.execute(
                "SELECT module_id FROM training_modules WHERE code = ?",
                (module_code,),
            ).fetchone()
            if module is None:
                raise ValueError(f"Module not found for code: {module_code}")

            module_id = module["module_id"]
            progress = conn.execute(
                """
                SELECT completion_rate
                FROM user_progress
                WHERE user_id = ? AND module_id = ?
                """,
                (user_id, module_id),
            ).fetchone()
            if progress is None or float(progress["completion_rate"]) < 100.0:
                raise ValueError("User is not eligible for certification until module completion is 100%.")

            existing = conn.execute(
                """
                SELECT certification_id, certificate_number, user_id, module_id, issued_at, expires_at, status
                FROM certifications
                WHERE user_id = ? AND module_id = ?
                """,
                (user_id, module_id),
            ).fetchone()
            if existing is not None:
                return self._row_to_certification(existing)

            certification_id = str(uuid.uuid4())
            certificate_number = f"CERT-{module_code}-{uuid.uuid4().hex[:10].upper()}"
            conn.execute(
                """
                INSERT INTO certifications (
                    certification_id, certificate_number, user_id, module_id, issued_at, expires_at, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    certification_id,
                    certificate_number,
                    user_id,
                    module_id,
                    issued_at,
                    expires_at,
                    "active",
                ),
            )
            created = conn.execute(
                """
                SELECT certification_id, certificate_number, user_id, module_id, issued_at, expires_at, status
                FROM certifications
                WHERE certification_id = ?
                """,
                (certification_id,),
            ).fetchone()
            if created is None:
                raise ValueError("Failed to create certification.")
            return self._row_to_certification(created)

    def list_user_certifications(self, user_id: str) -> List[Certification]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT certification_id, certificate_number, user_id, module_id, issued_at, expires_at, status
                FROM certifications
                WHERE user_id = ?
                ORDER BY issued_at DESC
                """,
                (user_id,),
            ).fetchall()
            return [self._row_to_certification(row) for row in rows]

    def get_certification_by_number(self, certificate_number: str) -> Certification | None:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT certification_id, certificate_number, user_id, module_id, issued_at, expires_at, status
                FROM certifications
                WHERE certificate_number = ?
                """,
                (certificate_number,),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_certification(row)

    def _build_module(
        self, conn: sqlite3.Connection, module_id: str, module_row: sqlite3.Row
    ) -> TrainingModule:
        lesson_rows = conn.execute(
            """
            SELECT title, content, estimated_minutes
            FROM lessons
            WHERE module_id = ?
            ORDER BY lesson_order
            """,
            (module_id,),
        ).fetchall()
        lessons = [
            Lesson(
                title=lesson_row["title"],
                content=lesson_row["content"],
                estimated_minutes=lesson_row["estimated_minutes"],
            )
            for lesson_row in lesson_rows
        ]
        return TrainingModule(
            module_id=module_row["module_id"],
            code=module_row["code"],
            title=module_row["title"],
            description=module_row["description"],
            regulation=module_row["regulation"],
            lessons=lessons,
        )

    def _get_progress_by_id(self, conn: sqlite3.Connection, progress_id: str) -> UserProgress:
        row = conn.execute(
            """
            SELECT progress_id, user_id, module_id, lessons_completed, total_lessons,
                   completion_rate, assessment_score, time_spent_minutes, completed_at, updated_at
            FROM user_progress
            WHERE progress_id = ?
            """,
            (progress_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"Progress not found: {progress_id}")
        return self._row_to_progress(row)

    def _row_to_progress(self, row: sqlite3.Row) -> UserProgress:
        return UserProgress(
            progress_id=row["progress_id"],
            user_id=row["user_id"],
            module_id=row["module_id"],
            lessons_completed=int(row["lessons_completed"]),
            total_lessons=int(row["total_lessons"]),
            completion_rate=float(row["completion_rate"]),
            assessment_score=float(row["assessment_score"])
            if row["assessment_score"] is not None
            else None,
            time_spent_minutes=int(row["time_spent_minutes"]),
            completed_at=row["completed_at"],
            updated_at=row["updated_at"],
        )

    def _row_to_certification(self, row: sqlite3.Row) -> Certification:
        return Certification(
            certification_id=row["certification_id"],
            certificate_number=row["certificate_number"],
            user_id=row["user_id"],
            module_id=row["module_id"],
            issued_at=row["issued_at"],
            expires_at=row["expires_at"],
            status=row["status"],
        )

    def _get_assessment_by_id(self, conn: sqlite3.Connection, assessment_id: str) -> Assessment:
        assessment_row = conn.execute(
            """
            SELECT assessment_id, module_id, title, pass_score
            FROM assessments
            WHERE assessment_id = ?
            """,
            (assessment_id,),
        ).fetchone()
        if assessment_row is None:
            raise ValueError(f"Assessment not found: {assessment_id}")
        question_rows = conn.execute(
            """
            SELECT question_id, assessment_id, question_order, prompt, options_json, correct_option
            FROM assessment_questions
            WHERE assessment_id = ?
            ORDER BY question_order
            """,
            (assessment_id,),
        ).fetchall()
        questions = [
            AssessmentQuestion(
                question_id=row["question_id"],
                assessment_id=row["assessment_id"],
                question_order=int(row["question_order"]),
                prompt=row["prompt"],
                options=json.loads(row["options_json"]),
                correct_option=row["correct_option"],
            )
            for row in question_rows
        ]
        return Assessment(
            assessment_id=assessment_row["assessment_id"],
            module_id=assessment_row["module_id"],
            title=assessment_row["title"],
            pass_score=float(assessment_row["pass_score"]),
            questions=questions,
        )

    def _row_to_notification(self, row: sqlite3.Row) -> Notification:
        return Notification(
            notification_id=row["notification_id"],
            user_id=row["user_id"],
            notification_type=row["notification_type"],
            title=row["title"],
            message=row["message"],
            status=row["status"],
            metadata_json=row["metadata_json"],
            created_at=row["created_at"],
        )

    def _row_to_organization(self, row: sqlite3.Row) -> Organization:
        return Organization(
            organization_id=row["organization_id"],
            name=row["name"],
            slug=row["slug"],
            branding_json=row["branding_json"],
            created_at=row["created_at"],
        )

    def _row_to_mobile_device(self, row: sqlite3.Row) -> MobileDevice:
        return MobileDevice(
            device_id=row["device_id"],
            user_id=row["user_id"],
            platform=row["platform"],
            app_version=row["app_version"],
            push_enabled=bool(row["push_enabled"]),
            last_seen_at=row["last_seen_at"],
        )

    def _row_to_offline_sync(self, row: sqlite3.Row) -> OfflineSyncRecord:
        return OfflineSyncRecord(
            sync_id=row["sync_id"],
            user_id=row["user_id"],
            module_id=row["module_id"],
            status=row["status"],
            progress_snapshot_json=row["progress_snapshot_json"],
            last_synced_at=row["last_synced_at"],
        )

    def _row_to_audit_log(self, row: sqlite3.Row) -> AuditLog:
        return AuditLog(
            audit_id=row["audit_id"],
            event_type=row["event_type"],
            actor_user_id=row["actor_user_id"],
            organization_slug=row["organization_slug"],
            entity_type=row["entity_type"],
            entity_id=row["entity_id"],
            action=row["action"],
            metadata_json=row["metadata_json"],
            created_at=row["created_at"],
        )

    def _get_organization_id(self, conn: sqlite3.Connection, slug: str) -> str:
        row = conn.execute(
            "SELECT organization_id FROM organizations WHERE slug = ?",
            (slug,),
        ).fetchone()
        if row is None:
            raise ValueError(f"Organization not found: {slug}")
        return row["organization_id"]

    def _ensure_default_organization(self, conn: sqlite3.Connection) -> None:
        exists = conn.execute(
            "SELECT organization_id FROM organizations WHERE slug = 'default'"
        ).fetchone()
        if exists is not None:
            return
        conn.execute(
            """
            INSERT INTO organizations (organization_id, name, slug, branding_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                "Default Organization",
                "default",
                json.dumps({"theme": "light"}),
                datetime.now(timezone.utc).isoformat(),
            ),
        )

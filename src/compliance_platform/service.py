from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .models import Lesson, TrainingModule
from .repository import TrainingModuleRepository


class HipaaTrainingService:
    def __init__(self, repository: TrainingModuleRepository) -> None:
        self.repository = repository

    def seed_default_modules(self) -> List[TrainingModule]:
        defaults = self._default_modules()
        created: List[TrainingModule] = []
        for module in defaults:
            existing = self.repository.get_module_by_code(module["code"])
            if existing is not None:
                self.repository.add_module_to_organization(
                    module_code=module["code"], organization_slug="default"
                )
                continue
            created_module = self.repository.create_module(
                code=module["code"],
                title=module["title"],
                description=module["description"],
                regulation=module.get("regulation", "HIPAA"),
                lessons=module["lessons"],
            )
            self.repository.add_module_to_organization(
                module_code=module["code"], organization_slug="default"
            )
            created.append(created_module)
        return created

    def create_module(
        self,
        *,
        code: str,
        title: str,
        description: str,
        lessons: Iterable[Lesson],
        regulation: str = "HIPAA",
        organization_slug: str = "default",
    ) -> TrainingModule:
        module = self.repository.create_module(
            code=code,
            title=title,
            description=description,
            regulation=regulation,
            lessons=lessons,
        )
        self.repository.add_module_to_organization(
            module_code=code, organization_slug=organization_slug
        )
        self._audit(
            event_type="module.created",
            entity_type="training_module",
            entity_id=module.module_id,
            action="create_module",
            organization_slug=organization_slug,
            metadata={"code": code, "regulation": regulation},
        )
        return module

    def register_user(
        self, *, full_name: str, email: str, organization_slug: str = "default"
    ) -> Dict[str, Any]:
        user = self.repository.upsert_user(full_name=full_name, email=email)
        self.repository.add_user_to_organization(
            user_id=user.user_id, organization_slug=organization_slug
        )
        self._audit(
            event_type="user.registered",
            actor_user_id=user.user_id,
            organization_slug=organization_slug,
            entity_type="user",
            entity_id=user.user_id,
            action="register_user",
            metadata={"email": email, "full_name": full_name},
        )
        return asdict(user)

    def create_organization(
        self, *, name: str, slug: str, branding: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        organization = self.repository.create_organization(name=name, slug=slug, branding=branding)
        self._audit(
            event_type="organization.created",
            organization_slug=slug,
            entity_type="organization",
            entity_id=organization.organization_id,
            action="create_organization",
            metadata={"name": name},
        )
        payload = asdict(organization)
        payload["branding"] = json.loads(payload.pop("branding_json"))
        return payload

    def list_organizations(self) -> List[Dict[str, Any]]:
        organizations = self.repository.list_organizations()
        output: List[Dict[str, Any]] = []
        for organization in organizations:
            payload = asdict(organization)
            payload["branding"] = json.loads(payload.pop("branding_json"))
            output.append(payload)
        return output

    def set_organization_branding(self, *, slug: str, branding: Dict[str, Any]) -> Dict[str, Any]:
        organization = self.repository.set_organization_branding(slug=slug, branding=branding)
        self._audit(
            event_type="organization.branding_updated",
            organization_slug=slug,
            entity_type="organization",
            entity_id=organization.organization_id,
            action="set_organization_branding",
            metadata={"branding_keys": sorted(list(branding.keys()))},
        )
        payload = asdict(organization)
        payload["branding"] = json.loads(payload.pop("branding_json"))
        return payload

    def track_user_progress(
        self,
        *,
        user_id: str,
        module_code: str,
        lessons_completed: int,
        assessment_score: float | None,
        time_spent_minutes: int,
    ) -> Dict[str, Any]:
        progress = self.repository.upsert_progress(
            user_id=user_id,
            module_code=module_code,
            lessons_completed=lessons_completed,
            assessment_score=assessment_score,
            time_spent_minutes=time_spent_minutes,
        )
        self._audit(
            event_type="progress.updated",
            actor_user_id=user_id,
            entity_type="user_progress",
            entity_id=progress.progress_id,
            action="track_user_progress",
            metadata={
                "module_code": module_code,
                "completion_rate": progress.completion_rate,
                "assessment_score": assessment_score,
                "time_spent_minutes": time_spent_minutes,
            },
        )
        return asdict(progress)

    def get_user_progress(self, user_id: str) -> List[Dict[str, Any]]:
        return [asdict(progress) for progress in self.repository.list_user_progress(user_id)]

    def get_module_progress_summary(self, module_code: str) -> Dict[str, Any]:
        summary = self.repository.get_module_progress_summary(module_code)
        summary["module_code"] = module_code
        return summary

    def issue_certification(
        self, *, user_id: str, module_code: str, valid_for_days: int = 365
    ) -> Dict[str, Any]:
        cert = self.repository.issue_certification(
            user_id=user_id, module_code=module_code, valid_for_days=valid_for_days
        )
        self._audit(
            event_type="certification.issued",
            actor_user_id=user_id,
            entity_type="certification",
            entity_id=cert.certification_id,
            action="issue_certification",
            metadata={"module_code": module_code, "certificate_number": cert.certificate_number},
        )
        return asdict(cert)

    def list_user_certifications(self, user_id: str) -> List[Dict[str, Any]]:
        return [asdict(cert) for cert in self.repository.list_user_certifications(user_id)]

    def verify_certificate(self, certificate_number: str) -> Dict[str, Any] | None:
        cert = self.repository.get_certification_by_number(certificate_number)
        if cert is None:
            return None
        payload = asdict(cert)
        payload["is_active"] = cert.status == "active"
        return payload

    def create_assessment(
        self,
        *,
        module_code: str,
        title: str,
        pass_score: float,
        questions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        assessment = self.repository.create_assessment(
            module_code=module_code,
            title=title,
            pass_score=pass_score,
            questions=questions,
        )
        self._audit(
            event_type="assessment.created",
            entity_type="assessment",
            entity_id=assessment.assessment_id,
            action="create_assessment",
            metadata={"module_code": module_code, "title": title, "question_count": len(questions)},
        )
        return asdict(assessment)

    def get_assessment(self, *, module_code: str, title: str) -> Dict[str, Any] | None:
        assessment = self.repository.get_assessment(module_code=module_code, title=title)
        if assessment is None:
            return None
        return asdict(assessment)

    def submit_assessment(
        self,
        *,
        user_id: str,
        module_code: str,
        title: str,
        answers: Dict[str, str],
    ) -> Dict[str, Any]:
        attempt = self.repository.submit_assessment(
            user_id=user_id,
            module_code=module_code,
            title=title,
            answers=answers,
        )
        self._audit(
            event_type="assessment.submitted",
            actor_user_id=user_id,
            entity_type="assessment_attempt",
            entity_id=attempt.attempt_id,
            action="submit_assessment",
            metadata={"module_code": module_code, "title": title, "score": attempt.score},
        )
        return asdict(attempt)

    def list_user_assessment_attempts(self, user_id: str) -> List[Dict[str, Any]]:
        return [asdict(attempt) for attempt in self.repository.list_assessment_attempts(user_id=user_id)]

    def assign_user_role(self, *, user_id: str, role_name: str) -> Dict[str, Any]:
        return self.repository.assign_user_role(user_id=user_id, role_name=role_name)

    def set_role_training_path(self, *, role_name: str, module_codes: List[str]) -> Dict[str, Any]:
        return self.repository.set_role_training_path(role_name=role_name, module_codes=module_codes)

    def get_user_training_path(self, user_id: str) -> Dict[str, Any]:
        return self.repository.get_user_training_path(user_id=user_id)

    def seed_default_role_training_paths(self) -> List[Dict[str, Any]]:
        default_paths = {
            "nurse": ["HIPAA-PRIV-101", "HIPAA-BREACH-301", "HITECH-101"],
            "doctor": ["HIPAA-PRIV-101", "HIPAA-SEC-201", "HITECH-101"],
            "administrator": ["HIPAA-PRIV-101", "SOX-HEALTH-101", "HIPAA-BREACH-301"],
            "it_staff": ["HIPAA-SEC-201", "HIPAA-BREACH-301", "FDA-21CFR11-101"],
        }
        configured: List[Dict[str, Any]] = []
        for role_name, module_codes in default_paths.items():
            configured.append(
                self.set_role_training_path(role_name=role_name, module_codes=module_codes)
            )
        return configured

    def get_compliance_dashboard(self) -> Dict[str, Any]:
        return self.repository.get_compliance_dashboard()

    def send_notification(
        self,
        *,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        metadata: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        notification = self.repository.create_notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            metadata=metadata,
        )
        self._audit(
            event_type="notification.created",
            actor_user_id=user_id,
            entity_type="notification",
            entity_id=notification.notification_id,
            action="send_notification",
            metadata={"notification_type": notification_type, "title": title},
        )
        return self._serialize_notification(notification)

    def list_user_notifications(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        return [
            self._serialize_notification(notification)
            for notification in self.repository.list_notifications(user_id=user_id, limit=limit)
        ]

    def mark_notification_as_read(self, notification_id: str) -> Dict[str, Any]:
        notification = self.repository.mark_notification_as_read(notification_id)
        self._audit(
            event_type="notification.read",
            actor_user_id=notification.user_id,
            entity_type="notification",
            entity_id=notification.notification_id,
            action="mark_notification_as_read",
        )
        return self._serialize_notification(notification)

    def run_notification_automation(
        self, *, renewal_days: int = 30, organization_slug: str | None = None
    ) -> List[Dict[str, Any]]:
        created: List[Dict[str, Any]] = []
        created.extend(self._generate_due_training_notifications(organization_slug))
        created.extend(self._generate_remedial_notifications())
        created.extend(self._generate_renewal_notifications(renewal_days=renewal_days))
        return created

    def _generate_due_training_notifications(
        self, organization_slug: str | None = None
    ) -> List[Dict[str, Any]]:
        created: List[Dict[str, Any]] = []
        for user_id in self._list_all_user_ids(organization_slug=organization_slug):
            due_modules = self.repository.get_due_modules_for_user(user_id)
            for due in due_modules:
                created.append(
                    self.send_notification(
                        user_id=user_id,
                        notification_type="training_due",
                        title="Training Module Due",
                        message=f"Please complete {due['module_code']} - {due['module_title']}.",
                        metadata={"module_code": due["module_code"]},
                    )
                )
        return created

    def _generate_remedial_notifications(self) -> List[Dict[str, Any]]:
        created: List[Dict[str, Any]] = []
        for item in self.repository.get_users_with_failed_assessments():
            created.append(
                self.send_notification(
                    user_id=item["user_id"],
                    notification_type="remedial_training",
                    title="Remedial Training Assigned",
                    message=(
                        f"Your score {item['score']} on {item['assessment_title']} is below pass threshold. "
                        "Additional training has been assigned."
                    ),
                    metadata={
                        "assessment_title": item["assessment_title"],
                        "module_code": item["module_code"],
                        "score": item["score"],
                    },
                )
            )
        return created

    def _generate_renewal_notifications(self, *, renewal_days: int) -> List[Dict[str, Any]]:
        created: List[Dict[str, Any]] = []
        for cert in self.repository.get_certifications_expiring_within_days(renewal_days):
            created.append(
                self.send_notification(
                    user_id=cert["user_id"],
                    notification_type="certification_renewal",
                    title="Certification Renewal Reminder",
                    message=(
                        f"Certificate {cert['certificate_number']} for {cert['module_code']} "
                        f"expires on {cert['expires_at']}."
                    ),
                    metadata={
                        "certificate_number": cert["certificate_number"],
                        "module_code": cert["module_code"],
                        "expires_at": cert["expires_at"],
                    },
                )
            )
        return created

    def _list_all_user_ids(self, organization_slug: str | None = None) -> List[str]:
        if organization_slug is None:
            return self.repository.list_user_ids()
        return self.repository.list_user_ids_by_organization(organization_slug)

    def _serialize_notification(self, notification: Any) -> Dict[str, Any]:
        payload = asdict(notification)
        payload["metadata"] = json.loads(payload.pop("metadata_json"))
        return payload

    def _serialize_audit_log(self, audit_log: Any) -> Dict[str, Any]:
        payload = asdict(audit_log)
        payload["metadata"] = json.loads(payload.pop("metadata_json"))
        return payload

    def _audit(
        self,
        *,
        event_type: str,
        entity_type: str,
        entity_id: str,
        action: str,
        actor_user_id: str | None = None,
        organization_slug: str | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> None:
        self.repository.create_audit_log(
            event_type=event_type,
            actor_user_id=actor_user_id,
            organization_slug=organization_slug,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            metadata=metadata,
        )

    def list_modules(
        self, regulation: str | None = None, organization_slug: str | None = None
    ) -> List[Dict[str, Any]]:
        if organization_slug is not None:
            modules = self.repository.list_modules_by_organization(organization_slug)
        else:
            modules = self.repository.list_modules()
        if regulation is not None:
            modules = [m for m in modules if m.regulation.upper() == regulation.upper()]
        return [self._serialize(module) for module in modules]

    def get_module(self, code: str) -> Dict[str, Any] | None:
        module = self.repository.get_module_by_code(code)
        if module is None:
            return None
        return self._serialize(module)

    def _serialize(self, module: TrainingModule) -> Dict[str, Any]:
        payload = asdict(module)
        payload["total_estimated_minutes"] = sum(
            lesson["estimated_minutes"] for lesson in payload["lessons"]
        )
        return payload

    def _default_modules(self) -> List[Dict[str, Any]]:
        return [
            {
                "code": "HIPAA-PRIV-101",
                "title": "HIPAA Privacy Rule Fundamentals",
                "description": "Covers protected health information, minimum necessary standards, and permitted disclosures.",
                "regulation": "HIPAA",
                "lessons": [
                    Lesson(
                        title="What is PHI?",
                        content="Defines protected health information and practical examples in clinical workflows.",
                        estimated_minutes=12,
                    ),
                    Lesson(
                        title="Minimum Necessary Standard",
                        content="Explains how to limit access and disclosure to the minimum necessary information.",
                        estimated_minutes=10,
                    ),
                    Lesson(
                        title="Patient Rights",
                        content="Reviews access, amendment, accounting of disclosures, and complaint pathways.",
                        estimated_minutes=8,
                    ),
                ],
            },
            {
                "code": "HIPAA-SEC-201",
                "title": "HIPAA Security Rule in Practice",
                "description": "Administrative, physical, and technical safeguards for ePHI handling.",
                "regulation": "HIPAA",
                "lessons": [
                    Lesson(
                        title="Administrative Safeguards",
                        content="Risk analysis, workforce training, and sanction policies required by the Security Rule.",
                        estimated_minutes=14,
                    ),
                    Lesson(
                        title="Physical Safeguards",
                        content="Facility access controls, workstation security, and device/media controls.",
                        estimated_minutes=9,
                    ),
                    Lesson(
                        title="Technical Safeguards",
                        content="Access control, audit controls, integrity, authentication, and transmission security.",
                        estimated_minutes=15,
                    ),
                ],
            },
            {
                "code": "HIPAA-BREACH-301",
                "title": "Breach Notification and Incident Response",
                "description": "Detecting, documenting, and notifying parties after impermissible PHI exposure.",
                "regulation": "HIPAA",
                "lessons": [
                    Lesson(
                        title="Breach Risk Assessment",
                        content="Walkthrough of the four-factor risk assessment required after potential incidents.",
                        estimated_minutes=11,
                    ),
                    Lesson(
                        title="Notification Timelines",
                        content="Covers individual, HHS, and media notification deadlines and thresholds.",
                        estimated_minutes=7,
                    ),
                    Lesson(
                        title="Response Playbook",
                        content="Outlines triage, containment, remediation, and audit-ready evidence collection.",
                        estimated_minutes=13,
                    ),
                ],
            },
            {
                "code": "HITECH-101",
                "title": "HITECH Act Fundamentals",
                "description": "Core HITECH provisions, enforcement changes, and breach expansion requirements.",
                "regulation": "HITECH",
                "lessons": [
                    Lesson(
                        title="Meaningful Use and Incentives",
                        content="Overview of HITECH incentives and implications for EHR adoption and compliance.",
                        estimated_minutes=10,
                    ),
                    Lesson(
                        title="Expanded Enforcement",
                        content="How HITECH strengthened penalties and audit expectations for covered entities.",
                        estimated_minutes=9,
                    ),
                    Lesson(
                        title="Business Associate Obligations",
                        content="Direct obligations for business associates and subcontractor responsibilities.",
                        estimated_minutes=11,
                    ),
                ],
            },
            {
                "code": "SOX-HEALTH-101",
                "title": "SOX Controls for Healthcare Finance",
                "description": "SOX internal controls, financial reporting integrity, and audit readiness for healthcare operators.",
                "regulation": "SOX",
                "lessons": [
                    Lesson(
                        title="Internal Control Framework",
                        content="SOX 302 and 404 controls mapped to healthcare revenue and procurement workflows.",
                        estimated_minutes=12,
                    ),
                    Lesson(
                        title="Evidence and Audit Trail",
                        content="Control evidence retention and segregation-of-duties checks in regulated processes.",
                        estimated_minutes=10,
                    ),
                    Lesson(
                        title="Deficiency Remediation",
                        content="Prioritizing, tracking, and closing control deficiencies before audit cycles.",
                        estimated_minutes=9,
                    ),
                ],
            },
            {
                "code": "FDA-21CFR11-101",
                "title": "FDA 21 CFR Part 11 Essentials",
                "description": "Electronic records/signatures controls for systems used in FDA-regulated activities.",
                "regulation": "FDA",
                "lessons": [
                    Lesson(
                        title="Electronic Record Requirements",
                        content="Validation, audit trails, and retention practices for regulated electronic records.",
                        estimated_minutes=11,
                    ),
                    Lesson(
                        title="Electronic Signatures",
                        content="Identity, non-repudiation, and signature manifestation requirements.",
                        estimated_minutes=8,
                    ),
                    Lesson(
                        title="Operational Controls",
                        content="Access controls, authority checks, and device checks in GxP environments.",
                        estimated_minutes=10,
                    ),
                ],
            },
        ]

    def list_supported_regulations(self) -> List[str]:
        modules = self.repository.list_modules()
        return sorted({module.regulation for module in modules})

    def set_role_training_path_for_organization(
        self, *, organization_slug: str, role_name: str, module_codes: List[str]
    ) -> Dict[str, Any]:
        return self.repository.set_role_training_path_in_organization(
            organization_slug=organization_slug,
            role_name=role_name,
            module_codes=module_codes,
        )

    def assign_user_role_for_organization(
        self, *, user_id: str, organization_slug: str, role_name: str
    ) -> Dict[str, Any]:
        return self.repository.assign_user_role_in_organization(
            user_id=user_id,
            organization_slug=organization_slug,
            role_name=role_name,
        )

    def get_user_training_path_for_organization(
        self, *, user_id: str, organization_slug: str
    ) -> Dict[str, Any]:
        return self.repository.get_user_training_path_in_organization(
            user_id=user_id, organization_slug=organization_slug
        )

    def get_organization_dashboard(self, organization_slug: str) -> Dict[str, Any]:
        return self.repository.get_organization_dashboard(organization_slug)

    def register_mobile_device(
        self,
        *,
        user_id: str,
        device_id: str,
        platform: str,
        app_version: str,
        push_enabled: bool = True,
    ) -> Dict[str, Any]:
        device = self.repository.register_mobile_device(
            user_id=user_id,
            device_id=device_id,
            platform=platform,
            app_version=app_version,
            push_enabled=push_enabled,
        )
        self._audit(
            event_type="mobile_device.registered",
            actor_user_id=user_id,
            entity_type="mobile_device",
            entity_id=device.device_id,
            action="register_mobile_device",
            metadata={"platform": platform, "app_version": app_version, "push_enabled": push_enabled},
        )
        return asdict(device)

    def list_user_mobile_devices(self, user_id: str) -> List[Dict[str, Any]]:
        return [asdict(device) for device in self.repository.list_mobile_devices(user_id=user_id)]

    def sync_module_for_offline(
        self,
        *,
        user_id: str,
        module_code: str,
        status: str,
        progress_snapshot: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        record = self.repository.upsert_offline_sync(
            user_id=user_id,
            module_code=module_code,
            status=status,
            progress_snapshot=progress_snapshot,
        )
        self._audit(
            event_type="offline_sync.updated",
            actor_user_id=user_id,
            entity_type="offline_sync",
            entity_id=record.sync_id,
            action="sync_module_for_offline",
            metadata={"module_code": module_code, "status": status},
        )
        payload = asdict(record)
        payload["progress_snapshot"] = json.loads(payload.pop("progress_snapshot_json"))
        return payload

    def list_offline_sync_records(self, user_id: str) -> List[Dict[str, Any]]:
        rows = self.repository.list_offline_sync_records(user_id=user_id)
        output: List[Dict[str, Any]] = []
        for row in rows:
            payload = dict(row)
            payload["progress_snapshot"] = json.loads(payload.pop("progress_snapshot_json"))
            output.append(payload)
        return output

    def get_mobile_learning_feed(self, *, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        return self.repository.get_mobile_learning_feed(user_id=user_id, limit=limit)

    def log_audit_event(
        self,
        *,
        event_type: str,
        entity_type: str,
        entity_id: str,
        action: str,
        actor_user_id: str | None = None,
        organization_slug: str | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        log = self.repository.create_audit_log(
            event_type=event_type,
            actor_user_id=actor_user_id,
            organization_slug=organization_slug,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            metadata=metadata,
        )
        return self._serialize_audit_log(log)

    def list_audit_logs(
        self,
        *,
        limit: int = 200,
        actor_user_id: str | None = None,
        organization_slug: str | None = None,
        action: str | None = None,
    ) -> List[Dict[str, Any]]:
        logs = self.repository.list_audit_logs(
            limit=limit,
            actor_user_id=actor_user_id,
            organization_slug=organization_slug,
            action=action,
        )
        return [self._serialize_audit_log(log) for log in logs]


def build_default_service(data_dir: Path) -> HipaaTrainingService:
    data_dir.mkdir(parents=True, exist_ok=True)
    repository = TrainingModuleRepository(data_dir / "compliance.db")
    return HipaaTrainingService(repository)

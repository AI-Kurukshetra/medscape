from __future__ import annotations

import unittest
import uuid
from pathlib import Path

from compliance_platform.models import Lesson
from compliance_platform.repository import TrainingModuleRepository
from compliance_platform.service import HipaaTrainingService


class TestHipaaTrainingService(unittest.TestCase):
    def _tmp_dir(self) -> Path:
        base_dir = Path(__file__).resolve().parents[1] / ".tmp-tests"
        base_dir.mkdir(parents=True, exist_ok=True)
        path = base_dir / f"run-{uuid.uuid4().hex}"
        path.mkdir(parents=True, exist_ok=False)
        return path

    def _service(self, tmp_path: Path) -> HipaaTrainingService:
        repository = TrainingModuleRepository(tmp_path / "test.db")
        return HipaaTrainingService(repository)

    def test_seed_creates_default_hipaa_modules(self) -> None:
        directory = self._tmp_dir()
        service = self._service(directory)
        created = service.seed_default_modules()
        self.assertEqual(len(created), 6)
        self.assertEqual(
            [module["code"] for module in service.list_modules()],
            [
                "FDA-21CFR11-101",
                "HIPAA-BREACH-301",
                "HIPAA-PRIV-101",
                "HIPAA-SEC-201",
                "HITECH-101",
                "SOX-HEALTH-101",
            ],
        )

    def test_seed_is_idempotent(self) -> None:
        directory = self._tmp_dir()
        service = self._service(directory)
        service.seed_default_modules()
        created = service.seed_default_modules()
        self.assertEqual(created, [])
        self.assertEqual(len(service.list_modules()), 6)

    def test_create_and_get_custom_hipaa_module(self) -> None:
        directory = self._tmp_dir()
        service = self._service(directory)
        created = service.create_module(
            code="HIPAA-CUSTOM-401",
            title="Advanced HIPAA Scenarios",
            description="Scenario-based HIPAA training module for security teams.",
            lessons=[
                Lesson(
                    title="Insider Access Misuse",
                    content="Detection and response controls for unauthorized internal access.",
                    estimated_minutes=10,
                ),
                Lesson(
                    title="Third-Party Exposure",
                    content="Vendor management and BAA obligations during incident handling.",
                    estimated_minutes=12,
                ),
            ],
        )

        fetched = service.get_module("HIPAA-CUSTOM-401")
        self.assertIsNotNone(fetched)
        assert fetched is not None
        self.assertEqual(fetched["module_id"], created.module_id)
        self.assertEqual(fetched["regulation"], "HIPAA")
        self.assertEqual(fetched["total_estimated_minutes"], 22)
        self.assertEqual(len(fetched["lessons"]), 2)

    def test_track_user_progress_for_module(self) -> None:
        directory = self._tmp_dir()
        service = self._service(directory)
        service.seed_default_modules()

        user = service.register_user(full_name="Alice Carter", email="alice@example.org")
        progress = service.track_user_progress(
            user_id=user["user_id"],
            module_code="HIPAA-PRIV-101",
            lessons_completed=2,
            assessment_score=84.5,
            time_spent_minutes=21,
        )
        self.assertEqual(progress["lessons_completed"], 2)
        self.assertEqual(progress["total_lessons"], 3)
        self.assertAlmostEqual(progress["completion_rate"], 66.67, places=2)
        self.assertEqual(progress["assessment_score"], 84.5)
        self.assertEqual(progress["time_spent_minutes"], 21)
        self.assertIsNone(progress["completed_at"])

        all_progress = service.get_user_progress(user["user_id"])
        self.assertEqual(len(all_progress), 1)
        self.assertEqual(all_progress[0]["module_id"], progress["module_id"])

    def test_progress_summary_and_completion(self) -> None:
        directory = self._tmp_dir()
        service = self._service(directory)
        service.seed_default_modules()

        user_one = service.register_user(full_name="Alice Carter", email="alice@example.org")
        user_two = service.register_user(full_name="Bob Khan", email="bob@example.org")

        service.track_user_progress(
            user_id=user_one["user_id"],
            module_code="HIPAA-SEC-201",
            lessons_completed=3,
            assessment_score=91.0,
            time_spent_minutes=35,
        )
        service.track_user_progress(
            user_id=user_two["user_id"],
            module_code="HIPAA-SEC-201",
            lessons_completed=1,
            assessment_score=70.0,
            time_spent_minutes=11,
        )

        summary = service.get_module_progress_summary("HIPAA-SEC-201")
        self.assertEqual(summary["tracked_users"], 2)
        self.assertEqual(summary["completed_users"], 1)
        self.assertAlmostEqual(summary["avg_completion_rate"], 66.66, places=2)
        self.assertAlmostEqual(summary["avg_assessment_score"], 80.5, places=2)
        self.assertEqual(summary["total_time_spent_minutes"], 46)

    def test_progress_update_reuses_same_record(self) -> None:
        directory = self._tmp_dir()
        service = self._service(directory)
        service.seed_default_modules()

        user = service.register_user(full_name="Alice Carter", email="alice@example.org")
        first = service.track_user_progress(
            user_id=user["user_id"],
            module_code="HIPAA-BREACH-301",
            lessons_completed=1,
            assessment_score=65.0,
            time_spent_minutes=8,
        )
        second = service.track_user_progress(
            user_id=user["user_id"],
            module_code="HIPAA-BREACH-301",
            lessons_completed=3,
            assessment_score=88.0,
            time_spent_minutes=26,
        )

        self.assertEqual(first["progress_id"], second["progress_id"])
        self.assertEqual(second["completion_rate"], 100.0)
        self.assertIsNotNone(second["completed_at"])
        self.assertEqual(second["time_spent_minutes"], 26)

    def test_issue_certification_after_completion(self) -> None:
        directory = self._tmp_dir()
        service = self._service(directory)
        service.seed_default_modules()
        user = service.register_user(full_name="Alice Carter", email="alice@example.org")

        service.track_user_progress(
            user_id=user["user_id"],
            module_code="HIPAA-PRIV-101",
            lessons_completed=3,
            assessment_score=92.0,
            time_spent_minutes=31,
        )
        cert = service.issue_certification(
            user_id=user["user_id"], module_code="HIPAA-PRIV-101", valid_for_days=365
        )
        self.assertTrue(cert["certificate_number"].startswith("CERT-HIPAA-PRIV-101-"))
        self.assertEqual(cert["status"], "active")

        listed = service.list_user_certifications(user["user_id"])
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["certificate_number"], cert["certificate_number"])

        verified = service.verify_certificate(cert["certificate_number"])
        self.assertIsNotNone(verified)
        assert verified is not None
        self.assertTrue(verified["is_active"])

    def test_issue_certification_requires_completion(self) -> None:
        directory = self._tmp_dir()
        service = self._service(directory)
        service.seed_default_modules()
        user = service.register_user(full_name="Alice Carter", email="alice@example.org")

        service.track_user_progress(
            user_id=user["user_id"],
            module_code="HIPAA-SEC-201",
            lessons_completed=2,
            assessment_score=76.0,
            time_spent_minutes=17,
        )
        with self.assertRaises(ValueError):
            service.issue_certification(user_id=user["user_id"], module_code="HIPAA-SEC-201")

    def test_issue_certification_is_idempotent_per_user_module(self) -> None:
        directory = self._tmp_dir()
        service = self._service(directory)
        service.seed_default_modules()
        user = service.register_user(full_name="Alice Carter", email="alice@example.org")
        service.track_user_progress(
            user_id=user["user_id"],
            module_code="HIPAA-BREACH-301",
            lessons_completed=3,
            assessment_score=85.0,
            time_spent_minutes=24,
        )

        first = service.issue_certification(user_id=user["user_id"], module_code="HIPAA-BREACH-301")
        second = service.issue_certification(user_id=user["user_id"], module_code="HIPAA-BREACH-301")
        self.assertEqual(first["certification_id"], second["certification_id"])
        self.assertEqual(first["certificate_number"], second["certificate_number"])

    def test_multi_regulation_filters_and_catalog(self) -> None:
        directory = self._tmp_dir()
        service = self._service(directory)
        service.seed_default_modules()

        hipaa_modules = service.list_modules("HIPAA")
        self.assertEqual(len(hipaa_modules), 3)
        self.assertTrue(all(module["regulation"] == "HIPAA" for module in hipaa_modules))

        supported = service.list_supported_regulations()
        self.assertEqual(supported, ["FDA", "HIPAA", "HITECH", "SOX"])

    def test_create_non_hipaa_module(self) -> None:
        directory = self._tmp_dir()
        service = self._service(directory)
        service.create_module(
            code="FDA-QMS-201",
            title="FDA Quality Management Controls",
            description="Quality management system controls for FDA-regulated operations.",
            regulation="FDA",
            lessons=[
                Lesson(
                    title="Document Controls",
                    content="Versioning, approval, and archival requirements.",
                    estimated_minutes=8,
                )
            ],
        )
        module = service.get_module("FDA-QMS-201")
        self.assertIsNotNone(module)
        assert module is not None
        self.assertEqual(module["regulation"], "FDA")

    def test_create_assessment_and_submit_attempt(self) -> None:
        directory = self._tmp_dir()
        service = self._service(directory)
        service.seed_default_modules()
        user = service.register_user(full_name="Alice Carter", email="alice@example.org")

        created = service.create_assessment(
            module_code="HIPAA-PRIV-101",
            title="HIPAA Privacy Knowledge Check",
            pass_score=70.0,
            questions=[
                {
                    "prompt": "What does PHI stand for?",
                    "options": ["Protected Health Information", "Personal Health Index", "Private Hospital Identifier"],
                    "correct_option": "Protected Health Information",
                },
                {
                    "prompt": "Which principle limits unnecessary access to data?",
                    "options": ["Open Access", "Minimum Necessary", "Universal Disclosure"],
                    "correct_option": "Minimum Necessary",
                },
            ],
        )
        self.assertEqual(created["title"], "HIPAA Privacy Knowledge Check")
        self.assertEqual(len(created["questions"]), 2)

        answers = {
            created["questions"][0]["question_id"]: "Protected Health Information",
            created["questions"][1]["question_id"]: "Minimum Necessary",
        }
        attempt = service.submit_assessment(
            user_id=user["user_id"],
            module_code="HIPAA-PRIV-101",
            title="HIPAA Privacy Knowledge Check",
            answers=answers,
        )
        self.assertEqual(attempt["score"], 100.0)
        self.assertTrue(attempt["passed"])
        self.assertEqual(attempt["correct_answers"], 2)
        self.assertEqual(attempt["total_questions"], 2)

    def test_assessment_fails_with_incorrect_answers(self) -> None:
        directory = self._tmp_dir()
        service = self._service(directory)
        service.seed_default_modules()
        user = service.register_user(full_name="Alice Carter", email="alice@example.org")
        assessment = service.create_assessment(
            module_code="HIPAA-SEC-201",
            title="Security Rule Quiz",
            pass_score=80.0,
            questions=[
                {
                    "prompt": "Which safeguard includes audit controls?",
                    "options": ["Technical", "Physical", "Environmental"],
                    "correct_option": "Technical",
                }
            ],
        )
        wrong_answers = {assessment["questions"][0]["question_id"]: "Physical"}
        attempt = service.submit_assessment(
            user_id=user["user_id"],
            module_code="HIPAA-SEC-201",
            title="Security Rule Quiz",
            answers=wrong_answers,
        )
        self.assertEqual(attempt["score"], 0.0)
        self.assertFalse(attempt["passed"])
        self.assertEqual(attempt["correct_answers"], 0)

    def test_list_user_assessment_attempts(self) -> None:
        directory = self._tmp_dir()
        service = self._service(directory)
        service.seed_default_modules()
        user = service.register_user(full_name="Alice Carter", email="alice@example.org")
        assessment = service.create_assessment(
            module_code="HIPAA-BREACH-301",
            title="Breach Response Quiz",
            pass_score=60.0,
            questions=[
                {
                    "prompt": "When should notification timelines start?",
                    "options": ["At discovery", "After committee approval", "At quarter end"],
                    "correct_option": "At discovery",
                }
            ],
        )
        qid = assessment["questions"][0]["question_id"]
        service.submit_assessment(
            user_id=user["user_id"],
            module_code="HIPAA-BREACH-301",
            title="Breach Response Quiz",
            answers={qid: "At quarter end"},
        )
        service.submit_assessment(
            user_id=user["user_id"],
            module_code="HIPAA-BREACH-301",
            title="Breach Response Quiz",
            answers={qid: "At discovery"},
        )
        attempts = service.list_user_assessment_attempts(user["user_id"])
        self.assertEqual(len(attempts), 2)
        self.assertTrue(attempts[0]["submitted_at"] >= attempts[1]["submitted_at"])

    def test_role_based_training_path_for_user(self) -> None:
        directory = self._tmp_dir()
        service = self._service(directory)
        service.seed_default_modules()
        service.seed_default_role_training_paths()
        user = service.register_user(full_name="Nina Shah", email="nina@example.org")
        service.assign_user_role(user_id=user["user_id"], role_name="nurse")

        path = service.get_user_training_path(user["user_id"])
        self.assertEqual(path["role_name"], "nurse")
        self.assertEqual(
            [module["code"] for module in path["modules"]],
            ["HIPAA-PRIV-101", "HIPAA-BREACH-301", "HITECH-101"],
        )

    def test_custom_role_training_path(self) -> None:
        directory = self._tmp_dir()
        service = self._service(directory)
        service.seed_default_modules()
        user = service.register_user(full_name="Ira Bose", email="ira@example.org")

        service.set_role_training_path(
            role_name="privacy_officer",
            module_codes=["HIPAA-PRIV-101", "SOX-HEALTH-101"],
        )
        service.assign_user_role(user_id=user["user_id"], role_name="privacy_officer")
        path = service.get_user_training_path(user["user_id"])
        self.assertEqual(
            [module["code"] for module in path["modules"]],
            ["HIPAA-PRIV-101", "SOX-HEALTH-101"],
        )

    def test_compliance_dashboard_metrics(self) -> None:
        directory = self._tmp_dir()
        service = self._service(directory)
        service.seed_default_modules()
        service.seed_default_role_training_paths()

        alice = service.register_user(full_name="Alice Carter", email="alice@example.org")
        bob = service.register_user(full_name="Bob Khan", email="bob@example.org")
        service.assign_user_role(user_id=alice["user_id"], role_name="nurse")
        service.assign_user_role(user_id=bob["user_id"], role_name="it_staff")

        service.track_user_progress(
            user_id=alice["user_id"],
            module_code="HIPAA-PRIV-101",
            lessons_completed=3,
            assessment_score=92.0,
            time_spent_minutes=30,
        )
        service.track_user_progress(
            user_id=bob["user_id"],
            module_code="HIPAA-PRIV-101",
            lessons_completed=1,
            assessment_score=68.0,
            time_spent_minutes=11,
        )
        service.track_user_progress(
            user_id=bob["user_id"],
            module_code="HIPAA-SEC-201",
            lessons_completed=3,
            assessment_score=88.0,
            time_spent_minutes=27,
        )

        service.issue_certification(user_id=alice["user_id"], module_code="HIPAA-PRIV-101")

        assessment = service.create_assessment(
            module_code="HIPAA-PRIV-101",
            title="Privacy Quiz Dashboard",
            pass_score=70.0,
            questions=[
                {
                    "prompt": "PHI stands for?",
                    "options": ["Protected Health Information", "Private Health Index"],
                    "correct_option": "Protected Health Information",
                }
            ],
        )
        qid = assessment["questions"][0]["question_id"]
        service.submit_assessment(
            user_id=alice["user_id"],
            module_code="HIPAA-PRIV-101",
            title="Privacy Quiz Dashboard",
            answers={qid: "Protected Health Information"},
        )
        service.submit_assessment(
            user_id=bob["user_id"],
            module_code="HIPAA-PRIV-101",
            title="Privacy Quiz Dashboard",
            answers={qid: "Private Health Index"},
        )

        dashboard = service.get_compliance_dashboard()
        self.assertEqual(dashboard["overview"]["total_users"], 2)
        self.assertEqual(dashboard["overview"]["total_modules"], 6)
        self.assertEqual(dashboard["overview"]["progress_records"], 3)
        self.assertEqual(dashboard["overview"]["completed_records"], 2)
        self.assertEqual(dashboard["overview"]["total_time_spent_minutes"], 68)
        self.assertEqual(dashboard["certifications"]["total_certifications"], 1)
        self.assertEqual(dashboard["certifications"]["active_certifications"], 1)
        self.assertEqual(dashboard["assessments"]["total_attempts"], 2)
        self.assertEqual(dashboard["assessments"]["pass_rate"], 50.0)
        self.assertEqual(len(dashboard["role_distribution"]), 2)
        self.assertGreaterEqual(len(dashboard["module_performance"]), 6)

    def test_automated_notifications_due_remedial_and_renewal(self) -> None:
        directory = self._tmp_dir()
        service = self._service(directory)
        service.seed_default_modules()
        service.seed_default_role_training_paths()
        user = service.register_user(full_name="Nina Shah", email="nina@example.org")
        service.assign_user_role(user_id=user["user_id"], role_name="nurse")

        service.track_user_progress(
            user_id=user["user_id"],
            module_code="HIPAA-PRIV-101",
            lessons_completed=3,
            assessment_score=91.0,
            time_spent_minutes=25,
        )
        service.track_user_progress(
            user_id=user["user_id"],
            module_code="HIPAA-BREACH-301",
            lessons_completed=3,
            assessment_score=88.0,
            time_spent_minutes=22,
        )
        service.issue_certification(
            user_id=user["user_id"], module_code="HIPAA-PRIV-101", valid_for_days=1
        )

        assessment = service.create_assessment(
            module_code="HIPAA-BREACH-301",
            title="Breach Remedial Quiz",
            pass_score=80.0,
            questions=[
                {
                    "prompt": "When should breach notification timelines start?",
                    "options": ["At discovery", "At fiscal quarter end"],
                    "correct_option": "At discovery",
                }
            ],
        )
        qid = assessment["questions"][0]["question_id"]
        service.submit_assessment(
            user_id=user["user_id"],
            module_code="HIPAA-BREACH-301",
            title="Breach Remedial Quiz",
            answers={qid: "At fiscal quarter end"},
        )

        generated = service.run_notification_automation(renewal_days=7)
        types = sorted([item["notification_type"] for item in generated])
        self.assertIn("training_due", types)
        self.assertIn("remedial_training", types)
        self.assertIn("certification_renewal", types)

        notifications = service.list_user_notifications(user["user_id"])
        self.assertGreaterEqual(len(notifications), 3)
        first = notifications[0]
        self.assertEqual(first["status"], "unread")
        updated = service.mark_notification_as_read(first["notification_id"])
        self.assertEqual(updated["status"], "read")

    def test_multi_tenant_isolation_for_modules_and_dashboards(self) -> None:
        directory = self._tmp_dir()
        service = self._service(directory)
        service.seed_default_modules()

        service.create_organization(
            name="NorthCare Health", slug="northcare", branding={"primaryColor": "#1155cc"}
        )
        service.create_organization(
            name="SouthCare Clinic", slug="southcare", branding={"primaryColor": "#009966"}
        )

        north_user = service.register_user(
            full_name="Nora North", email="nora@northcare.org", organization_slug="northcare"
        )
        south_user = service.register_user(
            full_name="Sam South", email="sam@southcare.org", organization_slug="southcare"
        )

        service.create_module(
            code="NC-HIPAA-001",
            title="NorthCare HIPAA Orientation",
            description="NorthCare-specific onboarding module.",
            regulation="HIPAA",
            organization_slug="northcare",
            lessons=[
                Lesson(
                    title="NorthCare Data Policy",
                    content="Local policy controls for PHI handling.",
                    estimated_minutes=8,
                )
            ],
        )
        service.create_module(
            code="SC-HIPAA-001",
            title="SouthCare HIPAA Orientation",
            description="SouthCare-specific onboarding module.",
            regulation="HIPAA",
            organization_slug="southcare",
            lessons=[
                Lesson(
                    title="SouthCare Privacy Workflow",
                    content="Local privacy and escalation flow.",
                    estimated_minutes=7,
                )
            ],
        )

        north_modules = service.list_modules(organization_slug="northcare")
        south_modules = service.list_modules(organization_slug="southcare")
        self.assertEqual([m["code"] for m in north_modules], ["NC-HIPAA-001"])
        self.assertEqual([m["code"] for m in south_modules], ["SC-HIPAA-001"])

        service.track_user_progress(
            user_id=north_user["user_id"],
            module_code="NC-HIPAA-001",
            lessons_completed=1,
            assessment_score=95.0,
            time_spent_minutes=9,
        )
        service.track_user_progress(
            user_id=south_user["user_id"],
            module_code="SC-HIPAA-001",
            lessons_completed=1,
            assessment_score=90.0,
            time_spent_minutes=8,
        )

        north_dashboard = service.get_organization_dashboard("northcare")
        south_dashboard = service.get_organization_dashboard("southcare")
        self.assertEqual(north_dashboard["overview"]["total_users"], 1)
        self.assertEqual(south_dashboard["overview"]["total_users"], 1)
        self.assertEqual(north_dashboard["overview"]["total_modules"], 1)
        self.assertEqual(south_dashboard["overview"]["total_modules"], 1)
        self.assertEqual(north_dashboard["overview"]["progress_records"], 1)
        self.assertEqual(south_dashboard["overview"]["progress_records"], 1)

    def test_multi_tenant_role_paths_are_organization_scoped(self) -> None:
        directory = self._tmp_dir()
        service = self._service(directory)
        service.seed_default_modules()
        service.create_organization(name="Org One", slug="org-one")
        service.create_organization(name="Org Two", slug="org-two")
        user = service.register_user(
            full_name="Taylor Reed", email="taylor@example.org", organization_slug="org-one"
        )

        service.create_module(
            code="ORG1-PRIV-100",
            title="Org1 Privacy",
            description="Org1 privacy track",
            regulation="HIPAA",
            organization_slug="org-one",
            lessons=[Lesson(title="Intro", content="intro", estimated_minutes=5)],
        )
        service.create_module(
            code="ORG2-PRIV-100",
            title="Org2 Privacy",
            description="Org2 privacy track",
            regulation="HIPAA",
            organization_slug="org-two",
            lessons=[Lesson(title="Intro", content="intro", estimated_minutes=5)],
        )

        service.set_role_training_path_for_organization(
            organization_slug="org-one",
            role_name="nurse",
            module_codes=["ORG1-PRIV-100"],
        )
        service.assign_user_role_for_organization(
            user_id=user["user_id"], organization_slug="org-one", role_name="nurse"
        )
        path = service.get_user_training_path_for_organization(
            user_id=user["user_id"], organization_slug="org-one"
        )
        self.assertEqual([m["code"] for m in path["modules"]], ["ORG1-PRIV-100"])

        with self.assertRaises(ValueError):
            service.set_role_training_path_for_organization(
                organization_slug="org-one",
                role_name="nurse",
                module_codes=["ORG2-PRIV-100"],
            )

    def test_mobile_device_and_offline_sync_support(self) -> None:
        directory = self._tmp_dir()
        service = self._service(directory)
        service.seed_default_modules()
        service.seed_default_role_training_paths()
        user = service.register_user(full_name="Maya Patel", email="maya@example.org")
        service.assign_user_role(user_id=user["user_id"], role_name="nurse")

        device = service.register_mobile_device(
            user_id=user["user_id"],
            device_id="ios-iphone-15-maya",
            platform="ios",
            app_version="1.0.0",
            push_enabled=True,
        )
        self.assertEqual(device["platform"], "ios")
        devices = service.list_user_mobile_devices(user["user_id"])
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]["device_id"], "ios-iphone-15-maya")

        sync_one = service.sync_module_for_offline(
            user_id=user["user_id"],
            module_code="HIPAA-PRIV-101",
            status="downloaded",
            progress_snapshot={"completion_rate": 33.3},
        )
        sync_two = service.sync_module_for_offline(
            user_id=user["user_id"],
            module_code="HIPAA-PRIV-101",
            status="synced",
            progress_snapshot={"completion_rate": 66.6},
        )
        self.assertEqual(sync_one["sync_id"], sync_two["sync_id"])
        self.assertEqual(sync_two["status"], "synced")
        self.assertEqual(sync_two["progress_snapshot"]["completion_rate"], 66.6)

        offline = service.list_offline_sync_records(user["user_id"])
        self.assertEqual(len(offline), 1)
        self.assertEqual(offline[0]["module_code"], "HIPAA-PRIV-101")

    def test_mobile_learning_feed_prioritizes_due_and_progress_items(self) -> None:
        directory = self._tmp_dir()
        service = self._service(directory)
        service.seed_default_modules()
        service.seed_default_role_training_paths()
        user = service.register_user(full_name="Dev Rao", email="dev@example.org")
        service.assign_user_role(user_id=user["user_id"], role_name="nurse")
        service.track_user_progress(
            user_id=user["user_id"],
            module_code="HIPAA-PRIV-101",
            lessons_completed=2,
            assessment_score=80.0,
            time_spent_minutes=18,
        )
        feed = service.get_mobile_learning_feed(user_id=user["user_id"], limit=5)
        self.assertGreaterEqual(len(feed), 2)
        codes = {item["module_code"] for item in feed}
        self.assertIn("HIPAA-PRIV-101", codes)
        self.assertIn("HIPAA-BREACH-301", codes)

    def test_audit_trail_logs_core_actions(self) -> None:
        directory = self._tmp_dir()
        service = self._service(directory)
        service.seed_default_modules()
        user = service.register_user(full_name="Audit User", email="audit@example.org")
        service.track_user_progress(
            user_id=user["user_id"],
            module_code="HIPAA-PRIV-101",
            lessons_completed=1,
            assessment_score=75.0,
            time_spent_minutes=12,
        )
        logs = service.list_audit_logs(limit=50, actor_user_id=user["user_id"])
        actions = {log["action"] for log in logs}
        self.assertIn("register_user", actions)
        self.assertIn("track_user_progress", actions)

    def test_audit_log_filters_by_organization_and_action(self) -> None:
        directory = self._tmp_dir()
        service = self._service(directory)
        service.create_organization(name="Audit Org", slug="audit-org")
        service.create_module(
            code="AUDIT-MOD-1",
            title="Audit Module",
            description="Module for audit test",
            regulation="HIPAA",
            organization_slug="audit-org",
            lessons=[Lesson(title="L1", content="c", estimated_minutes=5)],
        )
        org_logs = service.list_audit_logs(organization_slug="audit-org", action="create_module")
        self.assertGreaterEqual(len(org_logs), 1)
        self.assertTrue(all(log["organization_slug"] == "audit-org" for log in org_logs))


if __name__ == "__main__":
    unittest.main()

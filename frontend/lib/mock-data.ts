import {
  AuditItem,
  DashboardPayload,
  ModuleItem,
  NotificationItem,
  ProgressItem,
  UserItem
} from "@/lib/types";

export const dashboardData: DashboardPayload = {
  overview: {
    total_users: 4,
    total_modules: 10,
    progress_records: 71,
    avg_completion_rate: 78.42
  },
  certifications: {
    total_certifications: 34,
    active_certifications: 31
  },
  assessments: {
    total_attempts: 120,
    avg_score: 84.7,
    pass_rate: 88.3
  },
  role_distribution: [
    { role_name: "administrator", user_count: 3 },
    { role_name: "nurse", user_count: 1 }
  ]
};

export const modulesData: ModuleItem[] = [
  { code: "HIPAA-PRIV-101", title: "HIPAA Privacy Rule Fundamentals", regulation: "HIPAA", total_estimated_minutes: 30 },
  { code: "HIPAA-SEC-201", title: "HIPAA Security Rule in Practice", regulation: "HIPAA", total_estimated_minutes: 38 },
  { code: "HIPAA-BREACH-301", title: "Breach Notification and Incident Response", regulation: "HIPAA", total_estimated_minutes: 31 },
  { code: "HITECH-101", title: "HITECH Act Fundamentals", regulation: "HITECH", total_estimated_minutes: 30 },
  { code: "SOX-HEALTH-101", title: "SOX Controls for Healthcare Finance", regulation: "SOX", total_estimated_minutes: 31 },
  { code: "FDA-21CFR11-101", title: "FDA 21 CFR Part 11 Essentials", regulation: "FDA", total_estimated_minutes: 29 },
  { code: "PCI-DSS-101", title: "PCI DSS for Healthcare Payment Workflows", regulation: "PCI-DSS", total_estimated_minutes: 34 },
  { code: "OSHA-101", title: "OSHA Safety Basics for Clinical Facilities", regulation: "OSHA", total_estimated_minutes: 27 },
  { code: "GDPR-HEALTH-101", title: "GDPR Patient Data Handling Essentials", regulation: "GDPR", total_estimated_minutes: 33 },
  { code: "NIST-CSF-101", title: "NIST Cybersecurity Framework Fundamentals", regulation: "NIST", total_estimated_minutes: 35 }
];

export const usersData: UserItem[] = [
  { user_id: "u-1001", full_name: "Sachin Patel", email: "sachin.patel.admin1@example.com", role_name: "administrator" },
  { user_id: "u-1002", full_name: "Sachin Patel", email: "sachin.patel.admin2@example.com", role_name: "administrator" },
  { user_id: "u-1003", full_name: "Sachin Patel", email: "sachin.patel.admin3@example.com", role_name: "administrator" },
  { user_id: "u-1004", full_name: "Maya Patel", email: "maya@example.org", role_name: "nurse" }
];

export const progressData: ProgressItem[] = [
  { user_id: "u-1001", module_code: "HIPAA-PRIV-101", completion_rate: 100, assessment_score: 92, time_spent_minutes: 31 },
  { user_id: "u-1002", module_code: "HIPAA-SEC-201", completion_rate: 66.67, assessment_score: 74, time_spent_minutes: 21 },
  { user_id: "u-1003", module_code: "HITECH-101", completion_rate: 100, assessment_score: 90, time_spent_minutes: 28 },
  { user_id: "u-1004", module_code: "FDA-21CFR11-101", completion_rate: 33.33, assessment_score: 0, time_spent_minutes: 10 }
];

export const notificationsData: NotificationItem[] = [
  { notification_id: "n-1", notification_type: "training_due", title: "Training Module Due", status: "unread", created_at: "2026-03-14T09:10:00Z" },
  { notification_id: "n-2", notification_type: "remedial_training", title: "Remedial Training Assigned", status: "unread", created_at: "2026-03-14T09:02:00Z" },
  { notification_id: "n-3", notification_type: "certification_renewal", title: "Certification Renewal Reminder", status: "read", created_at: "2026-03-13T18:26:00Z" }
];

export const auditData: AuditItem[] = [
  { audit_id: "a-1", action: "register_user", entity_type: "user", actor_user_id: "u-1001", organization_slug: "default", created_at: "2026-03-14T08:10:00Z" },
  { audit_id: "a-2", action: "track_user_progress", entity_type: "user_progress", actor_user_id: "u-1001", organization_slug: null, created_at: "2026-03-14T08:20:00Z" },
  { audit_id: "a-3", action: "issue_certification", entity_type: "certification", actor_user_id: "u-1001", organization_slug: null, created_at: "2026-03-14T08:35:00Z" },
  { audit_id: "a-4", action: "send_notification", entity_type: "notification", actor_user_id: "u-1002", organization_slug: null, created_at: "2026-03-14T08:50:00Z" }
];

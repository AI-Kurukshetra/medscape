export type DashboardPayload = {
  overview: {
    total_users: number;
    total_modules: number;
    progress_records: number;
    avg_completion_rate: number;
  };
  certifications: {
    total_certifications: number;
    active_certifications: number;
  };
  assessments: {
    total_attempts: number;
    avg_score: number;
    pass_rate: number;
  };
  role_distribution: { role_name: string; user_count: number }[];
};

export type UserItem = {
  user_id: string;
  full_name: string;
  email: string;
  role_name: string | null;
};

export type ModuleItem = {
  code: string;
  title: string;
  regulation: string;
  total_estimated_minutes: number;
};

export type ProgressItem = {
  user_id: string;
  module_code: string;
  completion_rate: number;
  assessment_score: number;
  time_spent_minutes: number;
};

export type NotificationItem = {
  notification_id: string;
  notification_type: string;
  title: string;
  status: string;
  created_at: string;
};

export type AuditItem = {
  audit_id: string;
  action: string;
  entity_type: string;
  actor_user_id: string | null;
  organization_slug: string | null;
  created_at: string;
};

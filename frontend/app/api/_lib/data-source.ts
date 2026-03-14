import {
  auditData,
  dashboardData,
  modulesData,
  notificationsData,
  progressData,
  usersData
} from "@/lib/mock-data";
import { getSupabaseServerClient } from "@/lib/supabase";
import type {
  AuditItem,
  DashboardPayload,
  ModuleItem,
  NotificationItem,
  ProgressItem,
  UserItem
} from "@/lib/types";

type MockKey = "overview" | "modules" | "progress" | "notifications" | "audit" | "users";

const mockMap = {
  overview: dashboardData,
  modules: modulesData,
  progress: progressData,
  notifications: notificationsData,
  audit: auditData,
  users: usersData
};

function normalizeRoleName(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const role = value.trim();
  return role.length > 0 ? role : null;
}

function isValidEmail(value: string): boolean {
  return value.includes("@") && value.indexOf("@") > 0 && value.indexOf("@") < value.length - 1;
}

function sanitizeUsers(rows: unknown): UserItem[] {
  if (!Array.isArray(rows)) return [];

  const seen = new Set<string>();
  const output: UserItem[] = [];

  for (const row of rows) {
    if (!row || typeof row !== "object") continue;
    const r = row as Record<string, unknown>;

    const user_id = typeof r.user_id === "string" ? r.user_id.trim() : "";
    const full_name = typeof r.full_name === "string" ? r.full_name.trim() : "";
    const email = typeof r.email === "string" ? r.email.trim() : "";
    const role_name = normalizeRoleName(r.role_name);

    if (!user_id || !full_name || !email || !isValidEmail(email)) continue;
    if (seen.has(user_id)) continue;

    seen.add(user_id);
    output.push({ user_id, full_name, email, role_name });
  }

  return output;
}

async function getFromBackend(key: MockKey) {
  const backendBase = process.env.BACKEND_API_BASE_URL;
  if (!backendBase) return null;
  const target = `${backendBase.replace(/\/$/, "")}/${key}`;
  const response = await fetch(target, { cache: "no-store" });
  if (!response.ok) return null;
  return response.json();
}

async function getFromSupabase(key: MockKey) {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !anon) return null;
  const supabase = getSupabaseServerClient();

  if (key === "modules") {
    const { data, error } = await supabase
      .from("modules")
      .select<"code,title,regulation,total_estimated_minutes">();
    if (error) return null;
    return (data ?? []) as unknown as ModuleItem[];
  }

  if (key === "progress") {
    const { data, error } = await supabase
      .from("progress")
      .select<"user_id,module_code,completion_rate,assessment_score,time_spent_minutes">();
    if (error) return null;
    return (data ?? []) as unknown as ProgressItem[];
  }

  if (key === "notifications") {
    const { data, error } = await supabase
      .from("notifications")
      .select<"notification_id,notification_type,title,status,created_at">()
      .order("created_at", { ascending: false });
    if (error) return null;
    return (data ?? []) as unknown as NotificationItem[];
  }

  if (key === "audit") {
    const { data, error } = await supabase
      .from("audit_logs")
      .select<"audit_id,action,entity_type,actor_user_id,organization_slug,created_at">()
      .order("created_at", { ascending: false });
    if (error) return null;
    return (data ?? []) as unknown as AuditItem[];
  }

  if (key === "users") {
    const [{ data: users, error: usersError }, { data: roles, error: rolesError }] =
      await Promise.all([
        supabase.from("users").select<"user_id,full_name,email">(),
        supabase.from("user_roles").select<"user_id,role_name">()
      ]);
    if (usersError || rolesError) return null;

    const roleByUserId = new Map<string, string>();
    for (const row of roles ?? []) {
      const roleRow = row as { user_id: string; role_name: string };
      roleByUserId.set(roleRow.user_id, roleRow.role_name);
    }

    return sanitizeUsers((users ?? []).map((row: any) => ({
      user_id: row.user_id,
      full_name: row.full_name,
      email: row.email,
      role_name: roleByUserId.get(row.user_id) ?? null
    })));
  }

  if (key === "overview") {
    // Best-effort aggregates; fall back if any query fails
    const [usersCount, modulesCount, progressCount] = await Promise.all([
      supabase.from("users").select("*", { count: "exact", head: true }),
      supabase.from("modules").select("*", { count: "exact", head: true }),
      supabase.from("progress").select("*", { count: "exact", head: true })
    ]);
    if (
      usersCount.error ||
      modulesCount.error ||
      progressCount.error
    ) {
      return null;
    }

    // Example: compute simple pass rate/avg completion if progress table has fields
    const { data: progRows, error: progRowsError } = await supabase
      .from("progress")
      .select<"completion_rate,assessment_score">();
    if (progRowsError) return null;
    const completionRates = (progRows ?? []).map((r: any) => Number(r.completion_rate) || 0);
    const assessmentScores = (progRows ?? []).map((r: any) => Number(r.assessment_score) || 0);
    const avg = (arr: number[]) =>
      arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0;
    const avgCompletion = Number(avg(completionRates).toFixed(2));
    const avgScore = Number(avg(assessmentScores).toFixed(2));
    const passRate = Number(
      (
        (assessmentScores.filter((s) => s >= 70).length / (assessmentScores.length || 1)) *
        100
      ).toFixed(2)
    );

    const payload: DashboardPayload = {
      overview: {
        total_users: usersCount.count ?? 0,
        total_modules: modulesCount.count ?? 0,
        progress_records: progressCount.count ?? 0,
        avg_completion_rate: avgCompletion
      },
      certifications: {
        total_certifications: 0,
        active_certifications: 0
      },
      assessments: {
        total_attempts: assessmentScores.length,
        avg_score: avgScore,
        pass_rate: passRate
      },
      role_distribution: []
    };
    return payload;
  }
  return null;
}

export async function getRouteData(key: MockKey) {
  // 1) Prefer backend if configured
  const backendData = await getFromBackend(key);
  if (backendData) {
    if (key === "users") return sanitizeUsers(backendData);
    return backendData;
  }

  // 2) Try Supabase if env is present
  try {
    const supabaseData = await getFromSupabase(key);
    if (supabaseData) {
      if (key === "users") return sanitizeUsers(supabaseData);
      return supabaseData;
    }
  } catch {
    // ignore and fall back
  }

  // 3) Fallback to mock data
  if (key === "users") return sanitizeUsers(mockMap[key]);
  return mockMap[key];
}

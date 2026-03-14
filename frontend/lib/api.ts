import {
  AuditItem,
  DashboardPayload,
  ModuleItem,
  NotificationItem,
  ProgressItem,
  UserItem
} from "@/lib/types";

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Request failed for ${path}`);
  }
  return (await response.json()) as T;
}

export function getDashboard() {
  return fetchJson<DashboardPayload>("/api/overview");
}

export function getModules() {
  return fetchJson<ModuleItem[]>("/api/modules");
}

export function getProgress() {
  return fetchJson<ProgressItem[]>("/api/progress");
}

export function getNotifications() {
  return fetchJson<NotificationItem[]>("/api/notifications");
}

export function getAuditLogs() {
  return fetchJson<AuditItem[]>("/api/audit");
}

export function getUsers() {
  return fetchJson<UserItem[]>("/api/users");
}

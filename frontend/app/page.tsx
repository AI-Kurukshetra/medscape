"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getDashboard } from "@/lib/api";
import type { DashboardPayload } from "@/lib/types";

function toSafeCount(value: unknown): number {
  const parsed =
    typeof value === "number" ? value : typeof value === "string" ? Number(value) : NaN;
  if (!Number.isFinite(parsed) || parsed < 0) {
    return 0;
  }
  return Math.floor(parsed);
}

function toSafePercent(value: unknown): string {
  const parsed =
    typeof value === "number" ? value : typeof value === "string" ? Number(value) : NaN;
  if (!Number.isFinite(parsed) || parsed < 0) {
    return "0.00";
  }
  return parsed.toFixed(2);
}

function toBarWidth(value: string): number {
  const n = Number(value);
  if (!Number.isFinite(n) || n < 0) return 0;
  if (n > 100) return 100;
  return n;
}

export default function HomePage() {
  const [data, setData] = useState<DashboardPayload | null>(null);

  useEffect(() => {
    getDashboard().then(setData).catch(() => setData(null));
  }, []);

  if (!data) {
    return <div className="card">Loading dashboard...</div>;
  }

  const totalUsers = toSafeCount(data.overview.total_users);
  const totalModules = toSafeCount(data.overview.total_modules);
  const avgCompletion = toSafePercent(data.overview.avg_completion_rate);
  const passRate = toSafePercent(data.assessments.pass_rate);
  const avgCompletionWidth = toBarWidth(avgCompletion);
  const passRateWidth = toBarWidth(passRate);

  return (
    <div className="grid">
      <Link href="/users" className="card card-link" style={{ gridColumn: "span 3" }}>
        <div className="kpi">{totalUsers}</div>
        <div className="label">Total Users</div>
      </Link>
      <Link href="/modules" className="card card-link" style={{ gridColumn: "span 3" }}>
        <div className="kpi">{totalModules}</div>
        <div className="label">Training Modules</div>
      </Link>
      <Link href="/progress" className="card card-link" style={{ gridColumn: "span 3" }}>
        <div className="kpi">{avgCompletion}%</div>
        <div className="label">Avg Completion</div>
        <div className="percent-chart" aria-hidden>
          <div className="percent-fill" style={{ width: `${avgCompletionWidth}%` }} />
        </div>
      </Link>
      <Link href="/assessments" className="card card-link" style={{ gridColumn: "span 3" }}>
        <div className="kpi">{passRate}%</div>
        <div className="label">Assessment Pass Rate</div>
        <div className="percent-chart" aria-hidden>
          <div className="percent-fill" style={{ width: `${passRateWidth}%` }} />
        </div>
      </Link>

      <section className="card" style={{ gridColumn: "span 6" }}>
        <h3>Certifications</h3>
        <p>
          Active: <b>{data.certifications.active_certifications}</b> / Total:{" "}
          <b>{data.certifications.total_certifications}</b>
        </p>
      </section>

      <section className="card" style={{ gridColumn: "span 6" }}>
        <h3>Role Distribution</h3>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Role</th>
                <th>Users</th>
              </tr>
            </thead>
            <tbody>
              {data.role_distribution.map((role) => (
                <tr key={role.role_name}>
                  <td>{role.role_name}</td>
                  <td>{role.user_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

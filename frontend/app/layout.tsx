import "./globals.css";
import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Healthcare Compliance Platform",
  description: "Next.js frontend for compliance training operations"
};

export default function RootLayout({
  children
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <header className="topbar">
            <div>
              <div style={{ fontSize: 12, opacity: 0.8 }}>Med Compliance Suite</div>
              <div style={{ fontSize: 20, fontWeight: 700 }}>Operations Console</div>
            </div>
            <nav>
              <Link href="/">Dashboard</Link>
              <Link href="/users">Users</Link>
              <Link href="/modules">Modules</Link>
              <Link href="/progress">Progress</Link>
              <Link href="/assessments">Assessments</Link>
              <Link href="/notifications">Notifications</Link>
              <Link href="/audit">Audit</Link>
            </nav>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}

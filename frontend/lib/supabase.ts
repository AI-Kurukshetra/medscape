import { createClient, type SupabaseClient } from "@supabase/supabase-js";

let browserClient: SupabaseClient | null = null;
let serverClient: SupabaseClient | null = null;

function getEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required env: ${name}`);
  }
  return value;
}

// Client for use in React components (NEXT_PUBLIC_ vars)
export function getSupabaseBrowserClient(): SupabaseClient {
  if (browserClient) return browserClient;
  const url = getEnv("NEXT_PUBLIC_SUPABASE_URL");
  const anonKey = getEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY");
  browserClient = createClient(url, anonKey);
  return browserClient;
}

// Server-side client (uses same anon key unless you add a service key)
export function getSupabaseServerClient(): SupabaseClient {
  if (serverClient) return serverClient;
  const url =
    process.env.NEXT_PUBLIC_SUPABASE_URL ??
    (() => {
      throw new Error("Missing NEXT_PUBLIC_SUPABASE_URL");
    })();
  const key =
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ??
    (() => {
      throw new Error("Missing NEXT_PUBLIC_SUPABASE_ANON_KEY");
    })();
  serverClient = createClient(url, key);
  return serverClient;
}


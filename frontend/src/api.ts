import { useEffect, useState } from "react";

export type Year = "all" | "2024" | "2025";

export async function get<T>(path: string, params: Record<string, string | number | undefined> = {}): Promise<T> {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => v !== undefined && v !== "" && qs.set(k, String(v)));
  const res = await fetch(`/api/${path}?${qs}`);
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.json();
}

/** Fetch on mount and whenever `deps` change; exposes loading/error state. */
export function useApi<T>(path: string, params: Record<string, string | number | undefined>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let live = true;
    setError(null);
    get<T>(path, params).then((d) => live && setData(d)).catch((e) => live && setError(String(e)));
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return { data, error, loading: !data && !error };
}

export const fmt = (n: number | null | undefined) => (n == null ? "—" : n.toLocaleString("en-GB"));
export const pct = (n: number | null | undefined) => (n == null ? "—" : `${n.toFixed(2)}%`);

export interface Stat { key: string | number; events: number; strong: number; share: number; label?: string }
export interface Totals { events: number; strong: number; share: number | null; max_mag: number | null; mean_depth: number | null; mean_mag: number | null }

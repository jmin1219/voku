import { useState, useCallback, useRef } from "react";
import type { PhaseSpaceData } from "../types/phase-space";

const API_BASE = "http://localhost:8000/api";

interface UsePhaseSpaceReturn {
  data: PhaseSpaceData | null;
  loading: boolean;
  error: string | null;
  fetch: () => void;
}

/**
 * Lazy-loading hook for phase space data.
 *
 * Doesn't fetch until fetch() is called (phase space starts hidden).
 * Caches the result — call fetch() again to refresh.
 */
export function usePhaseSpace(): UsePhaseSpaceReturn {
  const [data, setData] = useState<PhaseSpaceData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fetchedRef = useRef(false);

  const fetchData = useCallback(() => {
    setLoading(true);
    setError(null);

    globalThis
      .fetch(`${API_BASE}/phase-space`)
      .then((res) => {
        if (!res.ok) throw new Error(`Phase space fetch failed: ${res.status}`);
        return res.json();
      })
      .then((json: PhaseSpaceData) => {
        setData(json);
        fetchedRef.current = true;
      })
      .catch((err) => {
        setError(err.message);
        console.error("Phase space fetch error:", err);
      })
      .finally(() => setLoading(false));
  }, []);

  return { data, loading, error, fetch: fetchData };
}

import { useEffect } from "react";
import type { PhaseSpaceData } from "../../types/phase-space";
import { PhaseSpaceScene } from "./PhaseSpaceScene";

/**
 * PhaseSpaceContainer — Summonable overlay panel.
 *
 * Slides in from right on ⌘+Space. Dark background.
 * Loads data on first open. Contains the full R3F scene.
 */

interface PhaseSpaceContainerProps {
  isOpen: boolean;
  data: PhaseSpaceData | null;
  loading: boolean;
  error: string | null;
  retrievalIds: string[];
  onFetchData: () => void;
}

export function PhaseSpaceContainer({
  isOpen,
  data,
  loading,
  error,
  retrievalIds,
  onFetchData,
}: PhaseSpaceContainerProps) {
  // Fetch on first open
  useEffect(() => {
    if (isOpen && !data && !loading) {
      onFetchData();
    }
  }, [isOpen, data, loading, onFetchData]);

  return (
    <div
      style={{
        position: "relative",
        width: isOpen ? "50%" : "0%",
        height: "100%",
        overflow: "hidden",
        transition: "width 0.2s ease-out",
        background: "var(--voku-phase-bg, #1a1a22)",
        borderLeft: isOpen ? "1px solid rgba(201, 162, 60, 0.15)" : "none",
        flexShrink: 0,
      }}
    >
      {isOpen && (
        <>
          {loading && !data && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                height: "100%",
                color: "rgba(224, 219, 208, 0.5)",
                fontSize: "0.8rem",
                fontFamily: "var(--voku-font-mono)",
              }}
            >
              loading phase space...
            </div>
          )}
          {error && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                height: "100%",
                color: "#a05050",
                fontSize: "0.8rem",
                fontFamily: "var(--voku-font-mono)",
                padding: 24,
                textAlign: "center",
              }}
            >
              {error}
            </div>
          )}
          {data && (
            <PhaseSpaceScene data={data} retrievalIds={retrievalIds} />
          )}
        </>
      )}
    </div>
  );
}

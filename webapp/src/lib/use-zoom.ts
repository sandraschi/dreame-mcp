import { useCallback, useEffect, useState } from "react";

const ZOOM_LEVELS = [0.8, 1.0, 1.25, 1.5, 2.0, 3.0];

function useZoom() {
  const [zoomIndex, setZoomIndex] = useState(() => {
    try {
      const saved = localStorage.getItem("tauri-zoom");
      return saved ? ZOOM_LEVELS.indexOf(parseFloat(saved)) : 0;
    } catch {
      return 0;
    }
  });

  const applyZoom = useCallback(async (level: number) => {
    localStorage.setItem("tauri-zoom", String(level));
    try {
      const { getCurrentWebview } = await import("@tauri-apps/api/webview");
      await getCurrentWebview().setZoom(level);
      return;
    } catch {
      // dev browser — fall through to CSS zoom
    }
    (
      document.documentElement as HTMLElement & { style: CSSStyleDeclaration }
    ).style.zoom = String(level);
  }, []);

  useEffect(() => {
    const handler = (e: WheelEvent) => {
      if (!e.ctrlKey) return;
      e.preventDefault();
      setZoomIndex((prev) => {
        const next =
          e.deltaY < 0
            ? Math.min(prev + 1, ZOOM_LEVELS.length - 1)
            : Math.max(prev - 1, 0);
        if (next !== prev) applyZoom(ZOOM_LEVELS[next]);
        return next;
      });
    };
    const reset = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === "0") {
        e.preventDefault();
        setZoomIndex(1);
        applyZoom(1.0);
      }
    };
    window.addEventListener("wheel", handler, { passive: false });
    window.addEventListener("keydown", reset);
    const saved = localStorage.getItem("tauri-zoom");
    if (saved) applyZoom(parseFloat(saved));
    return () => {
      window.removeEventListener("wheel", handler);
      window.removeEventListener("keydown", reset);
    };
  }, [applyZoom]);

  return { zoom: ZOOM_LEVELS[zoomIndex] };
}

export default useZoom;

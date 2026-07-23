import type { SearchResponse, Timeframe } from "@/types/result";

interface SearchParams {
  drawingPointsY: number[];
  timeframe?: Timeframe;
  windowSize?: number;
  algorithm?: string;
  topN?: number;
}

export async function searchMarket(params: SearchParams): Promise<SearchResponse> {
  const res = await fetch("/api/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      drawing_points_y: params.drawingPointsY,
      timeframe: params.timeframe,
      window_size: params.windowSize,
      algorithm: params.algorithm ?? "dtw",
      top_n: params.topN,
    }),
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? `Search failed with status ${res.status}`);
  }

  return res.json();
}
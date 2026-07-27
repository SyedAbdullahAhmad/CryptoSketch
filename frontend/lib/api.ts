import type {
  SearchResponse,
  ConceptScanResponse,
  HTFLiquidityScanResponse,
  LTFLiquidityScanResponse,
  Timeframe,
  HTFTimeframe,
  LTFTimeframe,
} from "@/types/result";

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
      algorithm: params.algorithm ?? "feature",
      top_n: params.topN,
    }),
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? `Search failed with status ${res.status}`);
  }

  return res.json();
}

interface ConceptScanParams {
  concept: string;
  timeframe?: Timeframe;
  topN?: number;
}

export async function scanConcept(params: ConceptScanParams): Promise<ConceptScanResponse> {
  const res = await fetch("/api/concept-scan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      concept: params.concept,
      timeframe: params.timeframe,
      top_n: params.topN,
    }),
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? `Concept scan failed with status ${res.status}`);
  }

  return res.json();
}

interface HTFLiquidityParams {
  timeframe?: HTFTimeframe;
  topN?: number;
}

export async function htfLiquidityScan(params: HTFLiquidityParams): Promise<HTFLiquidityScanResponse> {
  const res = await fetch("/api/htf-liquidity-scan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ timeframe: params.timeframe, top_n: params.topN }),
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? `HTF liquidity scan failed with status ${res.status}`);
  }

  return res.json();
}

interface LTFLiquidityParams {
  ltfTimeframe?: LTFTimeframe;
  htfTimeframe?: HTFTimeframe;
  topN?: number;
}

export async function ltfLiquidityScan(params: LTFLiquidityParams): Promise<LTFLiquidityScanResponse> {
  const res = await fetch("/api/ltf-liquidity-scan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ltf_timeframe: params.ltfTimeframe,
      htf_timeframe: params.htfTimeframe,
      top_n: params.topN,
    }),
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? `LTF liquidity scan failed with status ${res.status}`);
  }

  return res.json();
}
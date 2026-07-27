export interface MatchResult {
  symbol: string;
  exchange: string;
  timeframe: string;
  similarity: number;
  start_time: number;
  end_time: number;
  closes: number[];
  reasons: string[];
}

export interface SearchResponse {
  results: MatchResult[];
  scanned_symbols: number;
  timeframe: string;
  algorithm: string;
}

export interface ConceptScanResponse {
  results: MatchResult[];
  scanned_symbols: number;
  timeframe: string;
  concept: string;
}

export interface HTFLiquidityResult {
  symbol: string;
  exchange: string;
  timeframe: string;
  trend: string;
  liquidity_zone: number;
  liquidity_type: string;
  liquidity_taken: boolean;
  event_liquidity: boolean;
  bias: string;
  confidence: string;
  reason: string;
  closes: number[];
}

export interface HTFLiquidityScanResponse {
  results: HTFLiquidityResult[];
  scanned_symbols: number;
  timeframe: string;
}

export interface LTFLiquiditySignal {
  symbol: string;
  exchange: string;
  timeframe: string;
  htf_timeframe: string;
  trend: string;
  htf_bias: string;
  liquidity_type: string;
  liquidity_price: number;
  liquidity_status: string;
  signal: string;
  confidence: string;
  entry_price: number;
  stop_loss: number;
  target_price: number;
  reason: string;
  closes: number[];
}

export interface LTFLiquidityScanResponse {
  results: LTFLiquiditySignal[];
  scanned_symbols: number;
  ltf_timeframe: string;
  htf_timeframe: string;
}

export type Timeframe = "1m" | "5m" | "15m" | "30m" | "1h" | "4h" | "1d";
export type HTFTimeframe = "1h" | "4h" | "1d";
export type LTFTimeframe = "1m" | "5m";
export interface MatchResult {
  symbol: string;
  exchange: string;
  timeframe: string;
  similarity: number;
  start_time: number;
  end_time: number;
  closes: number[];
}

export interface SearchResponse {
  results: MatchResult[];
  scanned_symbols: number;
  timeframe: string;
  algorithm: string;
}

export type Timeframe = "1m" | "5m" | "15m" | "30m" | "1h" | "4h" | "1d";
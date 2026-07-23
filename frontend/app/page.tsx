"use client";

import { useRef, useState } from "react";
import DrawingCanvas, { DrawingCanvasHandle } from "@/components/canvas/DrawingCanvas";
import { extractOrderedYValues } from "@/components/canvas/canvasUtils";
import ClearButton from "@/components/ui/ClearButton";
import SearchButton from "@/components/ui/SearchButton";
import ResultsList from "@/components/results/ResultsList";
import { searchMarket } from "@/lib/api";
import type { MatchResult, Timeframe } from "@/types/result";

const TIMEFRAMES: Timeframe[] = ["1m", "5m", "15m","30m", "1h", "4h", "1d"];

export default function Home() {
  const canvasRef = useRef<DrawingCanvasHandle>(null);
  const [results, setResults] = useState<MatchResult[]>([]);
  const [scannedSymbols, setScannedSymbols] = useState<number | undefined>(undefined);
  const [timeframe, setTimeframe] = useState<Timeframe>("1h");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleClear = () => {
    canvasRef.current?.clear();
    setResults([]);
    setError(null);
  };

  const handleSearch = async () => {
    if (!canvasRef.current || canvasRef.current.isEmpty()) {
      setError("Draw a pattern first.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const points = canvasRef.current.getPoints();
      const yValues = extractOrderedYValues(points, 60);

      const response = await searchMarket({
        drawingPointsY: yValues,
        timeframe,
      });

      setResults(response.results);
      setScannedSymbols(response.scanned_symbols);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen flex flex-col items-center gap-8 px-6 py-10">
      <header className="text-center">
        <h1 className="text-3xl font-bold text-textPrimary">CryptoSketch</h1>
        <p className="text-textMuted mt-1">
          Draw a chart pattern. Scan the live crypto market for real matches.
        </p>
      </header>

      <section className="flex flex-col items-center gap-4">
        <DrawingCanvas ref={canvasRef} />

        <div className="flex items-center gap-3">
          <select
            value={timeframe}
            onChange={(e) => setTimeframe(e.target.value as Timeframe)}
            className="bg-surface border border-border rounded-md px-3 py-2 text-textPrimary"
          >
            {TIMEFRAMES.map((tf) => (
              <option key={tf} value={tf}>
                {tf}
              </option>
            ))}
          </select>

          <ClearButton onClick={handleClear} disabled={loading} />
          <SearchButton onClick={handleSearch} loading={loading} />
        </div>

        {error && <p className="text-red-400 text-sm">{error}</p>}
      </section>

      <section className="w-full max-w-2xl">
        <ResultsList results={results} scannedSymbols={scannedSymbols} />
      </section>
    </main>
  );
}
"use client";

import { useRef, useState } from "react";
import DrawingCanvas, { DrawingCanvasHandle } from "@/components/canvas/DrawingCanvas";
import { extractOrderedYValues } from "@/components/canvas/canvasUtils";
import ClearButton from "@/components/ui/ClearButton";
import SearchButton from "@/components/ui/SearchButton";
import ToolPanel from "@/components/ui/ToolPanel";
import ScannerModeSelector, { ScannerMode } from "@/components/ui/ScannerModeSelector";
import ResultsList from "@/components/results/ResultsList";
import HTFLiquidityCard from "@/components/results/HTFLiquidityCard";
import LTFLiquidityCard from "@/components/results/LTFLiquidityCard";
import { searchMarket, scanConcept, htfLiquidityScan, ltfLiquidityScan } from "@/lib/api";
import type {
  MatchResult,
  Timeframe,
  HTFTimeframe,
  LTFTimeframe,
  HTFLiquidityResult,
  LTFLiquiditySignal,
} from "@/types/result";

const TIMEFRAMES: Timeframe[] = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"];
const HTF_TIMEFRAMES: HTFTimeframe[] = ["1h", "4h", "1d"];
const LTF_TIMEFRAMES: LTFTimeframe[] = ["1m", "5m"];

export default function Home() {
  const canvasRef = useRef<DrawingCanvasHandle>(null);

  const [mode, setMode] = useState<ScannerMode>("pattern");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scannedSymbols, setScannedSymbols] = useState<number | undefined>(undefined);

  // Pattern scanner state
  const [results, setResults] = useState<MatchResult[]>([]);
  const [timeframe, setTimeframe] = useState<Timeframe>("1h");
  const [activeConcept, setActiveConcept] = useState<string | null>(null);

  // Liquidity scanner state
  const [htfTimeframe, setHtfTimeframe] = useState<HTFTimeframe>("1h");
  const [ltfTimeframe, setLtfTimeframe] = useState<LTFTimeframe>("5m");
  const [htfResults, setHtfResults] = useState<HTFLiquidityResult[]>([]);
  const [ltfResults, setLtfResults] = useState<LTFLiquiditySignal[]>([]);

  const handleModeChange = (newMode: ScannerMode) => {
    setMode(newMode);
    setError(null);
    setResults([]);
    setHtfResults([]);
    setLtfResults([]);
    setActiveConcept(null);
  };

  const handleClear = () => {
    canvasRef.current?.clear();
    setResults([]);
    setError(null);
    setActiveConcept(null);
  };

  const handleSearch = async () => {
    if (!canvasRef.current || canvasRef.current.isEmpty()) {
      setError("Draw a pattern first.");
      return;
    }

    setLoading(true);
    setError(null);
    setActiveConcept(null);

    try {
      const points = canvasRef.current.getPoints();
      const yValues = extractOrderedYValues(points, 60);

      const response = await searchMarket({ drawingPointsY: yValues, timeframe });
      setResults(response.results);
      setScannedSymbols(response.scanned_symbols);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleConceptSelect = async (conceptKey: string) => {
    setLoading(true);
    setError(null);
    setActiveConcept(conceptKey);

    try {
      const response = await scanConcept({ concept: conceptKey, timeframe });
      setResults(response.results);
      setScannedSymbols(response.scanned_symbols);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Concept scan failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleHtfScan = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await htfLiquidityScan({ timeframe: htfTimeframe });
      setHtfResults(response.results);
      setScannedSymbols(response.scanned_symbols);
    } catch (e) {
      setError(e instanceof Error ? e.message : "HTF liquidity scan failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleLtfScan = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await ltfLiquidityScan({ ltfTimeframe, htfTimeframe });
      setLtfResults(response.results);
      setScannedSymbols(response.scanned_symbols);
    } catch (e) {
      setError(e instanceof Error ? e.message : "LTF liquidity scan failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen flex flex-col items-center gap-6 px-6 py-10">
      <header className="text-center">
        <h1 className="text-3xl font-bold text-textPrimary">CryptoSketch</h1>
        <p className="text-textMuted mt-1">
          Draw a chart pattern, pick a market concept, or run a liquidity scan on the live market.
        </p>
      </header>

      <ScannerModeSelector mode={mode} onChange={handleModeChange} disabled={loading} />

      {mode === "pattern" && (
        <>
          <section className="flex items-start gap-4">
            <ToolPanel onSelect={handleConceptSelect} activeConcept={activeConcept} disabled={loading} />

            <div className="flex flex-col items-center gap-4">
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
            </div>
          </section>

          <section className="w-full max-w-2xl">
            <ResultsList results={results} scannedSymbols={scannedSymbols} />
          </section>
        </>
      )}

      {mode === "htf-liquidity" && (
        <>
          <section className="flex items-center gap-3">
            <select
              value={htfTimeframe}
              onChange={(e) => setHtfTimeframe(e.target.value as HTFTimeframe)}
              className="bg-surface border border-border rounded-md px-3 py-2 text-textPrimary"
            >
              {HTF_TIMEFRAMES.map((tf) => (
                <option key={tf} value={tf}>
                  {tf}
                </option>
              ))}
            </select>
            <SearchButton onClick={handleHtfScan} loading={loading} />
          </section>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <section className="w-full max-w-2xl flex flex-col gap-3">
            {scannedSymbols !== undefined && (
              <p className="text-textMuted text-sm">
                Scanned {scannedSymbols} live USDT pairs · top {htfResults.length} matches
              </p>
            )}
            {htfResults.length === 0 ? (
              <p className="text-textMuted text-center py-8">No results yet. Run a scan.</p>
            ) : (
              htfResults.map((r) => <HTFLiquidityCard key={`${r.exchange}-${r.symbol}`} result={r} />)
            )}
          </section>
        </>
      )}

      {mode === "ltf-liquidity" && (
        <>
          <section className="flex items-center gap-3">
            <select
              value={htfTimeframe}
              onChange={(e) => setHtfTimeframe(e.target.value as HTFTimeframe)}
              className="bg-surface border border-border rounded-md px-3 py-2 text-textPrimary"
            >
              {HTF_TIMEFRAMES.map((tf) => (
                <option key={tf} value={tf}>
                  HTF {tf}
                </option>
              ))}
            </select>
            <select
              value={ltfTimeframe}
              onChange={(e) => setLtfTimeframe(e.target.value as LTFTimeframe)}
              className="bg-surface border border-border rounded-md px-3 py-2 text-textPrimary"
            >
              {LTF_TIMEFRAMES.map((tf) => (
                <option key={tf} value={tf}>
                  LTF {tf}
                </option>
              ))}
            </select>
            <SearchButton onClick={handleLtfScan} loading={loading} />
          </section>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <section className="w-full max-w-2xl flex flex-col gap-3">
            {scannedSymbols !== undefined && (
              <p className="text-textMuted text-sm">
                Scanned {scannedSymbols} live USDT pairs · {ltfResults.length} signals
              </p>
            )}
            {ltfResults.length === 0 ? (
              <p className="text-textMuted text-center py-8">No signals yet. Run a scan.</p>
            ) : (
              ltfResults.map((r) => <LTFLiquidityCard key={`${r.exchange}-${r.symbol}`} result={r} />)
            )}
          </section>
        </>
      )}
    </main>
  );
}
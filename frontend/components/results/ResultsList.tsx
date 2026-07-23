import type { MatchResult } from "@/types/result";
import ResultCard from "./ResultCard";

interface ResultsListProps {
  results: MatchResult[];
  scannedSymbols?: number;
}

export default function ResultsList({ results, scannedSymbols }: ResultsListProps) {
  if (results.length === 0) {
    return <p className="text-textMuted text-center py-8">No matches yet. Draw a pattern and search.</p>;
  }

  return (
    <div className="flex flex-col gap-3">
      {scannedSymbols !== undefined && (
        <p className="text-textMuted text-sm">
          Scanned {scannedSymbols} live USDT pairs · top {results.length} matches
        </p>
      )}
      {results.map((r) => (
        <ResultCard key={`${r.exchange}-${r.symbol}-${r.start_time}`} result={r} />
      ))}
    </div>
  );
}
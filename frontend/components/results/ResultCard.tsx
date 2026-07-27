import type { MatchResult } from "@/types/result";
import MiniChart from "./MiniChart";

interface ResultCardProps {
  result: MatchResult;
}

export default function ResultCard({ result }: ResultCardProps) {
  const binanceChartUrl = `https://www.binance.com/en/trade/${result.symbol}`;

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border bg-surface p-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex flex-col gap-1 min-w-[140px]">
          <span className="text-textPrimary font-semibold">{result.symbol}</span>
          <span className="text-textMuted text-sm">
            {result.exchange} · {result.timeframe}
          </span>
        </div>

        <MiniChart closes={result.closes} />

        <div className="flex flex-col items-end gap-2 min-w-[100px]">
          <span className="text-accent font-bold text-lg">{result.similarity}%</span>
          <a
            href={binanceChartUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-textMuted hover:text-accent transition-colors"
          >
            Open full chart →
          </a>
        </div>
      </div>

      {result.reasons.length > 0 && (
        <div className="flex flex-col gap-1 pt-2 border-t border-border">
          <span className="text-textMuted text-xs uppercase tracking-wide">Matched because</span>
          <ul className="flex flex-col gap-0.5">
            {result.reasons.map((reason, i) => (
              <li key={i} className="text-sm text-textPrimary flex items-center gap-1.5">
                <span className="text-accent">✓</span>
                {reason}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
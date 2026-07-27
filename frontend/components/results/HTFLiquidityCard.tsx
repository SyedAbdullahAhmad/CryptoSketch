import type { HTFLiquidityResult } from "@/types/result";
import MiniChart from "./MiniChart";

interface HTFLiquidityCardProps {
  result: HTFLiquidityResult;
}

export default function HTFLiquidityCard({ result }: HTFLiquidityCardProps) {
  const binanceChartUrl = `https://www.binance.com/en/trade/${result.symbol}`;
  const trendColor =
    result.trend === "bullish" ? "text-accent" : result.trend === "bearish" ? "text-red-400" : "text-textMuted";

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

        <div className="flex flex-col items-end gap-1 min-w-[120px]">
          <span className={`font-bold ${trendColor}`}>{result.trend.toUpperCase()}</span>
          <span className="text-sm text-textMuted">Bias: {result.bias.toUpperCase()}</span>
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

      <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-textMuted pt-2 border-t border-border">
        <span>Liquidity: {result.liquidity_type} @ {result.liquidity_zone}</span>
        <span className={result.liquidity_taken ? "text-red-400" : "text-accent"}>
          {result.liquidity_taken ? "Already taken" : "Not yet taken"}
        </span>
        <span>{result.event_liquidity ? "Event-level liquidity" : "Standard liquidity"}</span>
        <span>Confidence: {result.confidence}</span>
      </div>
      <p className="text-sm text-textPrimary">{result.reason}</p>
    </div>
  );
}
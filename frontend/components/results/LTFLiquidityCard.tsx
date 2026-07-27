import type { LTFLiquiditySignal } from "@/types/result";
import MiniChart from "./MiniChart";

interface LTFLiquidityCardProps {
  result: LTFLiquiditySignal;
}

export default function LTFLiquidityCard({ result }: LTFLiquidityCardProps) {
  const binanceChartUrl = `https://www.binance.com/en/trade/${result.symbol}`;
  const signalColor = result.signal === "BUY" ? "text-accent" : "text-red-400";

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border bg-surface p-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex flex-col gap-1 min-w-[140px]">
          <span className="text-textPrimary font-semibold">{result.symbol}</span>
          <span className="text-textMuted text-sm">
            {result.exchange} · {result.timeframe} (HTF {result.htf_timeframe})
          </span>
        </div>

        <MiniChart closes={result.closes} />

        <div className="flex flex-col items-end gap-1 min-w-[120px]">
          <span className={`font-bold text-lg ${signalColor}`}>{result.signal}</span>
          <span className="text-sm text-textMuted">Confidence: {result.confidence}</span>
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

      <div className="grid grid-cols-3 gap-2 pt-2 border-t border-border">
        <div className="flex flex-col">
          <span className="text-textMuted text-xs uppercase tracking-wide">Entry</span>
          <span className="text-textPrimary font-medium">{result.entry_price}</span>
        </div>
        <div className="flex flex-col">
          <span className="text-textMuted text-xs uppercase tracking-wide">Stop Loss</span>
          <span className="text-red-400 font-medium">{result.stop_loss}</span>
        </div>
        <div className="flex flex-col">
          <span className="text-textMuted text-xs uppercase tracking-wide">Target</span>
          <span className="text-accent font-medium">{result.target_price}</span>
        </div>
      </div>

      <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-textMuted pt-2 border-t border-border">
        <span>Trend: {result.trend}</span>
        <span>HTF Bias: {result.htf_bias}</span>
        <span>Liquidity: {result.liquidity_type} @ {result.liquidity_price}</span>
        <span>Status: {result.liquidity_status}</span>
      </div>
      <p className="text-sm text-textPrimary">{result.reason}</p>
    </div>
  );
}
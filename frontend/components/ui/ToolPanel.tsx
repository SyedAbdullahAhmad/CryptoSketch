"use client";

interface Tool {
  key: string;
  label: string;
}

const TOOLS: Tool[] = [
  { key: "trend", label: "Trend" },
  { key: "higher_highs", label: "Higher Highs" },
  { key: "higher_lows", label: "Higher Lows" },
  { key: "lower_highs", label: "Lower Highs" },
  { key: "lower_lows", label: "Lower Lows" },
  { key: "break_of_structure", label: "Break of Structure" },
  { key: "change_of_character", label: "Change of Character" },
  { key: "support", label: "Support" },
  { key: "resistance", label: "Resistance" },
  { key: "trendline", label: "Trendline" },
  { key: "trendline_support_bounce", label: "Trendline Bounce" },
  { key: "ascending_triangle", label: "Ascending Triangle" },
  { key: "descending_triangle", label: "Descending Triangle" },
  { key: "symmetrical_triangle", label: "Symmetrical Triangle" },
  { key: "bull_flag", label: "Bull Flag" },
  { key: "bear_flag", label: "Bear Flag" },
  { key: "channel", label: "Channel" },
  { key: "double_top", label: "Double Top" },
  { key: "double_bottom", label: "Double Bottom" },
  { key: "head_and_shoulders", label: "Head & Shoulders" },
  { key: "inverse_head_and_shoulders", label: "Inverse H&S" },
  { key: "cup_and_handle", label: "Cup & Handle" },
  { key: "rounded_bottom", label: "Rounded Bottom" },
  { key: "rounded_top", label: "Rounded Top" },
  { key: "consolidation", label: "Consolidation" },
  { key: "liquidity_sweep", label: "Liquidity Sweep" },
  { key: "equal_highs", label: "Equal Highs" },
  { key: "equal_lows", label: "Equal Lows" },
  { key: "fair_value_gap", label: "Fair Value Gap" },
  { key: "order_block", label: "Order Block" },
  { key: "breaker_block", label: "Breaker Block" },
  { key: "mitigation_block", label: "Mitigation Block" },
  { key: "imbalance", label: "Imbalance" },
];

interface ToolPanelProps {
  onSelect: (conceptKey: string) => void;
  activeConcept?: string | null;
  disabled?: boolean;
}

export default function ToolPanel({ onSelect, activeConcept, disabled }: ToolPanelProps) {
  return (
    <div className="flex flex-col gap-1 w-48 max-h-[400px] overflow-y-auto rounded-lg border border-border bg-surface p-2">
      {TOOLS.map((tool) => (
        <button
          key={tool.key}
          onClick={() => onSelect(tool.key)}
          disabled={disabled}
          className={`text-left text-sm px-3 py-2 rounded-md transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
            activeConcept === tool.key
              ? "bg-accent text-background font-medium"
              : "text-textMuted hover:text-textPrimary hover:bg-background"
          }`}
        >
          {tool.label}
        </button>
      ))}
    </div>
  );
}
"use client";

export type ScannerMode = "pattern" | "htf-liquidity" | "ltf-liquidity";

interface ScannerModeSelectorProps {
  mode: ScannerMode;
  onChange: (mode: ScannerMode) => void;
  disabled?: boolean;
}

const OPTIONS: { value: ScannerMode; label: string }[] = [
  { value: "pattern", label: "Pattern Scanner" },
  { value: "htf-liquidity", label: "Higher Timeframe Liquidity" },
  { value: "ltf-liquidity", label: "Lower Timeframe Liquidity" },
];

export default function ScannerModeSelector({ mode, onChange, disabled }: ScannerModeSelectorProps) {
  return (
    <div className="flex flex-wrap items-center gap-4 rounded-lg border border-border bg-surface px-4 py-3">
      <span className="text-textMuted text-sm font-medium">Scanner Type</span>
      {OPTIONS.map((opt) => (
        <label key={opt.value} className="flex items-center gap-2 text-sm text-textPrimary cursor-pointer">
          <input
            type="radio"
            name="scanner-mode"
            value={opt.value}
            checked={mode === opt.value}
            onChange={() => onChange(opt.value)}
            disabled={disabled}
            className="accent-accent"
          />
          {opt.label}
        </label>
      ))}
    </div>
  );
}
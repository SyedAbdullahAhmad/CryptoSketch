"use client";

interface ClearButtonProps {
  onClick: () => void;
  disabled?: boolean;
}

export default function ClearButton({ onClick, disabled }: ClearButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="px-4 py-2 rounded-md border border-border text-textMuted hover:text-textPrimary hover:border-textMuted transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
    >
      Clear
    </button>
  );
}
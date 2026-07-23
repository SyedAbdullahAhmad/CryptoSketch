"use client";

interface SearchButtonProps {
  onClick: () => void;
  loading?: boolean;
  disabled?: boolean;
}

export default function SearchButton({ onClick, loading, disabled }: SearchButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className="px-6 py-2 rounded-md bg-accent text-background font-medium hover:bg-accentMuted hover:text-textPrimary transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
    >
      {loading ? "Scanning market..." : "Search"}
    </button>
  );
}
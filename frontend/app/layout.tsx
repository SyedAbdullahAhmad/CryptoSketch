import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CryptoSketch",
  description: "Draw a chart pattern, find it live in the crypto market.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
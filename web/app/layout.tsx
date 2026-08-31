import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Employer Intelligence",
  description:
    "Whether a public company can afford you, read from its own SEC filings.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

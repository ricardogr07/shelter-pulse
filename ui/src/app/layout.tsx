import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const SITE_URL = "https://sh-f52a79071fe149e0ac99448fc11e8496.ecs.us-east-1.on.aws";

export const metadata: Metadata = {
  title: {
    default: "ShelterPulse",
    template: "%s | ShelterPulse",
  },
  description:
    "Simulation and optimization lab for cat-shelter resource allocation during kitten season. Bayesian optimization finds the best budget split to minimize overflow.",
  metadataBase: new URL(SITE_URL),
  openGraph: {
    title: "ShelterPulse — Kitten Season Resource Optimizer",
    description:
      "Simulate your shelter capacity under uncertainty and find the optimal budget allocation to minimize overflow during kitten season.",
    siteName: "ShelterPulse",
    type: "website",
    locale: "en_US",
    url: SITE_URL,
  },
  twitter: {
    card: "summary",
    title: "ShelterPulse",
    description:
      "Simulate your shelter. Optimize your budget. Zero overflow.",
  },
  robots: {
    index: true,
    follow: true,
  },
  alternates: {
    canonical: SITE_URL,
    languages: {
      en: `${SITE_URL}/en`,
      es: `${SITE_URL}/es`,
    },
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}

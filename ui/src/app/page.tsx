import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "ShelterPulse - Redirecting",
  other: {
    "http-equiv": "refresh",
  },
};

/**
 * Root page - immediately redirects to /en.
 * Uses meta-refresh redirect since Next.js static export doesn't support server redirects.
 * Nginx also handles this with a 301, so this is a fallback.
 */
export default function RootPage() {
  return (
    <>
      <meta httpEquiv="refresh" content="0;url=/en" />
      <noscript>
        <p>
          Redirecting to <Link href="/en">/en</Link>...
        </p>
      </noscript>
    </>
  );
}

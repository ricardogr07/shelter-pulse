'use client';

import { useState } from 'react';
import Link from "next/link";
import { usePathname } from "next/navigation";
import { getDictionary, locales } from "@/i18n/dictionaries";

export default function NavBar({ lang }: { lang: string }) {
  const t = getDictionary(lang);
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  function langHref(locale: string) {
    const rest = pathname.replace(/^\/[a-z]{2}/, '');
    return `/${locale}${rest || ''}`;
  }

  const links = [
    { href: `/${lang}`, label: t.nav.home },
    { href: `/${lang}/demo`, label: t.nav.demo },
    { href: `/${lang}/how-it-works`, label: t.nav.howItWorks },
    { href: `/${lang}/simulate`, label: t.nav.buildCustom },
  ];

  return (
    <nav className="sticky top-0 z-50 bg-white/80 dark:bg-zinc-900/80 backdrop-blur border-b border-zinc-200 dark:border-zinc-800">
      <div className="max-w-5xl mx-auto flex items-center justify-between px-4 h-14">
        <Link href={`/${lang}`} className="text-lg font-bold text-zinc-900 dark:text-zinc-50">
          🐱 ShelterPulse
        </Link>
        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-6 text-sm font-medium">
          {links.map(l => (
            <Link key={l.href} href={l.href} className="text-zinc-600 hover:text-amber-500 dark:text-zinc-400 dark:hover:text-amber-400">
              {l.label}
            </Link>
          ))}
          <span className="border-l border-zinc-300 dark:border-zinc-700 pl-4 flex gap-2 text-xs">
            {locales.map((locale) => (
              <Link
                key={locale}
                href={langHref(locale)}
                className={`uppercase ${locale === lang ? 'text-amber-500 font-bold' : 'text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300'}`}
              >
                {locale}
              </Link>
            ))}
          </span>
        </div>
        {/* Mobile hamburger */}
        <button onClick={() => setOpen(!open)} className="md:hidden p-2 text-zinc-600 dark:text-zinc-300" aria-label="Toggle menu">
          <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            {open ? <path d="M6 18L18 6M6 6l12 12" /> : <path d="M4 6h16M4 12h16M4 18h16" />}
          </svg>
        </button>
      </div>
      {/* Mobile panel */}
      {open && (
        <div className="md:hidden border-t border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 px-4 py-3 space-y-2">
          {links.map(l => (
            <Link key={l.href} href={l.href} onClick={() => setOpen(false)} className="block text-sm text-zinc-700 dark:text-zinc-300 hover:text-amber-500">
              {l.label}
            </Link>
          ))}
          <div className="flex gap-3 pt-2 border-t border-zinc-200 dark:border-zinc-800 text-xs">
            {locales.map((locale) => (
              <Link key={locale} href={langHref(locale)} onClick={() => setOpen(false)}
                className={`uppercase ${locale === lang ? 'text-amber-500 font-bold' : 'text-zinc-400'}`}>
                {locale}
              </Link>
            ))}
          </div>
        </div>
      )}
    </nav>
  );
}

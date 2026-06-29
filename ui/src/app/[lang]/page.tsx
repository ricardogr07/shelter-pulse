import Link from "next/link";
import type { Metadata } from "next";
import { getDictionary } from "@/i18n/dictionaries";

export async function generateMetadata({ params }: { params: Promise<{ lang: string }> }): Promise<Metadata> {
  const { lang } = await params;
  const descriptions: Record<string, string> = {
    en: "Simulate your cat shelter's capacity under uncertainty and optimize budget allocation during kitten season.",
    es: "Simula la capacidad de tu refugio de gatos bajo incertidumbre y optimiza la asignación de presupuesto durante la temporada de gatitos.",
  };
  return {
    title: "Home",
    description: descriptions[lang] ?? descriptions.en,
    openGraph: { title: "ShelterPulse — Kitten Season Resource Optimizer" },
  };
}

export default async function LandingPage({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  const t = getDictionary(lang);

  return (
    <main className="bg-zinc-50 dark:bg-zinc-950">
      {/* Hero */}
      <section className="max-w-4xl mx-auto px-4 py-24 text-center">
        <h1 className="text-5xl font-bold text-zinc-900 dark:text-zinc-50 leading-tight whitespace-pre-line">
          {t.landing.title}
        </h1>
        <p className="mt-4 text-lg text-zinc-600 dark:text-zinc-400 max-w-2xl mx-auto">
          {t.landing.subtitle}
        </p>
        <div className="mt-8 flex justify-center gap-4 flex-wrap">
          <Link
            href={`/${lang}/demo`}
            className="px-6 py-3 bg-amber-500 hover:bg-amber-400 text-white font-semibold rounded-lg transition-colors"
          >
            {t.landing.ctaDemo}
          </Link>
          <Link
            href={`/${lang}/simulate`}
            className="px-6 py-3 border border-zinc-300 dark:border-zinc-600 text-zinc-700 dark:text-zinc-300 font-semibold rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
          >
            {t.landing.ctaCustom}
          </Link>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-5xl mx-auto px-4 pb-24">
        <div className="grid md:grid-cols-3 gap-6">
          <div className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 p-6">
            <div className="text-3xl mb-3">🎲</div>
            <h3 className="font-semibold text-zinc-900 dark:text-zinc-50 mb-2">{t.landing.feat1Title}</h3>
            <p className="text-sm text-zinc-600 dark:text-zinc-400">{t.landing.feat1Desc}</p>
          </div>
          <div className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 p-6">
            <div className="text-3xl mb-3">📈</div>
            <h3 className="font-semibold text-zinc-900 dark:text-zinc-50 mb-2">{t.landing.feat2Title}</h3>
            <p className="text-sm text-zinc-600 dark:text-zinc-400">{t.landing.feat2Desc}</p>
          </div>
          <div className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 p-6">
            <div className="text-3xl mb-3">🛠️</div>
            <h3 className="font-semibold text-zinc-900 dark:text-zinc-50 mb-2">{t.landing.feat3Title}</h3>
            <p className="text-sm text-zinc-600 dark:text-zinc-400">{t.landing.feat3Desc}</p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-zinc-200 dark:border-zinc-800 py-8 text-center text-sm text-zinc-500 dark:text-zinc-400">
        <p>{t.landing.footer1}</p>
        <p className="mt-1">{t.landing.footer2}</p>
        <p className="mt-1">Built by Ricardo García Ramírez</p>
        <div className="mt-3 flex justify-center gap-5">
          <a href="https://github.com/ricardogr07" target="_blank" rel="noopener noreferrer" className="hover:text-amber-500 transition-colors" aria-label="GitHub">
            <svg className="w-5 h-5 inline" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0 1 12 6.844a9.59 9.59 0 0 1 2.504.337c1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.02 10.02 0 0 0 22 12.017C22 6.484 17.522 2 12 2z"/></svg>
          </a>
          <a href="https://ricardogr07.github.io/" target="_blank" rel="noopener noreferrer" className="hover:text-amber-500 transition-colors" aria-label="Website">
            <svg className="w-5 h-5 inline" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
          </a>
          <a href="https://www.linkedin.com/in/ricardogarciaramirez/" target="_blank" rel="noopener noreferrer" className="hover:text-amber-500 transition-colors" aria-label="LinkedIn">
            <svg className="w-5 h-5 inline" fill="currentColor" viewBox="0 0 24 24"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
          </a>
        </div>
      </footer>
    </main>
  );
}

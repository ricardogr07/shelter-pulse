import type { Metadata } from "next";
import SimulateClient from "./SimulateClient";

export async function generateMetadata({ params }: { params: Promise<{ lang: string }> }): Promise<Metadata> {
  const { lang } = await params;
  const descriptions: Record<string, string> = {
    en: "Build a custom shelter simulation: configure capacity, budget, and seasonal parameters, then optimize with Bayesian search.",
    es: "Construye una simulación personalizada: configura capacidad, presupuesto y parámetros estacionales, luego optimiza con búsqueda bayesiana.",
  };
  return {
    title: "Simulate",
    description: descriptions[lang] ?? descriptions.en,
  };
}

export default async function SimulatePage({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  return <SimulateClient lang={lang} />;
}

import type { Metadata } from "next";
import HowItWorksClient from "./HowItWorksClient";

export async function generateMetadata({ params }: { params: Promise<{ lang: string }> }): Promise<Metadata> {
  const { lang } = await params;
  const descriptions: Record<string, string> = {
    en: "How ShelterPulse works: discrete-event simulation, common random numbers, and Bayesian optimization for cat shelter resource allocation.",
    es: "Cómo funciona ShelterPulse: simulación de eventos discretos, números aleatorios comunes y optimización bayesiana para la asignación de recursos en refugios de gatos.",
  };
  return {
    title: "How It Works",
    description: descriptions[lang] ?? descriptions.en,
  };
}

export default async function HowItWorksPage({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  return <HowItWorksClient lang={lang} />;
}

import type { Metadata } from "next";
import DemoClient from "./DemoClient";

export async function generateMetadata({ params }: { params: Promise<{ lang: string }> }): Promise<Metadata> {
  const { lang } = await params;
  const descriptions: Record<string, string> = {
    en: "Interactive demo: compare Whisker Haven budget allocations during kitten season.",
    es: "Demo interactiva: compara asignaciones de presupuesto de Whisker Haven durante la temporada de gatitos.",
  };
  return {
    title: "Demo",
    description: descriptions[lang] ?? descriptions.en,
  };
}

export default async function DemoPage({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  return <DemoClient lang={lang} />;
}

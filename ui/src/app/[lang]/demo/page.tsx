import type { Metadata } from "next";
import DemoClient from "./DemoClient";

export async function generateMetadata({ params }: { params: Promise<{ lang: string }> }): Promise<Metadata> {
  const { lang } = await params;
  const descriptions: Record<string, string> = {
    en: "Interactive demo: optimize Whisker Haven's budget allocation to eliminate overflow during kitten season.",
    es: "Demo interactiva: optimiza la asignación de presupuesto de Whisker Haven para eliminar el desbordamiento durante la temporada de gatitos.",
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

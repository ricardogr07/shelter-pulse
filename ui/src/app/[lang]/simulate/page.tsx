import SimulateClient from "./SimulateClient";

export default async function SimulatePage({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  return <SimulateClient lang={lang} />;
}

import HowItWorksClient from "./HowItWorksClient";

export default async function HowItWorksPage({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  return <HowItWorksClient lang={lang} />;
}

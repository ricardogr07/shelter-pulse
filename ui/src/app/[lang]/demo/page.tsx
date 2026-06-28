import DemoClient from "./DemoClient";

export default async function DemoPage({ params }: { params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  return <DemoClient lang={lang} />;
}

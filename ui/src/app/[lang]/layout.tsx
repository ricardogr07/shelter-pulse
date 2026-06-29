import NavBar from "@/components/NavBar";
import { locales } from "@/i18n/dictionaries";

export function generateStaticParams() {
  return locales.map((lang) => ({ lang }));
}

export default async function LangLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  return (
    <>
      <NavBar lang={lang} />
      <div className="flex-1">{children}</div>
    </>
  );
}

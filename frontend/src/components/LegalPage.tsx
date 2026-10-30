import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

// Mise en page commune des pages légales (politique de confidentialité, conditions
// d'utilisation, mentions légales) : titre, date de la dernière mise à jour, introduction, puis
// des sections (LegalSection)
interface LegalPageProps {
  title: string;
  // Date AAAA-MM-JJ, dans constants/legal.ts
  updatedAt: string;
  intro: string;
  children: ReactNode;
}

export function LegalPage({ title, updatedAt, intro, children }: LegalPageProps) {
  const { t } = useTranslation();

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-col gap-8 px-4 py-10 text-sm leading-relaxed">
      <header className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">{title}</h1>
        <p className="text-muted-foreground">
          {t('legalPages.updatedAt', { date: new Date(updatedAt) })}
        </p>
        <p>{intro}</p>
      </header>
      {children}
    </main>
  );
}

export function LegalSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-lg font-semibold">{title}</h2>
      {children}
    </section>
  );
}

// Liste à puces d'une section
export function LegalList({ items }: { items: string[] }) {
  return (
    <ul className="list-disc space-y-1 pl-5">
      {items.map((item: string) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import {
  CNIL_COMPLAINT_URL,
  LEGAL_CONTROLLER_NAME,
  PRIVACY_CONTACT_EMAIL,
  PRIVACY_POLICY_UPDATED_AT,
} from '../constants/legal';

const LINK_CLASS = 'font-medium underline underline-offset-4';

// Politique de confidentialité (#200), lisible sans compte. Le texte vient des locales
// (privacy.*) ; ce qu'il décrit est l'inventaire de docs/technical/legal-pages.md.
export function PrivacyPolicyPage() {
  const { t } = useTranslation();

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-col gap-8 px-4 py-10 text-sm leading-relaxed">
      <header className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">{t('privacy.title')}</h1>
        <p className="text-muted-foreground">
          {t('privacy.updatedAt', { date: new Date(PRIVACY_POLICY_UPDATED_AT) })}
        </p>
        <p>{t('privacy.intro')}</p>
      </header>

      <PolicySection title={t('privacy.controller.title')}>
        <p>{t('privacy.controller.body', { name: LEGAL_CONTROLLER_NAME })}</p>
        <p>
          <a href={`mailto:${PRIVACY_CONTACT_EMAIL}`} className={LINK_CLASS}>
            {PRIVACY_CONTACT_EMAIL}
          </a>
        </p>
      </PolicySection>

      <PolicySection title={t('privacy.data.title')}>
        <ul className="list-disc space-y-1 pl-5">
          <li>{t('privacy.data.account')}</li>
          <li>{t('privacy.data.google')}</li>
          <li>{t('privacy.data.guest')}</li>
          <li>{t('privacy.data.content')}</li>
          <li>{t('privacy.data.games')}</li>
          <li>{t('privacy.data.technical')}</li>
        </ul>
      </PolicySection>

      <PolicySection title={t('privacy.purposes.title')}>
        <ul className="list-disc space-y-1 pl-5">
          <li>{t('privacy.purposes.service')}</li>
          <li>{t('privacy.purposes.security')}</li>
        </ul>
        <p>{t('privacy.purposes.noAds')}</p>
      </PolicySection>

      <PolicySection title={t('privacy.retention.title')}>
        <ul className="list-disc space-y-1 pl-5">
          <li>{t('privacy.retention.account')}</li>
          <li>{t('privacy.retention.sessions')}</li>
          <li>{t('privacy.retention.links')}</li>
          <li>{t('privacy.retention.guests')}</li>
          <li>{t('privacy.retention.deleted')}</li>
          <li>{t('privacy.retention.backups')}</li>
        </ul>
      </PolicySection>

      <PolicySection title={t('privacy.visibility.title')}>
        <ul className="list-disc space-y-1 pl-5">
          <li>{t('privacy.visibility.room')}</li>
          <li>{t('privacy.visibility.results')}</li>
          <li>{t('privacy.visibility.deletedAccount')}</li>
        </ul>
      </PolicySection>

      <PolicySection title={t('privacy.processors.title')}>
        <p>{t('privacy.processors.intro')}</p>
        <ul className="list-disc space-y-1 pl-5">
          <li>{t('privacy.processors.minestrator')}</li>
          <li>{t('privacy.processors.scaleway')}</li>
          <li>{t('privacy.processors.cloudflare')}</li>
          <li>{t('privacy.processors.google')}</li>
          <li>{t('privacy.processors.github')}</li>
        </ul>
        <p>{t('privacy.processors.transfers')}</p>
      </PolicySection>

      <PolicySection title={t('privacy.cookies.title')}>
        <p>{t('privacy.cookies.intro')}</p>
        <ul className="list-disc space-y-1 pl-5">
          <li>{t('privacy.cookies.session')}</li>
          <li>{t('privacy.cookies.google')}</li>
          <li>{t('privacy.cookies.guest')}</li>
          <li>{t('privacy.cookies.local')}</li>
        </ul>
      </PolicySection>

      <PolicySection title={t('privacy.security.title')}>
        <p>{t('privacy.security.body')}</p>
      </PolicySection>

      <PolicySection title={t('privacy.rights.title')}>
        <p>{t('privacy.rights.body')}</p>
        <ul className="list-disc space-y-1 pl-5">
          <li>{t('privacy.rights.delete')}</li>
          <li>{t('privacy.rights.request', { email: PRIVACY_CONTACT_EMAIL })}</li>
        </ul>
        <p>
          {t('privacy.rights.cnil')}{' '}
          <a href={CNIL_COMPLAINT_URL} target="_blank" rel="noreferrer" className={LINK_CLASS}>
            {t('privacy.rights.cnilLink')}
          </a>
        </p>
      </PolicySection>

      <PolicySection title={t('privacy.changes.title')}>
        <p>{t('privacy.changes.body')}</p>
      </PolicySection>
    </main>
  );
}

function PolicySection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-lg font-semibold">{title}</h2>
      {children}
    </section>
  );
}

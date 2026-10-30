import { useTranslation } from 'react-i18next';

import { LegalList, LegalPage, LegalSection } from '../components/LegalPage';
import { ReportContentSection } from '../components/ReportContentSection';
import { textLinkClassName } from '../components/ui/text-link';
import { LEGAL_CONTACT_EMAIL, TERMS_UPDATED_AT } from '../constants/legal';

// Conditions d'utilisation (#201), lisibles sans compte. Le texte vient des locales (terms.*) ;
// les règles qu'il décrit sont celles du code (docs/technical/legal-pages.md)
export function TermsPage() {
  const { t } = useTranslation();

  return (
    <LegalPage title={t('terms.title')} updatedAt={TERMS_UPDATED_AT} intro={t('terms.intro')}>
      <LegalSection title={t('terms.service.title')}>
        <p>{t('terms.service.body')}</p>
      </LegalSection>

      <LegalSection title={t('terms.account.title')}>
        <LegalList
          items={[t('terms.account.one'), t('terms.account.password'), t('terms.account.delete')]}
        />
      </LegalSection>

      <LegalSection title={t('terms.guests.title')}>
        <p>{t('terms.guests.body')}</p>
      </LegalSection>

      <LegalSection title={t('terms.content.title')}>
        <p>{t('terms.content.rights')}</p>
        <p>{t('terms.content.forbidden')}</p>
        <LegalList
          items={[
            t('terms.content.illegal'),
            t('terms.content.hateful'),
            t('terms.content.sexual'),
            t('terms.content.infringing'),
          ]}
        />
        <p>{t('terms.content.removal')}</p>
      </LegalSection>

      <LegalSection title={t('terms.visibility.title')}>
        <LegalList items={[t('terms.visibility.room'), t('terms.visibility.results')]} />
      </LegalSection>

      <ReportContentSection />

      <LegalSection title={t('terms.sanctions.title')}>
        <p>{t('terms.sanctions.body')}</p>
      </LegalSection>

      <LegalSection title={t('terms.availability.title')}>
        <p>{t('terms.availability.body')}</p>
      </LegalSection>

      <LegalSection title={t('terms.liability.title')}>
        <p>{t('terms.liability.body')}</p>
      </LegalSection>

      <LegalSection title={t('terms.law.title')}>
        <p>{t('terms.law.body')}</p>
      </LegalSection>

      <LegalSection title={t('terms.changes.title')}>
        <p>{t('terms.changes.body')}</p>
      </LegalSection>

      <LegalSection title={t('terms.contact.title')}>
        <p>{t('terms.contact.body')}</p>
        <p>
          <a href={`mailto:${LEGAL_CONTACT_EMAIL}`} className={textLinkClassName}>
            {LEGAL_CONTACT_EMAIL}
          </a>
        </p>
      </LegalSection>
    </LegalPage>
  );
}

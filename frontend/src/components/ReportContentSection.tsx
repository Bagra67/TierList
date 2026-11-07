import { useTranslation } from 'react-i18next';

import { LEGAL_CONTACT_EMAIL } from '../constants/legal';
import { LegalList, LegalSection } from './LegalPage';
import { textLinkClassName } from './ui/text-link';

export function ReportContentSection() {
  const { t } = useTranslation();

  return (
    <LegalSection title={t('legalPages.report.title')}>
      <p>{t('legalPages.report.intro')}</p>
      <p>
        <a href={`mailto:${LEGAL_CONTACT_EMAIL}`} className={textLinkClassName}>
          {LEGAL_CONTACT_EMAIL}
        </a>
      </p>
      <p>{t('legalPages.report.include')}</p>
      <LegalList
        items={[
          t('legalPages.report.page'),
          t('legalPages.report.content'),
          t('legalPages.report.reason'),
          t('legalPages.report.reply'),
        ]}
      />
      <p>{t('legalPages.report.next')}</p>
    </LegalSection>
  );
}

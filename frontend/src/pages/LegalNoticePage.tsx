import { Trans, useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import { LegalList, LegalPage, LegalSection } from '../components/LegalPage';
import { ReportContentSection } from '../components/ReportContentSection';
import { textLinkClassName } from '../components/ui/text-link';
import {
  LEGAL_CONTACT_EMAIL,
  LEGAL_CONTROLLER_NAME,
  LEGAL_HOST_ADDRESS,
  LEGAL_HOST_NAME,
  LEGAL_HOST_PHONE,
  LEGAL_NOTICE_UPDATED_AT,
} from '../constants/legal';
import { ROUTES } from '../constants/routes';

// Mentions légales (#235, LCEN art. 6-III), lisibles sans compte : éditeur, hébergeur,
// prestataires et signalement. Le texte vient des locales (legalNotice.*)
export function LegalNoticePage() {
  const { t } = useTranslation();

  return (
    <LegalPage
      title={t('legalNotice.title')}
      updatedAt={LEGAL_NOTICE_UPDATED_AT}
      intro={t('legalNotice.intro')}
    >
      <LegalSection title={t('legalNotice.publisher.title')}>
        <p>{t('legalNotice.publisher.body', { name: LEGAL_CONTROLLER_NAME })}</p>
        <p>
          <a href={`mailto:${LEGAL_CONTACT_EMAIL}`} className={textLinkClassName}>
            {LEGAL_CONTACT_EMAIL}
          </a>
        </p>
        <p>{t('legalNotice.publisher.anonymity')}</p>
      </LegalSection>

      <LegalSection title={t('legalNotice.host.title')}>
        <p>{t('legalNotice.host.body')}</p>
        <LegalList items={[LEGAL_HOST_NAME, LEGAL_HOST_ADDRESS, LEGAL_HOST_PHONE]} />
      </LegalSection>

      <LegalSection title={t('legalNotice.providers.title')}>
        <LegalList
          items={[t('legalNotice.providers.cloudflare'), t('legalNotice.providers.scaleway')]}
        />
      </LegalSection>

      <ReportContentSection />

      <LegalSection title={t('legalNotice.data.title')}>
        <p>
          <Trans
            i18nKey="legalNotice.data.body"
            components={{ privacy: <Link to={ROUTES.PRIVACY} className={textLinkClassName} /> }}
          />
        </p>
      </LegalSection>
    </LegalPage>
  );
}

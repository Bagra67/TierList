import { useTranslation } from 'react-i18next';

import { LegalList, LegalPage, LegalSection } from '../components/LegalPage';
import { textLinkClassName } from '../components/ui/text-link';
import {
  CNIL_COMPLAINT_URL,
  LEGAL_CONTACT_EMAIL,
  LEGAL_CONTROLLER_NAME,
  PRIVACY_POLICY_UPDATED_AT,
} from '../constants/legal';

// Politique de confidentialité (#200), lisible sans compte. Le texte vient des locales
// (privacy.*) ; ce qu'il décrit est l'inventaire de docs/technical/legal-pages.md.
export function PrivacyPolicyPage() {
  const { t } = useTranslation();

  return (
    <LegalPage
      title={t('privacy.title')}
      updatedAt={PRIVACY_POLICY_UPDATED_AT}
      intro={t('privacy.intro')}
    >
      <LegalSection title={t('privacy.controller.title')}>
        <p>{t('privacy.controller.body', { name: LEGAL_CONTROLLER_NAME })}</p>
        <p>
          <a href={`mailto:${LEGAL_CONTACT_EMAIL}`} className={textLinkClassName}>
            {LEGAL_CONTACT_EMAIL}
          </a>
        </p>
      </LegalSection>

      <LegalSection title={t('privacy.data.title')}>
        <LegalList
          items={[
            t('privacy.data.account'),
            t('privacy.data.google'),
            t('privacy.data.guest'),
            t('privacy.data.content'),
            t('privacy.data.games'),
            t('privacy.data.reports'),
            t('privacy.data.technical'),
          ]}
        />
      </LegalSection>

      <LegalSection title={t('privacy.purposes.title')}>
        <LegalList
          items={[
            t('privacy.purposes.service'),
            t('privacy.purposes.security'),
            t('privacy.purposes.reports'),
          ]}
        />
        <p>{t('privacy.purposes.noAds')}</p>
      </LegalSection>

      <LegalSection title={t('privacy.retention.title')}>
        <LegalList
          items={[
            t('privacy.retention.account'),
            t('privacy.retention.sessions'),
            t('privacy.retention.links'),
            t('privacy.retention.guests'),
            t('privacy.retention.deleted'),
            t('privacy.retention.backups'),
            t('privacy.retention.reports'),
          ]}
        />
      </LegalSection>

      <LegalSection title={t('privacy.visibility.title')}>
        <LegalList
          items={[
            t('privacy.visibility.room'),
            t('privacy.visibility.results'),
            t('privacy.visibility.deletedAccount'),
          ]}
        />
      </LegalSection>

      <LegalSection title={t('privacy.processors.title')}>
        <p>{t('privacy.processors.intro')}</p>
        <LegalList
          items={[
            t('privacy.processors.minestrator'),
            t('privacy.processors.scaleway'),
            t('privacy.processors.cloudflare'),
            t('privacy.processors.google'),
            t('privacy.processors.github'),
          ]}
        />
        <p>{t('privacy.processors.transfers')}</p>
      </LegalSection>

      <LegalSection title={t('privacy.cookies.title')}>
        <p>{t('privacy.cookies.intro')}</p>
        <LegalList
          items={[
            t('privacy.cookies.session'),
            t('privacy.cookies.google'),
            t('privacy.cookies.guest'),
            t('privacy.cookies.local'),
          ]}
        />
      </LegalSection>

      <LegalSection title={t('privacy.security.title')}>
        <p>{t('privacy.security.body')}</p>
      </LegalSection>

      <LegalSection title={t('privacy.rights.title')}>
        <p>{t('privacy.rights.body')}</p>
        <LegalList
          items={[
            t('privacy.rights.delete'),
            t('privacy.rights.request', { email: LEGAL_CONTACT_EMAIL }),
          ]}
        />
        <p>
          {t('privacy.rights.cnil')}{' '}
          <a
            href={CNIL_COMPLAINT_URL}
            target="_blank"
            rel="noreferrer"
            className={textLinkClassName}
          >
            {t('privacy.rights.cnilLink')}
          </a>
        </p>
      </LegalSection>

      <LegalSection title={t('privacy.changes.title')}>
        <p>{t('privacy.changes.body')}</p>
      </LegalSection>
    </LegalPage>
  );
}

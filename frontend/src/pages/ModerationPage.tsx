import { useTranslation } from 'react-i18next';
import { cn } from 'cn';

import { PageContainer } from '../components/PageContainer';
import { CONTENT_COLUMN_CLASS } from '../constants/layout';

// Espace de modération des super admins (US-1.1). Vide pour l'instant : les signalements, le
// journal et les derniers envois y arriveront avec leurs issues
// (docs/product/milestone-2/screens.md).
export function ModerationPage() {
  const { t } = useTranslation();

  return (
    <PageContainer width="app">
      <div className={cn(CONTENT_COLUMN_CLASS, 'flex flex-col items-start gap-6')}>
        <h1 className="text-2xl font-semibold">{t('moderation.title')}</h1>
        <p className="text-muted-foreground">{t('moderation.intro')}</p>
      </div>
    </PageContainer>
  );
}

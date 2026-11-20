import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import { EmptyState } from './EmptyState';
import { type TierChip, TemplateTierChips } from './TemplateTierChips';

interface TemplateContentReadOnlyProps {
  tiers: TierChip[];
  tileCount: number;
  children: ReactNode;
}

export function TemplateContentReadOnly({
  tiers,
  tileCount,
  children,
}: TemplateContentReadOnlyProps) {
  const { t } = useTranslation();
  return (
    <>
      <section className="flex w-full flex-col items-start gap-3">
        <h2 className="text-lg font-semibold">{t('moderation.template.tiers')}</h2>
        <TemplateTierChips tiers={tiers} />
      </section>
      <section className="flex w-full flex-col items-start gap-3">
        <h2 className="text-lg font-semibold">
          {t('moderation.template.tiles', { count: tileCount })}
        </h2>
        {tileCount === 0 ? (
          <EmptyState message={t('moderation.template.noTiles')} />
        ) : (
          <ul className="grid w-full grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {children}
          </ul>
        )}
      </section>
    </>
  );
}

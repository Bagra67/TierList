import { useTranslation } from 'react-i18next';

import type { Template, Tile } from '../api/templates';
import { EmptyState } from './EmptyState';
import { TemplateTierChips } from './TemplateTierChips';
import { TemplateTileCard } from './TemplateTileCard';

interface OfficialTemplateReadOnlyProps {
  template: Template;
  editorName: string | null;
}

export function OfficialTemplateReadOnly({ template, editorName }: OfficialTemplateReadOnlyProps) {
  const { t } = useTranslation();
  return (
    <>
      <div
        role="status"
        className="w-full rounded-lg border border-l-4 border-warning bg-warning/10 px-4 py-3 text-sm"
      >
        <p className="font-semibold">
          {editorName === null
            ? t('officialTemplates.editor.lockedByAnother')
            : t('officialTemplates.editor.lockedBy', { editor: editorName })}
        </p>
        <p>{t('officialTemplates.editor.readOnly')}</p>
      </div>
      <h1 className="text-2xl font-semibold">{template.name}</h1>
      <section className="flex w-full flex-col items-start gap-3">
        <h2 className="text-lg font-semibold">{t('moderation.template.tiers')}</h2>
        <TemplateTierChips tiers={template.tiers} />
      </section>
      <section className="flex w-full flex-col items-start gap-3">
        <h2 className="text-lg font-semibold">
          {t('moderation.template.tiles', { count: template.tiles.length })}
        </h2>
        {template.tiles.length === 0 ? (
          <EmptyState message={t('moderation.template.noTiles')} />
        ) : (
          <ul className="grid w-full grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {template.tiles.map((tile: Tile, index: number) => (
              <TemplateTileCard
                key={tile.id}
                imageUrl={tile.image_url}
                imageRemoved={tile.image_removed}
                imageAlt={t('moderation.template.tileImage', { number: index + 1 })}
                text={tile.text}
              />
            ))}
          </ul>
        )}
      </section>
    </>
  );
}

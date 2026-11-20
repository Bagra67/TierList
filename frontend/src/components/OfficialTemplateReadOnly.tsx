import { useTranslation } from 'react-i18next';

import type { Template, Tile } from '../api/templates';
import { TemplateContentReadOnly } from './TemplateContentReadOnly';
import { TemplateTileCard } from './TemplateTileCard';

export function OfficialTemplateReadOnly({ template }: { template: Template }) {
  const { t } = useTranslation();
  return (
    <>
      <div
        role="status"
        className="w-full rounded-lg border border-l-4 border-warning bg-warning/10 px-4 py-3 text-sm"
      >
        <p className="font-semibold">
          {template.editing_by_name === null
            ? t('officialTemplates.editor.lockedByAnother')
            : t('officialTemplates.editor.lockedBy', { editor: template.editing_by_name })}
        </p>
        <p>{t('officialTemplates.editor.readOnly')}</p>
      </div>
      <h1 className="text-2xl font-semibold">{template.name}</h1>
      <TemplateContentReadOnly tiers={template.tiers} tileCount={template.tiles.length}>
        {template.tiles.map((tile: Tile, index: number) => (
          <TemplateTileCard
            key={tile.id}
            imageUrl={tile.image_url}
            imageRemoved={tile.image_removed}
            imageAlt={t('moderation.template.tileImage', { number: index + 1 })}
            text={tile.text}
          />
        ))}
      </TemplateContentReadOnly>
    </>
  );
}

import { verticalListSortingStrategy } from '@dnd-kit/sortable';
import { useId } from 'react';
import { type UseTranslationResponse, useTranslation } from 'react-i18next';

import {
  type Template,
  type TemplateChange,
  type Tier,
  type TierUpdate,
  useAddTier,
  useDeleteTier,
  useUpdateTier,
} from '../api/templates';
import { TIER_NAME_MAX_LENGTH } from '../constants/templates';
import { getFieldErrors, translateError, translateFieldError } from '../errors/apiError';
import { ColorField } from './ColorField';
import { ErrorMessage } from './ErrorMessage';
import { InlineEditField } from './InlineEditField';
import { SortableList } from './SortableList';
import { Button } from './ui/button';

interface TierEditorProps {
  template: Template;
}

// Tiers d'un template (US-1.4) : chaque action est enregistrée tout de suite
export function TierEditor({ template }: TierEditorProps) {
  const titleId: string = useId();
  const addMutation: TemplateChange<void> = useAddTier(template.id);
  const updateMutation: TemplateChange<TierUpdate> = useUpdateTier(template.id);
  const deleteMutation: TemplateChange<string> = useDeleteTier(template.id);
  const { t }: UseTranslationResponse<'translation', undefined> = useTranslation();
  const tiers: Tier[] = template.tiers;
  // Une seule modification de l'ordre à la fois : les réponses arrivent dans l'ordre des clics
  const isChangingOrder: boolean =
    addMutation.isPending || updateMutation.isPending || deleteMutation.isPending;
  // L'erreur de champ de la 422 concerne le tier dont le nom vient d'être envoyé
  const failedTierId: string | undefined = updateMutation.variables?.tierId;
  const nameError: string | undefined = translateFieldError(
    t,
    getFieldErrors(updateMutation.error).name,
  );
  const lastError: Error | null = addMutation.error ?? updateMutation.error ?? deleteMutation.error;

  function moveTier(tier: Tier, position: number) {
    updateMutation.mutate({ tierId: tier.id, changes: { position } });
  }

  return (
    <section aria-labelledby={titleId} className="flex w-full flex-col gap-3">
      <h2 id={titleId} className="text-lg font-semibold">
        {t('templates.editor.tiers')}
      </h2>
      <ol className="flex w-full flex-col gap-2">
        <SortableList
          items={tiers}
          strategy={verticalListSortingStrategy}
          getItemLabel={(tier) => tier.name}
          onMove={moveTier}
          renderItem={(tier, { setNodeRef, style, handleProps }) => (
            <li
              ref={setNodeRef}
              style={style}
              className="flex items-start gap-2 rounded-md border bg-card px-2 py-2"
            >
              <button
                type="button"
                {...handleProps}
                aria-label={t('templates.editor.dragHandle', { name: tier.name })}
                className="mt-1 cursor-grab touch-none rounded px-1 text-muted-foreground"
              >
                <span aria-hidden="true">⋮⋮</span>
              </button>
              <ColorField
                key={tier.color}
                label={t('templates.editor.tierColor', { name: tier.name })}
                value={tier.color}
                onSave={(color) => updateMutation.mutate({ tierId: tier.id, changes: { color } })}
              />
              <InlineEditField
                key={tier.name}
                label={t('templates.editor.tierName', { position: tier.position + 1 })}
                hideLabel
                value={tier.name}
                maxLength={TIER_NAME_MAX_LENGTH}
                error={failedTierId === tier.id ? nameError : undefined}
                onSave={(name) => updateMutation.mutate({ tierId: tier.id, changes: { name } })}
                className="flex-1"
              />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label={t('templates.editor.moveUp', { name: tier.name })}
                disabled={isChangingOrder || tier.position === 0}
                onClick={() => moveTier(tier, tier.position - 1)}
              >
                <span aria-hidden="true">↑</span>
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label={t('templates.editor.moveDown', { name: tier.name })}
                disabled={isChangingOrder || tier.position === tiers.length - 1}
                onClick={() => moveTier(tier, tier.position + 1)}
              >
                <span aria-hidden="true">↓</span>
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label={t('templates.editor.deleteTier', { name: tier.name })}
                // Une tier list garde au moins un tier (le backend le refuse aussi)
                disabled={isChangingOrder || tiers.length === 1}
                onClick={() => deleteMutation.mutate(tier.id)}
              >
                <span aria-hidden="true">✕</span>
              </Button>
            </li>
          )}
        />
      </ol>
      {lastError !== null && <ErrorMessage>{translateError(t, lastError)}</ErrorMessage>}
      <Button
        type="button"
        variant="outline"
        disabled={isChangingOrder}
        onClick={() => addMutation.mutate()}
      >
        {t('templates.editor.addTier')}
      </Button>
    </section>
  );
}

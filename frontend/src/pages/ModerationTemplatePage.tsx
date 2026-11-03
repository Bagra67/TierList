import { type RefObject, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, type NavigateFunction, useNavigate, useParams } from 'react-router';

import {
  type ReviewedTemplate,
  type ReviewedTile,
  type TemplateModerationAction,
  useModerateTemplate,
  useReviewedTemplate,
} from '../api/moderation';
import { tierColorStyle } from '../components/boardStyles';
import { EmptyState } from '../components/EmptyState';
import { ErrorMessage } from '../components/ErrorMessage';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { ModerationReasonDialog } from '../components/ModerationReasonDialog';
import { RemovedImage } from '../components/RemovedImage';
import { TemplateHiddenBadge } from '../components/TemplateHiddenBadge';
import { Button } from '../components/ui/button';
import { panelVariants } from '../components/ui/panel';
import { textLinkClassName } from '../components/ui/text-link';
import { moderationAccountPath } from '../constants/routes';
import { translateError } from '../errors/apiError';

export function ModerationTemplatePage() {
  const { t } = useTranslation();
  const { templateId = '' } = useParams();
  const { data: template, isPending, isError, error } = useReviewedTemplate(templateId);

  return (
    <div className="flex flex-col items-start gap-6">
      {isPending && <LoadingSkeleton shape="list" />}
      {isError && <ErrorMessage>{translateError(t, error)}</ErrorMessage>}
      {template !== undefined && <TemplateContent template={template} />}
    </div>
  );
}

function TemplateContent({ template }: { template: ReviewedTemplate }) {
  const { t } = useTranslation();
  const navigate: NavigateFunction = useNavigate();
  const dialogRef: RefObject<HTMLDialogElement | null> = useRef<HTMLDialogElement>(null);
  const [action, setAction] = useState<TemplateModerationAction>('hide');
  const moderateMutation = useModerateTemplate();
  const isHidden: boolean = template.moderation === 'hidden';
  const actions: TemplateModerationAction[] = isHidden ? ['unhide', 'delete'] : ['hide', 'delete'];
  const accountPath: string = moderationAccountPath(template.owner_id);

  function openDialog(chosenAction: TemplateModerationAction) {
    setAction(chosenAction);
    dialogRef.current?.showModal();
  }

  async function moderate(reason: string): Promise<boolean> {
    try {
      await moderateMutation.mutateAsync({ templateId: template.id, action, reason });
    } catch {
      return false;
    }
    if (action === 'delete') void navigate(accountPath);
    return true;
  }

  return (
    <>
      <div className="flex w-full flex-col gap-2">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-semibold break-words">{template.name}</h1>
          {isHidden && <TemplateHiddenBadge />}
        </div>
        <p className="text-muted-foreground">
          <Link to={accountPath} className={textLinkClassName}>
            {template.owner_name ?? t('moderation.template.unknownOwner')}
          </Link>
          {' · '}
          {t('moderation.template.updatedAt', { date: new Date(template.updated_at) })}
        </p>
        {template.moderation_reason !== null && (
          <p>{t('moderation.template.hiddenReason', { reason: template.moderation_reason })}</p>
        )}
      </div>

      <div className="flex gap-2">
        {actions.map((templateAction: TemplateModerationAction) => (
          <Button
            key={templateAction}
            type="button"
            size="sm"
            variant={templateAction === 'delete' ? 'destructive' : 'secondary'}
            onClick={() => openDialog(templateAction)}
          >
            {t(`moderation.actions.${templateAction}`)}
          </Button>
        ))}
      </div>

      <section className="flex w-full flex-col items-start gap-3">
        <h2 className="text-lg font-semibold">{t('moderation.template.tiers')}</h2>
        <ol className="flex flex-wrap gap-2">
          {template.tiers.map((tier) => (
            <li
              key={tier.id}
              style={tierColorStyle(tier.color)}
              className="rounded-md px-2 py-1 font-semibold break-words"
            >
              {tier.name}
            </li>
          ))}
        </ol>
      </section>

      <section className="flex w-full flex-col items-start gap-3">
        <h2 className="text-lg font-semibold">
          {t('moderation.template.tiles', { count: template.tiles.length })}
        </h2>
        {template.tiles.length === 0 ? (
          <EmptyState message={t('moderation.template.noTiles')} />
        ) : (
          <ul className="grid w-full grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {template.tiles.map((tile: ReviewedTile, index: number) => (
              <TileCard key={tile.id} tile={tile} number={index + 1} />
            ))}
          </ul>
        )}
      </section>

      <ModerationReasonDialog
        dialogRef={dialogRef}
        title={t(`moderation.templateDialog.${action}.title`, { name: template.name })}
        description={t(`moderation.templateDialog.${action}.description`)}
        submitLabel={t(`moderation.templateDialog.${action}.submit`)}
        submittingLabel={t(`moderation.templateDialog.${action}.submitting`)}
        destructive={action === 'delete'}
        isPending={moderateMutation.isPending}
        translatedFailureMessage={
          moderateMutation.isError ? translateError(t, moderateMutation.error) : null
        }
        onSubmit={moderate}
        onClose={() => moderateMutation.reset()}
      />
    </>
  );
}

function TileCard({ tile, number }: { tile: ReviewedTile; number: number }) {
  const { t } = useTranslation();
  return (
    <li className={panelVariants({ className: 'gap-2 p-3' })}>
      {tile.image_status === 'deleted' && (
        <RemovedImage className="aspect-square w-full rounded-sm" showLabel={true} />
      )}
      {tile.image_url !== null && (
        <img
          src={tile.image_url}
          alt={t('moderation.template.tileImage', { number })}
          className="aspect-square w-full rounded-sm object-cover"
        />
      )}
      {tile.image_status === 'hidden' && (
        <p className="text-sm font-medium text-destructive">
          {t('moderation.template.imageHidden')}
        </p>
      )}
      {tile.text !== null && <p className="text-sm font-medium break-words">{tile.text}</p>}
    </li>
  );
}

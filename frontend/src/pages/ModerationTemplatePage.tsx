import { useTranslation } from 'react-i18next';
import { Link, type NavigateFunction, useNavigate, useParams } from 'react-router';

import {
  type ReviewedTemplate,
  type ReviewedTile,
  isDestructiveTemplateAction,
  type TemplateModerationAction,
  useReviewedTemplate,
} from '../api/moderation';
import { DeletionDetails } from '../components/DeletionDetails';
import { EmptyState } from '../components/EmptyState';
import { eraseCountdown, isEraseUrgent } from '../components/eraseCountdown';
import { ErrorMessage } from '../components/ErrorMessage';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { TemplateHiddenBadge } from '../components/TemplateHiddenBadge';
import {
  type TemplateModerationDialog,
  useTemplateModerationDialog,
} from '../components/TemplateModerationDialog';
import { TemplateTierChips } from '../components/TemplateTierChips';
import { TemplateTileCard } from '../components/TemplateTileCard';
import { Button } from '../components/ui/button';
import { textLinkClassName } from '../components/ui/text-link';
import { cn } from 'cn';
import { moderationAccountPath, ROUTES } from '../constants/routes';
import { translateError } from '../errors/apiError';
import { useDocumentTitle } from '../components/useDocumentTitle';

export function ModerationTemplatePage() {
  const { t } = useTranslation();
  const { templateId = '' } = useParams();
  const { data: template, isPending, isError, error } = useReviewedTemplate(templateId);
  useDocumentTitle(template?.name);

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
  const isHidden: boolean = template.moderation === 'hidden';
  const isDeleted: boolean = template.deleted_at !== null;
  const actions: TemplateModerationAction[] = isDeleted
    ? ['restore', 'purge']
    : isHidden
      ? ['unhide', 'delete']
      : ['hide', 'delete'];
  const accountPath: string = moderationAccountPath(template.owner_id);

  const moderation: TemplateModerationDialog = useTemplateModerationDialog(
    (action: TemplateModerationAction) => {
      if (action === 'delete') void navigate(accountPath);
      if (action === 'purge') void navigate(ROUTES.MODERATION_DELETED_TEMPLATES);
    },
  );

  return (
    <>
      {isDeleted && (
        <Link to={ROUTES.MODERATION_DELETED_TEMPLATES} className={textLinkClassName}>
          {t('moderation.deletedTemplates.back')}
        </Link>
      )}
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

      {template.deleted_at !== null && template.erase_at !== null && (
        <section
          role="note"
          className={cn(
            'flex w-full flex-col gap-1 rounded-lg border border-l-4 border-warning p-4 text-sm',
            isEraseUrgent(template.erase_at) && 'bg-warning/10',
          )}
        >
          <DeletionDetails
            deletedAt={template.deleted_at}
            deletionReason={template.deletion_reason}
          />
          <p className="font-medium">
            {t('moderation.deletedTemplates.eraseAt', { date: new Date(template.erase_at) })}
            {' · '}
            {eraseCountdown(t, template.erase_at)}
          </p>
        </section>
      )}

      <div className="flex gap-2">
        {actions.map((templateAction: TemplateModerationAction) => (
          <Button
            key={templateAction}
            type="button"
            size="sm"
            variant={isDestructiveTemplateAction(templateAction) ? 'destructive' : 'secondary'}
            onClick={() => moderation.open(template.id, template.name, templateAction)}
          >
            {t(`moderation.actions.${templateAction}`)}
          </Button>
        ))}
      </div>

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
            {template.tiles.map((tile: ReviewedTile, index: number) => (
              <TileCard key={tile.id} tile={tile} number={index + 1} />
            ))}
          </ul>
        )}
      </section>

      {moderation.dialog}
    </>
  );
}

function TileCard({ tile, number }: { tile: ReviewedTile; number: number }) {
  const { t } = useTranslation();
  return (
    <TemplateTileCard
      imageUrl={tile.image_url}
      imageRemoved={tile.image_status === 'deleted'}
      imageAlt={t('moderation.template.tileImage', { number })}
      text={tile.text}
    >
      {tile.image_status === 'hidden' && (
        <p className="text-sm font-medium text-destructive">
          {t('moderation.template.imageHidden')}
        </p>
      )}
    </TemplateTileCard>
  );
}

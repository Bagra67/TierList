import { type RefObject, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import {
  type ReportDecisionKind,
  type ReportedContent,
  useDecideReport,
  useReportQueue,
} from '../api/moderation';
import { moderationAccountPath, resultsPath } from '../constants/routes';
import { translateError } from '../errors/apiError';
import { PagedList } from './PagedList';
import { EmptyState } from './EmptyState';
import { ModerationReasonDialog } from './ModerationReasonDialog';
import { Button } from './ui/button';
import { panelVariants } from './ui/panel';
import { textLinkClassName } from './ui/text-link';

const DECISIONS_BY_TARGET: Partial<Record<ReportedContent['target_type'], ReportDecisionKind[]>> = {
  image: ['dismiss', 'hide_image', 'delete_image'],
  nickname: ['dismiss', 'remove_nickname'],
  game: ['dismiss', 'hide_game'],
};

interface ReportQueueProps {
  ownerId?: string;
  emptyMessage: string;
}

interface PendingDecision {
  content: ReportedContent;
  kind: ReportDecisionKind;
}

export function ReportQueue({ ownerId, emptyMessage }: ReportQueueProps) {
  const { t } = useTranslation();
  const query = useReportQueue(ownerId);
  const contents: ReportedContent[] = query.data?.pages.flatMap((page) => page.contents) ?? [];

  const dialogRef: RefObject<HTMLDialogElement | null> = useRef<HTMLDialogElement>(null);
  const [pending, setPending] = useState<PendingDecision | null>(null);
  const decideMutation = useDecideReport();

  function openDialog(content: ReportedContent, kind: ReportDecisionKind) {
    setPending({ content, kind });
    dialogRef.current?.showModal();
  }

  async function decide(reason: string): Promise<boolean> {
    if (pending === null) return false;
    try {
      await decideMutation.mutateAsync({ ...pending, reason });
    } catch {
      return false;
    }
    return true;
  }

  function closeDialog() {
    decideMutation.reset();
    setPending(null);
  }

  const kind: ReportDecisionKind = pending?.kind ?? 'dismiss';

  return (
    <>
      <PagedList
        query={query}
        itemCount={contents.length}
        empty={<EmptyState message={emptyMessage} />}
        moreLabel={t('moderation.reports.more')}
      >
        <ul className="flex w-full flex-col gap-4">
          {contents.map((content: ReportedContent) => (
            <ReportedContentCard
              key={`${content.target_type}-${content.target_id}`}
              content={content}
              onDecide={openDialog}
            />
          ))}
        </ul>
      </PagedList>

      <ModerationReasonDialog
        dialogRef={dialogRef}
        title={t(`moderation.reports.decisions.${kind}.title`)}
        description={t(`moderation.reports.decisions.${kind}.description`)}
        submitLabel={t(`moderation.reports.decisions.${kind}.submit`)}
        submittingLabel={t(`moderation.reports.decisions.${kind}.submitting`)}
        destructive={kind !== 'dismiss'}
        isPending={decideMutation.isPending}
        translatedFailureMessage={
          decideMutation.isError ? translateError(t, decideMutation.error) : null
        }
        onSubmit={decide}
        onClose={closeDialog}
      />
    </>
  );
}

interface ReportedContentCardProps {
  content: ReportedContent;
  onDecide: (content: ReportedContent, kind: ReportDecisionKind) => void;
}

function ReportedContentCard({ content, onDecide }: ReportedContentCardProps) {
  const { t } = useTranslation();
  const contentName: string = content.label ?? t('moderation.reports.type.image');
  const decisions: ReportDecisionKind[] = DECISIONS_BY_TARGET[content.target_type] ?? ['dismiss'];

  return (
    <li className={panelVariants()}>
      <div className="flex flex-wrap items-start gap-4">
        {content.image_url !== null && (
          <img
            src={content.image_url}
            alt={contentName}
            className="size-24 rounded-sm object-cover"
          />
        )}
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <p className="text-sm text-muted-foreground">
            {t(`moderation.reports.type.${content.target_type}`)}
          </p>
          {content.label !== null && <p className="font-semibold break-words">{content.label}</p>}
          <p className="text-sm text-muted-foreground">
            {content.owner_name ?? t('moderation.reports.noOwner')}
            {' · '}
            {t('moderation.reports.count', { count: content.report_count })}
            {' · '}
            {t('moderation.reports.since', { date: new Date(content.first_reported_at) })}
          </p>
          <ul className="flex flex-wrap gap-2 text-sm">
            {content.reasons.map(({ reason, count }) => (
              <li key={reason} className="rounded-md bg-muted px-2 py-0.5">
                {t('moderation.reports.reason', {
                  reason: t(`report.reasons.${reason}`),
                  count,
                })}
              </li>
            ))}
          </ul>
          {content.details.length > 0 && (
            <ul className="mt-1 flex flex-col gap-1 text-sm">
              {content.details.map((detail: string, index: number) => (
                <li key={index} className="break-words">
                  {detail}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {decisions.map((kind: ReportDecisionKind) => (
          <Button
            key={kind}
            type="button"
            size="sm"
            variant={kind === 'dismiss' ? 'outline' : 'destructive'}
            aria-label={t(`moderation.reports.decisions.${kind}.openLabel`, { name: contentName })}
            onClick={() => onDecide(content, kind)}
          >
            {t(`moderation.reports.decisions.${kind}.open`)}
          </Button>
        ))}
        {content.owner_id !== null && (
          <Link to={moderationAccountPath(content.owner_id)} className={textLinkClassName}>
            {t('moderation.reports.viewAccount')}
          </Link>
        )}
        {content.public_token !== null && (
          <Link to={resultsPath(content.public_token)} className={textLinkClassName}>
            {t('moderation.reports.viewResults')}
          </Link>
        )}
      </div>
    </li>
  );
}

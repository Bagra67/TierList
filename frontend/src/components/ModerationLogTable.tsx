import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import {
  type ModerationLogEntry,
  type ModerationLogFilters,
  useModerationLog,
} from '../api/moderation';
import { moderationAccountPath } from '../constants/routes';
import { translateError } from '../errors/apiError';
import { EmptyState } from './EmptyState';
import { ErrorMessage } from './ErrorMessage';
import { LoadingSkeleton } from './LoadingSkeleton';
import { Button } from './ui/button';

interface ModerationLogTableProps {
  filters: ModerationLogFilters;
  emptyMessage: string;
}

export function ModerationLogTable({ filters, emptyMessage }: ModerationLogTableProps) {
  const { t } = useTranslation();
  const { data, isPending, isError, error, hasNextPage, fetchNextPage, isFetchingNextPage } =
    useModerationLog(filters);
  const entries: ModerationLogEntry[] = data?.pages.flatMap((page) => page.entries) ?? [];

  return (
    <>
      {isPending && <LoadingSkeleton shape="list" />}
      {isError && <ErrorMessage>{translateError(t, error)}</ErrorMessage>}
      {data !== undefined && entries.length === 0 && <EmptyState message={emptyMessage} />}
      {entries.length > 0 && (
        <div className="w-full overflow-x-auto rounded-panel border bg-card">
          <table className="w-full text-sm">
            <caption className="sr-only">{t('moderation.log.title')}</caption>
            <thead>
              <tr className="border-b bg-muted/50 text-left">
                <th scope="col" className="px-3 py-2 font-medium">
                  {t('moderation.log.columns.at')}
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  {t('moderation.log.columns.actor')}
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  {t('moderation.log.columns.action')}
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  {t('moderation.log.columns.target')}
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  {t('moderation.log.columns.reason')}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {entries.map((entry: ModerationLogEntry) => (
                <tr key={entry.id} className="align-top">
                  <td className="px-3 py-2 whitespace-nowrap text-muted-foreground">
                    {t('moderation.log.at', { date: new Date(entry.created_at) })}
                  </td>
                  <td className="px-3 py-2">{entry.actor_name}</td>
                  <td className="px-3 py-2">{t(`moderation.actions.${entry.action}`)}</td>
                  <td className="px-3 py-2">
                    <LogTarget entry={entry} />
                  </td>
                  <td className="px-3 py-2">{entry.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {hasNextPage && (
        <Button
          type="button"
          variant="outline"
          disabled={isFetchingNextPage}
          onClick={() => void fetchNextPage()}
        >
          {isFetchingNextPage ? t('common.loading') : t('moderation.log.more')}
        </Button>
      )}
    </>
  );
}

function LogTarget({ entry }: { entry: ModerationLogEntry }) {
  const { t } = useTranslation();
  const label: string = t('moderation.log.targetCell', {
    type: t(`moderation.targets.${entry.target_type}`),
    label: entry.target_label,
  });
  if (entry.target_type !== 'account' || entry.target_id === null) return label;
  return (
    <Link
      to={moderationAccountPath(entry.target_id)}
      className="underline-offset-4 hover:underline"
    >
      {label}
    </Link>
  );
}

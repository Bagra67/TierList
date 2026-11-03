import { type FormEvent, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import { type AccountSummary, useAccountSearch } from '../api/moderation';
import { EmptyState } from '../components/EmptyState';
import { ErrorMessage } from '../components/ErrorMessage';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { TextField } from '../components/TextField';
import { Button } from '../components/ui/button';
import { panelVariants } from '../components/ui/panel';
import { moderationAccountPath } from '../constants/routes';
import { translateError } from '../errors/apiError';

export function ModerationAccountsPage() {
  const { t } = useTranslation();
  const [queryDraft, setQueryDraft] = useState<string>('');
  const [query, setQuery] = useState<string | undefined>(undefined);
  const { data, isPending, isError, error, hasNextPage, fetchNextPage, isFetchingNextPage } =
    useAccountSearch(query);
  const accounts: AccountSummary[] = data?.pages.flatMap((page) => page.accounts) ?? [];

  function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const searched: string = queryDraft.trim();
    setQuery(searched === '' ? undefined : searched);
  }

  return (
    <div className="flex flex-col items-start gap-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">{t('moderation.accounts.title')}</h1>
        <p className="text-muted-foreground">{t('moderation.accounts.intro')}</p>
      </div>

      <form onSubmit={search} className="flex flex-wrap items-end gap-3">
        <TextField
          label={t('moderation.accounts.query')}
          name="query"
          placeholder={t('moderation.accounts.queryPlaceholder')}
          value={queryDraft}
          onChange={(event) => setQueryDraft(event.target.value)}
        />
        <Button type="submit" variant="outline">
          {t('moderation.accounts.search')}
        </Button>
      </form>

      {isPending && <LoadingSkeleton shape="list" />}
      {isError && <ErrorMessage>{translateError(t, error)}</ErrorMessage>}
      {data !== undefined && accounts.length === 0 && (
        <EmptyState message={t('moderation.accounts.empty')} />
      )}
      {accounts.length > 0 && (
        <ul className={panelVariants({ variant: 'list', className: 'w-full' })}>
          {accounts.map((account: AccountSummary) => (
            <li key={account.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-3">
              <Link
                to={moderationAccountPath(account.id)}
                className="font-medium underline-offset-4 hover:underline"
              >
                {account.display_name}
              </Link>
              <span className="text-sm text-muted-foreground">{account.email}</span>
              <span className="text-sm text-muted-foreground">
                {t('moderation.accounts.createdAt', { date: new Date(account.created_at) })}
              </span>
              {account.role === 'super_admin' && (
                <span className="rounded-md border px-2 py-0.5 text-xs font-semibold">
                  {t('moderation.accounts.superAdmin')}
                </span>
              )}
              {account.banned && (
                <span className="rounded-md border border-destructive/40 px-2 py-0.5 text-xs font-semibold">
                  {t('moderation.accounts.banned')}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
      {hasNextPage && (
        <Button
          type="button"
          variant="outline"
          disabled={isFetchingNextPage}
          onClick={() => void fetchNextPage()}
        >
          {isFetchingNextPage ? t('common.loading') : t('moderation.accounts.more')}
        </Button>
      )}
    </div>
  );
}

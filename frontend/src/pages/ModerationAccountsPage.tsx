import { type FormEvent, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';

import { type AccountSummary, useAccountSearch } from '../api/moderation';
import { PagedList } from '../components/PagedList';
import { EmptyState } from '../components/EmptyState';
import { TextField } from '../components/TextField';
import { Button } from '../components/ui/button';
import { panelVariants } from '../components/ui/panel';
import { moderationAccountPath } from '../constants/routes';

export function ModerationAccountsPage() {
  const { t } = useTranslation();
  const [queryDraft, setQueryDraft] = useState<string>('');
  const [query, setQuery] = useState<string | undefined>(undefined);
  const accountSearch = useAccountSearch(query);
  const accounts: AccountSummary[] =
    accountSearch.data?.pages.flatMap((page) => page.accounts) ?? [];

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

      <PagedList
        query={accountSearch}
        itemCount={accounts.length}
        empty={<EmptyState message={t('moderation.accounts.empty')} />}
        moreLabel={t('moderation.accounts.more')}
      >
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
      </PagedList>
    </div>
  );
}
